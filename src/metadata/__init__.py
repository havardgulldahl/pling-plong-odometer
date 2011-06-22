#!/usr/bin/env python
#-*- encoding: utf8 -*-

#__all__ = ['gluon',]
__name__ = 'metadata'

import sys, os.path, random, time, urllib, urllib2, urlparse, re, json
import PyQt4.QtCore as Core
import PyQt4.QtGui as Gui
import PyQt4.QtWebKit as Web
import PyQt4.Qt as Qt

import gluon

GLUON_HTTP_ENDPOINT="http://localhost:8000/gluon"

class TrackMetadata(object):
    def __init__(self,
                 filename=None,
                 musiclibrary=None,
                 title=None,
                 length=-1,
                 composer=None,
                 artist=None,
                 year=-1,
                 tracknumber=None,
                 albumname=None,
                 copyright=None,
                 lcnumber=None,
                 isrc=None,
                 ean=None,
                 catalogue=None,
                 label=None,
                 writer=None,
                 identifier=None,
                 ):
        self.filename = filename
        self.musiclibrary = musiclibrary
        self.title = title
        self.length = length # in seconds
        self.composer = composer
        self.artist = artist
        self.year = year
        self.tracknumber = tracknumber
        self.albumname = albumname
        self.copyright = copyright
        self.lcnumber = lcnumber
        self.isrc = isrc
        self.ean = ean
        self.catalogue = catalogue
        self.label = label
        self.writer = writer
        self.identifier = identifier

    def getmusicid(self):
        "Return a music id (DMA/Sonoton unique key) from filename"
        return os.path.splitext(self.filename)[0]

class GluonWorker(Core.QThread):
    loaded = Core.pyqtSignal([list], name="loaded")
    trackResolved = Core.pyqtSignal(unicode, TrackMetadata, name="trackResolved" )

    def __init__(self, parent=None):
        super(GluonWorker, self).__init__(parent)
        self.exiting = False

    def __del__(self):
        self.exiting = True
        self.wait()

    def load(self, prodno, clipnames):
        self.prodno = prodno
        self.clipnames = clipnames
        self.start()

    def run(self):
        gb = gluon.GluonBuilder(self.prodno, self.clipnames)
        xmlreq = gb.toxml()
        gp = gluon.GluonResponseParser()

        for metadata in gp.parse(self.request(xmlreq), factory=TrackMetadata):
            self.trackResolved.emit(metadata)

    def request(self, gluonpayload):
        "do an http post request with given gluon xml payload"
        data = urllib.urlencode( {"data":gluonpayload} )
        req = urllib.urlopen(GLUON_HTTP_ENDPOINT, data)
        response = req.read()
        print "response", response
        return response

class ResolverBase(Core.QObject):

    prefixes = [] # a list of file prefixes that this resolver recognizes
    name = 'general'
    trackResolved = Core.pyqtSignal(unicode, TrackMetadata, name="trackResolved" )
    trackProgress = Core.pyqtSignal(unicode, int, name="trackProgress" )

    def accepts(self, filename): 
        for f in self.prefixes:
            if unicode(filename).startswith(f):
                return True
        return False

    def testresolve(self, filename):
        self.filename = filename
        i = random.randint(0,1000)
        md = TrackMetadata( filename = unicode(filename),
                            musiclibrary = self.name, 
                            title = "Funky title %i" % i,
                            length = random.randint(30,500),
                            composer = "Mr. Composer %i" % i,
                            artist = "Mr. Performer %i" % i,
                            year = random.randint(1901,2011) )
        #time.sleep(random.random() * 4)
        self.trackResolved.emit(self.filename, md)
    
    def resolve(self, filename):
        self.filename = filename
        self.doc = webdoc(self.filename, self.url(filename), parent=None)
        self.doc.frame.loadFinished.connect(self.parse)
        self.doc.page.loadProgress.connect(self.progress)
        self.doc.load()

    def progress(self, i):
        self.trackProgress.emit(self.filename, i)

    def url(self, filename): # return url from filename
        tracknumber, fileext = os.path.splitext(filename)
        return self.urlbase % tracknumber

    def parse(self): 
        # reimplement this to emit a signal with a TrackMetadata object when found
        #self.trackResolved.emit(self.filename, md)
        pass
        

class SonotonResolver(ResolverBase):
    prefixes = ['SCD', ]
    name = 'Sonoton'
    urlbase = 'http://www.sonofind.com/search/html/popup_cddetails_i.php?cdkurz=%s&w=tr'
    urlbase = 'http://localhost:8000/sonoton.html?%s'

    def parse(self):
        metadatabox = unicode(self.doc.frame.findFirstElement("#csinfo").toInnerXml())
        metadata = TrackMetadata(filename=self.doc.filename, musiclibrary=self.name)
        try:
            duration = unicode(self.doc.frame.findAllElements("div[style='top:177px;']")[1].toInnerXml())
            mins, secs = [int(s.strip()) for s in duration.split(' ')[0].split(":")]
            metadata.length=mins*60+secs
        except:
            pass
        mapping = { 'Track Name': 'title', #REMEMBER LAST SUMMER
                    'Track Number': 'tracknumber', #SCD 821 20.0
                    'Composer': 'composer', #Mladen Franko
                    'Artist': 'artist', #(N/A for production music)
                    'Album Name': 'albumname',#ORCHESTRAL LANDSCAPES 2
                    'Catalogue number': 'catalogue', #821
                    'Label': 'label', #SCD
                    'Copyright Owner': 'copyright', #(This information requires login)
                    'LC Number': 'lcdnumber', #07573
                  }
        for l in metadatabox.split('\n'):
            if not len(l.strip()): continue
            meta, data = [s.strip() for s in l.split(':')]
            setattr(metadata, mapping[meta], data)
        #print vars(metadata)
        self.trackResolved.emit(self.filename, metadata)

def findResolver(filename):
    resolvers = [ SonotonResolver(), ]
    for resolver in resolvers:
        if resolver.accepts(filename):
            return resolver
    return False

class Gluon(Core.QObject):
    
    def __init__(self, parent=None):
        super(Gluon, self).__init__(parent)
        self.worker = GluonWorker()

    def resolve(self, prodno, clipnames):
        self.worker.load(prodno, clipnames)


class webdoc(Core.QObject):

    def __init__(self, filename, url, parent=None):
        super(webdoc, self).__init__(parent)
        self.filename = filename
        self.url = url
        self.page = Web.QWebPage(self)
        self.frame = self.page.mainFrame()
        self.settings = self.page.settings()
        self.settings.setAttribute(Web.QWebSettings.JavascriptEnabled, False)
        self.settings.setAttribute(Web.QWebSettings.AutoLoadImages, False)

    def load(self):
        print "loading url: ", self.url
        self.frame.load(Core.QUrl(self.url))

if __name__ == '__main__':
    #filename = 'SCD082120.wav'
    filename = 'NONRT900497LP0205_xxx.wav'
    app = Gui.QApplication(sys.argv)
    mq = findResolver(filename)
    if not mq:
        sys.exit(1)
    mq.trackResolved.connect(lambda f,m: app.quit())
    resolve = mq.resolve(filename)
    app.exec_()
