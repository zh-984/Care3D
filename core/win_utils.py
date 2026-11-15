"""Win32 click-through window styles and read-only window geometry helpers."""
import win32gui
import win32con
import win32api
import win32process
import os
from PyQt6.QtCore import QRect


def make_window_click_through(hwnd: int) -> bool:
    """
    为指定窗口句柄应用彻底的鼠标穿透、分层半透明、始终置顶与防抢焦点属性。

    :param hwnd: 窗口 Win32 句柄 (通过 widget.winId() 获取)
    :return: 是否设置成功
    """
    try:
        # 获取当前窗口现有的扩展样式 (Extended Style)
        ex_style = win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE)

        # 组合关键扩展样式：
        # - WS_EX_TRANSPARENT: 鼠标穿透，点击直达下方游戏
        # - WS_EX_LAYERED: 硬件分层，支持半透明 Alpha 通道
        # - WS_EX_TOOLWINDOW: 不在任务栏和 Alt+Tab 占位
        # - WS_EX_NOACTIVATE: 绝对不抢占输入焦点
        # - WS_EX_TOPMOST: 保持在游戏上方覆盖
        new_style = (
            ex_style
            | win32con.WS_EX_TRANSPARENT
            | win32con.WS_EX_LAYERED
            | win32con.WS_EX_TOOLWINDOW
            | win32con.WS_EX_NOACTIVATE
            | win32con.WS_EX_TOPMOST
        )

        # 设置更新后的扩展样式
        win32gui.SetWindowLong(hwnd, win32con.GWL_EXSTYLE, new_style)

        # 强化置顶层级：通知 Windows DWM 立即将该窗口置于 TOPMOST 队列最顶端，
        # 并显式添加 SWP_NOACTIVATE 避免抢夺游戏焦点。
        win32gui.SetWindowPos(
            hwnd,
            win32con.HWND_TOPMOST,
            0, 0, 0, 0,
            win32con.SWP_NOMOVE |
            win32con.SWP_NOSIZE |
            win32con.SWP_NOACTIVATE |
            win32con.SWP_SHOWWINDOW
        )
        return True
    except Exception as e:
        print(f"[win_utils] 设置穿透窗口扩展样式失败: {e}")
        return False


def bring_window_to_topmost(hwnd: int) -> bool:
    """
    重新置顶覆盖层窗口。
    当某些全屏游戏切换分辨率或切屏导致覆盖层被游戏压在下方时，调用此函数可重新拉回顶层。
    """
    try:
        win32gui.SetWindowPos(
            hwnd,
            win32con.HWND_TOPMOST,
            0, 0, 0, 0,
            win32con.SWP_NOMOVE |
            win32con.SWP_NOSIZE |
            win32con.SWP_NOACTIVATE
        )
        return True
    except Exception as e:
        print(f"[win_utils] 重新置顶失败: {e}")
        return False


def list_target_windows():
    """Enumerate visible top-level titles; no process memory or game hooks."""
    windows = []
    def collect(hwnd, _):
        try:
            title = win32gui.GetWindowText(hwnd).strip()
            if win32gui.IsWindowVisible(hwnd) and title:
                _, pid = win32process.GetWindowThreadProcessId(hwnd)
                if pid != os.getpid() and win32gui.GetClassName(hwnd) not in ("Progman", "WorkerW", "Shell_TrayWnd"):
                    windows.append((hwnd, title))
        except win32gui.error:
            pass  # A window can disappear while EnumWindows is visiting it.
    win32gui.EnumWindows(collect, None)
    return sorted(windows, key=lambda item: item[1].casefold())


def foreground_window():
    try:
        hwnd = win32gui.GetForegroundWindow()
        if not hwnd or win32gui.IsIconic(hwnd):
            return 0, ""
        return hwnd, win32gui.GetWindowText(hwnd)
    except win32gui.error:
        return 0, ""


def client_geometry(hwnd, screens):
    """Convert physical Win32 client coordinates to Qt logical screen coordinates."""
    try:
        left, top, right, bottom = win32gui.GetClientRect(hwnd)
        x, y = win32gui.ClientToScreen(hwnd, (left, top))
        info = win32api.GetMonitorInfo(win32api.MonitorFromWindow(hwnd, 2))
        screen = next((s for s in screens if s.name() == info.get("Device")), None)
        if screen is None:
            return None  # Keep the selected screen rather than guess a mixed-DPI mapping.
        ratio = screen.devicePixelRatio()
        origin = screen.geometry()
        mx, my, _, _ = info["Monitor"]
        return QRect(round(origin.x() + (x - mx) / ratio),
                     round(origin.y() + (y - my) / ratio),
                     round((right - left) / ratio), round((bottom - top) / ratio))
    except (win32gui.error, ValueError):
        return None
