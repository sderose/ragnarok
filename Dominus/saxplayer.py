#!/usr/bin/env python3
#
# saxplayer: Common stuff for SAX-like interfaces
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
    ENTREF       = 21

    XMLDCL       = 100
    ELEMENTDCL   = 101
    ATTLISTDCL   = 102
    ENTITYDCL    = 103
    PENTITYDCL   = 104
    SDATADCL     = 106
    NOTATIONDCL  = 105

