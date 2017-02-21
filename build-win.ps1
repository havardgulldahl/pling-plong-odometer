# This file is part of odometer by Håvard Gulldahl <havard.gulldahl@nrk.no>
# (C) 2011-2017

# building pling plong odometer for windows

$PYTHON = "C:/Python35/python.exe"
$VERSION = Get-Date -format yyyy-MM-dd

# change bulid defaults
#sed -i "s/beta=.*/beta=0/" BUILDFLAGS
#sed -i .bk "s/version=.*/version=$VERSION/" BUILDFLAGS
(Get-Content BUILDFLAGS) -replace "beta=.*", "beta=0" | Set-Content BUILDFLAGS
(Get-Content BUILDFLAGS) -replace "version=.*", "version=$VERSION" | Set-Content BUILDFLAGS

# update all generated code
Write-Host "Generate python code"
& $PYTHON buildpyqt.py

# build the castle
Write-Host "Building the app (see build.log)"
& pyinstaller -y pling-plong-odometer.spec

# create neat package
Write-Host "Creating package"
if ($APPVEYOR_BUILD_NUMBER -ne $null) {
    $NO=$APPVEYOR_BUILD_NUMBER
} else {
    $NO=$VERSION
}
$SHORTNAME = "odometer-$NO"
#/c/Program\ Files/7-Zip/7z.exe a -r -sfx7z.sfx $SHORTNAME $BUNDLE || error "creating sfx bundle failed";
& $PYTHON -m zipfile -c $SHORTNAME.zip dist/pling-plong-odometer

# create history
#git tag -a "v$VERSION-win" -m "Version $VERSION release" || error "couldnt tag git tree";
#git push --tags || error "problems pushing tags to central repository";
#git commit ./VERSIONWIN -m "build-win.sh: commiting new windows version $VERSION" || error "problems pushing changes to central repository";

# changing back defaults
#sed -i "s/beta=.*/beta=1/" BUILDFLAGS
#sed -i .bk "s/version=.*/version=1997-12-31/" BUILDFLAGS

Write-Host "Finished. Take a look at $SHORTNAME"
