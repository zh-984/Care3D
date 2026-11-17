"""Shared desktop theme. Geometry stays in the existing widget layouts."""

ACCENT = "#78C9C0"
TEXT = "#DCE5EF"
MUTED = "#8C9DB0"

STYLESHEET = """
QWidget {
    background: transparent;
    color: #DCE5EF;
    font-family: 'Microsoft YaHei UI', 'Segoe UI', 'Microsoft YaHei', sans-serif;
    font-size: 12px;
}
QWidget#care3dSettings, QDialog { background: #0D141F; }
QLabel { background: transparent; border: none; }
QToolTip {
    color: #E3ECF5; background: #213040; border: 1px solid #41576A;
    padding: 6px 9px;
}
QFrame#headerPanel {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #182431, stop:1 #121D2A);
    border: 1px solid #2A3B4D; border-radius: 8px; padding: 6px 10px;
}
QLabel#brandWordmark { color: #ECF2F8; font-size: 16px; font-weight: 600; }
QLabel#productBadge {
    background: #1C3440; color: #A8D2D9; border: 1px solid #304F5B;
    font-size: 10px; font-weight: 500; padding: 2px 6px; border-radius: 4px;
}
QLabel#headerDescription { color: #91A4B7; font-size: 11px; }
QFrame#noticePanel {
    background: #18232E; border: 1px solid #304353; border-radius: 6px; padding: 4px 8px;
}
QLabel#noticeText { color: #ACBCCB; font-size: 11px; }
QPushButton#retopButton { padding: 2px 8px; font-size: 11px; border-radius: 4px; }
QFrame#footerPanel {
    background: #111D2A; border: 1px solid #27384A; border-radius: 6px; padding: 6px 10px;
}
QFrame.compact_card {
    background: #162230; border: 1px solid #2B3A4C; border-radius: 8px; padding: 8px 10px;
}
QLabel#parameterLabel { color: #D5DFEB; font-size: 12px; font-weight: 500; }
QLabel#valueBadge {
    background: #152B35; color: #ACE1D9; font-size: 11px; font-weight: 600;
    padding: 2px 4px; border: 1px solid #33525C; border-radius: 4px;
}
QLabel#profileStatus { color: #92A6B9; font-size: 11px; }
QScrollArea { border: none; background: transparent; }
QScrollBar:vertical, QScrollBar:horizontal { background: #111C28; border-radius: 3px; }
QScrollBar:vertical { width: 6px; }
QScrollBar::handle:vertical, QScrollBar::handle:horizontal { background: #6FAFC6; border-radius: 3px; }
QScrollBar::handle:vertical { min-height: 20px; }
QScrollBar::handle:hover { background: #A2DDD8; }
QScrollBar::handle:pressed { background: #62C5BD; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0px; }
QScrollBar::add-page, QScrollBar::sub-page { background: transparent; }
QTabWidget::pane {
    background: #101B28; border: 1px solid #28394B; border-radius: 8px; top: -1px;
}
QTabBar::tab {
    background: #101B28; border: 1px solid #28394B; border-bottom: none;
    color: #95A8BC; padding: 7px 16px; margin-right: 4px;
    border-top-left-radius: 6px; border-top-right-radius: 6px;
    font-size: 12px; font-weight: 500;
}
QTabBar::tab:hover { color: #D8E9EC; background: #1A2B38; }
QTabBar::tab:selected {
    color: #AFE3DA; background: #1C303A; font-weight: 600; border-top: 2px solid #78C9C0;
}
QSlider::groove:horizontal { height: 5px; background: #2B3A4C; border-radius: 2px; }
QSlider::sub-page:horizontal {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #438E99, stop:1 #80C7BE);
    border-radius: 2px;
}
QSlider::handle:horizontal {
    background: #D9EEE9; border: 2px solid #6CB6B1; width: 14px;
    margin-top: -5px; margin-bottom: -5px; border-radius: 7px;
}
QSlider::handle:horizontal:hover { background: #F0FCF8; border-color: #AFE6DC; }
QSlider::handle:horizontal:pressed { background: #B3E3D8; border-color: #78C9C0; }
QSlider::groove:horizontal:disabled { background: #24313F; }
QSlider::sub-page:horizontal:disabled { background: #344B56; }
QSlider::handle:horizontal:disabled { background: #6A7B89; border-color: #4B606B; }
QCheckBox { background: transparent; spacing: 8px; color: #DCE5EF; font-weight: 600; font-size: 13px; }
QCheckBox::indicator { width: 17px; height: 17px; border-radius: 4px; border: 1px solid #4A6175; background: #172634; }
QCheckBox::indicator:hover { border-color: #8BCFC6; background: #203B46; }
QCheckBox::indicator:checked { background: #78C9C0; border-color: #92DED0; }
QCheckBox:disabled { color: #78899A; }
QCheckBox::indicator:disabled { background: #1A2734; border-color: #344657; }
QCheckBox::indicator:checked:disabled { background: #526F74; border-color: #617E83; }
QPushButton {
    background: #1E2D3C; color: #D6E2ED; border: 1px solid #3A4D60;
    border-radius: 5px; padding: 5px 12px; font-size: 12px; font-weight: 500;
}
QPushButton:hover { background: #293F4E; border-color: #6B969F; color: #F1F8F8; }
QPushButton:pressed { background: #152B37; border-color: #84C9C0; }
QPushButton:focus { border-color: #80C7BE; }
QPushButton:disabled { background: #182432; border-color: #2C3C4B; color: #697D91; }
QPushButton[role="profile"] {
    background: #142230; border: 1px solid #304455; border-radius: 6px;
    padding: 7px 6px; font-size: 11px; font-weight: 500; color: #A7B8C8;
}
QPushButton[role="profile"]:hover { background: #203542; color: #D8EDEB; border-color: #6B969F; }
QPushButton[role="profile"]:checked { background: #203D45; color: #BEEADD; border-color: #77BEB6; font-weight: 600; }
QPushButton#powerButton { padding: 5px 14px; border-radius: 13px; }
QPushButton#powerButton[state="running"] { background: #1A3C36; border-color: #3C7B68; color: #B2E8D1; }
QPushButton#powerButton[state="running"]:hover { background: #245246; border-color: #78B49B; }
QPushButton#powerButton[state="paused"] { background: #27313D; border-color: #526375; color: #C7D4DF; }
QPushButton#powerButton[state="paused"]:hover { background: #354454; border-color: #8A9EAF; }
QPushButton#btn_danger { background: #30252D; color: #D8ACB4; border-color: #64414D; }
QPushButton#btn_danger:hover { background: #44303B; border-color: #A36A7B; color: #F2D3D8; }
QComboBox {
    background: #132331; border: 1px solid #3A4F62; border-radius: 5px;
    padding: 4px 10px; color: #DCE5EF; font-size: 12px;
}
QComboBox:hover, QComboBox:focus { border-color: #78BDB7; }
QComboBox:disabled { background: #182431; border-color: #2D3F50; color: #71869A; }
QComboBox::drop-down { border: none; width: 18px; }
QComboBox QAbstractItemView {
    background: #1B2D3C; border: 1px solid #526F7D; color: #DCE5EF;
    selection-background-color: #2A555B; selection-color: #E3F9EF; border-radius: 4px; padding: 2px;
}
QLineEdit, QKeySequenceEdit, QSpinBox, QDoubleSpinBox {
    background: #12212F; color: #DDE7F0; border: 1px solid #3A4F62;
    border-radius: 5px; padding: 2px 8px; selection-background-color: #32676D; selection-color: #EDFFF8;
}
QLineEdit:focus, QKeySequenceEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus { border-color: #80C7BE; background: #172E3A; }
QLineEdit:disabled, QKeySequenceEdit:disabled, QSpinBox:disabled, QDoubleSpinBox:disabled { color: #71869A; background: #182431; border-color: #2D3F50; }
QPlainTextEdit {
    background: #12212F; color: #D9E4EE; border: 1px solid #3A4F62; border-radius: 5px;
    padding: 5px; selection-background-color: #32676D; selection-color: #EDFFF8;
}
QPlainTextEdit:focus { border-color: #80C7BE; }
QPlainTextEdit:disabled { color: #71869A; background: #182431; border-color: #2D3F50; }
QListWidget { background: #121F2D; border: 1px solid #2B4053; border-radius: 5px; outline: none; }
QListWidget::item { color: #9DAFC1; padding: 4px 2px; }
QListWidget::item:selected { color: #C4EADF; background: #24434B; }
QListWidget::item:hover:!selected { background: #1D3342; }
QProgressBar {
    border: 1px solid #344B5C; border-radius: 4px; text-align: center;
    background: #101E2B; color: #C7DFE5; font-weight: 500; font-size: 11px;
}
QProgressBar::chunk { background: #4D989F; border-radius: 3px; }
QMenu { background: #172635; color: #DAE5EF; border: 1px solid #3A5062; border-radius: 6px; padding: 4px; }
QMenu::item { padding: 6px 24px; border-radius: 4px; }
QMenu::item:selected { background: #294E57; color: #E3F8EF; }
QMenu::separator { height: 1px; background: #334B5E; margin: 4px 8px; }
"""
