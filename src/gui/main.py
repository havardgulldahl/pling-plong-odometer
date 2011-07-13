#!/usr/bin/env python
#-*- encoding: utf8 -*-
# This file is part of odometer by Håvard Gulldahl <havard.gulldahl@nrk.no>
# (C) 2011

import sys, os.path
import time
from PyQt4.uic import loadUi
import PyQt4.QtGui as Gui
import PyQt4.QtCore as Core
import PyQt4.QtSvg as Svg
import PyQt4.Qt as Qt

trans = Core.QCoreApplication.translate

import xmeml
import metadata
import odometer_ui
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
        #time.sleep(5) # uncomment to simulate large xmeml file
        x = xmeml.VideoSequence(file=self.xmemlfile)
        #print "thread xmeml loaded"
        self.loaded.emit(x)

class StatusBox(Gui.QWidget):
    INFO = 1
    WARNING = 2
    ERROR = 3

    def __init__(self, msg, autoclose=True, msgtype=None, parent=None):
        """autoclose may be a boolean (True == autoclose) or a signal that we
        connect our close() method to"""
        super(StatusBox, self).__init__(parent)
        self.parent = parent
        self.autoclose = autoclose
        self.setWindowFlags(Core.Qt.Popup)
        if msgtype in (None, self.INFO):
            bgcolor = '#ffff7f'
        elif msgtype == self.WARNING:
            bgcolor = 'blue'#'#ffff7f'
        elif msgtype == self.WARNING:
            bgcolor = 'red'#'#ffff7f'

        self.setStyleSheet(u'QWidget { background-color: %s; }' % bgcolor)
        layout = Gui.QVBoxLayout(self)
        s = Gui.QLabel(msg, self)
        layout.addWidget(s)

    def show_(self):
        if self.autoclose == True:
            Core.QTimer.singleShot(1000, self.close)
        elif hasattr(self.autoclose, 'connect'): # it's a qt/pyqt signal
            self.autoclose.connect(self.close)
        self.show()

    def delete_(self):
        self.hide()
        self.deleteLater()

    def close(self):
        #print "closing", id(self)
        anim = Core.QPropertyAnimation(self, "windowOpacity", self.parent)
        anim.setDuration(1000)
        anim.setStartValue(1.0)
        anim.setEndValue(0.0)
        anim.finished.connect(self.delete_)
        self.anim = anim
        self.anim.start()

class Odometer(Gui.QMainWindow):
    audioclips = {}
    workers = []
    rows = {}
    msg = Core.pyqtSignal(unicode, name="msg")
    loaded = Core.pyqtSignal()
    metadataLoaded = Core.pyqtSignal('QTreeWidgetItem')
    metadataloaded = 0
    statusboxes = []

    def __init__(self, xmemlfile=None, volume=0.05, parent=None):
        super(Odometer, self).__init__(parent)
        self.settings = Core.QSettings('nrk.no', 'Pling Plong Odometer')
        self.volumethreshold = xmeml.Volume(gain=volume)
        self.xmemlfile = xmemlfile
        self.xmemlthread = XmemlWorker()
        self.xmemlthread.loaded.connect(self.load)
    	self.ui = odometer_ui.Ui_MainWindow()
        self.ui.setupUi(self)
        self.ui.detailsBox.hide()
        self.ui.errors.hide()
        self.ui.volumeThreshold.setValue(self.volumethreshold.decibel)
        self.ui.previousButton = self.ui.buttonBox.addButton(trans('cmd', 'Pre&vious'), Gui.QDialogButtonBox.ActionRole)
        self.ui.previousButton.clicked.connect(self.showPreviousMetadata)
        self.ui.nextButton = self.ui.buttonBox.addButton(trans('cmd', 'Ne&xt'), Gui.QDialogButtonBox.ActionRole)
        self.ui.nextButton.clicked.connect(self.showNextMetadata)
        self.ui.buttonBox.rejected.connect(lambda: self.ui.detailsBox.hide())
        self.ui.loadFileButton.clicked.connect(self.clicked)
        self.ui.DMAButton.clicked.connect(self.gluon)
        self.ui.creditsButton.clicked.connect(self.creditsToClipboard)
        self.ui.clips.itemSelectionChanged.connect(lambda: self.hilited(self.ui.clips.selectedItems()))
        self.ui.clips.itemActivated.connect(self.showMetadata)
        self.ui.volumeThreshold.valueChanged.connect(lambda i: self.computeAudibleDuration(xmeml.Volume(decibel=int(i))))
        self.ui.actionAbout_Odometer.activated.connect(lambda: self.showstatus("About odometer"))
        self.ui.actionAbout_Qt.activated.connect(lambda: self.showstatus("About Qt"))
        self.ui.actionConfig.activated.connect(lambda: self.showstatus("About Config"))
        self.msg.connect(self.showstatus)
        self.loaded.connect(self.computeAudibleDuration)
        self.ui.dropIcon = Svg.QSvgWidget(':/gfx/graystar', self.ui.clips)
        self.ui.dropIcon.setMinimumSize(200,200)
        self.ui.dropIcon.setToolTip('Drop your xml file here')
        #self.metadataLoaded.connect(self.checkUsage)

    def keyPressEvent(self, event):
        if event.key() == Core.Qt.Key_Escape:
            self.close()

    def dragEnterEvent(self, event):
        self.ui.dropIcon.load(':/gfx/star')
        return event.accept()

    def dragLeaveEvent(self, event):
        self.ui.dropIcon.load(':/gfx/graystar')
        return event.accept()

    def dragMoveEvent(self, event):
        if xmemlfileFromEvent(event):
            event.accept()
            return
        #print "not an xml file, ignoring"
        event.ignore()

    def dropEvent(self, event):
        event.acceptProposedAction()
        self.ui.dropIcon.load(':/gfx/graystar')
        x = xmemlfileFromEvent(event)
        if x:
            self.loadxml(x)

    def resizeEvent(self, event):
        i = self.ui.dropIcon
        i.move(self.width()/2-i.width(), self.height()*0.75-i.height())

    def showstatus(self, msg, autoclose=True, msgtype=StatusBox.INFO):
        #self.ui.statusbar.showMessage(msg, 15000)
        b = StatusBox(msg, autoclose=autoclose, msgtype=msgtype, parent=self)
        self.statusboxes.append(b)
        b.show_()
        return b
        # if you don't autoclose, call self.closestatusboxes()
        # or keep a reference to this box and .close() it yourself

    def closestatusboxes(self):
        for b in self.statusboxes:
            b.close()

    def clicked(self, qml):
        lastdir = self.settings.value('lastdir', '').toString()
        xf = Gui.QFileDialog.getOpenFileName(self,
            trans('dialog', 'Open an xmeml file (FCP export)'),
            lastdir,
            'Xmeml files (*.xml)')
        self.xmemlfile = unicode(xf)
        if not os.path.exists(self.xmemlfile):
            return False
        self.settings.setValue('lastdir', os.path.dirname(self.xmemlfile))
        self.loadxml(self.xmemlfile)

    def loadxml(self, xmemlfile):
        msgbox = self.showstatus("Loading %s..." % xmemlfile, autoclose=self.loaded)
        self.ui.progress = Gui.QProgressBar(self)
        self.ui.progress.setMinimum(0)
        self.ui.progress.setMaximum(0) # don't show progress, only "busy" indicator
        def remove():
            self.ui.statusbar.removeWidget(self.ui.progress)
            self.ui.progress.deleteLater()
        self.loaded.connect(remove)
        self.ui.statusbar.addWidget(self.ui.progress, 100)
        self.xmemlthread.load(xmemlfile)

    def load(self, xmeml):
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
        self.msg.emit(self.tr(u"%i audio clips loaded from xmeml sequence \u00ab%s\u00bb." % (numclips, xmeml.name)))
        self.loaded.emit()

    def computeAudibleDuration(self, volumethreshold=None):
        if isinstance(volumethreshold, float):
            volumethreshold = xmeml.Volume(gain=volumethreshold)
        elif volumethreshold is None:
            volumethreshold = xmeml.Volume(decibel=int(self.ui.volumeThreshold.value()))
        print u'Computing duration of audio above %idB' % volumethreshold.decibel
        print "gain: ", volumethreshold.gain
        self.ui.clips.clear()
        for audioclip, pieces in self.audioclips.iteritems():
            a = []
            r = Gui.QTreeWidgetItem(self.ui.clips, ['', audioclip.name, "xx", '...'])
            r.clip = audioclip
            r.metadata = metadata.TrackMetadata(filename=audioclip.name)
            self.rows[audioclip.name] = r
            w = metadata.findResolver(audioclip.name)
            if w:
                w.trackResolved.connect(self.loadMetadata) # connect the 'resolved' signal
                w.trackResolved.connect(self.trackCompleted) # connect the 'resolved' signal
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
                r.clip.audibleDuration = 0
                r.setText(2, "0s")
                r.setToolTip(2, u'There are no audible frames at this volume threshold (%s dB)' % volumethreshold.decibel)
            else:
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
                r.setText(2, "%.1fs (%i frames)" % (secs, frames))
                r.clip.audibleDuration = secs

    def loadMetadata(self, filename, metadata):
        #print "got metadata for %s: %s" % (filename, metadata)
        row = self.rows[unicode(filename)]
        row.metadata = metadata
        if metadata.productionmusic:
            txt = u"\u00ab%(title)s\u00bb \u2117 %(label)s"
        else:
            txt = u"%(artist)s: \u00ab%(title)s\u00bb \u2117 %(label)s %(year)s" 
        row.setText(3, txt % vars(metadata))
        if metadata.musiclibrary == "Sonoton":
            self.ui.AUXButton.setEnabled(True)
        self.metadataLoaded.emit(row)

    def trackCompleted(self, filename, metadata):
        self.metadataloaded += 1
        print len(self.audioclips), self.metadataloaded
        if len(self.audioclips)  == self.metadataloaded:
            self.ui.DMAButton.setEnabled(True)

    def showProgress(self, filename, progress):
        print "got progress for %s: %s" % (filename, progress)
        row = self.rows[unicode(filename)]
        if progress < 100: # not yet reached 100%
            p = Gui.QProgressBar(parent=self.ui.clips)
            p.setValue(progress)
            self.ui.clips.setItemWidget(row, 3, p)
        else: # finishd, show some text instead
            self.ui.clips.removeItemWidget(row, 3)

    def hilited(self, rows):
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
        if self.ui.detailsBox.isVisible(): # currently editing metadata
            self.showMetadata(r)

    def showMetadata(self, row, col=None):
        try:
            self.ui.detailsBox.currentRow = row
            self.ui.clipTitle.setText(row.metadata.title or '')
            self.ui.clipArtist.setText(row.metadata.artist or '')
            self.ui.clipComposer.setText(row.metadata.composer or '')
            self.ui.clipYear.setText(unicode(row.metadata.year or 0))
            self.ui.clipTracknumber.setText(row.metadata.tracknumber or '')
            self.ui.clipCopyright.setText(row.metadata.copyright or '')
            self.ui.clipLabel.setText(row.metadata.label or '')
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
            if r.metadata.productionmusic:
                s += u"\u00ab%(title)s\u00bb\r\n\u2117 %(label)s" % vars(r.metadata)
            else:
                s += u"\u00ab%(title)s\u00bb\r\n%(artist)s\r\n \u2117 %(label)s %(year)s" % vars(r.metadata)
            s += u"\r\n\r\n\r\n" 
        clipboard = self.app.clipboard()
        clipboard.setText(s)
        self.msg.emit("End credit metadata copied to clipboard.")

    def checkUsage(self):
        maxArtists = None
        maxTitlePerArtist = 3
        maxTitleLength = 30
        artists = {}
        icon = Gui.QIcon(':/gfx/warn')
        for filename, row in self.rows.iteritems():
            try:
                md = row.metadata
                if row.clip.audibleDuration > maxTitleLength:
                    row.setIcon(2, icon)
                    row.setToolTip(2, "You're currently not allowed to peruse more than %s secs from each clip" % maxTitleLength)
                if not artists.has_key(md.artist):
                    artists[md.artist] = []
                artists[md.artist].append(md.title)
            except AttributeError:
                pass

        bads = [ (a,t) for a,t in artists.iteritems() if len(t) > maxTitlePerArtist ]
        #print bads
        if bads:
            self.ui.errors.show()
            self.ui.errorText.setText("""<h1>Warning</h1><p>Current agreements set a limit of %i titles per artist,
                    but in this sequence:</p><ul>%s<ul>""" % (maxTitlePerArtist, 
                        "".join(["<li>%s: %s times</li>" % (a,len(t)) for a,t in bads])))
            return False
        else:
            self.ui.errors.hide()
            return True

            
    def gluon(self):
        #ALL  data loaded
        prodno = unicode(self.ui.prodno.text()).strip()
        #ok = self.checkUsage()
        if False: #not ok:
            msg = Gui.QMessageBox.critical(self, "Rights errors", "Not ok according to usage agreement")
        if len(prodno) == 0:
            msg = Gui.QMessageBox.critical(self, "Need production number", 
                                           "You must enter the production number")
            self.ui.prodno.setFocus()
            return False
        self.gluon = metadata.Gluon()
        self.gluon.worker.trackResolved.connect(self.gluonFinished)
        self.gluon.resolve(prodno, self.rows.values())

    def gluonFinished(self, trackname, metadata):
        print "gluonFinished: %s -> %s" % (trackname, metadata)
        for nom, row in self.rows.items():
            print repr(os.path.splitext(nom)[0]), repr(unicode(trackname))
            if os.path.splitext(nom)[0] == unicode(trackname):
                row.setBackground(0, Gui.QBrush(Gui.QColor("light green")))

    def run(self, app):
        self.app = app
        self.show()
        if self.xmemlfile is not None: # program was started with an xmeml file as argument
            self.loadxml(self.xmemlfile)
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

def rungui(argv):
    f = None
    try:
        if os.path.exists(argv[1]):
            f = argv[1]
            #argv = argv[0:-1]
    except IndexError:
        pass
    app = Gui.QApplication(argv)
    if f is not None: o = Odometer(f)
    else: o = Odometer()
    o.run(app)

if __name__ == '__main__':
    rungui(sys.argv)
