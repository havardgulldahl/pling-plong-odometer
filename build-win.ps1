#!/bin/bash
# This file is part of odometer by Håvard Gulldahl <havard.gulldahl@nrk.no>
# (C) 2011-2016

function error {
    echo "Plonk! Something went wrong:";
    echo $1;
    exit 1;
}

# building pling plong odometer for windows

  - "%PYTHON% buildpyqt.py"
  #- "%PYTHON% setup.py py2exe"
  - "pyinstaller --path=C:\\Python35\\Lib\\site-packages\\PyQt5\\Qt\\bin -y pling-plong-odometer.spec"
  #- "%PYTHON% dist.py zip"
  - dir dist\
  - "%PYTHON% -m zipfile -c odometer-%APPVEYOR_BUILD_NUMBER%.zip dist/pling-plong-odometer"
# some settings

$PYTHON = "C:/Python35/python.exe"
$PYQTPATH = "/c/Python27/Lib/site-packages/PyQt4"
$VERSION=(Get-Date).Date

# change bulid defaults
sed -i "s/beta=.*/beta=0/" BUILDFLAGS
sed -i "s/releaseCheck=.*/releaseCheck=0/" BUILDFLAGS
sed -i .bk "s/version=.*/version=$VERSION/" BUILDFLAGS

# update all generated code

echo "Generating translations for UX"
#pylupdate4-2.7
$PYQTPATH/pylupdate4.exe src/gui/gui.pro || error "pylupdate failed";
$PYQTPATH/lrelease.exe src/gui/gui.pro || error "lrelease failed";
echo "Generating code for UX"
$PYTHON $PYQTPATH/uic/pyuic.py -o src/gui/odometer_ui.py src/gui/pling-plong-odometer.ui || error "pyuic failed"
$PYTHON $PYQTPATH/uic/pyuic.py -o src/gui/auxreport_ui.py src/gui/pling-plong-auxreport.ui || error "pyuic auxreport failed"
$PYTHON $PYQTPATH/uic/pyuic.py -o src/gui/prfreport_ui.py src/gui/pling-plong-prfreport.ui || error "pyuic prfreport failed"
$PYTHON $PYQTPATH/uic/pyuic.py -o src/gui/onlinelogin_ui.py src/gui/pling-plong-onlinelogin.ui || error "pyuic prfreport failed"

# store settings in files, to be picked up by pyqt resource system
echo "$VERSION" > ./VERSIONWIN;
$PYQTPATH/pyrcc4.exe -py2 -o src/gui/odometer_rc.py src/gui/odometer.qrc || error "pyrcc failed"

# clean up old cruft
echo "Removing old code"
rm -rf ./build ./dist || error "cleanup failed"

# update xmeml
(cd ../xmeml && git pull);
cp -fr ../xmeml/xmeml src/ || error "couldnt find xmeml library";

# build the castle
echo "Building the app (see build.log)"
$PYTHON setup.py py2exe > build.log || error "py2exe failed"

# create neat package
BUNDLE=Pling-Plong-Odometer-$VERSION;
SHORTNAME=odometer-$VERSION.exe;
mv dist $BUNDLE;
/c/Program\ Files/7-Zip/7z.exe a -r -sfx7z.sfx $SHORTNAME $BUNDLE || error "creating sfx bundle failed";

rm -rf ./$BUNDLE;

# create history
git tag -a "v$VERSION-win" -m "Version $VERSION release" || error "couldnt tag git tree";
git push --tags || error "problems pushing tags to central repository";
git commit ./VERSIONWIN -m "build-win.sh: commiting new windows version $VERSION" || error "problems pushing changes to central repository";

# changing back defaults
sed -i "s/beta=.*/beta=1/" BUILDFLAGS
sed -i .bk "s/version=.*/version=1997-12-31/" BUILDFLAGS
$PYQTPATH/pyrcc4.exe -py2 -o src/gui/odometer_rc.py src/gui/odometer.qrc || error "pyrcc failed"

echo "Finished. Take a look at $SHORTNAME"

