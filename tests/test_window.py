from __future__ import annotations

from PyQt5.QtCore import QPoint, Qt
from PyQt5.QtTest import QTest
from PyQt5.QtWidgets import QFileDialog, QMessageBox

from session import Session


def test_save_then_reopen_multiline_content(app, window_factory, tmp_path):
    path = tmp_path / "notes.txt"
    content = "今天需要完成的工作\n整理项目材料\n检查软件功能"
    window = window_factory()
    window.editor.setPlainText(content)

    assert window._save_to_path(str(path))
    assert window.dirty_label.text() == "✓"
    assert path.read_text(encoding="utf-8") == content

    reopened = window_factory()
    assert reopened.editor.toPlainText() == content
    assert reopened.file_path == str(path)


def test_file_shortcuts_open_save_as_save_and_new(
    app, window_factory, tmp_path, monkeypatch
):
    source = tmp_path / "source.txt"
    source.write_text("原文", encoding="utf-8")
    target = tmp_path / "copy.txt"
    monkeypatch.setattr(
        QFileDialog, "getOpenFileName", lambda *_args: (str(source), "文本文件 (*.txt)")
    )
    monkeypatch.setattr(
        QFileDialog, "getSaveFileName", lambda *_args: (str(target), "文本文件 (*.txt)")
    )
    window = window_factory()
    window.show()
    window.editor.setFocus()
    app.processEvents()

    QTest.keyClick(window.editor, Qt.Key_O, Qt.ControlModifier)
    app.processEvents()
    assert window.editor.toPlainText() == "原文"

    QTest.keyClick(window.editor, Qt.Key_S, Qt.ControlModifier | Qt.ShiftModifier)
    app.processEvents()
    assert target.read_text(encoding="utf-8") == "原文"
    window.editor.insertPlainText("追加")
    QTest.keyClick(window.editor, Qt.Key_S, Qt.ControlModifier)
    app.processEvents()
    assert target.read_text(encoding="utf-8") == "追加原文"

    QTest.keyClick(window.editor, Qt.Key_N, Qt.ControlModifier)
    app.processEvents()
    assert window.editor.toPlainText() == ""
    assert window.file_path is None


def test_open_bom_file_then_save_retains_bom_and_crlf(app, window_factory, tmp_path):
    path = tmp_path / "bom.txt"
    path.write_bytes(b"\xef\xbb\xbf" + "初始\r\n第二行".encode("utf-8"))
    window = window_factory()

    assert window.open_file(str(path))
    assert window.editor.toPlainText() == "初始\n第二行"
    window.editor.insertPlainText("！")
    assert window.save_document()
    assert path.read_bytes().startswith(b"\xef\xbb\xbf")
    assert b"\r\n" in path.read_bytes()


def test_save_refuses_to_replace_externally_changed_file(
    app, window_factory, tmp_path, monkeypatch
):
    path = tmp_path / "shared.txt"
    path.write_text("原始版本", encoding="utf-8")
    window = window_factory()
    assert window.open_file(str(path))
    window.editor.insertPlainText("本地修改")
    path.write_text("外部修改", encoding="utf-8")
    errors = []
    monkeypatch.setattr(window, "_show_error", lambda title, error: errors.append((title, str(error))))

    assert not window.save_document()
    assert path.read_text(encoding="utf-8") == "外部修改"
    assert window.editor.document().isModified()
    assert errors and "外部更改" in errors[0][1]

    copy = tmp_path / "local-copy.txt"
    monkeypatch.setattr(
        QFileDialog, "getSaveFileName", lambda *_args: (str(copy), "文本文件 (*.txt)")
    )
    assert window.save_as_document()
    assert path.read_text(encoding="utf-8") == "外部修改"
    assert copy.read_text(encoding="utf-8") == window.editor.toPlainText()
    assert not window.editor.document().isModified()


def test_modified_close_offers_save_discard_cancel(app, window_factory, monkeypatch):
    window = window_factory()
    window.show()
    window.editor.insertPlainText("未保存的内容")
    seen = []

    def cancel_dialog(self):
        seen.append({button.text() for button in self.buttons()})
        return 0

    monkeypatch.setattr(QMessageBox, "exec_", cancel_dialog)
    assert not window.close()
    assert window.isVisible()
    assert seen == [{"保存", "不保存", "取消"}]

    monkeypatch.setattr(window, "_ask_unsaved", lambda: "discard")
    assert window.close()
    assert window.sessions.load() is None


def test_restart_recovers_unsaved_text_and_cursor(app, window_factory):
    first = window_factory()
    first.editor.insertPlainText("第一行\n第二行的未保存内容")
    first.editor.go_to_line(2, 3)
    first._write_session()

    restored = window_factory()
    assert restored.editor.toPlainText() == first.editor.toPlainText()
    assert restored.editor.textCursor().position() == first.editor.textCursor().position()
    assert restored.editor.document().isModified()
    assert restored.dirty_label.text() == "⟳"
    restored._finish_recovery()
    assert restored.dirty_label.text() == "●"


def test_restart_restores_cursor_after_emoji(app, window_factory):
    first = window_factory()
    first.editor.insertPlainText("😀后面的文字")
    first._write_session()

    restored = window_factory()
    assert restored.editor.textCursor().position() == first.editor.textCursor().position()


def test_recovery_never_writes_back_to_saved_file(app, window_factory, tmp_path):
    path = tmp_path / "saved.txt"
    path.write_text("磁盘上的原文", encoding="utf-8")
    first = window_factory()
    first.sessions.save(Session("恢复出的草稿", 4, str(path), True))

    restored = window_factory()
    assert restored.editor.toPlainText() == "恢复出的草稿"
    assert restored.editor.document().isModified()
    assert path.read_text(encoding="utf-8") == "磁盘上的原文"
    assert restored.file_path is None


def test_modified_recovery_requires_save_as_before_replacing_a_newer_file(
    app, window_factory, tmp_path, monkeypatch
):
    source = tmp_path / "saved.txt"
    source.write_text("外部更新后的正文", encoding="utf-8")
    copy = tmp_path / "recovered.txt"
    first = window_factory()
    first.sessions.save(Session("旧会话草稿", 2, str(source), True))

    restored = window_factory()
    assert restored.file_path is None
    assert restored.editor.toPlainText() == "旧会话草稿"
    monkeypatch.setattr(
        QFileDialog, "getSaveFileName", lambda *_args: (str(copy), "文本文件 (*.txt)")
    )
    assert restored.save_document()
    assert source.read_text(encoding="utf-8") == "外部更新后的正文"
    assert copy.read_text(encoding="utf-8") == "旧会话草稿"


def test_missing_saved_file_recovers_as_unsaved_copy(app, window_factory, tmp_path):
    first = window_factory()
    first.sessions.save(Session("仅剩恢复副本", 3, str(tmp_path / "gone.txt"), False))

    restored = window_factory()
    assert restored.editor.toPlainText() == "仅剩恢复副本"
    assert restored.editor.document().isModified()
    assert restored.file_path is None


def test_window_position_width_and_top_state_restore(app, window_factory):
    first = window_factory()
    first.move(QPoint(120, 130))
    first.resize(650, 56)
    first.top_action.trigger()
    expected_top = first.on_top
    assert first.close()

    restored = window_factory()
    assert restored.pos() == QPoint(120, 130)
    assert restored.width() == 650
    assert restored.on_top == expected_top


def test_unavailable_saved_screen_position_is_recovered(app, window_factory):
    first = window_factory()
    first.settings.save_window(QPoint(100_000, 100_000), 650, first.on_top)

    restored = window_factory()
    assert any(
        screen.availableGeometry().intersects(restored.geometry())
        for screen in app.screens()
    )


def test_theme_and_font_size_restore(app, window_factory):
    first = window_factory()
    first.toggle_theme()
    first._set_font_size(18)

    restored = window_factory()
    assert restored.theme == "dark"
    assert restored.editor.font().pixelSize() == 18
    assert restored.height() == 56


def test_top_shortcut_does_not_use_ctrl_t(app, window_factory):
    window = window_factory()
    window.show()
    window.editor.setFocus()
    app.processEvents()

    QTest.keyClick(window.editor, Qt.Key_T, Qt.ControlModifier)
    app.processEvents()
    assert window.on_top
    QTest.keyClick(window.editor, Qt.Key_T, Qt.ControlModifier | Qt.ShiftModifier)
    app.processEvents()
    assert not window.on_top


def test_find_wraps_both_directions_without_resizing(app, window_factory):
    window = window_factory()
    window.editor.setPlainText("alpha\nbeta\nalpha")
    window.editor.go_to_line(3, 5)

    assert window.find_text("alpha")
    assert window.editor.current_line_number() == 1
    assert window.find_text("alpha", backward=True)
    assert window.editor.current_line_number() == 3
    assert window.height() == 56


def test_save_failure_keeps_dirty_state_and_reports_error(
    app, window_factory, tmp_path, monkeypatch
):
    window = window_factory()
    window.editor.insertPlainText("重要内容")
    errors = []
    monkeypatch.setattr(window, "_show_error", lambda title, error: errors.append((title, error)))

    assert not window._save_to_path(str(tmp_path / "missing" / "file.txt"))
    assert window.editor.document().isModified()
    assert errors and errors[0][0] == "保存文件失败"
