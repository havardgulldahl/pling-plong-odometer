#-*- encoding: utf8 -*-
# This file is part of odometer by Håvard Gulldahl <havard.gulldahl@nrk.no>
# (C) 2016-2017

from builtins import str
import PyQt5.QtCore as Core
import logging
from datetime import datetime

import urllib.parse 
import urllib.request
import json
from io import StringIO

from .model import TrackMetadata
from . import resolvers
from . import gluon

from pprint import pformat, pprint
GLUON_HTTP_LOOKUP="http://malxdmamv01/"

class LogThread(Core.QThread):
    'QThread subclass to log all exceptions and not bomb out on them'

    def __init__(self, parent, **kwargs):
        super(LogThread, self).__init__(parent, **kwargs)
        self._real_run = self.run
        self.run = self._wrap_run

    def _wrap_run(self):
        try:
            self._real_run()
        except Exception as e:
            logging.exception('Exception during LogThread.run: %r', e)

class GluonLookupWorker(LogThread):
    'Lookup a DMA track on gluon and retrieve metadata'
    trackResolved = Core.pyqtSignal(TrackMetadata, name="trackResolved" )
    trackFailed = Core.pyqtSignal(name="trackFailed" )
    progress = Core.pyqtSignal(int, name="progress")
    error = Core.pyqtSignal(str, name="error")

    def __init__(self, parent=None):
        super(GluonLookupWorker, self).__init__(parent)

    def __del__(self):
        self.wait()

    def load(self, filename):
        self.filename = filename
        self.musicid = resolvers.getmusicid(filename)
        self.start()

    def run(self):
        response = self.request(self.musicid)
        if response is None:
            return
        self.progress.emit(50)
        gp = gluon.GluonMetadataResponseParser()
        metadata = gp.parse(StringIO(response), factory=TrackMetadata)
        self.progress.emit(70)
        self.trackResolved.emit(metadata)
        self.progress.emit(100)
        #self.terminate()
        #self.deleteLater()

    def request(self, musicid):
        "do an http post request with given gluon xml payload"
        try:
            req = urllib.request.urlopen(GLUON_HTTP_LOOKUP +  musicid + '.xml')
        except IOError as e:
            # e.g. dns lookup failed
            self.trackFailed.emit()
            self.error.emit('Tried to lookup %s, but failed. Are you connected to the internet? (%s)' % (musicid, str(e)))
            return None

        if req.getcode() in (404, 403, 401, 400, 500):
            self.trackFailed.emit()
            self.error.emit('Tried to look up %s, but got %s' % (musicid, req.getcode()))
            return None
        response = req.read().decode()
        return response

class ApollomusicLookupWorker(LogThread):
    trackResolved = Core.pyqtSignal(TrackMetadata, name="trackResolved" )
    trackFailed = Core.pyqtSignal(name="trackFailed" )
    progress = Core.pyqtSignal(int, name="progress" )
    error = Core.pyqtSignal(str, name="error") # str : error msg

    def __init__(self, parent=None):
        super(ApollomusicLookupWorker, self).__init__(parent)

    def __del__(self):
        self.wait()

    def load(self, filename):
        self.filename = filename
        self.musicid = resolvers.ApollomusicResolver.musicid(filename)
        self.start()

    def get_sec(self, time_str):
        'helper method to get seconds from a time string, e.g. "01:04" -> 64'
        try:
            m, s = time_str.split(':')
            return int(m) * 60 + int(s)
        except ValueError:
            return -1

    def run(self):
        trackdata = self.request(self.musicid)
        logging.debug('got apollo track data: %r', trackdata)
        if trackdata is None:
            self.trackFailed.emit()
            self.error.emit('Tried to look up %s, but got failed -- dont know why, sorry' % (self.musicid))
            return None
        self.progress.emit(50)
        try: _yr = int(trackdata.get('recorded', -1), 10)
        except:  _yr = -1
        metadata = TrackMetadata(filename=self.filename,
                 musiclibrary=resolvers.ApollomusicResolver.name,
                 title=trackdata.get('primary_title', None),
                 length=self.get_sec(trackdata.get('duration', '')),
                 composer=trackdata.get('composer', None),
                 artist=trackdata.get('performer', None),
                 year=_yr,
                 recordnumber=self.musicid,
                 albumname=trackdata.get('album_title', None),
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

    def request(self, musicid):
        "do an http post request to apollomusic.dk"
        try:
            _lbl, _albumid, _trackno = self.musicid.split('_')
            params = {
                'label': _lbl,
                'album': _albumid,
                'track': _trackno
            }
            endpoint = 'http://www.findthetune.com/guests/search/label={label}&album={album}&track={track}'.format(**params)
            r = urllib.request.Request(endpoint)
            req = urllib.request.urlopen(r)

        except IOError as e:
            # e.g. dns lookup failed
            logging.exception(e)
            self.trackFailed.emit()
            self.error.emit('Tried to lookup %s, but failed. Are you connected to the internet? (%s)' % (musicid, str(e)))
            return None

        if req.getcode() in (404, 403, 401, 400, 500):
            logging.warning('apollo lookup returned %r', req.getcode())
            self.trackFailed.emit()
            self.error.emit('Tried to look up %s, but got %s' % (musicid, req.getcode()))
            return None

        response = json.loads(req.read().decode('utf-8')) # it's a json array
        if len(response) == 0:
            # empty response, likely not logged in or expired login cookie
            logging.warning('apollo lookup returned empty response')
            self.trackFailed.emit()
            self.error.emit('Tried to lookup %s, but failed. Please try to log in to Apollo again' % (musicid,))
            return None
        logging.debug('apolllo %s json data: %s', musicid, pformat(response))
        trackdata = response['tracks'][0]
        return trackdata



class UniPPMLookupWorker(LogThread):
    trackResolved = Core.pyqtSignal(TrackMetadata, name="trackResolved" )
    trackFailed = Core.pyqtSignal(name="trackFailed" )
    progress = Core.pyqtSignal(int, name="progress" )
    error = Core.pyqtSignal(str, name="error") # str : error msg

    def __init__(self, parent=None):
        super(UniPPMLookupWorker, self).__init__(parent)

    def __del__(self):
        self.wait()

    def load(self, filename):
        self.filename = filename
        self.musicid = None
        self.start()

    def run(self):
        # first, get track id
        self.progress.emit(10)
        self.musicid = resolvers.UniPPMResolver.musicid(self.filename)
        if self.musicid is None:
            # could not extract track id from filename
            self.trackFailed.emit()
            self.error.emit('Tried to get UniPPM track id from filename "%s", but failed. Please report this.' % (self.filename, ))
            return None

        self.progress.emit(50)

        # then, get all metadata
        albumdata, trackdata = self.request_trackdata(self.musicid)
        #print(trackdata)
        # trackdata looks like this: 
        '''         {
            "v": 1681900,
            "vt": "Main Track",
            "tt": "Fake Friends",
            "ac": "https://dams.cdn.unippm.com/AlbumImages/59x59/d9712fdd7ec84ec4bcfd74f398e9276f.jpg",
            "ano": "KOS453",
            "ana": "Drama TV Series - Season 3",
            "ad": "A Perfect Kit For Modern TV Drama Series",
            "tno": "36",
            "td": "DRAMEDY - Medium - Stealthy & wry dramedy theme - Pizzicato, piano, percussion, double bass - TV Series, sitcoms",
            "bwaid": 794691,
            "vc": 1,
            "w": 696000,
            "wg": 10467,
            "tg": [
                {
                    "id": 18431,
                    "na": "2000s",
                    "cid": 17,
                    "cn": "Eras"
                },
                {
                    "id": 18432,
                    "na": "2010s",
                    "cid": 17,
                    "cn": "Eras"
                },
                {
                    "id": 18597,
                    "na": "Piano",
                    "cid": 18,
                    "cn": "Instruments"
                },
                {
                    "id": 18817,
                    "na": "Pizzicato",
                    "cid": 18,
                    "cn": "Instruments"
                },
                {
                    "id": 18819,
                    "na": "String Section",
                    "cid": 18,
                    "cn": "Instruments"
                },
                {
                    "id": 18925,
                    "na": "Intrigue",
                    "cid": 19,
                    "cn": "Moods"
                },
                {
                    "id": 18971,
                    "na": "Stealthy",
                    "cid": 19,
                    "cn": "Moods"
                },
                {
                    "id": 19041,
                    "na": "Anticipation",
                    "cid": 19,
                    "cn": "Moods"
                },
                {
                    "id": 19052,
                    "na": "Mysterious",
                    "cid": 19,
                    "cn": "Moods"
                },
                {
                    "id": 19056,
                    "na": "Suspenseful",
                    "cid": 19,
                    "cn": "Moods"
                },
                {
                    "id": 19101,
                    "na": "Light Comedy",
                    "cid": 20,
                    "cn": "Music For"
                },
                {
                    "id": 19159,
                    "na": "Family/Light Comedy",
                    "cid": 20,
                    "cn": "Music For"
                },
                {
                    "id": 19177,
                    "na": "Reality TV",
                    "cid": 20,
                    "cn": "Music For"
                },
                {
                    "id": 19187,
                    "na": "Spy/Detective",
                    "cid": 20,
                    "cn": "Music For"
                },
                {
                    "id": 19196,
                    "na": "American Comedy",
                    "cid": 20,
                    "cn": "Music For"
                },
                {
                    "id": 19614,
                    "na": "Medium",
                    "cid": 22,
                    "cn": "Tempos"
                }
            ],
            "wa": [
                {
                    "wadId": 6,
                    "vop": 1,
                    "wop": 1,
                    "v": 1681900,
                    "a": "https://stream.music.cdn.unippm.com/KOS/KOS453/Fake_Friends/KOS_453_36_Fake_Friends_Kalfayan_794691.mp3",
                    "a2": "https://stream.music.cdn.unippm.com/KOS/KOS453/Fake_Friends/KOS_453_36_Fake_Friends_Kalfayan_794691.mp4",
                    "t": 36,
                    "wai": 794691,
                    "d": 98,
                    "vd": ""
                }
            ],
            "c": "Yannick Kalfayan [SACEM]",
            "l": "Kosinus",
            "lid": 138,
            "d": 98,
            "hs": false,
            "cData": [
                {
                    "id": 11382,
                    "na": "Yannick Kalfayan",
                    "s": "SACEM"
                }
            ],
            "pData": [
                {
                    "id": 79,
                    "na": "Kapagama"
                },
                {
                    "id": 194,
                    "na": "Kosinus"
                }
            ],
            "tid": "KOS453-36",
            "hly": false
        } '''
        if trackdata is None:
            return
        self.progress.emit(75)

        composers = [ x.get('na') for x in trackdata.get('cData') ]

        metadata = TrackMetadata(filename=self.filename,
                 musiclibrary=resolvers.UniPPMResolver.name,
                 title=trackdata.get('tt', None),
                 length=trackdata.get('d', -1),
                 composer=trackdata.get('c', None),
                 artist=None,
                 year=-1,
                 recordnumber=trackdata.get('tid', self.musicid),
                 albumname=trackdata.get('ana', None),
                 copyright='Universal Publishing Production Music',
                 # lcnumber=None,
                 # isrc=None,
                 # ean=None,
                 catalogue=trackdata.get('l', None),
                 label=trackdata.get('l', None),
                 # lyricist=None,
                 identifier='UniPPMTrack# %s' % self.musicid,
                 )
        metadata.productionmusic = True
        self.progress.emit(90)
        self.trackResolved.emit(metadata)
        self.progress.emit(100)
        #self.terminate()
        #self.deleteLater()

    def request_trackdata(self, musicid):
        """do an http get request to www.unippm.se/Feeds/TracksHandler.aspx

        look up musicid, e.g 794691

        by doing a get request to
        http://www.unippm.se/Feeds/TracksHandler.aspx?method=workaudiodetails&workAudioId=794691'

        and parse the json we get back

        """
        #endpoint = 'http://www.unippm.se/Feeds/TracksHandler.aspx'
        endpoint = 'http://cloud1.search.universalproductionmusic.com/uppm_work_12_1/select?q=editIds:(%s)'
        try:
            _req_url = endpoint % (musicid,)
            r = urllib.request.Request(_req_url)
            logging.debug('scraping track metadata from unippm: %r', _req_url)
            req = urllib.request.urlopen(r)

        except IOError as e:
            # e.g. dns lookup failed
            self.trackFailed.emit()
            self.error.emit('Tried to lookup %s, but failed. Are you connected to the internet? (%s)' % (musicid, str(e)))
            return None

        if req.getcode() in (404, 403, 401, 400, 500):
            self.trackFailed.emit()
            self.error.emit('Tried to look up %s, but got %s' % (musicid, req.getcode()))
            return None

        response = json.loads(req.read().decode('utf-8')) # it's a json array
        if len(response) == 0:
            # empty response,
            self.trackFailed.emit()
            self.error.emit('Tried to lookup %s, but failed. Please try again' % (musicid,))
            return None
        trackdata = response.get('docs')[0]
        albumdata = None # TODO: get this
        return albumdata, trackdata


class UprightmusicLookupWorker(LogThread):
    trackResolved = Core.pyqtSignal(TrackMetadata, name="trackResolved" )
    trackFailed = Core.pyqtSignal(name="trackFailed" )
    progress = Core.pyqtSignal(int, name="progress" )
    error = Core.pyqtSignal(str, name="error") # str : error msg

    def __init__(self, parent=None):
        super(UprightmusicLookupWorker, self).__init__(parent)

    def __del__(self):
        self.wait()

    def load(self, filename, logincookie):
        self.filename = filename
        self.musicid = None
        self.logincookie = logincookie
        self.start()

    def run(self):
        # first, get track guid
        self.progress.emit(10)

        self.musicid = self.request_guid(self.filename)
        self.progress.emit(50)

        # then, get all metadata
        albumdata, trackdata = self.request_trackdata(self.musicid)
        # print trackdata
        if trackdata is None:
            return
        self.progress.emit(75)
        # trackdata looks like this:
#         {"id":"6288627e-bae8-49c8-9f3c-f6ed024eb698",
#           "number":"6",
#             "title":"Downplay",
#               "album":{"number": "016",
#                        "title": "Bassline Garage",
#                        "label":"EDS 016 Bassline Garage",
#                        "library":{"id":"83981fec-466a-4ac5-bc27-a7c71e3491eb",
#                                   "code":"EDS",
#                                   "name":"Electronic Dance Series"}
#                       },"audiofiles":[{"id":"5a5a9381-ca19-4af3-b661-61fda3418962",
#                                        "quality":"1",
#                                        "type":"WAV",
#                                        "duration":"0"},
#                                       {"id":"e5d3b215-3810-4cf9-9e89-7cc3218b2cc7",
#                                        "quality":"0",
#                                        "type":"MP3",
#                                        "duration":"141.662"},
#                                       {"id":"f597087f-8cc8-47ab-b67d-adeed9469932",
#                                        "quality":"1",
#                                        "type":"MP3",
#                                        "duration":"141.662"}],
#          "shares":[{"id":"43b54626-b7d2-4b46-903d-e5e9f183d1e0",
#                     "stakeholder":{"id":"832c2692-0b06-42dc-bf22-bf8561d3313a",
#                                    "name":"Taelimb"}},
#                    {"id":"98101458-d04c-4f6e-8b3c-2d2b32f66609",
#                     "stakeholder":{"id":"4a45efe3-d4af-41cf-bd10-b4ccea78b95b",
#                                    "name":"Ogre"}
#                    }
#                   ]
#         }

        composers = [ s['stakeholder']['name'] for s in trackdata.get('shares', []) ]


        metadata = TrackMetadata(filename=self.filename,
                 musiclibrary=UprightmusicResolver.name,
                 title=trackdata.get('title', None),
                 # length=-1,
                 composer=", ".join(composers),
                 artist=None,
                 year=-1,
                 recordnumber=self.musicid,
                 albumname=trackdata['album']['title'],
                 copyright='Upright Music',
                 # lcnumber=None,
                 # isrc=None,
                 # ean=None,
                 # catalogue=None,
                 label=trackdata['album']['library']['name'],
                 # lyricist=None,
                 identifier='uprighttrack# %s' % trackdata.get('id', -1),
                 )
        metadata.productionmusic = True
        self.progress.emit(90)
        self.trackResolved.emit(metadata)
        self.progress.emit(100)
        #self.terminate()
        #self.deleteLater()

    def request_trackdata(self, musicid):
        """do an http get request to search.upright-music.com

        look up musicid, e.g 6288627e-bae8-49c8-9f3c-f6ed024eb698

        by doing a get request to
        http://search.upright-music.com/sites/all/modules/up/session.php?handler=load&tid=6288627e-bae8-49c8-9f3c-f6ed024eb698

        and parse the json we get back

        """
        endpoint = 'http://search.upright-music.com/sites/all/modules/up/session.php'
        try:
            data = ( ('handler','load'),
                     ('tid', musicid)
                   )
            r = urllib.request.Request(endpoint + '?' + urllib.parse.urlencode(data))
            req = urllib.request.urlopen(r)

        except IOError as e:
            # e.g. dns lookup failed
            self.trackFailed.emit()
            self.error.emit('Tried to lookup %s, but failed. Are you connected to the internet? (%s)' % (musicid, str(e)))
            return None

        if req.getcode() in (404, 403, 401, 400, 500):
            self.trackFailed.emit()
            self.error.emit('Tried to look up %s, but got %s' % (musicid, req.getcode()))
            return None

        response = json.loads(req.read().decode('utf-8')) # it's a json array
        if len(response) == 0:
            # empty response, likely not logged in or expired login cookie
            self.trackFailed.emit()
            self.error.emit('Tried to lookup %s, but failed. Please try to log in to Apollo again' % (musicid,))
            return None
        trackdata = response['track'] # return correct track, from the array of 'tracks' on the album dict
        albumdata = None # TODO: get this
        return albumdata, trackdata



class ExtremeMusicLookupWorker(LogThread):
    trackResolved = Core.pyqtSignal(TrackMetadata, name="trackResolved" )
    trackFailed = Core.pyqtSignal(name="trackFailed" )
    progress = Core.pyqtSignal(int, name="progress" )
    error = Core.pyqtSignal(str, name="error") # str : error msg

    def __init__(self, parent=None):
        super(ExtremeMusicLookupWorker, self).__init__(parent)

    def __del__(self):
        self.wait()

    def load(self, filename, logincookie):
        self.filename = filename
        self.musicid = resolvers.ExtremeMusicResolver.musicid(filename)
        self.logincookie = logincookie
        self.start()

    def run(self):
        try:
            data = self.request(self.musicid, self.logincookie)
        except TypeError: # self.request will return None on login errors
            data = None
        # print trackdata
        if data is None:
            return
        self.progress.emit(75)

        # Extreme Music has different versions of each song
        # e.g. "full version", "30 seconds", "bass only", etc.
        # and the different variants share the track_id, but
        # the track_sound_no will be different and equal to
        # self.musicid

        version_title = None
        version_duration = -1
        version_musicid = None

        logging.debug('Got following trackdata from Extreme: %s', pformat(data))
        for version in data['track_sounds']:
            if self.musicid == version['track_sound_no']: # this is the one
                version_title = '%s (%s)' % (version['title'], version['version_type'])
                version_duration = version['duration']


        trackdata = data['track']
        composers = ['%s (%s)' % (c['name'], c['society']) for c in trackdata['composers']]
        arrangers = ['%s' % (c['name'],) for c in trackdata['arrangers']]

        metadata = TrackMetadata(filename=self.filename,
                 musiclibrary=resolvers.ExtremeMusicResolver.name,
                 title=version_title or trackdata.get('title', None),
                 length=version_duration or trackdata.get('duration', -1),
                 composer=', '.join(composers),
                 artist=None,
                 year=-1,
                 recordnumber=self.musicid,
                 albumname=trackdata.get('album_title', None),
                 copyright=', '.join([c['name'] for c in trackdata['collecting_publishers']]),
                 # lcnumber=None,
                 # isrc=None,
                 # ean=None,
                 # catalogue=None,
                 label=self.musicid[0:3],
                 # lyricist=None,
                 identifier='extremetrack# %s' % trackdata.get('track_id', -1),
                 )
        metadata.productionmusic = True
        self.progress.emit(90)
        self.trackResolved.emit(metadata)
        self.progress.emit(100)
        #self.terminate()
        #self.deleteLater()

    def request(self, musicid, logincookie):
        "do http requests to lapi.extrememusic.com to get track metadata"

        def req(url):
            "helper function to do all the http heavy lifting. get url, return json"

            try:
                headers = {'X-API-Auth':logincookie}
                r = urllib.request.Request(url, headers=headers)
                req = urllib.request.urlopen(r)

            except IOError as e:
                # e.g. dns lookup failed
                self.trackFailed.emit()
                self.error.emit('Tried to lookup %s, but failed. Are you connected to the internet? (%s)' % (musicid, str(e)))
                return None

            if req.getcode() in (404, 403, 401, 400, 500):
                self.trackFailed.emit()
                self.error.emit('Tried to look up %s, but got %s' % (musicid, req.getcode()))
                return None

            response = json.loads(req.read().decode('utf-8')) # it's a json array
            if len(response) == 0:
                # empty response, likely not logged in or expired login cookie
                self.trackFailed.emit()
                self.error.emit('Tried to lookup %s, but failed. Please try again' % (musicid,))
                return None
            return response

        srch = req('https://lapi.extrememusic.com/search/tracks?query=%s&mode=filter' % musicid)
        if srch is None:
            return None
        self.progress.emit(40)
        if not len(srch['track_search_result_items']) > 0:
            # something is wrong, no results
            self.trackFailed.emit()
            self.error.emit('The Extreme Music catalogue does not seem to know anything about this music id: %s' % (musicid, ))
            return None
        # get internal music id
        extrack_id = srch['track_search_result_items'][0]['track_id']
        trackdata = req('https://lapi.extrememusic.com/tracks/%s' % extrack_id)
        if trackdata['track'] is None:
            # something is wrong, no results
            self.trackFailed.emit()
            self.error.emit('The Extreme Music catalogue does not seem to know anything about this music id: %s (internal music id: %s)' % (musicid, extrack_id))
            return None
        return trackdata



class AUXLookupWorker(LogThread):
    trackResolved = Core.pyqtSignal(TrackMetadata, name="trackResolved" )
    trackFailed = Core.pyqtSignal(name="trackFailed" )
    progress = Core.pyqtSignal(int, name="progress" )
    error = Core.pyqtSignal(str, name="error") # str : error msg

    def __init__(self, parent=None):
        super(AUXLookupWorker, self).__init__(parent)

    def __del__(self):
        self.wait()

    def load(self, filename):
        self.filename = filename
        self.musicid = None
        self.start()

    def run(self):
        # first, get track id
        self.progress.emit(10)
        self.musicid = resolvers.AUXResolver.musicid(self.filename)
        if self.musicid is None:
            # could not extract track id from filename
            self.trackFailed.emit()
            self.error.emit('Tried to get AUX track id from filename "%s", but failed. Please report this.' % (self.filename, ))
            return None

        self.progress.emit(50)

        # then, get all metadata
        albumdata, trackdata = self.request_trackdata(self.musicid)
        #print trackdata
        if trackdata is None:
            return
        self.progress.emit(75)
        # trackdata looks like this:
        # {
        # "tracks": [
        #     {
        #     "cd_samples": "",
        #     "cd_neu": "1",
        #     "cd_genre": "",
        #     "disc": "",
        #     "cd_title": "SPORTS ATTACK",
        #     "cd_description": "Aggressive, muscular and tough athletes, triumphant in rousing rock renditions, covering metal, alternative, indie and hard rock styles. Performed by members of the legendary metal band RUNNING WILD.",
        #     "cd_trackcnt": "37",
        #     "releasedat": "2016-07-29",
        #     "cd_webmix": "1",
        #     "cd_surround": "0",
        #     "cd_isrc": "",
        #     "ean": "4020771163564",
        #     "credits": "Arranged and produced by Peter Jordan. Recorded and mastered at PJ Music & Horus Sound Studio, Hannover, Germany. Sound engineers: Peter Jordan, Arne Neurand and Andre Bollweg. \nPerformed by Peter Jordan (guitars, bass, keyboards & percusssion), Ole Hempelmann (bass) and Michael Wolpers (drums & percussion)\n\nMusic consultant: Robert Narholz (LENA Film Inc., L.A.)\nCover design: Sahar Aharoni\n\nISRC: DE-B63-16-356-01-37  *  GTIN\/UPC: 4020771163564",
        #     "label": "ROCK",
        #     "p_nummer": "156",
        #     "p_cut": "2.0",
        #     "zeit": "0:30",
        #     "nZeit": "30",
        #     "solo": "GIEF",
        #     "allkomp": "Peter Jordan",
        #     "besetzb": "1",
        #     "versionb": "128",
        #     "tempob": "2",
        #     "soundb": "2",
        #     "has_mp3": "1",
        #     "has_mp3down": "1",
        #     "has_mp3play": "1",
        #     "has_wav": "1",
        #     "has_aiff": "1",
        #     "expreis": "0",
        #     "extrail": "0",
        #     "cdkurz": "ROCK015602",
        #     "cdcdkurz": "ROCK0156",
        #     "maintrack": "1.0",
        #     "webmix": "1",
        #     "surround": "0",
        #     "isrc": "DE-B63-16-356-02",
        #     "funktionen": "G73-G74-G75-G80-G81-G21-G14-INT-AGG-TVN-UNR-PRO-DXN-DRT-ENE-AUF-G17-DTA-ARK-RK1-HEM-COG-EXX-SSP-ARO-PUN-PRK-TLP-ACT-RCP-PSP-WST-",
        #     "copyrighted": "1",
        #     "bpm": "176",
        #     "tonart": "Gbmin",
        #     "haslyrics": "0",
        #     "hasstems": "0",
        #     "lyrics": "",
        #     "iswc": "",
        #     "title": "THE HYPE B",
        #     "description": "Commercial length. Uptempo alternative rock, punk rock with big nasty attitude for rough competition and endurance sports. 176 bpm (Gbmin)",
        #     "keywords": "Instrumental, Aggressive, Aggression, Combative, Fiery, Furious, In your face, Offensive, Provocative, Punchy, Rage, Raging, Rampaging, hard-hitting, Driving, Restless, Agitated, Agitation, Antsy, Anxious, Fidgety, Propulsive, Driving, Propelling, Dramatic Action, Dramatic, Stirring, Energetic, Dynamic, Exciting, Excite, Excitement, Electrifying, Rousing, Stimulating, Thrilling, Action, Panic, Action Heroes, Action Rock, Adrenalin, Arena, Baseball, Crime Drama, Football, Hockey, Macho, Punchy, Pursuit, Racing, Raging, Reckless, Stadium Rock, Urgency, 2010 Rock, 2010s Rock, Heavy Metal Rock, Death, Hooligan, Provocation, Skinhead, Yob, Videogames, Extreme Sports, Sport - Special Productions, Alternative Rock, Punk, Rebellious, Skinhead, Punk Rock, Skinhead, Trailer - Sports, Action Trailer, Rock promos, Sports - Promos, Commercials, Ads, Advertisements, Jingles, Spots,Guitar-electric,,fast,, ROCK015602, ROCK0156, ROCK",
        #     "alt_title": "",
        #     "langcode": "EN",
        #     "provider": "SON",
        #     "lc": "30572",
        #     "verlag": "Rockshop",
        #     "library": "Rockshop - ROCK",
        #     "gemadbnr": null,
        #     "notiz": "",
        #     "cd_notiz": "",
        #     "img": "rock\/rock0156.jpg",
        #     "repertoire": "ROCK",
        #     "licences": {
        #         "img": "\/img\/ctryspec\/rightsoc_NO.gif",
        #         "link": "",
        #         "text": "Copyright protected"
        #     },
        #     "tempotxt": "Fast",
        #     "soundtxt": "Natural sound",
        #     "formationtxt": "Small (1-10)",
        #     "versiontxt": "Commercial 29\/30 sec",
        #     "instruments": "Guitar-electric",
        #     "akomp1": "Peter Jordan",
        #     "artists": "Peter Jordan, Ole Hempelmann, Michael Wolpers",
        #     "csinfo": "Track name: THE HYPE B\r\nTrack number: ROCK 156  2.0 (Trackcode: ROCK015602)\r\nComposer: Peter Jordan, Artists: Peter Jordan, Ole Hempelmann, Michael Wolpers\r\nEAN\/GTIN: 4020771163564 \r\nISRC: DE-B63-16-356-02\r\nAlbum name: SPORTS ATTACK\r\nCatalogue number: 156  \r\nLabel: ROCK\r\nCopyright owner: SONOTON Music GmbH & Co. KG\r\nLC number: 30572",
        #     "dSec": "30",
        #     "dMin": "0"
        #     }
        # ],
        # "trackcnt": 1,
        # "cnt": 1,
        # "errmsg": "",
        # "ax_success": 1
        # }
        metadata = TrackMetadata(filename=self.filename,
                 musiclibrary=resolvers.AUXResolver.name,
                 title=trackdata.get('title', None),
                 length=trackdata.get('nZeit', -1),
                 composer=trackdata.get('allkomp', None),
                 artist=trackdata.get('artists', None),
                 year=-1,
                 recordnumber=self.musicid,
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
        self.progress.emit(90)
        metadata.productionmusic = True
        try:
            dt = datetime.strptime(trackdata.get('releasedat', None), '%Y-%m-%d') #SIC, 
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
        self.trackResolved.emit(metadata)
        self.progress.emit(100)
        #self.terminate()
        #self.deleteLater()

    def request_trackdata(self, musicid):
        """do an http get request to http://search.auxmp.co//search/html/ajax/axExtData.php

        look up musicid, e.g ROCK015601

        by doing a get request to
        http://search.auxmp.com//search/html/ajax/axExtData.php?cdkurz=ROCK015601&ac=track&country=NO'

        and parse the json we get back

        """
        endpoint = 'http://search.auxmp.com//search/html/ajax/axExtData.php'
        try:
            data = ( ('ac','track'),
                     ('country', 'NO'),
                     ('cdkurz', musicid)
                   )
            r = urllib.request.Request(endpoint + '?' + urllib.parse.urlencode(data))
            req = urllib.request.urlopen(r)

        except IOError as e:
            # e.g. dns lookup failed
            logging.exception(e)
            self.trackFailed.emit()
            self.error.emit('Tried to lookup %s, but failed. Are you connected to the internet? (%s)' % (musicid, str(e)))
            return None

        if req.getcode() in (404, 403, 401, 400, 500):
            self.trackFailed.emit()
            self.error.emit('Tried to look up %s, but got %s' % (musicid, req.getcode()))
            return None

        response = json.loads(req.read().decode('utf-8')) # it's a json array
        if len(response) == 0 or response.get('ax_success') != 1:
            # empty response,
            self.trackFailed.emit()
            self.error.emit('Tried to lookup %s, but failed. Please try again' % (musicid,))
            return None
        elif len(response.get('errmsg', '')) > 0:
            # we got an error message from auxmp.com
            self.trackFailed.emit()
            self.error.emit('Tried to lookup %s, but received an error from AUX: %r' % (musicid, response.errmsg))
        elif response.get('trackcnt') == 0:
            # auxmp.com didnt return any tracks for our search term
            self.trackFailed.emit()
            self.error.emit('Tried to lookup %s, but the AUX server returned no tracks with that id' % (musicid, ))
        trackdata = response.get('tracks')[0]
        albumdata = None # TODO: get this
        return albumdata, trackdata

