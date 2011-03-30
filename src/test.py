#!/usr/bin/env python
#-*- encoding: utf8 -*-

import xmeml


def main(fcpfile):
  v = xmeml.VideoSequence(file=fcpfile)
  for c in v.track_items:
    if c.id is None or c.type != 'clipitem': continue
    print "\_ %s (NTSC: %s, timebase: %s)" % (c.id, c.ntsc, c.timebase)
    #continue
    for f in c.filters:
      print "  \_ %s" % f.name
      if f.id != "audiolevels": continue
      for param in f.parameters: 
        if param.values: 
          print "    - %s (%s - %s) = %.1f -> %s" % (param.id, param.min, param.max, audiblesecs(param.values), param.values)
        
    
def audiblesecs(keyframelist, timebase=25, threshold=0.1):
  secs = 0.0
  prev = 0.0
  for keyframe, volume in keyframelist:
    if float(volume) < threshold: continue
    secs += (float(keyframe) - prev) / timebase
    prev = float(keyframe)
  return secs

if __name__ == '__main__':
  import sys, os.path
  f = sys.argv[1]
  if os.path.exists(f):
    main(os.path.realpath(f))

