"""
Care3D 主程序入口 (main.py)
整合鼠标运动监听、全屏穿透覆盖层、控制面板、系统托盘与全局快捷键。
"""

import sys
import os
import ctypes
import logging
from logging.handlers import RotatingFileHandler
from PyQt6.QtWidgets import QApplication, QMessageBox
from PyQt6.QtCore import QLockFile, QTimer, pyqtSignal, QObject

from core.config import ConfigManager
from core.mouse_tracker import MouseSpeedTracker
from core.hotkey_manager import GlobalHotkeyManager
from core.preset_library import PresetLibrary
from core.extensions import ExtensionController
from ui.overlay_window import MotionSicknessOverlay
from ui.settings_window import SettingsWindow
from ui.tray_icon import TrayIconManager
from ui.product_icons import app_icon


class AppBridge(QObject):
    """用于跨线程（如 pynput 热键回调）安全调度 Qt 主线程事件的桥接器"""
    trigger_toggle = pyqtSignal()
    trigger_comfort = pyqtSignal()
    hold_comfort = pyqtSignal(bool)
    trigger_profile = pyqtSignal()


def set_high_dpi_awareness():
    """启用 Windows 原生 Per-Monitor V2 DPI 感知，确保高分屏 (2K/4K) 像素 1:1 精确映射"""
    if sys.platform == "win32":
        try:
            # DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2 = -4
            ctypes.windll.user32.SetProcessDpiAwarenessContext(ctypes.c_void_p(-4))
        except Exception:
            try:
                ctypes.windll.shcore.SetProcessDpiAwareness(2)
            except Exception:
                try:
                    ctypes.windll.user32.SetProcessDPIAware()
                except Exception:
                    pass


def main():
    smoke_test = "--smoke-test" in sys.argv
    # 1. 设置 Windows 高分屏 DPI 感知
    set_high_dpi_awareness()

    # 2. 初始化 Qt 应用程序
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)  # 保持托盘常驻，关闭设置面板时不退出
    app.setApplicationName("Care3D")
    app.setApplicationDisplayName("Care3D · 游戏视觉舒适辅助")
    app.setWindowIcon(app_icon())

    # 3. 初始化配置与核心监听组件
    config_mgr = ConfigManager()
    # Multiple overlays can stack their opacity. Prevent duplicate application instances.
    instance_lock = QLockFile(os.path.join(config_mgr.config_dir, "care3d.lock"))
    if not instance_lock.tryLock(100):
        QMessageBox.information(None, "Care3D", "Care3D 已在运行，请从系统托盘打开控制面板。")
        return
    try:
        handler = RotatingFileHandler(os.path.join(config_mgr.config_dir, "care3d.log"),
                                      maxBytes=500_000, backupCount=2, encoding="utf-8")
        logging.basicConfig(level=logging.INFO, handlers=[handler],
                            format="%(asctime)s %(levelname)s %(name)s %(message)s")
    except OSError:
        logging.basicConfig(level=logging.INFO)
    def log_exception(exception_type, exception, traceback):
        logging.critical("Unhandled application error", exc_info=(exception_type, exception, traceback))
        app.quit()
    sys.excepthook = log_exception
    logging.info("Initializing input")
    mouse_tracker = MouseSpeedTracker()
    mouse_tracker.start()
    logging.info("Input backend: %s", mouse_tracker.input_source)

    # 4. 创建全屏穿透覆盖层与控制面板
    logging.info("Creating overlay")
    overlay = MotionSicknessOverlay(config_mgr, mouse_tracker)
    library = PresetLibrary(config_mgr)
    extensions = ExtensionController(config_mgr, library, overlay, app)
    logging.info("Creating settings")
    settings_win = SettingsWindow(config_mgr, mouse_tracker, overlay_ref=overlay,
                                  library=library, extension_controller=extensions)
    extensions.context_changed.connect(settings_win._load_values_to_ui)
    logging.info("Settings created")

    # 5. 创建系统托盘
    tray_mgr = TrayIconManager()
    if not smoke_test:
        tray_mgr.show()
        tray_mgr.show_startup_message()

    # 6. 设置覆盖层初始显隐
    if not smoke_test:
        logging.info("Showing overlay")
        overlay.on_config_changed(config_mgr.config)

    # 默认弹出设置面板供用户查看与调优参数
    if not smoke_test:
        settings_win.show()
        logging.info("Settings shown")

    # 7. 切换覆盖层逻辑封装
    def toggle_overlay():
        cfg = config_mgr.config
        cfg.overlay_visible = not cfg.overlay_visible
        config_mgr.save()
        config_mgr.notify_listeners()
        settings_win.update_power_button_state(cfg.overlay_visible)

    # 8. 全局热键桥接 (pynput 运行在子线程，通过 Qt Signal 调度到主线程执行)
    bridge = AppBridge()
    bridge.trigger_toggle.connect(toggle_overlay)
    bridge.trigger_comfort.connect(overlay.toggle_comfort)
    bridge.hold_comfort.connect(overlay.set_comfort_active)
    bridge.trigger_profile.connect(extensions.cycle_profile)
    extensions.request_toggle.connect(toggle_overlay)

    hotkey_mgr = GlobalHotkeyManager(
        hotkey_str=config_mgr.config.hotkey_toggle,
        on_triggered=bridge.trigger_toggle.emit
    )
    extensions.attach_hotkeys(hotkey_mgr, bridge)
    extensions.notification.connect(lambda message: tray_mgr.tray.showMessage("Care3D", message))

    # 9. 信号与槽关联
    settings_win.request_toggle_overlay.connect(toggle_overlay)
    settings_win.request_reapply_topmost.connect(overlay.reapply_topmost)

    tray_mgr.action_show_settings.connect(lambda: (settings_win.show(), settings_win.activateWindow()))
    tray_mgr.action_toggle_overlay.connect(toggle_overlay)
    tray_mgr.action_retop_overlay.connect(overlay.reapply_topmost)
    tray_mgr.action_exit.connect(app.quit)

    # 10. 退出时清理后台线程与监听
    def cleanup():
        logging.info("Shutting down input and timers")
        hotkey_mgr.stop()
        extensions.stop()
        overlay.timer.stop()
        overlay.context_timer.stop()
        settings_win.save_timer.stop()
        mouse_tracker.stop()
        config_mgr.save()
        instance_lock.unlock()
        logging.info("Shutdown complete")

    app.aboutToQuit.connect(cleanup)
    def startup_ready():
        logging.info("UI event loop ready")
    QTimer.singleShot(250, startup_ready)
    if smoke_test:
        QTimer.singleShot(400, app.quit)

    # 11. 进入 Qt 事件主循环
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
