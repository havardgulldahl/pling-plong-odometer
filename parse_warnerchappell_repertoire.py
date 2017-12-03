#-*- encoding: utf-8 -*-

import sys
import lxml.html
import requests
import logging
logging.basicConfig(level=logging.DEBUG)

URL='http://www.warnerchappellpm.com/our-libraries/'
SEARCHURL='http://search.warnerchappellpm.com/login/publicsearch'

def iterReportoire(ses):
    'return an iterator of all label names in reportoire'
    doc = ses.get(URL)
    html = lxml.html.fromstring(doc.text)
    return [h.text for h in html.iter('h2')]

def getSampleShortname(labelName, ses):
    'get a labelName, and get an example label filename'
    logging.debug('getting samples for %r', labelName)
    r = ses.get(SEARCHURL, params={'searchtext':'library["{}"]'.format(labelName),
                                        'public':'USGuestUser',
                                        'vista':'mixed'
        })
    r.raise_for_status()
    html = lxml.html.fromstring(r.text)
    names = html.xpath('//img[@album_value]/@album_value')
    logging.debug('got names. {!r}'.format(names))
    try:
        return names[0]
    except IndexError:
        return None


if __name__ == '__main__':
    _short = []
    session = requests.Session()
    s = ""
    for _label in iterReportoire(session):
        _prefix = getSampleShortname(_label, session)
        s = s+ """'{}': '{}', """.format(_prefix, _label)

    s = s + '\n\n{}'.format(_short)
    print(s)
    session.close()
