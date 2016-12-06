#!/usr/bin/env python
# -*- enc: utf-8 -*-

import sys, logging
import gui
import metadata
import xmeml
from gui import main
import warnings

logging.basicConfig(level=logging.CRITICAL)

warnings.simplefilter('ignore') # suppress error messages 

main.rungui(sys.argv)



