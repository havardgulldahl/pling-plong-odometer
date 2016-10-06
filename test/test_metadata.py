# encoding: utf-8
# tests of metadata resolvers

import sys
import logging
import os.path
import pytest
from PyQt4 import QtCore, QtGui

import metadata
from metadata.resolvers import DMAResolver, AUXResolver, ApollomusicResolver, UprightmusicResolver, UniPPMResolver, ExtremeMusicResolver
from metadata.login import ProviderLogin

log = logging.getLogger('test_metadata')
log.setLevel(logging.WARNING)

logincookies = {}

def setup_module(module):
    def loggedin(provider, cookie):
        module.logincookies[provider] = cookie

    for a in ['EXTREME', 'UNIPPM', 'UPRIGHT', 'APOLLO', 'AUX']:
        login = ProviderLogin(a)
        login.loginSuccess.connect(lambda c: loggedin(a, c))
        login.error.connect(lambda s: log.warning(s))
        login.loginWithCachedPasswords()

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
    log.warning('cookies: %r', logincookies)
    app = QtGui.QApplication([])
    for musicid, filename in xmemlfiles['EXTREME'].iteritems():
        resolver = ExtremeMusicResolver()
        resolver.setlogincookie(logincookies['EXTREME'])
        assert _resolvertest(qtbot, resolver, musicid, filename)
    app.deleteLater()
    app.exit()

def test_resolver_unippm(qtbot, xmemlfiles):
    app = QtGui.QApplication([])
    for musicid, filename in xmemlfiles['UNIPPM'].iteritems():
        resolver = UniPPMResolver()
        resolver.setlogincookie(logincookies['UNIPPM'])
        assert _resolvertest(qtbot, resolver, musicid, filename)
    app.deleteLater()
    app.exit()

def test_resolver_upright(qtbot, xmemlfiles):
    app = QtGui.QApplication([])
    for musicid, filename in xmemlfiles['UPRIGHT'].iteritems():
        resolver = UprightmusicResolver()
        resolver.setlogincookie(logincookies['UPRIGHT'])
        assert _resolvertest(qtbot, resolver, musicid, filename)
    app.deleteLater()
    app.exit()

def test_resolver_apollo(qtbot, xmemlfiles):
    app = QtGui.QApplication([])
    for musicid, filename in xmemlfiles['APOLLO'].iteritems():
        resolver = ApollomusicResolver()
        resolver.setlogincookie(logincookies['APOLLO'])
        assert _resolvertest(qtbot, resolver, musicid, filename)
    app.deleteLater()
    app.exit()

def test_resolver_aux(qtbot, xmemlfiles):
    app = QtGui.QApplication([])
    for musicid, filename in xmemlfiles['AUX'].iteritems():
        resolver = AUXResolver()
        resolver.setlogincookie(logincookies['AUX'])
        assert _resolvertest(qtbot, resolver, musicid, filename)
    app.deleteLater()
    app.exit()

def test_resolver_dma(qtbot, xmemlfiles):
    app = QtGui.QApplication([])
    for musicid, filename in xmemlfiles['DMA'].iteritems():
        assert _resolvertest(qtbot, DMAResolver(), musicid, filename)
    app.deleteLater()
    app.exit()

