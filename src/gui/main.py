#!/usr/bin/env python
#-*- encoding: utf8 -*-

import sys
from PyQt4.uic import loadUi
import PyQt4.QtGui as Gui
import PyQt4.QtCore as Core
import PyQt4.Qt as Qt

import xmeml


class Odometer(Gui.QMainWindow):
    UIFILE="pling-plong-odometer.ui"

    rows = []
    rowCreated = Core.pyqtSignal(['QTreeWidgetItem'], name="rowCreated")

    def __init__(self, xmemlfile,parent=None):
        super(Odometer, self).__init__(parent)
        self.xmemlfile = xmemlfile
        self.ui = loadUi(self.UIFILE, self)
        self.ui.loadFileButton.clicked.connect(self.clicked)
        self.rowCreated.connect(self.lookuprow)

    def keyPressEvent(self, event):
        if event.key() == Core.Qt.Key_Escape:
            self.close()

    def clicked(self, qml):
        audioclips = {}
        self.xmeml = xmeml.VideoSequence(file=self.xmemlfile)
        for c in self.xmeml.track_items:
            if c.id is None or c.type != 'clipitem' or c.mediatype != 'audio': continue
            #if not c.file.mediatype == 'audio': continue
            if not c.id.startswith("SCD"): continue
            if not audioclips.has_key(c.file.id): 
                audioclips[c.file.id] = [c,]
            else:
                audioclips[c.file.id] += [c,]
                
        for audioclip, pieces in audioclips.iteritems():
            length = 12.2
            r = Gui.QTreeWidgetItem(self.ui.clips, ['', audioclip, "%.1fs" % length, '...'])
            r.setData(0, Core.Qt.ItemIsUserCheckable, True)
            r.setCheckState(0, Core.Qt.Checked)
            self.rows.append(r)
            self.rowCreated.emit(r)
            for subclip in pieces:
                sr = Gui.QTreeWidgetItem(r, ['', subclip.id, "%s - %s" % (subclip.start(), subclip.end())])
                r.addChild(sr)

    def lookuprow(self, r):
        #print "lookup row: ", r
        pass

    def run(self, app):
        self.ui.show()
        sys.exit(app.exec_())

if __name__ == '__main__':
    app = Gui.QApplication(sys.argv)
    o = Odometer("../../data/fcp.sample.xml")
    o.run(app)

