#-*- encoding: utf-8 -*-
# This file is part of odometer by Håvard Gulldahl <havard.gulldahl@nrk.no>
# (C) 2011-2017
"""
sdist build script for odometer.

"""

import sys, os.path, re, datetime
from cx_Freeze import setup, Executable
from setuptools import setup

mainscript = os.path.join('src', 'pling-plong-odometer.py')

if sys.platform == 'win32':
    #import py2exe
    base = "Win32GUI" # for win32 guis 
else:
    base = None
# if sys.platform == 'darwin':
#      extra_options = dict(
#          setup_requires=['py2app'],
#          app=[mainscript],
#          zip_safe=False,
#          # Cross-platform applications generally expect sys.argv to
#          # be used for opening files.
#          options=dict(py2app=dict(
#              argv_emulation=False,
#              iconfile='odometer.icns',
#              packages=['lxml'],
#              includes=['sip','PyQt5','PyQt5.QtWidgets', 'PyQt5.QtCore', 'PyQt5.QtGui'],
#       	     excludes=["Tkconstants","Tkinter","tcl",
#                        "PyQt5.QtBluetooth", "PyQt5.QtMultimedia", "PyQt5.QtPrintSupport", "PyQt5.QtQml", 
#                        "PyQt5.QtQuick", "PyQt5.QtSensors", "PyQt5.QtSql", "PyQt5.QtWebSockets", ],
#              plist=dict(CFBundleIdentifier='no.nrk.odometer',
#                         ##CFBundleDisplayName='♫ ♪ Odometer',
#                         #CFBundleDisplayName=u'\u266b \u266a Odometer',
#                         CFBundleShortVersionString='Odometer, version %s' % getversion(),
#                         NSSupportsSuddenTermination=True,
#                         NSHumanReadableCopyright='havard.gulldahl@nrk.no 2011-2017')
#              )
#          ),
#      )
# elif sys.platform == 'win32':
#      extra_options = dict(
#          setup_requires=['py2exe'],
#          windows=[ 
#              {"script": mainscript,
#               "icon_resources": [(0, "odometer.ico")]     ### Icon to embed into the PE file.
#              }
#          ],
# 		 packages=['gui','metadata', 'core'],
# 		 package_dir={'metadata':'src/metadata',
# 		              'gui':'src/gui',
#                       'core': 'src/core',
# 		              #'xmeml':'src/xmeml'
# 					  },
# 		 options=dict(py2exe=dict(
#             packages=['lxml'],
#             excludes=["Tkconstants","Tkinter","tcl"],
#             includes=['sip','PyQt5','PyQt5.QtWidgets','gzip'])
# 		)
#     )
# else:
#      extra_options = dict(
#          # Normally unix-like platforms will use "setup.py install"
#          # and install the main script as such
#          scripts=[mainscript],
#      )

cx_options = dict( # cx_freeze
    options = {"build_exe": {"packages": ["gui", "metadata", "core"], 
                             "excludes": ["Tkinter"],
                             "includes": ["traceback", 'sip','PyQt5','PyQt5.QtWidgets','PyQt5.QtPrintSupport', 'gzip'],
                             "path": ['src']
                            },
               "bdist_mac": {
                             "iconfile": ['odometer.icns'],
                             "qt_menu_nib": [os.path.join('resources','qt_menu.nib')],
                             "bundle_name": '♫ ♪ Odometer',
                            }
              
    },
    executables = [Executable(mainscript, 
                              icon='odometer.ico',
                              base=base, 
                              targetName='odometer')]
    # https://cx-freeze.readthedocs.io/en/latest/distutils.html
    # iconfile	Path to an icns icon file for the application. This will be copied into the bundle.
    # qt_menu_nib	Path to the qt-menu.nib file for Qt applications. By default, it will be auto-detected.
    # bundle_name	File name for the bundle application without the .app extension.
    # custom_info_plist	File to be used as the Info.plist in the app bundle. A basic one will be generated by default.
    # include_frameworks	A list of Framework directories to include in the app bundle.
    # codesign_identity	The identity of the key to be used to sign the app bundle.
    # codesign_entitlements	The path to an entitlements file to use for your application’s code signature.
    # codesign_deep	Boolean for whether to codesign using the –deep option.
    # codesign_resource_rules	Plist file to be passed to codesign’s –resource-rules option.
)

setup(
    name="Pling Plong Odometer",
    version=datetime.datetime.now().strftime('%y.%-m.%-d'),
    author='Håvard Gulldahl',
    author_email='havard.gulldahl@nrk.no',
    description='A tool to calculate audio usage in a Adobe Premiere or Final Cut Pro project',
    **cx_options
)
