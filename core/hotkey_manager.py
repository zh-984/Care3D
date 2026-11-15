"""
全局快捷键管理模块 (hotkey_manager.py)
基于 pynput.keyboard 实现零侵入的后台全局快捷键监听。
支持一键显隐覆盖层，不拦截普通按键。
"""

import logging
from typing import Callable, Optional
from pynput import keyboard

log = logging.getLogger(__name__)

class GlobalHotkeyManager:
    """
    全局热键管理器
    运行于后台独立守护线程，捕获热键后通过回调函数通知主线程。
    """

    def __init__(self, hotkey_str: str = "<ctrl>+<alt>+h", on_triggered: Optional[Callable[[], None]] = None):
        self._hotkey_str = hotkey_str.lower().strip()
        self._on_triggered = on_triggered
        self._listener: Optional[keyboard.GlobalHotKeys] = None
        self._is_running = False

    def start(self):
        """启动热键监听"""
        if self._is_running:
            return

        try:
            mapping = {self._hotkey_str: self._handle_trigger}
            self._listener = keyboard.GlobalHotKeys(mapping)
            self._listener.daemon = True
            self._listener.start()
            self._is_running = True
            log.info("Global hotkey activated: %s", self._hotkey_str)
        except Exception:
            log.exception("Global hotkey registration failed: %s", self._hotkey_str)
            self._listener = None
            self._is_running = False

    def stop(self):
        """停止热键监听"""
        self._is_running = False
        if self._listener is not None:
            try:
                self._listener.stop()
            except Exception:
                pass
            self._listener = None

    def update_hotkey(self, new_hotkey_str: str):
        """更新热键组合并重新启动监听"""
        self.stop()
        self._hotkey_str = new_hotkey_str.lower().strip()
        self.start()

    def _handle_trigger(self):
        """热键命中内部处理"""
        if self._on_triggered:
            try:
                self._on_triggered()
            except Exception:
                log.exception("Global hotkey callback failed")
