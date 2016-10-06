# encoding: utf-8
# tests of metadata resolvers

import sys
import logging
import os.path
import pytest
from PyQt4 import QtCore, QtGui

import metadata
from metadata.resolvers import DMAResolver, AUXResolver, ApollomusicResolver, UprightmusicResolver, UniPPMResolver, ExtremeMusicResolver

log = logging.getLogger('test_metadata')
log.setLevel(logging.WARNING)

def test_musicid_extreme(xmemlfiles):
    for musicid, filename in xmemlfiles['EXTREME'].iteritems():
        log.warning(musicid)
        assert ExtremeMusicResolver.musicid(filename) == musicid

def test_musicid_unippm(xmemlfiles):
    for musicid, filename in xmemlfiles['UNIPPM'].iteritems():
        log.warning(musicid)
        assert UniPPMResolver.musicid(filename) == musicid

def test_musicid_upright(xmemlfiles):
    for musicid, filename in xmemlfiles['UPRIGHT'].iteritems():
        log.warning(musicid)
        assert UprightmusicResolver.musicid(filename) == musicid

def test_musicid_apollo(xmemlfiles):
    for musicid, filename in xmemlfiles['APOLLO'].iteritems():
        log.warning(musicid)
        assert ApollomusicResolver.musicid(filename) == musicid

def test_musicid_aux(xmemlfiles):
    for musicid, filename in xmemlfiles['AUX'].iteritems():
        log.warning(musicid)
        assert AUXResolver.musicid(filename) == musicid

def test_musicid_dma(xmemlfiles):
    for musicid, filename in xmemlfiles['DMA'].iteritems():
        log.warning(musicid)
        assert DMAResolver.musicid(filename) == musicid


def _resolvertest(qt, resolver, musicid, filename):
    def logger(msg):
        log.warning(msg)
    # Watch for the app.worker.finished signal, then start the worker.
    with qt.waitSignal(resolver.trackResolved, timeout=10000) as blocker:
        blocker.connect(resolver.trackFailed)  # Can add other signals to blocker
        resolver.error.connect(logger)

        resolver.resolve(filename, os.path.join(".", filename), fromcache=False)
        # Test will block at this point until either the "trackResolved" or the
        # "trackFailed" signal is emitted. If 10 seconds passed without a signal,
        # SignalTimeoutError will be raised.
    # trackResolved returns `tuple(filename, metadata.model.TrackMetadata)`
    # whereas trackFailed returns `tuple(filename)`
    assert len(blocker.args) == 2 #, msg='%s couldnt resolve %r' % (_resolvername, filename))
    _filename, _trackmetadata = blocker.args
    assert isinstance(_trackmetadata, metadata.model.TrackMetadata) # msg='expectd TrackMetadata() for %r, but got %r' % (musicid, _trackmetadata) )

    assert _trackmetadata.recordnumber == musicid # msg='%s: expected metadata.recordnumber %r from resolver, instead we got %r' % (_resolvername,
    #                                                musicid,
    #                                                _trackmetadata.identifier))
    return True

def test_resolver_extreme(qtbot, xmemlfiles):
    app = QtGui.QApplication([])
    for musicid, filename in xmemlfiles['EXTREME'].iteritems():
        assert _resolvertest(qtbot, ExtremeMusicResolver(), musicid, filename)
    app.deleteLater()
    app.exit()

def test_resolver_unippm(qtbot, xmemlfiles):
    app = QtGui.QApplication([])
    for musicid, filename in xmemlfiles['UNIPPM'].iteritems():
        assert _resolvertest(qtbot, UniPPMResolver(), musicid, filename)
    app.deleteLater()
    app.exit()

def test_resolver_upright(qtbot, xmemlfiles):
    app = QtGui.QApplication([])
    for musicid, filename in xmemlfiles['UPRIGHT'].iteritems():
        assert _resolvertest(qtbot, UprightmusicResolver(), musicid, filename)
    app.deleteLater()
    app.exit()

def test_resolver_apollo(qtbot, xmemlfiles):
    app = QtGui.QApplication([])
    for musicid, filename in xmemlfiles['APOLLO'].iteritems():
        assert _resolvertest(qtbot, ApollomusicResolver(), musicid, filename)
    app.deleteLater()
    app.exit()

def test_resolver_aux(qtbot, xmemlfiles):
    app = QtGui.QApplication([])
    for musicid, filename in xmemlfiles['AUX'].iteritems():
        assert _resolvertest(qtbot, AUXResolver(), musicid, filename)
    app.deleteLater()
    app.exit()

def test_resolver_dma(qtbot, xmemlfiles):
    app = QtGui.QApplication([])
    for musicid, filename in xmemlfiles['DMA'].iteritems():
        assert _resolvertest(qtbot, DMAResolver(), musicid, filename)
    app.deleteLater()
    app.exit()

def xtest_resolvers(qtbot, xmemlfiles):
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
        elif _resolvername == 'EXTREME':
            resolver = ExtremeMusicResolver()
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
            pytest.assume(len(blocker.args) == 2, msg='%s couldnt resolve %r' % (_resolvername, filename))
            if len(blocker.args) == 1:
                continue
            _filename, _trackmetadata = blocker.args
            pytest.assume(isinstance(_trackmetadata, metadata.model.TrackMetadata),
                          msg='expectd TrackMetadata() for %r, but got %r' % (musicid, _trackmetadata) )

            pytest.assume(_trackmetadata.recordnumber == musicid,
                          msg='%s: expected metadata.recordnumber %r from resolver, instead we got %r' % (_resolvername,
                                                                                                         musicid,
                                                                                                         _trackmetadata.identifier))

    app.deleteLater()
    app.exit()

