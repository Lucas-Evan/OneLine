"""Compact settings dialog for the floating editor."""

from __future__ import annotations

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont, QKeySequence
from PyQt5.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QFontComboBox,
    QFormLayout,
    QKeySequenceEdit,
    QLabel,
    QMessageBox,
    QSlider,
    QSpinBox,
    QVBoxLayout,
)

from settings import SettingsStore


class PreferencesDialog(QDialog):
    def __init__(self, settings: SettingsStore, current_font: QFont, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("OneLine 设置")
        self.setModal(True)
        form = QFormLayout()

        self.font_family = QFontComboBox(self)
        self.font_family.setCurrentFont(current_font)
        form.addRow("编辑字体", self.font_family)

        self.font_size = QSpinBox(self)
        self.font_size.setRange(11, 22)
        self.font_size.setValue(settings.font_size())
        self.font_size.setSuffix(" px")
        form.addRow("字体大小", self.font_size)

        self.opacity = QSlider(Qt.Horizontal, self)
        self.opacity.setRange(75, 100)
        self.opacity.setValue(round(settings.opacity() * 100))
        self.opacity_value = QLabel(f"{self.opacity.value()}%", self)
        self.opacity.valueChanged.connect(
            lambda value: self.opacity_value.setText(f"{value}%")
        )
        opacity_row = QVBoxLayout()
        opacity_row.addWidget(self.opacity)
        opacity_row.addWidget(self.opacity_value)
        form.addRow("窗口不透明度", opacity_row)

        self.restore_session = QCheckBox("启动时恢复上次会话", self)
        self.restore_session.setChecked(settings.restore_session())
        form.addRow("会话", self.restore_session)

        self.start_on_top = QCheckBox("启动时始终置顶", self)
        self.start_on_top.setChecked(settings.always_on_top())
        form.addRow("窗口", self.start_on_top)

        self.dark_mode = QCheckBox("深色模式", self)
        self.dark_mode.setChecked(settings.theme() == "dark")
        form.addRow("外观", self.dark_mode)

        self.hide_shortcut = QKeySequenceEdit(self)
        self.hide_shortcut.setKeySequence(QKeySequence(settings.hide_shortcut()))
        form.addRow("隐藏快捷键", self.hide_shortcut)

        buttons = QDialogButtonBox(
            QDialogButtonBox.Save | QDialogButtonBox.Cancel, parent=self
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout = QVBoxLayout(self)
        layout.addLayout(form)
        hint = QLabel("隐藏后可从系统托盘或任务栏恢复窗口。", self)
        hint.setStyleSheet("color: #64748b; font-size: 11px;")
        layout.addWidget(hint)
        layout.addWidget(buttons)

    def accept(self) -> None:
        shortcut = self.hide_shortcut.keySequence()
        reserved = (
            "Ctrl+N", "Ctrl+O", "Ctrl+S", "Ctrl+Shift+S", "Ctrl+F",
            "Ctrl+Shift+T", "Ctrl+Q", "Esc", "Meta+N", "Meta+O",
            "Meta+S", "Meta+Shift+S", "Meta+F", "Meta+Shift+T", "Meta+Q",
        )
        has_modifier = bool(
            not shortcut.isEmpty()
            and shortcut[0] & int(Qt.CTRL | Qt.ALT | Qt.META)
        )
        if not has_modifier or any(shortcut == QKeySequence(value) for value in reserved):
            QMessageBox.warning(self, "快捷键不可用", "请选择一个未被常用操作占用的快捷键。")
            return
        super().accept()
