"""Regenerate README images without capturing a real desktop or game window.

Run from the repository root: python tools/render_readme_images.py
"""

import os
from pathlib import Path
import sys
import tempfile

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from PyQt6.QtCore import QPointF, QRectF, Qt
from PyQt6.QtGui import QColor, QFont, QFontDatabase, QImage, QLinearGradient, QPainter, QPen
from PyQt6.QtWidgets import QApplication

from core.config import ConfigManager
from core.mouse_tracker import MouseSpeedTracker
from ui.overlay_window import MotionSicknessOverlay
from ui.settings_window import SettingsWindow


def main():
    app = QApplication([])
    font_dir = Path(os.environ.get("SystemRoot", "C:/Windows")) / "Fonts"
    for name in ("msyh.ttc", "msyhbd.ttc", "segoeui.ttf", "seguiemj.ttf"):
        path = font_dir / name
        if path.exists():
            QFontDatabase.addApplicationFont(str(path))
    output = ROOT / "docs" / "images"
    output.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(prefix="care3d-docs-") as temporary:
        manager = ConfigManager(temporary)
        tracker = MouseSpeedTracker()  # No mouse hook or Raw Input registration.
        tracker.input_source = "预览"
        settings = SettingsWindow(manager, tracker)
        settings.resize(800, 740)
        settings.show()
        app.processEvents()
        if not settings.grab().save(str(output / "settings.png")):
            raise RuntimeError("Could not write settings image")
        settings.hide()
        settings.save_timer.stop()

        width, height = 1280, 720
        scene = QImage(width, height, QImage.Format.Format_ARGB32_Premultiplied)
        painter = QPainter(scene)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        background = QLinearGradient(0, 0, width, height)
        background.setColorAt(0, QColor("#172536"))
        background.setColorAt(1, QColor("#0A111D"))
        painter.fillRect(scene.rect(), background)
        painter.setPen(QPen(QColor("#263A4D"), 1))
        for x in range(0, width, 80):
            painter.drawLine(x, 0, x, height)
        for y in range(0, height, 80):
            painter.drawLine(0, y, width, y)

        cfg = manager.config
        cfg.edge_triangles_enabled = True
        cfg.edge_triangles_size = 22
        cfg.edge_triangles_color = "#FFE082"
        cfg.reference_columns_enabled = True
        cfg.reference_columns_width = 2
        cfg.reference_columns_alpha = 0.45
        cfg.reference_columns_color = "#A6D6E6"
        overlay = MotionSicknessOverlay(manager, tracker)
        overlay.current_vignette_alpha = 0.45
        overlay.current_anchor_boost = 0.4
        overlay._paint_vignette(painter, width, height, cfg)
        overlay._paint_reference_columns(painter, width, height, cfg)
        overlay._paint_visual_anchors(painter, width, height, cfg)
        overlay._paint_edge_triangles(painter, width, height, cfg)

        painter.setPen(QColor("#E7F1F6"))
        painter.setFont(QFont("Microsoft YaHei UI", 25, QFont.Weight.Bold))
        painter.drawText(QRectF(330, 270, 620, 70), Qt.AlignmentFlag.AlignCenter, "固定参照，保留中央视野")
        painter.setFont(QFont("Microsoft YaHei UI", 12))
        painter.setPen(QColor("#96AFBE"))
        painter.drawText(QRectF(270, 345, 740, 45), Qt.AlignmentFlag.AlignCenter,
                         "四边三角形  ·  四根细柱  ·  边缘锚点  ·  可调暗角")
        painter.setFont(QFont("Microsoft YaHei UI", 10))
        painter.setPen(QColor("#6F8798"))
        painter.drawText(QPointF(28, height - 27), "绘图示意 / 非游戏截图 / 参数可分别调整")
        painter.end()
        if not scene.save(str(output / "reference-guides.png")):
            raise RuntimeError("Could not write reference image")
        overlay.context_timer.stop()
        overlay.timer.stop()
        overlay.deleteLater()
        settings.deleteLater()
    print("README images generated in docs/images")


if __name__ == "__main__":
    main()
