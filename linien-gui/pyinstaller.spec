# -*- mode: python -*-
# This spec file is for compiling a standalone version of linien using pyinstaller.
# Run with `pyinstaller pyinstaller.spec`

block_cipher = None

datas = [("linien_gui/ui/*", "linien_gui/ui"), ("linien_gui/icon.ico", "linien_gui")]

a = Analysis(
    ["linien_gui/app.py"],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=["PyQt5.sip", "superqt", "scipy.special._cdflib"],
    hookspath=[],
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="linien-gui",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    runtime_tmpdir=None,
    console=False,
    icon="linien_gui/icon.ico",
)
