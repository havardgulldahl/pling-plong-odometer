# encoding: utf-8
# tests of metadata resolvers

import sys
import logging
import os.path
import pytest
from PyQt4 import QtCore, QtGui

import metadata
from metadata.resolvers import DMAResolver, AUXResolver, ApollomusicResolver, UprightmusicResolver, UniPPMResolver

log = logging.getLogger('test_metadata')


def test_musicids(xmemlfiles):
    for _resolvername, data in xmemlfiles.iteritems():
        if _resolvername == 'DMA':
            resolver = DMAResolver
        elif _resolvername == 'AUX':
            resolver = AUXResolver
        elif _resolvername == 'APOLLO':
            resolver = ApollomusicResolver
        elif _resolvername == 'UPRIGHT':
            resolver = UprightmusicResolver
        elif _resolvername == 'UNIPPM':
            resolver = UniPPMResolver
        for musicid, filename in data.iteritems():
            log.warning(musicid)
            assert resolver.musicid(filename) == musicid

def test_resolvers(qtbot, xmemlfiles):
    app = QtGui.QApplication([])
    for _resolvername, data in xmemlfiles.iteritems():
        if _resolvername == 'DMA':
            resolver = DMAResolver()
        elif _resolvername == 'AUX':
            resolver = AUXResolver()
        elif _resolvername == 'APOLLO':
            resolver = ApollomusicResolver()
        elif _resolvername == 'UPRIGHT':
            resolver = UprightmusicResolver()
        elif _resolvername == 'UNIPPM':
            resolver = UniPPMResolver()
        for musicid, filename in data.iteritems():
            # Watch for the app.worker.finished signal, then start the worker.
            with qtbot.waitSignal(resolver.trackResolved, timeout=10000) as blocker:
                blocker.connect(resolver.trackFailed)  # Can add other signals to blocker

                resolver.resolve(filename, os.path.join(".", filename), fromcache=False)
                # Test will block at this point until either the "trackResolved" or the
                # "trackFailed" signal is emitted. If 10 seconds passed without a signal,
                # SignalTimeoutError will be raised.
            # trackResolved returns `tuple(filename, metadata.model.TrackMetadata)`
            # whereas trackFailed returns `tuple(filename)`
            pytest.assume(len(blocker.args) == 2)
            if len(blocker.args) == 1:
                continue
            _filename, _trackmetadata = blocker.args
            pytest.assume(_trackmetadata, metadata.model.TrackMetadata)

    app.deleteLater()
    app.exit()

