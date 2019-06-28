# -*- mode: python -*-

block_cipher = None


a = Analysis(['linien/client/client.py'],
             pathex=['/home/ben/Schreibtisch/linien'],
             binaries=[],
             datas=[
                 ('linien/VERSION', 'linien'),
                 ('linien/client/ui/*', 'linien/client/ui')
             ],
             hiddenimports=['linien', 'linien.common'],
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
          name='client',
          debug=False,
          bootloader_ignore_signals=False,
          strip=False,
          upx=True,
          runtime_tmpdir=None,
          console=False )
