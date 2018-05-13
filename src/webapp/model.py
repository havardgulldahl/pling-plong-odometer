#-*- encoding: utf8 -*-
# This file is part of odometer by Håvard Gulldahl <havard.gulldahl@nrk.no>
# (C) 2016

import time
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

class ReportedMissing:
    id = fields.Int(required=True)
    filename = fields.Str(required=True)
    resolver = fields.Str(required=True)
    reporter = fields.Str(allow_none=True)
    timestamp = fields.DateTime(required=True)

class Feedback:
    id = fields.Int(required=True)
    timestamp = fields.DateTime(required=True)
    public_id = fields.UUID(required=True)
    done = fields.Boolean(default=False, required=True)
    sender = fields.Str(required=True)
    message = fields.Str(required=True)

class ResolveResult:
    id = fields.Int(required=True)
    result_code = fields.Int(required=True)
    result_text = fields.Str(required=True)
    filename = fields.Str(required=True)
    resolver = fields.Str(required=True)
    overridden = fields.Boolean(default=False)
    timestamp = fields.DateTime(required=True)

