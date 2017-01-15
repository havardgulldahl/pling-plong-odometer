# -*- mode: python -*-

block_cipher = None


a = Analysis(['src\\pling-plong-odometer.py'],
             pathex=['c:\\python\\lib\\site-packages\\pyqt5\\qt\\bin', 'c:\\dev\\pling-plong-odometer\\src\\gui', 'C:\\dev\\pling-plong-odometer'],
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
