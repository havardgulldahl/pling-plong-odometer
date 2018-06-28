#-*- encoding: utf-8 -*-

# snippet to fetch fono members from https://www.fono.no/medlemmene/

import sys
from urllib.request import urlopen
import lxml.html

URL='https://www.fono.no/medlemmene/'

def iterMembers():
    html = lxml.html.parse(urlopen(URL))
    for row in html.getroot().xpath("//div[@class='members']//a"): #cssselect(".members li a"):
        txt = row.text_content().strip()
        yield txt
        if txt.lower().endswith(' AS'): # also add item without AS suffix
            yield txt[:-3]

if __name__ == '__main__':
    print("BEGIN;")
    print("DELETE FROM license_rule WHERE source='FONO' AND license_property='label';")
    for r in iterMembers():
        print("""INSERT INTO license_rule 
                (source, license_property, license_status, license_value, comment)
                VALUES 
                ('FONO', 'label', 'green', '{}', '{}');""".format(r, URL))
    print("COMMIT;")






