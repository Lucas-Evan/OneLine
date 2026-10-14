[简体中文](README.md) · [English](README.en.md)

# OneLine

OneLine is a floating plain-text editor that occupies a single-line strip of your desktop while keeping a complete, multi-line document underneath. The Mac development build has passed its release gate. A Linux x86-64 onedir package has been built in CI, but it has **not** yet been validated on an actual Kylin V10 desktop.

## Run on macOS

From the project directory, run these commands the first time:

```bash
./scripts/bootstrap-macos.sh
./scripts/run-macos.sh
```

After setup, use `./scripts/run-macos.sh`. Dependencies live in the project's `.venv`. You can quit from the `⋯` menu; when the window is hidden, use the OneLine menu-bar icon to restore or quit it.

The Linux x86-64 onedir candidate and its SHA256 file are available as a [GitHub Actions artifact](https://github.com/Lucas-Evan/OneLine/actions/runs/38520061426/artifacts/11873098074). Its CI offscreen checks do not establish Kylin GUI compatibility. See the [Linux packaging report](docs/LINUX_PACKAGING_PHASE1_REPORT.md) and [Kylin acceptance checklist](docs/KYLIN_ACCEPTANCE_CHECKLIST.md) before testing it on a target machine.

## How it works

- The window defaults to 800 × 56 pixels. Drag it using the `⋮⋮` handle on the left; resize its width from the narrow area on the far right.
- Enter creates a real newline. ↑/↓ move between logical lines, and Home/End move to the start/end of the logical line. `QPlainTextEdit` visually wraps long lines to the window width. A mouse-transparent overlay masks text outside the cursor's current visual row without changing the document, cursor, or Qt's native scrolling. The outer window remains 56 pixels tall.
- Visual wrapping never adds newlines to saved or copied text. Real newlines and the `QTextDocument` block structure remain intact.
- Typing, Backspace, and Delete use Qt's native behavior; there is no custom delete transaction.
- The right side shows the current/total line count, save state (`✓` saved, `●` unsaved, `⟳` restoring, `!` automatic recovery temporarily unavailable), and menu button. A session-write failure does not interrupt editing; the status clears after a successful later write.
- The quick menu includes New, Open, Save, Save As, Find, the five most recent files, Always on Top, Settings, and Quit.
- Settings cover the editor font and size, window opacity, dark mode, restore-on-start, start-on-top, and the configurable hide shortcut.
- Find opens a separate small window, leaving the main window's height unchanged. Previous/Next searches wrap through the full document.

| Action | macOS | Linux |
| --- | --- | --- |
| New / Open / Save / Save As | ⌘N / ⌘O / ⌘S / ⇧⌘S | Ctrl+N / Ctrl+O / Ctrl+S / Ctrl+Shift+S |
| Find | ⌘F | Ctrl+F |
| Undo / Redo | ⌘Z / ⌘⇧Z | Ctrl+Z / Ctrl+Y |
| Always on Top | ⇧⌘T | Ctrl+Shift+T |
| Quit | ⌘Q | Ctrl+Q |
| Hide the current window | Esc | Esc |
| Hide (configurable) | ⇧⌘Space | Ctrl+Shift+Space |

Qt displays the platform-appropriate shortcut at the right edge of each menu action. Esc closes an open menu first; in the editor, it hides the window. Restore a hidden window from the OneLine menu-bar/system-tray icon. The configurable hide shortcut is a **window shortcut**, not a system-wide hotkey: once another application has focus, use the icon to restore OneLine. If the system has no tray, hiding minimizes OneLine so it remains available from the taskbar or Dock.

## Files, recent files, and recovery

OneLine opens and saves UTF-8 TXT files, including UTF-8 BOM. It preserves the file's predominant newline style and saves atomically with Qt's `QSaveFile`. A failed save is reported and leaves the document marked unsaved. If another program changes the open file, OneLine stops the save and prompts for Save As rather than silently overwriting the disk version. Closing, creating a new file, or opening another file with unsaved changes prompts Save / Discard / Cancel.

The recent-files list stores at most five absolute paths in per-user Qt settings; it does not log document text. A separate local `session.json` stores the document text, cursor position, current line, open-file path, window position, width, and always-on-top state. After an unexpected exit, unsaved text returns to the editor still marked unsaved. The recovered draft is detached from its former file path, so it must be saved with Save As and cannot silently overwrite the TXT file. Disabling restore-on-start clears the local session snapshot. Window settings also retain the theme, editor font and size, opacity, and shortcut.

Session snapshots are debounced after text changes; moving the cursor alone does not rewrite an entire long document. Hiding or closing normally still records the latest cursor position.

## Tests

```bash
./scripts/test.sh
```

By default, `./scripts/test.sh` runs the current architecture's `release` tests with Qt offscreen. They cover fixed height, visual-row masking, themes, long-text input and deletion, simulated Chinese input-method events, logical-line navigation, save/copy after wrapping, file round trips, unsaved-change prompts, restart recovery, window state, find, menus, recent files, settings, and shortcuts. Offscreen and graphical backends produce different programmatic cursor-scroll geometry, so the long-line recovery visibility case is skipped offscreen and must pass separately under macOS Cocoa.

Legacy and diagnostic tests remain available through `./scripts/test-all-diagnostics.sh`; they can expose obsolete private APIs or historical performance issues. Use `./scripts/benchmark.sh` for the visual-wrap A/B benchmark and `./scripts/benchmark.sh session` for session-save timing. Neither benchmark is part of the default release gate. Test markers are defined in `tests/conftest.py`.

Manual macOS checks are still needed for Chinese IME preedit/candidate windows, real dragging and resizing, the menu-bar icon, hide/restore, display scaling, fonts, and opacity. Linux preparation notes are in [docs/platform-notes.md](docs/platform-notes.md).

Before formal distribution, verify the applicable PyQt5 licensing arrangement (a GPL-compatible distribution or a suitable commercial license). This is not a legal conclusion, and the project is not migrating to PySide in this phase. Release packages should exclude `.venv`, `__pycache__`, `.pytest_cache`, benchmarks, legacy rollback/diagnostic tests, and experiment files.
