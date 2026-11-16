"""Optional extensions: preserve defaults, isolate contexts and recover safely."""
import os
os.environ["QT_QPA_PLATFORM"] = "offscreen"
import copy
from dataclasses import asdict
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch, MagicMock

from PyQt6.QtCore import Qt, QPoint, QPointF
from PyQt6.QtGui import QImage, QPainter
from PyQt6.QtTest import QTest
from PyQt6.QtWidgets import QApplication
from pynput import keyboard
from core.config import AppConfig, ConfigManager, validated_config
from core.extensions import ExtensionController, recommend_input
from core.hotkey_manager import GlobalHotkeyManager, valid_shortcut
from core.mouse_tracker import MouseSpeedTracker
from core.gamepad import GamepadTracker
from core.preset_library import PresetLibrary
from ui.overlay_painter import OverlayPainter
from ui.overlay_window import MotionSicknessOverlay
from ui.settings_window import SettingsWindow, EditableValueLabel
from ui.extension_widgets import SetupGuide, OverlayPreview

APP = QApplication.instance() or QApplication([])


class ExtensionConfigTests(unittest.TestCase):
    def test_legacy_migration_preserves_values_and_makes_exact_backup(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "config.json"
            before = json.dumps(dict(config_version=3, active_profile="light", vignette_inner_radius=.68,
                                     edge_triangles_enabled=True, reference_columns_width=7)).encode()
            path.write_bytes(before)
            manager = ConfigManager(tmp)
            self.assertFalse(manager.config.safe_zones_enabled)
            self.assertFalse(manager.config.layout_enabled)
            self.assertFalse(manager.config.comfort_enabled)
            self.assertEqual(manager.config.vignette_inner_radius, .68)
            self.assertEqual(manager.config.reference_columns_width, 7)
            self.assertTrue(manager.save())
            self.assertEqual((Path(tmp) / "config-before-v4.json").read_bytes(), before)
            manager.config.vignette_inner_radius = .72
            manager.save()
            self.assertEqual((Path(tmp) / "config-before-v4.json").read_bytes(), before)

    def test_optional_lists_are_validated_and_profiles_do_not_alias(self):
        cfg = validated_config(dict(config_version=4, safe_zones=[dict(x=.8, y=.9, w=2, h=1),
                                                                  dict(x=float('nan'), y=0, w=1, h=1)],
                                    layout_sides=["top", "bad"], layout_column_positions=[float('nan')] * 4))
        self.assertEqual(len(cfg.safe_zones), 1)
        self.assertAlmostEqual(cfg.safe_zones[0]["w"], .2)
        self.assertEqual(cfg.layout_sides, ["top"])
        self.assertEqual(cfg.layout_column_positions, [.125, .375, .625, .875])
        with tempfile.TemporaryDirectory() as tmp:
            manager = ConfigManager(tmp)
            manager.config.safe_zones_enabled = True
            manager.config.safe_zones = [dict(x=0, y=0, w=.2, h=.3, label="HUD")]
            manager.switch_profile("light")
            self.assertFalse(manager.config.safe_zones_enabled)
            self.assertEqual(manager.config.safe_zones, [])
            manager.config.safe_zones.append(dict(x=.5, y=.5, w=.1, h=.1, label="Other"))
            manager.switch_profile("balanced")
            self.assertTrue(manager.config.safe_zones_enabled)
            self.assertEqual(manager.config.safe_zones[0]["label"], "HUD")
            self.assertEqual(len(ConfigManager(tmp).config.safe_zones), 1)

    def test_disabled_extensions_ignore_custom_values_in_rendering(self):
        before = AppConfig()
        after = copy.deepcopy(before)
        after.safe_zones = [dict(x=0, y=0, w=1, h=1, label="All")]
        after.layout_sides = []
        after.layout_style = "horizon"
        after.layout_column_positions = [.1, .2, .3, .4]
        after.comfort_alpha = .95
        def render(cfg):
            cfg.edge_triangles_enabled = cfg.reference_columns_enabled = True
            image = QImage(800, 450, QImage.Format.Format_ARGB32)
            image.fill(0)
            renderer = OverlayPainter()
            renderer.current_vignette_alpha = .6
            renderer.current_anchor_boost = .5
            painter = QPainter(image)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            renderer.paint_layers(painter, 800, 450, cfg)
            painter.end()
            return image.constBits().asstring(image.sizeInBytes())
        self.assertEqual(render(before), render(after))

    def test_overlapping_safe_areas_are_transparent_for_all_layers(self):
        cfg = AppConfig(safe_zones_enabled=True, edge_triangles_enabled=True,
                        reference_columns_enabled=True, center_dot_enabled=True)
        cfg.safe_zones = [dict(x=0, y=0, w=.7, h=.7, label="A"),
                          dict(x=.3, y=.3, w=.7, h=.7, label="B")]
        image = QImage(800, 450, QImage.Format.Format_ARGB32)
        image.fill(0)
        renderer = OverlayPainter()
        renderer.current_vignette_alpha = .8
        painter = QPainter(image)
        renderer.paint_layers(painter, 800, 450, cfg)
        painter.end()
        for point in ((10, 10), (400, 225), (795, 445)):
            self.assertEqual(image.pixelColor(*point).alpha(), 0)
        self.assertGreater(image.pixelColor(795, 5).alpha(), 0)


class LibraryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.manager = ConfigManager(self.tmp.name)
        self.library = PresetLibrary(self.manager)
        self.manager.config.game_library_enabled = True

    def tearDown(self):
        self.tmp.cleanup()

    def test_games_and_base_retain_all_four_profile_slots_after_restart(self):
        cfg = self.manager.config
        cfg.vignette_max_alpha = .71
        ident = self.library.create("Game", "Example")
        self.assertTrue(self.library.activate(ident))
        cfg.vignette_max_alpha = .81
        self.manager.switch_profile("light")
        cfg.vignette_max_alpha = .31
        self.manager.save()
        manager = ConfigManager(self.tmp.name)
        library = PresetLibrary(manager)
        self.assertEqual(library.active_id, ident)
        self.assertEqual(manager.config.vignette_max_alpha, .31)
        manager.switch_profile("balanced")
        self.assertEqual(manager.config.vignette_max_alpha, .81)
        self.assertTrue(library.deactivate())
        self.assertEqual(manager.config.vignette_max_alpha, .71)
        self.assertEqual(manager.config.active_profile, "balanced")
        self.assertTrue(library.activate(ident))
        manager.switch_profile("light")
        self.assertEqual(manager.config.vignette_max_alpha, .31)

    def test_import_export_is_portable_and_invalid_import_is_noop(self):
        self.manager.config.target_window_title = "Private title"
        self.manager.config.game_assistant_notes = "Private notes"
        ident = self.library.create("Portable")
        path = Path(self.tmp.name) / "share.json"
        self.library.export_preset(ident, path)
        text = path.read_text(encoding="utf-8")
        self.assertNotIn("Private", text)
        loaded = self.library.import_preset(path)
        self.assertEqual(self.library.entries[loaded]["match_title"], "")
        before = copy.deepcopy(self.library.entries)
        path.write_text('{"format":"other","settings":{}}', encoding="utf-8")
        with self.assertRaises(ValueError):
            self.library.import_preset(path)
        self.assertEqual(self.library.entries, before)

    def test_failed_save_does_not_switch_or_erase_original_file(self):
        ident = self.library.create("Game")
        before = asdict(self.manager.config)
        file_before = self.library.path.read_bytes()
        with patch("core.preset_library.atomic_json", side_effect=OSError("disk full")), \
             self.assertLogs("core.preset_library", level="ERROR"):
            self.assertFalse(self.library.activate(ident))
        self.assertEqual(self.library.active_id, "")
        self.assertEqual(self.manager.config.vignette_max_alpha, before["vignette_max_alpha"])
        self.assertEqual(self.library.path.read_bytes(), file_before)

    def test_ambiguous_matching_does_not_choose_a_game(self):
        first = self.library.create("A", "Game")
        self.assertEqual(self.library.match("Example GAME window"), first)
        self.library.create("B", "Example")
        self.assertIsNone(self.library.match("Example GAME window"))

    def test_new_game_match_uses_its_own_binding_and_can_be_updated(self):
        self.manager.config.only_target_window = True
        self.manager.config.target_window_title = "Previous game"
        ident = self.library.create("New game", "New game")
        self.library.activate(ident)
        self.assertEqual(self.manager.config.target_window_title, "New game")
        self.assertTrue(self.library.update_match(ident, "Renamed game"))
        self.assertEqual(self.manager.config.target_window_title, "Renamed game")
        self.library.deactivate()
        self.assertEqual(self.manager.config.target_window_title, "Previous game")

    def test_full_reset_keeps_game_entries_without_overwriting_them(self):
        ident = self.library.create("Game")
        self.library.activate(ident)
        self.manager.config.vignette_max_alpha = .88
        self.assertTrue(self.manager.reset_to_defaults())
        self.assertFalse(self.manager.config.game_library_enabled)
        self.assertEqual(self.library.active_id, "")
        self.assertEqual(self.library.entries[ident]["context"]["vignette_max_alpha"], .88)


class RuntimeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.manager = ConfigManager(self.tmp.name)
        self.library = PresetLibrary(self.manager)
        self.tracker = MouseSpeedTracker()
        self.overlay = MotionSicknessOverlay(self.manager, self.tracker)
        self.controller = ExtensionController(self.manager, self.library, self.overlay)

    def tearDown(self):
        self.controller.stop()
        self.overlay.timer.stop()
        self.overlay.context_timer.stop()
        self.overlay.hide()
        self.overlay.deleteLater()
        self.controller.deleteLater()
        self.tmp.cleanup()

    def test_temporary_comfort_does_not_rewrite_configuration_and_pause_wins(self):
        cfg = self.manager.config
        cfg.comfort_enabled = True
        before = asdict(cfg)
        self.overlay.set_comfort_active(True)
        self.assertTrue(self.overlay._comfort_active)
        self.overlay._animation_tick()
        self.assertEqual(asdict(cfg), before)
        self.overlay.set_comfort_active(False)
        self.assertFalse(self.overlay._comfort_active)
        self.overlay.set_comfort_active(True)
        cfg.overlay_visible = False
        self.overlay.on_config_changed(cfg)
        self.assertFalse(self.overlay._comfort_active)

    def test_automatic_game_switch_can_be_disabled_and_restores_base(self):
        cfg = self.manager.config
        cfg.game_library_enabled = True
        ident = self.library.create("A", "Example Game")
        self.library.entries[ident]["context"]["vignette_max_alpha"] = .82
        with patch("core.extensions.foreground_window", return_value=(123, "Example Game")):
            self.controller.tick(100)
            self.assertEqual(self.library.active_id, "")
            cfg.game_auto_switch_enabled = True
            self.controller.tick(102)
        self.assertEqual(self.library.active_id, ident)
        self.assertEqual(cfg.vignette_max_alpha, .82)
        cfg.game_library_enabled = False
        self.manager.notify_listeners()
        self.assertEqual(self.library.active_id, "")
        self.assertEqual(cfg.vignette_max_alpha, .65)

    def test_timer_excludes_paused_overlay_and_writes_only_when_opted_in(self):
        cfg = self.manager.config
        cfg.session_tools_enabled = True
        self.controller.start_session()
        self.controller._last_tick = 100
        self.controller.tick(102)
        self.assertEqual(self.controller.session_elapsed, 2)
        cfg.overlay_visible = False
        self.controller.tick(104)
        self.assertEqual(self.controller.session_elapsed, 2)
        self.assertFalse(self.controller.records_path.exists())
        with self.assertRaises(ValueError):
            self.controller.record_session("没变化")
        cfg.session_recording_enabled = True
        self.controller.record_session("舒服些", "User note")
        rows = self.controller.records()
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["seconds"], 2)
        self.assertNotIn("target_window_title", rows[0])

    def test_calibration_can_sample_while_overlay_input_is_disabled(self):
        self.tracker._is_running = True
        self.tracker.set_enabled(False)
        self.tracker.begin_calibration()
        self.tracker.add_delta(30, 40)
        self.assertGreater(self.tracker.calibration_sample(), 0)
        self.assertEqual(self.tracker._accumulated_dist, 0)
        self.tracker.end_calibration()
        self.assertFalse(self.tracker._calibrating)
        recommendation = recommend_input([0, 1000, 1100, 1200, 900, 1300, 1400])
        self.assertGreater(recommendation["vignette_sensitivity"], recommendation["vignette_threshold"] + 99)

    def test_gamepad_curve_and_selected_stick_are_optional(self):
        cfg = self.manager.config
        gamepad = GamepadTracker()
        def read(index, pointer):
            state = pointer._obj
            state.gamepad.left_x, state.gamepad.right_x = 32767, 0
            return 0
        gamepad._read = read
        cfg.gamepad_stick = "left"
        self.assertEqual(gamepad.poll(cfg), 0)
        cfg.gamepad_tuning_enabled = True
        self.assertEqual(gamepad.poll(cfg), 1)
        self.assertLess(GamepadTracker.strength(16000, 0, .22, 2), GamepadTracker.strength(16000, 0))


class OptionalUiTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.manager = ConfigManager(self.tmp.name)
        self.tracker = MouseSpeedTracker()
        self.window = SettingsWindow(self.manager, self.tracker)
        self.panel = self.window.optional_panel

    def tearDown(self):
        self.window.save_timer.stop()
        self.window.telemetry_timer.stop()
        self.window.deleteLater()
        self.tmp.cleanup()

    def test_all_optional_pages_start_disabled_and_enable_independently(self):
        for flag, body in self.panel.pages.items():
            self.assertFalse(getattr(self.manager.config, flag))
            self.assertFalse(body.isEnabled())
        self.panel.fields["safe_zones_enabled"][0].setChecked(True)
        self.assertTrue(self.panel.pages["safe_zones_enabled"].isEnabled())
        self.assertFalse(self.manager.config.layout_enabled)
        self.panel.add_area(dict(x=.1, y=.8, w=.8, h=.15, label="字幕"))
        self.assertTrue(self.window._save_config())
        self.assertEqual(ConfigManager(self.tmp.name).config.safe_zones[0]["label"], "字幕")

    def test_setup_guide_cancel_is_noop_and_cleans_calibration(self):
        before = asdict(self.manager.config)
        dialog = SetupGuide(self.manager.config, self.tracker)
        dialog.choice.setCurrentIndex(1)
        self.assertNotEqual(dialog.result_values["settings"]["vignette_max_alpha"], before["vignette_max_alpha"])
        self.tracker.begin_calibration()
        dialog.reject()
        self.assertFalse(self.tracker._calibrating)
        self.assertEqual(asdict(self.manager.config), before)
        dialog.deleteLater()

    def test_font_scaling_reverts_and_numeric_badge_edit_updates_slider(self):
        self.manager.config.accessibility_enabled = True
        self.manager.config.font_scale = 150
        badge = self.window.badge_vig_alpha
        original_width = badge.width()
        self.window._apply_accessibility()
        self.assertEqual(badge.width(), round(original_width * 1.5))
        self.window.update_power_button_state(False)
        self.assertIn("font-size: 18px", self.window.btn_main_power.styleSheet())
        with patch("ui.settings_window.QInputDialog.getInt", return_value=(73, True)):
            badge.editor()
        self.assertEqual(self.window.slider_vig_alpha.value(), 73)
        self.manager.config.accessibility_enabled = False
        self.window._apply_accessibility()
        self.assertEqual(badge.width(), original_width)
        self.assertIn("font-size: 12px", self.window.btn_main_power.styleSheet())

    def test_safe_area_drag_creates_normalized_rectangle(self):
        preview = self.panel.safe_preview
        self.panel.fields["safe_zones_enabled"][0].setChecked(True)
        preview.resize(400, 240)
        QTest.mousePress(preview, Qt.MouseButton.LeftButton, pos=QPoint(40, 150))
        QTest.mouseMove(preview, QPoint(320, 220))
        QTest.mouseRelease(preview, Qt.MouseButton.LeftButton, pos=QPoint(320, 220))
        areas = self.manager.config.safe_zones
        self.assertEqual(len(areas), 1)
        self.assertAlmostEqual(areas[0]["x"], .1)
        self.assertAlmostEqual(areas[0]["w"], .7)


class ShortcutTests(unittest.TestCase):
    def test_shortcuts_require_modifier_and_reject_duplicates(self):
        self.assertTrue(valid_shortcut("<ctrl>+<alt>+b"))
        self.assertTrue(valid_shortcut("<alt>+<f8>"))
        self.assertFalse(valid_shortcut("b"))
        self.assertFalse(valid_shortcut("<ctrl>+<ctrl>+b"))

    def test_hold_release_restores_without_changing_toggle_callbacks(self):
        captures = {}
        listener = MagicMock()
        listener.canonical.side_effect = lambda key: key
        def make_listener(**kwargs):
            captures.update(kwargs)
            return listener
        states = []
        manager = GlobalHotkeyManager()
        with patch("core.hotkey_manager.keyboard.GlobalHotKeys"), \
             patch("core.hotkey_manager.keyboard.Listener", side_effect=make_listener):
            manager.configure("<ctrl>+<alt>+h", {}, "<ctrl>+<alt>+b", states.append)
            for key in keyboard.HotKey.parse("<ctrl>+<alt>+b"):
                captures["on_press"](key)
            self.assertEqual(states, [True])
            captures["on_release"](keyboard.Key.alt)
            self.assertEqual(states, [True, False])
            manager.stop()


if __name__ == "__main__":
    unittest.main()
