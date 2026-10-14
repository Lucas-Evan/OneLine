"""Crash recovery snapshot, separate from the user's TXT file."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from PyQt5.QtCore import QIODevice, QSaveFile, QStandardPaths


@dataclass(frozen=True)
class Session:
    text: str
    cursor: int
    path: str | None
    modified: bool
    newline: str = "\n"
    bom: bool = False
    line: int = 1
    window_x: int | None = None
    window_y: int | None = None
    window_width: int | None = None
    on_top: bool | None = None


class SessionStore:
    def __init__(self, path: str | Path | None = None) -> None:
        if path is None:
            base = QStandardPaths.writableLocation(QStandardPaths.AppConfigLocation)
            path = Path(base) / "session.json"
        self.path = Path(path)

    def load(self) -> Session | None:
        if not self.path.exists():
            return None
        try:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
            if not isinstance(payload, dict):
                return None
            if payload.get("version") != 1:
                return None
            text = payload["text"]
            cursor = payload["cursor"]
            path = payload["path"]
            modified = payload["modified"]
            newline = payload.get("newline", "\n")
            bom = payload.get("bom", False)
            line = payload.get("line", 1)
            window = payload.get("window", {})
            if (
                not isinstance(text, str)
                or type(cursor) is not int
                or not (path is None or isinstance(path, str))
                or type(modified) is not bool
                or newline not in ("\n", "\r\n", "\r")
                or type(bom) is not bool
                or type(line) is not int
                or not isinstance(window, dict)
            ):
                return None
            x = window.get("x")
            y = window.get("y")
            width = window.get("width")
            on_top = window.get("on_top")
            if any(value is not None and type(value) is not int for value in (x, y, width)):
                return None
            if on_top is not None and type(on_top) is not bool:
                return None
            return Session(
                text, max(0, cursor), path, modified, newline, bom,
                max(1, line), x, y, width, on_top,
            )
        except (OSError, ValueError, KeyError, TypeError):
            return None

    def save(self, session: Session) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "version": 1,
            "text": session.text,
            "cursor": session.cursor,
            "path": session.path,
            "modified": session.modified,
            "newline": session.newline,
            "bom": session.bom,
            "line": session.line,
            "window": {
                "x": session.window_x,
                "y": session.window_y,
                "width": session.window_width,
                "on_top": session.on_top,
            },
        }
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        target = QSaveFile(str(self.path))
        if not target.open(QIODevice.WriteOnly):
            raise OSError(target.errorString())
        try:
            if target.write(data) != len(data):
                raise OSError(target.errorString() or "恢复文件写入不完整")
            if not target.commit():
                raise OSError(target.errorString())
        except Exception:
            target.cancelWriting()
            raise

    def clear(self) -> None:
        self.path.unlink(missing_ok=True)
