"""Best-effort colors for the application's existing native Windows title bar."""

from __future__ import annotations

import sys
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from PyQt6.QtWidgets import QWidget


# Public DWMWINDOWATTRIBUTE values, supported from Windows 11 build 22000.
# CAPTION_COLOR and TEXT_COLOR follow WINDOW_CORNER_PREFERENCE=33 and BORDER_COLOR.
# https://learn.microsoft.com/windows/win32/api/dwmapi/ne-dwmapi-dwmwindowattribute
_DWMWA_USE_IMMERSIVE_DARK_MODE = 20
_DWMWA_CAPTION_COLOR = 35
_DWMWA_TEXT_COLOR = 36


def apply_dark_titlebar(widget: QWidget) -> bool:
    """Color only this Qt window's native title bar, leaving its frame intact.

    Returns True when DWM accepts all requested attributes. Unsupported systems,
    offscreen Qt platforms, frameless widgets, and native failures quietly return
    False. Call after the top-level window has been shown, on the Qt GUI thread.
    """
    try:
        if sys.platform != "win32":
            return False

        from PyQt6.QtCore import Qt
        from PyQt6.QtGui import QGuiApplication

        app = QGuiApplication.instance()
        if app is None or app.platformName().lower() != "windows":
            return False
        if sys.getwindowsversion().build < 22000:
            return False
        if not widget.isWindow() or widget.windowFlags() & Qt.WindowType.FramelessWindowHint:
            return False

        hwnd = int(widget.winId())
        if not hwnd:
            return False

        import ctypes
        from ctypes import wintypes

        set_attribute = ctypes.WinDLL("dwmapi.dll").DwmSetWindowAttribute
        set_attribute.argtypes = [
            wintypes.HWND, wintypes.DWORD, wintypes.LPCVOID, wintypes.DWORD,
        ]
        set_attribute.restype = wintypes.LONG  # HRESULT; S_OK is zero.

        # COLORREF stores RGB bytes as 0x00BBGGRR, rather than CSS #RRGGBB.
        # https://learn.microsoft.com/windows/win32/gdi/colorref
        attributes = (
            (_DWMWA_USE_IMMERSIVE_DARK_MODE, wintypes.BOOL(True)),
            (_DWMWA_CAPTION_COLOR, wintypes.DWORD(0x001E1A17)),  # #171A1E
            (_DWMWA_TEXT_COLOR, wintypes.DWORD(0x00EEEBE7)),  # #E7EBEE
        )
        accepted = [
            set_attribute(hwnd, attribute, ctypes.byref(value), ctypes.sizeof(value)) == 0
            for attribute, value in attributes
        ]
        return all(accepted)
    except Exception:
        # Title bar decoration must never prevent the settings window from opening.
        return False
