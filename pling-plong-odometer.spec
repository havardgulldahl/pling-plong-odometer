# -*- mode: python -*-

block_cipher = None

import sys

added_files = [
               ('C:\\Python35\\Lib\\site-packages\\PyQt5\\Qt\\bin\\Qt5Core.dll', '.'),
               ('C:\\Python35\\Lib\\site-packages\\PyQt5\\Qt\\bin\\Qt5Gui.dll', '.'),
               ('C:\\Python35\\Lib\\site-packages\\PyQt5\\Qt\\bin\\Qt5Widgets.dll', '.')
              ]

a = Analysis(['src/pling-plong-odometer.py'],
             pathex=['c:\\python35\\lib\\site-packages\\pyqt5\\qt\\bin', './src/gui', './'],
             binaries=None,
             datas=None,
             hiddenimports=[],
             hookspath=[],
             runtime_hooks=[],
             excludes=[],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher)
pyz = PYZ(a.pure, a.zipped_data,
             cipher=block_cipher)
exe = EXE(pyz,
          a.scripts,
          exclude_binaries=True,
          name='pling-plong-odometer',
          debug=False,
          strip=False,
          upx=True,
          console=False , icon='odometer.ico')
coll = COLLECT(exe,
               a.binaries,
               a.zipfiles,
               a.datas,
               strip=False,
               upx=True,
               name='pling-plong-odometer')
