#!/bin/bash
# This file is part of odometer by Håvard Gulldahl <havard.gulldahl@nrk.no>
# (C) 2011-2012

function error {
    echo "Plonk! Something went wrong:";
    echo $1;
    exit 1;
}

# building pling plong odometer for win32

# some settings

PYTHON="/c/Python27/python.exe"
PYQTPATH="/c/Python27/Lib/site-packages/PyQt4"
DROPBOXURL=http://dl.dropbox.com/u/12128173;
VERSION=$(date +"%Y-%m-%d");

# update all generated code 

echo "Generating translations for UX"
#pylupdate4-2.7
$PYQTPATH/pylupdate4.exe src/gui/gui.pro || error "pylupdate failed";
$PYQTPATH/lrelease.exe src/gui/gui.pro || error "lrelease failed";
echo "Generating code for UX"
$PYTHON $PYQTPATH/uic/pyuic.py -o src/gui/odometer_ui.py src/gui/pling-plong-odometer.ui || error "pyuic failed"
$PYTHON $PYQTPATH/uic/pyuic.py -o src/gui/auxreport_ui.py src/gui/pling-plong-auxreport.ui || error "pyuic auxreport failed"
$PYTHON $PYQTPATH/uic/pyuic.py -o src/gui/prfreport_ui.py src/gui/pling-plong-prfreport.ui || error "pyuic prfreport failed"

# store settings in files, to be picked up by pyqt resource system
echo "$DROPBOXURL" > ./DROPBOXURL;
echo "$VERSION" > ./VERSIONWIN;
git commit ./VERSIONWIN -m "build-win.sh: commiting new version $VERSION"
$PYQTPATH/pyrcc4.exe -py2 -o src/gui/odometer_rc.py src/gui/odometer.qrc || error "pyrcc failed"



# clean up old cruft
echo "Removing old code"
rm -rf ./build ./dist ./pling-plong-odometer.dmg || error "cleanup failed"

# build the castle
echo "Building the app (see build.log)"
$PYTHON setup.py py2exe > build.log || error "py2exe failed"

exit;

# add some missing pieces
#echo "Adding some extra resources"
#cp -r /opt/local/lib/Resources/qt_menu.nib dist/Pling\ Plong\ Odometer.app/Contents/Resources/ || error "Could not copy crucial qt resource"
#echo -e "[Paths]\nPlugins = plugins" > dist/Pling\ Plong\ Odometer.app/Contents/Resources/qt.conf

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
