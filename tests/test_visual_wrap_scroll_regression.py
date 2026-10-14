"""Regression tests for viewport anchoring after wrapped-line deletion."""

from __future__ import annotations

import logging

import pytest
from PyQt5.QtCore import QEvent, Qt
from PyQt5.QtGui import QInputMethodEvent, QKeyEvent, QTextCursor
from PyQt5.QtTest import QTest
from PyQt5.QtWidgets import QApplication, QPlainTextEdit

from window import WINDOW_HEIGHT


def _repeat_backspace(editor, count):
    for _ in range(count):
        QApplication.sendEvent(
            editor,
            QKeyEvent(QEvent.KeyPress, Qt.Key_Backspace, Qt.NoModifier, "", True, 1),
        )


def _settle_cursor_sync(app, editor):
    for _ in range(4):
        app.processEvents()
        if not editor._post_delete_sync_timer.isActive() and not editor._cursor_sync_timer.isActive():
            break
    if editor._cursor_sync_timer.isActive():
        QTest.qWait(editor._cursor_sync_timer.interval() + 20)
    assert not editor._post_delete_sync_timer.isActive()
    assert not editor._cursor_sync_timer.isActive()


def _assert_caret_visible(editor):
    caret = editor.cursorRect()
    viewport = editor.viewport().rect()
    bar = editor.verticalScrollBar()
    detail = (
        f"caret={caret} viewport={viewport} scroll={bar.value()} "
        f"range=({bar.minimum()},{bar.maximum()}) "
        f"sync_active={editor._cursor_sync_timer.isActive()} "
        f"post_delete_active={editor._post_delete_sync_timer.isActive()}"
    )
    assert viewport.top() <= caret.top() <= caret.bottom() <= viewport.bottom(), detail
    assert viewport.left() <= caret.left() < viewport.right()


def test_wrapped_10k_delete_back_to_first_rows_type_and_undo(
    app, window_factory, monkeypatch
):
    window = window_factory()
    window.resize(300, WINDOW_HEIGHT)
    window.show()
    editor = window.editor
    editor.setFocus()
    ensure_calls = []
    monkeypatch.setattr(editor, "ensureCursorVisible", lambda: ensure_calls.append(1))
    editor.setPlainText("a" * 10_000)
    editor.moveCursor(QTextCursor.End)
    app.processEvents()

    assert window.height() == WINDOW_HEIGHT == 56
    assert editor.lineWrapMode() == QPlainTextEdit.WidgetWidth
    assert editor.verticalScrollBarPolicy() == Qt.ScrollBarAlwaysOff
    assert not editor.verticalScrollBar().isVisible()
    assert editor.document().blockCount() == 1
    assert editor.document().firstBlock().layout().lineCount() > 100
    _assert_caret_visible(editor)

    # Delete from the last wrapped row into the middle of the same logical line.
    _repeat_backspace(editor, 5_000)
    editor.flush_pending_delete()
    _settle_cursor_sync(app, editor)
    assert editor.toPlainText() == "a" * 5_000
    assert editor.textCursor().position() == 5_000
    _assert_caret_visible(editor)

    # Shrinking the document to its first wrapped rows used to leave Qt's
    # scroll anchor stale: the scrollbar was clamped but the caret stayed below
    # the 19-pixel editor viewport, even after ensureCursorVisible().
    _repeat_backspace(editor, 4_900)
    editor.flush_pending_delete()
    _settle_cursor_sync(app, editor)
    assert editor.toPlainText() == "a" * 100
    assert editor.textCursor().position() == 100
    _assert_caret_visible(editor)

    _repeat_backspace(editor, 90)
    editor.flush_pending_delete()
    _settle_cursor_sync(app, editor)
    assert editor.toPlainText() == "a" * 10
    assert editor.textCursor().position() == 10
    _assert_caret_visible(editor)

    editor.insertPlainText("继续")
    _settle_cursor_sync(app, editor)
    assert editor.toPlainText() == "a" * 10 + "继续"
    _assert_caret_visible(editor)

    editor.undo()
    _settle_cursor_sync(app, editor)
    assert editor.toPlainText() == "a" * 10
    _assert_caret_visible(editor)
    editor.undo()
    _settle_cursor_sync(app, editor)
    assert editor.toPlainText() == "a" * 100
    _assert_caret_visible(editor)
    editor.undo()
    _settle_cursor_sync(app, editor)
    assert editor.toPlainText() == "a" * 5_000
    _assert_caret_visible(editor)
    assert editor.document().blockCount() == 1
    assert "\n" not in editor.toPlainText()
    assert window.height() == 56
    assert ensure_calls == []


def test_visible_cursor_does_not_force_scroll_or_requeue_sync(
    app, window_factory
):
    window = window_factory()
    window.show()
    editor = window.editor
    editor.setPlainText("short")
    app.processEvents()
    before = editor.verticalScrollBar().value()
    editor._schedule_cursor_sync()
    _settle_cursor_sync(app, editor)
    assert editor.verticalScrollBar().value() == before
    assert not editor._cursor_sync_timer.isActive()


def test_delete_selection_from_middle_of_wrapped_logical_line(app, window_factory):
    window = window_factory()
    window.resize(300, WINDOW_HEIGHT)
    window.show()
    editor = window.editor
    editor.setPlainText("a" * 3_000 + "中" * 4_000 + "b" * 3_000)
    cursor = editor.textCursor()
    cursor.setPosition(3_000)
    cursor.setPosition(7_000, QTextCursor.KeepAnchor)
    editor.setTextCursor(cursor)
    app.processEvents()

    QApplication.sendEvent(
        editor, QKeyEvent(QEvent.KeyPress, Qt.Key_Backspace, Qt.NoModifier)
    )
    _settle_cursor_sync(app, editor)
    assert editor.toPlainText() == "a" * 3_000 + "b" * 3_000
    assert editor.textCursor().position() == 3_000
    assert editor.document().blockCount() == 1
    _assert_caret_visible(editor)


def test_batch_delete_schedules_one_post_edit_sync(app, window_factory):
    window = window_factory()
    window.resize(300, WINDOW_HEIGHT)
    window.show()
    editor = window.editor
    editor.setPlainText("a" * 10_000)
    editor.moveCursor(QTextCursor.End)
    app.processEvents()
    calls = []
    editor._cursor_sync_timer.timeout.connect(lambda: calls.append(1))
    _repeat_backspace(editor, 9_900)
    editor.flush_pending_delete()
    assert editor._post_delete_sync_timer.isActive()
    assert not editor._cursor_sync_timer.isActive()
    _settle_cursor_sync(app, editor)
    assert len(calls) == 1
    _assert_caret_visible(editor)


def test_single_batch_from_10k_to_first_visual_row(app, window_factory):
    window = window_factory()
    window.resize(300, WINDOW_HEIGHT)
    window.show()
    editor = window.editor
    editor.setPlainText("a" * 10_000)
    editor.moveCursor(QTextCursor.End)
    app.processEvents()

    _repeat_backspace(editor, 9_990)
    editor.flush_pending_delete()
    _settle_cursor_sync(app, editor)
    assert editor.toPlainText() == "a" * 10
    assert editor.document().firstBlock().layout().lineCount() == 1
    _assert_caret_visible(editor)


def test_ten_visual_rows_shrink_one_row_at_a_time(app, window_factory):
    window = window_factory()
    window.resize(300, WINDOW_HEIGHT)
    window.show()
    editor = window.editor
    editor.setFocus()
    editor.setPlainText("长句" * 90)
    editor.moveCursor(QTextCursor.End)
    app.processEvents()
    assert editor.document().firstBlock().layout().lineCount() >= 10

    # Exercise native single-key edits, not only the held-key batch path.
    for _ in range(150):
        QApplication.sendEvent(
            editor, QKeyEvent(QEvent.KeyPress, Qt.Key_Backspace, Qt.NoModifier)
        )
        app.processEvents()
        assert editor.textCursor().position() == len(editor.toPlainText())
    _settle_cursor_sync(app, editor)
    _assert_caret_visible(editor)
    assert editor.toPlainText() == "长句" * 15
    assert editor.document().blockCount() == 1
    assert window.height() == 56


def test_wrapped_chinese_ime_preedit_candidate_and_commit(app, window_factory):
    window = window_factory()
    window.resize(300, WINDOW_HEIGHT)
    window.show()
    editor = window.editor
    editor.setFocus()
    editor.setPlainText("今天需要完成项目测试并整理文档" * 100)
    editor.moveCursor(QTextCursor.End)
    app.processEvents()
    original = editor.toPlainText()

    QApplication.sendEvent(editor, QInputMethodEvent("候选", []))
    assert editor._ime_event_depth == 0
    assert editor._ime_preedit_active
    assert not editor._cursor_sync_timer.isActive()
    app.processEvents()
    assert editor.toPlainText() == original

    commit = QInputMethodEvent()
    commit.setCommitString("输入")
    QApplication.sendEvent(editor, commit)
    assert editor._ime_event_depth == 0
    assert not editor._ime_preedit_active
    assert editor._cursor_sync_timer.isActive()
    _settle_cursor_sync(app, editor)
    assert editor.toPlainText() == original + "输入"
    assert editor.document().blockCount() == 1
    _assert_caret_visible(editor)


def test_scroll_debug_log_has_geometry_but_no_document_text(
    app, window_factory, caplog
):
    window = window_factory()
    window.show()
    editor = window.editor
    editor.setPlainText("private-document-marker")
    app.processEvents()

    with caplog.at_level(logging.DEBUG, logger="editor"):
        editor._schedule_cursor_sync()
        _settle_cursor_sync(app, editor)

    messages = "\n".join(record.getMessage() for record in caplog.records)
    assert "cursor=" in messages
    assert "rect=" in messages
    assert "viewport_height=" in messages
    assert "scrollbar=" in messages
    assert "range=" in messages
    assert "private-document-marker" not in messages


@pytest.mark.parametrize("settle_before_typing", [False, True])
def test_select_all_delete_to_empty_then_immediately_type_ascii(
    app, window_factory, monkeypatch, settle_before_typing
):
    window = window_factory()
    window.resize(300, WINDOW_HEIGHT)
    window.show()
    editor = window.editor
    editor.setFocus()
    editor.setPlainText("a" * 10_000)
    editor.moveCursor(QTextCursor.End)
    app.processEvents()
    assert editor.document().firstBlock().layout().lineCount() > 10

    original_rect = editor.cursorRect
    empty_rect_calls = []

    def track_empty_rect():
        if editor.document().isEmpty():
            empty_rect_calls.append(1)
        return original_rect()

    monkeypatch.setattr(editor, "cursorRect", track_empty_rect)
    QTest.keyClick(editor, Qt.Key_A, Qt.ControlModifier)
    QTest.keyClick(editor, Qt.Key_Backspace)
    assert editor.document().isEmpty()
    if settle_before_typing:
        _settle_cursor_sync(app, editor)
    assert empty_rect_calls == []
    if settle_before_typing:
        assert editor.verticalScrollBar().value() == 0
    QTest.keyClicks(editor, "abc")
    app.processEvents()
    assert editor.toPlainText() == "abc"
    assert editor.textCursor().position() == 3
    assert editor.document().blockCount() == 1
    assert window.height() == 56
    _assert_caret_visible(editor)


def test_empty_after_wrapped_delete_accepts_chinese_ime(app, window_factory):
    window = window_factory()
    window.resize(300, WINDOW_HEIGHT)
    window.show()
    editor = window.editor
    editor.setFocus()
    editor.setPlainText("中文长句" * 2_000)
    editor.moveCursor(QTextCursor.End)
    app.processEvents()

    QTest.keyClick(editor, Qt.Key_A, Qt.ControlModifier)
    QTest.keyClick(editor, Qt.Key_Backspace)
    assert editor.document().isEmpty()
    _settle_cursor_sync(app, editor)
    assert editor.verticalScrollBar().value() == 0
    QApplication.sendEvent(editor, QInputMethodEvent("zhongwen", []))
    commit = QInputMethodEvent()
    commit.setCommitString("中文")
    QApplication.sendEvent(editor, commit)
    app.processEvents()
    assert editor.toPlainText() == "中文"
    assert editor.document().blockCount() == 1
    _assert_caret_visible(editor)


def test_absolute_visual_row_counts_wrapped_blocks_without_changing_newlines(
    app, window_factory
):
    window = window_factory()
    window.resize(300, WINDOW_HEIGHT)
    window.show()
    editor = window.editor
    editor.setPlainText("a" * 100 + "\n" + "b" * 100)
    editor.moveCursor(QTextCursor.End)
    app.processEvents()

    first = editor.document().firstBlock()
    second = first.next()
    expected = first.layout().lineCount() + second.layout().lineCount() - 1
    assert editor._cursor_visual_row() == expected
    assert editor.document().blockCount() == 2
    assert editor.toPlainText().count("\n") == 1
