"""The document-backed, fixed-height text editor."""

from __future__ import annotations

import logging

from PyQt5.QtCore import QEvent, QTimer, Qt, pyqtSignal
from PyQt5.QtGui import QFontDatabase, QTextCursor
from PyQt5.QtWidgets import QPlainTextEdit


_LOG = logging.getLogger(__name__)
LONG_WRAPPED_BLOCK_WARNING_LENGTH = 5_000


class OneLineEditor(QPlainTextEdit):
    """A full logical-line editor whose viewport is only one visual row tall.

    The complete document remains in QPlainTextEdit/QTextDocument.  Qt therefore
    retains its native selection, clipboard, undo, paste and input-method
    handling. Long blocks wrap visually, without adding document newlines.
    """

    linePositionChanged = pyqtSignal(int, int)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("oneLineEditor")
        self.setFont(QFontDatabase.systemFont(QFontDatabase.GeneralFont))
        self.document().setModified(False)
        self.setLineWrapMode(QPlainTextEdit.WidgetWidth)
        self.setFrameStyle(QPlainTextEdit.NoFrame)
        self.setTabChangesFocus(False)
        # A document margin consumes scarce vertical space in the one-row
        # viewport and can leave the native caret outside it after wrapping.
        self.document().setDocumentMargin(0)

        # Keep Qt's native vertical scrollbar policy and cursor positioning;
        # OneLine must not maintain a second scrolling implementation.
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        # One font row plus compact breathing room; the parent window remains
        # 56 px high while HiDPI scaling is handled by Qt logical pixels.
        self.setFixedHeight(self.fontMetrics().lineSpacing() + 10)

        # This timer updates line metadata only; Qt owns input and scrolling.
        self._cursor_sync_timer = QTimer(self)
        self._cursor_sync_timer.setSingleShot(True)
        self._cursor_sync_timer.setInterval(40)
        self._cursor_sync_timer.timeout.connect(self._sync_current_line)
        self._warned_long_blocks: set[int] = set()
        # Only a user navigation key may request a viewport correction.  The
        # flag is consumed by the first cursor change, before scrolling, so
        # any signal emitted by Qt's scroll handling cannot start a loop.
        self._navigation_pending = False
        self.installEventFilter(self)
        self.cursorPositionChanged.connect(self._schedule_cursor_sync)
        self.cursorPositionChanged.connect(self._show_navigated_cursor_if_needed)
        self.document().blockCountChanged.connect(self._schedule_cursor_sync)
        self.textChanged.connect(self._schedule_cursor_sync)
        self.document().contentsChange.connect(self._warn_if_long_wrapped_block)
        self._schedule_cursor_sync()
        self.document().setModified(False)

    def current_line_number(self) -> int:
        return self.textCursor().blockNumber() + 1

    def line_count(self) -> int:
        return max(1, self.document().blockCount())

    def _warn_if_long_wrapped_block(
        self, position: int, _removed: int, added: int
    ) -> None:
        """Inspect only changed blocks and log lengths, never document text."""
        if self.lineWrapMode() != QPlainTextEdit.WidgetWidth:
            return
        document = self.document()
        start = max(0, min(position, document.characterCount() - 1))
        end = max(start, min(position + added, document.characterCount() - 1))
        block = document.findBlock(start)
        while block.isValid() and block.position() <= end:
            block_number = block.blockNumber()
            length = max(0, block.length() - 1)
            if length <= LONG_WRAPPED_BLOCK_WARNING_LENGTH:
                self._warned_long_blocks.discard(block_number)
            elif block_number not in self._warned_long_blocks:
                _LOG.warning(
                    "Wrapped block exceeds diagnostic threshold: block=%d length=%d threshold=%d",
                    block_number,
                    length,
                    LONG_WRAPPED_BLOCK_WARNING_LENGTH,
                )
                self._warned_long_blocks.add(block_number)
            block = block.next()

    def go_to_line(self, line_number: int, column: int = 0) -> None:
        """Move to a one-based line number, clamped to the document."""
        target = max(1, min(line_number, self.line_count()))
        block = self.document().findBlockByNumber(target - 1)
        cursor = QTextCursor(block)
        next_block = block.next()
        document_end = max(0, self.document().characterCount() - 1)
        block_end = next_block.position() - 1 if next_block.isValid() else document_end
        cursor.movePosition(
            QTextCursor.Right,
            QTextCursor.MoveAnchor,
            min(max(0, column), max(0, block_end - block.position())),
        )
        self.setTextCursor(cursor)
        self._schedule_cursor_sync()

    def _schedule_cursor_sync(self, *_args) -> None:
        # Metadata debounce only; no viewport or document edits occur here.
        self._cursor_sync_timer.start()

    def _sync_current_line(self) -> None:
        self.linePositionChanged.emit(self.current_line_number(), self.line_count())

    def eventFilter(self, watched, event):  # noqa: N802 - Qt API name
        if watched is self:
            if event.type() == QEvent.KeyPress:
                self._navigation_pending = event.key() in (
                    Qt.Key_Left, Qt.Key_Right, Qt.Key_Up, Qt.Key_Down,
                    Qt.Key_Home, Qt.Key_End,
                )
            elif event.type() in (QEvent.KeyRelease, QEvent.InputMethod):
                self._navigation_pending = False
        return super().eventFilter(watched, event)

    def _show_navigated_cursor_if_needed(self) -> None:
        if not self._navigation_pending:
            return
        self._navigation_pending = False
        caret = self.cursorRect()
        viewport = self.viewport().rect()
        if not viewport.contains(caret.topLeft()) or not viewport.contains(caret.bottomRight()):
            self.ensureCursorVisible()

    def keyPressEvent(self, event) -> None:  # noqa: N802 - Qt API name
        key = event.key()
        # QPlainTextEdit normally treats Up/Down and Home/End as *visual* row
        # navigation under WidgetWidth. OneLine's navigation remains logical.
        if event.modifiers() & (Qt.ControlModifier | Qt.AltModifier | Qt.MetaModifier):
            super().keyPressEvent(event)
            return
        if key not in (Qt.Key_Up, Qt.Key_Down, Qt.Key_Home, Qt.Key_End):
            super().keyPressEvent(event)
            return
        cursor = self.textCursor()
        mode = QTextCursor.KeepAnchor if event.modifiers() & Qt.ShiftModifier else QTextCursor.MoveAnchor
        if key == Qt.Key_Home:
            cursor.movePosition(QTextCursor.StartOfBlock, mode)
        elif key == Qt.Key_End:
            cursor.movePosition(QTextCursor.EndOfBlock, mode)
        else:
            target = self.document().findBlockByNumber(
                cursor.blockNumber() + (-1 if key == Qt.Key_Up else 1)
            )
            if target.isValid():
                next_block = target.next()
                document_end = max(0, self.document().characterCount() - 1)
                block_end = (
                    next_block.position() - 1
                    if next_block.isValid()
                    else document_end
                )
                position = min(target.position() + cursor.positionInBlock(), block_end)
                position = max(0, min(position, document_end))
                cursor.setPosition(position, mode)
        self.setTextCursor(cursor)
        event.accept()

    def resizeEvent(self, event) -> None:  # noqa: N802 - Qt API name
        super().resizeEvent(event)
        self._schedule_cursor_sync()
