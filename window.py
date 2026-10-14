"""OneLine's compact frameless window."""

from __future__ import annotations

import sys
from pathlib import Path

from PyQt5.QtCore import QPoint, QTimer, Qt
from PyQt5.QtGui import (
    QColor,
    QFont,
    QIcon,
    QKeySequence,
    QMouseEvent,
    QPainter,
    QPen,
    QPixmap,
    QTextCursor,
    QTextDocument,
)
from PyQt5.QtWidgets import (
    QAction,
    QApplication,
    QDialog,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMenu,
    QMessageBox,
    QPushButton,
    QStyleOptionMenuItem,
    QSystemTrayIcon,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from editor import OneLineEditor
from file_manager import TextFile, file_digest, read_text_file, write_text_file
from preferences import PreferencesDialog
from session import Session, SessionStore
from settings import SettingsStore
from visual_line_overlay import VisualLineOverlay


WINDOW_HEIGHT = 56
DEFAULT_WIDTH = 800
MINIMUM_WIDTH = 300


class DragHandle(QLabel):
    """Small explicit drag target for a frameless window."""

    def __init__(self, parent=None) -> None:
        super().__init__("⋮⋮", parent)
        self.setObjectName("dragHandle")
        self.setAlignment(Qt.AlignCenter)
        self.setFixedWidth(26)
        self.setCursor(Qt.SizeAllCursor)
        self.setToolTip("拖动窗口")
        self._drag_offset: QPoint | None = None

    def mousePressEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        if event.button() == Qt.LeftButton:
            window = self.window()
            handle = window.windowHandle()
            if handle is not None and hasattr(handle, "startSystemMove"):
                if handle.startSystemMove():
                    event.accept()
                    return
            self._drag_offset = event.globalPos() - window.frameGeometry().topLeft()
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        if self._drag_offset is not None and event.buttons() & Qt.LeftButton:
            self.window().move(event.globalPos() - self._drag_offset)
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        self._drag_offset = None
        super().mouseReleaseEvent(event)


class QuickMenuButton(QToolButton):
    """Paint only a quiet ellipsis; Qt's default menu arrow is too prominent."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._ink = QColor("#64748b")
        self._hover = QColor("#e2e8f0")
        self.setText("⋯")
        self.setToolTip("菜单")
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedSize(24, 24)
        self.setToolButtonStyle(Qt.ToolButtonTextOnly)
        self.setPopupMode(QToolButton.InstantPopup)

    def set_colors(self, ink: str, hover: str) -> None:
        self._ink = QColor(ink)
        self._hover = QColor(hover)
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802 - Qt API
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setPen(Qt.NoPen)
        if self.underMouse():
            painter.setBrush(self._hover)
            painter.drawRoundedRect(self.rect().adjusted(1, 1, -1, -1), 5, 5)
        painter.setBrush(self._ink)
        middle = self.rect().center()
        for offset in (-6, 0, 6):
            painter.drawEllipse(middle.x() + offset - 1, middle.y() - 1, 3, 3)


class QuickMenu(QMenu):
    """Tint Qt-generated native shortcut hints without changing QAction text."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._background = QColor("#ffffff")
        self._hover = QColor("#e9eef4")
        self._shortcut_ink = QColor("#94a3b8")

    def set_colors(self, background: str, hover: str, shortcut_ink: str) -> None:
        self._background = QColor(background)
        self._hover = QColor(hover)
        self._shortcut_ink = QColor(shortcut_ink)
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802 - Qt API
        super().paintEvent(event)
        painter = QPainter(self)
        for action in self.actions():
            if not action.isVisible() or action.isSeparator():
                continue
            option = QStyleOptionMenuItem()
            self.initStyleOption(option, action)
            if "\t" not in option.text:
                continue
            # QMenu supplies the platform-native shortcut text here (⌘ on
            # macOS, Ctrl on Linux). Only repaint its existing right column.
            shortcut = option.text.split("\t", 1)[1]
            rect = self.actionGeometry(action)
            right_column = rect.adjusted(
                max(0, rect.width() - option.tabWidth - 42), 0, 0, 0
            )
            painter.fillRect(
                right_column,
                self._hover if self.activeAction() is action else self._background,
            )
            painter.setFont(option.font)
            painter.setPen(self._shortcut_ink)
            painter.drawText(
                right_column.adjusted(0, 0, -31, 0),
                Qt.AlignRight | Qt.AlignVCenter,
                shortcut,
            )


class ResizeHandle(QLabel):
    """Horizontal resize target that preserves the one-line height."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("resizeHandle")
        self.setFixedWidth(8)
        self.setCursor(Qt.SizeHorCursor)
        self.setToolTip("拖动调整宽度")
        self._start_x: int | None = None
        self._start_width = 0

    def mousePressEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        if event.button() == Qt.LeftButton:
            handle = self.window().windowHandle()
            if handle is not None and hasattr(handle, "startSystemResize"):
                if handle.startSystemResize(Qt.RightEdge):
                    event.accept()
                    return
            self._start_x = event.globalX()
            self._start_width = self.window().width()
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        if self._start_x is not None and event.buttons() & Qt.LeftButton:
            self.window().resize(
                max(MINIMUM_WIDTH, self._start_width + event.globalX() - self._start_x),
                WINDOW_HEIGHT,
            )
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        self._start_x = None
        super().mouseReleaseEvent(event)


class FindDialog(QDialog):
    """A small separate window, leaving the editor strip one row high."""

    def __init__(self, owner: "OneLineWindow") -> None:
        super().__init__(owner)
        self.setWindowTitle("查找")
        self.setWindowFlag(Qt.Tool, True)
        layout = QHBoxLayout(self)
        self.query = QLineEdit(self)
        self.query.setPlaceholderText("查找文本")
        self.query.returnPressed.connect(lambda: owner.find_text(self.query.text()))
        previous = QPushButton("上一个", self)
        following = QPushButton("下一个", self)
        previous.clicked.connect(lambda: owner.find_text(self.query.text(), backward=True))
        following.clicked.connect(lambda: owner.find_text(self.query.text()))
        layout.addWidget(self.query, 1)
        layout.addWidget(previous)
        layout.addWidget(following)


class OneLineWindow(QWidget):
    """Document backed floating window with file and session management."""

    def __init__(
        self,
        settings: SettingsStore | None = None,
        sessions: SessionStore | None = None,
    ) -> None:
        super().__init__()
        self.settings = settings or SettingsStore()
        self.sessions = sessions or SessionStore()
        self.file_path: str | None = None
        self._disk_digest: bytes | None = None
        self.newline = "\n"
        self.bom = False
        self.on_top = self.settings.always_on_top()
        self.theme = self.settings.theme()
        self._recovery_active = False
        self._session_error: str | None = None
        self._hidden_by_user = False
        self._find_dialog: FindDialog | None = None
        self._session_timer = QTimer(self)
        self._session_timer.setSingleShot(True)
        self._session_timer.setInterval(350)
        self._session_timer.timeout.connect(self._write_session)

        self.setObjectName("oneLineWindow")
        self.setAttribute(Qt.WA_TranslucentBackground)
        self._set_window_flags()
        self.setWindowOpacity(self.settings.opacity())
        self.setMinimumWidth(MINIMUM_WIDTH)
        self.setFixedHeight(WINDOW_HEIGHT)
        self.resize(self.settings.width(DEFAULT_WIDTH), WINDOW_HEIGHT)
        position = self.settings.position()
        if position is not None:
            self.move(position)

        self._panel = QFrame(self)
        self._panel.setObjectName("panel")
        layout = QHBoxLayout(self._panel)
        layout.setContentsMargins(6, 4, 2, 4)
        layout.setSpacing(6)

        self.drag_handle = DragHandle(self._panel)
        # Position the one-row editor slightly lower without consuming any of
        # its viewport. Padding inside QPlainTextEdit made wrapped carets vanish.
        self.editor_slot = QWidget(self._panel)
        editor_layout = QVBoxLayout(self.editor_slot)
        editor_layout.setContentsMargins(0, 0, 0, 2)
        editor_layout.setSpacing(0)
        self.editor = OneLineEditor(self.editor_slot)
        editor_layout.addWidget(self.editor, 0, Qt.AlignBottom)
        self.line_label = QLabel("1/1", self._panel)
        self.line_label.setObjectName("lineLabel")
        self.line_label.setAlignment(Qt.AlignCenter)
        self.line_label.setMinimumWidth(42)

        self.dirty_label = QLabel("✓", self._panel)
        self.dirty_label.setObjectName("dirtyLabel")
        self.dirty_label.setAlignment(Qt.AlignCenter)
        self.dirty_label.setFixedWidth(18)
        self.dirty_label.setToolTip("已保存")

        self.menu_button = QuickMenuButton(self._panel)
        self.menu_button.setObjectName("menuButton")
        self.menu_button.setMenu(self._build_menu())

        layout.addWidget(self.drag_handle)
        layout.addWidget(self.editor_slot, 1)
        layout.addWidget(self.line_label)
        layout.addWidget(self.dirty_label)
        layout.addWidget(self.menu_button)
        layout.addWidget(ResizeHandle(self._panel))

        outer = QHBoxLayout(self)
        outer.setContentsMargins(1, 1, 1, 1)
        outer.addWidget(self._panel)

        self.editor.linePositionChanged.connect(self._update_line_label)
        self.editor.document().modificationChanged.connect(self._update_dirty_state)
        self.editor.textChanged.connect(self._schedule_session)
        # Cursor-only moves must not serialize the entire document. The next
        # content snapshot and explicit hide/close still capture its position.
        self._set_font_size(self.settings.font_size(), persist=False)
        if self.settings.font_family():
            self._set_font_family(self.settings.font_family(), persist=False)
        self._apply_style()
        self.visual_line_overlay = VisualLineOverlay(self.editor, self._panel)
        self._create_tray_icon()
        self._restore_session()
        self._keep_window_on_screen()
        self._update_title()

    def _keep_window_on_screen(self) -> None:
        """A saved position from a disconnected monitor must remain recoverable."""
        visible = self.geometry()
        for screen in QApplication.screens():
            intersection = screen.availableGeometry().intersected(visible)
            if intersection.width() >= 60 and intersection.height() >= 40:
                return
        screen = QApplication.primaryScreen()
        if screen is not None:
            area = screen.availableGeometry()
            self.move(area.center() - self.rect().center())

    def _set_window_flags(self) -> None:
        # Without a tray, retain a taskbar/Dock entry so a minimized OneLine
        # can be recovered even if a global hotkey is unavailable.
        window_kind = Qt.Tool if QSystemTrayIcon.isSystemTrayAvailable() else Qt.Window
        flags = Qt.FramelessWindowHint | window_kind
        if self.on_top:
            flags |= Qt.WindowStaysOnTopHint
        self.setWindowFlags(flags)

    def _action(self, menu: QMenu, label: str, shortcut, callback) -> QAction:
        action = QAction(label, self)
        if shortcut is not None:
            if isinstance(shortcut, list):
                action.setShortcuts(shortcut)
            else:
                action.setShortcut(shortcut)
            action.setShortcutContext(Qt.WindowShortcut)
            # macOS can hide shortcuts in popup/context menus by default.
            # Let QMenu render the native shortcut column from QAction itself.
            action.setShortcutVisibleInContextMenu(True)
        action.triggered.connect(callback)
        menu.addAction(action)
        self.addAction(action)
        return action

    def _keyboard_action(self, shortcut, callback) -> QAction:
        action = QAction(self)
        if isinstance(shortcut, list):
            action.setShortcuts(shortcut)
        else:
            action.setShortcut(shortcut)
        action.setShortcutContext(Qt.WindowShortcut)
        action.triggered.connect(callback)
        self.addAction(action)
        return action

    def _build_menu(self) -> QMenu:
        menu = QuickMenu(self)
        self._action(menu, "新建", QKeySequence.New, self.new_document)
        self._action(menu, "打开…", QKeySequence.Open, self.open_document)
        self._action(menu, "保存", QKeySequence.Save, self.save_document)
        save_as_shortcut = QKeySequence("Ctrl+Shift+S")
        if sys.platform == "darwin":
            # Qt maps Ctrl in portable shortcut text to Command on macOS.
            save_as_shortcut = [save_as_shortcut, QKeySequence("Meta+Shift+S")]
        self._action(menu, "另存为…", save_as_shortcut, self.save_as_document)
        self._action(menu, "查找…", QKeySequence.Find, self.show_find)
        self.recent_divider = menu.addSeparator()
        self._recent_actions: list[QAction] = []
        menu.addSeparator()
        top_shortcut = QKeySequence("Ctrl+Shift+T")
        if sys.platform == "darwin":
            top_shortcut = [top_shortcut, QKeySequence("Meta+Shift+T")]
        self.top_action = self._action(
            menu, "始终置顶", top_shortcut, self.toggle_on_top
        )
        self.top_action.setCheckable(True)
        self.top_action.setChecked(self.on_top)
        self._action(menu, "设置…", None, self.show_preferences)
        quit_shortcut = QKeySequence("Ctrl+Q")
        if sys.platform == "darwin":
            quit_shortcut = [quit_shortcut, QKeySequence("Meta+Q")]
        self._action(menu, "退出", quit_shortcut, self.quit_app)

        # These commands stay accessible via keyboard / editor context menu.
        self._keyboard_action(QKeySequence.Undo, lambda: self.editor.undo())
        self._keyboard_action(
            [QKeySequence.Redo, QKeySequence("Ctrl+Y")],
            lambda: self.editor.redo(),
        )
        self.hide_action = self._keyboard_action(
            QKeySequence(self.settings.hide_shortcut()), self.toggle_visibility
        )
        self.escape_action = self._keyboard_action(QKeySequence(Qt.Key_Escape), self.hide_window)
        menu.aboutToShow.connect(self._refresh_recent_actions)
        return menu

    def _refresh_recent_actions(self) -> None:
        menu = self.menu_button.menu()
        for action in self._recent_actions:
            menu.removeAction(action)
            action.deleteLater()
        self._recent_actions.clear()
        paths = self.settings.recent_files()
        self.recent_divider.setVisible(bool(paths))
        if not paths:
            return
        header = QAction("最近文件", menu)
        header.setEnabled(False)
        menu.insertAction(self.recent_divider, header)
        self._recent_actions.append(header)
        for index, path in enumerate(paths, 1):
            escaped = Path(path).name.replace("&", "&&")
            action = QAction(f"{index}. {escaped}", menu)
            action.setToolTip(path)
            action.setData(path)
            action.triggered.connect(lambda _checked=False, p=path: self.open_recent(p))
            menu.insertAction(self.recent_divider, action)
            self._recent_actions.append(action)

    def open_recent(self, path: str) -> bool:
        if not self._confirm_abandon():
            return False
        return self.open_file(path)

    def _create_tray_icon(self) -> None:
        pixmap = QPixmap(32, 32)
        pixmap.fill(Qt.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setPen(QPen(QColor("#eef2ff"), 3))
        painter.setBrush(QColor("#334155"))
        painter.drawRoundedRect(2, 7, 28, 18, 6, 6)
        painter.drawLine(8, 16, 24, 16)
        painter.end()
        self.tray_icon = QSystemTrayIcon(QIcon(pixmap), self)
        self.tray_icon.setToolTip("OneLine（一行笔记）")
        tray_menu = QMenu(self)
        self.tray_toggle_action = QAction("显示/隐藏 OneLine", self)
        self.tray_toggle_action.triggered.connect(self.toggle_visibility)
        tray_menu.addAction(self.tray_toggle_action)
        tray_menu.addSeparator()
        tray_exit = QAction("退出", self)
        tray_exit.triggered.connect(self.quit_app)
        tray_menu.addAction(tray_exit)
        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.activated.connect(self._tray_activated)
        if QSystemTrayIcon.isSystemTrayAvailable():
            self.tray_icon.show()

    def _tray_activated(self, reason) -> None:
        if reason in (QSystemTrayIcon.Trigger, QSystemTrayIcon.DoubleClick):
            self.toggle_visibility()

    def hide_window(self) -> None:
        if self.menu_button.menu().isVisible():
            self.menu_button.menu().hide()
            return
        self.settings.save_window(self.pos(), self.width(), self.on_top)
        self._write_session()
        self._hidden_by_user = True
        if self.tray_icon.isVisible():
            self.hide()
        else:
            # Some Linux desktops do not expose a system tray. Keep a window
            # available to the desktop's application switcher in that case.
            self.showMinimized()

    def toggle_visibility(self) -> None:
        if self._hidden_by_user or self.isHidden() or self.isMinimized():
            self._hidden_by_user = False
            self.showNormal()
            self.raise_()
            self.activateWindow()
            self.editor.setFocus()
        else:
            self.hide_window()

    def quit_app(self) -> None:
        if self.close():
            QApplication.instance().quit()

    def _update_title(self) -> None:
        name = Path(self.file_path).name if self.file_path else "未命名"
        self.setWindowTitle(f"{name} — OneLine")

    def _show_error(self, title: str, error: Exception) -> None:
        QMessageBox.critical(self, title, str(error))

    def _confirm_abandon(self) -> bool:
        if not self.editor.document().isModified():
            return True
        choice = self._ask_unsaved()
        if choice == "cancel":
            return False
        if choice == "save":
            return self.save_document()
        return choice == "discard"

    def _ask_unsaved(self) -> str:
        dialog = QMessageBox(self)
        dialog.setIcon(QMessageBox.Warning)
        dialog.setWindowTitle("未保存的更改")
        dialog.setText("当前内容尚未保存。要保存后继续吗？")
        save_button = dialog.addButton("保存", QMessageBox.AcceptRole)
        discard_button = dialog.addButton("不保存", QMessageBox.DestructiveRole)
        dialog.addButton("取消", QMessageBox.RejectRole)
        dialog.setDefaultButton(save_button)
        dialog.exec_()
        clicked = dialog.clickedButton()
        if clicked == save_button:
            return "save"
        if clicked == discard_button:
            return "discard"
        return "cancel"

    def _set_document(self, document: TextFile, path: str | None) -> None:
        self._session_timer.stop()
        self.file_path = path
        self._disk_digest = document.source_digest if path else None
        self.newline = document.newline
        self.bom = document.bom
        self.editor.setPlainText(document.text)
        self.editor.document().setModified(False)
        self._update_dirty_state(False)
        self._update_title()
        self._schedule_session()
        self.editor.setFocus()

    def new_document(self) -> bool:
        if not self._confirm_abandon():
            return False
        self._set_document(TextFile(""), None)
        return True

    def open_document(self) -> bool:
        if not self._confirm_abandon():
            return False
        path, _ = QFileDialog.getOpenFileName(
            self, "打开文本文件", self.settings.recent_file(), "文本文件 (*.txt);;所有文件 (*)"
        )
        return self.open_file(path) if path else False

    def open_file(self, path: str) -> bool:
        try:
            document = read_text_file(path)
        except (OSError, UnicodeError) as error:
            self._show_error("打开文件失败", error)
            return False
        absolute = str(Path(path).resolve())
        self._set_document(document, absolute)
        self.settings.set_recent_file(absolute)
        self._refresh_recent_actions()
        return True

    def save_document(self) -> bool:
        if self.file_path is None:
            return self.save_as_document()
        return self._save_to_path(self.file_path)

    def save_as_document(self) -> bool:
        initial = self.file_path or self.settings.recent_file() or "未命名.txt"
        path, _ = QFileDialog.getSaveFileName(
            self, "另存为文本文件", initial, "文本文件 (*.txt);;所有文件 (*)"
        )
        if not path:
            return False
        target = Path(path)
        if not target.suffix:
            target = target.with_suffix(".txt")
        return self._save_to_path(str(target))

    def _save_to_path(self, path: str) -> bool:
        try:
            absolute = str(Path(path).resolve())
            if absolute == self.file_path:
                if self._disk_digest is None or file_digest(path) != self._disk_digest:
                    raise OSError("文件已在外部更改；请先核对磁盘版本，再另存为新文件")
            written_digest = write_text_file(
                path, TextFile(self.editor.toPlainText(), self.newline, self.bom)
            )
        except (OSError, ValueError) as error:
            self._show_error("保存文件失败", error)
            return False
        self.file_path = absolute
        self._disk_digest = written_digest
        self.settings.set_recent_file(self.file_path)
        self._refresh_recent_actions()
        self.editor.document().setModified(False)
        self._update_dirty_state(False)
        self._update_title()
        self._write_session()
        return True

    def _schedule_session(self) -> None:
        if self.settings.restore_session():
            self._session_timer.start()

    def _write_session(self) -> None:
        if not self.settings.restore_session():
            return
        # This snapshot contains all edits Qt has already applied.
        self._session_timer.stop()
        snapshot = Session(
            self.editor.toPlainText(),
            self.editor.textCursor().position(),
            self.file_path,
            self.editor.document().isModified(),
            self.newline,
            self.bom,
            self.editor.current_line_number(),
            self.pos().x(),
            self.pos().y(),
            self.width(),
            self.on_top,
        )
        try:
            self.sessions.save(snapshot)
        except OSError as error:
            self._session_error = str(error)
            self._update_dirty_state(self.editor.document().isModified())
        else:
            if self._session_error is not None:
                self._session_error = None
                self._update_dirty_state(self.editor.document().isModified())

    def _restore_session(self) -> None:
        if not self.settings.restore_session():
            return
        snapshot = self.sessions.load()
        if snapshot is not None:
            self._apply_session_window(snapshot)
        if snapshot is not None and snapshot.modified:
            # A recovery snapshot has no trustworthy baseline for its source
            # file: another program may have changed that TXT since the crash.
            # Keep the text but require an explicit Save As instead of letting
            # Ctrl+S silently replace a newer disk version.
            self._set_document(
                TextFile(snapshot.text, snapshot.newline, snapshot.bom), None
            )
            self.editor.document().setModified(True)
            self._restore_cursor(snapshot.cursor)
            self._show_recovery_state()
            return

        path = (snapshot.path if snapshot else None) or self.settings.recent_file()
        if path and Path(path).is_file():
            try:
                document = read_text_file(path)
            except (OSError, UnicodeError):
                document = None
            if document is not None:
                self._set_document(document, str(Path(path).resolve()))
                if snapshot is not None and snapshot.path == path:
                    self._restore_cursor(snapshot.cursor)
                    self._show_recovery_state()
                return
        if snapshot is not None and snapshot.path is None:
            self._set_document(TextFile(snapshot.text), None)
            self._restore_cursor(snapshot.cursor)
            self._show_recovery_state()
        elif snapshot is not None and snapshot.path is not None:
            # A saved file may have been moved or deleted since the last run.
            # Keep the locally recovered text, but require Save As before any
            # file can be written.
            self._set_document(
                TextFile(snapshot.text, snapshot.newline, snapshot.bom), None
            )
            self.editor.document().setModified(True)
            self._restore_cursor(snapshot.cursor)
            self._show_recovery_state()

    def _apply_session_window(self, snapshot: Session) -> None:
        if snapshot.window_width is not None:
            self.resize(max(MINIMUM_WIDTH, min(5000, snapshot.window_width)), WINDOW_HEIGHT)
        if snapshot.window_x is not None and snapshot.window_y is not None:
            self.move(QPoint(snapshot.window_x, snapshot.window_y))
        # The current startup preference wins for topmost state; QSettings is
        # updated immediately when the user changes it, while a recovery
        # snapshot can lag behind by the debounce interval.

    def _show_recovery_state(self) -> None:
        self._recovery_active = True
        self._set_status("recovering")
        QTimer.singleShot(150, self._finish_recovery)

    def _finish_recovery(self) -> None:
        self._recovery_active = False
        self._update_dirty_state(self.editor.document().isModified())

    def _restore_cursor(self, position: int) -> None:
        cursor = self.editor.textCursor()
        # QTextCursor positions count UTF-16 code units, unlike Python len().
        document_end = max(0, self.editor.document().characterCount() - 1)
        cursor.setPosition(max(0, min(position, document_end)))
        self.editor.setTextCursor(cursor)

    def show_find(self) -> None:
        if self._find_dialog is None:
            self._find_dialog = FindDialog(self)
        self._find_dialog.show()
        self._find_dialog.raise_()
        self._find_dialog.query.setFocus()

    def find_text(self, query: str, backward: bool = False) -> bool:
        if not query:
            return False
        flags = QTextDocument.FindBackward if backward else QTextDocument.FindFlags()
        if self.editor.find(query, flags):
            return True
        cursor = self.editor.textCursor()
        cursor.movePosition(QTextCursor.End if backward else QTextCursor.Start)
        self.editor.setTextCursor(cursor)
        return self.editor.find(query, flags)

    def toggle_on_top(self) -> None:
        self.on_top = self.top_action.isChecked()
        position = self.pos()
        visible = self.isVisible()
        self._set_window_flags()
        self.move(position)
        if visible:
            self.show()
        self.settings.save_window(self.pos(), self.width(), self.on_top)
        self._schedule_session()

    def reset_size(self) -> None:
        self.resize(DEFAULT_WIDTH, WINDOW_HEIGHT)
        self.settings.save_window(self.pos(), self.width(), self.on_top)
        self._schedule_session()

    def toggle_theme(self) -> None:
        self.theme = "light" if self.theme == "dark" else "dark"
        self.settings.set_theme(self.theme)
        self._apply_style()

    def show_preferences(self) -> None:
        dialog = PreferencesDialog(self.settings, self.editor.font(), self)
        if dialog.exec_() != QDialog.Accepted:
            return
        self._set_font_family(dialog.font_family.currentFont().family())
        self._set_font_size(dialog.font_size.value())
        opacity = dialog.opacity.value() / 100
        self.setWindowOpacity(opacity)
        self.settings.set_opacity(opacity)
        restore = dialog.restore_session.isChecked()
        self.settings.set_restore_session(restore)
        if not restore:
            self._session_timer.stop()
            self._session_error = None
            self._update_dirty_state(self.editor.document().isModified())
            try:
                self.sessions.clear()
            except OSError as error:
                self._show_error("清除恢复文件失败", error)
        desired_top = dialog.start_on_top.isChecked()
        if desired_top != self.on_top:
            self.top_action.setChecked(desired_top)
            self.toggle_on_top()
        desired_theme = "dark" if dialog.dark_mode.isChecked() else "light"
        if desired_theme != self.theme:
            self.toggle_theme()
        shortcut = dialog.hide_shortcut.keySequence().toString(QKeySequence.PortableText)
        self.settings.set_hide_shortcut(shortcut)
        self.hide_action.setShortcut(dialog.hide_shortcut.keySequence())
        if restore:
            self._write_session()

    def _set_font_size(self, size: int, persist: bool = True) -> None:
        was_modified = self.editor.document().isModified()
        font = QFont(self.editor.font())
        font.setPixelSize(size)
        self.editor.setFont(font)
        self.editor.setFixedHeight(self.editor.fontMetrics().lineSpacing() + 10)
        self.editor.document().setModified(was_modified)
        if persist:
            self.settings.set_font_size(size)

    def _set_font_family(self, family: str, persist: bool = True) -> None:
        was_modified = self.editor.document().isModified()
        font = QFont(self.editor.font())
        font.setFamily(family)
        self.editor.setFont(font)
        self.editor.setFixedHeight(self.editor.fontMetrics().lineSpacing() + 10)
        self.editor.document().setModified(was_modified)
        if persist:
            self.settings.set_font_family(family)

    def _update_line_label(self, current: int, total: int) -> None:
        self.line_label.setText(f"{current}/{total}")

    def _update_dirty_state(self, modified: bool) -> None:
        if self._recovery_active:
            return
        if self._session_error is not None:
            self._set_status("recovery_unavailable")
            return
        self._set_status("dirty" if modified else "saved")

    def _set_status(self, status: str) -> None:
        symbol, hint = {
            "saved": ("✓", "已保存"),
            "dirty": ("●", "尚未保存"),
            "recovering": ("⟳", "正在恢复上次会话"),
            "recovery_unavailable": (
                "!", f"自动恢复暂不可用：{self._session_error}"
            ),
        }[status]
        self.dirty_label.setText(symbol)
        self.dirty_label.setToolTip(hint)
        self.dirty_label.setProperty("status", status)
        self.dirty_label.style().unpolish(self.dirty_label)
        self.dirty_label.style().polish(self.dirty_label)

    def closeEvent(self, event) -> None:  # noqa: N802 - Qt API
        was_modified = self.editor.document().isModified()
        if not self._confirm_abandon():
            event.ignore()
            return
        self._session_timer.stop()
        self.settings.save_window(self.pos(), self.width(), self.on_top)
        if was_modified and self.editor.document().isModified():
            # The user chose Discard. Keep the prior saved file available via
            # recent path, but never resurrect the discarded edit.
            try:
                self.sessions.clear()
            except OSError as error:
                self._show_error("清除恢复文件失败", error)
                event.ignore()
                return
        else:
            self._write_session()
        event.accept()

    def moveEvent(self, event) -> None:  # noqa: N802 - Qt API
        super().moveEvent(event)
        if hasattr(self, "editor"):
            self._schedule_session()

    def resizeEvent(self, event) -> None:  # noqa: N802 - Qt API
        super().resizeEvent(event)
        if hasattr(self, "editor"):
            self._schedule_session()

    def _apply_style(self) -> None:
        if self.theme == "dark":
            panel, border, text, muted, hover, menu, selection = (
                "#1e293b", "#3b4758", "#f8fafc", "#94a3b8",
                "#334155", "#0f172a", "#334e78",
            )
            saved, dirty, recovering = "#8fa1ad", "#b0a48e", "#92a5b7"
        else:
            panel, border, text, muted, hover, menu, selection = (
                "#f8fafc", "#d8dee7", "#0f172a", "#7b8796",
                "#e9eef4", "#ffffff", "#bfdbfe",
            )
            saved, dirty, recovering = "#788b89", "#9b8b72", "#8295a6"
        self.menu_button.set_colors(muted, hover)
        self.menu_button.menu().set_colors(menu, hover, muted)
        self.setStyleSheet(
            f"""
            QFrame#panel {{ background: {panel}; border: 1px solid {border}; border-radius: 11px; }}
            QLabel#dragHandle {{ color: {muted}; border: none; font-size: 13px; }}
            QLabel#dragHandle:hover {{ color: {text}; background: {hover}; border-radius: 5px; }}
            QPlainTextEdit#oneLineEditor {{ color: {text}; background: transparent;
                border: none; padding: 0px; selection-background-color: {selection}; }}
            QLabel#lineLabel {{ color: {muted}; border: none; font-size: 11px; }}
            QLabel#dirtyLabel {{ color: {saved}; border: none; font-size: 12px; }}
            QLabel#dirtyLabel[status="dirty"] {{ color: {dirty}; font-size: 10px; }}
            QLabel#dirtyLabel[status="recovering"] {{ color: {recovering}; font-size: 14px; }}
            QLabel#dirtyLabel[status="recovery_unavailable"] {{ color: {dirty}; font-size: 12px; }}
            QLabel#resizeHandle {{ border: none; background: transparent; }}
            QMenu {{ background: {menu}; color: {text}; border: 1px solid {border};
                border-radius: 8px; padding: 4px; font-size: 12px; }}
            QMenu::item {{ padding: 5px 22px 5px 10px; }}
            QMenu::item:selected {{ background: {hover}; }}
            """
        )
        if hasattr(self, "visual_line_overlay"):
            self.visual_line_overlay.refresh_appearance()
