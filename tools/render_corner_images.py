"""Render corner references and their controls using synthetic, private-free content."""
import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from pathlib import Path
import sys
import tempfile
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from PyQt6.QtCore import Qt, QRectF
from PyQt6.QtGui import QColor, QFont, QFontDatabase, QImage, QPainter, QPen
from PyQt6.QtWidgets import QApplication
from core.config import AppConfig, ConfigManager
from core.mouse_tracker import MouseSpeedTracker
from ui.overlay_painter import OverlayPainter
from ui.settings_window import SettingsWindow


def main():
    app = QApplication([])
    fonts = Path(os.environ.get("SystemRoot", "C:/Windows")) / "Fonts"
    for name in ("msyh.ttc", "msyhbd.ttc", "segoeui.ttf", "seguiemj.ttf"):
        if (fonts / name).exists():
            QFontDatabase.addApplicationFont(str(fonts / name))
    output = Path("docs/images")
    output.mkdir(parents=True, exist_ok=True)
    image = QImage(1040, 600, QImage.Format.Format_ARGB32_Premultiplied)
    image.fill(QColor("#0E1017"))
    painter = QPainter(image)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setFont(QFont("Microsoft YaHei UI", 15, QFont.Weight.Bold))
    painter.setPen(QColor("#E2E8F0"))
    painter.drawText(QRectF(20, 4, 1000, 35), Qt.AlignmentFlag.AlignCenter, "四角固定锚点 · 四种可选样式")
    cfg = AppConfig(vignette_enabled=False, anchors_enabled=False, corner_markers_enabled=True,
                    corner_markers_size=32, corner_markers_margin=20, corner_markers_alpha=.70,
                    corner_markers_line_width=3, corner_markers_color="#67E8F9")
    renderer = OverlayPainter()
    for index, (style, label) in enumerate((("square", "空心正方形"), ("filled", "实心正方形"),
                                             ("diamond", "菱形"), ("brackets", "直角角标"))):
        painter.save()
        painter.translate(20 + index % 2 * 510, 45 + index // 2 * 275)
        painter.fillRect(QRectF(0, 0, 490, 230), QColor("#223246"))
        painter.setPen(QPen(QColor("#2E445D"), 1))
        for x in range(0, 490, 35):
            painter.drawLine(x, 0, x, 230)
        for y in range(0, 230, 35):
            painter.drawLine(0, y, 490, y)
        cfg.corner_markers_style = style
        renderer.paint_layers(painter, 490, 230, cfg)
        painter.setPen(QColor("#D2E3EF"))
        painter.setFont(QFont("Microsoft YaHei UI", 13))
        painter.drawText(QRectF(0, 0, 490, 230), Qt.AlignmentFlag.AlignCenter, label)
        painter.restore()
    painter.setPen(QColor("#8FA5BA"))
    painter.setFont(QFont("Microsoft YaHei UI", 10))
    painter.drawText(QRectF(20, 565, 1000, 25), Qt.AlignmentFlag.AlignCenter,
                     "静态示意 · 大小 / 颜色 / 可见度 / 线宽 / 边距可调 · 四个角可分别开关")
    painter.end()
    if not image.save(str(output / "corner-anchors.png")):
        raise RuntimeError("Cannot write corner reference image")
    with tempfile.TemporaryDirectory(prefix="care3d-corner-docs-") as tmp:
        manager = ConfigManager(tmp)
        manager.config.corner_markers_enabled = True
        manager.config.corner_markers_color = "#67E8F9"
        manager.config.corner_markers_alpha = .65
        window = SettingsWindow(manager, MouseSpeedTracker())
        window.resize(820, 900)
        window.tabs.setCurrentIndex(1)
        window.show()
        app.processEvents()
        scroll = window.tabs.currentWidget()
        scroll.verticalScrollBar().setValue(scroll.verticalScrollBar().maximum())
        app.processEvents()
        window.grab().save(str(output / "corner-anchor-settings.png"))
        window.hide()
        window.save_timer.stop()
        window.deleteLater()
    print("Corner anchor images generated in docs/images")


if __name__ == "__main__":
    main()
