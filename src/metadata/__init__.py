#-*- encoding: utf8 -*-
# This file is part of odometer by Håvard Gulldahl <havard.gulldahl@nrk.no>
# (C) 2011-2012

import os
import time
import cPickle as pickle
import sys, os.path, random, time, urllib, urllib2, urlparse, re
import json, StringIO
import hashlib
import demjson
import xml.etree.ElementTree as ET
import PyQt4.QtCore as Core
import PyQt4.QtGui as Gui
import PyQt4.QtWebKit as Web
import PyQt4.Qt as Qt
import mutagen

import gluon

GLUON_HTTP_REPORT="http://localhost:8000/gluon"
#GLUON_HTTP_LOOKUP="http://localhost:8000/lookup/"
GLUON_HTTP_LOOKUP="http://mamcdma02/DMA/"



class TrackMetadata(object):
    def __init__(self,
                 filename=None,
                 musiclibrary=None,
                 title=None,
                 length=-1,
                 composer=None,
                 artist=None,
                 year=-1,
                 recordnumber=None,
                 albumname=None,
                 copyright=None,
                 lcnumber=None,
                 isrc=None,
                 ean=None,
                 catalogue=None,
                 label=None,
                 lyricist=None,
                 identifier=None,
                 ):
        self.filename = filename
        self.musiclibrary = musiclibrary
        self.title = title
        self.length = length # in seconds
        self.composer = composer
        self.artist = artist
        self.year = year
        self.recordnumber = recordnumber
        self.albumname = albumname
        self.copyright = copyright
        self.lcnumber = lcnumber # library of congress id
        self.isrc = isrc # International Standard Recording Code
        self.ean = ean # ean-13 (barcode)
        self.catalogue = catalogue
        self.label = label
        self.lyricist = lyricist
        self.identifier = identifier # system-specific identifier
        self.productionmusic = False
        self._retrieved = time.mktime(time.localtime())

    def getmusicid(self):
        "Return a music id (DMA/Sonoton unique key) from filename"
        if self.musiclibrary == "DMA":
            return DMAResolver.musicid(self.filename)
        elif self.musiclibrary == "Sonoton":
            return SonotonResolver.musicid(self.filename)
        else:
            return ResolverBase.musicid(self.filename)

class GluonReportWorker(Core.QThread):
    reported = Core.pyqtSignal(name="reported") # success
    error = Core.pyqtSignal(unicode, name="error") # failure, with error message

    def __init__(self, parent=None):
        super(GluonReportWorker, self).__init__(parent)

    def __del__(self):
        self.wait()

    def load(self, prodno, clips):
        self.prodno = prodno
        self.clips = clips
        self.start()

    def run(self):
        gb = gluon.GluonReportBuilder(self.prodno, self.clips)
        xmlreq = gb.toxml()
        response = self.request(xmlreq)
        if response is None:
            self.error('Could not report to Gluon. Are you connected to the network?')

        if response.getvalue() == "OK":
            self.reported.emit()
        else:
            self.error.emit("Some error occured")

    def request(self, gluonpayload):
        "do an http post request with given gluon xml payload"
        data = urllib.urlencode( {"data":gluonpayload} )
        try:
            req = urllib.urlopen(GLUON_HTTP_REPORT, data)
        except Exception, (e):
            self.error.emit(e)
        if req.getcode() in (400, 401, 403, 404, 500):
            self.error.emit('Got error message %s from Gluon server when reporting' % req.getcode())
            return None

        response = req.read()
        return response

class GluonLookupWorker(Core.QThread):
    trackResolved = Core.pyqtSignal(TrackMetadata, name="trackResolved" )
    trackFailed = Core.pyqtSignal(name="trackFailed" )
    progress = Core.pyqtSignal(int, name="progress")
    error = Core.pyqtSignal(unicode, name="error")

    def __init__(self, parent=None):
        super(GluonLookupWorker, self).__init__(parent)

    def __del__(self):
        self.wait()

    def load(self, filename):
        self.filename = filename
        self.musicid = DMAResolver.musicid(filename)
        self.start()

    def run(self):
        response = self.request(self.musicid)
        if response is None:
            return 
        self.progress.emit(50)
        gp = gluon.GluonMetadataResponseParser()
        metadata = gp.parse(StringIO.StringIO(response), factory=TrackMetadata)
        self.progress.emit(70)
        self.trackResolved.emit(metadata)
        self.progress.emit(100)

    def request(self, musicid):
        "do an http post request with given gluon xml payload"
        req = urllib.urlopen(GLUON_HTTP_LOOKUP +  musicid + '.xml')
        if req.getcode() in (404, 403, 401, 400, 500):
            self.trackFailed.emit()
            self.error.emit('Tried to look up %s, but got %s' % (musicid, req.getcode()))
            return None
        response = req.read()
        return response

class DMAWorker(Core.QThread):
    trackResolved = Core.pyqtSignal(TrackMetadata, name="trackResolved" )
    trackFailed = Core.pyqtSignal(name="trackFailed" ) 
    progress = Core.pyqtSignal(int, name="progress" )
    error = Core.pyqtSignal(unicode, name="error") # unicode : error msg

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
        # -> internal muobid and track details
        # http://dma/productDetailsJson.do, POST muobId=592113247
        # -> album ('product') details
        url = 'http://dma/trackDetailsPage.do?muobId='+self.musicid
        try:
            data = urllib.urlopen(url).read(512)
        except IOError:
            self.error.emit(u'Could not open DMA. Not connected to the network?')
            self.trackFailed.emit()
            return 
        rex = re.compile(r'NRK.action.onMuobResultClick\((\d+)\);')
        m = rex.search(data)
        muobid = m.group(1)
        self.progress.emit(33)
        try:
            #rexstart = re.search(r'var\ albumRecs\ =\ \[', data).end()
            #rexend = re.compile(r'];\s*trackRecord.albums\ =\ albumRecs;', re.M).search(data).start()
            rexstart = re.search(r"CM.app.cache\('track\.details\.\d+',", data).end()
            rexend = re.compile(r'\);\s*function\ callAddToWindow\(\){', re.M).search(data).start()
        except AttributeError:
            self.progress.emit(5)
            return None
        metadata = demjson.decode(data[rexstart:rexend])
        print metadata
        self.progress.emit(66)
        _albumname = '; '.join([x['name'] for x in metadata['albums']])
        if not _albumname:
            _albumname = '; '.join([x['name'] for x in metadata['products']])
        md = TrackMetadata(filename=self.filename,
                           identifier=self.musicid,
                           musiclibrary='DMA',
                           title=metadata['title'],
                           artist="; ".join([x['name'] for x in metadata['artists']]),
                           year=metadata['releaseYear'],
                           albumname=_albumname,
                           composer='; '.join([x['name'] for x in metadata['composer']]),
                           label='Må hentes i DMA',
                           copyright='Må hentes i DMA')

        try:
            recordid = metadata['media'][0]['id']
            recorddetails = urllib.urlopen('http://dma/productDetailsJson.do', 
                                     {'muobId': recordid})
            recordmetadata = demjson.decode(details.read())['records'][0]
            print recordmetadata
            md.label = recordmetadata['recordLabel'][0]['label']
            md.lcnumber = recordmetadata['recordLabel'][0]['recordLabelNr']
        except IOError:
            self.error.emit(u'Could not open DMA. Sorry. Please look %s up yourself.' % self.musicid)
            self.trackFailed.emit(self.filename)
        except:
            # something failed, but we have almost everything we need
            # TODO: popup an error dialog about this
            self.error.emit(u'Resolving %s failed because - well, who knows why? Biscuit?' % self.musicid)
            self.trackFailed.emit(self.filename)

        #xml = urllib.urlopen('http://dma/playerInformation.do?muobId='+muobid).read()
        #tree = ET.parse(StringIO.StringIO(xml.strip()))
        #md = TrackMetadata(filename=self.filename, identifier=self.musicid, musiclibrary='DMA')
        #md.title = tree.find('./track/title').text
        #md.composer = 'Kommer fra DMA'
        #md.label = 'Kommer fra DMA'
        #md.artist = '; '.join([a.text.strip() for a in tree.iterfind('./track/artists/artist/name')])
        #md.composer = 'Kommer fra DMA'
        #md.copyright = 'Kommer fra DMA'
        self.progress.emit(100)
        self.trackResolved.emit(md)

class ResolverBase(Core.QObject):

    prefixes = [] # a list of file prefixes that this resolver recognizes
    name = 'general'
    error = Core.pyqtSignal(unicode, name="error" ) # error message
    trackFailed = Core.pyqtSignal(unicode, name="trackFailed" ) # filename
    trackResolved = Core.pyqtSignal(unicode, TrackMetadata, name="trackResolved" ) # filename, metadataobj
    trackProgress = Core.pyqtSignal(unicode, int, name="trackProgress" ) # filename, progress 0-100
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
    
    def resolve(self, filename, fromcache=True):
        self.filename = filename
        if fromcache:
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
        return self.urlbase % self.musicid(filename)

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
            #print "CACHE HIT", loc
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
        if metadata._retrieved + self.cacheTimeout < time.mktime(time.localtime()):
            return None
        return metadata

    def incache(self):
        "Checks to see if the metadata is in cache"
        return os.path.exists(self.cachelocation())

    def cachelocation(self):
        "Return a dir suitable for storage"
        dir = Gui.QDesktopServices.storageLocation(Gui.QDesktopServices.CacheLocation)
        ourdir = os.path.join(os.path.abspath(unicode(dir)), 'no.nrk.odometer')
        if not os.path.exists(ourdir):
           os.makedirs(ourdir) 
               #return os.path.join(ourdir, self.filename)
        try:
            return os.path.join(ourdir, hashlib.md5(self.filename.encode('utf8')).hexdigest())
        except UnicodeEncodeError:
            print repr(self.filename), type(self.filename)

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
    #cacheTimeout = 1

    @staticmethod
    def musicid(filename):
        rex = re.compile(r'^((NRKO_|NRKT_|NONRO|NONRT|NONRE)\d{6}(CD|CS|HD|LP)\d{4})')
        g = rex.search(filename)
        try:
            return g.group(1)
        except AttributeError: #no match
            print "oh noes, could not understand this dma id:",filename
            return None

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

    def resolve(self, filename, fromcache=True):
        self.filename = filename
        if fromcache:
            md = self.fromcache()
            if md is not None:
                self.trackResolved.emit(self.filename, md)
                return
        self.worker = GluonLookupWorker()
        self.worker.progress.connect(self.progress)
        self.worker.trackResolved.connect(lambda md: self.trackResolved.emit(self.filename, md))
        self.worker.trackFailed.connect(lambda: self.trackFailed.emit(self.filename))
        self.worker.error.connect(lambda msg: self.error.emit(msg))
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
    prefixes = [ 'SCD', 'SAS', 'STT', 'SDCV',]
    name = 'Sonoton'
    urlbase = 'http://www.sonofind.com/search/html/popup_cddetails_i.php?cdkurz=%s&w=tr'
    #urlbase = 'http://localhost:8000/sonoton.html?%s'
    labelmap = {
                'SCD':'Sonoton',
                'SAS':'Sonoton Authentic Series',
                'STT':'Sonoton Trailer Tracks',
                'SDCV':'Sonoton Virtual CDs',
               }

    @staticmethod
    def musicid(filename):
        """Returns musicid from filename. 

        SCD076819.wav -> SCD076819
        SCD076819.wav -> SCD076819
        STT002015_NAME_OF_SONG -> STT002015

        """
        rex = re.compile(r'^((%s)\d{6})' % '|'.join(self.prefixes))
        g = rex.search(filename)
        try:
            return g.group(1)
        except AttributeError: #no match
            print "oh noes, could not understand this Sonoton id:",filename
            return None

    def getlabel(self, hint):
        "Return a nice, verbose name for a label, if it is known (returns hint otherwise)"
        return self.labelmap.get(hint, hint) # return hint verbatim if it's not in map

    def parse(self):
        metadatabox = unicode(self.doc.frame.findFirstElement("#csinfo").toInnerXml())
        if len(metadatabox.strip()) == 0:
            self.trackFailed.emit(self.filename)
            self.error.emit("Could not get info on %s. Lookup failed" % self.filename)
            return
        metadata = TrackMetadata(filename=self.doc.filename, musiclibrary=self.name)
        try:
            duration = unicode(self.doc.frame.findAllElements("div[style='top:177px;']")[1].toInnerXml())
            mins, secs = [int(s.strip()) for s in duration.split(' ')[0].split(":")]
            metadata.length=mins*60+secs
        except:
            pass
        mapping = { 'Track Name': 'title', #REMEMBER LAST SUMMER
                    'Track Number': 'recordnumber', #SCD 821 20.0
                    'Composer': 'composer', #Mladen Franko
                    'Artist': 'artist', #(N/A for production music)
                    'Album Name': 'albumname',#ORCHESTRAL LANDSCAPES 2
                    'Catalogue number': 'catalogue', #821
                    'Label': '_label', #SCD
                    'Copyright Owner': 'copyright', #(This information requires login)
                    'LC Number': 'lcnumber', #07573 - Library of Congress id
                  }
        for l in metadatabox.split('\n'):
            if not len(l.strip()): continue
            meta, data = [s.strip() for s in l.split(':')]
            setattr(metadata, mapping[meta], data)
        metadata.productionmusic = True
        metadata.label = self.getlabel(metadata._label)
        self.trackResolved.emit(self.filename, metadata)

class AUXResolver(SonotonResolver):
    prefixes = ['AUXMP_', 'CNS', 'DK', 'ECM', 'FWM', 'HGR', 'ISCD', 'JW', 'CAND', 'PPM', 'SONIA',
        'SCD', 'SCDC', 'SAS', 'STT', 'STTV', 'SCDV', 'STRIP', 'TM', 'TREDE', 'TSU', 'AD', 'BAC',
        'BM', 'CCS', 'CCCD', 'CAVCD', 'CAVT', 'CLC', 'CNS',]
    labelmap = {
                'AD':'Adapt',
                'BAC':'Big and Clever Music',
                'BM':'Brilliant Music',
                'CCS':'Cavendish Classic Series',
                'CCCD':'Cavendish Classic',
                'CAVCD':'Cavendish Music',
                'CAVT':'Cavendish Trailers',
                'CLC':'Commercial Length Cuts',
                'CNS':'Commercials Non Stop',
                'DK':'DramaKing',
                'ECM':'Extra Chilli Music',
                'FWM':'Frameworks',
                'HGR':'Hella Good Records',
                'ISCD':'Intersound',
                'JW':'JW Media Music',
                'CAND':'Music Candy',
                'PPM':'Post Production Music',
                'SONIA':'Sonia Classics',
                'SCD':'Sonoton',
                'SCDC':'Sonoton Classical',
                'SAS':'Sonoton Authentic Series',
                'STT':'Sonoton Trailer Tracks',
                'STTV':'Sonoton Trailer Tracks V',
                'SCDV':'Sonoton Virtual CDs',
                'STRIP':'Strip Sounds',
                'TM':'Telemusic',
                'TREDE':'Trede Collection',
                'TSU':'Tsunami Sounds',
                'UBMM':'UBM Media',
                
               }
    name = 'AUX Publishing'
    urlbase = 'http://search.auxmp.com/search/html/popup_cddetails_i.php?cdkurz=%s&w=tr&lyr=0'

    @staticmethod
    def musicid(filename):
        """Returns musicid from filename.  """
        rex = re.compile(r'^((AUXMP_)?((%s)\d{6}))' % '|'.join(AUXResolver.prefixes))
        g = rex.search(filename)
        try:
            return g.group(3)
        except AttributeError: #no match
            print "oh noes, could not understand this AUX id:",filename
            return None

    def resolve(self, filename, fromcache=True):
        taggedmd = taggedfileparser(filename) # try to read embedded metadata, e.g. id3 tags
        if taggedmd is not None:
            self.trackResolved.emit(filename, taggedmd)
            return
        else:
            super(AUXResolver, self).resolve(filename, fromcache) # fall back to network lookup


def findResolver(filename):
    resolvers = [ DMAResolver(), AUXResolver(), SonotonResolver(), ]
    for resolver in resolvers:
        if resolver.accepts(filename):
            return resolver
    return False

class Gluon(Core.QObject):
    
    def __init__(self, parent=None):
        super(Gluon, self).__init__(parent)
        self.worker = GluonReportWorker()

    def resolve(self, prodno, clipnames):
        self.currentList = clipnames
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

def taggedfileparser(filename):
    """Extract embedded tags/metadata from the audio file. Requires that the file is accessible"""
    try:
        _filemd = mutagen.File(filename, easy=True)
    except IOError: # file isn't accessible on this system
        return None
    if _filemd is None or _filemd['title'] is None or _filemd['composer'] is None:
        return None
    _map = {'album': 'album',
            'organization':'musiclibrary',
            'copyright':'copyright',
            'artist':'artist',
            'title':'title',
            'composer':'composer',
            'isrc':'isrc',
            'tracknumber':'tracknumber',
            'date':'year',
           }
    md = TrackMetadata(filename=filename)
    for fromfield, tofield in _map.iteritems():
        if _filemd.haskey(fromfield):
            md.setattr(tofield, _filemd[fromfield])
    return md

def mdprint(f,m):
    print "filename: ",f
    print "metadata: ", vars(m)

if __name__ == '__main__':
    import signal
    signal.signal(signal.SIGINT, signal.SIG_DFL)

    #filename = 'SCD082120.wav'
    #filename = 'AUXMP_SCD082120.wav'
    #filename = 'AUXMP_AD002306.mp3'
    filename = 'SCDV020016_WARMING SUN A_SONOTON.wav'
    #filename = 'NONRT900497LP0205_xxx.wav'
    metadata = None
    def mymeta(filename, _metadata):
        metadata = _metadata
        print "mymeta:", vars(metadata)

    app = Gui.QApplication(sys.argv)
    resolver = findResolver(filename)
    resolver.trackResolved.connect(mymeta)
    resolver.resolve(filename, fromcache=False)
    #doc = webdoc(filename, 'http://search.auxmp.com/search/html/popup_cddetails_i.php?cdkurz=SCD082120&w=tr&lyr=0')
    #doc.load()
    sys.exit(app.exec_())
