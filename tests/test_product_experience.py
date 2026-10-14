from __future__ import annotations

from PyQt5.QtCore import QPoint, Qt
from PyQt5.QtGui import QFont, QFontDatabase, QKeySequence
from PyQt5.QtTest import QTest
from PyQt5.QtWidgets import QDialog

import window as window_module
from preferences import PreferencesDialog


def test_flat_menu_and_recent_file_actions(app, window_factory, tmp_path):
    window = window_factory()
    paths = []
    for number in range(6):
        path = tmp_path / f"memo-{number}.txt"
        path.write_text(f"备忘 {number}", encoding="utf-8")
        paths.append(path)
        assert window.open_file(str(path))

    window._refresh_recent_actions()
    menu = window.menu_button.menu()
    labels = [action.text() for action in menu.actions() if not action.isSeparator()]
    assert labels[:5] == ["新建", "打开…", "保存", "另存为…", "查找…"]
    assert "始终置顶" in labels
    assert "设置…" in labels
    assert "退出" in labels
    assert not any(action.menu() for action in menu.actions())

    recent = [action for action in menu.actions() if action.data()]
    assert len(recent) == 5
    assert recent[0].data() == str(paths[-1])
    assert all(action.data() != str(paths[0]) for action in recent)
    recent[-1].trigger()
    assert window.file_path == str(paths[1])
    assert window.editor.toPlainText() == "备忘 1"


def test_escape_closes_menu_then_hides_window(app, window_factory):
    window = window_factory()
    window.show()
    app.processEvents()
    menu = window.menu_button.menu()
    menu.show()
    app.processEvents()

    QTest.keyClick(menu, Qt.Key_Escape)
    app.processEvents()
    assert not menu.isVisible()
    assert window.isVisible()

    window.editor.setFocus()
    QTest.keyClick(window.editor, Qt.Key_Escape)
    app.processEvents()
    assert window._hidden_by_user
    assert window.isHidden() or window.isMinimized()

    window.tray_toggle_action.trigger()
    app.processEvents()
    assert not window._hidden_by_user
    assert window.isVisible() and not window.isMinimized()


def test_hide_shortcut_and_ctrl_q(app, window_factory):
    window = window_factory()
    window.show()
    window.editor.setFocus()
    app.processEvents()

    QTest.keyClick(window.editor, Qt.Key_Space, Qt.ControlModifier | Qt.ShiftModifier)
    app.processEvents()
    assert window._hidden_by_user
    window.toggle_visibility()

    window.editor.setFocus()
    QTest.keyClick(window.editor, Qt.Key_Q, Qt.ControlModifier)
    app.processEvents()
    assert not window.isVisible()


def test_preferences_save_and_custom_hide_shortcut(
    app, window_factory, monkeypatch
):
    window = window_factory()
    original_dialog = PreferencesDialog
    chosen = {}

    def configured_dialog(settings, current_font, parent):
        dialog = original_dialog(settings, current_font, parent)
        dialog.font_family.setCurrentFont(
            QFont(QFontDatabase.systemFont(QFontDatabase.FixedFont).family())
        )
        chosen["family"] = dialog.font_family.currentFont().family()
        dialog.font_size.setValue(18)
        dialog.opacity.setValue(85)
        dialog.restore_session.setChecked(False)
        dialog.start_on_top.setChecked(False)
        dialog.dark_mode.setChecked(True)
        dialog.hide_shortcut.setKeySequence(QKeySequence("Ctrl+Alt+Space"))
        dialog.exec_ = lambda: QDialog.Accepted
        return dialog

    monkeypatch.setattr(window_module, "PreferencesDialog", configured_dialog)
    window.show_preferences()

    assert window.editor.font().pixelSize() == 18
    assert window.settings.font_family() == chosen["family"]
    assert window.settings.opacity() == 0.85
    assert not window.settings.restore_session()
    assert not window.on_top
    assert window.theme == "dark"
    assert window.hide_action.shortcut() == QKeySequence("Ctrl+Alt+Space")
    assert window.sessions.load() is None

    restarted = window_factory()
    assert restarted.editor.font().pixelSize() == 18
    assert restarted.settings.font_family() == chosen["family"]
    assert restarted.settings.opacity() == 0.85
    assert restarted.theme == "dark"
    assert not restarted.on_top
    assert restarted.hide_action.shortcut() == QKeySequence("Ctrl+Alt+Space")


def test_session_records_line_file_and_window_state(
    app, window_factory, tmp_path
):
    path = tmp_path / "current.txt"
    path.write_text("第一行\n第二行\n第三行", encoding="utf-8")
    first = window_factory()
    assert first.open_file(str(path))
    first.editor.go_to_line(3, 2)
    first.move(QPoint(160, 170))
    first.resize(670, 56)
    first._write_session()
    snapshot = first.sessions.load()

    assert snapshot is not None
    assert snapshot.path == str(path)
    assert snapshot.line == 3
    assert snapshot.cursor == first.editor.textCursor().position()
    assert (snapshot.window_x, snapshot.window_y, snapshot.window_width) == (160, 170, 670)
    assert snapshot.on_top == first.on_top

    restarted = window_factory()
    assert restarted.file_path == str(path)
    assert restarted.editor.current_line_number() == 3
    assert restarted.pos() == QPoint(160, 170)
    assert restarted.width() == 670
    assert restarted.dirty_label.text() == "⟳"
    restarted._finish_recovery()
    assert restarted.dirty_label.text() == "✓"


def test_restore_disabled_starts_blank(app, window_factory):
    first = window_factory()
    first.editor.insertPlainText("私有草稿")
    first._write_session()
    first.settings.set_restore_session(False)

    restarted = window_factory()
    assert restarted.editor.toPlainText() == ""
    assert restarted.file_path is None
