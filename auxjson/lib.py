#-*- encoding: utf8 -*-
# This file is part of odometer by Håvard Gulldahl <havard.gulldahl@nrk.no>
# (C) 2011-2012
#

import lxml.html

URL='http://search.auxmp.com/search/html/list_rep.php?'

def iterRepertoire():
    html = lxml.html.parse(URL)
    for row in html.getroot().find_class('s_t'):
        title, shorts = (x.strip() for x in row.text.split('-'))
        for short in [x.strip()[:4] for x in shorts.split(',')]:
            yield (short, title)

if __name__ == '__main__':
    for title, short in iterRepertoire():
        print short, " -> ", title
