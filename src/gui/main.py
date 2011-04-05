#!/usr/bin/env python
#-*- encoding: utf8 -*-

import sys, os.path
from PyQt4.uic import loadUi
import PyQt4.QtGui as Gui
import PyQt4.QtCore as Core
import PyQt4.Qt as Qt

import xmeml
import odometer_rc 


class Odometer(Gui.QMainWindow):
    UIFILE="pling-plong-odometer.ui"

    rows = []
    rowCreated = Core.pyqtSignal(['QTreeWidgetItem'], name="rowCreated")

    def __init__(self, xmemlfile,parent=None):
        super(Odometer, self).__init__(parent)
        self.xmemlfile = xmemlfile
        self.ui = loadUi(self.UIFILE, self)
        self.ui.loadFileButton.clicked.connect(self.clicked)
        self.ui.clips.itemSelectionChanged.connect(lambda: self.hilited(self.ui.clips.selectedItems()))
        self.rowCreated.connect(self.lookuprow)

    def keyPressEvent(self, event):
        if event.key() == Core.Qt.Key_Escape:
            self.close()

    def dragEnterEvent(self, event):
        return event.accept()

    def dragMoveEvent(self, event):
        if xmemlfileFromEvent(event):
            event.accept()
            return
        print "no xml file, ignoring"
        event.ignore()

    def dropEvent(self, event):
        event.acceptProposedAction()
        x = xmemlfileFromEvent(event)
        if x:
            self.load(x)

    def clicked(self, qml):
        self.load(self.xmemlfile)

    def load(self, xmemlfile):
        self.ui.statusbar.showMessage("Loading %s..." % xmemlfile)
        audioclips = {}
        self.xmeml = xmeml.VideoSequence(file=xmemlfile)
        for c in self.xmeml.track_items:
            if not ( c.type == 'clipitem' and c.file.mediatype == 'audio' ): continue
            if not audioclips.has_key(c.file): 
                audioclips[c.file] = [c,]
            else:
                audioclips[c.file] += [c,]
                    
        self.ui.statusbar.showMessage("%i audio clips loaded from %s" % (len(audioclips.keys()), xmemlfile)
        for audioclip, pieces in audioclips.iteritems():
            a = []
            r = Gui.QTreeWidgetItem(self.ui.clips, ['', audioclip.name, "xx", '...'])
            r.setData(0, Core.Qt.ItemIsUserCheckable, True)
            r.setCheckState(0, Core.Qt.Checked)
            r.clip = audioclip
            self.rows.append(r)
            self.rowCreated.emit(r)
            for subclip in pieces:
                sr = Gui.QTreeWidgetItem(r, ['', subclip.id, "%s" % (subclip.audibleframes(),)])
                sr.clip = subclip
                a += subclip.audibleframes()
                r.addChild(sr)
            aa = uniqify(a)
            aa.sort()
            comp = []
            start, end = aa[0]
            for (s, e) in aa[1:]: 
                if s < end and s > start and e > end:
                    end = e
                elif s == end:
                    end = e
                elif (s > end or e < start): 
                    comp.append( (start, end) )
                    start = s
                    end = e 
                elif (e > start and e < end and s < start) or e == start:
                    start = s
            comp.append( (start, end) )
            frames = sum( o-i for (i,o) in comp )
            secs = frames  / audioclip.timebase
            #print audioclip.name, a, comp, frames, secs
            r.setText(2, "%i frames = %.1fs" % (frames, secs))

    def lookuprow(self, r):
        print "lookup row: ", r

    def hilited(self, rows):
        print "hilite row: ", rows
        self.ui.metadata.setText('')
        if not len(rows): return
        s = "<b>Metadata:</b><br>"
        for r in rows:
            #print vars(r.clip)
            s += """<i>Name:</i><br>%(name)s<br>
                    <i>Type:</i><br>%(mediatype)s<br>
                    <i>Length:</i><br>%(duration)sf<br>
                    <i>Rate:</i><br>%(timebase)sfps<br>
                    """ % (vars(r.clip))
            if isinstance(r.clip, xmeml.TrackItem):
                s += """<i>Start/End:</i><br>%.0ff/%.0ff<br>
                        <i>Filters:</i><br><ul><li>%s</li></ul><br>
                        """ % (r.clip.start(), r.clip.end(), 
                              '</li><li>'.join([f.name for f in r.clip.filters]))
        self.ui.metadata.setText(s)


    def run(self, app):
        self.ui.show()
        sys.exit(app.exec_())

def uniqify(seq):
    keys = {} 
    for e in seq: 
        keys[e] = 1 
    return keys.keys()

def xmemlfileFromEvent(event):
    data = event.mimeData()
    try:
        for f in data.urls():
            fil = unicode(f.toLocalFile())
            if os.path.isfile(fil) and os.path.splitext(fil.upper())[1] == ".XML":
                # also try to load it with xmeml.Videosequence ?
                return fil
    except Exception, (e):
        print e
    return False

if __name__ == '__main__':
    app = Gui.QApplication(sys.argv)
    o = Odometer("../../data/fcp.sample.xml")
    o.run(app)

