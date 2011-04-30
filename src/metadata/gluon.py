#-*- encoding: utf8 -*-
#
# This file is part of odofon by Håvard Gulldahl <havard.gulldahl@nrk.no>
# (C) 2011

import sys, xml.etree.ElementTree as ET

def ezSubEl(parent, tagName, *args, **kwargs):
    return ET.SubElement(parent, tagName, *args, **kwargs)

class ezEl(ET.Element):
    def add(self, tagName):
        return ezSubEl(self, tagName)

class GluonBuilder(object):
    prodno = 'DNPR63001010AA'
    objects = []

    def __init__(self, prodno, metadatalist):
        self.prodno = prodno
        self.objects = metadatalist

    def build(self):
        self.root = ezEl('gluon')
        head = self.root.add('head')
        md = head.add('metadata')
        creators = md.add('creators')
        creator = creators.add('creator')
        name = creator.add('name')
        name.text = 'odofon'

        rootobject = ezSubEl(ezSubEl(self.root, 'objects'), 'object', {'objecttype':'programme'})
        prodno = ezSubEl(ezSubEl(rootobject,'metadata'), 'identifier').text=self.prodno
        elements = ezSubEl(rootobject,'subelements')
        for obj in self.objects:
            xobj = ezSubEl(elements,'object', {'objecttype':'item'})
            identifier = ezSubEl(xobj,'identifier').text=obj['musicid']
            lib = ezSubEl(ezSubEl(xobj,'types'),'type').text=obj['musiclibrary']
            duration = ezSubEl(ezSubEl(xobj,'format'),'formatExtend').text='%.2f' % obj['duration']
        return ET.tostring(self.root, encoding='utf-8')

if __name__ == '__main__':
    items = [
             {'musicid':'DNPRNPNPNPN',
              'musiclibrary':'DMA',
              'duration':2.0}
            ]
    gb = GluonBuilder('DNPR630009AA', items)
    r = gb.build()
    print r
            


