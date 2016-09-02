#!/usr/bin/env python
# encoding: utf-8
# This file is part of odometer by Håvard Gulldahl <havard.gulldahl@nrk.no>
# (C) 2016

# 1. make sure embedded project settings are sane
# 2. generate code: translations, gui, resources

import sys
import site
import os.path
import subprocess
from clint.textui import puts, colored
from datetime import date

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
    _sp = None
    for _p in sys.path:
        if not _p.endswith('site-packages'):
            continue
        if os.path.exists(os.path.join(_p, "PyQt4")):
            _sp = os.path.join(_p, "PyQt4")

    if not os.path.exists(_sp):
        puts(colored.red("Couldnt find PyQt4 installation (looked at {path}".format(path=_sp)))
        sys.exit(1)

    version = date.today().isoformat()
    puts(colored.blue("Building PyQt4 resources for Odometer version {v}".format(v=version)))

    puts(colored.blue("Checking project settings"))

    if sys.platform == 'darwin':
        # osx
        _pylupdate = run('which', 'pylupdate4').strip()
        _lrelease = run('which', 'lrelease').strip()
        _pyuic = run('which', 'pyuic4').strip()
        _pyrcc = run('which', 'pyrcc4').strip()
        _versionfile = os.path.join('.', 'VERSIONMAC')
    elif sys.platform == 'win32':
        _pylupdate = os.path.join(_sp, 'pylupdate4.exe')
        _lrelease = os.path.join(_sp, 'lrelease.exe')
        _pyuic = os.path.join(_sp, 'pyuic4.bat')
        _pyrcc = os.path.join(_sp, 'pyrcc4.exe')
        _versionfile = os.path.join('.', 'VERSIONWIN')

    puts(colored.blue("Generating translations for UX"))
    run(_pylupdate, 'src/gui/gui.pro') # translate
    run(_lrelease, 'src/gui/gui.pro')  # compile

    puts(colored.blue("Generating UI"))
    run(_pyuic, '-o', 'src/gui/odometer_ui.py', 'src/gui/pling-plong-odometer.ui')  # compile
    run(_pyuic, '-o', 'src/gui/auxreport_ui.py', 'src/gui/pling-plong-auxreport.ui')  # compile
    run(_pyuic, '-o', 'src/gui/prfreport_ui.py', 'src/gui/pling-plong-prfreport.ui')  # compile
    run(_pyuic, '-o', 'src/gui/onlinelogin_ui.py', 'src/gui/pling-plong-onlinelogin.ui')  # compile

    puts(colored.blue("Compiling resource file"))
    run(_pyrcc, '-py2', '-o', 'src/gui/odometer_rc.py', 'src/gui/odometer.qrc')


    puts(colored.green('All PyQt4 resources built'))
