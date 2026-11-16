"""Optional runtime controls. No game memory access or screen capture."""
from datetime import datetime
import json
import logging
from pathlib import Path
import time

from PyQt6.QtCore import QObject, QTimer, pyqtSignal
from core.config import PROFILE_NAMES
from core.hotkey_manager import valid_shortcut
from core.preset_library import atomic_json
from core.win_utils import foreground_window

log = logging.getLogger(__name__)


def recommend_input(samples):
    values = sorted(v for v in samples if type(v) in (int, float) and 15 < v < 1_000_000)
    if len(values) < 5:
        raise ValueError("有效输入太少；请正常移动鼠标后重试，也可保留原设置。")
    peak = values[min(len(values) - 1, int(len(values) * 0.85))]
    sensitivity = max(200.0, min(20000.0, peak))
    threshold = min(sensitivity - 100, max(0.0, sensitivity * 0.10))
    return dict(vignette_sensitivity=round(sensitivity), vignette_threshold=round(threshold))


class ExtensionController(QObject):
    context_changed = pyqtSignal()
    notification = pyqtSignal(str)
    state_changed = pyqtSignal()
    request_toggle = pyqtSignal()

    def __init__(self, manager, library, overlay, parent=None):
        super().__init__(parent)
        self.manager, self.library, self.overlay = manager, library, overlay
        self.hotkeys = None
        self.bridge = None
        self._syncing = False
        self._last_context = None
        self._last_auto_check = 0.0
        self._last_buttons = 0
        self.session_running = False
        self.session_elapsed = 0.0
        self.session_name = "本次游戏"
        self._last_tick = time.monotonic()
        self._next_reminder = 0.0
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.tick)
        manager.add_listener(self.config_changed)
        self.config_changed(manager.config)

    def attach_hotkeys(self, hotkeys, bridge):
        self.hotkeys, self.bridge = hotkeys, bridge
        self.config_changed(self.manager.config)

    def config_changed(self, cfg):
        if self._syncing:
            return
        self._syncing = True
        try:
            if not cfg.game_library_enabled and self.library.active_id:
                if self.library.deactivate():
                    self.context_changed.emit()
                else:
                    cfg.game_library_enabled = True
                    self.notification.emit("游戏方案保存失败，已保留当前参数，请检查目录权限。")
            context = (self.library.active_id, cfg.active_profile)
            if self._last_context != context:
                self.overlay.set_comfort_active(False)
                self._last_context = context
            interval = 50 if cfg.controls_enabled and cfg.controls_gamepad_enabled else 1000
            needed = (cfg.game_library_enabled and cfg.game_auto_switch_enabled) or cfg.session_tools_enabled or (cfg.controls_enabled and cfg.controls_gamepad_enabled)
            if needed:
                self.timer.start(interval)
            else:
                self.timer.stop()
            if not cfg.session_tools_enabled:
                self.session_running = False
            self._last_tick = time.monotonic()
            if self.hotkeys and self.bridge:
                toggle = cfg.hotkey_toggle
                bindings, hold_key = {}, ""
                if cfg.comfort_enabled:
                    bindings["<ctrl>+<alt>+b"] = self.bridge.trigger_comfort.emit
                if cfg.controls_enabled:
                    keys = (cfg.controls_toggle_key, cfg.controls_comfort_key, cfg.controls_profile_key)
                    if all(valid_shortcut(k) for k in keys) and len(set(keys)) == 3:
                        bindings.clear()
                        toggle = keys[0]
                        bindings[keys[2]] = self.bridge.trigger_profile.emit
                        if cfg.comfort_enabled:
                            if cfg.controls_comfort_hold:
                                hold_key = keys[1]
                            else:
                                bindings[keys[1]] = self.bridge.trigger_comfort.emit
                    else:
                        self.notification.emit("快捷键格式无效或重复，继续使用原来的主开关快捷键。")
                self.hotkeys.configure(toggle, bindings, hold_key, self.bridge.hold_comfort.emit)
            self.state_changed.emit()
        finally:
            self._syncing = False

    def cycle_profile(self):
        self.overlay.set_comfort_active(False)
        names = list(PROFILE_NAMES)
        current = self.manager.config.active_profile
        if self.manager.switch_profile(names[(names.index(current) + 1) % len(names)]):
            self.context_changed.emit()
        else:
            self.notification.emit("方案保存失败，请检查目录权限。")

    def tick(self, now=None):
        now = time.monotonic() if now is None else now
        delta = max(0.0, min(5.0, now - self._last_tick))
        self._last_tick = now
        cfg = self.manager.config
        if cfg.game_library_enabled and cfg.game_auto_switch_enabled and now - self._last_auto_check >= 1:
            self._last_auto_check = now
            _, title = foreground_window()
            match = self.library.match(title)
            if match and match != self.library.active_id:
                if self.library.activate(match):
                    self.context_changed.emit()
                else:
                    self.notification.emit("自动切换未完成，原参数已保留。")
        if cfg.controls_enabled and cfg.controls_gamepad_enabled:
            self.overlay.gamepad.poll(cfg)
            buttons = self.overlay.gamepad.buttons
            # Back + Start toggles the overlay; Back + Y toggles comfort.
            _, title = foreground_window()
            allowed = not cfg.only_target_window or (bool(cfg.target_window_title) and cfg.target_window_title.casefold() in title.casefold())
            for mask, action in ((0x0030, self.request_toggle.emit), (0x8020, self.overlay.toggle_comfort)):
                if allowed and buttons & mask == mask and self._last_buttons & mask != mask:
                    action()
            self._last_buttons = buttons
        else:
            self._last_buttons = 0
        if self.session_running and cfg.session_tools_enabled and cfg.overlay_visible and self.overlay._context_allowed:
            self.session_elapsed += delta
            if cfg.break_reminder_enabled and self.session_elapsed >= self._next_reminder:
                self.notification.emit("本次使用已达到提醒时间。可以暂停游戏、离开屏幕休息；不适时请立即停止。")
                self._next_reminder = self.session_elapsed + cfg.break_minutes * 60
        self.state_changed.emit()

    def start_session(self):
        cfg = self.manager.config
        if not cfg.session_tools_enabled:
            return
        self.session_elapsed = 0.0
        self._last_tick = time.monotonic()
        self._next_reminder = cfg.break_minutes * 60
        entry = self.library.entries.get(self.library.active_id)
        self.session_name = entry["name"] if entry else "本次游戏"
        self.session_running = True
        self.state_changed.emit()

    def pause_session(self):
        self.tick()
        self.session_running = False
        self.state_changed.emit()

    def resume_session(self):
        if self.manager.config.session_tools_enabled:
            self._last_tick = time.monotonic()
            if self._next_reminder <= self.session_elapsed:
                self._next_reminder = self.session_elapsed + self.manager.config.break_minutes * 60
            self.session_running = True
            self.state_changed.emit()

    @property
    def records_path(self):
        return Path(self.manager.config_dir) / "comfort-history.json"

    def records(self):
        if not self.records_path.exists():
            return []
        data = json.loads(self.records_path.read_text(encoding="utf-8"))
        if not isinstance(data, list):
            raise ValueError("本地体验记录格式无效，原文件已保留")
        return [item for item in data[-200:] if isinstance(item, dict)]

    def record_session(self, feeling, note=""):
        cfg = self.manager.config
        if not cfg.session_tools_enabled or not cfg.session_recording_enabled:
            raise ValueError("请先启用本地体验记录")
        if feeling not in ("舒服些", "没变化", "更难受"):
            raise ValueError("请选择本次感受")
        self.pause_session()
        if self.session_elapsed <= 0:
            raise ValueError("请先开始一次计时")
        rows = self.records()
        rows.append(dict(time=datetime.now().astimezone().isoformat(timespec="seconds"),
                         name=self.session_name, seconds=round(self.session_elapsed), feeling=feeling,
                         note=note[:500], profile=cfg.active_profile,
                         settings={"idle_alpha": cfg.vignette_idle_alpha, "max_alpha": cfg.vignette_max_alpha,
                                   "inner_radius": cfg.vignette_inner_radius,
                                   "anchors": cfg.anchors_enabled, "triangles": cfg.edge_triangles_enabled,
                                   "columns": cfg.reference_columns_enabled}))
        atomic_json(self.records_path, rows[-200:])
        self.session_elapsed = 0.0
        self.state_changed.emit()
        return True

    def stop(self):
        self.timer.stop()
        self.session_running = False
        self.overlay.set_comfort_active(False)
