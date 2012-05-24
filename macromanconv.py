#!/usr/bin/env python
#-*- enc: utf-8 -*-

import codecs

def cnv(infile, outfile):
    f = codecs.open(infile, encoding='utf-8')
    w = codecs.getwriter('macroman')(file(outfile, 'wb'))
    xx = f.read().replace(u'\u266b', 'Pling').replace(u'\u266a', 'Plong').replace(u'\u272a', '').replace(u'\u2606', 'o').replace(u'\u2014', '-')
    w.write(xx)
    w.close()

if __name__ == '__main__':
    import sys
    cnv(sys.argv[1], sys.argv[2])

