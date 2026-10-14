"""Stage 3.5 checks for the compact window's visual controls."""

from __future__ import annotations

import sys

from PyQt5.QtCore import QPoint, QTimer, Qt
from PyQt5.QtGui import QKeySequence
from PyQt5.QtTest import QTest

from window import QuickMenuButton, WINDOW_HEIGHT


def _open_menu_by_click(app, window):
    menu = window.menu_button.menu()
    observed = {}

    def observe_and_close():
        observed.update(visible=menu.isVisible(), geometry=menu.geometry())
        menu.hide()

    # InstantPopup may enter a nested event loop; observe it while open and
    # close it from that loop instead of waiting for mouseClick to return.
    QTimer.singleShot(50, observe_and_close)
    QTest.mouseClick(window.menu_button, Qt.LeftButton)
    QTest.qWait(60)
    return observed


def test_menu_button_click_opens_quick_menu(app, window_factory, monkeypatch):
    window = window_factory()
    window.resize(600, WINDOW_HEIGHT)
    window.move(QPoint(80, 80))
    window.show()
    app.processEvents()

    assert isinstance(window.menu_button, QuickMenuButton)
    assert window.menu_button.text() == "⋯"
    assert window.menu_button.width() == 24
    idle_image = window.menu_button.grab().toImage()
    sample = (round(12 * idle_image.devicePixelRatio()), round(4 * idle_image.devicePixelRatio()))
    idle = idle_image.pixelColor(*sample)
    # Synthetic pointer movement is not reflected by underMouse() on every
    # platform, so exercise the hover paint state directly.
    monkeypatch.setattr(window.menu_button, "underMouse", lambda: True)
    hover = window.menu_button.grab().toImage().pixelColor(*sample)
    assert hover != idle
    monkeypatch.setattr(window.menu_button, "underMouse", lambda: False)
    assert _open_menu_by_click(app, window)["visible"]


def test_menu_popup_stays_anchored_to_button(app, window_factory):
    window = window_factory()
    window.resize(600, WINDOW_HEIGHT)
    window.move(QPoint(80, 80))
    window.show()
    app.processEvents()

    popup = _open_menu_by_click(app, window)["geometry"]
    button = window.menu_button
    upper_left = button.mapToGlobal(QPoint(0, 0))
    lower_right = button.mapToGlobal(QPoint(button.width(), button.height()))
    vertical_gap = min(
        abs(popup.top() - lower_right.y()),
        abs(popup.bottom() - upper_left.y()),
    )
    assert vertical_gap <= 12
    assert popup.left() <= lower_right.x()
    assert popup.right() >= upper_left.x()


def test_flat_menu_displays_platform_shortcuts(app, window_factory):
    window = window_factory()
    actions = {
        action.text(): action
        for action in window.menu_button.menu().actions()
        if not action.isSeparator()
    }
    expected = {
        "新建": "N",
        "打开…": "O",
        "保存": "S",
        "另存为…": "S",
        "查找…": "F",
        "始终置顶": "T",
        "退出": "Q",
    }
    for label, key in expected.items():
        native = actions[label].shortcut().toString(QKeySequence.NativeText)
        assert key in native
        if sys.platform == "darwin":
            assert "⌘" in native
        else:
            assert "Ctrl" in native
        if label in ("另存为…", "始终置顶"):
            assert ("⇧" if sys.platform == "darwin" else "Shift") in native


def test_light_and_dark_themes_render_single_line(app, window_factory):
    window = window_factory()
    window.show()
    window.editor.setPlainText("一行内容")
    app.processEvents()

    light = window.grab().toImage()
    ratio = light.devicePixelRatio()
    assert light.width() == round(window.width() * ratio)
    assert light.height() == round(WINDOW_HEIGHT * ratio)
    assert abs(window.editor.geometry().center().y() - window._panel.rect().center().y()) <= 4
    assert window.editor.cursorRect().height() <= window.editor.viewport().height()

    window.toggle_theme()
    app.processEvents()
    dark = window.grab().toImage()
    assert dark.width() == light.width()
    assert dark.height() == round(WINDOW_HEIGHT * dark.devicePixelRatio())
    light_panel = light.pixelColor(round(100 * ratio), round(5 * ratio))
    dark_panel = dark.pixelColor(
        round(100 * dark.devicePixelRatio()), round(5 * dark.devicePixelRatio())
    )
    assert light_panel.lightness() > dark_panel.lightness()
    assert window.menu_button.menu().actions()
