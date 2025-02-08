#!/usr/bin/env python3
# DocementType class: split from basedom 2024-06-28 sjd.
#
#
import os
import codecs
from collections import defaultdict, namedtuple
from typing import List, Set, Dict, Union  # Any,
import logging

from basedomtypes import (NMTOKEN_t, QName_t, FlexibleEnum,
    NSuppE, DOMException, ICharE)  # NodeType
from domenums import RWord
from xmlstrings import XmlStrings as XStr, CaseHandler, UNormHandler, WSHandler
from basedom import Node
from xsdtypes import XSDDatatypes

lg = logging.getLogger("documenttype")

descr = """
This library provides a basic interface to schema information, whether created
via the API, an XML (or perhaps SGML) DTD, an XML Schems, or (eventually) a Relax-NG schema (I'm less
familiar with those, so that may be a while). The idea here is to get any
schema into a common API that parsers and validators can talk to.

There are a lot of classes, but most are quite small and correspond closely
to SGML/HTML/XML/XSD notions. Enums in here generally include the union
of possibilities (for example, #CURRENT has a defined name even though
it is only used in SGML).
Unnamed options such as having NO repetition or no seq operator (as for
singleton model groups) have corresponding enum values for expliciteness.


* SimpleType/attribute stuff (perhaps split to separate file?)

    ** DerivationLimits(FlexibleEnum): Ways to derive types
    (extension, etc)

    ** SimpleType(dict): Basicallly like XSD, a name, base type
    (plus corresponding Python type if any), and selected facets

    ** XsdType(dict): The set of built-in XSD datatypes, with their facets

    ** DateTimeFrag: Support for fragmentary dates/times per XSD

    ** XsdFacet(Enum): The set of known XSD facets

    ** AttributeDef: A single attribute with name/type/default

    ** AttlistDef(dict): A bundle of attributes. These must be attached to
the Doctype, and to their element(s)


* ComplexType(SimpleType): Basically like XSD or SGML Element

    ** ContentType(FlexibleEnum): ANY, EMPTY, etc., or X_MODEL

    ** DclType(FlexibleEnum):  Attribute declared types (cf XsdType)

    ** DftType(FlexibleEnum):  Attribute defaults (#IMPLIED etc., or X_LITERAL)

    ** SeqType(FlexibleEnum):  OR vs. SEQ vs. the late AND

    ** RepType(FlexibleEnum):  *?+ or {} like XSD min/maxOccurs

    ** ModelItem: A token + RepType in a content model

    ** ModelGroup: A group in a content model

    ** Model(ModelGroup): An *entire* content model or declared content value

    ** ElementDef(ComplexType): An element declaration (name(s?) plus Model)
    Cf ComplexType


* Entity stuff

    ** EntitySpace(FlexibleEnum): What kinds of entities we got?
    parameter, general, ndata, maybe sdata

    ** EntityParsing(FlexibleEnum): Parsing constraint on entity

    ** EntityDef: An entity declaration


* Notation stuff (treated as a quasi-entity)

    ** Notation: A notation declaration: name, publicID, systemID(s)

* Document stuff

    ** DocumentType(Node):
"""


###########################################################################
#
class DerivationLimits(FlexibleEnum):
    """for XSD .block and .final
    """
    NONE = "NONE"
    EXTENSION = "EXTENSION"
    RESTRICTION = "RESTRICTION"
    ALL = "ALL"


###########################################################################
#
class SimpleType(dict):
    def __init__(self, name:NMTOKEN_t, baseType:NMTOKEN_t):
        self.name = name
        self.baseType = baseType
        self.restrictions = {}
        self.memberTypes = None  # For list and union types
        self.caseTx = CaseHandler.NONE


###########################################################################
#
class DclType(FlexibleEnum):  # For attributes
    CDATA     = "CDATA"
    NDATA     = "NDATA"
    RCDATA    = "RCDATA"      # In case of SGML
    SDATA     = "SDATA"       # In case of SGML


###########################################################################
#
class DftType(FlexibleEnum):  # For attributes
    REQUIRED  = "#REQUIRED"
    IMPLIED   = "#IMPLIED"
    FIXED     = "#FIXED"
    X_VALUE   = "X_VALUE"     # Set when there's a literal default value
    CONREF    = "#CONREF"     # In case of SGML
    CURRENT   = "#CURRENT"    # In case of SGML


###########################################################################
# An AttrKey is what attributes are index by in a Doctype. Elements also
# have their own list of attributes, which should probably point via one of
# these, though one of these could apply to many elements. Is an attribute
# identified by
#   * the attribute name, in a given namespace
#   * the attribute name and a single element (q)name (on which it occurs)
#   * the attribute name and the element (q)name(s) from the same ATTLIST dcl
#   * the attribute name, regardless
#   ...
#
AttrKey = namedtuple("AttrKey", [ "ens", "ename", "ans", "aname" ])

class AttributeDef:
    """Define an Attribute. This can be handed information from parsing
    a schema, or just be called on the fly. There does not have to be
    an element of the given name defined (either now or later).

    This does NOT save/attach the definition anywhere. Caller must do that.
    """
    def __init__(self,
        ens:NMTOKEN_t, ename:NMTOKEN_t,
        ans:NMTOKEN_t, aname:NMTOKEN_t,
        atype:NMTOKEN_t, adfttype:DftType,
        literal:str=None, readOrder:int=0):
        self.ens = ens
        self.ename = ename  # TODO Provide for element name lists? What about NS?
        self.ans = ans
        self.aname = aname
        self.atype = atype   # TODO string or a type object?
        self.adfttype = adfttype
        self.literal = literal
        self.readOrder = readOrder

        self.caseTx = "NONE"
        self.enumValues:dict = None

        if not XStr.isXmlQName(aname): raise ICharE(
             "Bad name '{aname}' for attribute.")
        if atype not in XSDDatatypes and not isinstance(atype, type): raise TypeError(
            "Unrecognized type for attribute {aname} for {self.name}.")
        if adfttype is not None:
            pass  # TODO

    def enumSpec(self) -> str:
        if self.enumValues: return " (%s)" % (" | ".join(self.enumValues))
        return None

    def getKey(self):
        """Return a hashable key for this attribute.
        """
        return AttrKey(self.ens, self.ename, self.ans, self.aname)

class AttlistDef(dict):
    """Represent an entire ATTLIST declaration.
    But how are attributes attached? A copy to each element? Or one object
    per ATTLIST and pointers from elements? And do the attributes identify
    their owner element(s), or just via their ATTLIST?
    Who creates/attaches the element if it's not already there?  TODO
    """
    def __init__(self, enames:Union[str, List[str]], readOrder:int=0):
        """Add the individual attrs with __setitem__. The AttlistDef crosses
        a set of elements, with a set of attributes. We actually *need* readOrder
        because in case of duplicates attr names for a single elements, 1st applies.
        Eventually
        """
        self.enames = enames if isinstance(enames, list) else [ enames ]
        bads = []
        for ename in self.enames:
            if not XStr.isXmlQName(ename): bads.append(ename)
        if bads: raise ICharE(
            "Bad element name(s) {bads} in ATTLIST.")
        self.readOrder = readOrder
        self.attributes = {}

    def __setitem__(self, aname:NMTOKEN_t, atype:str, adfttype:DftType=None) -> AttributeDef:
        """Just makes an attribute; caller must attach to element, doctype.
        """
        if aname in self.attributes:
            raise KeyError("Attribute {aname} already defined for {self.name}.")
        adef = AttributeDef(ens=None, ename=None, ans=RWord.NS_ANY, aname=aname,
            atype=atype, adfttype=adfttype, readOrder=len(self.attributes))
        self.attributes[(RWord.NS_ANY, aname)] = adef
        return adef

    def tostring(self) -> str:
        buf = "<!ATTLIST (%s) " % (", ".join(self.enames))
        for aname, aobj in self.items():
            buf += "\n    %16s %16s %s" % (aname, aobj.enumSpec(), aobj.adfttype)
        buf += ">\n"
        return buf


###############################################################################
# ELEMENT / ComplexType Stuff
#
class ComplexType(SimpleType):
    def __init__(self, name:NMTOKEN_t, baseType=None, model:'Model'=None):
        super().__init__(name=name, baseType=baseType)
        self.abstract = False
        self.final = None
        self.block = None
        self.attributeDefs:Dict[AttrKey, 'AttributeDef'] = {}
        self.contentType = None
        self.model = model

class ContentType(FlexibleEnum):  # For elements
    ANY       = "ANY"
    EMPTY     = "EMPTY"
    PCDATA    = "#PCDATA"
    # TODO: Are these better names X_, or just plain?
    X_MODEL   = "X_MODEL"     # Has content model, not one of the above
    X_ELEMENT = "X_ELEMENT"   # HERE -- for element-only content

class SeqType(FlexibleEnum):  # For ModelGroups
    NOSEQ     = ""            # Only for singleton groups
    SEQUENCE  = ","
    CHOICE    = "|"
    ALL       = "&"

UNLIMITED = -1  # (or None?)

class RepType(FlexibleEnum):  # For ModelItems and ModelGroups
    # TODO Figure out best way to deal with {} case
    # Why shouldn't this be available for List attributes too?
    NOREP   = ""
    STAR    = "*"
    PLUS    = "+"
    QUEST   = "?"
    X_BOUNDS= "{}"            # Like regex and xsd

    def __init__(self, minOccurs:int=1, maxOccurs:int=1):
        try:
            self.minOccurs = int(minOccurs)
        except (TypeError, ValueError):
            self.minOccurs = 0
        try:
            self.maxOccurs = int(maxOccurs)
        except (TypeError, ValueError):
            self.maxOccurs = 0

    def setBounds(self, minOccurs:int=None, maxOccurs:int=None) -> None:
        """Mainly meant for X_BOUNDS case and XSD-based usage.
        """
        if self.value == "*":
            self.minOccurs = 0; self.maxOccurs = UNLIMITED
        elif self.value == "+":
            self.minOccurs = 1; self.maxOccurs = UNLIMITED
        elif self.value == "?":
            self.minOccurs = 0; self.maxOccurs = 1
        elif self.value == "":
            self.minOccurs = 1; self.maxOccurs = 1
        else:
            self.minOccurs = 0
            if self.minOccurs is not None: self.minOccurs = minOccurs
            self.maxOccurs = UNLIMITED
            if self.maxOccurs is not None: self.maxOccurs = maxOccurs
        if (self.minOccurs >= 0 and self.maxOccurs >= 0
            and self.minOccurs > self.maxOccurs): raise SyntaxError(
                "Occurrence bounds out of order: min %d, max %d."
                % (self.minOccurs, self.maxOccurs))

    def tostring(self) -> str:
        if self.minOccurs == 0:
            if self.maxOccurs == 1: return "?"
            if self.maxOccurs == UNLIMITED: return "*"
        elif self.minOccurs == 1:
            if self.maxOccurs == 1: return ""
            if self.maxOccurs == UNLIMITED: return "+"
        return "{%d,%d}" % (self.minOccurs, self.maxOccurs)


###############################################################################
#
class ModelItem:
    """One item (an element name with a rep, or just #PCDATA).
    BS integration?
    """
    def __init__(self, name:NMTOKEN_t, rep:RepType=RepType.NOREP):
        assert name == ContentType.PCDATA.value or XStr.isXmlNMTOKEN(name)
        self.name = name
        self.rep = rep

    def tostring(self, indent:str="") -> str:
        return indent + self.name + self.rep.tostring()

class ModelGroup:
    """Any parenthesized group, with ModelItem and/or ModelGroup members,
    plus sequence and rep settings.
    Maybe keep the original string, or a list of PEs in it?
    """
    def __init__(self, childItems:List[Union['ModelGroup', ModelItem]]=None,
        seq:SeqType=None, rep:RepType=None):
        if not seq: self.seq = SeqType.NOSEQ
        else: self.seq = SeqType(seq) or SeqType.NOSEQ
        if not rep: self.rep = RepType.NOREP
        else: self.rep = RepType(rep) or RepType.NOREP
        self.childItems = childItems or []

    def getNames(self) -> Set:
        """Recursively extract the set of all names used anywhere within.
        """
        names = set()
        for childItem in self.childItems:
            if isinstance(childItem, ModelItem):
                names.add(childItem.name)
            elif isinstance(childItem, ModelGroup):
                names.union(childItem.getNames())
            else:
                raise NSuppE(f"Unexpected type '{type(childItem)}' in ModelGroup.")
        return names

    def tostring(self, indent:str=None) -> str:
        """TODO Maybe re-introduce PEs or complex types?
        """
        if not self.childItems: return "()"
        buf = ""
        connector = self.seq.value
        for ch in self.childItems:
            if not buf: buf = f"\n{indent}({ch.tostring()}"
            else: buf +=  f" {connector} {ch.tostring()}"
        return buf + ")"

class Model(ModelGroup):
    """The whole/top model, which can be a declared content keyword OR
     a model group (passed here as a List of string tokens.
     Tokens are converted to an AST of ModelGroups and ModelItems.

    childItems comes in as List[str], for example:
        [ "(", "i", "|", "b", "*", "|", "tt", ")", "+" ]
    """
    def __init__(self, tokens:List[str]=None, seq:SeqType=None, rep:RepType=None,
        contentType:ContentType=None):
        super(). __init__(None, None, None)
        if contentType is None:
            self.contentType = ContentType.X_MODEL
        else:
            self.contentType = ContentType(contentType)
            if self.contentType is None: raise ValueError(
                f"Unrecognized declared content type '{contentType}')")

        if tokens is None: return

        # Model, not declared content
        #
        if not isinstance(tokens, list): raise TypeError(
            f"token list is a {type(tokens)}, not list.")
        if self.contentType != ContentType.X_MODEL: raise TypeError(
            f"Token list incompatible w/ dcl content '{self.contentType}'.")

        if seq or rep: raise DOMException(
            "Don't pass seq or rep to Model, only to ModelGroup or ModelItem.")
        if self.contentType != ContentType.X_MODEL: raise SyntaxError(
            f"Expected contentType X_MODEL (not {self.contentType}) with tokens = {tokens}")
        if not isinstance(tokens, list): raise SyntaxError(
            f"Model tokens arg is not list, but {type(tokens)}.")

        # Make a proper AST from the model tokens
        #   TODO What does tokens get for {1:2}?
        #   (super() already set .childItems = [])
        #
        #print("\nToken processing:")
        MGStack = [ self ]
        i = 0
        while i < len(tokens):
            t = tokens[i]
            #print("\Tokens %2d: '%s'" % (i, t))
            if t == "(":
                newMG = ModelGroup()
                if MGStack: MGStack[-1].childItems.append(newMG)
                MGStack.append(newMG)
            elif t == ")":
                if i+1 < len(tokens) and tokens[i+1] in "+?*":
                    MGStack[-1].rep = RepType(tokens[i+1])
                    i += 1
                MGStack.pop()
                if len(MGStack) == 0: raise SyntaxError(
                    "Extra ')' at token %d in model: %s." % (i, tokens))
            elif t in "|&,":  # Sequence type
                if MGStack[-1].seq == SeqType.NOSEQ:
                    MGStack[-1].seq = SeqType(t)
                elif MGStack[-1].seq != SeqType(t): raise SyntaxError(
                    "Inconsistent connector token %d '%s' vs. '%s'."
                    % (i, t, MGStack[-1].seq))
            elif t == ContentType.PCDATA.value or XStr.isXmlName(t):
                newMI = ModelItem(t)
                MGStack[-1].childItems.append(newMI)
                if i+1 < len(tokens) and tokens[i+1] in "+?*":
                    #print("Seeking rep, next token is '%s'." % (tokens[i+1]))
                    newMI.rep = RepType(tokens[i+1])
                    i += 1
            else:
                raise SyntaxError("Unexpected model token %d: '%s' in %s." % (i, t, tokens))
            i += 1
        if len(MGStack) != 1:
            raise SyntaxError("Unclosed () group in model: %s." % (tokens))

    def tostring(self, indent:str=None) -> str:
        if self.contentType != ContentType.X_MODEL:
            return self.contentType.tostring()
        else:
            return super().tostring(indent=indent)

class ElementDef(ComplexType):
    def __init__(self, name:NMTOKEN_t, model:Model,
        ownerSchema:'DocumentType'=None, readOrder:int=0):
        super().__init__(name, model)
        self.ownerSchema = ownerSchema
        self.readOrder = readOrder
        self.attributeDefs:Dict[AttrKey, 'AttributeDef'] = None
        self.allowText:bool = True
        self.inclusions = None
        self.exclusions = None

    def attachAttr(self, attrDef:AttributeDef):
        akey = attrDef.getKey()
        if akey not in self.attributeDefs:
            self.attributeDefs[akey] = attrDef

    def tostring(self) -> str:
        buf = "<!ELEMEMT %-12s %s" % (self.name, self.model.tostring())
        if self.inclusions: buf += "\n    +(%s)" % " | ".join(self.inclusions)
        if self.exclusions: buf += "\n    -(%s)" % " | ".join(self.exclusions)
        buf += ">\n"
        # TODO Issue attlist alongside element dcl?
        return buf

    # Integrate the validator


###############################################################################
#
class DataSourceOBS:
    """Encapsulate a source of characters, generally one of:
        * A string(typically originating in a qlit in an ENTITY dcl.
        * A set of public/system ids that should identify
            ** a file object (perhaps to resolve via a catalog or similar)
            ** a possibly-abstract identifier, as from a NOTATION dcl.

    TODO: Who owns the catalog or path, the pwd,....?
    """
    def __init__(self,
        literal:str=None,
        publicId:str=None,
        systemId:Union[str, List]=None,
        encoding:str="utf-8"):
        self.literal = literal
        self.publicId = publicId
        self.systemId = systemId if isinstance(systemId, list) else [ systemId ]
        self.encoding = encoding
        self.foundPath = None
        self.ifh = None

    def open(self) -> None:
        """Make the source ready to read:
            * If it's already open, rewind it.
            * If it's already been resolved to a path, open it.
            * Otherwise resolve it, save the resolution, then open it.
        """
        if self.literal is not None:
            return self.literal
        if not self.foundPath:
            self.foundPath = self.findPath()
            if not self.foundPath: raise IOError(
                "Cannot resolve ids: PUBLIC '{self.publicId}', {self.systemID}.")
        self.ifh = codecs.open(self.foundPath, "rb", encoding=self.encoding)

    def findPath(self) -> str:  # TODO Connect to better resolver, entDirs,....
        for s in self.systemId:
            if os.path.isfile(s): return s
        return None

    def findLocalPath(self, eDef:'EntityDef', dirs:List[str]=None, trace:bool=1) -> str:
        """Resolve a set of publicID/systemID(s) to an actual absolute path.
        TODO: Pulled from xsparser, finish integrating
        Who holds the catalog, pwd, whatever?
        """
        old_level = lg.getEffectiveLevel()
        if (trace): lg.setLevel(logging.INFO)

        if not self.systemId:
            raise IOError("No system ID for %s." % (eDef.entName))
        if isinstance(self.systemId, list): systemIds = self.systemId
        else: systemIds = [ self.systemId ]

        lg.info("Seeking entity '%s':", eDef.entName)
        for systemId in systemIds:
            lg.info("  System id '%s'", systemId)
            if os.path.isfile(systemId):
                lg.info("    FOUND")
                lg.setLevel(old_level)
                return systemId
            if dirs:
                for epath in dirs:
                    cand = os.path.join(epath, systemId)
                    lg.info("    Trying dir '%s'", cand)
                    if os.path.isfile(cand):
                        lg.info("      FOUND")
                        lg.setLevel(old_level)
                        return cand
        raise OSError("No file found for %s (systemIds %s)."
            % (eDef.entName, systemIds))

    def close(self) -> None:
        if self.ifh:
            self.ifh.close()
            self.ifh = None

    def tostring(self) -> str:
        """Get the entire content of the source in one gulp
        (this is just read() except that we rewind and restore).
        """
        if self.literal is not None: return self.literal
        origPos = self.ifh.tell()
        self.ifh.seek(0, 0)
        s = self.ifh.read()
        self.ifh.seek(origPos, 0)
        return s


###############################################################################
#
EOF = -1

class EntitySpace(FlexibleEnum):
    """Where/how the entity can be referenced.
    Yeah, notations aren't technically entities.
    """
    GENERAL   = 1   # &: Only these have meaningful EntityParsing choices
    PARAMETER = 2   # %:
    NOTATION  = 4   # ...NDATA x and <obj notn="x">

class EntityParsing(FlexibleEnum):
    """Whether/how the data in an entity is parsed.
    """
    NDATA   = 0     # A General entity in a specific named notation
    CDATA   = 1     # No markup recognized
    RCDATA  = 2     # Only entity refs recognized
    PCDATA  = 3     # Usual XML parsing
    SDATA   = 4     # Always their own thing

    # Names for possible additions (some from SGML)
    #XINCLUDE = 100
    #SUBDOC   = 101
    #STARTTAG = 102
    #ENDTAG   = 103
    #PI       = 104
    #NAMESET  = 205 # Possible addition to parameters, for complexType dcls?

class EntityDef:
    """Represent a declared entity, of several kinds. An entity has:
        * an entName,
        * an entSpace from EntitySpace (general, parameter, sdata, etc.
        * a dataSource (literal string or public + system ids)
        * parsing rules from EntityParsing (when this is NDATA, also the name)
        * an encoding (not necessarily applicable to NDATA)
    """
    def __init__(self,
        entName:NMTOKEN_t,
        entSpace:EntitySpace,
        entParsing:EntityParsing=EntityParsing.PCDATA,
        publicId:str=None,
        systemId:str=None,
        data:str=None,
        notationName:NMTOKEN_t=None,
        encoding:str="utf-8",
        ownerSchema:'DocumentType'=None,
        readOrder:int=0
        ):
        self.entName = entName
        assert isinstance(entSpace, EntitySpace)
        self.entSpace = entSpace
        assert isinstance(entParsing, EntityParsing)
        self.entParsing = entParsing

        hasId = bool(publicId) or bool(systemId)
        if not (bool(data) ^ hasId): raise DOMException(
            "Specify exactly one: literal XOR public/system id.")
        self.publicId = publicId
        self.systemId = systemId if isinstance(systemId, list) else [ systemId ]
        self.literal = data

        if (notationName and entSpace != EntityParsing.NDATA): raise DOMException(
            "Notation name '%s' given for non-NDATA entity '%s'."
            % (notationName, entName))
        self.notationName = notationName
        self.encoding = encoding
        self.ownerSchema = ownerSchema
        self.readOrder = readOrder

        self.caseTx = CaseHandler("NONE")
        self.localPath = None  # Resolved on first reference

    def tostring(self) -> str:
        if self.literal is not None:
            data = f'"{self.literal}"'
        else:
            data = f'PUBLIC "{self.publicId}" "{self.systemId}"'
        pct = "% " if self.entSpace == EntitySpace.PARAMETER else ""
        return "<!ENTITY %s%s %s>\n" % (pct, self.entName, data)

class NotationDef:
    """This is for data notation/format applicable to entities. They are normally
    embedded by declaring an external file or object as an ENTITY, and then
    mentioning that entity name (not actually referencing the entity) as
    the value of an attribute that was declared as being of type ENTITY.
    """
    def __init__(self,
        name:NMTOKEN_t,
        publicId:str=None,
        systemId:Union[str, List]=None,
        ownerSchema:'DocumentType'=None,
        readOrder:int=0):
        self.name = name
        self.publicId = publicId
        self.systemId = systemId if isinstance(systemId, list) else [ systemId ]
        self.ownerSchema = ownerSchema
        self.readOrder = readOrder

    def tostring(self) -> str:
        data = f'PUBLIC "{self.publicId}" "{self.systemId}"'
        return "<!NOTATION %-12s %s>\n" % (self.name, data)


###############################################################################
#
class DocumentType(Node):
    """Just a stub for the moment.
    See also Schemas.py and https://docs.python.org/3.8/library/xml.dom.html
    TODO Also keep track of who was defined by which ATTLISTs.
    """
    def __init__(self, qualifiedName:QName_t=None,
        publicId:str='', systemId:Union[str, List]=None, htmlEntities:bool=True):
        super().__init__(nodeName=RWord.NN_DOCTYPE)
        self.nodeType = Node.DOCUMENT_TYPE_NODE

        self.name = self.nodeName = qualifiedName  # TODO Get from DOCTYPE
        self.publicId = publicId
        self.systemId = systemId if isinstance(systemId, list) else [ systemId ]
        self.htmlEntities = htmlEntities

        self.elementDefs:dict[NMTOKEN_t, 'ElementDef'] = {}
        self.attributeDefs:dict[NMTOKEN_t, AttributeDef] = {}  # NamedNodeMap() later if needed
        self.attlistDefs:list[AttlistDef] = []

        # These are all considered subtypes of entity here:
        self.entityDefs:Dict[NMTOKEN_t, 'EntityDef'] = {}
        self.pentityDefs:Dict[NMTOKEN_t, 'EntityDef'] = {}
        self.notationDefs:Dict[NMTOKEN_t, 'EntityDef'] = {}
        self.nameSetDefs:Dict[NMTOKEN_t, set] = {}  # Accommodation for schema maintenance

    def connectAttributes(self):
        """Ensure that each attribute is listed under all available elements.
        AttlistDef objects know their attributes, but not vice versa.
        TODO Should we create dummy element defs?
        TODO What about * and ##any?
        """
        for attributeDef in self.attributeDefs.items():
            if attributeDef.ename not in self.elementDefs: continue
            edef = self.elementDefs[attributeDef.ename]
            if attributeDef.aname not in edef.attributeDefs:
                edef.attributeDefs[attributeDef.aname] = attributeDef

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
        self.attlistDefs = []
        self.attributeDefs = {}
        self.entityDefs = {}
        self.pentityDefs = {}
        self.notationDefs = {}
        self.nameSetDefs = {}

        for ch in self.childNodes:
            if isinstance(ch, ElementDef): self.elementDefs[ch.name] = ch
            elif isinstance(ch, AttributeDef): self.attributeDefs[ch.name] = ch
            elif isinstance(ch, EntityDef):
                self.entityDefs[ch.entSpace][ch.name] = ch
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
        if aname in edef.attributeDefs: return edef.attributeDefs[aname]
        return None

    def defineAttribute(self, ename:NMTOKEN_t, aname:NMTOKEN_t,
        atype:NMTOKEN_t="CDATA", adfttype:DftType=DftType.IMPLIED,
        literal:str=None) -> None:
        assert aname not in self.attributeDefs
        self.elementDefs[(ename)].attributeDefs[aname] = AttributeDef(
            ens=None, ename=ename, ans=None, aname=aname,
            atype=atype, adfttype=adfttype, literal=literal, readOrder=None)

    # Entity (subtypes for General, Parameter, Notation, and NameSet)
    def getEntityDef(self, name:NMTOKEN_t) -> EntityDef:
        return self.entityDefs[name] if name in self.entityDefs else None

    def defineEntity(self,
        name:NMTOKEN_t,
        literal:str=None, publicId:str=None, systemId:str=None,
        entParsing:EntityParsing=EntityParsing.PCDATA,
        notationName:NMTOKEN_t=None) -> None:
        assert name not in self.entityDefs
        assert isinstance(entParsing, EntityParsing)
        self.entityDefs[name] = EntityDef(
            name, entSpace=EntitySpace.GENERAL,
            data=literal, publicId=publicId, systemId=systemId,
            entParsing=EntityParsing, notationName=notationName)

    def getPEntityDef(self, name:NMTOKEN_t) -> EntityDef:
        return self.pentityDefs[name] if name in self.pentityDefs else None

    def definePEntity(self, name:NMTOKEN_t,
        literal:str=None, publicId:str=None, systemId:str=None) -> None:
        assert name not in self.pentityDefs
        self.entityDefs[name] = EntityDef(name,
            EntitySpace.PARAMETER, literal, publicId, systemId)

    def getNotationDef(self, name:NMTOKEN_t) -> EntityDef:
        return self.notationDefs[name] if name in self.notationDefs else None

    def defineNotation(self, name:NMTOKEN_t,
        literal:str=None, publicId:str=None, systemId:str=None) -> None:
        assert name not in self.notationDefs
        self.notationDefs[name] = EntityDef(name,
            EntitySpace.NOTATION, literal, publicId, systemId)

    # Basic operations
    #
    def cloneNode(self, deep:bool=False) -> 'Node':
        newNode = DocumentType(
            qualifiedName=self.name,
            publicId = self.publicId,
            systemId = self.systemId
        )
        if deep: newNode.elementDefs = self.elementDefs.deepcopy()
        else: newNode.elementDefs = self.elementDefs.copy()
        return newNode

    def isEqualNode(self, n2) -> bool:  # DocumentType
        if self.nodeType != n2.nodeType: return False
        #if (self.nodeName != n2.nodeName or  # TODO use nodeNameMatches
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

DocType = Doctype = DocumentType
