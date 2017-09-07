#!/usr/bin/env python3
# encoding: utf-8
# This file is part of odometer by Håvard Gulldahl <havard.gulldahl@nrk.no>
# (C) 2016-2017

# 1. make sure embedded project settings are sane
# 2. generate code: translations, gui, resources

import sys
import site
import os.path
import subprocess
from clint.textui import puts, colored
from datetime import date
import sysconfig

def run(cmd, *args):
    try:
        return subprocess.check_output([cmd,] + list(args))
    except (subprocess.CalledProcessError, OSError) as e:
        if hasattr(e, 'output'):
            _error = e.output
        else:
            _error = e.strerror
        if hasattr(e, 'returncode'):
            _errno = e.returncode
        else:
            _errno = e.errno
        puts(colored.red("Tried to run `{command}`, but got {error} ({errno})".format(command=cmd,
                                                                                      error=_error,
                                                                                      errno=_errno)))

if __name__ == '__main__':
    site_packages_dir = sysconfig.get_path('purelib')
    scripts_dir =  sysconfig.get_path('scripts')

    _sp = os.path.join(site_packages_dir, "PyQt5")

    version = date.today().isoformat()
    puts(colored.blue("Building PyQt5 resources for Odometer version {v}".format(v=version)))

    puts(colored.blue("Checking project settings"))

    if sys.platform == 'darwin':
        # osx
        _pylupdate = run('which', 'pylupdate5').strip()
        _lrelease = run('which', 'lrelease').strip()
        _pyuic = run('which', 'pyuic5').strip()
        _pyrcc = run('which', 'pyrcc5').strip()
        _versionfile = os.path.join('.', 'VERSIONMAC')
    elif sys.platform == 'win32':
        _pylupdate = os.path.join(scripts_dir, 'pylupdate5.exe')
        # look at https://www.appveyor.com/docs/build-environment/#qt
        _lrelease = os.path.join('C:\Qt\5.9.1\msvc2015', 'lrelease.exe')
        _pyuic = os.path.join(scripts_dir, 'pyuic5.exe')
        _pyrcc = os.path.join(scripts_dir, 'pyrcc5.exe')
        _versionfile = os.path.join('.', 'VERSIONWIN')

    puts(colored.blue("Generating translations for UX"))
    run(_pylupdate, 'src/gui/gui.pro') # translate
    run(_lrelease, 'src/gui/gui.pro')  # compile

    puts(colored.blue("Generating UI"))
    run(_pyuic, '--from-imports', '-o', 'src/gui/odometer_ui.py', 'src/gui/pling-plong-odometer.ui')  # compile
    run(_pyuic, '--from-imports', '-o', 'src/gui/auxreport_ui.py', 'src/gui/pling-plong-auxreport.ui')  # compile
    run(_pyuic, '--from-imports', '-o', 'src/gui/prfreport_ui.py', 'src/gui/pling-plong-prfreport.ui')  # compile
    run(_pyuic, '--from-imports', '-o', 'src/gui/onlinelogin_ui.py', 'src/gui/pling-plong-onlinelogin.ui')  # compile

    puts(colored.blue("Compiling resource file"))
    run(_pyrcc, '-o', 'src/gui/odometer_rc.py', 'src/gui/odometer.qrc')


    puts(colored.green('All PyQt5 resources built'))
