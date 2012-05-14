#!/usr/bin/env python2.7
#-*- encoding: utf-8 -*-

# snippet to fetch help text online

import urllib
import sys
import lxml.html
import ConfigParser

def parse(url):
    html = lxml.html.parse(url)
    doc = html.getroot().find_class('entry-content')
    images = [ child.get('src') for child in doc.iterchildren(tag='img') ]
    return { 'html': doc.pop(),
             'images': images }

def get(url):
    pass


if __name__ == '__main__':
    config = ConfigParser.ConfigParser()
    config.read('BUILDFLAGS')
    doc = parse(config.get('release', 'helpUrl'))
    with open(sys.argv[1], 'w') as txt:
        txt.write(lxml.html.tostring(doc['html']))
    for imgurl in doc['images']:
        print imgurl
        with open(os.path.join(sys.argv[2], os.path.basename(imgurl)), 'wb') as img:
            shutil.copyfileob(get(imgurl), img)
    


