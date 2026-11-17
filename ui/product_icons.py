"""Small, dependency-free vector icons for the Care3D desktop interface.

Create a QApplication before calling these helpers.  Icons are rendered at
multiple device pixel ratios so the same artwork stays crisp on scaled displays.
"""

from __future__ import annotations

from math import cos, pi, sin

from PyQt6.QtCore import QLineF, QPointF, QRectF, Qt
from PyQt6.QtGui import (
    QBrush,
    QColor,
    QIcon,
    QPainter,
    QPainterPath,
    QPen,
    QPixmap,
    QPolygonF,
    QRadialGradient,
)

__all__ = ["icon", "logo_pixmap", "app_icon"]

_ICON_NAMES = frozenset(
    {"vignette", "anchors", "columns", "reticle", "settings",
     "extensions", "retop", "palette", "play", "pause"}
)


def _line(painter: QPainter, x1: float, y1: float,
          x2: float, y2: float) -> None:
    painter.drawLine(QLineF(x1, y1, x2, y2))


def _draw_icon(painter: QPainter, name: str, color: QColor) -> None:
    pen = QPen(color, 1.7)
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
    painter.setPen(pen)
    painter.setBrush(Qt.BrushStyle.NoBrush)

    if name == "vignette":
        painter.drawRoundedRect(QRectF(3.5, 4.5, 17, 15), 3, 3)
        for x, y, dx, dy in ((6.5, 7.5, 3, 3), (17.5, 7.5, -3, 3),
                             (6.5, 16.5, 3, -3), (17.5, 16.5, -3, -3)):
            _line(painter, x, y, x + dx, y)
            _line(painter, x, y, x, y + dy)
    elif name == "anchors":
        for x, y, dx, dy in ((4.5, 4.5, 4, 4), (19.5, 4.5, -4, 4),
                             (4.5, 19.5, 4, -4), (19.5, 19.5, -4, -4)):
            _line(painter, x, y, x + dx, y)
            _line(painter, x, y, x, y + dy)
        painter.drawEllipse(QRectF(10, 10, 4, 4))
    elif name == "columns":
        for x in (4, 10, 16):
            painter.drawRoundedRect(QRectF(x, 4.5, 4, 15), 1.3, 1.3)
    elif name == "reticle":
        painter.drawEllipse(QRectF(6.5, 6.5, 11, 11))
        for x1, y1, x2, y2 in ((12, 3, 12, 7), (12, 17, 12, 21),
                                 (3, 12, 7, 12), (17, 12, 21, 12)):
            _line(painter, x1, y1, x2, y2)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(color)
        painter.drawEllipse(QRectF(10.8, 10.8, 2.4, 2.4))
    elif name == "settings":
        # Eight teeth, with rounded joins and a clear central aperture.
        points = []
        for index in range(32):
            angle = -pi / 2 + index * pi / 16
            radius = 8.7 if index % 4 in (1, 2) else 7.1
            points.append(QPointF(12 + radius * cos(angle),
                                 12 + radius * sin(angle)))
        painter.drawPolygon(QPolygonF(points))
        painter.drawEllipse(QRectF(8.8, 8.8, 6.4, 6.4))
    elif name == "extensions":
        for x, y in ((4, 4), (4, 13), (13, 13)):
            painter.drawRoundedRect(QRectF(x, y, 6.5, 6.5), 1.5, 1.5)
        _line(painter, 16.3, 3.5, 16.3, 10)
        _line(painter, 13, 6.8, 19.5, 6.8)
    elif name == "retop":
        path = QPainterPath()
        path.moveTo(8, 7)
        path.lineTo(4.5, 7)
        path.lineTo(4.5, 20)
        path.lineTo(19.5, 20)
        path.lineTo(19.5, 7)
        path.lineTo(16, 7)
        painter.drawPath(path)
        _line(painter, 12, 14, 12, 3.5)
        _line(painter, 8.5, 7, 12, 3.5)
        _line(painter, 12, 3.5, 15.5, 7)
    elif name == "palette":
        path = QPainterPath()
        path.moveTo(20.3, 11.6)
        path.cubicTo(20.3, 6.7, 16.6, 3.7, 12, 3.7)
        path.cubicTo(7.1, 3.7, 3.7, 7.3, 3.7, 12)
        path.cubicTo(3.7, 16.7, 7.2, 20.3, 11.8, 20.3)
        path.cubicTo(14.5, 20.3, 15.2, 18.7, 14, 17.2)
        path.cubicTo(12.8, 15.7, 13.9, 14, 15.6, 14)
        path.lineTo(17.7, 14)
        path.cubicTo(19.4, 14, 20.3, 13.1, 20.3, 11.6)
        painter.drawPath(path)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(color)
        for x, y in ((7.5, 10.5), (10.5, 7.5), (14.8, 8)):
            painter.drawEllipse(QRectF(x - 1.1, y - 1.1, 2.2, 2.2))
    elif name == "play":
        painter.setBrush(color)
        painter.drawPolygon(QPolygonF([
            QPointF(8, 4.8), QPointF(19, 12), QPointF(8, 19.2)
        ]))
    elif name == "pause":
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(color)
        for x in (6.5, 14):
            painter.drawRoundedRect(QRectF(x, 5, 3.5, 14), 1, 1)


def icon(name: str, color: str = "#A0ADB7", size: int = 18) -> QIcon:
    """Return a consistent line icon, at 1x, 2x and 3x display resolution.

    Supported names: vignette, anchors, columns, reticle, settings, extensions,
    retop, palette, play and pause. Unknown names raise ValueError.
    """
    if name not in _ICON_NAMES:
        raise ValueError(f"Unknown Care3D icon: {name!r}")
    if size < 1:
        raise ValueError("Icon size must be positive")
    tint = QColor(color)
    if not tint.isValid():
        raise ValueError(f"Invalid icon color: {color!r}")
    result = QIcon()
    for ratio in (1, 2, 3):
        pixmap = QPixmap(size * ratio, size * ratio)
        pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap)
        try:
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            painter.scale(size * ratio / 24, size * ratio / 24)
            _draw_icon(painter, name, tint)
        finally:
            painter.end()
        pixmap.setDevicePixelRatio(ratio)
        result.addPixmap(pixmap)
    return result


def logo_pixmap(size: int = 64) -> QPixmap:
    """Render the Care3D focus mark on a rounded slate tile.

    The simple ring, central point and four reference ticks remain recognizable
    at taskbar sizes. The returned pixmap has device pixel ratio 1.
    """
    if size < 1:
        raise ValueError("Logo size must be positive")
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    try:
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.scale(size / 64, size / 64)
        painter.setPen(QPen(QColor("#354555"), 1))
        painter.setBrush(QColor("#1D2A36"))
        painter.drawRoundedRect(QRectF(2.5, 2.5, 59, 59), 14, 14)

        glow = QRadialGradient(QPointF(32, 32), 24)
        glow.setColorAt(0, QColor(98, 197, 189, 26))
        glow.setColorAt(1, QColor(98, 197, 189, 0))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(glow))
        painter.drawEllipse(QRectF(8, 8, 48, 48))

        pen = QPen(QColor("#62C5BD"), 3.5)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawEllipse(QRectF(19, 19, 26, 26))

        pen.setColor(QColor("#91A4B7"))
        pen.setWidthF(2.5)
        painter.setPen(pen)
        for x1, y1, x2, y2 in ((32, 10.5, 32, 15),
                                 (32, 49, 32, 53.5),
                                 (10.5, 32, 15, 32),
                                 (49, 32, 53.5, 32)):
            _line(painter, x1, y1, x2, y2)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor("#C3F2E9"))
        painter.drawEllipse(QRectF(29, 29, 6, 6))
    finally:
        painter.end()
    return pixmap


def app_icon() -> QIcon:
    """Return the brand mark with all common desktop icon resolutions."""
    result = QIcon()
    for size in (16, 24, 32, 48, 64, 128, 256):
        result.addPixmap(logo_pixmap(size))
    return result
