#-*- encoding: utf8 -*-
# This file is part of odometer by Håvard Gulldahl <havard.gulldahl@nrk.no>
# (C) 2016

import os
import os.path
import hashlib
import logging
import cPickle as pickle
import random
import urllib
import time
import datetime
import re
import json
import HTMLParser

import PyQt4.QtCore as Core
import PyQt4.QtGui as Gui
import PyQt4.QtWebKit as Web


import lookupWorkers
from model import TrackMetadata

def findResolver(filename):
    resolvers = [DMAResolver(),
             AUXResolver(),
             ApollomusicResolver(),
             UniPPMResolver(),
             UprightmusicResolver(),
             GenericFileResolver()]
    for resolver in resolvers:
        # print "%s accepts: %s" % (resolver, resolver.accepts(filename))
        if resolver.accepts(filename):
            return resolver
    return False

def getResolverPatterns():
    resolvers = [DMAResolver(),
             AUXResolver(),
             ApollomusicResolver(),
             UniPPMResolver(),
             UprightmusicResolver(),
             GenericFileResolver()]
    r = {}
    for resolver in resolvers:
        r[resolver.name] = {'prefixes':resolver.prefixes, 'postfixes':resolver.postfixes}
    return r


def htmlunescape(s):
    return HTMLParser.HTMLParser().unescape(s)


def getmusicid(filename):
    "Return a music id from filename"
    res = findResolver(filename)
    if not res:
        return ResolverBase.musicid(filename)
    return res.musicid(filename)

class webdoc(Core.QObject):
    '''A helper class to load urls in Qt'''
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


class ResolverBase(Core.QObject):

    prefixes = [] # a list of file prefixes that this resolver recognizes
    postfixes = [] # a list of file postfixes (a.k.a. file suffix) that this resolver recognizes
    labelmap = [] # a list of labels that this music service carries
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

    def getlabel(self, hint):
        "Return a nice, verbose name for a label, if it is known (returns hint otherwise)"
        return self.labelmap.get(hint, hint) # return hint verbatim if it's not in map


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
	# disable mp3 scanning
	return False
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
        self.worker = lookupWorkers.GluonLookupWorker()
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


class AUXResolver(ResolverBase):
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

    def resolve(self, filename, fullpath, fromcache=True):
        self.filename = filename
        self.fullpath = fullpath
        if fromcache:
            md = self.fromcache()
            if md is not None:
                self.trackResolved.emit(self.filename, md)
                return
        self.worker = lookupWorkers.ApollomusicLookupWorker()
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

class UniPPMResolver(ResolverBase):
    prefixes = [ ]
    name = 'UniPPM'
    urlbase = 'http://www.unippm.se/Feeds/TracksHandler.aspx?method=workaudiodetails&workAudioId={trackid}' # HTTP GET interface, returns json
    labelmap = {  'AA':'Atmosphere Archive ',
 'AK':'Atmosphere Kitsch ',
 'AM':'Access Music ',
 'ATMOS':'Atmosphere ',
 'ATV':'Atmosphere TV ',
 'AXS':'Access Promo ',
 'BBCPM':'BBCPM',
 'BCC':'Bruton Classical Series ',
 'BEE':'Bruton Bee Stings ',
 'BER':'BER',
 'BEST4':'Best4',
 'BIGS':'Big Shorts ',
 'BPM':'BPM',
 'BPM1':'BPM Classical Series ',
 'BPM2':'BPM Explorer Series ',
 'BPM3':'BPM Score Series ',
 'BR':'Bruton ',
 'BTV':'BTV ',
 'CHAP':'Chappell ',
 'CHAPAV':'Chappell AV ',
 'CHAPC':'Chappell Classical Series ',
 'CHAPWR':'Chappell World Series ',
 'CHUCKD':'Chuck D ',
 'CM':'Chronic Music ',
 'CNCT':'Connect ',
 'COHH':'Chronicles of Hip Hop ',
 'DC':'Directors Choice ',
 'DF':'Darkfly ',
 'EDGE':'Killer Edge ',
 'ESS':'Essential Series ',
 'EVO':'EVO',
 'FC':'FirstCom ',
 'GAL':'GAL',
 'GIM':'Ghost In The Machine ',
 'GM':'Gotham Music ',
 'HITS':'Greatest Hits ',
 'HM':'Hollywood Music ',
 'HS':'HeadSpace ',
 'HV':'HV',
 'IM':'Immediate Music ',
 'IMCD':'Immediate Music ',
 'KA':'Killer Animation ',
 'KAR':'Kosinus Arts ',
 'KAS':'Killer Artist Series ',
 'KCL':'Kosinus Classical ',
 'KL':'Killer Latino ',
 'KLA':'Koka Classical Series ',
 'KOK':'Koka Media ',
 'KOL':'Kosinus World ',
 'KOM':'Kosinus Magazine ',
 'KOS':'Kosinus ',
 'KT':'Killer Tracks ',
 'KTP':'Killer Promos ',
 'KTS':'Killer Score ',
 'KTST':'Killer Stage and Screen ',
 'KTV':'Koka TV ',
 'KUT':'Koka Kuts ',
 'LOCD':'Lo Editions ',
 'LO-CD':'Lo Editions',
 'MAT':'Match Music ',
 'MEX':'Mexican Music Library ',
 'MHSR':'Mannheim Steamroller ',
 'MSTR':'MasterSource ',
 'MSV':'MasterSource ',
 'MXS':'Match XS Dance Label ',
 'NM':'Network Music ',
 'NPM':'Noise Pump Music ',
 'NPM':'NoisePumpMusic ',
 'Nuggets':'Nuggets',
 'OM':'One Music ',
 'OM':'OneMusic ',
 'PMCD':'Parry Classical ',
 'PML':'Parry Music Library ',
 'PN8':'Plan 8 ',
 'PN8CD':'Plan 8 Music',
 'RCAL':'RCAL ',
 'RCF':'REALITY by C. Franke ',
 'RCR':'Roadside Couch Records ',
 'RDR':'RADAR ',
 'RNM':'ReverbNation Music ',
 'RW':'Real World Production Music ',
 'SAMP':'Sampler ',
 'SEE':'SEE ',
 'SEE':'See Trailer Tracks ',
 'SLAM':'SLAM!',
 'SND':'Snowdrop',
 'ST':'Selectracks ',
 'STDT':'Selectracks Documentary ',
 'STSC':'Selectracks Songs ',
 'STTK':'Selectracks Toolkits ',
 'ULS':'Ultimate Latin Series ',
 'US':'Ultimate Series ',
 'UTS':'Universal Trailer Series ',
 'VL':'Velocity',
 'VTMA':'Vitamin A',
 'VTM-A':'Vitamin A',
 'ZONES':'Zones',
 'ZTS':'Zero To Sixty',} # TODO: get list of labels automatically

    def __init__(self, parent=None):
        self.prefixes = self.labelmap.keys()
        super(UniPPMResolver, self).__init__(parent)


    @staticmethod
    def musicid(filename):
        """Returns musicid from filename.

        KOS_397_3_Exploit_Kalfayan_Sarkissian_710023.wav -> 710023

        """
        rex = re.compile(r'^[A-Z]{2,4}_.*_(\d+).wav') # _<label>_<albumid>_<trackno>_<title>_<musicid>.wav
        g = rex.search(filename)
        try:
            return g.group(1)
        except AttributeError: #no match
            return None

    def resolve(self, filename, fullpath, fromcache=True):
        self.filename = filename
        self.fullpath = fullpath
        if fromcache:
            md = self.fromcache()
            if md is not None:
                self.trackResolved.emit(self.filename, md)
                return
        self.worker = lookupWorkers.UniPPMLookupWorker()
        self.worker.progress.connect(self.progress)
        self.worker.trackResolved.connect(lambda md: self.trackResolved.emit(self.filename, md))
        self.worker.trackFailed.connect(lambda: self.trackFailed.emit(self.filename))
        self.worker.error.connect(lambda msg: self.error.emit(msg))

        self.worker.load(filename)


class UprightmusicResolver(ResolverBase):
    prefixes = [ '_UPRIGHT',]
    name = 'UprightMusic'
    urlbase = 'http://search.upright-music.com/sites/all/modules/up/session.php?handler=load&tid={trackid}' # HTTP GET interface, returns json
    labelmap = { } # TODO: get list of labels

    @staticmethod
    def musicid(filename):
        """Returns musicid from filename.

        _UPRIGHT_EDS_016_006_Downplay_(Main).WAV -> 6288627e-bae8-49c8-9f3c-f6ed024eb698

        """
        rex = re.compile(r'^_UPRIGHT_([A-Z]+_\d+_\d+)_.*') # _<label>_<albumid>_<trackno>__
        g = rex.search(filename)
        try:
            return g.group(1)
        except AttributeError: #no match
            return None

    def resolve(self, filename, fullpath, fromcache=True):
        self.filename = filename
        self.fullpath = fullpath
        if fromcache:
            md = self.fromcache()
            if md is not None:
                self.trackResolved.emit(self.filename, md)
                return
        self.worker = lookupWorkers.UprightmusicLookupWorker()
        self.worker.progress.connect(self.progress)
        self.worker.trackResolved.connect(lambda md: self.trackResolved.emit(self.filename, md))
        self.worker.trackFailed.connect(lambda: self.trackFailed.emit(self.filename))
        self.worker.error.connect(lambda msg: self.error.emit(msg))
        # check login cookie, without it we get nothing from the service
        if self.logincookie is None:
            self.error.emit(u"You need to log in to UprightMusic before we can look something up")
            self.trackFailed.emit(self.filename)
            return

        self.worker.load(filename, self.logincookie)

