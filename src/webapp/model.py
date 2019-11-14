#-*- encoding: utf8 -*-
# This file is part of odometer by Håvard Gulldahl <havard.gulldahl@nrk.no>
# (C) 2012-2018

import json
import uuid
import time
import datetime
from marshmallow import Schema, fields, pre_load # pip install marshmallow

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
    def _deserialize(self, value, attr, data, **kwargs):
        if isinstance(value, datetime.datetime):
            return value.isoformat()
        return super()._deserialize(value, attr, data, **kwargs)

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
    odometer_version = fields.Str(required=True)

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
    license_status = fields.Str(required=True)   # oneOf NO, OK, CHECK
    comment = fields.Str(allow_none=True)        # free type string - editor comment
    aliases = fields.Int()                       # number of aliases defined - look at LicenseRuleAlias

class LicenseRuleAlias(Schema):
    'Alias for licensing rules'
    id = fields.Int(required=True)               # internal id
    public_id = fields.UUID(required=True)       # public uuid
    timestamp = RichDateTimeField(required=True) # last changed timestamp
    property = fields.Str(required=True)         # must match LicenseRule
    value = fields.Str(required=True)            # must match LicenseRule
    alias = fields.Str(required=True)            # case insensitive search - if it matches, the rule is applied

class Test(Schema):
    'Urls for high level test for functionality'
    id = fields.Int(required=True)               # internal id
    timestamp = RichDateTimeField(required=True) # last changed timestamp
    active = fields.Boolean(default=True)        # boolean -  active or not
    name = fields.Str(required=True)             # 
    url = fields.Str(required=True)              # 

class TrackStub(Schema):
    'A short/small object to pass around while we are waiting for the rich metadata'
    title = fields.Str(required=True)
    artists = fields.List(fields.Str(), required=True)
    uri = fields.Str()
    album_uri = fields.Str()
    year = fields.Int()

class ISRCDataHealth(Schema):
    'Model for the dma_data_health table'
    '''
    CREATE TABLE dma_data_health (
    id SERIAL PRIMARY KEY,
    dma_id character varying(255) NOT NULL UNIQUE,
    timestamp timestamp with time zone NOT NULL DEFAULT now(),
    isrc character varying(255),
    isrc_ok boolean DEFAULT false,
    ean character varying(255),
    ean_ok boolean DEFAULT false,
    checked timestamp with time zone
    );
    '''

    id = fields.Int(required=True)               # internal id
    dma_id = fields.Str(required=True)           # DMA_id
    timestamp = RichDateTimeField(required=True) # last changed timestamp
    isrc = fields.Str(required=False, allow_none=True) # ISRC code, might be missing
    isrc_ok = fields.Boolean(allow_none=True)    # boolean - is the ISRC code correct? NULL means not verified
    ean = fields.Str(required=False, allow_none=True) # EAN code, might be missing
    ean_ok = fields.Boolean(allow_none=True )    # boolean - is the EAN code correct? NULL means not verified
    checked = RichDateTimeField(allow_none=True) # timestamp of last check. NULL means not checked

class IFPIsearchTrack(Schema):
    'Model for replies from IFPIsearch.org when you search for tracks'
    '''{'duration': '3:25', 'recordingVersion': '', 'recordingYear': '2019', 'artistName': 'Drake ♦ Rick Ross', 'isrcCode': 'USCM51900314', 'documentType': 'recording', 'showReleases': 0, 'trackTitle': 'Money In The Grave', 'id': 'USCM51900314'}'''
    id = fields.Str(required=True)                                  # id. same as ISRC?
    isrc = fields.Str(required=True, data_key='isrcCode')           # ISRC
    title = fields.Str(required=True, data_key='trackTitle')        # track title
    year = fields.Str(allow_none=True, data_key='recordingYear')    # recorded year
    duration = fields.Str(allow_none=True)                          # track duration in MM:SS, may be missing
    artistName = fields.List(fields.Str())

    @pre_load
    def split_artists(self, in_data, **kwargs):
        in_data['artistName'] = [f.strip() for f in in_data['artistName'].split('♦')]
        return in_data


    class Meta:
        additional = ('duration', 'recordingVersion', 'documentType', 'showReleases')
    

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

