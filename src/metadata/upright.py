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
        self.worker = UprightmusicLookupWorker()
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



class UprightmusicLookupWorker(Core.QThread):
    trackResolved = Core.pyqtSignal(TrackMetadata, name="trackResolved" )
    trackFailed = Core.pyqtSignal(name="trackFailed" )
    progress = Core.pyqtSignal(int, name="progress" )
    error = Core.pyqtSignal(unicode, name="error") # unicode : error msg

    def __init__(self, parent=None):
        super(UprightLookupWorker, self).__init__(parent)

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
                 albumname=albumdata.get('album', {}).get(',
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
