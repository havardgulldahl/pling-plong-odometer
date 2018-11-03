#-*- encoding: utf-8 -*-

# snippet to fetch fono members from https://www.fono.no/medlemmene/

import sys
from urllib.request import urlopen
import lxml.html

URL='http://www.ifpi.no/ifpi-norge/ifpi-medlemmer'

def iterMembers():
    html = lxml.html.parse(urlopen(URL))
    for row in html.getroot().xpath("//div[@itemtype='https://schema.org/BlogPosting']//p/strong"): 
        txt = row.text_content().strip()
        if txt.endswith(' AS'): # normalize without corporate suffix
            yield txt[:-3]
        else:
            yield txt


if __name__ == '__main__':
    print("BEGIN;")
    print("DELETE FROM license_rule WHERE source='IFPI medlem' AND license_property='label';")
    for r in iterMembers():
        print("""INSERT INTO license_rule 
                (source, license_property, license_status, license_value, comment)
                VALUES 
                ('IFPI medlem', 'label', 'OK', '{}', '{}');""".format(r, URL))
    print("COMMIT;")
    print('-- Tip:  Pipe this to `| ( sudo su postgres -c "psql odometer" )')







