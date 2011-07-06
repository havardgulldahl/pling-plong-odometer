#-*- encoding: utf8 -*-
# This file is part of odometer by Håvard Gulldahl <havard.gulldahl@nrk.no>
# (C) 2011

import json
import urllib
import urllib2
import wave
from cStringIO import StringIO
        
def echonest(audiodata):
    # http://developer.echonest.com/docs/v4/track.html#upload
    # get 30" audio from filename
    # submit it to echonest:
    # curl -F "api_key=JNMMQ1SOMJ64AR4ES" -F "filetype=wav" -F "track=@audio.wav" "http://developer.echonest.com/api/v4/track/upload"
    # read json result
    url = "http://developer.echonest.com/api/v4/track/upload"
    data = ( ('api_key', 'JNMMQ1SOMJ64AR4ES'),
              ('filetype', 'wav'),
              #('track', open(filename)),
             )
    req = urllib2.Request(url+'?'+urllib.urlencode(data), audiodata.getvalue())
    print req.get_full_url()
    req.add_header('Content-type', 'application/octet-stream')
    conn = urllib2.urlopen(req)
    data = conn.read()
    return json.loads(data)

def shrinkwav(filename):
    out = StringIO()
    samplelen = 30
    inn = wave.open(filename)
    ut = wave.open(out, 'wb')
    ut.setparams(inn.getparams())
    sample = inn.readframes(samplelen*inn.getframerate())
    inn.close()
    ut.writeframes(sample)
    return out


def identify(filename):
    return echonest(shrinkwav(filename))

if __name__ == '__main__':
    import sys
    w = shrinkwav(sys.argv[1])
    print identify(sys.argv[1])
