#!/usr/bin/env python
# -*- enc: utf-8 -*-

import sys, logging, glob

from PyQt4 import QtCore, QtGui

from pytestqt.qt_compat import qWarning

import gui
import metadata
import xmeml
from gui import main

logging.basicConfig(level=logging.WARNING)


def test_basic_window(qtbot, tmpdir):

    app = QtGui.QApplication([])
    odo = main.Odometer(app)
    odo.show()
    qtbot.addWidget(odo)
    #qtbot.mouseClick(odo.ui.loadFileButton, QtCore.Qt.LeftButton)
    for _x in glob.glob('xmemlsamples/*.xml'):
        with qtbot.waitSignal(odo.loaded, timeout=10000) as blocker:
            odo.loadxml(_x) # load xmeml in thread
        # xmeml fully loaded here
        # run some tests to check the health of what we loaded
        #assert len(odo.audioclips) > 0