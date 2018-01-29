#!/bin/bash

# deploy latest odometer

cd /tmp;

#1
# get latest release
echo "Get latest release from Github.";

LATEST=$(curl -s https://api.github.com/repos/havardgulldahl/pling-plong-odometer/releases/latest \
    | grep tarball_url \
    | cut -d '"' -f 4);

VERSION=$(basename "$LATEST");
echo "got $LATEST -> $VERSION";
curl -L -o "${VERSION}.tar" "$LATEST" && echo "Downloaded $VERSION";

OUTPUT=/tmp;
echo "Unwrap into ${OUTPUT}/$VERSION";

mkdir -p "$OUTPUT/$VERSION";
tar -xvf "$VERSION.tar" --strip 1 -C "${OUTPUT}/${VERSION}" && echo "unpacked";

echo "Setting up zymlink"

ln -sf ${OUTPUT}/$VERSION ${OUTPUT}/latest;

echo "restarting odometer server with new version";

#systemctl restart odometer@{1..2} && "Running version $LATEST";
