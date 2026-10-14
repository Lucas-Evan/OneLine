"""The production overlay masks paint only, leaving Qt editing untouched."""

from __future__ import annotations

from PyQt5.QtCore import QPoint, Qt
from PyQt5.QtGui import QInputMethodEvent, QPalette
from PyQt5.QtTest import QTest
from PyQt5.QtWidgets import QApplication

from visual_line_overlay import VisualLineOverlay
from window import WINDOW_HEIGHT


LONG_TEXT = "今天需要检查视觉折行和输入稳定性" * 35


def _setup(app, window_factory):
    window = window_factory()
    window.resize(300, WINDOW_HEIGHT)
    window.show()
    editor = window.editor
    editor.setFocus()
    editor.setPlainText(LONG_TEXT)
    app.processEvents()
    assert isinstance(window.visual_line_overlay, VisualLineOverlay)
    assert editor.document().firstBlock().layout().lineCount() > 5
    return window, editor, window.visual_line_overlay


def _mask_matches_caret(editor, overlay):
    caret = editor.cursorRect()
    viewport = editor.viewport().rect()
    assert viewport.intersects(caret)
    assert overlay._top_mask_height == max(0, caret.top())
    assert overlay._bottom_mask_y == min(viewport.height(), caret.bottom() + 1)


def _masked_pixels(image, top, bottom):
    ratio = image.devicePixelRatio()
    return (
        (x, y)
        for y in list(range(0, round(top * ratio)))
        + list(range(round(bottom * ratio), image.height()))
        for x in range(image.width())
    )


def _viewport_image(window, editor):
    snapshot = window.grab()
    ratio = snapshot.devicePixelRatio()
    origin = editor.viewport().mapTo(window, QPoint(0, 0))
    return snapshot.toImage().copy(
        round(origin.x() * ratio),
        round(origin.y() * ratio),
        round(editor.viewport().width() * ratio),
        round(editor.viewport().height() * ratio),
    )


def test_long_wrap_overlay_masks_adjacent_row_without_moving_document(
    app, window_factory
):
    window, editor, overlay = _setup(app, window_factory)
    assert overlay.testAttribute(Qt.WA_TransparentForMouseEvents)
    assert overlay.focusPolicy() == Qt.NoFocus
    QTest.keyClick(editor, Qt.Key_End)
    for _ in range(36):
        QTest.keyClick(editor, Qt.Key_Left)
    app.processEvents()
    assert editor.cursorRect().bottom() < editor.viewport().height() - 1

    position = editor.textCursor().position()
    scroll = editor.verticalScrollBar().value()
    overlay.hide()
    app.processEvents()
    before = _viewport_image(window, editor)
    overlay.show()
    overlay.raise_()
    overlay.refresh()
    app.processEvents()
    after = _viewport_image(window, editor)
    color = window._panel.palette().color(QPalette.Window)

    # Cocoa may draw its transient scrollbar over the right edge of viewport.
    # Validate the text area rather than that platform-owned indicator.
    text_right = after.width() - round(12 * after.devicePixelRatio())
    masked = [
        (x, y)
        for x, y in _masked_pixels(
            after, overlay._top_mask_height, overlay._bottom_mask_y
        )
        if x < text_right
    ]
    assert masked
    assert any(before.pixel(x, y) != after.pixel(x, y) for x, y in masked)
    assert all(after.pixelColor(x, y).name() == color.name() for x, y in masked)
    _mask_matches_caret(editor, overlay)
    assert editor.toPlainText() == LONG_TEXT
    assert editor.document().blockCount() == 1
    assert editor.textCursor().position() == position
    assert editor.verticalScrollBar().value() == scroll
    assert window.height() == 56


def test_navigation_delete_empty_retype_and_ime_keep_overlay_aligned(
    app, window_factory
):
    window, editor, overlay = _setup(app, window_factory)
    QTest.keyClick(editor, Qt.Key_End)
    app.processEvents()
    for key in ([Qt.Key_Left] * 80) + ([Qt.Key_Right] * 80):
        QTest.keyClick(editor, key)
        app.processEvents()
        _mask_matches_caret(editor, overlay)
    QTest.keyClick(editor, Qt.Key_Home)
    app.processEvents()
    assert editor.textCursor().positionInBlock() == 0
    _mask_matches_caret(editor, overlay)
    QTest.keyClick(editor, Qt.Key_End)
    app.processEvents()
    assert editor.textCursor().positionInBlock() == len(LONG_TEXT)
    _mask_matches_caret(editor, overlay)

    for _ in range(100):
        QTest.keyClick(editor, Qt.Key_Backspace)
    app.processEvents()
    assert editor.toPlainText() == LONG_TEXT[:-100]
    _mask_matches_caret(editor, overlay)

    QApplication.sendEvent(editor, QInputMethodEvent("候选", []))
    app.processEvents()
    _mask_matches_caret(editor, overlay)
    commit = QInputMethodEvent()
    commit.setCommitString("中文输入")
    QApplication.sendEvent(editor, commit)
    app.processEvents()
    assert editor.toPlainText() == LONG_TEXT[:-100] + "中文输入"
    _mask_matches_caret(editor, overlay)

    QTest.keyClick(editor, Qt.Key_A, Qt.ControlModifier)
    QTest.keyClick(editor, Qt.Key_Backspace)
    app.processEvents()
    assert editor.toPlainText() == ""
    _mask_matches_caret(editor, overlay)
    QTest.keyClicks(editor, "abc")
    commit = QInputMethodEvent()
    commit.setCommitString("你好")
    QApplication.sendEvent(editor, commit)
    app.processEvents()
    assert editor.toPlainText() == "abc你好"
    assert editor.document().blockCount() == 1
    _mask_matches_caret(editor, overlay)
    assert window.height() == 56


def test_short_empty_theme_and_opacity_follow_panel_palette(app, window_factory):
    window = window_factory()
    window.show()
    editor = window.editor
    overlay = window.visual_line_overlay
    app.processEvents()
    _mask_matches_caret(editor, overlay)

    for content in ("", "短文本"):
        editor.setPlainText(content)
        app.processEvents()
        _mask_matches_caret(editor, overlay)

    first_color = window._panel.palette().color(QPalette.Window)
    window.toggle_theme()
    app.processEvents()
    second_color = window._panel.palette().color(QPalette.Window)
    assert second_color != first_color
    image = _viewport_image(window, editor)
    assert all(
        image.pixelColor(x, y).name() == second_color.name()
        for x, y in _masked_pixels(
            image, overlay._top_mask_height, overlay._bottom_mask_y
        )
    )

    window.setWindowOpacity(0.85)
    app.processEvents()
    assert abs(window.windowOpacity() - 0.85) < 0.01
    assert overlay._background_widget is window._panel
    assert window.height() == 56
