#!/usr/bin/env python
#-*- encoding: utf8 -*-

import sys
from PyQt4.uic import loadUi
import PyQt4.QtGui as Gui

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



class Odometer(object):
  UIFILE="pling-plong-odometer.ui"

  def __init__(self, argv, xmemlfile):
    self.xmeml = xmeml.VideoSequence(file=xmemlfile)
    self.app = Gui.QApplication(argv)
    self.ui = loadUi(self.UIFILE)
    self.ui.loadFileButton.clicked.connect(self.clicked)

  def clicked(self, qml):
    print "clicked"
    for c in self.xmeml.track_items:
      if c.id is None or c.type != 'clipitem' or c.mediatype != 'audio': continue
      if not c.name.startswith("SCD"): continue
      for f in c.filters:
        if f.id != "audiolevels": continue
        for param in f.parameters:
          if param.values:
            print "    - %s (%s - %s) = %.1f -> %s" % (param.id, param.min, param.max, audiblesecs(c, param.values), param.values)
            Gui.QTreeWidgetItem([c.name, audiblesecs(c, param.values)]) 
          elif param.value:
            print "    - %s (%s - %s) = %.1f -> %s" % (param.id, param.min, param.max, audiblesecs(c, param.value), param.value)
            Gui.QTreeWidgetItem([c.name, audiblesecs(c, param.value)]) 

  def run(self):
    self.ui.show()
    sys.exit(self.app.exec_())

if __name__ == '__main__':
  o = Odometer(sys.argv, "../../data/fcp.sample.xml")
  o.run()

