#!/usr/bin/env python
#-*- encoding: utf8 -*-

import sys
from PyQt4.uic import loadUi
import PyQt4.QtGui as Gui
import PyQt4.QtCore as Core

import xmeml


def audiblesecs(clipitem, values, threshold=0.1):
  secs = 0.0
  prev = 0.0
  if isinstance(values, basestring): # single value for whole clipitem
    if float(values) > threshold:
      secs = float(clipitem.duration) / clipitem.timebase
  else: # a list of keyframes and respective volume level
    # add the (implicit) keyframe end point
    keyframelist = values[:]
    keyframelist += (clipitem.duration, values[-1][1]),
    for keyframe, volume in keyframelist:
      if float(volume) < threshold: continue
      secs += (float(keyframe) - prev) / clipitem.timebase
      prev = float(keyframe)
  return secs

class Odometer(Gui.QMainWindow):
  UIFILE="pling-plong-odometer.ui"

  rows = []
  rowCreated = Core.pyqtSignal(['QTreeWidgetItem'], name="rowCreated")

  def __init__(self, xmemlfile,parent=None):
    super(Odometer, self).__init__(parent)
    self.xmeml = xmeml.VideoSequence(file=xmemlfile)
    #self.app = Gui.QApplication(argv)
    self.ui = loadUi(self.UIFILE, self)
    self.ui.loadFileButton.clicked.connect(self.clicked)
    self.rowCreated.connect(self.lookuprow)

  def clicked(self, qml):
    print "clicked"
    for c in self.xmeml.track_items:
      if c.id is None or c.type != 'clipitem' or c.mediatype != 'audio': continue
      if not c.name.startswith("SCD"): continue
      for f in c.filters:
        if f.id != "audiolevels": continue
        for param in f.parameters:
          if param.values:
            secs = "%.1fs" % audiblesecs(c, param.values)
          else:
            secs = "%.1fs" % audiblesecs(c, param.value)

          r = Gui.QTreeWidgetItem(self.ui.clips, ['', c.name, secs, '...'])
          self.rows.append(r)
          self.rowCreated.emit(r)

  def lookuprow(self, r):
    print "lookup row: ", r

  def run(self, app):
    self.ui.show()
    sys.exit(app.exec_())

if __name__ == '__main__':
  app = Gui.QApplication(sys.argv)
  o = Odometer("../../data/fcp.sample.xml")
  o.run(app)

