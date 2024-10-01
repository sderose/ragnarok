#!/usr/bin/env python3
#
# saxplayer: Common stuff for SAX and SAX-like interfaces
#
from enum import Enum

class SaxEvents(Enum):
    START        =  1
    END          =  2
    CHAR         =  3
    PROC         =  4
    COMMENT      =  5
    CDATASTART   =  6
    CDATAEND     =  7
    DEFAULT      =  8
    INIT         =  9
    FINAL        = 10
    DOCTYPE      = 11
    DOCTYPEFIN   = 12

    # Support a separate event for each attribute; this simplifies
    # things by making every event have at most a type and 2 values.
    # If used these should be generated/expected to immediately follow
    # a start-tag event.
    #
    ATTRIBUTE    = 20

    ENTITYDCL    = 13
    ELEMENTDCL   = 14
    ATTLISTDCL   = 15
    NOTATIONDCL  = 16

### Provide at least:
# A callback thing like normal SAX
# for eventType, name, data in parseStuff()
# a feed-based interface?
# a direct DOM builder (cf dombuilder)
# a direct JSONX builder?
