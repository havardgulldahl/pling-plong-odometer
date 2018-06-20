#-*- encoding: utf8 -*-
# This file is part of odometer by Håvard Gulldahl <havard.gulldahl@nrk.no>
# (C) 2012-2018

import json
import uuid
import time
import datetime
from marshmallow import Schema, fields # pip install marshmallow

class TrackMetadata(object): # TODO: marshmallow this
    'All important metadata properties of a track that we need for a sane report'
    # pylint: disable=too-many-instance-attributes
    # pylint: disable=too-many-arguments
    # pylint: disable=too-many-locals
    # We need all 19
    def __init__(self,
                 filename=None,
                 musiclibrary=None,
                 title=None,
                 length=-1,
                 composer=None,
                 artist=None,
                 year=-1,
                 recordnumber=None,
                 albumname=None,
                 copyright=None,
                 lcnumber=None,
                 isrc=None,
                 ean=None,
                 catalogue=None,
                 label=None,
                 lyricist=None,
                 identifier=None,
                 productionmusic=False,
                 **kwargs
                ):

        def tit(val):
            'Return title case strings or None if val is None'
            return val.title() if isinstance(val, str) else val

        self.filename = filename
        self.musiclibrary = musiclibrary
        self.title = tit(title)
        self.length = length # in seconds
        self.composer = tit(composer)
        self.artist = tit(artist)
        self.year = year
        self.recordnumber = recordnumber
        self.albumname = tit(albumname)
        self.copyright = copyright
        self.lcnumber = lcnumber # library of congress id
        self.isrc = isrc # International Standard Recording Code
        self.ean = ean # ean-13 (barcode)
        self.catalogue = tit(catalogue)
        self.label = label
        self.lyricist = tit(lyricist)
        self.identifier = identifier # system-specific identifier
        self.productionmusic = productionmusic
        self._retrieved = time.mktime(time.localtime())

class RichDateTimeField(fields.DateTime):
    'Extend fields.DateTime to also accept datetime instance upon load()ing '
    def _deserialize(self, value, attr, data):
        if isinstance(value, datetime.datetime):
            return value.isoformat()
        return super()._deserialize(value, attr, data)

class ReportedMissing(Schema):
    id = fields.Int(required=True)
    filename = fields.Str(required=True)
    recordnumber = fields.Str(required=True)
    musiclibrary = fields.Str(required=True)
    timestamp = RichDateTimeField(required=True)
    resolved = fields.Boolean(default=False, required=True)

class Feedback(Schema):
    id = fields.Int(required=True)
    timestamp = RichDateTimeField(required=True)
    public_id = fields.UUID(required=True)
    done = fields.Boolean(default=False, required=True)
    sender = fields.Str(required=True)
    message = fields.Str(required=True)

class ResolveResult(Schema):
    id = fields.Int(required=True)
    result_code = fields.Int(required=True)
    result_text = fields.Str(required=True)
    filename = fields.Str(required=True)
    resolver = fields.Str(required=True)
    overridden = fields.Boolean(default=False)
    timestamp = RichDateTimeField(required=True)

class LicenseRule(Schema):
    'Rules for licensing '
    id = fields.Int(required=True)               # internal id
    active = fields.Boolean(default=True)        # boolean -  active or not
    public_id = fields.UUID(required=True)       # public uuid
    timestamp = RichDateTimeField(required=True) # last changed timestamp
    source = fields.Str(required=True)           # free type string - the source of the rule
    license_property = fields.Str(required=True) # oneOf album, artist, label
    license_value = fields.Str(required=True)    # case insensitive search - if it matches, the rule is applied
    license_status = fields.Str(required=True)   # oneOf green, yellow, red - allowed, check or prohibited
    comment = fields.Str(allow_none=True)        # free type string - editor comment

class TrackStub(Schema):
    'A short/small object to pass around while we are waiting for the rich metadata'
    title = fields.Str(required=True)
    artists = fields.List(fields.Str(), required=True)
    uri = fields.Str()
    album_uri = fields.Str()

class OdometerJSONEncoder(json.JSONEncoder):
    'turning external models and complex objects into neat json'
    def default(self, obj):
        if isinstance(obj, TrackMetadata):
            return vars(obj)
        elif isinstance(obj, uuid.UUID):
            # https://docs.python.org/3/library/uuid.html
            return str(obj)
        # Let the base class default method raise the TypeError
        return json.JSONEncoder.default(self, obj)

