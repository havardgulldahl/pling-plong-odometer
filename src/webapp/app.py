import sys
import os.path
import tempfile
import pathlib
from urllib.parse import quote
import configparser
import io
import datetime
import json
import functools
import concurrent

import asyncio

from aiohttp import web
import aiohttp

from aiohttp_swagger import swagger_path, setup_swagger

import aiohttp_jinja2 # pip install aiohttp-jinja2
import jinja2

import asyncpg # pip install asyncpg
import multidict # pip install multidict
from aiohttp_apispec import docs, use_kwargs, marshal_with, AiohttpApiSpec
import aiocache 
from aiocache.serializers import JsonSerializer

from xmeml import iter as xmemliter

from metadataresolvers import findResolvers, getAllResolvers, getResolverByName
import metadataresolvers

from rights import DueDiligence, DueDiligenceJSONEncoder, DiscogsNotFoundError, SpotifyNotFoundError, \
    remove_corporate_suffix, release_is_old_and_public_domain

import model

routes = web.RouteTableDef()
loop = asyncio.get_event_loop()
app = web.Application(loop=loop,
                      client_max_size=20*(1024**2)) # upload size max 20 megs
headers = { 'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_13_2) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/62.0.3202.94 Safari/537.36',
}
clientSession = aiohttp.ClientSession(loop=loop, headers=headers)
executor = concurrent.futures.ThreadPoolExecutor(max_workers=3)
aiohttp_jinja2.setup(app,
    loader=jinja2.FileSystemLoader('./templates'))

async def on_shutdown(_app):
    'Cleaning up right before shutdown'
    await clientSession.close()
    await _app.dbpool.close()

async def on_startup(_app):
    'Things to do on startup'
    _app.configuration = configparser.ConfigParser()
    _app.configuration.read('config.ini')
    _app.dbpool = await asyncpg.create_pool(dsn=_app.configuration.get('db', 'dsn'))
    _app.duediligence = DueDiligence(config=_app.configuration)
    _app.debugmode = False # set this in init

app.on_startup.append(on_startup)
app.on_shutdown.append(on_shutdown)
app.debugmode = False # set this in init

APIVERSION = '0.1'

async def store_resolve_result(_app, result_code, result_text, filename, resolver, overridden):
    'Helper to add result of a resolve attempt to DB'

    sql = '''INSERT INTO resolve_result (result_code, result_text, filename, resolver, overridden)
             VALUES ($1, $2, $3, $4, $5);'''
    async with _app.dbpool.acquire() as connection:
        await connection.execute(sql, result_code, result_text, filename, resolver, overridden)
        
async def store_copyright_result(_app, spotify_id, result, reason, spotify_label, parsed_label):
    'Helper to add result of a copyright lookup to DB'

    sql = '''INSERT INTO copyright_lookup_result (spotify_id, result, reason, spotify_label, parsed_label)
             VALUES ($1, $2, $3, $4, $5);'''
    async with _app.dbpool.acquire() as connection:
        await connection.execute(sql, spotify_id, result, reason, spotify_label, parsed_label)

class AudioClip:
    'The important properties of an audio clip for JSON export'
    def __init__(self, filename):
        self.filename = filename
        self.services = None  # [] set in is_resolvable()
        self.ranges = None  # [] set in set_ranges()
        self.audible_length = None  # float() set in set_ranges()

    def set_ranges(self, ranges):
        self.ranges = ranges
        audible_frames = len(ranges) # in frames
        self.audible_length = float(audible_frames) / ranges.framerate  # gives us seconds

    def is_audible(self):
        return self.audible_length > 0

    def is_resolvable(self):
        'Look at the filename and say if it is resolvable from one or the other service. Returns bool'
        resolvers = findResolvers(self.filename)
        if not resolvers:
            return False
        self.services = list([x.name for x in resolvers])
        return True

    def to_dict(self):
        'Boil everything down to a dict that is easy to jsonify'
        if not self.services: 
            app.logger.warning('No resolver services found for %s', self.filename)
            self.services = []
        return {'clipname': self.filename,
                'audible_length': self.audible_length,
                'resolvable': self.is_resolvable(),
                'music_services': self.services,
                'resolve': {s:'/api/resolve/{}/{}'.format(quote(s), quote(self.filename)) for s in self.services},
                'resolve_other': '/api/resolve/{{music_service}}/{}?override=1'.format(quote(self.filename)),
                'add_missing':'/api/add_missing/{}'.format(quote(self.filename)),
               }


@routes.get('/api/resolve/{resolver}/{audioname}')
@swagger_path("handle_resolve.yaml")
@aiocache.cached(key="handle_resolve", serializer=JsonSerializer())
async def handle_resolve(request):
    'Get an audioname from the request and resolve it from its respective service resolver'
    audioname = request.match_info.get('audioname', None) # match path string, see the respective route
    resolvername = request.match_info.get('resolver', None) # match path string, see the respective route
    override = request.query.get('override', False) == '1'
    app.logger.info('Parsed path and got audioname: %r, resolvername%r, overide? %s', audioname, resolvername, override)
    # find resolver as it is provided to us on the path string
    resolver = getResolverByName(resolvername)
    if resolver is None:
        try:
            resolver = findResolvers(audioname)[0]
        except IndexError: #no resolvers found
            return web.json_response({
                'error': {'type':'No resolvers found',
                          'args':'Nothing to resolve this file: {!r}'.format(audioname)},
                'metadata': []
            }, status=404)
    resolver.setSession(clientSession) # use the same session object for speedups
    resolver.setConfig(request.app.configuration)
    # add passwords for services that need it for lookup to succeed
    # run resolver
    app.logger.info("resolve audioname %r with resolver %r", audioname, resolver)
    try:
        metadata = await resolver.resolve(audioname, fuzzy=override)
    except aiohttp.ClientConnectorError as _e:
        await store_resolve_result(app, 400, str(_e.args), audioname, resolvername, override)
        return web.json_response({
            'error': {'type':_e.__class__.__name__,
                      'args':_e.args},
            'metadata': []
        }, status=400)
    except (aiohttp.client_exceptions.ClientResponseError, metadataresolvers.ResolveError) as _e:
        await store_resolve_result(app, 404, str(_e.args), audioname, resolvername, override)
        return web.json_response({
            'error': {'type':_e.__class__.__name__,
                      'args':_e.args},
            'metadata': []
        }, status=404)
    await store_resolve_result(app, 200, 'OK', audioname, resolvername, override)
    return web.json_response({
        'metadata': vars(metadata),
        'error': [],
    })

#'Methods and endpoints to receive an xmeml file and start analyzing it'

class FakeFileUpload:
    filename = 'static/test_all_services.xml'
    def __init__(self):
        self.file = open(self.filename, mode='rb')

@routes.post('/api/analyze')
@swagger_path("handle_analyze_post.yaml")
async def handle_analyze_post(request):
    'POST an xmeml sequence to start the music report analysis. Returns a list of recognised audio tracks and their respective audible duration.'
    # WARNING: don't do that if you plan to receive large files! Stores all in memory
    data = await request.post() # TODO: switch to request.multipart() to handle big uploads!
    app.logger.debug('Got POST args: %r', data)
    #'The Xmeml sequence from Premiere or Final Cut that we want to analyze.',
    try:
        xmeml = data['xmeml']
    except KeyError: # no file uploaded
        if 'usetestfile' in data and data['usetestfile'] == '1':
            # use our own, server side test file instead of a file upload
            xmeml = FakeFileUpload()
        else:
            raise web.HTTPBadRequest(reason='multipart/form-data file named <<xmeml>> is missing') # HTTP 400
    # .filename contains the name of the file in string format.
    if not os.path.splitext(xmeml.filename)[1].lower() == '.xml':
        raise web.HTTPBadRequest(reason='Invalid file extension, expecting .xml') # HTTP 400

    # .file contains the actual file data that needs to be stored somewhere.
    __f = io.BytesIO(xmeml.file.read())
    xmeml = xmemliter.XmemlParser(__f) # XmemlParser expects a file like object
    audioclips, audiofiles = xmeml.audibleranges()
    app.logger.info('Analyzing the audible parts: %r, files: %r', audioclips, audiofiles)

    # keep the file
    with tempfile.NamedTemporaryFile(suffix='.xml', delete=False) as xmemlfile:
        xmemlfile.write(__f.getvalue())
        app.logger.debug('Wrote xmeml data to %r', xmemlfile.name)

    _r = []
    for clipname, ranges in audioclips.items():
        _ac = AudioClip(clipname)
        _ac.set_ranges(ranges)
        _r.append(_ac)
    if not _r:
        raise web.HTTPBadRequest(reason='No audible clips found. Use /report_error to report an error.') # HTTP 400
    return web.json_response(data={
        'audioclips': [
            c.to_dict() for c in _r
        ]
    })

@routes.get('/api/supported_resolvers/')
@swagger_path("handle_supported_resolvers.yaml")
@aiocache.cached(key="handle_supported_resolvers", serializer=JsonSerializer())
async def handle_supported_resolvers(request):
    'GET a request and return a dict of currently suppported resolvers and their file patterns'
    return web.json_response(data={
        'resolvers': getAllResolvers()
    })

@routes.post('/api/feedback/')
async def handle_feedback_post(request):
    'POST form data feedback. No returned content.'
    data = await request.post() 
    app.logger.debug('Got POST args: %r', data)
    async with app.dbpool.acquire() as connection:
        _id = await connection.fetchval("INSERT INTO feedback (sender, message) VALUES ($1, $2) RETURNING public_id", 
                                       data.get('sender'),
                                       data.get('text'))
        
    url = '/feedback/{}'.format(str(_id))
    return web.json_response(data={'error': [], 'url': url})

@routes.post('/api/add_missing/{filename}')
async def handle_add_missing(request):
    'POST json metadata object corresponding to a filename that we should have known about'
    filename = request.match_info.get('filename') # match path string, see the respective route
    data = await request.json() 
    app.logger.debug('add missing filename: %r, with POST args %r', filename, data)
    async with app.dbpool.acquire() as connection:
        await connection.fetchval("INSERT INTO reported_missing (filename, recordnumber, musiclibrary) VALUES ($1, $2, $3)", 
                                  filename,
                                  data.get('recordnumber'),
                                  data.get('musiclibrary'))
    return web.json_response(data={'error': [], })


@routes.get(r'/api/trackinfo/{type:(DMA|spotify)}/{trackinfo}')
@aiocache.cached(key="handle_trackinfo", serializer=JsonSerializer())
async def handle_trackinfo(request):
    'Handle GET trackid from DMA or Spotify and return json formatted TrackMetadata or TrackStub'
    trackinfo = request.match_info.get('trackinfo', None) 
    querytype = request.match_info.get('type')
    if querytype == 'DMA':
        # look up metadata from DMA
        resolver = getResolverByName('DMA')
        resolver.setSession(clientSession) # use the same session object for speedups
        resolver.setConfig(request.app.configuration)
        # run resolver
        app.logger.info("resolve audioname %r with resolver %r", trackinfo, resolver)
        _metadata = await resolver.resolve(trackinfo)
        app.logger.info("resolve audioname %r got metadata %r", trackinfo, vars(_metadata))
        metadata = model.TrackMetadata(**vars(_metadata)) # TODO: verify with marshmallow
    elif querytype == 'spotify':
        spotifyuri = trackinfo
        track = await loop.run_in_executor(executor, app.duediligence.sp.track, spotifyuri)
        #app.logger.info("got spotify track: %r", track)
        trackstub = model.TrackStub()
        try:
            y = int(track['album']['release_date'][:4])
        except TypeError:
            y = -1
        metadata, errors = trackstub.dump({'title':     track['name'],
                                           'uri':       track['uri'],
                                           'artists':   [a['name'] for a in track['artists']], 
                                           'album_uri': track['album']['uri'],
                                           'year':      y
                                           })
    return web.json_response({'error':[],
                              'tracks': [metadata,] },
                              dumps=model.OdometerJSONEncoder().encode)

@routes.post(r'/api/ownership/')
async def handle_post_ownership(request):
    'handle POST music data (TrackMetadata or TrackStub) and try to get copyrights from spotify and discogs'
    metadata = await request.json() # TODO verify with marshmallow 
    logging.debug('Got metadata payload: %r ', metadata)
    #
    # Here's the routine:
    # 1. Get the copyright info from spotify
    #  1a If we already know the album (look at the supplied metadata), get the rights. Or,
    #  1b Get the album first, and then the copyrights.
    # 2. Check our license table to see if this is enough to get an explicit answer. That is,
    #    can we tell by the artist name, track title and album label wether it's OK or NO?
    #    In that case, we have an answer. In the case of "MUST CHECK":
    # 3. Get the top parent label from Discogs, using the label info from Spotify as a starting point.
    # 4. Then, check the license table again. This time, MUST CHECK means the user has to do it herself

    def check_license_result(licenses):
        license_result = "CHECK";
        must_check = seems_ok = is_not_ok = False
        reasons = []
        for l in licenses:
            if l['license_status'] == "NO":
                is_not_ok = True
                reasons = [l['source'], ]
                break
            if l['license_status'] == "CHECK":
                must_check = True
                reasons.append(l['source'])
            elif l['license_status'] == "OK":
                seems_ok = True
                reasons.append(l['source'])
        if is_not_ok:
            license_result = "NO"
        elif seems_ok and not must_check:
            # one or more license rules say yes, and none say we must check 
            license_result = "OK"
        else:
            # undetermined, or specifically must check
            license_result = "CHECK"
        return license_result, reasons


    try:
        # try to see if we have spotify metadata already
        spotifycopyright = await loop.run_in_executor(executor, app.duediligence.spotify_get_album_rights, metadata['spotify']['album_uri'])
    except KeyError:
        # fall back to finding the track on spotyfy using track metadta (title, artists, year )
        spotifymetadata, spotifycopyright = await loop.run_in_executor(executor, app.duediligence.spotify_search_copyrights, metadata['metadata'])
        # store spotify track metadata
        metadata['spotify']['uri'] = spotifymetadata['uri']
        metadata['spotify']['album_uri'] = spotifymetadata['album']['uri']
        try:
            metadata['metadata']['year'] = int(spotifymetadata['album']['release_date'][:4]) # we only need the release year
        except TypeError:
            # fall back to year provided from Trackmetadata object
            metadata['metadata']['year'] = metadata['year']


    # look up licenses from our license table
    lookup = multidict.MultiDict( [ ('artist', v) for v in metadata['metadata'].get('artists', []) ] )
    lookup.add('label', remove_corporate_suffix(spotifycopyright['parsed_label']))
    if 'artist' in metadata['metadata']:
        lookup.add('artist', metadata['metadata']['artist'])

    # CCHEKC if released year is older than 1963, since everything before that date is allowed
    released_year, copyright_expired = release_is_old_and_public_domain(metadata['metadata']['year'], spotifycopyright)
    if copyright_expired:
        app.logger.debug('This release is public domain')
        license_result = 'OK'
        reasons = ['Released {}. Copyright expired'.format(released_year)]
        errors = []
    else:
        licenses, errors = await get_licenses(lookup)
        license_result, reasons = check_license_result(licenses)

    discogs_label_heritage = []
    # only look at discogs if we're unsure
    if license_result == "CHECK":
        # TODO:
        # TODO: add discogs cache, so we can get this async from discogs without hititng rate limits
        # TODO:
        discogs_label_heritage = await loop.run_in_executor(executor, get_discogs_label, spotifycopyright['parsed_label'])
        if discogs_label_heritage is not None:
            lbl = discogs_label_heritage[-1].name # discogs_client.models.Label, topmost parent 
            lookup.add('label', remove_corporate_suffix(lbl))
            licenses, errors = await get_licenses(lookup)
            license_result, reasons = check_license_result(licenses)

    # keep track of how good we are
    await store_copyright_result(app, 
                                 metadata['spotify']['uri'], 
                                 license_result, 
                                 ', '.join(reasons),
                                 spotifycopyright.get('P', None) or spotifycopyright.get('C', None), 
                                 spotifycopyright['parsed_label'])

    jsonencoder = DueDiligenceJSONEncoder().encode
    return web.json_response({'error':[errors],
                              'trackinfo': metadata,
                              'licenses': { 'result': license_result, 'reasons': reasons},
                              'ownership':{'spotify':spotifycopyright,
                                           'timestamp': datetime.datetime.now().isoformat('T'),
                                           'discogs':discogs_label_heritage}
                             }, 
                             dumps=jsonencoder

    )

async def get_licenses(where=None, active=True):
    'Return a json list of all license rules from the DB that match. where is a Multidict'
    schema = model.LicenseRule()

    q = []
    v = []
    i = 1
    for key, value in where.items():
        q.append( " (license_property=${} AND (license_value ILIKE ${} OR alias ILIKE ${})) ".format(i, i+1, i+2) )
        v.append(key)
        v.append(value)
        v.append(value)
        i = i+3

    if where is not None:
        query = " OR ".join(q) + " AND active=${}".format(i)
    else:
        query = "active=$1"
    v.append(active)
    app.logger.debug("running asyncpg query %r with values %r", query, v)
    async with app.dbpool.acquire() as connection:
        records = await connection.fetch("""
        SELECT * FROM license_rule 
        LEFT JOIN license_alias ON 
            license_rule.license_property=license_alias.property AND 
            license_rule.license_value=license_alias.value 
        WHERE {}
        """.format(query), *v)
        app.logger.debug('Got DB ROW: %r', records)
        rules, errors = schema.load([dict(r) for r in records], many=True)
        app.logger.debug('Made schame u %r', rules)

        return rules, errors

@routes.get(r'/api/tracklistinfo/{type:(DMA|spotify)}/{tracklist}')
@aiocache.cached(key="handle_get_tracklist", serializer=JsonSerializer())
async def handle_get_tracklist(request):
    'GET tracklist id and return lists of spoityf ids or DMA ids'
    tracklist_id = request.match_info.get('tracklist', None) 
    querytype = request.match_info.get('type')
    if querytype in ('DMA',):
        # look up metadata from DMA
        resolver = getResolverByName('DMA')
        resolver.setSession(clientSession) # use the same session object for speedups
        resolver.setConfig(request.app.configuration)
        # run resolver
        app.logger.info("get playlist from id %s", tracklist_id)
        metadata = await resolver.getPlaylist(tracklist_id)
        app.logger.info("got plylist %r", metadata)
        tracklist = metadata
    elif querytype == 'spotify':
        try:
            tracklist = list(app.duediligence.spotify_search_playlist(tracklist_id))
        except SpotifyNotFoundError as e:
            tracklist = []
    else:
        raise NotImplementedError

    return web.json_response({'error':[],
                              'tracks': tracklist})

@routes.get(r'/api/labelinfo/{labelquery}')
@aiocache.cached(key="handle_get_label")#, serializer=JsonSerializer())
async def handle_get_label(request):
    'GET a label string and look it up in discogs'
    labelquery = request.match_info.get('labelquery')
    #discogs_labels = get_discogs_label(labelquery)
    discogs_labels = await loop.run_in_executor(executor, get_discogs_label, labelquery)
    jsonencoder = DueDiligenceJSONEncoder().encode
    return web.json_response({'error':[],
                              'labels': discogs_labels},
                             dumps=jsonencoder
    )

@functools.lru_cache(maxsize=128)
def get_discogs_label(labelquery):
    try:
        discogs_label = app.duediligence.discogs_search_label(labelquery)
        discogs_label_heritage = app.duediligence.discogs_label_heritage(discogs_label)
        #TODO gather ifnormaton with an async queue and return EventSource
    except DiscogsNotFoundError as e:
        app.logger.warning('Coul dnot get label from discogs: %s', e)
        discogs_label = discogs_label_heritage = None
    return discogs_label_heritage

@routes.get('/api/license_rules/')
async def handle_get_license_rules(request):
    'Return a json list of all license rules from the DB'
    schema = model.LicenseRule()

    async with app.dbpool.acquire() as connection:
        records = await connection.fetch("""
        SELECT *,
            (select count(*) from license_alias where license_rule.license_value = license_alias.value) AS aliases
        FROM license_rule WHERE active=TRUE""")
        rules, errors = schema.load([dict(r) for r in records], many=True)

    return web.json_response({'error':errors,
                              'rules': rules},
                              dumps=model.OdometerJSONEncoder().encode)

@routes.get('/api/license_alias/') # expecting ?property=<license_property>&value=<license_value>
async def handle_get_license_alias(request):
    'Return a json list of license aliases for the matching license rule from the DB'
    params = request.rel_url.query
    schema_alias = model.LicenseRuleAlias()

    async with app.dbpool.acquire() as connection:
        records_aliases = await connection.fetch("SELECT * FROM license_alias WHERE property=$1 AND value=$2",
            params.get('property'), params.get('value'))
        aliases, errors = schema_alias.load([dict(r) for r in records_aliases], many=True)


    return web.json_response({'error':errors,
                              'aliases': aliases},
                              dumps=model.OdometerJSONEncoder().encode)

@routes.post('/api/license_alias/')
async def handle_post_license_alias(request):
    'Add new license alias, return new alias'

    schema_alias = model.LicenseRuleAlias()
    data = await request.json() 
    #app.logger.debug('Got POST args: %r', data)
    async with app.dbpool.acquire() as connection:
        new = await connection.fetchrow("INSERT INTO license_alias (property, value, alias) VALUES ($1, $2, $3) RETURNING *", 
                                        data.get('property'),
                                        data.get('value'),
                                        data.get('alias').strip())
        #app.logger.debug("INSERTED ROW: %r", dict(new))
        alias, errors = schema_alias.load(dict(new))
    return web.json_response({'error':errors,
                              'alias':alias},
                              dumps=model.OdometerJSONEncoder().encode)
        
@routes.delete('/api/license_alias/{alias_uuid}')
async def handle_delete_license_alias(request):
    'Delete license alias by uuid'

    schema_alias = model.LicenseRuleAlias()
    app.logger.debug('detele license by uuid %r', request.match_info.get('alias_uuid'))
    async with app.dbpool.acquire() as connection:
        status = await connection.execute("DELETE FROM license_alias WHERE public_id=$1",
                                          request.match_info.get('alias_uuid'))
        app.logger.debug("DELETED ROW: %r", status)

    return web.json_response({'error':[],
                              'status':status},
                              dumps=model.OdometerJSONEncoder().encode)

@routes.get('/licenses')
@aiohttp_jinja2.template('licenses.tpl')
async def handle_get_licenses(request):
    'Show all license rules in a view'
    return {}

@routes.get('/api/feedback/')
async def handle_get_feedback_api(request):
    'Return a json list of all license rules from the DB'
    schema = model.Feedback()

    async with app.dbpool.acquire() as connection:
        records = await connection.fetch("SELECT * FROM feedback ORDER BY done DESC")
        feedbacks, errors = schema.load([dict(r) for r in records], many=True)

    return web.json_response({'error':errors,
                              'feedback': feedbacks},
                              dumps=model.OdometerJSONEncoder().encode)

@routes.get('/feedback')
@aiohttp_jinja2.template('feedback.tpl')
async def handle_get_feedback(request):
    'Show all feedback in a view'
    return {}

@routes.get('/')
@aiohttp_jinja2.template('index.tpl')
def index(request):
    app.active_page = "analysis"
    return {}


@routes.get('/copyright_owner')
@aiohttp_jinja2.template('copyright_owner.tpl')
def copyright_owner(request):
    app.active_page = "ownership"
    return {}


@routes.get('/api/missing_filenames/')
async def handle_get_missing_filenames_api(request):
    'Return a json list of all reported missing filenames from the DB'
    schema = model.ReportedMissing()

    async with app.dbpool.acquire() as connection:
        records = await connection.fetch("SELECT * FROM reported_missing")
        missing, errors = schema.load([dict(r) for r in records], many=True)

    return web.json_response({'error':errors,
                              'missing': missing},
                              dumps=model.OdometerJSONEncoder().encode)


@routes.get('/missing_filenames')
@aiohttp_jinja2.template('missing_filenames.tpl')
def missing_filenames(request):
    return {}

@routes.get('/api/tests/')
async def handle_get_tests_api(request):
    'Return a json list of all tests from the DB'
    schema = model.Tests()

    async with app.dbpool.acquire() as connection:
        records = await connection.fetch("SELECT * FROM tests WHERE active=1")
        tests, errors = schema.load([dict(r) for r in records], many=True)

    return web.json_response({'error':errors,
                              'tests': tests},
                              dumps=model.OdometerJSONEncoder().encode)



@routes.get('/tests')
@aiohttp_jinja2.template('admin_tests.tpl')
def tests(request):
    return {}

@routes.get('/dashboard')
@aiohttp_jinja2.template('admin_dashboard.tpl')
def dashboard(request):
    return {}

@routes.get('/favicon.ico')
def favicon(request):
    return web.FileResponse('./static/favicon.ico')

app.router.add_routes(routes) # find all @routes.* decorators

app.router.add_static('/media', 'static/media')

# TODO app.router.add_get('/submit_runsheet', handle_submit_runsheet) # submit a runsheet to applicable services
# TODO app.router.add_get('/get_track', get_track) # get track from unique id



async def init(debugmode=False):
    'init everything, but dont start it up. '
    # setup application
    # add routes
    # add startup and shutdown routines
    # set up swagger
    global app
    app.debugmode = debugmode
    setup_swagger(app,
                    swagger_url="/api/doc",
                    description='API to parse and resolve audio metadata from XMEML files, i.e. Adobe Premiere projects',
                    title='Pling Plong Odometer Online',
                    api_version=APIVERSION,
                    contact="havard.gulldahl@nrk.no"
                    )

if __name__ == '__main__':
    DBG = os.path.exists('_DEVELOPMENT') # look for this file in the current directory
    import logging
    if DBG:
        logging.basicConfig(level=logging.DEBUG)
        logging.debug("_DEVELOPMENT flag detected, debug mode activated")
        loop.set_debug(True)

    import argparse

    parser = argparse.ArgumentParser(description="Odometer server")
    parser.add_argument('--path')
    parser.add_argument('--port', type=int)

    args = parser.parse_args()

    loop.run_until_complete(init(debugmode=DBG))

    try:
        web.run_app(
            app,
            path=args.path,
            port=args.port)
    except ConnectionRefusedError:
        print("Could not connect to Postgres SQL server. This is fatal.")
        loop.close()
        sys.exit(1)

""" # TODO: enable AppRunner startup when we can run on py3.6 / aiohttp > v3
    # main program loop
    try:
        loop.run_forever()
    except KeyboardInterrupt:
        pass
    finally:
        loop.run_until_complete()
    #stop the loop
    loop.close()
"""
