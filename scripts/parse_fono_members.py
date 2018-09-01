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
        suburl = row.attrib.get("href")
        #print("url: {}{}".format(URL, suburl))
        sub = lxml.html.parse(urlopen(URL+suburl))
        for subrow in sub.getroot().xpath("//main/ul/li/a"):
            subtxt = subrow.text_content().strip()
            if len(subtxt):
                yield subtxt

if __name__ == '__main__':

    print("BEGIN;")
    print("DELETE FROM license_rule WHERE source='FONO medlem' AND license_property='label';")
    for r in iterMembers():
        print("""INSERT INTO license_rule 
                (source, license_property, license_status, license_value, comment)
                VALUES 
                ('FONO medlem', 'label', 'OK', '{}', '{}');""".format(r, URL))
    print("COMMIT;")
    print("-- Tip: Pipe this to `psql odometer`")






