#!/usr/bin/env python3
#
# saxplayer: Common stuff for SAX-like interfaces
#
#from enum import Enum
from ragnaroktypes import FlexibleEnum

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
    """
    DEFAULT      = "DefaultHandler"
    START        = "StartElementHandler"
    END          = "EndElementHandler"
    CHAR         = "CharacterDataHandler"
    CDATA        = "StartCdataSectionHandler"
    CDATAEND     = "EndCdataSectionHandler"
    PROC         = "ProcessingInstructionHandler"
    COMMENT      = "CommentHandler"
    DOCTYPE      = "StartDoctypeDeclHandler"
    DOCTYPEEND   = "EndDoctypeDeclHandler"

    # DTD/schema events
    #
    XMLDCL       =    "XmlDeclHandler"  # (NOT in expat)
    ELEMENTDCL   = "ElementDeclHandler"
    ATTLISTDCL   = "AttlistDeclHandler"
    NOTATIONDCL  = "NotationDeclHandler"
    ENTITYDCL    = "EntityDeclHandler"
    UENTITYDCL   = "UnparsedEntityDeclHandler"

    ATTRIBUTE    =     "AttributeHandler"  # (NOT in expat)
    ENTREF       =     "EntityReferenceHandler"  # (NOT in expat)
    ENTITY       =     "EntityHandler"  # (NOT in expat)
    DOC          =     "DocumentStartHandler"  # (NOT in expat)
    DOCEND       =     "DocumentEndHandler"  # (NOT in expat)
    DOCFRAG      =     "DocumentFragmentStartHandler"  # (NOT in expat)
    DOCFRAGEND   =     "DocumentFragmentHandler"  # (NOT in expat)

    #StartNamespaceDeclHandler(prefix, uri)
    #EndNamespaceDeclHandler(prefix)

    #DefaultHandlerExpand(data)
    #SkippedEntityHandler(entityName, is_parameter_entity)

    #PENTITYDCL   = 126  # -- Parameter entity
    #SENTITYDCL   = 136  # -- SDATA entity (SGML only)
    #COMMFRAG     = "Embedded" comment (SGML only)
    #ANNOT        = "Annotation" to last DCL

    # Events perhaps helpful for parsers treating overlap
    #
    SUSPEND      =     "SuspectElementHandler"  # (NOT in expat)
    RESUME       =     "ResumeElementHandler"  # (NOT in expat)

    START_MULTI  =     "ElementMultiStartHandler"  # (NOT in expat)
    END_MULTI    =     "ElementMultiEndHandler"  # (NOT in expat)

    END_OLIST    =     "ElementOlistEndHandler"  # (NOT in expat)

    RESTART      =     "EndAndRestartElementHandler"
