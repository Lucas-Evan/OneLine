"""Visual wrapping must never create real file lines or change navigation."""

from __future__ import annotations

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QInputMethodEvent, QTextCursor
from PyQt5.QtTest import QTest
from PyQt5.QtWidgets import QApplication

from editor import OneLineEditor
from window import WINDOW_HEIGHT


LONG_CHINESE = "今天下午需要完成项目测试，然后整理开发文档，并提交给负责人审核确认。" * 8


def _wrapped_editor(app):
    editor = OneLineEditor()
    editor.resize(260, editor.height())
    editor.setPlainText(LONG_CHINESE)
    editor.show()
    editor.setFocus()
    app.processEvents()
    return editor


def _caret_in_view(editor):
    caret = editor.cursorRect()
    view = editor.viewport().rect()
    assert 0 <= caret.top() and caret.bottom() <= view.bottom()
    assert 0 <= caret.left() and caret.right() <= view.right()


def test_long_chinese_text_has_visual_rows_but_one_logical_block(app):
    editor = _wrapped_editor(app)
    block = editor.document().firstBlock()
    assert editor.lineWrapMode() == OneLineEditor.WidgetWidth
    assert editor.document().blockCount() == editor.line_count() == 1
    assert block.layout().lineCount() > 2
    assert editor.toPlainText() == LONG_CHINESE
    editor.moveCursor(QTextCursor.EndOfBlock)
    app.processEvents()
    _caret_in_view(editor)


def test_saving_visual_wrap_adds_no_newlines(app, window_factory, tmp_path):
    window = window_factory()
    window.resize(350, WINDOW_HEIGHT)
    window.show()
    original = LONG_CHINESE + "\n第二个真实行"
    window.editor.setPlainText(original)
    app.processEvents()
    assert window.editor.document().firstBlock().layout().lineCount() > 1
    assert window.editor.document().blockCount() == 2

    path = tmp_path / "wrapped.txt"
    assert window._save_to_path(str(path))
    assert path.read_text(encoding="utf-8") == original
    assert path.read_text(encoding="utf-8").count("\n") == 1


def test_copy_selection_contains_no_visual_newlines(app):
    editor = _wrapped_editor(app)
    cursor = editor.textCursor()
    cursor.movePosition(QTextCursor.StartOfBlock)
    cursor.movePosition(QTextCursor.EndOfBlock, QTextCursor.KeepAnchor)
    editor.setTextCursor(cursor)
    mime_data = editor.createMimeDataFromSelection()
    assert mime_data.text() == LONG_CHINESE
    assert "\n" not in mime_data.text()


def test_up_and_down_skip_visual_rows(app):
    editor = _wrapped_editor(app)
    editor.setPlainText(LONG_CHINESE + "\n第二行\n第三行")
    editor.go_to_line(1, 8)
    app.processEvents()
    QTest.keyClick(editor, Qt.Key_Down)
    app.processEvents()
    assert editor.current_line_number() == 2
    _caret_in_view(editor)
    QTest.keyClick(editor, Qt.Key_Down)
    app.processEvents()
    assert editor.current_line_number() == 3
    QTest.keyClick(editor, Qt.Key_Up)
    app.processEvents()
    assert editor.current_line_number() == 2


def test_home_and_end_target_logical_block_edges(app):
    editor = _wrapped_editor(app)
    editor.go_to_line(1, len(LONG_CHINESE) // 2)
    app.processEvents()
    QTest.keyClick(editor, Qt.Key_Home)
    app.processEvents()
    assert editor.textCursor().positionInBlock() == 0
    _caret_in_view(editor)
    QTest.keyClick(editor, Qt.Key_End)
    app.processEvents()
    assert editor.textCursor().positionInBlock() == len(LONG_CHINESE)
    _caret_in_view(editor)


def test_window_remains_56px_after_wrap_and_width_change(app, window_factory):
    window = window_factory()
    window.show()
    window.editor.setPlainText(LONG_CHINESE)
    window.resize(320, 150)
    app.processEvents()
    assert window.height() == WINDOW_HEIGHT == 56
    assert window.editor.document().firstBlock().layout().lineCount() > 1
    assert window.editor.document().blockCount() == 1
    window.editor.moveCursor(QTextCursor.End)
    app.processEvents()
    _caret_in_view(window.editor)


def test_chinese_ime_commit_preserves_wrapped_logical_line(app):
    editor = _wrapped_editor(app)
    editor.moveCursor(QTextCursor.End)
    app.processEvents()
    QApplication.sendEvent(editor, QInputMethodEvent("输入法", []))
    app.processEvents()
    assert editor.toPlainText() == LONG_CHINESE
    _caret_in_view(editor)
    commit = QInputMethodEvent()
    commit.setCommitString("输入法")
    QApplication.sendEvent(editor, commit)
    app.processEvents()
    assert editor.toPlainText() == LONG_CHINESE + "输入法"
    assert editor.document().blockCount() == 1
    _caret_in_view(editor)
