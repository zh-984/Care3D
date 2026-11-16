"""Optional, read-only XInput right-stick sampling."""
import ctypes
import math
import time
from ctypes import wintypes

class Gamepad(ctypes.Structure):
    _fields_ = [("buttons", wintypes.WORD), ("left_trigger", ctypes.c_ubyte),
                ("right_trigger", ctypes.c_ubyte), ("left_x", ctypes.c_short),
                ("left_y", ctypes.c_short), ("right_x", ctypes.c_short),
                ("right_y", ctypes.c_short)]

class State(ctypes.Structure):
    _fields_ = [("packet", wintypes.DWORD), ("gamepad", Gamepad)]

class GamepadTracker:
    def __init__(self):
        self._read = None
        self._index = None
        self._next_probe = 0
        self.buttons = 0
        self._requested_device = -1
        for name in ("xinput1_4", "xinput1_3", "xinput9_1_0"):
            try:
                self._read = ctypes.WinDLL(name).XInputGetState
                self._read.argtypes = [wintypes.DWORD, ctypes.POINTER(State)]
                self._read.restype = wintypes.DWORD
                break
            except OSError:
                pass

    @staticmethod
    def strength(x, y, deadzone=0.22, curve=1.0):
        magnitude = min(1.0, math.hypot(x, y) / 32767.0)
        return max(0.0, (magnitude - deadzone) / (1 - deadzone)) ** curve

    def poll(self, config=None):
        tuning = config is not None and config.gamepad_tuning_enabled
        requested = config.gamepad_device if tuning else -1
        if requested != self._requested_device:
            self._index, self._next_probe = None, 0
            self._requested_device = requested
        if self._read is None:
            self.buttons = 0
            return 0.0
        now = time.perf_counter()
        if self._index is None and now < self._next_probe:
            return 0.0
        indices = [requested] if requested >= 0 else ([self._index] if self._index is not None else range(4))
        for index in indices:
            state = State()
            if self._read(index, ctypes.byref(state)) == 0:
                self._index = index
                self.buttons = state.gamepad.buttons
                if tuning:
                    x, y = ((state.gamepad.left_x, state.gamepad.left_y) if config.gamepad_stick == "left"
                            else (state.gamepad.right_x, state.gamepad.right_y))
                    return self.strength(x, y, config.gamepad_deadzone, config.gamepad_curve)
                return self.strength(state.gamepad.right_x, state.gamepad.right_y)
        self._index = None
        self.buttons = 0
        self._next_probe = now + 1
        return 0.0
