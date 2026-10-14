"""Long logical lines remain usable inside the fixed one-row viewport."""

from __future__ import annotations

from PyQt5.QtCore import QPoint, Qt
from PyQt5.QtGui import QInputMethodEvent, QWheelEvent
from PyQt5.QtTest import QTest
from PyQt5.QtWidgets import QApplication

from editor import OneLineEditor
from window import WINDOW_HEIGHT


def _visible_caret(editor):
    caret = editor.cursorRect()
    viewport = editor.viewport().rect()
    assert 0 <= caret.left() <= viewport.right()
    assert caret.right() <= viewport.right()
    assert 0 <= caret.top() < viewport.height()


def _short_editor(app):
    editor = OneLineEditor()
    editor.resize(300, editor.height())
    editor.show()
    editor.setFocus()
    app.processEvents()
    return editor


def _settle_editor(editor):
    QTest.qWait(editor._cursor_sync_timer.interval() + 20)


def test_thousand_character_line_can_be_edited(app):
    editor = _short_editor(app)
    for _ in range(10):
        QTest.keyClicks(editor, "a" * 100)
        app.processEvents()
        _visible_caret(editor)
    assert editor.toPlainText() == "a" * 1000
    assert editor.line_count() == 1
    assert editor.lineWrapMode() == OneLineEditor.WidgetWidth
    assert editor.document().firstBlock().layout().lineCount() > 1
    assert editor.verticalScrollBar().value() > 0


def test_long_line_typing_keeps_caret_visible(app):
    editor = _short_editor(app)
    editor.insertPlainText("x" * 1000)
    app.processEvents()
    for character in "ending":
        QTest.keyClicks(editor, character)
        app.processEvents()
        _visible_caret(editor)
    assert editor.toPlainText().endswith("ending")


def test_left_and_right_follow_wrapped_rows_without_half_page_jumps(app):
    editor = _short_editor(app)
    editor.insertPlainText("a" * 1000)
    app.processEvents()
    _settle_editor(editor)
    bar = editor.verticalScrollBar()
    previous = bar.value()
    steps = []
    for key in ([Qt.Key_Left] * 150) + ([Qt.Key_Right] * 150):
        QTest.keyClick(editor, key)
        app.processEvents()
        _visible_caret(editor)
        steps.append(abs(bar.value() - previous))
        previous = bar.value()
    assert max(steps) <= 1
    assert editor.textCursor().position() == 1000


def test_chinese_long_line_and_ime_commit(app):
    editor = _short_editor(app)
    editor.insertPlainText("中文" * 500)
    app.processEvents()
    _settle_editor(editor)
    assert editor.document().firstBlock().layout().lineCount() > 1
    _visible_caret(editor)

    preedit = QInputMethodEvent("输入", [])
    QApplication.sendEvent(editor, preedit)
    app.processEvents()
    _visible_caret(editor)
    commit = QInputMethodEvent()
    commit.setCommitString("输入")
    QApplication.sendEvent(editor, commit)
    _settle_editor(editor)
    _visible_caret(editor)
    assert editor.toPlainText() == "中文" * 500 + "输入"
    assert editor.line_count() == 1


def test_wheel_scrolls_wrapped_visual_rows(app):
    editor = _short_editor(app)
    editor.insertPlainText("a" * 1000)
    app.processEvents()
    _settle_editor(editor)
    bar = editor.verticalScrollBar()
    before = bar.value()
    pos = QPoint(20, 10)
    wheel = QWheelEvent(
        pos, editor.mapToGlobal(pos), QPoint(), QPoint(0, 120),
        120, Qt.Vertical, Qt.NoButton, Qt.NoModifier,
    )
    QApplication.sendEvent(editor.viewport(), wheel)
    app.processEvents()
    assert wheel.isAccepted()
    assert bar.value() < before


def test_window_stays_56px_after_long_and_multiline_text(app, window_factory):
    window = window_factory()
    window.show()
    window.editor.setPlainText("长" * 1000 + "\n第二行")
    window.editor.go_to_line(2)
    window.resize(600, 200)
    app.processEvents()
    assert window.height() == WINDOW_HEIGHT == 56
    assert window.minimumHeight() == window.maximumHeight() == 56
    assert window.editor.line_count() == 2
    assert window.editor.height() < window.height()
