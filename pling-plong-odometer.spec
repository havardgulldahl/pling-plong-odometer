# -*- mode: python -*-

import sys
import os, os.path
import PyQt5
import distutils.util


block_cipher = None

pyqtpath=os.path.join(os.path.dirname(PyQt5.__file__), 'Qt')
pyqtbinpath=os.path.join(pyqtpath, 'bin')
pyqtlibpath=os.path.join(pyqtpath, 'lib')
thispath=os.getcwd()

_platform = distutils.util.get_platform()
if 'win' in _platform:
    platform = 'win'
elif _platform == 'linux-x86_64':
    platform = 'nix64'
elif "macosx" and "x86_64" in _platform:
    platform = 'mac'
else:
    platform = 'unknown'

added_files = [
               (os.path.join(pyqtbinpath, 'Qt5Core.dll'), '.'),
               (os.path.join(pyqtbinpath, 'Qt5Gui.dll'), '.'),
               (os.path.join(pyqtbinpath, 'Qt5Widgets.dll'), '.'),
               (os.path.join(pyqtbinpath, 'QtWebEngineProcess.exe'), '.'),
               (os.path.join(pyqtlibpath, 'bin', 'QtWebEngineProcess.exe'), '.')
              ]

a = Analysis(['src/pling-plong-odometer.py'],
             pathex=[os.path.join(thispath, 'src', 'gui'), thispath, pyqtbinpath, pyqtlibpath],
             binaries=None,
             datas=None,
             hiddenimports=['gui', 'xmeml'],
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
          console=True, icon='odometer.ico')
coll = COLLECT(exe,
               a.binaries,
               a.zipfiles,
               a.datas,
               strip=False,
               upx=True,
               name='pling-plong-odometer')
             
if platform == 'mac':
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
    # NOTE, you still have to manually copy everything from
    # dist/pling-plong-odometer/ -> dist/Pling plong odometer.app/Contents/MacOS
    # pynstaller does not do this
    # https://github.com/pyinstaller/pyinstaller/issues/2460