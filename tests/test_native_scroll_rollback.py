"""Focused A/B experiment with Qt's native wrapped-block scrolling."""

from __future__ import annotations

from time import perf_counter

from PyQt5.QtCore import QEvent, Qt, qInstallMessageHandler
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
    editor.flush_pending_delete()


def test_native_scroll_rollback_10k_delete_empty_retype_and_ime(app, window_factory):
    window = window_factory()
    window.resize(300, WINDOW_HEIGHT)
    window.show()
    editor = window.editor
    editor.setFocus()
    editor.setPlainText("a" * 10_000)
    editor.moveCursor(QTextCursor.End)
    app.processEvents()

    assert editor.lineWrapMode() == QPlainTextEdit.WidgetWidth
    assert editor.document().firstBlock().layout().lineCount() > 10
    assert window.height() == 56
    assert editor.document().blockCount() == 1

    warnings = []

    def capture(_kind, _context, message):
        warnings.append(message)

    previous = qInstallMessageHandler(capture)
    start = perf_counter()
    try:
        _repeat_backspace(editor, 5_000)
        app.processEvents()
        assert editor.toPlainText() == "a" * 5_000
        _repeat_backspace(editor, 5_000)
        app.processEvents()
        assert editor.toPlainText() == ""

        # The first input is deliberately sent before any timer can fire.
        for character in "abc":
            QTest.keyClicks(editor, character)
        preedit = QInputMethodEvent("候选", [])
        QApplication.sendEvent(editor, preedit)
        commit = QInputMethodEvent()
        commit.setCommitString("你好世界")
        QApplication.sendEvent(editor, commit)
        app.processEvents()
    finally:
        qInstallMessageHandler(previous)

    assert editor.toPlainText() == "abc你好世界"
    assert editor.textCursor().position() == len("abc你好世界")
    assert editor.document().blockCount() == 1
    assert "\n" not in editor.toPlainText()
    assert window.height() == 56
    assert not [item for item in warnings if "setPosition" in item]
    print(f"native-scroll 10k delete/retype/IME: {perf_counter() - start:.3f}s")


def test_logical_navigation_and_restore_never_set_out_of_range(app, window_factory):
    window = window_factory()
    window.show()
    editor = window.editor
    editor.setFocus()
    warnings = []

    def capture(_kind, _context, message):
        warnings.append(message)

    previous = qInstallMessageHandler(capture)
    try:
        for content in ("", "a\n\nz", "\n", "一\n二"):
            editor.setPlainText(content)
            window._restore_cursor(-1)
            window._restore_cursor(999_999)
            for key in (Qt.Key_Up, Qt.Key_Down, Qt.Key_Home, Qt.Key_End):
                for _ in range(4):
                    QApplication.sendEvent(
                        editor, QKeyEvent(QEvent.KeyPress, key, Qt.NoModifier)
                    )
                    position = editor.textCursor().position()
                    assert 0 <= position < editor.document().characterCount()
            for line in range(-1, editor.line_count() + 3):
                editor.go_to_line(line, column=999_999)
                position = editor.textCursor().position()
                assert 0 <= position < editor.document().characterCount()
            app.processEvents()
    finally:
        qInstallMessageHandler(previous)

    assert not [item for item in warnings if "setPosition" in item]
