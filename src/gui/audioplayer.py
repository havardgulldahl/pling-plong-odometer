#-*- encoding: utf8 -*-
# This file is part of odometer by Håvard Gulldahl <havard.gulldahl@nrk.no>
# (C) 2011
# This file incorporates code from the pyqt qmusicplayer.py example, which 
# carries the following license header
##
## Copyright (C) 2010 Riverbank Computing Limited.
## Copyright (C) 2010 Nokia Corporation and/or its subsidiary(-ies).
## All rights reserved.
##
## This file is part of the examples of PyQt.
##
## $QT_BEGIN_LICENSE:BSD$
## You may use this file under the terms of the BSD license as follows:
##
## "Redistribution and use in source and binary forms, with or without
## modification, are permitted provided that the following conditions are
## met:
##   * Redistributions of source code must retain the above copyright
##     notice, this list of conditions and the following disclaimer.
##   * Redistributions in binary form must reproduce the above copyright
##     notice, this list of conditions and the following disclaimer in
##     the documentation and/or other materials provided with the
##     distribution.
##   * Neither the name of Nokia Corporation and its Subsidiary(-ies) nor
##     the names of its contributors may be used to endorse or promote
##     products derived from this software without specific prior written
##     permission.
##
## THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
## "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
## LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
## A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
## OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
## SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
## LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
## DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
## THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
## (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
## OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE."
## $QT_END_LICENSE$
##

# 

import os.path
import PyQt4.QtCore as Core
from PyQt4.phonon import Phonon

class AudioPlayer(Core.QObject):
    error = Core.pyqtSignal(unicode, name="error")

    def __init__(self):
        super(Core.QObject, self).__init__()
        self.audioOutput = Phonon.AudioOutput(Phonon.MusicCategory, self)
        self.mediaObject = Phonon.MediaObject(self)
        #self.metaInformationResolver = Phonon.MediaObject(self)

        self.mediaObject.setTickInterval(1000)

        self.mediaObject.tick.connect(self.tick)
        #self.mediaObject.stateChanged.connect(self.stateChanged)
        #self.metaInformationResolver.stateChanged.connect(self.metaStateChanged)
        #self.mediaObject.aboutToFinish.connect(self.aboutToFinish)

        Phonon.createPath(self.mediaObject, self.audioOutput)
        
    def play(self, filename, extract=20):
        if not os.path.exists(filename):
            self.error.emit("Path does not exist: %s" % filename)
            return False

        self.timeout = extract
        self.mediaObject.stop()
        self.mediaObject.clearQueue()
        self.mediaObject.setCurrentSource(filename)
        print "palaying: ", filename, " for duration_: ", extract
        self.mediaObject.play()

    def stop(self):
        self.mediaObject.stop()

    def tick(self, time):
        print "tick:", time
        if time/1000 > self.timeout:
            print " finish playing, timeout reached"
            self.stop()

if __name__ == '__main__':
    import sys
    player = AudioPlayer()
    player.play(sys.argv[1])
