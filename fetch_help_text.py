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
    return doc.pop()

if __name__ == '__main__':
    config = ConfigParser.ConfigParser()
    config.read('BUILDFLAGS')
    text = parse(config.get('release', 'helpUrl'))
    print lxml.html.tostring(text)


