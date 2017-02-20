# -*- mode: python -*-

block_cipher = None

import sys
import os.path
import ntpath
import PyQt5

added_files = [
               ('C:\\Python35\\Lib\\site-packages\\PyQt5\\Qt\\bin\\Qt5Core.dll', '.'),
               ('C:\\Python35\\Lib\\site-packages\\PyQt5\\Qt\\bin\\Qt5Gui.dll', '.'),
               ('C:\\Python35\\Lib\\site-packages\\PyQt5\\Qt\\bin\\Qt5Widgets.dll', '.'),
               ('C:\\Python35\\Lib\\site-packages\\PyQt5\\Qt\\bin\\QtWebEngineProcess.exe', '.')
              ]

a = Analysis(['src/pling-plong-odometer.py'],
             pathex=[os.path.join(ntpath.dirname(PyQt5.__file__), 'Qt', 'bin'), './src/gui', './'],
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
          debug=True,
          strip=False,
          upx=True,
          console=True, icon='odometer.ico')
app = BUNDLE(exe,
             name='Pling plong odometer.app',
             icon='odometer.icns',
             bundle_identifier='no.nrk.odometer',
             info_plist={
                 # create osx Info.plist 
                 # https://developer.apple.com/library/content/documentation/CoreFoundation/Conceptual/CFBundles/BundleTypes/BundleTypes.html
                'NSHighResolutionCapable': 'True',
                'CFBundleDisplayName': '♫ ♪ Odometer',
                'NSHumanReadableCopyright': 'Copyright 2011-2017 havard.gulldahl@nrk.no',
             },
             )
coll = COLLECT(exe,
               a.binaries,
               a.zipfiles,
               a.datas,
               strip=False,
               upx=True,
               name='pling-plong-odometer')