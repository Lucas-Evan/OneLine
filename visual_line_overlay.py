"""Paint-only clipping of visual rows outside the editor's current caret row."""

from __future__ import annotations

from PyQt5.QtCore import QEvent, QRect, QTimer, Qt
from PyQt5.QtGui import QPainter, QPalette
from PyQt5.QtWidgets import QPlainTextEdit, QWidget


class VisualLineOverlay(QWidget):
    """Mask adjacent wrapped rows without changing Qt's editing or scrolling."""

    def __init__(self, editor: QPlainTextEdit, background_widget: QWidget) -> None:
        viewport = editor.viewport()
        # A child of viewport is moved with its contents by Qt's native
        # scroll optimization. Keep this as a sibling over the viewport.
        super().__init__(editor)
        self._editor = editor
        self._viewport = viewport
        self._background_widget = background_widget
        self._top_mask_height = 0
        self._bottom_mask_y = viewport.height()
        self.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.setAttribute(Qt.WA_NoSystemBackground)
        self.setFocusPolicy(Qt.NoFocus)
        self.setGeometry(viewport.geometry())

        # One pending repaint follows native layout/scroll handling. This
        # observes edits but never intercepts or changes an input event.
        self._refresh_timer = QTimer(self)
        self._refresh_timer.setSingleShot(True)
        self._refresh_timer.setInterval(0)
        self._refresh_timer.timeout.connect(self.refresh)
        editor.cursorPositionChanged.connect(self._refresh_timer.start)
        editor.textChanged.connect(self._refresh_timer.start)
        editor.installEventFilter(self)
        viewport.installEventFilter(self)
        self.show()
        self.raise_()
        self.refresh()

    def eventFilter(self, watched, event):  # noqa: N802 - Qt API name
        if event.type() in (QEvent.Resize, QEvent.Move):
            if watched is self._viewport:
                self.setGeometry(watched.geometry())
                self.raise_()
                self._refresh_timer.start()
            elif watched is self._editor:
                self._refresh_timer.start()
        elif watched is self._editor and event.type() == QEvent.InputMethod:
            # Preedit can change cursorRect without cursorPositionChanged.
            self._refresh_timer.start()
        return super().eventFilter(watched, event)

    def refresh_appearance(self) -> None:
        """Repaint after the panel palette changes; top-level opacity is shared."""
        self.update()

    def refresh(self) -> None:
        # cursorRect is the only source used to identify the active visual row.
        self.setGeometry(self._viewport.geometry())
        self.raise_()
        caret = self._editor.cursorRect()
        view = self._editor.viewport().rect()
        if not caret.intersects(view):
            # Painting cannot recover an offscreen caret. Expose the native
            # viewport instead of turning it into a blank strip.
            self._top_mask_height = 0
            self._bottom_mask_y = self.height()
        else:
            self._top_mask_height = max(0, min(self.height(), caret.top()))
            self._bottom_mask_y = max(
                self._top_mask_height, min(self.height(), caret.bottom() + 1)
            )
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802 - Qt API name
        background = self._background_widget.palette().color(QPalette.Window)
        painter = QPainter(self)
        if self._top_mask_height:
            painter.fillRect(
                QRect(0, 0, self.width(), self._top_mask_height), background
            )
        if self._bottom_mask_y < self.height():
            painter.fillRect(
                QRect(
                    0,
                    self._bottom_mask_y,
                    self.width(),
                    self.height() - self._bottom_mask_y,
                ),
                background,
            )
