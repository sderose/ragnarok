#!/usr/bin/env python3
# DocType class: split from basedom 2024-06-28 sjd.
#
#
import re
from enum import Enum
from datetime import datetime, date, time, timedelta
from collections import defaultdict, namedtuple

from typing import List, Set, Any, Union, Iterable

from basedomtypes import NMTOKEN_t
from xmlstrings import XmlStrings as XStr, CaseHandler

from basedomtypes import NSuppE
from domenums import NodeType
from basedom import Node

descr = """
This library provides a basic interface to schema information, whether created
via the API, an XML (or perhaps SGML) DTD, an XML Schems, or (eventually) a Relax-NG schema (I'm less
familiar with those, so that may be a while). The idea here is to get any
schema into a common API that parsers and validators can talk to.

The major classes include:

SimpleType --

ComplexType -- This covers the needed info describing an element type,
such as its name, content type and model, attributes, etc.
"""


###############################################################################
#
class PropDict(dict):
    """A dict whose keys must be drawn from a certain set of values.
    """
    def __init__(self, *args, keyList:Iterable, caseTx="NONE"):
        super().__init__(*args)
        self.caseTx = CaseHandler(caseTx)
        self.keyList = {}
        for key in keyList:
            normKey = self.caseTx.normalize(key)
            self.keyList[normKey] = key

    def __setitem__(self, k:NMTOKEN_t, v:Any) -> None:
        normKey = self.caseTx.normalize(k)
        if normKey in self.keyList:
            super().__setitem__(normKey, v)
        else:
            raise KeyError("Key '{k}' (->{normKey}) not in list.")

    def __getitem__(self, k) -> Union[List, 'Node']:
        normKey = self.caseTx.normalize(k)
        if normKey in self.keyList:
            return super().__getitem__(normKey)
        else:
            raise KeyError("Key '{k}' (->{normKey}) not in list.")


###############################################################################
#
# restrictions: min/max; len; pattern; etc.
#
class SimpleType(dict):
    def __init__(self, name:NMTOKEN_t, baseType:NMTOKEN_t):
        self.name = name
        self.baseType = baseType
        self.restrictions = {}
        self.memberTypes = None  # For list and union types
        self.caseTx = "NONE"
        self.unormTx = "NONE"
        self.wsTx = "XML"


###############################################################################
#
class DerivationLimits(Enum):
    """for XSD .block and .final
    """
    NONE = "NONE"
    EXTENSION = "EXTENSION"
    RESTRICTION = "RESTRICTION"
    ALL = "ALL"

class ComplexType(SimpleType):
    def __init__(self, name:NMTOKEN_t, model):
        super().__init__(name, model)
        self.abstract = False
        self.final = None
        self.block = None
        self.attributeDefs = {}
        self.contentType = None
        self.model = None


###############################################################################
#
class XsdType(dict):
    """Support the XSD built-in datatypes (e.g. for attributes).
    """
    def __getitem__(self, key) -> Union[List, 'Node']:
        # TODO fetch up the inheritance chain?
        return super().get(key, None)

MinMax = namedtuple('MinMax',
    ['minInclusive', 'minExclusive', 'maxExclusive', 'maxInclusive'])

# These are the signed, positive maxima (rest calculated from them)
MAXLONG = 9223372036854775807
MAXINT = 2147483647
MAXSHORT = 32767
MAXBYTE = 127

ALPHA_re = "[a-zA-Z]"
ALNUM_re = "[a-zA-Z0-9]"
HEX_re = "[0-9a-fA-F]"
DIGIT_re = r"\d"
EXPNAN_re = r"([eE][-+]?\d+)?|INF|NaN"

TZONE_re = r"(Z|(\+|-)((0\d|1[0-3]):[0-5]\d|14:00))?"
GYEAR_re = r"-?([1-9]\d{3,}|0\d{3})"
GMONTH_re = r"-?([1-9]\d{3,}|0\d{3})"
GDAY_re = r"\(0\[1-9\]\|\[12\]\\d\|3\[01\]\)"
TIME_re = (r"\(\(\[01\]\\d\|2\[0-3\]\):\[0-5\]\\d:\[0-5\]\\d\(\\\.\\d\+\)\?\|" +
    r"\(24:00:00\(\\\.0\+\)\?\)\)")


###########################################################################
# See [https://www.w3.org/TR/xml/]
# iscastable; iscanonical; ispybaseof;
# topybase; to canonical;
# lists/unions?
# inheritable fetch?
#
AttrTypes = {
    "string": XsdType({
        "pybase": str,
        "base": None,
        "pattern": r".*",
        "length": None,
        "minLength": None,
        "maxLength": None,
        "whiteSpace": "preserve"
    }),
    "normalizedString": XsdType({
        "pybase": str,
        "base": "string",
        "pattern": r".*",
        "whiteSpace": "replace"
    }),
    "token": XsdType({
        "pybase": str,
        "base": "normalizedString",
        "pattern": r".*",
        "whiteSpace": "collapse"
    }),
    "language": XsdType({
        "pybase": str,
        "base": "token",
        "pattern": r"[a-zA-Z]{1,8}(-[a-zA-Z0-9]{1,8})*" # TODO
    }),
    "NMTOKEN": XsdType({
        "pybase": str,
        "base": "token",
        "pattern": XStr.NMTOKEN_re,
    }),
    "NMTOKENS": XsdType({
        "pybase": str,
        "list": True,
        "base": "NMTOKEN",
        "pattern": r"%s(\s+%s)*" % (XStr.NMTOKEN_re, XStr.NMTOKEN_re),
    }),
    "Name": XsdType({
        "pybase": str,
        "base": "token",
        "pattern": XStr.QQName_re,
    }),
    "NCName": XsdType({
        "pybase": str,
        "base": "Name",
        "pattern": XStr.NCName_re,
    }),
    "ID": XsdType({
        "pybase": str,
        "base": "NCName",
        "pattern": XStr.NCName_re,
    }),
    "IDREF": XsdType({
        "pybase": str,
        "base": "NCName",
        "pattern": XStr.NCName_re,
    }),
    "IDREFS": XsdType({
        "pybase": str,
        "base": "IDREF",
        "list": True,
        "pattern": r"%s(\s+%s)*" % (XStr.QName_re, XStr.QName_re),
    }),
    "ENTITY": XsdType({
        "pybase": str,
        "base": "NCName",
        "pattern": XStr.NCName_re,
    }),
    "ENTITIES": XsdType({
        "pybase": str,
        "base": "ENTITY",
        "list": True,
        "pattern": r"%s(\s+%s)*" % (XStr.NCName_re, XStr.NCName_re),
    }),
    "QName": XsdType({
        "pybase": str,
        "base": "string",
        "pattern": XStr.QName_re,
        "whiteSpace": "collapse",
    }),
    "NOTATION": XsdType({
        "pybase": str,
        "base": "string",
        "pattern": XStr.QName_re,
        "whiteSpace": "collapse",
    }),

    ###########################################################################
    "decimal": XsdType({
        "pybase": int,
        "base": None,
        "pattern": r"(\+|-)?((\d+(\.\d*)?)|(\.\d+))",
        "totalDigits": None,
        "fractionDigits": None,
        "whiteSpace": "collapse",
    }),
    "integer": XsdType({
        "pybase": int,
        "base": "decimal",
        "pattern": r"[\-+]?\d+",
        "fractionDigits": 0,
    }),
    "nonPositiveInteger": XsdType({
        "pybase": int,
        "base": "integer",
        "pattern": r"(-\d+)|0",
        "range": MinMax(None, None, None, 0),
    }),
    "negativeInteger": XsdType({
        "pybase": int,
        "base": "nonPositiveInteger",
        "pattern": r"-\d+",
        "range": MinMax(None, None, None, -1),
    }),
    "nonNegativeInteger": XsdType({
        "pybase": int,
        "base": "integer",
        "pattern": r"[+]?\d+",
        "range": MinMax(0, None, None, None),
    }),
    "positiveInteger": XsdType({
        "pybase": int,
        "base": "nonNegativeInteger",
        "pattern": r"[+]?\d*[1-9]\d*",
        "range": MinMax(1, None, None, None),
    }),
    "long": XsdType({
        "pybase": int,
        "base": "integer",
        "pattern": r"[-+]?\d+",
        "range": MinMax(-MAXLONG-1, None, None, MAXLONG),
    }),
    "int": XsdType({
        "pybase": int,
        "base": "long",
        "pattern": r"[-+]?\d+",
        "range": MinMax(-MAXINT-1, None, None, MAXINT),
    }),
    "short": XsdType({
        "pybase": int,
        "base": "int",
        "pattern": r"[-+]?\d+",
        "range": MinMax(-MAXSHORT-1, None, None, MAXSHORT),
    }),
    "byte": XsdType({
        "pybase": int,
        "base": "short",
        "pattern": r"[-+]?\d+",
        "range": MinMax(-MAXBYTE-1, None, None, MAXBYTE),
    }),
    "unsignedLong": XsdType({
        "pybase": int,
        "base": "nonNegativeInteger",
        "pattern": r"[+]?\d+",
        "range": MinMax(0, None, None, MAXLONG<<1 + 1),
    }),
    "unsignedInt": XsdType({
        "pybase": int,
        "base": "unsignedLong",
        "pattern": r"[+]?\d+",
        "range": MinMax(0, None, None, MAXINT<<1 + 1),
    }),
    "unsignedShort": XsdType({
        "pybase": int,
        "base": "unsignedInt",
        "pattern": r"[+]?\d+",
        "range": MinMax(0, None, None, MAXSHORT<<1 + 1),
    }),
    "unsignedByte": XsdType({
        "pybase": int,
        "base": "unsignedShort",
        "pattern": r"[+]?\d+",
        "range": MinMax(0, None, None, MAXBYTE<<1 + 1),
    }),

    ###########################################################################
    "boolean": XsdType({
        "pybase": bool,
        "base": None,
        "pattern": r"true|false|1|0",
        "whiteSpace": "collapse",
    }),

    ###########################################################################
    "float": XsdType({
        "pybase": float,
        "base": "decimal",
        "pattern": r"(\+|-)?(\d+(\.\d*)?|\.\d+)" + EXPNAN_re,
        "whiteSpace": "collapse",
    }),
    "double": XsdType({
        "pybase": float,
        "base": "decimal",
        "pattern": r"(\+|-)?(\d+(\.\d*)?|\.\d+)" + EXPNAN_re,
        "whiteSpace": "collapse",
    }),

    ###########################################################################
    "duration": XsdType({
        "pybase": timedelta,
        "base": None,
        "pattern": r"-?P(\d+Y)?(\d+M)?(\d+D)?(T(\d+H)?(\d+M)?(\d+(\.\d+)?S)?)?",
        "whiteSpace": "collapse",
    }),

    ###########################################################################
    "dateTime": XsdType({
        "pybase": datetime,
        "base": None,
        "pattern": GYEAR_re + r"-" + GMONTH_re + r"-" + GDAY_re + r"T" + TIME_re + TZONE_re,
        "whiteSpace": "collapse",
    }),
    "time": XsdType({
        "pybase": time,
        "base": None,
        "pattern": TIME_re + TZONE_re,
        "whiteSpace": "collapse",
    }),
    "date": XsdType({
        "pybase": date,
        "base": None,
        "pattern": GYEAR_re + r"-" + GMONTH_re + r"-" + GDAY_re + TZONE_re,
        "whiteSpace": "collapse",
    }),
    "gYearMonth": XsdType({
        "pybase": date,
        "base": None,
        "pattern": GYEAR_re + r"-" + GMONTH_re + TZONE_re,
        "whiteSpace": "collapse",
    }),
    "gYear": XsdType({
        "pybase": date,
        "base": None,
        "pattern": GYEAR_re + TZONE_re,
        "whiteSpace": "collapse",
    }),
    "gMonthDay": XsdType({
        "base": None,
        "pattern": r"--" + GMONTH_re + r"-" + GDAY_re + TZONE_re,
        "whiteSpace": "collapse",
    }),
    "gDay": XsdType({
        "base": None,
        "pattern": r"---" + GDAY_re + TZONE_re,
        "whiteSpace": "collapse",
    }),
    "gMonth": XsdType({
        "base": None,
        "pattern": r"--" + GMONTH_re + TZONE_re,
        "whiteSpace": "collapse",
    }),

    ###########################################################################
    "hexBinary": XsdType({
        "pybase": bytes,
        "base": "string",
        "pattern": r"([0-9a-fA-F]{2})*",
        "whiteSpace": "collapse",
    }),

    ###########################################################################
    "base64Binary": XsdType({
        "pybase": bytes,
        "base": "string",
        "pattern": (
            r"((([A-Za-z0-9+/] ?){4})*(([A-Za-z0-9+/] ?){3}" +
            r"[A-Za-z0-9+/]|([A-Za-z0-9+/] ?){2}" +
            r"[AEIMQUYcgkosw048] ?=|[A-Za-z0-9+/] ?[AQgw] ?= ?=))?"),
        "whiteSpace": "collapse",
    }),

    ###########################################################################
    "anyURI": XsdType({
        "pybase": str,
        "base": "string",
        "pattern": r".*",  # Too lenient, at least rule out spaces?
        "whiteSpace": "collapse",
    }),
}  # AttrTypes


def fitsDatatype(val:Any, typ:Union[str, type]) -> bool:
    """Who counts? Must it *be* of the type, or just fit?
    By both Python and XSD lights, probably just fit...
    What about None?
    TODO Check whether *already* (normalized, cast, etc), or castable?
    TODO Generators for canonical form.
    TODO Case?
    """
    if isinstance(typ, type):
        try:
            tval = typ(val)
            return True
        except ValueError:
            return False

    try:
        typeSpec = AttrTypes[typ]
    except KeyError as e:
        raise TypeError(f"Unrecognized type {typ} for value {val}.") from e

    if "list"  in typeSpec:
        return True  # TODO Finish!

    sval = str(val)
    if "whiteSpace" in typeSpec:
        if typeSpec["whiteSpace"] == "collapse": sval = XStr.collapseSpace(sval)
        elif typeSpec["whiteSpace"] == "replace": sval = XStr.replaceSpace(sval)
    if "pybase" in typeSpec:
        try:
            _castVal = typeSpec["pybase"](sval)
        except ValueError:
            return False, "pybase"
    if "minLength" in typeSpec:
        if len(sval) < typeSpec["minLength"]: return False, "minLength"
    if "maxLength" in typeSpec:
        if len(sval) > typeSpec["minLength"]: return False, "maxLength"
    if "pattern" in typeSpec:
        if not re.match(typeSpec["pattern"], sval): return False, "pattern"
    if "range" in typeSpec:
        mm = typeSpec["range"]
        if mm[0] is not None and tval < mm[0]: return False, "minInclusive"
        if mm[1] is not None and tval <= mm[1]: return False, "minExclusive"
        if mm[2] is not None and tval >= mm[2]: return False, "maxExclusive"
        if mm[3] is not None and tval > mm[3]: return False, "maxInclusive"
    if "enumeration" in typeSpec and typeSpec["enumeration"]:
        if sval not in typeSpec["enumeration"]: return False, "enumeration"
    #"totalDigits": None,
    #"fractionDigits": None,


###############################################################################
# TODO Sync w/ lxml or similar.
#
class DKey(Enum):
    # DTD items (not incl. attribute types, dcl names,...)
    #
    ANY     = "ANY"
    EMPTY   = "EMPTY"
    PCDATA  = "#PCDATA"
    X_ELEMENT = "X_ELEMENT"  # HERE -- for element-only content
    X_MODEL = "X_MODEL"      # Has content model, not one of the above

    CDATA   = "CDATA"
    RCDATA  = "RCDATA"
    NDATA   = "NDATA"
    SDATA   = "SDATA"

    REQUIRED= "#REQUIRED"
    IMPLIED = "#IMPLIED"
    FIXED   = "#FIXED"
    X_VALUE = "X_VALUE"  # Set when there's a literal default value

    SEQ   = ","
    OR    = "|"
    AND   = "&"  # SGML but not XML

    STAR    = "*"
    PLUS    = "+"
    QUEST   = "?"
    X_BOUNDS= r"{\d*(,\d*)?}"  # Like regex and xsd

    PERO    = "%"
    RNI     = "#"

    def isContentType(self):
        """Is the value one that specifies element content?
        """
        return self in [
            DKey.ANY, DKey.EMPTY, DKey.PCDATA, DKey.X_ELEMENT, DKey.X_MODEL ]

    def isSeqType(self):
        return self in [ DKey.SEQ, DKey.OR, DKey.AND ]

    def isRepType(self):
        return self in [ DKey.STAR, DKey.PLUS, DKey.QUEST, DKey.X_BOUNDS ]

    def isAttrDefault(self):
        return self in [ DKey.REQUIRED, DKey.IMPLIED, DKey.FIXED, DKey.X_VALUE ]

class RepType:  # TODO?
    def __init__(self, minOccurs:int=1, maxOccurs:int=1):
        assert int(minOccurs) and int(maxOccurs)
        self.minOccurs = int(minOccurs)
        self.maxOccurs = int(maxOccurs)

    def tostring(self) -> str:
        if (self.minOccurs == 0):
            if (self.maxOccurs == 1): return "?"
            if (self.maxOccurs == -1): return "*"
        elif (self.minOccurs == 1):
            if (self.maxOccurs == 1): return ""
            if (self.maxOccurs == -1): return "+"
        return "{%d,%d}" % (self.minOccurs, self.maxOccurs)


###############################################################################
#
class ModelItem:
    """One item (an element name with a rep, or just #PCDATA).
    """
    def __init__(self, name:NMTOKEN_t, rep:RepType=None):
        assert name == DKey.PCDATA.value or XStr.isXmlNMTOKEN(name)
        self.name = name
        self.rep = rep

    def tostring(self) -> str:
        return self.name + (self.rep.tostring() if self.rep else "")

class ModelGroup:
    """Any parenthesized group, with ModelItem members, plus connector and rep.
    Maybe keep the original string (if any), or a list of PEs in it?
    """
    def __init__(self, items:List=None, seq:DKey=None, rep:DKey=None):
        assert DKey.isSeqType(seq)
        assert DKey.isRepType(rep)
        self.items = items
        self.seq = seq
        self.rep =  rep

    def getNames(self) -> Set:
        """Extract the set of all names used anywhere in a model.
        """
        names = set()
        for item in self.items:
            if isinstance(item, ModelItem):
                names = names.union([item.name])
            elif isinstance(item, ModelGroup):
                names = names.union(item.getNames())
        return names

    def tostring(self) -> str:
        """TODO Maybe re-introduce PEs or complex types?
        """
        buf = ""
        txt = False
        for item in self.items:
            if isinstance(item, ModelItem):
                if item.name == "#PCDATA": txt = True
                else: names = names.union([item.name])
            elif isinstance(item, ModelGroup):
                names = names.union(item.getNames())
        connector = str(self.seq)
        buf = "(%s%s)%s" % (
            ("#PCDATA" + connector) if txt else "",
            connector.join(self.items),
            self.rep.tostring())
        return buf

class Model(ModelGroup):
    """The whole/top model, which can be a declared content keyword OR a ModelGroup.
    This also converts a token sequence to the model ASN.
    """
    def __init__(self, contentType:DKey=None, tokens:List[str]=None):
        super(). __init__()
        assert DKey.isContentType(contentType)
        if tokens: assert contentType == DKey.X_MODEL

        self.contentType = contentType
        self.tokens = tokens

        if not tokens: return
        self.items = []
        self.seq = None
        self.rep =  None
        pstack = [ self ]
        for i in range(len(tokens)):
            t = tokens[i]
            if t == "(":
                newGroup = ModelGroup()
                pstack[-1].items.append(newGroup)
                pstack.append(newGroup)
            elif t == ")":
                if i+1 < len(tokens) and isinstance(tokens[i+1], RepType):
                    pstack[-1].rep = tokens[i+1]
                    i += 1
            elif t in "|&,":  # TODO Map to enum
                if pstack[-1].seq != t:
                    if pstack[-1].seq is None: pstack[-1].seq = t
                    else: raise SyntaxError("Inconsistent connectors.")
            elif XStr.isXmlName(t):
                newItem = ModelItem(t)
                pstack[-1].items.append(newItem)
                if i+1 < len(tokens) and isinstance(tokens[i+1], RepType):   # TODO Map to enum
                    newItem.rep = tokens[i+1]
                    i += 1
            else:
                raise SyntaxError(f"Unexpected model token '{t}'.")
        if (len(pstack) != 1):
            raise SyntaxError("Unbalanced () in model.")

    def tostring(self) -> str:
        if self.contentType: return self.contentType.tostring()
        else: return super().tostring()

class ElementDef(ComplexType):
    def __init__(self, name:NMTOKEN_t, model:Model, readOrder:int=0):
        super().__init__(name, model)
        self.attributeDefs = None
        self.allowText:bool = True
        self.allowAnywhere:Set = None
        self.allowNowhere:Set = None
        self.readOrder = readOrder

    def tostring(self) -> str:
        buf = "<!ELEMEMT %-12s %s>\n" % (self.name, self.model.tostring())
        # TODO Add attlist?
        return buf


###############################################################################
# TODO Move attr stuff to separate file
#
class AttributeDef:
    def __init__(self, name:NMTOKEN_t, aname:NMTOKEN_t, atype:str, adefault:Any, readOrder:int=0):
        self.name = name
        self.aname = aname
        self.atype = atype
        self.adefault = adefault
        self.caseTx = "NONE"
        self.wsTx = "NONE"
        self.enumList = None
        self.readOrder = readOrder

    def enumSpec(self) -> str:
        if self.enumList: return " (%s)" % (" | ".join(self.enumList))
        return None

class AttlistDef(dict):
    def __init__(self, name:str, readOrder:int=0):  # Or list of enames?
        self.name = name
        self.attrs = {}
        self.readOrder = readOrder

    def __setitem__(self, aname:NMTOKEN_t, atype:str, adefault:Any=None) -> AttributeDef:
        if aname in self.attrs:
            raise KeyError("Attribute {aname} already defined for {self.ename}.")
        if atype not in AttrTypes and not isinstance(atype, type):
            raise TypeError("Unrecognized type for attribute {aname} for {self.ename}.")
        if adefault is not None:
            pass  # TODO
        adef = AttributeDef(self.name, aname, atype, adefault)
        self.attrs[aname] = adef
        return adef

    def tostring(self) -> str:
        buf = f"<!ATTLIST {self.name} "
        for aname, aobj in self.items():
            buf += "    %12s %12s %s\n" % (aname, aobj.enumSpec(), aobj.adefault)
        buf += ">\n"
        return buf


###############################################################################
#
class EntityType(Enum):
    GENERAL = 1
    PARAMETER = 2
    NOTATION = 4  # Treat as special entity, or not?

    # Names for possible extensions
    SDATA = 8
    NAMESET = 16

class EntityParseType(Enum):  # Includes extras...
    NDATA   = 0
    CDATA   = 1
    RCDATA  = 2
    PCDATA  = 3

    # Names for possible extensions
    XINCLUDE = 100
    SUBDOC   = 101
    STARTTAG = 102
    ENDTAG   = 103
    PI       = 104

class DataSource:
    """PUBLIC and/or SYSTEM identifier or (for ENTITY but not NOTATION) QLit.
    """
    def __init__(self,
        literal:str=None,
        publicId:str=None,
        systemId:Union[str, List]=None):
        self.literal = literal
        self.publicId = publicId
        if not isinstance(systemId, List): systemId = [ systemId ]
        self.systemId = systemId

    def tostring(self) -> str:
        if (self.literal):
            return '"%s"' % (XStr.escapeAttribute(self.literal))
        if self.publicId:
            src = 'PUBLIC "%s"' % (XStr.escapeAttribute(self.literal))
        else:
            src = 'SYSTEM'
        if (not self.systemId):
            src += ' ""'
        else:
            for s in self.systemId:
                src += ' "%s"' % (XStr.escapeAttribute(s.literal))
        return src

class EntityDef:
    """Any of several subtypes.
    """
    def __init__(self, name:NMTOKEN_t,
        etype:EntityType,
        dataSource:DataSource,
        parseType:EntityParseType=EntityParseType.PCDATA,
        notation:NMTOKEN_t=None,
        readOrder:int=0
        ):
        self.name = name
        self.etype = etype
        self.dataSource = dataSource
        self.parseType = parseType
        self.notation = notation
        self.localPath = None
        self.readOrder = readOrder

    def tostring(self) -> str:
        # TODO Support keywords -- SDATA, CTYPE,....
        src = self.dataSource.tostring()
        pct = "% " if self.etype == EntityType.PARAMETER else ""
        return "<!ENTITY %s%s %s>\n" % (pct, self.name, src)

class Notation:
    """This is for data notation/format applicable to entities. They are normally
    embedded by declaring an external file or object as an ENTITY, and then
    mentioning that entity name (not actually referencing the entity) as
    the value of an attribute that was declared as being of type ENTITY.
    """
    def __init__(self, name:NMTOKEN_t, dataSource:DataSource, readOrder:int=0):
        if (dataSource.literal is not None):
            raise SyntaxError("NOTATION {nname} has QLit, not PUBLIC or SYSTEM.")
        self.name = name
        self.dataSource = dataSource
        self.readOrder = readOrder

    def tostring(self) -> str:
        return "<!NOTATION %-12s %s>\n" % (self.name, self.dataSource.tostring())


###############################################################################
#
class DocumentType(Node):
    """Just a stub for the moment.
    See also my Schemas.py, and https://docs.python.org/3.8/library/xml.dom.html
    """
    def __init__(self, qualifiedName:str, doctypeString:str='',
        publicId:str='', systemId:str=''):
        super().__init__(nodeName="#doctype")
        self.nodeType = NodeType.DOCUMENT_TYPE_NODE

        self.name = self.nodeName = qualifiedName  # Should come from the DOCTYPE
        # TODO Switch to DataSource
        self.publicId = publicId
        self.systemId = systemId
        #self.userData = None

        self.doctypeString = doctypeString
        if (qualifiedName and doctypeString and
            not doctypeString.strip().startswith(qualifiedName)):
            raise ValueError("doctype mismatch, '%s' vs. '%s'." %
                (qualifiedName, doctypeString))

        self.elementDefs = None
        self.attributeDefs = None  # NamedNodeMap() later if needed

        # These are all considered types of entities here:
        self.entityDefs = None
        self.pentityDefs = None
        self.notationDefs = None
        self.nameSetDefs = {}  # Accommodation for schema maintenance

    @property
    def nodeValue(self) -> str:
        return None

    def after(self, stuff:List) -> None:
        """Inserts a set of Node or string objects in the child list of the
        parent, just after this node.
        """
        par = self.parentNode
        rsib = self.nextSibling
        if rsib:
            rsib.before(stuff)
        else:
            for thing in stuff:
                par.appendChild(thing)

    def before(self, stuff:List) -> None:
        """Inserts a set of Node or string objects in the child list of the
        parent, just before this node.
        """
        par = self.parentNode
        for thing in stuff:
            par.insertBefore(self, thing)

    def removeNode(self) -> None:
        """Removes this object from its parent child list.
        """
        par = self.parentNode
        par.removeChild(self)

    def replaceWith(self, stuff:List) -> None:
        """Replaces the document type with a set of given nodes.
        """
        raise NSuppE

    ####### EXTENSIONS

    def reindex(self) -> None:
        self.elementDefs = {}
        self.attributeDefs = {}
        self.entityDefs = {}
        self.pentityDefs = {}
        self.notationDefs = {}
        self.nameSetDefs = {}

        for ch in self.childNodes:
            if isinstance(ch, ElementDef): self.elementDefs[ch.name] = ch
            elif isinstance(ch, AttributeDef): self.attributeDefs[ch.name] = ch
            elif isinstance(ch, EntityDef):
                self.entityDefs[ch.etype][ch.name] = ch
            else:
                assert False, "Unknown declaration type %s." % (type(ch))
        return

    # ELEMENT
    def getElementDef(self, name:NMTOKEN_t) -> ElementDef:
        return self.elementDefs[name] if name in self.elementDefs else None

    def defineElement(self, name:NMTOKEN_t, modelInfo):
        assert name not in self.elementDefs
        self.elementDefs[name] = modelInfo

    # Attribute
    def getAttributeDef(self, ename:NMTOKEN_t, aname:NMTOKEN_t) -> AttributeDef:
        if ename not in self.elementDefs: return None
        edef = self.elementDefs[ename]
        if aname not in edef.attributeDefs: return None
        return edef.attributeDefs[aname]

    def defineAttribute(self, ename:NMTOKEN_t, aname:NMTOKEN_t,
        atype:NMTOKEN_t="CDATA", adefault:NMTOKEN_t="IMPLIED") -> None:
        assert aname not in self.attributeDefs
        self.elementDefs[(ename)].attributeDefs[aname] = [ atype, adefault ]

    # Entity (subtypes for General, Parameter, Notation, and NameSet)
    def getEntityDef(self, name:NMTOKEN_t) -> EntityDef:
        return self.entityDefs[name] if name in self.entityDefs else None

    def defineEntity(self, name:NMTOKEN_t,
        literal:str=None, publicId:str=None, systemId:str=None,
        parseType:EntityParseType=EntityParseType.PCDATA, notation:NMTOKEN_t=None) -> None:
        assert name not in self.entityDefs
        assert isinstance(parseType, EntityParseType)
        ds = DataSource(literal, publicId, systemId)
        self.entityDefs[name] = EntityDef(name, EntityType.GENERAL,
            dataSource=ds, parseType=parseType, notation=notation)

    def getPEntityDef(self, name:NMTOKEN_t) -> EntityDef:
        return self.pentityDefs[name] if name in self.pentityDefs else None

    def definePEntity(self, name:NMTOKEN_t,
        literal:str=None, publicId:str=None, systemId:str=None) -> None:
        assert name not in self.pentityDefs
        self.entityDefs[name] = EntityDef(name,
            EntityType.PARAMETER, literal, publicId, systemId)

    def getNotationDef(self, name:NMTOKEN_t) -> EntityDef:
        return self.notationDefs[name] if name in self.notationDefs else None

    def defineNotation(self, name:NMTOKEN_t,
        literal:str=None, publicId:str=None, systemId:str=None) -> None:
        assert name not in self.notationDefs
        self.notationDefs[name] = EntityDef(name,
            EntityType.NOTATION, literal, publicId, systemId)

    # Basic operations
    #
    def cloneNode(self, deep:bool=False) -> 'Node':
        newNode = DocumentType(
            qualifiedName=self.name,
            doctypeString=self.doctypeString,
            publicId = self.publicId,
            systemId = self.systemId
        )
        if deep: newNode.elementDefs = self.elementDefs.deepcopy()
        else: newNode.elementDefs = self.elementDefs.copy()
        return newNode

    def isEqualNode(self, n2) -> bool:  # Doctype
        if self.nodeType != n2.nodeType: return False
        if self.doctypeString != n2.doctypeString: return False
        #if (self.nodeName != n2.nodeName or
        #    self.publicId != n2.publicId or
        #    self.systemId != n2.systemId): return False
        docel1 = self.ownerDocument.documentElement
        docel2 = n2.ownerDocument.documentElement
        if not docel1.isEqualNode(docel2): return False
        return True

    ####### EXTENSIONS

    @property
    def outerXML(self) -> str:
        """TODO: Preserve input order
        """
        return self.toprettyxml()

    def tostring(self) -> str:
        buf = ('<!DOCTYPE %s PUBLIC "%s" "%s" [\n') % (
            self.nodeName, self.publicId, self.systemId)

        for pent in sorted(self.pentityDefs):
            buf += pent.toprettyxml()

        for notn in sorted(self.notationDefs):
            buf += notn.toprettyxml()

        for ent in sorted(self.entityDefs):
            buf += ent.toprettyxml()

        attrsDone = defaultdict(int)
        for elem in sorted(self.elementDefs):
            buf += elem.toprettyxml()
            if elem.name in self.attributeDefs:
                buf += self.attributeDefs[elem.name].toprettyxml()
                attrsDone[elem.name] = True

        for attr in self.attributeDefs:
            if attr.name in attrsDone: continue
            buf += self.attributeDefs[attr.name].toprettyxml()

        buf += "]>\n"
        return buf

    # end class DocumentType

DocType = DocumentType
