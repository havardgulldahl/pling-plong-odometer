#-*- encoding: utf-8 -*-
# This file is part of odometer by Håvard Gulldahl <havard.gulldahl@nrk.no>
# (C) 2011
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

import sys
from setuptools import setup

def getversion():
    try:
        _ver = open('VERSION').readline().split(':')[0]
        return _ver
    except:
        raise

mainscript = 'src/pling-plong-odometer.py'

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
             plist=dict(CFBundleIdentifier='no.nrk.odometer',
                        ##CFBundleDisplayName='♫ ♪ Odometer',
                        #CFBundleDisplayName=u'\u266b \u266a Odometer',
                        CFBundleShortVersionString='Odometer, version x.x',
                        NSSupportsSuddenTermination=True,
                        NSHumanReadableCopyright='havard.gulldahl@nrk.no 2011-2012')
             )
         ),
     )
elif sys.platform == 'win32':
     extra_options = dict(
         setup_requires=['py2exe'],
         app=[mainscript],
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

