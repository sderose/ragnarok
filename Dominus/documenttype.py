#!/usr/bin/env python3
# DocType class: split from basedom 2024-06-28 sjd.
#
#
import re
from enum import Enum
from datetime import datetime, date, time, timedelta
from collections import defaultdict, namedtuple

from typing import List, Set, Any, Union
from typing import NewType

from xmlstrings import XmlStrings as XStr
from domenums import NodeType  #, UNormTx, CaseTx
from basedom import Node

NmToken = str  # TODO Switch to NewType

descr = """
This library provides a basic interface to XML schema information.
An instance should be loadable from XSD, RelaxNG, or DTD, and provide a common
API for any of them. That's hard, so I'm starting with DTD++ and parts of XSD.

The hardest bits will likely be (a) preserving DTD classes implemented via
parameter entities, and (b) making that compatible with XSD complex types.

I may also integrate the shorthand declarations I rough out in XSD_compact
and elsewhere.
"""


###############################################################################
#
class XsdType(dict):
    def __getitem__(self, key):
        # TODO fetch up the inheritance chain?
        return super().get(key, None)

MinMax = namedtuple('MinMax',
    ['minInclusive', 'minExclusive', 'maxExclusive', 'maxInclusive'])

ALPHA = "[a-zA-Z]"
ALNUM = "[a-zA-Z0-9]"
HEX = "[0-9a-fA-F]"
DIGIT = r"\d"
EXPNAN = r"([eE][-+]?\d+)?|INF|NaN"

# These are the signed, positive maxima (rest calculated from them)
MAXLONG = 9223372036854775807
MAXINT = 2147483647
MAXSHORT = 32767
MAXBYTE = 127

TZONE = r"(Z|(\+|-)((0\d|1[0-3]):[0-5]\d|14:00))?"
GYEAR = r"-?([1-9]\d{3,}|0\d{3})"
GMONTH = r"-?([1-9]\d{3,}|0\d{3})"
GDAY = r"\(0\[1-9\]\|\[12\]\\d\|3\[01\]\)"
TIME = (r"\(\(\[01\]\\d\|2\[0-3\]\):\[0-5\]\\d:\[0-5\]\\d\(\\\.\\d\+\)\?\|" +
    r"\(24:00:00\(\\\.0\+\)\?\)\)")

NMTOKEN = XStr.xmlNmtoken
NCNAME = "^%s$" % (XStr.xmlNCName)
QNAME = "^%s$" % (XStr.xmlQName)
QQNAME = "^%s$" % (XStr.xmlQQName)


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
        "whiteSpace": "replace"
    }),
    "token": XsdType({
        "pybase": str,
        "base": "normalizedString",
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
        "pattern": NMTOKEN,
    }),
    "NMTOKENS": XsdType({
        "pybase": str,
        "list": True,
        "base": "NMTOKEN",
        "pattern": r"%s(\s+%s)*" % (NMTOKEN, NMTOKEN),
    }),
    "Name": XsdType({
        "pybase": str,
        "base": "token",
        "pattern": QQNAME,
    }),
    "NCName": XsdType({
        "pybase": str,
        "base": "Name",
        "pattern": NCNAME,
    }),
    "ID": XsdType({
        "pybase": str,
        "base": "NCName",
        "pattern": NCNAME,
    }),
    "IDREF": XsdType({
        "pybase": str,
        "base": "NCName",
    }),
    "IDREFS": XsdType({
        "pybase": str,
        "base": "IDREF",
        "list": True,
        "pattern": r"%s(\s+%s)*" % (QNAME, QNAME),
    }),
    "ENTITY": XsdType({
        "pybase": str,
        "base": "NCName",
        "pattern": NCNAME,
    }),
    "ENTITIES": XsdType({
        "pybase": str,
        "base": "ENTITY",
        "list": True,
        "pattern": r"%s(\s+%s)*" % (NCNAME, NCNAME),
    }),
    "QName": XsdType({
        "pybase": str,
        "base": "string",
        "pattern": QNAME,
        "whiteSpace": "collapse",
    }),
    "NOTATION": XsdType({
        "pybase": str,
        "base": "string",
        "pattern": QNAME,
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
        "pattern": r"(\+)?\d+",
        "range": MinMax(0, None, None, None),
    }),
    "positiveInteger": XsdType({
        "pybase": int,
        "base": "nonNegativeInteger",
        "pattern": r"(\+)?\d*[1-9]\d*",
        "range": MinMax(1, None, None, None),
    }),
    "long": XsdType({
        "pybase": int,
        "base": "integer",
        "range": MinMax(-MAXLONG-1, None, None, MAXLONG),
    }),
    "int": XsdType({
        "pybase": int,
        "base": "long",
        "range": MinMax(-MAXINT-1, None, None, MAXINT),
    }),
    "short": XsdType({
        "pybase": int,
        "base": "int",
        "range": MinMax(-MAXSHORT-1, None, None, MAXSHORT),
    }),
    "byte": XsdType({
        "pybase": int,
        "base": "short",
        "range": MinMax(-MAXBYTE-1, None, None, MAXBYTE),
    }),
    "unsignedLong": XsdType({
        "pybase": int,
        "base": "nonNegativeInteger",
        "range": MinMax(0, None, None, MAXLONG<<1 + 1),
    }),
    "unsignedInt": XsdType({
        "pybase": int,
        "base": "unsignedLong",
        "range": MinMax(0, None, None, MAXINT<<1 + 1),
    }),
    "unsignedShort": XsdType({
        "pybase": int,
        "base": "unsignedInt",
        "range": MinMax(0, None, None, MAXSHORT<<1 + 1),
    }),
    "unsignedByte": XsdType({
        "pybase": int,
        "base": "unsignedShort",
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
        "pattern": r"(\+|-)?(\d+(\.\d*)?|\.\d+)" + EXPNAN,
        "whiteSpace": "collapse",
    }),
    "double": XsdType({
        "pybase": float,
        "base": "decimal",
        "pattern": r"(\+|-)?(\d+(\.\d*)?|\.\d+)" + EXPNAN,
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
        "pattern": GYEAR + r"-" + GMONTH + r"-" + GDAY + r"T" + TIME + TZONE,
        "whiteSpace": "collapse",
    }),
    "time": XsdType({
        "pybase": time,
        "base": None,
        "pattern": TIME + TZONE,
        "whiteSpace": "collapse",
    }),
    "date": XsdType({
        "pybase": date,
        "base": None,
        "pattern": GYEAR + r"-" + GMONTH + r"-" + GDAY + TZONE,
        "whiteSpace": "collapse",
    }),
    "gYearMonth": XsdType({
        "pybase": date,
        "base": None,
        "pattern": GYEAR + r"-" + GMONTH + TZONE,
        "whiteSpace": "collapse",
    }),
    "gYear": XsdType({
        "pybase": date,
        "base": None,
        "pattern": GYEAR + TZONE,
        "whiteSpace": "collapse",
    }),
    "gMonthDay": XsdType({
        "base": None,
        "pattern": r"--" + GMONTH + r"-" + GDAY + TZONE,
        "whiteSpace": "collapse",
    }),
    "gDay": XsdType({
        "base": None,
        "pattern": r"---" + GDAY + TZONE,
        "whiteSpace": "collapse",
    }),
    "gMonth": XsdType({
        "base": None,
        "pattern": r"--" + GMONTH + TZONE,
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
        "pattern": r".*",  # Too lenient
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
# NewType mainly informs linters (and humans), for type-hinting etc.
# TODO Keep?

### Bits
base64Binary        = NewType('base64Binary', bytes)
hexBinary           = NewType('hexBinary', bytes)

### Truth values
boolean             = NewType('boolean', bool)

### Various integers
byte                = NewType('byte', int)
short               = NewType('short', int)
#int                 = NewType('int', int)
integer             = NewType('integer', int)
long                = NewType('long', int)
nonPositiveInteger  = NewType('nonPositiveInteger', int)
negativeInteger     = NewType('negativeInteger', int)
nonNegativeInteger  = NewType('nonNegativeInteger', int)
positiveInteger     = NewType('positiveInteger', int)
unsignedByte        = NewType('unsignedByte', int)
unsignedShort       = NewType('unsignedShort', int)
unsignedInt         = NewType('unsignedInt', int)
unsignedLong        = NewType('unsignedLong', int)

### Real numbers
#decimal            = NewType('decimal', float)
double              = NewType('double', float)
#float               = NewType('float', float)

### Dates and times (unfinished)
gDay                = NewType('gDay', int)
gMonth              = NewType('gMonth', int)
gMonthDay           = NewType('gMonthDay', str)
gYear               = NewType('gYear', date)
gYearMonth          = NewType('gYearMonth', date)
date                = NewType('date', date)
dateTime            = NewType('dateTime', datetime)
time                = NewType('time', time)
duration            = NewType('duration', timedelta)

### Strings
language            = NewType('language', str)
normalizedString    = NewType('normalizedString', str)
string              = NewType('string', str)
token               = NewType('token', str)
anyURI              = NewType('anyURI', str)

### XML constructs (note caps)
XmlName             = NewType('XmlName', str)
XmlQName            = NewType('XmlQName', str)
XmlNmtoken          = NewType('XmlNmtoken', str)

ID                  = NewType('ID', str)
IDREF               = NewType('IDREF', str)
IDREFS              = NewType('IDREFS', str)  # [str]
Name                = NewType('Name', str)
NCName              = NewType('NCName', str)
NMTOKEN             = NewType('NMTOKEN', str)
NMTOKENS            = NewType('NMTOKENS', str)  # [str]
QName               = NewType('QName', str)
ENTITY              = NewType('ENTITY', str)
ENTITIES            = NewType('ENTITIES', str)  # [str]


###############################################################################
# TODO Sync w/ lxml or similar.
#
class ContentType(Enum):
    """Predicated of each element type
    """
    EMPTY   = 0     # EMPTY
    PCDATA  = 1     # #PCDATA allowed
    ELEMENT = 2     # Element(s) allowed
    ANY     = 3     # Mixed content (includes ANY)

    # Extras
    CDATA   = 8

    def tostring(self):
        if self == ContentType.EMPTY: return "EMPTY"
        if self == ContentType.PCDATA: return "(#PCDATA)"
        if self == ContentType.ELEMENT:
            raise ValueError("No export for dcl content 'ELEMENT' extension.")
        return "ANY"

class SeqType(Enum):
    """Predicated of each ()-group in a model.
    """
    CHOICE = "|"      # (x | y | z)
    ALL = "&"         # (x & y & z)   # SGML only
    SEQUENCE = ","    # (x, y, z)


class RepType:
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

class ModelItem:
    """One item (and element name with a rep, or just #PCDATA).
    """
    def __init__(self, name:NmToken, rep:RepType=None):
        self.name = name
        self.rep = rep

    def tostring(self) -> str:
        return self.name + (self.rep.tostring() if self.rep else "")

class ModelGroup:
    """Any parenthesized group, with ModelItem members, plus connector and rep.
    Maybe keep the original string (if any), or a list of PEs in it?
    """
    def __init__(self, items:List=None, seq:SeqType=None, rep:RepType=None):
        self.items = items
        self.seq = seq
        self.rep =  rep

    def getNames(self):
        """Extract the set of all names used anywhere in a model.
        """
        names = set()
        for item in self.items:
            if isinstance(item, ModelItem):
                names = names.union([item.name])
            elif isinstance(item, ModelGroup):
                names = names.union(item.getNames())
        return names

    def tostring(self):
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
    """The top model, which can be a declared content keyword OR a ModelGroup.
    This also converts a token sequence to the model ASN.
    """
    def __init__(self, contentType:ContentType=None, tokens:List[str]=None):
        super(). __init__()
        self.contentType = contentType
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
            elif t in "|&,":
                if pstack[-1].seq != t:
                    if pstack[-1].seq is None: pstack[-1].seq = t
                    else: raise SyntaxError("Inconsistent connectors.")
            elif XStr.isXmlName(t):
                newItem = ModelItem(t)
                pstack[-1].items.append(newItem)
                if i+1 < len(tokens) and isinstance(tokens[i+1], RepType):
                    newItem.rep = tokens[i+1]
                    i += 1
            else:
                raise SyntaxError(f"Unexpected model token '{t}'.")
        if (len(pstack) != 1):
            raise SyntaxError("Unbalanced () in model.")

    def tostring(self):
        if self.contentType: return self.contentType.tostring()
        else: return super().tostring()

class ElementDef:
    def __init__(self, name:NmToken, model:Model):
        self.name = name
        self.model = model
        self.attributeDefs = None
        self.allowText:bool = True
        self.allowAnywhere:Set = None
        self.allowNowhere:Set = None
        self.readOrder = 0

    def tostring(self) -> str:
        buf = "<!ELEMEMT %-12s %s>\n" % (self.name, self.model.tostring())
        # TODO Add attlist?
        return buf

class ComplexType:
    def __init__(self, name:str, model:Model):
        self.name = name
        self.model = model


###############################################################################
# TODO Move attr stuff to separate file
#
class AttrDefault(Enum):
    REQUIRED = "#REQUIRED"
    IMPLIED = "#IMPLIED"
    FIXED = "#FIXED"

class AttributeDef:
    def __init__(self, name:NmToken, aname:NmToken, atype:str, adefault:Any):
        self.name = name
        self.aname = aname
        self.atype = atype
        self.adefault = adefault
        self.caseTx = None
        self.multi = False
        self.enumList = None

    def enumSpec(self):
        if self.enumList: return " (%s)" % (" | ".join(self.enumList))
        return None

class AttlistDef(dict):
    def __init__(self, name:str):  # Or list of enames?
        self.name = name
        self.attrs = {}

    def __setitem__(self, aname:NmToken, atype:str, adefault:Any=None) -> AttributeDef:
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
    def __init__(self, name:NmToken,
        etype:EntityType,
        dataSource:DataSource,
        parseType:EntityParseType=EntityParseType.PCDATA,
        notation:NmToken=None
        ):
        self.name = name
        self.etype = etype
        self.dataSource = dataSource
        self.parseType = parseType
        self.notation = notation
        self.localPath = None

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
    def __init__(self, name:NmToken, dataSource:DataSource):
        if (dataSource.literal is not None):
            raise SyntaxError("NOTATION {nname} has QLit, not PUBLIC or SYSTEM.")
        self.name = name
        self.dataSource = dataSource

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
    def nodeValue(self):
        return None

    def after(self, stuff:List):
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

    def before(self, stuff:List):
        """Inserts a set of Node or string objects in the child list of the
        parent, just before this node.
        """
        par = self.parentNode
        for thing in stuff:
            par.insertBefore(self, thing)

    def removeNode(self):
        """Removes this object from its parent child list.
        """
        par = self.parentNode
        par.removeChild(self)

    def replaceWith(self, stuff:List):
        """Replaces the document type with a set of given nodes.
        """

    ####### EXTENSIONS

    def reindex(self):
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
    def getElementDef(self, name:NmToken):
        return self.elementDefs[name] if name in self.elementDefs else None

    def defineElement(self, name:NmToken, modelInfo):
        assert name not in self.elementDefs
        self.elementDefs[name] = modelInfo

    # Attribute
    def getAttributeDef(self, ename:NmToken, aname:NmToken):
        if ename not in self.elementDefs: return None
        edef = self.elementDefs[ename]
        if aname not in edef.attributeDefs: return None
        return edef.attributeDefs[aname]

    def defineAttribute(self, ename:NmToken, aname:NmToken,
        atype:NmToken="CDATA", adefault:NmToken="IMPLIED"):
        assert aname not in self.attributeDefs
        self.elementDefs[(ename)].attributeDefs[aname] = [ atype, adefault ]

    # Entity (subtypes for General, Parameter, Notation, and NameSet)
    def getEntityDef(self, name:NmToken):
        return self.entityDefs[name] if name in self.entityDefs else None

    def defineEntity(self, name:NmToken,
        literal:str=None, publicId:str=None, systemId:str=None,
        parseType:EntityParseType=EntityParseType.PCDATA, notation:NmToken=None):
        assert name not in self.entityDefs
        assert isinstance(parseType, EntityParseType)
        ds = DataSource(literal, publicId, systemId)
        self.entityDefs[name] = EntityDef(name, EntityType.GENERAL,
            dataSource=ds, parseType=parseType, notation=notation)

    def getPEntityDef(self, name:NmToken):
        return self.pentityDefs[name] if name in self.pentityDefs else None

    def definePEntity(self, name:NmToken,
        literal:str=None, publicId:str=None, systemId:str=None):
        assert name not in self.pentityDefs
        self.entityDefs[name] = EntityDef(name,
            EntityType.PARAMETER, literal, publicId, systemId)

    def getNotationDef(self, name:NmToken):
        return self.notationDefs[name] if name in self.notationDefs else None

    def defineNotation(self, name:NmToken,
        literal:str=None, publicId:str=None, systemId:str=None):
        assert name not in self.notationDefs
        self.notationDefs[name] = EntityDef(name,
            EntityType.NOTATION, literal, publicId, systemId)

    # Basic operations
    #
    def cloneNode(self, deep:bool=False):
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
