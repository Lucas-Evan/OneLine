"""A failed crash snapshot is visible without interrupting editing."""

from __future__ import annotations

import os


def test_unwritable_session_directory_reports_and_recovers(
    app, window_factory, tmp_path
):
    directory = tmp_path / "readonly"
    directory.mkdir()
    window = window_factory()
    window.sessions.path = directory / "session.json"
    window.editor.insertPlainText("first")

    os.chmod(directory, 0o500)
    try:
        window._write_session()
        assert window.dirty_label.text() == "!"
        assert "自动恢复暂不可用" in window.dirty_label.toolTip()
        window.editor.insertPlainText("second")
        assert window.editor.toPlainText() == "firstsecond"
        assert window.dirty_label.text() == "!"
    finally:
        os.chmod(directory, 0o700)

    window._write_session()
    assert window.dirty_label.text() == "●"
    assert directory.joinpath("session.json").is_file()
