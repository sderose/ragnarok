#!/usr/bin/env python
#
from enum import Enum
from typing import Union, Any

#from xmlstrings import XmlStrings as XStr


###############################################################################
#
def toEnum(value:Any, theEnum:type, default:Any=None) -> Enum:
    """Get a full-fledged instance of the given Enum given any of:
        1: an instance of the Enum,
        2: a string that matches a membr names,
        3: a value that one represents, or
        4: the 'default' value provided

    "The necessity of an enumeration of Existences, as the basis of Logic, did
    not escape the attention of the schoolmen, and of their master Aristotle."
        -- J. S. Mill, A System of Logic: Ratiocinative and Inductive
    """
    assert issubclass(theEnum, Enum)
    if isinstance(value, theEnum):
        return value
    try:
        return theEnum(value)
    except ValueError:
        return default


###############################################################################
#
class NodeType(Enum):
    NONE                         = 0  # Not in DOM
    ELEMENT_NODE                 = 1
    ATTRIBUTE_NODE               = 2
    TEXT_NODE                    = 3
    CDATA_SECTION_NODE           = 4
    ENTITY_REFERENCE_NODE        = 5  # Not in DOM
    ENTITY_NODE                  = 6  # Not in DOM
    PROCESSING_INSTRUCTION_NODE  = 7
    COMMENT_NODE                 = 8
    DOCUMENT_NODE                = 9
    DOCUMENT_TYPE_NODE           = 10
    DOCUMENT_FRAGMENT_NODE       = 11
    NOTATION_NODE                = 12 # Not in DOM

    @staticmethod
    def okNodeType(nt:Union[int, 'NodeType'], die:bool=True) -> 'NodeType':
        """Check a nodeType property. You can pass either a NodeType or an int,
        (so people who remember the ints and just test are still ok).
        Returns the actual NodeType.x (or None on fail).
        """
        if (isinstance(nt, NodeType)): return nt
        try:
            _nt = NodeType(nt)
        except ValueError:
            if (not die): return None
            assert False, "nodeType %s is a %s, not int or NodeType." % (
                nt, type(nt))
        return _nt

    @staticmethod
    def tostring(value:Union[int, 'NodeType']) -> str:  # NodeType
        if (isinstance(value, NodeType)): return value.name
        try:
            return NodeType(int(value))
        except ValueError:
            return "[UNKNOWN_NODETYPE]"

class RWord(str, Enum):
    """Reserved words for XML, DOM, etc.

    "'It is a most repulsive quality, indeed,’ said he.
    ‘Oftentimes very convenient, no doubt, but never pleasing.
    There is safety in reserve, but no attraction.'"
        -- Jane Austen, Emma, chapter VI
    """
    # XML constants
    #


    # Attribute names
    NS_PREFIX   = "xmlns"
    LANG_ATTR   = "xml:lang"
    SPACE_ATTR  = "xml:space"
    BASE_ATTR   = "xml:base"
    ID_QNAME    = "xml:id"

    # XML Namespace constants
    #
    XMLNS_URI   = "http://www.w3.org/2000/xmlns/"
    XHTML_NS    = "http://www.w3.org/1999/xhtml"
    XSI_NS      = "http://www.w3.org/2001/XMLSchema-instance"
    XML_NS_URI  = "http://www.w3.org/XML/1998/namespace"

    # DOM nodeName constants
    #
    NN_TEXT     = "#text"
    NN_PI       = "#pi"
    NN_COMMENT  = "#comment"
    NN_CDATA    = "#cdata"
    NN_DOCTYPE  = "#doctype"
    NN_DOCUMENT = "#document"
    NN_FRAGMENT = "#document-fragment"

    # Processing instruction targets
    #
    XML_TARGET  = "xml"
    XML_STYLESHEET = "xml-stylesheet"

    # Other
    #
    NS_ANY      = "##any"
    EL_ANY      = "*"


###############################################################################
#
class RelPosition(Enum):
    """Places relative to element, mainly for insertAdjacentXML().

    "Now this is not the end. It is not even the beginning of the end.
    But it is, perhaps, the end of the beginning."
        -- Churchhill, Lord Mayor's Day Luncheon, 10 November 1942
    """
    beforebegin = "beforebegin"
    afterbegin = "afterbegin"
    beforeend = "beforeend"
    afterend = "afterend"
