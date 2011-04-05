#!/usr/bin/env python
#-*- encoding: utf8 -*-

import sys, os.path, random, time
import PyQt4.QtCore as Core
import PyQt4.Qt as Qt

class TrackMetadata(object):
    def __init__(self,
                 filename=None,
                 title=None,
                 length=-1,
                 composer=None,
                 artist=None,
                 year=-1,
                 ):
        self.filename = filename
        self.title = title
        self.length = length
        self.composer = composer
        self.artist = artist
        self.year = year

class ResolverBase(Core.QObject):

    prefixes = [] # file prefixes this resolver recognizes

    def accepts(self, filename): 
        for f in self.prefixes:
            if unicode(filename).startswith(f):
                return True
        return False

    def resolve(self, filename): 
        # reimplement this to return a TrackMetadata object if found
        return False
        

class SonotonResolver(ResolverBase):
    prefixes = ['SCD', ]
    def resolve(self, filename):
        i = random.randint(0,1000)
        md = TrackMetadata( filename = unicode(filename),
                            title = "Funky title %i" % i,
                            length = random.randint(30,500),
                            composer = "Mr. Composer %i" % i,
                            artist = "Mr. Performer %i" % i,
                            year = random.randint(1901,2011) )
        time.sleep(random.random() * 4)
        return md

class DMAResolver(ResolverBase):
    prefixes = ['NDRO', ]
        

class MetadataQuery(Core.QObject):
    resolvers = [ SonotonResolver(), DMAResolver() ]

    def resolve(self, filename):
        for resolver in self.resolvers:
            if resolver.accepts(filename):
                return resolver.resolve(filename)
        return False

