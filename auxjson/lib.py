#!/usr/bin/env python
#-*- encoding: utf8 -*-
# This file is part of odometer by Håvard Gulldahl <havard.gulldahl@nrk.no>
# (C) 2011-2012
#

import urllib
import lxml.html

URL='http://search.auxmp.com/search/html/list_rep.php?'

def iterReportoire():
    html = lxml.html.parse(URL)
    for row in html.getroot().find_class('s_t'):
        yield (x.strip() for x in row.text.split('-'))
