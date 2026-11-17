"""Render interface states with isolated settings and record layout geometry."""
import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from pathlib import Path
import json
import sys
import tempfile
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from PyQt6.QtGui import QFontDatabase
from PyQt6.QtWidgets import QApplication, QWidget
from core.config import ConfigManager
from core.mouse_tracker import MouseSpeedTracker
from ui.settings_window import SettingsWindow


def main():
    app = QApplication([])
    fonts = Path(os.environ.get("SystemRoot", "C:/Windows")) / "Fonts"
    for name in ("msyh.ttc", "msyhbd.ttc", "segoeui.ttf", "seguiemj.ttf"):
        if (fonts / name).exists():
            QFontDatabase.addApplicationFont(str(fonts / name))
    tag = sys.argv[1] if len(sys.argv) > 1 else "after"
    output = Path("build/theme-review") / tag
    output.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="care3d-theme-") as tmp:
        manager = ConfigManager(tmp)
        tracker = MouseSpeedTracker()
        tracker.input_source = "Raw Input"
        window = SettingsWindow(manager, tracker)
        window.show()
        app.processEvents()
        geometry = {}
        for row in range(window.layout().count()):
            widget = window.layout().itemAt(row).widget()
            rect = widget.geometry()
            geometry[f"band-{row}"] = [rect.x(), rect.y(), rect.width(), rect.height()]
        for name in ("slider_vig_alpha", "badge_vig_alpha", "btn_main_power", "lbl_profile_status", "tabs"):
            widget = getattr(window, name)
            rect = widget.geometry()
            geometry[name] = [rect.x(), rect.y(), rect.width(), rect.height()]
        (output / "geometry.json").write_text(json.dumps(geometry, indent=2), encoding="utf-8")
        window.grab().save(str(output / "main-running.png"))
        manager.config.overlay_visible = False
        window.update_power_button_state(False)
        app.processEvents()
        window.grab().save(str(output / "main-paused.png"))
        manager.config.corner_markers_enabled = True
        window._load_values_to_ui()
        window.tabs.setCurrentIndex(1)
        app.processEvents()
        window.tabs.currentWidget().verticalScrollBar().setValue(window.tabs.currentWidget().verticalScrollBar().maximum())
        app.processEvents()
        window.grab().save(str(output / "anchors.png"))
        window.tabs.setCurrentWidget(window.optional_panel)
        for flag in window.optional_panel.pages:
            setattr(manager.config, flag, True)
        window.optional_panel.load()
        for index in (0, 1, 6, 7, 8):
            window.optional_panel.navigation.setCurrentRow(index)
            app.processEvents()
            window.grab().save(str(output / f"optional-{index}.png"))
        manager.config.accessibility_enabled = True
        manager.config.font_scale = 150
        window._apply_accessibility()
        app.processEvents()
        window.grab().save(str(output / "large-font.png"))
        window.hide()
        window.save_timer.stop()
        window.deleteLater()
    print(json.dumps(geometry))


if __name__ == "__main__":
    main()
