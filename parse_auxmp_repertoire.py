#!/usr/bin/env python2.7
#-*- encoding: utf-8 -*-

# snippet to fetch all catalogues and their prefixes from auxmp.com

import urllib
import sys
import lxml.html

URL='http://search.auxmp.com/search/html/list_rep.php?'

def iterReportoire():
    html = lxml.html.parse(URL)
    for row in html.getroot().find_class('s_t'):
        yield (x.strip() for x in row.text.split('-'))




if __name__ == '__main__':
    _short = []
    for _rep, _sh in iterReportoire():
        _short.append(_sh)
        print """'%s': '%s', """ % (_sh, _rep)

    print '\n\n%s' % _short





