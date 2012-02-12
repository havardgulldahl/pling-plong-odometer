#!/bin/bash
# This file is part of odometer by Håvard Gulldahl <havard.gulldahl@nrk.no>
# (C) 2011

function error {
    echo "Plonk! Something went wrong:";
    echo $1;
    exit 1;
}

# building pling plong odometer for mac os x

# some settings

DROPBOXURL=http://dl.dropbox.com/u/12128173;
VERSION=$(date +"%Y-%m-%d");

# update all generated code 

echo "Generating code for UX"
pyuic4-2.7 -o src/gui/odometer_ui.py src/gui/pling-plong-odometer.ui || error "pyuic failed"

# store settings in files, to be picked up by pyqt resource system
echo "$DROPBOXURL" > ./DROPBOXURL;
echo "$VERSION" > ./VERSIONMAC;
pyrcc4-2.7 -o src/gui/odometer_rc.py src/gui/odometer.qrc || error "pyrcc failed"

# something for translations?

# clean up old cruft
echo "Removing old code"
rm -rf ./build ./dist ./pling-plong-odometer.dmg || error "cleanup failed"

# build the castle
echo "Building the app (see build.log)"
python2.7 setup.py py2app > build.log || error "py2app failed"

# add some missing pieces
echo "Adding some extra resources"
cp -r /opt/local/lib/Resources/qt_menu.nib dist/Pling\ Plong\ Odometer.app/Contents/Resources/ || error "Could not copy crucial qt resource"
echo -e "[Paths]\nPlugins = plugins" > dist/Pling\ Plong\ Odometer.app/Contents/Resources/qt.conf

# rename to maximase brand name exposure (badges to come!)
mv "dist/Pling Plong Odometer.app" "dist/♫ ♪ Odometer.app"

# create dmg images since all mac heads like to mount archives
echo "Creating dmg image"
DMGNAME=pling-plong-odometer-$VERSION.dmg 
hdiutil create "$DMGNAME" -volname "♫ ♪ Odometer" -fs "HFS+" -srcfolder "dist/" || error "Failed to create dmg"

# publish to dropbox
echo "Publishing to dropbox"
DMGURL=$DROPBOXURL/$DMGNAME;
cp "$DMGNAME" $HOME/Dropbox/Public/"$DMGNAME" || error "Copying to dropbox failed"
echo "$VERSION|$DMGURL" > $HOME/Dropbox/Public/odometerversion_mac.txt

echo "Finished. Take a look at $DMGNAME"
echo "Online: $DMGURL"; 
