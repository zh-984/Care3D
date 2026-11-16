"""Shared overlay drawing for the desktop window and non-interactive previews."""
import math
from collections import OrderedDict
from PyQt6.QtCore import Qt, QPointF, QRectF
from PyQt6.QtGui import QPainter, QColor, QRadialGradient, QPen, QBrush, QImage, QPolygonF, QPainterPath
from core.config import AppConfig


class OverlayPainter:
    def __init__(self):
        self._textures = OrderedDict()
        self.current_vignette_alpha = 0.0
        self.current_anchor_boost = 0.0
        self._comfort_active = False

    def paint_layers(self, painter, width, height, cfg):
        painter.save()
        if cfg.safe_zones_enabled:
            clip = QPainterPath()
            clip.addRect(QRectF(0, 0, width, height))
            for area in cfg.safe_zones:
                hole = QPainterPath()
                hole.addRect(QRectF(area["x"] * width, area["y"] * height,
                                   area["w"] * width, area["h"] * height))
                clip = clip.subtracted(hole)
            painter.setClipPath(clip)
        if (cfg.vignette_enabled or self._comfort_active) and self.current_vignette_alpha > 0.001:
            self._paint_vignette(painter, width, height, cfg)
        if cfg.reference_columns_enabled:
            self._paint_reference_columns(painter, width, height, cfg)
        if cfg.anchors_enabled:
            self._paint_visual_anchors(painter, width, height, cfg)
        if cfg.edge_triangles_enabled:
            self._paint_edge_triangles(painter, width, height, cfg)
        if cfg.corner_markers_enabled:
            self._paint_corner_markers(painter, width, height, cfg)
        if cfg.layout_enabled and cfg.layout_style != "none":
            self._paint_layout_reference(painter, width, height, cfg)
        if cfg.center_dot_enabled:
            self._paint_center_reference(painter, width, height, cfg)
        painter.restore()

    def _paint_vignette(self, painter, width, height, cfg):
        inner = max(0.20, cfg.vignette_inner_radius - cfg.vignette_contraction * self.current_anchor_boost)
        if self._comfort_active and cfg.comfort_enabled:
            inner = cfg.comfort_inner_radius
        key = round(inner * 100)
        texture = self._textures.get(key)
        if texture is None:
            size = 512
            texture = QImage(size, size, QImage.Format.Format_ARGB32_Premultiplied)
            texture.fill(0)
            gradient = QRadialGradient(size / 2, size / 2, size / 2)
            inner = key / 100
            gradient.setColorAt(0, QColor(0, 0, 0, 0))
            gradient.setColorAt(inner, QColor(0, 0, 0, 0))
            gradient.setColorAt(inner + (1 - inner) * 0.5, QColor(0, 0, 0, 95))
            gradient.setColorAt(1, QColor(0, 0, 0, 255))
            cache_painter = QPainter(texture)
            cache_painter.fillRect(texture.rect(), QBrush(gradient))
            cache_painter.end()
            self._textures[key] = texture
            if len(self._textures) > 16:
                self._textures.popitem(last=False)
        self._textures.move_to_end(key)
        painter.save()
        painter.setOpacity(self.current_vignette_alpha)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        # Stretch a normalized circular mask into an ellipse: all four sides are covered.
        from PyQt6.QtCore import QRectF
        painter.drawImage(QRectF(0, 0, width, height), texture)
        painter.restore()

    def _paint_visual_anchors(self, painter: QPainter, width: int, height: int, cfg: AppConfig):
        """
        绘制屏幕边缘静止视觉锚点 (Visual Anchors)
        技术要点：
        1. 锚点分布于屏幕四边及四角，绝对避开正中心 60% 的战斗视野区域。
        2. 锚点在静止时呈现极淡的透明度 (anchor_idle_alpha)，几乎不引起察觉。
        3. 视角高速转动时，透明度自动强化至 (anchor_boost_alpha)，强化大脑对外部不动坐标系的识别。
        4. 可选柔和外光晕双层绘制，增强科幻 UI 质感与边界提示感。
        """
        # 计算当前动态不透明度
        eff_alpha = cfg.anchor_idle_alpha + (cfg.anchor_boost_alpha - cfg.anchor_idle_alpha) * self.current_anchor_boost
        if eff_alpha <= 0.002:
            return

        base_color = QColor(cfg.anchor_color)
        alpha_int = int(max(0.0, min(1.0, eff_alpha)) * 255)
        anchor_color = QColor(base_color.red(), base_color.green(), base_color.blue(), alpha_int)

        r = max(1.5, cfg.anchor_radius)
        margin_x = width * cfg.anchor_margin_ratio
        margin_y = height * cfg.anchor_margin_ratio

        # 收集所有锚点坐标 (避开屏幕正中心)
        points = []
        sides = cfg.layout_sides if cfg.layout_enabled else ("top", "bottom", "left", "right")
        if cfg.layout_enabled:
            margin_x, margin_y = width * cfg.layout_margin, height * cfg.layout_margin

        # 左右两侧竖向点阵 (从 y=15% 到 y=85% 均匀分布)
        rows = max(2, cfg.anchor_rows)
        y_start = height * 0.15
        y_end = height * 0.85
        y_step = (y_end - y_start) / (rows - 1) if rows > 1 else 0

        for i in range(rows):
            py = y_start + i * y_step
            # 左边缘点
            if "left" in sides:
                points.append((margin_x, py))
            # 右边缘点
            if "right" in sides:
                points.append((width - margin_x, py))

        # 上下两侧横向点阵 (从 x=15% 到 x=85% 均匀分布)
        cols = max(2, cfg.anchor_cols)
        x_start = width * 0.15
        x_end = width * 0.85
        x_step = (x_end - x_start) / (cols - 1) if cols > 1 else 0

        for j in range(cols):
            px = x_start + j * x_step
            # 避开屏幕正中央横向 35%~65% 区域，确保上方/下方核心无干扰
            if 0.38 * width <= px <= 0.62 * width:
                continue
            # 上边缘点
            if "top" in sides:
                points.append((px, margin_y))
            # 下边缘点
            if "bottom" in sides:
                points.append((px, height - margin_y))

        # 四角斜向内凹参考锚点 (提供直角坐标基准)
        corner_offset_x = margin_x * 1.8 if cfg.layout_enabled else width * (cfg.anchor_margin_ratio * 1.8)
        corner_offset_y = margin_y * 1.8 if cfg.layout_enabled else height * (cfg.anchor_margin_ratio * 1.8)
        for x, y, a, b in ((corner_offset_x, corner_offset_y, "left", "top"),
                            (width - corner_offset_x, corner_offset_y, "right", "top"),
                            (corner_offset_x, height - corner_offset_y, "left", "bottom"),
                            (width - corner_offset_x, height - corner_offset_y, "right", "bottom")):
            if a in sides and b in sides:
                points.append((x, y))

        # 执行绘制
        painter.setPen(Qt.PenStyle.NoPen)

        # 若启用光晕，先绘制一层低透明度的大半透明外环
        if cfg.anchor_glow and alpha_int > 20:
            glow_color = QColor(base_color.red(), base_color.green(), base_color.blue(), int(alpha_int * 0.28))
            painter.setBrush(QBrush(glow_color))
            glow_r = r * 2.2
            for px, py in points:
                painter.drawEllipse(QPointF(px, py), glow_r, glow_r)

        # 绘制实体中心圆点
        painter.setBrush(QBrush(anchor_color))
        for px, py in points:
            painter.drawEllipse(QPointF(px, py), r, r)

    def _paint_reference_columns(self, painter: QPainter, width: int, height: int, cfg: AppConfig):
        """Four stationary slender bars centered in four equal horizontal screen sections."""
        bar_width = min(float(cfg.reference_columns_width), width / 16.0)
        bar_height = height * cfg.reference_columns_height_ratio
        top = (height - bar_height) / 2.0
        color = QColor(cfg.reference_columns_color)
        color.setAlphaF(cfg.reference_columns_alpha)
        painter.save()
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(color)
        positions = cfg.layout_column_positions if cfg.layout_enabled else (0.125, 0.375, 0.625, 0.875)
        for position in positions:
            center_x = width * position
            painter.drawRoundedRect(QRectF(center_x - bar_width / 2.0, top, bar_width, bar_height),
                                    bar_width / 2.0, bar_width / 2.0)
        painter.restore()

    def _paint_edge_triangles(self, painter: QPainter, width: int, height: int, cfg: AppConfig):
        """Four static inward-facing references; no motion-driven position or opacity."""
        half_base = min(cfg.edge_triangles_size / 2.0, width / 8.0, height / 8.0)
        depth = math.sqrt(3.0) * half_base
        margin = min(8.0, width / 16.0, height / 16.0)
        if cfg.layout_enabled:
            margin = min(width, height) * cfg.layout_margin
        cx, cy = width / 2.0, height / 2.0
        triangles = (
            ((cx - half_base, margin), (cx + half_base, margin), (cx, margin + depth)),
            ((cx - half_base, height - margin), (cx + half_base, height - margin),
             (cx, height - margin - depth)),
            ((margin, cy - half_base), (margin, cy + half_base), (margin + depth, cy)),
            ((width - margin, cy - half_base), (width - margin, cy + half_base),
             (width - margin - depth, cy)),
        )
        painter.save()
        painter.setPen(QPen(QColor(0, 0, 0, 135), 1.0))
        color = QColor(cfg.edge_triangles_color)
        color.setAlpha(175)
        painter.setBrush(color)
        sides = cfg.layout_sides if cfg.layout_enabled else ("top", "bottom", "left", "right")
        for side, vertices in zip(("top", "bottom", "left", "right"), triangles):
            if side not in sides:
                continue
            painter.drawPolygon(QPolygonF([QPointF(x, y) for x, y in vertices]))
        painter.restore()

    def _paint_corner_markers(self, painter, width, height, cfg):
        """Independent static corner references; all geometry stays inside the surface."""
        if width <= 0 or height <= 0 or cfg.corner_markers_alpha <= 0:
            return
        size = min(float(cfg.corner_markers_size), min(width, height) / 4.0)
        margin = min(float(cfg.corner_markers_margin), max(0.0, (min(width, height) - 2 * size) / 2))
        line = min(float(cfg.corner_markers_line_width), size / 3.0)
        color = QColor(cfg.corner_markers_color)
        color.setAlphaF(cfg.corner_markers_alpha)
        corners = (("top_left", margin, margin),
                   ("top_right", width - margin - size, margin),
                   ("bottom_left", margin, height - margin - size),
                   ("bottom_right", width - margin - size, height - margin - size))
        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(QPen(color, line, Qt.PenStyle.SolidLine, Qt.PenCapStyle.SquareCap,
                            Qt.PenJoinStyle.MiterJoin))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        for corner, x, y in corners:
            if not getattr(cfg, "corner_markers_" + corner):
                continue
            outer = QRectF(x, y, size, size)
            inset = line / math.sqrt(2) if cfg.corner_markers_style == "diamond" else line / 2
            rect = outer.adjusted(inset, inset, -inset, -inset)
            if cfg.corner_markers_style == "filled":
                painter.fillRect(outer, color)
            elif cfg.corner_markers_style == "diamond":
                center = rect.center()
                painter.drawPolygon(QPolygonF([QPointF(center.x(), rect.top()),
                                              QPointF(rect.right(), center.y()),
                                              QPointF(center.x(), rect.bottom()),
                                              QPointF(rect.left(), center.y())]))
            elif cfg.corner_markers_style == "brackets":
                pivot = {"top_left": rect.topLeft(), "top_right": rect.topRight(),
                         "bottom_left": rect.bottomLeft(), "bottom_right": rect.bottomRight()}[corner]
                horizontal = QPointF(rect.right() if "left" in corner else rect.left(), pivot.y())
                vertical = QPointF(pivot.x(), rect.bottom() if "top" in corner else rect.top())
                path = QPainterPath(horizontal)
                path.lineTo(pivot)
                path.lineTo(vertical)
                painter.drawPath(path)
            else:
                painter.drawRect(rect)
        painter.restore()

    def _paint_layout_reference(self, painter, width, height, cfg):
        color = QColor(cfg.layout_color)
        color.setAlphaF(cfg.layout_alpha)
        painter.save()
        painter.setPen(QPen(color, cfg.layout_line_width))
        x, y = width * cfg.layout_margin, height * cfg.layout_margin
        if cfg.layout_style == "horizon":
            # A fixed screen reference, not a measured in-game horizon.
            painter.drawLine(QPointF(x, height / 2), QPointF(width - x, height / 2))
        else:
            lines = {"top": ((x, y), (width - x, y)),
                     "bottom": ((x, height - y), (width - x, height - y)),
                     "left": ((x, y), (x, height - y)),
                     "right": ((width - x, y), (width - x, height - y))}
            for side in cfg.layout_sides:
                a, b = lines[side]
                painter.drawLine(QPointF(*a), QPointF(*b))
        painter.restore()

    def _paint_center_reference(self, painter: QPainter, width: int, height: int, cfg: AppConfig):
        """
        绘制屏幕正中心固定参照物 (固定微十字或极小圆点)
        作为视觉注意力焦点，帮助视网膜中心在画面高速翻转时有固定参照点可依。
        """
        cx = width / 2.0
        cy = height / 2.0

        base_color = QColor(cfg.center_dot_color)
        alpha_int = int(max(0.0, min(1.0, cfg.center_dot_alpha)) * 255)
        color = QColor(base_color.red(), base_color.green(), base_color.blue(), alpha_int)

        r = max(1.0, cfg.center_dot_radius)

        if cfg.center_dot_style == "cross":
            # 极细战术小十字准星
            pen = QPen(color, 1.5)
            painter.setPen(pen)
            cross_len = r * 3.5
            gap = r * 1.2
            # 上下左右四条短线
            painter.drawLine(QPointF(cx, cy - cross_len), QPointF(cx, cy - gap))
            painter.drawLine(QPointF(cx, cy + gap), QPointF(cx, cy + cross_len))
            painter.drawLine(QPointF(cx - cross_len, cy), QPointF(cx - gap, cy))
            painter.drawLine(QPointF(cx + gap, cy), QPointF(cx + cross_len, cy))
            # 中心极微小点
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(color))
            painter.drawEllipse(QPointF(cx, cy), 1.0, 1.0)
        else:
            # 极简中心微点 (带微黑边以防浅色背景看不清)
            pen = QPen(QColor(0, 0, 0, int(alpha_int * 0.5)), 0.8)
            painter.setPen(pen)
            painter.setBrush(QBrush(color))
            painter.drawEllipse(QPointF(cx, cy), r, r)
