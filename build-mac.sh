#!/bin/bash
# This file is part of odometer by Håvard Gulldahl <havard.gulldahl@nrk.no>
# (C) 2011

# building pling plong odometer for mac os x

# update all generated code 

echo "Generating code for UX"
pyuic4-2.7 -o src/gui/odometer_ui.py src/gui/pling-plong-odometer.ui
pyrcc4-2.7 -o src/gui/odometer_rc.py src/gui/odometer.qrc

# something for translations?

# clean up old cruft
echo "Removing old code"
rm -rf ./build ./dist ./pling-plong-odometer.dmg

# build the castle
echo "Building the app (see build.log)"
python2.7 setup.py py2app > build.log

# add some missing pieces
echo "Adding some extra resources"
cp -r /opt/local/lib/Resources/qt_menu.nib dist/Pling\ Plong\ Odometer.app/Contents/Resources/
echo -e "[Paths]\nPlugins = plugins" > dist/Pling\ Plong\ Odometer.app/Contents/Resources/qt.conf

# rename to maximase brand name exposure (badges to come!)
mv "dist/Pling Plong Odometer.app" "dist/♫ ♪ Odometer.app"

# finally, create dmg images since all mac heads like to mount archives
echo "Creating dmg image"
hdiutil create pling-plong-odometer.dmg -volname "♫ ♪ Odometer" -fs "HFS+" -srcfolder "dist/"

echo "Finished. Take a look at pling-plong-odometer.dmg"
