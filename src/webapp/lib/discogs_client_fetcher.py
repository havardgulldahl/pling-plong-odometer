from discogs_client.fetchers import UserTokenRequestsFetcher 
from functools import lru_cache
import requests


@lru_cache(maxsize=256)
class CachingUserTokenRequestsFetcher(UserTokenRequestsFetcher):
    """Fetches via HTTP from the Discogs API using user_token authentication and caches the results"""

    def fetch(self, client, method, url, data=None, headers=None, json=True):
        resp = requests.request(method, url, params={'token':self.user_token},
                                data=data, headers=headers)
        return resp.content, resp.status_code
