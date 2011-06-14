#-*- encoding: utf8 -*-
#
# This file is part of odofon by Håvard Gulldahl <havard.gulldahl@nrk.no>
# (C) 2011

import sys, xml.etree.ElementTree as ET

from metadata import TrackMetadata

GLUON_NAMESPACE='{http://gluon.nrk.no/gluon2}'
GLUONDICT_NAMESPACE='{http://gluon.nrk.no/gluonDict}'
XSI_NAMESPACE='{http://www.w3.org/2001/XMLSchema-instance}'

## three convenience methods to hide all 
## namespace ugliness and clutter

def glns(tag):
    return '%s%s' % (GLUON_NAMESPACE, tag)

class glel(ET._ElementInterface):
    def add(self, tagName):
        return ET.SubElement(self, glns(tagName))

def glsel(parent, tag, *a, **kw):
    return ET.SubElement(parent, glns(tag), *a, **kw)

class GluonBuilder(object):
    "Build a gluon xml tree from a list of audio clips and their length"
    prodno = 'DNPR63001010AA'
    objects = []

    def __init__(self, prodno, metadatalist):
        self.prodno = prodno
        self.objects = metadatalist
        self.build()

    def build(self):
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
            xobj = glsel(elements,'object', {'objecttype':'item'})
            identifier = glsel(xobj,'identifier').text=obj['musicid']

            types = glsel(xobj,'types')
            lib = glsel(types,'type').text=obj['musiclibrary']
            formatel = glsel(xobj,'format')
            duration = glsel(formatel,'formatExtend').text='%.2f' % obj['duration']

            dates = glsel(xobj, 'dates')
            dateAlternative = glsel(dates, 'dateAlternative')
            dateAlternative.set(ET.QName(GLUONDICT_NAMESPACE+'datesGroupType'), 'objectEvent')
            start = glsel(dateAlternative, 'start')
            start.set('startPoint', 'XX')
            end = glsel(dateAlternative, 'end')
            end.set('startPoint', 'XX')
            
    def toxml(self):
        return ET.tostring(self.root, encoding='utf-8')


class GluonParser(object):
    "Parse a gluon xml response to retrieve metadata for audio clips"

    def parse(self, xmlsource):
        self.tree = ET.parse(xmlsource)
        for obj in self.tree.getiterator(glns('object')):
            md = TrackMetadata()
            md.identifier = obj.find('.//'+glns('identifier')).text
            md.title = obj.find('.//'+glns('title')).text
            md.albumname = obj.find('.//'+glns('titleAlternative')).text
            for creator in obj.findall('.//'+glns('creator')):
                self.c = creator
                if creator.find('./'+glns('role')).get('link') == 'http://gluon.nrk.no/nrkRoller.xml#V34':
                    # Komponist
                    md.composer = creator.find('./'+glns('name')).text
                elif creator.find('./'+glns('role')).get('link') == 'http://gluon.nrk.no/nrkRoller.xml#V811':
                    # Tekstforfatter
                    md.writer = creator.find('./'+glns('name')).text
            md.artist = obj.find('.//'+glns('contributors')+'/'+glns('contributor')+'/'+glns('name')).text
            md.year = obj.find('.//'+glns('dates')+'/*/'+glns('start')).get('startYear')
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
    gb = GluonBuilder('DNPR630009AA', items)
    r = gb.build()
    print r
    gp = GluonParser()
    x = gp.parse(sys.argv[1])
            


