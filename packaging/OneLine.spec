# -*- mode: python ; coding: utf-8 -*-
"""Linux x86-64 onedir only; Qt editing remains in the production modules."""

from pathlib import Path

from PyQt5.QtCore import QLibraryInfo


project_root = Path(SPECPATH).resolve().parent.parent
plugin_dir = Path(QLibraryInfo.location(QLibraryInfo.PluginsPath)) / "platforms"
platform_plugins = []
for plugin_name in ("libqxcb.so", "libqoffscreen.so"):
    plugin = plugin_dir / plugin_name
    if not plugin.is_file():
        raise FileNotFoundError(f"Required Qt platform plugin is missing: {plugin_name}")
    platform_plugins.append((str(plugin), "PyQt5/Qt5/plugins/platforms"))

a = Analysis(
    [str(project_root / "packaging" / "linux" / "frozen_entry.py")],
    pathex=[str(project_root)],
    binaries=platform_plugins,
    datas=[],  # No application assets or icons are required in Phase 1.
    hiddenimports=["PyQt5.QtCore", "PyQt5.QtGui", "PyQt5.QtWidgets"],
    hookspath=[],
    runtime_hooks=[],
    excludes=["pytest", "_pytest", "tests", "tkinter", "unittest"],
    noarchive=False,
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="OneLine",
    debug=False,
    strip=False,
    upx=False,
    console=False,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name="OneLine",
)
