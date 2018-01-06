#!/bin/bash

pyenv activate pling-plong-odometer

cd src/webapp;

python3 ./app.py $*
