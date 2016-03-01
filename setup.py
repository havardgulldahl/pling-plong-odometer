#-*- encoding: utf-8 -*-
# This file is part of odometer by Håvard Gulldahl <havard.gulldahl@nrk.no>
# (C) 2011-2012
"""
py2app/py2exe build script for odometer.

Will automatically ensure that all build prerequisites are available
via ez_setup

Usage (Mac OS X):
    python setup.py py2app

Usage (Windows):
    python setup.py py2exe
"""
#import ez_setup
#ez_setup.use_setuptools()

import sys, os.path
from setuptools import setup

if sys.platform == 'win32':
    import py2exe

def getversion():
    if sys.platform == 'darwin':
        _p = 'MAC'
    elif sys.platform == 'win32':
        _p = 'WIN'
    else:
        _p = 'x'
    try:
        _ver = open('VERSION%s' % _p).readline().strip()
        return _ver.replace('-', '.')
    except:
        raise

mainscript = os.path.join('src', 'pling-plong-odometer.py')

if sys.platform == 'darwin':
     extra_options = dict(
         setup_requires=['py2app'],
         app=[mainscript],
         # Cross-platform applications generally expect sys.argv to
         # be used for opening files.
         options=dict(py2app=dict(
             argv_emulation=False,
             iconfile='odometer.icns',
             packages=['lxml'],
             includes=['sip','PyQt4', 'PyQt4.QtNetwork','gzip'],
	     excludes=["Tkconstants","Tkinter","tcl"],
             plist=dict(CFBundleIdentifier='no.nrk.odometer',
                        ##CFBundleDisplayName='♫ ♪ Odometer',
                        #CFBundleDisplayName=u'\u266b \u266a Odometer',
                        CFBundleShortVersionString='Odometer, version %s' % getversion(),
                        NSSupportsSuddenTermination=True,
                        NSHumanReadableCopyright='havard.gulldahl@nrk.no 2011-2014')
             )
         ),
     )
elif sys.platform == 'win32':
     extra_options = dict(
         setup_requires=['py2exe'],
         windows=[mainscript],
		 packages=['gui','metadata','xmeml'],
		 package_dir={'metadata':'src/metadata',
		              'gui':'src/gui',
		              'xmeml':'src/xmeml'
					  },
		 options=dict(py2exe=dict(
             packages=['lxml'],
	     excludes=["Tkconstants","Tkinter","tcl"],
             includes=['sip','PyQt4', 'PyQt4.QtNetwork','gzip'])
		)
    )
else:
     extra_options = dict(
         # Normally unix-like platforms will use "setup.py install"
         # and install the main script as such
         scripts=[mainscript],
     )

setup(
    name="Pling Plong Odometer",
    version=getversion(),
    author=u'Håvard Gulldahl',
    author_email='havard.gulldahl@nrk.no',
    description='Pling Plong Odometer is a tool to automatically calculate audio usage in an fcp project',
    **extra_options
)
