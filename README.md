# Pling Plong Odometer #

### keeping track of what goes into your sound track ###

This tool will analyze your FCP project and tell you what
audio clips goes in it and for how long each clip is audible.

Created by *havard.gulldahl@nrk.no*


## Build prerequisites ##

* Python 2.7
* python-demjson
* hachoir-metadata
* pyqt4
* python-hashlib
* https://github.com/havardgulldahl/xmeml
* lxml

# Build deps #

### OSX ###

* `Packages` for packaging (http://s.sudre.free.fr/Software/Packages/about.html)
* lxml needs static dependencies to work smoothly on all osx versions:


```
#!bash

STATIC_DEPS=true pip install lxml
```
