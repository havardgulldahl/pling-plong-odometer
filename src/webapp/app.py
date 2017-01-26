#!/usr/bin/env python

import os.path
import tempfile
import time
import pathlib
from urllib.parse import quote


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
    # return metadata
    app.logger.info("pretending to resove audio {!r} with resolver {!r}".format(audioname, resolver))
    import random
    await asyncio.sleep(random.randint(0, 20)*0.1)
    return TrackMetadata(filename=audioname)

async def handle_resolve(request):
    'Get an audioname from the request and resolve it from its respective service resolver'
    _uuid = request.GET.get('uuid', 'World')
    audioname = request.match_info.get('audioname', None)

    metadata = await resolve_metadata(audioname)
    return web.json_response({
        'metadata': vars(metadata)
    })

app.router.add_get('/resolve/{audioname}', handle_resolve, name='resolve')

analyze_args = {
    #'The Xmeml sequence from Premiere or Final Cut that we want to analyze.',
    'xmeml': webfields.Str(location='files', missing='crikey')
}

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

async def handle_analyze_post(request):
    'POST an xmeml sequence to start the music report analysis. Returns a unique identifier'
    app.logger.debug('About to parse POST args')
    # WARNING: don't do that if you plan to receive large files! Stores all in memory
    data = await request.post()
    app.logger.debug('Got POST args: {!r}'.format(data))
    xmeml = data['xmeml']
    # .filename contains the name of the file in string format.
    if not os.path.splitext(xmeml.filename)[1].lower() == '.xml':
        raise InvalidXmeml('Invalid file extension, expexting .xml')

    # .file contains the actual file data that needs to be stored somewhere.
    with tempfile.NamedTemporaryFile(suffix='.xml', delete=False) as xmemlfile:
        xmemlfile.write(xmeml.file.read())
        f = pathlib.Path(xmemlfile.name)
        app.logger.info('uploaded file: {!r}'.format(f))
        audioclips, audiofiles = await parse_xmeml(xmemlfile.name)
        #return web.Response(status=200, text='created task: {!r}'.format(task))
        _r = []
        for clipname, ranges in audioclips.items():
            if not is_resolvable(clipname):
                continue
            _r.append(resolvableClip(clipname, len(ranges), None))
        return web.json_response(data={
            'audible': [
                c.to_dict() for c in _r
            ]
        })


app.router.add_post('/analyze', handle_analyze_post)

@coroutine
def index(request):
    return web.Response(text='Welcome!')
app.router.add_get('/', index)

#Contentnegotiation
#negotiation.setup(
    #app, renderers={
        #'application/json': negotiation.render_json
    #}
#)


if __name__ == '__main__':
    import logging
    logging.basicConfig(level=logging.DEBUG)
    # Development server
    web.run_app(
        app,
        #reload=True,
        port=8000
    )
