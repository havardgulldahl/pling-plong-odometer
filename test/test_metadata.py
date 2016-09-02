
import metadata
from metadata.resolvers import DMAResolver, AUXResolver

def test_resolveDMA():
    _filenames = {"NONRO716733SG0201": "NONRO716733SG0201 Ofelastema.wav",
                  "NONRO174537CD0001": "NONRO174537CD0001 Klaverkonsert, op. 16, a-moll_ 1. sats. Alleg.wav",
                  "NONRE643326HD0001": "NONRE643326HD0001 Panda.wav",
                  "NONRO306374CS0002": "NONRO306374CS0002 Phone Tap (Instrumental).wav",
                  "NONRE643326LP0001": "NONRE643326LP0001 Panda.wav",}

    for musicid, filename in _filenames.iteritems():
        assert DMAResolver.musicid(filename) == musicid


def test_resolveAUX():
    _filenames = {"SCD086738": "SCD086738_PRETTY IN PINK_SONOTON.wav",
                  "SCD074002": "AUXMP_SCD074002_HEARTWARMING  B.wav",
                  "RSM010436": "AUXMP_RSM010436_HEAVY URBAN.mp3",
                  "UBMM214809": "AUXMP_UBMM214809_EVIL FORCES.wav"}

    for musicid, filename in _filenames.iteritems():
        assert AUXResolver.musicid(filename) == musicid

