from pprint import pprint as pp
import logging
import configparser
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
import discogs_client # pip install discogs_client  

class NotFoundError(Exception): 
    pass

class DiscogsNotFoundError(NotFoundError): 
    pass

class SpotifyNotFoundError(NotFoundError): 
    pass

class DueDiligence:
    useragent:str = 'no.nrk.odometer/0.1'

    def __init__(self, config:configparser.ConfigParser):
        self.cred_manager = SpotifyClientCredentials(config.get('spotify', 'clientId'),
                                                     config.get('spotify', 'secret')
        )
        self.sp = spotipy.Spotify(client_credentials_manager=self.cred_manager)
        self.discogs = discogs_client.Client(self.useragent, user_token=config.get('discogs', 'token'))

    def spotify_search_copyrights(self, titleandartist:str) -> dict:
        'Try to llok up a Track in spotify and return the copyrights'
        #pp(sp.album('spotify:album:5UAN1IyYzJUDLvweDXDqJf').get('copyrights'))
        # 1. search for track info (track title and artist)
        # 2. get album
        # 3. get album uri and return it
        track = self.spotify_search_track(titleandartist)
        return self.spotify_get_album_rights(track['album']['uri'])

    def spotify_search_track(self, titleandartist:str) -> dict:
        'Search for track in spotify and return all metadata'
        srch = self.sp.search(q=titleandartist, type='track', market='NO')
        logging.debug('search int sqrch: %r', srch)
        # TODO iterate trhroug all
        firsttrack = srch['tracks']['items'][0]
        return firsttrack

    def spotify_get_album_rights(self, albumuri:str) -> dict:
        'Get copyright info from spotify album uri'
        return {'spotify': self.sp.album(albumuri).get('copyrights')}

        #return sp.album('spotify:album:5UAN1IyYzJUDLvweDXDqJf').get('copyrights')

    # discogs
    def discogs_search_label(self, label:str) -> discogs_client.models.Label:
        'Search for label in discogs'
        #TODO: add fuzzy search
        srch = self.discogs.search(type='label', q=label)
        logging.debug('got srch :%r', srch)
        for l in srch.page(0):
            # see if we find direct name hit
            # l is discogs_client.models.Label
            if l.name == label:
                return l

        raise DiscogsNotFoundError('Could not find the label "{}" in the Discogs database'.format(label))

    def discogs_top_label(self, label:discogs_client.models.Label) -> discogs_client.models.Label:
        heritage = [label]
        while hasattr(label, 'parent_label'):
            if label.parent_label is not None: # None indicates we reached top level
                label = label.parent_label
                heritage.append(label)
        return heritage


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
    rights = dd.spotify_search_copyrights(args.trackinfo)
    pp(rights)