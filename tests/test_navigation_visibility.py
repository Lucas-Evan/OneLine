"""Navigation-only caret correction in a wrapped, fixed-height viewport."""

from __future__ import annotations

from PyQt5.QtCore import QRect, Qt
from PyQt5.QtGui import QInputMethodEvent, QTextCursor
from PyQt5.QtTest import QTest
from PyQt5.QtWidgets import QApplication

from window import WINDOW_HEIGHT


def _visible(editor) -> bool:
    caret = editor.cursorRect()
    view = editor.viewport().rect()
    # Qt's offscreen rasterizer may round the caret one pixel outside the
    # viewport on Linux. Larger clipping remains a release failure.
    tolerance = 1
    return (
        view.left() - tolerance <= caret.left()
        and caret.right() <= view.right() + tolerance
        and view.top() - tolerance <= caret.top()
        and caret.bottom() <= view.bottom() + tolerance
    )


def _wrapped_window(app, window_factory):
    window = window_factory()
    window.resize(300, WINDOW_HEIGHT)
    window.show()
    editor = window.editor
    editor.setFocus()
    editor.setPlainText("今天测试视觉折行" * 35)
    app.processEvents()
    assert editor.document().firstBlock().layout().lineCount() > 3
    assert editor.document().blockCount() == 1
    assert window.height() == 56
    return window, editor


def test_navigation_keeps_caret_visible_across_wrapped_rows(app, window_factory):
    window, editor = _wrapped_window(app, window_factory)
    QTest.keyClick(editor, Qt.Key_End)
    app.processEvents()
    assert _visible(editor)
    for _ in range(90):
        QTest.keyClick(editor, Qt.Key_Left)
        assert _visible(editor)
    for _ in range(90):
        QTest.keyClick(editor, Qt.Key_Right)
        assert _visible(editor)
    QTest.keyClick(editor, Qt.Key_Home)
    assert editor.textCursor().positionInBlock() == 0
    assert _visible(editor)
    QTest.keyClick(editor, Qt.Key_End)
    assert editor.textCursor().positionInBlock() == len(editor.toPlainText())
    assert _visible(editor)
    assert window.height() == 56
    assert editor.document().blockCount() == 1


def test_navigation_correction_runs_once_only_when_outside(
    app, window_factory, monkeypatch
):
    _, editor = _wrapped_window(app, window_factory)
    calls = []
    original_ensure = editor.ensureCursorVisible

    def counted_ensure():
        calls.append(editor.textCursor().position())
        original_ensure()

    monkeypatch.setattr(editor, "ensureCursorVisible", counted_ensure)
    original_rect = editor.cursorRect

    def outside_rect(cursor=None):
        if cursor is not None:
            return original_rect(cursor)
        return QRect(0, editor.viewport().height() + 5, 1, 10)

    monkeypatch.setattr(editor, "cursorRect", outside_rect)
    QTest.keyClick(editor, Qt.Key_End)
    assert len(calls) == 1
    QTest.keyClick(editor, Qt.Key_Left)
    assert len(calls) == 2
    monkeypatch.setattr(editor, "cursorRect", lambda cursor=None: QRect(0, 1, 1, 10))
    QTest.keyClick(editor, Qt.Key_Left)
    assert len(calls) == 2
    monkeypatch.setattr(editor, "cursorRect", original_rect)

    # Ordinary text, deletion and IME must never invoke this correction.
    QTest.keyClicks(editor, "abc")
    QTest.keyClick(editor, Qt.Key_Backspace)
    preedit = QInputMethodEvent("候选", [])
    QApplication.sendEvent(editor, preedit)
    commit = QInputMethodEvent()
    commit.setCommitString("中文")
    QApplication.sendEvent(editor, commit)
    assert len(calls) == 2


def test_delete_empty_retype_and_ime_do_not_enter_navigation_path(
    app, window_factory, monkeypatch
):
    window, editor = _wrapped_window(app, window_factory)
    calls = []
    monkeypatch.setattr(editor, "ensureCursorVisible", lambda: calls.append(True))
    editor.moveCursor(QTextCursor.End)
    QTest.keyClick(editor, Qt.Key_A, Qt.ControlModifier)
    QTest.keyClick(editor, Qt.Key_Backspace)
    assert editor.toPlainText() == ""
    QTest.keyClicks(editor, "abcdefg")
    commit = QInputMethodEvent()
    commit.setCommitString("你好世界测试")
    QApplication.sendEvent(editor, commit)
    app.processEvents()
    assert editor.toPlainText() == "abcdefg你好世界测试"
    assert editor.document().blockCount() == 1
    assert _visible(editor)
    assert calls == []
    assert window.height() == 56
