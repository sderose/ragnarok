#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# A fairly simple native Python DOM implementation. Basically DOM 2,
# plus a bunch of Pythonic conveniences.
#
#pylint: disable=W0613, W0212
#pylint: disable=E1101
#
import re
from collections import OrderedDict
from enum import Enum
from typing import Any, Callable, Dict, List, Union
import logging

#import xml.dom.minidom
#from xml.dom.minidom import Node as miniNode
#from xml.dom.minidom import Document as miniDocument

import XMLRegexes

from XMLStrings import XMLStrings as XStr
#import DOMImplementation
#import DocumentType
import DOMBuilder
import DOMImplementation

lg = logging.getLogger("BaseDOM")
xr = XMLRegexes.XMLRegexes(compile=True)

# Provide synonym types for type-hints these common args
#
NodeType = int
NmToken = str

__metadata__ = {
    "title"        : "BaseDOM",
    "description"  : "A more Pythonic DOM~2 implementation.",
    "rightsHolder" : "Steven J. DeRose",
    "creator"      : "http://viaf.org/viaf/50334488",
    "type"         : "http://purl.org/dc/dcmitype/Software",
    "language"     : "Python 3.7",
    "created"      : "2016-02-06",
    "modified"     : "2024-06-28",
    "publisher"    : "http://github.com/sderose",
    "license"      : "https://creativecommons.org/licenses/by-sa/3.0/"
}
__version__ = __metadata__['modified']

descr = """
=Description=

A pure Python DOM, intended to cover all of DOM Level 2 Core, but be more
Pythonic/convenient that regular xml.dom.minidom.
This can be used independently, and is meant to be a backward-compatible
pluggable replacement for xml.dom.mindom. It also adds some features:

* [] is supported so you can just walk down through trees in Python style:

    myDoc['body']['div']['p', 3]['@class']

* Shorthand Node properties such as isElement, isPI, etc.

* Separate classes to test strings for non-XML characters;
for whether they are XML names, local-names, qnames, or prefixed names;
for escaping strings as needed for all relevant XML contexts; etc.

* NamedNodeMap is a subclass of Python OrderedDict.

* Node types are a Python Enum.

* .text is added as a property that recursively gathers the text of Element,
Text, CDATA, or Document nodes, optionally with separators for element boundaries.

* Constructors are streamlined. For example, createElement can take a Dict
of attributes, and optional parent and text arguments.

It is also used to build my `Dominus` package on, which adds the ability
to load, save, and edit persistent DOM structures on disk.

For many more handy functions such as a table-management API, XPointer
support, Trojan milestone support, and so on, see my other utilities,
which should work fine on top of either this or minidom.


=To do=

* Small convenience extensions
** inherited attributes
** xpointer
* some good way to auto-type int, ID, and other attributes. Maybe
just hand it a dict of "elem?:attr": type?
* Maybe a type for class-ish attrs?
* child generators by nodeType (at least text, elem, elem+text)

* Take some conveniences from ET:
*     ET.SubElement(parent, tag, attrs)

* Finish parse() (cf DomDuilder.py)
* Hook up additional parsers (html5lib, YML; maybe cross-loaders like JSON, CSV)
* Finish namespace support.
* Much more testing.
* Add some DOM 3 features, esp. XPath, events, ranges, serialization?
* Support 'canonical' option for tostring().
* Integrate into Dominµs.
* Add JQuery-like selectors, iether here or in `DomExtensions`.
* Make Node a true subclass of list and/or dict?


=Known bugs and limitations=

Namespace support is incomplete.

`cloneNode()` copies any `userData` merely via assignment, not a deep copy,
even when `deep=True` is set. You can of course copy and reset
it afterwards if desired. However, `cloneNode()` on a DocumentType node does
use `deepcopy(deep=True)` for the schema (if any).


=Related commands=

`DOMBuilder` -- the glue that turns parser events into a DOM.

`DomExtensions.py` -- sits on top and provides lots of added methods.

`Dominus.py` -- alternative DOM implementation that keeps everything on
disk to allow for very large documents.

`testDom.py` -- basic test that should at least try each method at least once.

`testDomExtensions.py` -- same, but for `DomExtensions.py`.


=References=

W3C/NIST DOM test suite: [https://www.w3.org/DOM/Test/]. These are available
for Java and ECMAScript. Why not Python?

Actual DOM specs: [https://www.w3.org/DOM/DOMTR].

W3 test suites: [https://www.w3.org/DOM/Test/].

[https://developer.mozilla.org/en-US/docs/Web/API/Document_Object_Model/Introduction]
claims to provide test examples for all DOM methods.


=History=

* Written by Steven J. DeRose, ~Feb 2016.
* 2018-04-18: lint.
* 2019-12-30: Split out DOMBuilder and various extensions to separate packages.
Rename from RealDOM.py to BaseDOM.py, and move from PYTHONLIBS to XML/BINARY.
Check and fix sync with DOM 2 Core spec. Hook to testDom.py.
* 2020-01-15: Lots of bug-fixing, linting, and API checking. Add choice to use
Python vs. regular DOM exceptions.
* 2024-06-28: Refactor, capitalize "DOM" in names, use instead of copy
XML utility packages.


=Rights=

Copyright 2016, Steven J. DeRose. This work is licensed under a Creative Commons
Attribution-Share Alike 3.0 Unported License. For further information on
this license, see [http://creativecommons.org/licenses/by-sa/3.0].

For the most recent version, see [http://www.derose.net/steve/utilities] or
[http://github/com/sderose].


=Options=
"""

###############################################################################
# xml.dom.minidom uses typical Python exceptions, although DOM defines
# it's own. We offer either option. See also:
#
# https://developer.mozilla.org/en-US/docs/Web/API/DOMException
# w3.org/TR/1998/REC-DOM-Level-1-19981001/level-one-core.html
# http://stackoverflow.com/questions/1319615
# https://docs.python.org/2/library/xml.dom.html
#
class INDEX_SIZE_ERR(Exception):                pass  # 1
class DOMSTRING_SIZE_ERR(Exception):            pass  # 2
class HIERARCHY_REQUEST_ERR(Exception):         pass  # 3
class WRONG_DOCUMENT_ERR(Exception):            pass  # 4
class INVALID_CHARACTER_ERR(Exception):         pass  # 5
class NO_DATA_ALLOWED_ERR(Exception):           pass  # 6
class NO_MODIFICATION_ALLOWED_ERR(Exception):   pass  # 7
class NOT_FOUND_ERR(Exception):                 pass  # 8
class NOT_SUPPORTED_ERR(Exception):             pass  # 9
class INUSE_ATTRIBUTE_ERR(Exception):           pass  # 10

# Not in minidom:
NAME_ERR = INVALID_CHARACTER_ERR

##### Rest unused:
#class INVALID_STATE_ERR(Exception):             pass  # 11
#class SYNTAX_ERR(Exception):                    pass  # 12
#class INVALID_MODIFICATION_ERR(Exception):      pass  # 13
#class NAMESPACE_ERR(Exception):                 pass  # 14
#class INVALID_ACCESS_ERR(Exception):            pass  # 15
#class TYPE_MISMATCH_ERR(Exception):             pass  # 17
#class SECURITY_ERR(Exception):                  pass  # 18
#class NETWORK_ERR(Exception):                   pass  # 19
#class ABORT_ERR(Exception):                     pass  # 20
#class URL_MISMATCH_ERR(Exception):              pass  # 21
#class QUOTA_EXCEEDED_ERR(Exception):            pass  # 22
#class TIMEOUT_ERR(Exception):                   pass  # 23
#class INVALID_NODE_TYPE_ERR(Exception):         pass  # 24
#class DATA_CLONE_ERR(Exception):                pass  # 25
#EncodingError, NotReadableError, UnknownError, ConstraintError, DataError,
#TransactionInactiveError, ReadOnlyError, VersionError, OperationError,
#NotAllowedError


###############################################################################
#
class NodeTypes(Enum):
    UNSPECIFIED_NODE             = 0  # Not in DOM, but useful
    ELEMENT_NODE                 = 1  # ELEM
    ATTRIBUTE_NODE               = 2  # ATTR
    TEXT_NODE                    = 3  # TEXT
    CDATA_SECTION_NODE           = 4  # CDATA
    ENTITY_REFERENCE_NODE        = 5  # ENTREF
    ENTITY_NODE                  = 6  # ENT
    PROCESSING_INSTRUCTION_NODE  = 7  # PI
    COMMENT_NODE                 = 8  # COM
    DOCUMENT_NODE                = 9  # DOC
    DOCUMENT_TYPE_NODE           = 10 # DOCTYPE
    DOCUMENT_FRAGMENT_NODE       = 11 # FRAG
    NOTATION_NODE                = 12 # NOTATION

    @staticmethod
    def okNodeType(thing:Union[int, 'NodeTypes', 'Node'], die:bool=True) -> 'NodeTypes':
        """Check a nodeType property. You can pass either a Node, a NodeTypes,
        or an int (so people who remember the ints and just test are still ok.
        """
        nt = thing.nodeType if isinstance(thing, Node) else thing
        if (isinstance(nt, NodeTypes)): return nt
        try:
            _nt = NodeTypes(nt)
        except ValueError:
            if (not die): return None
            assert False, "nodeType %s is a %s, not int or NodeTypes." % (
                nt, type(nt))
        return _nt

    @staticmethod
    def tostring(value:Union[int, 'NodeTypes']) -> str:
        if (isinstance(value, NodeTypes)): return value.name
        try:
            return NodeTypes(int(value))
        except ValueError:
            return "[UNKNOWN_NODETYPE]"


###############################################################################
#
class Node(list):
    """The main class for DOM, from which most others are derived.

    Note: properties/attributes and methods are listed in the same order as
    in the IDL definition in the DOM 2 Core spec, but separately.
    https://www.w3.org/TR/2000/REC-DOM-Level-2-Core-20001113/core.html#ID-1950641247
    """
    UNSPECIFIED_NODE             = NodeTypes.UNSPECIFIED_NODE
    ELEMENT_NODE                 = NodeTypes.ELEMENT_NODE
    ATTRIBUTE_NODE               = NodeTypes.ATTRIBUTE_NODE
    TEXT_NODE                    = NodeTypes.TEXT_NODE
    CDATA_SECTION_NODE           = NodeTypes.CDATA_SECTION_NODE
    ENTITY_REFERENCE_NODE        = NodeTypes.ENTITY_REFERENCE_NODE
    ENTITY_NODE                  = NodeTypes.ENTITY_NODE
    PROCESSING_INSTRUCTION_NODE  = NodeTypes.PROCESSING_INSTRUCTION_NODE
    COMMENT_NODE                 = NodeTypes.COMMENT_NODE
    DOCUMENT_NODE                = NodeTypes.DOCUMENT_NODE
    DOCUMENT_TYPE_NODE           = NodeTypes.DOCUMENT_TYPE_NODE
    DOCUMENT_FRAGMENT_NODE       = NodeTypes.DOCUMENT_FRAGMENT_NODE
    NOTATION_NODE                = NodeTypes.NOTATION_NODE

    def __init__(self, nodeType:Union[int, NodeTypes],
        ownerDocument:'Document'=None, nodeName:NmToken=None):
        super(Node, self).__init__()

        NodeTypes.okNodeType(nodeType)
        #lg.info("Make Node, nodeType %s (%s), ownerDocument %s." %
        #    (nodeType, NodeTypes(nodeType), ownerDocument))
        if (ownerDocument is not None and
            not isinstance(ownerDocument, Document)):
            raise HIERARCHY_REQUEST_ERR("Bad type (%s) for ownerDocument." %
                (type(ownerDocument)))

        # See below: nodeName, nodeValue
        self.nodeType        = nodeType
        self._nodeName       = nodeName

        self.parentNode      = None
        # We keep a real doubly-linked list, not just search via parent. Faster.
        self.previousSibling = None
        self.nextSibling     = None
        self.attributes      = NamedNodeMap()
        self.ownerDocument   = ownerDocument
        # See below: insertBefore()
        # See below: replaceChild()
        # See below: removeChild()
        # See below: appendChild()
        # See below: hasChildNodes()
        # See below: cloneNode()
        # See below: normalize()

        # ******* Added in DOM 2 *******
        # See below: isSupported()
        self.namespaceURI    = ""
        self.prefix          = ""
        self.localName       = XStr.getLocalPart(self._nodeName)
        # See below: hasAttributes()

        # EXTRA, non-DOM stuff
        self.nsPrefix        = ""
        self.nsAttributes    = NamedNodeMap()
        self.startLoc        = None
        self.data            = None    # For Leaf subclasses
        self.target          = None    # For PIs
        self.userData        = None

    @property
    def childNodes(self):
        """TODO: This may want its own getitem, to support my extensions;
        easier to just add the list API, or to indirect somehow?
        """
        return self  # OR list(self)?

    @property
    def nodeName(self):
        t = self.nodeType
        if (t == Node.ATTRIBUTE_NODE)              : return self._nodeName
        if (t == Node.CDATA_SECTION_NODE)          : return '#cdata-section'
        if (t == Node.COMMENT_NODE)                : return '#comment'
        if (t == Node.DOCUMENT_NODE)               : return '#document'
        if (t == Node.DOCUMENT_FRAGMENT_NODE)      : return '#document-fragment'
        if (t == Node.DOCUMENT_TYPE_NODE)          :
            return self.ownerDocument.doctype.name
        if (t == Node.ELEMENT_NODE)                : return self._nodeName
        if (t == Node.ENTITY_NODE)                 : return self._nodeName
        if (t == Node.ENTITY_REFERENCE_NODE)       : return self._nodeName
        if (t == Node.NOTATION_NODE)               : return self._nodeName
        if (t == Node.PROCESSING_INSTRUCTION_NODE) : return self._nodeName
        if (t == Node.TEXT_NODE)                   : return '#text'
        if (t == Node.UNSPECIFIED_NODE)            : return '#None'
        raise HIERARCHY_REQUEST_ERR("Undefined nodeType %d." % (t))

    @nodeName.setter
    def nodeName(self, name:NmToken):
        if (not xr.isXmlName(name)):
            raise NAME_ERR("Bad nodeName '%s'." % (name))
        self._nodeName = name

    @property
    def nodeValue(self):
        assert False, "nodeValue was not overridden for %s." % (self)

    @property
    def firstChild(self):
        try:
            return self.childNodes[0]
        except IndexError:
            return None

    @property
    def lastChild(self):
        try:
            return self.childNodes[-1]
        except IndexError:
            return None

    def insertBefore(self, newNode, ch):
        if (ch.parentNode != self):
            raise NOT_FOUND_ERR("Node to insert before is not a child.")
        if (newNode.ownerDocument is None):
            newNode.ownerDocument = self.ownerDocument
        elif (newNode.ownerDocument != self.ownerDocument):
            raise WRONG_DOCUMENT_ERR()
        if (ch.parentNode != self):
            raise NOT_FOUND_ERR("Reference node for insertBefore is not a child.")
        newNode.parentNode = self
        newNode.nextSibling = ch
        newNode.previousSibling = ch.previousSibling
        if (ch.previousSibling is not None):
            ch.previousSibling.nextSibling = ch
        ch.previousSibling = newNode
        self.childNodes.append(newNode)
        newNode.ownerDocument = self.ownerDocument

    def replaceChild(self, newChild, oldChild):
        if (oldChild.parentNode != self):
            raise NOT_FOUND_ERR("Node to replace is not a child.")
        if (newChild.ownerDocument is None):
            newChild.ownerDocument = self.ownerDocument
        elif (newChild.ownerDocument != self.ownerDocument):
            raise WRONG_DOCUMENT_ERR()
        newChild.previousSibling = oldChild.previousSibling
        newChild.nextSibling = oldChild.nextSibling
        newChild.parentNode = self
        if (oldChild.previousSibling is not None):
            oldChild.previousSibling.nextSibling = newChild
        if (oldChild.nextSibling is not None):
            oldChild.nextSibling.previousSibling = newChild
        oldChild.previousSibling = oldChild.nextSibling = oldChild.parentNode = None
        for i, curChild in enumerate(self.childNodes):
            if (curChild == oldChild):
                self.childNodes[i] = newChild
                break

    def removeChild(self, oldChild):
        if (oldChild.parentNode != self):
            raise NOT_FOUND_ERR("Node to remove is not a child.")
        if (oldChild.previousSibling is not None):
            oldChild.previousSibling.nextSibling = oldChild.nextSibling
        if (oldChild.nextSibling is not None):
            oldChild.nextSibling.previousSibling = oldChild.previousSibling
        oldChild.parentNode.childNodes.remove(oldChild)
        oldChild.previousSibling = oldChild.nextSibling = oldChild.parentNode = None

    def appendChild(self, newChild):
        if (newChild.ownerDocument is None):
            newChild.ownerDocument = self.ownerDocument
        elif (newChild.ownerDocument != self.ownerDocument):
            raise WRONG_DOCUMENT_ERR()
        newChild.parentNode = self
        if (len(self.childNodes) > 0):
            newChild.previousSibling = self.childNodes[-1]
            self.childNodes[-1].nextSibling = newChild
        self.childNodes.append(newChild)

    def hasChildNodes(self) -> bool:
        return len(self.childNodes) > 0

    def cloneNode(self, deep:bool=False):
        """NOTE: Default value for 'deep' has changed in spec and browsers!
         Don't copy the tree relationships.
         TODO: Move nodeType cases to the subclasses.
        """
        nt = self.nodeType
        if   (nt==Node.ELEMENT_NODE):
            newNode = Element(ownerDocument=self.ownerDocument,
                nodeName=self._nodeName)
            newNode.attributes = self.attributes.clone()
            newNode.userData = self.userData
            if (deep):
                for ch in self.childNodes:
                    newNode.appendChild(ch.cloneNode(deep=True))
        # Following Leaf subtypes could still move...
        elif (nt==Node.TEXT_NODE):
            newNode = Text(ownerDocument=self.ownerDocument, data=self.data)
        elif (nt==Node.COMMENT_NODE):
            newNode = Comment(ownerDocument=self.ownerDocument, data=self.data)
        elif (nt==Node.NOTATION_NODE):
            newNode = Notation(ownerDocument=self.ownerDocument, data=self.data)
        #elif (nt==Node.ATTRIBUTE_NODE): [Overridden]
        #elif (nt==Node.DOCUMENT_NODE): [Overridden]
        #elif (nt==Node.PROCESSING_INSTRUCTION_NODE [Overridden]
        #elif (nt==Node.DOCUMENT_TYPE_NODE):  [Overridden]
        else:
            raise NOT_SUPPORTED_ERR(
                "Unexpected nodeType %d." % (self.nodeType))

        if (self.userData): newNode.userData = self.userData
        return newNode

    def normalize(self):
        for ch in self.childNodes:
            if (ch.isElement):
                self.normalize()
            elif (ch.isText and ch.nextSibling and ch.nextSibling.isText):
                ch.textContent += ch.nextSibling.textContent
                self.removeChild(ch.nextSibling)

    def isSupported(self, feature, version) -> bool:
        return False

    def hasAttributes(self) -> bool:
        return (len(self.attributes) > 0)


    ###########################################################################
    # EXTRA NON-DOM stuff
    #
    # I don't like the lengthy ritual for checking node types:
    #    if (node.nodeType = Node.PROCESSING_INSTRUCTION_NODE)
    # so just do:
    #    if (node.isPI)
    #
    @property
    def isElement(self)   -> bool: return self.nodeType == NodeTypes.ELEMENT_NODE
    @property
    def isAttribute(self) -> bool: return self.nodeType == NodeTypes.ATTRIBUTE_NODE
    @property
    def isText(self)      -> bool: return self.nodeType == NodeTypes.TEXT_NODE
    @property
    def isCdata(self)     -> bool: return self.nodeType == NodeTypes.CDATA_SECTION_NODE
    @property
    def isEntRef(self)    -> bool: return self.nodeType == NodeTypes.ENTITY_REFERENCE_NODE
    @property
    def isEntity(self)    -> bool: return self.nodeType == NodeTypes.ENTITY_NODE
    @property
    def isPI(self)        -> bool:
        return self.nodeType == NodeTypes.PROCESSING_INSTRUCTION_NODE
    def isComment(self)   -> bool: return self.nodeType == NodeTypes.COMMENT_NODE
    @property
    def isDocument(self)  -> bool: return self.nodeType == NodeTypes.DOCUMENT_NODE
    @property
    def isDoctype(self)   -> bool: return self.nodeType == NodeTypes.DOCUMENT_TYPE_NODE
    @property
    def isFragment(self)  -> bool: return self.nodeType == NodeTypes.DOCUMENT_FRAGMENT_NODE
    @property
    def isNotation(self)  -> bool: return self.nodeType == NodeTypes.NOTATION_NODE

    @property
    def text(self:Node, delim:str=" ") -> str:
        """Cat together all descendant text nodes, optionally with separators.
        @param delim: What to put between the separate text nodes
        """
        textBuf = ""
        if (self.isText):
            if (textBuf): textBuf += delim
            textBuf += self.data
        elif (self.hasChildNodes()):
            for ch in self.childNodes:
                if (textBuf): textBuf += delim
                textBuf = textBuf + ch.text(delim=delim)
        return textBuf

    @property
    def hasIDAttribute(self):
        """TODO: Default to name 'id' if no schema info?
        """
        ename = self._nodeName
        if (self.ownerDocument.doctype is not None):
            for k, _v in self.attributes.items():
                if ('*@'+k in self.ownerDocument.doctype.IDAttrs or
                    ename+'@'+k in self.ownerDocument.theDOM.doctype.IDAttrs):
                    return k
        return None

    def compareDocumentPosition(self, n2:'Node') -> int:
        """XPointers are a nice way to do this, see DomExtensions.py.
        """
        t1 = self.getPath()
        t2 = n2.getPath()
        i = 0
        while (i<len(t1) and i<len(t2)):
            if (t1[i] < t2[i]): return -1
            if (t1[i] > t2[i]): return 1
            i = i + 1
        # At least one of them ran out...
        if (len(t1) < len(t2)): return -1
        if (len(t1) > len(t2)): return 1
        return 0

    def getPath(self) -> List:
        """Get a simple numeric path to the node, as a list.
        """
        f = []
        cur = self
        while (cur):
            f.insert(0, cur.getChildIndex())
            cur = cur.parentNode
        return f

    def getChildIndex(self, onlyElements:bool=False) -> int:
        """Return the position in order, among the node's siblings.
        The first child is [0]! Undefined for attribute nodes.
        TODO: Move assert to override in Attribute.
        """
        if (self.nodeType not in
            [ Node.ELEMENT_NODE, Node.TEXT_NODE, Node.COMMENT_NODE,
            Node.CDATA_SECTION_NODE, Node.PROCESSING_INSTRUCTION_NODE ]):
            raise HIERARCHY_REQUEST_ERR(
                "No child Index for nodeType %d." % (self.nodeType))
        thePar = self.parentNode
        if (not thePar):
            raise HIERARCHY_REQUEST_ERR("No parent found.")
        n = 0
        for sib in thePar.childNodes:
            if sib.isSameNode(self): return n
            if (not onlyElements or sib.isElement): n += 1
        raise HIERARCHY_REQUEST_ERR("child not found")

    def getFeature(self, feature, version):
        if (feature==version): return __version__
        return None

    def getUserData(self, key:str):
        return self.userData[key]

    def isDefaultNamespace(self, uri:str):
        return True
        #raise NOT_SUPPORTED_ERR

    def isEqualNode(self, n2):  # Node
        """See https://dom.spec.whatwg.org/#concept-node-equals.
        Overridden by DocumentType, Element, Text, Comment, ProcessingInstruction)
        """
        if (self.nodeType != n2.nodeType): return False
        raise HIERARCHY_REQUEST_ERR(
            "Node.isEqualNode() was not overridden for %s." % (self.nodeType))

    def isSameNode(self, n2) -> bool:
        return self is n2

    def lookupNamespaceURI(self, uri):
        cur = self
        while(cur):
            for nsa in cur.nsAttributes:
                if (nsa.namespaceURI == uri): return nsa.nsPrefix
            cur = cur.parentNode
        return None

    def lookupPrefix(self, prefix:NmToken) -> str:
        cur = self
        while(cur):
            for nsa in cur.nsAttributes:
                if (nsa.nsPrefix == prefix): return nsa.namespaceURI
            cur = cur.parentNode
        return None

    def setUserData(self, key:NmToken, data:Any, handler:Callable=None):
        if (self.userData is None): self.userData = {}
        self.userData[key] = (data, handler)

    def collectAllXml(self):
        raise NOT_SUPPORTED_ERR

    # TODO: Add methods and make it an instance of List
    #     (make childNodes the thing itself...)
    #     append()
    #     clear()
    #     count()
    #     extend()
    #     index()
    #     insert()
    #     pop()
    #     remove()
    #     sort() -- why not?
    # End class Node


###############################################################################
#
for nam, val in NodeTypes.__members__.items():
    setattr(Node, nam, val)


###############################################################################
# Cf https://developer.mozilla.org/en-US/docs/Web/API/Document
#
class Document(Node):
    """Creating the Document object, does *not* include creating a root element.
    """
    def __init__(self, namespaceUri:str, qualifiedName:str, doctype:str,
        isFragment:bool=False):
        print("Constructing Document Node, qname = '%s'." % (qualifiedName))
        if (not xr.isQName(qualifiedName)):
            raise ValueError("Document: qname '%s' isn't." % (qualifiedName))
        localName = XStr.getLocalPart(qualifiedName)
        if (not xr.isXmlName(localName)):
            raise ValueError("local part of '%s' is '%s', not an XML name." %
                (qualifiedName, localName))
        super(Document, self).__init__(
            nodeType=Node.DOCUMENT_NODE, nodeName=localName, ownerDocument=None)

        self.namespaceUri       = namespaceUri
        self.qualifiedName      = qualifiedName
        self.doctype            = doctype
        self.documentElement    = None

        self.impl               = 'sjd2019'
        self.version            = __version__

        self.IDIndex            = {}
        self.loadedFrom         = None
        self.characterSet       = 'utf-8'
        self.mimeType           = 'text/XML'
        self.uri                = None

    @property
    def charset(self):
        return self.characterSet
    @property
    def contentType(self):
        return self.mimeType
    @property
    def documentURI(self):
        return self.uri
    @property
    def domConfig(self):
        raise NOT_SUPPORTED_ERR
    @property
    def implementation(self):
        raise NOT_SUPPORTED_ERR
    @property
    def inputEncoding(self):
        return self.characterSet

    @property
    def nodeValue(self):  # Document
        return None

    def createElement(self, tagName:NmToken, attributes:Dict=None,
        parent:Node=None, text:str=None) -> 'Element':
        elem = Element(ownerDocument=self, nodeName=tagName)
        if attributes:
            for a, v in attributes.items():
                elem.setAttribute(a, v)
        if text:
            elem.appendChild(self.createTextNode(text))
        if parent:
            parent.appendChild(elem)
        return elem

    def createDocumentFragment(
        self,
        namespaceUri:str=None,
        qualifiedName:str="frag",
        doctype:str=None,
        isFragment:bool=True
        ) -> 'Document':
        df = Document(namespaceUri=namespaceUri,
            qualifiedName=qualifiedName, doctype=doctype, isFragment=True)
        df.isFragment = True
        return df

    def createAttribute(self, name:NmToken, value=None, parentNode=None) -> 'Attr':
        return Attr(name, value, ownerDocument=self,
            nsPrefix=None, namespaceURI=None, parentNode=parentNode)

    def createTextNode(self, data:str) -> 'Text':
        return Text(ownerDocument=self, data=data)

    def createComment(self, data:str) -> 'Comment':
        return Comment(ownerDocument=self, data=data)

    def createCDATASection(self, data:str) -> 'CDATASection':
        return CDATASection(ownerDocument=self, data=data)

    def createProcessingInstruction(self, target:NmToken, data:str
        ) -> 'ProcessingInstruction':
        return ProcessingInstruction(
            ownerDocument=self, target=target, data=data)

    def createEntityReference(self, name:NmToken) -> 'EntityReference':
        return EntityReference(ownerDocument=self, data=name)

    ####### EXTENSIONS

    createPI = createProcessingInstruction

    @property
    def outerXML(self) -> str:  # Node
        return self.startTag + self.innerXML + self.endTag

    @property
    def innerXML(self) -> str:  # Node
        t = ""
        for ch in self.childNodes:
            t += ch.outerXML()
        return t

    def tostring(self):  # Node
        buf = """<?xml version="1.0" encoding="utf-8"?>\n"""
        if (self.doctype):
            buf += self.doctype.tostring() + "\n"
        #buf += "\n<!-- n children: %d -->\n" % (len(self.childNodes))
        for ch in self.childNodes:
            buf += ch.tostring()
        return buf

    # End class Document


###############################################################################
# Element
#
class Element(Node):
    """DOM Level 2 Core.
    https://www.w3.org/TR/2000/REC-DOM-Level-2-Core-20001113/core.html
    https://docs.python.org/2/library/xml.dom.html#dom-element-objects
    """
    def __init__(self, ownerDocument=None, nodeName:NmToken=None):
        super(Element, self).__init__(
            ownerDocument=ownerDocument,
            nodeType=Node.ELEMENT_NODE, nodeName=nodeName)
        self.recursiveNodeValue = False

    @property
    def nodeValue(self):  # Element
        if (self.recursiveNodeValue):
            return self.text
        return None

    @property
    def tagName(self) -> NmToken: return self._nodeName

    def getAttribute(self, an:NmToken):
        avalue = self.attributes.getNamedItem(an)
        return avalue

    def setAttribute(self, an:NmToken, av):
        if (not xr.isXmlName(an)):
            raise NAME_ERR("Bad attribute name '%s'." % (an))
        attrNode = Attr(an, av,
            ownerDocument=self.ownerDocument,
            nsPrefix=None, namespaceURI=None, parentNode=self)
        self.attributes.setNamedItem(attrNode)
        if (an.startswith("xmlns:")):
            attrNode2 = Attr(an[6:], av,
                ownerDocument=self.ownerDocument,
                nsPrefix=None, namespaceURI=None, parentNode=self)
            self.nsAttributes.setNamedItem(attrNode2)

    def removeAttribute(self, an:NmToken):
        if (not xr.isXmlName(an)):
            raise NAME_ERR("Bad attribute name '%s'." % (an))
        if (self.hasAttribute(an)): del self.attributes[an]

    def getAttributeNode(self, an:NmToken):
        if (not xr.isXmlName(an)):
            raise NAME_ERR("Bad attribute name '%s'." % (an))
        if (self.hasAttribute(an)): return { an: self.attributes[an] }
        return None

    def setAttributeNode(self, an:NmToken, av):
        if (not xr.isXmlName(an)):
            raise NAME_ERR("Bad attribute name '%s'." % (an))
        self.attributes[an] = Attr(an, av, ownerDocument=self.ownerDocument,
        nsPrefix=None, namespaceURI=None, parentNode=None)

    def removeAttributeNode(self, an:NmToken):
        if (not xr.isXmlName(an)):
            raise NAME_ERR("Bad attribute name '%s'." % (an))
        if (self.hasAttribute(an)): del self.attributes[an]

    def getElementsByTagName(self, tagName:NmToken, nodeList=None):
        if (nodeList is None): nodeList = []
        if (self.nodeType != Node.ELEMENT_NODE): return nodeList
        if (self._nodeName == tagName): nodeList.append(self)
        for ch in self.childNodes:
            ch.getElementsByTagName(tagName, nodeList)
        return nodeList

    # Added in DOM 2
    def getAttributeNS(self, ns, an:NmToken) -> str:
        if (not xr.isXmlName(an)):
            raise NAME_ERR("Bad attribute name '%s'." % (an))
        avalue = self.attributes.getNamedItem(an)
        if (avalue): return avalue
        raise NOT_SUPPORTED_ERR

    def setAttributeNS(self, ns, an:NmToken, av):
        if (not xr.isXmlName(an)):
            raise NAME_ERR("Bad attribute name '%s'." % (an))
        attrNode = Attr(an, av,
            ownerDocument=self.ownerDocument,
            nsPrefix=ns, namespaceURI=None, parentNode=self)
        self.attributes.setNamedItem(attrNode)
        if (ns=="xmlns"):
            attrNode2 = Attr(an[6:], av,
                ownerDocument=self.ownerDocument,
                nsPrefix=ns, namespaceURI=None, parentNode=self)
            self.nsAttributes.setNamedItem(attrNode2)

    def removeAttributeNS(self, ns, an:NmToken):
        if (not xr.isXmlName(an)):
            raise NAME_ERR("Bad attribute name '%s'." % (an))
        if (self.hasAttribute(an)): del self.attributes[an]

    def getAttributeNodeNS(self, ns, an:NmToken) -> str:
        if (not xr.isXmlName(an)):
            raise NAME_ERR("Bad attribute name '%s'." % (an))
        raise NOT_SUPPORTED_ERR

    def setAttributeNodeNS(self, ns, an:NmToken, av):
        if (not xr.isXmlName(an)):
            raise NAME_ERR("Bad attribute name '%s'." % (an))
        raise NOT_SUPPORTED_ERR

    def hasAttribute(self, an:NmToken) -> bool:
        if (not xr.isXmlName(an)):
            raise NAME_ERR("Bad attribute name '%s'." % (an))
        for k, _v in self.attributes.items():
            if (k==an): return True
        return False

    def hasAttributeNS(self, an:NmToken, ns) -> bool:
        if (not xr.isXmlName(an)):
            raise NAME_ERR("Bad attribute name '%s'." % (an))
        for k, _v in self.attributes.items():
            if (k==an): return True
        return False

    ####### EXTENSIONS

    @property
    def outerXML(self) -> str:  # Element
        return self.startTag + self.innerXML + self.endTag

    @property
    def innerXML(self) -> str:  # Element
        t = ""
        for ch in self.childNodes:
            t += ch.outerXML()
        return t

    # TODO: Add innerXML and outerXML setters

    @property
    def startTag(self, sortAttrs:bool=True) -> str:
        """Gets a correct start-tag for the element.
        Never produces empty-tags, however.
        """
        if (not isinstance(self, Element)): return ''
        t = "<" + self._nodeName
        names = self.attributes.keys()
        if (sortAttrs): names = sorted(names)
        for k in names:
            t += ' %s="%s"' % (k, XStr.escapeAttribute(set.attributes[k]))
        return t + ">"

    @property
    def endTag(self) -> str:
        if (not isinstance(self, Element)): return ''
        return "</" + self._nodeName + ">"

    ########## Properties/functions involving counting siblings (not DOM)
    @property
    def firstElementChild(self):
        for ch in self.childNodes:
            if (ch.nodeType == Node.ELEMENT_NODE): return ch
        return None

    @property
    def lastElementChild(self):
        nchildren = len(self.childNodes)
        i = nchildren-1
        while (i>=0):
            ch = self.childNodes[i]
            if (ch.nodeType == Node.ELEMENT_NODE): return ch
            i -= 1
        return None

    @property
    def elementChildNodes(self):
        x = []
        for ch in self.childNodes:
            if (ch.nodeType == Node.ELEMENT_NODE): x.append(ch)
        return x

    # Return the nth *element* child of the Node
    def elementChildN(self, n:int):
        elementCount = 0
        for ch in self.childNodes:
            if (ch.nodeType == Node.ELEMENT_NODE):
                elementCount += 1
                if (elementCount >= n): return ch
        return None


    ###########################################################################
    # Misc
    #
    def isEqualNode(self, n2) -> bool:  # Element
        if (self.nodeType != n2.nodeType): return False
        if (self._nodeName!=n2._nodeName or
            len(self.attributes) != len(n2.attributes) or
            self.nsPrefix != n2.nsPrefix or
            self.namespaceURI != n2.namespaceURI): return False

        for anode in self.attributes.theAttrs:  # TODO: Check
            if (not anode.isEqualAttr(anode.name, n2)): return False

        if (len(self.childNodes) != len(n2.childNodes)): return False

        for i, ch1 in enumerate(self.childNodes):
            if (not ch1.isEqualNode(n2.childNodes[i])): return False

        return True


    ###########################################################################
    # Node/Element: Attributes
    #
    # FIX: Review for attribute node vs. value to be returned!
    #
    @property
    def classList(self) -> List[NmToken]:
        return re.split(r'\s+', self.getAttribute('class'))

    @property
    def className(self) -> str:
        return self.getAttribute('class')

    @property
    def id(self) -> str:
        idName = self.hasIDAttribute
        if (idName): return self.getAttribute(idName)
        return None


    ###########################################################################
    # Fetching elements

    # getElementsByClassName
    #
    # Return element by class name.
    # Works even if it's just one of multiple class tokens.
    #
    def getElementsByClassName(self, className:str, nodeList=None):
        if (nodeList is None): nodeList = []
        if (self.nodeType != Node.ELEMENT_NODE): return nodeList
        if (className in self.getAttribute('class') and
            (' '+className+' ') in (' '+self.getAttribute('class')+' ')):
            nodeList.append(self)
        for ch in self.childNodes:
            ch.getElementsByClassName(className, nodeList)
        return nodeList

    # For HTML these should be case-insensitive.
    #
    def getElementById(self, IDValue:str):  # DOM 2
        if (self.ownerDocument.MLDeclaration.caseInsensitive):
            IDValue = IDValue.lower()
        if (IDValue in self.ownerDocument.IDIndex):
            return self.ownerDocument.IDIndex[IDValue]
        return None
    getElementById = getElementById  # Gimme a break....

    def getElementsByTagNameNS(self, tagName:NmToken, namespaceURI:str, nodeList=None):
        if (not xr.isXmlName(tagName)):
            raise NAME_ERR("Bad attribute name '%s'." % (tagName))
        if (nodeList is None): nodeList = []
        if (self.nodeType != Node.ELEMENT_NODE): return nodeList
        if (self._nodeName == tagName and
            self.namespaceURI == namespaceURI): nodeList.append(self)
        for ch in self.childNodes:
            ch.getElementsByTagNameNS(tagName, nodeList, namespaceURI)
        return nodeList

    ########### Node/Element: JQuery-like 'find'?
    # See https://api.jquery.com/find/
    # and http://api.jquery.com/Types/#Selector
    #
    def find(self):                         # Whence?
        raise NOT_SUPPORTED_ERR

    def findAll(self):                      # Whence?
        raise NOT_SUPPORTED_ERR


    ########### Node/Element: Modify actual tree
    #
    def insertAdjacentHTML(self, html:str):
        raise NOT_SUPPORTED_ERR

    ########### Node/Element:: Other
    #
    def matches(self):
        raise NOT_SUPPORTED_ERR

    def querySelector(self):
        raise NOT_SUPPORTED_ERR

    def querySelectorAll(self):
        raise NOT_SUPPORTED_ERR

    def remove(self):
        raise NOT_SUPPORTED_ERR

    def tostring(self) -> str:  ### Not DOM
        buf = self.startTag
        for ch in self.childNodes:
            buf += ch.tostring()
        buf += self.endTag
        return buf

    # End class Element


###############################################################################
#
class Leaf(Node):  # AKA CharacterData?
    """A cover class for the Node sub-types that can only occur as leaf children:
    Text, CDATASection, ProcessingInstruction, Comment, EntityReference,
    Notation, DocumentType.
    """
    def __init__(self, nodeType:NodeType=0, nodeName:NmToken=None,
        ownerDocument=None, data:str=""):
        super(Leaf, self).__init__(
            nodeType=nodeType, nodeName=None, ownerDocument=ownerDocument)
        self.data = data

    @property
    def nodeValue(self):
        return self.data

    @property
    def nodeValue_setter(self, newData:str=""):
        self.data = newData

    def isEqualNode(self, n2) -> bool:
        if (self.nodeType != n2.nodeType): return False
        if (self.ownerDocument != n2.ownerDocument): return False
        if (self.data != n2.data): return False
        return True

    # TODO: Offer options to wrap text/comments?
    def tostring(self) -> str:
        return self.data

    # Override any methods that can't apply to leaves. Don't know why DOM
    # put them on Node instead of Element.
    #
    def replaceChild(self, newChild, oldChild):
        raise NOT_SUPPORTED_ERR
    def removeChild(self, oldChild):
        raise NOT_SUPPORTED_ERR
    def appendChild(self, newChild):
        raise NOT_SUPPORTED_ERR
    def hasChildNodes(self) -> bool:
        return False


###############################################################################
#
class Text(Leaf):
    def __init__(self, ownerDocument=None, data:str=""):
        super(Text, self).__init__(
            nodeType=Node.TEXT_NODE, nodeName="#text",
            ownerDocument=ownerDocument)
        self.data          = data

    ####### EXTENSIONS

    @property
    def outerXML(self) -> str:  # Text
        return XStr.escapeText(self.data)

    @property
    def innerXML(self) -> str:  # Text
        return XStr.escapeText(self.data)

    def tostring(self) -> str:
        return self.outerXML


###############################################################################
#
class CDATASection(Leaf):
    def __init__(self, ownerDocument, data:str):
        super(CDATASection, self).__init__(
            nodeType=Node.CDATA_SECTION_NODE, nodeName="#cdata-section",
            ownerDocument=ownerDocument, data=data)
        #Node.__init__(nodeType=Node.CDATA_SECTION_NODE, ownerDocument=ownerDocument)
        self.data          = data

    ####### EXTENSIONS

    @property
    def outerXML(self) -> str:  # CDATASection
        return '<![CDATA[%s]]>' % (XStr.escapeCDATA(self.data))

    @property
    def innerXML(self) -> str:  # CDATASection
        return XStr.escapeCDATA(self.data)

    def tostring(self) -> str:  # CDATASection
        return self.outerXML


###############################################################################
#
class ProcessingInstruction(Leaf):
    def __init__(self, ownerDocument=None, target=None, data:str=""):
        if (target is not None and target!="" and not xr.isXmlName(target)):
            raise NAME_ERR("Bad PI target '%s'." % (target))
        super(ProcessingInstruction, self).__init__(
            nodeType=Node.PROCESSING_INSTRUCTION_NODE, nodeName=target,
            ownerDocument=ownerDocument, data=data)
        self.data          = data

    def cloneNode(self, deep:bool=False):
        newNode = ProcessingInstruction(
            ownerDocument=self.ownerDocument,
            target=self._nodeName,
            data=self.data
            )
        if (self.userData): newNode.userData = self.userData
        return newNode

    ####### EXTENSIONS

    @property
    def outerXML(self) -> str:  # ProcessingInstruction
        return '<?%s %s?>' % (XStr.escapePI(self.target), XStr.escapePI(self.data))

    @property
    def innerXML(self) -> str:  # ProcessingInstruction
        return XStr.escapePI(self.data)

    def tostring(self) -> str:  # ProcessingInstruction
        return self.outerXML

PI = ProcessingInstruction


###############################################################################
#
class Comment(Leaf):
    def __init__(self, ownerDocument=None, data:str=""):
        super(Comment, self).__init__(
            nodeType=Node.COMMENT_NODE, nodeName="#comment",
            ownerDocument=ownerDocument, data=data)
        self.data = data

    ####### EXTENSIONS

    @property
    def outerXML(self) -> str:  # Comment
        return '<!--%s-->' % (XStr.escapeComment(self.data))

    @property
    def innerXML(self) -> str:  # Comment
        return XStr.escapeComment(self.data)

    def tostring(self) -> str:  # Comment
        return self.outerXML


###############################################################################
#
class EntityReference(Leaf):
    """These nodes are special, for apps that need to track physical structure
    as well as logical. This has not been tested. Probably it should carry
    the original name, and any declared PUBLIC/SYSTEM IDs (or the literal
    expansion text), and the NOTATION if any.
    """
    def __init__(self, ownerDocument=None, data:str=""):
        super(EntityReference, self).__init__(
            nodeType=Node.ENTITY_REFERENCE_NODE, nodeName="#entity", # TODO
            ownerDocument=ownerDocument, data=data)
        self.data = data

    ####### EXTENSIONS

    @property
    def outerXML(self) -> str:  # EntityReference
        return '&%s;' % (self.data)

    @property
    def innerXML(self) -> str:  # EntityReference
        return self.data

    def tostring(self) -> str:  # EntityReference
        return self.outerXML

EntRef = EntityReference


###############################################################################
#
class Notation(Leaf):
    """This is for entities in a given data notation/format. They are normally
    embedded by declaring an external file or object as an ENTITY, and then
    mentioning that entity name (not actually referencing the entiry), as
    the value of an attribute that was declared as being of type ENTITY.
    """
    def __init__(self, ownerDocument=None, data:str=""):
        super(Notation, self).__init__(
            nodeType=Node.NOTATION_NODE, nodeName="#notation", # TODO
            ownerDocument=ownerDocument, data=data)
        self.data = data

    ####### EXTENSIONS

    @property
    def outerXML(self) -> str:  # Notation
        return ""

    @property
    def innerXML(self) -> str:  # Notation
        return self.data

    def tostring(self) -> str:  # Notation
        return self.outerXML


###############################################################################
#
class Attr(Node):
    """This is a little weird, because each Node owns a NamedNodeMap (which is
    not a subclass of Node), and the NamedNodeMap then owns the Attr objects.

    TODO: namespace support
    FIX: Deal with case-ignorance as for HTML
    """
    def __init__(self, name:NmToken, value:str, ownerDocument=None,
        nsPrefix:NmToken=None, namespaceURI:str=None, parentNode=None):
        if (ownerDocument is None):
            if (parentNode): ownerDocument = parentNode.ownerDocument
        elif (ownerDocument!=parentNode.ownerDocument):
            raise WRONG_DOCUMENT_ERR()
        if (not xr.isXmlName(name)):
            raise NAME_ERR(
                "Bad attribute name '%s'." % (name))
        super(Attr, self).__init__(
            nodeType=Node.ATTRIBUTE_NODE, nodeName=name,
            ownerDocument=ownerDocument)
        self.parentNode    = parentNode
        self.name          = self._nodeName = name
        self.localName     = re.sub(r'^.*:', '', name)
        self.prefix        = re.sub(r':.*$', '', name)
        self.value         = value
        self.namespaceURI  = namespaceURI

        # In DOM, Attributes have a parent (the element), but are not
        # listed in the element childNodes.
        #
        if (parentNode and not parentNode.isElement):
            raise HIERARCHY_REQUEST_ERR(
                "parentNode for attr '%s' is type %s, not %s." %
                (name, parentNode.nodeType, Node.ELEMENT_NODE))

    def isEqualAttr(self, other) -> bool:
        if (self.name         == other.name and
            self.value        == other.value and
            self.nsPrefix     == other.nsPrefix and
            self.namespaceURI == other.namespaceURI): return True
        return False

    def cloneNode(self, deep:int=False):
        newNode = Attr(self.name, self.data,
            ownerDocument=self.ownerDocument,
            nsPrefix=self.nsPrefix, namespaceURI=self.namespaceURI,
            parentNode=self.parentNode)
        if (self.userData): newNode.userData = self.userData
        return newNode

    @property
    def outerXML(self) -> str:  # Attr
        return "%s=%s" % (self.name, self.innerXML())

    @property
    def innerXML(self) -> str:  # Attr
        return '"' + XStr.escapeAttr(self.value) + '"'


Attribute = Attr  # Attr vs. setAttribute


###############################################################################
#
class NodeList(list):
    def item(self, i):
        return self[i]

    def length(self, i):
        return len(self)


###############################################################################
#
class NamedNodeMap(OrderedDict):
    """This is really just a dict or OrderedDict (latter lets us retain
    order from source if desired). So let people do Python stuff with it.
    """
    def __init__(self, ownerDocument=None, parentNode=None):
        super(NamedNodeMap, self).__init__()
        self.ownerDocument = ownerDocument
        self.parentNode    = parentNode
        self.byLocalName   = {}  # TODO: Collisions?

    def __len__(self):
        return len(self)

    def getNamedItem(self, name:NmToken):
        if (name in self):
            return self[name]
        return None

    def setNamedItem(self, attrNode):
        name = attrNode.name
        if (not xr.isXmlName(name)):
            raise NAME_ERR("Bad name '%s'." % (name))
        self[attrNode.name] = attrNode.value
        self.byLocalName[XStr.getLocalPart(name)] = attrNode.value

    def removeNamedItem(self, name:NmToken):
        if (name in self.byLocalName):
            del self.byLocalName[name]
            pos = self.getIndexOf(name)
            if (pos is not None): del self[pos]
            del self.byLocalName[XStr.getLocalPart(name)]

    def item(self, index:int):
        if (index < 0 or len(self) <= index): return None
        i = 0
        for key in self.keys():
            if (i >= index): return self[key]
            i += 1
        assert False

    def tostring(self) -> str:
        s = ""
        for k, v in self.items():
            s += ' %s="%s"' % (k, XStr.escapeAttribute(v))
        return s

    def getNamedItemNS(self, name:NmToken):
        raise NOT_SUPPORTED_ERR  # TODO

    def setNamedItemNS(self, attrNode:Node):
        if (not xr.isXmlName(attrNode.name)):
            raise NAME_ERR("Bad name '%s'." % (attrNode.name))
        raise NOT_SUPPORTED_ERR  # TODO

    def removeNamedItemNS(self, attrNode:Node):
        raise NOT_SUPPORTED_ERR  # TODO

    def clone(self):
        # TODO: Namespaces
        other = NamedNodeMap(
            ownerDocument=self.ownerDocument, parentNode=self.parentNode)
        for anode in self.keys():
            attrNodeCopy = Attr(anode.name, anode.data,
                ownerDocument=self.ownerDocument,
                nsPrefix=None, namespaceURI=None, parentNode=self.parentNode)
            other.setNamedItem(attrNodeCopy)
        return other

    def getIndexOf(self, name:NmToken):  ### Not DOM
        """This returns the position of the node in the order.
        """
        for k, v in enumerate(self):
            if (v.name == name): return k
        return None


###############################################################################
# Main
#
if __name__ == "__main__":
    import argparse
    import testDom

    lg = logging.getLogger("BaseDOM main")

    def processOptions():
        try:
            from BlockFormatter import BlockFormatter
            parser = argparse.ArgumentParser(
                description=descr, formatter_class=BlockFormatter)
        except ImportError:
            parser = argparse.ArgumentParser(description=descr)

        parser.add_argument(
            "--baseDom", action='store_true',
            help='Use BaseDOM instead of xml.dom.minidom')
        parser.add_argument(
            "--quiet", "-q", action='store_true',
            help='Suppress most messages.')
        parser.add_argument(
            "--verbose", "-v", action='count', default=0,
            help='Add more messages (repeatable).')
        parser.add_argument(
            "--version", action='version', version=__version__,
            help='Display version information, then exit.')

        parser.add_argument(
            'files', type=str,
            nargs=argparse.REMAINDER,
            help='Path(s) to input file(s)')

        args0 = parser.parse_args()
        return(args0)

    def makeMinidomDoc():
        import xml.dom.minidom
        theDomImpl = xml.dom.minidom.getDOMImplementation()
        print("Creating document via minidom")
        theDoc = theDomImpl.createDocument(None, "HTML", None)
        theDoctype = theDomImpl.createDocumentType(
            "HTML",
            "-//W3C//DTD XHTML 1.0 Strict//EN",
            "http://www.w3.org/TR/xhtml1/DTD/xhtml1-strict.dtd")
        theDoc.doctype = theDoctype
        testDom.fillDoc(theDoc)
        return theDomImpl, theDoc

    def makeBaseDOMDoc():
        theDomImpl = DOMImplementation.py.getDOMImplementation()
        print("Creating document via BaseDOM")
        theDoc = theDomImpl.createDocument(None, "HTML", None)
        theDoctype = theDomImpl.createDocumentType(
            "HTML",
            "-//W3C//DTD XHTML 1.0 Strict//EN",
            "http://www.w3.org/TR/xhtml1/DTD/xhtml1-strict.dtd")
        theDoc.doctype = theDoctype
        testDom.fillDoc(theDoc)
        return theDomImpl, theDoc


    ###########################################################################
    #
    print("******* UNFINISHED *******")

    args = processOptions()

    if (len(args.files) > 0):
        for path0 in args.files:
            #fh0 = codecs.open(path0, "rb", encoding="utf-8")
            #theXML = xml.dom.minidom.parse(fh0)
            db = DOMBuilder.DOMBuilder(path0)
            #db.feed(h)
            print("\nResults:")
            print(db.tostring())
            #fh0.close()

    else:
        lg.warning("No files specified, synthesizing via testDom.py....")
        if (args.baseDom):
            domImpl, theOwnerDocument = makeBaseDOMDoc()
        else:
            domImpl, theOwnerDocument = makeMinidomDoc()
        testDom.exercise(domImpl, theOwnerDocument)

        if (args.baseDom):
            print("\nResults:")
            print(theOwnerDocument.collectAllXml())

    lg.warning("\nBaseDOM.py test done.")
