from __future__ import annotations

from PyQt5.QtCore import QMimeData, Qt
from PyQt5.QtTest import QTest

from editor import OneLineEditor
from window import WINDOW_HEIGHT


def test_document_keeps_one_hundred_lines(app):
    editor = OneLineEditor()
    content = "\n".join(f"第 {number} 行" for number in range(1, 101))
    editor.setPlainText(content)
    editor.show()
    editor.go_to_line(100)
    app.processEvents()

    assert editor.line_count() == 100
    assert editor.toPlainText() == content
    assert editor.current_line_number() == 100
    assert editor.verticalScrollBar().value() == 99
    assert 0 <= editor.cursorRect().top() < editor.viewport().height()
    assert editor.height() <= editor.fontMetrics().lineSpacing() + 10


def test_up_and_down_move_between_document_lines(app):
    editor = OneLineEditor()
    editor.setPlainText("第一行\n第二行\n第三行")
    editor.show()
    editor.go_to_line(2)
    app.processEvents()

    assert editor.verticalScrollBar().value() == 1
    assert 0 <= editor.cursorRect().top() < editor.viewport().height()

    QTest.keyClick(editor, Qt.Key_Down)
    app.processEvents()
    assert editor.current_line_number() == 3

    QTest.keyClick(editor, Qt.Key_Up)
    app.processEvents()
    assert editor.current_line_number() == 2


def test_multiline_paste_preserves_text(app):
    editor = OneLineEditor()
    pasted = "中文第一行\nline two\n第三行包含，。！？"
    mime_data = QMimeData()
    mime_data.setText(pasted)
    editor.insertFromMimeData(mime_data)

    assert editor.toPlainText() == pasted
    assert editor.line_count() == 3


def test_long_line_wraps_visually_and_keeps_cursor_visible(app):
    editor = OneLineEditor()
    editor.resize(300, editor.height())
    editor.setPlainText("很长的文字" * 100)
    editor.moveCursor(editor.textCursor().End)
    editor.show()
    app.processEvents()

    assert editor.lineWrapMode() == OneLineEditor.WidgetWidth
    assert editor.document().blockCount() == 1
    assert editor.document().firstBlock().layout().lineCount() > 1
    assert editor.horizontalScrollBar().maximum() == 0
    assert editor.verticalScrollBar().value() > 0
    assert editor.cursorRect().bottom() <= editor.viewport().rect().bottom()


def test_window_is_a_fixed_height_strip(app, window_factory):
    window = window_factory()

    assert WINDOW_HEIGHT == 56
    assert window.height() == WINDOW_HEIGHT
    assert window.minimumHeight() == WINDOW_HEIGHT
    assert window.maximumHeight() == WINDOW_HEIGHT
    assert window.minimumWidth() == 300
