"""Native-delete isolation: no batching, cursor fixups or post-delete timer."""

from __future__ import annotations

from time import perf_counter

import pytest
from PyQt5.QtCore import QEvent, Qt, qInstallMessageHandler
from PyQt5.QtGui import QInputMethodEvent, QKeyEvent, QTextCursor
from PyQt5.QtTest import QTest
from PyQt5.QtWidgets import QApplication, QPlainTextEdit

from editor import OneLineEditor
from window import WINDOW_HEIGHT


@pytest.mark.parametrize("size", [5_000, 10_000])
def test_native_backspace_across_wraps_then_empty_and_retype(
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
    assert editor.document().firstBlock().layout().lineCount() > 10
    assert not hasattr(editor, "flush_pending_delete")
    assert not hasattr(editor, "_repeat_delete_timer")
    assert not hasattr(editor, "_post_delete_sync_timer")

    warnings = []

    def capture(_kind, _context, message):
        warnings.append(message)

    previous = qInstallMessageHandler(capture)
    started = perf_counter()
    slowest_ms = 0.0
    try:
        # Ordinary key presses cross multiple wrapped rows. Each goes through
        # QPlainTextEdit, with no synthetic delete transaction or batching.
        for index in range(300):
            key_started = perf_counter()
            if index < 150:
                QTest.keyClick(editor, Qt.Key_Backspace)
            else:
                QApplication.sendEvent(
                    editor,
                    QKeyEvent(
                        QEvent.KeyPress, Qt.Key_Backspace, Qt.NoModifier, "", True, 1
                    ),
                )
            slowest_ms = max(slowest_ms, (perf_counter() - key_started) * 1000)
            if index % 10 == 0:
                app.processEvents()
        assert editor.toPlainText() == "a" * (size - 300)
        caret_after_backspace = editor.cursorRect()
        viewport_after_backspace = editor.viewport().rect()
        caret_visible_after_backspace = (
            viewport_after_backspace.top() <= caret_after_backspace.top()
            and caret_after_backspace.bottom() <= viewport_after_backspace.bottom()
        )
        QTest.keyClicks(editor, "xyz")
        assert editor.toPlainText() == "a" * (size - 300) + "xyz"
        caret_after_hidden_input = editor.cursorRect()
        viewport_after_hidden_input = editor.viewport().rect()
        caret_visible_after_hidden_input = (
            viewport_after_hidden_input.top() <= caret_after_hidden_input.top()
            and caret_after_hidden_input.bottom() <= viewport_after_hidden_input.bottom()
        )
        for _ in range(3):
            QTest.keyClick(editor, Qt.Key_Backspace)
        assert editor.toPlainText() == "a" * (size - 300)

        # Exercise native forward Delete as well, then delete the remainder.
        editor.moveCursor(QTextCursor.Start)
        for _ in range(30):
            QTest.keyClick(editor, Qt.Key_Delete)
        assert editor.toPlainText() == "a" * (size - 330)
        QTest.keyClick(editor, Qt.Key_A, Qt.ControlModifier)
        QTest.keyClick(editor, Qt.Key_Backspace)
        assert editor.toPlainText() == ""
        caret_after_empty = editor.cursorRect()
        viewport_after_empty = editor.viewport().rect()
        caret_visible_after_empty = (
            viewport_after_empty.top() <= caret_after_empty.top()
            and caret_after_empty.bottom() <= viewport_after_empty.bottom()
        )

        # First input arrives before the event loop runs the metadata timer.
        QTest.keyClicks(editor, "abc")
        preedit = QInputMethodEvent("候选", [])
        QApplication.sendEvent(editor, preedit)
        commit = QInputMethodEvent()
        commit.setCommitString("中文")
        QApplication.sendEvent(editor, commit)
        app.processEvents()
    finally:
        qInstallMessageHandler(previous)

    assert editor.toPlainText() == "abc中文"
    assert editor.document().blockCount() == 1
    assert "\n" not in editor.toPlainText()
    assert window.height() == 56
    assert not [message for message in warnings if "setPosition" in message]
    assert caret_visible_after_backspace
    assert caret_visible_after_hidden_input
    assert caret_visible_after_empty
    print(
        f"native-delete size={size} elapsed={perf_counter() - started:.3f}s "
        f"slowest_backspace={slowest_ms:.1f}ms "
        f"caret_visible_after_backspace={caret_visible_after_backspace} "
        f"caret_visible_after_hidden_input={caret_visible_after_hidden_input} "
        f"caret_visible_after_empty={caret_visible_after_empty}"
    )


@pytest.mark.parametrize("padding_pixels", [0, 4])
@pytest.mark.parametrize("size", [5_000, 10_000])
def test_bare_qplaintextedit_control_with_same_wrap_and_viewport(
    app, window_factory, size, padding_pixels
):
    """Check whether the same viewport symptom exists without OneLine code."""
    window = window_factory()
    window.resize(300, WINDOW_HEIGHT)
    window.show()
    app.processEvents()
    reference_size = window.editor.size()
    editor = QPlainTextEdit()
    editor.setObjectName("oneLineEditor")
    editor.setFont(window.editor.font())
    editor.setLineWrapMode(QPlainTextEdit.WidgetWidth)
    editor.setFrameStyle(QPlainTextEdit.NoFrame)
    editor.document().setDocumentMargin(2)
    editor.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
    editor.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
    editor.setStyleSheet(
        f"QPlainTextEdit#oneLineEditor {{ border: none; padding: {padding_pixels}px 0px; }}"
    )
    editor.setFixedHeight(reference_size.height())
    editor.resize(reference_size)
    editor.show()
    editor.setFocus()
    editor.setPlainText("a" * size)
    editor.moveCursor(QTextCursor.End)
    app.processEvents()
    assert editor.document().firstBlock().layout().lineCount() > 10

    started = perf_counter()
    for index in range(300):
        QTest.keyClick(editor, Qt.Key_Backspace)
        if index % 10 == 0:
            app.processEvents()
    assert editor.toPlainText() == "a" * (size - 300)
    caret = editor.cursorRect()
    viewport = editor.viewport().rect()
    visible = viewport.top() <= caret.top() and caret.bottom() <= viewport.bottom()

    QTest.keyClicks(editor, "xyz")
    assert editor.toPlainText() == "a" * (size - 300) + "xyz"
    QTest.keyClick(editor, Qt.Key_A, Qt.ControlModifier)
    QTest.keyClick(editor, Qt.Key_Backspace)
    QTest.keyClicks(editor, "abc")
    assert editor.toPlainText() == "abc"
    print(
        f"bare-QPlainTextEdit size={size} padding={padding_pixels}px "
        f"elapsed={perf_counter() - started:.3f}s "
        f"caret_visible_after_backspace={visible} "
        f"viewport={editor.viewport().width()}x{editor.viewport().height()} "
        f"reference={window.editor.viewport().width()}x{window.editor.viewport().height()}"
    )


@pytest.mark.parametrize("size", [5_000, 10_000])
def test_standalone_oneline_editor_control(app, window_factory, size):
    """Separate editor subclass behavior from the parent window's slots."""
    window = window_factory()
    window.resize(300, WINDOW_HEIGHT)
    window.show()
    app.processEvents()
    reference_size = window.editor.size()

    editor = OneLineEditor()
    editor.resize(reference_size)
    editor.show()
    editor.setFocus()
    editor.setPlainText("a" * size)
    editor.moveCursor(QTextCursor.End)
    app.processEvents()
    started = perf_counter()
    for index in range(300):
        QTest.keyClick(editor, Qt.Key_Backspace)
        if index % 10 == 0:
            app.processEvents()
    assert editor.toPlainText() == "a" * (size - 300)
    caret = editor.cursorRect()
    viewport = editor.viewport().rect()
    visible = viewport.top() <= caret.top() and caret.bottom() <= viewport.bottom()
    QTest.keyClicks(editor, "xyz")
    assert editor.toPlainText() == "a" * (size - 300) + "xyz"
    print(
        f"standalone-OneLineEditor size={size} "
        f"elapsed={perf_counter() - started:.3f}s "
        f"caret_visible_after_backspace={visible}"
    )


@pytest.mark.parametrize("size", [5_000, 10_000])
def test_full_window_zero_padding_control(app, window_factory, size):
    """The production style leaves enough viewport height for native scrolling."""
    window = window_factory()
    window.resize(300, WINDOW_HEIGHT)
    window.show()
    editor = window.editor
    assert "padding: 0px" in window.styleSheet()
    editor.setFocus()
    editor.setPlainText("a" * size)
    editor.moveCursor(QTextCursor.End)
    app.processEvents()
    started = perf_counter()
    for index in range(300):
        QTest.keyClick(editor, Qt.Key_Backspace)
        if index % 10 == 0:
            app.processEvents()
    assert editor.toPlainText() == "a" * (size - 300)
    caret = editor.cursorRect()
    viewport = editor.viewport().rect()
    visible = viewport.top() <= caret.top() and caret.bottom() <= viewport.bottom()
    QTest.keyClicks(editor, "xyz")
    assert editor.toPlainText() == "a" * (size - 300) + "xyz"
    assert visible
    print(
        f"full-window-zero-padding size={size} "
        f"elapsed={perf_counter() - started:.3f}s "
        f"caret_visible_after_backspace={visible} "
        f"viewport_height={viewport.height()}"
    )
