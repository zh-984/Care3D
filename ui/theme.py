"""Shared desktop theme. Geometry stays in the existing widget layouts."""

ACCENT = "#72B8A5"
TEXT = "#E7EBEE"
MUTED = "#A0A8B1"


def apply_dark_palette(widget):
    """Keep native control glyphs readable on the dark themed window."""
    from PyQt6.QtGui import QColor, QPalette

    palette = widget.palette()
    colors = {
        "Window": "#171A1E", "WindowText": TEXT,
        "Base": "#202429", "AlternateBase": "#202429", "Text": TEXT,
        "Button": "#202429", "ButtonText": TEXT,
        "Highlight": "#315E53", "HighlightedText": "#F0F5F2",
        "Light": "#5D6871", "Midlight": "#46515A", "Mid": "#363F47",
        "Dark": "#14171B", "Shadow": "#101316", "PlaceholderText": MUTED,
    }
    for role, color in colors.items():
        palette.setColor(getattr(QPalette.ColorRole, role), QColor(color))
    for role in ("WindowText", "Text", "ButtonText", "PlaceholderText"):
        palette.setColor(QPalette.ColorGroup.Disabled,
                         getattr(QPalette.ColorRole, role), QColor("#727C86"))
    widget.setPalette(palette)


STYLESHEET = """
QWidget {
    background: transparent;
    color: #E7EBEE;
    font-family: 'Microsoft YaHei UI', 'Segoe UI', 'Microsoft YaHei', sans-serif;
    font-size: 12px;
}
QWidget#care3dSettings, QDialog { background: #171A1E; }
QLabel { background: transparent; border: none; }
QToolTip {
    color: #D7DDE2; background: #202429; border: 1px solid #3B444D;
    padding: 6px 9px;
}
QFrame#headerPanel {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #202429, stop:1 #202429);
    border: 1px solid #323941; border-radius: 8px; padding: 6px 10px;
}
QLabel#brandWordmark { color: #EDF1F4; font-size: 16px; font-weight: 600; }
QLabel#productBadge {
    background: #272D34; color: #B3BDC5; border: 1px solid #3C454E;
    font-size: 10px; font-weight: 500; padding: 2px 6px; border-radius: 4px;
}
QLabel#headerDescription { color: #A0A8B1; font-size: 11px; }
QFrame#noticePanel {
    background: #23272D; border: 1px solid #363E46; border-radius: 6px; padding: 4px 8px;
}
QLabel#noticeText { color: #BDC6CD; font-size: 11px; }
QPushButton#retopButton { padding: 2px 8px; font-size: 11px; border-radius: 4px; }
QFrame#footerPanel {
    background: #1D2126; border: 1px solid #323A42; border-radius: 6px; padding: 6px 10px;
}
QFrame.compact_card {
    background: #202429; border: 1px solid #333B44; border-radius: 8px; padding: 8px 10px;
}
QLabel#parameterLabel { color: #CCD4DA; font-size: 12px; font-weight: 500; }
QLabel#valueBadge {
    background: #242A30; color: #D9E2E6; font-size: 11px; font-weight: 600;
    padding: 2px 4px; border: 1px solid #3A444D; border-radius: 4px;
}
QLabel#profileStatus { color: #A0A8B1; font-size: 11px; }
QScrollArea { border: none; background: transparent; }
QScrollBar:vertical, QScrollBar:horizontal { background: #272D34; border-radius: 3px; }
QScrollBar:vertical { width: 6px; }
QScrollBar::handle:vertical, QScrollBar::handle:horizontal { background: #788690; border-radius: 3px; }
QScrollBar::handle:vertical { min-height: 20px; }
QScrollBar::handle:hover { background: #99A8B2; }
QScrollBar::handle:pressed { background: #BDCCD3; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0px; }
QScrollBar::add-page, QScrollBar::sub-page { background: transparent; }
QTabWidget::pane {
    background: #1B1F24; border: 1px solid #313941; border-radius: 8px; top: -1px;
}
QTabBar::tab {
    background: #1B1F24; border: 1px solid #313941; border-bottom: none;
    color: #A8B1BA; padding: 7px 16px; margin-right: 4px;
    border-top-left-radius: 6px; border-top-right-radius: 6px;
    font-size: 12px; font-weight: 500;
}
QTabBar::tab:hover { color: #DCE5E9; background: #272D34; }
QTabBar::tab:selected {
    color: #A6D8CA; background: #243A35; font-weight: 600; border-top: 2px solid #72B8A5;
}
QSlider::groove:horizontal { height: 5px; background: #333B44; border-radius: 2px; }
QSlider::sub-page:horizontal {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #518B7E, stop:1 #72B8A5);
    border-radius: 2px;
}
QSlider::handle:horizontal {
    background: #E2EBE7; border: 2px solid #8AC3B2; width: 14px;
    margin-top: -5px; margin-bottom: -5px; border-radius: 7px;
}
QSlider::handle:horizontal:hover { background: #F2F7F5; border-color: #B5DACD; }
QSlider::handle:horizontal:pressed { background: #B5DACD; border-color: #72B8A5; }
QSlider::groove:horizontal:disabled { background: #2B3138; }
QSlider::sub-page:horizontal:disabled { background: #465159; }
QSlider::handle:horizontal:disabled { background: #3A444D; border-color: #5C6872; }
QCheckBox { background: transparent; spacing: 8px; color: #E7EBEE; font-weight: 600; font-size: 13px; }
QCheckBox::indicator { width: 17px; height: 17px; border-radius: 4px; border: 1px solid #66737D; background: #202429; }
QCheckBox::indicator:hover { border-color: #8AC3B2; background: #2A3239; }
QCheckBox::indicator:checked { background: #72B8A5; border-color: #8AC3B2; }
QCheckBox:disabled { color: #727D86; }
QCheckBox::indicator:disabled { background: #252B31; border-color: #363F47; }
QCheckBox::indicator:checked:disabled { background: #50625B; border-color: #50625B; }
QPushButton {
    background: #202429; color: #D2DADF; border: 1px solid #414B54;
    border-radius: 5px; padding: 5px 12px; font-size: 12px; font-weight: 500;
}
QPushButton:hover { background: #2A3239; border-color: #63747D; color: #EFF4F5; }
QPushButton:pressed { background: #34413F; border-color: #80AE9F; }
QPushButton:focus { border-color: #72B8A5; }
QPushButton:disabled { background: #22272D; border-color: #30383F; color: #707A83; }
QPushButton[role="profile"] {
    background: #1B1F24; border: 1px solid #3A434C; border-radius: 6px;
    padding: 7px 6px; font-size: 11px; font-weight: 500; color: #A8B1BA;
}
QPushButton[role="profile"]:hover { background: #202429; color: #E0E7EB; border-color: #63747D; }
QPushButton[role="profile"]:checked { background: #243B35; color: #A9D8C9; border-color: #598F7D; font-weight: 600; }
QPushButton#powerButton { padding: 5px 14px; border-radius: 13px; }
QPushButton#powerButton[state="running"] { background: #203B31; border-color: #3C6F59; color: #9DD7BC; }
QPushButton#powerButton[state="running"]:hover { background: #2A493D; border-color: #638E7B; }
QPushButton#powerButton[state="paused"] { background: #282E35; border-color: #47535E; color: #B8C2CA; }
QPushButton#powerButton[state="paused"]:hover { background: #323C44; border-color: #677A88; }
QPushButton#btn_danger { background: #3C282B; color: #DFACB0; border-color: #70464C; }
QPushButton#btn_danger:hover { background: #4C3036; border-color: #A36B75; color: #F1C1C6; }
QComboBox {
    background: #202429; border: 1px solid #363F47; border-radius: 5px;
    padding: 4px 10px; color: #E7EBEE; font-size: 12px;
}
QComboBox:hover, QComboBox:focus { border-color: #8BB6A9; }
QComboBox:disabled { background: #1C2025; border-color: #343D45; color: #727C86; }
QComboBox::drop-down { border: none; width: 18px; }
QComboBox QAbstractItemView {
    background: #202429; border: 1px solid #50635E; color: #E7EBEE;
    selection-background-color: #2C4B42; selection-color: #D6F1E6; border-radius: 4px; padding: 2px;
}
QLineEdit, QKeySequenceEdit, QSpinBox, QDoubleSpinBox {
    background: #202429; color: #D7DDE2; border: 1px solid #363F47;
    border-radius: 5px; padding: 2px 8px; selection-background-color: #315E53; selection-color: #F0F5F2;
}
QLineEdit:focus, QKeySequenceEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus { border-color: #72B8A5; background: #242E2C; }
QLineEdit:disabled, QKeySequenceEdit:disabled, QSpinBox:disabled, QDoubleSpinBox:disabled { color: #727C86; background: #1C2025; border-color: #343D45; }
QPlainTextEdit {
    background: #202429; color: #D7DDE2; border: 1px solid #363F47; border-radius: 5px;
    padding: 5px; selection-background-color: #315E53; selection-color: #F0F5F2;
}
QPlainTextEdit:focus { border-color: #72B8A5; }
QPlainTextEdit:disabled { color: #727C86; background: #1C2025; border-color: #343D45; }
QListWidget { background: #1C2025; border: 1px solid #3A434C; border-radius: 5px; outline: none; }
QListWidget::item { color: #A8B1BA; padding: 4px 2px; }
QListWidget::item:selected { color: #A9D8C9; background: #243B35; }
QListWidget::item:hover:!selected { background: #202429; }
QProgressBar {
    border: 1px solid #3B474D; border-radius: 4px; text-align: center;
    background: #202429; color: #D0D9DF; font-weight: 500; font-size: 11px;
}
QProgressBar::chunk { background: #385E53; border-radius: 3px; }
QMenu { background: #202429; color: #D7DDE2; border: 1px solid #414C56; border-radius: 6px; padding: 4px; }
QMenu::item { padding: 6px 24px; border-radius: 4px; }
QMenu::item:selected { background: #243A35; color: #A9D8C9; }
QMenu::separator { height: 1px; background: #343D45; margin: 4px 8px; }
"""
