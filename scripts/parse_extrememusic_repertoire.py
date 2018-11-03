#!/usr/bin/env python3

#-*- encoding: utf-8 -*-

import sys
import requests
import logging
logging.basicConfig(level=logging.DEBUG)

LOGINURL='https://www.extrememusic.com/env'
URL='https://napi.extrememusic.com/grid_items?range=0%2C50&view=series' # returns JSON

def startSession(ses):
    'access extrememusic to get session cookie'
    data = ses.get(LOGINURL)
    logincookie = data.json()['env']['API_AUTH']
    ses.headers.update({'X-API-AUTH': logincookie})

def iterReportoire(ses):
    'return an iterator of all label names in reportoire'
    data = ses.get(URL)
    for itm in data.json().get('grid_items'):
        prefix = itm.get('image_large_url').split('/')[-1].split('.')[0].upper()
        yield (prefix, itm.get('title').title())

if __name__ == '__main__':
    session = requests.Session()
    startSession(session)
    s = ""
    for _prefix, _label in iterReportoire(session):
        s = s+ """'{}': '{}', """.format(_prefix, _label)

    print(s)
    session.close()
