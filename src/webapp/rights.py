from pprint import pprint as pp
import re
import logging
import configparser
import json
import uuid
#import spotipy
#from spotipy.oauth2 import SpotifyClientCredentials
import pyfy
import discogs_client # pip install discogs_client  
import functools
import backoff # pip install backoff
import requests
import requests_cache
import datetime
import time
import aiohttp

import model

TRUST_ISRC=True
TRUST_EAN=False # TODO: figure out if we can trust EAN

MUSIC_OWNERSHIP_IS_PUBLIC_DOMAIN_YEAR=1963

class NotFoundError(Exception): 
    pass

class DiscogsNotFoundError(NotFoundError): 
    pass

class SpotifyNotFoundError(NotFoundError): 
    pass

def remove_corporate_suffix(lbl):
    'Removes common corporation suffixes to normalize string before lookup'
    if lbl is None:
        return lbl
    for sufx in [' AS', ' A/S', ' A.S.', 'Ltd.', 'O/S']:  # remove suffix
        if lbl.upper().endswith(sufx):
            return lbl[:-len(sufx)]
    return lbl

def get_year_from_string(s):
    'Extract everything that looks like a year from a string'
    return [ int(y) for y in re.findall(r'\d{4}', s) if 1850 < int(y) < 2100 ]

def release_is_old_and_public_domain(releaseyear, spotifylabelinfo=None):
    '''Return True if both the released date and the copyright date are older 
    than the 'MUSIC_OWNERSHIP_IS_PUBLIC_DOMAIN_YEAR' variable.''' 
    #logging.debug('public_domain? %r %r', releaseyear, spotifylabelinfo)
    try:
        spotifyyear = min( get_year_from_string (spotifylabelinfo.get('P', None) or spotifylabelinfo.get('C', None)) )
    except ValueError as e:
        # spotify cant help us, look at what we have
        return releaseyear, releaseyear < MUSIC_OWNERSHIP_IS_PUBLIC_DOMAIN_YEAR

    minyear =  min(releaseyear, spotifyyear)  # get the oldest year
    return minyear, minyear < MUSIC_OWNERSHIP_IS_PUBLIC_DOMAIN_YEAR

class RateLimitedCachingClient(discogs_client.Client):
    'Reimplemntattion to cache data from discogs, and to retry if we get 429 rate limit errors'

    def __init__(self, *args, **kwargs):
        'subclass that inits requests.sessions and hands over to superclass'
        super().__init__(*args, **kwargs)
        expiry = datetime.timedelta(days=7) # keep cached values this long
        self._session = requests_cache.core.CachedSession(cache_name='discogs_client', 
                                                          backend=None, 
                                                          expire_after=expiry)

    '''
    def _fetcher(self, client, method, url, data=None, headers=None, json=True):
        'subclassing to add token to every request, and to add session awareness'
        resp = self._session.request(method, url, params={'token':self.user_token},
                                     data=data, headers=headers)
        return resp.content, resp.status_code 
    '''

    # TODO: check HTTP_ERROR=429
    # catch 429 rate limit blowups and retry
    # this will happen if we make too many requests per minute. 
    # discogs_client.exceptions.HTTPError: 429: You are making requests too quickly.
    @backoff.on_exception(lambda: backoff.constant(interval=5), # wait 5 secs
                          discogs_client.exceptions.HTTPError,
                          max_tries=5,
                          jitter=backoff.full_jitter)
    def _get(self, url):
        time.sleep(2)
        return self._request('GET', url)

class DueDiligence:
    useragent = 'no.nrk.odometer/0.3'

    def __init__(self, config): #:configparser.ConfigParser):
        self.cred_manager = pyfy.ClientCreds(config.get('spotify', 'clientId'),
                                             config.get('spotify', 'secret')
        )
        self.sp = pyfy.Spotify(client_creds=self.cred_manager)
        self.sp.authorize_client_creds()
        self.discogs = RateLimitedCachingClient(self.useragent, user_token=config.get('discogs', 'token'))

    def spotify_search_copyrights(self, trackmetadata): #:dict) -> dict:
        'Try to llok up a Track in spotify and return the copyrights.'
        #pp(sp.album('spotify:album:5UAN1IyYzJUDLvweDXDqJf').get('copyrights'))
        # 1. search for track info (track title and artist)
        # 2. get album
        # 3. get album uri and return it

        # Trackmetadata is modelled in model.py
        q = []
        SEARCH_USING_ISRC=False
        if TRUST_ISRC and 'isrc' in trackmetadata and trackmetadata['isrc'] is not None:
            q.append('isrc:{}'.format(trackmetadata['isrc']))
            SEARCH_USING_ISRC=True
        elif TRUST_EAN and 'ean' in trackmetadata and trackmetadata['ean'] is not None:
            q.append('upc:{}'.format(trackmetadata['ean']))
        else:
            # no unique code searches, build up a query of what we know
            if 'year' in trackmetadata and trackmetadata['year'] != -1:
                q.append('year:{}'.format(trackmetadata['year']))
            q.append('{} {}'.format(trackmetadata['title'], trackmetadata['artist']))
            if 'albumname' in trackmetadata and trackmetadata['albumname'] is not None:
                q.append(trackmetadata['albumname'])
        track = self.spotify_search_track(' '.join(q))

        # sanity check to figure out if spotify gave us something that looks like what we are after
        # because sometimes, ISRC codes are wrong
        logging.debug("got track from spotify: %r", track)
        if track['name'].lower() != trackmetadata['title'].lower(): # check if title matches
            if SEARCH_USING_ISRC:
                # we have hit a wrong ISRC code
                # try to search again, without the ISRC 
                logging.warn("ISRC code seems to be wrong: %s (%s)", 
                            trackmetadata['isrc'], trackmetadata['identifier'])
                del trackmetadata['isrc']
                return self.spotify_search_copyrights(trackmetadata)
            raise SpotifyNotFoundError('Ambigous result returned from Spotify. Please check manually')
        if not SEARCH_USING_ISRC:
            # we only check artist if we haven't used ISRC 
            if not trackmetadata['artist'].lower() in [a['name'].lower() for a in track['artists']]: # check artist
                raise SpotifyNotFoundError('Ambigous result returned from Spotify. Please check manually')

        return track, self.spotify_get_album_rights(track['album']['id']) # return track metadata + album copyright

    def spotify_search_track(self, querystring):#:str) -> dict:
        '''Search for track in spotify and return all metadata. 
        
        See this for search tips: https://support.spotify.com/us/article/search/

        As per march 2018

        Enter any of these before your search term to narrow the results.

            year: Displays music from a particular year. You can also enter a range of years, for example year:1978-1984.
            genre: Displays music in the genre matching keyword.
            label: Displays music released by the label matching keyword.
            isrc: Displays tracks matching ID number according to the International Standard Recording Code.
            upc: Displays albums matching ID number according to the Universal Product Code.
            tag:new - Lists the most recently added albums.

        Refine your search with AND, OR, and NOT, for example:

            Kyuss AND Green - Displays results with keywords 'Kyuss' and 'Green'.
            Zeppelin OR Floyd - Displays results with keywords 'Zeppelin' or 'Floyd'.
            Metallica NOT Anger - Displays all Metallica tracks except with the word 'Anger'. 
            Tip: Instead of using AND or NOT, you can also use + or -.

        Use any combination of the advanced search options to find exactly what you want!

            year:1989-2013 NOT year:1993
            genre:metal AND year:1932
            Note: This particular example may not yield many results.
        '''

        srch = self.sp.search(q=querystring, type='track', market='NO')
        logging.debug('search int sqrch: %r', srch)
        # TODO iterate trhroug all
        try:
            firsttrack = srch['tracks']['items'][0]
        except IndexError:
            # no results returned
            raise SpotifyNotFoundError('Could not find a track using the query "{}". Please refine your search terms'.format(querystring))
        return firsttrack

    def spotify_search_playlist(self, playlist_urn): #:str) -> dict:
        'Get a list of spotify ids from a playlist'
        # 'spotify:user:spotifycharts:playlist:37i9dQZEVXbJiZcmkrIHGU' -> spotifycharts, 37i9d...
        try:
            _, _, user, _, playlist_id = playlist_urn.split(':')
        except ValueError:
            # try the new (2018) version of playlists
            #spotify:playlist:5k6vmN2dpZjvdSv8aXvz44
            _, _, playlist_id = playlist_urn.split(':')

        srch = self.sp.playlist(playlist_id)
        trackstub = model.TrackStub(many=False)
        # TODO: handle paging (more than 100 items in list). look at spotipy.next(), srch["next"] is an url if there are more items, null if there arent
        for item in srch['tracks']['items']:
            logging.debug('got spotify item %r', json.dumps(item['track']['album']))
            try:
                y = int(item['track']['album']['release_date'][:4])
            except TypeError:
                y = -1
            st = trackstub.dump({'title':     item['track']['name'],
                                   'uri':       item['track']['uri'],
                                   'artists':   [a['name'] for a in item['track']['artists']], 
                                   'album_uri': item['track']['album']['uri'],
                                   'year':      y
                                   })
            yield st

    def spotify_get_album_rights(self, albumuri):#:str) -> dict:
        'Get copyright info from spotify album uri'
        def parse_label(labelstring):#:str) -> str:
            #logging.debug('Parsing copyright owner from %r', labelstring)
            # (C) 1993 Virgin Records America, Inc. -> "Virgin Records America, Inc."
            # ℗ 2017 Propeller Recordings, distributed by Universal Music AS, Norway -> 
            rex = re.compile(r'^(?:\(C\)|\(P\)|℗|©)? ?\d{4}?(?:, \d{4})? ?(.+)')
            try:
                first_step = rex.match(labelstring).group(1)
            except AttributeError:
                # (P) NorskAmerikaner AS 2008
                try:
                    rex2 = re.compile(r'^(?:\(C\)|\(P\)|℗|©)? (.+) \d{4}(?:, \d{4})?')
                    first_step = rex2.match(labelstring).group(1)
                except AttributeError:
                    return None
            second_step = self.parse_label_attribution(first_step)
            return second_step or first_step # return what we have if the second step didnt return anything better
        r = self.sp.albums(albumuri).get('copyrights')
        ret = { k['type']:k['text'] for k in r}
        if 'P' in ret: # have (P) section
            ret.update({'parsed_label': parse_label(ret['P'])})
        elif 'C' in ret: # have (C) section
            ret.update({'parsed_label': parse_label(ret['C'])})
        return ret

    @functools.lru_cache(maxsize=256)
    def parse_label_attribution(self, labelquery):#:str) -> str:
        'Simplify label / phonograph / copyright attribution, for lookups at discogs'
        # Atlantic Recording Corporation for the United States and WEA International Inc. for the world outside of the United States. A Warner Music Group Company -> ???
        # Bad Vibes Forever / EMPIRE 
        _origquery = labelquery

        # normalize A/S, AS, as suffix
        labelquery = re.sub(r' a/s$', ' AS', labelquery, flags=re.IGNORECASE)

        # remove norway suffix
        labelquery = re.sub(r',? norway$', '', labelquery, flags=re.IGNORECASE)

        rexes = [
            r'(?i)^(.+), manufactured and marketed by .+', # The Weeknd XO, Inc., manufactured and marketed by Republic Records, a division of UMG Recordings, Inc. -> The Weeknd XO, Inc.
            r'(?i)^(.+), marketed and distributed by .+', # Pink Floyd Music Ltd., marketed and distributed by Parlophone Records Ltd., a Warner Music Group Company -> Pink Floyd Music Ltd.
            r'(?i)^(.+?),? distributed by (?:.+)', # Propeller Recordings, distributed by Universal Music AS, Norway
            r'(?i)(?:.+), a division of (.+)', #Republic Records, a division of UMG Recordings, Inc. -> UMG Recordings, Inc 
            r'(?i)(?:.+) – a division of (.+)', #Cosmos Music Norway – A division of Cosmos Music Group
            r'(?i)(?:.+?),? under exclusive licen[cs]e to (.+)', #The copyright in this sound recording is owned by Willy Mason under exclusive licence to Virgin Records Ltd
            r'(?i)^The copyright in this sound recording is owned by (.+)', # The copyright in this sound recording is owned by Mawlaw 388 Ltd T/A Source UK
            r'(?i)^Originally Released \d{4}\.? (.+)', # Originally Released 1962 SONY BMG MUSIC ENTERTAINMENT
            r'^[^/]+/(.+)', # KIDinaKORNER/Interscope Records -> Interscope Records
            r'(?i)^(.+) Inc\.', # Cash Money Records Inc. (company) -> Cash Money Records (label)
        ]
        for rx in rexes:
            try:
                logging.debug('Trying to simplyfi with rx %r', rx)
                return re.compile(rx).match(labelquery).group(1).strip()
            except AttributeError:
                continue

        if _origquery != labelquery:
            # no regexp matched, but we've still brushed it up a bit
            return labelquery

        logging.debug('Could not simplify label %r', labelquery)
        return None

    #@functools.lru_cache(maxsize=256)
    def discogs_search_label(self, labelquery):#:str) -> discogs_client.models.Label:
        'Search for label in discogs'
        # strategy
        # 1. first, search naively with the full string
        # 2. if no match, parse the label string and simplify, and search again
        # 3. do sanity check of the topmost result
        # 4. return it if it passes

        def normalize(string):
            'Make strings possible to compare'
            try:
                string = re.sub(r'Ltd(\ |$)', 'Ltd.', string) # in discogs, Ltd is always abbreviated with the dot
            except TypeError as e:
                logging.debug('could not normalize %r, got etror %r', string, e)

            string = string.lower()                       # casing is such a mess
            return string

        def search(query):
            if query is None:
                return None
            srch = self.discogs.search(type='label', q=query)
            logging.debug('got srch :%r', srch)
            for l in srch.page(0):
                # see if we find direct name hit
                # l is discogs_client.models.Label
                if normalize(l.name) == normalize(query):
                    return l
            return None

        if labelquery is None:
            raise DiscogsNotFoundError('This is not a valid label query: {}'.format(labelquery))
        
        first = search(labelquery)
        if first is not None:
            return first

        second = search(self.parse_label_attribution(labelquery))
        if second is not None:
            return second

        raise DiscogsNotFoundError('Could not find the label "{}" in the Discogs database'.format(labelquery))

    #@functools.lru_cache(maxsize=128)
    def discogs_label_heritage(self, label):#discogs_client.models.Label) -> discogs_client.models.Label:
        'Take a discogs label and walk the parenthood till the very top'

        heritage = [label]
        while hasattr(label, 'parent_label'):
            label = label.parent_label
            if label is not None:
                heritage.append(label)
        return heritage

class ISRCChecker:
    'Check ISRC codes from ifpi.org and get metadata'
    session = None
    headers = {}

    def __init__(self):
        self.session = aiohttp.ClientSession()
        self.headers = {
            'referer': 'https://isrcsearch.ifpi.org/',
            'origin': 'https://isrcsearch.ifpi.org',
            'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/78.0.3904.97 Safari/537.36'
        }

    async def seed(self):
        async with self.session.get('https://isrcsearch.ifpi.org/') as r:# seed cookie jar
            t = await r.text()
            csrf = re.compile(r'window.csrfmiddlewaretoken\ =\ "([^"]+)";').findall(t)[0]
            # get CSRF token
            self.headers.update({'x-csrftoken': csrf})


    async def fetch(self, isrc_code):
        url = 'https://isrcsearch.ifpi.org/api/v1/search'
        postdata = {
            'number': 10,
            'searchFields': { 'isrcCode': isrc_code},
            'showReleases': 0,
            'start': 0
        }
        schema = model.IFPIsearchTrack()
        async with self.session.post(url, json=postdata, headers=self.headers) as response:
            data = await response.json()
            if data['numberOfHits'] == 0:
                # no hits
                return None

            # load into shecma for data validation
            track = schema.load(data=data["displayDocs"][0])
            return track

class DueDiligenceJSONEncoder(json.JSONEncoder):
    'turning external models into neat json'
    def default(self, obj):
        if isinstance(obj, discogs_client.models.Label):
            # model definitoion: 
            # https://github.com/discogs/discogs_client/blob/dc6551e5844d20a9da69e97c19afa8234f292d41/discogs_client/models.py#L521
            d = {'id':obj.id,
                 'name':obj.name,}
            return d
        elif isinstance(obj, uuid.UUID):
            # https://docs.python.org/3/library/uuid.html
            return str(obj)
        # Let the base class default method raise the TypeError
        return json.JSONEncoder.default(self, obj)


if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    import argparse

    parser = argparse.ArgumentParser(description="Odometer stats generator")
    parser.add_argument('--configfile', default='config.ini')
    parser.add_argument('trackinfo')
    args = parser.parse_args()

    configuration = configparser.ConfigParser()
    configuration.read(args.configfile)

    dd = DueDiligence(configuration)
    rights = dd.spotify_search_track(args.trackinfo)
    pp(rights)
