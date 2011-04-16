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

class Odometer(Gui.QMainWindow):
    UIFILE="pling-plong-odometer.ui"

    audioclips = {}
    workers = []
    rows = {}
    msg = Core.pyqtSignal(unicode, name="msg")
    loaded = Core.pyqtSignal()
    metadataLoaded = Core.pyqtSignal('QTreeWidgetItem')

    def __init__(self, xmemlfile, volume=0.05, parent=None):
        super(Odometer, self).__init__(parent)
        self.xmemlfile = xmemlfile
        self.volumethreshold = xmeml.Volume(gain=volume)
        self.xmemlthread = XmemlWorker()
        self.xmemlthread.loaded.connect(self.load)
        self.ui = loadUi(self.UIFILE, self)
        self.ui.detailsBox.hide()
        self.ui.errors.hide()
        self.ui.volumeThreshold.setValue(self.volumethreshold.decibel)
        self.ui.previousButton = self.ui.buttonBox.addButton(u'Pre&vious', Gui.QDialogButtonBox.ActionRole)
        self.ui.previousButton.clicked.connect(self.showPreviousMetadata)
        self.ui.nextButton = self.ui.buttonBox.addButton(u'Ne&xt', Gui.QDialogButtonBox.ActionRole)
        self.ui.nextButton.clicked.connect(self.showNextMetadata)
        self.ui.buttonBox.rejected.connect(lambda: self.ui.detailsBox.hide())
        self.ui.loadFileButton.clicked.connect(self.clicked)
        self.ui.creditsButton.clicked.connect(self.creditsToClipboard)
        self.ui.clips.itemSelectionChanged.connect(lambda: self.hilited(self.ui.clips.selectedItems()))
        self.ui.clips.itemActivated.connect(self.showMetadata)
        self.ui.clipTitle.textEdited.connect(lambda s: setattr(self.ui.detailsBox.currentRow.metadata, 'title', unicode(s)))
        self.ui.clipArtist.textEdited.connect(lambda s: setattr(self.ui.detailsBox.currentRow.metadata, 'artist', unicode(s)))
        self.ui.clipComposer.textEdited.connect(lambda s: setattr(self.ui.detailsBox.currentRow.metadata, 'composer', unicode(s)))
        self.ui.clipYear.valueChanged.connect(lambda i: setattr(self.ui.detailsBox.currentRow.metadata, 'year', int(i)))
        self.ui.clipTracknumber.textEdited.connect(lambda s: setattr(self.ui.detailsBox.currentRow.metadata, 'tracknumber', unicode(s)))
        self.ui.clipCopyright.textEdited.connect(lambda s: setattr(self.ui.detailsBox.currentRow.metadata, 'copyright', unicode(s)))
        self.ui.clipLabel.textEdited.connect(lambda s: setattr(self.ui.detailsBox.currentRow.metadata, 'label', unicode(s)))
        self.ui.volumeThreshold.valueChanged.connect(lambda i: self.computeAudibleDuration(xmeml.Volume(decibel=int(i))))
        self.msg.connect(self.showstatus)
        self.loaded.connect(self.computeAudibleDuration)
        self.metadataLoaded.connect(self.checkUsage)

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
        self.ui.statusbar.showMessage(msg, 15000)

    def clicked(self, qml):
        self.loadxml(self.xmemlfile)

    def loadxml(self, xmemlfile):
        self.msg.emit("Loading %s..." % xmemlfile)
        self.xmemlthread.load(xmemlfile)

    def load(self, xmeml):
        #print "load: got xmeml: ", xmeml 
        self.xmeml = xmeml
        self.audioclips = {}
        for c in xmeml.track_items:
            if not ( c.type == 'clipitem' and c.file.mediatype == 'audio' ): continue
            if not self.audioclips.has_key(c.file): 
                self.audioclips[c.file] = [c,]
            else:
                self.audioclips[c.file] += [c,]
        numclips = len(self.audioclips.keys())
        self.ui.creditsButton.setEnabled(numclips > 0)
        self.msg.emit(u"%i audio clips loaded from xmeml sequence \u00ab%s\u00bb." % (numclips, xmeml.name))
        self.loaded.emit()

    def computeAudibleDuration(self, volumethreshold=None):
        if isinstance(volumethreshold, float):
            volumethreshold = xmeml.Volume(gain=volumethreshold)
        elif volumethreshold is None:
            volumethreshold = xmeml.Volume(decibel=int(self.ui.volumeThreshold.value()))
        self.msg.emit(u'Computing duration of audio above %idB' % volumethreshold.decibel)
        print "gain: ", volumethreshold.gain
        self.clips.clear()
        for audioclip, pieces in self.audioclips.iteritems():
            a = []
            r = Gui.QTreeWidgetItem(self.ui.clips, ['', audioclip.name, "xx", '...'])
            r.setData(0, Core.Qt.ItemIsUserCheckable, True)
            r.setCheckState(0, Core.Qt.Checked)
            r.clip = audioclip
            self.rows[audioclip.name] = r
            w = metadata.findResolver(audioclip.name)
            w.trackResolved.connect(self.loadMetadata) # connect the 'resolved' signal
            w.trackProgress.connect(self.showProgress) 
            self.workers.append(w) # keep track of the worker
            w.resolve(audioclip.name) # put the worker to work async
            #w.testresolve(audioclip.name) # put the worker to work async
            for subclip in pieces:
                sr = Gui.QTreeWidgetItem(r, ['', subclip.id, "%s" % (subclip.audibleframes(volumethreshold),)])
                sr.clip = subclip
                a += subclip.audibleframes(volumethreshold)
                r.addChild(sr)
            if not len(a):
                self.msg.emit(u'There are no audible frames at this volume threshold (%s dB)' % volumethreshold.decibel)
                self.clips.clear()
                return None # no audible frames at this volume threshold
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
            r.clip.audibleDuration = secs

    def loadMetadata(self, filename, metadata):
        #print "got metadata for %s: %s" % (filename, metadata)
        row = self.rows[unicode(filename)]
        row.metadata = metadata
        row.setText(3, u"%(artist)s \u2117 %(year)s: \u00ab%(title)s\u00bb" % vars(metadata))
        if metadata.musiclibrary == "Sonoton":
            self.AUXButton.setEnabled(True)
        self.metadataLoaded.emit(row)

    def showProgress(self, filename, progress):
        print "got progress for %s: %s" % (filename, progress)
        return
        p = Gui.QProgressBar(parent=self.ui.clips)
        p.setValue(progress)
        row = self.rows[unicode(filename)]
        self.ui.clips.setItemWidget(row, 3, p)

    def hilited(self, rows):
        #print "hilite row: ", rows
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
            if hasattr(r, 'metadata') and r.metadata.musiclibrary is not None:
                s += """<i>Library</i><br>%s</br>""" % r.metadata.musiclibrary
            if isinstance(r.clip, xmeml.TrackItem):
                s += """<i>Start/End:</i><br>%.0ff/%.0ff<br>
                        <i>Filters:</i><br><ul><li>%s</li></ul><br>
                        """ % (r.clip.start(), r.clip.end(), 
                              '</li><li>'.join([f.name for f in r.clip.filters]))
        self.ui.metadata.setText(s)

    def showMetadata(self, row, col=None):
        try:
            self.ui.clipTitle.setText(row.metadata.title or '')
            self.ui.clipArtist.setText(row.metadata.artist or '')
            self.ui.clipComposer.setText(row.metadata.composer or '')
            self.ui.clipYear.setValue(row.metadata.year or 0)
            self.ui.clipTracknumber.setText(row.metadata.tracknumber or '')
            self.ui.clipCopyright.setText(row.metadata.copyright or '')
            self.ui.clipLabel.setText(row.metadata.label or '')
            self.ui.detailsBox.currentRow = row
            self.ui.detailsBox.show()
        except AttributeError:
            self.ui.detailsBox.hide()
        self.ui.previousButton.setEnabled(self.ui.clips.itemAbove(row) is not None)
        self.ui.nextButton.setEnabled(self.ui.clips.itemBelow(row) is not None)

    def showPreviousMetadata(self, b):
        clips = self.ui.clips
        r = clips.itemAbove(self.ui.detailsBox.currentRow)
        clips.setCurrentItem(r)
        clips.itemActivated.emit(r, -1)

    def showNextMetadata(self, b):
        clips = self.ui.clips
        r = clips.itemBelow(self.ui.detailsBox.currentRow)
        clips.setCurrentItem(r)
        clips.itemActivated.emit(r, -1)

    def creditsToClipboard(self):
        s = ""
        for r in self.rows.values():
            s += u"%(title)s\r\n%(artist)s\r\n%(label)s \u2117 %(year)s\r\n\r\n\r\n" % vars(r.metadata)
        clipboard = self.app.clipboard()
        clipboard.setText(s)
        self.msg.emit("End credit metadata copied to clipboard.")

    def checkUsage(self, row):
        maxArtists = None
        maxTitlePerArtist = 3
        maxTitleLength = 60
        artists = {}
        for filename, row in self.rows.iteritems():
            try:
                md = row.clip.metadata
                print row.clip.audibleDuration
                if row.clip.audibleDuration > maxTitleLength:
                    row.setIcon(':/gfx/warn.png')
                if not artists.has_key(md.artist):
                    artists[md.artist] = []
                artists[md.artist].append(md.title)
            except AttributeError:
                pass

        bads = [ (a,t) for a,t in artists.iteritems() if len(t) > maxTitlePerArtist ]
        print bads
        if bads:
            self.ui.errors.show()
            self.ui.errors.setText("""<h1>Warning</h1><p>Current agreements set a limit of %i titles per artist,
                    but in this sequence:</p><ul>%s<ul>""" % (maxTitlePerArtist, 
                        "".join(["<li>%s: %s times</li>" % (a,t) for a,t in bads])))
        else:
            self.ui.errors.hide()

            


    def run(self, app):
        self.app = app
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

