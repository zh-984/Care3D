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
        self._bindings = {}
        self._hold_binding = ""
        self._hold_callback = None
        self._hold_listener = None
        self._held_keys = set()
        self._hold_active = False

    def start(self):
        """启动热键监听"""
        if self._is_running:
            return

        try:
            mapping = {self._hotkey_str: self._handle_trigger}
            mapping.update(self._bindings)
            self._listener = keyboard.GlobalHotKeys(mapping)
            self._listener.daemon = True
            self._listener.start()
            self._is_running = True
            if self._hold_binding:
                required = set(keyboard.HotKey.parse(self._hold_binding))
                def press(key):
                    if self._hold_listener is not hold_listener:
                        return
                    key = hold_listener.canonical(key)
                    self._held_keys.add(key)
                    if required.issubset(self._held_keys) and not self._hold_active:
                        self._hold_active = True
                        self._hold_callback(True)
                def release(key):
                    if self._hold_listener is not hold_listener:
                        return
                    key = hold_listener.canonical(key)
                    self._held_keys.discard(key)
                    if self._hold_active and not required.issubset(self._held_keys):
                        self._hold_active = False
                        self._hold_callback(False)
                hold_listener = keyboard.Listener(on_press=press, on_release=release)
                self._hold_listener = hold_listener
                self._hold_listener.daemon = True
                self._hold_listener.start()
            log.info("Global hotkey activated: %s", self._hotkey_str)
        except Exception:
            log.exception("Global hotkey registration failed: %s", self._hotkey_str)
            self.stop()

    def stop(self):
        """停止热键监听"""
        self._is_running = False
        if self._hold_listener:
            try:
                self._hold_listener.stop()
            except Exception:
                log.exception("Failed to stop held-key listener")
            self._hold_listener = None
        self._held_keys.clear()
        if self._hold_active and self._hold_callback:
            self._hold_callback(False)
        self._hold_active = False
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

    def configure(self, toggle_key, bindings=None, hold_binding="", hold_callback=None):
        signature = (toggle_key, tuple(sorted((bindings or {}).keys())), hold_binding)
        if signature == getattr(self, "_signature", None):
            return
        self.stop()
        self._hotkey_str = toggle_key
        self._bindings = bindings or {}
        self._hold_binding, self._hold_callback = hold_binding, hold_callback
        self._signature = signature
        self.start()


def valid_shortcut(value):
    """Require a modifier and one non-modifier, with no multi-chord shortcuts."""
    if not isinstance(value, str) or len(value) > 80:
        return False
    try:
        keys = keyboard.HotKey.parse(value)
        modifiers = {keyboard.Key.ctrl, keyboard.Key.alt, keyboard.Key.shift, keyboard.Key.cmd}
        return len(keys) >= 2 and len(set(keys)) == len(keys) and any(k in modifiers for k in keys) and sum(k not in modifiers for k in keys) == 1
    except (ValueError, KeyError, TypeError):
        return False
