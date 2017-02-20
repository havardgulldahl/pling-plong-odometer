#!/usr/bin/env python3
# -*- enc: utf-8 -*-

import sys, logging
import warnings
import time

import xmeml
from gui import main


if True: #'-d' in sys.argv:
    lvl = logging.DEBUG
else:
    # suppress error messages 
    lvl = logging.CRITICAL
    warnings.simplefilter('ignore') 

logging.basicConfig(level=lvl)

## suppress error on win
#if hasattr(sys, 'frozen') and sys.frozen == 'windows_exe':
    #import StringIO
    #sys.stderr = StringIO.StringIO()
    #sys.stdout = StringIO.StringIO()

# strptime has threading issues, calling it once before threading starts prevents this
time.strptime('2016', '%Y') 

main.rungui(sys.argv)



