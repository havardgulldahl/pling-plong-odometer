#!/usr/bin/env python
# -*- enc: utf-8 -*-

import SimpleHTTPServer
import BaseHTTPServer, urlparse
import SocketServer
import StringIO

from metadata.gluon import GluonRequestParser

class GluonHandler(BaseHTTPServer.BaseHTTPRequestHandler):
    def do_POST(self):
        print self.path
        if self.path == '/gluon':
            parser = GluonRequestParser()
            #print [vars(z) for z in parser.parse(self.rfile)]
            data = self.rfile.read()
            print repr(data)
            data = urlparse.parse_qs(data)["data"][0]
            print repr(data)
            f = StringIO.StringIO(data)
            print [vars(z) for z in parser.parse(f)]


def run_while_true(server_class=BaseHTTPServer.HTTPServer,
                   handler_class=BaseHTTPServer.BaseHTTPRequestHandler):
                   """
                   This assumes that keep_running() is a function
                   of no arguments which
                   is tested initially and after each
                   request.  If its return value
                   is true, the server continues.
                   """
                   server_address = ('', 8000)
                   httpd = server_class(server_address, handler_class)
                   while True: #keep_running():
                       httpd.handle_request()


run_while_true(handler_class=GluonHandler)
