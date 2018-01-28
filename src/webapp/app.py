import os.path
import tempfile
import pathlib
from urllib.parse import quote
import configparser
import io

import asyncio

from aiohttp import web
import aiohttp

from aiohttp_swagger import swagger_path, setup_swagger

from metadataresolvers import findResolvers, getAllResolvers, getResolverByName
#from model import TrackMetadata
from xmeml import iter as xmemliter

loop = asyncio.get_event_loop()
app = web.Application(loop=loop,
                      client_max_size=20*(1024**2)) # upload size max 20 megs
headers = { 'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_13_2) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/62.0.3202.94 Safari/537.36',
}
clientSession = aiohttp.ClientSession(loop=loop, headers=headers)

async def on_shutdown(_app):
    'Cleaning up right before shutdown'
    await clientSession.close()

async def on_startup(_app):
    'Things to do on startup'
    _app.configuration = configparser.ConfigParser()
    _app.configuration.read('config.ini')

app.on_startup.append(on_startup)
app.on_shutdown.append(on_shutdown)

APIVERSION = '0.1'

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
                'resolve': {s:'/resolve/{}/{}'.format(quote(s), quote(self.filename)) for s in self.services},
                'resolve_other': '/resolve/{{music_service}}/{}'.format(quote(self.filename)),
                'add_missing':'/add_missing/{}'.format(quote(self.filename)),
               }

@swagger_path("handle_resolve.yaml")
async def handle_resolve(request):
    'Get an audioname from the request and resolve it from its respective service resolver'
    audioname = request.match_info.get('audioname', None) # match path string, see the respective route
    resolvername = request.match_info.get('resolver', None) # match path string, see the respective route
    logging.warning('Parsed path and got audioname: %r, resolvername%r', audioname, resolvername)
    # find resolver if it is not provided to us on the path string
    if resolvername:
        resolver = getResolverByName(resolvername)
    else:
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
        metadata = await resolver.resolve(audioname)
    except aiohttp.ClientConnectorError as _e:
        return web.json_response({
            'error': {'type':_e.__class__.__name__,
                      'args':_e.args},
            'metadata': []
        }, status=400)
    return web.json_response({
        'metadata': vars(metadata),
        'error': [],
    })

app.router.add_get('/resolve/{resolver}/{audioname}', handle_resolve, name='resolve')
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

app.router.add_post('/analyze', handle_analyze_post)

@swagger_path("handle_supported_resolvers.yaml")
async def handle_supported_resolvers(request):
    'GET a request and return a dict of currently suppported resolvers and their file patterns'
    return web.json_response(data={
        'resolvers': getAllResolvers()
    })

app.router.add_get('/supported_resolvers', handle_supported_resolvers) # show currently supported resolvers and their patterns

def index(request):
    with open('static/index.html', encoding='utf-8') as _f:
        return web.Response(text=_f.read(), content_type='text/html')

app.router.add_get('/', index)
app.router.add_static('/media', 'static/media')

# TODO app.router.add_get('/submit_runsheet', handle_submit_runsheet) # submit a runsheet to applicable services
# TODO app.router.add_get('/report_error', handle_report_error) # report an error
# TODO app.router.add_get('/report_missing', handle_report_missing) # report a missing audio pattern
# TODO app.router.add_get('/stats', handle_stats) # show usage stats and patterns

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

    # start server
    web.run_app(
        app,
        path=args.path,
        port=args.port
    )
    try:
        loop.run_forever()
    finally:
        loop.run_until_complete(loop.shutdown_asyncgens())
        loop.close()
