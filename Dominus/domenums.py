#!/usr/bin/env python
#
from enum import Enum
from typing import Union, Any
import unicodedata
import re


###############################################################################
#
def toEnum(whichEnum:type, s:Any, onFail:Any=None):
    """Get a full-fledged instance of the given Enum given any of:
        1: an instance of the Enum,
        2: a string that names one,
        3: a value that one represents, or
        4: the default value given in 'onFail'

    "The necessity of an enumeration of Existences, as the basis of Logic, did
    not escape the attention of the schoolmen, and of their master Aristotle."
        -- J. S. Mill, A System of Logic: Ratiocinative and Inductive
    """
    if isinstance(s, whichEnum):
        return whichEnum
    if s in whichEnum.__members__:  # s a key
        return whichEnum(s)
    try:
        return whichEnum(s)  # (s a value)
    except ValueError:
        pass
    return onFail


###############################################################################
#
class NodeType(Enum):
    UNSPECIFIED_NODE             = 0  # Not in DOM
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

class RWords(str, Enum):
    """Reserved words for XML (and additional contexts?)
    Including superclass str lets us use them in string contexts.

    "'It is a most repulsive quality, indeed,’ said he.
    ‘Oftentimes very convenient, no doubt, but never pleasing.
    There is safety in reserve, but no attraction.'"
        -- Jane Austen, Emma, chapter VI
    """
    NS_PREFIX   = "xmlns"

    NN_TEXT     = "#text"
    NN_PI       = "#pi"
    NN_COMMENT  = "#comment"
    NN_CDATA    = "#cdata"
    NN_DOCTYPE  = "#doctype"


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


###############################################################################
#
class UNormTx(Enum):
    """Whether/how various tokens should be Unicode-normalized.

    "Lest one good custom should corrupt the world."
        -- Alfred Lord Tennyson, "The Passing of Arthur"
    """
    NONE = "NONE"
    NFKC = "NFKC"
    NFKD = "NFKD"
    NFC = "NFC"
    NFD = "NFD"

    @staticmethod
    def normalize(s:str, which:'UNormTx'="NONE") -> str:
        which = toEnum(UNormTx, which)
        if not which or which == UNormTx.NONE: return s
        return unicodedata.normalize(str(which), s)


###############################################################################
#
class CaseTx(Enum):
    """How case should be handled.

    "You've got to know when to hold 'em,
    know when to fold 'em,
    know when to walk away
    know when to run."
        -- Don Schlitz, "The Gambler"
    """
    NONE = "NONE"
    FOLD = "FOLD"
    LOWER = "LOWER"
    UPPER = "UPPER"

    @staticmethod
    def fold(how:'CaseTx', s:str) -> str:
        if how == CaseTx.NONE: return s
        elif how == CaseTx.FOLD: return s.casefold()
        elif how == CaseTx.LOWER: return s.lower()
        elif how == CaseTx.UPPER: return s.upper()
        raise ValueError(f"Unknown CaseTx value {how}.")


###############################################################################
#
class WSDefs(Enum):
    """Ways to define blank space.

    "And the people did whatever seemed right in their own eyes."
        -- Judges 21:25

    “And then I have a secret. Did you know what will happen if you
    eliminate the empty spaces from the universe, eliminate the  empty
    spaces in all the atoms? The universe will become as big as my fist."
        -- Umberto Ecu, Interview with Mukund Padmanabhan, Oct 23, 2005
    """
    UNKNOWN = ""
    XML = "XML"  # SQL same?
    WHATWG = "WHATWG"
    UNICODE_ZS = "UNICODE_ZS"
    UNICODE_ALL = "UNICODE_ALL"
    JAVASCRIPT = "JAVASCRIPT"
    CPP = "CPP"
    PY_ISSPACE= "PY_ISSPACE"

    # Following list is Unicode category Z, minus nbsp, plus cr lf tab vt ff
    unicodeZs = ( ""
        + "\u0020"  # (Zs) SPACE
        #+ "\u00a0"  # (Zs) NO-BREAK SPACE
        + "\u1680"  # (Zs) OGHAM SPACE MARK
        + "\u2000"  # (Zs) EN QUAD
        + "\u2001"  # (Zs) EM QUAD
        + "\u2002"  # (Zs) EN SPACE
        + "\u2003"  # (Zs) EM SPACE
        + "\u2004"  # (Zs) THREE-PER-EM SPACE
        + "\u2005"  # (Zs) FOUR-PER-EM SPACE
        + "\u2006"  # (Zs) SIX-PER-EM SPACE
        + "\u2007"  # (Zs) FIGURE SPACE
        + "\u2008"  # (Zs) PUNCTUATION SPACE
        + "\u2009"  # (Zs) THIN SPACE
        + "\u200a"  # (Zs) HAIR SPACE
        + "\u202f"  # (Zs) NARROW NO-BREAK SPACE
        + "\u205f"  # (Zs) MEDIUM MATHEMATICAL SPACE
        + "\u3000"  # (Zs) IDEOGRAPHIC SPACE
    )
    c0All = "\r\n\t\x0B\f"
    unicodeOther = ( c0All  # (Cc)
        + "\u2028"  # (Zl) LINE SEPARATOR
        + "\u2029"  # (Zp) PARAGRAPH SEPARATOR
    )

    @staticmethod
    def spaces(which:'WSDefs'=""):
        which = toEnum(WSDefs, which)
        if which == WSDefs.XML: return " \t\n\r"
        if which == WSDefs.WHATWG: return " \t\n\r\f"
        if which == WSDefs.JAVASCRIPT:
            return WSDefs.c0All + "\xA0" + WSDefs.unicodeZs + WSDefs.unicodeOther
        if which == WSDefs.CPP: return WSDefs.c0All
        if which == WSDefs.UNICODE_ZS:
            return WSDefs.unicodeZs
        if which == WSDefs.UNICODE_ALL:
            return WSDefs.unicodeZs + WSDefs.unicodeOther
        if which == WSDefs.PY_ISSPACE:
            return WSDefs.c0All + WSDefs.unicodeZs + WSDefs.unicodeOther
        #if which == WSDefs.PY_RE:
        #    return WSDefs.c0All + WSDefs.unicodeZs + WSDefs.unicodeOther + WSDefs.UnicodeCf
        # And, oddly, unassigned code points, which I'm ignoring.
        return " \t\n\r\f"

    @staticmethod
    def isspace(s:str, which:'WSDefs'="") -> bool:
        """Like Python is___(), True if non-empty and all chars in category.
        """
        which = toEnum(WSDefs, which)
        nonSpaceExpr = f"[^{WSDefs.spaces(which)}]"
        return s!="" and not re.search(nonSpaceExpr, s)

    @staticmethod
    def containsspace(s:str, which:'WSDefs'="") -> bool:
        """True if has at least one char of category.
        """
        which = toEnum(WSDefs, which)
        spaceExpr = f"[^{WSDefs.spaces(which)}]"
        return re.search(spaceExpr, s)

    @staticmethod
    def normspace(s:str, which:'WSDefs'="", tgtChar:str=" ") -> bool:
        """Reduce internal spaces/runs to a single tgtChar, and drop
        leading and trailing spaces.
        """
        which = toEnum(WSDefs, which)
        assert len(tgtChar) == 1
        spaceExpr = f"[^{WSDefs.spaces(which)}]"
        return re.sub(spaceExpr, tgtChar, s).strip(tgtChar)


###############################################################################
#
class NameTx(Enum):
    """And name/identifier characters likewise vary.

    "Stat rosa pristina nomine, nomina nuda tenemus"
        -- Umberto Ecu, Il nome d'rosa
    """
    XML = "XML"         # XML NAME
    HTML = "HTML"       # ANY but XML SPACE?
    WHATWG = "WHATWG"   # Any but WHATWG__whitespace
    ASCII = "ASCII"     # XML except no non-ASCII
    PYTHON = "PYTHON"   # Python identifiers

    @staticmethod
    def isName(s:str, which:'NameTx'="") -> bool:
        """This provides a choice of treatments.
        None of these, btw, allow colons (as in QNAMES). Add?
        XmlStrings.isXmlName() does the full XML definitions.
        """
        which = toEnum(NameTx, which)
        if which == NameTx.XML:
            # TODO Use real XmlStrings.isXmlName().
            return re.match(r"^\w[-_.:\w]*$", s)
        elif which == NameTx.HTML:
            return re.match(r"^[^ \t\r\n]+$", s)
        elif which == NameTx.WHATWG:
            return re.match(r"^[^ \t\r\n\f]+$", s)
        elif which == NameTx.ASCII:
            return re.match(r"^\w[-.\w]+$", s, flags=re.ASCII)
        elif which == NameTx.PYTHON:
            return s.isidentifier()
        raise KeyError("Unknown NameTx value %s." % (which))
