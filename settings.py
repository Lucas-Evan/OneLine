"""Small wrapper around user-scoped Qt settings."""

from __future__ import annotations

import math

from PyQt5.QtCore import QPoint, QSettings
from PyQt5.QtGui import QKeySequence


class SettingsStore:
    def __init__(self, backend: QSettings | None = None) -> None:
        self.backend = backend or QSettings(
            QSettings.IniFormat, QSettings.UserScope, "OneLine", "OneLine"
        )

    def _value(self, key: str, default, value_type):
        # Corrupt INI values must not prevent the editor from starting.
        try:
            return self.backend.value(key, default, type=value_type)
        except (TypeError, ValueError, OverflowError):
            return default

    def position(self) -> QPoint | None:
        value = self.backend.value("window/position")
        return value if isinstance(value, QPoint) else None

    def width(self, default: int) -> int:
        return max(300, min(5000, self._value("window/width", default, int)))

    def always_on_top(self) -> bool:
        return self._value("window/always_on_top", True, bool)

    def theme(self) -> str:
        value = self._value("appearance/theme", "light", str)
        return value if value in ("light", "dark") else "light"

    def font_size(self) -> int:
        value = self._value("appearance/font_size", 14, int)
        return value if 11 <= value <= 22 else 14

    def font_family(self) -> str:
        return self._value("appearance/font_family", "", str)

    def opacity(self) -> float:
        value = self._value("window/opacity", 1.0, float)
        if not math.isfinite(value):
            return 1.0
        return max(0.75, min(1.0, value))

    def restore_session(self) -> bool:
        return self._value("session/restore_on_start", True, bool)

    def hide_shortcut(self) -> str:
        value = self._value("window/hide_shortcut", "Ctrl+Shift+Space", str)
        # QKeySequence can hold an invalid key while reporting isEmpty=False.
        return value if QKeySequence(value).toString(QKeySequence.PortableText) else "Ctrl+Shift+Space"

    def recent_file(self) -> str:
        recent = self.recent_files()
        return recent[0] if recent else ""

    def recent_files(self) -> list[str]:
        stored = self.backend.value("file/recent_paths", [])
        if isinstance(stored, str):
            stored = [stored] if stored else []
        if not isinstance(stored, list):
            stored = []
        paths = [value for value in stored if isinstance(value, str) and value]
        if not paths:
            legacy = self._value("file/recent_path", "", str)
            if legacy:
                paths = [legacy]
        return list(dict.fromkeys(paths))[:5]

    def save_window(self, position: QPoint, width: int, on_top: bool) -> None:
        self.backend.setValue("window/position", position)
        self.backend.setValue("window/width", width)
        self.backend.setValue("window/always_on_top", on_top)
        self.backend.sync()

    def set_theme(self, theme: str) -> None:
        self.backend.setValue("appearance/theme", theme)
        self.backend.sync()

    def set_font_size(self, size: int) -> None:
        self.backend.setValue("appearance/font_size", size)
        self.backend.sync()

    def set_font_family(self, family: str) -> None:
        self.backend.setValue("appearance/font_family", family)
        self.backend.sync()

    def set_opacity(self, opacity: float) -> None:
        self.backend.setValue("window/opacity", max(0.75, min(1.0, opacity)))
        self.backend.sync()

    def set_restore_session(self, enabled: bool) -> None:
        self.backend.setValue("session/restore_on_start", enabled)
        self.backend.sync()

    def set_hide_shortcut(self, shortcut: str) -> None:
        self.backend.setValue("window/hide_shortcut", shortcut)
        self.backend.sync()

    def set_recent_file(self, path: str) -> None:
        self.record_recent_file(path)

    def record_recent_file(self, path: str) -> None:
        if not path:
            return
        paths = [path] + [old for old in self.recent_files() if old != path]
        self.backend.setValue("file/recent_paths", paths[:5])
        self.backend.setValue("file/recent_path", path)
        self.backend.sync()
