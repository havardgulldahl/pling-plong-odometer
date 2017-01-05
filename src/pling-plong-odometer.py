#!/usr/bin/env python
# -*- enc: utf-8 -*-

import sys, logging
import gui
import metadata
import xmeml
from gui import main
import warnings


if '-d' in sys.argv:
    lvl = logging.DEBUG
else:
    lvl = logging.CRITICAL

logging.basicConfig(level=lvl)

warnings.simplefilter('ignore') # suppress error messages 

main.rungui(sys.argv)



