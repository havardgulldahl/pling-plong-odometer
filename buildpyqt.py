#!/usr/bin/env python
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
        return subprocess.check_output([cmd, args*])
    except subprocess.CalledProcessError as e:
        puts(colored.red("Tried to run `{command}`, but got {error} ({errno})".format(command=cmd,
                                                                                      error=e.output,
                                                                                      errno=e.returncode)))

if __name__ == '__main__':
    _sp = os.path.join(site.getsitepackages()[0], "PyQt4")
    if not os.path.exists(_sp):
        puts(colored.red("Couldnt find PyQt4 installation (looked at {path}".format(path=_sp)))
        sys.exit(1)

    version = date.today().isoformat()
    puts(colored.blue("Building PyQt4 resources for Odometer version {v}".format(v=version)))

    puts(colored.blue("Checking project settings"))
    #TODO
    # change bulid defaults
    #sed -i "s/beta=.*/beta=0/" BUILDFLAGS
    #sed -i "s/releaseCheck=.*/releaseCheck=0/" BUILDFLAGS
    if sys.platform == 'darwin':
        # osx
        _pylupdate = os.path.join(_sp, 'pylupdate4')
        _lrelease = os.path.join(_sp, 'lrelease')
        _pyuic = os.path.join(_sp, 'pyuic4.bat')
        _pyrcc = os.path.join(_sp, 'pyrcc4')
        _versionfile = os.path.join('.', 'VERSIONMAC')
    elif sys.platform == 'win32':
        _pylupdate = os.path.join(_sp, 'pylupdate4.exe')
        _lrelease = os.path.join(_sp, 'lrelease.exe')
        _pyuic = os.path.join(_sp, 'uic', 'pyuic.py')
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
    # store settings in files, to be picked up by pyqt resource system
    with open(_versionfile, 'w') as f:
        f.write(version)
    run(_pyrcc, '-py2', '-o', 'src/gui/odometer_rc.py', 'src/gui/odometer.qrc')


    puts(colored.green('All PyQt4 resources built'))