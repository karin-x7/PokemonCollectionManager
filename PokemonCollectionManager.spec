# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller build spec for the Windows .exe.

Onefile, windowed (no console). Bundles the read-only resources the app
reads relative to its own __file__ at runtime (icon, checkbox glyph,
the pre-generated Pokémon name-translation table) -- these resolve
correctly inside PyInstaller's extraction directory (sys._MEIPASS) as-is.
Writable data (database, photos, logs, backups) is handled separately: see
app/config.py's frozen-aware BASE_DIR, which points next to the built .exe
instead, so it persists across runs instead of living in the temporary
extraction directory.

Build with:
    pyinstaller PokemonCollectionManager.spec
"""

from PyInstaller.utils.hooks import collect_data_files

datas = [
    ("app/resources", "app/resources"),
    ("app/catalog/pokemon_name_translations.json", "app/catalog"),
]
datas += collect_data_files("app")

a = Analysis(
    ["app/main.py"],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=[
        "PySide6.QtCharts",
        "win32gui",
        "win32ui",
        "win32com",
        "win32com.client",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="PokemonCollectionManager",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon="app/resources/icon.ico",
)
