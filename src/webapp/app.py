import os.path
import tempfile
import pathlib
from urllib.parse import quote
import configparser
import io
import datetime
import json

import asyncio

from aiohttp import web
import aiohttp

from aiohttp_swagger import swagger_path, setup_swagger

import aiohttp_jinja2 # pip install aiohttp-jinja2
import jinja2

import aioslacker # pip install aioslacker
import asyncpg # pip install asyncpg

from aiohttp_apispec import docs, use_kwargs, marshal_with, AiohttpApiSpec

from xmeml import iter as xmemliter

from metadataresolvers import findResolvers, getAllResolvers, getResolverByName
import metadataresolvers

from rights import DueDiligence, DueDiligenceJSONEncoder, DiscogsNotFoundError, SpotifyNotFoundError

import model

loop = asyncio.get_event_loop()
app = web.Application(loop=loop,
                      client_max_size=20*(1024**2)) # upload size max 20 megs
headers = { 'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_13_2) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/62.0.3202.94 Safari/537.36',
}
clientSession = aiohttp.ClientSession(loop=loop, headers=headers)
aiohttp_jinja2.setup(app,
    loader=jinja2.FileSystemLoader('./templates'))

async def on_shutdown(_app):
    'Cleaning up right before shutdown'
    await clientSession.close()
    await _app.slack.close()
    await _app.dbpool.close()

async def on_startup(_app):
    'Things to do on startup'
    _app.configuration = configparser.ConfigParser()
    _app.configuration.read('config.ini')
    _app.slack = aioslacker.Slacker(_app.configuration.get('slack', 'token'))
    _app.dbpool = await asyncpg.create_pool(dsn=_app.configuration.get('db', 'dsn'))
    _app.duediligence = DueDiligence(config=_app.configuration)

app.on_startup.append(on_startup)
app.on_shutdown.append(on_shutdown)

APIVERSION = '0.1'

async def store_resolve_result(_app, result_code:int, result_text:str, filename:str, resolver:str, overridden:bool):
    'Helper to add result of a resolve attempt to DB'

    sql = '''INSERT INTO resolve_result (result_code, result_text, filename, resolver, overridden)
             VALUES ($1, $2, $3, $4, $5);'''
    async with _app.dbpool.acquire() as connection:
        await connection.execute(sql, result_code, result_text, filename, resolver, overridden)
        
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

@swagger_path("handle_resolve.yaml")
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

app.router.add_get('/api/resolve/{resolver}/{audioname}', handle_resolve, name='resolve')
#app.router.add_get('/resolve/{audioname}', handle_resolve, name='resolve')

#'Methods and endpoints to receive an xmeml file and start analyzing it'

class FakeFileUpload:
    filename = 'static/test_all_services.xml'
    def __init__(self):
        self.file = open(self.filename, mode='rb')

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

app.router.add_post('/api/analyze', handle_analyze_post)

@swagger_path("handle_supported_resolvers.yaml")
async def handle_supported_resolvers(request):
    'GET a request and return a dict of currently suppported resolvers and their file patterns'
    return web.json_response(data={
        'resolvers': getAllResolvers()
    })

app.router.add_get('/api/supported_resolvers', handle_supported_resolvers) # show currently supported resolvers and their patterns

async def handle_feedback_post(request):
    'POST form data feedback. No returned content.'
    data = await request.post() 
    app.logger.debug('Got POST args: %r', data)
    async with app.dbpool.acquire() as connection:
        _id = await connection.fetchval("INSERT INTO feedback (sender, message) VALUES ($1, $2) RETURNING public_id", 
                                       data.get('sender'),
                                       data.get('text'))
        
    url = '/feedback/{}'.format(str(_id))
    try:
        app.slack.chat.post_message(app.configuration.get('slack', 'channel'),
                                    'New feedback from {}: {}'.format(data.get('sender'), url))
    except:
        pass
    return web.json_response(data={'error': [], 'url': url})

app.router.add_post('/api/feedback', handle_feedback_post)

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
    try:
        app.slack.chat.post_message(app.configuration.get('slack', 'channel'),
                                'Missing audio reported:\n`{}` -> *{}* ({})'.format(filename, 
                                                                                    data.get('recordnumber'),
                                                                                    data.get('musiclibrary')))
    except:
        pass # slack is not that important
    return web.json_response(data={'error': [], })

app.router.add_post('/api/add_missing/{filename}', handle_add_missing) # report an audio file that is missing from odometer patterns

async def handle_getpost_ownership(request):
    'GET / POST music data and try to get copyrights from spotify and discogs'
    #TODO gather ifnormaton with an async queue and return EventSource
    trackinfo = request.match_info.get('trackinfo', None) 
    querytype = request.match_info.get('type')
    try:
        # get album copyright from spoitfy
        if querytype in ('DMA', 'metadata'):
            if querytype == 'DMA':
                # look up metadata from DMA
                resolver = getResolverByName('DMA')
                resolver.setSession(clientSession) # use the same session object for speedups
                resolver.setConfig(request.app.configuration)
                # run resolver
                app.logger.info("resolve audioname %r with resolver %r", trackinfo, resolver)
                _metadata = await resolver.resolve(trackinfo)
                metadata = vars(_metadata) # TODO: verify with marshmallow
            elif querytype == 'metadata':
                metadata = await request.json()
            logging.debug('Got metadata payload: %r ', metadata)
            info = {'title': metadata['title'], 'artist': metadata['artist']}
            spotifycopyright = app.duediligence.spotify_search_copyrights(metadata)
        elif querytype == 'spotify':
            metadata = None
            spotifyuri = trackinfo
            track = app.duediligence.sp.track(spotifyuri)
            spotifycopyright = app.duediligence.spotify_get_album_rights(track['album']['uri'])
            info = {'title': track['name'], 'artist': ', '.join([a['name'] for a in track['artists']])}
        else:
            raise NotImplementedError
    except SpotifyNotFoundError as e:
        spotifycopyright = None
        #return web.json_response(status=404,
                                 #data={'error': ['Could not find track in the spotify database, please do it manually.']}
                                #)

    discogs_label = None
    discogs_label_heritage = []
    if spotifycopyright is not None:
        try:
            discogs_label = app.duediligence.discogs_search_label(spotifycopyright["parsed_label"])
            discogs_label_heritage = app.duediligence.discogs_label_heritage(discogs_label)
        except DiscogsNotFoundError as e:
            app.logger.warning('Coul dnot get label from discogs: %s', e)
    jsonencoder = DueDiligenceJSONEncoder().encode
    return web.json_response({'error':[],
                              'trackinfo': info,
                              'ownership':{'spotify':spotifycopyright,
                                           'timestamp': datetime.datetime.now().isoformat('T'),
                                           'original_query':trackinfo,
                                           'discogs':discogs_label_heritage}
                             }, 
                             dumps=jsonencoder

    )

app.router.add_get(r'/api/ownership/{type:(DMA|spotify)}/{trackinfo}', handle_getpost_ownership)
app.router.add_post(r'/api/ownership/{type:metadata}', handle_getpost_ownership)

async def handle_get_tracklist(request):
    'GET tracklist id and return lists of spoityf ids or DMA ids'
    tracklist_id = request.match_info.get('tracklist', None) 
    querytype = request.match_info.get('type')
    if querytype in ('DMA',):
        # look up metadata from DMA
        raise NotImplementedError
        resolver = getResolverByName('DMA')
        resolver.setSession(clientSession) # use the same session object for speedups
        resolver.setConfig(request.app.configuration)
        # run resolver
        app.logger.info("resolve audioname %r with resolver %r", trackinfo, resolver)
        _metadata = await resolver.resolve(trackinfo)
        metadata = vars(_metadata)
    elif querytype == 'spotify':
        try:
            tracklist = list(app.duediligence.spotify_search_playlist(tracklist_id))
        except SpotifyNotFoundError as e:
            tracklist = []
    else:
        raise NotImplementedError

    return web.json_response({'error':[],
                              'tracks': tracklist})

app.router.add_get(r'/api/tracklist/{type:(DMA|spotify)}/{tracklist}', handle_get_tracklist)

async def handle_get_license_rules(request):
    'Return a json list of all license rules from the DB'
    schema = model.LicenseRule()

    async with app.dbpool.acquire() as connection:
        records = await connection.fetch("SELECT * FROM license_rule WHERE active=TRUE")
        #app.logger.debug('Got DB ROW: %r', records)
        rules, errors = schema.load([dict(r) for r in records], many=True)
        #app.logger.debug('Made schame u %r', rules)

    return web.json_response({'error':errors,
                              'rules': rules},
                              dumps=model.OdometerJSONEncoder().encode)

app.router.add_get(r'/api/license_rules/', handle_get_license_rules)

@use_kwargs(model.LicenseRule(strict=True))
async def handle_post_license_rule(request):
    'Add new license rule, return id'
    raise NotImplementedError

    data = await request.post() 
    app.logger.debug('Got POST args: %r', data)
    async with app.dbpool.acquire() as connection:
        _id = await connection.fetchval("INSERT INTO feedback (sender, message) VALUES ($1, $2) RETURNING public_id", 
                                       data.get('sender'),
                                       data.get('text'))
        

@aiohttp_jinja2.template('licenses.tpl')
async def handle_get_licenses(request):
    'Show all license rules in a view'
    return {}
app.router.add_get('/licenses', handle_get_licenses)

async def handle_get_feedback_api(request):
    'Return a json list of all license rules from the DB'
    schema = model.Feedback()

    async with app.dbpool.acquire() as connection:
        records = await connection.fetch("SELECT * FROM feedback")
        feedbacks, errors = schema.load([dict(r) for r in records], many=True)

    return web.json_response({'error':errors,
                              'feedback': feedbacks},
                              dumps=model.OdometerJSONEncoder().encode)

app.router.add_get(r'/api/feedback/', handle_get_feedback_api)

@aiohttp_jinja2.template('feedback.tpl')
async def handle_get_feedback(request):
    'Show all feedback in a view'
    return {}
app.router.add_get('/feedback', handle_get_feedback)

@aiohttp_jinja2.template('index.tpl')
def index(request):
    return {}

app.router.add_get('/', index)

@aiohttp_jinja2.template('copyright_owner.tpl')
def copyright_owner(request):
    return {}

app.router.add_get('/copyright_owner', copyright_owner)

async def handle_get_missing_filenames_api(request):
    'Return a json list of all reported missing filenames from the DB'
    schema = model.ReportedMissing()

    async with app.dbpool.acquire() as connection:
        records = await connection.fetch("SELECT * FROM reported_missing")
        missing, errors = schema.load([dict(r) for r in records], many=True)

    return web.json_response({'error':errors,
                              'missing': missing},
                              dumps=model.OdometerJSONEncoder().encode)

app.router.add_get(r'/api/missing_filenames/', handle_get_missing_filenames_api)

@aiohttp_jinja2.template('missing_filenames.tpl')
def missing_filenames(request):
    return {}

app.router.add_get('/missing_filenames', missing_filenames)


app.router.add_static('/media', 'static/media')

# TODO app.router.add_get('/submit_runsheet', handle_submit_runsheet) # submit a runsheet to applicable services
# TODO app.router.add_get('/stats', handle_stats) # show usage stats and patterns
# TODO app.router.add_get('/get_track', get_track) # get track from unique id

setup_swagger(app,
              swagger_url="/doc",
              description='API to parse and resolve audio metadata from XMEML files, i.e. Adobe Premiere projects',
              title='Pling Plong Odometer Online',
              api_version=APIVERSION,
              contact="havard.gulldahl@nrk.no"
             )

async def init(loop):
    'init everything, but dont start it up. returns Application'
    # setup application
    # add routes
    # add startup and shutdown routines
    # set up swagger



if __name__ == '__main__':
    import logging
    logging.basicConfig(level=logging.DEBUG)
    import argparse

    parser = argparse.ArgumentParser(description="Odometer server")
    parser.add_argument('--path')
    parser.add_argument('--port', type=int)

    args = parser.parse_args()

    web.run_app(
        app,
        path=args.path,
        port=args.port)
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