#-*- encoding: utf8 -*-
# This file is part of odometer by Håvard Gulldahl <havard.gulldahl@nrk.no>
# (C) 2016

import time

class TrackMetadata(object):
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
