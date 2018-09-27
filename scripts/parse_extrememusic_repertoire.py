#!/usr/bin/env python3

#-*- encoding: utf-8 -*-

#curl 'https://napi.extrememusic.com/grid_items?range=0%2C34&view=series' -H 'Origin: https://www.extrememusic.com' -H 'Accept-Encoding: gzip, deflate, br' -H 'X-API-Auth: 2285d3fe0cedadea9418c76c2ae47f372c58f5149ec8e101918c9b524cabc88b' -H 'User-Agent: Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/69.0.3497.100 Safari/537.36' -H 'Accept-Language: nb-NO,nb;q=0.9,en-US;q=0.8,en;q=0.7,no;q=0.6,nn;q=0.5,sv;q=0.4,da;q=0.3' -H 'Accept: application/json, text/javascript, */*; q=0.01' -H 'Referer: https://www.extrememusic.com/new_releases' -H 'X-Site-Id: 1' -H 'Connection: keep-alive' -H 'DNT: 1' --compressed
import sys
import requests
import logging
logging.basicConfig(level=logging.DEBUG)

LOGINURL='https://www.extrememusic.com/env'
URL='https://napi.extrememusic.com/grid_items?range=0%2C50&view=series' # returns JSON
#SEARCHURL='http://search.warnerchappellpm.com/login/publicsearch'

def startSession(ses):
    'access extrememusic to get session cookie'
    data = ses.get(LOGINURL)
    logincookie = datai['env']['API_AUTH']
    s.headers.update({'X-API-AUTH': logincookie})

def iterReportoire(ses):
    'return an iterator of all label names in reportoire'
    data = ses.json(URL)
    for itm in data.get('grid_items'):
        prefix = itm.get('image_large_url').split('/')[-1].split('.')[0].upper()
        yield (prefix, itm.get('title').title())

if __name__ == '__main__':
    session = requests.Session()
    startSession(session)
    s = ""
    for _prefix, _label in iterReportoire(session):
        s = s+ """'{}': '{}', """.format(_prefix, _label)

    s = s + '\n\n{}'.format(_short)
    print(s)
    session.close()
