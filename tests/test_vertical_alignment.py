"""Visual-only alignment checks for the fixed-height text strip."""

from __future__ import annotations

import pytest
from PyQt5.QtCore import QPoint
from PyQt5.QtGui import QGuiApplication
from PyQt5.QtTest import QTest

from window import WINDOW_HEIGHT


@pytest.mark.parametrize("font_size", [14, 20, 22])
def test_editor_is_centered_without_shrinking_viewport(app, window_factory, font_size):
    window = window_factory()
    window._set_font_size(font_size, persist=False)
    window.show()
    editor = window.editor
    editor.setPlainText("OneLine 中文")
    app.processEvents()

    editor_top = editor.mapTo(window, QPoint(0, 0)).y()
    slot_top = window.editor_slot.mapTo(window, QPoint(0, 0)).y()
    caret = editor.cursorRect()
    caret_center = editor_top + editor.viewport().geometry().top() + caret.top() + caret.height() / 2
    centered_editor_top = slot_top + (window.editor_slot.height() - editor.height()) / 2
    old_caret_center = centered_editor_top + caret.top() + caret.height() / 2
    window_center = window.height() / 2
    content_margins = editor.contentsMargins()
    viewport_margins = editor.viewportMargins()

    assert window.height() == WINDOW_HEIGHT == 56
    assert editor.height() == editor.fontMetrics().lineSpacing() + 10
    assert editor.viewport().height() == editor.height()
    assert all(
        margin == 0
        for margin in (
            content_margins.left(), content_margins.top(),
            content_margins.right(), content_margins.bottom(),
            viewport_margins.left(), viewport_margins.top(),
            viewport_margins.right(), viewport_margins.bottom(),
        )
    )
    assert abs(caret_center - window_center) < abs(old_caret_center - window_center)
    if QGuiApplication.platformName() == "cocoa":
        assert abs(caret_center - window_center) <= 3


def test_short_text_typing_stays_visible(app, window_factory):
    window = window_factory()
    window.show()
    editor = window.editor
    editor.setFocus()
    QTest.keyClicks(editor, "Quick note")
    app.processEvents()

    caret = editor.cursorRect()
    viewport = editor.viewport().rect()
    assert editor.toPlainText() == "Quick note"
    assert window.height() == 56
    assert viewport.top() <= caret.top() <= caret.bottom() <= viewport.bottom()
