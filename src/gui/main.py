#!/usr/bin/env python
#-*- encoding: utf8 -*-
# This file is part of odometer by Håvard Gulldahl <havard.gulldahl@nrk.no>
# (C) 2011

import sys, os.path
import time
import datetime
import urllib
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
import prfreport_ui

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
        self.autoclosetimeout = 1000
        self.setWindowFlags(Core.Qt.Popup)
        if msgtype in (None, self.INFO):
            bgcolor = '#ffff7f'
        elif msgtype == self.WARNING:
            bgcolor = 'blue'#'#ffff7f'
        elif msgtype == self.ERROR:
            bgcolor = 'red'#'#ffff7f'
            self.autoclosetimeout = 3000

        self.setStyleSheet(u'QWidget { background-color: %s; }' % bgcolor)
        layout = Gui.QVBoxLayout(self)
        s = Gui.QLabel(msg, self)
        layout.addWidget(s)

    def show_(self):
        if self.autoclose == True:
            Core.QTimer.singleShot(self.autoclosetimeout, self.close)
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

def readResourceFile(qrcPath):
    """Read qrc file and return QString.

    'qrcPath' is ':/path/name', for example ':/txt/about.html'
    """
    f = Core.QFile(qrcPath)
    if not f.open(Core.QIODevice.ReadOnly | Core.QIODevice.Text):
        raise IOError(u"Could not read resource '%s'" % qrcPath)
    t = Core.QTextStream(f)
    t.setCodec("UTF-8")
    s = Core.QString(t.readAll())
    f.close()
    return s

class Odometer(Gui.QMainWindow):
    msg = Core.pyqtSignal(unicode, name="msg")
    loaded = Core.pyqtSignal()
    metadataLoaded = Core.pyqtSignal('QTreeWidgetItem')

    def __init__(self, app, xmemlfile=None, volume=0.01, language='no', parent=None):
        super(Odometer, self).__init__(parent)
        self.app = app
        self.audioclips = {}
        self.workers = []
        self.rows = {}
        self.metadataloaded = 0
        self.statusboxes = []
        self.showsubclips = True
        self.translator = None
        self.settings = Core.QSettings('nrk.no', 'Pling Plong Odometer')
        self.volumethreshold = xmemliter.Volume(gain=volume)
        self.xmemlfile = xmemlfile
        self.xmemlthread = XmemlWorker()
        self.xmemlthread.loaded.connect(self.load)
    	self.ui = odometer_ui.Ui_MainWindow()
        self.setLanguage(language)
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
        #self.ui.DMAButton.clicked.connect(self.gluon)
        self.ui.DMAButton.clicked.connect(self.prfReport)
        self.ui.DMAButton.setEnabled(True)
        self.ui.AUXButton.clicked.connect(self.auxReport)
        self.ui.creditsButton.clicked.connect(self.credits)
        self.ui.clips.itemSelectionChanged.connect(lambda: self.hilited(self.ui.clips.selectedItems()))
        self.ui.clips.itemActivated.connect(self.showMetadata)
        self.ui.clips.itemDoubleClicked.connect(self.editDuration) # manually override duration column
        self.ui.volumeThreshold.valueChanged.connect(lambda i: self.computeAudibleDuration(xmemliter.Volume(gain=float(i))))
        self.ui.actionAbout_Odometer.triggered.connect(self.showAbout)
        self.ui.actionHelp.triggered.connect(self.showHelp)
        self.ui.actionLicenses.triggered.connect(self.showLicenses)
        self.ui.actionCheck_for_updates.triggered.connect(self.showCheckForUpdates)
        #self.ui.actionConfig.triggered.connect(lambda: self.showstatus("About Config"))
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
        self.showerror("This does not seem to be a valid FCP XML file. Sorry.")
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
        if hasattr(self, '_laststatusmsg') and msg == self._laststatusmsg: 
            return None
        b = StatusBox(msg, autoclose=autoclose, msgtype=msgtype, parent=self)
        self.statusboxes.append(b)
        b.show_()
        self._laststatusmsg = msg
        return b

    def showerror(self, msg):
        "Show error message"
        return self.showstatus(msg, msgtype=StatusBox.ERROR)

    def closestatusboxes(self):
        for b in self.statusboxes:
            b.close()

    def showAbout(self):
        _aboutText = readResourceFile(':/txt/about')
        if sys.platform == 'darwin':
            _version = readResourceFile(':/txt/version_mac')
        elif sys.platform == 'win32':
            _version = readResourceFile(':/txt/version_win')
        else: # unknown platform
            _version = ''
        _aboutbox = Gui.QMessageBox.about(self, u'About Odometer', _aboutText.replace(u'✪', _version))

    def showHelp(self):
        HelpDialog = Gui.QDialog()
        ui = prfreport_ui.Ui_PlingPlongPRFDialog()
        ui.setupUi(HelpDialog)
        _helpText = readResourceFile(':/txt/help_no')
        ui.textBrowser.setHtml(_helpText)
        HelpDialog.setWindowTitle('Help')
        return HelpDialog.exec_()

    def showLicenses(self):
        _licenseText = readResourceFile(':/txt/license')
        _box = Gui.QMessageBox(self)
        _box.setText(u'This project is free software')
        _box.setInformativeText('You may use and redistribute it according to the GPL license, version 3')
        _box.setDetailedText(_licenseText)
        return _box.exec_()

    def showCheckForUpdates(self):
        _dropboxUrl = unicode(readResourceFile(':/txt/dropbox_url'))
        if sys.platform == 'darwin':
            _platform = 'mac'
        else:
            _platform = 'win'
        _versionFile = urllib.urlopen('%s/odometerversion_%s.txt' % (_dropboxUrl, _platform)).read()
        _ver, _url = _versionFile.split('|')
        def _date(s):
            return datetime.datetime.strptime(s.strip(), "%Y-%m-%d").date()
        _currentVersion = _date(unicode(readResourceFile(':/txt/version_%s' % _platform)))
        _onlineVersion = _date(_ver)
        if _currentVersion < _onlineVersion:
            # out of date
            _box = Gui.QMessageBox.warning(self, 'Oooooo!', 'Odometer is out of date. \nGet the new version: %s' % _url)
        else:
            _box = Gui.QMessageBox.information(self, 'Relax', 'Odometer is up to date')

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
        self.audioclips, self.audiofiles = xmemlparser.audibleranges(self.volumethreshold)
        self.ui.volumeInfo.setText("<i>(above %i dB)</i>" % self.volumethreshold.decibel)
        self.xmemlparser = xmemlparser
        numclips = len(self.audioclips.keys())
        self.ui.creditsButton.setEnabled(numclips > 0)
        self.msg.emit(self.tr(u"%i audio clips loaded from xmeml sequence \u00ab%s\u00bb." % (numclips, xmemlparser.name)))
        self.loaded.emit()

    def computeAudibleDuration(self, volume=None):
        if isinstance(volume, xmemliter.Volume):
            self.audioclips, self.audiofiles = self.xmemlparser.audibleranges(volume)
            self.ui.volumeInfo.setText("<i>(above %i dB)</i>" % volume.decibel)
        self.ui.clips.clear()
        self.rows = {}
        for audioname, ranges in self.audioclips.iteritems():
            frames = len(ranges)
            if frames == 0:
                continue
            #print "======= %s: %s -> %s======= " % (audioname, ranges.r, frames)
            fileref = self.audiofiles[audioname]
            secs = frames / fileref.timebase
            r = Gui.QTreeWidgetItem(self.ui.clips, ['', audioname, 
                                                    '%ss (%sf)' % (secs, frames)])
            r.metadata = metadata.TrackMetadata(filename=audioname)
            r.audioname = audioname
            r.clip = {'durationsecs':secs, 'durationframes':frames}
            r.subclips = []
            self.rows[audioname] = r
            w = metadata.findResolver(audioname)
            r.setCheckState(0, Core.Qt.Unchecked)
            if w:
                w.trackResolved.connect(self.loadMetadata) # connect the 'resolved' signal
                w.trackResolved.connect(self.trackCompleted) # connect the 'resolved' signal
                w.trackProgress.connect(self.showProgress) 
                #w.trackFailed.connect( ... ?
                w.error.connect(self.showerror) 
                self.workers.append(w) # keep track of the worker
                w.resolve(audioname) # put the worker to work async
                r.setCheckState(0, Core.Qt.Checked)
                #w.testresolve(audioclip.name) # put the worker to work async
            if self.showsubclips:
                i = 1
                for range in ranges:
                    frames = len(range)
                    secs = frames / fileref.timebase
                    r.subclips.append( {'durationsecs':secs, 'durationframes':frames} )
                    sr = Gui.QTreeWidgetItem(r, ['', '%s-%i' % (audioname, i),
                                                 '%ss (%sf)' % (secs, frames),
                                                 u'%sf\u2013%sf' % (range.start, range.end)
                                                ]
                                            )
                    i = i+1


    def loadMetadata(self, filename, metadata):
        row = self.rows[unicode(filename)]
        row.metadata = metadata
        if metadata.productionmusic:
            if metadata.title is None and metadata.label is None:
                txt = "Incomplete metadata. Please update manually"
            else:
                txt = u"\u00ab%(title)s\u00bb \u2117 %(label)s"
        else:
            if metadata.title is None and metadata.artist is None:
                txt = "Incomplete metadata. Please update manually"
            else:
                txt = u"%(artist)s: \u00ab%(title)s\u00bb \u2117 %(label)s %(year)s" 
        row.setText(3, txt % vars(metadata))
        if metadata.musiclibrary in("Sonoton", 'AUX Publishing'):
            self.ui.AUXButton.setEnabled(True)
        self.metadataLoaded.emit(row)

    def trackCompleted(self, filename, metadata):
        #print "got metadata (%s): %s" % (filename, metadata)
        self.metadataloaded += 1
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
            self.ui.clipTitle.setText(row.metadata.title or 'Unknown')
            self.ui.clipAlbum.setText(row.metadata.albumname or 'Unknown')
            self.ui.clipArtist.setText(row.metadata.artist or 'Unknown')
            self.ui.clipComposer.setText(row.metadata.composer or 'Unknown')
            self.ui.clipLyricist.setText(row.metadata.lyricist or 'Unknown')
            self.ui.clipYear.setText(unicode(row.metadata.year or 0))
            self.ui.clipRecordnumber.setText(row.metadata.recordnumber or 'Unknown')
            self.ui.clipCopyright.setText(row.metadata.copyright or 'Unknown')
            self.ui.clipLabel.setText(row.metadata.label or 'Unknown')
            self.ui.detailsBox.show()
        except AttributeError, (e):
            print e
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

    def itercheckedrows(self):
        for row in self.rows.values():
            #print row
            if row.checkState(0) == Core.Qt.Checked: 
                yield row


    def prfReport(self):
        PRFDialog = Gui.QDialog()
        ui = prfreport_ui.Ui_PlingPlongPRFDialog()
        ui.setupUi(PRFDialog)
        s = ""
        for r in self.itercheckedrows():
            s += u"""<dl>
            <dt>Title:</dt><dd>%(title)s</dd>
            <dt>Artist:</dt><dd>%(artist)s</dd>
            <dt>Album name:</dt><dd>%(albumname)s</dd>
            <dt>Lyricist:</dt><dd>%(lyricist)s</dd>
            <dt>Composer:</dt><dd>%(composer)s</dd>
            <dt>Label:</dt><dd>%(label)s</dd>
            <dt>Recordnumber:</dt><dd>%(recordnumber)s</dd>
            <dt>Copyright owner:</dt><dd>%(copyright)s</dd>
            <dt>Released year:</dt><dd>%(year)s</dd>
            </dl>""" % vars(r.metadata)
            s += u"<p><b>Seconds in total</b>: %s" % r.clip['durationsecs']
            if len(r.subclips):
                s += ", in these subclips: <ol>"
                for sc in r.subclips:
                    s += "<li>%s</li>" % sc['durationsecs']
                s += "</ol>"
            s += "</p><hr>"
        ui.textBrowser.setHtml(s)
        def _save():
            print "saving report for prf"
            try:
                loc = Gui.QFileDialog.getSaveFileName(PRFDialog, "Save prf report")
                f = open(unicode(loc), "wb")
                f.write(unicode(ui.textBrowser.toHtml()).encode('utf-8'))
                f.close()
                self.showstatus('Prf report saved')
            except IOError, (e):
                self.showerror(e)
        ui.buttonBox.accepted.connect(_save)
        return PRFDialog.exec_()

    def auxReport(self):
        s = ""
        for r in self.itercheckedrows():
            if r.metadata.musiclibrary == "AUX Publishing":
                s = s + u"%s x %s sek \r\n" % (r.metadata.getmusicid(), r.clip['durationsecs'])
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
            productionname.setAttribute("value", self.ui.prodno.text())
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
                    self.showerror('"%s" cannot be blank' % el.title())
                    return None
                self.settings.setValue('AUX/%s' % el, val)
            submit = html.findFirstElement('input[type=submit]')
            submit.setAttribute('style', 'visibility:show')
            #submit.evaluateJavaScript('this.click()')
            #return AUXDialog.accept()
        ui.buttonBox.accepted.connect(reportsubmit)
        return AUXDialog.exec_()

    def credits(self):
        _labels_seen = []
        s = ""
        for r in self.itercheckedrows():
            if r.metadata.productionmusic:
                if not r.metadata.label in _labels_seen:
                    s += u'%(musiclibrary)s\r\n\u2117 %(label)s\r\n\r\n' % vars(r.metadata)
                    _labels_seen.append(r.metadata.label)
            else:
                s += u'%(title)s\r\n%(artist)s\r\n \u2117 %(label)s %(year)s\r\n\r\n' % vars(r.metadata)
        CreditsDialog = Gui.QDialog()
        ui = prfreport_ui.Ui_PlingPlongPRFDialog()
        ui.setupUi(CreditsDialog)
        ui.textBrowser.setText(s)
        def _save():
            print "saving credits"
            try:
                loc = Gui.QFileDialog.getSaveFileName(CreditsDialog, "Save credits")
                f = open(unicode(loc), "wb")
                f.write(unicode(ui.textBrowser.toHtml()).encode('utf-8'))
                f.close()
                self.showstatus('End credits saved')
            except IOError, (e):
                self.showerror(e)
        ui.buttonBox.accepted.connect(_save)
        CreditsDialog.setWindowTitle('Credits')
        return CreditsDialog.exec_()

    def editDuration(self, row, col): # called when double clicked
        "Replace duration column with a spinbox to manually change value"
        #print "editDuration:", row, col
        if col != 2: 
            return False
        editor = Gui.QDoubleSpinBox(parent=self.ui.clips)
        editor.setMaximum(10000.0)
        editor.setValue(row.clip['durationsecs'])
        editor.setSuffix('s')
        def editingFinished():
            val = float(editor.value())
            row.clip['durationsecs'] = val
            self.ui.clips.removeItemWidget(row, col)
            row.setText(2, unicode(val)+'s')
        editor.editingFinished.connect(editingFinished)
        self.ui.clips.setItemWidget(row, col, editor)

    def checkUsage(self):
        "To be reimplemented whenever there usage agreements change"
        return True # TODO: check FONO status, calculate Apollo pricing
            
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
        self.show()
        if self.xmemlfile is not None: # program was started with an xmeml file as argument
            self.loadxml(self.xmemlfile)
        sys.exit(app.exec_())

    def setLanguage(self, language):
        if self.translator is not None:
            self.app.removeTranslator(self.translator)
        else:
            self.translator = Core.QTranslator(self.app)
        print "loading translation: odometer_%s" % language
        print self.translator.load(':data/translation_%s' % language)
        self.app.installTranslator(self.translator)
        #self.ui.retranslateUi(self)

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
    if f is not None: o = Odometer(app, f)
    else: o = Odometer(app)
    o.run(app)

if __name__ == '__main__':
    rungui(sys.argv)
