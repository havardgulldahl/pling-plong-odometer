#!/bin/bash
# This file is part of odometer by Håvard Gulldahl <havard.gulldahl@nrk.no>
# (C) 2011-2012

function error {
    echo "Plonk! Something went wrong:";
    echo $1;
    exit 1;
}

# building pling plong odometer for mac os x

# some settings

DROPBOXPATH=/Volumes/Media/Dropbox;
DROPBOXURL=http://dl.dropbox.com/u/12128173/Odometer;
VERSION=$(date +"%Y-%m-%d");
#NIB=/Library/Frameworks/QtGui.framework/Versions/4/Resources/qt_menu.nib
NIB=./resources/qt_menu.nib

echo "Generating version: $VERSION";

# change bulid defaults
sed -i .bk "s/beta=.*/beta=0/" BUILDFLAGS
sed -i .bk "s/releaseCheck=.*/releaseCheck=0/" BUILDFLAGS

# update all generated code

echo "Generating translations for UX"
#pylupdate4-2.7r
pylupdate4 src/gui/gui.pro || error "pylupdate failed";
lrelease src/gui/gui.pro || error "lrelease failed";

echo "Generating code for UX"
pyuic4 -o src/gui/odometer_ui.py src/gui/pling-plong-odometer.ui || error "pyuic failed"
pyuic4 -o src/gui/auxreport_ui.py src/gui/pling-plong-auxreport.ui || error "pyuic failed"
pyuic4 -o src/gui/prfreport_ui.py src/gui/pling-plong-prfreport.ui || error "pyuic failed"
pyuic4 -o src/gui/onlinelogin_ui.py src/gui/pling-plong-onlinelogin.ui || error "pyuic failed"

# store settings in files, to be picked up by pyqt resource system
echo "$DROPBOXURL" > ./DROPBOXURL;
echo "$VERSION" > ./VERSIONMAC;
pyrcc4 -o src/gui/odometer_rc.py src/gui/odometer.qrc || error "pyrcc failed"

# clean up old cruft
echo "Removing old code"
rm -rf ./build ./dist ./pling-plong-odometer.dmg || error "cleanup failed"

# update xmeml
(cd ../xmeml && git pull);
cp -fr ../xmeml/xmeml src/ || error "couldnt find xmeml library";

# build the castle
echo "Building the app (see build.log)"
python2.7 setup.py py2app > build.log || error "py2app failed"

# changing back defaults
sed -i .bk "s/beta=.*/beta=1/" BUILDFLAGS
pyrcc4 -o src/gui/odometer_rc.py src/gui/odometer.qrc || error "pyrcc failed"

# add some missing pieces
echo "Adding some extra resources"
cp -r "$NIB" dist/Pling\ Plong\ Odometer.app/Contents/Resources/ || error "Could not copy crucial qt resource"
echo -e "[Paths]\nPlugins = plugins" > dist/Pling\ Plong\ Odometer.app/Contents/Resources/qt.conf

# rename to maximase brand name exposure (badges to come!)
mv "dist/Pling Plong Odometer.app" "dist/♫ ♪ Odometer.app"

# create dmg images since all mac heads like to mount archives
echo "Creating dmg image"
DMGNAME=pling-plong-odometer-$VERSION.dmg
test -f "$DMGNAME" && rm -f "$DMGNAME"; # remove old build
hdiutil create "$DMGNAME" -volname "♫ ♪ Odometer" -fs "HFS+" -srcfolder "dist/" || error "Failed to create dmg"

# create pkg
echo "Creating .pkg installer";
./macromanconv.py ABOUT build/ABOUT.txt
/usr/local/bin/packagesbuild -v Odometer.pkgproj || error "Packagemaker failed";

# create history
git tag -a "v$VERSION-mac" -m "Version $VERSION release" || error "couldnt tag git tree";
git push --tags || error "problems pushing tags to central repository";
git commit ./VERSIONMAC -m "build-mac.sh: commiting new mac version $VERSION" || error "problems pushing changes to central repository";


echo "Finished. Take a look at $DMGNAME"
echo "Installer in dist/";
