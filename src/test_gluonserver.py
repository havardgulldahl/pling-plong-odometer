#!/usr/bin/env python
# -*- encoding: utf-8 -*-

import SimpleHTTPServer
import BaseHTTPServer, urlparse
import SocketServer
import StringIO
import random

from metadata.gluon import GluonRequestParser

class dummy(object):
    def __init__(self, musicid):
        i = random.randint(0,1000)
        self.tracktitle = "Tracktitle %s" % i
        self.albumtitle = "Albumtitle %s" % i
        self.writer = "Writer %s" % i
        self.composer = "Composer %s" % i
        self.artist = "Artist %s" % i
        self.year = random.randint(1850,1999)
        self.musicid = musicid

def xml(data):
    s = """
<?xml version="1.0" encoding="utf-8"?>
<gluon priority="3" artID="gms123"
xmlns="http://gluon.nrk.no/gluon2"
xmlns:gluonDict="http://gluon.nrk.no/gluonDict"
xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
xsi:schemaLocation="http://gluon.nrk.no/gluon2 file:///C:/Documents%20and%20Settings/n12327/Desktop/mine%20filer/gluon.xmlSpy/gluon2.xsd">

  <head>
    <metadata>
      <creators>
        <creator>
          <name>gluonDmaServices</name>
        </creator>
      </creators>
    </metadata>
  </head>
  <objects>
"""
    for obj in data:
        print vars(obj)
        s += """
    <object objecttype="item">
      <metadata>
        <titles>
          <title>%(tracktitle)s</title>
          <titleAlternative gluonDict:titlesGroupType="albumTitle">
          %(albumtitle)s</titleAlternative>
        </titles>
        <creators>
          <creator>
            <name>%(composer)s</name>
            <role link="http://gluon.nrk.no/nrkRoller.xml#V34">
            %(composer)s</role>
          </creator>
          <creator>
            <name>%(writer)s</name>
            <role link="http://gluon.nrk.no/nrkRoller.xml#V811">
            %(writer)s</role>
          </creator>
        </creators>
        <contributors>
          <contributor>
            <name>%(artist)s</name>
            <role link="http://gluon.nrk.no/nrkRoller.xml#V35">
            %(artist)s</role>
          </contributor>
        </contributors>
        <dates>
          <dateAlternative gluonDict:datesGroupType="dateIssued">
            <start startYear="%(year)s" />
            <!--Utgivelsesår-->
          </dateAlternative>
        </dates>
        <identifier>%(musicid)s</identifier>
      </metadata>
    </object>
""" % vars(dummy(obj.identifier))
    s += """
  </objects>
</gluon>
"""
    return s

class GluonHandler(BaseHTTPServer.BaseHTTPRequestHandler):
    def do_POST(self):
        print self.path
        if self.path == '/gluon':
            rlen = int(self.headers.get("Content-Length", 1))
            data = self.rfile.read(rlen)
            self.send_response(200)
            self.end_headers()
            self.wfile.write("THanks!\r\n\r\n")
            data = urlparse.parse_qs(data)["data"][0]
            f = StringIO.StringIO(data)
            parser = GluonRequestParser()
            parsed = parser.parse(f)
            self.wfile.write(xml(list(parsed)))
            return 


if __name__ == '__main__':
    from BaseHTTPServer import HTTPServer
    server = HTTPServer(('localhost', 8000), GluonHandler)
    print 'Starting server, use <Ctrl-C> to stop'
    server.serve_forever()

