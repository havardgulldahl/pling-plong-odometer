from pprint import pprint as pp
import logging
import configparser
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
#import python-discogs

class DueDiligence:

    def __init__(self, config:configparser.ConfigParser):
        self.cred_manager = SpotifyClientCredentials(config.get('spotify', 'clientId'),
                                                     config.get('spotify', 'secret')
        )
        self.sp = spotipy.Spotify(client_credentials_manager=self.cred_manager)


    def search_track_rights(self, trackinfo:str) -> dict:
        'Try to llok up a Track in spotify and return the copyrights'
        #pp(sp.album('spotify:album:5UAN1IyYzJUDLvweDXDqJf').get('copyrights'))
        # 1. search for track info (name and artist)
        # 2. get album
        # 3. get album copyrights and return them
        srch = self.sp.search(q=trackinfo, type='track', market='NO')
        logging.debug('search int sqrch: %r', srch)
        # TODO iterate trhroug all
        firsttrack = srch['tracks']['items'][0]
        return self.get_album_rights(firsttrack['album']['uri'])

    def get_album_rights(self, albumuri:str) -> dict:
        'Get copyright info from spotify album uri'
        return {'spotify': self.sp.album(albumuri).get('copyrights')}

        #return sp.album('spotify:album:5UAN1IyYzJUDLvweDXDqJf').get('copyrights')

    # discogs


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
    rights = dd.search_track_rights(args.trackinfo)
    pp(rights)