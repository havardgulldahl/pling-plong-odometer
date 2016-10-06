#-*- encoding: utf8 -*-
# This file is part of odometer by Håvard Gulldahl <havard.gulldahl@nrk.no>
# (C) 2016

import PyQt4.QtCore as Core
import logging

import urllib, urllib2

import json
import StringIO

from model import TrackMetadata
import resolvers
import gluon

GLUON_HTTP_LOOKUP="http://mamcdma02/DMA/"

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
        self.musicid = resolvers.getmusicid(filename)
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
        self.musicid = resolvers.ApollomusicResolver.musicid(filename)
        self.logincookie = logincookie
        self.start()

    def run(self):
        try:
            albumdata, trackdata = self.request(self.musicid, self.logincookie)
        except TypeError: # self.request will return None on login errors
            albumdata, trackdata = (None, None)
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
                 musiclibrary=resolvers.ApollomusicResolver.name,
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
        if len(response) == 0:
            # empty response, likely not logged in or expired login cookie
            self.trackFailed.emit()
            self.error.emit('Tried to lookup %s, but failed. Please try to log in to Apollo again' % (musicid,))
            return None
        albumdata = response.pop()        # of 1 albumdict

        trackdata = albumdata['tracks'][int(_trackno, 10)-1] # return correct track, from the array of 'tracks' on the album dict
        del(albumdata['tracks'])
        return albumdata, trackdata



class UniPPMLookupWorker(Core.QThread):
    trackResolved = Core.pyqtSignal(TrackMetadata, name="trackResolved" )
    trackFailed = Core.pyqtSignal(name="trackFailed" )
    progress = Core.pyqtSignal(int, name="progress" )
    error = Core.pyqtSignal(unicode, name="error") # unicode : error msg

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
        #print trackdata
        if trackdata is None:
            return
        self.progress.emit(75)
        # trackdata looks like this:
#         {
#         VersionId: 1681900,
#         VersionDescription: null,
#         WorkName: "Fake Friends",
#         LabelId: 0,
#         WorkId: 696000,
#         WorkAudioId: 794691,
#         Publishers: [
#         {
#         Name: "Kapagama",
#         Society: "SACEM"
#         },
#         {
#         Name: "Kosinus",
#         Society: "SACEM"
#         }
#         ],
#         Composers: null,
#         WorkGroupingId: 10467,
#         WorkGroupingName: "Drama TV Series - Season 3",
#         DiscNo: 453,
#         TrackNo: 36,
#         TrackNoIndex: 0,
#         LabelDescription: null,
#         LabelName: "KOS",
#         Lyrics: "",
#         CDNTrackName: null,
#         CDNFilePath: null,
#         VersionType: null,
#         Length: null,
#         BPM: null,
#         DiscNoSuffix: null,
#         WorkComposers: "Yannick Kalfayan [SACEM]",
#         Duration: null,
#         Versions: [
#         {
#         VersionId: 1681900,
#         WorkId: 696000,
#         DurationId: 6,
#         WorkAudioId: 794691,
#         TrackNumber: 36,
#         TrackNoIndex: 0,
#         Length: 98,
#         VersionType: "Main Track",
#         VersionDescription: "",
#         EditType: "Full Length",
#         BPM: 0,
#         AudioFilePath: "46/91/KOS_453_36_Fake_Friends_Kalfayan_794691",
#         InVirtualLibrary: false,
#         WorkName: null,
#         PrsUrl: null,
#         PrsAltText: null
#         }
#         ],
#         InVirtualLibrary: false,
#         Label: "Kosinus"
#         }
        composers = [ trackdata.get('shares', []) ]

        metadata = TrackMetadata(filename=self.filename,
                 musiclibrary=resolvers.UniPPMResolver.name,
                 title=trackdata.get('WorkName', None),
                 # length=-1,
                 composer=trackdata.get('WorkComposers', None),
                 artist=None,
                 year=-1,
                 recordnumber=self.musicid,
                 albumname=trackdata.get('WorkGroupingName', None),
                 copyright='Universal Publishing Production Music',
                 # lcnumber=None,
                 # isrc=None,
                 # ean=None,
                 # catalogue=None,
                 label=trackdata.get('LabelName', ''),
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
        endpoint = 'http://www.unippm.se/Feeds/TracksHandler.aspx'
        try:
            data = ( ('method','workaudiodetails'),
                     ('workAudioId', musicid)
                   )
            r = urllib2.Request(endpoint + '?' + urllib.urlencode(data))
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
        if len(response) == 0:
            # empty response,
            self.trackFailed.emit()
            self.error.emit('Tried to lookup %s, but failed. Please try again' % (musicid,))
            return None
        trackdata = response
        albumdata = None # TODO: get this
        return albumdata, trackdata


class UprightmusicLookupWorker(Core.QThread):
    trackResolved = Core.pyqtSignal(TrackMetadata, name="trackResolved" )
    trackFailed = Core.pyqtSignal(name="trackFailed" )
    progress = Core.pyqtSignal(int, name="progress" )
    error = Core.pyqtSignal(unicode, name="error") # unicode : error msg

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
            r = urllib2.Request(endpoint + '?' + urllib.urlencode(data))
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
        if len(response) == 0:
            # empty response, likely not logged in or expired login cookie
            self.trackFailed.emit()
            self.error.emit('Tried to lookup %s, but failed. Please try to log in to Apollo again' % (musicid,))
            return None
        trackdata = response['track'] # return correct track, from the array of 'tracks' on the album dict
        albumdata = None # TODO: get this
        return albumdata, trackdata



class ExtremeMusicLookupWorker(Core.QThread):
    trackResolved = Core.pyqtSignal(TrackMetadata, name="trackResolved" )
    trackFailed = Core.pyqtSignal(name="trackFailed" )
    progress = Core.pyqtSignal(int, name="progress" )
    error = Core.pyqtSignal(unicode, name="error") # unicode : error msg

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
            trackdata = self.request(self.musicid, self.logincookie)
        except TypeError: # self.request will return None on login errors
            trackdata = None
        # print trackdata
        if trackdata is None:
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

        for version in trackdata['track_sounds']:
            if self.musicid == version['track_sound_no']: # this is the one
                version_title = '%s (%s)' % (version['title'], version['version_type'])
                version_duration = version['duration']


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
                 albumname=albumdata.get('album_title', None),
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
                r = urllib2.Request(url, headers)
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
        return trackdata['track']



