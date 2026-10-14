"""The fixed-height editor keeps wrapped text and the native caret visible."""

from __future__ import annotations

import pytest
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QInputMethodEvent, QTextCursor
from PyQt5.QtTest import QTest
from PyQt5.QtWidgets import QApplication, QPlainTextEdit

from window import WINDOW_HEIGHT


def _assert_caret_visible(editor):
    caret = editor.cursorRect()
    viewport = editor.viewport().rect()
    assert viewport.top() <= caret.top() <= caret.bottom() <= viewport.bottom(), (
        f"caret={caret} viewport={viewport}"
    )


@pytest.mark.parametrize("size", [5_000, 10_000])
def test_wrapped_delete_empty_retype_and_chinese_ime_keep_caret_visible(
    app, window_factory, size
):
    window = window_factory()
    window.resize(300, WINDOW_HEIGHT)
    window.show()
    editor = window.editor
    editor.setFocus()
    editor.setPlainText("a" * size)
    editor.moveCursor(QTextCursor.End)
    app.processEvents()

    assert window.height() == 56
    assert editor.lineWrapMode() == QPlainTextEdit.WidgetWidth
    assert editor.document().documentMargin() == 0
    assert editor.document().firstBlock().layout().lineCount() > 10
    assert editor.viewport().height() > editor.fontMetrics().lineSpacing()
    # Programmatic setPlainText/moveCursor does not necessarily scroll Qt's
    # native viewport. The regression target is visibility during user edits.

    # Each checkpoint crosses another visual row, without changing the block.
    for index in range(300):
        QTest.keyClick(editor, Qt.Key_Backspace)
        if index % 30 == 29:
            app.processEvents()
            _assert_caret_visible(editor)
    assert editor.toPlainText() == "a" * (size - 300)
    assert editor.document().blockCount() == 1

    QTest.keyClick(editor, Qt.Key_A, Qt.ControlModifier)
    QTest.keyClick(editor, Qt.Key_Backspace)
    assert editor.toPlainText() == ""
    _assert_caret_visible(editor)
    QTest.keyClicks(editor, "abc")
    assert editor.toPlainText() == "abc"
    _assert_caret_visible(editor)

    QApplication.sendEvent(editor, QInputMethodEvent("候选", []))
    commit = QInputMethodEvent()
    commit.setCommitString("中文")
    QApplication.sendEvent(editor, commit)
    app.processEvents()
    assert editor.toPlainText() == "abc中文"
    assert editor.document().blockCount() == 1
    assert "\n" not in editor.toPlainText()
    assert window.height() == 56
    _assert_caret_visible(editor)


@pytest.mark.parametrize("font_size", [12, 20, 24])
def test_font_size_keeps_one_row_editor_inside_56px_window(
    app, window_factory, font_size
):
    window = window_factory()
    window._set_font_size(font_size, persist=False)
    window.show()
    app.processEvents()
    editor = window.editor

    assert window.height() == 56
    assert editor.document().documentMargin() == 0
    assert editor.height() == editor.fontMetrics().lineSpacing() + 10
    assert editor.viewport().height() > editor.fontMetrics().lineSpacing()
    assert editor.viewport().height() < 2 * editor.fontMetrics().lineSpacing()
    _assert_caret_visible(editor)


@pytest.mark.parametrize("fill_editor", [False, True])
@pytest.mark.parametrize("input_method", ["setPlainText", "insertPlainText"])
def test_programmatic_long_text_position_probe(
    app, window_factory, fill_editor, input_method
):
    """Record whether space alone fixes Qt's separate initial-position issue."""
    window = window_factory()
    window.resize(300, WINDOW_HEIGHT)
    window.show()
    editor = window.editor
    if fill_editor:
        editor.setMinimumHeight(0)
        editor.setMaximumHeight(16_777_215)
        window._panel.layout().activate()
    editor.setFocus()
    getattr(editor, input_method)("中文" * 2_500)
    editor.moveCursor(QTextCursor.End)
    app.processEvents()
    caret = editor.cursorRect()
    viewport = editor.viewport().rect()
    visible = viewport.top() <= caret.top() and caret.bottom() <= viewport.bottom()
    assert editor.document().blockCount() == 1
    assert window.height() == 56
    print(
        f"initial-position fill={fill_editor} method={input_method} "
        f"viewport_height={viewport.height()} caret_top={caret.top()} visible={visible}"
    )
