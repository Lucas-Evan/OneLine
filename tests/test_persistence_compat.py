from __future__ import annotations

import json

from PyQt5.QtCore import QSettings

from session import SessionStore
from settings import SettingsStore


def test_stage_two_recent_file_setting_is_still_readable(tmp_path):
    backend = QSettings(str(tmp_path / "settings.ini"), QSettings.IniFormat)
    backend.setValue("file/recent_path", "/example/old.txt")
    store = SettingsStore(backend)

    assert store.recent_files() == ["/example/old.txt"]
    store.record_recent_file("/example/new.txt")
    assert store.recent_files() == ["/example/new.txt", "/example/old.txt"]


def test_stage_two_session_snapshot_is_still_readable(tmp_path):
    path = tmp_path / "session.json"
    path.write_text(
        json.dumps({
            "version": 1,
            "text": "旧版草稿",
            "cursor": 2,
            "path": None,
            "modified": True,
            "newline": "\n",
            "bom": False,
        }),
        encoding="utf-8",
    )

    snapshot = SessionStore(path).load()
    assert snapshot is not None
    assert snapshot.text == "旧版草稿"
    assert snapshot.line == 1
    assert snapshot.window_width is None


def test_session_with_valid_json_but_wrong_root_type_is_ignored(tmp_path):
    path = tmp_path / "session.json"
    for payload in ("[]", '"not an object"', "42", "null"):
        path.write_text(payload, encoding="utf-8")
        assert SessionStore(path).load() is None


def test_invalid_typed_settings_fall_back_without_crashing(tmp_path):
    backend = QSettings(str(tmp_path / "settings.ini"), QSettings.IniFormat)
    backend.setValue("window/width", "not a number")
    backend.setValue("appearance/font_size", "broken")
    backend.setValue("window/opacity", "not a float")
    backend.setValue("window/hide_shortcut", "not a shortcut")
    store = SettingsStore(backend)

    assert store.width(800) == 800
    assert store.font_size() == 14
    assert store.opacity() == 1.0
    assert store.hide_shortcut() == "Ctrl+Shift+Space"
