#!/usr/bin/env python
#-*- encoding: utf8 -*-

import xmeml

def f3(seq): 
    # Not order preserving 
    keys = {} 
    for e in seq: 
        keys[e] = 1 
    return keys.keys()

def main(fcpfile):
    v = xmeml.VideoSequence(file=fcpfile)
    audioclips = {}
    for c in v.track_items:
        if not ( c.type == 'clipitem' and c.file.mediatype == 'audio' ): continue
        #print "\_ %s (NTSC: %s, timebase: %s)" % (c.name, c.ntsc, c.timebase)
        #print "    - duration: %s - in: %s - out: %s - start: %s - end: %s" % \
             #(c.duration, c.in_frame, c.out_frame, c.start_frame, c.end_frame)
        #continue
        if not audioclips.has_key(c.file): 
            audioclips[c.file] = [c,]
        else:
            audioclips[c.file] += [c,]
                                
    for audioclip, pieces in audioclips.iteritems():
        a = []
        for subclip in pieces:
            a += subclip.audibleframes()
        aa = f3(a)
        aa.sort()
        r = []
        start, end = aa[0]
        for (s, e) in aa[1:]: 
            if s < end and s > start and e > end:
                end = e
            elif s == end:
                end = e
            elif (s > end or e < start): 
                r.append( (start, end) )
                start = s
                end = e 
            elif (e > start and e < end and s < start) or e == start:
                start = s
        r.append( (start, end) )
        frames = sum( o-i for (i,o) in r )
        secs = frames  / audioclip.rate
        print audioclip.name, aa, r, frames, secs

    return
        ##for f in c.filters:
            #print "    \_ %s" % f.name
            #if f.id != "audiolevels": continue
            #for param in f.parameters: 
                #if param.values: 
                    #print "        - %s (%s - %s) = %.1f -> %s" % (param.id, param.min, param.max, audiblesecs(c, param.values), param.values)
                #elif param.value:
                    #print "        - %s (%s - %s) = %.1f -> %s" % (param.id, param.min, param.max, audiblesecs(c, param.value), param.value)
                
        
if __name__ == '__main__':
    import sys, os.path
    #f = sys.argv[1]
    #if os.path.exists(f):
        #main(os.path.realpath(f))
    #print xmeml.Volume(gain=0.001).decibel
    #print xmeml.Volume(gain=3.98).decibel
    #print xmeml.Volume(decibel=-26).gain

    import metadata
    from metadata import gluon
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
    gb = gluon.GluonBuilder('DNPR630009AA', items)
    print gb.toxml()
    #gp = gluon.GluonParser()
    #x = gp.parse(sys.argv[1])
            





