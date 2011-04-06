#!/usr/bin/env python
#-*- encoding: utf8 -*-

import sys, os.path, random, time, urllib2, urlparse
import PyQt4.QtCore as Core
import PyQt4.QtGui as Gui
import PyQt4.QtWebKit as Web
import PyQt4.Qt as Qt

class TrackMetadata(object):
    def __init__(self,
                 filename=None,
                 title=None,
                 length=-1,
                 composer=None,
                 artist=None,
                 year=-1,
                 tracknumber=None,
                 albumname=None,
                 copyright=None,
                 lcnumber=None,
                 isrc=None,
                 ean=None,
                 catalogue=None,
                 label=None,
                 ):
        self.filename = filename
        self.title = title
        self.length = length # in seconds
        self.composer = composer
        self.artist = artist
        self.year = year
        self.tracknumber = tracknumber
        self.albumname = albumname
        self.copyright = copyright
        self.lcnumber = lcnumber
        self.isrc = isrc
        self.ean = ean
        self.catalogue = catalogue
        self.label = label

class ResolverBase(Core.QObject):

    prefixes = [] # file prefixes this resolver recognizes
    name = 'general'
    trackResolved = Core.pyqtSignal(unicode, TrackMetadata, name="trackResolved" )
    trackProgress = Core.pyqtSignal(unicode, int, name="trackProgress" )

    def accepts(self, filename): 
        for f in self.prefixes:
            if unicode(filename).startswith(f):
                return True
        return False

    def resolve(self, filename): 
        # reimplement this to return a TrackMetadata object if found
        return False
        
    def testresolve(self, filename):
        self.filename = filename
        i = random.randint(0,1000)
        md = TrackMetadata( filename = unicode(filename),
                            title = "Funky title %i" % i,
                            length = random.randint(30,500),
                            composer = "Mr. Composer %i" % i,
                            artist = "Mr. Performer %i" % i,
                            year = random.randint(1901,2011) )
        #time.sleep(random.random() * 4)
        self.trackResolved.emit(self.filename, md)
    

class SonotonResolver(ResolverBase):
    prefixes = ['SCD', ]
    name = 'Sonoton'
    url = 'http://www.sonofind.com/search/html/popup_cddetails_i.php?cdkurz=%s&w=tr'
    #url = 'http://www.google.com/?q=%s'
    #url = 'file:///home/havard/Documents/dev/Pling-Plong-Odometer/src/metadata/sonoton.%s.example'

    def resolve(self, filename):
        self.filename = filename
        self.doc = webdoc(self.filename, parent=None)
        self.doc.frame.loadFinished.connect(self.parse)
        self.doc.page.loadProgress.connect(self.progress)
        self.doc.load()

    def progress(self, i):
        self.trackProgress.emit(self.filename, i)
        
    def parse(self):
        metadatabox = unicode(self.doc.frame.findFirstElement("#csinfo").toInnerXml())
        metadata = TrackMetadata(filename=self.doc.filename)
        try:
            duration = unicode(self.doc.frame.findAllElements("div[style='top:177px;']")[1].toInnerXml())
            mins, secs = [int(s.strip()) for s in duration.split(' ')[0].split(":")]
            metadata.length=mins*60+secs
        except:
            pass
        mapping = { 'Track Name': 'title', #REMEMBER LAST SUMMER
                    'Track Number': 'tracknumber', #SCD 821 20.0
                    'Composer': 'composer', #Mladen Franko
                    'Artist': 'artist', #(N/A for production music)
                    'Album Name': 'album',#ORCHESTRAL LANDSCAPES 2
                    'Catalogue number': 'catalogue', #821
                    'Label': 'label', #SCD
                    'Copyright Owner': 'copyright', #(This information requires login)
                    'LC Number': 'lcdnumber', #07573
                  }
        for l in metadatabox.split('\n'):
            if not len(l.strip()): continue
            meta, data = [s.strip() for s in l.split(':')]
            setattr(metadata, mapping[meta], data)
        #print vars(metadata)
        self.trackResolved.emit(self.filename, metadata)

class DMAResolver(ResolverBase):
    prefixes = ['NDRO', ]
    name = 'DMA'

def findResolver(filename):
    resolvers = [ SonotonResolver(), DMAResolver() ]
    for resolver in resolvers:
        if resolver.accepts(filename):
            return resolver
    return False

class webdoc(Core.QObject):
    urlbase = 'http://www.sonofind.com/search/html/popup_cddetails_i.php?cdkurz=%s&w=tr'

    def __init__(self, filename, parent=None):
        super(webdoc, self).__init__(parent)
        self.filename = filename
        tracknumber, fileext = os.path.splitext(filename)
        self.url = self.urlbase % tracknumber
        self.page = Web.QWebPage(self)
        self.frame = self.page.mainFrame()
        self.settings = self.page.settings()
        self.settings.setAttribute(Web.QWebSettings.JavascriptEnabled, False)
        self.settings.setAttribute(Web.QWebSettings.AutoLoadImages, False)

    def load(self):
        #print "loading url: ", self.url
        self.frame.load(Core.QUrl(self.url))
        return

if __name__ == '__main__':
    app = Gui.QApplication(sys.argv)
    mq = MetadataQuery()
    resolve = mq.resolve('SCD082120')
    print resolve
    app.exec_()
