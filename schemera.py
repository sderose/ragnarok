#!/usr/bin/env python3
#
# DocementType class: split from basedom 2024-06-28 sjd.
#
import os
from collections import defaultdict, namedtuple
from typing import List, Set, Dict, Union  # Any,
import logging
import re

from ragnaroktypes import (NMTOKEN_t, QName_t, FlexibleEnum,
    NSuppE, DOMException, ICharE)  # NodeType
from domenums import RWord
from runeheim import XmlStrings as Rune, CaseHandler #, UNormHandler, WSHandler
from basedom import Node
from xsdtypes import XSDDatatypes
from prettyxml import FormatXml

lg = logging.getLogger("documenttype")

__metadata__ = {
    "title"        : "documenttype",
    "description"  : "Support for DTD, XML Schema, etc.",
    "rightsHolder" : "Steven J. DeRose",
    "creator"      : "http://viaf.org/viaf/50334488",
    "type"         : "http://purl.org/dc/dcmitype/Software",
    "language"     : "Python 3.11",
    "created"      : "2024-06-28",
    "modified"     : "2025-05-26",
    "publisher"    : "http://github.com/sderose",
    "license"      : "https://creativecommons.org/licenses/by-sa/3.0/"
}
__version__ = __metadata__['modified']


EOF = -1

UNLIMITED = -1  # (or None?)


###########################################################################
#
class DerivationLimits(FlexibleEnum):
    """For XSD .block and .final.
    """
    NONE = "NONE"
    EXTENSION = "EXTENSION"
    RESTRICTION = "RESTRICTION"
    ALL = "ALL"


###########################################################################
#
class DclType(FlexibleEnum):
    """For attribute declared values.
    """
    CDATA     = "CDATA"
    NDATA     = "NDATA"
    RCDATA    = "RCDATA"      # In case of SGML
    SDATA     = "SDATA"       # In case of SGML


###########################################################################
#
class DftType(FlexibleEnum):
    """For attribute default values.
    """
    REQUIRED  = "#REQUIRED"
    IMPLIED   = "#IMPLIED"
    FIXED     = "#FIXED"
    X_VALUE   = "X_VALUE"     # Set when there's a literal default value
    CONREF    = "#CONREF"     # In case of SGML
    CURRENT   = "#CURRENT"    # In case of SGML


###########################################################################
# An AttrKey is what is needed to identify a specific attribute in the
# context of a schema For example, different elements may have same-named
# attributes, which are distinct. And both attributes and elements can
# exhibit duplicate names in different namespaces.
#
# Otoh, it is common for the "same" conceptual attribute to occur, with the
# same name, type, and default, on multiple elements ("id ID #IMPLIED" being
# an obvious case).
#
# In Loki and Schemera, there are also specialized ID-like attributes,
# with various special semantics. See loki.py and xsdtypes.py.
#
# We can identify a particular (conceptual) attribute by combining
#   * the attribute name
#   * the attribute namespace URI
#   * the element name on which it was declared/present
#   * the element's namespace URI
#
# TODO: Should AttrKey be a class instead of a namedtuple?
#
AttrKey = namedtuple("AttrKey", [ "elemNS", "elemName", "attrNS", "attrName" ])


###########################################################################
class AttrDef:
    """Define an Attribute. This can be handed information from parsing
    a schema, or just be called on the fly. There does not have to be
    an element of the given name defined (either now or later).

    This does NOT save/attach the definition anywhere. Caller must do that.
    """
    def __init__(self,
        elemNS:NMTOKEN_t, elemName:NMTOKEN_t,
        attrNS:NMTOKEN_t, attrName:NMTOKEN_t,
        attrType:NMTOKEN_t, attrDft:DftType, literal:str=None,
        ownerSchema:'DocumentType'=None, readOrder:int=0):
        self.elemNS = elemNS
        self.elemName = elemName  # TODO Provide for element name lists? What about NS?
        self.attrNS = attrNS
        self.attrName = attrName
        self.attrType = attrType   # TODO string or a type object?
        self.attrDft = attrDft
        self.literal = literal
        self.ownerSchema = ownerSchema
        self.readOrder = readOrder

        self.caseTx = "NONE"
        self.enumValues:dict = None

        if not Rune.isXmlQName(attrName): raise ICharE(
             f"Bad name '{attrName}' for attribute.")
        if attrType not in XSDDatatypes and not isinstance(attrType, type): raise TypeError(
            f"Unrecognized type '{attrType}' for attribute '{attrName}' for '{self.elemName}'.")
        if attrDft is not None:
            pass  # TODO

    def enumSpec(self) -> str:
        if self.enumValues: return " (%s)" % (" | ".join(self.enumValues))
        return None

    def getKey(self) -> str:
        """Return a hashable key for this attribute.

        TODO: Problem: elemName can be for multiple at once....
        """
        return AttrKey(self.elemNS, self.elemName, self.attrNS, self.attrName)


###########################################################################
class AttlistDef(dict):
    """Represent an entire ATTLIST declaration.
    I want to be able to re-use ATTLISTs (sets of AttrDefs). That's not
    directly possible in XML DTDs, but SGML has it, it's conceptually sensible,
    and there's no reason another schema language shouldn't do it.

    So this is the class that represents an ATTLIST, as a bundle of AttrDefs,
    and a set of elements to which it applies (in pure XML, just one element).

    So during parsing we need to:
        * Create the AttlistDef object
        * Make and add all the individual AttrDef objects
        * Create a dummy ElementDef object(s) if needed
        * Distribute the AttlistDef and/or AttrDefs onto the ElementDefs(s).

    """
    def __init__(self, elemNames:Union[str, List[str]],
        ownerSchema:'DocumentType'=None, readOrder:int=0):
        """Add the individual attributes via __setitem__.
        The AttlistDef crosses a set of elements with a set of attributes.
        readOrder matters b/c with duplicate names, the first applies.
        """
        self.elemNames = list(elemNames)
        bads = []
        for elemName in self.elemNames:
            if not Rune.isXmlQName(elemName): bads.append(elemName)
        if bads: raise ICharE(
            f"Bad element name(s) '{bads}' in ATTLIST.")
        self.ownerSchema = ownerSchema
        self.readOrder = readOrder
        self.attributes = {}

    def __setitem__(self, attrName:NMTOKEN_t, attrType:str, attrDft:DftType=None) -> AttrDef:
        """Just makes an attribute; caller must attach to element, doctype.  TODO Check
        """
        if attrName in self.attributes:
            raise KeyError(f"Attribute '{attrName}' already defined for '{self.elemNames}'.")
        attrDef = AttrDef(elemNS=None, elemName=None, attrNS=RWord.NS_ANY, attrName=attrName,
            attrType=attrType, attrDft=attrDft, readOrder=len(self.attributes))
        self.addAttrDef(attrDef=attrDef)
        return attrDef

    def addAttrDef(self, attrDef:AttrDef) -> bool:
        """Add a pre-constructed AttrDef to this ATTLIST.
        """
        assert attrDef.attrName not in self.attributes  # TODO NS?
        self.attributes[RWord.NS_ANY, attrDef.attrName] = attrDef
        return True

    def tostring(self) -> str:
        buf = "<!ATTLIST (%s) " % (", ".join(self.elemNames))
        for attrName, aobj in self.items():
            buf += "\n    %16s %16s %s" % (attrName, aobj.enumSpec(), aobj.attrDft)
        buf += ">\n"
        return buf

    def attachAttlistToElements(self):
        for e in self.elemNames:
            if e not in self.ownerSchema.elements:
                self.ownerSchema.elements[e] = ElementDef(e, model=None)
            eDef = self.ownerSchema.elements[e]
            eDef.attrList = self


###########################################################################
#
class SimpleType(dict):
    def __init__(self, name:NMTOKEN_t, baseType:NMTOKEN_t):
        self.name = name
        self.baseType = baseType
        self.restrictions = {}
        self.memberTypes = None  # For list and union types
        self.caseTx = CaseHandler.NONE


###############################################################################
# ELEMENT / ComplexType Stuff
#
class ComplexType(SimpleType):
    def __init__(self, name:NMTOKEN_t, baseType:NMTOKEN_t=None, model:'Model'=None):
        super().__init__(name=name, baseType=baseType)
        self.abstract = False
        self.final = None
        self.block = None
        self.attrDefs:Dict[AttrKey, 'AttrDef'] = {}
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
        assert name == ContentType.PCDATA.value or Rune.isXmlNMTOKEN(name)
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

    def __str__(self) -> str:
        lg.info('Casting a {type(self)}')
        return self.tostring()

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

    Comes in as List[str], for example:
        [ "(", "i", "|", "b", "*", "|", "tt", ")", "+" ]
    """
    def __init__(self, tokens:List[str]=None, seq:SeqType=None, rep:RepType=None,
        contentType:ContentType=None):
        super(). __init__(None, None, None)
        lg.info("Model(): tokens %s", tokens)
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
            f"token list is a '{type(tokens)}', not list.")
        if self.contentType != ContentType.X_MODEL: raise TypeError(
            f"Token list incompatible w/ dcl content '{self.contentType}'.")

        if seq or rep: raise DOMException(
            "Don't pass seq or rep to Model, only to ModelGroup or ModelItem.")
        if self.contentType != ContentType.X_MODEL: raise SyntaxError(
            f"Expected contentType X_MODEL (not '{self.contentType}') with tokens = '{tokens}'.")
        if not isinstance(tokens, list): raise SyntaxError(
            f"Model tokens arg is not list, but '{type(tokens)}'.")

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
            elif t == ContentType.PCDATA.value or Rune.isXmlName(t):
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
        lg.info("Model string: %s", self.tostring())

    def tostring(self, indent:str=None) -> str:
        if self.contentType != ContentType.X_MODEL:
            return self.contentType.tostring()
        else:
            return super().tostring(indent=indent)

class ElementDef(ComplexType):
    def __init__(self, name:NMTOKEN_t, model:Model,
        ownerSchema:'DocumentType'=None, readOrder:int=0):
        super().__init__(name, model)
        self.ownerSchema:'DocumentType' = ownerSchema
        self.readOrder:int = readOrder
        self.attrDefs:Dict = None
        self.allowText:bool = True
        self.inclusions = None
        self.exclusions = None

    def attachAttr(self, attrDef:AttrDef) -> None:
        if attrDef.attrName not in self.attrDefs:
            self.attrDefs[attrDef.attrName] = attrDef
        else:
            raise DOMException(
                f"Attempt to attach duplicate attribute {attrDef.attrName} to {self.name}.")
        # TODO Issue Error?

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
class SourceThing:
    """Encapsulate the source info for an entity, or similar.
    That can include a public ID and/or system ID (or IDs, by extension).
    Entities, but not Notation or Doctypes, can instead be a quoted literal.
    """
    def __init__(self, publicId:str=None, systemId:str=None, literal:str=None):
        self.publicId = publicId
        self.systemId = systemId
        self.literal = literal
        if self.hasId and (literal is not None): raise DOMException(
            "SourceThing: Specify only one of literal or public/system ids.")

    @property
    def hasId(self) -> bool:
        return self.publicId or self.systemId

    def findLocalPath(self, entDef:'EntityDef', dirs:List[str]=None, trace:bool=1) -> str:
        """Resolve a set of publicId/systemId to an actual absolute path.
        TODO: Pulled from xsparser, finish integrating
        Who holds the catalog, pwd, whatever?
        """
        old_level = lg.getEffectiveLevel()
        if (trace): lg.setLevel(logging.INFO)

        if not self.systemId:
            raise IOError("No system ID for %s." % (entDef.entName))
        # TODO Condition on option
        systemIds = self.splitSystemId(self.systemId)

        lg.info("Seeking entity '%s':", entDef.entName)
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
            % (entDef.entName, systemIds))

    def splitSystemId(self, s:str) -> List:
        return re.split(r"\s*\r\s*", s)

    def tostring(self) -> str:
        """A qlit in a declaration does not need everything escaped; basically
        just quotes.
        TODO: Fix, it seems to escape < and &.
        """
        if (self.literal):
            return FormatXml.escapeAttribute(self.literal, addQuotes=True)
        if self.publicId:
            buf = "PUBLIC " + FormatXml.escapeAttribute(self.publicId, addQuotes=True)
        else:
            buf = "SYSTEM"
        if not self.systemId:
            buf += ' ""'
        else:
            buf += " " + FormatXml.escapeAttribute(self.systemId, addQuotes=True)
        return buf


###############################################################################
#
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

        self.source = SourceThing(publicId, systemId, data)

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
        loc = self.source.tostring()
        pct = "% " if self.entSpace == EntitySpace.PARAMETER else ""
        return "<!ENTITY %s%s %s>\n" % (pct, self.entName, loc)

class NotationDef:
    """This is for data notation/format applicable to entities. They are normally
    embedded by declaring an external file or object as an ENTITY, and then
    mentioning that entity name (not actually referencing the entity) as
    the value of an attribute that was declared as being of type ENTITY.
    """
    def __init__(self,
        name:NMTOKEN_t,
        publicId:str=None,
        systemId:str=None,
        ownerSchema:'DocumentType'=None,
        readOrder:int=0):
        self.name = name
        self.source = SourceThing(publicId, systemId)
        self.ownerSchema = ownerSchema
        self.readOrder = readOrder

    def tostring(self) -> str:
        loc = self.source.tostring()
        return "<!NOTATION %-12s %s>\n" % (self.name, loc)


###############################################################################
#
class DocumentType(Node):
    """Just a stub for the moment.
    See also Schemas.py and https://docs.python.org/3.8/library/xml.dom.html
    TODO Also keep track of who was defined by which ATTLISTs.
    """
    def __init__(self, qualifiedName:QName_t=None,
        publicId:str='', systemId:str=None, htmlEntities:bool=True):
        super().__init__(nodeName=RWord.NN_DOCTYPE)
        self.nodeType = Node.DOCUMENT_TYPE_NODE

        self.name = self.nodeName = qualifiedName  # TODO Get from DOCTYPE
        self.source = SourceThing(publicId, systemId)
        self.htmlEntities = htmlEntities

        self.elementDefs:dict[NMTOKEN_t, 'ElementDef'] = {}
        self.attrDefs:dict[NMTOKEN_t, AttrDef] = {}  # NamedNodeMap()?
        self.attlistDefs:list[AttlistDef] = []

        # These are all considered subtypes of entity here:
        self.entityDefs:Dict[NMTOKEN_t, 'EntityDef'] = {}
        self.pentityDefs:Dict[NMTOKEN_t, 'EntityDef'] = {}
        self.notationDefs:Dict[NMTOKEN_t, 'EntityDef'] = {}
        self.nameSetDefs:Dict[NMTOKEN_t, set] = {}  # for schema maintenance

    @property
    def publicId(self) -> str: return self.source.publicId

    @property
    def systemId(self) -> str: return self.source.systemId

    def connectAttributes(self) -> None:
        """Ensure that each attribute is listed under all available elements.
        AttlistDef objects know their attributes, but not vice versa.
        TODO Should we create dummy element defs?
        TODO What about * and ##any?
        """
        if not self.attrDefs: return
        for attrDef in self.attrDefs.items():
            if attrDef.elemName not in self.elementDefs: continue
            elemDef = self.elementDefs[attrDef.elemName]
            if attrDef.attrName not in elemDef.attrDefs:
                elemDef.attrDefs[attrDef.attrName] = attrDef

    def applyDefaults(self, elDcl:ElementDef, attrs:Dict) -> Dict:
        raise NotImplementedError("TODO attribute defaults!")

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

    def getElementDef(self, name:NMTOKEN_t) -> ElementDef:
        return self.elementDefs[name] if name in self.elementDefs else None

    def defineElement(self, name:NMTOKEN_t, modelInfo) -> None:
        assert name not in self.elementDefs
        self.elementDefs[name] = modelInfo

    def getAttrDef(self, elemName:NMTOKEN_t, attrName:NMTOKEN_t) -> AttrDef:
        if elemName not in self.elementDefs: return None
        elemDef = self.elementDefs[elemName]
        if attrName in elemDef.attrDefs: return elemDef.attrDefs[attrName]
        return None

    def defineAttribute(self, elemName:NMTOKEN_t, attrName:NMTOKEN_t,
        attrType:NMTOKEN_t="CDATA", attrDft:DftType=DftType.IMPLIED,
        literal:str=None) -> None:
        assert attrName not in self.attrDefs
        self.elementDefs[(elemName)].attrDefs[attrName] = AttrDef(
            elemNS=None, elemName=elemName, attrNS=None, attrName=attrName,
            attrType=attrType, attrDft=attrDft, literal=literal, readOrder=None)

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
        self.notationDefs[name] = EntityDef(name, EntitySpace.NOTATION,
            publicId=publicId, systemId=systemId, data=literal)

    # Basic operations
    #
    def cloneNode(self, deep:bool=False) -> 'Node':
        newNode = DocumentType(
            qualifiedName=self.name,
            publicId = self.source.publicId,
            systemId = self.source.systemId
        )
        if deep: newNode.elementDefs = self.elementDefs.deepcopy()
        else: newNode.elementDefs = self.elementDefs.copy()
        return newNode

    def isEqualNode(self, n2) -> bool:  # DocumentType
        if self.nodeType != n2.nodeType: return False
        #if (not self.nodeNameMatches(n2) or
        #    self.source.publicId != n2.source.publicId or
        #    self.source.systemId != n2.source.systemId): return False
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
        loc = self.source.tostring()
        buf = ('<!DOCTYPE %s %s [\n') % (self.nodeName, loc)

        for pent in sorted(self.pentityDefs):
            buf += pent.toprettyxml()

        for notn in sorted(self.notationDefs):
            buf += notn.toprettyxml()

        for ent in sorted(self.entityDefs):
            buf += ent.toprettyxml()

        attrDone = defaultdict(int)
        for elem in sorted(self.elementDefs):
            buf += elem.toprettyxml()
            if elem.name in self.attrDefs:
                buf += self.attrDefs[elem.name].toprettyxml()
                attrDone[elem.name] = True

        for attrDef in self.attrDefs:
            if attrDef.name in attrDone: continue
            buf += self.attrDefs[attrDef.name].toprettyxml()

        buf += "]>\n"
        return buf

    # end class DocumentType

DocType = Doctype = DocumentType
