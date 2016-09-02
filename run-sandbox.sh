#!/usr/bin/env bash

export X=$PATH;

PROG="${1:-dist/♫ ♪ Odometer.app/Contents/MacOS/Pling Plong Odometer}";

sandbox-exec -f odometer-sandbox.sb "${PROG}";

