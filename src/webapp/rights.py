from pprint import pprint as pp
import spotipy
import python-discogs

# spotify:
from spotipy.oauth2 import SpotifyClientCredentials
clientId = ''
secret = ''
client_credentials_manager = SpotifyClientCredentials(clientId, secret)
sp = spotipy.Spotify(client_credentials_manager=client_credentials_manager)

pp(sp.album('spotify:album:5UAN1IyYzJUDLvweDXDqJf').get('copyrights'))

# discogs
