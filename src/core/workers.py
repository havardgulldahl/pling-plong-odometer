#-*- encoding: utf8 -*-
# This file is part of odometer by Håvard Gulldahl <havard.gulldahl@nrk.no>
# (C) 2016
#
# workers.py: a collection of different threaded workers

import sys
import urllib
from six.moves.urllib import request
import logging


import PyQt5.QtCore as Core
import PyQt5.QtNetwork as QtNetwork
import PyQt5.Qt as Qt

from xmeml import iter as xmemliter


class UrlWorker(Core.QThread):
    finished = Core.pyqtSignal(object)
    failed = Core.pyqtSignal(tuple)

    def __init__(self, parent=None):
        super(UrlWorker, self).__init__(parent)
        self.exiting = False

    def __del__(self):
        self.exiting = True
        self.wait()

    def load(self, url, timeout=10, data=None, headers=None):
        self.url = url
        self.timeout = timeout
        if data is not None:
            logging.warning("urlworker load data %r", data)
            if isinstance(data, basestring):
                self.data = data
            else:
                self.data = urllib.urlencode(data)
        else:
            self.data = None
        self.headers = {'X_REQUESTED_WITH' :'XMLHttpRequest',
           'ACCEPT': 'application/json, text/javascript, */*; q=0.01',}
        self.headers.update(headers or {})
        logging.debug('UrlWorker headers: %r', self.headers)
        self.start()

    def run(self):
        logging.info('urlworker working on url %s with data %s', self.url, self.data)
        try:
            req = request.Request(self.url, self.data, headers=self.headers)
            con = request.urlopen(req, timeout=self.timeout)

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