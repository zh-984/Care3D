"""
系统托盘管理模块 (tray_icon.py)
基于 QSystemTrayIcon 提供系统通知区托盘图标、右键菜单、以及气泡提醒。
"""

from PyQt6.QtWidgets import QSystemTrayIcon, QMenu
from PyQt6.QtGui import QIcon, QPixmap, QPainter, QColor, QBrush, QPen
from PyQt6.QtCore import Qt, pyqtSignal, QObject


class TrayIconManager(QObject):
    """
    Care3D 系统托盘管理器
    """
    action_show_settings = pyqtSignal()
    action_toggle_overlay = pyqtSignal()
    action_retop_overlay = pyqtSignal()
    action_exit = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.tray = QSystemTrayIcon(parent)
        self.icon = self._generate_tray_icon()
        self.tray.setIcon(self.icon)
        self.tray.setToolTip("Care3D - 3D 晕动症缓解辅助系统 (运行中)")

        self._init_menu()
        self.tray.activated.connect(self._on_tray_activated)

    def _generate_tray_icon(self) -> QIcon:
        """
        动态绘制高清防晕视网膜罗盘图标 (无需依赖外置静态资源图片，打包 100% 稳妥)
        """
        size = 64
        pixmap = QPixmap(size, size)
        pixmap.fill(Qt.GlobalColor.transparent)

        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        # 1. 外部科技暗黑圆形底板
        painter.setBrush(QBrush(QColor("#16171D")))
        painter.setPen(QPen(QColor("#00E5FF"), 3))
        painter.drawEllipse(4, 4, size - 8, size - 8)

        # 2. 内圈防晕护眼罗盘环
        painter.setPen(QPen(QColor("#38BDF8"), 2, Qt.PenStyle.DashLine))
        painter.drawEllipse(14, 14, size - 28, size - 28)

        # 3. 中心防晕聚焦点 (亮红色)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(QColor("#FF5252")))
        painter.drawEllipse(26, 26, 12, 12)

        painter.end()
        return QIcon(pixmap)

    def _init_menu(self):
        """初始化托盘右键菜单"""
        menu = QMenu()
        menu.setStyleSheet("""
            QMenu {
                background-color: #1E202B;
                color: #F8FAFC;
                border: 1px solid #334155;
                border-radius: 6px;
                padding: 4px;
            }
            QMenu::item {
                padding: 6px 24px;
                border-radius: 4px;
            }
            QMenu::item:selected {
                background-color: #2563EB;
                color: #FFFFFF;
            }
            QMenu::separator {
                height: 1px;
                background: #334155;
                margin: 4px 8px;
            }
        """)

        # 控制面板
        act_settings = menu.addAction("🛠️ 打开控制面板")
        act_settings.triggered.connect(self.action_show_settings.emit)

        # 覆盖层显隐切换
        act_toggle = menu.addAction("👁️ 切换覆盖层 (Ctrl+Alt+H)")
        act_toggle.triggered.connect(self.action_toggle_overlay.emit)

        # 重新置顶
        act_retop = menu.addAction("📌 重新置顶悬浮窗")
        act_retop.triggered.connect(self.action_retop_overlay.emit)

        menu.addSeparator()

        # 退出
        act_exit = menu.addAction("❌ 退出 Care3D")
        act_exit.triggered.connect(self.action_exit.emit)

        self.tray.setContextMenu(menu)

    def show(self):
        self.tray.show()

    def show_startup_message(self):
        """显示启动提示气泡"""
        if self.tray.supportsMessages():
            self.tray.showMessage(
                "Care3D 已就绪",
                "抗晕动辅助已在后台守护。\n快捷键: Ctrl + Alt + H 可随时切换显示/隐藏。",
                QSystemTrayIcon.MessageIcon.Information,
                3000
            )

    def _on_tray_activated(self, reason: QSystemTrayIcon.ActivationReason):
        """左键单击或双击托盘图标，打开控制面板"""
        if reason in (QSystemTrayIcon.ActivationReason.Trigger, QSystemTrayIcon.ActivationReason.DoubleClick):
            self.action_show_settings.emit()
