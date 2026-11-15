"""Run with: python -m unittest discover -s tests -v (no game required)."""
import os
os.environ["QT_QPA_PLATFORM"] = "offscreen"

import ctypes
from ctypes import wintypes
from dataclasses import asdict
import json
import io
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from PyQt6.QtCore import QRect
from PyQt6.QtGui import QImage, QPainter, QColor
from PyQt6.QtWidgets import QApplication
from core.config import AppConfig, ConfigManager, validated_config
from core.gamepad import GamepadTracker
from core.hotkey_manager import GlobalHotkeyManager
from core.mouse_tracker import MouseSpeedTracker
from core.raw_input import RAWINPUTHEADER, RAWMOUSE, RawMouseInput
from ui.overlay_window import MotionSicknessOverlay
from ui.settings_window import SettingsWindow

APP = QApplication.instance() or QApplication([])


class HotkeyTests(unittest.TestCase):
    def test_hotkey_start_works_with_ascii_output_stream(self):
        # A non-Chinese Windows redirected stream cannot encode Chinese text.
        # Status reporting must not interrupt successful hook registration.
        manager = GlobalHotkeyManager()
        with io.TextIOWrapper(io.BytesIO(), encoding="ascii") as output, \
             patch("sys.stdout", output), \
             patch("core.hotkey_manager.keyboard.GlobalHotKeys") as listener:
            try:
                manager.start()
                self.assertTrue(manager._is_running)
                listener.return_value.start.assert_called_once()
            finally:
                manager.stop()
            listener.return_value.stop.assert_called_once()


class ConfigTests(unittest.TestCase):
    def test_validation_and_cross_field_constraints(self):
        cfg = validated_config(dict(config_version=2, vignette_max_alpha=0.1,
            vignette_idle_alpha=0.4, vignette_threshold=4900, vignette_sensitivity=200,
            fps_limit=float("nan"), anchor_color="invalid", anchors_enabled="false",
            anchor_rows=10**8, center_dot_style="bad", unknown=1))
        self.assertEqual(cfg.vignette_idle_alpha, 0.1)
        self.assertEqual(cfg.vignette_sensitivity, 5000)
        self.assertEqual(cfg.fps_limit, 60)
        self.assertEqual(cfg.anchor_color, AppConfig().anchor_color)
        self.assertIs(cfg.anchors_enabled, True)
        self.assertEqual(cfg.anchor_rows, 12)
        self.assertEqual(cfg.center_dot_style, "dot")

    def test_atomic_save_and_per_user_path(self):
        with tempfile.TemporaryDirectory() as tmp, patch.dict(os.environ, LOCALAPPDATA=tmp):
            cfg = ConfigManager()
            self.assertEqual(Path(cfg.config_path).parent, Path(tmp) / "Care3D")
            cfg.config.vignette_max_alpha = 0.77
            self.assertTrue(cfg.save())
            self.assertEqual(ConfigManager().config.vignette_max_alpha, 0.77)
            self.assertFalse(list(Path(cfg.config_dir).glob("*.tmp")))
            before = Path(cfg.config_path).read_bytes()
            with patch("core.config.os.replace", side_effect=OSError("disk failure")):
                with self.assertLogs("core.config", level="ERROR"):
                    self.assertFalse(cfg.save())
            self.assertEqual(Path(cfg.config_path).read_bytes(), before)

    def test_legacy_preferences_are_kept_as_my_settings(self):
        with tempfile.TemporaryDirectory() as tmp:
            original = dict(config_version=2, vignette_max_alpha=0.73,
                            vignette_inner_radius=0.67, center_dot_enabled=True)
            Path(tmp, "config.json").write_text(json.dumps(original), encoding="utf-8")
            manager = ConfigManager(tmp)
            self.assertEqual(manager.config.active_profile, "custom")
            manager.switch_profile("light")
            self.assertEqual(manager.config.vignette_max_alpha, 0.45)
            manager.switch_profile("custom")
            self.assertEqual(manager.config.vignette_max_alpha, 0.73)
            self.assertEqual(manager.config.vignette_inner_radius, 0.67)
            self.assertTrue(manager.config.center_dot_enabled)

    def test_independent_profiles_survive_switches_and_restart(self):
        with tempfile.TemporaryDirectory() as tmp:
            manager = ConfigManager(tmp)
            manager.switch_profile("custom")
            manager.config.vignette_max_alpha = 0.73
            manager.config.center_dot_color = "#123456"
            manager.config.mouse_gain = 1.7
            manager.switch_profile("light")
            manager.config.vignette_max_alpha = 0.32
            manager.config.mouse_gain = 0.55
            manager.switch_profile("strong")
            manager.config.vignette_max_alpha = 0.88
            manager.switch_profile("light")
            reloaded = ConfigManager(tmp)
            self.assertEqual(reloaded.config.active_profile, "light")
            self.assertEqual(reloaded.config.vignette_max_alpha, 0.32)
            self.assertEqual(reloaded.config.mouse_gain, 0.55)
            reloaded.switch_profile("custom")
            self.assertEqual(reloaded.config.vignette_max_alpha, 0.73)
            self.assertEqual(reloaded.config.center_dot_color, "#123456")
            self.assertEqual(reloaded.config.mouse_gain, 1.7)
            reloaded.switch_profile("strong")
            self.assertEqual(reloaded.config.vignette_max_alpha, 0.88)

    def test_reset_only_affects_the_current_profile(self):
        with tempfile.TemporaryDirectory() as tmp:
            manager = ConfigManager(tmp)
            manager.config.vignette_max_alpha = 0.71
            manager.switch_profile("light")
            manager.config.vignette_max_alpha = 0.29
            manager.switch_profile("strong")
            manager.config.vignette_max_alpha = 0.81
            manager.switch_profile("light")
            manager.reset_current_profile()
            self.assertEqual(manager.config.vignette_max_alpha, 0.45)
            manager.switch_profile("strong")
            self.assertEqual(manager.config.vignette_max_alpha, 0.81)
            manager.switch_profile("balanced")
            self.assertEqual(manager.config.vignette_max_alpha, 0.71)


class SettingsTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.manager = ConfigManager(self.tmp.name)
        self.manager.config.active_profile = "custom"
        self.manager.config.vignette_max_alpha = 0.82
        self.manager.config.vignette_sensitivity = 1800
        self.manager.config.center_dot_style = "cross"
        self.before = asdict(self.manager.config)
        self.window = SettingsWindow(self.manager, MouseSpeedTracker())

    def tearDown(self):
        self.window.save_timer.stop()
        self.window.telemetry_timer.stop()
        self.window.deleteLater()
        self.tmp.cleanup()

    def test_loading_never_writes_back_partial_controls(self):
        self.assertEqual(asdict(self.manager.config), self.before)
        self.manager.config.anchors_enabled = True
        self.manager.config.center_dot_enabled = True
        self.window._load_values_to_ui()
        self.assertTrue(self.manager.config.anchors_enabled)
        self.assertTrue(self.manager.config.center_dot_enabled)

    def test_all_presets_apply_and_preserve_system_settings(self):
        self.manager.config.fps_limit = 90
        self.manager.config.overlay_visible = False
        self.manager.config.target_window_title = "Example Game"
        for apply, peak, sensitivity, inner, idle in [
            (self.window._apply_light_preset, 0.45, 2800, 0.70, 0.08),
            (self.window._apply_heavy_preset, 0.78, 1800, 0.50, 0.22),
            (self.window._apply_pubg_preset, 0.65, 2200, 0.55, 0.12),
        ]:
            apply()
            cfg = self.manager.config
            self.assertEqual((cfg.vignette_max_alpha, cfg.vignette_sensitivity,
                              cfg.vignette_inner_radius, cfg.vignette_idle_alpha),
                             (peak, sensitivity, inner, idle))
            self.assertEqual(cfg.fps_limit, 90)
            self.assertFalse(cfg.overlay_visible)
            self.assertEqual(cfg.target_window_title, "Example Game")
            self.assertFalse(cfg.center_dot_enabled)

    def test_pending_slider_edit_survives_immediate_switch(self):
        self.window.slider_vig_alpha.setValue(73)
        self.assertTrue(self.window.save_timer.isActive())
        self.window._apply_light_preset()
        self.window.slider_vig_alpha.setValue(29)
        self.window._apply_heavy_preset()
        self.window._apply_preset("custom")
        self.assertEqual(self.window.slider_vig_alpha.value(), 73)
        self.window._apply_light_preset()
        self.assertEqual(self.window.slider_vig_alpha.value(), 29)
        self.assertEqual(ConfigManager(self.tmp.name).config.vignette_max_alpha, 0.29)

    def test_clicking_selected_profile_does_not_reset_it(self):
        self.window._apply_light_preset()
        self.window.slider_vig_alpha.setValue(38)
        self.window._apply_light_preset()
        self.assertEqual(self.window.slider_vig_alpha.value(), 38)
        self.assertEqual(self.manager.config.vignette_max_alpha, 0.38)
        self.assertIn("已保存", self.window.lbl_profile_status.text())

    def test_edge_triangles_are_independent_and_persist_with_profile(self):
        self.assertFalse(self.window.chk_edge_triangles.isChecked())
        self.window.chk_anchors.setChecked(False)
        self.window.chk_edge_triangles.setChecked(True)
        self.window.slider_edge_triangles_size.setValue(32)
        with patch("ui.settings_window.QColorDialog.getColor", return_value=QColor("#FF8800")):
            self.window._pick_edge_triangles_color()
        self.window._apply_light_preset()
        self.assertFalse(self.window.chk_edge_triangles.isChecked())
        self.assertEqual(self.window.slider_edge_triangles_size.value(), 16)
        self.window._apply_preset("custom")
        self.assertTrue(self.window.chk_edge_triangles.isChecked())
        self.assertEqual(self.window.slider_edge_triangles_size.value(), 32)
        self.assertIn("#ff8800", self.window.edge_triangles_color_preview.styleSheet())
        self.assertFalse(self.window.chk_anchors.isChecked())
        reloaded = ConfigManager(self.tmp.name)
        self.assertTrue(reloaded.config.edge_triangles_enabled)
        self.assertEqual(reloaded.config.edge_triangles_size, 32)
        self.assertEqual(reloaded.config.edge_triangles_color, "#ff8800")
        self.assertFalse(reloaded.config.anchors_enabled)
        self.assertEqual(reloaded.config.vignette_max_alpha, 0.82)

    def test_cancel_triangle_color_picker_preserves_parameters(self):
        before = asdict(self.manager.config)
        with patch("ui.settings_window.QColorDialog.getColor", return_value=QColor()):
            self.window._pick_edge_triangles_color()
        self.assertEqual(asdict(self.manager.config), before)

    def test_reference_columns_save_independently_with_each_profile(self):
        self.assertFalse(self.window.chk_reference_columns.isChecked())
        self.window.chk_reference_columns.setChecked(True)
        self.window.slider_reference_columns_width.setValue(3)
        self.window.slider_reference_columns_height.setValue(75)
        self.window.slider_reference_columns_alpha.setValue(35)
        with patch("ui.settings_window.QColorDialog.getColor", return_value=QColor("#7799AA")):
            self.window._pick_reference_columns_color()
        self.window._apply_light_preset()
        self.assertFalse(self.window.chk_reference_columns.isChecked())
        self.assertEqual(self.window.slider_reference_columns_width.value(), 2)
        self.window._apply_preset("custom")
        self.assertTrue(self.window.chk_reference_columns.isChecked())
        self.assertEqual(self.window.slider_reference_columns_width.value(), 3)
        self.assertEqual(self.window.slider_reference_columns_height.value(), 75)
        reloaded = ConfigManager(self.tmp.name).config
        self.assertEqual(reloaded.reference_columns_color, "#7799aa")
        self.assertEqual(reloaded.reference_columns_alpha, 0.35)
        self.assertEqual(reloaded.reference_columns_height_ratio, 0.75)
        self.assertTrue(reloaded.reference_columns_enabled)
        self.assertEqual(reloaded.vignette_max_alpha, 0.82)


class InputTests(unittest.TestCase):
    def test_native_mouse_message_reaches_delta_callback(self):
        seen = []
        raw = RawMouseInput(lambda x, y: seen.append((x, y)))
        raw.hwnd = 123
        header = RAWINPUTHEADER(0, ctypes.sizeof(RAWINPUTHEADER) + 24, None, 0)
        mouse = RAWMOUSE()
        mouse.lLastX, mouse.lLastY = 30, -7
        packet = bytes(header) + bytes(mouse)
        def read(handle, command, buffer, size, header_size):
            ctypes.memmove(buffer, packet, len(packet))
            return len(packet)
        raw.read = read
        message = wintypes.MSG()
        message.message = 0xFF
        message.hWnd = 123
        self.assertEqual(raw.nativeEventFilter(b"windows_generic_MSG", ctypes.addressof(message)), (False, 0))
        self.assertEqual(seen, [(30, -7)])
        self.assertFalse(raw._failed)
        message.hWnd = 456
        raw.nativeEventFilter(b"windows_generic_MSG", ctypes.addressof(message))
        self.assertEqual(len(seen), 1)

    def test_native_callback_failure_does_not_terminate_ui(self):
        errors = []
        raw = RawMouseInput(lambda x, y: None, lambda: errors.append(True))
        raw.hwnd = 123
        raw.read = lambda *args: (_ for _ in ()).throw(RuntimeError("input failure"))
        message = wintypes.MSG()
        message.hWnd, message.message = 123, 0xFF
        with self.assertLogs("core.raw_input", level="ERROR"):
            self.assertEqual(raw.nativeEventFilter(None, ctypes.addressof(message)), (False, 0))
        self.assertEqual(errors, [True])
        self.assertTrue(raw._failed)
        self.assertEqual(raw.nativeEventFilter(None, ctypes.addressof(message)), (False, 0))
        self.assertEqual(errors, [True])

    def test_raw_packet_relative_only_and_64bit_layout(self):
        self.assertEqual(ctypes.sizeof(RAWMOUSE), 24)
        self.assertEqual(ctypes.sizeof(RAWINPUTHEADER), 8 + 2 * ctypes.sizeof(ctypes.c_void_p))
        seen = []
        raw = RawMouseInput(lambda x, y: seen.append((x, y)))
        header = RAWINPUTHEADER(0, ctypes.sizeof(RAWINPUTHEADER) + 24, None, 0)
        mouse = RAWMOUSE()
        mouse.lLastX, mouse.lLastY = -10, 4
        raw.process_packet(bytes(header) + bytes(mouse))
        mouse.usFlags = 1
        raw.process_packet(bytes(header) + bytes(mouse))
        raw.process_packet(b"short")
        self.assertEqual(seen, [(-10, 4)])

    def test_idle_wakeup_is_coalesced_and_pause_discards_input(self):
        tracker = MouseSpeedTracker()
        tracker._is_running = True
        wakes = []
        tracker.motion_detected.connect(lambda: wakes.append(1))
        for _ in range(100):
            tracker.add_delta(3, 4)
        self.assertEqual(len(wakes), 1)
        self.assertEqual(tracker._accumulated_dist, 500)
        tracker.poll_speed()
        tracker.add_delta(1, 0)
        self.assertEqual(len(wakes), 2)
        tracker.set_enabled(False)
        tracker.add_delta(1000, 0)
        self.assertEqual(tracker._accumulated_dist, 0)

    def test_gamepad_deadzone_and_normalization(self):
        self.assertEqual(GamepadTracker.strength(1000, 1000), 0)
        self.assertEqual(GamepadTracker.strength(32767, 32767), 1)


class OverlayTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.manager = ConfigManager(self.tmp.name)
        self.tracker = MouseSpeedTracker()
        self.overlay = MotionSicknessOverlay(self.manager, self.tracker)

    def tearDown(self):
        self.overlay.timer.stop()
        self.overlay.context_timer.stop()
        self.overlay.hide()
        self.overlay.deleteLater()
        self.tmp.cleanup()

    def mask(self, motion=0):
        self.overlay.current_anchor_boost = motion
        self.overlay.current_vignette_alpha = 0.65
        image = QImage(1920, 1080, QImage.Format.Format_ARGB32)
        image.fill(0)
        painter = QPainter(image)
        self.overlay._paint_vignette(painter, 1920, 1080, self.manager.config)
        painter.end()
        return image

    def test_edge_triangles_render_on_four_sides_and_stay_static(self):
        cfg = self.manager.config
        cfg.vignette_enabled = cfg.anchors_enabled = cfg.center_dot_enabled = False
        self.overlay.resize(800, 450)
        def render():
            image = QImage(800, 450, QImage.Format.Format_ARGB32)
            image.fill(0)
            self.overlay.render(image)
            return image
        disabled = render()
        points = [(400, 13), (400, 437), (13, 225), (787, 225)]
        self.assertTrue(all(disabled.pixelColor(x, y).alpha() == 0 for x, y in points))
        cfg.edge_triangles_enabled = True
        resting = render()
        self.assertTrue(all(resting.pixelColor(x, y).alpha() > 100 for x, y in points))
        self.assertEqual(resting.pixelColor(400, 225).alpha(), 0)
        self.overlay.current_anchor_boost = 1.0
        self.overlay.current_vignette_alpha = 0.95
        moving = render()
        self.assertEqual(bytes(resting.constBits().asstring(resting.sizeInBytes())),
                         bytes(moving.constBits().asstring(moving.sizeInBytes())))

    def test_triangle_size_and_color_change_the_rendered_shape(self):
        cfg = self.manager.config
        cfg.vignette_enabled = cfg.anchors_enabled = cfg.center_dot_enabled = False
        cfg.edge_triangles_enabled = True
        cfg.edge_triangles_color = "#FF8800"
        self.overlay.resize(800, 450)
        counts = []
        for size in (8, 32):
            cfg.edge_triangles_size = size
            image = QImage(800, 450, QImage.Format.Format_ARGB32)
            image.fill(0)
            self.overlay.render(image)
            counts.append(sum(a > 0 for a in image.constBits().asstring(image.sizeInBytes())[3::4]))
            # Sample the centroid, clear of the black antialiased outline at small sizes.
            color = image.pixelColor(400, 8 + round(size / (2 * 3 ** 0.5)))
            self.assertGreater(color.red(), 240)
            self.assertLess(abs(color.green() - 136), 5)
            self.assertLess(color.blue(), 5)
        self.assertGreater(counts[1], counts[0] * 5)

    def test_four_columns_are_evenly_spaced_thin_and_static(self):
        cfg = self.manager.config
        cfg.vignette_enabled = cfg.anchors_enabled = cfg.center_dot_enabled = False
        cfg.edge_triangles_enabled = False
        cfg.reference_columns_color = "#FF0000"
        def render(width, height):
            self.overlay.resize(width, height)
            image = QImage(width, height, QImage.Format.Format_ARGB32)
            image.fill(0)
            self.overlay.render(image)
            return image
        disabled = render(800, 450)
        self.assertEqual(disabled.pixelColor(100, 225).alpha(), 0)
        cfg.reference_columns_enabled = True
        for width, height in ((800, 450), (1600, 900)):
            image = render(width, height)
            for numerator in (1, 3, 5, 7):
                x, y = width * numerator // 8, height // 2
                color = image.pixelColor(x, y)
                self.assertEqual(color.red(), 255)
                self.assertEqual(color.green(), 0)
                self.assertGreater(color.alpha(), 0)
                self.assertLess(color.alpha(), 100)
                self.assertEqual(image.pixelColor(x + 5, y).alpha(), 0)
                self.assertEqual(image.pixelColor(x, height // 10).alpha(), 0)
            self.assertEqual(image.pixelColor(width // 2, height // 2).alpha(), 0)
            self.overlay.current_anchor_boost = 1
            self.overlay.current_vignette_alpha = 0.95
            moving = render(width, height)
            self.assertEqual(image.constBits().asstring(image.sizeInBytes()),
                             moving.constBits().asstring(moving.sizeInBytes()))
        cfg.reference_columns_width = 6
        thicker = render(800, 450)
        self.assertGreater(thicker.pixelColor(102, 225).alpha(), 0)

    def test_mask_covers_four_edges_and_contracts_clear_area(self):
        resting, moving = self.mask(), self.mask(1)
        alphas = [resting.pixelColor(x, y).alphaF() for x, y in
                  [(0, 540), (1919, 540), (960, 0), (960, 1079)]]
        self.assertLess(max(alphas) - min(alphas), 0.02)
        self.assertTrue(all(a > 0.60 for a in alphas))
        self.assertEqual(resting.pixelColor(960, 540).alpha(), 0)
        self.assertEqual(resting.pixelColor(1440, 540).alpha(), 0)
        self.assertGreater(moving.pixelColor(1440, 540).alpha(), 0)

    def test_animation_settles_at_baseline_stops_timer_and_wakes(self):
        self.overlay.on_config_changed(self.manager.config)
        self.overlay.current_vignette_alpha = 0.65
        start = self.overlay._last_tick
        with patch("ui.overlay_window.time.perf_counter") as clock:
            for tick in range(1, 180):
                clock.return_value = start + tick / 60
                self.overlay._animation_tick()
        self.assertAlmostEqual(self.overlay.current_vignette_alpha, 0.12)
        self.assertTrue(self.overlay.is_sleeping)
        self.assertFalse(self.overlay.timer.isActive())
        self.overlay._wake_animation()
        self.assertTrue(self.overlay.timer.isActive())

    def test_binding_hides_when_unfocused_and_master_pause_wins(self):
        cfg = self.manager.config
        cfg.only_target_window = True
        cfg.target_window_title = "Example Game"
        with patch("ui.overlay_window.foreground_window", return_value=(123, "Example Game")), \
             patch("ui.overlay_window.client_geometry", return_value=QRect(20, 30, 800, 600)):
            self.overlay.on_config_changed(cfg)
            self.assertTrue(self.overlay.isVisible())
            self.assertEqual(self.overlay.geometry(), QRect(20, 30, 800, 600))
            cfg.overlay_visible = False
            self.overlay.on_config_changed(cfg)
            self.assertFalse(self.overlay.isVisible())
            self.assertFalse(self.overlay.context_timer.isActive())
        cfg.overlay_visible = True
        with patch("ui.overlay_window.foreground_window", return_value=(456, "Desktop")):
            self.overlay.on_config_changed(cfg)
            self.assertFalse(self.overlay.isVisible())
            self.assertTrue(self.overlay.context_timer.isActive())
            self.assertFalse(self.tracker._enabled)

    def test_animation_response_does_not_depend_on_frame_rate(self):
        results = []
        self.tracker.poll_speed = lambda *_: (2200, True)
        for fps in (30, 60, 120):
            self.overlay.current_vignette_alpha = 0.12
            self.overlay.current_anchor_boost = 0
            self.overlay._last_tick = 100
            self.overlay.show()
            self.overlay.current_vignette_alpha = 0.12
            self.overlay._last_tick = 100
            with patch("ui.overlay_window.time.perf_counter") as clock:
                for tick in range(1, round(fps * 0.2) + 1):
                    clock.return_value = 100 + tick / fps
                    self.overlay._animation_tick()
            results.append(self.overlay.current_vignette_alpha)
        self.assertLess(max(results) - min(results), 0.001)


if __name__ == "__main__":
    unittest.main()
