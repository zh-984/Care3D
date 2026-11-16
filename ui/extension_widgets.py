"""Static previews and a cancel-safe optional setup guide."""
import copy
from PyQt6.QtCore import Qt, QRectF, QPointF, QSize, QTimer, pyqtSignal
from PyQt6.QtGui import QColor, QPainter, QPen
from PyQt6.QtWidgets import (QWidget, QDialog, QVBoxLayout, QLabel, QComboBox,
                             QPushButton, QDialogButtonBox, QHBoxLayout)
from core.config import default_profile, valid_rectangles
from core.extensions import recommend_input
from ui.overlay_painter import OverlayPainter


class OverlayPreview(QWidget):
    areas_changed = pyqtSignal(list)
    selection_changed = pyqtSignal(int)

    def __init__(self, config, editable=False, parent=None):
        super().__init__(parent)
        self.config = copy.deepcopy(config)
        self.editable = editable
        self.selected = -1
        self.renderer = OverlayPainter()
        self.comfort = False
        self._drag = None
        self.setMinimumSize(260, 160)
        self.setMouseTracking(editable)
        self.setToolTip("在示意图中拖动框选避让区；拖动已有框可移动，拖动右下角可缩放。" if editable else "静态效果示意，不捕获游戏画面。")

    def sizeHint(self):
        return QSize(560, 260)

    def set_config(self, config):
        self.config = copy.deepcopy(config)
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.fillRect(self.rect(), QColor("#26384A"))
        painter.setPen(QPen(QColor("#3D5266"), 1))
        for x in range(0, self.width(), 40):
            painter.drawLine(x, 0, x, self.height())
        for y in range(0, self.height(), 40):
            painter.drawLine(0, y, self.width(), y)
        painter.setPen(QColor("#E3EAF0"))
        painter.drawText(QRectF(0, 0, self.width(), self.height()), Qt.AlignmentFlag.AlignCenter, "游戏画面示意")
        self.renderer._comfort_active = self.comfort and self.config.comfort_enabled
        self.renderer.current_vignette_alpha = (self.config.comfort_alpha if self.renderer._comfort_active else
                                               self.config.vignette_idle_alpha + (self.config.vignette_max_alpha - self.config.vignette_idle_alpha) * 0.35)
        self.renderer.current_anchor_boost = 0.35
        self.renderer.paint_layers(painter, self.width(), self.height(), self.config)
        if self.editable:
            for index, area in enumerate(self.config.safe_zones):
                rect = QRectF(area["x"] * self.width(), area["y"] * self.height(),
                              area["w"] * self.width(), area["h"] * self.height())
                painter.setPen(QPen(QColor("#FDE047" if index == self.selected else "#67E8F9"), 2))
                painter.setBrush(Qt.BrushStyle.NoBrush)
                painter.drawRect(rect)
                painter.drawText(rect.adjusted(5, 3, -3, -3), Qt.AlignmentFlag.AlignTop, area["label"])
                painter.fillRect(QRectF(rect.right() - 7, rect.bottom() - 7, 7, 7), QColor("#FDE047"))
        painter.end()

    def mousePressEvent(self, event):
        if not self.editable or not self.isEnabled() or event.button() != Qt.MouseButton.LeftButton:
            return
        point = event.position()
        x, y = point.x() / self.width(), point.y() / self.height()
        for index in range(len(self.config.safe_zones) - 1, -1, -1):
            area = self.config.safe_zones[index]
            if QRectF(area["x"], area["y"], area["w"], area["h"]).contains(QPointF(x, y)):
                self.selected = index
                resize = abs(x - area["x"] - area["w"]) * self.width() < 14 and abs(y - area["y"] - area["h"]) * self.height() < 14
                self._drag = ("resize" if resize else "move", x, y, copy.deepcopy(area))
                self.selection_changed.emit(index)
                self.update()
                return
        if len(self.config.safe_zones) >= 16:
            return
        self.config.safe_zones.append(dict(x=x, y=y, w=0.01, h=0.01, label="自定义区域"))
        self.selected = len(self.config.safe_zones) - 1
        self._drag = ("new", x, y, None)
        self.selection_changed.emit(self.selected)

    def mouseMoveEvent(self, event):
        if not self._drag:
            return
        x = max(0, min(1, event.position().x() / self.width()))
        y = max(0, min(1, event.position().y() / self.height()))
        mode, sx, sy, original = self._drag
        area = self.config.safe_zones[self.selected]
        if mode == "new":
            area.update(x=min(sx, x), y=min(sy, y), w=max(0.01, abs(x - sx)), h=max(0.01, abs(y - sy)))
        elif mode == "move":
            area.update(x=max(0, min(1 - original["w"], original["x"] + x - sx)),
                        y=max(0, min(1 - original["h"], original["y"] + y - sy)))
        else:
            area.update(w=max(0.01, x - area["x"]), h=max(0.01, y - area["y"]))
        self.config.safe_zones = valid_rectangles(self.config.safe_zones)
        self.update()

    def mouseReleaseEvent(self, event):
        if self._drag and event.button() == Qt.MouseButton.LeftButton:
            self.mouseMoveEvent(event)
            self._drag = None
            self.areas_changed.emit(copy.deepcopy(self.config.safe_zones))


class SetupGuide(QDialog):
    def __init__(self, config, tracker, parent=None):
        super().__init__(parent)
        self.original = copy.deepcopy(config)
        self.tracker = tracker
        self.result_values = {}
        self.samples = []
        self.setWindowTitle("可选设置向导 · 先预览再应用")
        self.resize(650, 560)
        layout = QVBoxLayout(self)
        hint = QLabel("选择一个起点，或只校准输入。这里的预览不会修改现有参数；取消即可退出。\n这不是效果检测，出现不适请停止游戏。")
        hint.setWordWrap(True)
        layout.addWidget(hint)
        self.choice = QComboBox()
        for label, key in (("保留当前设置", "current"), ("轻度起点 · 少遮挡", "light"), ("平衡起点 · 转向时增强", "balanced")):
            self.choice.addItem(label, key)
        layout.addWidget(self.choice)
        self.preview = OverlayPreview(config)
        layout.addWidget(self.preview, 1)
        self.status = QLabel("静态示意，不会自动旋转游戏镜头。")
        self.status.setWordWrap(True)
        layout.addWidget(self.status)
        self.calibrate = QPushButton("采集 6 秒正常鼠标输入（可选）")
        self.calibrate.clicked.connect(self.start_calibration)
        layout.addWidget(self.calibrate)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Apply | QDialogButtonBox.StandardButton.Cancel)
        buttons.button(QDialogButtonBox.StandardButton.Apply).setText("应用到当前方案")
        buttons.button(QDialogButtonBox.StandardButton.Apply).clicked.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        self.choice.currentIndexChanged.connect(self.update_preview)
        self.timer = QTimer(self)
        self.timer.setInterval(100)
        self.timer.timeout.connect(self.sample)
        self.finished.connect(self.cleanup)

    def update_preview(self):
        cfg = copy.deepcopy(self.original)
        choice = self.choice.currentData()
        values = {}
        if choice != "current":
            values = {key: value for key, value in default_profile(choice).items() if key.startswith("vignette_")}
        values.update(self.result_values.get("calibration", {}))
        for key, value in values.items():
            setattr(cfg, key, value)
        self.result_values["settings"] = values
        self.preview.set_config(cfg)

    def start_calibration(self):
        if not self.tracker._is_running:
            self.status.setText("输入检测尚未启动，可直接选择起点或取消。")
            return
        self.samples = []
        self.tracker.begin_calibration()
        self.calibrate.setEnabled(False)
        self.timer.start()
        self.status.setText("请按平时习惯移动鼠标，不需要快速旋转游戏画面。")

    def sample(self):
        self.samples.append(self.tracker.calibration_sample())
        if len(self.samples) < 60:
            return
        self.timer.stop()
        self.tracker.end_calibration()
        self.calibrate.setEnabled(True)
        try:
            recommendation = recommend_input(self.samples)
        except ValueError as error:
            self.status.setText(str(error))
            return
        self.result_values["calibration"] = recommendation
        self.status.setText(f"建议输入阈值 {recommendation['vignette_sensitivity']}，死区 {recommendation['vignette_threshold']}。仅校准输入响应，应用前不会保存。")
        self.update_preview()

    def cleanup(self):
        self.timer.stop()
        self.tracker.end_calibration()
