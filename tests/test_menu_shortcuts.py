"""Qt, not action labels, renders the platform shortcut column."""

from __future__ import annotations

import sys

from PyQt5.QtGui import QKeySequence
from PyQt5.QtWidgets import QStyleOptionMenuItem

import window as window_module


SHORTCUTS = {
    "新建": "Ctrl+N",
    "打开…": "Ctrl+O",
    "保存": "Ctrl+S",
    "另存为…": "Ctrl+Shift+S",
    "查找…": "Ctrl+F",
    "始终置顶": "Ctrl+Shift+T",
    "退出": "Ctrl+Q",
}


def _menu_actions(window):
    return {action.text(): action for action in window.menu_button.menu().actions()}


def test_menu_actions_expose_native_shortcut_column(app, window_factory):
    window = window_factory()
    menu = window.menu_button.menu()
    window.show()
    menu.show()
    app.processEvents()
    actions = _menu_actions(window)
    for label in SHORTCUTS:
        action = actions[label]
        assert action.isShortcutVisibleInContextMenu()
        assert action.shortcut().count()
        assert "\t" not in action.text()  # No manually appended hints.
        assert menu.actionGeometry(action).width() > 0
    menu.hide()


def test_macos_shortcut_mapping_uses_command_glyphs(app, window_factory):
    if sys.platform != "darwin":
        return  # NativeText can only be verified on an actual macOS Qt build.
    actions = _menu_actions(window_factory())
    for label, portable in SHORTCUTS.items():
        assert actions[label].shortcut().toString(QKeySequence.PortableText) == portable
        native = actions[label].shortcut().toString(QKeySequence.NativeText)
        assert "⌘" in native
        assert portable[-1] in native
        if "Shift" in portable:
            assert "⇧" in native


def test_linux_shortcut_mapping_keeps_ctrl_primary(app, window_factory, monkeypatch):
    with monkeypatch.context() as patch:
        patch.setattr(window_module.sys, "platform", "linux")
        actions = _menu_actions(window_factory())
    for label, portable in SHORTCUTS.items():
        action = actions[label]
        assert action.shortcut().toString(QKeySequence.PortableText) == portable
        assert len(action.shortcuts()) == 1
        assert action.isShortcutVisibleInContextMenu()


def test_shortcut_column_is_visually_muted_in_both_themes(app, window_factory):
    window = window_factory()
    window.show()
    menu = window.menu_button.menu()
    action = _menu_actions(window)["新建"]

    def foreground_lightnesses():
        menu.show()
        app.processEvents()
        option = QStyleOptionMenuItem()
        menu.initStyleOption(option, action)
        rect = menu.actionGeometry(action)
        image = menu.grab().toImage()
        scale = image.width() / menu.width()

        def values(left, right):
            return [
                image.pixelColor(int(x * scale), int(y * scale)).lightness()
                for x in range(left, right)
                for y in range(rect.top() + 3, rect.bottom() - 2)
            ]

        label = values(rect.left() + 20, rect.left() + 100)
        shortcut = values(
            rect.right() - option.tabWidth - 42,
            rect.right() - 30,
        )
        menu.hide()
        return label, shortcut

    label, shortcut = foreground_lightnesses()
    assert min(shortcut) > min(label) + 40

    window.toggle_theme()
    label, shortcut = foreground_lightnesses()
    assert max(label) > max(shortcut) + 40
