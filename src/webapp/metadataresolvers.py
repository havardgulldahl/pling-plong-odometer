#-*- encoding: utf8 -*-
# This file is part of odometer by Håvard Gulldahl <havard.gulldahl@nrk.no>
# (C) 2016

import os
import os.path
import hashlib
import logging
import pickle
import random
import urllib
import urllib.request
from io import StringIO
import time
import datetime
import re
import json
import html.parser

import aiohttp

import PyQt5.QtCore as Core
import xml.etree.ElementTree as ET

import appdirs 

from model import TrackMetadata

def findResolver(filename):
    for resolver in [x() for x in CURRENT_RESOLVERS]:
        if not resolver.enabled: continue
        if resolver.accepts(filename):
            return resolver
    return False

def getResolvers():
    r = [] 
    for resolver in [x() for x in CURRENT_RESOLVERS]:
        r.append({'name': resolver.name, 
                  'prefixes':resolver.prefixes, 
                  'postfixes':resolver.postfixes,
                  'enabled': resolver.enabled,
                  'prettyname': resolver.prettyname,
                  'description': resolver.description,
                  'website': resolver.website,
                  'contractdetails': resolver.contractdetails,
        })
    return r

def htmlunescape(s):
    return html.parser.HTMLParser().unescape(s)

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
        try:
            self.page = Web.QWebPage(self)
            self.frame = self.page.mainFrame()
        except AttributeError: # qt4 /qt5 
            self.page = Web.QWebEnginePage(self)
            self.frame = self.page
        self.settings = self.page.settings()
        self.settings.setAttribute(Web.QWebSettings.JavascriptEnabled, False)
        self.settings.setAttribute(Web.QWebSettings.AutoLoadImages, False)

    def load(self):
        print("loading url: ", self.url)
        #self.frame.load(Core.QUrl(self.url))

class ResolverBase:

    prefixes = [] # a list of file prefixes that this resolver recognizes
    postfixes = [] # a list of file postfixes (a.k.a. file suffix) that this resolver recognizes
    labelmap = [] # a list of labels that this music service carries
    name = 'general'
    description = ''
    prettyname = 'General'
    enabled = True
    website = ''
    contractdetails = ''
    #error = Core.pyqtSignal(str, str, name="error" ) # filename,  error message
    #trackFailed = Core.pyqtSignal(str, name="trackFailed" ) # filename
    #trackResolved = Core.pyqtSignal(str, TrackMetadata, name="trackResolved" ) # filename, metadataobj
    #trackProgress = Core.pyqtSignal(str, int, name="trackProgress" ) # filename, progress 0-100
    #warning = Core.pyqtSignal(str, name="warning") # warning message
    cacheTimeout = 60*60*24*2 # how long are cached objects valid? in seconds

    def __init__(self, session=None):
        #super(ResolverBase, self).__init__(parent)
        #self.trackResolved.connect(lambda f,md: self.cache(md))
        #self.trackResolved.connect(self.cleanup)
        #self.trackFailed.connect(self.cleanup)
        self.session = session or aiohttp.ClientSession()
        self.logincookie = None

    def accepts(self, filename):
        for f in self.prefixes:
            if str(filename).upper().startswith(f):
                return True
        for f in self.postfixes:
            if str(filename).upper().endswith(f):
                return True
        return False

    async def resolve(self, filename, fromcache=True):
        self.filename = filename
        if fromcache:
            md = self.fromcache()
            if md is not None:
                #self.trackResolved.emit(self.filename, md)
                return md
        url = self.url(filename)
        if not url: # invalid url, dont load it
            #self.error.emit(filename, 'Invalid url for filename %s' % filename)
            #self.trackFailed.emit(filename)
            return False
        logging.debug('ResolverBase.resolve traversing the INTERNET: %s => %s', filename, url)
        async with session.get(url) as response:
            logging.debug('INTERNET got us %r', response)
            return await response.text()

        #self.doc = webdoc(self.filename, url, parent=None)
        #self.doc.frame.loadFinished.connect(self.parse)
        #self.doc.page.loadProgress.connect(self.progress)
        #self.doc.load()
        #return True

    def progress(self, i):
        #self.trackProgress.emit(self.filename, i)
        pass

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
        except Exception as e:
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
        ourdir = appdirs.user_cache_dir('odometer', 'no.nrk.odometer')
        if not os.path.exists(ourdir):
            os.makedirs(ourdir)
               #return os.path.join(ourdir, self.filename)
        try:
            return os.path.join(ourdir, hashlib.md5(self.filename.encode('utf8')).hexdigest())
        except UnicodeEncodeError:
            logging.warning("cachelocation warn: %r - %r", repr(self.filename), type(self.filename))

    def cleanup(self, filename, *args):
        "Remove objects to prevent hanging threads"
        return True
        try:
            if hasattr(self, 'doc'):
                self.doc.deleteLater()
        except Exception as e:
            logging.warning("cleanup failed: %r", e)
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
    enabled = False

    def resolve(self, filename, fullpath, fromcache=True):
        self.filename = filename
        self.fullpath = fullpath  # may be None, on offline clips
        if fromcache:
            md = self.fromcache()
            if md is not None:
                self.trackResolved.emit(self.filename, md)
                return True
        parsed = False
        if isinstance(fullpath, str) and os.path.exists(fullpath) and fullpath.upper().endswith('.MP3'):
            parsed = self.id3parse(fullpath)
        elif isinstance(fullpath, str) and os.path.exists(fullpath) and fullpath.upper().endswith('.WAV'):
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
                self.error.emit(filename, e.message)
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
        if isinstance(md.year, str):
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
    prettyname = 'NRKs Digitale Musikkarkiv'
    website = 'http://dma/'
    enabled = True
    #cacheTimeout = 1

    @staticmethod
    def musicid(filename):
        rex = re.compile(r'^((NRKO_|NRKT_|NONRO|NONRT|NONRE)[A-Za-z0-9]+)')
        g = rex.search(filename)
        try:
            return g.group(1)
        except AttributeError: #no match
            return None

    async def resolve(self, filename, fromcache=True):
        self.filename = filename
        _musicid = self.musicid(filename)
        if fromcache:
            md = self.fromcache()
            if md is not None:
                return md

        endpoint="http://mamcdma02/DMA/{musicid}.xml"
        async with self.session.get(endpoint.format(musicid=_musicid)) as resp:
            logging.debug('hitting endpoint url: %r', resp.url)
            resp.raise_for_status() # bomb on errors
            data = await resp.text()
            metadata = await self.parse_gluon_xml(StringIO(data))
            return metadata

    async def parse_gluon_xml(self, xmlsource):
        'Get a string of xml from gluon and parse it into TrackMetadata'

        # GLUON XML CONVENIENCE METHODS AND STUFF
        GLUON_NAMESPACE='{http://gluon.nrk.no/gluon2}'
        GLUONDICT_NAMESPACE='{http://gluon.nrk.no/gluonDict}'
        def glns(tag):
            s = []
            for ss in tag.split("/"):
                s.append('%s%s' % (GLUON_NAMESPACE, ss))
            return "/".join(s)

        self.tree = ET.parse(xmlsource)
        obj = self.tree.find('.//'+glns('object'))
        md = TrackMetadata()
        md.identifier = obj.find('.//'+glns('identifier')).text
        md.title = obj.find('.//'+glns('title')).text
        md.albumname = obj.find('.//'+glns('titleAlternative')).text
        for creator in obj.findall('.//'+glns('creator')):
            if creator.find('./'+glns('role')).get('link') == 'http://gluon.nrk.no/nrkRoller.xml#V34':
                # Komponist
                md.composer = creator.find('./'+glns('name')).text
            elif creator.find('./'+glns('role')).get('link') == 'http://gluon.nrk.no/nrkRoller.xml#V811':
                # Tekstforfatter
                md.lyricist = creator.find('./'+glns('name')).text
        _a = []
        for contributor in obj.findall('.//'+glns('contributor')):
            if contributor.find('./'+glns('role')).get('link') == 'http://gluon.nrk.no/nrkRoller.xml#V35':
                # Utøver
                _a.append(contributor.find('./'+glns('name')).text)
        md.artist = '; '.join(_a)
        for date in obj.findall('.//'+glns('dateAlternative')):
            if date.get('%sdatesGroupType' % GLUONDICT_NAMESPACE) == 'dateIssued':
                md.year = date.find('./'+glns('start')).get('startYear')
        for ref in obj.findall('.//'+glns('relationIsReferencedBy')):
            if ref.get('link') == 'http://gluon.nrk.no/dataordbok.xml#recordNumber':
                _recordnumber = ref.text
                try:
                    md.label, md.recordnumber = [ x.strip() for x in _recordnumber.split(';')]
                except ValueError:
                    md.recordnumber = _recordnumber
                    md.label = 'Unknown'
        return md

    """
    @staticmethod
    def quicklookup(ltype, substring):
        url = 'http://dma/getUnitNames.do?type=%s&limit=10' % ltype
        data = urllib.parse.urlencode( ('in', substring ), )
        labels = json.loads(urllib.request.urlopen(req).read().decode())

    @staticmethod
    def performerlookup(substring):
        return self.quicklookup('performer', substring)

    @staticmethod
    def creatorlookup(substring):
        return self.quicklookup('creator', substring)

    """

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
    prettyname = 'AUX Publishing (inkluderer Sonoton)'
    website = 'http://search.auxmp.com/'
    urlbase = 'http://search.auxmp.com//search/html/ajax/axExtData.php?cdkurz=%s&ac=track&country=NO'

    @staticmethod
    def musicid(filename):
        """Returns musicid from filename.  """
        rex = re.compile(r'^((AUXMP_)?([A-Z]+\d{6}))')
        g = rex.search(filename)
        try:
            return g.group(3)
        except AttributeError: #no match
            return None

    def updateRepertoire(self, labelmap):
        """Takes an updated label map, e.g. from auxjson.appspot.com, and updates the internal list"""
        self.labelmap.update(labelmap)
        for prefix in labelmap.keys():
            if not prefix in self.prefixes:
                self.prefixes.append(prefix)

    async def resolve(self, filename, fromcache=True):
        self.filename = filename
        _musicid = self.musicid(filename)
        if fromcache:
            md = self.fromcache()
            if md is not None:
                return md

        """do an http get request to http://search.auxmp.co//search/html/ajax/axExtData.php

        look up musicid, e.g ROCK015601

        by doing a get request to
        http://search.auxmp.com//search/html/ajax/axExtData.php?cdkurz=ROCK015601&ac=track&country=NO'

        and parse the json we get back

        """
        endpoint = 'http://search.auxmp.com//search/html/ajax/axExtData.php'
        params = {'ac': 'track',
                  'country': 'NO',
                  'cdkurz': _musicid
        }
        async with self.session.get(endpoint, params=params) as resp:
            logging.debug('hitting endpoint url: %r', resp.url)
            resp.raise_for_status() # bomb on errors
            data = await resp.json()
            logging.info('got data: %r', data)
            trackdata = data.get('tracks')[0]

            metadata = TrackMetadata(filename=self.filename,
                    musiclibrary=self.name,
                    title=trackdata.get('title', None),
                    length=trackdata.get('nZeit', -1),
                    composer=trackdata.get('allkomp', None),
                    artist=trackdata.get('artists', None),
                    year=-1,
                    recordnumber=_musicid,
                    albumname=trackdata.get('cd_title', None),
                    copyright='SONOTON Music GmbH & Co. KG',
                    lcnumber=trackdata.get('lc', None),
                    isrc=trackdata.get('isrc', None),
                    ean=trackdata.get('ean', None),
                    catalogue=trackdata.get('p_nummer', None),
                    label=trackdata.get('label', None),
                    lyricist=trackdata.get('lyrics', None),
                    identifier=trackdata.get('cdkurz', self.musicid)
                    )
            metadata.productionmusic = True
            try:
                dt = datetime.datetime.strptime(trackdata.get('releasedat', None), '%Y-%m-%d') #SIC, 
                logging.debug('Got datetime %r for musicid %r', dt, self.musicid)            
                metadata.year = dt.year
            except (ValueError, TypeError) as e:
                logging.exception(e)
                pass # the data does not fit our expectations, so we let it slide
            except Exception as e:
                # this is unexpected
                logging.exception(e)

            if metadata.title is not None:
                metadata.title = metadata.title.title() # all AUX titles are ALL CAPS. Noisy!
            return metadata

        """
        except IOError as e:
            # e.g. dns lookup failed
            logging.exception(e)
            raise web.HTTPBadRequest(reason='Tried to lookup %s, but DNS lookup failed. ' % (musicid,))

        if req.getcode() in (404, 403, 401, 400, 500):
            raise web.HTTPBadRequest(reason='Tried to lookup %s, but failed. Please try again' % (musicid,))
        if len(response) == 0 or response.get('ax_success') != 1:
            # empty response,
            raise web.HTTPBadRequest(reason='Tried to lookup %s, but failed. Please try again' % (musicid,))
        elif len(response.get('errmsg', '')) > 0:
            # we got an error message from auxmp.com
            raise web.HTTPBadRequest(reason='Tried to lookup %s, but received an error from AUX: %r' % (musicid, response.errmsg))
        elif response.get('trackcnt') == 0:
            # auxmp.com didnt return any tracks for our search term
            raise web.HTTPBadRequest(reason='Tried to lookup %s, but the AUX server returned no tracks with that id' % (musicid, ))
        else:
            raise web.HTTPBadRequest(reason='unknow error')
        """



class ApollomusicResolver(ResolverBase):
    prefixes = [ 'APOLLO_',]
    name = 'ApolloMusic'
    prettyname = 'Apollo Music'
    website = 'http://findthethune.com/'
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

    async def resolve(self, filename, fromcache=True):
        self.filename = filename
        _musicid = self.musicid(filename)
        if fromcache:
            md = self.fromcache()
            if md is not None:
                return md
        #"do an http post request to apollomusic.dk"
        _lbl, _albumid, _trackno = _musicid.split('_')
        postdata = {'label_fk':_lbl,
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
                                        }
        # logging.debug('postdata: %s', postdata)
        headers = {'Cookie':logincookie}
        endpoint = 'http://www.findthetune.com/action/search_albums_action/'
        async with self.session.get(endpoint, params=postdata, headers=headers) as resp:
            logging.debug('hitting endpoint url: %r', resp.url)
            resp.raise_for_status() # bomb on errors
            data = await resp.json()
            logging.info('got data: %r', data)

            albumdata = data.pop()        # of 1 albumdict

            trackdata = albumdata['tracks'][int(_trackno, 10)-1] # return correct track, from the array of 'tracks' on the album dict
            del(albumdata['tracks'])
            try: _yr = int(trackdata.get('recorded', -1), 10)
            except:  _yr = -1
            metadata = TrackMetadata(filename=self.filename,
                        musiclibrary=self.name,
                        title=trackdata.get('primary_title', None),
                        # length=-1,
                        composer=trackdata.get('composer', None),
                        artist=trackdata.get('performer', None),
                        year=_yr,
                        recordnumber=_musicid,
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
            return metadata


class UniPPMResolver(ResolverBase):
    prefixes = [ ]
    name = 'UniPPM'
    prettyname = 'Universal Production Publising Music'
    website = 'http://www.unippm.se/'
    urlbase = 'http://www.unippm.se/Feeds/TracksHandler.aspx?method=workaudiodetails&workAudioId={musicid}' # HTTP GET interface, returns json
    labelmap = {  'AA':'Atmosphere Archive ',
                  'AK':'Atmosphere Kitsch ',
                  'AM':'Access Music ',
                  'ATMOS':'Atmosphere ',
                  'ATV':'Atmosphere TV ',
                  'AXS':'Access Promo ',
                  'BBCPM':'BBCPM',
                  'BCC':'Bruton Classical Series ',
                  'BEE':'Bruton Bee Stings ',
                  'BER':'Berlin Production Music',
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
                  'PKT': 'Unknown',
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
                  'STQM': 'Unknown',
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
        BER_1216B_76_Silent_Movie_Theme_Mersch_433103.wav -> 433103
        """
        rex = re.compile(r'^(%s)_\d{1,4}[A-Z]?_\d{1,4}_\w+_(\d+).*' % '|'.join(UniPPMResolver.labelmap.keys()), 
            re.UNICODE) # _<label>_<albumid>_<trackno>_<title>_<musicid>.wav
        g = rex.search(filename)
        try:
            return g.group(2)
        except AttributeError: #no match
            return None

    async def resolve(self, filename, fromcache=True):
        self.filename = filename
        _musicid = self.musicid(filename)
        if fromcache:
            md = self.fromcache()
            if md is not None:
                return md

        async with self.session.get(self.urlbase.format(musicid=_musicid)) as resp:
            logging.debug('hitting endpoint url: %r', resp.url)
            resp.raise_for_status() # bomb on errors
            data = await resp.json()
            logging.info('got data: %r', data)
            composers = [ data.get('shares', []) ]

            metadata = TrackMetadata(filename=self.filename,
                    musiclibrary=self.name,
                    title=data.get('WorkName', None),
                    # length=-1,
                    composer=data.get('WorkComposers', None),
                    artist=None,
                    year=-1,
                    recordnumber=_musicid,
                    albumname=data.get('WorkGroupingName', None),
                    copyright='Universal Publishing Production Music',
                    # lcnumber=None,
                    # isrc=None,
                    # ean=None,
                    # catalogue=None,
                    label=data.get('LabelName', ''),
                    # lyricist=None,
                    identifier='UniPPMTrack# %s' % _musicid
                    )
            metadata.productionmusic = True
            return metadata


class UprightmusicResolver(ResolverBase):
    prefixes = [ '_UPRIGHT',]
    name = 'UprightMusic'
    prettyname = 'Upright Music'
    website = 'http://www.upright-music.com/'
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

    async def resolve(self, filename, fromcache=True):
        self.filename = filename
        if fromcache:
            md = self.fromcache()
            if md is not None:
                self.trackResolved.emit(self.filename, md)
                return
        self.worker = lookupWorkers.UprightmusicLookupWorker()
        self.worker.progress.connect(self.progress)
        self.worker.trackResolved.connect(lambda md: self.trackResolved.emit(self.filename, md))
        self.worker.trackFailed.connect(lambda: self.trackFailed.emit(self.filename))
        self.worker.error.connect(lambda msg: self.error.emit(self.filename, msg))
        # check login cookie, without it we get nothing from the service
        if self.logincookie is None:
            self.error.emit(self.filename, u"You need to log in to UprightMusic before we can look something up")
            self.trackFailed.emit(self.filename)
            return

        self.worker.load(filename, self.logincookie)


class ExtremeMusicResolver(ResolverBase):
    prefixes = [ ]
    name = 'ExtremeMusic'
    prettyname = 'Extreme Music'
    website = 'https://www.extrememusic.com/'
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

    async def resolve(self, filename, fromcache=True):
        self.filename = filename
        if fromcache:
            md = self.fromcache()
            if md is not None:
                return md

        self.worker = lookupWorkers.ExtremeMusicLookupWorker()
        self.worker.progress.connect(self.progress)
        self.worker.trackResolved.connect(lambda md: self.trackResolved.emit(self.filename, md))
        self.worker.trackFailed.connect(lambda: self.trackFailed.emit(self.filename))
        self.worker.error.connect(lambda msg: self.error.emit(self.filename, msg))
        # check login cookie, without it we get nothing from the service
        if self.logincookie is None:
            self.fetchlogincookie()

        self.worker.load(filename, self.logincookie)

    def fetchlogincookie(self):
        "get loging cookie / session token"
        #0. Get session token
        #curl 'https://www.extrememusic.com/env' -H 'Accept: application/json, text/javascript, */*; q=0.01' -H 'Referer: https://www.extrememusic.com/labels/1' -H 'X-Requested-With: XMLHttpRequest' -H 'User-Agent: Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/53.0.2785.116 Safari/537.36' --compressed
        ENVURL = 'https://www.extrememusic.com/env'
        env = json.loads(urllib.request.urlopen(ENVURL).read().decode())
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
        req = urllib.request.Request('https://lapi.extrememusic.com/grid_items?range=0%2C200&view=series')
        req.add_header('X-API-Auth', self.logincookie)

        labels = json.loads(urllib.request.urlopen(req).read().decode())
        r = { g['image_detail_url'][59:62].upper() : g['title'] for g in labels['grid_items'] }
        return r

# a list of supported resolvers, for easy disabling etc
CURRENT_RESOLVERS = [
    DMAResolver,
    AUXResolver,
    ApollomusicResolver,
    UniPPMResolver,
    UprightmusicResolver,
    ExtremeMusicResolver,
    GenericFileResolver
]