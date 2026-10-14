"""Production OneLine entry plus an opt-in, data-free frozen-binary smoke path."""

from __future__ import annotations

import sys
from pathlib import Path
from tempfile import TemporaryDirectory

# Keep direct source-tree smoke runnable; PyInstaller resolves these imports
# from the spec's pathex and does not use this branch once frozen.
if not getattr(sys, "frozen", False):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from PyQt5.QtCore import QSettings

from main import create_application, main
from session import SessionStore
from settings import SettingsStore
from window import OneLineWindow


def packaging_smoke() -> int:
    app = create_application(sys.argv[:1])
    with TemporaryDirectory(prefix="oneline-smoke-") as temporary:
        root = Path(temporary)
        settings = SettingsStore(QSettings(str(root / "settings.ini"), QSettings.IniFormat))
        sessions = SessionStore(root / "session.json")
        window = OneLineWindow(settings=settings, sessions=sessions)
        try:
            window.show()
            app.processEvents()
            if window.height() != 56 or not window.editor or not window.visual_line_overlay:
                raise RuntimeError("Window/editor/overlay construction failed")
            window.editor.insertPlainText("OneLine packaging smoke")
            app.processEvents()
            if window.editor.toPlainText() != "OneLine packaging smoke":
                raise RuntimeError("Text insertion failed")
            if not window.visual_line_overlay.isVisible():
                raise RuntimeError("Visual line overlay is not visible")
            print("ONELINE_SMOKE_OK", flush=True)
            return 0
        finally:
            window._session_timer.stop()
            window.editor.document().setModified(False)
            window.tray_icon.hide()
            window.close()


if __name__ == "__main__":
    raise SystemExit(packaging_smoke() if "--packaging-smoke" in sys.argv[1:] else main())
