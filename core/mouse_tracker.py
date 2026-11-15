"""Raw mouse accumulation with frame-rate-independent filtering."""
import logging
import math
import threading
import time
from PyQt6.QtCore import QObject, pyqtSignal
from pynput import mouse
from core.raw_input import RawMouseInput

class MouseSpeedTracker(QObject):
    motion_detected = pyqtSignal()

    def __init__(self):
        super().__init__()
        self._lock = threading.Lock()
        self._listener = None
        self._raw_input = None
        self._is_running = False
        self._enabled = True
        self.input_source = "未启动"
        self.reset()

    def reset(self):
        with self._lock:
            self._accumulated_dist = 0.0
            self._smoothed_speed = 0.0
            self._last_coord = None
            self._last_poll_time = time.perf_counter()
            self._wake_pending = False

    def set_enabled(self, enabled):
        if enabled != self._enabled:
            self._enabled = enabled
            self.reset()

    def start(self):
        if self._is_running:
            return
        self._is_running = True
        self.reset()
        try:
            self._raw_input = RawMouseInput(self.add_delta, self._on_raw_error)
            self._raw_input.start()
            self.input_source = "Raw Input"
        except Exception:
            logging.getLogger(__name__).exception("Raw Input 不可用，回退到光标坐标")
            if self._raw_input:
                self._raw_input.stop()
            self._raw_input = None
            self._listener = mouse.Listener(on_move=self._on_mouse_move, suppress=False)
            self._listener.start()
            self.input_source = "光标回退（锁鼠标游戏可能不准确）"

    def stop(self):
        self._is_running = False
        if self._raw_input:
            self._raw_input.stop()
            self._raw_input = None
        if self._listener:
            self._listener.stop()
            self._listener = None
        self.input_source = "已停止"
        self.reset()

    def _on_raw_error(self):
        self.input_source = "输入检测异常（常驻暗角仍可使用）"
        self.reset()

    def add_delta(self, dx, dy):
        if not self._is_running or not self._enabled or (dx == 0 and dy == 0):
            return
        wake = False
        with self._lock:
            self._accumulated_dist += math.hypot(dx, dy)
            if not self._wake_pending:
                self._wake_pending = True
                wake = True
        if wake:
            self.motion_detected.emit()

    def _on_mouse_move(self, x, y, injected=False):
        if injected:
            return
        previous = self._last_coord
        self._last_coord = (x, y)
        if previous:
            dx, dy = x - previous[0], y - previous[1]
            if math.hypot(dx, dy) < 2500:
                self.add_delta(dx, dy)

    def poll_speed(self, decay_time=0.55):
        now = time.perf_counter()
        with self._lock:
            # A long-idle renderer samples the recent burst, rather than all idle time.
            dt = max(0.001, min(0.05, now - self._last_poll_time))
            dist = self._accumulated_dist
            self._accumulated_dist = 0.0
            self._wake_pending = False
            self._last_poll_time = now
        raw_speed = dist / dt
        tau = 0.025 if raw_speed > self._smoothed_speed else max(0.04, decay_time * 0.22)
        self._smoothed_speed += (raw_speed - self._smoothed_speed) * (-math.expm1(-dt / tau))
        if dist == 0 and self._smoothed_speed < 15:
            self._smoothed_speed = 0.0
        return self._smoothed_speed, self._smoothed_speed > 0 or dist > 0

    @property
    def smoothed_speed(self):
        return self._smoothed_speed
