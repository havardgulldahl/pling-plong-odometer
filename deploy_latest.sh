#!/bin/bash

# deploy latest odometer

RESTORE=$(echo -en '\033[0m')
RED=$(echo -en '\033[00;31m')
GREEN=$(echo -en '\033[00;32m')
YELLOW=$(echo -en '\033[00;33m')
BLUE=$(echo -en '\033[00;34m')
MAGENTA=$(echo -en '\033[00;35m')
PURPLE=$(echo -en '\033[00;35m')
CYAN=$(echo -en '\033[00;36m')
LIGHTGRAY=$(echo -en '\033[00;37m')
LRED=$(echo -en '\033[01;31m')
LGREEN=$(echo -en '\033[01;32m')
LYELLOW=$(echo -en '\033[01;33m')
LBLUE=$(echo -en '\033[01;34m')
LMAGENTA=$(echo -en '\033[01;35m')
LPURPLE=$(echo -en '\033[01;35m')
LCYAN=$(echo -en '\033[01;36m')
WHITE=$(echo -en '\033[01;37m')


function result {
    echo ${GREEN}$*${RESTORE};
}

function info {
    echo -n ${MAGENTA}$*... ${RESTORE};
}

function err {
    echo ${RED}$*${RESTORE};
    exit 1;
}

cd /tmp;

info "Get latest release from Github.";

LATEST=$(curl -s https://api.github.com/repos/havardgulldahl/pling-plong-odometer/releases/latest \
    | grep tarball_url \
    | cut -d '"' -f 4);

VERSION=$(basename "$LATEST");
result "got $LATEST -> $VERSION";
curl -s -L -o "${VERSION}.tar" "$LATEST" || err "Could not download latest tar: $LATEST";
result "Downloaded $VERSION";

OUTPUT=/usr/local/odometer;
#OUTPUT=/tmp;
info "Unwrap into ${OUTPUT}/$VERSION";

mkdir -p "$OUTPUT/$VERSION";
tar -xf "$VERSION.tar" --strip 1 -C "${OUTPUT}/${VERSION}" || err "Untarring $VERSION.tar failed";
result "unpacked";

info "Copying config.ini";
CONFIG="${OUTPUT}/latest/src/webapp/config.ini";
cp "${CONFIG}" "${OUTPUT}/${VERSION}/src/webapp/config.ini" || err "Copying config.ini failed";
result "copied";

info "Setting up zymlink";
ln -snf "${OUTPUT}/$VERSION" "${OUTPUT}/latest" || err "Symlinking failed";
result "symlinked";

info "Storing version string";
echo "${VERSION}" > "${OUTPUT}/latest/src/webapp/_VERSION" || err "Storing version failed";
result "stored"

info "You need to update/verify ${CONFIG} before we restart the server:";
cat "${CONFIG}";

read -n 1 -s -r -p "Press any key to start up the new server"

info "Restarting odometer server with new version";
sudo systemctl restart odometer@{1..2} || err "Systemd restart failed";
result "Running version $VERSION";
