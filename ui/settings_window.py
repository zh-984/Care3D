"""
现代化电竞风格紧凑控制面板 (settings_window.py)
特点：
1. 高密度紧凑排版：参数之间紧密对齐，单行整合 (名称+滑块+数值Badge)，彻底告别空旷感与多余留白。
2. 彻底屏蔽滚轮误触 (NoWheelSlider, NoWheelComboBox)。
3. 专业电竞驱动软件级视觉层次与呼吸状态感。
"""

import sys
import re
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QSlider, QCheckBox,
    QPushButton, QColorDialog, QComboBox, QTabWidget,
    QProgressBar, QScrollArea, QFrame, QMessageBox, QApplication,
    QStyle, QStyleOptionButton, QInputDialog
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from core.win_utils import list_target_windows
from PyQt6.QtGui import QColor, QPainter, QPainterPath, QPen

from core.config import ConfigManager, PROFILE_NAMES
from core.mouse_tracker import MouseSpeedTracker
from core.preset_library import PresetLibrary


# =============================================================================
# 无滚轮误触组件
# =============================================================================

class MarkedCheckBox(QCheckBox):
    """Keep native checkbox behavior and draw a crisp tick over the styled indicator."""

    def paintEvent(self, event):
        super().paintEvent(event)
        if self.checkState() != Qt.CheckState.Checked:
            return
        option = QStyleOptionButton()
        self.initStyleOption(option)
        rect = self.style().subElementRect(QStyle.SubElement.SE_CheckBoxIndicator, option, self)
        path = QPainterPath()
        path.moveTo(rect.x() + rect.width() * 0.23, rect.y() + rect.height() * 0.51)
        path.lineTo(rect.x() + rect.width() * 0.43, rect.y() + rect.height() * 0.71)
        path.lineTo(rect.x() + rect.width() * 0.78, rect.y() + rect.height() * 0.29)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        color = QColor("#07131B" if self.isEnabled() else "#8B98A5")
        pen = QPen(color, 2.5, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
        painter.setPen(pen)
        painter.drawPath(path)
        painter.end()


class NoWheelSlider(QSlider):
    """彻底忽略滚轮事件，防止滚动页面时误修改滑块数值"""
    def wheelEvent(self, event):
        event.ignore()


class NoWheelComboBox(QComboBox):
    """彻底忽略滚轮事件，防止滚动页面时误切换下拉项"""
    def wheelEvent(self, event):
        event.ignore()


class EditableValueLabel(QLabel):
    """The original value badge gains opt-in keyboard and double-click editing."""
    def __init__(self, text, editor):
        super().__init__(text)
        self.editor = editor

    def mouseDoubleClickEvent(self, event):
        self.editor()

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter, Qt.Key.Key_Space):
            self.editor()
        else:
            super().keyPressEvent(event)


# =============================================================================
# 主设置控制面板
# =============================================================================

class SettingsWindow(QWidget):
    request_reapply_topmost = pyqtSignal()
    request_toggle_overlay = pyqtSignal()

    def __init__(self, config_manager: ConfigManager, mouse_tracker: MouseSpeedTracker, overlay_ref=None,
                 library=None, extension_controller=None):
        super().__init__()
        self.cfg_mgr = config_manager
        self.mouse_tracker = mouse_tracker
        self.overlay_ref = overlay_ref
        self.library = library or PresetLibrary(config_manager)
        self.extension_controller = extension_controller
        self._loading = True
        self.save_timer = QTimer(self)
        self.save_timer.setSingleShot(True)
        self.save_timer.setInterval(300)
        self.save_timer.timeout.connect(self._save_config)

        self.setWindowTitle("Care3D - 游戏视觉舒适辅助")
        # 精致紧凑尺寸：单屏尽收眼底，无需繁琐翻页
        self.setMinimumSize(720, 640)
        self.resize(800, 740)

        self._apply_compact_stylesheet()
        self._init_ui()
        self._load_values_to_ui()

        # Only update telemetry while the panel is visible.
        self.telemetry_timer = QTimer(self)
        self.telemetry_timer.setInterval(150)
        self.telemetry_timer.timeout.connect(self._update_telemetry)

    def _apply_compact_stylesheet(self):
        """专业电竞紧凑暗黑 QSS"""
        self.setStyleSheet("""
            QWidget {
                background-color: #0E1017;
                color: #F1F5F9;
                font-family: 'Microsoft YaHei UI', 'Microsoft YaHei', 'Segoe UI', sans-serif;
                font-size: 12px;
            }

            /* --- 滚动区域 --- */
            QScrollArea {
                border: none;
                background-color: transparent;
            }
            QScrollBar:vertical {
                background: #141722;
                width: 6px;
                border-radius: 3px;
            }
            QScrollBar::handle:vertical {
                background: #2D3349;
                min-height: 20px;
                border-radius: 3px;
            }
            QScrollBar::handle:vertical:hover {
                background: #00E5FF;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }

            /* --- 选项卡紧凑排布 --- */
            QTabWidget::pane {
                border: 1px solid #1E2333;
                background-color: #12151E;
                border-radius: 8px;
                top: -1px;
            }
            QTabBar::tab {
                background: #0E1017;
                border: 1px solid #1E2333;
                border-bottom: none;
                color: #8E98B0;
                padding: 7px 16px;
                margin-right: 4px;
                border-top-left-radius: 6px;
                border-top-right-radius: 6px;
                font-size: 12px;
                font-weight: 500;
            }
            QTabBar::tab:hover {
                color: #E2E8F0;
                background-color: #161A25;
            }
            QTabBar::tab:selected {
                background: #12151E;
                color: #00E5FF;
                font-weight: bold;
                border-top: 2px solid #00E5FF;
            }

            /* --- 卡片容器 --- */
            QFrame.compact_card {
                background-color: #151823;
                border: 1px solid #202638;
                border-radius: 8px;
                padding: 8px 10px;
            }

            /* --- 滑块紧凑电竞槽 --- */
            QSlider::groove:horizontal {
                height: 5px;
                background: #23283B;
                border-radius: 2px;
            }
            QSlider::sub-page:horizontal {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #0284C7, stop:1 #00E5FF);
                border-radius: 2px;
            }
            QSlider::handle:horizontal {
                background: #FFFFFF;
                border: 2px solid #00E5FF;
                width: 14px;
                margin-top: -5px;
                margin-bottom: -5px;
                border-radius: 7px;
            }
            QSlider::handle:horizontal:hover {
                background: #00E5FF;
                border: 2px solid #FFFFFF;
            }

            /* --- 复选框 --- */
            QCheckBox {
                spacing: 8px;
                color: #F8FAFC;
                font-weight: 600;
                font-size: 13px;
            }
            QCheckBox::indicator {
                width: 17px;
                height: 17px;
                border-radius: 4px;
                border: 1px solid #333C54;
                background: #1A1E2B;
            }
            QCheckBox::indicator:hover {
                border: 1px solid #00E5FF;
            }
            QCheckBox::indicator:checked {
                background: #00E5FF;
                border: 1px solid #00E5FF;
            }

            /* --- 按钮 --- */
            QPushButton {
                background-color: #1C2130;
                color: #E2E8F0;
                border: 1px solid #283044;
                border-radius: 5px;
                padding: 5px 12px;
                font-size: 12px;
                font-weight: 500;
            }
            QPushButton:hover {
                background-color: #242B3E;
                border-color: #3B4664;
                color: #FFFFFF;
            }
            QPushButton:pressed {
                background-color: #171B26;
            }
            QPushButton#btn_danger {
                background-color: #241416;
                color: #F87171;
                border: 1px solid #4D1E22;
            }
            QPushButton#btn_danger:hover {
                background-color: #351A1D;
                color: #FCA5A5;
                border-color: #EF4444;
            }

            /* --- 下拉框 --- */
            QComboBox {
                background: #171B26;
                border: 1px solid #293043;
                border-radius: 5px;
                padding: 4px 10px;
                color: #F1F5F9;
                font-size: 12px;
            }
            QComboBox:hover {
                border: 1px solid #00E5FF;
            }
            QComboBox::drop-down {
                border: none;
                width: 18px;
            }
            QComboBox QAbstractItemView {
                background-color: #171B26;
                border: 1px solid #293043;
                color: #F1F5F9;
                selection-background-color: #0284C7;
                selection-color: #FFFFFF;
                border-radius: 4px;
                padding: 2px;
            }

            /* --- 进度条 --- */
            QProgressBar {
                border: 1px solid #202637;
                border-radius: 4px;
                text-align: center;
                background: #0B0D13;
                color: #FFFFFF;
                font-weight: bold;
                font-size: 11px;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #0284C7, stop:1 #00E5FF);
                border-radius: 3px;
            }
        """)

    def _init_ui(self):
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(12, 12, 12, 12)
        root_layout.setSpacing(8)

        # 1. 紧凑 Header
        root_layout.addWidget(self._create_compact_header())

        # 2. 紧凑预设选择栏
        root_layout.addWidget(self._create_compact_presets())

        # 3. 游戏设置注意事项提示条
        root_layout.addWidget(self._create_compact_notice())

        # 4. 紧凑 Tab 选项卡
        self.tabs = QTabWidget()
        self.tabs.addTab(self._create_vignette_tab(), "🌀 动态暗角")
        self.tabs.addTab(self._create_anchors_tab(), "⚓ 边缘锚点")
        self.tabs.addTab(self._create_reference_columns_tab(), "固定细柱")
        self.tabs.addTab(self._create_reticle_tab(), "🎯 中心准星")
        self.tabs.addTab(self._create_system_tab(), "⚙️ 系统与屏幕")
        from ui.optional_panel import OptionalPanel
        self.optional_panel = OptionalPanel(self, self.library, self.extension_controller)
        self.tabs.addTab(self.optional_panel, "可选扩展")
        root_layout.addWidget(self.tabs, stretch=1)

        # 5. 常驻底部遥测监控栏
        root_layout.addWidget(self._create_compact_footer())

    # =========================================================================
    # 顶部与公共紧凑组件
    # =========================================================================

    def _create_compact_header(self) -> QWidget:
        """紧凑 Header"""
        frame = QFrame()
        frame.setStyleSheet("""
            QFrame {
                background-color: #131620;
                border: 1px solid #1E2333;
                border-radius: 8px;
                padding: 6px 10px;
            }
        """)
        layout = QHBoxLayout(frame)
        layout.setContentsMargins(4, 2, 4, 2)
        layout.setSpacing(8)

        # 标题
        lbl_title = QLabel("🛡️ Care3D Pro")
        lbl_title.setStyleSheet("font-size: 16px; font-weight: bold; color: #00E5FF;")
        layout.addWidget(lbl_title)

        badge_pubg = QLabel("游戏舒适辅助")
        badge_pubg.setStyleSheet("""
            background-color: #0369A1;
            color: #FFFFFF;
            font-size: 10px;
            font-weight: bold;
            padding: 2px 6px;
            border-radius: 3px;
        """)
        layout.addWidget(badge_pubg)

        lbl_desc = QLabel("缓解效果因人而异")
        lbl_desc.setStyleSheet("color: #717D96; font-size: 11px;")
        layout.addWidget(lbl_desc)

        layout.addStretch()

        # 主开关胶囊按钮
        self.btn_main_power = QPushButton("● 抗晕运行中 (点击暂停)")
        self.btn_main_power.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_main_power.setStyleSheet("""
            QPushButton {
                background-color: #064E3B;
                color: #34D399;
                border: 1px solid #059669;
                font-size: 12px;
                font-weight: bold;
                padding: 5px 14px;
                border-radius: 14px;
            }
            QPushButton:hover {
                background-color: #047857;
                color: #FFFFFF;
            }
        """)
        self.btn_main_power.clicked.connect(self._on_toggle_overlay_clicked)
        layout.addWidget(self.btn_main_power)

        return frame

    def _create_compact_presets(self) -> QWidget:
        """Persistent profiles: selecting a button never resets its saved values."""
        container = QWidget()
        outer = QVBoxLayout(container)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(5)
        layout = QHBoxLayout()
        outer.addLayout(layout)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        self.btn_pre_custom = QPushButton("我的设置")
        self.btn_pre_custom.setToolTip("保留升级前的参数；每个方案中的修改都会独立自动保存。")
        self.btn_pre_custom.clicked.connect(lambda: self._apply_preset("custom"))
        layout.addWidget(self.btn_pre_custom)

        self.btn_pre_pubg = QPushButton("平衡遮挡")
        self.btn_pre_pubg.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_pre_pubg.setToolTip("恢复平衡方案上次保存的参数；再次点击也不会重置。")
        self.btn_pre_pubg.setStyleSheet("""
            QPushButton {
                background-color: #122538;
                border: 1px solid #0284C7;
                border-radius: 6px;
                padding: 7px 6px;
                font-size: 11px;
                font-weight: bold;
                color: #38BDF8;
            }
            QPushButton:hover {
                border-color: #00E5FF;
                background-color: #18334E;
            }
        """)
        self.btn_pre_pubg.clicked.connect(self._apply_pubg_preset)
        layout.addWidget(self.btn_pre_pubg)

        self.btn_pre_light = QPushButton("轻度遮挡")
        self.btn_pre_light.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_pre_light.setToolTip("恢复轻度方案上次保存的参数；每个方案独立保存。")
        self.btn_pre_light.setStyleSheet("""
            QPushButton {
                background-color: #141722;
                border: 1px solid #202638;
                border-radius: 6px;
                padding: 7px 6px;
                font-size: 11px;
                font-weight: 500;
                color: #CBD5E1;
            }
            QPushButton:hover {
                border-color: #10B981;
                color: #6EE7B7;
            }
        """)
        self.btn_pre_light.clicked.connect(self._apply_light_preset)
        layout.addWidget(self.btn_pre_light)

        self.btn_pre_heavy = QPushButton("加强遮挡")
        self.btn_pre_heavy.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_pre_heavy.setToolTip("恢复加强方案上次保存的参数；会减少周边可见范围，效果因人而异。")
        self.btn_pre_heavy.setStyleSheet("""
            QPushButton {
                background-color: #141722;
                border: 1px solid #202638;
                border-radius: 6px;
                padding: 7px 6px;
                font-size: 11px;
                font-weight: 500;
                color: #CBD5E1;
            }
            QPushButton:hover {
                border-color: #F59E0B;
                color: #FCD34D;
            }
        """)
        self.btn_pre_heavy.clicked.connect(self._apply_heavy_preset)
        layout.addWidget(self.btn_pre_heavy)

        status_row = QHBoxLayout()
        self.lbl_profile_status = QLabel()
        self.lbl_profile_status.setTextFormat(Qt.TextFormat.PlainText)
        self.lbl_profile_status.setStyleSheet("color: #94A3B8; font-size: 11px;")
        status_row.addWidget(self.lbl_profile_status, 1)
        save_button = QPushButton("保存当前方案")
        save_button.clicked.connect(self._save_config)
        status_row.addWidget(save_button)
        reset_button = QPushButton("重置当前方案")
        reset_button.clicked.connect(self._on_reset_current_profile)
        status_row.addWidget(reset_button)
        outer.addLayout(status_row)

        return container

    def _create_compact_notice(self) -> QWidget:
        """PUBG 游戏模式提醒与置顶按钮"""
        frame = QFrame()
        frame.setStyleSheet("""
            QFrame {
                background-color: #1A1811;
                border: 1px solid #483912;
                border-radius: 6px;
                padding: 4px 8px;
            }
        """)
        layout = QHBoxLayout(frame)
        layout.setContentsMargins(4, 2, 4, 2)
        layout.setSpacing(8)

        lbl_text = QLabel("游戏请使用<b>无边框或窗口模式</b>；Ctrl+Alt+H 随时开启或暂停。")
        self.lbl_shortcut_notice = lbl_text
        lbl_text.setWordWrap(True)
        lbl_text.setStyleSheet("color: #FDE047; font-size: 11px;")
        layout.addWidget(lbl_text, stretch=1)

        btn_retop = QPushButton("🛠️ 重新置顶")
        btn_retop.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_retop.setToolTip("切屏后若悬浮窗被游戏遮挡，点击此按钮立即拉回最上层")
        btn_retop.setStyleSheet("""
            QPushButton {
                background-color: #2A2414;
                color: #FDE047;
                border: 1px solid #634C15;
                padding: 2px 8px;
                font-size: 11px;
                border-radius: 3px;
            }
            QPushButton:hover {
                background-color: #3F351B;
                border-color: #FDE047;
            }
        """)
        btn_retop.clicked.connect(self._on_retop_clicked)
        layout.addWidget(btn_retop)

        return frame

    # =========================================================================
    # 各 Tab 页面 (紧凑型卡片内联排布，参数间距缩小紧挨)
    # =========================================================================

    def _create_vignette_tab(self) -> QWidget:
        """动态暗角紧凑参数页"""
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        # 单一卡片承载所有参数，不再多层嵌套
        card = QFrame()
        card.setProperty("class", "compact_card")
        c_layout = QVBoxLayout(card)
        c_layout.setContentsMargins(10, 8, 10, 8)
        c_layout.setSpacing(6)  # 参数之间紧凑紧挨着 (6px)

        # 总开关行
        top_row = QHBoxLayout()
        self.chk_vignette = MarkedCheckBox("启用动态暗角视场收缩 (Dynamic Tunneling)")
        self.chk_vignette.toggled.connect(self._on_setting_changed)
        top_row.addWidget(self.chk_vignette)
        top_row.addStretch()
        c_layout.addLayout(top_row)

        desc = QLabel("常驻轻度暗角覆盖无鼠标输入的运动场景；转向时再平滑加深并收缩清晰区。")
        desc.setWordWrap(True)
        desc.setStyleSheet("color: #717D96; font-size: 11px; margin-bottom: 4px;")
        c_layout.addWidget(desc)

        # 分割微线
        sep = QFrame()
        sep.setFixedHeight(1)
        sep.setStyleSheet("background-color: #1F2536;")
        c_layout.addWidget(sep)

        # 紧凑单行参数列表 (紧挨着)
        self.slider_vig_alpha, self.badge_vig_alpha = self._create_compact_slider_row(
            c_layout, "最大暗角强度", "视角剧烈旋转时的最大遮罩深度。推荐 60%~75%。",
            0, 95, 65, "%"
        )
        self.slider_vig_sens, self.badge_vig_sens = self._create_compact_slider_row(
            c_layout, "触发灵敏度", "达到该转速时暗角达到最大上限。数值越低越容易触发。",
            200, 20000, 2200, " 单位/s"
        )
        self.slider_vig_thresh, self.badge_vig_thresh = self._create_compact_slider_row(
            c_layout, "瞄准死区门限", "低于此输入速度不增强动态遮挡，常驻暗角仍保留。",
            0, 5000, 250, " 单位/s"
        )
        self.slider_vig_inner, self.badge_vig_inner = self._create_compact_slider_row(
            c_layout, "静止清晰区半径", "椭圆半轴相对游戏窗口宽高的比例；转向时可进一步收缩。",
            35, 85, 55, "%"
        )
        self.slider_vig_decay, self.badge_vig_decay = self._create_compact_slider_row(
            c_layout, "淡出恢复时间", "鼠标停止晃动后暗角平滑消退的时间。推荐 0.35s~0.5s，呈现呼吸感。",
            15, 150, 55, " x10ms"
        )

        self.slider_vig_idle, self.badge_vig_idle = self._create_compact_slider_row(
            c_layout, "常驻暗角强度", "无鼠标输入时仍保留遮挡，可用于载具、行走和过场；0 表示关闭常驻暗角。",
            0, 40, 12, "%")
        self.slider_vig_contract, self.badge_vig_contract = self._create_compact_slider_row(
            c_layout, "转向清晰区收缩", "运动时缩小透明椭圆的半轴，0 表示仅改变暗角深浅。",
            0, 25, 12, "%")
        self.slider_mouse_gain, self.badge_mouse_gain = self._create_compact_slider_row(
            c_layout, "输入响应倍率", "高 DPI 可降低倍率，低 DPI 可提高；此数值不改变游戏内鼠标灵敏度。",
            25, 400, 100, "%")

        layout.addWidget(card)
        layout.addStretch()
        scroll.setWidget(content)
        return scroll

    def _create_anchors_tab(self) -> QWidget:
        """边缘视觉锚点紧凑参数页"""
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        card = QFrame()
        card.setProperty("class", "compact_card")
        c_layout = QVBoxLayout(card)
        c_layout.setContentsMargins(10, 8, 10, 8)
        c_layout.setSpacing(6)

        # 总开关
        self.chk_anchors = MarkedCheckBox("启用屏幕边缘视觉锚点阵列 (Visual Frame)")
        self.chk_anchors.toggled.connect(self._on_setting_changed)
        c_layout.addWidget(self.chk_anchors)

        desc = QLabel("可选的固定视觉参照。保持低亮度，避免吸引注意；效果需要个人体验验证。")
        desc.setWordWrap(True)
        desc.setStyleSheet("color: #717D96; font-size: 11px; margin-bottom: 4px;")
        c_layout.addWidget(desc)

        sep = QFrame()
        sep.setFixedHeight(1)
        sep.setStyleSheet("background-color: #1F2536;")
        c_layout.addWidget(sep)

        # 紧凑参数
        self.slider_anc_radius, self.badge_anc_radius = self._create_compact_slider_row(
            c_layout, "锚点圆点大小", "边缘参照小圆点的半径尺寸 (像素)。", 2, 10, 4, " px"
        )
        self.slider_anc_rows, self.badge_anc_rows = self._create_compact_slider_row(
            c_layout, "左右两侧数量", "屏幕左右两侧的垂直点阵数量。", 3, 9, 5, " 个"
        )
        self.slider_anc_cols, self.badge_anc_cols = self._create_compact_slider_row(
            c_layout, "上下两侧数量", "屏幕上下边框的水平点阵数量 (避开正中央)。", 3, 11, 7, " 个"
        )
        self.slider_anc_idle_alpha, self.badge_anc_idle_alpha = self._create_compact_slider_row(
            c_layout, "静止基础透明度", "平时画面不动时的基础可见度，极低不干扰视野。", 0, 40, 12, "%"
        )
        self.slider_anc_boost_alpha, self.badge_anc_boost_alpha = self._create_compact_slider_row(
            c_layout, "甩枪增强透明度", "高速甩枪转头时自动变亮，强化稳定坐标感。", 20, 100, 70, "%"
        )

        # 颜色与发光控制行
        col_row = QHBoxLayout()
        col_row.setContentsMargins(2, 4, 2, 2)
        lbl_c = QLabel("锚点颜色 & 外发光：")
        lbl_c.setFixedWidth(135)
        lbl_c.setStyleSheet("font-size: 12px; font-weight: 600; color: #E2E8F0;")
        col_row.addWidget(lbl_c)

        self.btn_anc_color = QPushButton("🎨 选色")
        self.btn_anc_color.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_anc_color.clicked.connect(self._pick_anchor_color)
        col_row.addWidget(self.btn_anc_color)

        self.anc_color_preview = QFrame()
        self.anc_color_preview.setFixedSize(26, 18)
        self.anc_color_preview.setStyleSheet("border-radius: 3px; border: 1px solid #475569;")
        col_row.addWidget(self.anc_color_preview)

        col_row.addSpacing(16)
        self.chk_anc_glow = MarkedCheckBox("柔和外发光")
        self.chk_anc_glow.toggled.connect(self._on_setting_changed)
        col_row.addWidget(self.chk_anc_glow)
        col_row.addStretch()
        c_layout.addLayout(col_row)

        self.chk_edge_triangles = MarkedCheckBox("启用四边固定小三角形")
        self.chk_edge_triangles.setToolTip("在上下左右边缘中点各显示一个朝向中心的小三角形，位置和亮度固定；可独立于圆点锚点开启。")
        self.chk_edge_triangles.toggled.connect(self._on_setting_changed)
        c_layout.addWidget(self.chk_edge_triangles)
        triangle_hint = QLabel("四边各一个，固定不动、不会随转向闪动；此选项随当前方案保存。")
        triangle_hint.setWordWrap(True)
        triangle_hint.setStyleSheet("color: #717D96; font-size: 11px;")
        c_layout.addWidget(triangle_hint)

        self.slider_edge_triangles_size, self.badge_edge_triangles_size = self._create_compact_slider_row(
            c_layout, "三角形大小", "三角形底边长度，随系统显示缩放；四边统一调整。",
            6, 64, 16, " px")
        triangle_color_row = QHBoxLayout()
        triangle_color_label = QLabel("三角形颜色：")
        triangle_color_label.setFixedWidth(135)
        triangle_color_row.addWidget(triangle_color_label)
        self.btn_edge_triangles_color = QPushButton("选择颜色")
        self.btn_edge_triangles_color.clicked.connect(self._pick_edge_triangles_color)
        triangle_color_row.addWidget(self.btn_edge_triangles_color)
        self.edge_triangles_color_preview = QFrame()
        self.edge_triangles_color_preview.setFixedSize(26, 18)
        triangle_color_row.addWidget(self.edge_triangles_color_preview)
        triangle_color_row.addStretch()
        c_layout.addLayout(triangle_color_row)

        layout.addWidget(card)
        layout.addStretch()
        scroll.setWidget(content)
        return scroll

    def _create_reference_columns_tab(self) -> QWidget:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(10, 10, 10, 10)
        card = QFrame()
        card.setProperty("class", "compact_card")
        controls = QVBoxLayout(card)
        controls.setContentsMargins(10, 8, 10, 8)
        controls.setSpacing(6)
        self.chk_reference_columns = MarkedCheckBox("启用四根固定细柱")
        self.chk_reference_columns.toggled.connect(self._on_setting_changed)
        controls.addWidget(self.chk_reference_columns)
        hint = QLabel("横向均分四个区域，每区中央一根细柱。位置和亮度固定，不随视角转动；默认较细、较淡。")
        hint.setWordWrap(True)
        hint.setStyleSheet("color: #94A3B8; font-size: 11px;")
        controls.addWidget(hint)
        self.slider_reference_columns_width, self.badge_reference_columns_width = self._create_compact_slider_row(
            controls, "柱子宽度", "四根柱子统一调整宽度；建议先从 1–3 像素开始，减少画面遮挡。",
            1, 12, 2, " px")
        self.slider_reference_columns_height, self.badge_reference_columns_height = self._create_compact_slider_row(
            controls, "柱子高度", "占覆盖区域高度的比例，上下居中。", 10, 100, 60, "%")
        self.slider_reference_columns_alpha, self.badge_reference_columns_alpha = self._create_compact_slider_row(
            controls, "柱子可见度", "数值越低越透明；保持较淡可减少对游戏画面的遮挡。", 5, 80, 25, "%")
        color_row = QHBoxLayout()
        color_label = QLabel("柱子颜色：")
        color_label.setFixedWidth(135)
        color_row.addWidget(color_label)
        self.btn_reference_columns_color = QPushButton("选择颜色")
        self.btn_reference_columns_color.clicked.connect(self._pick_reference_columns_color)
        color_row.addWidget(self.btn_reference_columns_color)
        self.reference_columns_color_preview = QFrame()
        self.reference_columns_color_preview.setFixedSize(26, 18)
        color_row.addWidget(self.reference_columns_color_preview)
        color_row.addStretch()
        controls.addLayout(color_row)
        saved_hint = QLabel("本页选项随当前方案保存。绑定游戏窗口时，四根细柱按游戏客户区均分。")
        saved_hint.setWordWrap(True)
        saved_hint.setStyleSheet("color: #717D96; font-size: 11px;")
        controls.addWidget(saved_hint)
        layout.addWidget(card)
        layout.addStretch()
        scroll.setWidget(content)
        return scroll

    def _create_reticle_tab(self) -> QWidget:
        """中心准星定焦点紧凑参数页"""
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        card = QFrame()
        card.setProperty("class", "compact_card")
        c_layout = QVBoxLayout(card)
        c_layout.setContentsMargins(10, 8, 10, 8)
        c_layout.setSpacing(6)

        self.chk_center_dot = MarkedCheckBox("启用屏幕中心固定定焦参考点")
        self.chk_center_dot.toggled.connect(self._on_setting_changed)
        c_layout.addWidget(self.chk_center_dot)

        desc = QLabel("可选中心参考点，默认关闭；游戏已有准星时通常无需叠加。")
        desc.setStyleSheet("color: #717D96; font-size: 11px; margin-bottom: 4px;")
        c_layout.addWidget(desc)

        sep = QFrame()
        sep.setFixedHeight(1)
        sep.setStyleSheet("background-color: #1F2536;")
        c_layout.addWidget(sep)

        # 样式与颜色行
        style_row = QHBoxLayout()
        style_row.setContentsMargins(2, 4, 2, 2)
        lbl_s = QLabel("准星样式 & 颜色：")
        lbl_s.setFixedWidth(135)
        lbl_s.setStyleSheet("font-size: 12px; font-weight: 600; color: #E2E8F0;")
        style_row.addWidget(lbl_s)

        self.cmb_center_style = NoWheelComboBox()
        self.cmb_center_style.addItem("定焦微点 (Dot)", "dot")
        self.cmb_center_style.addItem("战术细十字 (Cross)", "cross")
        self.cmb_center_style.currentIndexChanged.connect(self._on_setting_changed)
        style_row.addWidget(self.cmb_center_style)

        style_row.addSpacing(10)
        self.btn_center_color = QPushButton("🎨 选色")
        self.btn_center_color.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_center_color.clicked.connect(self._pick_center_color)
        style_row.addWidget(self.btn_center_color)

        self.center_color_preview = QFrame()
        self.center_color_preview.setFixedSize(26, 18)
        self.center_color_preview.setStyleSheet("border-radius: 3px; border: 1px solid #475569;")
        style_row.addWidget(self.center_color_preview)
        style_row.addStretch()
        c_layout.addLayout(style_row)

        self.slider_center_radius, self.badge_center_radius = self._create_compact_slider_row(
            c_layout, "中心点/十字大小", "中心参照物半径，推荐 2px~3px 极细微点，不遮挡敌人。", 1, 8, 2, " px"
        )
        self.slider_center_alpha, self.badge_center_alpha = self._create_compact_slider_row(
            c_layout, "中心点不透明度", "中心参照物的清晰度。", 20, 100, 80, "%"
        )

        layout.addWidget(card)
        layout.addStretch()
        scroll.setWidget(content)
        return scroll

    def _create_system_tab(self) -> QWidget:
        """系统与快捷键页"""
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        card = QFrame()
        card.setProperty("class", "compact_card")
        c_layout = QVBoxLayout(card)
        c_layout.setContentsMargins(10, 8, 10, 8)
        c_layout.setSpacing(8)

        # 屏幕绑定行
        scr_row = QHBoxLayout()
        lbl_scr = QLabel("覆盖层作用屏幕：")
        lbl_scr.setFixedWidth(135)
        lbl_scr.setStyleSheet("font-size: 12px; font-weight: 600; color: #E2E8F0;")
        scr_row.addWidget(lbl_scr)

        self.cmb_screen = NoWheelComboBox()
        screens = QApplication.screens()
        for i, scr in enumerate(screens):
            geom = scr.geometry()
            name = f"显示器 {i+1} ({geom.width()}x{geom.height()})"
            if scr == QApplication.primaryScreen():
                name += " [主屏]"
            self.cmb_screen.addItem(name, i)
        self.cmb_screen.currentIndexChanged.connect(self._on_screen_selected)
        scr_row.addWidget(self.cmb_screen, stretch=1)
        c_layout.addLayout(scr_row)

        # 快捷键行
        key_row = QHBoxLayout()
        lbl_k = QLabel("游戏内全局快捷键：")
        lbl_k.setFixedWidth(135)
        lbl_k.setStyleSheet("font-size: 12px; font-weight: 600; color: #E2E8F0;")
        key_row.addWidget(lbl_k)

        badge_key = QLabel("Ctrl + Alt + H")
        self.badge_main_shortcut = badge_key
        badge_key.setStyleSheet("""
            background-color: #0369A1;
            color: #FFFFFF;
            font-size: 12px;
            font-weight: bold;
            padding: 2px 10px;
            border-radius: 4px;
        """)
        key_row.addWidget(badge_key)
        key_row.addStretch()
        c_layout.addLayout(key_row)

        self.chk_gamepad = MarkedCheckBox("手柄右摇杆动态增强（XInput）")
        self.chk_gamepad.setToolTip("支持原生 XInput 或 Steam Input 的 XInput 输出；其他模式可使用常驻暗角。")
        self.chk_gamepad.toggled.connect(self._on_setting_changed)
        c_layout.addWidget(self.chk_gamepad)
        self.slider_fps, self.badge_fps = self._create_compact_slider_row(
            c_layout, "动态刷新上限", "静止时停止动画定时器；提高上限会增加绘制开销。", 20, 120, 60, " FPS")
        self.chk_target_only = MarkedCheckBox("仅在选定游戏位于前台时显示，并跟随其窗口")
        self.chk_target_only.toggled.connect(self._on_setting_changed)
        c_layout.addWidget(self.chk_target_only)
        target_row = QHBoxLayout()
        self.cmb_target = NoWheelComboBox()
        self.cmb_target.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
        self.cmb_target.setMinimumContentsLength(20)
        self.cmb_target.currentIndexChanged.connect(self._on_target_selected)
        target_row.addWidget(self.cmb_target, 1)
        refresh = QPushButton("刷新窗口")
        refresh.clicked.connect(self._refresh_targets)
        target_row.addWidget(refresh)
        c_layout.addLayout(target_row)
        target_hint = QLabel("先启动游戏，再刷新并选择窗口。切到桌面自动隐藏。独占全屏请改为无边框。")
        target_hint.setWordWrap(True)
        c_layout.addWidget(target_hint)
        self.lbl_input_source = QLabel("输入检测：尚未启动")
        self.lbl_input_source.setWordWrap(True)
        c_layout.addWidget(self.lbl_input_source)
        self._refresh_targets()

        # 安全声明
        sep = QFrame()
        sep.setFixedHeight(1)
        sep.setStyleSheet("background-color: #1F2536;")
        c_layout.addWidget(sep)

        sec_desc = QLabel(
            "• 独立透明窗口，不读写游戏内存、不注入游戏、不模拟按键；请遵守各游戏规则。<br>"
            "• 静止时暂停动画绘制，仍保留输入监听与窗口检查；性能以实际游戏测试为准。<br>"
            "• 本工具尝试减少视觉刺激，不保证缓解症状；出现恶心或头晕应停止游戏并休息。"
        )
        sec_desc.setWordWrap(True)
        sec_desc.setStyleSheet("color: #8E98B0; font-size: 11px; line-height: 1.5;")
        c_layout.addWidget(sec_desc)

        btn_reset = QPushButton("重置所有方案与系统设置")
        btn_reset.setObjectName("btn_danger")
        btn_reset.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_reset.clicked.connect(self._on_reset_defaults_clicked)
        c_layout.addWidget(btn_reset)

        layout.addWidget(card)
        layout.addStretch()
        scroll.setWidget(content)
        return scroll

    def _create_compact_footer(self) -> QWidget:
        """常驻底部的紧凑遥测监控栏"""
        footer = QFrame()
        footer.setStyleSheet("""
            QFrame {
                background-color: #131620;
                border: 1px solid #1E2333;
                border-radius: 6px;
                padding: 6px 10px;
            }
        """)
        layout = QHBoxLayout(footer)
        layout.setContentsMargins(4, 2, 4, 2)
        layout.setSpacing(10)

        layout.addWidget(QLabel("鼠标速率："))
        self.bar_speed = QProgressBar()
        self.bar_speed.setRange(0, 20000)
        self.bar_speed.setValue(0)
        self.bar_speed.setFixedWidth(120)
        self.bar_speed.setFixedHeight(14)
        self.bar_speed.setTextVisible(True)
        self.bar_speed.setFormat("%v 单位/s")
        layout.addWidget(self.bar_speed)

        self.lbl_vignette_status = QLabel("暗角：静止")
        self.lbl_vignette_status.setStyleSheet("color: #717D96; font-size: 11px;")
        layout.addWidget(self.lbl_vignette_status)

        layout.addStretch()

        self.lbl_sleep_status = QLabel("等待渲染状态")
        self.lbl_sleep_status.setStyleSheet("color: #34D399; font-weight: bold; font-size: 11px;")
        layout.addWidget(self.lbl_sleep_status)

        return footer

    # =========================================================================
    # 核心紧凑单行构造器 (标题 + 全宽滑块 + 数值Badge，紧凑不留白)
    # =========================================================================

    def _create_compact_slider_row(self, parent_layout, title: str, tooltip: str, min_val: int, max_val: int, default_val: int, suffix: str):
        """
        单行紧凑排版：
        左侧：参数名称 (定宽 135px，带悬浮 Tooltip 解释)
        中间：全宽防滚轮误触滑块 NoWheelSlider
        右侧：紧凑微光数值 Badge (定宽 60px)
        参数之间高度极低，彻底杜绝空旷感
        """
        row_widget = QWidget()
        row_layout = QHBoxLayout(row_widget)
        row_layout.setContentsMargins(0, 1, 0, 1)
        row_layout.setSpacing(8)

        # 1. 标题
        lbl_title = QLabel(title)
        lbl_title.setFixedWidth(135)
        lbl_title.setStyleSheet("font-size: 12px; font-weight: 600; color: #E2E8F0;")
        if tooltip:
            lbl_title.setToolTip(tooltip)
        row_layout.addWidget(lbl_title)

        # 2. 防滚轮误触滑块
        slider = NoWheelSlider(Qt.Orientation.Horizontal)
        slider.setRange(min_val, max_val)
        slider.setValue(default_val)
        if tooltip:
            slider.setToolTip(tooltip)
        row_layout.addWidget(slider, stretch=1)

        # 3. 紧凑数值 Badge
        def edit_value():
            if not self.cfg_mgr.config.accessibility_enabled:
                return
            value, ok = QInputDialog.getInt(self, title, f"输入数值（{suffix.strip() or '整数'}）", slider.value(), min_val, max_val)
            if ok:
                slider.setValue(value)
        badge_val = EditableValueLabel(f"{default_val}{suffix}", edit_value)
        badge_val.setToolTip("启用可选扩展中的界面辅助后，可双击或按 Enter 输入数值。")
        badge_val.setFixedWidth(104)
        badge_val.setAlignment(Qt.AlignmentFlag.AlignCenter)
        badge_val.setStyleSheet("""
            background-color: #171E2E;
            color: #00E5FF;
            font-size: 11px;
            font-weight: bold;
            padding: 2px 4px;
            border-radius: 4px;
            border: 1px solid #23314B;
        """)
        slider.valueChanged.connect(lambda v: badge_val.setText(f"{v}{suffix}"))
        slider.valueChanged.connect(self._on_setting_changed)
        row_layout.addWidget(badge_val)

        parent_layout.addWidget(row_widget)
        return slider, badge_val

    # =========================================================================
    # 数据加载与联动
    # =========================================================================

    def _load_values_to_ui(self):
        self._loading = True
        try:
            cfg = self.cfg_mgr.config

            # 动态暗角
            self.chk_vignette.setChecked(cfg.vignette_enabled)
            self.slider_vig_alpha.setValue(round(cfg.vignette_max_alpha * 100))
            self.slider_vig_sens.setValue(int(cfg.vignette_sensitivity))
            self.slider_vig_thresh.setValue(int(cfg.vignette_threshold))
            self.slider_vig_inner.setValue(round(cfg.vignette_inner_radius * 100))
            self.slider_vig_decay.setValue(round(cfg.vignette_decay_time * 100))

            # 边缘锚点
            self.chk_anchors.setChecked(cfg.anchors_enabled)
            self.slider_anc_radius.setValue(int(cfg.anchor_radius))
            self.slider_anc_rows.setValue(cfg.anchor_rows)
            self.slider_anc_cols.setValue(cfg.anchor_cols)
            self.slider_anc_idle_alpha.setValue(round(cfg.anchor_idle_alpha * 100))
            self.slider_anc_boost_alpha.setValue(round(cfg.anchor_boost_alpha * 100))
            self.chk_anc_glow.setChecked(cfg.anchor_glow)
            self.chk_edge_triangles.setChecked(cfg.edge_triangles_enabled)
            self.slider_edge_triangles_size.setValue(cfg.edge_triangles_size)
            self._update_color_preview(self.edge_triangles_color_preview, cfg.edge_triangles_color)
            self._update_color_preview(self.anc_color_preview, cfg.anchor_color)
            self.chk_reference_columns.setChecked(cfg.reference_columns_enabled)
            self.slider_reference_columns_width.setValue(cfg.reference_columns_width)
            self.slider_reference_columns_height.setValue(round(cfg.reference_columns_height_ratio * 100))
            self.slider_reference_columns_alpha.setValue(round(cfg.reference_columns_alpha * 100))
            self._update_color_preview(self.reference_columns_color_preview, cfg.reference_columns_color)

            # 中心固定参照点
            self.chk_center_dot.setChecked(cfg.center_dot_enabled)
            self.slider_center_radius.setValue(int(cfg.center_dot_radius))
            self.slider_center_alpha.setValue(round(cfg.center_dot_alpha * 100))
            idx = self.cmb_center_style.findData(cfg.center_dot_style)
            if idx >= 0:
                self.cmb_center_style.setCurrentIndex(idx)
            self._update_color_preview(self.center_color_preview, cfg.center_dot_color)

            # 系统设置
            scr_idx = self.cmb_screen.findData(cfg.selected_screen_index)
            if scr_idx >= 0:
                self.cmb_screen.setCurrentIndex(scr_idx)

            self.slider_vig_idle.setValue(round(cfg.vignette_idle_alpha * 100))
            self.slider_vig_contract.setValue(round(cfg.vignette_contraction * 100))
            self.slider_mouse_gain.setValue(round(cfg.mouse_gain * 100))
            self.chk_gamepad.setChecked(cfg.gamepad_enabled)
            self.slider_fps.setValue(cfg.fps_limit)
            self.chk_target_only.setChecked(cfg.only_target_window)
            self._refresh_targets()
            self.update_power_button_state(cfg.overlay_visible)
            self._update_profile_status("自动保存已开启")
            if hasattr(self, "optional_panel"):
                self.optional_panel.load()
            self._apply_accessibility()
            self._update_shortcut_labels()
        finally:
            self._loading = False

    def _optional_changed(self):
        self.save_timer.start()
        self._update_profile_status("正在保存…")
        self.cfg_mgr.notify_listeners()
        self._apply_accessibility()
        self._update_shortcut_labels()

    def _update_shortcut_labels(self):
        from core.hotkey_manager import valid_shortcut
        from ui.optional_panel import OptionalPanel
        cfg = self.cfg_mgr.config
        keys = (cfg.controls_toggle_key, cfg.controls_comfort_key, cfg.controls_profile_key)
        key = cfg.controls_toggle_key if cfg.controls_enabled and all(valid_shortcut(k) for k in keys) and len(set(keys)) == 3 else cfg.hotkey_toggle
        display = OptionalPanel.display_shortcut(key)
        self.badge_main_shortcut.setText(display)
        self.lbl_shortcut_notice.setText(f"游戏请使用<b>无边框或窗口模式</b>；{display} 随时开启或暂停。")

    def _apply_accessibility(self):
        cfg = self.cfg_mgr.config
        scale = cfg.font_scale / 100 if cfg.accessibility_enabled else 1.0
        widgets = [self, *self.findChildren(QWidget)]
        for widget in widgets:
            current = widget.styleSheet()
            if not hasattr(widget, "_care3d_base_style") or current != getattr(widget, "_care3d_scaled_style", None):
                widget._care3d_base_style = current
            base = widget._care3d_base_style
            scaled = re.sub(r"font-size:\s*(\d+)px", lambda match: f"font-size: {round(int(match[1]) * scale)}px", base)
            if current != scaled:
                widget.setStyleSheet(scaled)
            widget._care3d_scaled_style = scaled
            if not hasattr(widget, "_care3d_dimensions"):
                widget._care3d_dimensions = (widget.minimumWidth(), widget.maximumWidth(), widget.minimumHeight(), widget.maximumHeight())
            mw, xw, mh, xh = widget._care3d_dimensions
            # Enlarge fixed labels/badges as well as their fonts; preserve scrollable pages.
            if mw == xw and 0 < mw < 1000:
                widget.setFixedWidth(round(mw * scale))
            if mh == xh and 0 < mh < 200:
                widget.setFixedHeight(round(mh * scale))
            if isinstance(widget, EditableValueLabel):
                widget.setFocusPolicy(Qt.FocusPolicy.StrongFocus if cfg.accessibility_enabled else Qt.FocusPolicy.NoFocus)

    def _scale_dynamic_style(self, widget):
        # Called only after status code assigns a fresh, unscaled stylesheet.
        scale = self.cfg_mgr.config.font_scale / 100 if self.cfg_mgr.config.accessibility_enabled else 1.0
        base = widget.styleSheet()
        scaled = re.sub(r"font-size:\s*(\d+)px", lambda match: f"font-size: {round(int(match[1]) * scale)}px", base)
        widget._care3d_base_style = base
        widget._care3d_scaled_style = scaled
        if base != scaled:
            widget.setStyleSheet(scaled)

    def _on_setting_changed(self):
        if self._loading:
            return
        cfg = self.cfg_mgr.config

        cfg.vignette_enabled = self.chk_vignette.isChecked()
        cfg.vignette_max_alpha = self.slider_vig_alpha.value() / 100.0
        cfg.vignette_sensitivity = float(self.slider_vig_sens.value())
        cfg.vignette_threshold = float(self.slider_vig_thresh.value())
        cfg.vignette_inner_radius = self.slider_vig_inner.value() / 100.0
        cfg.vignette_decay_time = self.slider_vig_decay.value() / 100.0
        cfg.vignette_idle_alpha = min(self.slider_vig_idle.value() / 100.0, cfg.vignette_max_alpha)
        cfg.vignette_contraction = self.slider_vig_contract.value() / 100.0
        cfg.mouse_gain = self.slider_mouse_gain.value() / 100.0
        cfg.gamepad_enabled = self.chk_gamepad.isChecked()
        cfg.fps_limit = self.slider_fps.value()
        cfg.only_target_window = self.chk_target_only.isChecked()
        cfg.vignette_sensitivity = max(cfg.vignette_sensitivity, cfg.vignette_threshold + 100)

        cfg.anchors_enabled = self.chk_anchors.isChecked()
        cfg.anchor_radius = float(self.slider_anc_radius.value())
        cfg.anchor_rows = self.slider_anc_rows.value()
        cfg.anchor_cols = self.slider_anc_cols.value()
        cfg.anchor_idle_alpha = self.slider_anc_idle_alpha.value() / 100.0
        cfg.anchor_boost_alpha = self.slider_anc_boost_alpha.value() / 100.0
        cfg.anchor_glow = self.chk_anc_glow.isChecked()
        cfg.edge_triangles_enabled = self.chk_edge_triangles.isChecked()
        cfg.edge_triangles_size = self.slider_edge_triangles_size.value()
        cfg.reference_columns_enabled = self.chk_reference_columns.isChecked()
        cfg.reference_columns_width = self.slider_reference_columns_width.value()
        cfg.reference_columns_height_ratio = self.slider_reference_columns_height.value() / 100.0
        cfg.reference_columns_alpha = self.slider_reference_columns_alpha.value() / 100.0

        cfg.center_dot_enabled = self.chk_center_dot.isChecked()
        cfg.center_dot_radius = float(self.slider_center_radius.value())
        cfg.center_dot_alpha = self.slider_center_alpha.value() / 100.0
        cfg.center_dot_style = self.cmb_center_style.currentData() or "dot"

        self.save_timer.start()
        self._update_profile_status("正在保存…")
        self.cfg_mgr.notify_listeners()
        if self.slider_vig_idle.value() != round(cfg.vignette_idle_alpha * 100) or self.slider_vig_sens.value() != round(cfg.vignette_sensitivity):
            self._load_values_to_ui()

    def update_power_button_state(self, is_visible: bool):
        if is_visible:
            self.btn_main_power.setText("● 抗晕运行中 (点击暂停)")
            self.btn_main_power.setStyleSheet("""
                QPushButton {
                    background-color: #064E3B;
                    color: #34D399;
                    border: 1px solid #059669;
                    font-size: 12px;
                    font-weight: bold;
                    padding: 5px 14px;
                    border-radius: 14px;
                }
                QPushButton:hover {
                    background-color: #047857;
                    color: #FFFFFF;
                }
            """)
        else:
            self.btn_main_power.setText("○ 抗晕已暂停 (点击开启)")
            self.btn_main_power.setStyleSheet("""
                QPushButton {
                    background-color: #381216;
                    color: #F87171;
                    border: 1px solid #DC2626;
                    font-size: 12px;
                    font-weight: bold;
                    padding: 5px 14px;
                    border-radius: 14px;
                }
                QPushButton:hover {
                    background-color: #55191F;
                    color: #FFFFFF;
                }
            """)

        self._scale_dynamic_style(self.btn_main_power)

    def _apply_preset(self, name):
        # Live controls already updated the model, even if debounce hasn't fired.
        self.save_timer.stop()
        saved = self.cfg_mgr.switch_profile(name)
        self._load_values_to_ui()
        self._update_profile_status("已保存" if saved else "保存失败，请检查配置目录权限")

    def _update_profile_status(self, status):
        active = self.cfg_mgr.config.active_profile
        buttons = {"custom": self.btn_pre_custom, "balanced": self.btn_pre_pubg,
                   "light": self.btn_pre_light, "strong": self.btn_pre_heavy}
        for name, button in buttons.items():
            button.setText(("● " if name == active else "") + PROFILE_NAMES[name])
        entry = self.library.entries.get(self.library.active_id)
        prefix = entry["name"] + " / " if entry else ""
        self.lbl_profile_status.setText(f"当前：{prefix}{PROFILE_NAMES[active]} · {status}")
        self.lbl_profile_status.setToolTip(f"各方案独立记忆，切换不重置参数。\n{self.cfg_mgr.config_path}")

    def _save_config(self):
        self.save_timer.stop()
        saved = self.cfg_mgr.save()
        self._update_profile_status("已保存" if saved else "保存失败，请检查配置目录权限")
        return saved

    def _on_reset_current_profile(self):
        name = PROFILE_NAMES[self.cfg_mgr.config.active_profile]
        answer = QMessageBox.question(self, "重置当前方案",
            f"将【{name}】恢复为默认参数？其他方案中的参数会保留。",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No)
        if answer == QMessageBox.StandardButton.Yes:
            self.save_timer.stop()
            saved = self.cfg_mgr.reset_current_profile()
            self._load_values_to_ui()
            self._update_profile_status("已重置并保存" if saved else "保存失败，请检查配置目录权限")

    def _apply_pubg_preset(self):
        self._apply_preset("balanced")

    def _apply_light_preset(self):
        self._apply_preset("light")

    def _apply_heavy_preset(self):
        self._apply_preset("strong")

    def _refresh_targets(self):
        selected = self.cfg_mgr.config.target_window_title
        previous = self.cmb_target.blockSignals(True)
        try:
            self.cmb_target.clear()
            self.cmb_target.addItem("未选择游戏窗口", "")
            titles = sorted({title for _, title in list_target_windows()})
            if selected and selected not in titles:
                self.cmb_target.addItem(selected + "（尚未运行）", selected)
            for title in titles:
                self.cmb_target.addItem(title, title)
            index = self.cmb_target.findData(selected)
            self.cmb_target.setCurrentIndex(max(0, index))
        finally:
            self.cmb_target.blockSignals(previous)

    def _on_target_selected(self, index):
        if self._loading:
            return
        self.cfg_mgr.config.target_window_title = self.cmb_target.currentData() or ""
        self._on_setting_changed()

    def showEvent(self, event):
        super().showEvent(event)
        self.telemetry_timer.start()
        self._update_telemetry()

    def hideEvent(self, event):
        super().hideEvent(event)
        self.telemetry_timer.stop()

    def _pick_anchor_color(self):
        curr = QColor(self.cfg_mgr.config.anchor_color)
        col = QColorDialog.getColor(curr, self, "选择视觉锚点颜色")
        if col.isValid():
            hex_color = col.name()
            self.cfg_mgr.config.anchor_color = hex_color
            self._update_color_preview(self.anc_color_preview, hex_color)
            self._on_setting_changed()

    def _pick_edge_triangles_color(self):
        current = QColor(self.cfg_mgr.config.edge_triangles_color)
        color = QColorDialog.getColor(current, self, "选择四边三角形颜色")
        if color.isValid():
            self.cfg_mgr.config.edge_triangles_color = color.name()
            self._update_color_preview(self.edge_triangles_color_preview, color.name())
            self._on_setting_changed()

    def _pick_reference_columns_color(self):
        current = QColor(self.cfg_mgr.config.reference_columns_color)
        color = QColorDialog.getColor(current, self, "选择四根细柱颜色")
        if color.isValid():
            self.cfg_mgr.config.reference_columns_color = color.name()
            self._update_color_preview(self.reference_columns_color_preview, color.name())
            self._on_setting_changed()

    def _pick_center_color(self):
        curr = QColor(self.cfg_mgr.config.center_dot_color)
        col = QColorDialog.getColor(curr, self, "选择中心定焦点颜色")
        if col.isValid():
            hex_color = col.name()
            self.cfg_mgr.config.center_dot_color = hex_color
            self._update_color_preview(self.center_color_preview, hex_color)
            self._on_setting_changed()

    def _update_color_preview(self, frame: QFrame, hex_color: str):
        frame.setStyleSheet(f"background-color: {hex_color}; border-radius: 3px; border: 1px solid #475569;")

    def _on_screen_selected(self, index: int):
        if self._loading:
            return
        val = self.cmb_screen.currentData()
        if val is not None:
            self.cfg_mgr.config.selected_screen_index = int(val)
            self._on_setting_changed()

    def _on_retop_clicked(self):
        self.request_reapply_topmost.emit()
        QMessageBox.information(self, "已重新置顶", "已将覆盖层拉至 Windows 顶层！已恢复置顶悬浮状态。")

    def _on_toggle_overlay_clicked(self):
        self.request_toggle_overlay.emit()

    def _on_reset_defaults_clicked(self):
        res = QMessageBox.question(
            self, "重置所有方案与系统设置", "将通用四套方案与系统设置恢复默认。游戏方案库和本地体验记录会保留，可在可选扩展中单独删除。确定继续吗？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        if res == QMessageBox.StandardButton.Yes:
            if not self.cfg_mgr.reset_to_defaults():
                QMessageBox.warning(self, "保存失败", "无法保存重置结果，请检查配置目录权限。")
            self._load_values_to_ui()

    def _update_telemetry(self):
        if not self.isVisible():
            return

        self.lbl_input_source.setText(f"输入检测：{self.mouse_tracker.input_source}")
        self.lbl_input_source.setToolTip(f"配置文件：{self.cfg_mgr.config_path}")
        spd = self.mouse_tracker.smoothed_speed
        self.bar_speed.setValue(min(20000, max(0, int(spd))))
        if self.tabs.currentWidget() is self.optional_panel:
            self.optional_panel.refresh_runtime()

        if self.overlay_ref:
            self.lbl_sleep_status.setToolTip(self.overlay_ref.status_text)
            alpha = self.overlay_ref.current_vignette_alpha
            if alpha > 0.005:
                self.lbl_vignette_status.setText(f"暗角: {int(alpha * 100)}%")
                self.lbl_vignette_status.setStyleSheet("color: #00E5FF; font-weight: bold; font-size: 11px;")
            else:
                self.lbl_vignette_status.setText("暗角: 静止")
                self.lbl_vignette_status.setStyleSheet("color: #717D96; font-size: 11px;")
            self._scale_dynamic_style(self.lbl_vignette_status)

            if self.overlay_ref.is_sleeping:
                self.lbl_sleep_status.setText("静止 · 暂停重绘" if self.overlay_ref.isVisible() else self.overlay_ref.status_text)
                self.lbl_sleep_status.setStyleSheet("color: #34D399; font-weight: bold; font-size: 11px;")
            else:
                self.lbl_sleep_status.setText(f"动态 · 上限 {self.cfg_mgr.config.fps_limit} FPS")
                self.lbl_sleep_status.setStyleSheet("color: #38BDF8; font-weight: bold; font-size: 11px;")

    def closeEvent(self, event):
        self._save_config()
        event.ignore()
        self.hide()
