"""OneLine application entry point."""

from __future__ import annotations

import logging
import os
import sys

from PyQt5.QtCore import QCoreApplication, Qt
from PyQt5.QtWidgets import QApplication

from window import OneLineWindow


def create_application(argv: list[str] | None = None) -> QApplication:
    """Create (or return) the Qt application used by OneLine."""
    QCoreApplication.setOrganizationName("OneLine")
    QCoreApplication.setApplicationName("OneLine")
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
    return QApplication.instance() or QApplication(argv or sys.argv)


def main() -> int:
    if os.environ.get("ONELINE_DEBUG_SCROLL") == "1":
        scroll_logger = logging.getLogger("editor")
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter("%(levelname)s %(name)s: %(message)s"))
        scroll_logger.addHandler(handler)
        scroll_logger.setLevel(logging.DEBUG)
        scroll_logger.propagate = False
    app = create_application()
    window = OneLineWindow()
    window.show()
    window.activateWindow()
    window.editor.setFocus()
    return app.exec_()


if __name__ == "__main__":
    raise SystemExit(main())

