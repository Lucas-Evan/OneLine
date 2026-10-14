"""Qt test fixtures that do not require pytest-qt."""

from __future__ import annotations

import os
import sys

import pytest
from PyQt5.QtCore import QSettings
from PyQt5.QtWidgets import QApplication

from session import SessionStore
from settings import SettingsStore
from window import OneLineWindow


os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


# Explicit file-level ownership keeps an obsolete private-API assertion from
# silently becoming a release requirement. Newly added test files must be
# classified here before collection succeeds.
RELEASE_FILES = {
    "test_file_manager.py", "test_menu_shortcuts.py", "test_navigation_visibility.py",
    "test_persistence_compat.py", "test_product_experience.py",
    "test_release_navigation.py", "test_release_session_failure.py",
    "test_vertical_alignment.py", "test_viewport_space.py",
    "test_visual_line_overlay.py", "test_visual_polish.py", "test_visual_wrap.py",
    "test_window.py", "test_wrap_layout_warning.py",
}
LEGACY_FILES = {
    "test_input_stability.py", "test_native_scroll_rollback.py",
    "test_performance_stress.py", "test_visual_wrap_scroll_regression.py",
}
DIAGNOSTIC_FILES = {
    "test_delete_isolation.py", "test_editor.py", "test_long_line_experience.py",
}


def pytest_collection_modifyitems(items):
    for item in items:
        name = item.path.name
        if name in RELEASE_FILES:
            item.add_marker(pytest.mark.release)
        elif name in LEGACY_FILES:
            item.add_marker(pytest.mark.legacy)
        elif name in DIAGNOSTIC_FILES:
            item.add_marker(pytest.mark.diagnostic)
        else:
            raise pytest.UsageError(f"未分类测试文件：{name}")


@pytest.fixture(scope="session")
def app():
    instance = QApplication.instance() or QApplication(sys.argv[:1])
    yield instance


@pytest.fixture
def window_factory(tmp_path):
    settings = SettingsStore(QSettings(str(tmp_path / "settings.ini"), QSettings.IniFormat))
    sessions = SessionStore(tmp_path / "session.json")

    def create():
        return OneLineWindow(settings=settings, sessions=sessions)

    return create
