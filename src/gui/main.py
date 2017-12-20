#!/usr/bin/env python
#-*- encoding: utf8 -*-
# This file is part of odometer by Håvard Gulldahl <havard.gulldahl@nrk.no>
# (C) 2011-2017

from builtins import str
import sys, os, os.path
import time
import datetime
import urllib.parse
import json
from io import StringIO
import configparser 
import logging
import traceback
import subprocess
import hashlib
import functools
import html

from enum import Enum
from collections import defaultdict
import pickle

import PyQt5.QtCore as Core
import PyQt5.QtGui as Gui
import PyQt5.QtNetwork as QtNetwork
import PyQt5.Qt as Qt
import PyQt5.QtSvg as Svg
from PyQt5.QtWidgets import (QWidget, QMainWindow, QDialog, QTreeWidgetItem,
    QLineEdit, QMessageBox, QInputDialog, QDoubleSpinBox, QErrorMessage,
    QDialogButtonBox, QApplication, QFileDialog, QLabel, QProgressBar)

from xmeml import iter as xmemliter
import metadata.gluon
import metadata.model
import metadata.resolvers
from core.workers import UrlWorker, XmemlWorker


# import gui
from . import odometer_ui
from . import odometer_rc
from . import auxreport_ui
from . import prfreport_ui
from . import onlinelogin_ui

class Status(Enum):
    INFO = 1
    WARNING = 2
    ERROR = 3

def readResourceFile(qrcPath):
    """Read qrc file and return string

    'qrcPath' is ':/path/name', for example ':/txt/about.html'
    """
    f = Core.QFile(qrcPath)
    if not f.open(Core.QIODevice.ReadOnly | Core.QIODevice.Text):
        raise IOError(u"Could not read resource '%s'" % qrcPath)
    t = Core.QTextStream(f)
    t.setCodec("UTF-8")
    s = str(t.readAll())
    f.close()
    return s

def readBuildflags():
    "Read build flags from builtin resource file"
    cp = configparser.ConfigParser()
    cp.readfp(StringIO(str(readResourceFile(':/data/buildflags'))))
    return cp

def formatTC(secs):
    '''Convert floating point /secs/ to a TC label. E.g. 62.1 -> 00:01:02.200
    Returns hh:mm:ss.sss'''
    return "%02d:%02d:%02d.%02d" % \
        functools.reduce(lambda ll,b : divmod(ll[0],b) + ll[1:],
                        [(secs*1000,),1000,60,60])

class Odometer(QMainWindow):
    msg = Core.pyqtSignal(str, name="msg")
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
        self.ui.volumeThreshold.setValue(self.volumethreshold.gain)
        if self.buildflags.getboolean('ui', 'editbutton'):
            self.ui.editMetadataButton = self.ui.buttonBox.addButton(self.tr('Edit'), QDialogButtonBox.ActionRole)
            self.ui.editMetadataButton.clicked.connect(self.editMetadata)
        if self.buildflags.getboolean('ui', 'manuallookupbutton'):
            self.setManualLookupButtonVisible(True)
            # check the option in the pulldown menu
            self.ui.actionManualLookup.setChecked(True)
        self.ui.buttonBox.rejected.connect(lambda: self.ui.detailsBox.hide())
        self.ui.loadFileButton.clicked.connect(self.clicked)
        #self.ui.DMAButton.clicked.connect(self.gluon)
        self.ui.DMAButton.clicked.connect(self.prfReport)
        self.ui.DMAButton.setEnabled(True)
        self.ui.AUXButton.clicked.connect(self.auxReport)
        self.ui.ApolloButton.clicked.connect(self.apollomusicReport)
        self.ui.creditsButton.clicked.connect(self.credits)
        self.ui.errorButton.clicked.connect(self.reportError)
        self.ui.clips.setIconSize(Core.QSize(16,16))
        self.ui.clips.itemSelectionChanged.connect(lambda: self.hilited(self.ui.clips.selectedItems()))
        self.ui.clips.itemActivated.connect(self.showMetadata)
        self.ui.clips.itemDoubleClicked.connect(self.editDuration) # manually override duration column
        self.ui.volumeThreshold.valueChanged.connect(lambda i: self.computeAudibleDuration(xmemliter.Volume(gain=float(i))))
        self.ui.actionAboutOdometer.triggered.connect(self.showAbout)
        self.ui.actionHelp.triggered.connect(self.showHelp)
        self.ui.actionLicenses.triggered.connect(self.showLicenses)
        self.ui.actionLogs.triggered.connect(self.showLogs)
        self.ui.actionCheckForUpdates.triggered.connect(self.showCheckForUpdates)
        self.ui.actionShowPatterns.triggered.connect(self.showShowPatterns)
        self.ui.actionLoginOnline.triggered.connect(self.showLoginOnline)
        self.ui.actionTimelineOrderReport.triggered.connect(self.showTimelineOrderReport)
        self.ui.actionAdjustThreshold.toggled.connect(self.setThresholdVisible)
        self.ui.actionManualLookup.toggled.connect(self.setManualLookupButtonVisible)
        self.ui.actionReportError.triggered.connect(self.reportError)
        self.msg.connect(self.showstatus)
        self.loaded.connect(self.computeAudibleDuration)
        self.ui.dropIcon = Svg.QSvgWidget(':/gfx/graystar', self.ui.clips)
        self.ui.dropIcon.setMinimumSize(200,200)
        self.ui.dropIcon.setToolTip(self.tr('Drop your xml file here'))
        if not self.buildflags.getboolean('release', 'releasecheck'):
            self.ui.actionCheckForUpdates.setEnabled(False)
        if not self.buildflags.getboolean('ui', 'volumeThreshold'):
            self.setThresholdVisible(False)
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

        self.ui.information.hide()
        self.resize(Core.QSize(1200,1000))
        #self.metadataLoaded.connect(self.checkUsage)
        Core.QTimer.singleShot(5, self.updateAUXRepertoire)

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
        self.showerror(self.tr("This does not seem to be a valid FCP XML file. Sorry."), errtype='invalid file')
        event.ignore()

    def dropEvent(self, event):
        'React to file being dropped (if it looks like an xmeml file, load it)'
        event.acceptProposedAction()
        self.ui.dropIcon.load(':/gfx/graystar')
        x = xmemlfileFromEvent(event) # x is a unicode file path
        if x:
            self.xmemlfile = x
            self.loadxml(self.xmemlfile)

    def resizeEvent(self, event):
        'React to main gui being resized'
        i = self.ui.dropIcon
        i.move(self.width()/2-i.width(), self.height()*0.75-i.height())

    def logMessage(self, msg, msgtype=Status.INFO):
        'Add a message to the log'
        if msgtype == Status.ERROR:
            color = 'red'
        elif msgtype == Status.INFO:
            color = '#390'
        elif msgtype == Status.WARNING:
            color = 'blue'
        try:
            if isinstance(self.xmemlfile, str):
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
            msg = str(e)
        self.log.append('<div style="color:red">')
        for line in traceback.format_exception(etype, e, tb):
            self.log.append(line)
        self.log.append('</div>')

    def showException(self, e):
        self.logException(e)
        self.showerror(str(self.tr('Unexpected error: %s')) % e)

    def showstatus(self, msg, autoclose=True, msgtype=Status.INFO):
        'Popup some info'

        if hasattr(self, '_laststatusmsg') and msg == self._laststatusmsg:
            # don't repeat yourself
            return None

        if isinstance(msg, Exception): #unwrap exception
            msg=str(msg)

        infoLayout = self.ui.information.layout()
        b = QLabel(msg, self.ui.information)
        infoLayout.addWidget(b)
        self._laststatusmsg = str(msg)
        self.logMessage(msg, msgtype)
        return b

    def showerror(self, msg, errtype=None):
        'Show error message'
        _errormsg = QErrorMessage()
        if errtype is not None:
            _errormsg.showMessage(msg, errtype)
        else:
            _errormsg.showMessage(msg)

        _errormsg.exec()
        self.logMessage(msg, msgtype=Status.ERROR)

    def clearstatus(self):
        'empty message list'

        infoLayout = self.ui.information.layout()
        while infoLayout.count() > 0:
            child = infoLayout.takeAt(0)
            widget = child.widget()
            del widget
            del child

    def getVersion(self):
        _version = self.buildflags.get('release', 'version')
        if self.buildflags.getboolean('release', 'beta'):
            _version = str(_version).strip() + ' NEXT'
        logging.debug("got version:  ---%s---", _version)
        return _version

    def showAbout(self):
        'Show "About" text'
        _aboutText = readResourceFile(':/txt/about')
        _aboutbox = QMessageBox.about(None, 'About Odometer', _aboutText.replace(u'✪', self.getVersion()))

    def showHelp(self):
        'Show help document from online resource'
        HelpDialog = QDialog()
        ui = auxreport_ui.Ui_PlingPlongAUXDialog()
        ui.setupUi(HelpDialog)
        HelpDialog.setWindowTitle(self.tr('Help'))
        ui.buttonBox.hide()
        ui.webEngineView.load(Core.QUrl(self.buildflags.get('release', 'helpUrl')))
        ui.webEngineView.loadStarted.connect(lambda: ui.progressBar.show())
        ui.webEngineView.loadProgress.connect(ui.progressBar.setValue)
        ui.webEngineView.loadFinished.connect(lambda: ui.progressBar.hide())
        def helpdocloaded(success):
            logging.debug("help doc loaded: %s", success)
            # TODO: Add offline fallback
            if not success:
                self.showerror(self.tr("Could not load help document, sorry. :("), errtype='offline')
        ui.webEngineView.loadFinished.connect(helpdocloaded)
        return HelpDialog.exec_()

    def showLicenses(self):
        'Show a dialog to display licenses and terms'
        _licenseText = readResourceFile(':/txt/license')
        _box = QMessageBox(self)
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
            _currentVersion = _date(str(readResourceFile(':/txt/version_%s' % _platform)))
            _onlineVersion = _date(_ver)
            if _currentVersion < _onlineVersion:
                # out of date
                _box = Gui.QMessageBox.warning(self, self.tr('Oooooo!'), str(self.tr('Odometer is out of date. \nGet the new version: %s')) % _url)
            else:
                _box = Gui.QMessageBox.information(self, self.tr('Relax'), self.tr('Odometer is up to date'))
        async = UrlWorker()
        _url = '%s/odometerversion_%s.txt' % (_dropboxUrl, _platform)
        async.load(_url, timeout=7)
        async.finished.connect(compare)
        async.failed.connect(failed)

    def showShowPatterns(self):
        'Show a list of recognised Patternes'
        PatternDialog = QDialog()
        ui = prfreport_ui.Ui_PlingPlongPRFDialog()
        ui.setupUi(PatternDialog)
        ui.buttonBox.removeButton(ui.buttonBox.button(QDialogButtonBox.Save))
        r = []
        for catalog, patterns in metadata.resolvers.getResolverPatterns().items():
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
        LogDialog = QDialog()
        ui = prfreport_ui.Ui_PlingPlongPRFDialog()
        ui.setupUi(LogDialog)
        ui.textBrowser.setHtml(''.join(self.log))
        LogDialog.setWindowTitle('Help')
        return LogDialog.exec_()

    def showTimelineOrderReport(self):
        'Pop up a dialog to show a detailed report, showing each subclip in the order they appear on the timeline'
        logging.debug('Pop up a dialog to show detailed run sheet report')
        ExportDialog = QDialog()
        ui = prfreport_ui.Ui_PlingPlongPRFDialog()
        ui.setupUi(ExportDialog)
        s = str(self.tr('<h1>Tracks by order of entry on timeline</h1>'))
        s = s + '<table cellpadding=10><tr>'
        s = s + str(self.tr('<th>In</th>'))
        s = s + str(self.tr('<th>Out</th>'))
        s = s + str(self.tr('<th>Duration</th>'))
        s = s + str(self.tr('<th>Clip details</th>'))
        s = s + '</tr>'
        clips = defaultdict(list)
        for r in self.itercheckedrows():
            if r.metadata.title is None:
                # not resolved, use file name
                _t = repr(r.audioname)
            else:
                _t = u'\u00ab%(title)s\u00bb \u2117 %(musiclibrary)s' % vars(r.metadata)
            for sc in r.subclips:
                _s = '<tr><td><code>%s</code></td><td><code>%s</code></td>' % (sc['in'], sc['out'])
                _s += '<td>%06.2f\"</td>' % (sc['durationsecs'])
                _s += '<td>%s</td>' % _t
                _s += "</tr>"
                clips[sc['in']].append(_s)
        # sort all clips by inpoint
        inpoints = list(clips.keys())
        inpoints.sort()
        s = s + "".join(["".join(clips[inpoint]) for inpoint in inpoints])
        s = s + '</table>'
        ui.textBrowser.setHtml(s)
        ExportDialog.setWindowTitle(self.tr('Detailed run sheet'))
        return ExportDialog.exec_()

    def showLoginOnline(self):
        'Pop up a dialog to log in to online services like AUX and ApolloMusic'
        LoginDialog = QDialog()
        ui = onlinelogin_ui.Ui_PlingPlongOnlineDialog()
        ui.setupUi(LoginDialog)
        ui.AUXuser.setText(self.settings.value('AUXuser', ''))
        ui.AUXpassword.setText(self.settings.value('AUXpassword', ''))
        ui.Apollouser.setText(self.settings.value('Apollouser', ''))
        ui.Apollopassword.setText(self.settings.value('Apollopassword', ''))
        ui.Universaluser.setText(self.settings.value('Universaluser', ''))
        ui.Universalpassword.setText(self.settings.value('Universalpassword', ''))
        ui.Uprightuser.setText(self.settings.value('Uprightuser', ''))
        ui.Uprightpassword.setText(self.settings.value('Uprightpassword', ''))
        #TODO: enable this when login is implemented
        ui.Uprightuser.setDisabled(True)
        ui.Uprightpassword.setDisabled(True)
        ui.Uprightlogin.setDisabled(True)
        ui.Extremeuser.setText(self.settings.value('Extremeuser', ''))
        ui.Extremepassword.setText(self.settings.value('Extremepassword', ''))
        def storeCookie(service, data):
            logging.debug("Storing cookie for %s: %s", service, data.info().get('Set-Cookie', None))
            logging.debug("Service returned %s", data.getcode())
            #logging.debug("Headers: %s", data.info())
            b = data.read().decode()
            logging.debug("body: %s", b)
            login = False
            if service == 'AUX':
                result = json.loads(b)
                if result['ax_success'] == 1:
                    self.showstatus(self.tr('Logged in to AUX'))
                else:
                    m = self.tr('%s login failed: %s') % (service, result['ax_errmsg'])
                    logging.warning(m)
                    self.showerror(m)
            elif service == 'Apollo':
                result = json.loads(b)
                if result['success'] == 1:
                    self.settings.setValue('Apollocookie', data.info()['Set-Cookie'])
                    self.showstatus(self.tr('Logged in to Apollo'))
                else:
                    m = self.tr('%s login failed: %s') % (service, result['message'])
                    logging.warning(m)
                    self.showerror(m)
            elif service == 'Upright':
                if result['success'] == 1:
                    self.settings.setValue('Uprightcookie', data.info()['Set-Cookie'])
                    self.showstatus(self.tr('Logged in to Upright'))
                else:
                    m = self.tr('%s login failed: %s') % (service, result['message'])
                    logging.warning(m)
                    self.showerror(m)
            elif service == 'Universal':
                # if password matched, we get
                #  <div class="result" ssoToken="xxx">True</div>
                # but if pasword failed, instead we get
                # <div class="error failedlogin">You have 5 password attempts remaining.</div>
                # or
                # <div class="error"><li>Please enter a valid email address.</li></div>
                if b.startswith('''<div class="result" ssoToken="'''):
                    self.settings.setValue('Universalcookie', data.info()['Set-Cookie'])
                    self.showstatus(self.tr('Logged in to Universal'))
                else:
                    m = self.tr('%s login failed: %s') % (service, b)
                    logging.warning(m)
                    self.showerror(m)
            elif service == 'Extreme':
                result = json.loads(b)
                try:
                    success = result['login']['error'] == 'WRONG_PASSWORD'
                except KeyError:
                    success = True
                if not success:
                    m = self.tr('%s login failed: %s') % (service, result['message'])
                    logging.warning(m)
                    self.showerror(m)
                else:
                    self.settings.setValue('Extremecookie', data.info()['Set-Cookie'])
                    self.showstatus(self.tr('Logged in to Extreme'))


            #logging.debug("settings: %r", list(self.settings.allKeys()))

            stopBusy()

        def failed(ex):
            logging.warning("faile! %r", ex)
            self.logException(ex)
            self.showerror(self.tr('Login failed. Check your password at the website.'))
            stopBusy()
        def startBusy():
            ui.progressBar.setRange(0,0)
        def stopBusy():
            ui.progressBar.setMaximum(1)

        def AUXauth():
            logging.info('Getting auth (session id) from AUX')
            def getauth(resp):
                'extract session id from response json'
                body = resp.read().decode()
                sid = json.loads(body)['sid'] 
                logging.debug('aux sid: %s', sid)
                self.settings.setValue('AUXSID', sid)
                self.settings.setValue('AUXcookie', resp.info()['Set-Cookie'])

            startBusy()
            sid = UrlWorker()
            sid.failed.connect(failed)
            sid.finished.connect(getauth)
            sid.finished.connect(lambda d: AUXlogin())
            sid.load('http://search.auxmp.com//search/html/ajax/axExtData.php?_dc=%s&ext=1&sprache=en&country=NO&ac=login' % int(time.time()))
        def AUXlogin():
            logging.info('login to aux')
            self.settings.setValue('AUXuser', ui.AUXuser.text())
            self.settings.setValue('AUXpassword', ui.AUXpassword.text())
            startBusy()
            async = UrlWorker()
            url = 'http://search.auxmp.com//search/html/ajax/axExtData.php'
            # from javascript source: var lpass = Sonofind.Helper.md5(pass + "~" + Sonofind.AppInstance.SID);
            _password = ui.AUXpassword.text() +'~'+ self.settings.value('AUXSID', '')
            getdata = urllib.parse.urlencode({'ac':'login',
                                            'country': 'NO',
                                            'sprache': 'en',
                                            'ext': 1,
                                            '_dc': int(time.time()),
                                            'luser':str(ui.AUXuser.text()),
                                            'lpass':hashlib.md5(_password).hexdigest(),  
                                            })
            async.load('%s?%s' % (url, getdata), 
                       timeout=7, 
                       headers={
                        'Cookie':self.settings.value('AUXcookie', '')
                       })
            async.finished.connect(lambda d: storeCookie('AUX', d))
            async.failed.connect(failed)
        def Apollologin():
            logging.info('login to apollo')
            self.settings.setValue('Apollouser', ui.Apollouser.text())
            self.settings.setValue('Apollopassword', ui.Apollopassword.text())
            startBusy()
            async = UrlWorker()
            url = 'http://www.findthetune.com/online/login/ajax_authentication/'
            postdata = {'user':str(ui.Apollouser.text()),
                        'pass':str(ui.Apollopassword.text())}
            async.load(url, timeout=7, data=postdata)
            async.finished.connect(lambda d: storeCookie('Apollo', d))
            async.failed.connect(failed)
        def Uprightlogin():
            logging.info('login to Upright')
            self.settings.setValue('Uprightuser', ui.Uprightuser.text())
            self.settings.setValue('Uprightpassword', ui.Uprightpassword.text())
            startBusy()
            async = UrlWorker()
            url = 'http://www.findthetune.com/online/login/ajax_authentication/'
            postdata = {'user':str(ui.Uprightuser.text()),
                        'pass':str(ui.Uprightpassword.text())}
            async.load(url, timeout=7, data=postdata)
            async.finished.connect(lambda d: storeCookie('Upright', d))
            async.failed.connect(failed)
        def Universallogin():
            logging.info('login to Universal PPM')
            self.settings.setValue('Universaluser', ui.Universaluser.text())
            self.settings.setValue('Universalpassword', ui.Universalpassword.text())
            startBusy()
            async = UrlWorker()
            url = 'http://www.unippm.se/Feeds/commonXMLFeed.aspx'
            getdata = urllib.parse.urlencode({'method': 'Login',
                                            'user':str(ui.Universaluser.text()),
                                            'password':str(ui.Universalpassword.text()),
                                            'rememberme':'false',
                                            'autoLogin':'false',
                                            '_': int(time.time()),
                                            })
            async.load('%s?%s' % (url, getdata), timeout=7)
            async.finished.connect(lambda d: storeCookie('Universal', d))
            async.failed.connect(failed)
        def Extremeauth():
            logging.info('Getting auth from Extreme Music')
            def getauth(resp):
                'extract json from response body'
                body = resp.read().decode()
                logging.debug('auth: %s', body)
                self.settings.setValue('ExtremeAUTH', json.loads(body)['env']['API_AUTH'])
            startBusy()
            env = UrlWorker()
            env.failed.connect(failed)
            env.finished.connect(getauth)
            env.finished.connect(lambda d: Extremelogin())
            env.load('https://www.extrememusic.com/env')

        def Extremelogin():
            logging.info('login to Extreme Music')
            time.sleep(0.5)
            self.settings.setValue('Extremeuser', ui.Extremeuser.text())
            self.settings.setValue('Extremepassword', ui.Extremepassword.text())
            async = UrlWorker()
            url = 'https://lapi.extrememusic.com/accounts/login'
            postdata = json.dumps({'username': str(ui.Extremeuser.text()),
                                   'password': str(ui.Extremepassword.text()),
                                   'remember_me': False})
            auth = {'X-API-Auth': self.settings.value('ExtremeAUTH', ''),
                    'Content-Type':'application/json; charset=utf-8'}
            async.load(url, timeout=7, data=postdata, headers=auth)
            async.finished.connect(lambda d: storeCookie('Extreme', d))
            async.failed.connect(failed)
        ui.AUXlogin.clicked.connect(AUXauth)
        ui.Apollologin.clicked.connect(Apollologin)
        ui.Universallogin.clicked.connect(Universallogin)
        # TODO: implement this login: 
        # ui.Uprightlogin.clicked.connect(Uprightlogin)
        ui.Extremelogin.clicked.connect(Extremeauth)
        return LoginDialog.exec_()

    def updateAUXRepertoire(self):
        self.logMessage(self.tr('Updating AUX repertoire'))
        try:
            repertoire = pickle.loads(self.settings.value('auxrepertoire', ''))
        except Exception as e:
            self.logException(e)
            repertoire = None
        logging.debug("found repertoire: %s", repertoire)
        def age(dt):
            return (datetime.datetime.now() - dt).days
        if repertoire is not None and age(repertoire['timestamp']) < 7:
            self.logMessage(self.tr('Found fresh AUX repertoire list in cache'))
            self.logMessage(str(self.tr('AUX repertoire: %s catalogs')) % (len(repertoire.keys())-1))
            self.AUXRepertoire = repertoire
            return

        # get new data online
        self.logMessage(self.tr('AUX repertoire cache is too old, fetch new online'))
        _url = self.buildflags.get('release', 'AUXRepertoireUrl')

        def store(data):
            logging.debug("got json aux data: %s", data)
            repertoire = json.loads(data.read().decode('utf8'))
            logging.debug("got repertoire: %s", repertoire)
            repertoire['timestamp'] = datetime.datetime.now()
            self.settings.setValue('auxrepertoire', pickle.dumps(repertoire))
            self.AUXRepertoire = repertoire
            self.logMessage(str(self.tr('AUX repertoire: %s catalogs')) % (len(repertoire.keys())-1))
        def failed(ex):
            #logging.debug("faile!", ex
            self.logException(ex)
        async = UrlWorker()
        async.load(_url, timeout=7)
        async.finished.connect(store)
        async.failed.connect(failed)

    def setThresholdVisible(self, b):
        "toggle visibility of volume threshold spinbox"
        self.ui.volumeThreshold.setVisible(b)
        self.ui.volumeInfo.setVisible(b)

    def setManualLookupButtonVisible(self, show):
        if show:
            self.ui.resolveManualButton = self.ui.buttonBox.addButton(self.tr('Manual lookup'), QDialogButtonBox.ActionRole)
            self.ui.resolveManualButton.clicked.connect(self.manualResolve)
        else:
            try:
                self.ui.buttonBox.removeButton(self.ui.resolveManualButton)
            except Exception as e:
                self.showException(e)

    def setSubmitMissingButtonVisible(self, show):
        if show:
            self.ui.submitMissingButton = self.ui.buttonBox.addButton(self.tr('Submit missing filename'), QDialogButtonBox.ActionRole)
            self.ui.submitMissingButton.clicked.connect(self.submitMissingFilename)
        else:
            try:
                self.ui.buttonBox.removeButton(self.ui.submitMissingButton)
            except Exception as e:
                self.showException(e)

    def clicked(self, qml):
        'Open file dialog to get xmeml file name'
        lastdir = self.settings.value('lastdir', '')
        xf = QFileDialog.getOpenFileName(self,
            self.tr('Open an xmeml file (FCP export)'),
            lastdir,
            self.tr('Xmeml files (*.xml)'))
        logging.debug('Got following file name to open: %r', xf)
        _xmemlfile, _filter = xf
        if not os.path.exists(_xmemlfile):
            logging.warning('Tried to open a non-existing file: %r', _xmemlfile)
            return False
        self.xmemlfile = _xmemlfile
        self.settings.setValue('lastdir', os.path.dirname(self.xmemlfile))
        self.loadxml(self.xmemlfile)

    def loadxml(self, xmemlfile):
        'Start loading xmeml file, start xmeml parser'
        if isinstance(xmemlfile, str):
            unicxmemlfile = xmemlfile
        else:
            unicxmemlfile = xmemlfile.decode(sys.getfilesystemencoding())
        self.clearstatus()
        msgbox = self.showstatus(str(self.tr("Loading %s...")) % unicxmemlfile, autoclose=self.loaded)
        self.loadingbar()
        self.loaded.connect(self.removeLoadingbar)
        self.xmemlthread.failed.connect(self.removeLoadingbar)
        self.loaded.connect(lambda: self.ui.fileInfo.setText(str(self.tr("<b>Loaded:</b> %s")) % os.path.basename(unicxmemlfile)))
        self.loaded.connect(lambda: self.ui.fileInfo.setToolTip(os.path.abspath(unicxmemlfile)))
        try:
      	    self.xmemlthread.load(xmemlfile)
        except Exception:
            self.removeLoadingbar()
            raise

    def loadingbar(self):
        'Add global progress bar'
        self.ui.progress = QProgressBar(self)
        self.ui.progress.setMinimum(0)
        self.ui.progress.setMaximum(0) # don't show progress, only "busy" indicator
        self.ui.statusbar.addWidget(self.ui.progress, 100)

    def removeLoadingbar(self):
        'Remove global progress bar'
        self.ui.statusbar.removeWidget(self.ui.progress)
        self.ui.progress.deleteLater()

    def load(self, xmemlparser):
        'Load audio clips from xmeml parser into the gui'
        logging.debug('Got xmemlparser: %r', xmemlparser)
        try:
            self.audioclips, self.audiofiles = xmemlparser.audibleranges(self.volumethreshold)
        except Exception as e:
            self.removeLoadingbar()
            self.logException(e)
            return False

        self.ui.volumeInfo.setText(str(self.tr("<i>(above %i dB)</i>")) % self.volumethreshold.decibel)
        self.xmemlparser = xmemlparser
        numclips = len(self.audioclips.keys())
        self.ui.creditsButton.setEnabled(numclips > 0)
        self.msg.emit(str(self.tr(u"%i audio clips loaded from xmeml sequence \u00ab%s\u00bb.")) % (numclips, xmemlparser.name))
        self.loaded.emit()

    def computeAudibleDuration(self, volume=None):
        'Loop through all audio clips and start the metadata workers'
        if isinstance(volume, xmemliter.Volume):
            self.audioclips, self.audiofiles = self.xmemlparser.audibleranges(volume)
            self.ui.volumeInfo.setText(str(self.tr("<i>(above %i dB)</i>")) % volume.decibel)
        self.ui.clips.clear()
        self.rows = {}
        for audioname, ranges in self.audioclips.items():
            frames = len(ranges)
            if frames == 0:
                self.logMessage(str(self.tr(u'Skipping clip "%s" because no frames are audible')) % audioname)
                continue
            logging.debug("======= %s: %s -> %s======= ", audioname, ranges.r, frames)
            fileref = self.audiofiles[audioname] # might be None, if clip is offline
            secs = ranges.seconds()
            r = QTreeWidgetItem(self.ui.clips, ['', audioname,
                                                '%ss (%sf)' % (secs, frames)])
            r.metadata = metadata.model.TrackMetadata(filename=audioname)
            r.audioname = audioname
            r.clip = {'durationsecs':secs, 'durationframes':frames, 'in':None, 'out':None}
            r.subclips = []
            self.rows[audioname] = r
            w = metadata.resolvers.findResolver(audioname)
            logging.debug("w: %s -> %s",audioname.encode('utf-8'), w)
            r.setCheckState(0, Core.Qt.Unchecked)
            if w:
                if isinstance(w, metadata.resolvers.AUXResolver):
                    w.updateRepertoire(self.AUXRepertoire) # make sure repertoire is current
                elif isinstance(w, metadata.resolvers.ApollomusicResolver):
                    logincookie = self.settings.value('Apollocookie', '')
                    if not logincookie: # not logged in to apollo, big problem
                        self.showerror(self.tr(u'Track from Apollo Music detected. Please log in to the service'))
                        self.logMessage(self.tr(u'No logincookie from apollo music found.'), msgtype=Status.WARNING)
                        continue # go to next track
                    else:
                        w.setlogincookie(logincookie)
                w.trackResolved.connect(self.loadMetadata) # connect the 'resolved' signal
                w.trackResolved.connect(self.trackCompleted) # connect the 'resolved' signal
                w.trackProgress.connect(self.showProgress)
                w.trackFailed.connect(lambda x: self.showProgress(x, 100)) # dont leave progress bar dangling
                w.error.connect(lambda f, e: self.setRowInfo(row=f, text=e, warning=True))
                w.error.connect(lambda s: self.logMessage(s, msgtype=Status.ERROR))
                w.warning.connect(lambda s: self.logMessage(s, msgtype=Status.WARNING))
                self.workers.append(w) # keep track of the worker
                w.newresolve(audioname, fileref.pathurl) # put the worker to work async. NOTE: pathurl will be None on offilne files
            if self.showsubclips:
                i = 1
                for range in ranges:
                    frames = len(range)
                    secs = float(frames) / ranges.framerate
                    r.subclips.append( {'durationsecs':secs, 'durationframes':frames,
                                        'in':formatTC(float(range.start) / ranges.framerate),
                                        'out':formatTC(float(range.end) / ranges.framerate)} )
                    sr = QTreeWidgetItem(r, ['', '%s-%i' % (audioname, i),
                                                 '%ss (%sf)' % (secs, frames),
                                                 u'%sf\u2013%sf' % (range.start, range.end)
                                                ]
                                            )
                    i = i+1


    def loadMetadata(self, filename, metadata):
        'Handle metadata for a specific clip'
        row = self.rows[str(filename)]
        logging.debug("loadMetadata: %s - %s", filename, metadata)
        row.metadata = metadata
        if metadata.productionmusic:
            if metadata.title is None and metadata.label is None:
                txt = self.tr("Incomplete metadata. Please update manually")
            else:
                txt = u"\u00ab%(title)s\u00bb \u2117 %(label)s (%(musiclibrary)s)"
        else:
            if metadata.title is None and metadata.artist is None:
                txt = self.tr("Incomplete metadata. Please update manually")
            else:
                txt = u"%(artist)s: \u00ab%(title)s\u00bb \u2117 %(label)s %(year)s"
        #row.setText(3, txt % vars(metadata))
        self.setRowInfo(row, txt % vars(metadata))

        if metadata.musiclibrary in ("Sonoton", 'AUX Publishing'):
            self.ui.AUXButton.setEnabled(True)
        elif metadata.musiclibrary == 'ApolloMusic':
            self.ui.ApolloButton.setEnabled(True)
        #elif metadata.musiclibrary == 'ExtremeMusic': # TODO: enable this when dynamic report is possible
        #    self.ui.ExtremeButton.setEnabled(True)
        #elif metadata.musiclibrary == 'Universal': # TODO: enable this when dynamic report is possible
        #    self.ui.UniversalButton.setEnabled(True)
        #elif metadata.musiclibrary == 'Upright': # TODO: enable this when dynamic report is possible
        #    self.ui.Upright.setEnabled(True)
        self.metadataLoaded.emit(row)

    def trackCompleted(self, filename, metadata):
        'React to metadata finished loading for a specific clip'
        logging.debug("got metadata (%s): %s", filename, metadata)
        self.rows[str(filename)].setCheckState(0, Core.Qt.Checked)
        self.metadataloaded += 1
        if len(self.audioclips)  == self.metadataloaded:
            self.ui.DMAButton.setEnabled(True)

    def showProgress(self, filename, progress):
        'Show progress bar for a specific clip, e.g. when metadata is loading'
        logging.debug("got progress for %s: %r", filename, progress)
        row = self.rows[str(filename)]
        if progress < 100: # not yet reached 100%
            p = QProgressBar(parent=self.ui.clips)
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
        s += str(self.tr("""<i>Name:</i><br>%(name)s<br>
                <i>Total length:</i><br>%(secs)ss<br>
                <i>Rate:</i><br>%(timebase)sfps<br>
                """)) % ss
        if hasattr(r, 'metadata') and r.metadata.musiclibrary is not None:
            s += str(self.tr("<i>Library</i><br>%s<br>")) % r.metadata.musiclibrary
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
            self.ui.clipYear.setText(str(row.metadata.year or 0))
            self.ui.detailsBox.show()
        except AttributeError as e:
            self.logException(e)
            self.ui.detailsBox.hide()
        if hasattr(self.ui, 'resolveManualButton'):
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
            _edit = QLineEdit(text, self.ui.detailsBox)
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

    def setRowInfo(self, row, text, warning=False):
        'Set the 3rd cell of the <row> to <text>'
        if isinstance(row, str):
            row = self.rows[row]
        logging.debug('setting row  <%r> to <%r>', row, text)
        row.setText(3, text)
        if warning:
            row.setIcon(3, Gui.QIcon(':/gfx/warn'))
        else:
            row.setIcon(3, Gui.QIcon())

    def itercheckedrows(self):
        'iterate through rows that are checked'
        for row in self.rows.values():
            #logging.debug(row
            if row.checkState(0) == Core.Qt.Checked:
                yield row

    def prfReport(self):
        PRFDialog = QDialog()
        ui = prfreport_ui.Ui_PlingPlongPRFDialog()
        ui.setupUi(PRFDialog)
        s = str(self.tr('<h1>Track metadata sheet for PRF</h1>'))
        for r in self.itercheckedrows():
            _t = r.metadata.title if r.metadata.title else repr(r.audioname)
            s += str(self.tr('<div><dt>Title:</dt><dd>%s</dd>')) % _t
            if r.metadata.identifier is not None:
                s += str(self.tr('<dt>Track identifier:</dt><dd>%s</dd>')) % r.metadata.identifier
            if r.metadata.artist not in (None, u'(N/A for production music)'):
                s += str(self.tr('<dt>Artist:</dt><dd>%s</dd>')) % r.metadata.artist
            if r.metadata.albumname is not None:
                s += str(self.tr('<dt>Album name:</dt><dd>%s</dd>')) % r.metadata.albumname
            if r.metadata.lyricist is not None:
                s += str(self.tr('<dt>Lyricist:</dt><dd>%s</dd>')) % r.metadata.lyricist
            if r.metadata.composer is not None:
                s += str(self.tr('<dt>Composer:</dt><dd>%s</dd>')) % r.metadata.composer
            if r.metadata.label is not None:
                s += str(self.tr('<dt>Label:</dt><dd>%s</dd>')) % r.metadata.label
            if r.metadata.recordnumber is not None:
                s += str(self.tr('<dt>Recordnumber:</dt><dd>%s</dd>')) % r.metadata.recordnumber
            if r.metadata.copyright is not None and r.metadata.copyright != u'(This information requires login)':
                s += str(self.tr('<dt>Copyright owner:</dt><dd>%s</dd>')) % r.metadata.copyright
            if r.metadata.year != -1:
                s += str(self.tr('<dt>Released year:</dt><dd>%s</dd>')) % r.metadata.year

            s += "<p><b>" + str(self.tr(u"Seconds in total</b>: %s")) % r.clip['durationsecs']
            if len(r.subclips):
                s += str(self.tr(", in these subclips:")) + "<ol>"
                for sc in r.subclips:
                    s += u"<li>%s\" \u2013 %s-%s</li>" % (sc['durationsecs'], sc['in'], sc['out'])
                s += "</ol>"
            s += "</p></div><hr>"
        ui.textBrowser.setHtml(s)
        def _save():
            logging.debug("saving report for prf")
            try:
                loc = QFileDialog.getSaveFileName(PRFDialog, self.tr("Save PRF report (as HTML)"), '', self.tr('HTML document (*.html)'))
                if(len(str(loc)) == 0): # cancelled
                    return False
                f = open(str(loc), "wb")
                f.write(str(ui.textBrowser.toHtml()).encode('utf-8'))
                f.close()
                self.showstatus(self.tr('Prf report saved'))
            except IOError as e:
                self.showerror(e)
        ui.buttonBox.accepted.connect(_save)
        return PRFDialog.exec_()

    def auxReport(self):
        'Load the online AUX report form in a dialog'
        s = ""
        for r in self.itercheckedrows():
            if r.metadata.musiclibrary == "AUX Publishing":
                s = s + "%s x %s sek \r\n" % (r.metadata.identifier, r.clip['durationsecs'])
        AUXDialog = QDialog()
        ui = auxreport_ui.Ui_PlingPlongAUXDialog()
        ui.setupUi(AUXDialog)
        ui.webEngineView.loadStarted.connect(lambda: ui.progressBar.show())
        ui.webEngineView.loadProgress.connect(ui.progressBar.setValue)
        ui.webEngineView.loadFinished.connect(lambda: ui.progressBar.hide())
        page = ui.webEngineView.page()
        def callback(msg):
            logging.debug('callback from js land: %r', msg)
        def reportloaded(boolean):
            logging.debug("report loaded: %s", boolean)
            #page.runJavaScript("""document.title""", callback)
            page.runJavaScript("""document.querySelector('input[name="foretag"]').value='%s'""" % self.settings.value('AUX/foretag', "NRK <avdeling>"))
            page.runJavaScript("""document.querySelector('input[name="kontakt"]').value='%s'""" %  self.settings.value('AUX/kontakt', "<ditt eller prosjektleders navn>"))
            page.runJavaScript("""document.querySelector('input[name="telefon"]').value='%s'""" % self.settings.value('AUX/telefon', "<ditt eller prosjektleders telefonnummer>"))
            page.runJavaScript("""document.querySelector('input[name="email"]').value='%s'""" %  self.settings.value('AUX/email', "<ditt eller prosjektleders epostadresse>"))
            page.runJavaScript("""document.querySelector('input[name="produktionsnamn"]').value='%s'""" %  self.ui.prodno.text())
            page.runJavaScript("""document.querySelector('input[name="checkbox2"]').checked=1;""")
            logging.debug('setting aux report: %r', s)
            page.runJavaScript('''document.querySelector("textarea").value="%r";''' % s)
        ui.webEngineView.loadFinished.connect(reportloaded)
        def reportsubmit():
            logging.debug("report submitting")
            for el in ['foretag', 'kontakt', 'telefon', 'email', 'produktionsnamn']:
                htmlel = html.findFirstElement('input[name=%s]' % el)
                val = htmlel.evaluateJavaScript("this.value")
                #if len(val) == 0:
                    #self.showerror(str(self.tr('"%s" cannot be blank')) % el.title())
                    #return None
                self.settings.setValue('AUX/%s' % el, val)
            submit = html.findFirstElement('input[type=submit]')
            submit.setAttribute('style', 'visibility:show')
            submit.evaluateJavaScript('this.click()')
            #return AUXDialog.accept()
        ui.buttonBox.accepted.connect(reportsubmit)
        ui.webEngineView.load(Core.QUrl('http://auxlicensing.com/Forms/Express%20Rapportering/index.html'))
        return AUXDialog.exec_()

    def apollomusicReport(self):
        'Load the online Apollo Music (findthetune.com) report form in a dialog'

        # 1:
        # HTTP POST: http://www.findthetune.com/online/projects
        # model={"title":"ODOTEST","description":"Automatically created by odometer for report","children":false,"tracks":"428544,429492"}

        # collect all tracks and their apollomusic identifier
        _trackids={}
        for r in self.itercheckedrows(): # find the appropriate tracks
            if r.metadata.musiclibrary == 'ApolloMusic':
                _trackids[r.metadata.identifier.replace('apollotrack# ', '')] = r.clip['durationsecs']

        def createRequest(url): # helper method to add cookie to request
            r = QtNetwork.QNetworkRequest(Core.QUrl(url))
            r.setRawHeader('Cookie', self.settings.value('Apollocookie'))
            return r

        apollomusicDialog = QDialog()
        ui = auxreport_ui.Ui_PlingPlongAUXDialog()
        ui.setupUi(apollomusicDialog)
        apollomusicDialog.setWindowTitle(self.tr('Apollo Music report'))
        ui.webEngineView.loadStarted.connect(lambda: ui.progressBar.show())
        ui.webEngineView.loadProgress.connect(ui.progressBar.setValue)
        ui.webEngineView.loadFinished.connect(lambda: ui.progressBar.hide())
        requestq = [ # a last in, first out queue of requests
                     # ('http://www.findthetune.com/online/#projects', None), # the last request: show project page
                     (None, '<html><body><h1>Tracks added to Apollo Music Project</h1><p>Please log on to findthetune.com and finish your report</p></body></html>'),
                     ('http://www.findthetune.com/online/projects', # the first request: create a project with all tracks
                      {'model': json.dumps({'title':str(self.ui.prodno.text()) or datetime.datetime.now().isoformat(),
                                  'description':'Created by Pling Plong Odometer for easy reporting and big smiles',
                                  'children':False,
                                  'tracks': ",".join(_trackids.keys())
                                  })
                      }),
                    ]

        def next(): # get next url in queue
            try:
                _url, _data = requestq.pop()
            except IndexError:
                return # queue empty
            logging.debug("next url: %s, data:%s", _url, _data)
            if _url is None: # display _data, which is html
                ui.webEngineView.setHtml(_data)
                return

            r = createRequest(_url)

            if _data is None: # do a http GET
                ui.webEngineView.load(r, QtNetwork.QNetworkAccessManager.GetOperation)
            else: # do a http POST
                body = urllib.parse.urlencode(_data)
                r.setHeader(QtNetwork.QNetworkRequest.ContentTypeHeader, 'application/x-www-form-urlencoded')
                ui.webEngineView.load(r, QtNetwork.QNetworkAccessManager.PostOperation, body)

        ui.webEngineView.loadFinished.connect(next)
        next()
        return apollomusicDialog.exec_()

    def manualResolve(self):
        'Manually submit selected tracks to proper music provider for resolving'
        row = self.ui.detailsBox.currentRow
        def updateMetadata(filename, md):
            row.metadata = md
            self.showMetadata(row)
            row.setCheckState(0, Core.Qt.Checked)
            self.loadMetadata(row.audioname, md)

        filepath = self.audiofiles[row.audioname]
        manualPattern, result = QInputDialog.getText(self, self.tr('Music ID'),
            self.tr('Enter the correct music ID:'), QLineEdit.Normal, filepath.name)
        logging.debug('got manual music pattern: %r, dialog status %r', manualPattern, result)
        if not result:
            # dialog was cancelled 
            return None
        resolver = metadata.resolvers.findResolver(str(manualPattern))
        if isinstance(resolver, metadata.resolvers.ApollomusicResolver):
            logincookie = self.settings.value('Apollocookie', '')
            if not logincookie: # not logged in to apollo, big problem
                self.showerror(self.tr(u'Please log in to the Apollo Music service from the login menu'))
                self.logMessage(self.tr(u'Tried to manually resolve apollo track, but no logincookie found.'), msgtype=Status.WARNING)
                return # we cant continue
            else:
                resolver.setlogincookie(logincookie)
        resolver.trackResolved.connect(updateMetadata)
        # pop up a dialog to submit this filename to us, since it clearly is missing from our lists
        resolver.trackResolved.connect(self.submitMissingFilename) 
        resolver.trackProgress.connect(lambda fn, p: self.showProgress(fn, p))
        resolver.error.connect(lambda f, e: self.showerror(e, errtype='resover error %s' % resolver.name))
        self.workers.append(resolver) # keep track of the worker
        resolver.newresolve(str(manualPattern), filepath.pathurl) # put the worker to work async

    def submitMissingFilename(self, filename, resolvedmetadata=None):
        'Add filename and metadata to a public spreadsheet'
        _url = 'https://docs.google.com/spreadsheet/embeddedform?formkey=dEx0Z2xIWWJncHFxLVBQVWd2aW9xSUE6MQ'
        GdocsDialog = QDialog()
        ui = auxreport_ui.Ui_PlingPlongAUXDialog()
        ui.setupUi(GdocsDialog)
        GdocsDialog.setWindowTitle(self.tr('Submit missing filename'))
        ui.buttonBox.hide()
        ui.webEngineView.load(Core.QUrl(_url))
        ui.webEngineView.loadStarted.connect(lambda: ui.progressBar.show())
        ui.webEngineView.loadFinished.connect(lambda: ui.progressBar.hide())
        if resolvedmetadata is None:
            # take metadata from current row
            try:
                row = self.ui.detailsBox.currentRow
                resolvedmetadata = row.metadata
            except:
                resolvedmetadata = {}


        def reportloaded(boolean):
            logging.debug("report loaded: %s" % boolean)
            page = ui.webEngineView.page()
            page.runJavaScript("""document.getElementById('entry_0').value='%s'""" % filename)
            page.runJavaScript("""document.querySelector('textarea').value='%s'""" % str(vars(resolvedmetadata)))
        ui.webEngineView.loadFinished.connect(reportloaded)
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
        CreditsDialog = QDialog()
        ui = prfreport_ui.Ui_PlingPlongPRFDialog()
        ui.setupUi(CreditsDialog)
        s = s.replace('UniPPM', 'Universal Publishing Production Music')
        ui.textBrowser.setText(s)
        def _save():
            logging.debug("saving credits")
            try:
                loc = QFileDialog.getSaveFileName(CreditsDialog, self.tr("Save credits (as HTML)"), '', self.tr('HTML document (*.html)'))
                f = open(str(loc), "wb")
                f.write(str(ui.textBrowser.toHtml()).encode('utf-8'))
                f.close()
                self.showstatus(self.tr('End credits saved'))
            except IOError as e:
                self.showerror(e)
        ui.buttonBox.accepted.connect(_save)
        CreditsDialog.setWindowTitle(self.tr('Credits'))
        return CreditsDialog.exec_()

    def reportError(self):
        'Report program error to an online form'
        _url = 'https://goo.gl/forms/vasvfQWR1o1MMetj1'
        GdocsDialog = QDialog()
        ui = auxreport_ui.Ui_PlingPlongAUXDialog()
        ui.setupUi(GdocsDialog)
        ui.buttonBox.hide()
        GdocsDialog.setWindowTitle(self.tr('Report an error'))
        ui.webEngineView.load(Core.QUrl(_url))
        ui.webEngineView.loadStarted.connect(lambda: ui.progressBar.show())
        ui.webEngineView.loadProgress.connect(ui.progressBar.setValue)
        ui.webEngineView.loadFinished.connect(lambda: ui.progressBar.hide())
        page = ui.webEngineView.page()
        def reportloaded(boolean):
            logging.debug("reporterror loaded: %s", boolean)
            log = html.escape(''.join(self.log))
            page.runJavaScript('''var x = document.querySelector('textarea[aria-label="Programlogg"]'); if (x) {x.value="%s"};''' % log)
            page.runJavaScript("""document.querySelector('input[aria-label="Programversjon"]').value='%s'""" % self.getVersion())
        ui.webEngineView.loadFinished.connect(reportloaded)
        return GdocsDialog.exec_()

    def editDuration(self, row, col): # called when double clicked
        "Replace duration column with a spinbox to manually change value"
        logging.debug("editDuration: %s %s", row, col)
        if col != 2:
            return False
        editor = QDoubleSpinBox(parent=self.ui.clips)
        editor.setMaximum(10000.0)
        editor.setValue(row.clip['durationsecs'])
        editor.setSuffix('s')
        def editingFinished():
            val = float(editor.value())
            row.clip['durationsecs'] = val
            self.ui.clips.removeItemWidget(row, col)
            row.setText(2, str(val)+'s')
        editor.editingFinished.connect(editingFinished)
        self.ui.clips.setItemWidget(row, col, editor)

    def checkUsage(self):
        "To be reimplemented whenever there usage agreements change"
        return True # TODO: check FONO status, calculate Apollo pricing

    def gluon(self):
        #ALL  data loaded
        prodno = str(self.ui.prodno.text()).strip()
        #ok = self.checkUsage()
        if False: #not ok:
            msg = QMessageBox.critical(self, "Rights errors", "Not ok according to usage agreement")
        if len(prodno) == 0:
            msg = QMessageBox.critical(self, self.tr("Need production number"),
                                           self.tr("You must enter the production number"))
            self.ui.prodno.setFocus()
            return False
        self.gluon = metadata.gluon.Gluon()
        self.gluon.worker.reported.connect(self.gluonFinished)
        self.gluon.worker.reported.connect(self.removeLoadingbar)
        self.gluon.worker.error.connect(self.removeLoadingbar)
        self.gluon.worker.error.connect(self.msg)
        checked = list([r for r in self.rows.values() if r.checkState(0) == Core.Qt.Checked])
        self.gluon.resolve(prodno, checked)

    def gluonFinished(self, trackname, metadata):
        logging.debug("gluonFinished: %s -> %s", trackname, metadata)
        for nom, row in self.gluon.currejtList:
            logging.debug("%s %s", repr(os.path.splitext(nom)[0]), repr(str(trackname)))
            if os.path.splitext(nom)[0] == str(trackname):
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
            fil = str(f.toLocalFile())
            if fil.startswith('/.file/id='):
                # thanks for nothing, apple
                # https://stackoverflow.com/questions/37351647/get-path-from-os-x-file-reference-url-alias-file-file-id/37363026#37363026
                fil = subprocess.check_output(['osascript', '-e get posix path of my posix file "%s"' % fil]).strip()
            if os.path.isfile(fil) and os.path.splitext(fil.upper())[1] == ".XML":
                # TODO: also try to see if xmemliter accepts it?
                return fil
    except Exception as e:
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
    app = QApplication(argv)
    if f is not None: o = Odometer(app, f)
    else: o = Odometer(app)
    o.run(app)

if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    rungui(sys.argv)
