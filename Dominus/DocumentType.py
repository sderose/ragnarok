#!/usr/bin/env python3
# DocType class: split from BaseDOM 2024-06-28 sjd.
#
import re
from enum import Enum
from typing import List, Any

from BaseDOM import Node, Leaf

NmToken = str

class DocumentType(Leaf):
    """Just a stub for the moment.
    See also my Schemas.py, and https://docs.python.org/3.8/library/xml.dom.html
    """
    def __init__(self, qualifiedName:str, ownerDocument=None, doctypeString:str='',
        publicId:str='', systemId:str=''):
        super(DocumentType, self).__init__(
            ownerDocument=ownerDocument,
            nodeName="", nodeType=Node.DOCUMENT_TYPE_NODE)

        self.name = self._nodeName = qualifiedName  # Should come from the DOCTYPE
        self.publicId = publicId
        self.systemId = systemId
        self.userData = None

        self.doctypeString = doctypeString
        self.internalSubset = None  # As a string
        if (qualifiedName and doctypeString and
            not doctypeString.strip().startswith(qualifiedName)):
            raise ValueError("doctype mismatch, '%s' vs. '%s'." %
                (qualifiedName, doctypeString))

        self.elements = None
        self.attributes = None
        self.entities = None
        self.pentities = None
        self.notations = None

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

    def remove(self):
        """Removes this object from its parent child list.
        """
        par = self.parentNode
        par.removeChild(self)

    def replaceWith(self, stuff:List):
        """Replaces the document type with a set of given nodes.
        """

    ####### EXTENSIONS

    def reindex(self):
        self.elements = {}
        self.attributes = {}
        self.entities = {}
        self.pentities = {}
        self.notations = {}

        for ch in self.childNodes:
            if   (isinstance(ch, ElementDcl)):   self.elements[ch.name] = ch
            elif (isinstance(ch, AttributeDcl)): self.attributes[ch.name] = ch
            elif (isinstance(ch, EntityDcl)):    self.entities[ch.name] = ch
            elif (isinstance(ch, PEntityDcl)):   self.pentities[ch.name] = ch
            elif (isinstance(ch, NotationDcl)):  self.notations[ch.name] = ch
            else:
                assert False, "Unknown declaration type %s." % (type(ch))
        return

    def hasElement(self, name:NmToken):
        return (name in self.elements)

    def addElement(self, name:NmToken, modelInfo):
        self.elements[name] = modelInfo

    def addAttribute(self, ename:NmToken, aname:NmToken,
        atype:NmToken="CDATA", adefault:NmToken="IMPLIED"):
        self.elements[ename].attributes[aname] = [ atype, adefault ]

    def addEntity(self, name:NmToken, value:str, location=None, parseType="XML"):
        assert parseType in [
            "XML", "HTML", "JSON", "CDATA", "RCATA", "UNPARSED" ]
        self.entities[name] = [ value, location, parseType ]

    def addNotation(self, name:NmToken, publicId:str='', systemId:str=''):
        self.entities[name] = [ publicId, systemId ]

    def cloneNode(self, deep:bool=False):
        newNode = DocumentType(
            qualifiedName=self.name,
            ownerDocument=self.ownerDocument,
            doctypeString=self.doctypeString,
            publicId = self.publicId,
            systemId = self.systemId
        )
        if (deep): newNode.elements = self.elements.deepcopy()
        else: newNode.elements = self.elements.copy()
        if (self.userData): newNode.userData = self.userData
        return newNode

    def parseDoctypeString(self):
        """Parse the DOCTYPE declaration
        """
        self._nodeName = re.sub(r'^\s*(\w+)\W.*', r'\\1', self.doctypeString)
        qlit = r'("[^"]*"|\'[^\']*\')'
        mat = re.match(r'\s+PUBLIC\s+'+qlit+r'\s+'+qlit, self.doctypeString)
        if (mat):
            self.publicId = mat.group(1).strip("'\" ")
            self.systemId = mat.group(2).strip("'\" ")
        else:
            mat = re.match(r'\s+SYSTEM\s+'+qlit, self.doctypeString)
            if (mat):
                self.systemId = mat.group(1).strip("'\" ")

    def parseInternalSubset(self):
        pass

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
            self._nodeName, self.publicId, self.systemId, self.internalSubset)
        return buf

    @property
    def innerXML(self) -> str:  # Notation
        return self.data

    def tostring(self) -> str:  # Notation
        return self.outerXML

    # end class DocumentType

DocType = DocumentType


###############################################################################
# Stub classes for schema constructs (DTD-ish for the moment).
#
class Dcl:
    def __init__(self, name, ):
        self.name = name

class ElementDcl(Dcl):
    def __init__(self, name:str, modelObj:Any):
        super(ElementDcl, self).__init__(name)
        self.modelObj = modelObj

class AttrTypes(Enum):
    """Really this wants to be XSD built-ins, at least.
    """
    UNKNOWN     = 0
    CDATA       = 1
    ID          = 2
    IDREF       = 3
    ENTITY      = 4
    NMTOKEN     = 5
    NOTATION    = 6
    Enumerated  = 7

    IDREFS      = 102
    ENTITIES    = 104
    NMTOKENS    = 105

class AttributeDcl(Dcl):
    def __init__(self, name:str, attrType:AttrTypes, attrDft:str):
        super(AttributeDcl, self).__init__(name)
        self.attrType = attrType
        self.attrDft = attrDft


class BaseEntityDcl(Dcl):
    def __init__(self, name:str,
        publicID:str=None, systemID:str=None, notation:str=None, data:str=None
        ):
        super(BaseEntityDcl, self).__init__(name)
        self.publicID = publicID
        self.systemID = systemID
        self.notation = notation
        self.data = data

class EntityDcl(BaseEntityDcl):
    def __init__(self, *args, **kwargs):
        super(EntityDcl, self).__init__(*args, **kwargs)

class PEntityDcl(BaseEntityDcl):
    def __init__(self, *args, **kwargs):
        super(PEntityDcl, self).__init__(*args, **kwargs)

class NotationDcl(BaseEntityDcl):
    def __init__(self, *args, **kwargs):
        super(NotationDcl, self).__init__(*args, **kwargs)
