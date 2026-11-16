"""Opt-in extensions, kept separate from the original settings tabs."""
import copy
import json
import platform

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QKeySequence
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QFormLayout, QLabel,
    QPushButton, QLineEdit, QDoubleSpinBox, QSpinBox, QListWidget, QStackedWidget,
    QScrollArea, QMessageBox, QFileDialog, QPlainTextEdit, QColorDialog, QKeySequenceEdit,
    QApplication, QFrame)
from core.config import valid_rectangles
from core.hotkey_manager import valid_shortcut
from core.preset_library import atomic_json
from ui.settings_window import MarkedCheckBox, NoWheelComboBox
from ui.extension_widgets import OverlayPreview, SetupGuide


class OptionalPanel(QWidget):
    def __init__(self, settings, library, controller):
        super().__init__(settings)
        self.settings, self.manager = settings, settings.cfg_mgr
        self.library, self.controller = library, controller
        self.loading = True
        self.fields, self.pages, self.previews = {}, {}, []
        root = QVBoxLayout(self)
        hint = QLabel("按需勾选，新增功能默认关闭。避让、布局与临时增强参数随当前方案保存；其他开关为共用设置。")
        hint.setWordWrap(True)
        root.addWidget(hint)
        row = QHBoxLayout()
        self.navigation = QListWidget()
        self.navigation.setFixedWidth(108)
        self.navigation.setStyleSheet("QListWidget::item { padding: 4px 2px; } QListWidget::item:selected { background: #0369A1; color: white; }")
        self.stack = QStackedWidget()
        row.addWidget(self.navigation)
        row.addWidget(self.stack, 1)
        root.addLayout(row, 1)
        self._games()
        self._safe_areas()
        self._comfort()
        self._guide()
        self._layout()
        self._gamepad()
        self._controls()
        self._sessions()
        self._assistant()
        self.navigation.currentRowChanged.connect(self.stack.setCurrentIndex)
        self.navigation.setCurrentRow(0)
        self.load()

    def page(self, name, flag, description):
        page = QWidget()
        outer = QVBoxLayout(page)
        check = MarkedCheckBox("启用" + name)
        self.fields[flag] = (check, 1)
        outer.addWidget(check)
        hint = QLabel(description)
        hint.setWordWrap(True)
        outer.addWidget(hint)
        body = QWidget()
        layout = QVBoxLayout(body)
        layout.setContentsMargins(0, 8, 0, 0)
        outer.addWidget(body)
        outer.addStretch()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(page)
        self.navigation.addItem(name)
        self.stack.addWidget(scroll)
        self.pages[flag] = body
        check.toggled.connect(lambda value, k=flag: self.put(k, value))
        return layout

    def put(self, key, value):
        if self.loading:
            return
        setattr(self.manager.config, key, copy.deepcopy(value))
        if key in self.pages:
            self.pages[key].setEnabled(bool(value))
        self.settings._optional_changed()
        self.refresh_previews()
        self.refresh_runtime()

    def check(self, layout, label, key):
        widget = MarkedCheckBox(label)
        widget.toggled.connect(lambda value: self.put(key, value))
        self.fields[key] = (widget, 1)
        layout.addWidget(widget)
        return widget

    def spin(self, layout, label, key, lower, upper, scale=1, suffix="", decimals=0):
        row = QHBoxLayout()
        text = QLabel(label)
        text.setWordWrap(True)
        row.addWidget(text, 1)
        widget = QDoubleSpinBox() if decimals else QSpinBox()
        if decimals:
            widget.setDecimals(decimals)
            widget.setSingleStep(0.05 if scale == 1 else 1)
        widget.setRange(lower, upper)
        widget.setSuffix(suffix)
        widget.setMinimumWidth(115)
        widget.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        widget.valueChanged.connect(lambda value: self.put(key, value / scale if decimals or scale != 1 else value))
        self.fields[key] = (widget, scale)
        row.addWidget(widget)
        layout.addLayout(row)
        return widget

    def combo(self, layout, label, key, options):
        row = QHBoxLayout()
        row.addWidget(QLabel(label), 1)
        widget = NoWheelComboBox()
        for text, value in options:
            widget.addItem(text, value)
        widget.currentIndexChanged.connect(lambda: self.put(key, widget.currentData()))
        self.fields[key] = (widget, 1)
        row.addWidget(widget, 1)
        layout.addLayout(row)
        return widget

    def button(self, layout, label, action):
        button = QPushButton(label)
        button.clicked.connect(action)
        layout.addWidget(button)
        return button

    def message(self, text, error=False):
        (QMessageBox.warning if error else QMessageBox.information)(self, "Care3D", str(text))

    def perform(self, action, success=""):
        try:
            result = action()
            if result is False:
                raise OSError("保存失败，请检查配置目录权限。原有方案保留。")
            if success:
                self.message(success)
            return result
        except (OSError, ValueError, KeyError) as error:
            self.message(error, True)
            return None

    def _games(self):
        layout = self.page("游戏方案", "game_library_enabled", "为不同游戏保留独立的四套参数。关闭此功能或点击返回，即恢复原来的通用方案。")
        self.game_list = NoWheelComboBox()
        layout.addWidget(self.game_list)
        self.game_status = QLabel()
        self.game_status.setTextFormat(Qt.TextFormat.PlainText)
        self.game_status.setWordWrap(True)
        layout.addWidget(self.game_status)
        self.game_name = QLineEdit()
        self.game_name.setMaxLength(80)
        self.game_name.setPlaceholderText("新方案名称，例如：我的冒险游戏")
        layout.addWidget(self.game_name)
        self.match_title = QLineEdit()
        self.match_title.setMaxLength(512)
        self.match_title.setPlaceholderText("窗口标题关键字（可留空，留空时手动切换）")
        layout.addWidget(self.match_title)
        self.button(layout, "使用系统页已选择的窗口标题", lambda: self.match_title.setText(self.manager.config.target_window_title))
        self.button(layout, "复制当前参数为新游戏方案", self.create_game)
        row = QHBoxLayout()
        self.button(row, "加载所选", self.load_game)
        self.button(row, "返回通用方案", self.leave_game)
        self.button(row, "删除所选", self.delete_game)
        layout.addLayout(row)
        row = QHBoxLayout()
        self.button(row, "导入方案", self.import_game)
        self.button(row, "导出所选", self.export_game)
        layout.addLayout(row)
        self.check(layout, "按前台窗口标题自动切换（多个匹配时保持原状）", "game_auto_switch_enabled")
        self.button(layout, "更新所选方案的匹配标题", self.update_match)

    def refresh_games(self, selected=None):
        selected = selected or self.game_list.currentData()
        self.game_list.blockSignals(True)
        self.game_list.clear()
        for ident, entry in self.library.entries.items():
            self.game_list.addItem(entry["name"], ident)
        index = self.game_list.findData(selected)
        if index >= 0:
            self.game_list.setCurrentIndex(index)
        self.game_list.blockSignals(False)
        entry = self.library.entries.get(self.library.active_id)
        self.game_status.setText(self.library.error or ("当前：" + entry["name"] if entry else "当前：原来的通用方案"))

    def create_game(self):
        ident = self.perform(lambda: self.library.create(self.game_name.text(), self.match_title.text()))
        if ident:
            self.game_name.clear()
            self.refresh_games(ident)

    def load_game(self):
        self.settings.save_timer.stop()
        if self.perform(lambda: self.library.activate(self.game_list.currentData())):
            self.settings._load_values_to_ui()

    def leave_game(self):
        self.settings.save_timer.stop()
        if self.perform(self.library.deactivate):
            self.settings._load_values_to_ui()

    def delete_game(self):
        ident = self.game_list.currentData()
        if not ident:
            return
        if QMessageBox.question(self, "删除游戏方案", "仅删除所选游戏方案，原来的通用方案会保留。继续吗？",
                                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                QMessageBox.StandardButton.No) == QMessageBox.StandardButton.Yes:
            if self.perform(lambda: self.library.delete(ident)):
                self.settings._load_values_to_ui()

    def import_game(self):
        path, _ = QFileDialog.getOpenFileName(self, "导入 Care3D 方案", "", "Care3D 方案 (*.json)")
        if path:
            ident = self.perform(lambda: self.library.import_preset(path))
            self.refresh_games(ident)

    def export_game(self):
        ident = self.game_list.currentData()
        if not ident:
            return
        path, _ = QFileDialog.getSaveFileName(self, "导出方案（不含窗口标题与备注）", "Care3D-preset.json", "JSON (*.json)")
        if path:
            self.perform(lambda: self.library.export_preset(ident, path), "方案已导出。")

    def update_match(self):
        ident = self.game_list.currentData()
        if ident:
            if self.perform(lambda: self.library.update_match(ident, self.match_title.text())):
                self.settings._load_values_to_ui()
                self.message("匹配标题已保存，已绑定游戏的方案也会更新绑定标题。请避免过于宽泛的关键字。")

    def _safe_areas(self):
        layout = self.page("画面避让", "safe_zones_enabled", "框选字幕、小地图等区域，暗角和所有参照都会避开它们。只在下方示意图中编辑，不拦截游戏操作。最多 16 个区域。")
        self.safe_preview = OverlayPreview(self.manager.config, editable=True)
        self.previews.append(self.safe_preview)
        self.safe_preview.areas_changed.connect(self.set_areas)
        self.safe_preview.selection_changed.connect(self.select_area)
        layout.addWidget(self.safe_preview)
        row = QHBoxLayout()
        self.button(row, "添加字幕区", lambda: self.add_area(dict(x=.16, y=.78, w=.68, h=.18, label="字幕")))
        self.button(row, "左上角", lambda: self.add_area(dict(x=0, y=0, w=.22, h=.25, label="左上 HUD")))
        self.button(row, "右上角", lambda: self.add_area(dict(x=.78, y=0, w=.22, h=.25, label="右上 HUD")))
        layout.addLayout(row)
        self.area_list = NoWheelComboBox()
        self.area_list.currentIndexChanged.connect(self.select_area)
        layout.addWidget(self.area_list)
        self.area_fields = {}
        form = QFormLayout()
        self.area_label = QLineEdit()
        self.area_label.setMaxLength(40)
        self.area_label.editingFinished.connect(self.edit_area)
        form.addRow("名称", self.area_label)
        for label, key in (("左侧位置", "x"), ("顶部位置", "y"), ("宽度", "w"), ("高度", "h")):
            spin = QDoubleSpinBox()
            spin.setDecimals(1)
            spin.setRange(0 if key in ("x", "y") else 1, 100)
            spin.setSuffix("%")
            spin.valueChanged.connect(self.edit_area)
            self.area_fields[key] = spin
            form.addRow(label, spin)
        layout.addLayout(form)
        self.button(layout, "删除当前区域", self.remove_area)

    def set_areas(self, areas):
        self.put("safe_zones", valid_rectangles(areas))
        self.refresh_areas(self.safe_preview.selected)

    def add_area(self, area):
        areas = copy.deepcopy(self.manager.config.safe_zones)
        if len(areas) >= 16:
            self.message("最多支持 16 个避让区域。")
            return
        areas.append(area)
        self.set_areas(areas)
        self.refresh_areas(len(areas) - 1)

    def refresh_areas(self, index=None):
        index = self.area_list.currentIndex() if index is None else index
        self.area_list.blockSignals(True)
        self.area_list.clear()
        for i, area in enumerate(self.manager.config.safe_zones):
            self.area_list.addItem(f"{i + 1}. {area['label']}", i)
        self.area_list.setCurrentIndex(min(max(index, 0), self.area_list.count() - 1))
        self.area_list.blockSignals(False)
        self.select_area(self.area_list.currentIndex())

    def select_area(self, index):
        if index < 0 or index >= len(self.manager.config.safe_zones):
            return
        previous = self.loading
        self.loading = True
        area = self.manager.config.safe_zones[index]
        self.area_list.setCurrentIndex(index)
        self.area_label.setText(area["label"])
        for key, widget in self.area_fields.items():
            widget.setValue(area[key] * 100)
        self.safe_preview.selected = index
        self.safe_preview.update()
        self.loading = previous

    def edit_area(self):
        if self.loading:
            return
        index = self.area_list.currentIndex()
        areas = copy.deepcopy(self.manager.config.safe_zones)
        if 0 <= index < len(areas):
            areas[index] = {key: widget.value() / 100 for key, widget in self.area_fields.items()}
            areas[index]["label"] = self.area_label.text() or "避让区域"
            self.set_areas(areas)

    def remove_area(self):
        areas = copy.deepcopy(self.manager.config.safe_zones)
        index = self.area_list.currentIndex()
        if 0 <= index < len(areas):
            del areas[index]
            self.set_areas(areas)

    def _comfort(self):
        layout = self.page("临时增强", "comfort_enabled", "适合过场、观战等没有鼠标输入的场景。启用后可按 Ctrl+Alt+B 切换固定遮挡；再次切换即恢复。运行状态不会写入保存参数。")
        self.spin(layout, "固定遮挡不透明度", "comfort_alpha", 0, 95, 100, "%")
        self.spin(layout, "固定清晰区半径", "comfort_inner_radius", 20, 85, 100, "%")
        self.comfort_status = QLabel()
        layout.addWidget(self.comfort_status)
        self.button(layout, "切换临时增强 / 恢复原状", self.toggle_comfort)
        self.comfort_preview = OverlayPreview(self.manager.config)
        self.comfort_preview.comfort = True
        self.previews.append(self.comfort_preview)
        layout.addWidget(self.comfort_preview)
        hint = QLabel("主开关优先。自定义按键和按住模式可在“操作与界面”中启用；切换参数方案会结束临时增强。")
        hint.setWordWrap(True)
        layout.addWidget(hint)

    def toggle_comfort(self):
        if self.settings.overlay_ref:
            self.settings.overlay_ref.toggle_comfort()
        self.refresh_runtime()

    def _guide(self):
        layout = self.page("设置向导", "guide_enabled", "先用静态示意比较起点，再选择是否应用。鼠标校准只调整输入响应，不检测症状，也不要求快速转动游戏镜头。")
        self.button(layout, "打开设置向导（可预览、可取消）", self.open_guide)

    def open_guide(self):
        dialog = SetupGuide(self.manager.config, self.settings.mouse_tracker, self)
        if dialog.exec() == dialog.DialogCode.Accepted:
            for key, value in dialog.result_values.get("settings", {}).items():
                setattr(self.manager.config, key, value)
            self.settings._load_values_to_ui()
            self.settings._optional_changed()

    def _layout(self):
        layout = self.page("参照布局", "layout_enabled", "原来的参照样式保留。此选项允许分别隐藏各边的圆点和三角形，调整四根细柱的位置，并额外选择静态细边框或水平线。")
        row = QHBoxLayout()
        self.side_checks = {}
        for text, side in (("上", "top"), ("下", "bottom"), ("左", "left"), ("右", "right")):
            check = MarkedCheckBox(text + "边")
            check.toggled.connect(self.change_sides)
            row.addWidget(check)
            self.side_checks[side] = check
        layout.addLayout(row)
        self.spin(layout, "边缘参照内缩", "layout_margin", 1, 15, 100, "%")
        self.column_spins = []
        for index in range(4):
            row = QHBoxLayout()
            row.addWidget(QLabel(f"细柱 {index + 1} 横向位置"), 1)
            spin = QDoubleSpinBox()
            spin.setDecimals(1)
            spin.setRange(1.5, 98.5)
            spin.setSuffix("%")
            spin.valueChanged.connect(self.change_columns)
            self.column_spins.append(spin)
            row.addWidget(spin)
            layout.addLayout(row)
        self.button(layout, "将四根细柱恢复为均分位置", lambda: self.reset_columns())
        self.combo(layout, "额外固定参照", "layout_style", (("不额外添加", "none"), ("细边框", "frame"), ("静态水平线", "horizon")))
        self.spin(layout, "额外参照线宽", "layout_line_width", 1, 6, suffix=" px")
        self.spin(layout, "额外参照可见度", "layout_alpha", 5, 80, 100, "%")
        self.button(layout, "选择额外参照颜色", self.pick_layout_color)
        self.layout_preview = OverlayPreview(self.manager.config)
        self.previews.append(self.layout_preview)
        layout.addWidget(self.layout_preview)

    def change_sides(self):
        self.put("layout_sides", [side for side, check in self.side_checks.items() if check.isChecked()])

    def change_columns(self):
        self.put("layout_column_positions", [spin.value() / 100 for spin in self.column_spins])

    def reset_columns(self):
        self.put("layout_column_positions", [.125, .375, .625, .875])
        self.load()

    def pick_layout_color(self):
        color = QColorDialog.getColor(QColor(self.manager.config.layout_color), self, "选择额外参照颜色")
        if color.isValid():
            self.put("layout_color", color.name())

    def _gamepad(self):
        layout = self.page("手柄响应", "gamepad_tuning_enabled", "仅调整 XInput 输入响应。需要同时开启原有“系统与屏幕”页中的手柄动态增强；Steam Input 请输出 XInput。")
        self.combo(layout, "使用的摇杆", "gamepad_stick", (("右摇杆", "right"), ("左摇杆", "left")))
        self.combo(layout, "手柄编号", "gamepad_device", (("自动检测", -1), ("手柄 1", 0), ("手柄 2", 1), ("手柄 3", 2), ("手柄 4", 3)))
        self.spin(layout, "摇杆死区", "gamepad_deadzone", 2, 60, 100, "%")
        self.spin(layout, "响应曲线指数", "gamepad_curve", .4, 3, decimals=2)
        hint = QLabel("指数大于 1 时小幅操作更柔和，小于 1 时小幅操作更明显。手柄断开会停止增强，不改变游戏输入。")
        hint.setWordWrap(True)
        layout.addWidget(hint)

    def _controls(self):
        layout = self.page("操作与界面", "controls_enabled", "可自定义主开关、临时增强和四套方案轮换的快捷键。快捷键只控制 Care3D，不向游戏发送按键。")
        self.key_edits = {}
        for label, key in (("主开关", "controls_toggle_key"), ("临时增强", "controls_comfort_key"), ("轮换四套方案", "controls_profile_key")):
            row = QHBoxLayout()
            row.addWidget(QLabel(label), 1)
            edit = QKeySequenceEdit()
            edit.setMaximumSequenceLength(1)
            self.key_edits[key] = edit
            row.addWidget(edit, 1)
            layout.addLayout(row)
        self.button(layout, "应用以上快捷键", self.apply_shortcuts)
        self.check(layout, "临时增强使用按住模式（松开即恢复）", "controls_comfort_hold")
        self.check(layout, "启用手柄组合键：Back+Start 开关，Back+Y 临时增强", "controls_gamepad_enabled")
        # Font/value editing has its own independent switch.
        page_outer = self.pages["controls_enabled"].parentWidget().layout()
        access = MarkedCheckBox("启用界面辅助（独立于上方快捷键开关）")
        access.toggled.connect(lambda value: self.put("accessibility_enabled", value))
        self.fields["accessibility_enabled"] = (access, 1)
        page_outer.insertWidget(page_outer.count() - 1, access)
        body = QWidget()
        access_layout = QVBoxLayout(body)
        self.combo(access_layout, "字体与控件缩放", "font_scale", (("100%", 100), ("125%", 125), ("150%", 150)))
        text = QLabel("开启后，原参数页的蓝色数值可双击输入，也可用 Tab 聚焦后按 Enter 编辑。滑块依然可用。")
        text.setWordWrap(True)
        access_layout.addWidget(text)
        page_outer.insertWidget(page_outer.count() - 1, body)
        self.pages["accessibility_enabled"] = body

    @staticmethod
    def display_shortcut(value):
        replacements = {"<ctrl>": "Ctrl", "<alt>": "Alt", "<shift>": "Shift", "<cmd>": "Meta"}
        for before, after in replacements.items():
            value = value.replace(before, after)
        return value.replace("<", "").replace(">", "").upper()

    def apply_shortcuts(self):
        values = {}
        for key, edit in self.key_edits.items():
            tokens = edit.keySequence().toString(QKeySequence.SequenceFormat.PortableText).lower().split("+")
            modifiers = {"ctrl": "<ctrl>", "alt": "<alt>", "shift": "<shift>", "meta": "<cmd>"}
            value = "+".join(modifiers.get(token, f"<{token}>" if token.startswith("f") and token[1:].isdigit() else token) for token in tokens)
            if not valid_shortcut(value):
                self.message("每组快捷键需包含 Ctrl / Alt / Shift 等修饰键，以及一个普通键或功能键。", True)
                return
            values[key] = value
        if len(set(values.values())) != len(values):
            self.message("三组快捷键不能重复。", True)
            return
        for key, value in values.items():
            setattr(self.manager.config, key, value)
        self.settings._optional_changed()
        self.message("快捷键已应用。可关闭本页开关恢复原主开关快捷键。")

    def _sessions(self):
        layout = self.page("计时记录", "session_tools_enabled", "手动开始计时；主开关暂停或绑定游戏失去焦点时不累计。记录和提醒分别选择，默认不保存使用记录。")
        self.check(layout, "启用休息提醒（托盘提示，可随时关闭）", "break_reminder_enabled")
        self.spin(layout, "提醒间隔", "break_minutes", 5, 180, suffix=" 分钟")
        self.check(layout, "启用本地体验记录（仅点击记录时保存）", "session_recording_enabled")
        self.session_status = QLabel()
        layout.addWidget(self.session_status)
        row = QHBoxLayout()
        self.button(row, "开始新计时", lambda: self.controller.start_session() if self.controller else None)
        self.button(row, "暂停", lambda: self.controller.pause_session() if self.controller else None)
        self.button(row, "继续", lambda: self.controller.resume_session() if self.controller else None)
        layout.addLayout(row)
        self.feeling = NoWheelComboBox()
        self.feeling.addItems(("舒服些", "没变化", "更难受"))
        layout.addWidget(self.feeling)
        self.session_note = QLineEdit()
        self.session_note.setMaxLength(500)
        self.session_note.setPlaceholderText("可选备注；不要填写个人敏感信息")
        layout.addWidget(self.session_note)
        self.button(layout, "记录本次感受并结束计时", self.record_session)
        self.history = QPlainTextEdit()
        self.history.setReadOnly(True)
        self.history.setMinimumHeight(120)
        layout.addWidget(self.history)
        self.button(layout, "导出本地体验记录", self.export_history)
        self.button(layout, "清空本地体验记录", self.clear_history)

    def record_session(self):
        if self.controller and self.perform(lambda: self.controller.record_session(self.feeling.currentText(), self.session_note.text())) is not None:
            self.session_note.clear()
        self.refresh_history()

    def refresh_history(self):
        if not self.controller:
            self.history.setPlainText("运行程序后可使用计时和记录。")
            return
        try:
            rows = self.controller.records()
            text = "\n".join(f"{row.get('time', '')} · {row.get('name', '')} · {int(row.get('seconds', 0)) // 60} 分钟 · {row.get('feeling', '')}" for row in rows[-10:])
            self.history.setPlainText(text or "尚无本地记录。记录用于个人比较，不能证明缓解效果。")
        except (OSError, ValueError, TypeError) as error:
            self.history.setPlainText(str(error))

    def export_history(self):
        if not self.controller:
            return
        path, _ = QFileDialog.getSaveFileName(self, "导出体验记录（含个人备注，请自行检查）", "Care3D-history.json", "JSON (*.json)")
        if path:
            self.perform(lambda: atomic_json(path, self.controller.records()), "记录已导出。")

    def clear_history(self):
        if self.controller and QMessageBox.question(self, "清空体验记录", "只清空本机的体验记录，已导出的文件保留。继续吗？",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No) == QMessageBox.StandardButton.Yes:
            self.perform(lambda: atomic_json(self.controller.records_path, []))
            self.refresh_history()

    def _assistant(self):
        layout = self.page("游戏建议", "game_assistant_enabled", "在游戏自身设置中检查下列项目。Care3D 不会修改游戏设置或文件；FOV 应结合屏幕和观看距离调整，不是越大越好。")
        text = QLabel("• 检查能否关闭或降低运动模糊、镜头晃动、走路颠簸和武器摆动。\n• 检查自动镜头回正、冲刺时的 FOV 变化和镜头灵敏度。\n• 使用适合自己的视角和稳定的游戏帧率，并逐项比较。\n• 当前覆盖层不能消除游戏已经渲染出来的镜头运动。")
        text.setWordWrap(True)
        layout.addWidget(text)
        self.assistant_notes = QPlainTextEdit()
        self.assistant_notes.setPlaceholderText("记下这个游戏里适合自己的设置；使用游戏方案库时，备注也分别保存。")
        self.assistant_notes.setMinimumHeight(140)
        self.assistant_notes.textChanged.connect(lambda: self.put("game_assistant_notes", self.assistant_notes.toPlainText()[:4000]))
        layout.addWidget(self.assistant_notes)
        self.button(layout, "生成运行状态摘要", self.diagnostics)
        self.diagnostics_text = QPlainTextEdit()
        self.diagnostics_text.setReadOnly(True)
        self.diagnostics_text.setMinimumHeight(110)
        layout.addWidget(self.diagnostics_text)
        self.button(layout, "复制摘要（不含窗口标题或个人路径）", lambda: QApplication.clipboard().setText(self.diagnostics_text.toPlainText()))

    def diagnostics(self):
        cfg = self.manager.config
        screen = QApplication.primaryScreen()
        geometry = screen.geometry() if screen else None
        text = ["Care3D 可选功能版", "Windows: " + platform.version(),
                "输入: " + self.settings.mouse_tracker.input_source,
                "主开关: " + ("开启" if cfg.overlay_visible else "暂停"),
                "游戏窗口绑定: " + ("开启" if cfg.only_target_window else "关闭"),
                "配置自动保存: " + ("等待保存" if self.settings.save_timer.isActive() else "空闲"),
                "主屏逻辑尺寸: " + (f"{geometry.width()}x{geometry.height()}" if geometry else "不可用"),
                "独占全屏与游戏规则需自行确认。"]
        self.diagnostics_text.setPlainText("\n".join(text))

    def refresh_previews(self):
        for preview in self.previews:
            if not preview._drag:
                preview.set_config(self.manager.config)

    def refresh_runtime(self):
        overlay = self.settings.overlay_ref
        active = overlay is not None and overlay._comfort_active
        self.comfort_status.setText("当前：临时增强运行中" if active else "当前：原来的动态响应")
        if self.controller:
            seconds = int(self.controller.session_elapsed)
            self.session_status.setText(f"{'计时中' if self.controller.session_running else '已暂停'} · {seconds // 60:02d}:{seconds % 60:02d}")
        else:
            self.session_status.setText("计时未启动")

    def load(self):
        self.loading = True
        try:
            cfg = self.manager.config
            for key, (widget, scale) in self.fields.items():
                value = getattr(cfg, key)
                if isinstance(widget, MarkedCheckBox):
                    widget.setChecked(value)
                elif isinstance(widget, NoWheelComboBox):
                    widget.setCurrentIndex(widget.findData(value))
                else:
                    widget.setValue(round(value * scale) if isinstance(widget, QSpinBox) else value * scale)
            for key, body in self.pages.items():
                body.setEnabled(bool(getattr(cfg, key)))
            for side, check in self.side_checks.items():
                check.setChecked(side in cfg.layout_sides)
            for widget, value in zip(self.column_spins, cfg.layout_column_positions):
                widget.setValue(value * 100)
            for key, edit in self.key_edits.items():
                edit.setKeySequence(QKeySequence(self.display_shortcut(getattr(cfg, key))))
            self.assistant_notes.setPlainText(cfg.game_assistant_notes)
            self.refresh_games()
            self.refresh_areas()
            self.refresh_previews()
            self.refresh_history()
            self.refresh_runtime()
        finally:
            self.loading = False
