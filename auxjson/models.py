#!/usr/bin/env python
#-*- encoding: utf8 -*-
# This file is part of odometer by Håvard Gulldahl <havard.gulldahl@nrk.no>
# (C) 2011-2012
#

from google.appengine.ext import db
from google.appengine.api import users


class Catalogue(db.Model):
  "Models an AUX catalogue "
  datetimestamp = db.DateTimeProperty(auto_now_add=True)
  name = db.StringProperty(multiline=False)
  shortname = db.StringProperty(multiline=False)

def catalogue_key(catalogue_shortname=None):
  "Constructs a Datastore key for a Catalogue with a shortname"
  return db.Key.from_path('Catalogue', guestbook_name)


