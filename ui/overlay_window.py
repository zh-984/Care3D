"""A click-through comfort overlay with adaptive rendering and optional game binding."""
import math
import time
from collections import OrderedDict
from PyQt6.QtWidgets import QWidget, QApplication
from PyQt6.QtCore import Qt, QTimer, QPointF, QRectF
from PyQt6.QtGui import QPainter, QColor, QRadialGradient, QPen, QBrush, QImage, QPolygonF
from core.config import ConfigManager, AppConfig
from core.mouse_tracker import MouseSpeedTracker
from core.gamepad import GamepadTracker
from core.win_utils import (make_window_click_through, bring_window_to_topmost,
                            foreground_window, client_geometry)

class MotionSicknessOverlay(QWidget):
    def __init__(self, config_manager: ConfigManager, mouse_tracker: MouseSpeedTracker):
        super().__init__()
        self.cfg_mgr = config_manager
        self.mouse_tracker = mouse_tracker
        self.gamepad = GamepadTracker()
        self.current_vignette_alpha = 0.0
        self.current_anchor_boost = 0.0
        self._gamepad_strength = 0.0
        self._is_sleeping = False
        self._last_tick = time.perf_counter()
        self._textures = OrderedDict()
        self._target_hwnd = 0
        self._target_title = ""
        self._context_allowed = True
        self._last_topmost = 0.0
        self.status_text = "已就绪"
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint |
                            Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Tool |
                            Qt.WindowType.WindowTransparentForInput)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)
        self.timer = QTimer(self)
        self.timer.setTimerType(Qt.TimerType.PreciseTimer)
        self.timer.timeout.connect(self._animation_tick)
        self.context_timer = QTimer(self)
        self.context_timer.timeout.connect(self.refresh_context)
        self.mouse_tracker.motion_detected.connect(self._wake_animation)
        self.cfg_mgr.add_listener(self.on_config_changed)
        app = QApplication.instance()
        app.screenAdded.connect(self._screens_changed)
        app.screenRemoved.connect(self._screens_changed)
        self._connected_screens = set()
        self._connect_screens()
        self.update_screen_geometry()

    def _connect_screens(self):
        for screen in QApplication.screens():
            if screen not in self._connected_screens:
                screen.geometryChanged.connect(self._screens_changed)
                self._connected_screens.add(screen)

    def _screens_changed(self, *args):
        self._connect_screens()
        self.refresh_context()

    def update_screen_geometry(self, target_hwnd=0):
        screens = QApplication.screens()
        if not screens:
            return
        cfg = self.cfg_mgr.config
        geom = client_geometry(target_hwnd, screens) if target_hwnd else None
        if geom is None:
            screen = screens[cfg.selected_screen_index] if cfg.selected_screen_index < len(screens) else QApplication.primaryScreen()
            geom = screen.geometry()
        if not geom.isEmpty() and geom != self.geometry():
            self.setGeometry(geom)
            self.update()

    def refresh_context(self):
        cfg = self.cfg_mgr.config
        if cfg.target_window_title != self._target_title:
            self._target_title = cfg.target_window_title
            self._target_hwnd = 0
        allowed = cfg.overlay_visible
        hwnd = 0
        if allowed and cfg.only_target_window:
            foreground, title = foreground_window()
            match = bool(self._target_title and self._target_title.casefold() in title.casefold())
            if foreground and (match or foreground == self._target_hwnd):
                hwnd = foreground
                self._target_hwnd = foreground
            else:
                allowed = False
        self._context_allowed = allowed
        if allowed:
            self.update_screen_geometry(hwnd)
            if not self.isVisible():
                self.show()
            if cfg.gamepad_enabled:
                strength = self.gamepad.poll()
                if strength != self._gamepad_strength:
                    self._gamepad_strength = strength
                    self._wake_animation()
            else:
                self._gamepad_strength = 0.0
            if time.perf_counter() - self._last_topmost > 2:
                self.reapply_topmost()
            self.status_text = "游戏窗口内运行" if cfg.only_target_window else "所选屏幕内运行"
        else:
            self.hide()
            self.mouse_tracker.set_enabled(False)
            self._gamepad_strength = 0.0
            self.status_text = "已暂停" if not cfg.overlay_visible else "等待目标游戏获得焦点"
        if cfg.overlay_visible:
            self.context_timer.start(50 if cfg.gamepad_enabled else 250)
        else:
            self.context_timer.stop()

    def showEvent(self, event):
        super().showEvent(event)
        if QApplication.instance().platformName() == "windows":
            make_window_click_through(int(self.winId()))
        self.mouse_tracker.set_enabled(True)
        self.mouse_tracker.reset()
        self.current_vignette_alpha = 0.0
        self.current_anchor_boost = 0.0
        self._wake_animation()

    def hideEvent(self, event):
        super().hideEvent(event)
        self.timer.stop()
        self.mouse_tracker.set_enabled(False)
        self.current_vignette_alpha = 0.0
        self.current_anchor_boost = 0.0
        self._is_sleeping = True

    def on_config_changed(self, cfg: AppConfig):
        self.timer.setInterval(max(8, round(1000 / cfg.fps_limit)))
        self.refresh_context()
        self._wake_animation()
        self.update()

    def reapply_topmost(self):
        if self.isVisible() and self._context_allowed:
            if QApplication.instance().platformName() == "windows":
                bring_window_to_topmost(int(self.winId()))
            self._last_topmost = time.perf_counter()

    def _wake_animation(self):
        if not self.isVisible() or not self._context_allowed:
            return
        if not self.timer.isActive():
            self._last_tick = time.perf_counter() - 1 / self.cfg_mgr.config.fps_limit
            self.timer.start(max(8, round(1000 / self.cfg_mgr.config.fps_limit)))
        self._is_sleeping = False

    def _animation_tick(self):
        if not self.isVisible():
            return
        cfg = self.cfg_mgr.config
        now = time.perf_counter()
        dt = max(0.001, min(0.1, now - self._last_tick))
        self._last_tick = now
        speed, moving = self.mouse_tracker.poll_speed(cfg.vignette_decay_time)
        ratio = max(0.0, min(1.0, (speed * cfg.mouse_gain - cfg.vignette_threshold) /
                               max(100.0, cfg.vignette_sensitivity - cfg.vignette_threshold)))
        ratio = max(ratio, self._gamepad_strength)
        target_motion = ratio * ratio * (3 - 2 * ratio)
        target_alpha = (cfg.vignette_idle_alpha +
                        (cfg.vignette_max_alpha - cfg.vignette_idle_alpha) * target_motion) if cfg.vignette_enabled else 0.0
        previous_alpha = self.current_vignette_alpha
        previous_motion = self.current_anchor_boost
        tau = 0.055 if target_motion > previous_motion else cfg.vignette_decay_time / 2.3
        blend = -math.expm1(-dt / max(0.025, tau))
        self.current_anchor_boost += (target_motion - previous_motion) * blend
        self.current_vignette_alpha += (target_alpha - previous_alpha) * blend
        settled = (abs(self.current_anchor_boost - target_motion) < 0.002 and
                   abs(self.current_vignette_alpha - target_alpha) < 0.002)
        if settled:
            self.current_anchor_boost = target_motion
            self.current_vignette_alpha = target_alpha
        if previous_alpha != self.current_vignette_alpha or previous_motion != self.current_anchor_boost:
            self.update()
        if settled and not moving:
            self._is_sleeping = True
            self.timer.stop()  # Input signal wakes it; context checks stay low-frequency.

    @property
    def is_sleeping(self):
        return self._is_sleeping

    def paintEvent(self, event):
        cfg = self.cfg_mgr.config
        width, height = self.width(), self.height()
        if width <= 0 or height <= 0:
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Source)
        painter.fillRect(self.rect(), QColor(0, 0, 0, 0))
        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)
        if cfg.vignette_enabled and self.current_vignette_alpha > 0.001:
            self._paint_vignette(painter, width, height, cfg)
        if cfg.reference_columns_enabled:
            self._paint_reference_columns(painter, width, height, cfg)
        if cfg.anchors_enabled:
            self._paint_visual_anchors(painter, width, height, cfg)
        if cfg.edge_triangles_enabled:
            self._paint_edge_triangles(painter, width, height, cfg)
        if cfg.center_dot_enabled:
            self._paint_center_reference(painter, width, height, cfg)
        painter.end()

    def _paint_vignette(self, painter, width, height, cfg):
        inner = max(0.20, cfg.vignette_inner_radius - cfg.vignette_contraction * self.current_anchor_boost)
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

        # 左右两侧竖向点阵 (从 y=15% 到 y=85% 均匀分布)
        rows = max(2, cfg.anchor_rows)
        y_start = height * 0.15
        y_end = height * 0.85
        y_step = (y_end - y_start) / (rows - 1) if rows > 1 else 0

        for i in range(rows):
            py = y_start + i * y_step
            # 左边缘点
            points.append((margin_x, py))
            # 右边缘点
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
            points.append((px, margin_y))
            # 下边缘点
            points.append((px, height - margin_y))

        # 四角斜向内凹参考锚点 (提供直角坐标基准)
        corner_offset_x = width * (cfg.anchor_margin_ratio * 1.8)
        corner_offset_y = height * (cfg.anchor_margin_ratio * 1.8)
        points.append((corner_offset_x, corner_offset_y))
        points.append((width - corner_offset_x, corner_offset_y))
        points.append((corner_offset_x, height - corner_offset_y))
        points.append((width - corner_offset_x, height - corner_offset_y))

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
        for index in range(4):
            center_x = width * (2 * index + 1) / 8.0
            painter.drawRoundedRect(QRectF(center_x - bar_width / 2.0, top, bar_width, bar_height),
                                    bar_width / 2.0, bar_width / 2.0)
        painter.restore()

    def _paint_edge_triangles(self, painter: QPainter, width: int, height: int, cfg: AppConfig):
        """Four static inward-facing references; no motion-driven position or opacity."""
        half_base = min(cfg.edge_triangles_size / 2.0, width / 8.0, height / 8.0)
        depth = math.sqrt(3.0) * half_base
        margin = min(8.0, width / 16.0, height / 16.0)
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
        for vertices in triangles:
            painter.drawPolygon(QPolygonF([QPointF(x, y) for x, y in vertices]))
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
