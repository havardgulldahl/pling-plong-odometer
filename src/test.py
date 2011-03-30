#!/usr/bin/env python
#-*- encoding: utf8 -*-

import xmeml


def main(fcpfile):
  v = xmeml.VideoSequence(file=fcpfile)
  for c in v.track_items:
    if c.id is None or c.type != 'clipitem' or c.mediatype != 'audio': continue
    if not c.name.startswith("SCD"): continue
    print "\_ %s (NTSC: %s, timebase: %s)" % (c.name, c.ntsc, c.timebase)
    print "  - duration: %s - in: %s - out: %s - start: %s - end: %s" % \
       (c.duration, c.in_frame, c.out_frame, c.start_frame, c.end_frame)
    #continue
    for f in c.filters:
      print "  \_ %s" % f.name
      if f.id != "audiolevels": continue
      for param in f.parameters: 
        if param.values: 
          print "    - %s (%s - %s) = %.1f -> %s" % (param.id, param.min, param.max, audiblesecs(c, param.values), param.values)
        elif param.value:
          print "    - %s (%s - %s) = %.1f -> %s" % (param.id, param.min, param.max, audiblesecs(c, param.value), param.value)
        
    
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

