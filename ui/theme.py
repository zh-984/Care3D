"""Shared desktop theme. Geometry stays in the existing widget layouts."""

ACCENT = "#343A40"
TEXT = "#242529"
MUTED = "#6B727B"

STYLESHEET = """
QWidget {
    background: transparent;
    color: #242529;
    font-family: 'Microsoft YaHei UI', 'Segoe UI', 'Microsoft YaHei', sans-serif;
    font-size: 12px;
}
QWidget#care3dSettings, QDialog { background: #FFFFFF; }
QLabel { background: transparent; border: none; }
QToolTip {
    color: #30363D; background: #FFFFFF; border: 1px solid #CDD2D7;
    padding: 6px 9px;
}
QFrame#headerPanel {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #F7F8F9, stop:1 #F7F8F9);
    border: 1px solid #DFE2E5; border-radius: 8px; padding: 6px 10px;
}
QLabel#brandWordmark { color: #202428; font-size: 16px; font-weight: 600; }
QLabel#productBadge {
    background: #F0F2F4; color: #5F6872; border: 1px solid #DADEE2;
    font-size: 10px; font-weight: 500; padding: 2px 6px; border-radius: 4px;
}
QLabel#headerDescription { color: #6B737D; font-size: 11px; }
QFrame#noticePanel {
    background: #F6F7F8; border: 1px solid #DFE3E7; border-radius: 6px; padding: 4px 8px;
}
QLabel#noticeText { color: #606973; font-size: 11px; }
QPushButton#retopButton { padding: 2px 8px; font-size: 11px; border-radius: 4px; }
QFrame#footerPanel {
    background: #F8F9FA; border: 1px solid #DFE3E7; border-radius: 6px; padding: 6px 10px;
}
QFrame.compact_card {
    background: #FFFFFF; border: 1px solid #E0E3E6; border-radius: 8px; padding: 8px 10px;
}
QLabel#parameterLabel { color: #353B43; font-size: 12px; font-weight: 500; }
QLabel#valueBadge {
    background: #F8F9FA; color: #30363D; font-size: 11px; font-weight: 600;
    padding: 2px 4px; border: 1px solid #D7DDE2; border-radius: 4px;
}
QLabel#profileStatus { color: #6B727B; font-size: 11px; }
QScrollArea { border: none; background: transparent; }
QScrollBar:vertical, QScrollBar:horizontal { background: #F0F2F4; border-radius: 3px; }
QScrollBar:vertical { width: 6px; }
QScrollBar::handle:vertical, QScrollBar::handle:horizontal { background: #919AA3; border-radius: 3px; }
QScrollBar::handle:vertical { min-height: 20px; }
QScrollBar::handle:hover { background: #66727D; }
QScrollBar::handle:pressed { background: #3E4A56; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0px; }
QScrollBar::add-page, QScrollBar::sub-page { background: transparent; }
QTabWidget::pane {
    background: #FAFAFB; border: 1px solid #DEE2E6; border-radius: 8px; top: -1px;
}
QTabBar::tab {
    background: #FAFAFB; border: 1px solid #DEE2E6; border-bottom: none;
    color: #68717B; padding: 7px 16px; margin-right: 4px;
    border-top-left-radius: 6px; border-top-right-radius: 6px;
    font-size: 12px; font-weight: 500;
}
QTabBar::tab:hover { color: #2C333A; background: #F0F2F4; }
QTabBar::tab:selected {
    color: #242A30; background: #EBEEF0; font-weight: 600; border-top: 2px solid #343A40;
}
QSlider::groove:horizontal { height: 5px; background: #E0E3E6; border-radius: 2px; }
QSlider::sub-page:horizontal {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #59636E, stop:1 #343A40);
    border-radius: 2px;
}
QSlider::handle:horizontal {
    background: #FFFFFF; border: 2px solid #68737E; width: 14px;
    margin-top: -5px; margin-bottom: -5px; border-radius: 7px;
}
QSlider::handle:horizontal:hover { background: #FFFFFF; border-color: #414B55; }
QSlider::handle:horizontal:pressed { background: #E1E6EA; border-color: #343A40; }
QSlider::groove:horizontal:disabled { background: #E9ECEF; }
QSlider::sub-page:horizontal:disabled { background: #CAD0D6; }
QSlider::handle:horizontal:disabled { background: #D7DDE2; border-color: #BBC4CC; }
QCheckBox { background: transparent; spacing: 8px; color: #242529; font-weight: 600; font-size: 13px; }
QCheckBox::indicator { width: 17px; height: 17px; border-radius: 4px; border: 1px solid #A9B2BB; background: #FFFFFF; }
QCheckBox::indicator:hover { border-color: #59636E; background: #F1F3F5; }
QCheckBox::indicator:checked { background: #343A40; border-color: #343A40; }
QCheckBox:disabled { color: #929AA3; }
QCheckBox::indicator:disabled { background: #F2F4F6; border-color: #D6DCE2; }
QCheckBox::indicator:checked:disabled { background: #A0A9B3; border-color: #A0A9B3; }
QPushButton {
    background: #FFFFFF; color: #343B43; border: 1px solid #D6DBE0;
    border-radius: 5px; padding: 5px 12px; font-size: 12px; font-weight: 500;
}
QPushButton:hover { background: #F1F3F5; border-color: #A8B1BA; color: #23292F; }
QPushButton:pressed { background: #E7EBEF; border-color: #798590; }
QPushButton:focus { border-color: #343A40; }
QPushButton:disabled { background: #F5F6F7; border-color: #E0E4E8; color: #949DA7; }
QPushButton[role="profile"] {
    background: #FAFAFB; border: 1px solid #D9DEE3; border-radius: 6px;
    padding: 7px 6px; font-size: 11px; font-weight: 500; color: #626C76;
}
QPushButton[role="profile"]:hover { background: #EFF2F4; color: #30373E; border-color: #A8B1BA; }
QPushButton[role="profile"]:checked { background: #E7ECEF; color: #242B32; border-color: #929EA9; font-weight: 600; }
QPushButton#powerButton { padding: 5px 14px; border-radius: 13px; }
QPushButton#powerButton[state="running"] { background: #EAF4EF; border-color: #A4C9B5; color: #286343; }
QPushButton#powerButton[state="running"]:hover { background: #DBEDE2; border-color: #79AB91; }
QPushButton#powerButton[state="paused"] { background: #F1F3F4; border-color: #CBD1D6; color: #535B64; }
QPushButton#powerButton[state="paused"]:hover { background: #E7EBEE; border-color: #9CA8B2; }
QPushButton#btn_danger { background: #FFF6F6; color: #A54B58; border-color: #E9C3C9; }
QPushButton#btn_danger:hover { background: #FCE9EC; border-color: #D298A4; color: #8D3747; }
QComboBox {
    background: #FFFFFF; border: 1px solid #D6DCE2; border-radius: 5px;
    padding: 4px 10px; color: #242529; font-size: 12px;
}
QComboBox:hover, QComboBox:focus { border-color: #87949F; }
QComboBox:disabled { background: #F7F8F9; border-color: #E0E5E9; color: #919AA4; }
QComboBox::drop-down { border: none; width: 18px; }
QComboBox QAbstractItemView {
    background: #FFFFFF; border: 1px solid #C6CDD4; color: #242529;
    selection-background-color: #E8EDF1; selection-color: #222930; border-radius: 4px; padding: 2px;
}
QLineEdit, QKeySequenceEdit, QSpinBox, QDoubleSpinBox {
    background: #FFFFFF; color: #30363D; border: 1px solid #D6DCE2;
    border-radius: 5px; padding: 2px 8px; selection-background-color: #DCE6ED; selection-color: #20272E;
}
QLineEdit:focus, QKeySequenceEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus { border-color: #343A40; background: #FAFBFC; }
QLineEdit:disabled, QKeySequenceEdit:disabled, QSpinBox:disabled, QDoubleSpinBox:disabled { color: #919AA4; background: #F7F8F9; border-color: #E0E5E9; }
QPlainTextEdit {
    background: #FFFFFF; color: #30363D; border: 1px solid #D6DCE2; border-radius: 5px;
    padding: 5px; selection-background-color: #DCE6ED; selection-color: #20272E;
}
QPlainTextEdit:focus { border-color: #343A40; }
QPlainTextEdit:disabled { color: #919AA4; background: #F7F8F9; border-color: #E0E5E9; }
QListWidget { background: #F7F8F9; border: 1px solid #DFE4E8; border-radius: 5px; outline: none; }
QListWidget::item { color: #65707A; padding: 4px 2px; }
QListWidget::item:selected { color: #242C34; background: #E5EAEE; }
QListWidget::item:hover:!selected { background: #EFF2F4; }
QProgressBar {
    border: 1px solid #D3DBE1; border-radius: 4px; text-align: center;
    background: #FFFFFF; color: #52616D; font-weight: 500; font-size: 11px;
}
QProgressBar::chunk { background: #7B8792; border-radius: 3px; }
QMenu { background: #FFFFFF; color: #30363D; border: 1px solid #D6DDE3; border-radius: 6px; padding: 4px; }
QMenu::item { padding: 6px 24px; border-radius: 4px; }
QMenu::item:selected { background: #E9EEF2; color: #242C33; }
QMenu::separator { height: 1px; background: #E0E5E9; margin: 4px 8px; }
"""
