#!/usr/bin/env python
#-*- encoding: utf8 -*-
# This file is part of odometer by Håvard Gulldahl <havard.gulldahl@nrk.no>
# (C) 2011-2014

import sys, os, os.path
import time
import datetime
import urllib, urllib2
import json
import StringIO
import ConfigParser
import logging
import traceback
try:
    import cPickle as pickle
except ImportError:
    import pickle
import PyQt4.QtGui as Gui
import PyQt4.QtCore as Core
import PyQt4.QtSvg as Svg
import PyQt4.Qt as Qt

from xmeml import iter as xmemliter
import metadata
import odometer_ui
import odometer_rc 
import auxreport_ui
import prfreport_ui
import onlinelogin_ui

try:
    from gui import audioplayer
    USE_AUDIOPLAYER=True
except ImportError:
    USE_AUDIOPLAYER=False

class UrlWorker(Core.QThread):
    finished = Core.pyqtSignal(object)
    failed = Core.pyqtSignal(tuple)

    def __init__(self, parent=None):
        super(UrlWorker, self).__init__(parent)
        self.exiting = False

    def __del__(self):
        self.exiting = True
        self.wait()

    def load(self, url, timeout=10, data=None):
        self.url = url
        self.timeout = timeout
        self.data = data is not None and urllib.urlencode(data) or None
        self.start()

    def run(self):
        logging.info('urlworker working on url %s with data %s', self.url, self.data)
        try:
            con = urllib2.urlopen(self.url, self.data, timeout=self.timeout)
            self.finished.emit(con)
        except Exception as e:
            logging.exception(e)
            self.failed.emit(tuple(sys.exc_info()))

class XmemlWorker(Core.QThread):
    loaded = Core.pyqtSignal(xmemliter.XmemlParser, name="loaded")
    failed = Core.pyqtSignal(BaseException)

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
        try:
            xmeml = xmemliter.XmemlParser(self.xmemlfile)
            self.loaded.emit(xmeml)
        except BaseException as e:
            #logging.debug("beep"
            self.failed.emit(e)

class StatusBox(Gui.QWidget):
    INFO = 1
    WARNING = 2
    ERROR = 3

    class Emitter(Core.QObject):

        closing = Core.pyqtSignal()
        def __init__(self):
            super(StatusBox.Emitter, self).__init__()


    def __init__(self, msg, autoclose=True, msgtype=None, parent=None):
        """autoclose may be a boolean (True == autoclose) or a signal that we
        connect our close() method to"""
        super(StatusBox, self).__init__(parent)
        self.emitter = StatusBox.Emitter()
        self.parent = parent
        self.autoclose = autoclose
        self.stopped = False
        self.timer = Core.QTimer(parent=self)
        self.timer.timeout.connect(self.close)
        self.timer.timeout.connect(self.timer.stop)
        self.anim = Core.QPropertyAnimation(self, "windowOpacity", self.parent)
        self.anim.finished.connect(self.delete_)
        self.setWindowFlags(Core.Qt.Popup)
        self.setup(msgtype)
        layout = Gui.QVBoxLayout(self)
        self.s = Gui.QLabel(msg, self)
        layout.addWidget(self.s)

    def setup(self, msgtype):
        self.autoclosetimeout = msgtype==self.ERROR and 3000 or 1000
        if msgtype in (None, self.INFO):
            bgcolor = '#ffff7f'
        elif msgtype == self.WARNING:
            bgcolor = 'blue'#'#ffff7f'
        elif msgtype == self.ERROR:
            bgcolor = 'red'#'#ffff7f'

        self.setStyleSheet(u'QWidget { background-color: %s; }' % bgcolor)

    def show_(self):
        if self.autoclose == True:
            self.timer.start(self.autoclosetimeout)
        elif hasattr(self.autoclose, 'connect'): # it's a qt/pyqt signal
            self.autoclose.connect(self.close)
        self.show()

    def delete_(self):
        self.hide()
        self.emitter.closing.emit()
        self.deleteLater()

    def close(self):
        self.stopped = True
        self.anim.setDuration(1000)
        self.anim.setStartValue(1.0)
        self.anim.setEndValue(0.0)
        self.anim.start()

    def addMessage(self, s, msgtype):
        self.setup(msgtype)
        try:
            self.anim.stop()
        except AttributeError:#close animation does not exist because close() was never run
            pass 
        self.timer.start(self.autoclosetimeout)
        self.s.setText(unicode(self.s.text()) + "<br>" + s)

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

def readBuildflags():
    "Read build flags from builtin resource file"
    cp = ConfigParser.ConfigParser()
    cp.readfp(StringIO.StringIO(unicode(readResourceFile(':/data/buildflags'))))
    return cp
    
class Odometer(Gui.QMainWindow):
    msg = Core.pyqtSignal(unicode, name="msg")
    loaded = Core.pyqtSignal()
    metadataLoaded = Core.pyqtSignal('QTreeWidgetItem')

    def __init__(self, app, xmemlfile=None, volume=0.01, language='no', parent=None):
        super(Odometer, self).__init__(parent)
        self.log = []
        self.app = app
        self.audioclips = {}
        self.workers = []
        self.rows = {}
        self.AUXRepertoire = {}
        self.metadataloaded = 0
        self.statusboxes = []
        self.showsubclips = True
        self.translator = None
        self.translatorQt = None
        self.buildflags = readBuildflags()
        self.settings = Core.QSettings('nrk.no', 'Pling Plong Odometer')
        self.volumethreshold = xmemliter.Volume(gain=volume)
        self.xmemlfile = xmemlfile
        self.xmemlthread = XmemlWorker()
        self.xmemlthread.loaded.connect(self.load)
        self.xmemlthread.failed.connect(self.showException)
    	self.ui = odometer_ui.Ui_MainWindow()
        self.setLanguage(language)
        self.ui.setupUi(self)
        self.ui.detailsBox.hide()
        self.ui.errors.hide()
        self.ui.volumeThreshold.setValue(self.volumethreshold.gain)
        if self.buildflags.getboolean('ui', 'editbutton'):
            self.ui.editMetadataButton = self.ui.buttonBox.addButton(self.tr('Edit'), Gui.QDialogButtonBox.ActionRole)
            self.ui.editMetadataButton.clicked.connect(self.editMetadata)
        if self.buildflags.getboolean('ui', 'manuallookupbutton'):
            self.ui.resolveManualButton = self.ui.buttonBox.addButton(self.tr('Manual lookup'), Gui.QDialogButtonBox.ActionRole)
            self.ui.resolveManualButton.clicked.connect(self.manualResolve)
        self.ui.buttonBox.rejected.connect(lambda: self.ui.detailsBox.hide())
        self.ui.loadFileButton.clicked.connect(self.clicked)
        #self.ui.DMAButton.clicked.connect(self.gluon)
        self.ui.DMAButton.clicked.connect(self.prfReport)
        self.ui.DMAButton.setEnabled(True)
        self.ui.AUXButton.clicked.connect(self.auxReport)
        self.ui.creditsButton.clicked.connect(self.credits)
        self.ui.errorButton.clicked.connect(self.reportError)
        self.ui.clips.itemSelectionChanged.connect(lambda: self.hilited(self.ui.clips.selectedItems()))
        self.ui.clips.itemActivated.connect(self.showMetadata)
        self.ui.clips.itemDoubleClicked.connect(self.editDuration) # manually override duration column
        self.ui.volumeThreshold.valueChanged.connect(lambda i: self.computeAudibleDuration(xmemliter.Volume(gain=float(i))))
        self.ui.actionAbout_Odometer.triggered.connect(self.showAbout)
        self.ui.actionHelp.triggered.connect(self.showHelp)
        self.ui.actionLicenses.triggered.connect(self.showLicenses)
        self.ui.actionLogs.triggered.connect(self.showLogs)
        self.ui.actionCheck_for_updates.triggered.connect(self.showCheckForUpdates)
        self.ui.actionShowPatterns.triggered.connect(self.showShowPatterns)
        self.ui.actionLoginOnline.triggered.connect(self.showLoginOnline)
        #self.ui.actionConfig.triggered.connect(lambda: self.showstatus("About Config"))
        self.msg.connect(self.showstatus)
        self.loaded.connect(self.computeAudibleDuration)
        self.ui.dropIcon = Svg.QSvgWidget(':/gfx/graystar', self.ui.clips)
        self.ui.dropIcon.setMinimumSize(200,200)
        self.ui.dropIcon.setToolTip(self.tr('Drop your xml file here'))
        if not (USE_AUDIOPLAYER and self.buildflags.getboolean('ui', 'playbutton')):
            self.ui.playButton.hide()
        if not self.buildflags.getboolean('release', 'releasecheck'):
            self.ui.actionCheck_for_updates.setEnabled(False)
        if not self.buildflags.getboolean('ui', 'volumeThreshold'):
            self.ui.volumeThreshold.hide()
            self.ui.volumeInfo.hide()
        if not self.buildflags.getboolean('ui', 'prfbutton'):
            self.ui.DMAButton.hide()
        if not self.buildflags.getboolean('ui', 'auxbutton'):
            self.ui.AUXButton.hide()
        if not self.buildflags.getboolean('ui', 'apollobutton'):
            self.ui.ApolloButton.hide()
        if not self.buildflags.getboolean('ui', 'creditsbutton'):
            self.ui.creditsButton.hide()
        if not self.buildflags.getboolean('ui', 'errorbutton'):
            self.ui.errorButton.hide()

        #self.metadataLoaded.connect(self.checkUsage)
        Core.QTimer.singleShot(5, self.updateAUXRepertoire)

    def keyPressEvent(self, event):
        'React to keyboard keys being pressed'
        if event.key() == Core.Qt.Key_Escape:
            # self.close()
            self.deleteLater()

    def dragEnterEvent(self, event):
        'React to file being dragged inside gui'
        self.ui.dropIcon.load(':/gfx/star')
        return event.accept()

    def dragLeaveEvent(self, event):
        'React to file being dragged outside gui'
        self.ui.dropIcon.load(':/gfx/graystar')
        return event.accept()

    def dragMoveEvent(self, event):
        'React to file being moved over gui'
        if xmemlfileFromEvent(event):
            event.accept()
            return
        self.showerror(self.tr("This does not seem to be a valid FCP XML file. Sorry."))
        event.ignore()

    def dropEvent(self, event):
        'React to file being dropped (if it looks like an xmeml file, load it)'
        event.acceptProposedAction()
        self.ui.dropIcon.load(':/gfx/graystar')
        x = xmemlfileFromEvent(event)
        if x:
            self.loadxml(x)

    def resizeEvent(self, event):
        'React to main gui being resized'
        i = self.ui.dropIcon
        i.move(self.width()/2-i.width(), self.height()*0.75-i.height())

    def logMessage(self, msg, msgtype=StatusBox.INFO):
        'Add a message to the log'
        if msgtype == StatusBox.ERROR:
            color = 'red'
        elif msgtype == StatusBox.INFO:
            color = '#390'
        elif msgtype == StatusBox.WARNING:
            color = 'blue'
        try:
            if isinstance(self.xmemlfile, unicode):
                name = os.path.basename(self.xmemlfile)
            else:
                name = os.path.basename(self.xmemlfile.decode(sys.getfilesystemencoding()))
        except (AttributeError, TypeError):
            name = self.tr('No XMEML loaded')
        self.log.append('<div style="color:%s">[%s - %s]: %s</div>' % (color, 
                                                                       name,
                                                                       datetime.datetime.now().time().isoformat(),
                                                                       msg))

    def logException(self, e):
        'Add an exception to the log'
        if isinstance(e, tuple):
            etype, e, tb = e
        else:
            etype, exc_value, tb = sys.exc_info()
        if hasattr(e, 'msg'):
            msg = e.msg
        elif hasattr(e, 'reason'):
            msg = e.reason
        elif hasattr(e, 'message'):
            msg = e.message
        else:
            msg = unicode(e)
        self.log.append('<div style="color:red">')
        for line in traceback.format_exception(etype, e, tb):
            self.log.append(line)
        self.log.append('</div>')

    def showException(self, e):
        self.logException(e)
        self.showerror(unicode(self.tr('Unexpected error: %s')) % e)
        
    def showstatus(self, msg, autoclose=True, msgtype=StatusBox.INFO):
        'Show floating status box'
        # if you don't autoclose, call self.closestatusboxes()
        # or keep a reference to this box and .close() it yourself

        if hasattr(self, '_laststatusmsg') and msg == self._laststatusmsg: 
            # don't repeat yourself
            return None

        if len(self.statusboxes):
            b = self.statusboxes[-1]
            if not b.stopped: 
                b.addMessage(msg, msgtype)
                return b
            else:
                self.closebox(b)
        if isinstance(msg, Exception): #unwrap exception
            msgtype=StatusBox.ERROR
            msg=unicode(msg)
        b = StatusBox(msg, autoclose=autoclose, msgtype=msgtype, parent=self)
        self.statusboxes.append(b)
        b.emitter.closing.connect(lambda: self.closebox(b))
        b.show_()
        self._laststatusmsg = unicode(msg)
        self.logMessage(msg, msgtype)
        return b

    def showerror(self, msg):
        'Show error message'
        return self.showstatus(msg, msgtype=StatusBox.ERROR)

    def closebox(self, b):
        try:
            self.statusboxes.remove(b)
        except: 
            pass

    def closestatusboxes(self):
        'Close all statusboxes'
        for b in self.statusboxes:
            b.close()
        self.statusboxes = []

    def getVersion(self):
        if sys.platform == 'darwin':
            _version = readResourceFile(':/txt/version_mac')
        elif sys.platform == 'win32':
            _version = readResourceFile(':/txt/version_win')
        else: # unknown platform
            _version = ''
        if self.buildflags.getboolean('release', 'beta'):
            _version = unicode(_version).strip() + ' NEXT'
        logging.debug("got version:  ---%s---", _version)
        return _version

    def showAbout(self):
        'Show "About" text'
        _aboutText = readResourceFile(':/txt/about')
        _aboutbox = Gui.QMessageBox.about(self, u'About Odometer', _aboutText.replace(u'✪', self.getVersion()))

    def showHelp(self):
        'Show help document from online resource'
        HelpDialog = Gui.QDialog()
        ui = auxreport_ui.Ui_PlingPlongAUXDialog()
        ui.setupUi(HelpDialog)
        ui.buttonBox.hide()
        ui.webView.load(Core.QUrl(self.buildflags.get('release', 'helpUrl')))
        ui.webView.loadStarted.connect(lambda: ui.progressBar.show())
        ui.webView.loadFinished.connect(lambda: ui.progressBar.hide())
        def helpdocloaded(success):
            logging.debug("help doc loaded: %s", success)
            # TODO: Add offline fallback 
            if not success:
                self.showerror(self.tr("Could not load help document, sorry. :("))
        ui.webView.loadFinished.connect(helpdocloaded)
        return HelpDialog.exec_()     

    def showLicenses(self):
        'Show a dialog to display licenses and terms'
        _licenseText = readResourceFile(':/txt/license')
        _box = Gui.QMessageBox(self)
        _box.setText(self.tr('This project is free software'))
        _box.setInformativeText(self.tr('You may use and redistribute it according to the GPL license, version 3'))
        _box.setDetailedText(_licenseText)
        return _box.exec_()

    def showCheckForUpdates(self):
        'Check online for updates'
        _dropboxUrl = self.buildflags.get('release', 'dropboxUrl')
        if sys.platform == 'darwin':
            _platform = 'mac'
        else:
            _platform = 'win'
        #try:
            #_versionFile = urllib2.urlopen('%s/odometerversion_%s.txt' % (_dropboxUrl, _platform), timeout=7).read()
        #except Exception as e:
            #self.logException(e)
            #self.showerror(self.tr('Could not look up the most recent version online. Check your internet connection'))
            #return 
        def failed(ex):
            logging.error("faile! %s", ex)
            self.showerror(self.tr('Could not look up the most recent version online. Check your internet connection'))
            self.logException(ex)
        def compare(data):
            _ver, _url = data.read().split('|')
            def _date(s):
                return datetime.datetime.strptime(s.strip(), "%Y-%m-%d").date()
            _currentVersion = _date(unicode(readResourceFile(':/txt/version_%s' % _platform)))
            _onlineVersion = _date(_ver)
            if _currentVersion < _onlineVersion:
                # out of date
                _box = Gui.QMessageBox.warning(self, self.tr('Oooooo!'), unicode(self.tr('Odometer is out of date. \nGet the new version: %s')) % _url)
            else:
                _box = Gui.QMessageBox.information(self, self.tr('Relax'), self.tr('Odometer is up to date'))
        async = UrlWorker()
        _url = '%s/odometerversion_%s.txt' % (_dropboxUrl, _platform)
        async.load(_url, timeout=7)
        async.finished.connect(compare)
        async.failed.connect(failed)

    def showShowPatterns(self):
        'Show a list of recognised Patternes'
        PatternDialog = Gui.QDialog()
        ui = prfreport_ui.Ui_PlingPlongPRFDialog()
        ui.setupUi(PatternDialog)
        ui.buttonBox.removeButton(ui.buttonBox.button(Gui.QDialogButtonBox.Save))
        r = []
        for catalog, patterns in metadata.getResolverPatterns().iteritems():
            r.append('<h1>%s</h1><ul>' % catalog)
            for tok in patterns['prefixes']:
                r.append('<li>%s...</li>' % tok)
            for tok in patterns['postfixes']:
                r.append('<li>...%s</li>' % tok)
            r.append('</ul><hr>')
        ui.textBrowser.setHtml('\n'.join(r))
        PatternDialog.setWindowTitle('Recognised patterns')
        return PatternDialog.exec_()

    def showLogs(self):
        'Pop up a dialog to show internal log'
        LogDialog = Gui.QDialog()
        ui = prfreport_ui.Ui_PlingPlongPRFDialog()
        ui.setupUi(LogDialog)
        ui.textBrowser.setHtml(''.join(self.log))
        LogDialog.setWindowTitle('Help')
        return LogDialog.exec_()

    def showLoginOnline(self):
        'Pop up a dialog to log in to online services like AUX and ApolloMusic'
        LoginDialog = Gui.QDialog()
        ui = onlinelogin_ui.Ui_PlingPlongOnlineDialog()
        ui.setupUi(LoginDialog)
        ui.AUXuser.setText(self.settings.value('AUXuser', '').toString())
        ui.AUXpassword.setText(self.settings.value('AUXpassword', '').toString())
        ui.Apollouser.setText(self.settings.value('Apollouser', '').toString())
        ui.Apollopassword.setText(self.settings.value('Apollopassword', '').toString())
        def storeCookie(service, data):
            logging.debug("Storing cookie for %s: %s", service, data)
            logging.debug("Service returned %s", data.getcode())
            logging.debug("Headers: %s", data.info())
            b = data.read()
            logging.debug("body: %s", b)
            result = json.loads(b)
            login = False
            if service == 'AUX':
                if result['ax_success'] == 1:
                    self.settings.setValue('AUXcookie', data.info()['Set-Cookie'])
                    self.showstatus('Logged in to AUX')
                else:
                    m = '%s login failed: %s' % (service, result['ax_errmsg'])
                    logging.warning(m)
                    self.showerror(m)
            elif service == 'Apollo':
                if result['success'] == 1: 
                    self.settings.setValue('Apollocookie', data.info()['Set-Cookie'])
                    self.showstatus('Logged in to Apollo')
                else:   
                    m = '%s login failed: %s' % (service, result['message'])
                    logging.warning(m)
                    self.showerror(m)
            print list(self.settings.allKeys())
            stopBusy()

                
        def failed(ex):
            logging.warning("faile!", ex)
            self.logException(ex)
            stopBusy()
        def startBusy():
            ui.progressBar.setRange(0,0)
        def stopBusy():
            ui.progressBar.setMaximum(1)
        def AUXlogin():
            logging.info('login to aux')
            self.settings.setValue('AUXuser', ui.AUXuser.text())
            self.settings.setValue('AUXpassword', ui.AUXpassword.text())
            startBusy()
            async = UrlWorker()
            url = 'http://search.auxmp.com//search/html/ajax/axExtData.php'
            getdata = urllib.urlencode({'ac':'login',
                                        'country': 'NO',
                                        'sprache': 'en',
                                        'ext': 1,
                                        '_dc': int(time.time()),
                                        'luser':unicode(ui.AUXuser.text()),
                                        # from javascript source: var lpass = Sonofind.Helper.md5(pass + "~" + Sonofind.AppInstance.SID);

                                        'lpass':unicode(ui.AUXpassword.text())})
            async.load('%s?%s' % (url, getdata), timeout=7)
            async.finished.connect(lambda d: storeCookie('AUX', d))
            async.failed.connect(failed)
        def Apollologin():
            logging.info('login to apollo')
            self.settings.setValue('Apollouser', ui.Apollouser.text())
            self.settings.setValue('Apollopassword', ui.Apollopassword.text())
            startBusy()
            async = UrlWorker()
            url = 'http://www.findthetune.com/online/login/ajax_authentication/'
            postdata = {'user':unicode(ui.Apollouser.text()),
                        'pass':unicode(ui.Apollopassword.text())}
            async.load(url, timeout=7, data=postdata)
            async.finished.connect(lambda d: storeCookie('Apollo', d))
            async.failed.connect(failed)
        ui.AUXlogin.clicked.connect(AUXlogin)
        ui.Apollologin.clicked.connect(Apollologin)
        return LoginDialog.exec_()

    def updateAUXRepertoire(self):
        self.logMessage(self.tr('Updating AUX repertoire'))
        try:
            repertoire = pickle.loads(str(self.settings.value('auxrepertoire', None).toString()))
        except Exception as e:
            self.logException(e)
            repertoire = None
        logging.debug("found repertoire: %s", repertoire)
        def age(dt):
            return (datetime.datetime.now() - dt).days
        if repertoire is not None and age(repertoire['timestamp']) < 7:
            self.logMessage(self.tr('Found fresh AUX repertoire list in cache'))
            self.AUXRepertoire = repertoire
            return

        # get new data online
        self.logMessage(self.tr('AUX repertoire cache is too old, fetch new online'))
        _url = self.buildflags.get('release', 'AUXRepertoireUrl')

        def store(data):
            repertoire = json.loads(data.read())
            logging.debug("got repertoire: %s", repertoire)
            repertoire['timestamp'] = datetime.datetime.now()
            self.settings.setValue('auxrepertoire', pickle.dumps(repertoire))
            self.AUXRepertoire = repertoire
        def failed(ex):
            #logging.debug("faile!", ex
            self.logException(ex)
        async = UrlWorker()
        async.load(_url, timeout=7)
        async.finished.connect(store)
        async.failed.connect(failed)

    def clicked(self, qml):
        'Open file dialog to get xmeml file name'
        lastdir = self.settings.value('lastdir', '').toString()
        xf = Gui.QFileDialog.getOpenFileName(self,
            self.tr('Open an xmeml file (FCP export)'),
            lastdir,
            self.tr('Xmeml files (*.xml)'))
        self.xmemlfile = unicode(xf)
        if not os.path.exists(self.xmemlfile):
            return False
        self.settings.setValue('lastdir', os.path.dirname(self.xmemlfile))
        self.loadxml(self.xmemlfile)

    def loadxml(self, xmemlfile):
        'Start loading xmeml file, start xmeml parser'
        if isinstance(xmemlfile, unicode):
            unicxmemlfile = xmemlfile
        else:
            unicxmemlfile = xmemlfile.decode(sys.getfilesystemencoding())
        msgbox = self.showstatus(unicode(self.tr("Loading %s...")) % unicxmemlfile, autoclose=self.loaded)
        self.loadingbar()
        self.loaded.connect(self.removeLoadingbar)
        self.xmemlthread.failed.connect(self.removeLoadingbar)
        self.loaded.connect(lambda: self.ui.fileInfo.setText(unicode(self.tr("<b>Loaded:</b> %s")) % os.path.basename(unicxmemlfile)))
        self.loaded.connect(lambda: self.ui.fileInfo.setToolTip(os.path.abspath(unicxmemlfile)))
        try:
	    self.xmemlthread.load(xmemlfile)
        except Exception:
            self.removeLoadingbar()
            raise 

    def loadingbar(self):
        'Add global progress bar'
        self.ui.progress = Gui.QProgressBar(self)
        self.ui.progress.setMinimum(0)
        self.ui.progress.setMaximum(0) # don't show progress, only "busy" indicator
        self.ui.statusbar.addWidget(self.ui.progress, 100)

    def removeLoadingbar(self):
        'Remove global progress bar'
        self.ui.statusbar.removeWidget(self.ui.progress)
        self.ui.progress.deleteLater()

    def load(self, xmemlparser):
        'Load audio clips from xmeml parser into the gui'
        try:
            self.audioclips, self.audiofiles = xmemlparser.audibleranges(self.volumethreshold)
        except Exception as e:
            self.removeLoadingbar()
            self.logException(e)
            return False

        self.ui.volumeInfo.setText(unicode(self.tr("<i>(above %i dB)</i>")) % self.volumethreshold.decibel)
        self.xmemlparser = xmemlparser
        numclips = len(self.audioclips.keys())
        self.ui.creditsButton.setEnabled(numclips > 0)
        self.msg.emit(unicode(self.tr(u"%i audio clips loaded from xmeml sequence \u00ab%s\u00bb.")) % (numclips, xmemlparser.name))
        self.loaded.emit()

    def computeAudibleDuration(self, volume=None):
        'Loop through all audio clips and start the metadata workers'
        if isinstance(volume, xmemliter.Volume):
            self.audioclips, self.audiofiles = self.xmemlparser.audibleranges(volume)
            self.ui.volumeInfo.setText(unicode(self.tr("<i>(above %i dB)</i>")) % volume.decibel)
        self.ui.clips.clear()
        self.rows = {}
        for audioname, ranges in self.audioclips.iteritems():
            frames = len(ranges)
            if frames == 0:
                continue
            logging.debug("======= %s: %s -> %s======= ", audioname, ranges.r, frames)
            fileref = self.audiofiles[audioname] # might be None, if clip is offline
            secs = ranges.seconds()
            r = Gui.QTreeWidgetItem(self.ui.clips, ['', audioname, 
                                                    '%ss (%sf)' % (secs, frames)])
            r.metadata = metadata.TrackMetadata(filename=audioname)
            r.audioname = audioname
            r.clip = {'durationsecs':secs, 'durationframes':frames}
            r.subclips = []
            self.rows[audioname] = r
            w = metadata.findResolver(audioname)
            logging.debug("w: %s -> %s",audioname.encode('utf-8'), w)
            r.setCheckState(0, Core.Qt.Unchecked)
            if w:
                if isinstance(w, metadata.AUXResolver): 
                    w.updateRepertoire(self.AUXRepertoire) # make sure repertoire is current
                elif isinstance(w, metadata.ApollomusicResolver):
                    logincookie = unicode(self.settings.value('Apollocookie', '').toString())
                    if not logincookie: # not logged in to apollo, big problem
                        self.showerror(self.tr(u'Track from Apollo Music detected. Please log in to the service'))
                        self.logMessage(self.tr(u'No logincookie from apollo music found.'), msgtype=StatusBox.WARNING)
                        continue # go to next track
                    else:
                        w.setlogincookie(logincookie)
                w.trackResolved.connect(self.loadMetadata) # connect the 'resolved' signal
                w.trackResolved.connect(self.trackCompleted) # connect the 'resolved' signal
                w.trackProgress.connect(self.showProgress) 
                #w.trackFailed.connect(lambda x: r.setCheckState(0, Core.Qt.Unchecked))
                w.error.connect(self.showerror) 
                w.warning.connect(lambda s: self.logMessage(s, msgtype=StatusBox.WARNING))
                self.workers.append(w) # keep track of the worker
                w.resolve(audioname, fileref.pathurl) # put the worker to work async. NOTE: pathurl will be None on offilne files
            if self.showsubclips:
                i = 1
                for range in ranges:
                    frames = len(range)
                    secs = float(frames) / ranges.framerate
                    r.subclips.append( {'durationsecs':secs, 'durationframes':frames} )
                    sr = Gui.QTreeWidgetItem(r, ['', '%s-%i' % (audioname, i),
                                                 '%ss (%sf)' % (secs, frames),
                                                 u'%sf\u2013%sf' % (range.start, range.end)
                                                ]
                                            )
                    i = i+1


    def loadMetadata(self, filename, metadata):
        'Handle metadata for a specific clip'
        row = self.rows[unicode(filename)]
        logging.debug("loadMetadata: %s - %s", filename, metadata)
        row.metadata = metadata
        if metadata.productionmusic:
            if metadata.title is None and metadata.label is None:
                txt = self.tr("Incomplete metadata. Please update manually")
            else:
                txt = u"\u00ab%(title)s\u00bb \u2117 %(label)s"
        else:
            if metadata.title is None and metadata.artist is None:
                txt = self.tr("Incomplete metadata. Please update manually")
            else:
                txt = u"%(artist)s: \u00ab%(title)s\u00bb \u2117 %(label)s %(year)s" 
        row.setText(3, txt % vars(metadata))
        if metadata.musiclibrary in("Sonoton", 'AUX Publishing'):
            self.ui.AUXButton.setEnabled(True)
        self.metadataLoaded.emit(row)

    def trackCompleted(self, filename, metadata):
        'React to metadata finished loading for a specific clip'
        logging.debug("got metadata (%s): %s", filename, metadata)
        self.rows[unicode(filename)].setCheckState(0, Core.Qt.Checked)
        self.metadataloaded += 1
        if len(self.audioclips)  == self.metadataloaded:
            self.ui.DMAButton.setEnabled(True)

    def showProgress(self, filename, progress):
        'Show progress bar for a specific clip, e.g. when metadata is loading'
        logging.debug("got progress for %s: %s", filename, progress)
        row = self.rows[unicode(filename)]
        if progress < 100: # not yet reached 100%
            p = Gui.QProgressBar(parent=self.ui.clips)
            p.setValue(progress)
            self.ui.clips.setItemWidget(row, 3, p)
        else: # finishd, show some text instead
            self.ui.clips.removeItemWidget(row, 3)

    def hilited(self, rows):
        'React to rows being highlighted. E.g. show some info in a sidebar'
        self.ui.metadata.setText('')
        if not len(rows): return
        s = "<b>%s:</b><br>" % self.tr('Metadata')
        r = rows[0]
        try:
            md = self.audiofiles[r.audioname]
        except AttributeError:
            return
        ss = vars(md)
        ss.update({'secs':md.duration/25}) # TODO: FIXME: Dont hardcode framerate
        s += unicode(self.tr("""<i>Name:</i><br>%(name)s<br>
                <i>Total length:</i><br>%(secs)ss<br>
                <i>Rate:</i><br>%(timebase)sfps<br>
                """)) % ss
        if hasattr(r, 'metadata') and r.metadata.musiclibrary is not None:
            s += unicode(self.tr("<i>Library</i><br>%s<br>")) % r.metadata.musiclibrary
        self.ui.metadata.setText(s)
        #self.ui.playButton.setEnabled(os.path.exists(r.clip.name))
        if self.ui.detailsBox.isVisible(): # currently editing metadata
            self.showMetadata(r)

    def showMetadata(self, row, col=None):
        'Show a list of all (most) known metadata'
        try:
            self.ui.detailsBox.currentRow = row
            self.ui.clipTitle.setText(row.metadata.title or self.tr('Unknown'))
            self.ui.clipAlbum.setText(row.metadata.albumname or self.tr('Unknown'))
            _a = row.metadata.artist if row.metadata.artist != '(N/A for production music)' else None
            self.ui.clipArtist.setText(_a or self.tr('Unknown'))
            self.ui.clipComposer.setText(row.metadata.composer or self.tr('Unknown'))
            self.ui.clipLyricist.setText(row.metadata.lyricist or self.tr('Unknown'))
            self.ui.clipRecordnumber.setText(row.metadata.recordnumber or self.tr('Unknown'))
            _c = row.metadata.copyright if row.metadata.copyright != '(This information requires login)' else None
            self.ui.clipCopyright.setText(_c or self.tr('Unknown'))
            self.ui.clipLabel.setText(row.metadata.label or self.tr('Unknown'))
            _y = row.metadata.year if row.metadata.year != -1 else None
            self.ui.clipYear.setText(unicode(row.metadata.year or 0))
            self.ui.detailsBox.show()
        except AttributeError, (e):
            self.logException(e)
            self.ui.detailsBox.hide()
        self.ui.resolveManualButton.setEnabled(row.metadata.title is None)

    def editMetadata(self):
        'Show fields to edit metadata for a specific track'
        detailsLayout = self.ui.detailsBox.layout()
        def editable(widget):
            def close(editWidget, labelWidget, r, c):
                labelWidget.setText(editWidget.text())
                i = detailsLayout.indexOf(editWidget)
                detailsLayout.takeAt(i)
                editWidget.deleteLater()
                detailsLayout.addWidget(labelWidget, r, c)
                labelWidget.show()
            index = detailsLayout.indexOf(widget)
            row, column, cols, rows = detailsLayout.getItemPosition(index)
            logging.debug("poss: %s %s %s %s %s ",index, row, column, cols, rows)
            text = widget.text()
            widget.hide()
            detailsLayout.takeAt(index)
            _edit = Gui.QLineEdit(text, self.ui.detailsBox)
            detailsLayout.addWidget(_edit, row, column)
            _edit.editingFinished.connect(lambda: close(_edit, widget, row, column))
        for x in (self.ui.clipTitle,
                  self.ui.clipAlbum,
                  self.ui.clipArtist,
                  self.ui.clipComposer,
                  self.ui.clipLyricist,
                  # self.ui.clipYear,
                  self.ui.clipRecordnumber,
                  self.ui.clipCopyright,
                  self.ui.clipLabel):
            editable(x)
        
    def itercheckedrows(self):
        'iterate through rows that are checked'
        for row in self.rows.values():
            #logging.debug(row
            if row.checkState(0) == Core.Qt.Checked: 
                yield row

    def prfReport(self):
        PRFDialog = Gui.QDialog()
        ui = prfreport_ui.Ui_PlingPlongPRFDialog()
        ui.setupUi(PRFDialog)
        s = unicode(self.tr('<h1>Track metadata sheet for PRF</h1>'))
        for r in self.itercheckedrows():
            _t = r.metadata.title if r.metadata.title else repr(r.audioname)
            s += unicode(self.tr('<div><dt>Title:</dt><dd>%s</dd>')) % _t
            if r.metadata.artist not in (None, u'(N/A for production music)'):
                s += unicode(self.tr('<dt>Artist:</dt><dd>%s</dd>')) % r.metadata.artist
            if r.metadata.albumname is not None:
                s += unicode(self.tr('<dt>Album name:</dt><dd>%s</dd>')) % r.metadata.albumname
            if r.metadata.lyricist is not None:
                s += unicode(self.tr('<dt>Lyricist:</dt><dd>%s</dd>')) % r.metadata.lyricist
            if r.metadata.composer is not None:
                s += unicode(self.tr('<dt>Composer:</dt><dd>%s</dd>')) % r.metadata.composer
            if r.metadata.label is not None:
                s += unicode(self.tr('<dt>Label:</dt><dd>%s</dd>')) % r.metadata.label
            if r.metadata.recordnumber is not None:
                s += unicode(self.tr('<dt>Recordnumber:</dt><dd>%s</dd>')) % r.metadata.recordnumber
            if r.metadata.copyright is not None and r.metadata.copyright != u'(This information requires login)':
                s += unicode(self.tr('<dt>Copyright owner:</dt><dd>%s</dd>')) % r.metadata.copyright
            if r.metadata.year != -1:
                s += unicode(self.tr('<dt>Released year:</dt><dd>%s</dd>')) % r.metadata.year

            s += "<p><b>" + unicode(self.tr(u"Seconds in total</b>: %s")) % r.clip['durationsecs']
            if len(r.subclips):
                s += unicode(self.tr(", in these subclips:")) + "<ol>"
                for sc in r.subclips:
                    s += "<li>%s</li>" % sc['durationsecs']
                s += "</ol>"
            s += "</p></div><hr>"
        ui.textBrowser.setHtml(s)
        def _save():
            logging.debug("saving report for prf")
            try:
                loc = Gui.QFileDialog.getSaveFileName(PRFDialog, self.tr("Save PRF report (as HTML)"), '', self.tr('HTML document (*.html)'))
                if(len(unicode(loc)) == 0): # cancelled
                    return False
                f = open(unicode(loc), "wb")
                f.write(unicode(ui.textBrowser.toHtml()).encode('utf-8'))
                f.close()
                self.showstatus(self.tr('Prf report saved'))
            except IOError, (e):
                self.showerror(e)
        ui.buttonBox.accepted.connect(_save)
        return PRFDialog.exec_()

    def auxReport(self):
        'Load the online AUX report form in a dialog'
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
            logging.debug("report loaded: %s", boolean)
            html = ui.webView.page().mainFrame()
            submit = html.findFirstElement('input[type=submit]')
            submit.setAttribute('style', 'visibility:hidden')
            business = html.findFirstElement('input[name="foretag"]')
            business.setAttribute("value", self.settings.value('AUX/foretag', "NRK <avdeling>").toString())
            contact = html.findFirstElement('input[name=kontakt]')
            contact.setAttribute("value", self.settings.value('AUX/kontakt', "<ditt eller prosjektleders navn>").toString())
            phone = html.findFirstElement('input[name="telefon"]')
            phone.setAttribute("value", self.settings.value('AUX/telefon', "<ditt eller prosjektleders telefonnummer>").toString())
            email = html.findFirstElement('input[name="email"]')
            email.setAttribute("value", self.settings.value('AUX/email', "<ditt eller prosjektleders epostadresse>").toString())
            productionname = html.findFirstElement('input[name="produktionsnamn"]')
            productionname.setAttribute("value", self.ui.prodno.text())
            check_tv = html.findFirstElement('input[name="checkbox2"]')
            check_tv.setAttribute("checked", "checked")
            text = html.findFirstElement("textarea")
            text.setPlainText(s)
        ui.webView.loadFinished.connect(reportloaded)
        def reportsubmit():
            logging.debug("report submitting")
            html = ui.webView.page().mainFrame()
            for el in ['foretag', 'kontakt', 'telefon', 'email', 'produktionsnamn']:
                htmlel = html.findFirstElement('input[name=%s]' % el)
                val = htmlel.evaluateJavaScript("this.value").toString()
                if len(val) == 0:
                    self.showerror(unicode(self.tr('"%s" cannot be blank')) % el.title())
                    return None
                self.settings.setValue('AUX/%s' % el, val)
            submit = html.findFirstElement('input[type=submit]')
            submit.setAttribute('style', 'visibility:show')
            #submit.evaluateJavaScript('this.click()')
            #return AUXDialog.accept()
        ui.buttonBox.accepted.connect(reportsubmit)
        return AUXDialog.exec_()

    def manualResolve(self):
        'Manually submit selected tracks to aux for resolving'
        row = self.ui.detailsBox.currentRow
        def updateMetadata(filename, md):
            row.metadata = md
            self.showMetadata(row)
            row.setCheckState(0, Core.Qt.Checked)

        filepath = self.audiofiles[row.audioname]
        manualPattern, result = Gui.QInputDialog.getText(self, self.tr('Music ID'), 
            self.tr('Enter the correct music ID:'), Gui.QLineEdit.Normal, filepath.name)

        #resolver = metadata.AUXResolver()
        resolver = metadata.findResolver(unicode(manualPattern))
        resolver.trackResolved.connect(self.loadMetadata) # connect the 'resolved' signal
        resolver.trackResolved.connect(updateMetadata)
        resolver.trackResolved.connect(self.submitMissingFilename)
        resolver.trackProgress.connect(self.showProgress) 
        resolver.error.connect(self.showerror) 
        self.workers.append(resolver) # keep track of the worker
        resolver.resolve(unicode(manualPattern), filepath.pathurl) # put the worker to work async

    def submitMissingFilename(self, filename, resolvedmetadata):
        'Add filename and metadata to a public spreadsheet'
        _url = 'https://docs.google.com/spreadsheet/embeddedform?formkey=dEx0Z2xIWWJncHFxLVBQVWd2aW9xSUE6MQ'
        GdocsDialog = Gui.QDialog()
        ui = auxreport_ui.Ui_PlingPlongAUXDialog()
        ui.setupUi(GdocsDialog)
        ui.buttonBox.hide()
        ui.webView.load(Core.QUrl(_url))
        ui.webView.loadStarted.connect(lambda: ui.progressBar.show())
        ui.webView.loadFinished.connect(lambda: ui.progressBar.hide())
        def reportloaded(boolean):
            logging.debug("report loaded: %s" % boolean)
            html = ui.webView.page().mainFrame()
            fn = html.findFirstElement('input[id="entry_0"]')
            fn.setAttribute("value", filename)
            text = html.findFirstElement("textarea")
            text.setPlainText(unicode(vars(resolvedmetadata)))
        ui.webView.loadFinished.connect(reportloaded)
        return GdocsDialog.exec_()

    def credits(self):
        'Show text dialog with a list of track metadata suitable for end credits'
        _labels_seen = []
        s = ""
        for r in self.itercheckedrows():
            if r.metadata.title is None: continue
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
            logging.debug("saving credits")
            try:
                loc = Gui.QFileDialog.getSaveFileName(CreditsDialog, self.tr("Save credits (as HTML)"), '', self.tr('HTML document (*.html)'))
                f = open(unicode(loc), "wb")
                f.write(unicode(ui.textBrowser.toHtml()).encode('utf-8'))
                f.close()
                self.showstatus(self.tr('End credits saved'))
            except IOError, (e):
                self.showerror(e)
        ui.buttonBox.accepted.connect(_save)
        CreditsDialog.setWindowTitle(self.tr('Credits'))
        return CreditsDialog.exec_()

    def reportError(self):
        'Report program error to an online form'
        _url = 'https://docs.google.com/a/lurtgjort.no/spreadsheet/viewform?formkey=dHFtZHFFMlkydmRPTnFNM2l3SHZFcFE6MQ'
        GdocsDialog = Gui.QDialog()
        ui = auxreport_ui.Ui_PlingPlongAUXDialog()
        ui.setupUi(GdocsDialog)
        ui.buttonBox.hide()
        ui.webView.load(Core.QUrl(_url))
        ui.webView.loadStarted.connect(lambda: ui.progressBar.show())
        ui.webView.loadFinished.connect(lambda: ui.progressBar.hide())
        def reportloaded(boolean):
            logging.debug("reporterror loaded: %s", boolean)
            html = ui.webView.page().mainFrame()
            log = html.findFirstElement('textarea[id="entry_5"]')
            log.setPlainText(''.join(self.log))
            log = html.findFirstElement('input[id="entry_7"]')
            log.setAttribute('value', self.getVersion())
        ui.webView.loadFinished.connect(reportloaded)
        return GdocsDialog.exec_()     
        
    def editDuration(self, row, col): # called when double clicked
        "Replace duration column with a spinbox to manually change value"
        logging.debug("editDuration: %s %s", row, col)
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
            msg = Gui.QMessageBox.critical(self, self.tr("Need production number"), 
                                           self.tr("You must enter the production number"))
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
        logging.debug("gluonFinished: %s -> %s", trackname, metadata)
        for nom, row in self.gluon.currejtList:
            logging.debug("%s %s", repr(os.path.splitext(nom)[0]), repr(unicode(trackname)))
            if os.path.splitext(nom)[0] == unicode(trackname):
                row.setBackground(0, Gui.QBrush(Gui.QColor("light green")))

    def run(self, app):
        self.show()
        if self.xmemlfile is not None: # program was started with an xmeml file as argument
            self.loadxml(self.xmemlfile)
        sys.exit(app.exec_())

    def setLanguage(self, language):
        'Load translations for language'
        if self.translator is not None:
            self.app.removeTranslator(self.translator)
        else:
            self.translator = Core.QTranslator(self.app)
        logging.debug("loading translation: odometer_%s", language)
        self.translator.load(':data/translation_%s' % language)
        self.app.installTranslator(self.translator)
        # also for qt strings
        if self.translatorQt is not None:
            self.app.removeTranslator(self.translatorQt)
        else:
            self.translatorQt = Core.QTranslator(self.app)
        logging.debug("loading Qttranslation: qt_%s", language)
        self.translatorQt.load(':data/qt_%s' % language)
        self.app.installTranslator(self.translatorQt)

def uniqify(seq):
    'Return list of unique items in a sequence'
    keys = {} 
    for e in seq: 
        keys[e] = 1 
    return keys.keys()

def xmemlfileFromEvent(event):
    'Return first xmeml file from a (e.g. dropped) Qt event'
    data = event.mimeData()
    try:
        for f in data.urls():
            fil = unicode(f.toLocalFile())
            if os.path.isfile(fil) and os.path.splitext(fil.upper())[1] == ".XML":
                # also try to see if xmemliter accepts it?
                return fil
    except Exception, (e):
        logging.error(e)
    return False

def rungui(argv):
    f = None
    try:
        if os.path.exists(argv[1]):
            f = argv[1]
            #argv = argv[0:-1]
    except IndexError:
        pass
    if sys.platform == 'win32':
        # default win32 looks awful, make it pretty
        # docs advise to do this before QApplication() is started
        Gui.QApplication.setStyle("cleanlooks") 
    app = Gui.QApplication(argv)
    if sys.platform == 'win32':
        def setfont(fontname):
            app.setFont(Gui.QFont(fontname, 9))
            return unicode(app.font().toString()).split(',')[0] == fontname
        # default win32 looks awful, make it pretty
        for z in ['Lucida Sans Unicode', 'Arial Unicode MS', 'Verdana']:
            if setfont(z): break
    if f is not None: o = Odometer(app, f)
    else: o = Odometer(app)
    o.run(app)

if __name__ == '__main__':
    # suppress error on win
    logging.basicConfig(level=logging.DEBUG)
    if hasattr(sys, 'frozen') and sys.frozen == 'windows_exe':
        import StringIO
        sys.stderr = StringIO.StringIO()
        sys.stdout = StringIO.StringIO()
    rungui(sys.argv)



