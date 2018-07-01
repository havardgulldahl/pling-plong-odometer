#-*- encoding: utf-8 -*-

# snippet to fetch fono members from https://www.fono.no/medlemmene/

import sys
from urllib.request import urlopen
import lxml.html

URL='http://www.ifpi.no/ifpi-norge/ifpi-medlemmer'

def iterMembers():
    html = lxml.html.parse(urlopen(URL))
    for row in html.getroot().xpath("//div[starts-with(@class, 'item')]/div/p/strong/strong"): 
        txt = row.text_content().strip()
        yield txt
        if txt.endswith(' AS'): # also add item without AS suffix
            yield txt[:-3]


if __name__ == '__main__':
    print("BEGIN;")
    print("DELETE FROM license_rule WHERE source='IFPI medlem' AND license_property='label';")
    for r in iterMembers():
        print("""INSERT INTO license_rule 
                (source, license_property, license_status, license_value, comment)
                VALUES 
                ('IFPI medlem', 'label', 'OK', '{}', '{}');""".format(r, URL))
    print("COMMIT;")






