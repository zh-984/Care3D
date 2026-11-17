"""
系统托盘管理模块 (tray_icon.py)
基于 QSystemTrayIcon 提供系统通知区托盘图标、右键菜单、以及气泡提醒。
"""

from PyQt6.QtWidgets import QSystemTrayIcon, QMenu
from PyQt6.QtGui import QIcon
from PyQt6.QtCore import Qt, pyqtSignal, QObject
from ui.product_icons import app_icon, icon as product_icon
from ui.theme import STYLESHEET


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
        self.tray.setToolTip("Care3D · 游戏视觉舒适辅助")

        self._init_menu()
        self.tray.activated.connect(self._on_tray_activated)

    def _generate_tray_icon(self) -> QIcon:
        return app_icon()

    def _init_menu(self):
        """初始化托盘右键菜单"""
        menu = QMenu()
        menu.setStyleSheet(STYLESHEET)

        # 控制面板
        act_settings = menu.addAction(product_icon("settings"), "打开控制面板")
        act_settings.triggered.connect(self.action_show_settings.emit)

        # 覆盖层显隐切换
        act_toggle = menu.addAction(product_icon("play"), "开启 / 暂停辅助")
        act_toggle.triggered.connect(self.action_toggle_overlay.emit)

        # 重新置顶
        act_retop = menu.addAction(product_icon("retop"), "重新置顶悬浮窗")
        act_retop.triggered.connect(self.action_retop_overlay.emit)

        menu.addSeparator()

        # 退出
        act_exit = menu.addAction("退出 Care3D")
        act_exit.triggered.connect(self.action_exit.emit)

        self.tray.setContextMenu(menu)

    def show(self):
        self.tray.show()

    def show_startup_message(self):
        """显示启动提示气泡"""
        if self.tray.supportsMessages():
            self.tray.showMessage(
                "Care3D 已就绪",
                "视觉舒适辅助已启动。\n可从托盘打开控制面板或暂停辅助。",
                QSystemTrayIcon.MessageIcon.Information,
                3000
            )

    def _on_tray_activated(self, reason: QSystemTrayIcon.ActivationReason):
        """左键单击或双击托盘图标，打开控制面板"""
        if reason in (QSystemTrayIcon.ActivationReason.Trigger, QSystemTrayIcon.ActivationReason.DoubleClick):
            self.action_show_settings.emit()
