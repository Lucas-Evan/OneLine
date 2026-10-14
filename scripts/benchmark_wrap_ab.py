"""Compare deletion cost with NoWrap and WidgetWidth; never saves text."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from time import perf_counter

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QTextCursor
from PyQt5.QtTest import QTest
from PyQt5.QtWidgets import QApplication, QPlainTextEdit

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from editor import OneLineEditor  # noqa: E402


def run_case(app, mode: int, size: int, sample_keys: int, budget_seconds: float):
    editor = OneLineEditor()
    editor.setLineWrapMode(mode)
    editor.resize(300, editor.height())
    editor.show()
    editor.setFocus()
    app.processEvents()

    started = perf_counter()
    editor.insertPlainText("a" * size)
    editor.moveCursor(QTextCursor.End)
    app.processEvents()
    insert_ms = (perf_counter() - started) * 1000
    visual_rows = editor.document().firstBlock().layout().lineCount()

    delete_samples = []
    sample_started = perf_counter()
    for _ in range(min(sample_keys, size)):
        started = perf_counter()
        QTest.keyClick(editor, Qt.Key_Backspace)
        app.processEvents()
        delete_samples.append((perf_counter() - started) * 1000)
        if perf_counter() - sample_started >= budget_seconds:
            break

    started = perf_counter()
    if size > len(delete_samples):
        QTest.keyClick(editor, Qt.Key_A, Qt.ControlModifier)
        QTest.keyClick(editor, Qt.Key_Backspace)
        app.processEvents()
    clear_ms = (perf_counter() - started) * 1000
    assert editor.toPlainText() == ""
    assert editor.document().blockCount() == 1

    started = perf_counter()
    QTest.keyClicks(editor, "abc")
    app.processEvents()
    retype_ms = (perf_counter() - started) * 1000
    assert editor.toPlainText() == "abc"
    editor.close()
    return {
        "rows": visual_rows,
        "insert_ms": round(insert_ms, 1),
        "keys": len(delete_samples),
        "delete_avg_ms": round(sum(delete_samples) / len(delete_samples), 1),
        "delete_max_ms": round(max(delete_samples), 1),
        "clear_ms": round(clear_ms, 1),
        "retype_ms": round(retype_ms, 1),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--sizes", type=int, nargs="+", default=[1000, 5000, 10000, 20000, 50000, 100000]
    )
    parser.add_argument("--sample-keys", type=int, default=30)
    parser.add_argument("--budget-seconds", type=float, default=3.0)
    args = parser.parse_args()
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    app = QApplication.instance() or QApplication(sys.argv[:1])
    print("mode,size,rows,insert_ms,keys,delete_avg_ms,delete_max_ms,clear_ms,retype_ms", flush=True)
    for size in args.sizes:
        for mode, name in (
            (QPlainTextEdit.NoWrap, "NoWrap"),
            (QPlainTextEdit.WidgetWidth, "WidgetWidth"),
        ):
            result = run_case(app, mode, size, args.sample_keys, args.budget_seconds)
            print(
                f"{name},{size},{result['rows']},{result['insert_ms']},"
                f"{result['keys']},{result['delete_avg_ms']},"
                f"{result['delete_max_ms']},{result['clear_ms']},"
                f"{result['retype_ms']}",
                flush=True,
            )


if __name__ == "__main__":
    main()
