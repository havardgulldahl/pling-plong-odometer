#!/bin/bash
# This file is part of odometer by Håvard Gulldahl <havard.gulldahl@nrk.no>
# (C) 2011-2016

function error {
    echo "Plonk! Something went wrong:";
    echo $1;
    exit 1;
}

# building pling plong odometer for mac os x

# some settings
IDENTIFIER=${1:-DEV}; # pass version on cmdline
VERSION=$(date +"%Y-%m-%d")-${IDENTIFIER};
NIB=./resources/qt_menu.nib

echo "Generating version: $VERSION";

# change bulid defaults
sed -i .bk "s/beta=.*/beta=0/" BUILDFLAGS
sed -i .bk "s/releaseCheck=.*/releaseCheck=0/" BUILDFLAGS

echo "$VERSION" > ./VERSIONMAC

# update all generated code

python3 ./buildpyqt.py

# build the castle
echo "Building the app (see build.log)"
#python3 setup.py py2app > build.log || error "py2app failed"
pyinstaller -y pling-plong-odometer.spec || error "pyinstaller failed"

# changing back defaults
sed -i .bk "s/beta=.*/beta=1/" BUILDFLAGS

# add some missing pieces
echo "Adding some extra resources"
cp -r "$NIB" dist/Pling\ Plong\ Odometer.app/Contents/Resources/ || error "Could not copy crucial qt resource"
echo -e "[Paths]\nPlugins = plugins" > dist/Pling\ Plong\ Odometer.app/Contents/Resources/qt.conf

# rename to maximase brand name exposure (badges to come!)
mv "dist/Pling Plong Odometer.app" "dist/♫ ♪ Odometer.app"

#TODO: add to Info.plist
#
#               'CFBundleDocumentTypes': [{
#                    # https://developer.apple.com/library/content/documentation/General/Reference/InfoPlistKeyReference/Articles/CoreFoundationKeys.html#//apple_ref/doc/uid/20001431-101685
#                    'CFBundleTypeRole': 'Viewer',
#                    'CFBundleTypeMIMETypes': ['text/xml', 'application/xml'],
#                    'CFBundleTypeExtensions': ['xml',],
#                }]

# create dmg images since all mac heads like to mount archives
echo "Creating dmg image"
DMGNAME=pling-plong-odometer-$VERSION.dmg
test -f "$DMGNAME" && rm -f "$DMGNAME"; # remove old build
hdiutil create "$DMGNAME" -volname "♫ ♪ Odometer $IDENTIFIER" -fs "HFS+" -srcfolder "dist/" || error "Failed to create dmg"

# create pkg
#echo "Creating .pkg installer";
#./macromanconv.py ABOUT build/ABOUT.txt
#/usr/local/bin/packagesbuild -v Odometer.pkgproj || error "Packagemaker failed";

echo "Finished. Take a look at $DMGNAME"
echo "Installer in dist/";
