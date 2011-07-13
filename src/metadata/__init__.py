#-*- encoding: utf8 -*-
# This file is part of odometer by Håvard Gulldahl <havard.gulldahl@nrk.no>
# (C) 2011

#__all__ = ['gluon',]
#__name__ = 'metadata'

import os
import time
import cPickle as pickle
import sys, os.path, random, time, urllib, urllib2, urlparse, re
import json, StringIO
import xml.etree.ElementTree as ET
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
        self.productionmusic = False
        self._created = time.mktime(time.localtime())

    def getmusicid(self):
        "Return a music id (DMA/Sonoton unique key) from filename"
        print repr(self.filename)
        if self.musiclibrary == "DMA":
            return DMAResolver.musicid(self.filename)
        elif self.musiclibrary == "Sonoton":
            return SonotonResolver.musicid(self.filename)
        else:
            return ResolverBase.musicid(self.filename)

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
        response = StringIO.StringIO(self.request(xmlreq))

        for metadata in gp.parse(response, factory=TrackMetadata):
            self.trackResolved.emit(metadata.identifier, metadata)

    def request(self, gluonpayload):
        "do an http post request with given gluon xml payload"
        data = urllib.urlencode( {"data":gluonpayload} )
        req = urllib.urlopen(GLUON_HTTP_ENDPOINT, data)
        response = req.read()
        return response

class DMAWorker(Core.QThread):
    trackResolved = Core.pyqtSignal(TrackMetadata, name="trackResolved" )
    progress = Core.pyqtSignal(int, name="progress" )

    def __init__(self, parent=None):
        super(DMAWorker, self).__init__(parent)

    def __del__(self):
        self.wait()

    def load(self, filename):
        self.filename = filename
        self.musicid = DMAResolver.musicid(filename)
        self.start()

    def run(self):
        #http://dma/trackDetailsPage.do?muobId=NONRT023272CD0010
        # -> internal muobid
        # http://dma/playerInformation.do?muobId=592113247
        url = 'http://dma/trackDetailsPage.do?muobId='+self.musicid
        data = urllib.urlopen(url).read(512)
        rex = re.compile(r'NRK.action.onMuobResultClick\((\d+)\);')
        m = rex.search(data)
        muobid = m.group(1)
        self.progress.emit(50)
        print 'http://dma/playerInformation.do?muobId='+muobid
        xml = urllib.urlopen('http://dma/playerInformation.do?muobId='+muobid).read()
        tree = ET.parse(StringIO.StringIO(xml.strip()))
        md = TrackMetadata(filename=self.filename, identifier=self.musicid, musiclibrary='DMA')
        md.title = tree.find('./track/title').text
        md.composer = 'Kommer fra DMA'
        md.label = 'Kommer fra DMA'
        md.artist = '; '.join([a.text.strip() for a in tree.iterfind('./track/artists/artist/name')])
        md.composer = 'Kommer fra DMA'
        md.copyright = 'Kommer fra DMA'
        self.progress.emit(100)
        self.trackResolved.emit(md)

class EchonestWorker(Core.QThread):
    trackResolved = Core.pyqtSignal(TrackMetadata, name="trackResolved" )
    progress = Core.pyqtSignal(int, name="progress" )
    finished = Core.pyqtSignal(name='finished')

    def __init__(self, parent=None):
        super(EchonestWorker, self).__init__(parent)

    def __del__(self):
        self.wait()

    def load(self, filename):
        self.filename = filename
        self.start()

    def run(self):
        fingerprint = echonest.identify(self.filename)
        print fingerprint
        self.finished.emit()
        if fingerprint['response']['status']['code'] != 0: # errors
            return False
        echo = fingerprint['response']['track']
        md = TrackMetadata(filename=self.filename, musiclibrary='Unknown')
        md.identifier = echo['id']
        md.title = echo['title']
        md.artist = echo['artist']
        md.album = echo['release']
        print vars(md)
        self.trackResolved.emit(md)

class ResolverBase(Core.QObject):

    prefixes = [] # a list of file prefixes that this resolver recognizes
    name = 'general'
    trackResolved = Core.pyqtSignal(unicode, TrackMetadata, name="trackResolved" )
    trackProgress = Core.pyqtSignal(unicode, int, name="trackProgress" )
    cacheTimeout = 60*60*24*2 # how long are cached objects valid? in seconds

    def __init__(self, parent=None):
        super(ResolverBase, self).__init__(parent)
        self.trackResolved.connect(lambda f,md: self.cache(md))

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
        md = self.fromcache()
        if md is not None:
            self.trackResolved.emit(self.filename, md)
            return
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

    @staticmethod
    def musicid(filename):
        "Returns musicid from filename. Reimplement for different resolvers"
        return os.path.splitext(filename)[0]

    def cache(self, metadata):
        "Add metadata for a filename to a local cache to prevent constant network lookups"
        loc = self.cachelocation()
        if self.incache() and self.fromcache() is not None:
            print "CACHE HIT", loc
            return False
        print "caching metadata to ", loc
        f = open(loc, "wb")
        f.write(pickle.dumps(metadata))
        f.close()
        return True

    def fromcache(self):
        "Get metadata from local cache, or None if it's not cached or too old"
        try:
            loc = open(self.cachelocation(), "rb")
        except IOError: #file doesn't exist -> not cached
            return None
        metadata =  pickle.loads(loc.read())
        loc.close()
        if metadata._created + self.cacheTimeout < time.mktime(time.localtime()):
            return None
        return metadata

    def incache(self):
        "Checks to see if the metadata is in cache"
        return os.path.exists(self.cachelocation())

    def cachelocation(self):
        "Return a dir suitable for storage"
        dir = Gui.QDesktopServices.storageLocation(Gui.QDesktopServices.CacheLocation)
        ourdir = os.path.join(unicode(dir), 'no.nrk.odometer')
        if not os.path.exists(ourdir):
           os.mkdir(ourdir) 
        return os.path.join(ourdir, self.filename)

class DMAResolver(ResolverBase):
    # Fra gammelt av har vi disse kodene:
    # NRKO_
    # NRKT_
    # Fra en gang etter 2009 brukes disse:
    # NONRO
    # NONRT
    # NONRE
    # 
    prefixes = ['NRKO_', 'NRKT_', 'NONRO', 'NONRT', 'NONRE' ]
    name = 'DMA'

    @staticmethod
    def musicid(filename):
        rex = re.compile(r'^((NRKO_|NRKT_|NONRO|NONRT|NONRE)\d{6}CD\d{4})')
        g = rex.search(filename)
        return g.group(1)

    def xresolve(self, filename):
        # return placeholder metadata
        # to be replaced by a gluon/DMA lookup later in the process
        self.filename = filename
        dummymetadata = TrackMetadata(filename=unicode(filename),
                                      musiclibrary='DMA',
                                      title = 'Kommer fra DMA',
                                      composer = 'Kommer fra DMA',
                                      artist = 'Kommer fra DMA',
                                      year = 2011,
                                      length = 23)
        self.progress(100)
        self.trackResolved.emit(self.filename, dummymetadata)

    def resolve(self, filename):
        self.filename = filename
        md = self.fromcache()
        if md is not None:
            self.trackResolved.emit(self.filename, md)
            return
        self.worker = DMAWorker()
        self.worker.progress.connect(self.progress)
        self.worker.trackResolved.connect(lambda md: self.trackResolved.emit(self.filename, md))
        self.worker.load(filename)

    @staticmethod
    def quicklookup(ltype, substring):
        url = 'http://dma/getUnitNames.do?type=%s&limit=10' % ltype
        data = urllib.urlencode( ('in', substring ), )
        return json.loads(urllib.urlopen(url, data).read())

    @staticmethod
    def performerlookup(substring):
        return self.quicklookup('performer', substring)

    @staticmethod
    def creatorlookup(substring):
        return self.quicklookup('creator', substring)

class SonotonResolver(ResolverBase):
    prefixes = ['SCD', ]
    name = 'Sonoton'
    urlbase = 'http://www.sonofind.com/search/html/popup_cddetails_i.php?cdkurz=%s&w=tr'
    #urlbase = 'http://localhost:8000/sonoton.html?%s'

    def parse(self):

        return self.testresolve(self.filename)
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
        metadata.productionmusic = True
        metadata.label = 'Sonoton'
        self.trackResolved.emit(self.filename, metadata)

class EchonestResolver(ResolverBase):
    "Acoustic fingerprinting using echoprint.me"
    prefixes = ['*',]
    name = 'echonest'
    stop = False

    def accepts(self, filename):
        return True # echonest is a generic fingerprinter

    def resolve(self, filename, timeout=40):
        self.filename = filename
        self.worker = EchonestWorker()
        #self.worker.progress.connect(self.progress)
        #self.worker.finished.connect(lambda: self.stop = True)
        self.worker.finished.connect(self.finished)
        print self.worker.finished
        self.worker.trackResolved.connect(self.resolved)
        self.worker.load(filename)
        i = 1
        while not self.stop and i < timeout:
            print "tick ", i
            self.progress(i)
            i += 3
            time.sleep(3)
        if i > timeout:
            self.finished()
            self.trackResolved.emit(self.filename, TrackMetadata())
            return False

    def finished(self):
        print "finished"
        self.progress(100)
        self.stop = True

    def resolved(self, metadata):
        print "resolved"
        self.stop = True
        self.trackResolved.emit(self.filename, md)

def findResolver(filename):
    resolvers = [ DMAResolver(), SonotonResolver(), ]
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

def mdprint(f,m):
    print "filename: ",f
    print "metadata: ", vars(m)

if __name__ == '__main__':
    #filename = 'SCD082120.wav'
    filename = 'NONRT900497LP0205_xxx.wav'
    app = Gui.QApplication(sys.argv)
    mq = EchonestResolver()
    mq.trackResolved.connect(lambda f,m: mdprint)
    mq.trackResolved.connect(lambda f,m: app.quit())
    mq.trackResolved.connect(lambda f,m: app.quit())
    resolve = mq.resolve(sys.argv[1])
    app.exec_()
