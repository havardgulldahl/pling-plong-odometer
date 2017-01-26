#!/usr/bin/env python

import os.path
import tempfile
import time
import pathlib
from urllib.parse import quote

from aiohttp_swagger import *

from metadataresolvers import findResolver
from model import TrackMetadata
from xmeml import iter as xmemliter

import asyncio
import uuid

from asyncio import coroutine

from aiohttp import web

from webargs.aiohttpparser import parser as webargsparser
from webargs import fields as webfields

loop = asyncio.get_event_loop()
app = web.Application(loop=loop)

APIVERSION = '0.1'

class resolvableClip:
    def __init__(self, filename, audible_length, service):
        self.filename = filename
        self.audible_length = audible_length
        self.service = service
    def to_dict(self):
        return {'clipname': self.filename, 
                 'total_length': self.audible_length, 
                 'resolve':'/resolve/{}'.format(quote(self.filename))
                 }

class InvalidXmeml(Exception):
    pass

async def parse_xmeml(xmemlfile):
    """Background task to parse Xmeml with python-xmeml"""
    app.logger.info('Parsing the xmemlf ile with xmemliter: %r', xmemlfile)
    app.logger.info('exists? %s', os.path.exists(xmemlfile))
    xmeml = xmemliter.XmemlParser(xmemlfile)
    audioclips, audiofiles = xmeml.audibleranges()
    app.logger.info('Analyzing the audible parts: %r, files: %r', audioclips, audiofiles)
    return (audioclips, audiofiles) 

def is_resolvable(audioname):
    'Look at the filename and say if it is resolvable from one or the other service. Returns bool'
    return findResolver(audioname) != False

async def resolve_metadata(audioname):
    'Resolve metadata for some audioname (filename). Returns Trackmetadata object or None'
    # find resolver
    resolver = findResolver(audioname)
    # run resolver
    app.logger.info("resolve audioname {!r} with resolver {!r}".format(audioname, resolver))
    metadata = await resolver.resolve(audioname)
    # return metadata
    return metadata

@swagger_path("handle_resolve.yaml")
async def handle_resolve(request):
    'Get an audioname from the request and resolve it from its respective service resolver'
    audioname = request.match_info.get('audioname', None)

    metadata = await resolve_metadata(audioname)
    return web.json_response({
        'metadata': vars(metadata)
    })

app.router.add_get('/resolve/{audioname}', handle_resolve, name='resolve')

#'Methods and endpoints to receive an xmeml file and start analyzing it'
async def handle_analyze_get(request):
    return web.Response(body="""
    <html><head><title>Submit xmeml</title></head>
    <body>
    <form action="/analyze" method="post" accept-charset="utf-8"
      enctype="multipart/form-data">

    <label for="xmeml">Xmeml file:</label>
    <input id="xmeml" name="xmeml" type="file" value=""/>

    <input type="submit" value="submit"/>
</form></body></html>""".encode())

app.router.add_get('/analyze', handle_analyze_get)

@swagger_path("handle_analyze_post.yaml")
async def handle_analyze_post(request):
    'POST an xmeml sequence to start the music report analysis. Returns a list of recognised audio tracks and their respective audible duration.'
    app.logger.debug('About to parse POST args')
    # WARNING: don't do that if you plan to receive large files! Stores all in memory
    data = await request.post() # TODO: switch to request.multipart() to handle big uploads!
    app.logger.debug('Got POST args: {!r}'.format(data))
    #'The Xmeml sequence from Premiere or Final Cut that we want to analyze.',
    try:
        xmeml = data['xmeml']
    except KeyError: # no file uploaded
        raise web.HTTPBadRequest(reason='multipart/form-data file named <<xmeml>> is missing') # HTTP 400
    # .filename contains the name of the file in string format.
    if not os.path.splitext(xmeml.filename)[1].lower() == '.xml':
        raise web.HTTPBadRequest(reason='Invalid file extension, expecting .xml') # HTTP 400

    # .file contains the actual file data that needs to be stored somewhere.
    with tempfile.NamedTemporaryFile(suffix='.xml', delete=False) as xmemlfile:
        xmemlfile.write(xmeml.file.read())
        f = pathlib.Path(xmemlfile.name)
        app.logger.info('uploaded file: {!r}'.format(f))
        audioclips, audiofiles = await parse_xmeml(xmemlfile.name)
        _r = []
        for clipname, ranges in audioclips.items():
            if not is_resolvable(clipname):
                continue
            _r.append(resolvableClip(clipname, len(ranges), None))
        if len(_r) == 0:
            raise web.HTTPBadRequest(reason='No audible clips found. Use /report_error to report an error.') # HTTP 400
        return web.json_response(data={
            'audible': [
                c.to_dict() for c in _r
            ]
        })

app.router.add_post('/analyze', handle_analyze_post)

@coroutine
def index(request):
    return web.HTTPFound('/doc') # forward to docs

app.router.add_get('/', index)

# TODO app.router.add_get('/report_error', handle_report_error) # report an error
# TODO app.router.add_get('/report_missing', handle_report_missing) # report a missing audio pattern
# TODO app.router.add_get('/supported_resolvers', handle_supported_resolvers) # show currently supported resolvers and their patterns

setup_swagger(app,
              swagger_url="/doc",
              description='API to parse and resolve audio metadata from XMEML files, i.e. Adobe Premiere projects',
              title='Pling Plong Odometer Online',
              api_version=APIVERSION,
              contact="havard.gulldahl@nrk.no"
)

if __name__ == '__main__':
    import logging
    logging.basicConfig(level=logging.DEBUG)
    # Development server
    web.run_app(
        app,
        #reload=True,
        port=8000
    )
