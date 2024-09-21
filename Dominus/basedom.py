#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# A fairly simple native Python DOM implementation. Basically DOM 2,
# plus a bunch of Pythonic, xpath, etree, etc. conveniences.
#
#pylint: disable=W0613, W0212
#pylint: disable=E1101
#
import re
from collections import OrderedDict
from enum import Enum
import unicodedata
from typing import Any, Callable, Dict, List, Union, Iterable
import logging

from xmlstrings import XmlStrings as XStr
from nodetypes import NodeTypes
#from domgetitem import __domgetitem__  # NodeSelKind
from dombuilder import DOMBuilder

lg = logging.getLogger("BaseDOM")

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

descr = """See BaseDom.md"""


###############################################################################
# xml.dom.minidom uses typical Python exceptions, although DOM defines
# it's own. Not sure which way to go.
#
# https://developer.mozilla.org/en-US/docs/Web/API/DOMException
# w3.org/TR/1998/REC-DOM-Level-1-19981001/level-one-core.html
# http://stackoverflow.com/questions/1319615
# https://docs.python.org/2/library/xml.dom.html
#
class DOMException(Exception):                 pass

class HIERARCHY_REQUEST_ERR(ValueError):       pass  # 3
class WRONG_DOCUMENT_ERR(ValueError):          pass  # 4
class INVALID_CHARACTER_ERR(ValueError):       pass  # 5
class NOT_FOUND_ERR(ValueError):               pass  # 8
class NOT_SUPPORTED_ERR(Exception):            pass  # 9
class NAMESPACE_ERR(ValueError):               pass
### Rest unused:
#
#class INDEX_SIZE_ERR(Index_Error):              pass  # 1
#class DOMSTRING_SIZE_ERR(Index_Error):          pass  # 2
#class NO_DATA_ALLOWED_ERR(ValueError):          pass  # 6
#class NO_MODIFICATION_ALLOWED_ERR(Exception):   pass  # 7
#class INUSE_ATTRIBUTE_ERR(Exception):           pass  # 10
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

# Not in minidom:
NAME_ERR = INVALID_CHARACTER_ERR

_xmlNS_URI = "http://www.w3.org/XML/1998/namespace"

def escapeJsonStr(s:str) -> str:
    return re.sub(r'([\\"])', "\\\\1", s)


class UNormTx(Enum):
    """Whether/how various tokens should be Unicode-normalized.
    """
    NONE = "NONE"
    NFKC = "NFKC"
    NFKD = "NFKD"
    NFC = "NFC"
    NFD = "NFD"

    @staticmethod
    def normalize(s:str, which:'UNormTx'="NONE") -> str:
        which = toEnum(UNormTx, which)
        if not which: return s
        return unicodedata.normalize(str(which), s)

class CaseTx(Enum):
    NONE = "NONE"
    FOLD = "FOLD"
    LOWER = "LOWER"


###############################################################################
#
def getDOMImplementation(name:str=None, features=None):
    #return DOMImplementation(name, features)
    assert name is None and features is None
    return DOMImplementation()

class DOMImplementation:
    name = "BaseDOM"
    version = "0.1"
    _features = [
        ("core", "1.0"),
        ("core", "2.0"),
        ("core", None),
        ("xml", "1.0"),
        ("xml", "2.0"),
        ("xml", None),
        ("ls-load", "3.0"),  # ???
        ("ls-load", None),  # ???
        # new
        ("caseSensitive", True),  # ??? settable?
        ("verbose", 0),
        # Possibles?
        ("prev-next", 1),
        ("getitem-n", 1),
        ("getitem-name", 1),
        ("getitem-attr", 1),
        ("nodeTypeProps", 1),
        ("NodeTypesEnum", 1),
        ("attr-types", 1),
        ("constructor-content", 1),
        ("NS-any", 1),
        ("value-indexer", 1),
        ("jsonx", 1),
    ]

    def hasFeature(self, feature, version):
        if version == "":
            version = None
        return (feature.lower(), version) in self._features

    def __init__(self, name:str=None, features=None):
        if name: DOMImplementation.name = name
        if features:
            #for k, v in features.items:
            #    DOMImplementation.features[k] = v
            pass

    def createDocument(self, namespaceURI:str, qualifiedName:NmToken,
        doctype:'DocumentType'
        ) -> 'Document':
        doc = Document(namespaceURI, qualifiedName, doctype)

        # TODO Move rest into Document constructer so can just instantiate
        # TODO: Inherited ns should not show up in nodeName. Explicit do, and
        # namespaceURI should get the right thing, but prefix is empty.
        #
        add_root_element = not (
            namespaceURI is None and qualifiedName is None and doctype is None)

        if namespaceURI is None: namespaceURI = ""

        if not qualifiedName and add_root_element:
            raise INVALID_CHARACTER_ERR("Root element to be has no name")
        prefix = XStr.getLocalPart(qualifiedName)
        if prefix == "xml":
            if namespaceURI in [ _xmlNS_URI, "" ]:
                namespaceURI = _xmlNS_URI
            else:
                raise NAMESPACE_ERR("URI for 'xml' prefix is not '%s'" % (_xmlNS_URI))

        doc.documentElement = doc.createElement(qualifiedName)
        if doctype: doctype.parentNode = doctype.ownerDocument = doc
        doc.doctype = doctype
        return doc

    def createDocumentType(self, qualifiedName:NmToken,
        publicId:str, systemId:str) -> 'DocumentType':
        import DocumentType
        #loc = XStr.getLocalPart(qualifiedName)
        return DocumentType.DocumentType(qualifiedName, publicId, systemId)

    # DOM Level 3

    def getInterface(self, feature):
        if self.hasFeature(feature, None):
            return self
        else:
            return None

    # internal
    def _create_document(self):
        return Document(None, "root", None)

    def registerDOMImplementation(self, name:str, factory):
        pass

    @staticmethod
    def getImplementation():
        return None  #DOMImplementation?

    # And put in some loaders

    def parse(self, filename_or_file:str, parser=None, bufsize:int=None
        ) -> 'Document':
        dbuilder = DOMBuilder()
        theDom = dbuilder.parse(filename_or_file)
        return theDom

    def parse_string(self, s:str, parser=None):
        dbuilder = DOMBuilder()
        theDom = dbuilder.parse_string(s)
        return theDom


###############################################################################
#
class NodeList(list):  # TODO: Or UserList?
    """We just subclass Python list.
    EXCEPT that in/contains only test for *value* -- and the value of a list L
    is simply a boolean for whether it's non-empty, which is useless for us.

    NodeList seems kind of obsolete. Move to whatwg extensions?
    https://dom.spec.whatwg.org/#interface-nodelist
    """
    getLength = len

    def item(self, index:int) -> 'Node':
        return self[index]

    def __contains__(self, item:'Node') -> bool:
        """Careful, the Python built-in "contins"/"in" is wrong for node containment!
        NodeList is not parent to its items, like a regular Element Node is.
        """
        assert isinstance(item, Node)
        for x in self:
            if x is item: return True
        return False

    def __mul__(self, x):
        if self: raise NotImplementedError("No multiplying elements.")

    def __rmul__(self, x):
        if self: raise NotImplementedError("No rmultiplying elements.")


###############################################################################
#
class Node(NodeList):
    """The main class for DOM, from which most others are derived.

    https://www.w3.org/TR/2000/REC-DOM-Level-2-Core-20001113
    TODO: Hook up __getitem__ !
    """
    #__slots__ = ("nodeType", "nodeName", "ownerDocument", "parentNode")

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

    # The *constant* nodeName strings. The rest use  a real name
    # (Element, Attr, PI (target), DocumentType).
    __reservedNodeNames__ = {
        CDATA_SECTION_NODE          : '#cdata-section',
        COMMENT_NODE                : '#comment',
        DOCUMENT_NODE               : '#document',
        DOCUMENT_FRAGMENT_NODE      : '#document-fragment',
        TEXT_NODE                   : '#text',
    }

    def __init__(self, nodeType:Union[int, NodeTypes],
        ownerDocument:'Document'=None, nodeName:NmToken=None):
        super(Node, self).__init__()

        #lg.info("Constructing Node, type %s, owner %s @ %x, name %s.", nodeType,
        #    ownerDocument,  id(ownerDocument) if ownerDocument else 0, nodeName)

        if isinstance(nodeType, int): nodeType = NodeTypes(nodeType)
        if not isinstance(nodeType, NodeTypes):
            raise TypeError("New node not of known nodeType.")
        self.nodeType = nodeType
        if (not XStr.isXmlName(nodeName)
            and nodeName not in Node.__reservedNodeNames__.values()):
            raise KeyError(
                "New node name '%s' is not an XML or reserved name." % (nodeName))
        self.nodeName = nodeName

        self.ownerDocument:Document = ownerDocument
        if ownerDocument is not None and ownerDocument.nodeType != NodeTypes.DOCUMENT_NODE:
            raise TypeError("parenownerDocument for new node is not DOCUMENT.")
        self.parentNode:Node = None
        self.userData = None
        #self.nsAttributes = NamedNodeMap(self.ownerDocument, self)
        #self.startLoc = None    # Can track XML source position
        # target is only for PIs
        self.data = None  # Character data, mainly

        if nodeType == NodeTypes.ELEMENT_NODE:  # Move to subclass?
            self.attributes = None  # NamedNodeMap()

    def __contains__(self, item:'Node') -> bool:
        """Careful, the Python built-in "contins"/"in" is wrong for node
        containment, because lists are considered equal if they contain
        the same items. That means:
            * an element that contains any empty node, contains all empty nodes.
            * testing contains cost a recursive traversal
            * testing is essentially by isEqualNode, not isSameNode.
        """
        return item.parentNode == self

    def __eq__(self, other:'Node') -> bool:
        """Two different nodes cannot be in the same place, nor the same node
        in two different places, so it's ok to test eq/ne via identity.
        """
        return self is other

    def __ne__(self, other:'Node') -> bool:
        return self is not other

    def __lt__(self, other:'Node') -> bool:
        return self.compareDocumentPosition(other) < 0

    def __le__(self, other:'Node') -> bool:
        return self.compareDocumentPosition(other) <= 0

    def __ge__(self, other:'Node') -> bool:
        assert self.ownerDocument == other.ownerDocument
        return self.compareDocumentPosition(other) >= 0

    def __gt__(self, other:'Node') -> bool:
        assert self.ownerDocument == other.ownerDocument
        return self.compareDocumentPosition(other) > 0

    def NOTYET__getitem__(self, key: Union[int, slice, str]):
        if isinstance(key, int):
            return super(Node, self).__getitem__(key)
        if isinstance(key, str):
            theChosen = []
            for ch in self:
                if ch.nodeName == key: theChosen.append(ch)
            return theChosen or None
        elif isinstance(key, slice):
            # TODO Component are instances of "member_descriptor"
            #return __domgetitem__(self, slice.start, slice.stop, slice.step)
            assert False, "Not hooked up yet"
        else:
            raise IndexError("Unexpected [] arg type: %s" % (type(key)))

    def NOTYET__bool__(self) -> bool:
        """This is so that a node with no children is not false, making it
        safe to do things like:
            if (x.parentNode)
        instead of requiring:
            if (x.parentNode is not None)
        Probably don't do this while debugging, so the library itself is clear.
        """
        return True

    @property
    def childNodes(self) -> List:
        return self  # OR list(self)?

    @property
    def parentElement(self) -> 'Node':
        if (self.parentNode is None
            or not self.parentNode.isElement): return None
        return self.parentNode

    @property
    def nextSibling(self) -> 'Node':
        if self.parentNode is None: return None
        if self.isLastChild: return None
        return self.parentNode.childNodes[self.getChildIndex()+1]

    @property
    def previousSibling(self) -> 'Node':
        if self.parentNode is None: return None
        if self.isFirstChild: return None
        return self.parentNode.childNodes[self.getChildIndex()-1]

    @property
    def previous(self) -> 'Node':
        """Find the previous node. If you're first it's your parent;
        otherwise it's your previous sibling's last descendant.
        """
        #lg.error("previous: At '%s' (cnum %d), is1st %s.",
        #    self.nodeName, self.getChildIndex(), self.isFirstChild)
        if self.parentNode is None: return None
        if self.isFirstChild: return self.parentNode
        pr = self.previousSibling.rightmost
        if pr is not None: return pr
        return self.previousSibling

    @property
    def next(self) -> 'Node':
        if self.childNodes: return self.childNodes[0]
        cur = self
        while (cur.parentNode is not None):
            if not cur.isLastChild: return cur.nextSibling
            cur = cur.parentNode
        return None

    # Next three are defined on Node, but only work for Element and Attr.
    @property
    def prefix(self) -> str:
        return None
    @property
    def localName(self) -> str:
        return None
    @property
    def namespaceURI(self) -> str:
        return None

    @property
    def isConnected(self) -> bool:
        """Overridden for Attr nodes. (HTML DOM ONLY)
        """
        if not self.ownerDocument: return False
        if self.ownerDocument.documentElement is self: return True
        if self.parentNode is None: return False
        return True

    @property
    def nodeValue(self):
        """null for Document, Frag, Doctype, Element, NamedNodeMap.
        """
        return None

    @nodeValue.setter
    def nodeValue(self, newData:str=""):
        raise NOT_SUPPORTED_ERR(
            "Cannot set nodeValue on nodeType %s." % (self.nodeType.__name__))

    @property
    def textContent(self, delim:str=" ") -> str:
        """Cat together all descendant text nodes, optionally with separators.
        @param delim: What to put between the separate text nodes
        """
        textBuf = ""
        if self.isText:
            if textBuf: textBuf += delim
            textBuf += self.data
        elif self.childNodes:
            for ch in self.childNodes:
                if textBuf: textBuf += delim
                textBuf += ch.textContent(delim=delim)
        return textBuf

    @textContent.setter
    def textContent(self, newData:str) -> None:
        if self.nodeType == NodeTypes.TEXT_NODE:
            self.data = newData
        else:
            # TODO Maybe replace whole subtree w/ new text node?
            raise NOT_SUPPORTED_ERR(
            "Cannot set textContent on nodeType %s." % (self.nodeType.__name__))

    ### Methods
    #
    def cloneNode(self, deep:bool=False) -> 'Node':
        """NOTE: Default value for 'deep' has changed in spec and browsers!
         Don't copy the tree relationships.
         TODO: Move nodeType cases to the subclasses.
        """
        nt = self.nodeType
        if   (nt==Node.ELEMENT_NODE):
            newNode = Element(ownerDocument=self.ownerDocument,
                nodeName=self.nodeName)
            if self.attributes:
                newNode.attributes = self.attributes.clone()
            else:
                newNode.attributes = None
            newNode.userData = self.userData
            if deep and self.childNodes:
                for ch in self.childNodes:
                    newNode.appendChild(ch.cloneNode(deep=True))

        if self.userData: newNode.userData = self.userData
        return newNode

    def compareDocumentPosition(self, other:'Node') -> int:
        """Returns -1, 0, or 1 to reflect relative document order.
        Two different nodes cannot be in the same places, nor the same node
        in two different places (like, say, electrons). Therefore, for
        equality it's enough to test identity instead of position.

        XPointers are good for this, except that getChildIndex() is O(fanout).

        Does not apply to Attribute nodes (overridden).
        """
        assert self.ownerDocument == other.ownerDocument
        assert self.parentnode is not None and other.parentnode is not None
        if self is other: return 0
        t1 = self.getNodePath()
        t2 = other.getNodePath()
        minLen = min(len(t1), len(t2))
        for i in range(minLen):
            if t1[i] < t2[i]: return -1
            if t1[i] > t2[i]: return 1
        # At least one of them ran out...
        if len(t1) < len(t2): return -1
        if len(t1) > len(t2): return 1
        raise ValueError("Non-identical nodes with equal position shouldn't happen.")

    def contains(self, other:'Node') -> bool:
        """UNLIKE __contains__, this includes recursive containment (descendants).

        This way is far faster than searching all descendants.
        BTW, nodes do NOT contain self, nor elements attributes.
        NOTE: DOM "contains" means descendant; Python "contains" means child.
        Uing the synonym 'hasDescendant' may help avoid confusion.
        """
        other = other.parentNode
        while (other is not None):
            if other is self: return True
            other = other.parentNode
        return False

    hasDescendant = contains

    def getRootNode(self) -> 'Node':
        """This seems mainly meant for HTML shadow stuff.
        """
        return self.ownerDocument

    def hasAttributes(self) -> bool:
        return (self.attributes is not None and len(self.attributes) > 0)

    def isDefaultNamespace(self, uri:str) -> bool:  # TODO Implement
        return True
        #raise NOT_SUPPORTED_ERR("isDefaultNamespace")

    def isEqualNode(self, n2) -> bool:  # Node
        """Check the common properties that matter.
        Subclasses may override to check more, but should call this, too!
        See https://dom.spec.whatwg.org/#concept-node-equals.
        This does *not* check ownerDocument, so should work across docs.
        Element's override applies this then adds other checks.
        """
        if n2 is None: return False
        if n2 is self: return True
        if self.nodeType != n2.nodeType: return False
        if self.nodeName != n2.nodeName: return False
        if self.nodeValue != n2.nodeValue: return False
        if self.localName != n2.localName: return False
        if self.nameSpaceURI != n2.nameSpaceURI: return False
        if self.prefix != n2.prefix: return False
        if self.attributes != n2.attributes: return False
        if self.childNodes is None:
            if n2.childNodes is not None: return False
        else:
            if n2.childNodes is None: return False
            if len(self.childNodes) != (n2.childNodes): return False
            for i, ch in enumerate(self.childNodes):
                if not ch.isEqualNode(n2.childNodes[i]): return False
        return True

    def isSameNode(self, n2) -> bool:
        return self is n2

    def isSupported(self, feature, version) -> bool:
        return feature in DOMImplementation._features

    def lookupNamespaceURI(self, uri) -> str:
        cur = self
        while(cur):
            if not cur.nsAttributes:
                for nsa in cur.nsAttributes:
                    if nsa.namespaceURI == uri: return nsa.nsPrefix
            cur = cur.parentNode
        return None

    def lookupPrefix(self, prefix:NmToken) -> str:
        cur = self
        while(cur):
            if not cur.nsAttributes:
                for nsa in cur.nsAttributes:
                    if nsa.nsPrefix == prefix: return nsa.namespaceURI
            cur = cur.parentNode
        return None

    def normalize(self):
        """Scan the subtree and merge any adjacent text nodes.
        Run children backward so we don't miss when we delete.
        """
        if not self.childNodes: return
        fsib = self.childNodes[-1]
        for i in reversed(range(len(self.childNodes)-1)):
            ch = self.childNodes[i]
            if ch.nodeType == NodeTypes.ELEMENT_NODE:
                self.normalize()
            elif ch.nodeType == NodeTypes.TEXT_NODE:
                if fsib.nodeType == NodeTypes.TEXT_NODE:
                    ch.textContent += fsib.textContent
                    self.removeChild(fsib)
            fsib = ch


    ########################################################################
    # Child change methods (CharacterData overrides all these)
    #
    def appendChild(self, newChild:'Node'):
        assert newChild.parentNode is None
        self.append(newChild)

    def prependChild(self, newChild:'Node'):
        assert newChild.parentNode is None
        newChild.ownerDocument = self.ownerDocument
        newChild.parentNode = self
        self.childNodes.insert(newChild, 0)
        #if self.siblingThread: newChild.spliceIn()

    def hasChildNodes(self) -> bool:
        """Rreturns False for either None or [] (Nodes are lists).
        """
        return bool(self.childNodes)

    def insertBefore(self, newChild:'Node', ch:'Node'):
        assert newChild.parentNode is None
        if ch.parentNode != self:
            raise NOT_FOUND_ERR("Node to insert before is not a child.")
        newChild.ownerDocument = self.ownerDocument
        newChild.parentNode = self
        self.childNodes.insert(ch.getChildIndex(), newChild)
        #if self.siblingThread: newChild.spliceIn()

    # TODO InsertAfter?

    def removeChild(self, oldChild:'Node') -> 'Node':
        if oldChild.parentNode != self:
            raise HIERARCHY_REQUEST_ERR("Node to remove is not a child.")
        #lg.warning("ch: [ %s ]\n", ", ".join(x.nodeName for x in self.childNodes))
        chNum = oldChild.getChildIndex()
        #lg.warning("removing a %s at #%d (of %d)",
        #    oldChild.nodeName, chNum, len(self.childNodes))
        del self.childNodes[chNum]
        oldChild.parentNode = None
        #lg.warning("    afterward: %d children.", len(self.childNodes))
        return oldChild

    def removeNode(self) -> 'Node':
        """Remove the node itself from its parentNode, unlinking as needed.
        Not sure; should the subtree be left intact, or not?
        """
        if self.parentNode is None: raise HIERARCHY_REQUEST_ERR("No parent in removeNode.")
        return self.parentNode.removeChild(self)

    def replaceChild(self, newChild:'Node', oldChild:'Node'):
        assert newChild.parentNode is None
        if oldChild.parentNode != self:
            raise NOT_FOUND_ERR("Node to remove is not a child.")
        newChild.ownerDocument = self.ownerDocument
        newChild.parentNode = self
        tgtIndex = oldChild.getChildIndex()
        self.removeChild(oldChild)
        self.childNodes.insert(newChild, tgtIndex)
        #if self.siblingThread: newChild.spliceIn()


    #######################################################################
    # Extras for Node
    #
    def unlink(self, keepAttrs:bool=False):
        """Break all internal references in the subtree, to help gc.
        Has to delete attributes, b/c they have ownerElement, ownerDocument.
        But with keepAttrs=True, it will unlink them instead.
        ELement overrides this to unlink attrs and childNodes, too.
        """
        self.ownerDocument    = None
        self.parentNode       = None
        self.userData         = None
        self.data             = None
        #self.target           = None  # Move to PI
        return

    def writexml(self, writer, indent:str="", addindent:str="", newl:str="",
        encoding:str=None, standalone:bool=None):  # Node
        assert encoding in [ None, "utf-8" ]
        if newl: writer.write(newl + indent)
        if self.nodeType == NodeTypes.ELEMENT_NODE:
            if not self.childNodes:
                writer.write(self._startTag(empty=True))
                return
            writer.write(self.startTag)
            for ch in self.childNodes:
                ch.writexml(writer, indent+addindent, addindent, newl)
            writer.write(self.endTag)
        else:
            writer.write(self.outerXML)

    def toxml(self, encoding=None):
        assert encoding in [ None, "utf-8" ]
        return self.outerXML

    def toprettyxml(self, indent:str="\t", newl:str="\n", encoding:str="utf-8"):
        assert False


    ###########################################################################
    # EXTRA NON-DOM stuff for Node
    #
    # I don't like the lengthy ritual for checking node types:
    #    if (node.nodeType = Node.PROCESSING_INSTRUCTION_NODE)
    # so just do:
    #    if node.isPI:
    #
    @property
    def isElement(self) -> bool:
        return self.nodeType == NodeTypes.ELEMENT_NODE
    @property
    def isAttribute(self) -> bool:
        return self.nodeType == NodeTypes.ATTRIBUTE_NODE
    @property
    def isText(self) -> bool:
        return self.nodeType == NodeTypes.TEXT_NODE
    @property
    def isCDATA(self) -> bool:
        return self.nodeType == NodeTypes.CDATA_SECTION_NODE
    @property
    def isEntRef(self) -> bool:
        return self.nodeType == NodeTypes.ENTITY_REFERENCE_NODE
    @property
    def isEntity(self) -> bool:
        return self.nodeType == NodeTypes.ENTITY_NODE
    @property
    def isPI(self) -> bool:
        return self.nodeType == NodeTypes.PROCESSING_INSTRUCTION_NODE
    isProcessingInstruction = isPI # b/c DOM.
    @property
    def isComment(self) -> bool:
        return self.nodeType == NodeTypes.COMMENT_NODE
    @property
    def isDocument(self) -> bool:
        return self.nodeType == NodeTypes.DOCUMENT_NODE
    @property
    def isDoctype(self) -> bool:
        return self.nodeType == NodeTypes.DOCUMENT_TYPE_NODE
    @property
    def isFragment(self) -> bool:
        return self.nodeType == NodeTypes.DOCUMENT_FRAGMENT_NODE
    @property
    def isNotation(self) -> bool:
        return self.nodeType == NodeTypes.NOTATION_NODE

    @property
    def isWSN(self) -> bool:
        return (self.nodeType == NodeTypes.TEXT_NODE
        and (not self.data or self.data.isspace()))
    @property
    def isWhitespaceInElementContent(self) -> bool:
        return (self.nodeType == NodeTypes.TEXT_NODE
        and (not self.data or self.data.isspace())
        and self.parent.hasSubElements)

    @property
    def isFirstChild(self) -> bool:
        """Don't do a full getChildIndex() if this is all you need.
        """
        if self.parentNode is None: return False
        return (self.parentNode.childNodes[0] is self)

    @property
    def isLastChild(self) -> bool:
        if self.parentNode is None: return False
        return (self.parentNode.lastChild is self)

    @property
    def hasSubElements(self) -> bool:
        if not self.childNodes: return False
        for ch in self.childNodes:
            if ch.nodeType == Node.ELEMENT_NODE: return True
        return False

    @property
    def hasTextNodes(self) -> bool:
        if not self.childNodes: return False
        for ch in self.childNodes:
            if ch.nodeType == Node.TEXT_NODE: return True
        return False

    @property
    def firstChild(self) -> 'Node':
        if not self.childNodes: return None
        return self.childNodes[0]

    @property
    def lastChild(self) -> 'Node':
        if not self.childNodes: return None
        return self.childNodes[-1]

    @property
    def leftmost(self) -> 'Node':
        """Deepest descendant along left branch of subtree  (never self).
        """
        if not self.childNodes: return None
        cur = self
        while (cur.childNodes): cur = cur.childNodes[0]
        return cur

    @property
    def rightmost(self) -> 'Node':
        """Deepest descendant along right branch of subtree (never self).
        """
        if not self.childNodes: return None
        cur = self
        while (cur.childNodes): cur = cur.childNodes[-1]
        return cur

    def getChildIndex(self, onlyElements:bool=False, ofType:bool=False,
        noWSN:bool=False) -> int:
        """Return the position in order (from 0), among the node's siblings,
        or selected siblings. This is O(n). We could save the position,
        but then insert and delete would become O(n).
        *** This is used internally, unlike most extensions ***
        """
        if self.parentNode is None: return None
        i = 0
        for ch in self.parentNode.childNodes:
            if ch is self: return i
            if onlyElements and not ch.isElement: continue
            if noWSN and ch.isWSN: continue
            if ofType and ch.nodeName != self.nodeName: continue
            i += 1
        #assert False, "Child not found."
        return None

    def getRChildIndex(self, onlyElements:bool=False, ofType:bool=False,
        noWSN:bool=False) -> int:
        """Return the position from the end (from -1...) among the node's siblings.
        or selected siblings.
        """
        if self.parentNode is None: return False
        i = -1
        for ch in reversed(self.parentNode.childNodes):
            if ch is self: return i
            if onlyElements and not ch.isElement: continue
            if noWSN and ch.isWSN: continue
            if ofType and ch.nodeName != self.nodeName: continue
            i -= 1
        #assert False, "Child not found."
        return None

    def changeOwnerDocument(self, otherDocument:'Document') -> None:
        """Move a subtree to another document. This requires deleting it, too.
        """
        if self.ownerDocument is not None: self.removeNode()
        #self.unlink(keepAttrs=True)
        for node in self.eachNode(attrs=True):
            node.ownerDocument = otherDocument

    def getFeature(self, feature, version) -> str:
        if feature==version: return __version__
        return None

    def getUserData(self, key:str) -> Any:
        return self.userData[key][0]

    def setUserData(self, key:NmToken, data:Any, handler:Callable=None) -> None:
        if self.userData is None: self.userData = {}
        self.userData[key] = (data, handler)


    # Serialization (Node)
    #
    def collectAllXml(self) -> str:
        return self.outerXML

    def outerJSON(self, indent:str="  ", depth:int=0) -> str:  # Node
        """Convert a subtree to isomorphic JSON.
        Intended to be idempotently round-trippable.
        Defined in each subclass.
        TODO: Should probably become a setter/getter pair like innerXML/outerXML.
        """
        raise NOT_SUPPORTED_ERR("outerJSON called on Node (superclass)")


    #######################################################################
    # Node paths, pointers, etc.
    #
    def getNodePath(self, useId:bool=False) -> str:
        return "/".join(self.getNodeSteps(useId=useId))

    def getNodeSteps(self, useId:bool=False) -> List:
        """Get a simple numeric path to the node, as a list.
        At option, start it at the nearest ancestral ID.
        TODO: Allow a final /@aname? Should useID take an attr name?
        """
        if self.isAttribute: cur = self.parentNode
        else: cur = self

        f = []
        while (cur):
            f.insert(0, cur.getChildIndex() + 1)
            cur = cur.parentNode
        return f

    def useNodePath(self, npath:str) -> 'Node':
        steps = npath.split(r'/')
        if steps[0] == "": del steps[0]
        return self.useNodeSteps(steps)

    def useNodeSteps(self, steps:List) -> 'Node':
        document = self.ownerDocument
        if not steps[0].isdigit():  # Leading ID:
            node = document.getElementById(steps[0])
            startAt = 1
            if not node: raise HIERARCHY_REQUEST_ERR(
                "Leading id '%s' on path not found." % (steps[0]))
        else:
            startAt = 0
            node = document.documentElement

        for i in range(startAt, len(steps)):
            if not steps[i].isdigit():
                raise HIERARCHY_REQUEST_ERR("Non-integer in path: %s" % (steps))
            cnum = int(steps[i])
            if node.nodeType not in [ Node.ELEMENT_NODE, Node.DOCUMENT_NODE ]:
                raise HIERARCHY_REQUEST_ERR(
                    "Node path step %d from non-node in: %s" % (i, steps))
            nChildren = len(node.childNodes)
            if cnum<=0 or cnum>nChildren:
                raise HIERARCHY_REQUEST_ERR(
                    "Node path step %d to #%d out of range (%d) in: %s." %
                    (i, cnum, nChildren, steps))
            node = node.childNodes[cnum-1]
        return node


    ###########################################################################
    # List operations and tree structure changes
    #
    def count(self, x) -> int:
        found = 0
        for ch in self.childNodes:
            if ch.isOfValue(x): found += 1
        return found

    def index(self, x, start:int=None, end:int=None) -> int:
        """TODO: Is this the best way to support the list op?
        """
        if start is None: start = 0
        if end is None: end = len(self.childNodes)
        for i in range(start, end):
            if self.childNodes[i].isOfValue(x): return i
        raise ValueError("index for %s in ([%s], %d, %d) not found."
            % (x, self.nodeName, start, end))

    def append(self, newChild:'Node') -> None:
        newChild.ownerDocument = self.ownerDocument
        newChild.parentNode = self
        super(Node, self).append(newChild)
        #if self.siblingThread: newChild.spliceIn()

    def clear(self) -> None:
        if self.attributes:
            self.attributes = None  # TODO: Unlink
        for ch in reversed(self):
            self.removeChild(ch)
            ch.unlink()

    # "del" can't just do a plain delete, 'cuz unlink.
    #def __delitem__(self, i:int) -> None:
    #    self.removeChild(self.childNodes[i])
    #    for other in others:
    #        self.appendChild(other)

    def insert(self, i:int, x:'Node') -> None:
        if not self.childNodes: self.childNodes = []
        if i == len(self.childNodes): self.appendChild(x)
        else: self.insertBefore(x, self.childNodes[i])

    def pop(self, i:int=-1) -> 'Node':
        try:
            toDel = self.childNodes[i]
            return self.removeChild(toDel)
        except IndexError as e:
            raise NOT_FOUND_ERR from e

    def remove(self, x:Any=None) -> 'Node':
        """Remove all members (child nodes) that match x.
        """
        if not self.childNodes: return None
        for ch in self.childNodes:
            if ch.isOfValue(x): ch.removeNode()

    def reverse(self) -> None:
        if not self.childNodes: return None
        revCh = []
        while (self.childNodes): revCh.append(self.pop())
        self.extend(revCh)

    # TODO reversed? Copy to a new NodeList?

    def sort(self, key:Callable=None, reverse:bool=False) -> None:
        if not self.childNodes: return
        sortedCh = sorted(self.childNodes, key=key, reverse=reverse)
        while (self.childNodes): sortedCh.append(self.pop())
        for ch in sortedCh: self.append(ch)

    def isOfValue(self, value:Any) -> bool:
        """Used by count, index, remove to pick node to work on.
        What *should* the test be? Going with nodeName for now.
        Though that's not good for Attribute nodes.
        """
        if value is None: return True
        if value == "*" and self.nodeType == NodeTypes.ELEMENT_NODE: return True
        if value == self.nodeName: return True
        return False

    def eachNode(self:'Node', attrs:bool=False, exclude:List=None, depth:int=1) -> 'Node':
        """Generate all descendant nodes in document order. But don't include
        attribute nodes unless asked.
        @param nodeNames: Filter out any nodes whose names are in the list
        (their entire subtrees are skipped).
        (nodeNames like #text, #cdata, #pi, may be specified, and "#wsn" to
        exclude white-space-only texst nodes).
        Example:  n.eachNode(exclude=[ "#wsn", "#pi", "#comment" ])
        Based on DomExtensions.py.
        """
        if exclude:
            if self.nodeName in exclude: return
            if ("#wsn" in exclude and self.nodeName=="#text"
                and self.data.strip()==""): return
        yield self

        if attrs and self.attributes:
            for v in self.attributes.values():
                yield v

        if self.childNodes:
            for ch in self.childNodes:
                for chEvent in ch.eachNode(
                    attrs=attrs, exclude=exclude, depth=depth+1):
                    yield chEvent
        return

    def checkNode(self, deep:bool=True):  # Node
        """Be pretty thorough about making sure the tree is right.
        TODO: Could move more to specific subclasses....
        """
        assert (self.nodeType != Node.ATTRIBUTE_NODE)  # (overridden there)
        assert isinstance(self.nodeType, NodeTypes)

        assert self.ownerDocument.isDocument
        #assert self.ownerDocument.contains(self)
        if self.parentNode is not None:
            assert self in self.parentNode.childNodes
            assert self.parentNode.childNodes[self.getChildIndex()] is self

        assert self.userData is None or isinstance(self.userData, dict)

        # Following checks via getChildIndex() ensure sibling uniqueness
        if self.previousSibling is not None:
            assert self.previousSibling.nextSibling is self
            assert self.previousSibling.getChildIndex() == self.getChildIndex() - 1
        if self.nextSibling is not None:
            assert self.nextSibling.previousSibling is self
            assert self.nextSibling.getChildIndex() == self.getChildIndex() + 1

    # End class Node


###############################################################################
# Cf https://developer.mozilla.org/en-US/docs/Web/API/Document
#

class Document(Node):
    """Creating the Document object, does *not* include creating a root element.
    """
    def __init__(self, namespaceUri:str, qualifiedName:NmToken,
        doctype:'DocumentType'=None, isFragment:bool=False):
        #print("Constructing Document Node, qname '%s', doctype '%s'." %
        #    (qualifiedName, doctype))
        if not XStr.isXmlQName(qualifiedName):
            raise ValueError("Document: qname '%s' isn't." % (qualifiedName))
        localName = XStr.getLocalPart(qualifiedName)
        if not XStr.isXmlName(localName):
            raise ValueError("local part of '%s' is '%s', not an XML name." %
                (qualifiedName, localName))
        super(Document, self).__init__(
            nodeType=Node.DOCUMENT_NODE, nodeName=localName, ownerDocument=None)

        self.namespaceUri       = namespaceUri
        self.qualifiedName      = qualifiedName
        self.doctype            = doctype
        self.documentElement    = None

        self.impl               = 'BaseDOM'
        self.version            = __version__

        self.IdIndex            = None  # Lazy build
        self.loadedFrom         = None
        self.uri                = None
        self.characterSet       = 'utf-8'
        self.mimeType           = 'text/XML'
        self.options            = self.initOptions()

    def initOptions(self) -> None:
        return {
            "attrTypes":    False,
            "IdCase":       CaseTx.NONE,
            "NameCase":     CaseTx.NONE,
            #"parser":       "lxml",
        }

    @property
    def charset(self):
        return self.characterSet
    @property
    def contentType(self) -> str:
        return self.mimeType
    @property
    def documentURI(self) -> str:
        return self.uri
    @property
    def domConfig(self):
        raise NOT_SUPPORTED_ERR("Document.domConfig")
    @property
    def inputEncoding(self) -> str:
        return self.characterSet

    def createElement(self,
        tagName:NmToken,
        attributes:Dict=None,   # Extension
        parent:Node=None,
        text:str=None           # Extension
        ) -> 'Element':
        """Allow some shorthand for creating attributes and/or text.
        To put in whole chunks of XML, or insert lists of elements and text,
        there are other extensions.
        """
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
        df = Document(
            namespaceUri=namespaceUri,
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

    def createEntityReference(self, name:NmToken, value:str=None) -> 'EntityReference':
        """Instantiate it and fetch value either from arg or schema.
        These are not commonly supported. Most things should just treat them
        like text nodes or CDATA.
        """
        return EntityReference(ownerDocument=self, name=name)

    ####### EXTENSIONS

    # shorthand creation -- use the class constructors or these
    Attr = createAttribute
    Text = createTextNode
    Comment = createComment
    CDATA = createCDATASection
    PI = createProcessingInstruction
    EntRef = createEntityReference

    def writexml(self, writer, indent:str="", addindent:str="", newl:str="",
        encoding:str=None, standalone:bool=None) -> None:  # Document
        assert encoding in [ None, "utf-8" ]
        if encoding is None: encoding = "utf-8"
        writer.write(self.getXmlDcl(encoding, standalone))
        if self.documentElement:
            self.documentElement.writexml(indent, addindent, newl,
                encoding, standalone)

    def getXmlDcl(self, encoding:str="utf-8", standalone:bool=None) -> str:
        pub = sys = ""
        if self.doctype:
            pub = self.doctype.publicId
            sys = self.doctype.systemId
        return (
            '<?xml version="1.0" encoding="%s" standalone="%s"?>\n'
            % (encoding, standalone) +
            '<!DOCTYPE %s PUBLIC "%s" "%s">\n'
            % (self.qualifiedName, pub, sys)
        )

    @property
    def outerXML(self) -> str:  # Node
        return self.startTag + self.innerXML + self.endTag

    @property
    def innerXML(self) -> str:  # Node
        # raise HIERARCHY_REQUEST_ERR() ? Everybody overrides...
        if not self.childNodes: return ""
        t = ""
        for ch in self.childNodes:
            t += ch.outerXML
        return t

    def outerJSON(self, indent:str="  ", depth:int=0) -> str:  # Document
        """Intended to be idempotently round-trippable.
        TODO: Add in Doctype or at least its reference.
        """
        return (
            """[{
    "JSONX":"1.0",
    "#name":"#document-wrapper",
    "namespaceUri":"%s",
    "rootName":"%s",
    },\n"""
        % (self.namespaceUri, self.qualifiedName)
        + self.documentElement.outerJSON(indent, depth=depth+1)
        + "]\n"
        )

    def tostring(self) -> str:  # Document
        buf = """<?xml version="1.0" encoding="utf-8"?>\n"""
        if self.doctype:
            buf += self.doctype.tostring() + "\n"
        #buf += "\n<!-- n children: %d -->\n" % (len(self.childNodes))
        if self.childNodes:
            for ch in self.childNodes: buf += ch.tostring()
        return buf

    def buildIdIndex(self, ename:NmToken=None, aname:NmToken=None) -> Dict:
        """Build an index of all values of the given named attribute
        on the given element name. If ename is empty, all elements.
        If aname is empty, do ID attributes.
        """
        theIndex = {}
        for node in self.documentElement.eachNode("*"):
            IdValue = node.getIdAttribute()
            if IdValue: theIndex[IdValue] = node
        return theIndex

    def checkNode(self, deep:bool=True):  # Document
        assert self.nodeType == "#document"  # ???
        assert self.nodeName == self.qualifiedName
        assert self.parentNode is None
        assert self.attributes is None and self.childNodes is None
        assert self.previousSibling is None and self.nextSibling is None
        if self.documentElement is not None:
            assert self.documentElement.isElement
            assert self.documentElement.nodeName == self.qualifiedName
            if deep: self.documentElement.checkNode(deep)

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
        #self.recursiveNodeValue = False
        self.attributes = None

    @property
    def tagName(self) -> NmToken: return self.nodeName
    @property
    def prefix(self) -> str:
        return XStr.getPrefixPart(self.nodeName)
    @property
    def localName(self) -> str:
        return XStr.getLocalPart(self.nodeName)
    @property
    def namespaceURI(self) -> str:
        prefix = XStr.getPrefixPart(self.nodeName)
        if prefix: return None  # TODO: Or default?
        assert False  # TODO: Implement lookup


    ###########################################################################
    # TODO: Finish the NS version of all the attr operations.
    # Just make ns option on the regular calls?
    #    prefix on name; optional separate name or URL arg; ...NS() call;
    #    "*" or "#all" for any;

    ### Attribute testers
    #
    # (hasAttributes is on Node, not Element)
    #
    def hasAttribute(self, aname:NmToken) -> bool:
        if not self.attributes: return False
        return (aname in self.attributes)

    def hasAttributeNS(self, aname:NmToken, ns) -> bool:
        return self.hasAttribute(aname)

    ### Attribute Getters
    #
    def getAttribute(self, aname:NmToken, castAs:type=str, default:Any=None) -> str:
        """Normal getAttribute, but can cast and default for caller.
        """
        if not self.attributes: return default
        if aname not in self.attributes: return default
        anode = self.attributes[aname]
        if castAs: return castAs(anode.value)
        return anode.value

    def getAttributeNS(self, ns:str, aname:NmToken, castAs:type=str, default:Any=None) -> str:
        assert NameSpaces.isNamespaceURI(ns)
        return self.getAttribute(aname, castAs, default)

    def getAttributeNode(self, aname:NmToken) -> 'Attr':
        if not self.attributes: return None
        if aname not in self.attributes: return None
        return self.attributes[aname]

    def getAttributeNodeNS(self, ns:str, aname:NmToken) -> 'Attr':
        assert NameSpaces.isNamespaceURI(ns)
        return self.getAttributeNode(aname)  # TODO NS

    def getInheritedAttribute(self:Node, aname:NmToken, default:Any=None) -> str:
        """Search upward to find the attribute.
        Return the first one found, otherwise the default (like xml:lang).
        """
        cur = self
        while (cur is not None):
            if cur.hasAttribute(aname): return cur.getAttribute(aname)
            cur = cur.parentNode
        return default

    def getInheritedAttributeNS(self:Node, ns:str, aname:NmToken, default:Any=None) -> 'Attr':
        assert NameSpaces.isNamespaceURI(ns)
        return self.getInheritedAttribute(aname, default)

    def getStackedAttribute(self:Node, aname:NmToken, sep:str="/") -> str:
        """Accumulate the attribute across self and all ancestors.
        Assumes the same name; uses "" if not present.
        """
        buf = ""
        cur = self
        while (cur is not None):
            buf =  (cur.getAttribute(aname) or "") + sep + buf
            cur = cur.parentNode
        return buf

    ### Attribute Setters
    #
    def setAttribute(self, aname:NmToken, avalue:Any) -> None:
        if self.attributes is None:
            self.attributes = NamedNodeMap(ownerDocument=self.ownerDocument, parentNode=self)
        self.attributes.setNamedItem(aname, avalue)
        #"""
        #if aname.startswith("xmlns:"):
        #    attrNode2 = Attr(aname[6:], avalue,
        #        ownerDocument=self.ownerDocument,
        #        nsPrefix=None, namespaceURI=None, parentNode=self)
        #    self.nsAttributes.setNamedItem(attrNode2)
        #"""

    def setAttributeNS(self, ns, aname:NmToken, avalue) -> None:
        if self.attributes is None:
            self.attributes = NamedNodeMap(ownerDocument=self.ownerDocument, parentNode=self)
        attrNode = Attr(aname, avalue,
            ownerDocument=self.ownerDocument,
            nsPrefix=ns, namespaceURI=None, parentNode=self)
        self.attributes.setNamedItem(attrNode)
        if ns == "xmlns":
            attrNode2 = Attr(aname[6:], avalue,
                ownerDocument=self.ownerDocument,
                nsPrefix=ns, namespaceURI=None, parentNode=self)
            self.nsAttributes.setNamedItem(attrNode2)

    def setAttributeNode(self, anode:'Attr') -> 'Attr':
        assert isinstance(anode, Attr)
        if self.attributes is None:
            self.attributes = NamedNodeMap(ownerDocument=self.ownerDocument, parentNode=self)
        old = self.attributes[anode.name] if anode.name in self.attributes else None
        anode.ownerDocument=self.ownerDocument
        anode.nsPrefix = None
        anode.parentNode = self
        self.attributes[anode.name] = anode
        old.parentNode = None
        return old

    def setAttributeNodeNS(self, ns, anode:'Attr') -> 'Attr':
        assert isinstance(anode, Attr)
        return self.setAttributeNode(anode)

    ### Attribute Removers
    #
    def removeAttribute(self, aname:NmToken) -> None:
        """TODO: unlink?
        """
        if not self.attributes: return # TODO: Or raise something?
        if self.hasAttribute(aname): self.attributes.removeNamedItem(aname)
        if len(self.attributes) == 0: self.attributes = None

    def removeAttributeNS(self, ns, aname:NmToken) -> None:
        if self.hasAttribute(aname):
            self.attributes[aname].parentNode = None
            del self.attributes[aname]

    def removeAttributeNode(self, anode:'Attr') -> 'Attr':
        assert isinstance(anode, Attr)
        if self.hasAttribute(anode.name):
            anode.parentNode = None
            del self.attributes[anode.name]
        else:
            raise NOT_FOUND_ERR(f"Attribute node for '{anode.name}' not found: "
                + self.startTag)


    ###########################################################################
    ####### Element: Descendant Selectors
    #
    def elementChildN(self, n:int) -> 'Element':
        """Return the nth *element* child of the Node
        TODO: Delete? getitem will do this fine.
        """
        elementCount = 0
        if not self.childNodes: return None
        for ch in self.childNodes:
            if ch.nodeType == Node.ELEMENT_NODE:
                elementCount += 1
                if elementCount >= n: return ch
        return None

    def getElementById(self, IdValue:str) -> 'Element':  # DOM 2
        """TODO: For HTML these should be case-insensitive.
        """
        if self.ownerDocument.IdIndex is None:
            self.ownerDocument.IDIndex = self.buildIdIndex()
        if self.ownerDocument.MLDeclaration.caseInsensitive:
            IdValue = IdValue.lower()
        if IdValue in self.ownerDocument.IdIndex:
            return self.ownerDocument.IdIndex[IdValue]
        return None

    def getElementsByClassName(self, className:str, nodeList=None) -> List:
        """Works even if it's just one of multiple class tokens.
        """
        if nodeList is None: nodeList = []
        if self.nodeType != Node.ELEMENT_NODE: return nodeList
        if className in self.getAttribute('class').split():
            nodeList.append(self)
        for ch in self.childNodes:
            ch.getElementsByClassName(className, nodeList)
        return nodeList

    def getElementsByTagName(self, tagName:NmToken, nodeList:NodeList=None) -> List:
        """Search descendants for nodes of the right name, and return them.
        """
        # TODO: Make ns an optional argument.
        if nodeList is None: nodeList = []
        if self.nodeType != Node.ELEMENT_NODE: return nodeList
        if NameSpaces.nameMatch(self, tagName, ns=None):
            nodeList.append(self)
        for ch in self.childNodes:
            ch.getElementsByTagName(tagName, nodeList)
        return nodeList

    def getElementsByTagNameNS(self, tagName:NmToken, namespaceURI:str, nodeList=None) -> List:
        if not XStr.isXmlName(tagName):
            raise NAME_ERR("Bad attribute name '%s'." % (tagName))
        if nodeList is None: nodeList = []
        if self.nodeType != Node.ELEMENT_NODE: return nodeList
        if NameSpaces.nameMatch(self, tagName, ns=namespaceURI):
            nodeList.append(self)
        for ch in self.childNodes:
            ch.getElementsByTagNameNS(tagName, nodeList, namespaceURI)
        return nodeList

    # Element: TODO: CSS/JQuery-like 'find'?
    # See https://api.jquery.com/find/
    # and http://api.jquery.com/Types/#Selector
    #

    def unlink(self, keepAttrs:bool=False):
        super(Element, self).unlink(keepAttrs=keepAttrs)
        if self.childNodes:
            for ch in self.childNodes: ch.unlink()
            self.childNodes.clear()
        if self.attributes:
            for attr in self.attributes.values(): attr.unlink()
            if not keepAttrs: self.attributes = None

    ###########################################################################
    ####### Element: (de)serializers
    #
    def insertAdjacentHTML(self, html:str):
        raise NOT_SUPPORTED_ERR("Element.insertAdjacentHTML")

    def outerJSON(self, indent:str="  ", depth:int=0) -> str:  # Element
        """TODO: Check depth==0, and if so generate the wrapper
        like for document, and call this a Fragment (?).
        """
        istr = indent * depth
        buf = '%s[ { "#name": "%s", ' % (
            istr, self.nodeName)
        for anode in self.attributes.values():
            # If the values are actual int/float/bool/none, use JSON vals.
            buf += ', ' + anode.attrToJson()
        buf += " }"
        if self.childNodes:
            for ch in self.childNodes:
                buf += ",\n" + istr + ch.outerJSON(indent, depth+1)
            buf += "\n" + istr
        buf += " ]"
        return buf

    def tostring(self) -> str:  # Element
        buf = self.startTag
        if self.childNodes:
            for ch in self.childNodes: buf += ch.tostring()
        buf += self.endTag
        return buf

    @property
    def outerXML(self) -> str:
        if self.childNodes:
            return self.startTag + self.innerXML + self.endTag
        else:
            return self._startTag(empty=True)

    @property
    def innerXML(self) -> str:
        return "".join([ ch.outerXML for ch in self.childNodes])

    @outerXML.setter
    def outerXML(self, xml:str) -> None:
        """To assign, we have to parse the XML first.
        """
        par = self.parentNode
        rsib = self.nextSibling
        par.removeChild(self)
        myOD = self.ownerDocument

        # TODO: Hook up DomBuilder for inner and outer XML setters
        # Parse the incoming XML
        impl = getDOMImplementation()
        doc = impl.createDocument(namespaceURI=myOD, qualifiedName="wrapper",
            doctype=None)
        for ch in doc.documentElement.childNodes:
            ch.changeOwnerDocument(ch, otherDocument=myOD)
            if rsib: par.insertBefore(rsib, ch)
            else: par.appendChild(ch)

    @innerXML.setter
    def innerXML(self, xml:str) -> None:
        for ch in reversed(self.childNodes):
            self.removeChild(ch)
        myOD = self.ownerDocument
        impl = getDOMImplementation()
        doc = impl.createDocument(namespaceURI=myOD, qualifiedName="wrapper",
            doctype=None)
        for ch in doc.documentElement.childNodes:
            ch.changeOwnerDocument(ch, otherDocument=myOD)
            self.appendChild(ch)

    @property
    def startTag(self) -> str:
        """Done as property to allow parameters to _ form.
        """
        return self._startTag()

    def _startTag(self, sortAttrs:bool=True, empty:bool=False) -> str:
        """Gets a correct start-tag for the element.
        Never produces empty-tags, however.
        """
        if self.nodeType != NodeTypes.ELEMENT_NODE: return ''
        t = f"<{self.nodeName}"
        if self.attributes:
            names = self.attributes.keys()
            if sortAttrs: names = sorted(names)
            for k in names:
                t += f' {k}={XStr.escapeAttribute(self.attributes[k].value)}"'
        return t + ("/" if empty else "") + ">"

    @property
    def endTag(self) -> str:
        return f"</{self.nodeName}>"

    ### Debugging aid
    #
    def checkNode(self, deep:bool=True):  # Element
        super(Element, self).checkNode()
        assert XStr.isXmlName(self.nodeName)
        #assert self.data is None
        #assert self.target is None

        if self.attributes is not None:
            assert isinstance(self.attributes, NamedNodeMap)
            for aname, anode in self.attributes.items():
                assert isinstance(anode, Attr)
                assert aname == anode.name
                anode.checkNode()

        if not self.childNodes:
            #assert self.childNodes is None  # require or not???
            pass
        else:
            for i, ch in enumerate(self.childNodes):
                assert isinstance(ch, Node)
                if i > 0: assert ch.previousSibling
                if i < len(self.childNodes)-1: assert ch.nextSibling
                if deep: ch.childNode(deep)

    # End class Element


###############################################################################
#
class CharacterData(Node):
    """A cover class for Node sub-types that can only occur as leaf nodes
    (and not including Attr either):
        Text, CDATASection, PI, Comment
        (and EntityReference and Notation, now obsolete)

    Not fond of this interface.
    * Should be called "Leaf"
    * String mutators could be left to the host language.
    * All string methods end with "Data" except "remove", which is
      also likely to be a reserved (or just confusing) word.
    * next/prev ElementSibling belong on Node, not here.
    * deletions and replacements should return the old stuff like elsewhere.
    """
    def isEqualNode(self, n2) -> bool:  # CharacterData
        if not super(CharacterData, self).isEqualNode(n2): return False
        if self.data != n2.data: return False
        return True

    def length(self) -> int:
        return len(self.data)

    # Why would these not just be on Node?
    @property
    def nextElementSibling(self):
        cur = self.nextSibling
        while (cur is not None):
            if cur.isELement: return cur
            cur = self.nextSibling
        return None
    @property
    def previousElementSibling(self):
        cur = self.previousSibling
        while (cur is not None):
            if cur.isELement: return cur
            cur = self.previousSibling
        return None

    # String mutators
    def appendData(self, s:str) -> None:
        self.data += s

    def deleteData(self, offset:int, count:int) -> None:
        if not (0 <= offset <= offset+count < len(self.data)):
            raise IndexError("Bad offset(%d)/count(%d) for deleteData (len %d)."
                % (offset, count, len(self.data)))
        self.data = self.data[0:offset] + self.data[offset+count:]

    def insertData(self, offset:int, s:str) -> None:
        if not (0 <= offset <= len(self.data)):
            raise IndexError("Bad offset(%d) for insertData (len %d)."
                % (offset, len(self.data)))
        self.data = self.data[0:offset] + s + self.data[offset:]

    def remove(self, x:Any=None) -> None:
        if x is not None:
            raise KeyError("CharacterData.remove is not like list.remove!")
        self.data = ""

    def replaceData(self, offset:int, count:int, s:str):
        if not (0 <= offset <= offset+count < len(self.data)):
            raise IndexError("Bad offset(%d)/count(%d) for replaceData (len %d)."
                % (offset, count, len(self.data)))
        self.data = self.data[0:offset] + s + self.data[offset+count:]

    def substringData(self, offset:int, count:int) -> str:
        if not (0 <= offset <= offset+count < len(self.data)):
            raise IndexError("Bad offset(%d)/count(%d) for substringData (len %d)."
                % (offset, count, len(self.data)))
        return self.data[offset:offset+count]

    # Multi-item sibling insertions
    def before(self, stuff:List) -> None:
        par = self.parentNode
        for s in stuff:
            if isinstance(s, str):
                s = self.ownerDocument.createTextNode(s)
            par.insertBefore(s, self)  # TODO Faster

    def after(self, stuff:List) -> None:
        par = self.parentNode
        nxt = self.nextSibling
        for s in stuff:
            if isinstance(s, str):
                s = self.ownerDocument.createTextNode(s)
            if nxt: par.insertBefore(s, nxt)  # TODO Faster
            else: par.appendChild(s)

    def replaceWith(self, stuff:List) -> None:
        self.before(stuff)
        self.removeNode()

    def hasChildNodes(self) -> bool:
        return False
    def contains(self, other:'Node') -> bool:
        return False
    def hasAttributes(self) -> bool:
        return False

    def count(self, x) -> int:
        return 0
    def index(self, x, start:int=None, end:int=None) -> int:
        return None
    def clear(self) -> None:
        return

    # TODO: Offer options to wrap text/comments?
    def tostring(self) -> str:  # CharacterData (PI overrides too)
        return self.data

    # Override any methods that can't apply to leaves.
    # Don't know why DOM put them on Node instead of Element.
    #
    LeafChildMsg = "CharacterData nodes cannot have children."
    @property
    def firstChild(self):
        raise HIERARCHY_REQUEST_ERR(CharacterData.LeafChildMsg)
    @property
    def lastChild(self):
        raise HIERARCHY_REQUEST_ERR(CharacterData.LeafChildMsg)  # TODO Right Exception?
    def __getitem__(self, *args):
        raise HIERARCHY_REQUEST_ERR(CharacterData.LeafChildMsg)
    def appendChild(self, newChild:Node):
        raise HIERARCHY_REQUEST_ERR(CharacterData.LeafChildMsg)
    def prependChild(self, newChild:Node):
        raise HIERARCHY_REQUEST_ERR(CharacterData.LeafChildMsg)
    def insertBefore(self, newChild:'Node', ch:'Node'):
        raise HIERARCHY_REQUEST_ERR(CharacterData.LeafChildMsg)
    def removeChild(self, oldChild:Node):
        raise HIERARCHY_REQUEST_ERR(CharacterData.LeafChildMsg)
    def replaceChild(self, newChild:Node, oldChild:Node):
        raise HIERARCHY_REQUEST_ERR(CharacterData.LeafChildMsg)
    def buildSiblingChain(self):
        raise HIERARCHY_REQUEST_ERR(CharacterData.LeafChildMsg)
    def append(self, newChild:'Node') -> None:
        raise HIERARCHY_REQUEST_ERR(CharacterData.LeafChildMsg)

    def checkNode(self, deep:bool=True):  # CharacterData (see also Attr):
        super(CharacterData, self).checkNode()
        assert self.parentNode.isElement
        #assert self.attributes is None and self.childNodes is None
        if self.isPI: assert XStr.isXMLName(self.target)


###############################################################################
#
class Text(CharacterData):
    def __init__(self, ownerDocument=None, data:str=""):
        super(Text, self).__init__(
            nodeType=Node.TEXT_NODE, nodeName="#text",
            ownerDocument=ownerDocument)
        self.data          = data

    def cloneNode(self, deep:bool=False) -> 'Node':
        newNode = Text(ownerDocument=self.ownerDocument, data=self.data)
        if self.userData: newNode.userData = self.userData
        return newNode

    @property
    def nodeValue(self):
        return self.data

    @nodeValue.setter
    def nodeValue(self, newData:str=""):
        self.data = newData

    ####### EXTENSIONS for Text

    def cleanText(self, unorm:str=None, normSpace:bool=False):
        """Apply Unicode normalization and or XML space normalization
        to the text of the node.
        """
        if unorm: buf =  unicodedata.normalize(unorm, self.data)
        else: buf = self.data
        if normSpace: buf = XStr.normalizeSpace(buf)
        self.data = buf

    @property
    def outerXML(self) -> str:  # Text
        return XStr.escapeText(self.data)

    @property
    def innerXML(self) -> str:  # Text
        return XStr.escapeText(self.data)

    def outerJSON(self, indent:str="  ", depth:int=0) -> str:  # Text
        istr = indent * depth
        return istr + '"%s"' % (escapeJsonStr(self.data))

    def tostring(self) -> str:  # Text
        return self.innerXML


###############################################################################
#
class CDATASection(CharacterData):
    def __init__(self, ownerDocument, data:str):
        super(CDATASection, self).__init__(
            nodeType=Node.CDATA_SECTION_NODE, nodeName="#cdata-section",
            ownerDocument=ownerDocument)
        #Node.__init__(nodeType=Node.CDATA_SECTION_NODE, ownerDocument=ownerDocument)
        self.data = data

    @property
    def nodeValue(self):  # CDATASection
        return self.data

    @nodeValue.setter
    def nodeValue(self, newData:str=""):  # CDATASection
        self.data = newData

    ####### EXTENSIONS

    @property
    def outerXML(self) -> str:  # CDATASection
        return '<![CDATA[%s]]>' % (XStr.escapeCDATA(self.data))

    @property
    def innerXML(self) -> str:  # CDATASection
        return XStr.escapeCDATA(self.data)

    def outerJSON(self, indent:str="  ", depth:int=0) -> str:  # CDATASection
        # TODO: Maybe construct something to say it's CDATA? Meh.
        istr = indent * depth
        return istr + '"%s"' % (escapeJsonStr(self.data))

    def tostring(self) -> str:  # CDATASection
        return self.outerXML


###############################################################################
#
class ProcessingInstruction(CharacterData):
    def __init__(self, ownerDocument=None, target=None, data:str=""):
        if target is not None and target!="" and not XStr.isXmlName(target):
            raise NAME_ERR("Bad PI target '%s'." % (target))
        super(ProcessingInstruction, self).__init__(
            nodeType=Node.PROCESSING_INSTRUCTION_NODE, nodeName=target,
            ownerDocument=ownerDocument)
        self.target = target
        self.data = data

    def cloneNode(self, deep:bool=False) -> 'ProcessingInstruction':
        newNode = ProcessingInstruction(
            ownerDocument=self.ownerDocument,
            target=self.nodeName, data=self.data)
        if self.userData: newNode.userData = self.userData
        return newNode

    def isEqualNode(self, n2) -> bool:  # PI
        if not super(CharacterData, self).isEqualNode(n2): return False
        if self.target != n2.target: return False
        return True

    @property
    def nodeValue(self):  # PI
        return self.data

    @nodeValue.setter
    def nodeValue(self, newData:str=""):  # PI
        self.data = newData

    ####### EXTENSIONS PI

    @property
    def outerXML(self) -> str:  # PI
        return f"<?{XStr.escapePI(self.target)} {XStr.escapePI(self.data)}?>"

    @property
    def innerXML(self) -> str:  # PI
        return XStr.escapePI(self.data)

    def outerJSON(self, indent:str="  ", depth:int=0) -> str:  # PI
        istr = indent * depth
        return (istr + '[ { "#name":"#pi", "#target":"%s", "#data":"%s" } ]'
             % (escapeJsonStr(self.target), escapeJsonStr(self.data)))

    def tostring(self) -> str:  # PI
        return self.outerXML

PI = ProcessingInstruction


###############################################################################
#
class Comment(CharacterData):
    def __init__(self, ownerDocument=None, data:str=""):
        super(Comment, self).__init__(
            nodeType=Node.COMMENT_NODE, nodeName="#comment",
            ownerDocument=ownerDocument)
        self.data = data

    def cloneNode(self, deep:bool=False) -> 'Comment':
        newNode = Comment(ownerDocument=self.ownerDocument, data=self.data)
        if self.userData: newNode.userData = self.userData
        return newNode

    @property
    def nodeValue(self):  # Comment
        return self.data

    @nodeValue.setter
    def nodeValue(self, newData:str=""):  # Comment
        self.data = newData

    ####### EXTENSIONS

    @property
    def outerXML(self) -> str:  # Comment
        return '<!--%s-->' % (XStr.escapeComment(self.data))

    @property
    def innerXML(self) -> str:  # Comment
        return XStr.escapeComment(self.data)

    def outerJSON(self, indent:str="  ", depth:int=0) -> str:  # Comment
        istr = indent * depth
        return (istr + '[ { "#name":"#comment, "#data":"%s" } ]'
            % (escapeJsonStr(self.data)))

    def tostring(self) -> str:  # Comment
        return self.outerXML


###############################################################################
#
class EntityReference(CharacterData):
    """These nodes are special, for apps that need to track physical structure
    as well as logical. This has not been tested. Probably it should carry
    the original name, and any declared PUBLIC/SYSTEM IDs (or the literal
    expansion text), and the NOTATION if any.
        Not widely supported. This is mostly a placeholder for now. This should
    be hooked up with DocType and the entity definition from a schema, or dropped.
    """
    def __init__(self, ownerDocument:str, name:str, data:str=""):
        super(EntityReference, self).__init__(
            nodeType=Node.ENTITY_REFERENCE_NODE, nodeName="#entity",
            ownerDocument=ownerDocument)
        self.name = name
        self.data = data

    @property
    def nodeValue(self):  # EntityReference
        return self.data

    @nodeValue.setter
    def nodeValue(self, newData:str=""):  # EntityReference
        self.data = newData

    @property
    def outerXML(self) -> str:  # EntityReference
        return '&%s;' % (self.name)

    @property
    def innerXML(self) -> str:  # EntityReference
        return self.data

    def outerJSON(self, indent:str="  ", depth:int=0) -> str:  # EntityReference
        istr = indent * depth
        return istr + '[ { "#name":"#entref, "#ref":"%s" } ]' % (escapeJsonStr(self.data))

    def tostring(self) -> str:  # EntityReference
        return self.outerXML

EntRef = EntityReference


###############################################################################
#
class Notation(CharacterData):
    """This is for entities in a given data notation/format. They are normally
    embedded by declaring an external file or object as an ENTITY, and then
    mentioning that entity name (not actually referencing the entiry), as
    the value of an attribute that was declared as being of type ENTITY.
    """
    def __init__(self, ownerDocument=None, data:str=""):
        super(Notation, self).__init__(
            nodeType=Node.NOTATION_NODE, nodeName="#notation",
            ownerDocument=ownerDocument)
        self.data = data
        # no sysid pubid?

    def cloneNode(self, deep:bool=False) -> 'Node':  # Notation
        newNode = Notation(ownerDocument=self.ownerDocument, data=self.data)
        if self.userData: newNode.userData = self.userData
        return newNode

    ####### EXTENSIONS for Notation

    @property
    def outerXML(self) -> str:  # Notation
        return ""

    @property
    def innerXML(self) -> str:  # Notation
        return self.data

    def outerJSON(self, indent:str="  ", depth:int=0) -> str:  # Notation
        istr = indent * depth
        return (istr +
            '[ { "#name":"#notation, "#notation":"%s", "#public":%s", "#system":"%s" } ]'
            % (escapeJsonStr(self.name), escapeJsonStr(self.publicID),
            escapeJsonStr(self.systemID)))

    def tostring(self) -> str:  # Notation
        return self.outerXML


class Attr(Node):
    """This is a little weird, because each Element can own a NamedNodeMap
    (which is a Dict, not a Node), which then owns the Attr objects.
    TODO: namespace support
    """
    def __init__(self, name:NmToken, value:Any, ownerDocument:Document=None,
        nsPrefix:NmToken=None, namespaceURI:str=None, parentNode:Node=None,
        attrType:type=str):
        super(Attr, self).__init__(nodeType=Node.ATTRIBUTE_NODE,
            nodeName=name, ownerDocument=ownerDocument)

        self.parentNode = parentNode
        self.ownerDocument = ownerDocument
        if (parentNode is not None
            and parentNode.nodeType != Node.ELEMENT_NODE):
            raise TypeError("parentNode for attribute '%s' is nodeType %s, not ELEMENT."
                % (name, parentNode.nodeType))

        self.name = name
        if not isinstance(attrType, type):
            raise TypeError("attrType for {name} is not a type, but %s." % (type(attrType)))
        self.XSDType = attrType
        self.value = attrType(value)

    @property
    def prefix(self) -> str:
        return XStr.getPrefixPart(self.nodeName)
    @property
    def localName(self) -> str:
        return XStr.getLocalPart(self.nodeName)
    @property
    def namespaceURI(self) -> str:
        prefix = XStr.getPrefixPart(self.nodeName)
        if prefix: return None  # TODO: Or default?
        assert False  # TODO: Implement lookup

    @property
    def isConnected(self) -> bool:  # Attr
        return None

    @property
    def isFirstChild(self) -> bool:
        raise HIERARCHY_REQUEST_ERR("Attributes are not children.")

    @property
    def isLastChild(self) -> bool:
        raise HIERARCHY_REQUEST_ERR("Attributes are not children.")

    def getChildIndex(self, onlyElements:bool=False, ofType:bool=False,
        noWSN:bool=False) -> int:  # Attr
        raise HIERARCHY_REQUEST_ERR("Attributes are not children.")

    def compareDocumentPosition(self, other:'Node') -> int:  # Attr
        """Could user the owning element's position, but that would also
        mean document order becomes a *partial* order.
        # TODO: Use parent position?
        """
        raise HIERARCHY_REQUEST_ERR("Attributes do not have document positions.")

    def isEqualAttr(self, other:'Attr') -> bool:
        # TODO: Attribute typing and casts?
        # Is namespace #any equal to anything?
        if not other.isAttribute: raise ValueError("No other attr provided.")
        if (self.name         == other.name and
            self.value        == other.value and
            #self.nsPrefix     == other.nsPrefix and  # TODO ??? nsPrefix check?
            self.namespaceURI == other.namespaceURI): return True
        return False

    def cloneNode(self, deep:bool=False) -> 'Attr':
        newNode = Attr(self.name, self.data,
            ownerDocument=self.ownerDocument,
            nsPrefix=self.prefix, namespaceURI=self.namespaceURI,
            parentNode=self.parentNode)
        if self.userData: newNode.userData = self.userData
        return newNode

    @property
    def outerXML(self) -> str:  # Attr
        """Includes the name, equal, and quoted/escaped value.
        (this is unlike innerHTML(), which doesn't exist for Attrs)
        """
        return f"{self.name}={self.innerXML}"

    @property
    def innerXML(self) -> str:  # Attr
        """Includes just the quoted/escaped value.
        (this is unlike innerHTML(), which doesn't exist for Attrs)
        """
        return f'"{XStr.escapeAttribute(self.value)}"'

    def outerJSON(self, indent:str="  ", depth:int=0) -> str:  # Attr
        # This was handled on Element.
        raise HIERARCHY_REQUEST_ERR("outerJSON() not available on Attr.")

    def attrToJson(self) -> str:
        """This uses JSON non-string types iff the value is actually
        of that type, or somebody declared the attr that way.
        not if it's a string that just looks like it.
        TODO: Move onto Attr?
        """
        aname = self.name
        avalue = self.value
        buf = f'"{aname}":'
        if isinstance(avalue, float): buf += "%f" % (avalue)
        elif isinstance(avalue, int): buf += "%d" % (avalue)
        elif avalue is True: buf += "true"
        elif avalue is False: buf += "false"
        elif avalue is None: buf += "nil"
        elif isinstance(avalue, str): buf += escapeJsonStr(avalue)
        elif isinstance(avalue, list):  # Only for tokenized attrs
            # TODO: Option to let this be a JSON List (and for Dict)?
            buf += escapeJsonStr(" ".join([ str(x) for x in avalue ]))
        else:
            raise HIERARCHY_REQUEST_ERR(f"attrToJson got unsupported type {type(avalue)}.")
        return buf

    def tostring(self):  # Attr
        """Attr is not quoted or escaped for this.
        """
        return self.nodeValue  # TODO: This ok? or whole a=v?

    def checkNode(self, deep:bool=True):  # Attr
        assert self.isAttribute
        # TODO: minidom lets you create parentless/docless Attrs.... Should we?
        assert self.parentNode.isElement
        assert self not in self.parentNode.childNodes
        assert self.ownerDocument == self.parentNode.ownerDocument
        assert self.previousSibling is None and self.nextSibling is None
        assert self.previous is None and self.next is None
        assert self.attributes is None and self.childNodes is None
        assert self.data is None and self.target is None

        assert XStr.isXMLName(self.aname)
        assert self.nodeName == self.aname

        # TODO: Attribute types, via schema or API. See PYTHONLIBS/Datatypes.py.
        # ALso XML/Unfinished/XSDown.py, DocumentType.py, XML/PARSERS/xmltuples.py
        #if self.XSDType is not None:
        #    assert isOfType(self.value, self.XSDType)

Attribute = Attr  # Attr vs. setAttribute


###############################################################################
# Stuff related to tokenized attribues (most notably HTML class)
#
def toEnum(whichEnum:type, s:Any, onFail:Any=None):
    """Get a full-fledged instance of the given Enum given any of:
        1: an instance of the Enum,
        2: a string that names one,
        3: a value that one represents, or
        4: the default value given in 'onFail'
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

class WSDefs(Enum):
    """And everyone defined whitespace as seemed right in their eyes.
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
        if which == WSDefs.PY_RE:
            return WSDefs.c0All + WSDefs.unicodeZs + WSDefs.unicodeOther + WSDefs.UnicodeCf
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


class NameTx(Enum):
    """And name/identifier characters likewise vary.
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
        XmlStrings.isXMLName() does the full XML definitions.
        """
        which = toEnum(NameTx, which)
        if which == NameTx.XML:
            return re.match(r"^\w[-_.:\s]*$", s)
        elif which == NameTx.HTML:
            return re.match(r"^[^ \t\r\n]+$", s)
        elif which == NameTx.WHATWG:
            return re.match(r"^[^ \t\r\n\f]+$", s)
        elif which == NameTx.ASCII:
            return re.match(r"^\w[-.\w]+$", s, flags=re.ASCII)
        elif which == NameTx.PYTHON:
            return s.isidentifier()
        raise KeyError("Unknown NameTx value %s." % (which))


class DOMTokenList(set):
    """This is poorly named, since it's a mutable set (not ordered, no values),
    not a list. Whatwg uses it via Element.classList.
    [But [https://dom.spec.whatwg.org/#ref-for-dom-element-classlist%E2%91%A0].

    DOM: add, remove (if), toggle, replace, contains, supports, stringifier.
    set has add, remove (and discard for if), contains.

    whatwg specifies forcing lower case; we offer the option to casefold or not,
    AND use .casefold(), which covers lots of cases that str.lower() doesn't,
    such as ligatures, medial s and final sigma, etc. etc.  But remember that
    this still doesn't suffice for things like combining vs. combined accents.
    You can choose a Unicode normalization, too.

    You can also choose among various definitions of NAME (see above).
    """
    def __init__(self, ownerElement:Node=None, ownerAttribute:str=None,
        unorm:UNormTx="", caseTx:CaseTx=CaseTx.FOLD, rules:NameTx=NameTx.XML,
        vals:Union=None):
        super(DOMTokenList, self).__init__()
        self.ownerElement = ownerElement
        self.ownerAttribute = ownerAttribute
        self.unorm = unorm
        self.caseTx = caseTx
        self.rules = rules
        if not isinstance(vals, Iterable):
            vals = re.split(r"[ \t\r\n]+", str(vals).strip)
        for val in vals: self.add(val)

    def add(self, token:str):
        self.add(self.normalize(token))

    def remove(self, token:str):  # DOMTokenList
        self.discard(self.normalize(token))

    def replace(self, token:str, newToken:str):  # DOMTokenList
        assert False

    def toggle(self, token:str):
        if token in self: self.remove(token)
        else: self.add(token)

    def normalizeKey(self, key:str):
        if not isinstance(key, str): key = str(key)
        if key == "": raise SyntaxError("normalizeKey 'key' arg is empty.")

        # Support varying token rules WhatWG, HTML4, XML NAME, and Python.
        if self.rules == NameTx.XML:
            if  not XStr.isXmlName(key):
                raise INVALID_CHARACTER_ERR("Key is not an XML NAME.")
        elif self.rules == NameTx.HTML:
            if  not re.search(r"\s", key):
                raise INVALID_CHARACTER_ERR("Key is not an HTML NAME.")
        elif self.rules == NameTx.WHATWG:
            if  not re.search(r"\s", key):
                raise INVALID_CHARACTER_ERR("Key is not a WHATWG NAME.")
        elif self.rules == NameTx.PYTHON:
            if  not key.isidentifier():
                raise INVALID_CHARACTER_ERR("Key is not a Python NAME.")

        if self.unorm: key = UNormTx.normalize(key, self.unorm)
        if self.caseTx == CaseTx.FOLD: key = key.casefold()
        elif self.caseTx == CaseTx.LOWER: key = key.lower()
        return key


###############################################################################
#
class NamedNodeMap(OrderedDict):
    """This is really just a dict or OrderedDict (latter lets us retain
    order from source if desired). So let people do Python stuff with it.

    TODO: Problem is, Individual attributes need to know who owns them, so
    they kinda have to be a Node subclass instead, not just a Dict item.

    So this stores a whole Attr instance as the value. Might be better to
    store just the nominal value there, and rig it to have the rest accessible,
    but I don't see a way I like much better....
    """
    def __init__(self, ownerDocument=None, parentNode=None,
        aname:NmToken=None, avalue:Any=None):
        """On creation, you can optionally set an attribute.
        """
        super(NamedNodeMap, self).__init__()
        self.ownerDocument = ownerDocument
        self.parentNode    = parentNode
        if aname: self.setNamedItem(aname, avalue)

    def getNamedItem(self, name:NmToken) -> Attr:
        """Per DOM, this returns the entire Attr instance, not just value.
        """
        if name not in self: return None
        return self[name]

    def getNamedItemNS(self, ns:str, name:NmToken) -> Any:  # TODO Implement getNamedItemNS
        assert NameSpaces.isNamespaceURI(ns)
        raise NOT_SUPPORTED_ERR("NamedNodeMap.getNamedItemNS")

    def getNamedValue(self, name:NmToken) -> Any:  # Not DOM
        """Returns just the actual value.
        """
        if name not in self: return None
        return self[name].value

    def getNamedValueNS(self, ns:str, name:NmToken) -> Any:  # Not DOM
        assert NameSpaces.isNamespaceURI(ns)
        raise NOT_SUPPORTED_ERR("NamedNodeMap.getNamedItemNS")

    def setNamedItem(self, attrNodeOrName:Union[str, Attr], avalue:Any=None) -> None:
        """This can take either an Attr (as in the DOM version), which contains
        its own name; or a string name and then a value (in which case the Attr
        is constructed automatically).
        TODO: types
        """
        if isinstance(attrNodeOrName, Attr):
            assert avalue is None
            self[attrNodeOrName.name] = attrNodeOrName
        else:
            assert XStr.isXmlName(attrNodeOrName)
            self[attrNodeOrName] = Attr(attrNodeOrName, avalue,
                self.ownerDocument, parentNode=self.parentNode)

    def setNamedItemNS(self, ns:str, attrNode:Node) -> None:  # TODO Implement
        assert NameSpaces.isNamespaceURI(ns)
        if not XStr.isXmlName(attrNode.name):
            raise NAME_ERR("Bad name '%s'." % (attrNode.name))
        raise NOT_SUPPORTED_ERR("NamedNodeMap.setNamedItemNS")

    def removeNamedItem(self, name:NmToken) -> Attr:
        theAttrNode = self[name]
        self[name].unlink()
        del self[name]
        return theAttrNode

    def removeNamedItemNS(self, ns:str, name:NmToken) -> None:  # TODO Implement removeNamedItemNS
        assert NameSpaces.isNamespaceURI(ns)
        raise NOT_SUPPORTED_ERR("NamedNodeMap.removeNamedItemNS")

    def item(self, index:int) -> Attr:
        if index < 0: index = len(self) + index
        if index >= len(self): raise IndexError("NamedNodeMap item #{index} out of range.")
        for i, key in enumerate(self.keys()):
            if i >= index: return self[key]
        raise IndexError("NamedNodeMap item #{index} not found.")

    def tostring(self) -> str:
        """Produce the complete attribute-list as would go in a start tag.
        """
        ks = self.keys() if self.ownerDocument.canonical else sorted(self.keys())
        s = ""
        for k in ks:
            s += ' %s="%s"' % (k, XStr.escapeAttribute(self[k].value))
        return s

    def clone(self) -> 'NamedNodeMap':
        # TODO: Namespaces
        other = NamedNodeMap(
            ownerDocument=self.ownerDocument, parentNode=self.parentNode)
        for aname, avalue in self.items():
            assert isinstance(aname, str) and isinstance(avalue, Attr)
            attrNodeCopy = avalue.cloneNode()
            other.setNamedItem(attrNodeCopy)
        return other

    copy = clone

    def getIndexOf(self, name:NmToken) -> int:  # ???
        """Return the position of the node in the source/creation order.
        """
        for k, anode in enumerate(self):
            if anode.name == name: return k
        return None

    def clear(self) -> None:
        for aname in self.keys():
            self.removeNamedItem(aname)
        assert len(self) == 0

    # TODO: Add keys/items/values, or do the Python ones suffice?


###############################################################################
#
class CSSSelectors(Node):
    """See CSSSelectors.py.
    """


###############################################################################
#
class ETAdditions(Node):
    """elementtree compatibility
    Also: fromstring _setroot canonicalize(?) findtext
    Constructors: Comment, P19n, SubElement, QName, etc.

    How textContent (getting all the text) would be in ET:
        buf = ""
        if (self.text): buf += self.text
        for ch in self.childNodes: buf += ch.textContent()
        buf += self.tail
        return buf

    vs. in DOM
        if (self.nodeName == "#text"): return self.data
        buf = ""
        for ch in self.childNodes: buf += ch.textContent()
        return buf

    Or in DOM, omit the nodename (or nodeType) test and
    have the Text.textContent just return self.data.
    """
    def find(self, name:NmToken) -> 'Node':
        """Get first direct child of that type.
        """
        if not self.childNodes: return None
        isQName = ":" in name
        for ch in self.childNodes:
            if not ch.isElement: continue
            if (isQName):
                if ch.nodeName == name: return ch
            else:
                if ch.localName == name: return ch
        return None

    def findAll(self, name:NmToken) -> List:
        """Get all direct children of that type.
        """
        if not self.childNodes: return None
        isQName = ":" in name
        nodes = []
        for ch in self.childNodes:
            if not ch.isElement: continue
            if (isQName):
                if ch.nodeName == name: nodes.append(ch)
            else:
                if ch.localName == name: nodes.append(ch)
        return nodes

    set = Element.setAttribute
    get = Element.getAttribute

    @property
    def getroot(self):
        return self.ownerDocument.documentElement

    @property
    def tag(self):
        return self.nodeName  # localName?

    def matches(self):
        raise NOT_SUPPORTED_ERR("Element.matches")

    @property
    def tail(self):
        """No. Just no.
        """
        if self.nextSibling and self.nextSibling.isText:
            return self.nextSibling.data
        return None

    @property
    def text(self):
        if self.childNodes and self.childNodes[0].isText:
            return self.childNodes[0].data
        return None


###############################################################################
#
class whatwgAdditions(Node):
    """These are largely HTML hard-wired.
    Also:
    createDocumentFragment
    dataset -- just mirrors attrs starting with "data-"
    add[remove]eventListener, MutationObserver,
    closest(), matches(), and children.
    createElement() and createElementNS()
    template stuff
    """
    def querySelector(self):
        """Find first match to CSS selector
        """
        raise NOT_SUPPORTED_ERR("Element.querySelector")

    def querySelectorAll(self):
        """Find all matches to CSS selector
        """
        raise NOT_SUPPORTED_ERR("Element.querySelectorAll")

    def matches(self:Node, selector:str) -> bool:
        """Test whether the node is matched bt the selector.
        """
        raise  NOT_SUPPORTED_ERR("Element.matches")

    def children(self:Node) -> List:
        """Returns only elements.
        """
        theChosen = []
        for ch in self:
            if ch.isElement: theChosen.append(ch)
        return theChosen or None

    def closest(self:Node, selector:str) -> Node:
        cur = self
        while (cur is not None):
            if cur.matches(selector): return cur
            cur = cur.parentNode
        return None

    # The classlist then has add/remove/toggle
    @property
    def classList(self) -> List[NmToken]:  # (from whatwg; why just class?)
        return re.split(r'\s+', self.getAttribute('class'))

    @property
    def className(self) -> str:
        return self.getAttribute('class')


###############################################################################
#
class Synonyms:  # TODO: Implement?
    """
        length       = len,
        getLength    = len,
        copy         = cloneNode
        append       = appendChild
        insert       = insertBefore

        (operators for compareDocumentPosition)
        % for ["*"] ??


        prev         = previous
        prevSibling = previousSibling
        hasDescendant= contains,

        u = parentNode
        d = firstChild
        l = previousSibling
        r = nextSibling
        t = textContent

        Attr         = createAttribute
        createAttr   = createAttribute
        Text         = createTextNode
        Comment      = createComment
        CDATA        = createCDATASection
        PI           = createProcessingInstruction
        EntRef       = createEntityReference

        PI_NODE      = PROCESSING_INSTRUCTION_NODE
        CDATA_NODE   = CDATA_SECTION_NODE
        ENTREF_NODE  = ENTITY_REFERENCE_NODE
    """


###############################################################################
#
class OtherAdditions(Node):
    """Add hypertext and ID extensions.
        * Way to get identify ID attrs via schema
        * Way to just declare them via API
        * Add notions (are these all just scheme prefixes? a la XPointer?
            COID      Multiples must be on same element type. same att or sId/eId
            STACKID   "/".join(x.attr[name] for x in reversed(ancestors)
            SCOPEDID  Only needs to0 be unique within innermost anc of type T
            NSID      Only unique in NS (delared somewhere)
            COMPOUND  Value is cal by declared XPath.
        * Add XLink/XPointer support
        * Support HTML name vs. ID option
        *
    """
    @property
    def Id(self) -> str:
        idName = self.hasIdAttribute
        if idName: return self.getAttribute(idName)
        return None

    @property
    def getIdAttribute(self) -> str:
        """This was apparently an old IE addition, now obsolete. But
        if you have a schema handy it can be pretty useful....
        called can set up a list by elname@atname with the doctype, by
        adding one or more entries like:
            *@id
            p@name
            myThing@anchor
        Returns a QName with prefix:pointerstring
            (are these the same as node selectors?)
        """
        if not self.nsAttributes: return None
        if self.hasAttribute("xml:id"): return True
        if (self.ownerDocument.doctype is not None
            and self.ownerDocument.doctype.IDAttrs):
            for k, _anode in self.attributes.items():
                if ('*@'+k in self.ownerDocument.doctype.IDAttrs or
                    self.nodeName+'@'+k in self.ownerDocument.theDOM.doctype.IDAttrs):
                    return k
        return None

    @property
    def baseURI(self) -> str:
        """From the HTML DOM. If added, I want a set of named Bases, that are
        integrated into URI processing.
        """
        assert False


###############################################################################
#
class NameSpaces(Dict):
    """Manage prefix <-> URI mappings.
    And the reverse -- though that can be 1:n, so uri2prefix[] contains lists!
    TODO: Check match semantic and integrate.
    """
    def __init__(self):
        self.uri2prefix = {}

    def __setitem__(self, prefix:str, uri:str) -> None:
        assert XStr.isXmlName(prefix)
        assert self.isNamespaceURI(uri)
        if prefix in self:
            if self[prefix] == uri: return
            lg.warning("Prefix '%s' rebound from '%s' to '%s'.",
                prefix, self[prefix], uri)
        super().__setitem__(prefix, uri)

        if uri not in self.uri2prefix:
            self.uri2prefix[uri] = []
        elif self.uri2prefix.contains(uri):
            return
        self.uri2prefix[uri].append(prefix)

    def __delitem__(self, prefix:str):
        assert XStr.isXmlName(prefix)
        uri = self[prefix]
        del self.uri2prefix[uri]
        super().__delitem__(prefix)

    @staticmethod
    def isNamespaceURI(ns:str) -> bool:
        """Good enough for present purposes?
        Is setting to "" ok?
        """
        return re.match(r"\w+://", ns)

    @staticmethod
    def nameMatch(node:Node, target:str, ns:str=None) -> bool:
        """Determine whether the node's name matches the target.
        """
        if ":" in target:
            Tprefix, _, Tname = target.partition(":")
            Turi = node.ownerDocument.namespaceIndex[Tprefix]
        else:
            Tprefix = ""
            Tname = target
            Turi = None

        if ns:
            assert NameSpaces.isNamespaceURI(ns)
            assert Turi is None or Turi == ns

        if Turi and node.nsURI != Turi: return False
        if Tprefix == "#none":
            if node.prefix: return False
        elif Tprefix:
            if (not re.match(r"\*|#all|#any", Tprefix, flags=re.I)
                and node.prefix != Turi): return False
        if Tname and node.nodeName != Turi: return False
        return True
