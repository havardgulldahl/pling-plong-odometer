#!/bin/bash

# deploy latest odometer

cd /tmp;

#1
# get latest release
echo "Get latest release from Github.";

LATEST=$(curl -s https://api.github.com/repos/havardgulldahl/pling-plong-odometer/releases/latest \
    | grep zipball_url \
    | cut -d '"' -f 4);

VERSION=$(basename "$LATEST");
curl -O "$LATEST" && echo "Downloaded $VERSION";

echo "Unwrap into /usr/local";

unzip "$VERSION" -d "/tmp" && "unpacked";

echo "Setting up zymlink"

ln -sf /tmp/latest /tmp/"$LATEST";

echo "restarting odometer server with new version";

#systemctl restart odometer@{1..2} && "Running version $LATEST";
