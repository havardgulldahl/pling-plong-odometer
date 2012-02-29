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
rm -rf ./build ./dist || error "cleanup failed"

# build the castle
echo "Building the app (see build.log)"
$PYTHON setup.py py2exe > build.log || error "py2exe failed"

# create neat package
BUNDLE=Pling-Plong-Odometer-$VERSION;
SHORTNAME=odometer-$VERSION.exe;
mv dist $BUNDLE;
/c/Programfiler/7-Zip/7z.exe a -r -sfx7z.sfx $SHORTNAME $BUNDLE || error "creating sfx bundle failed";

# publish to dropbox
echo "Publishing to dropbox"
DBURL=$DROPBOXURL/$SHORTNAME;
cp "$SHORTNAME" $HOME/Dropbox/Public/"$SHORTNAME" || error "Copying to dropbox failed"
echo "$VERSION|$DBURL" > $HOME/Dropbox/Public/odometerversion_win.txt

rm -rf ./$BUNDLE;

echo "Finished. Take a look at $SHORTNAME"
echo "Online: $DBURL"; 
