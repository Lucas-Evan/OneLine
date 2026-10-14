"""Input ordering after large wrapped deletions and during IME composition."""

from __future__ import annotations

from PyQt5.QtCore import QEvent, Qt
from PyQt5.QtGui import QInputMethodEvent, QKeyEvent, QTextCursor
from PyQt5.QtTest import QTest
from PyQt5.QtWidgets import QApplication

from window import WINDOW_HEIGHT


def _window(app, window_factory):
    window = window_factory()
    window.resize(300, WINDOW_HEIGHT)
    window.show()
    window.editor.setFocus()
    app.processEvents()
    return window


def _caret_visible(editor):
    caret = editor.cursorRect()
    viewport = editor.viewport().rect()
    return viewport.top() <= caret.top() and caret.bottom() <= viewport.bottom()


def _repeat_backspace(editor, count):
    for _ in range(count):
        QApplication.sendEvent(
            editor,
            QKeyEvent(QEvent.KeyPress, Qt.Key_Backspace, Qt.NoModifier, "", True, 1),
        )


def test_first_ascii_input_cancels_pending_post_delete_sync(app, window_factory):
    editor = _window(app, window_factory).editor
    editor.setPlainText("a" * 10_000)
    editor.moveCursor(QTextCursor.End)
    app.processEvents()
    _repeat_backspace(editor, 10_000)
    editor.flush_pending_delete()
    assert editor.document().isEmpty()
    assert editor._post_delete_sync_timer.isActive()

    QTest.keyClicks(editor, "abcdefg")
    assert editor.toPlainText() == "abcdefg"
    assert editor.textCursor().position() == 7
    assert not editor._post_delete_sync_timer.isActive()
    QTest.qWait(70)
    assert _caret_visible(editor)
    assert editor.document().blockCount() == 1


def test_select_all_delete_then_immediate_ascii_input(app, window_factory):
    editor = _window(app, window_factory).editor
    editor.setPlainText("a" * 10_000)
    editor.moveCursor(QTextCursor.End)
    app.processEvents()
    QTest.keyClick(editor, Qt.Key_A, Qt.ControlModifier)
    QTest.keyClick(editor, Qt.Key_Backspace)
    QTest.keyClicks(editor, "abcdefg")
    assert editor.toPlainText() == "abcdefg"
    QTest.qWait(70)
    assert editor.textCursor().position() == 7
    assert _caret_visible(editor)


def test_chinese_preedit_after_delete_does_not_scroll_until_commit(
    app, window_factory
):
    editor = _window(app, window_factory).editor
    editor.setPlainText("中文长句" * 2_000)
    editor.moveCursor(QTextCursor.End)
    app.processEvents()
    QTest.keyClick(editor, Qt.Key_A, Qt.ControlModifier)
    QTest.keyClick(editor, Qt.Key_Backspace)
    assert editor.document().isEmpty()

    QApplication.sendEvent(editor, QInputMethodEvent("nihaoshijie", []))
    assert editor.toPlainText() == ""
    assert editor._ime_preedit_active
    assert not editor._cursor_sync_timer.isActive()
    QTest.qWait(70)
    assert editor.toPlainText() == ""

    commit = QInputMethodEvent()
    commit.setCommitString("你好世界测试")
    QApplication.sendEvent(editor, commit)
    assert editor.toPlainText() == "你好世界测试"
    assert not editor._ime_preedit_active
    QTest.qWait(70)
    assert editor.textCursor().position() == len("你好世界测试")
    assert _caret_visible(editor)
    assert editor.document().blockCount() == 1


def test_wrapped_text_and_100_fast_characters_are_preserved(app, window_factory):
    editor = _window(app, window_factory).editor
    original = "长文本视觉折行" * 200
    editor.setPlainText(original)
    editor.moveCursor(QTextCursor.End)
    app.processEvents()
    assert editor.document().firstBlock().layout().lineCount() > 10

    suffix = "x" * 100
    QTest.keyClicks(editor, suffix)
    assert editor.toPlainText() == original + suffix
    assert editor.textCursor().position() == len(original + suffix)
    QTest.qWait(70)
    assert _caret_visible(editor)
    assert editor.document().blockCount() == 1
    assert editor.height() < WINDOW_HEIGHT


def test_nested_event_processing_cannot_scroll_during_key_input(
    app, window_factory, monkeypatch
):
    editor = _window(app, window_factory).editor
    editor.setPlainText("a" * 10_000)
    editor.moveCursor(QTextCursor.End)
    QTest.qWait(70)

    scroll_during_input = []
    original_scroll = editor._position_visual_scroll

    def track_scroll():
        if editor._input_event_depth or editor._ime_event_depth:
            scroll_during_input.append(1)
        original_scroll()

    monkeypatch.setattr(editor, "_position_visual_scroll", track_scroll)
    editor.textChanged.connect(app.processEvents)
    QTest.keyClicks(editor, "abcdefg")
    assert editor.toPlainText() == "a" * 10_000 + "abcdefg"
    assert scroll_during_input == []
    QTest.qWait(70)
    assert _caret_visible(editor)


def test_input_arriving_during_sync_gets_a_fresh_debounced_sync(
    app, window_factory, monkeypatch
):
    editor = _window(app, window_factory).editor
    editor.setPlainText("a" * 1_000)
    editor.moveCursor(QTextCursor.End)
    QTest.qWait(70)

    calls = []
    original_scroll = editor._position_visual_scroll

    def inject_input_once():
        calls.append(1)
        if len(calls) == 1:
            QTest.keyClicks(editor, "z")
        original_scroll()

    monkeypatch.setattr(editor, "_position_visual_scroll", inject_input_once)
    editor._schedule_cursor_sync()
    QTest.qWait(120)
    assert editor.toPlainText() == "a" * 1_000 + "z"
    assert len(calls) >= 2
    assert not editor._resync_after_input
    assert _caret_visible(editor)
