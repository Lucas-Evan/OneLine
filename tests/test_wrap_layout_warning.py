"""The wrap diagnostic records only block sizes, never document content."""

from __future__ import annotations

import logging

from PyQt5.QtWidgets import QPlainTextEdit

from editor import OneLineEditor


def test_wrapped_block_warning_starts_above_5000_and_does_not_log_text(app, caplog):
    editor = OneLineEditor()
    with caplog.at_level(logging.WARNING, logger="editor"):
        editor.setPlainText("private" + "a" * 4_993)
        assert not caplog.records
        editor.insertPlainText("b")
        assert len(caplog.records) == 1
        editor.insertPlainText("c")
        assert len(caplog.records) == 1

    message = caplog.records[0].getMessage()
    assert "length=5001" in message
    assert "private" not in message
    assert "a" * 20 not in message


def test_no_wrap_does_not_emit_wrapped_block_warning(app, caplog):
    editor = OneLineEditor()
    editor.setLineWrapMode(QPlainTextEdit.NoWrap)
    with caplog.at_level(logging.WARNING, logger="editor"):
        editor.setPlainText("a" * 10_000)
    assert not caplog.records


def test_warning_covers_a_long_block_before_the_cursor(app, caplog):
    editor = OneLineEditor()
    with caplog.at_level(logging.WARNING, logger="editor"):
        editor.setPlainText("short\n" + "中" * 5_001 + "\nend")
    assert len(caplog.records) == 1
    assert "block=1 length=5001" in caplog.records[0].getMessage()
    assert "中" not in caplog.records[0].getMessage()
