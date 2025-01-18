#!/usr/bin/env python3
#
# saxplayer: Common stuff for SAX-like interfaces
#
#from enum import Enum
from basedomtypes import FlexibleEnum

class SaxEvent(FlexibleEnum):
    """An enum for SAX events. Parsers commonly make you monkey-patch
    handlers, which means their methods names are exposed and if you
    spell one wrong you're likely (at least in Python) to create a
    quiet error. Here, in keeping with my treatment of other enumerated
    sets, I define an enum for SAX event types.

    These are passed back as the first tuple member from eachSaxEvent().
    Parsers can support them via a small glue layer to do some checking
    and then do whatever that parser needs:
        parser.setHandler(which:SaxEvent, handler:Callable)

    Parsers vary in how/whether they use/name these events. To use a parser
    you'll have to know whether (for example) it passes back (CDATA, text)
    or [CDATA, CHAR text, CDATAEND), etc., and what the rest of the arguments
    are (for example, how does START get attributes?).

    These values are chosen to match DOM nodeType values for the corresponding
    Node types (plus additions such as for the outer wrapper, schema events,
    etc.. When a nodeType has both start and end  events (ELEMENT, I'm
    looking at you), the end is the negative of the start.
    """
    START        =   1
    END          =  -1
    ATTRIBUTE    =   2  # Most parsers pack these into START
    # This is for a separate event for each attribute, which simplifies
    # things by making every event have at most a type and two values.
    # If used these must immediately follow a START event.
    CHAR         =   3
    CDATA        =   4  # Some parser do just one CDATA event
    CDATAEND     =  -4
    ENTREF       =   5  # Obsolete
    ENTITY       =   6  # Obsolete
    PROC         =   7
    COMMENT      =   8
    DOC          =   9  # Not commonly issued
    DOCEND       =  -9  # Not commonly issued
    DOCTYPE      =  10
    DOCTYPEEND   = -10
    DOCFRAG      =  11  # Obsolete?
    DOCFRAGEND   =  11  # Obsolete?
    NOTATION     =  12  # Obsolete

    DEFAULT      =   0
    INIT         =  99
    FINAL        = -99

    # DTD/schema events
    #
    XMLDCL       = 100
    ELEMENTDCL   = 101
    ATTLISTDCL   = 102
    ENTITYDCL    = 106  # General entity
    PENTITYDCL   = 116  # Parameter entity
    UENTITYDCL   = 126  # Unparsed entity
    SENTITYDCL   = 136  # SDATA entity (SGML only)
    COMMFRAG     = 108  # Embedded comment (--SGML only--)
    NOTATIONDCL  = 112
    ANNOT        = 120  # Annotation to last DCL

    # Skipping USEMAP, SHORTREF, etc.

    # Events perhaps helpful for parsers treating overlap
    #
    RESUME       =  50
    SUSPEND      = -50  # Suspend element a la TagML or <-p>

    START_MULTI  =  51  # Simultaneous starts (e.g. <p|q|r>)
    END_MULTI    = -51

    END_OLIST    = -52  # Close non-innermost element a la MECS
