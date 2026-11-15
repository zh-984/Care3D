"""Receive relative mouse input in a hidden Qt window, without game hooks."""
import ctypes
import logging
from ctypes import wintypes
from PyQt6.QtCore import QAbstractNativeEventFilter, Qt
from PyQt6.QtWidgets import QApplication, QWidget

class RAWINPUTDEVICE(ctypes.Structure):
    _fields_ = [("usUsagePage", wintypes.USHORT), ("usUsage", wintypes.USHORT),
                ("dwFlags", wintypes.DWORD), ("hwndTarget", wintypes.HWND)]

class RAWINPUTHEADER(ctypes.Structure):
    _fields_ = [("dwType", wintypes.DWORD), ("dwSize", wintypes.DWORD),
                ("hDevice", wintypes.HANDLE), ("wParam", wintypes.WPARAM)]

class RAWMOUSE(ctypes.Structure):
    # The unused button union occupies one aligned ULONG.
    _fields_ = [("usFlags", wintypes.USHORT), ("ulButtons", wintypes.ULONG),
                ("ulRawButtons", wintypes.ULONG), ("lLastX", wintypes.LONG),
                ("lLastY", wintypes.LONG), ("ulExtraInformation", wintypes.ULONG)]

class RawMouseInput(QAbstractNativeEventFilter):
    def __init__(self, on_delta, on_error=None):
        super().__init__()
        self.on_delta = on_delta
        self.on_error = on_error
        self._failed = False
        self.window = None
        self.hwnd = None
        user32 = ctypes.WinDLL("user32", use_last_error=True)
        self.register = user32.RegisterRawInputDevices
        self.register.argtypes = [ctypes.POINTER(RAWINPUTDEVICE), wintypes.UINT, wintypes.UINT]
        self.register.restype = wintypes.BOOL
        self.read = user32.GetRawInputData
        self.read.argtypes = [wintypes.HANDLE, wintypes.UINT, ctypes.c_void_p,
                              ctypes.POINTER(wintypes.UINT), wintypes.UINT]
        self.read.restype = wintypes.UINT
        self.buffer = ctypes.create_string_buffer(256)

    def start(self):
        self._failed = False
        app = QApplication.instance()
        if app is None or app.platformName() != "windows":
            raise RuntimeError("Raw Input requires the Windows Qt platform")
        self.window = QWidget(None, Qt.WindowType.Tool | Qt.WindowType.FramelessWindowHint)
        self.window.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.hwnd = int(self.window.winId())
        device = RAWINPUTDEVICE(1, 2, 0x100, self.hwnd)  # RIDEV_INPUTSINK; no suppression.
        if not self.register(ctypes.byref(device), 1, ctypes.sizeof(device)):
            error = ctypes.get_last_error()
            self.stop()
            raise ctypes.WinError(error)
        app.installNativeEventFilter(self)

    def stop(self):
        if QApplication.instance():
            QApplication.instance().removeNativeEventFilter(self)
        if self.hwnd:
            device = RAWINPUTDEVICE(1, 2, 1, None)
            self.register(ctypes.byref(device), 1, ctypes.sizeof(device))
        if self.window:
            self.window.destroy()
            self.window.deleteLater()
        self.window = None
        self.hwnd = None

    def nativeEventFilter(self, event_type, message):
        if self._failed:
            return False, 0
        try:
            msg = wintypes.MSG.from_address(int(message))
            # ctypes.wintypes.MSG spells this member hWnd (not hwnd).
            if msg.message == 0xFF and msg.hWnd == self.hwnd:
                size = wintypes.UINT(len(self.buffer))
                count = self.read(msg.lParam, 0x10000003, self.buffer, ctypes.byref(size),
                                  ctypes.sizeof(RAWINPUTHEADER))
                if count == 0xFFFFFFFF:
                    raise ctypes.WinError(ctypes.get_last_error())
                self.process_packet(self.buffer.raw[:count])
        except Exception:
            # Never allow a Python exception to escape a Qt native callback:
            # PyQt can terminate the whole UI process in that case.
            self._failed = True
            logging.getLogger(__name__).exception("Raw Input 消息处理失败，保留常驻暗角")
            if self.on_error:
                self.on_error()
        # Let Qt/DefWindowProc perform the required raw-input cleanup.
        return False, 0

    def process_packet(self, packet):
        offset = ctypes.sizeof(RAWINPUTHEADER)
        if len(packet) < offset + ctypes.sizeof(RAWMOUSE):
            return
        header = RAWINPUTHEADER.from_buffer_copy(packet)
        if header.dwType != 0:
            return
        mouse = RAWMOUSE.from_buffer_copy(packet, offset)
        if not mouse.usFlags & 1:  # Exclude absolute tablet coordinates.
            self.on_delta(mouse.lLastX, mouse.lLastY)
