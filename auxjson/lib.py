#-*- encoding: utf8 -*-
# This file is part of odometer by Håvard Gulldahl <havard.gulldahl@nrk.no>
# (C) 2011-2012
#

from google.appengine.api import urlfetch
from StringIO import StringIO
import lxml.html

URL='http://search.auxmp.com/search/html/list_rep.php?'
URL='http://www.lurtgjort.no/auxrepertoire.php' # Norwegian mirror due to geoblock

def iterRepertoire():
    file = urlfetch.fetch(URL) 
    html = lxml.html.parse(StringIO(file.content)) 
    for row in html.getroot().find_class('s_t'):
        title, shorts = (x.strip() for x in row.text.split('-'))
        for short in [x.strip()[:4] for x in shorts.split(',')]:
            yield (short, title)

if __name__ == '__main__':
    for title, short in iterRepertoire():
        print short, " -> ", title
