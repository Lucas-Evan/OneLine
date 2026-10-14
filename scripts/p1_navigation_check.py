#!/usr/bin/env python3
"""Cocoa-only, synthetic-data A/B check of the production OneLine window.

This is a diagnostic entry, not an alternate editor. It never logs document
text and uses private temporary settings, session and TXT files.
"""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path

from PyQt5.QtCore import QEvent, QMimeData, QObject, QSettings, QTimer, Qt
from PyQt5.QtGui import QImage, QInputMethodEvent, QTextCursor
from PyQt5.QtTest import QTest
from PyQt5.QtWidgets import QApplication

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from session import Session, SessionStore  # noqa: E402
from settings import SettingsStore  # noqa: E402
from window import OneLineWindow  # noqa: E402
from main import create_application  # noqa: E402


KEYS = {
    "Left": Qt.Key_Left,
    "Right": Qt.Key_Right,
    "Home": Qt.Key_Home,
    "End": Qt.Key_End,
}


def sample_text(name: str) -> str:
    # These strings are generated for the experiment, never read from a user file.
    if name == "A":
        return "视" * 65  # About five visual rows at the default diagnostic width.
    if name == "B":
        return "视" * 140  # About ten visual rows.
    if name == "C":
        return ("今天下午完成项目测试并整理文档，然后交给同事审核。" * 8).rstrip()
    if name == "D":
        return ("Review the release notes and verify the floating editor behavior. " * 6).rstrip()
    if name == "E":
        return "x" * 1000  # Extra stress case for the previously reported scroll delta.
    raise ValueError(name)


def rect_tuple(rect) -> list[int]:
    return [rect.x(), rect.y(), rect.width(), rect.height()]


class NavigationTrace(QObject):
    """Observe one real editor; variant B suppresses only its navigation ensure call."""

    def __init__(self, window: OneLineWindow, variant: str, capture: bool) -> None:
        super().__init__(window)
        self.window = window
        self.editor = window.editor
        self.overlay = window.visual_line_overlay
        self.variant = variant
        self.capture = capture
        self.ensure_calls = 0
        self.original_ensure = self.editor.ensureCursorVisible
        self.before: dict | None = None
        self.after: dict | None = None
        self.before_image = None
        self.after_image = None
        self.first_keys: set[str] = set()

        def observed_ensure() -> None:
            self.ensure_calls += 1
            if self.variant == "A":
                self.original_ensure()

        # Instance-local and diagnostic-only. Production editor.py is unchanged.
        self.editor.ensureCursorVisible = observed_ensure
        self.editor.installEventFilter(self)

    def eventFilter(self, watched, event):  # noqa: N802 - Qt API
        if watched is self.editor and event.type() == QEvent.KeyPress:
            key = next((label for label, code in KEYS.items() if event.key() == code), None)
            if key and key not in self.first_keys:
                self.first_keys.add(key)
                self.before = self.state()
                if self.capture:
                    self.before_image = self.window.grab().toImage()
                QTimer.singleShot(0, lambda label=key: self.finish_key(label))
        return False

    def finish_key(self, key: str) -> None:
        self.after = self.state()
        if self.capture:
            self.after_image = self.window.grab().toImage()
        self.emit(key)

    def state(self) -> dict:
        editor = self.editor
        caret = editor.cursorRect()
        viewport = editor.viewport().rect()
        bar = editor.verticalScrollBar()
        overlay = self.overlay
        return {
            "cursor_position": editor.textCursor().position(),
            "cursor_rect": rect_tuple(caret),
            "viewport_rect": rect_tuple(viewport),
            "scrollbar": [bar.value(), bar.minimum(), bar.maximum()],
            "overlay": {
                "visible": overlay.isVisible(),
                "top_mask_height": overlay._top_mask_height,
                "bottom_mask_y": overlay._bottom_mask_y,
            },
            "caret_intersects_viewport": caret.intersects(viewport),
            "ensure_calls": self.ensure_calls,
        }

    def emit(self, key: str) -> None:
        if self.before is None or self.after is None:
            return
        print(json.dumps({
            "event": "first_navigation",
            "variant": self.variant,
            "key": key,
            "before": self.before,
            "after": self.after,
        }, ensure_ascii=False), flush=True)

    def close(self) -> None:
        self.editor.removeEventFilter(self)
        self.editor.ensureCursorVisible = self.original_ensure


def create_window(work: Path, source: str, sample: str, variant: str,
                  width: int, cursor_at: str, settle_ms: int,
                  capture: bool) -> tuple[OneLineWindow, NavigationTrace, int]:
    work.mkdir(parents=True, exist_ok=True)
    settings = SettingsStore(QSettings(str(work / "settings.ini"), QSettings.IniFormat))
    settings.backend.setValue("window/width", width)
    settings.backend.setValue("window/always_on_top", False)
    settings.backend.sync()
    sessions = SessionStore(work / "session.json")
    text = sample_text(sample)
    target_position = len(text) // 2 if cursor_at == "middle" else len(text)
    if source == "session":
        sessions.save(Session(text, target_position, None, True, window_width=width))
    window = OneLineWindow(settings=settings, sessions=sessions)
    window.show()
    window.editor.setFocus()
    QApplication.processEvents()
    if source == "paste":
        mime = QMimeData()
        mime.setText(text)
        window.editor.insertFromMimeData(mime)
    elif source == "plain":
        window.editor.setPlainText(text)
    elif source == "open":
        path = work / "synthetic.txt"
        path.write_text(text, encoding="utf-8")
        if not window.open_file(str(path)):
            raise RuntimeError("Synthetic TXT could not be opened")
    elif source not in ("session", "blank"):
        raise ValueError(source)
    if source not in ("session", "blank"):
        cursor = window.editor.textCursor()
        if cursor_at == "middle":
            cursor.setPosition(target_position)
        else:
            cursor.movePosition(QTextCursor.End)
        window.editor.setTextCursor(cursor)
    if settle_ms:
        # Compare immediate first navigation with a settled real-window state.
        QApplication.processEvents()
        QTest.qWait(settle_ms)
    rows = window.editor.document().firstBlock().layout().lineCount()
    trace = NavigationTrace(window, variant, capture)
    print(json.dumps({"event": "prepared", "variant": variant, "source": source,
                      "sample": sample, "visual_rows": rows, "width": width,
                      "cursor_at": cursor_at, "settle_ms": settle_ms,
                      "state": trace.state()}, ensure_ascii=False), flush=True)
    return window, trace, rows


def pixel_difference(first, second) -> float | None:
    if first is None or second is None or first.size() != second.size():
        return None
    # Whole-window pixel delta is a proxy for a visible frame change. A moving
    # caret normally changes only a tiny fraction of pixels; this is not a
    # substitute for human evaluation of motion.
    first = first.convertToFormat(QImage.Format_ARGB32)
    second = second.convertToFormat(QImage.Format_ARGB32)
    changed = sum(first.pixel(x, y) != second.pixel(x, y)
                  for y in range(first.height()) for x in range(first.width()))
    return round(changed / (first.width() * first.height()), 5)


def cleanup(window: OneLineWindow, trace: NavigationTrace) -> None:
    trace.close()
    window._session_timer.stop()
    window.editor.document().setModified(False)
    window.tray_icon.hide()
    window.close()
    window.deleteLater()
    QApplication.processEvents()


def automated_case(work: Path, output: Path, variant: str, source: str,
                   sample: str, key: str, width: int,
                   continuous: bool = False, ime: bool = False,
                   cursor_at: str = "end", settle_ms: int = 75,
                   capture: bool = True) -> dict:
    window, trace, rows = create_window(work, source, sample, variant, width,
                                       cursor_at, settle_ms, capture)
    try:
        if ime:
            QApplication.sendEvent(window.editor, QInputMethodEvent("拼", []))
            QApplication.processEvents()
            QApplication.sendEvent(window.editor, QInputMethodEvent("", []))
            QApplication.processEvents()
        QTest.keyClick(window.editor, KEYS[key])
        QApplication.processEvents()
        if trace.after is None:
            QTest.qWait(10)
        result = {
            "variant": variant, "source": source, "sample": sample,
            "key": key, "visual_rows": rows, "cursor_at": cursor_at,
            "settle_ms": settle_ms, "before": trace.before,
            "after": trace.after,
            "pixel_difference": pixel_difference(trace.before_image, trace.after_image),
        }
        if continuous:
            for repeat_key in ([Qt.Key_Left] * 20 + [Qt.Key_Right] * 20):
                QTest.keyClick(window.editor, repeat_key)
                QApplication.processEvents()
            result["continuous_final"] = trace.state()
        stem = f"{variant}-{source}-{sample}-{key}-{cursor_at}-{settle_ms}{'-ime' if ime else ''}"
        if trace.before_image is not None:
            trace.before_image.save(str(output / f"{stem}-before.png"))
        if trace.after_image is not None:
            trace.after_image.save(str(output / f"{stem}-after.png"))
        print(json.dumps({"event": "case_result", **result}, ensure_ascii=False), flush=True)
        return result
    finally:
        cleanup(window, trace)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--variant", choices=("A", "B", "both"), default="A")
    parser.add_argument("--source", choices=("paste", "plain", "open", "session", "blank"), default="paste")
    parser.add_argument("--sample", choices=("A", "B", "C", "D", "E"), default="B")
    parser.add_argument("--width", type=int, default=360)
    parser.add_argument("--cursor-at", choices=("end", "middle"), default="end")
    parser.add_argument("--settle-ms", type=int, default=75)
    parser.add_argument("--automated", action="store_true")
    parser.add_argument("--output-dir", type=Path)
    args = parser.parse_args()
    if sys.platform != "darwin":
        parser.error("This verification entry requires a real macOS Cocoa desktop")
    app = create_application(sys.argv[:1])
    if app.platformName() != "cocoa":
        parser.error(f"Qt platform is {app.platformName()!r}, not cocoa")
    output = args.output_dir or Path(tempfile.mkdtemp(prefix="oneline-p1-navigation-"))
    output.mkdir(parents=True, exist_ok=True)
    samples_dir = output / "samples"
    samples_dir.mkdir(exist_ok=True)
    for sample_name in ("A", "B", "C", "D", "E"):
        (samples_dir / f"{sample_name}.txt").write_text(
            sample_text(sample_name), encoding="utf-8"
        )
    print(json.dumps({"event": "output", "path": str(output)}), flush=True)
    variants = ("A", "B") if args.variant == "both" else (args.variant,)
    with tempfile.TemporaryDirectory(prefix="oneline-p1-private-") as temporary:
        root = Path(temporary)
        if args.automated:
            cases = [
                ("paste", "B", "Left", True, False, "end", 75),
                ("paste", "B", "Right", False, False, "middle", 75),
                ("paste", "B", "Home", False, False, "middle", 75),
                ("paste", "B", "End", False, False, "middle", 75),
                ("paste", "A", "Left", False, False, "end", 75),
                ("plain", "B", "Left", False, False, "end", 75),
                ("open", "D", "Left", False, False, "end", 75),
                ("session", "B", "Left", False, False, "end", 75),
                ("session", "B", "Right", False, False, "middle", 75),
                ("paste", "C", "Left", False, True, "end", 75),
                ("paste", "E", "Left", False, False, "end", 75),
                ("plain", "E", "Left", False, False, "end", 75),
                ("session", "E", "Left", False, False, "end", 75),
                ("paste", "E", "Left", False, False, "end", 0),
                ("plain", "E", "Left", False, False, "end", 0),
                ("session", "E", "Left", False, False, "end", 0),
            ]
            results = []
            for variant in variants:
                for index, (source, sample, key, continuous, ime,
                            cursor_at, settle_ms) in enumerate(cases):
                    case_work = root / f"{variant}-{index}"
                    results.append(automated_case(case_work, output, variant,
                                                  source, sample, key, args.width,
                                                  continuous, ime, cursor_at,
                                                  settle_ms, settle_ms != 0))
            (output / "results.json").write_text(
                json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8"
            )
            print(json.dumps({"event": "summary", "cases": len(results),
                              "failed_visibility": sum(not result["after"]["caret_intersects_viewport"]
                                                       for result in results),
                              "output": str(output)}), flush=True)
            return 0
        if args.variant == "both":
            parser.error("Interactive mode needs one variant at a time")
        window, trace, _rows = create_window(root / "interactive", args.source,
                                             args.sample, args.variant, args.width,
                                             args.cursor_at, args.settle_ms, True)
        print("真实窗口已打开。请按 Left/Right/Home/End；首次按键的前后状态会输出为 JSON。"
              "关闭时若提示未保存，可选‘不保存’。", flush=True)
        try:
            return app.exec_()
        finally:
            trace.close()
            window.tray_icon.hide()


if __name__ == "__main__":
    raise SystemExit(main())
