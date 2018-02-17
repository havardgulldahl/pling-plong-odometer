#-*- encoding: utf-8 -*-

# snippet to fetch help text online

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
        for _prefix in [x.strip()[:4] for x in _sh.split(',')]:
            _short.append(_prefix)
            print("""'%s': '%s', """ % (_prefix, _rep))

    print('\n\n%s' % _short)





