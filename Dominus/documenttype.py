#!/usr/bin/env python3
# DocementType class: split from basedom 2024-06-28 sjd.
#
#
from collections import defaultdict, namedtuple
from typing import List, Set, Dict, Any, Union, Iterable

from basedomtypes import (NMTOKEN_t, QName_t, NodeType, FlexibleEnum,
    NSuppE, DOMException, ICharE)
from domenums import RWord
from xmlstrings import XmlStrings as XStr, CaseHandler, WSHandler
from basedom import Node
from xsdtypes import AttrTypes

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

    ** EntityType(FlexibleEnum): What kinds of entities we got?
    parameter, general, ndata, maybe sdata

    ** EntityParseType(FlexibleEnum): Parsing constraint on entity

    ** DataSource: A QLit or PUBLIC/SYSTEM ID(s)

    ** EntityDef: An entity declaration (name plus
    EntityType, ParseType, and DataSource)


* Notation stuff (treated as a quasi-entity)

    ** Notation: A notation declaration: name, plus
    a DataSource (which should always be a PUBLIC/SYSTEM ID(s), not QLit)

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
        self.unormTx = CaseHandler.NONE
        self.wsTx = WSHandler.XML


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
    def __init__(self, ens:NMTOKEN_t, ename:NMTOKEN_t, ans:NMTOKEN_t, aname:NMTOKEN_t,
        atype:NMTOKEN_t, adefault:Any, readOrder:int=0):
        self.ens = ens
        self.ename = ename  # TODO Provide for element name lists? What about NS?
        self.ans = ans
        self.aname = aname
        self.atype = atype   # TODO string or a type object?
        self.adefault = adefault
        self.readOrder = readOrder

        self.caseTx = "NONE"
        self.wsTx = "NONE"
        self.enumValues:dict = None

        if not XStr.isXmlQName(aname): raise ICharE(
             "Bad name '{aname}' for attribute.")
        if atype not in AttrTypes and not isinstance(atype, type): raise TypeError(
            "Unrecognized type for attribute {aname} for {self.name}.")
        if adefault is not None:
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
        self.enames = enames if isinstance(enames, Iterable) else [ enames ]
        bads = []
        for ename in self.enames:
            if not XStr.isXmlQName(ename): bads.append(ename)
        if bads: raise ICharE(
            "Bad element name(s) {bads} in ATTLIST.")
        self.readOrder = readOrder
        self.attributes = {}

    def __setitem__(self, aname:NMTOKEN_t, atype:str, adefault:Any=None) -> AttributeDef:
        """Just makes an attribute; caller must attach to element, doctype.
        """
        if aname in self.attributes:
            raise KeyError("Attribute {aname} already defined for {self.name}.")
        adef = AttributeDef(ens=None, ename=None, ans=RWord.NS_ANY, aname=aname,
            atype=atype, adefault=adefault, readOrder=len(self.attributes))
        self.attributes[(RWord.NS_ANY, aname)] = adef
        return adef

    def tostring(self) -> str:
        buf = "<!ATTLIST (%s) " % (", ".join(self.enames))
        for aname, aobj in self.items():
            buf += "\n    %16s %16s %s" % (aname, aobj.enumSpec(), aobj.adefault)
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

    def tostring(self, indent:str=None) -> str:
        return self.name + self.rep.tostring()

class ModelGroup:
    """Any parenthesized group, with ModelItem and/or ModelGroup members,
    plus sequence and rep settings.
    Maybe keep the original string, or a list of PEs in it?
    """
    def __init__(self, childItems:List[Union['ModelGroup', ModelItem]]=None,
        seq:SeqType=None, rep:RepType=None):
        self.seq = SeqType(seq) or SeqType.NOSEQ
        self.rep = RepType(rep) or RepType.NOREP
        self.childItems = childItems or []

    def getNames(self) -> Set:
        """Recursively extract the set of all names used anywhere within.
        """
        names = set()
        for childItem in self.childItems:
            if isinstance(childItem, ModelItem):
                names = names.union([childItem.name])
            elif isinstance(childItem, ModelGroup):
                names = names.union(childItem.getNames())
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
        self.contentType = None if not contentType else ContentType(contentType)
        if not tokens: return

        # Model, not declared content
        #
        if seq or rep: raise DOMException(
            "Don't pass seq or rep to Model, only to ModelGroup or ModelItem.")
        if contentType != ContentType.X_MODEL: raise SyntaxError(
            f"Expected contentType X_MODEL (not {contentType}) with tokens = {tokens}")
        if not isinstance(tokens, Iterable): raise SyntaxError(
            f"Model tokens arg is not Iterable, but {type(tokens)}.")

        # Make a proper AST from the model tokens
        #   (super() already set .childItems = [])
        #
        MGStack = [ self.childItems ]
        for i in range(len(tokens)):
            t = tokens[i]
            if t == "(":
                newMG = ModelGroup()
                if MGStack: MGStack[-1].childItems.append(newMG)
                MGStack.append(newMG)
            elif t == ")":
                if len(MGStack) == 0: raise SyntaxError(
                    "Extra ')' at token {i} in model: %s." % (tokens))
                if i+1 < len(tokens) and isinstance(tokens[i+1], RepType):
                    MGStack[-1].rep = tokens[i+1]
                    MGStack.pop()
                    i += 1
            elif t in "|&,":  # Sequence type
                if MGStack[-1].seq is SeqType.NOSEQ:
                    MGStack[-1].seq = SeqType(t)
                elif MGStack[-1].seq != SeqType(t): raise SyntaxError(
                    f"Inconsistent connector (token {i} '{t}' vs. {MGStack[-1].seq}.")
            elif t == ContentType.PCDATA.value or XStr.isXmlName(t):
                newMI = ModelItem(t)
                MGStack[-1].childItems.append(newMI)
                if i+1 < len(tokens) and isinstance(tokens[i+1], RepType):
                    newMI.rep = RepType(tokens[i+1])  # TODO Map to enum
                    i += 1
            else:
                raise SyntaxError(f"Unexpected model token #{i}: '{t}'.")
        if len(MGStack) != 0:
            raise SyntaxError(f"Unclosed () group in model: {tokens}.")

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
class EntityType(FlexibleEnum):
    GENERAL = 1
    PARAMETER = 2
    NOTATION = 4  # Treat as special entity, or not?

    # Names for possible extensions
    SDATA = 8
    NAMESET = 16

class EntityParseType(FlexibleEnum):  # Includes extras...
    NDATA   = 0
    CDATA   = 1
    RCDATA  = 2
    PCDATA  = 3

    # Names for possible additions
    XINCLUDE = 100
    SUBDOC   = 101
    STARTTAG = 102
    ENDTAG   = 103
    PI       = 104
    XMSKEY   = 105

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
        if self.literal:
            return '"%s"' % (XStr.escapeAttribute(self.literal))
        if self.publicId:
            src = 'PUBLIC "%s"' % (XStr.escapeAttribute(self.literal))
        else:
            src = 'SYSTEM'
        if not self.systemId:
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
        ownerSchema:'DocumentType'=None,
        readOrder:int=0
        ):
        self.name = name
        self.etype = etype
        self.dataSource = dataSource
        self.parseType = parseType
        self.notation = notation
        self.localPath = None
        self.ownerSchema = ownerSchema
        self.readOrder = readOrder

    def tostring(self) -> str:
        src = self.dataSource.tostring()
        pct = "% " if self.etype == EntityType.PARAMETER else ""
        return "<!ENTITY %s%s %s>\n" % (pct, self.name, src)

class Notation:
    """This is for data notation/format applicable to entities. They are normally
    embedded by declaring an external file or object as an ENTITY, and then
    mentioning that entity name (not actually referencing the entity) as
    the value of an attribute that was declared as being of type ENTITY.
    """
    def __init__(self, name:NMTOKEN_t, dataSource:DataSource,
        ownerSchema:'DocumentType'=None, readOrder:int=0):
        if dataSource.literal is not None:
            raise SyntaxError("NOTATION {nname} has QLit, not PUBLIC or SYSTEM.")
        self.name = name
        self.dataSource = dataSource
        self.ownerSchema = ownerSchema
        self.readOrder = readOrder

    def tostring(self) -> str:
        return "<!NOTATION %-12s %s>\n" % (self.name, self.dataSource.tostring())


###############################################################################
#
class DocumentType(Node):
    """Just a stub for the moment.
    See also Schemas.py and https://docs.python.org/3.8/library/xml.dom.html
    TODO Also keep track of who was defined by which ATTLISTs.
    """
    def __init__(self, qualifiedName:QName_t=None,
        publicId:str='', systemId:str='', htmlEntities:bool=True):
        super().__init__(nodeName="#doctype")
        self.nodeType = NodeType.DOCUMENT_TYPE_NODE

        self.name = self.nodeName = qualifiedName  # TODO Get from DOCTYPE
        self.publicId = publicId  # TODO Switch to DataSource
        self.systemId = systemId
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
        if aname in edef.attributeDefs: return edef.attributeDefs[aname]
        return None

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
            publicId = self.publicId,
            systemId = self.systemId
        )
        if deep: newNode.elementDefs = self.elementDefs.deepcopy()
        else: newNode.elementDefs = self.elementDefs.copy()
        return newNode

    def isEqualNode(self, n2) -> bool:  # DocumentType
        if self.nodeType != n2.nodeType: return False
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

DocType = Doctype = DocumentType
