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

from xmeml import iter as xmemliter
import metadata
import odometer_ui
import odometer_rc 
import auxreport_ui

try:
    from gui import audioplayer
    USE_AUDIOPLAYER=True
except ImportError:
    USE_AUDIOPLAYER=False


class XmemlWorker(Core.QThread):
    loaded = Core.pyqtSignal(xmemliter.XmemlParser, name="loaded")

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
        xmeml = xmemliter.XmemlParser(self.xmemlfile)
        self.loaded.emit(xmeml)

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
        elif msgtype == self.ERROR:
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
    showsubclips = True

    def __init__(self, xmemlfile=None, volume=0.05, parent=None):
        super(Odometer, self).__init__(parent)
        self.settings = Core.QSettings('nrk.no', 'Pling Plong Odometer')
        self.volumethreshold = xmemliter.Volume(gain=volume)
        self.xmemlfile = xmemlfile
        self.xmemlthread = XmemlWorker()
        self.xmemlthread.loaded.connect(self.load)
    	self.ui = odometer_ui.Ui_MainWindow()
        self.ui.setupUi(self)
        self.ui.detailsBox.hide()
        self.ui.errors.hide()
        self.ui.volumeThreshold.setValue(self.volumethreshold.gain)
        self.ui.previousButton = self.ui.buttonBox.addButton(trans('cmd', 'Pre&vious'), Gui.QDialogButtonBox.ActionRole)
        self.ui.previousButton.clicked.connect(self.showPreviousMetadata)
        self.ui.nextButton = self.ui.buttonBox.addButton(trans('cmd', 'Ne&xt'), Gui.QDialogButtonBox.ActionRole)
        self.ui.nextButton.clicked.connect(self.showNextMetadata)
        self.ui.buttonBox.rejected.connect(lambda: self.ui.detailsBox.hide())
        self.ui.loadFileButton.clicked.connect(self.clicked)
        self.ui.DMAButton.clicked.connect(self.gluon)
        self.ui.AUXButton.clicked.connect(self.auxReport)
        self.ui.creditsButton.clicked.connect(self.creditsToClipboard)
        self.ui.clips.itemSelectionChanged.connect(lambda: self.hilited(self.ui.clips.selectedItems()))
        self.ui.clips.itemActivated.connect(self.showMetadata)
        self.ui.volumeThreshold.valueChanged.connect(lambda i: self.computeAudibleDuration(xmemliter.Volume(gain=float(i))))
        self.ui.actionAbout_Odometer.triggered.connect(lambda: self.showstatus("About odometer"))
        self.ui.actionAbout_Qt.triggered.connect(lambda: self.showstatus("About Qt"))
        self.ui.actionConfig.triggered.connect(lambda: self.showstatus("About Config"))
        self.msg.connect(self.showstatus)
        self.loaded.connect(self.computeAudibleDuration)
        self.ui.dropIcon = Svg.QSvgWidget(':/gfx/graystar', self.ui.clips)
        self.ui.dropIcon.setMinimumSize(200,200)
        self.ui.dropIcon.setToolTip('Drop your xml file here')
        if not USE_AUDIOPLAYER:
            self.ui.playButton.hide()
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
        # if you don't autoclose, call self.closestatusboxes()
        # or keep a reference to this box and .close() it yourself
        b = StatusBox(msg, autoclose=autoclose, msgtype=msgtype, parent=self)
        self.statusboxes.append(b)
        b.show_()
        return b

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
        self.loadingbar()
        self.loaded.connect(self.removeLoadingbar)
        self.loaded.connect(lambda: self.ui.fileInfo.setText("<b>Loaded:</b> %s" % os.path.basename(xmemlfile)))
        self.loaded.connect(lambda: self.ui.fileInfo.setToolTip(os.path.abspath(xmemlfile)))
        self.xmemlthread.load(xmemlfile)

    def loadingbar(self):
        self.ui.progress = Gui.QProgressBar(self)
        self.ui.progress.setMinimum(0)
        self.ui.progress.setMaximum(0) # don't show progress, only "busy" indicator
        self.ui.statusbar.addWidget(self.ui.progress, 100)

    def removeLoadingbar(self):
        self.ui.statusbar.removeWidget(self.ui.progress)
        self.ui.progress.deleteLater()

    def load(self, xmemlparser):
        self.audioclips, self.audiofiles = xmemlparser.audibleranges()
        numclips = len(self.audioclips.keys())
        self.ui.creditsButton.setEnabled(numclips > 0)
        self.msg.emit(self.tr(u"%i audio clips loaded from xmeml sequence \u00ab%s\u00bb." % (numclips, xmemlparser.name)))
        self.loaded.emit()

    def computeAudibleDuration(self):
        self.ui.clips.clear()
        for audioname, ranges in self.audioclips.iteritems():
            frames = len(ranges)
            fileref = self.audiofiles[audioname]
            secs = frames / fileref.timebase
            r = Gui.QTreeWidgetItem(self.ui.clips, ['', audioname, 
                                                    '%ss (%sf)' % (secs, frames)])
            r.metadata = metadata.TrackMetadata(filename=audioname)
            r.audioname = audioname
            r.clip = {'durationsecs':secs, 'durationframes':frames}
            self.rows[audioname] = r
            w = metadata.findResolver(audioname)
            r.setCheckState(0, Core.Qt.Unchecked)
            if w:
                w.trackResolved.connect(self.loadMetadata) # connect the 'resolved' signal
                w.trackResolved.connect(self.trackCompleted) # connect the 'resolved' signal
                w.trackProgress.connect(self.showProgress) 
                self.workers.append(w) # keep track of the worker
                w.resolve(audioname) # put the worker to work async
                r.setCheckState(0, Core.Qt.Checked)
                #w.testresolve(audioclip.name) # put the worker to work async
            if self.showsubclips:
                i = 1
                for range in ranges:
                    frames = len(range)
                    secs = frames / fileref.timebase
                    sr = Gui.QTreeWidgetItem(r, ['', '%s-%i' % (audioname, i),
                                                 '%ss (%sf)' % (secs, frames)])
                    i = i+1


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
        r = rows[0]
        try:
            md = self.audiofiles[r.audioname]
        except AttributeError:
            return
        ss = vars(md)
        ss.update({'secs':md.duration/md.timebase})
        s += """<i>Name:</i><br>%(name)s<br>
                <i>Total length:</i><br>%(secs)ss<br>
                <i>Rate:</i><br>%(timebase)sfps<br>
                """ % ss
        if hasattr(r, 'metadata') and r.metadata.musiclibrary is not None:
            s += """<i>Library</i><br>%s</br>""" % r.metadata.musiclibrary
        self.ui.metadata.setText(s)
        #self.ui.playButton.setEnabled(os.path.exists(r.clip.name))
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

    def auxReport(self):
        s = ""
        for r in [row for row in self.rows.values() if row.checkState(0) == Core.Qt.Checked]:
            if r.metadata.label == 'Sonoton':
                s = s + u"%s x %s \r\n" % (r.metadata.getmusicid(), r.clip['durationsecs'])
        AUXDialog = Gui.QDialog()
        ui = auxreport_ui.Ui_PlingPlongAUXDialog()
        ui.setupUi(AUXDialog)
        ui.webView.load(Core.QUrl('http://auxlicensing.com/Forms/Express%20Rapportering/index.html'))
        ui.webView.loadStarted.connect(lambda: ui.progressBar.show())
        ui.webView.loadFinished.connect(lambda: ui.progressBar.hide())
        def reportloaded(boolean):
            print "report loaded: %s" % boolean
            html = ui.webView.page().mainFrame()
            submit = html.findFirstElement('input[type=submit]')
            submit.setAttribute('style', 'visibility:hidden')
            business = html.findFirstElement('input[name="foretag"]')
            business.setAttribute("value", self.settings.value('AUX/foretag', "NRK").toString())
            contact = html.findFirstElement('input[name=kontakt]')
            contact.setAttribute("value", self.settings.value('AUX/kontakt', "NRK Troms").toString())
            phone = html.findFirstElement('input[name="telefon"]')
            phone.setAttribute("value", self.settings.value('AUX/telefon', "776").toString())
            email = html.findFirstElement('input[name="email"]')
            email.setAttribute("value", self.settings.value('AUX/email', "troms@NRK").toString())
            productionname = html.findFirstElement('input[name="produktionsnamn"]')
            productionname.setAttribute("value", self.settings.value('AUX/produktionsnamn', u"Kråkeklubben").toString())
            check_tv = html.findFirstElement('input[name="checkbox2"]')
            check_tv.setAttribute("checked", "checked")
            text = html.findFirstElement("textarea")
            text.setPlainText(s)
        ui.webView.loadFinished.connect(reportloaded)
        def reportsubmit():
            print "report submitting"
            html = ui.webView.page().mainFrame()
            for el in ['foretag', 'kontakt', 'telefon', 'email', 'produktionsnamn']:
                htmlel = html.findFirstElement('input[name=%s]' % el)
                val = htmlel.evaluateJavaScript("this.value").toString()
                if len(val) == 0:
                    self.showstatus('"%s" cannot be blank' % el.title(), msgtype=StatusBox.ERROR)
                    return None
                self.settings.setValue('AUX/%s' % el, val)
            submit = html.findFirstElement('input[type=submit]')
            submit.setAttribute('style', 'visibility:show')
            #submit.evaluateJavaScript('this.click()')
            #return AUXDialog.accept()
        ui.buttonBox.accepted.connect(reportsubmit)
        return AUXDialog.exec_()

    def creditsToClipboard(self):
        s = ""
        for r in [row for row in self.rows.values() if row.checkState(0) == Core.Qt.Checked]:
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
        self.gluon.worker.reported.connect(self.gluonFinished)
        self.gluon.worker.reported.connect(self.removeLoadingbar)
        self.gluon.worker.error.connect(self.removeLoadingbar)
        self.gluon.worker.error.connect(self.msg)
        checked = list([r for r in self.rows.values() if r.checkState(0) == Core.Qt.Checked])
        self.gluon.resolve(prodno, checked)

    def gluonFinished(self, trackname, metadata):
        print "gluonFinished: %s -> %s" % (trackname, metadata)
        for nom, row in self.gluon.currentList:
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
                # also try to see if xmemliter accepts it?
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
