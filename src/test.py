#!/usr/bin/env python
#-*- encoding: utf8 -*-

import xmeml


def main(fcpfile):
    v = xmeml.VideoSequence(file=fcpfile)
    audioclips = {}
    for c in v.track_items:
        if c.id is None or c.type != 'clipitem' or c.mediatype != 'audio': continue
        if not c.name.startswith("SCD"): continue
        #print "\_ %s (NTSC: %s, timebase: %s)" % (c.name, c.ntsc, c.timebase)
        #print "    - duration: %s - in: %s - out: %s - start: %s - end: %s" % \
             #(c.duration, c.in_frame, c.out_frame, c.start_frame, c.end_frame)
        #continue
        if not audioclips.has_key(c.file): 
            audioclips[c.file] = [c,]
        else:
            audioclips[c.file] += [c,]
                                
    for audioclip, pieces in audioclips.iteritems():
        length = 12.2
        a = []
        for subclip in pieces:
            a += subclip.audibleframes()
        r = []
        start, end = a[0]
        for (s, e) in a[1:]: 
            if s < end and s > start and e > end:
                end = e
            elif s > end: 
                r.append( (start, end) )
                start = s
                end = e 
        r.append( (start, end) )
        frames = sum( o-i for (i,o) in r )
        secs = frames  / audioclip.rate
        print audioclip.name, a, r, frames, secs

    return
        ##for f in c.filters:
            #print "    \_ %s" % f.name
            #if f.id != "audiolevels": continue
            #for param in f.parameters: 
                #if param.values: 
                    #print "        - %s (%s - %s) = %.1f -> %s" % (param.id, param.min, param.max, audiblesecs(c, param.values), param.values)
                #elif param.value:
                    #print "        - %s (%s - %s) = %.1f -> %s" % (param.id, param.min, param.max, audiblesecs(c, param.value), param.value)
                
        
def audibleframes(clipitem, threshold=0.1):
    "Returns list of (start, end) pairs of audible chunks"
    f = []
    audiolevels = clipitem.getfilter('audiolevels')
    print audiolevels
    if isinstance(audiolevels, basestring): # single value = single level for whole clip
        if(float(audiolevels) > threshold):
            return [(clipitem.start(), clipitem.end()),]
    else: # audiolevels is a list of (keyframe, level) tuples
        keyframelist = audiolevels[:]
        # add the (implicit) keyframe end point
        keyframelist += (clipitem.duration, keyframelist[-1][1]),    
        #prevframe = float(clipitem.start())
        prevframe = 0.0
        thisvolume = 0.0
        audible = False
        for keyframe, volume in keyframelist:
            thisframe = prevframe+float(keyframe)
            thisvolume = float(volume) 
            if thisvolume > threshold:
                if audible is True: continue
                audible = True
            else: 
                # level is below threshold, write out range so far
                if audible is False: continue
                audible = False
                f.append( (prevframe, thisframe) )
    return f
            

def audiblesecs(clipitem, values, threshold=0.1):
    secs = 0.0
    prev = 0.0
    if isinstance(values, basestring): # single value for whole clipitem
        if float(values) > threshold:
            secs = float(clipitem.duration) / clipitem.timebase
    else: # a list of keyframes and respective volume level
        # add the (implicit) keyframe end point
        keyframelist = values[:]
        keyframelist += (clipitem.duration, values[-1][1]),    
        for keyframe, volume in keyframelist:
            if float(volume) < threshold: continue
            secs += (float(keyframe) - prev) / clipitem.timebase
            prev = float(keyframe)
    return secs

if __name__ == '__main__':
    import sys, os.path
    f = sys.argv[1]
    if os.path.exists(f):
        main(os.path.realpath(f))

