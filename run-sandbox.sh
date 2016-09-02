#!/usr/bin/env bash

export PATH=/usr/bin:/bin:/usr/sbin:/sbin;

PROG="${1:-dist/♫ ♪ Odometer.app/Contents/MacOS/Pling Plong Odometer}";

sandbox-exec -f odometer-sandbox.sb "${PROG}";

