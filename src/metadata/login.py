#-*- encoding: utf8 -*-
# This file is part of odometer by Håvard Gulldahl <havard.gulldahl@nrk.no>
# (C) 2016
#
# login.py: login routines for different metadata providers

import json
import urllib
import logging
import time

import PyQt4.QtCore as Core
import PyQt4.QtNetwork as QtNetwork
import PyQt4.Qt as Qt

from core.workers import UrlWorker

class ProviderLogin(Core.QObject):
    "Everything you need to log in to different metadata providers"
    # signals
    error = Core.pyqtSignal(unicode, name="error" ) # error message
    warning = Core.pyqtSignal(unicode, name="warning") # warning message
    loginFailed = Core.pyqtSignal(unicode, name="loginFailed" ) # explanation
    loginSuccess = Core.pyqtSignal(unicode, name="loginSuccess" ) # logincookie
    loginInProgress = Core.pyqtSignal(bool, name="loginInProgress" ) # True/False

    def __init__(self, provider, parent=None):
        super(ProviderLogin, self).__init__(parent)
        self.provider = provider
        self.settings = Core.QSettings('nrk.no', 'Pling Plong Odometer')

    def loginWithCachedPasswords(self):
        'Start login procedure with username and password from settings'
        if self.provider == 'AUX':
            self.login(unicode(self.settings.value('AUXuser', '').toString()),
                       unicode(self.settings.value('AUXpassword', '').toString()))
        elif self.provider == 'APOLLO':
            self.login(unicode(self.settings.value('Apollouser', '').toString()),
                       unicode(self.settings.value('Apollopassword', '').toString()))
        elif self.provider == 'UNIPPM':
            self.login(unicode(self.settings.value('Universaluser', '').toString()),
                       unicode(self.settings.value('Universalpassword', '').toString()))
        elif self.provider == 'UPRIGHT':
            self.login(unicode(self.settings.value('Uprightuser', '').toString()),
                       unicode(self.settings.value('Uprightpassword', '').toString()))
        elif self.provider == 'EXTREME':
            self.login(unicode(self.settings.value('Extremeuser', '').toString()),
                       unicode(self.settings.value('Extremepassword', '').toString()))

    def login(self, username, password):
        "start login procedure. connect to signals to get updates and results"
        self.username = username
        self.password = password

        def storeCookie(service, data):
            cookie = data.info().get('Set-Cookie', None)
            logging.debug("Storing cookie for %s: %s", service, cookie)
            logging.debug("Service returned %s", data.getcode())
            #logging.debug("Headers: %s", data.info())
            b = data.read()
            #logging.debug("body: %s", b)
            login = False
            if service == 'AUX':
                result = json.loads(b)
                if result['ax_success'] == 1:
                    self.settings.setValue('AUXcookie', cookie)
                    self.loginSuccess.emit(cookie)
                else:
                    m = '%s login failed: %s' % (service, result['ax_errmsg'])
                    logging.warning(m)
                    self.error.emit(m)
            elif service == 'Apollo':
                result = json.loads(b)
                if result['success'] == 1:
                    self.settings.setValue('Apollocookie', cookie)
                    self.loginSuccess.emit(cookie)
                else:
                    m = '%s login failed: %s' % (service, result['message'])
                    logging.warning(m)
                    self.error.emit(m)
            elif service == 'Upright':
                if result['success'] == 1:
                    self.settings.setValue('Uprightcookie', cookie)
                    self.loginSuccess.emit(cookie)
                else:
                    m = '%s login failed: %s' % (service, result['message'])
                    logging.warning(m)
                    self.error.emit(m)
            elif service == 'Universal':
                # if password matched, we get
                #  <div class="result" ssoToken="xxx">True</div>
                # but if password failed, instead we get
                # <div class="error failedlogin">You have 5 password attempts remaining.</div>
                if b.startswith('''<div class="result" ssoToken="'''):
                    self.settings.setValue('Universalcookie', cookie)
                    self.loginSuccess.emit(cookie)
                else:
                    m = '%s login failed: %s' % (service, b)
                    logging.warning(m)
                    self.error.emit(m)
            elif service == 'Extreme':
                result = json.loads(b)
                try:
                    success = result['login']['error'] == 'WRONG_PASSWORD'
                except KeyError:
                    success = True
                if not success:
                    m = '%s login failed: %s' % (service, result)
                    logging.warning(m)
                    self.error.emit(m)
                else:
                    self.settings.setValue('Extremecookie', cookie)
                    self.loginSuccess.emit(cookie)


            #logging.debug("settings: %r", list(self.settings.allKeys()))

            stopBusy()

        def failed(ex):
            logging.warning("faile! %r", ex)
            self.error.emit(ex)
            stopBusy()
        def startBusy():
            self.loginInProgress.emit(True)
        def stopBusy():
            self.loginInProgress.emit(False)
        def AUXlogin():
            logging.info('login to aux')
            startBusy()
            async = UrlWorker()
            url = 'http://search.auxmp.com//search/html/ajax/axExtData.php'
            getdata = urllib.urlencode({'ac':'login',
                                        'country': 'NO',
                                        'sprache': 'en',
                                        'ext': 1,
                                        '_dc': int(time.time()),
                                        'luser':username,
                                        # from javascript source: var lpass = Sonofind.Helper.md5(pass + "~" + Sonofind.AppInstance.SID);

                                        'lpass':password})
            async.load('%s?%s' % (url, getdata), timeout=7)
            async.finished.connect(lambda d: storeCookie('AUX', d))
            async.failed.connect(failed)
        def Apollologin():
            logging.info('login to apollo')
            startBusy()
            async = UrlWorker()
            url = 'http://www.findthetune.com/online/login/ajax_authentication/'
            postdata = {'user':username,
                        'pass':password}
            async.load(url, timeout=7, data=postdata)
            async.finished.connect(lambda d: storeCookie('Apollo', d))
            async.failed.connect(failed)
        def Uprightlogin():
            logging.info('login to Upright')
            startBusy()
            async = UrlWorker()
            url = 'http://www.findthetune.com/online/login/ajax_authentication/'
            getdata = urllib.urlencode({'ac':'login',
                                        'country': 'NO',
                                        'sprache': 'en',
                                        'ext': 1,
                                        '_dc': int(time.time()),
                                        'luser':username,
                                        # from javascript source: var lpass = Sonofind.Helper.md5(pass + "~" + Sonofind.AppInstance.SID);

                                        'lpass':password})
            postdata = {'user':username,
                        'pass':password}
            async.load(url, timeout=7, data=postdata)
            async.finished.connect(lambda d: storeCookie('Upright', d))
            async.failed.connect(failed)
        def Universallogin():
            logging.info('login to Universal PPM')
            startBusy()
            async = UrlWorker()
            url = 'http://www.unippm.se/Feeds/commonXMLFeed.aspx'
            getdata = urllib.urlencode({'method': 'Login',
                                        'user':username,
                                        'password':password,
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
                body = resp.read()
                logging.debug('auth: %s', body)
                self.settings.setValue('ExtremeAUTH', json.loads(body)['env']['API_AUTH'])
            startBusy()
            env = UrlWorker()
            env.failed.connect(failed)
            env.finished.connect(getauth)
            #env.finished.connect(lambda d: Extremelogin())
            env.finished.connect(lambda d: Core.QTimer.singleShot(2, Extremelogin))

            env.load('https://www.extrememusic.com/env')

        def Extremelogin():
            logging.info('login to Extreme Music')
            async = UrlWorker()
            url = 'https://lapi.extrememusic.com/accounts/login'
            postdata = json.dumps({'username': username,
                                   'password': password,
                                   'remember_me': False})
            auth = {'X-API-Auth': unicode(self.settings.value('ExtremeAUTH', '').toString()),
                    'Content-Type':'application/json; charset=utf-8'}
            async.load(url, timeout=7, data=postdata, headers=auth)
            async.finished.connect(lambda d: storeCookie('Extreme', d))
            async.failed.connect(failed)

        def start():
            entry = {'AUX': AUXlogin,
                     'APOLLO': Apollologin,
                     'UPRIGHT': Uprightlogin,
                     'UNIPPM': Universallogin,
                     'EXTREME': Extremeauth,
                     }
            provider = entry[self.provider]()

        #Core.QTimer.singleShot(0.1, start)
        start()
