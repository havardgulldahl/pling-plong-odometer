#-*- encoding: utf8 -*-
# This file is part of odometer by Håvard Gulldahl <havard.gulldahl@nrk.no>
# (C) 2011-2013

import os
import logging
import cPickle as pickle
import sys, os.path, random, time, urllib, urllib2, urlparse, re, datetime
import json, StringIO, HTMLParser
import hashlib
import demjson
import xml.etree.ElementTree as ET
import PyQt4.QtCore as Core
import PyQt4.QtGui as Gui
import PyQt4.QtWebKit as Web
import PyQt4.Qt as Qt
import mutagen
import tagger # unfortunately, we need tagger also, to read id3v1 frames, since mutagen skips past them

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
        for res in (DMAResolver, AUXResolver, SonotonResolver, ApollomusicResolver):
            if self.musiclibrary == res.name:
                return res.musicid(self.filename)
        return ResolverBase.musicid(self.filename)

class GluonReportWorker(Core.QThread):
    'Create a Gluon report (a music metadata usage report) to and submit it to Gluon'
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
    'Lookup a DMA track on gluon and retrieve metadata'
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
        #self.terminate()
        #self.deleteLater()

    def request(self, musicid):
        "do an http post request with given gluon xml payload"
        try:
            req = urllib.urlopen(GLUON_HTTP_LOOKUP +  musicid + '.xml')
        except IOError as e:
            # e.g. dns lookup failed
            self.trackFailed.emit()
            self.error.emit('Tried to lookup %s, but failed. Are you connected to the internet? (%s)' % (musicid, unicode(e)))
            return None

        if req.getcode() in (404, 403, 401, 400, 500):
            self.trackFailed.emit()
            self.error.emit('Tried to look up %s, but got %s' % (musicid, req.getcode()))
            return None
        response = req.read()
        return response

class ApollomusicLookupWorker(Core.QThread):
    trackResolved = Core.pyqtSignal(TrackMetadata, name="trackResolved" )
    trackFailed = Core.pyqtSignal(name="trackFailed" )
    progress = Core.pyqtSignal(int, name="progress" )
    error = Core.pyqtSignal(unicode, name="error") # unicode : error msg

    def __init__(self, parent=None):
        super(ApollomusicLookupWorker, self).__init__(parent)

    def __del__(self):
        self.wait()

    def load(self, filename, logincookie):
        self.filename = filename
        self.musicid = ApollomusicResolver.musicid(filename)
        self.logincookie = logincookie
        self.start()

    def run(self):
        albumdata, trackdata = self.request(self.musicid, self.logincookie)
        # print trackdata
        if trackdata is None:
            return
        self.progress.emit(50)
        # albumdata is a dict, like:
        # {u'active': u'1',
        # u'album_desc': u'A superb selection of music tracks particularly suitable to spice up any media such as websites - online videos - slide shows - etc.',
        # u'album_num': u'360',
        # u'album_title': u'WEBTRAXX',
        # u'comment_ext': u'',
        # u'comment_int': u'',
        # u'country': u'BE',
        # u'created': u'2013-11-04 16:27:06',
        # u'deleted': u'0',
        # u'isNewest': u'0',
        # u'label_fk': u'SMI',
        # u'published': u'2011',
        # u'rating': u'8',
        # u'registered_album': u'',
        # u'score': u'8',
        # u'society': u'',
        # u'sound_type': u'0',
        # u'upload_fk': u'808'}
        #
        # trackdata is a dict, e.g.:
        # {u'album_num': u'360',
        #  u'bpm': u'99',
        #  u'composer': u'MIKE KNELLER STEPHAN NORTH      ',
        #  u'country': u'',
        #  u'created': u'2013-11-04 16:27:06',
        #  u'deleted': u'0',
        #  u'description': u'Uplifting carefree piano melody',
        #  u'downloaded_score': u'0',
        #  u'duration': u'01:00',
        #  u'instrumentation': None,
        #  u'keywords': [u''],
        #  u'keywords_internal': u'Uplifting carefree piano melody',
        #  u'label_fk': u'SMI',
        #  u'performer': None,
        #  u'primary_title': u'HOLD ON TO YOUR DREAMS',
        #  u'published_score': u'20',
        #  u'rating_score': u'40',
        #  u'recorded': u'2011',
        #  u'registered_track': None,
        #  u'secondary_title': u'',
        #  u'serialized_composers': [{u'album_num': u'360',
        #                             u'composer': u'MIKE KNELLER STEPHAN NORTH      ',
        #                             u'ipi_id': None,
        #                             u'label_fk': u'SMI',
        #                             u'role': None,
        #                             u'share': 0,
        #                             u'track_num': u'2',
        #                             u'upload_fk': 808}],
        #  u'sort_score': None,
        #  u'sound_type': u'0',
        #  u'tempo': u'Medium-Slow',
        #  u'time_score': u'0',
        #  u'track_id': u'391529',
        #  u'track_num': u'2',
        #  u'upload_fk': u'808',
        #  u'wave_created': u'1'}
        try: _yr = int(trackdata.get('recorded', -1), 10)
        except:  _yr = -1
        metadata = TrackMetadata(filename=self.filename,
                 musiclibrary=ApollomusicResolver.name,
                 title=trackdata.get('primary_title', None),
                 # length=-1,
                 composer=trackdata.get('composer', None),
                 artist=trackdata.get('performer', None),
                 year=_yr,
                 recordnumber=self.musicid,
                 albumname=albumdata.get('album_title', None),
                 copyright='Apollo Music',
                 # lcnumber=None,
                 # isrc=None,
                 # ean=None,
                 # catalogue=None,
                 label=trackdata.get('label_fk', None),
                 # lyricist=None,
                 identifier='apollotrack# %s' % trackdata.get('track_id', -1),
                 )
        metadata.productionmusic = True
        self.progress.emit(70)
        self.trackResolved.emit(metadata)
        self.progress.emit(100)
        #self.terminate()
        #self.deleteLater()

    def request(self, musicid, logincookie):
        "do an http post request to apollomusic.dk"
        try:
            _lbl, _albumid, _trackno = self.musicid.split('_')
            postdata = urllib.urlencode({'label_fk':_lbl,
                                         'album_num':_albumid,
                                         # 'track_num':_trackno,
                                         'type_query':'tracks',
                                         'sound_type':'0',
                                         'query':'',
                                         'genre':'',
                                         'min_length':'00:00:00',
                                         'max_length':'99:99:99',
                                         'composer':'',
                                         'track_num':'',
                                         'cur_page':'1',
                                         'per_page':'100',
                                         'offset':'0',
                                         'limit':'100',
                                         })
            # logging.debug('postdata: %s', postdata)
            headers = {'Cookie':logincookie}
            r = urllib2.Request('http://www.findthetune.com/action/search_albums_action/', postdata, headers)
            req = urllib2.urlopen(r)

        except IOError as e:
            # e.g. dns lookup failed
            self.trackFailed.emit()
            self.error.emit('Tried to lookup %s, but failed. Are you connected to the internet? (%s)' % (musicid, unicode(e)))
            return None

        if req.getcode() in (404, 403, 401, 400, 500):
            self.trackFailed.emit()
            self.error.emit('Tried to look up %s, but got %s' % (musicid, req.getcode()))
            return None

        response = json.loads(req.read()) # it's a json array
        albumdata = response.pop()        # of 1 albumdict

        trackdata = albumdata['tracks'][int(_trackno, 10)-1] # return correct track, from the array of 'tracks' on the album dict
        del(albumdata['tracks'])
        return albumdata, trackdata

class ResolverBase(Core.QObject):

    prefixes = [] # a list of file prefixes that this resolver recognizes
    postfixes = [] # a list of file postfixes (a.k.a. file suffix) that this resolver recognizes
    name = 'general'
    error = Core.pyqtSignal(unicode, name="error" ) # error message
    trackFailed = Core.pyqtSignal(unicode, name="trackFailed" ) # filename
    trackResolved = Core.pyqtSignal(unicode, TrackMetadata, name="trackResolved" ) # filename, metadataobj
    trackProgress = Core.pyqtSignal(unicode, int, name="trackProgress" ) # filename, progress 0-100
    warning = Core.pyqtSignal(unicode, name="warning") # warning message
    cacheTimeout = 60*60*24*2 # how long are cached objects valid? in seconds

    def __init__(self, parent=None):
        super(ResolverBase, self).__init__(parent)
        self.trackResolved.connect(lambda f,md: self.cache(md))
        def dbgresolved(f, md):
            print "trakresolved:", f, md
        self.trackResolved.connect(dbgresolved)
        self.trackResolved.connect(self.cleanup)
        self.trackFailed.connect(self.cleanup)
        self.logincookie = None

    def accepts(self, filename):
        for f in self.prefixes:
            if unicode(filename).upper().startswith(f):
                return True
        for f in self.postfixes:
            if unicode(filename).upper().endswith(f):
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

    def resolve(self, filename, fullpath, fromcache=True):
        self.filename = filename
        self.fullpath = fullpath
        if fromcache:
            md = self.fromcache()
            if md is not None:
                self.trackResolved.emit(self.filename, md)
                return False
        url = self.url(filename)
        if not url: # invalid url, dont load it
            self.error.emit('Invalid url for filename %s' % filename)
            self.trackFailed.emit(filename)
            return False
        logging.debug('ResolverBase.resolve traversing the INTERNET: %s => %s', filename, url)
        self.doc = webdoc(self.filename, url, parent=None)
        self.doc.frame.loadFinished.connect(self.parse)
        self.doc.page.loadProgress.connect(self.progress)
        self.doc.load()
        return True

    def progress(self, i):
        self.trackProgress.emit(self.filename, i)

    def url(self, filename): # return url from filename
        _id = self.musicid(filename)
        if _id is None:
            return False
        return self.urlbase % _id

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
        if None in [metadata.title, metadata.recordnumber]:
            # invalid cached object, we dont cache it
            return False
        loc = self.cachelocation()
        if self.incache() and self.fromcache() is not None:
            #print "CACHE HIT", loc
            return False
        #print "caching metadata to ", loc
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
        try:
            metadata =  pickle.loads(loc.read())
            loc.close()
        except Exception, (e):
            # something went wrong, cache invalid
            self.warning.emit('fromcache error: %s' % e)
            return None
        if None in [metadata.title, metadata.recordnumber]:
            # invalid cached object:
            return None
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

    def cleanup(self, filename, *args):
        "Remove objects to prevent hanging threads"
        try:
            if hasattr(self, 'doc'):
                self.doc.deleteLater()
        except Exception as e:
            print "cleanup failed:", e
            pass

    def setlogincookie(self, cookie):
        "Add login cookie to service. Only applicable for some services"
        self.logincookie = cookie

class GenericFileResolver(ResolverBase):
    'Resolve file based on embedded metadata, i.e. id3 tags, vorbis tags, bwf'
    name = 'file'
    postfixes = ['MP3','WAV']

    def resolve(self, filename, fullpath, fromcache=True):
        self.filename = filename
        self.fullpath = fullpath  # may be None, on offline clips
        if fromcache:
            md = self.fromcache()
            if md is not None:
                self.trackResolved.emit(self.filename, md)
                return True
        parsed = False
        if isinstance(fullpath, basestring) and os.path.exists(fullpath) and fullpath.upper().endswith('.MP3'):
            parsed = self.id3parse(fullpath)
        elif isinstance(fullpath, basestring) and os.path.exists(fullpath) and fullpath.upper().endswith('.WAV'):
            parsed = self.wavparse(fullpath)
        if not parsed:
            if fullpath is None: # clip is offline
                self.warning.emit(u"Could not parse '%s', clip is offline" % filename)
            elif not os.path.exists(fullpath):
                self.warning.emit(u"Could not parse '%s', file not found" % filename)
            else:
                self.warning.emit(u'Could not parse %s' % fullpath)
            self.trackFailed.emit(filename)
            return False
        else:
            self.trackResolved.emit(self.filename, parsed)
            return True

    def wavparse(self, filename):
        'Parse metadata from wav and return TrackMetadata object or False'
        #TODO: implement this
        md = TrackMetadata(filename)
        return False

    def id3parse(self, filename):
        'Parse metadata from id3 tags and return TrackMetadata object or False'
        try:
            _filev1 = tagger.ID3v1(filename)
            _filev2 = tagger.ID3v2(filename)
        except Exception as e:
            #file is not available or is corrupt
            if hasattr(e, 'message'):
                self.error.emit(e.message)
            return False

        md = TrackMetadata(filename)

        md.title = _filev1.songname.decode('latin1')
        md.year = int(_filev1.year, 10)
        md.tracknumber = _filev1.track
        md.artist = _filev1.artist.decode('latin1')
        # see http://en.wikipedia.org/wiki/ID3
        _map = {'TEXT': 'lyricist',
                'TCOM':'composer',
                'TCOP':'copyright',
                'TPUB':'catalogue',
                'TIM':'length',
                'TSRC':'isrc',
                'TALB':'album',
                'TIT2':'title',
                'TPE1':'artist',
                #'TPUB':'musiclibrary',
                'MCDI':'tracknumber',
                'TRCK':'tracknumber',
                'TYER':'year', # replaced by TDRC in v2.4
                'TDRC':'year',
               }
        for _frame in _filev2.frames:
            if _frame.fid in _map.keys():
                _toattr = _map[_frame.fid]
                _value = ','.join( s.decode(_frame.encoding) for s in _frame.strings )
                setattr(md, _toattr, _value)
        # these id3v1 values take precedence
        if _filev1.album.decode('latin1') == u'NRK P3 Urørt':
            md.musiclibrary = u'Urørt'
        # try to fix things
        if isinstance(md.year, basestring):
            try:
                _y = md.year
                md.year = datetime.datetime.strptime(_y, '%Y-%m-%dT%H:%M:%SZ').year
            except ValueError:
                pass
        return md


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

    def resolve(self, filename, fullpath, fromcache=True):
        self.filename = filename
        self.fullpath = fullpath
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
            return None

    def getlabel(self, hint):
        "Return a nice, verbose name for a label, if it is known (returns hint otherwise)"
        return self.labelmap.get(hint, hint) # return hint verbatim if it's not in map

    def parse(self):
        metadatabox = unicode(self.doc.frame.findFirstElement("#csinfo").toInnerXml())
        #logging.debug('metadatabox: %s', metadatabox)
        if len(metadatabox.strip()) == 0:
            self.trackFailed.emit(self.filename)
            self.error.emit("Could not get info on %s. Lookup failed" % self.filename)
            return None
        metadata = TrackMetadata(filename=self.doc.filename, musiclibrary=self.name)
        try:
            duration = unicode(self.doc.frame.findAllElements("div[style='top:177px;']")[1].toInnerXml())
            mins, secs = [int(s.strip()) for s in duration.split(' ')[0].split(":")]
            metadata.length=mins*60+secs
        except:
            pass
        mapping = { 'Track name': 'title', #REMEMBER LAST SUMMER
                    'Track number': 'recordnumber', #SCD 821 20.0
                    'Composer': 'composer', #Mladen Franko
                    'Artist': 'artist', #(N/A for production music)
                    'Album name': 'albumname',#ORCHESTRAL LANDSCAPES 2
                    'Catalogue number': 'catalogue', #821
                    'Label': '_label', #SCD
                    'Copyright owner': 'copyright', #(This information requires login)
                    'LC number': 'lcnumber', #07573 - Library of Congress id
                    'EAN/GTIN': 'ean', # 4020771100217 - ean-13 (barcode)
                    'ISRC': 'isrc', # DE-B63-10-021-20 - International Standard Recording Code
                  }
        for l in metadatabox.split('\n'):
            if not len(l.strip()): continue
            meta, data = [s.strip() for s in l.split(':', 1)]
            logging.debug('metadata: %s=%s', meta, htmlunescape(data))
            try:
                setattr(metadata, mapping[meta], htmlunescape(data))
            except KeyError:
                logging.error('Unknown metadata field received from AUX: -%s-, skipping to next', meta)

        metadata.productionmusic = True
        metadata.label = self.getlabel(metadata._label)
        self.trackResolved.emit(self.filename, metadata)

class AUXResolver(SonotonResolver):
    prefixes = ['AUXMP_', 'AD', 'AFRO', 'BAC', 'BL', 'BM', 'CNS', 'ECM', 'FWM', 'IPX', 'ISCD', 'SPOT', 'JW', 'CAND', 'MMIT', 'KOK', 'PMA', 'ISPV', 'RSM', 'RSMV', 'SONI', 'SCD', 'SAS', 'SCDC', 'STT', 'STTV', 'SCDV', 'TM', 'TRED', 'TSU', 'UBMM', 'WDA', 'WD']

    labelmap = { # static label map. See .updateReportoire()
                'AD': 'Adapt',
                'AFRO': 'AFRO Musique',
                'BAC': 'Big and Clever Music',
                'BL': 'Bleach',
                'BM': 'Brilliant Music',
                'CNS': 'Commercials Non Stop',
                'ECM': 'Extra Chilli Music',
                'FWM': 'Frameworks',
                'IPX': 'Impax Music',
                'ISCD': 'Intersound',
                'SPOT': 'Intersound',
                'JW': 'JW Media Music',
                'CAND': 'Music Candy',
                'MMIT': 'MUSICA IT',
                'KOK': 'Pacifica Artist',
                'PMA': 'Pacifica Music Artist',
                'ISPV': 'Pro Viva',
                'RSM': 'Reliable Source Music',
                'RSMV': 'Reliable Source Music Virtual',
                'SONI': 'Sonia Classics',
                'SCD': 'Sonoton',
                'SAS': 'Sonoton Authentic Series',
                'SCDC': 'Sonoton Classical',
                'STT': 'Sonoton Trailer Tracks',
                'STTV': 'Sonoton Trailer Tracks V',
                'SCDV': 'Sonoton Virtual CDs',
                'TM': 'Telemusic',
                'TRED': 'Trede Collection',
                'TSU': 'Tsunami Sounds',
                'UBMM': 'UBM Media',
                'WDA': 'Wild Diesel Artist',
                'WD': 'Wild Diesel',
               }
    name = 'AUX Publishing'
    urlbase = 'http://search.auxmp.com/search/html/popup_cddetails_i.php?cdkurz=%s&w=tr&lyr=0'

    @staticmethod
    def musicid(filename):
        """Returns musicid from filename.  """
        rex = re.compile(r'^((AUXMP_)?([A-Z]+\d{6}))')
        g = rex.search(filename)
        try:
            return g.group(3)
        except AttributeError: #no match
            return None

    def resolve(self, filename, fullpath, fromcache=True):
        # first try to get metadata from online sources.
        if super(AUXResolver, self).resolve(filename, fullpath, fromcache):
            return True
        # then try to read id3 data from mp3 file, if we have a path
        # (if the clip is offline, there won't be a path available)
        if fullpath is not None:
            _mp3 = GenericFileResolver()
            return _mp3.resolve(filename, fullpath)
        return False

    def updateRepertoire(self, labelmap):
        """Takes an updated label map, e.g. from auxjson.appspot.com, and updates the internal list"""
        self.labelmap.update(labelmap)
        for prefix in labelmap.keys():
            if not prefix in self.prefixes:
                self.prefixes.append(prefix)


class ApollomusicResolver(ResolverBase):
    prefixes = [ 'APOLLO_',]
    name = 'ApolloMusic'
    urlbase = 'http://www.findthetune.com/action/search_tracks_action/' # HTTP POST interface, returns json
    labelmap = { } # TODO: get list of labels

    @staticmethod
    def musicid(filename):
        """Returns musicid from filename.

        Apollo_SMI_360_1__TOUCH_THE_SKY__MIKE_KNELLER_STEPHAN_NORTH.mp3 -> SMI_360_1

        """
        rex = re.compile(r'^Apollo_([A-Z]+_\d+_\d+)__') # _<label>_<albumid>_<trackno>__
        g = rex.search(filename)
        try:
            return g.group(1)
        except AttributeError: #no match
            return None

    def getlabel(self, hint):
        "Return a nice, verbose name for a label, if it is known (returns hint otherwise)"
        return self.labelmap.get(hint, hint) # return hint verbatim if it's not in map

    def resolve(self, filename, fullpath, fromcache=True):
        self.filename = filename
        self.fullpath = fullpath
        if fromcache:
            md = self.fromcache()
            if md is not None:
                self.trackResolved.emit(self.filename, md)
                return
        self.worker = ApollomusicLookupWorker()
        self.worker.progress.connect(self.progress)
        self.worker.trackResolved.connect(lambda md: self.trackResolved.emit(self.filename, md))
        self.worker.trackFailed.connect(lambda: self.trackFailed.emit(self.filename))
        self.worker.error.connect(lambda msg: self.error.emit(msg))
        # check login cookie, without it we get nothing from the service
        if self.logincookie is None:
            self.error.emit(u"You need to log in to ApolloMusic before we can look something up")
            self.trackFailed.emit(self.filename)
            return

        self.worker.load(filename, self.logincookie)


def findResolver(filename):
    resolvers = [ DMAResolver(), AUXResolver(), SonotonResolver(), ApollomusicResolver(), GenericFileResolver()]
    for resolver in resolvers:
        # print "%s accepts: %s" % (resolver, resolver.accepts(filename))
        if resolver.accepts(filename):
            return resolver
    return False

def getResolverPatterns():
    resolvers = [ DMAResolver(), AUXResolver(), SonotonResolver(), ApollomusicResolver(), GenericFileResolver()]
    r = {}
    for resolver in resolvers:
        r[resolver.name] = {'prefixes':resolver.prefixes, 'postfixes':resolver.postfixes}
    return r

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
        #print "loading url: ", self.url
        self.frame.load(Core.QUrl(self.url))

def mdprint(f,m):
    print "filename: ",f
    print "metadata: ", vars(m)

def htmlunescape(s):
    return HTMLParser.HTMLParser().unescape(s)

if __name__ == '__main__':
    try:
        filename = sys.argv[1]
    except IndexError:
        filename = 'test.mp3'
    logging.basicConfig(level=logging.DEBUG)
    def mymeta(filename, _metadata):
        metadata = _metadata
        print "mymeta:", vars(metadata)

    class Application(Gui.QApplication):
        def event(self, e):
            return Gui.QApplication.event(self, e)

    app = Application(sys.argv)
    import signal
    signal.signal(signal.SIGINT, lambda *a: app.quit()) # trap ^C to quit cleanly
    app.startTimer(200)
    resolver = findResolver(filename)
    print 'resolver:', resolver
    import os
    print "login cookie detected: %s" % os.environ.get('LOGINCOOKIE', None)
    resolver.setlogincookie(os.environ.get('LOGINCOOKIE', None))
    resolver.trackResolved.connect(mymeta)
    import os.path
    resolver.resolve(filename, os.path.abspath(filename), fromcache=False)
    sys.exit(app.exec_())
