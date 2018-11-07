#!/usr/bin/env python

import sys
from getpass import getpass

# insert IFPI artists and labels that are excluded from use

ARTISTS = [
    'Michael Krohn',
    'Raga Rockers',
    'Kjøtt',
    'Tom Trussel',
    'Mickey Faust',
    'Krohn & Co',
    'Easy Riders',
    'Hellbillies',
    'Karpe Diem',
    'Pink Floyd',
    'Tina Turner',
    'Red Hot Chili Peppers',
    'Led Zeppelin',
    'Madonna',
    'Roxette',
    'R.E.M',
    'The Beatles',
    'Metallica',
    'Abba',
    'U2',
    'Rammstein',
    'Nirvana',
    'Don Henley',
    'Guns\'n\'Roses',
    'Elvis Presley',
    'Bob Dylan',
    'Bruce Springsteen',
    'Kygo',
    'AC/DC',
    'Michael Jackson',
    'Pharell Williams',
    'Adele',
    'Karpe'
]

LABELS = [
    'Beggars Group',
    'Beggars Banquet Records Ltd.', 
    '4AD Ltd', 
    'Rough Trade Records Ltd.',
    'Matador Records', 
    'Young Turks Recordings',
    'Too Pure Records Limited', 
    'Kobalt Music Group',
]

COLUMN_LABEL = 'IFPI reservasjonsliste'

if __name__=='__main__':
    print('-- Tip:  Pipe this to `| ( sudo su postgres -c "psql odometer" )')
    print("-- Updating IFPI exclusion list.\n-- ============ --\n-- {} artist names and {} labels are defined in this script.".format(len(ARTISTS), len(LABELS)), file=sys.stderr)
    if(getpass("-- Type 'y' if you want to replace all existing IFPI exclusion rules in the database").strip().lower() != 'y'):
        print("Aborting, database list not changed.", file=sys.stderr)
        sys.exit()

    print("BEGIN;")
    print("DELETE FROM license_rule WHERE source='{}' AND license_property='artist';".format(COLUMN_LABEL))
    print("DELETE FROM license_rule WHERE source='{}' AND license_property='label';".format(COLUMN_LABEL))
    print("""INSERT INTO license_rule (source, license_property, license_status, license_value)\n
            VALUES \n""")
    rows = []
    for a in ARTISTS:
        rows.append("""('{}', 'artist', 'NO', $odo${}$odo$)""".format(COLUMN_LABEL, a))
    for l in LABELS:
        rows.append("""('{}', 'label', 'NO', $odo${}$odo$)""".format(COLUMN_LABEL, l))
    print(",\n".join(rows) + ";")
    print("COMMIT;")
