#-*- encoding: utf8 -*-
# This file is part of odometer by Håvard Gulldahl <havard.gulldahl@nrk.no>
# (C) 2016

import os
import os.path
import hashlib
import logging
import cPickle as pickle
import random
import urllib, urllib2
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
        rex = re.compile(r'^((NRKO_|NRKT_|NONRO|NONRT|NONRE)[A-Za-z0-9]+)')
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
        metadata = TrackMetadata(filename=self.doc.filename,
                                 recordnumber=self.musicid(self.doc.filename),
                                 musiclibrary=self.name)
        try:
            duration = unicode(self.doc.frame.findAllElements("div[style='top:177px;']")[1].toInnerXml())
            mins, secs = [int(s.strip()) for s in duration.split(' ')[0].split(":")]
            metadata.length=mins*60+secs
        except:
            pass
        mapping = { 'Track name': 'title', #REMEMBER LAST SUMMER
                    'Track number': 'identifier', #SCD 821 20.0
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
                  'LO_CD':'Lo Editions',
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
                  'SOHO': 'Unknown',
                  'ST':'Selectracks ',
                  'STDT':'Selectracks Documentary ',
                  'STSC':'Selectracks Songs ',
                  'STTK':'Selectracks Toolkits ',
                  'STFTA': 'Selectedtracks Unknown',
                  'SUN': 'Unknown',
                  'ULS':'Ultimate Latin Series ',
                  'US':'Ultimate Series ',
                  'UTS':'Universal Trailer Series ',
                  'VL':'Velocity',
                  'VTMA':'Vitamin A',
                  'VTM-A':'Vitamin A',
                  'VTM_A':'Vitamin A',
                  'ZONES':'Zones',
                  'ZTS':'Zero To Sixty',} # TODO: get list of labels automatically

    def __init__(self, parent=None):
        self.prefixes = ['%s_' % x for x in self.labelmap.keys()] # prfix is <LABEL> + _
        super(UniPPMResolver, self).__init__(parent)


    @staticmethod
    def musicid(filename):
        """Returns musicid from filename.

        KOS_397_3_Exploit_Kalfayan_Sarkissian_710023.wav -> 710023

        """
        rex = re.compile(r'^(%s)_\d{1,4}_\d{1,4}_.*_(\d+).*' % '|'.join(UniPPMResolver.labelmap.keys())) # _<label>_<albumid>_<trackno>_<title>_<musicid>.wav
        g = rex.search(filename)
        try:
            return g.group(2)
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


class ExtremeMusicResolver(ResolverBase):
    prefixes = [ ]
    name = 'ExtremeMusic'
    urlbase = 'https://lapi.extrememusic.com/' # JSON REST interface
    labelmap = {'XCD': 'X-Series',
'DCD': 'Directors Cuts',
'HYP': 'Hype Music',
'XXL': 'The 13 Brotherhood',
'ATN': 'A-Tone',
'LAA': 'Law & Audio',
'GAA': 'Gore & Audio',
'WAA': 'War & Audio',
'XRC': 'Reality Check',
'XTS': 'Two Steps From Hell',
'SPN': 'Spintrest',
'XLR': 'Lab Rat Recordings',
'XGM': 'Grandmaster',
'VEX': 'Velvet Ears',
'XXX': 'Moonshine',
'XSP': 'Superpop',
'XST': 'Stampede',
'XEL': 'Easy Listening',
'XMT': 'Mixtape',
'XCL': 'Ultimate Classix',
'QCD': 'Q-Series',
'XPS': 'Passport',
'SCS': 'Scoreganics',
'MDE': 'Made', } # TODO: get list of labels automatically

    def __init__(self, parent=None):
        self.prefixes = [x.upper() for x in self.labelmap.keys()] # prfix is <LABEL> + _
        super(ExtremeMusicResolver, self).__init__(parent)

    @staticmethod
    def musicid(filename):
        """Returns musicid from filename.

        SCS069_02 MR DARKSIDE.WAV -> SCS069_02
        SCS062_06_3 DINGO BINGO_DIDGERIDOO ONLY.WAV -> SCS062_06_3

        """
        prefixes = [x.upper() for x in ExtremeMusicResolver.labelmap.keys()]
        rex = re.compile(r'^((%s)\d{2,5}_\d{2,3}(_\d{1,3})?)\s.*' % '|'.join(prefixes)) # <label><albumid>_<trackno>_[variant]
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
        self.worker = lookupWorkers.ExtremeMusicLookupWorker()
        self.worker.progress.connect(self.progress)
        self.worker.trackResolved.connect(lambda md: self.trackResolved.emit(self.filename, md))
        self.worker.trackFailed.connect(lambda: self.trackFailed.emit(self.filename))
        self.worker.error.connect(lambda msg: self.error.emit(msg))
        # check login cookie, without it we get nothing from the service
        if self.logincookie is None:
            self.fetchlogincookie()

        self.worker.load(filename, self.logincookie)

    def fetchlogincookie(self):
        "get loging cookie / session token"
        #0. Get session token
        #curl 'https://www.extrememusic.com/env' -H 'Accept: application/json, text/javascript, */*; q=0.01' -H 'Referer: https://www.extrememusic.com/labels/1' -H 'X-Requested-With: XMLHttpRequest' -H 'User-Agent: Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/53.0.2785.116 Safari/537.36' --compressed
        ENVURL = 'https://www.extrememusic.com/env'
        env = json.loads(urllib.urlopen(ENVURL).read())
        self.setlogincookie(env['env']['API_AUTH'])


    def fetchlabels(self):
        """get a new list of labels online

        0. Get session token
        curl 'https://www.extrememusic.com/env' -H 'Accept: application/json, text/javascript, */*; q=0.01' -H 'Referer: https://www.extrememusic.com/labels/1' -H 'X-Requested-With: XMLHttpRequest' -H 'User-Agent: Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/53.0.2785.116 Safari/537.36' --compressed

        1. Get label/"series"
        curl 'https://lapi.extrememusic.com/grid_items?range=0%2C24&view=series' -H 'Origin: https://www.extrememusic.com' -H 'Accept-Encoding: gzip, deflate, sdch, br' -H 'X-API-Auth: 2347c6f3f3ea9cc6e3405f54a3789a6ada9e7631d2e92b0d50cecc8401a360d2' -H 'User-Agent: Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/53.0.2785.116 Safari/537.36' -H 'Accept-Language: en-US,en;q=0.8,nb;q=0.6,sv;q=0.4,da;q=0.2' -H 'Accept: application/json, text/javascript, */*; q=0.01' -H 'Referer: https://www.extrememusic.com/labels' -H 'Connection: keep-alive' -H 'X-Site-Id: 1' --compressed

        -> image_detail_url:
        "https://d2oet5a29f64lj.cloudfront.net/IMAGES/series/detail/dcd.jpg"
                                                                    ^^^ <- label abbreviation
        """
        if self.logincookie is None:
            self.fetchlogincookie()
        req = urllib2.Request('https://lapi.extrememusic.com/grid_items?range=0%2C200&view=series')
        req.add_header('X-API-Auth', self.logincookie)

        labels = json.loads(urllib2.urlopen(req).read())
        r = { g['image_detail_url'][59:62].upper() : g['title'] for g in labels['grid_items'] }
        return r

"""
Extreme Music


URLS:
0. Get session token
curl 'https://www.extrememusic.com/env' -H 'Accept: application/json, text/javascript, */*; q=0.01' -H 'Referer: https://www.extrememusic.com/labels/1' -H 'X-Requested-With: XMLHttpRequest' -H 'User-Agent: Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/53.0.2785.116 Safari/537.36' --compressed

1. Get label/"series"
curl 'https://lapi.extrememusic.com/grid_items?range=0%2C24&view=series' -H 'Origin: https://www.extrememusic.com' -H 'Accept-Encoding: gzip, deflate, sdch, br' -H 'X-API-Auth: 2347c6f3f3ea9cc6e3405f54a3789a6ada9e7631d2e92b0d50cecc8401a360d2' -H 'User-Agent: Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/53.0.2785.116 Safari/537.36' -H 'Accept-Language: en-US,en;q=0.8,nb;q=0.6,sv;q=0.4,da;q=0.2' -H 'Accept: application/json, text/javascript, */*; q=0.01' -H 'Referer: https://www.extrememusic.com/labels' -H 'Connection: keep-alive' -H 'X-Site-Id: 1' --compressed

-> image_detail_url:
"https://d2oet5a29f64lj.cloudfront.net/IMAGES/series/detail/dcd.jpg"
                                                            ^^^ <- label abbreviation

2. Get albums from label/series catalog:
curl 'https://lapi.extrememusic.com/grid_items?range=0%2C48&order_by=default&order=asc&view=series_albums&series_id=1' -H 'Origin: https://www.extrememusic.com' -H 'Accept-Encoding: gzip, deflate, sdch, br' -H 'X-API-Auth: 1df604ce0a306858cd3f1da00a80a6322170ad361b4c380d040899e8300e8e07' -H 'User-Agent: Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/53.0.2785.116 Safari/537.36' -H 'Accept-Language: en-US,en;q=0.8,nb;q=0.6,sv;q=0.4,da;q=0.2' -H 'Accept: application/json, text/javascript, */*; q=0.01' -H 'Referer: https://www.extrememusic.com/labels/1' -H 'Connection: keep-alive' -H 'X-Site-Id: 1' --compressed

3. Get tracks from albums:
curl 'https://lapi.extrememusic.com/albums/2861' -H 'Origin: https://www.extrememusic.com' -H 'Accept-Encoding: gzip, deflate, sdch, br' -H 'X-API-Auth: 1df604ce0a306858cd3f1da00a80a6322170ad361b4c380d040899e8300e8e07' -H 'User-Agent: Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/53.0.2785.116 Safari/537.36' -H 'Accept-Language: en-US,en;q=0.8,nb;q=0.6,sv;q=0.4,da;q=0.2' -H 'Accept: application/json, text/javascript, */*; q=0.01' -H 'Referer: https://www.extrememusic.com/labels/1' -H 'Connection: keep-alive' -H 'X-Site-Id: 1' --compressed

4. Get track metadata:
curl 'https://lapi.extrememusic.com/search/tracks?query=SCS062_06_3&mode=filter' -H 'Origin: https://www.extrememusic.com' -H 'Accept-Encoding: gzip, deflate, sdch, br' -H 'X-API-Auth: 1df604ce0a306858cd3f1da00a80a6322170ad361b4c380d040899e8300e8e07' -H 'User-Agent: Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/53.0.2785.116 Safari/537.36' -H 'Accept-Language: en-US,en;q=0.8,nb;q=0.6,sv;q=0.4,da;q=0.2' -H 'Accept: application/json, text/javascript, */*; q=0.01' -H 'Referer: https://www.extrememusic.com/search?q=%22SCS062_06_3%22' -H 'Cookie: _ga=GA1.2.876280479.1473240093; Token=tYBNWXOnEAA7wFhyo6BMeb7K/kb3LTeO9R1GY9t6DUZDo0x2KpxtVRmC02LfR3tZCE2HNPQODIaHyTiHdj3oJAHD7Ds7JEVSPtnq0flNZli69Fq9QKSJR6XBaQCCdOvm2/EoGPzr/y3bNoP5M9oi6W8VO8ZMoMA3r3TsaEVzHFE=DPrbk9apaHNOcM+4am0AI77+xapKVMjodU2diZqLsUwGZNfpIXghgY4/jGOrR0ZSW5xYt/AXq6gqGXRylsCeGoVXvb8suWsuvxa62k8Uuhr9sJ/yUdaCvGwvWdcnN7zwSvIHg/I/sQUiLoI4gdVuuIYUyCq53drnQCf9dnmcYBw=AH5yQ7H0txhssYfyO1SPV936Wd+VVSiW1fRK+5XB8U3rpgDnASVTMAAur1cQ63X13TWG4zWd6i+aMPQxggE5SNzS3b8RmlNyYrUz244DkK0o4mMjoqkDrgcOw972q2N77ZBYpqyDH2MGOiAzzcNsud14iZzLHOhWjRrUiH3iHiE=6Wrl3a3YmOp0fvOh17E5rR8VwVBqOXTVR6B+s35nr6hjcRwA4e7o+xmOv152QDcZMsXZIir/M29WieO6tCjPaYIete48jJPNCp9U9PywAzHjiOJyqsf33pTiocyEHIyrQ3KtfqDot0ucWg+VhzHw5npWPhxY2TksG8dAvoZmejc=8yhsC1iMNjK95K9L60qjUkc+S1u9wqjTkgQopdwZ13EwskwswVIpWNE6pzd9H76xMiQ1cCiDZKl3K+hk6HMHxutnxpXIl1kgMEdQWQLxrZ94SFyTqwkyGU3URu0euEqfEZnPTjBG3n4TaBnG/gLqMijcC/hjvoUh8iUkhKJ8nyw=FqPVmftu0jxtGk4vncPgetCTEkAhLNxYcyF0gl+AbuLU9AZcSaRIoe3b+r4gQ1sYWiSEHl2t9tsr9U7v4ZzBLqwbsqtk5/H5yB7oOApZ5rXbBwixGCFHtOX7XrKOJGtcIB2p6KU6qFKD9QT9QkljiKKqlLSN+hd2s5F5XnELbl4=nDyISwVCV9uSwaS991PM/M7bIzijyKH4rA2knxMowsI/gO/lfyqKVlffapoPf2fPI98AQVjDabOPUFElmepr56EbWI1YlJ0ZaNQz/N8QSqXo69qitknb+vM+T83tLwcQvUwpPMWe4YSQwYBSl1lWMBei7daeYyspGsuxnXI3LZA=efnlr1P0KYjENtGioBrTVGXcdU4P/Yp4ao+6H058qqNbvSDlb1a/tmqrqGzaxjn2h8ne4+JY523XGxGkHBlsHuK+wlNBRDzR+n6mbgS4/OferOJjlvruP5mSG3LjC8oq5gRaedJSgCNFfYybWAbMr9q0T7oot1X7n8UhM7U9maU=bXwVdCTCnTAx/NpfycXKoZjEu9h+TcWEu9isVPxKFUrel7ibVvzMu/EpzSR6UbMnp+c1kGi7Qmkyk+Cpp9u87XHpIvGP+T2FMiAcYdJjS/AnLB4vN+6t541b3s/eWiyrk5AX05OOLKYEcRZBqCzR40hXHCVzd02wD4m/SIi+Ba8=4SxaN182sfe381VH7sgAcFEvkiFFLowpfLyGPIpm4R4a+7PHesUHI31UlMiz2m5nvonUhE0YRYadwd0EwyVUazx5TRf4Pnd+tnTX1DV12O0ZF7wCEMjafw8DlHzbwIXJHNJzxBf8V9a5zKUpBv12RMpWXSavs+iGgaBbdZiGBjA=aaqLJdErgNW6UR3QQzWi4hNzDj0GDB0/RqPIseXdR4qgiaWg01wCGos9985j2NZFqBTLOEDxW/ieHaOl8DE8ZolAsuafA4XrIc3T5iq9E+tgLZgfC/4vBHw8vfUhw3POVgkh158nP88k8QDbA+sGlBIsdV+OgUcimL5H1uxZFi4=Zmupd1nB/jGmPoPvaeTGOTspM2mfetKaYtSED2Pat2WzOaBB0YLUYR1USRlV/URoyb49yxXSpYe/7rfOUPXREZcilAk6oQ0UKSizw7WCbTGR3ckZpPIo1eyUKYQV9gs1K/caKUDtgq7qIq/W1KlAMYLB4sOCzFHnvLYDKKPmJSw=XalXY6Yf+rFV7WkeAffzZKCYF2Rp4v6ZVTOA7G3phS7HujmC0FZ8ci0K0+bFvUZThPCMPTgITysx/A77WYliE1eTo5MT423K641MM3XPC3XYq8fTjBk+O2HJadTgdYl7oGrXd5PHeoInyS9e0YI6FVPe+Xbfoz+rSuDO4TxMixo=iOSJ1UWqn+/bte01ZZ/1J3xUf1xe6CVkZeeqS+Dln+vdr2+OYKXJ7sRVCZ4aCrJe7Qmg6m5Djrz2hEOZnJyDPnSCWLJGw/7IS3S7p7QeV9m3LO6CflPW6P2r85o3MLTbEAUeBnkVd/DmIxmXsFNaMWmMP+5vNnW4G5wsJnYmmBg=3VvkpJaW37xbyI8T9ChviRApDSkSAZgLV/UhnOgHDQqJAkn43OKQEX5OW5TS+1CXI5lmOA6filVqezOFqftxwO4DzQiMX/U32mMgnIECe2sAxIDVlbsaIlxj5xCrDLnRGagJj45OfMQGwYwejrxB35FhsoNHA5ee91CqElP5ek8=DsPcSthjdV0SyE+UYcCtzJlxKKIdLbWfASI9YWnYJkqKjbf/e/MPYimV1O/82kO7Jisa1zRq4lpY+9+F5T4jFSXv0+d9dy8LpAFHDlXJ3rTqL+uhajRV2zUU6Xj4yx1cQWjD34dzmVq2MmhgUyYTAN5ZtMBeUHcwaLo5NG+DBB4=hvSuiqsw07PMNVydxksTiQDfGsNbhBFnZUVXe5gL4CXUGbCunvXBR3oLtV8jgy4WkN/iwoyqiu1yvZp1dK9KqchqHXXP89d5xRzFrg7TilvGHG3jLBdDba+zqj8GL3roJQ5b1u9heD8cWdZFvSFwY2LX22F3GCQiK87K+Xu18oM=WAtx9iXwHkHxbfTnQwXnRE9j3LkbbhGgxUWke/KLxxyF9DVysqgSJE/BPEAabGZBsdW7WRc41eDM8fo2CI0XdoXFG3RFqC8Qdm9csWaERm2ieNDIPPvpWydhN9zoUMTiQ/CgGAr55rIco/ZTHFUJkmroqr8nHRTIMawFwzI3JQ4=4s2f5KnP0Q6SUQMZ59mU3VdM0JBFwkUb1UXgJ7iZo4OInJweu1ktOluYy0OTq/LcH2bxP50RbsxWKPr+GUx7vz8ZWgpKlGXs/eS0oAs6aDcADf87s+oY+wlDr1MwzS5RLSG5MZae3ZvezdiCWkuHXIHnHBJy26gb2NdB88dT8Yg=s361/k73V/eWMSUqQwxmZvKzZZO7EoqchApaH14YrAvOPdN3XyVcJyvZMmvVIrPqduzQqWFV/osupejkgBTtzxBet+FiogMTevC4JaSM2K9d8uwvqGOkQKdbVd9M7rPGOaEoHLe8lhKMb3h14woFkP9nFQZIcxs+UxcPExviX50=K1P6RKCJJS82eXyJEGpK66lvwGvd0ChqdnVd6Fa81fsJSVsrYmPd0R3+IWl7i1itgN+6s09YhxMaTFFKf505KDXvfWNDksOEesKwRoa1oJxtEXcdz9QmonPI64VOfLPcSogSaifSVfpqUNaK+WbwRGAr9Xu3JLxxfmjfRlFygEw=jqXbcMBQR5EltE3TxMZ+9yd3+PU5WFA6QwZoM1+EvnbFF4OOv5eHPVkutLIxOCYE7jnSNCYMxpvQvKA/kT1Mh48pUXGkeRuwRV4P/P8/Dox6D9a5qQYwsKj0rVurJkXUfr71KYYQ4z52UtvjPeZwdshlfXYtv5AekZFAjlpGjVQ=; RefreshKey=zZfAlVdFrB5cFtB1WdK4L1uVoat5lHaO9eAB5G3s61o9JGXFuTMY1JWIk2q0h5f5oEfyxXXKGVSoK/vbWSuTft9vVU/9iRfUEV2Hpzb6EWgCXl+eNDSbHxi0oQAs851Jnp6wDBMrIXpdDSnuaIRIGQB2c6OCfCQPygJmN47RXn0=1aU8sFCnHRk1S7nS2jIOwNg8nEv87uZ44zo6TZax+tUX1OVZXj08HyiTft1Mho4CxURHbnZU7SzcdCpPH4SmZv0x/BmgWp4kc65HzbDLWXuyMNHgpei5gTNGIuiPv9UZMwZvyNVskUB43/hRGqI6bWSEvh3MKETUUFjYnzgWY4g=PB7Se6kuns6cHVx6e/Mjh1iod9trXNCInXHk9NQo44cawWzATJ1stL0kMZpn+wiDxZYVq0eehsx8BpPPz+iIQaVtghPqxxVqQAHgpuevsQWz4lXMCb6YlDJ6zWG7G85zgfEglPG2D+imdp0BFkHyKQ6qUEydfsiBUcs2wc+zxzM=YzVRaYCNpKQq1rqBkx4AvNz74cYDfXR/E6vDXlyoUt3tcEcsqJ3eNzTcnsFS7GDuwSaojwW3Dhlt6h1UTZ8zcmxrt+iAbuEhgQraXQdgTrgu79TYk43gCcxhJibMVqYyjiPVC+AWfTk68beBED6jwGg9q6HWEPLVniULKIlnYgk=FJYd+cOANH6BWYB3QI467BVVh1YaK/5RgxkHEoK0VbCcB4yNoboiWRzOO1deNH0y+QFfOApOyAHA/WDB03cB5jB8/zsY1e8QfyaGVr3PoN2iTYMpB+sNKE7SfXTZt/HGsZGvHeme4DZZGlT9i+SttlO7tFEZmoXeB/jgFzKbpG4=OOtvFR3lcfqKTrRUa9VIjGluEd3EctQwRoT3z5RzxCE8532DA3DYGHufA9BnZCPvbTEZ3UzkJj12nvz5PnK8N8XSMiDcNg1fQSEovU18dFyny8qAGNLkHV04kPYWkcSYVjHiYbbhvINBkdrj4LztkvL2LjPNtz+ETWxICJZoMDw=1XI5LqOOgGGTvyvKEtzXF8xETwrmJcv1feL9/GGQ4WjcFLE52TLWnY4b0czPol4nR7mr9Jg2gZKsQwORER23xb4wecgWWKGtGlUD/7va1CZRloVMgaYsZ7pkOXd+n5X7VMZH31ey/nM33noJ9wnyzrIVrZa+tCaixbHm7JFRDn0=QdVpLDuQtS/jjSaZ5FGKQyeB+dI+F7vSYhwJJqXJ1dM0e4H0r/eSsKfjOJwNaDTpwQsMUDEKWbSNKdHGgklwLuEzKwrRyVQc5nkX9vy2gzrUJIivicgPje8n0AfwOSAesav+IYlEf8TeQGe5D/bHmU+RDSaXo42QyYkaKF/mIEg=FQB4d7sTeHhOcERd7ozNuHxUzcWdVM7RuxdqYZZEdck0TxGGJ0VlhohWY1D1X7N2J8SJ8fKXY2n08iOyru+Q/eZkzxOY5tKaPjV+0JgJ5UfqoSEZ1Z9RBMArPSMEBqNyptRJefsV/Tq0mzBsU2knyHBAszMHVH/Ep31qu7FL114=wqF2c5A9yHBIzfkxOYicsapPJTq91l2ECemwGtEuHXvM7bP0jlUaFZtw5uvDeVJZBFe04SIFCu8/ZHvV9mfo20bqdTLemmEnoURgy174ggdaXodo27rJjCcUCZ6dULnR/yOo45OgxpBLHqxJStQBs51UEQdkDcNj+P1Umbh1R0k=UnMGdxYFs2MLdV28IaFYBLe5Xcl22R29YPGRH04KgUKpRn45MExJoqi03aqlCc5OG3B57uB3oABuOUnUBmasokwo2KwZ6IghOOc3fVTl6PRCm2+mQ20Y837+RuvhGztAeM0rUIqupcO2rT1EbJOwHl3NomSy5irvXw0REBPXgAw=tlKiml+U9PLxvZRtY0d/WIK2VLymlcF10PqHQFjRvLBIbXYJLte7Zzbsn5YGj3c2x9UTdK/Zeu0eptJ7a5M+FL/PMHwX62I/Q5h/S8uOmBLD/JBVw3lsefwl13I3VO7NKP9DhBWHHcEDEpSIUpuxkmye22RoYgzRr41oWHTQHXk=+u09IpBwTl++jgsgdugR7PW4BuAeinryPa01M0JjV56AbPp04cBZd9nAlo2Ii9peUJbDTaMdXz9nFLnmvymRPDyk+S+nbKCGrfIZgytWk+w7sTC/AaIZm6mEK2DRrkT4RLIJuu2pk8JIuS0gAcBz2BeCwVEP5wtNv5bWXyMK3FY=e84GKywg0PSHzzUqIc/PjpOCMLZEAmcPPi1o2ppA/IumEZG7LlVRxYOHDnj2yJey6nLfvCo4TzbqqhG+HZZbVoVtwE911/kt8yB2NeY9ommQbwKq4mhvwGRutq6qXCgcUhMar/RGylaS959LSu7QrreT6slXgucE+PTeaYn4AQI=33YMzZ7n7TjyCkO0Ku42BJoPWlZgwoVvI9D9y6arsHXeoanaHBcu0TnNW9l9zwfMxkCMUUcM+P33YH0+DLukPqb93BOtd8uenA5TqSC/iB7mtfofzKMplf41tgXpcUsa7NL0wPpY8S6L7nWHpQDQGtToA70j+4s8FhRlOuRZR3M=I3Y53KoHf6fD1aRiCD/4RFi2gFhj83aJrqatCJfekKbGJfpFFdqKs4V6ogkpjD+Pr2FLHUFWpG5oUzaW0ejROCk9kUeK0F75GLDkIl1ItiHSaYxO13GWjhX5goUsy8TIti6xcE+0JYl1mQUyBrVDGkr7fn0tsPyPLTfXPZuudTs=iGg18gtuJRJMiN5wIcbsikRNMnCn9c4JwEhzg+u1wTrHBVK1+rR0ClB6HdetygbbcoidALmghqQoSl/GvXJkB4WL2qR1f7A9aaBSudDKDTKfFhwwqJm+C9lieTgQPjxkLPh4iqcr0EwicIv1FRSHnV4PYjv7AiqDPaW4yxkx5W8=wkOBm6D7OWHoLD0eXhDunJlAYiYye2+G7a1GjI0VJoh0Mtn1v+4EE4Og7O4XSnyMru+tspagOfIV08wASDYWaJbKuLMY3xWxa4EgrwiVKeUXf9iT+P4xSPAa7VCEhy+SJHCdcXlnVXhDj2/X0pEKExUUrN9XRxskrJCWuJQr8KU=MXk/ySpyv5XSyszUn0K0xjVtgabyw94UZGenfa5viOFl2gWoxGEBuf5aITBvZ+TSeozOCEyov6KxyL+ZbO1R9bjRzXDFlPZtBbOecZaDdRpIKyG1IfiOMPdTIS/pmwH9VczG9zUv08dW8DuThCkMm2VUDP25+67ASrWS7Sv4DpM=2BnvXlILS6pJBvTwJSwDvD7XXPC6CSXQSkQeqvweOLfB8bLQ9idxmaGAiB3oDSdfM9N84FadwY6kplH4dom5lyxH0P4Qa7KrOoVNC0+gwHItMx8pJ39NMq47gIxZ7qEeDMXmhVCzHdAKKpNJTczzFVhiJqtuPpNMivJTVCT5aLc=' -H 'Connection: keep-alive' -H 'X-Site-Id: 1' --compressed

JSON:
{
  "track_search_result_items": [
    {
      "id": "41023",
      "type": "track_search_result_item",
      "title": "dingo bingo",
      "album_id": 2415,
      "album_title": "outback",
      "resource_type": "track",
      "track_id": 41023,
      "tempo": "MEDIUM",
      "tempo_value": 3,
      "duration": 65,
      "stems_avail": false,
      "customix_avail": false,
      "score": 0.14856823
    }
  ],
  "meta": {
    "total_count": 1,
    "filter_facets": {
      "ser": [
        {
          "count": 1,
          "id": 19,
          "label": "SCOREGANICS"
        }
      ],
      "gen": [
        {
          "count": 1,
          "id": 8,
          "label": "FILMSCORE"
        }
      ],
      "sub_gen": [],
      "vib": [
        {
          "count": 1,
          "id": 11757,
          "label": "CONFIDENT"
        },
        {
          "count": 1,
          "id": 11363,
          "label": "DETERMINED"
        }
      ],
      "ins": [
        {
          "count": 1,
          "id": 6797,
          "label": "ACOUSTIC GUITAR"
        },
        {
          "count": 1,
          "id": 7102,
          "label": "DIDGERIDOO"
        }
      ],
      "voc": [],
      "cou": [
        {
          "count": 1,
          "id": 151,
          "label": "AUSTRALIA"
        }
      ],
      "era": [],
      "tem": [
        {
          "count": 1,
          "id": 137,
          "label": "MEDIUM"
        }
      ]
    }
  }
}




"""
