"""A click-through comfort overlay with adaptive rendering and optional game binding."""
import math
import time
from collections import OrderedDict
from PyQt6.QtWidgets import QWidget, QApplication
from PyQt6.QtCore import Qt, QTimer, QPointF, QRectF
from PyQt6.QtGui import QPainter, QColor, QRadialGradient, QPen, QBrush, QImage, QPolygonF
from core.config import ConfigManager, AppConfig
from ui.overlay_painter import OverlayPainter
from core.mouse_tracker import MouseSpeedTracker
from core.gamepad import GamepadTracker
from core.win_utils import (make_window_click_through, bring_window_to_topmost,
                            foreground_window, client_geometry)

class MotionSicknessOverlay(QWidget, OverlayPainter):
    def __init__(self, config_manager: ConfigManager, mouse_tracker: MouseSpeedTracker):
        super().__init__()
        self.cfg_mgr = config_manager
        self.mouse_tracker = mouse_tracker
        self.gamepad = GamepadTracker()
        self.current_vignette_alpha = 0.0
        self.current_anchor_boost = 0.0
        self._gamepad_strength = 0.0
        self._comfort_active = False
        self._is_sleeping = False
        self._last_tick = time.perf_counter()
        self._textures = OrderedDict()
        self._target_hwnd = 0
        self._target_title = ""
        self._context_allowed = True
        self._last_topmost = 0.0
        self.status_text = "已就绪"
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint |
                            Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Tool |
                            Qt.WindowType.WindowTransparentForInput)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)
        self.timer = QTimer(self)
        self.timer.setTimerType(Qt.TimerType.PreciseTimer)
        self.timer.timeout.connect(self._animation_tick)
        self.context_timer = QTimer(self)
        self.context_timer.timeout.connect(self.refresh_context)
        self.mouse_tracker.motion_detected.connect(self._wake_animation)
        self.cfg_mgr.add_listener(self.on_config_changed)
        app = QApplication.instance()
        app.screenAdded.connect(self._screens_changed)
        app.screenRemoved.connect(self._screens_changed)
        self._connected_screens = set()
        self._connect_screens()
        self.update_screen_geometry()

    def _connect_screens(self):
        for screen in QApplication.screens():
            if screen not in self._connected_screens:
                screen.geometryChanged.connect(self._screens_changed)
                self._connected_screens.add(screen)

    def _screens_changed(self, *args):
        self._connect_screens()
        self.refresh_context()

    def update_screen_geometry(self, target_hwnd=0):
        screens = QApplication.screens()
        if not screens:
            return
        cfg = self.cfg_mgr.config
        geom = client_geometry(target_hwnd, screens) if target_hwnd else None
        if geom is None:
            screen = screens[cfg.selected_screen_index] if cfg.selected_screen_index < len(screens) else QApplication.primaryScreen()
            geom = screen.geometry()
        if not geom.isEmpty() and geom != self.geometry():
            self.setGeometry(geom)
            self.update()

    def refresh_context(self):
        cfg = self.cfg_mgr.config
        if cfg.target_window_title != self._target_title:
            self._target_title = cfg.target_window_title
            self._target_hwnd = 0
        allowed = cfg.overlay_visible
        hwnd = 0
        if allowed and cfg.only_target_window:
            foreground, title = foreground_window()
            match = bool(self._target_title and self._target_title.casefold() in title.casefold())
            if foreground and (match or foreground == self._target_hwnd):
                hwnd = foreground
                self._target_hwnd = foreground
            else:
                allowed = False
        self._context_allowed = allowed
        if allowed:
            self.update_screen_geometry(hwnd)
            if not self.isVisible():
                self.show()
            if cfg.gamepad_enabled:
                strength = self.gamepad.poll(cfg)
                if strength != self._gamepad_strength:
                    self._gamepad_strength = strength
                    self._wake_animation()
            else:
                self._gamepad_strength = 0.0
            if time.perf_counter() - self._last_topmost > 2:
                self.reapply_topmost()
            self.status_text = "游戏窗口内运行" if cfg.only_target_window else "所选屏幕内运行"
        else:
            self.hide()
            self.mouse_tracker.set_enabled(False)
            self._gamepad_strength = 0.0
            self.status_text = "已暂停" if not cfg.overlay_visible else "等待目标游戏获得焦点"
        if cfg.overlay_visible:
            self.context_timer.start(50 if cfg.gamepad_enabled else 250)
        else:
            self.context_timer.stop()

    def showEvent(self, event):
        super().showEvent(event)
        if QApplication.instance().platformName() == "windows":
            make_window_click_through(int(self.winId()))
        self.mouse_tracker.set_enabled(True)
        self.mouse_tracker.reset()
        self.current_vignette_alpha = 0.0
        self.current_anchor_boost = 0.0
        self._wake_animation()

    def hideEvent(self, event):
        super().hideEvent(event)
        self.timer.stop()
        self.mouse_tracker.set_enabled(False)
        self.current_vignette_alpha = 0.0
        self.current_anchor_boost = 0.0
        self._is_sleeping = True

    def on_config_changed(self, cfg: AppConfig):
        if not cfg.comfort_enabled or not cfg.overlay_visible:
            self._comfort_active = False
        self.timer.setInterval(max(8, round(1000 / cfg.fps_limit)))
        self.refresh_context()
        self._wake_animation()
        self.update()

    def set_comfort_active(self, active):
        self._comfort_active = bool(active and self.cfg_mgr.config.comfort_enabled and self.cfg_mgr.config.overlay_visible)
        self._wake_animation()
        self.update()

    def toggle_comfort(self):
        self.set_comfort_active(not self._comfort_active)

    def reapply_topmost(self):
        if self.isVisible() and self._context_allowed:
            if QApplication.instance().platformName() == "windows":
                bring_window_to_topmost(int(self.winId()))
            self._last_topmost = time.perf_counter()

    def _wake_animation(self):
        if not self.isVisible() or not self._context_allowed:
            return
        if not self.timer.isActive():
            self._last_tick = time.perf_counter() - 1 / self.cfg_mgr.config.fps_limit
            self.timer.start(max(8, round(1000 / self.cfg_mgr.config.fps_limit)))
        self._is_sleeping = False

    def _animation_tick(self):
        if not self.isVisible():
            return
        cfg = self.cfg_mgr.config
        now = time.perf_counter()
        dt = max(0.001, min(0.1, now - self._last_tick))
        self._last_tick = now
        speed, moving = self.mouse_tracker.poll_speed(cfg.vignette_decay_time)
        ratio = max(0.0, min(1.0, (speed * cfg.mouse_gain - cfg.vignette_threshold) /
                               max(100.0, cfg.vignette_sensitivity - cfg.vignette_threshold)))
        ratio = max(ratio, self._gamepad_strength)
        target_motion = ratio * ratio * (3 - 2 * ratio)
        target_alpha = (cfg.vignette_idle_alpha +
                        (cfg.vignette_max_alpha - cfg.vignette_idle_alpha) * target_motion) if cfg.vignette_enabled else 0.0
        if self._comfort_active and cfg.comfort_enabled:
            target_alpha = cfg.comfort_alpha
        previous_alpha = self.current_vignette_alpha
        previous_motion = self.current_anchor_boost
        tau = 0.055 if target_motion > previous_motion else cfg.vignette_decay_time / 2.3
        blend = -math.expm1(-dt / max(0.025, tau))
        self.current_anchor_boost += (target_motion - previous_motion) * blend
        self.current_vignette_alpha += (target_alpha - previous_alpha) * blend
        settled = (abs(self.current_anchor_boost - target_motion) < 0.002 and
                   abs(self.current_vignette_alpha - target_alpha) < 0.002)
        if settled:
            self.current_anchor_boost = target_motion
            self.current_vignette_alpha = target_alpha
        if previous_alpha != self.current_vignette_alpha or previous_motion != self.current_anchor_boost:
            self.update()
        if settled and not moving:
            self._is_sleeping = True
            self.timer.stop()  # Input signal wakes it; context checks stay low-frequency.

    @property
    def is_sleeping(self):
        return self._is_sleeping

    def paintEvent(self, event):
        cfg = self.cfg_mgr.config
        width, height = self.width(), self.height()
        if width <= 0 or height <= 0:
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Source)
        painter.fillRect(self.rect(), QColor(0, 0, 0, 0))
        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)
        self.paint_layers(painter, width, height, cfg)
        painter.end()
