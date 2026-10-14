"""Measure local session snapshot costs with synthetic text only."""

from __future__ import annotations

import os
import sys
from pathlib import Path
from statistics import median
from tempfile import TemporaryDirectory
from time import perf_counter

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from PyQt5.QtCore import QSettings  # noqa: E402
from PyQt5.QtWidgets import QApplication  # noqa: E402

from session import Session, SessionStore  # noqa: E402
from settings import SettingsStore  # noqa: E402
from window import OneLineWindow  # noqa: E402


def elapsed_ms(action) -> float:
    started = perf_counter()
    action()
    return (perf_counter() - started) * 1000


def main() -> None:
    app = QApplication.instance() or QApplication(sys.argv[:1])
    with TemporaryDirectory(prefix="oneline-session-benchmark-") as temporary:
        base = Path(temporary)
        store = SessionStore(base / "session.json")
        settings = SettingsStore(QSettings(str(base / "settings.ini"), QSettings.IniFormat))
        window = OneLineWindow(settings=settings, sessions=store)
        print("bytes,toPlainText_median_ms,serialize_write_median_ms,full_snapshot_median_ms")
        for size in (10 * 1024, 100 * 1024, 500 * 1024, 1024 * 1024):
            line = "x" * 99 + "\n"
            synthetic = line * (size // 100) + "x" * (size % 100)
            window.editor.setPlainText(synthetic)
            app.processEvents()
            plain = []
            serialized = []
            full = []
            for _ in range(3):
                plain.append(elapsed_ms(window.editor.toPlainText))
                serialized.append(
                    elapsed_ms(lambda: store.save(Session(synthetic, 0, None, True)))
                )
                full.append(elapsed_ms(window._write_session))
            print(
                f"{size},{median(plain):.2f},{median(serialized):.2f},{median(full):.2f}",
                flush=True,
            )
        window.editor.document().setModified(False)
        window.tray_icon.hide()
        window.close()


if __name__ == "__main__":
    main()
