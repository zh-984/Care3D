"""Validated settings with atomic per-user persistence and legacy migration."""
import json
import logging
import math
import os
from pathlib import Path
import re
import sys
import tempfile
import copy
from dataclasses import dataclass, asdict, fields, field

log = logging.getLogger(__name__)

@dataclass
class AppConfig:
    config_version: int = 4
    active_profile: str = "balanced"
    profiles: dict = field(default_factory=dict)
    anchors_enabled: bool = True
    anchor_rows: int = 5
    anchor_cols: int = 7
    anchor_radius: float = 3.0
    anchor_color: str = "#B8C8CC"
    anchor_idle_alpha: float = 0.10
    anchor_boost_alpha: float = 0.30
    anchor_margin_ratio: float = 0.04
    anchor_glow: bool = False
    edge_triangles_enabled: bool = False
    edge_triangles_size: int = 16
    edge_triangles_color: str = "#D9E2E5"
    corner_markers_enabled: bool = False
    corner_markers_style: str = "square"
    corner_markers_size: int = 24
    corner_markers_color: str = "#B8C8CC"
    corner_markers_alpha: float = 0.35
    corner_markers_margin: int = 20
    corner_markers_line_width: int = 2
    corner_markers_top_left: bool = True
    corner_markers_top_right: bool = True
    corner_markers_bottom_left: bool = True
    corner_markers_bottom_right: bool = True
    reference_columns_enabled: bool = False
    reference_columns_width: int = 2
    reference_columns_height_ratio: float = 0.60
    reference_columns_color: str = "#B8C8CC"
    reference_columns_alpha: float = 0.25
    vignette_enabled: bool = True
    vignette_max_alpha: float = 0.65
    vignette_idle_alpha: float = 0.12
    vignette_sensitivity: float = 2200.0  # Raw counts/s, not camera degrees/s.
    vignette_threshold: float = 250.0
    vignette_inner_radius: float = 0.55  # Fraction of each ellipse half-axis.
    vignette_contraction: float = 0.12
    vignette_decay_time: float = 0.55
    mouse_gain: float = 1.0
    gamepad_enabled: bool = False
    center_dot_enabled: bool = False
    center_dot_radius: float = 2.0
    center_dot_color: str = "#D9E2E5"
    center_dot_alpha: float = 0.60
    center_dot_style: str = "dot"
    hotkey_toggle: str = "<ctrl>+<alt>+h"
    selected_screen_index: int = 0
    fps_limit: int = 60
    overlay_visible: bool = True
    only_target_window: bool = False
    target_window_title: str = ""
    # Optional extensions. Old configurations render identically with these off.
    game_library_enabled: bool = False
    game_auto_switch_enabled: bool = False
    safe_zones_enabled: bool = False
    safe_zones: list = field(default_factory=list)
    comfort_enabled: bool = False
    comfort_alpha: float = 0.65
    comfort_inner_radius: float = 0.50
    guide_enabled: bool = False
    layout_enabled: bool = False
    layout_sides: list = field(default_factory=lambda: ["top", "bottom", "left", "right"])
    layout_column_positions: list = field(default_factory=lambda: [0.125, 0.375, 0.625, 0.875])
    layout_margin: float = 0.04
    layout_style: str = "none"
    layout_color: str = "#B8C8CC"
    layout_alpha: float = 0.25
    layout_line_width: int = 2
    gamepad_tuning_enabled: bool = False
    gamepad_deadzone: float = 0.22
    gamepad_curve: float = 1.0
    gamepad_stick: str = "right"
    gamepad_device: int = -1
    controls_enabled: bool = False
    controls_toggle_key: str = "<ctrl>+<alt>+h"
    controls_comfort_key: str = "<ctrl>+<alt>+b"
    controls_profile_key: str = "<ctrl>+<alt>+n"
    controls_comfort_hold: bool = False
    controls_gamepad_enabled: bool = False
    accessibility_enabled: bool = False
    font_scale: int = 100
    session_tools_enabled: bool = False
    session_recording_enabled: bool = False
    break_reminder_enabled: bool = False
    break_minutes: int = 30
    game_assistant_enabled: bool = False
    game_assistant_notes: str = ""

BOUNDS = {
    "anchor_rows": (2, 12), "anchor_cols": (2, 16), "anchor_radius": (1, 12),
    "anchor_idle_alpha": (0, 1), "anchor_boost_alpha": (0, 1),
    "anchor_margin_ratio": (0.01, 0.15), "vignette_max_alpha": (0, 0.95),
    "edge_triangles_size": (6, 64),
    "corner_markers_size": (6, 120), "corner_markers_alpha": (0, 1),
    "corner_markers_margin": (0, 240), "corner_markers_line_width": (1, 8),
    "reference_columns_width": (1, 12), "reference_columns_height_ratio": (0.10, 1.0),
    "reference_columns_alpha": (0.05, 0.80),
    "vignette_idle_alpha": (0, 0.40), "vignette_sensitivity": (200, 20000),
    "vignette_threshold": (0, 5000), "vignette_inner_radius": (0.35, 0.85),
    "vignette_contraction": (0, 0.25), "vignette_decay_time": (0.15, 1.5),
    "mouse_gain": (0.25, 4), "center_dot_radius": (1, 8),
    "center_dot_alpha": (0, 1), "selected_screen_index": (0, 32), "fps_limit": (20, 120),
    "comfort_alpha": (0, 0.95), "comfort_inner_radius": (0.20, 0.85),
    "layout_margin": (0.01, 0.15), "layout_alpha": (0.05, 0.80), "layout_line_width": (1, 6),
    "gamepad_deadzone": (0.02, 0.60), "gamepad_curve": (0.40, 3.0), "gamepad_device": (-1, 3),
    "font_scale": (100, 150), "break_minutes": (5, 180),
}

PROFILE_NAMES = {"custom": "我的设置", "balanced": "平衡遮挡", "light": "轻度遮挡", "strong": "加强遮挡"}
PROFILE_KEYS = tuple(f.name for f in fields(AppConfig) if
                     f.name.startswith(("vignette_", "anchor_", "anchors_", "center_dot_", "edge_triangles_", "corner_markers_", "reference_columns_", "safe_", "layout_", "comfort_")) or f.name == "mouse_gain")


def profile_values(config):
    return {key: copy.deepcopy(getattr(config, key)) for key in PROFILE_KEYS}


def valid_rectangles(value):
    """Bounded normalized safe areas; never accept arbitrary executable settings."""
    result = []
    if not isinstance(value, list):
        return result
    for item in value[:16]:
        if not isinstance(item, dict):
            continue
        numbers = [item.get(k) for k in ("x", "y", "w", "h")]
        if any(type(n) not in (int, float) or not math.isfinite(n) for n in numbers):
            continue
        x, y, w, h = numbers
        x, y = max(0.0, min(0.99, x)), max(0.0, min(0.99, y))
        w, h = min(1 - x, max(0.01, w)), min(1 - y, max(0.01, h))
        label = item.get("label", "避让区域")
        result.append(dict(x=x, y=y, w=w, h=h, label=label[:40] if isinstance(label, str) else "避让区域"))
    return result


def default_profile(name):
    values = profile_values(AppConfig())
    if name == "light":
        values.update(vignette_max_alpha=0.45, vignette_idle_alpha=0.08,
                      vignette_sensitivity=2800.0, vignette_threshold=350.0,
                      vignette_inner_radius=0.70, vignette_contraction=0.08,
                      vignette_decay_time=0.45, anchor_idle_alpha=0.08, anchor_boost_alpha=0.20)
    elif name == "strong":
        values.update(vignette_max_alpha=0.78, vignette_idle_alpha=0.22,
                      vignette_sensitivity=1800.0, vignette_threshold=180.0,
                      vignette_inner_radius=0.50, vignette_contraction=0.12,
                      vignette_decay_time=0.65, anchor_idle_alpha=0.12, anchor_boost_alpha=0.35)
    return values


def validated_config(data, include_profiles=True):
    result = AppConfig()
    if not isinstance(data, dict):
        return result
    for field in fields(result):
        name = field.name
        if name in ("profiles", "active_profile", "safe_zones", "layout_sides", "layout_column_positions"):
            continue
        default = getattr(result, name)
        value = data.get(name, default)
        if isinstance(default, bool):
            value = value if type(value) is bool else default
        elif name in BOUNDS:
            if type(value) not in (int, float) or not math.isfinite(value):
                value = default
            value = max(BOUNDS[name][0], min(BOUNDS[name][1], value))
            value = int(value) if isinstance(default, int) else float(value)
        elif isinstance(default, str):
            value = value[:(4000 if name == "game_assistant_notes" else 512)] if isinstance(value, str) else default
            if name.endswith("_color") and not re.fullmatch(r"#[0-9a-fA-F]{6}", value):
                value = default
        setattr(result, name, value)
    result.config_version = 4
    result.safe_zones = valid_rectangles(data.get("safe_zones"))
    sides = data.get("layout_sides", result.layout_sides)
    if isinstance(sides, list):
        result.layout_sides = [side for side in ("top", "bottom", "left", "right") if side in sides]
    positions = data.get("layout_column_positions")
    if isinstance(positions, list) and len(positions) == 4 and all(type(n) in (int, float) and math.isfinite(n) for n in positions):
        result.layout_column_positions = [max(0.015, min(0.985, n)) for n in positions]
    for name, choices in (("layout_style", ("none", "frame", "horizon")), ("gamepad_stick", ("left", "right")),
                          ("corner_markers_style", ("square", "filled", "diamond", "brackets"))):
        if getattr(result, name) not in choices:
            setattr(result, name, getattr(AppConfig(), name))
    result.vignette_sensitivity = max(result.vignette_sensitivity, result.vignette_threshold + 100)
    result.vignette_idle_alpha = min(result.vignette_idle_alpha, result.vignette_max_alpha)
    result.anchor_boost_alpha = max(result.anchor_idle_alpha, result.anchor_boost_alpha)
    if result.center_dot_style not in ("dot", "cross"):
        result.center_dot_style = "dot"
    if data.get("config_version") not in (2, 3, 4):
        result.vignette_inner_radius = 0.55
    if include_profiles:
        # Preserve pre-profile preferences as a distinct, immediately selectable profile.
        requested = data.get("active_profile", "custom")
        result.active_profile = requested if isinstance(requested, str) and requested in PROFILE_NAMES else "custom"
        saved = data.get("profiles", {})
        if isinstance(saved, dict):
            for name, values in saved.items():
                if name in PROFILE_NAMES and isinstance(values, dict):
                    merged = {**default_profile(name), **{k: v for k, v in values.items() if k in PROFILE_KEYS}}
                    sanitized = validated_config({**merged, "config_version": 4}, include_profiles=False)
                    result.profiles[name] = profile_values(sanitized)
        result.profiles[result.active_profile] = profile_values(result)
    return result

class ConfigManager:
    def __init__(self, config_dir=None):
        self._listeners = []
        self._save_hooks = []
        self._reset_hooks = []
        self.config = AppConfig()
        if config_dir is None:
            root = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
            self.config_dir = str(root / "Care3D")
            base = Path(sys.executable).parent if getattr(sys, "frozen", False) else Path(__file__).resolve().parent.parent
            self._legacy_path = base / "config.json"
        else:
            self.config_dir = str(config_dir)
            self._legacy_path = None
        self.config_path = str(Path(self.config_dir) / "config.json")
        self.load()

    def add_listener(self, callback):
        if callback not in self._listeners:
            self._listeners.append(callback)

    def remove_listener(self, callback):
        if callback in self._listeners:
            self._listeners.remove(callback)

    def notify_listeners(self):
        for callback in tuple(self._listeners):
            try:
                callback(self.config)
            except Exception:
                log.exception("配置变更回调失败")

    def load(self):
        path = Path(self.config_path)
        source = path if path.exists() else self._legacy_path
        if source and source.exists():
            try:
                self.config = validated_config(json.loads(source.read_text(encoding="utf-8")))
            except (OSError, ValueError):
                log.exception("无法读取配置，使用默认值；原文件保留")
                return self.config
        if not path.exists():
            self.save()
        return self.config

    def save(self):
        temporary = None
        try:
            self.remember_current_profile()
            Path(self.config_dir).mkdir(parents=True, exist_ok=True)
            path = Path(self.config_path)
            backup = path.with_name("config-before-v4.json")
            if path.exists() and not backup.exists():
                original = path.read_bytes()
                try:
                    original_data = json.loads(original)
                except ValueError:
                    original_data = {}
                version = original_data.get("config_version", 0) if isinstance(original_data, dict) else 0
                if type(version) is not int or version < 4:
                    # One migration backup; never overwrite the user's original backup.
                    with backup.open("xb") as stream:
                        stream.write(original)
            with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=self.config_dir,
                                             prefix="config-", suffix=".tmp", delete=False) as stream:
                temporary = stream.name
                json.dump(asdict(self.config), stream, indent=4, ensure_ascii=False, allow_nan=False)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, self.config_path)
            return all([hook() for hook in tuple(self._save_hooks)])
        except (OSError, ValueError):
            log.exception("无法保存配置")
            return False
        finally:
            if temporary and os.path.exists(temporary):
                os.unlink(temporary)

    def reset_to_defaults(self):
        if not all([hook() for hook in tuple(self._reset_hooks)]):
            return False
        self.config = AppConfig()
        saved = self.save()
        self.notify_listeners()
        return saved

    def remember_current_profile(self):
        self.config.profiles[self.config.active_profile] = profile_values(self.config)

    def switch_profile(self, name):
        if name not in PROFILE_NAMES:
            raise ValueError("Unknown profile")
        self.remember_current_profile()
        values = self.config.profiles.get(name, default_profile(name))
        for key, value in values.items():
            if key in PROFILE_KEYS:
                setattr(self.config, key, copy.deepcopy(value))
        self.config.active_profile = name
        saved = self.save()
        self.notify_listeners()
        return saved

    def reset_current_profile(self):
        for key, value in default_profile(self.config.active_profile).items():
            setattr(self.config, key, copy.deepcopy(value))
        saved = self.save()
        self.notify_listeners()
        return saved
