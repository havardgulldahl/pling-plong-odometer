#-*- encoding: utf8 -*-
#
# This file is part of odometer by Håvard Gulldahl <havard.gulldahl@nrk.no>
# (C) 2011

import sys, xml.etree.ElementTree as ET

#from metadata import TrackMetadata

GLUON_NAMESPACE='{http://gluon.nrk.no/gluon2}'
GLUONDICT_NAMESPACE='{http://gluon.nrk.no/gluonDict}'
XSI_NAMESPACE='{http://www.w3.org/2001/XMLSchema-instance}'

## three convenience methods to hide all 
## namespace ugliness and clutter

def glns(tag):
    s = []
    for ss in tag.split("/"):
        s.append('%s%s' % (GLUON_NAMESPACE, ss))
    return "/".join(s)

class glel(ET._ElementInterface):
    def add(self, tagName):
        return ET.SubElement(self, glns(tagName))

def glsel(parent, tag, *a, **kw):
    return ET.SubElement(parent, glns(tag), *a, **kw)

class GluonReportBuilder(object):
    "Build a gluon xml tree from a list of audio clips and their length"
    def __init__(self, prodno, metadatalist):
        print "gluonbuilder init"
        self.prodno = prodno
        self.objects = metadatalist
        self.build()

    def build(self):
        print "gluonbuilder build"
        self.root = glel(glns('gluon'), {'priority':'3',
                                   'artID':'odofon-1234',
                                })
        self.root.set('%s%s' % (XSI_NAMESPACE, 'schemaLocation'),
                      'http://gluon.nrk.no/gluon2 http://gluon.nrk.no/gluon2.xsd')
        head = self.root.add('head')
        md = glsel(head, 'metadata')
        creators = glsel(md, 'creators')
        creator = glsel(creators, 'creator')
        name = glsel(creator, 'name')
        name.text = 'odofon'

        objects = self.root.add('objects')
        rootobject = glsel(objects, 'object', {'objecttype':'programme'})

        rootmd = glsel(rootobject, 'metadata')
        prodno = glsel(rootmd, 'identifier')
        prodno.text = self.prodno

        elements = glsel(rootobject,'subelements')

        for obj in self.objects:
            md = obj.metadata
            clip = obj.clip
            xobj = glsel(elements,'object', {'objecttype':'item'})
            xobjmd = glsel(xobj, 'metadata')
            identifier = glsel(xobjmd,'identifier').text=md.getmusicid()

            types = glsel(xobjmd,'types')
            lib = glsel(types,'type').text=md.musiclibrary
            formatel = glsel(xobjmd,'format')
            # duration is ISO 8601 formatted ("Durations")
            duration = glsel(formatel,'formatExtent').text='PT%.2fS' % clip.audibleDuration

            dates = glsel(xobjmd, 'dates')
            dateAlternative = glsel(dates, 'dateAlternative')
            dateAlternative.set(ET.QName(GLUONDICT_NAMESPACE+'datesGroupType'), 'objectEvent')
            start = glsel(dateAlternative, 'start')
            start.set('startPoint', 'XX')
            end = glsel(dateAlternative, 'end')
            end.set('startPoint', 'XX')
            
    def toxml(self):
        xml = ET.tostring(self.root, encoding='utf-8')
        return xml

class GluonFactory(object):
    pass


class GluonMetadataResponseParser(object):
    "Parse a gluon xml response to retrieve metadata for audio clips"

    def parse(self, xmlsource, factory=GluonFactory):
        self.tree = ET.parse(xmlsource)
        obj = self.tree.find('.//'+glns('object'))
        #for obj in self.tree.getiterator(glns('object')):
            #md = TrackMetadata()
        md = factory()
        md.identifier = obj.find('.//'+glns('identifier')).text
        md.title = obj.find('.//'+glns('title')).text
        md.albumname = obj.find('.//'+glns('titleAlternative')).text
        for creator in obj.findall('.//'+glns('creator')):
            if creator.find('./'+glns('role')).get('link') == 'http://gluon.nrk.no/nrkRoller.xml#V34':
                # Komponist
                md.composer = creator.find('./'+glns('name')).text
            elif creator.find('./'+glns('role')).get('link') == 'http://gluon.nrk.no/nrkRoller.xml#V811':
                # Tekstforfatter
                md.lyricist = creator.find('./'+glns('name')).text
        _a = []
        for contributor in obj.findall('.//'+glns('contributor')):
            if contributor.find('./'+glns('role')).get('link') == 'http://gluon.nrk.no/nrkRoller.xml#V35':
                # Utøver
                _a.append(contributor.find('./'+glns('name')).text)
        md.artist = '; '.join(_a)
        for date in obj.findall('.//'+glns('dateAlternative')):
            if date.get('%sdatesGroupType' % GLUONDICT_NAMESPACE) == 'dateIssued':
                md.year = date.find('./'+glns('start')).get('startYear')
        for ref in obj.findall('.//'+glns('relationIsReferencedBy')):
            if ref.get('link') == 'http://gluon.nrk.no/dataordbok.xml#recordNumber':
                _recordnumber = ref.text
                try:
                    md.label, md.recordnumber = [ x.strip() for x in _recordnumber.split(';')]
                except ValueError:
                    md.recordnumber = _recordnumber
                    md.label = 'Unknown'
        return md

class GluonRequestParser(object):
    "Parse a gluon xml request to retrieve metadata for audio clips"

    def parse(self, xmlsource, factory=GluonFactory):
        self.tree = ET.parse(xmlsource)
        programmeobj = self.tree.find('./'+glns('objects/object'))
        if programmeobj.get('objecttype') != 'programme':
            return 
        programme = {"identifier": 
                programmeobj.find('./'+glns('metadata/identifier')).text,
                     "metadatacreator":
                self.tree.find('./' + \
                           glns('head/metadata/creators/creator/name')).text
        }
        subelements = programmeobj.find('./'+glns('subelements'))
        for obj in subelements.getiterator(glns('object')):
            if obj.get('objecttype') != 'item':
                print "gaffe"
                continue
            md = factory()
            md.programme = programme
            metadatatree = obj.find('./'+glns('metadata'))
            md.identifier = metadatatree.find('./'+glns('identifier')).text
            md.musiclibrary = metadatatree.find('./'+glns('types/type')).text
            md.duration = metadatatree.find('./'+glns('format/formatExtent')).text
            md.dateStart = \
            metadatatree.find('./'+glns('dates/dateAlternative/start')).get('startPoint')
            md.dateEnd = \
            metadatatree.find('./'+glns('dates/dateAlternative/end')).get('startPoint')
            yield md

if __name__ == '__main__':
    items = [
             {'musicid':'DNPRNPNPNPN',
              'musiclibrary':'DMA',
              'duration':2.0},
             {'musicid':'SCDASDFAS',
              'musiclibrary':'SONOTON',
              'duration':42.0},
             {'musicid':'DNPTRADFD',
              'musiclibrary':'DMA',
              'duration':200.0},
            ]
    #gb = GluonBuilder('DNPR630009AA', items)
    #r = gb.build()
    #print r
    gp = GluonMetadataResponseParser()
    x = gp.parse(sys.argv[1])
    print vars(x)
            


