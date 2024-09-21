#!/usr/bin/env python3
# DocType class: split from basedom 2024-06-28 sjd.
#
#
import re
from enum import Enum
from datetime import datetime  #, date, time
from typing import List, Set, Iterable

from xmlstrings import XmlStrings as XStr
from basedom import Node, NodeTypes, CaseTx

NmToken = str
DOCUMENT_TYPE_NODE = 10

descr = """
This library provides a basic interface to XML schema information.
An instance should be loadable from XSD, RelaxNG, or DTD, and provide a
common API for any of them. That's a tall order, so I'm just starting
with DTDs as the simplest place to start. That should at least help with
converting DTDs to the others, which is commonly desired.

The hardest bits will likely be (a) preserving DTD classes implemented via
parameter entities, and (b) making that compatible with XSD complex types.

I may also integrate the shorthand declarations I rough out in XSD_compact
and elsewhere. ?


==Extensions==

DTDs are extended in these ways:

* New declaration types

** Add PATH, which takes a bunch of system ids as places to look to
find other system id that don't start with "/" or "file:///".
    <!PATH "c:\\stuff" "/Users/jsmith/XML/entities"...>

** Add distinct CHAR declarations for special-character entities.
They are just like ENTITY declarations, but can only have a qlit value,
which must resolve to a single Unicode character.
    <!CHAR bull 0x2022>
    <!CHAR nbsp 160>

** Add CTYPE declarations to correspond to XSD complex types. They
can be referenced within content models via #xxx (think of them as
custom reserved words; they cannot be named "PCDATA" etc). They are retained
when the model is parsed.
    <!CTYPE fontish "i b u tt">

*** Possibly add set operations on them?
    <!CTYPE inlines (#fontish) - (tt) + (em string sup sub)>

** Add LITERAL declaration, just like ENTITY except only qlit value.
     <!LITERAL foo "hello">

** Extend ENTITY to allow multiple SYSTEM identifier literals, to be
tried from left to right.
    <!ENTITY chap2 SYSTEM "/home/ents/chap2.xml" "/xml/common/ents/chap2.xml">

** Add MIXIN declarations to allow things like footnote anywhere in certain elements.
    <!MIXIN footnote (div ul ol)>
    <!MIXON del      *>


* Elements

** Add {m,n} suffix where [*+?] go.

** Recognize %... to refer to CTYPE items within content models

** For consistency, allow "*" as a synonym for "ANY":
    <!ELEMENT stuff *>

** For consistency, allow "()" as a synonym for "EMPTY":
    <!ELEMENT hr ()>


* Attributes

* Add "*" as a reserved name in ATTLIST, to declare global attributes.
    <!ATTLIST * id #IMPLIED

* Allow multiple SYSTEM identifiers, used from left to right.

* Allow fragment identifiers on SYSTEM identifiers?

* attribute types: all XSD built-in types, plus .



===Attributes
    * Add all xsd built-in types
    * Generalize repeatability -- just suffix type with *?+ or {}
    * Add COID -- must be >1, on same eltype, unique within eltype
    * Add SCOPEID -- unique within ancestor of type
    * Add STACKID -- value is accumulated by attr type

===Content models
    * content model tokens with {}
    * incl/excl exceptions (but no whitespace effects!)

===Entities etc.===
    * Multiple qlits for SYSTEM ID
    * <!ENTITY name SET (x y z)>
    * <!ENTITY name PREFIX ...>
    * <!NOTATION name IXML ...


==See also==
IBM’s Websphere Development Studio Client (WDSC) has a utility that converts DTDs to XSDs. While in WDSC right click on the DTD and select Generate→ XML Schema.


==To do==
    * Figure out catalog/path interface
    * How to store state of in-progress element validation? API?
    * XSD facets
    * Namespaced IDs?
    * Attr casting -- offer setCasterCallback?
    * Easy way to support attr types/defaults in doc?
      Why not just ATTLIST?
      types = r"CDATA|ID|IDREF|IDREFS|ENTITY|ENTITIES|NMTOKEN|NMTOKENS"
      dfts = r"#REQUIRED|#IMPLIED|#FIXED"  # Plus maybe more
      qLit =  r"('[^']*'|"[^"]*")"
      r"<!ATTLIST (\\w+) (\\w+) ({type}|NOTATION|\\([^\\)]+\\)) ({dft}) ({qLit})>"
"""


###############################################################################
#
class BaseTypes(Enum):
    """Map each XSD type to an underlying Python/generic types.
    How best to treat *semantic* attr types like IDs, ENTITIES, etc?
        (not to mention conref, current, etc.
    """
    BIT = bool
    NUM = float
    INT = int
    STR = str
    BIN = bytes
    TIM = datetime

floatExpr = r"([-+]?\d+(\.\d+)([eE][-+]?\d+)?)|INF|-INF|NaN"
dateExpr = r"\d\d\d\d:\d\d:\d\d"
timeExpr = r"\d\d:\d\d:\d\d(\.\d+)?"
datetimeExpr = dateExpr + "T" + timeExpr
uintExpr = r"\d+"
intExpr = r"[-+]?d+"
negintExpr = r"(-\d+)"
posintExpr = r"\+?\d+"
XMLNAMEExpr = r"[.\w][-.\w]*"
URIExpr = r"(([a-zA-Z0-9-$_.+!*,();/?:@=&])|(%\x\x))+"

XMLNAMEExprS = r"%s(\s+%s)*" % (XMLNAMEExpr, XMLNAMEExpr)

isX = XStr.isXmlName

B = BaseTypes

class AttrTypes(Enum):
    """See [https://www.w3.org/TR/xml/]
    """
    # XSD NAME          sup    regex
    boolean =          (B.BIT, r"true|1|false|0" )

    # Floats
    decimal =          (B.NUM, r"[-+]?\d+(\.\d+)" )
    double =           (B.NUM, floatExpr )
    float =            (B.NUM, floatExpr )

    # Ints
    byte =             (B.INT, intExpr )
    int =              (B.INT, intExpr )
    integer =          (B.INT, intExpr )
    long =             (B.INT, intExpr )
    short =            (B.INT, intExpr )
    nonPositiveInteger=(B.INT, negintExpr+"|0+" )
    negativeInteger =  (B.INT, negintExpr )
    nonNegativeInteger=(B.INT, posintExpr+"|0+" )
    positiveInteger =  (B.INT, posintExpr )
    unsignedByte =     (B.INT, posintExpr )
    unsignedInt =      (B.INT, posintExpr )
    unsignedLong =     (B.INT, posintExpr )
    unsignedShort =    (B.INT, posintExpr )

    # Date/time stuff (TODO: Support partials?)
    date =             (B.TIM, date,  dateExpr )
    dateTime =         (B.TIM, datetime, datetimeExpr )
    gDay =             (B.TIM, uintExpr )
    gMonth =           (B.TIM, uintExpr )
    gMonthDay =        (B.TIM, uintExpr )
    gYear =            (B.TIM, uintExpr )
    gYearMonth =       (B.TIM, uintExpr )
    time =             (B.TIM, time,  timeExpr )
    duration =         (B.TIM, None ),  # TODO Add

    # Strings
    language =         (B.STR, r"\w+" )
    normalizedString = (B.STR, r"[^\r\n\t]*" )
    string =           (B.STR, r".*" )
    token =            (B.STR, r"[^\s]( ?[^\s]+)*" )
    anyURI =           (B.STR, URIExpr )
    ID =               (B.STR, XMLNAMEExpr )
    IDREF =            (B.STR, XMLNAMEExpr )
    XMLNAME =          (B.STR, XMLNAMEExpr )
    NMTOKEN =          (B.STR, XMLNAMEExpr )  # TODO Loosen

    # Plurals
    IDREFS =           (B.STR, XMLNAMEExprS )
    NMTOKENS =         (B.STR, XMLNAMEExprS )

    # Binaries
    base64Binary =     (B.BIN, r"[+/=a-zA-Z0-9]+" )
    hexBinary =        (B.BIN, r"([\da-fA-F][\da-fA-F])+" )

    # Additions beyond XSD built-ins
    CDATA =             (B.STR, r".*" )
    ENTITY =            (B.STR, XMLNAMEExpr)
    NOTATION =          (B.STR, XMLNAMEExpr)
    ENUM =              (B.STR, XMLNAMEExpr)  # How to set up?
    ENTITIES =          (B.STR, XMLNAMEExprS)

    QXMLNAME =         (B.STR, r"%s:%s" % (XMLNAMEExpr, XMLNAMEExpr) )
    NCXMLNAME =        (B.STR, XMLNAMEExpr )


class AttrDefaults(Enum):
    REQUIRED = "#REQUIRED"
    IMPLIED = "#IMPLIED"
    FIXED = "#FIXED"


###############################################################################
#
class EntityType(Enum):
    GENERAL = 1
    PARAMETER = 2
    NOTATION = 4
    NAMESET = 8
    CHAR = 16

class EntitySource(Enum):
    INTERNAL = 1  # Quoted literal
    EXTERNAL = 2  # PUBLIC, SYSTEM ID(s), etc.

class EntityParseType(Enum):  # Includes extras...
    PCDATA  = 0
    CDATA   = 1
    RCDATA  = 2
    NDATA   = 4
    # SGML also has STARTTAG ENDTAG
    # Maybe special for CHAR EntityType?


###############################################################################
# Stub classes for schema constructs (DTD-ish for the moment).
#
class DataLoc:
    def __init__(self, literal:str=None, publicId:str=None, systemId:str=None):
        pass

class Def:
    def __init__(self, name):
        self.name = name


###############################################################################
#
class ElementDef(Def):
    def __init__(self, name:str, aliasFor:str, model):
        super(ElementDef, self).__init__(name)
        self.aliasFor = aliasFor
        self.model = model
        self.attributeDefs = None
        self.allowText:bool = True
        self.allowAnywhere:Set = None
        self.allowNowhere:Set = None


class ModelTypes(Enum):
    EMPTY = 0
    ANY = 1
    TEXTONLY = 2
    CHOICE = 3
    ALL = 4
    SEQUENCE = 5
    GROUP = 6
    ATTRGROUP = 7


class ComplexType:
    def __init__(self, typename:str, model:str):
        self.typename = typename
        self.modelType = ModelTypes.SEQUENCE
        self.model = model
        self.minOccurs = 1
        self.maxOccurs = 1
        self.mixins = None


class AttributeDef(Def):
    def __init__(self, name:str, attrType:AttrTypes, default:str):
        super(AttributeDef, self).__init__(name)
        self.attrType = attrType
        self.caseTx = CaseTx.NONE
        self.wsNorm = None
        self.multi = False
        self.enumList = None
        self.default = default


class EntityDef(Def):
    """Any of several subtypes.
    """
    def __init__(self, name:str, etype:EntityType,
        literal:str=None, publicID:str=None, systemID:str=None,
        parseType:EntityParseType=EntityParseType.PCDATA,
        notation:str=None,
        members:Iterable=None
        ):
        super(EntityDef, self).__init__(name)
        self.etype = etype
        self.literal = literal
        self.publicID = publicID
        self.systemID = systemID
        self.localPath = None
        self.parseType = parseType
        self.notation = notation
        self.members = members


###############################################################################
#
class DocumentType(Node):
    """Just a stub for the moment.
    See also my Schemas.py, and https://docs.python.org/3.8/library/xml.dom.html
    """
    def __init__(self, qualifiedName:str, ownerDocument=None, doctypeString:str='',
        publicId:str='', systemId:str=''):
        super(DocumentType, self).__init__(
            ownerDocument=ownerDocument,
            nodeName="#doctype", nodeType=NodeTypes.DOCUMENT_TYPE_NODE)

        self.name = self._nodeName = qualifiedName  # Should come from the DOCTYPE
        self.publicId = publicId
        self.systemId = systemId
        self.userData = None

        self.doctypeString = doctypeString
        # self.internalSubset = None  # As a string
        if (qualifiedName and doctypeString and
            not doctypeString.strip().startswith(qualifiedName)):
            raise ValueError("doctype mismatch, '%s' vs. '%s'." %
                (qualifiedName, doctypeString))

        self.elementDefs = None
        self.attributeDefs = None  # NamedNodeMap() later if needed

        # These are all considere types of entities:
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
        if (rsib):
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
            if   (isinstance(ch, ElementDef)):   self.elementDefs[ch.name] = ch
            elif (isinstance(ch, AttributeDef)): self.attributeDefs[ch.name] = ch
            elif (isinstance(ch, EntityDef)):
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
        if (ename not in self.elementDefs): return None
        edef = self.elementDefs[ename]
        if (aname not in edef.attributeDefs): return None
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
        self.entityDefs[name] = EntityDef(name,
            EntityType.GENERAL, literal, publicId, systemId, parseType, notation)

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

    def defineNameSet(self, name:NmToken, members:Iterable):
        self.nameSetDefs[name] = EntityDef(
            name, EntityType.NAMESET, members=members)

    # Basic operations
    #
    def cloneNode(self, deep:bool=False):
        newNode = DocumentType(
            qualifiedName=self.name,
            ownerDocument=self.ownerDocument,
            doctypeString=self.doctypeString,
            publicId = self.publicId,
            systemId = self.systemId
        )
        if (deep): newNode.elementDefs = self.elementDefs.deepcopy()
        else: newNode.elementDefs = self.elementDefs.copy()
        if (self.userData): newNode.userData = self.userData
        return newNode

    def isEqualNode(self, n2) -> bool:  # Doctype
        if (self.nodeType != n2.nodeType): return False
        if (self.doctypeString != n2.doctypeString): return False
        #if (self._nodeName!=n2._nodeName or  # TODO: Check
        #    self.publicId!=n2.publicId or
        #    self.systemId!=n2.systemId): return False
        # TODO Check: do we compare the document, too?
        docel1 = self.ownerDocument.documentElement
        docel2 = n2.ownerDocument.documentElement
        if (not docel1.isEqualNode(docel2)): return False
        return True

    ####### EXTENSIONS

    @property
    def outerXML(self) -> str:  # Notation
        """TODO: Generate entity and notation dcls?
        """
        buf = ('<!DOCTYPE %s  PUBLIC "%s" "%s" [ %s ]>' + "\n") % (
            self._nodeName, self.publicId, self.systemId, "[]")
        return buf

    @property
    def innerXML(self) -> str:  # Notation
        return self.data

    def tostring(self) -> str:  # Notation
        return self.outerXML



    ###########################################################################
    # Parsing and grammar
    #
    # TODO: Change all the spaces to \s*, doubles to \s+
    #
    name = r"[\w][-.\w]*"
    names = r"{name}(  {name})*"
    qlit = r"\"[^\"]*\"|\'[^\']*\'"
    rep = r"""([*+?]|\{\d*,\d*\})"""
    ctref = r"""%\w+;"""
    modelToken = r"""(#PCDATA)?|{name}{rep}?|{ctref}{rep}?"""
    plist = r"""  {modelToken}(  [|,  {modelToken}  """  # Only works if next thing is different
    source = f"""PUBLIC  (?P<pub>{qlit})  (?P<sys>{qlit})|SYSTEM  (?P<sys>{qlit})|(?P<lit>{qlit})"""
    subset = r"""\[ [^]* ]"""
    docTypeExpr = f"""<!DOCTYPE  ({name})  ({source})  ({subset})  >"""
    model = f"""{plist}|EMPTY|ANY|#PCDATA"""
    incl = r" \+\({names}\)"
    excl = r" -\({names}\)"
    elemExpr = f"""<!ELEMENT  ({name})  ({model})  {incl}?  {excl}  >"""
    atyp = "|".join(list(AttrTypes.__members__.keys()))
    adft = "|".join(list(AttrDefaults.__members__.keys())) + f"({qlit})?"
    attrExpr = f"""<!ATTLIST  ({name})  (  ({name})  ({atyp})  ({adft})  )+  >"""
    ndata = f"""NDATA  ({name})"""
    entExpr = f"""<!ENTITY  (%)?  ({name})  ({source})  ({ndata}))?  >"""
    notExpr = f"""<!NOTATION  ({name})  ({source})  >"""

    def parseDoctypeString(self, s:str):
        """Parse the DOCTYPE declaration:
            <!DOCTYPE rootName PUBLIC "" "" [...]>
        """
        mat = re.match(DocumentType.docTypeExpr, s)
        self._nodeName = mat.group(1)
        self.publicId = mat.group("pub")
        self.systemId = mat.group("sys")
        self.publicId = mat.group("lit")[1:-1]
        self.parseInternalSubset()

    def parseInternalSubset(self):  # TODO subset
        pass

    # end class DocumentType

DocType = DocumentType


###############################################################################
#
class ExtraDcls:
    names     = r"""({name})(\s+{name})*"""
    baseInt   = r"""(0x[\da-f]+|\d+)"""
    charExpr  = r"""<!CHAR  ({name})  ({baseInt})(  ,  ({name})  ({baseInt}))*  >"""
    litExpr   = r"""<!LITERAL  ({name})  ({qLit})  >"""
    ctypeExpr = r"""<!CTYPE  ({name})  ({names})  >"""
    mixinExpr = r"""<!MIXIN  ({name})  ({names})  >"""
    pathExpr  = r"""<!PATH(  {qLit})*  >"""
