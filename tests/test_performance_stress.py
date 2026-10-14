"""Regression checks for large wrapped blocks and fast deletion bursts."""

from __future__ import annotations

from PyQt5.QtCore import QEvent, Qt
from PyQt5.QtGui import QInputMethodEvent, QKeyEvent, QTextCursor
from PyQt5.QtTest import QTest
from PyQt5.QtWidgets import QApplication

from editor import OneLineEditor
from window import WINDOW_HEIGHT


LONG_TEXT = "中" * 50_000


def _editor(app):
    editor = OneLineEditor()
    editor.resize(500, editor.height())
    editor.show()
    editor.setFocus()
    app.processEvents()
    return editor


def _repeat_backspace(editor, count):
    for _ in range(count):
        QApplication.sendEvent(
            editor,
            QKeyEvent(QEvent.KeyPress, Qt.Key_Backspace, Qt.NoModifier, "", True, 1),
        )


def test_cursor_sync_has_only_one_pending_task(app):
    editor = _editor(app)
    calls = []
    editor._cursor_sync_timer.timeout.connect(lambda: calls.append(1))
    for _ in range(10_000):
        editor._schedule_cursor_sync()
    assert editor._cursor_sync_timer.isActive()
    QTest.qWait(editor._cursor_sync_timer.interval() + 20)
    assert len(calls) == 1
    assert not editor._cursor_sync_timer.isActive()


def test_50k_insert_delete_and_continue_typing(app):
    editor = _editor(app)
    editor.insertPlainText(LONG_TEXT)
    app.processEvents()
    assert len(editor.toPlainText()) == 50_000
    assert editor.document().blockCount() == 1
    assert editor.document().firstBlock().layout().lineCount() > 1
    QTest.keyClick(editor, Qt.Key_A, Qt.ControlModifier)
    QTest.keyClick(editor, Qt.Key_Backspace)
    app.processEvents()
    assert editor.toPlainText() == ""
    QTest.keyClicks(editor, "ok")
    app.processEvents()
    assert editor.toPlainText() == "ok"


def test_50k_auto_repeat_delete_batches_and_undo_redo(app):
    editor = _editor(app)
    editor.insertPlainText(LONG_TEXT)
    app.processEvents()
    _repeat_backspace(editor, 500)
    assert editor._pending_delete_count == 500
    assert len(editor.toPlainText()) == 50_000
    editor.flush_pending_delete()
    app.processEvents()
    assert editor.toPlainText() == LONG_TEXT[:-500]
    for _ in range(3):
        editor.undo()
        assert editor.toPlainText() == LONG_TEXT
        editor.redo()
        assert editor.toPlainText() == LONG_TEXT[:-500]
    assert editor.document().blockCount() == 1


def test_auto_repeat_flushes_after_short_idle_period(app):
    editor = _editor(app)
    editor.insertPlainText("甲" * 1000)
    app.processEvents()
    _repeat_backspace(editor, 10)
    QTest.qWait(100)
    assert editor.toPlainText() == "甲" * 990
    assert editor._pending_delete_count == 0


def test_long_chinese_ime_and_visual_wrap(app):
    editor = _editor(app)
    editor.insertPlainText("中文" * 25_000)
    app.processEvents()
    assert editor.document().firstBlock().layout().lineCount() > 1
    QApplication.sendEvent(editor, QInputMethodEvent("输入", []))
    app.processEvents()
    assert editor.toPlainText() == "中文" * 25_000
    commit = QInputMethodEvent()
    commit.setCommitString("输入")
    QApplication.sendEvent(editor, commit)
    app.processEvents()
    assert editor.toPlainText() == "中文" * 25_000 + "输入"
    assert editor.document().blockCount() == 1
    assert 0 <= editor.cursorRect().top() < editor.viewport().height()


def test_ime_commit_flushes_pending_delete_in_order(app):
    editor = _editor(app)
    editor.setPlainText("中文😀")
    editor.moveCursor(QTextCursor.End)
    app.processEvents()
    _repeat_backspace(editor, 1)
    commit = QInputMethodEvent()
    commit.setCommitString("输入")
    QApplication.sendEvent(editor, commit)
    app.processEvents()
    assert editor.toPlainText() == "中文输入"
    assert editor._pending_delete_count == 0


def test_cursor_only_move_does_not_schedule_full_session(app, window_factory):
    window = window_factory()
    window.show()
    window.editor.insertPlainText(LONG_TEXT)
    app.processEvents()
    window._write_session()
    window._session_timer.stop()
    window.editor.moveCursor(QTextCursor.Start)
    app.processEvents()
    assert not window._session_timer.isActive()
    window.hide_window()
    snapshot = window.sessions.load()
    assert snapshot is not None
    assert snapshot.cursor == 0
    assert snapshot.text == LONG_TEXT


def test_saving_50k_wrapped_text_flushes_pending_deletion(
    app, window_factory, tmp_path
):
    window = window_factory()
    window.show()
    window.editor.insertPlainText(LONG_TEXT)
    app.processEvents()
    _repeat_backspace(window.editor, 500)
    path = tmp_path / "stress.txt"
    assert window._save_to_path(str(path))
    assert path.read_text(encoding="utf-8") == LONG_TEXT[:-500]
    assert "\n" not in path.read_text(encoding="utf-8")
    assert window.height() == WINDOW_HEIGHT == 56
