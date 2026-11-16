"""Render opt-in settings pages with synthetic data, without capturing a desktop."""
import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from pathlib import Path
import sys
import tempfile
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from PyQt6.QtGui import QFontDatabase
from PyQt6.QtWidgets import QApplication
from core.config import ConfigManager
from core.mouse_tracker import MouseSpeedTracker
from core.preset_library import PresetLibrary
from core.extensions import ExtensionController
from ui.overlay_window import MotionSicknessOverlay
from ui.settings_window import SettingsWindow


def main():
    app = QApplication([])
    fonts = Path(os.environ.get("SystemRoot", "C:/Windows")) / "Fonts"
    for name in ("msyh.ttc", "msyhbd.ttc", "segoeui.ttf", "seguiemj.ttf"):
        if (fonts / name).exists():
            QFontDatabase.addApplicationFont(str(fonts / name))
    output = Path("build/optional-ui-check")
    output.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="care3d-options-preview-") as tmp:
        manager = ConfigManager(tmp)
        tracker = MouseSpeedTracker()
        tracker.input_source = "文档预览"
        library = PresetLibrary(manager)
        overlay = MotionSicknessOverlay(manager, tracker)
        controller = ExtensionController(manager, library, overlay)
        settings = SettingsWindow(manager, tracker, overlay, library, controller)
        settings.show()
        settings.tabs.setCurrentWidget(settings.optional_panel)
        for flag in settings.optional_panel.pages:
            setattr(manager.config, flag, True)
        manager.config.edge_triangles_enabled = manager.config.reference_columns_enabled = True
        manager.config.safe_zones = [dict(x=.16, y=.78, w=.68, h=.18, label="字幕避让区")]
        ident = library.create("演示游戏", "Example Game")
        settings.optional_panel.load()
        for index in range(settings.optional_panel.navigation.count()):
            settings.optional_panel.navigation.setCurrentRow(index)
            app.processEvents()
            if not settings.grab().save(str(output / f"page-{index + 1}.png")):
                raise RuntimeError("Cannot render preview")
        manager.config.font_scale = 150
        settings._apply_accessibility()
        settings.optional_panel.navigation.setCurrentRow(6)
        app.processEvents()
        settings.grab().save(str(output / "font-150.png"))
        settings.hide()
        settings.save_timer.stop()
        controller.stop()
        overlay.timer.stop()
        overlay.context_timer.stop()
        settings.deleteLater()
        overlay.deleteLater()
    print("Optional pages rendered in build/optional-ui-check")


if __name__ == "__main__":
    main()
