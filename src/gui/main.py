#!/usr/bin/env python
#-*- encoding: utf8 -*-

import sys, os.path
from PyQt4.uic import loadUi
import PyQt4.QtGui as Gui
import PyQt4.QtCore as Core
import PyQt4.Qt as Qt

import xmeml
import metadata
import odometer_rc 

class XmemlWorker(Core.QThread):
    loaded = Core.pyqtSignal([xmeml.VideoSequence], name="loaded")

    def __init__(self, parent=None):
        super(XmemlWorker, self).__init__(parent)
        self.exiting = False

    def __del__(self):
        self.exiting = True
        self.wait()

    def load(self, filename):
        self.xmemlfile = filename
        self.start()

    def run(self):
        x = xmeml.VideoSequence(file=self.xmemlfile)
        #print "thread xmeml loaded"
        self.loaded.emit(x)

class MetadataWorker(Core.QThread):
    worklist = []
    resolved = Core.pyqtSignal( [ unicode, metadata.TrackMetadata ], name="resolved")

    def __init__(self, parent=None):
        super(MetadataWorker, self).__init__(parent)
        self.exiting = False
        self.query = metadata.MetadataQuery()

    def __del__(self):
        self.exiting = True
        self.wait()

    def load(self, filename):
        print "thread %s loading filename: %s" % (self, filename)
        self.filename = filename
        self.start()

    def run(self):
        print "finding metadata from", self.filename
        metadata = self.query.resolve(self.filename)
        self.resolved.emit(self.filename, metadata)

class Odometer(Gui.QMainWindow):
    UIFILE="pling-plong-odometer.ui"

    workers = []
    rows = {}
    rowCreated = Core.pyqtSignal(['QTreeWidgetItem'], name="rowCreated")
    msg = Core.pyqtSignal([unicode], name="msg")
    filenameFound = Core.pyqtSignal([unicode], name="filenameFound")

    def __init__(self, xmemlfile,parent=None):
        super(Odometer, self).__init__(parent)
        self.xmemlfile = xmemlfile
        self.xmemlthread = XmemlWorker()
        self.xmemlthread.loaded.connect(self.load)
        self.ui = loadUi(self.UIFILE, self)
        self.ui.loadFileButton.clicked.connect(self.clicked)
        self.ui.clips.itemSelectionChanged.connect(lambda: self.hilited(self.ui.clips.selectedItems()))
        self.rowCreated.connect(self.lookuprow)
        self.msg.connect(self.showstatus)

    def keyPressEvent(self, event):
        if event.key() == Core.Qt.Key_Escape:
            self.close()

    def dragEnterEvent(self, event):
        return event.accept()

    def dragMoveEvent(self, event):
        if xmemlfileFromEvent(event):
            event.accept()
            return
        #print "not an xml file, ignoring"
        event.ignore()

    def dropEvent(self, event):
        event.acceptProposedAction()
        x = xmemlfileFromEvent(event)
        if x:
            self.loadxml(x)

    def showstatus(self, msg):
        self.ui.statusbar.showMessage(msg)

    def clicked(self, qml):
        self.loadxml(self.xmemlfile)

    def loadxml(self, xmemlfile):
        self.msg.emit("Loading %s..." % xmemlfile)
        self.xmemlthread.load(xmemlfile)

    def load(self, xmeml):
        #print "load: got xmeml: ", xmeml 
        audioclips = {}
        self.clips.clear()
        for c in xmeml.track_items:
            if not ( c.type == 'clipitem' and c.file.mediatype == 'audio' ): continue
            if not audioclips.has_key(c.file): 
                audioclips[c.file] = [c,]
            else:
                audioclips[c.file] += [c,]
        self.msg.emit("%i audio clips loaded from xml file" % len(audioclips.keys()))

        for audioclip, pieces in audioclips.iteritems():
            a = []
            r = Gui.QTreeWidgetItem(self.ui.clips, ['', audioclip.name, "xx", '...'])
            r.setData(0, Core.Qt.ItemIsUserCheckable, True)
            r.setCheckState(0, Core.Qt.Checked)
            r.clip = audioclip
            self.rows[audioclip.name] = r
            w = MetadataWorker()
            w.resolved.connect(self.loadMetadata)
            self.workers.append(w)
            w.load(audioclip.name)
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

    def loadMetadata(self, filename, metadata):
        print "got metadata for %s: %s" % (filename, metadata)
        print vars(metadata)
        row = self.rows[unicode(filename)]
        row.metadata = metadata
        row.setText(3, "%(composer)s - %(year)s: %(title)s" % vars(metadata))

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

