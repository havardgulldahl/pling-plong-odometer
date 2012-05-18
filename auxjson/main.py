#!/usr/bin/env python2.7
#-*- encoding: utf8 -*-
# This file is part of odometer by Håvard Gulldahl <havard.gulldahl@nrk.no>
# (C) 2011-2012
#
import webapp2
import json

import models
import lib

class MainHandler(webapp2.RequestHandler):
    def get(self):
        self.response.out.write('Hello world!')
        repertoire = models.Catalogue.all()
        self.response.out.write(json.dumps( dict( { x.shortname: x.name for x in repertoire } ) ))

class UpdateHandler(webapp2.RequestHandler):
    def get(self):
        for shortname, catalogue in lib.iterRepertoire():
            models.Catalogue.get_or_insert(shortname, name=catalogue, shortname=shortname)
        self.response.out.write('updated!')

app = webapp2.WSGIApplication([('/', MainHandler),
                               ('/update', UpdateHandler)],
                              debug=True)
