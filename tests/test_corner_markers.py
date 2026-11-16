"""Corner shapes remain stationary, optional, clipped and independently saved."""
import os
os.environ["QT_QPA_PLATFORM"] = "offscreen"
import tempfile
import unittest
from unittest.mock import patch

from PyQt6.QtGui import QImage, QPainter, QColor
from PyQt6.QtWidgets import QApplication
from core.config import AppConfig, ConfigManager, validated_config
from core.mouse_tracker import MouseSpeedTracker
from ui.overlay_painter import OverlayPainter
from ui.settings_window import SettingsWindow

APP = QApplication.instance() or QApplication([])


def render(config, motion=0, width=800, height=450):
    image = QImage(width, height, QImage.Format.Format_ARGB32)
    image.fill(0)
    renderer = OverlayPainter()
    renderer.current_anchor_boost = motion
    renderer.current_vignette_alpha = .8
    painter = QPainter(image)
    renderer.paint_layers(painter, width, height, config)
    painter.end()
    return image


def alpha_count(image, x, y, size):
    return sum(image.pixelColor(i, j).alpha() > 0 for i in range(x, x + size) for j in range(y, y + size))


class CornerMarkerTests(unittest.TestCase):
    def config(self):
        return AppConfig(vignette_enabled=False, anchors_enabled=False, corner_markers_enabled=True)

    def test_disabled_by_default_and_bad_settings_are_bounded(self):
        cfg = self.config()
        cfg.corner_markers_enabled = False
        image = render(cfg)
        self.assertFalse(any(image.constBits().asstring(image.sizeInBytes())))
        self.assertFalse(AppConfig().corner_markers_enabled)
        validated = validated_config(dict(config_version=4, corner_markers_style="bad", corner_markers_size=-1,
                                          corner_markers_alpha=2, corner_markers_margin=float("nan"),
                                          corner_markers_color="bad", corner_markers_top_left="false"))
        self.assertEqual(validated.corner_markers_style, "square")
        self.assertEqual(validated.corner_markers_size, 6)
        self.assertEqual(validated.corner_markers_alpha, 1)
        self.assertEqual(validated.corner_markers_margin, 20)
        self.assertTrue(validated.corner_markers_top_left)

    def test_four_distinct_shapes_stay_fixed_at_four_corners(self):
        cfg = self.config()
        signatures = []
        for style in ("square", "filled", "diamond", "brackets"):
            cfg.corner_markers_style = style
            image = render(cfg)
            counts = [alpha_count(image, x, y, 24) for x, y in ((20, 20), (756, 20), (20, 406), (756, 406))]
            self.assertTrue(all(count > 0 for count in counts), style)
            self.assertEqual(max(counts), min(counts), style)
            self.assertEqual(image.pixelColor(400, 225).alpha(), 0)
            signatures.append(image.constBits().asstring(image.sizeInBytes()))
            moving = render(cfg, motion=1)
            self.assertEqual(signatures[-1], moving.constBits().asstring(moving.sizeInBytes()))
            self.assertEqual(image.pixelColor(32, 32).alpha() > 0, style == "filled")
        self.assertEqual(len(set(signatures)), 4)

    def test_size_color_opacity_and_small_window_limits(self):
        cfg = self.config()
        cfg.corner_markers_style = "filled"
        cfg.corner_markers_color = "#FF8800"
        cfg.corner_markers_alpha = .25
        cfg.corner_markers_size = 12
        small = render(cfg)
        color = small.pixelColor(24, 24)
        self.assertGreater(color.red(), 250)
        self.assertLess(abs(color.green() - 136), 4)
        self.assertTrue(63 <= color.alpha() <= 65)
        cfg.corner_markers_size = 36
        large = render(cfg)
        self.assertGreater(alpha_count(large, 20, 20, 36), alpha_count(small, 20, 20, 36) * 5)
        cfg.corner_markers_margin = 240
        cfg.corner_markers_size = 120
        tiny = render(cfg, width=40, height=20)
        self.assertEqual(tiny.pixelColor(20, 10).alpha(), 0)
        self.assertGreater(tiny.pixelColor(7, 7).alpha(), 0)
        self.assertGreater(tiny.pixelColor(32, 12).alpha(), 0)

    def test_corner_switches_and_safe_regions_apply_to_new_shapes(self):
        cfg = self.config()
        cfg.corner_markers_style = "filled"
        cfg.corner_markers_top_right = False
        cfg.safe_zones_enabled = True
        cfg.safe_zones = [dict(x=0, y=0, w=.2, h=.2, label="HUD")]
        image = render(cfg)
        self.assertEqual(alpha_count(image, 20, 20, 24), 0)
        self.assertEqual(alpha_count(image, 756, 20, 24), 0)
        self.assertGreater(alpha_count(image, 20, 406, 24), 0)
        self.assertGreater(alpha_count(image, 756, 406, 24), 0)

    def test_thick_diamond_at_zero_margin_does_not_extend_outside_surface(self):
        cfg = self.config()
        cfg.corner_markers_style = "diamond"
        cfg.corner_markers_margin = 0
        cfg.corner_markers_line_width = 8
        image = QImage(820, 470, QImage.Format.Format_ARGB32)
        image.fill(0)
        painter = QPainter(image)
        painter.translate(10, 10)
        OverlayPainter()._paint_corner_markers(painter, 800, 450, cfg)
        painter.end()
        self.assertTrue(all(image.pixelColor(x, y).alpha() == 0 for x in (8, 9, 810, 811) for y in range(470)))
        self.assertTrue(all(image.pixelColor(x, y).alpha() == 0 for y in (8, 9, 460, 461) for x in range(820)))

    def test_ui_parameters_survive_profile_switch_and_restart(self):
        with tempfile.TemporaryDirectory() as tmp:
            manager = ConfigManager(tmp)
            window = SettingsWindow(manager, MouseSpeedTracker())
            try:
                self.assertTrue(window.corner_controls.isHidden())
                window.chk_corner_markers.setChecked(True)
                self.assertFalse(window.corner_controls.isHidden())
                window.cmb_corner_style.setCurrentIndex(window.cmb_corner_style.findData("diamond"))
                window.slider_corner_size.setValue(46)
                window.slider_corner_margin.setValue(30)
                window.slider_corner_alpha.setValue(65)
                window.slider_corner_line_width.setValue(3)
                window.corner_checks["top_right"].setChecked(False)
                with patch("ui.settings_window.QColorDialog.getColor", return_value=QColor("#FF8800")):
                    window._pick_corner_color()
                window._apply_light_preset()
                self.assertFalse(window.chk_corner_markers.isChecked())
                window._apply_preset("balanced")
                self.assertTrue(window.chk_corner_markers.isChecked())
                self.assertEqual(window.slider_corner_size.value(), 46)
                self.assertFalse(window.corner_checks["top_right"].isChecked())
                loaded = ConfigManager(tmp).config
                self.assertEqual(loaded.corner_markers_style, "diamond")
                self.assertEqual(loaded.corner_markers_color, "#ff8800")
                self.assertEqual(loaded.corner_markers_margin, 30)
                self.assertAlmostEqual(loaded.corner_markers_alpha, .65)
            finally:
                window.save_timer.stop()
                window.telemetry_timer.stop()
                window.deleteLater()


if __name__ == "__main__":
    unittest.main()
