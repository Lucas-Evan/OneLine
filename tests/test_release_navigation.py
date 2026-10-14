"""Release navigation checks for the current Qt-native editor architecture."""

from __future__ import annotations

import os
import pytest
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QInputMethodEvent
from PyQt5.QtTest import QTest
from PyQt5.QtWidgets import QApplication

from session import Session


LONG_LINE = "中" * 800


def _geometry(editor, overlay):
    """Diagnostic geometry only; never capture document contents."""
    caret = editor.cursorRect()
    viewport = editor.viewport().rect()
    bar = editor.verticalScrollBar()
    return {
        "cursor": (caret.x(), caret.y(), caret.width(), caret.height()),
        "viewport": (viewport.x(), viewport.y(), viewport.width(), viewport.height()),
        "scroll": (bar.value(), bar.minimum(), bar.maximum()),
        "overlay": (overlay.isVisible(), overlay._top_mask_height, overlay._bottom_mask_y),
    }


def _assert_current_row_visible(editor, overlay):
    state = _geometry(editor, overlay)
    caret = editor.cursorRect()
    viewport = editor.viewport().rect()
    assert viewport.intersects(caret), state
    assert overlay.isVisible(), state
    assert overlay._top_mask_height == max(0, caret.top()), state
    assert overlay._bottom_mask_y == min(viewport.height(), caret.bottom() + 1), state


def _window_with_wrap(app, window_factory):
    window = window_factory()
    window.resize(300, 56)
    window.show()
    window.editor.setFocus()
    window.editor.setPlainText("开头\n" + LONG_LINE + "\n结尾")
    app.processEvents()
    assert window.editor.document().findBlockByNumber(1).layout().lineCount() >= 5
    return window


def _close(window):
    window.editor.document().setModified(False)
    window.tray_icon.hide()
    window.close()


def test_release_navigation_across_visual_and_logical_lines(app, window_factory):
    window = _window_with_wrap(app, window_factory)
    try:
        editor = window.editor
        overlay = window.visual_line_overlay
        editor.go_to_line(2, 400)
        app.processEvents()
        _assert_current_row_visible(editor, overlay)

        previous_scroll = editor.verticalScrollBar().value()
        scroll_steps = []
        for key in ([Qt.Key_Left] * 35) + ([Qt.Key_Right] * 35):
            QTest.keyClick(editor, key)
            app.processEvents()
            _assert_current_row_visible(editor, overlay)
            current_scroll = editor.verticalScrollBar().value()
            scroll_steps.append(abs(current_scroll - previous_scroll))
            previous_scroll = current_scroll
        assert max(scroll_steps) <= 1, scroll_steps
        for key, line in (
            (Qt.Key_Home, 2), (Qt.Key_End, 2),
            (Qt.Key_Up, 1), (Qt.Key_Down, 2),
        ):
            QTest.keyClick(editor, key)
            app.processEvents()
            assert editor.current_line_number() == line
            _assert_current_row_visible(editor, overlay)
    finally:
        _close(window)


@pytest.mark.skipif(
    os.environ.get("QT_QPA_PLATFORM") == "offscreen",
    reason="离屏 Qt 插件的程序性光标滚动几何不同；须在 Cocoa/X11 图形后端验证",
)
@pytest.mark.parametrize("position", [400, 799])
def test_release_session_restores_visible_caret_in_long_line(
    app, window_factory, position
):
    first = window_factory()
    first.sessions.save(
        Session(LONG_LINE, position, None, True, window_width=300)
    )
    restored = window_factory()
    try:
        restored.show()
        app.processEvents()
        assert restored.editor.textCursor().position() == position
        _assert_current_row_visible(restored.editor, restored.visual_line_overlay)
    finally:
        _close(restored)
        _close(first)


def test_release_resize_font_ime_and_empty_retype_keep_overlay(
    app, window_factory
):
    window = _window_with_wrap(app, window_factory)
    try:
        editor = window.editor
        overlay = window.visual_line_overlay
        editor.go_to_line(2, 500)
        app.processEvents()
        for width in (500, 300):
            window.resize(width, 56)
            app.processEvents()
            QTest.keyClick(editor, Qt.Key_Right)
            app.processEvents()
            _assert_current_row_visible(editor, overlay)
        window._set_font_size(18)
        app.processEvents()
        QTest.keyClick(editor, Qt.Key_Right)
        app.processEvents()
        _assert_current_row_visible(editor, overlay)

        QApplication.sendEvent(editor, QInputMethodEvent("拼", []))
        app.processEvents()
        _assert_current_row_visible(editor, overlay)
        QApplication.sendEvent(editor, QInputMethodEvent("", []))
        QTest.keyClick(editor, Qt.Key_A, Qt.ControlModifier)
        QTest.keyClick(editor, Qt.Key_Backspace)
        QTest.keyClicks(editor, "abc")
        app.processEvents()
        assert editor.toPlainText() == "abc"
        _assert_current_row_visible(editor, overlay)
    finally:
        _close(window)
