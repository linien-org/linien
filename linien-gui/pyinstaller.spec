# -*- mode: python -*-
# this spec file is for compiling a standalone version of linien using pyinstaller.
# use `scripts/build_standalone_client.sh` for this purpose

block_cipher = None

import platform

datas= [
    ('linien_gui/ui/*', 'linien_gui/ui'),
    ('linien_gui/icon.ico', 'linien_gui')
]

pathex = []

if platform.system().lower() != 'linux':
    import os

    # IMPORTANT: For some reason the app doesn't work if pyqt is not installed globally
    # using powershell run with admin privileges.
    """qt_site_packages = 'C:\\Program Files\\Python38\\lib\\site-packages'
    qt_bin_folder = qt_site_packages + '\\PyQt5\\Qt\\bin'
    if not os.path.exists(qt_bin_folder):
        print('')
        print('============================================')
        print('pyinstaller.spec was customized due to a pyinstaller bug that lead to Qt5Core.dll not being bundled.')
        print('see also https://github.com/pyinstaller/pyinstaller/issues/2152')
        print('therefore, qt_bin_folder is set to')
        print(qt_bin_folder)
        print('However, on your machine this folder does not exist. You probably have to modify the spec file.')
        input('Proceed anyway? [press enter]')

    datas += [(qt_bin_folder + '\\Qt5Core.dll', 'PyQt5\\Qt\\bin')]
    pathex.append(qt_site_packages)"""


a = Analysis(['linien/gui/app.py'],
             pathex=pathex,
             binaries=[],
             datas=datas,
             hiddenimports=['linien_common', 'PyQt5.sip', 'superqt'],
             hookspath=[],
             runtime_hooks=[],
             excludes=[],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher,
             noarchive=False)
pyz = PYZ(a.pure, a.zipped_data,
             cipher=block_cipher)
exe = EXE(pyz,
          a.scripts,
          a.binaries,
          a.zipfiles,
          a.datas,
          [],
          name='linien-gui',
          debug=False,
          bootloader_ignore_signals=False,
          strip=False,
          upx=True,
          runtime_tmpdir=None,
          console=False,
          icon="linien_gui/icon.ico")
