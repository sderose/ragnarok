#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# A fairly simple native Python DOM implementation. Basically DOM 2
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
import functools
import logging

from domexceptions import *
from xmlstrings import XmlStrings as XStr
from domenums import NodeType, UNormTx, CaseTx
#from domgetitem import __domgetitem__  # NodeSelKind
from dombuilder import DomBuilder
#from domadditions import whatwgAdditions, EtAdditions, OtherAdditions
#from cssselectors import CssSelectors

lg = logging.getLogger("BaseDOM")

NmToken = str
ANY_NS = "##any"  # See https://qt4cg.org/specifications/xquery-40/xpath-40.html

__metadata__ = {
    "title"        : "BaseDOM",
    "description"  : "A more Pythonic, pretty fast DOM-ish implementation.",
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

def hidden(func):
    """Define "@hidden" decorator to signal that a method is hiding
    a superclass method. This could also be set up to make it uncallable.
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        raise AttributeError(f"'{func.__name__}' is a hidden method")
    wrapper.__is_hidden__ = True
    return wrapper


_xmlNS_URI = "http://www.w3.org/XML/1998/namespace"

def escapeJsonStr(s:str) -> str:
    return re.sub(r'([\\"])', "\\\\1", s)


###############################################################################
#
def getDOMImplementation(name:str=None):
    return DOMImplementation()

class DOMImplementation:
    name = "BaseDOM"
    version = "0.1"

    def __init__(self, name:str=None):
        if name: DOMImplementation.name = name

    def createDocument(self, namespaceURI:str, qualifiedName:NmToken,
        doctype:'DocumentType'
        ) -> 'Document':
        doc = Document(namespaceURI, qualifiedName, doctype)

        # TODO Move rest into Document constructer so can just instantiate?
        #
        if namespaceURI is None:
            namespaceURI = ""
            if not qualifiedName:  # fetch from doctype?
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
        """TODO Prevent circular import, since DocumentType needs Node.
        """
        raise NotImplementedError
        #import DocumentType
        #loc = XStr.getLocalPart(qualifiedName)
        #return DocumentType.DocumentType(qualifiedName, publicId, systemId)

    # DOM Level 3

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
        dbuilder = DomBuilder()
        theDom = dbuilder.parse(filename_or_file)
        return theDom

    def parse_string(self, s:str, parser=None):
        dbuilder = DomBuilder(impl=self)
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
        assert False, "No multiplying elements."

    def __rmul__(self, x):
        assert False, "No rmultiplying elements."

    def getInterface(self):
        assert False, "getInterface: obsolete."

    def isSupported(self):
        assert False, "isSupported: obsolete."


###############################################################################
#
class PlainNode(NodeList):
    """Separate the basic stuff out from extensions and Pythonizations.
    Except, we're not hiding Python List methods.
    The main (basically abstract) class for DOM, from which many are derived.
        https://www.w3.org/TR/2000/REC-DOM-Level-2-Core-20001113
    """
    DOCUMENT_NODE                = NodeType.DOCUMENT_NODE
    ELEMENT_NODE                 = NodeType.ELEMENT_NODE
    ATTRIBUTE_NODE               = NodeType.ATTRIBUTE_NODE
    TEXT_NODE                    = NodeType.TEXT_NODE
    CDATA_SECTION_NODE           = NodeType.CDATA_SECTION_NODE
    PROCESSING_INSTRUCTION_NODE  = NodeType.PROCESSING_INSTRUCTION_NODE
    COMMENT_NODE                 = NodeType.COMMENT_NODE

    def __init__(self, ownerDocument=None, nodeName:NmToken=None):
        """This shouldn't really be instantiated, but minidom lets you.
        But minidom doesn't give the same params as all others, even though
        it creates the basic vars as None. I add the params for consistency.
        """
        super().__init__()
        self.ownerDocument = ownerDocument
        self.parentNode = None  # minidom Attr lacks....
        self.nodeType = NodeType.UNSPECIFIED_NODE
        self.nodeName = nodeName
        self.inScopeNamespaces = {}
        self.userData = None

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

    # Next three are defined here, but only work for Element and Attr.
    # (we could support them; constructor takes nodeName for consistency....
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
    def childNodes(self) -> List:
        return self

    @property
    def isConnected(self) -> bool:
        """Overridden for Attr nodes. (HTML DOM ONLY)
        """
        if self.ownerDocument is None: return False
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
    def parentElement(self) -> 'Node':
        if self.parentNode is None or not self.parentNode.isElement:
            return None
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

    def isSameNode(self, n2) -> bool:
        return self is n2

    def isEqualNode(self, n2) -> bool:  # Node
        """Check the common properties that matter.
        Subclasses may override to check more, but should call this, too!
        See https://dom.spec.whatwg.org/#concept-node-equals.
        This does *not* check ownerDocument, so should work across docs.
        Element's override applies this then adds other checks.

        You can't just compare nodeName, since the prefix could differ
        but be mapped to the same uri!!!
        """
        if n2 is self: return True
        if n2 is None: return False  # self of course can't be None
        if self.nodeType != n2.nodeType: return False
        if not self.nodeNameMatches(n2): return False
        if self.nodeValue != n2.nodeValue: return False
        # Element does additional checks like attributes and childNodes
        return True

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

    def cloneNode(self, deep:bool=False) -> 'Node':
        """NOTE: Default value for 'deep' has changed in spec and browsers!
        """
        raise NOT_SUPPORTED_ERR("Shouldn't really be cloning abstract Node.")

    #### Mutators (PlainNode)

    def _expandChildArg(self, ch:Union['Node', int]) -> (int, 'Node'):
        """Let callers specify a child either by object itslef or position.
        See which they passed, calculate the other, and return both.
        This is b/c various methods are faster one way or the other, but the
        user should be able to just use what they have.
        """
        if isinstance(ch, Node):
            return ch.getChildIndex(), ch
        if isinstance(ch, int):
            n = ch
            if n < 0: n = len(self) + n
            if n >= 0 and n < len(self):
                return n, ch
            raise IndexError(f"child number {ch}, but only {len(self)} there.")
        raise TypeError("Bad child specifier type '%s'." % (type(ch).__name__))

    def normalize(self):
        """Scan the subtree and merge any adjacent text nodes.
        Run children backward so we don't miss when we delete.
        """
        if not self.childNodes: return
        fsib = self.childNodes[-1]
        for i in reversed(range(len(self.childNodes)-1)):
            ch = self.childNodes[i]
            if ch.nodeType == NodeType.ELEMENT_NODE:
                ch.normalize()
            elif ch.nodeType == NodeType.TEXT_NODE:
                if fsib.nodeType == NodeType.TEXT_NODE:
                    ch.textContent += fsib.textContent
                    self.removeChild(fsib)
            fsib = ch

    def appendChild(self, newChild:'Node'):
        if newChild.parentNode is not None:
            raise HIERARCHY_REQUEST_ERR(
                f"newChild already has parent (type {newChild.parentNode.nodeType}).")
        self.append(newChild)  # Defined below, does the connecting.

    def insertBefore(self, newChild:'Node', oldChild:Union['Node', int]):
        """TODO Allow int for 'ch' arg? append if old is None or >=len?
        """
        assert newChild.parentNode is None
        oNum, oChild = self._expandChildArg(oldChild)
        if oChild.parentNode != self:
            raise NOT_FOUND_ERR("Node to insert before is not a child.")
        self.childNodes.insert(oNum, newChild)

    def removeChild(self, oldChild:Union['Node', int]) -> 'Node':
        """Disconnect oldChild from this node, removing it from the tree,
        but not fromm the document. To destroy it, it should also unlinked.
        """
        assert oldChild.parentNode is not None
        oNum, oChild = self._expandChildArg(oldChild)
        ocp = oChild.parentNode
        if ocp is not self:
            raise HIERARCHY_REQUEST_ERR("Node to remove has parent %s, not %s." %
                (ocp.nodeName if ocp is not None else "None",
                 self.nodeName if self is not None else "None"))
        #lg.warning("ch: [ %s ]\n", ", ".join(x.nodeName for x in self.childNodes))
        del self.childNodes[oNum]
        oChild.parentNode = None
        #lg.warning("    afterward: %d children.", len(self.childNodes))
        return oChild

    def writexml(self, writer, indent:str="", addindent:str="", newl:str="",
        encoding:str=None, standalone:bool=None):  # Node
        assert encoding in [ None, "utf-8" ]
        if newl: writer.write(newl + indent)
        if self.nodeType == NodeType.ELEMENT_NODE:
            if not self.childNodes:
                writer.write(self._startTag(empty=True))
                return
            writer.write(self.startTag)
            for ch in self.childNodes:
                ch.writexml(writer, indent+addindent, addindent, newl)
            writer.write(self.endTag)
        else:
            writer.write(self.outerXML)


    ### Python list operations (PlainNode)

    def count(self, x:Any) -> int:
        found = 0
        for ch in self.childNodes:
            assert isinstance(ch, Node)
            if ch._isOfValue(x): found += 1
        return found

    def index(self, x, start:int=None, end:int=None) -> int:
        """TODO: Is this the best way to support the list op?
        """
        if start is None: start = 0
        if end is None or end > len(self.childNodes): end = len(self.childNodes)
        for i in range(start, end):
            if self.childNodes[i]._isOfValue(x): return i
        raise ValueError("'%s' not found in %s '%s' [%d:%d]."
            % (x, self.nodeType, self.nodeName, start, end))

    def append(self, newChild:'Node') -> None:
        # TODO: maybe just do self.insert(len(self), newChild)?
        newChild.ownerDocument = self.ownerDocument
        newChild.parentNode = self
        newChild.inScopeNamespaces = self.inScopeNamespaces
        super().append(newChild)

    def insert(self, i:int, newChild:'Node') -> None:  # PlainNode
        if not isinstance(newChild, Node) or newChild.isAttribute:
            raise HIERARCHY_REQUEST_ERR("Only insert Nodes, not {type{newChild}}")
        newChild.ownerDocument = self.ownerDocument
        newChild.inScopeNamespaces = self.inScopeNamespaces
        if i < 0: i = len(self) + i
        if i >= len(self): self.appendChild(newChild)  # TODO: needed at all?
        else: super().insert(i, newChild)
        newChild.parentNode = self

    def clear(self) -> None:
        assert False, "Can't clear() abstract Node."

    # "del" can't just do a plain delete, 'cuz unlink.
    #def __delitem__(self, i:int) -> None:
    #    self.removeChild(self.childNodes[i])
    #    for other in others:
    #        self.appendChild(other)

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
            if ch._isOfValue(x): ch.removeNode()

    def reverse(self) -> None:
        if not self.childNodes: return None
        revCh = []
        while (self.childNodes): revCh.append(self.pop())
        self.extend(revCh)

    def reversed(self) -> NodeList:
        revCh = NodeList()
        if self.childNodes:
            for cnum in reversed(range(len(self.childNodes))):
                revCh.append(self.childNodes[cnum])
        return revCh

    def sort(self, key:Callable=None, reverse:bool=False) -> None:
        if not self.childNodes: return
        sortedCh = sorted(self.childNodes, key=key, reverse=reverse)
        while (self.childNodes): sortedCh.append(self.pop())
        for ch in sortedCh: self.append(ch)

    def _isOfValue(self, value:Any) -> bool:
        """Used by count, index, remove to pick node(s) to work on.
        What *should* the test be? Going with nodeName for now.
        """
        if value is None: return True
        if callable(value): return value(self)
        if value == "*" and self.nodeType == NodeType.ELEMENT_NODE: return True
        if value == self.nodeName: return True
        return False

    ### Meta (PlainNode)

    def unlink(self, keepAttrs:bool=False):
        """Break all internal references in the subtree, to help gc.
        Has to delete attributes, b/c they have ownerElement, ownerDocument.
        But with keepAttrs=True, it will unlink them instead.
        ELement overrides this to unlink attrs and childNodes, too.
        """
        self.ownerDocument    = None
        self.parentNode       = None
        return


###############################################################################
#
class Node(PlainNode):
    # whatwgAdditions, EtAdditions, OtherAdditions,
    #CssSelectors,
    #__slots__ = ("nodeType", "nodeName", "ownerDocument", "parentNode")

    UNSPECIFIED_NODE            = NodeType.UNSPECIFIED_NODE
    ENTITY_REFERENCE_NODE       = NodeType.ENTITY_REFERENCE_NODE
    ENTITY_NODE                 = NodeType.ENTITY_NODE
    DOCUMENT_TYPE_NODE          = NodeType.DOCUMENT_TYPE_NODE
    DOCUMENT_FRAGMENT_NODE      = NodeType.DOCUMENT_FRAGMENT_NODE
    NOTATION_NODE               = NodeType.NOTATION_NODE
    PI_NODE                     = NodeType.PROCESSING_INSTRUCTION_NODE

    # The *constant* nodeName strings. The rest use a real name
    # (Element, Attr, PI (target), DocumentType).
    __reservedNodeNames__ = {
        PlainNode.CDATA_SECTION_NODE : '#cdata-section',
        PlainNode.COMMENT_NODE       : '#comment',
        PlainNode.DOCUMENT_NODE      : '#document',
        PlainNode.TEXT_NODE          : '#text',
        DOCUMENT_FRAGMENT_NODE       : '#document-fragment',
    }

    def bool(self):
        """A node can be empty but still meaningful (think hr or br in HTML).
        That is not like 0, [], or {}, we want it to test True.
        """
        return bool(self.value)

    def __contains__(self, item:'Node') -> bool:
        """Careful, the Python built-in "contins"/"in" is wrong for node
        containment, because all empty lists are considered equal.
        Thus an element with any empty node "contains" *all* empty nodes.
        """
        return item.parentNode == self

    # There is no ordering for nodes except document ordering, so I'm using
    # it for all the comparison operators.
    # TODO: Attributes and Text may want to override....
    # TODO: Is this ok for eq and ne? Or should they be like isEqualNode?
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

    # Overload [] to be more useful.
    def NOTYET__getitem__(self, key: Union[int, slice, str]):
        # Integrate __getitem__
        if isinstance(key, int):
            return super(Node, self).__getitem__(key)
        if isinstance(key, str):
            theChosen = []
            for ch in self:
                if ch.nodeName == key: theChosen.append(ch)  # TODO NS?
            return theChosen or None
        elif isinstance(key, slice):
            # Component are instances of "member_descriptor"
            #return __domgetitem__(self, slice.start, slice.stop, slice.step)
            assert False, "Not hooked up yet"
        else:
            raise IndexError("Unexpected [] arg type: %s" % (type(key)))

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

    def nodeNameMatches(self, other) -> bool:
        """Factor this out b/c with namespaces there can be a match even
        if the prefixes don't match, because they could map to the same URI!.
        TODO: Is this where to add case-ignoring?
        """
        if self.localName != other.localName: return False
        if self.namespaceURI == ANY_NS or other.namespaceURI == ANY_NS: return True
        if self.namespaceURI != other.namespaceURI: return False
        return True

    @property
    def textContent(self, delim:str="") -> str:
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
        if self.nodeType == NodeType.TEXT_NODE:
            self.data = newData
        else:
            # TODO Maybe replace whole subtree w/ new text node?
            raise NOT_SUPPORTED_ERR(
            "Cannot set textContent on nodeType %s." % (self.nodeType.__name__))

    def compareDocumentPosition(self, other:'Node') -> int:
        """Returns -1, 0, or 1 to reflect relative document order.
        Two different nodes cannot be in the same places, nor the same node
        in two different places (like, say, electrons). Therefore, for
        equality it's enough to test identity instead of position.

        XPointers are good for this, except that getChildIndex() is O(fanout).

        Does not apply to Attribute nodes (overridden).
        """
        if self.ownerDocument is None or self.ownerDocument != other.ownerDocument:
            raise HIERARCHY_REQUEST_ERR("No common document for compareDocumentPosition")
        if self.parentnode is None or other.parentnode is None:
            raise HIERARCHY_REQUEST_ERR("Nodes are not both connected.")
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

    def hasDescendant(self, other:'Node'):
        """Provided b/c 'contains' vs. '__contains__' may be confusing.
        """
        return self.contains(other)

    def getRootNode(self) -> 'Node':
        """This seems mainly useful for HTML shadow stuff.
        """
        return self.ownerDocument

    def hasAttributes(self) -> bool:
        return (self.attributes is not None and len(self.attributes) > 0)

    def isDefaultNamespace(self, uri:str) -> bool:  # TODO Implement isDefaultNamespace
        return True
        #raise NOT_SUPPORTED_ERR("isDefaultNamespace")

    def lookupNamespaceURI(self, uri:str) -> str:
        """This assumes we accumulate inScopeNamespaces down the tree.
        Each node gets at least a pointer to its parent's one (copy on change).
        It gets set/cleared at the same times as parentNode, b/c inheritance.
        Non-elements can't declare any ns, so don't get a dict.
        TODO: Is this right for Attrs or must we override?
        """
        bearer = self if self.isElement else self.parent
        assert bearer.inScopeNamespaces is not None
        for k, v in bearer.inScopeNamespaces.items():
            if v == uri: return k
        return None

    def lookupPrefix(self, prefix:NmToken) -> str:
        """Pass prefix "" for default namespace.
        """
        assert self.inScopeNamespaces is not None
        if not (prefix == "" or XStr.isXmlName(prefix)):
            raise NAME_ERR("lookupPrefix: Bad prefix '{prefix}'.")
        if prefix not in self.inScopeNamespaces: return None
        return  self.inScopeNamespaces[prefix]

    #### Mutators (Node) CharacterData hides all these)

    def prependChild(self, newChild:'Node'):
        assert newChild.parentNode is None
        self.childNodes.insert(0, newChild)

    def hasChildNodes(self) -> bool:
        """Rreturns False for either None or [] (Nodes are lists).
        """
        return bool(self.childNodes)

    # TODO insertAfter()?

    def removeNode(self) -> 'Node':
        """Remove the node itself from its parentNode, unlinking as needed.
        Not sure; should the subtree be left intact, or not?
        """
        if self.parentNode is None:
            raise HIERARCHY_REQUEST_ERR("No parent in removeNode.")
        return self.parentNode.removeChild(self)

    def replaceChild(self, newChild:'Node', oldChild:Union['Node', int]):
        assert newChild.parentNode is None
        oNum, oChild = self._expandChildArg(oldChild)
        self.removeChild(oChild)
        self.childNodes.insert(oNum, newChild)


    #######################################################################
    # Extras for Node
    #
    def toxml(self, encoding:str="utf-8"):
        if encoding != "utf-8":
            raise ValueError("Encoding must be utf-9 for now.")
        return self.outerXML

    def toprettyxml(self, indent:str="\t", newl:str="\n", encoding:str="utf-8"):
        self.toxml(encoding=encoding)

    def getUserData(self, key:str) -> Any:
        if not self.userData: return None
        return self.userData[key][0]

    def setUserData(self, key:NmToken, data:Any, handler:Callable=None) -> None:
        if self.userData is None: self.userData = {}
        self.userData[key] = (data, handler)


    # Shorter checking for node types:
    #    if node.nodeType = Node.PROCESSING_INSTRUCTION_NODE
    # so just do:
    #    if node.isPI:
    #
    @property
    def isElement(self) -> bool:
        return self.nodeType == NodeType.ELEMENT_NODE
    @property
    def isAttribute(self) -> bool:
        return self.nodeType == NodeType.ATTRIBUTE_NODE
    @property
    def isText(self) -> bool:
        return self.nodeType == NodeType.TEXT_NODE
    @property
    def isCDATA(self) -> bool:
        return self.nodeType == NodeType.CDATA_SECTION_NODE
    @property
    def isEntRef(self) -> bool:
        return self.nodeType == NodeType.ENTITY_REFERENCE_NODE
    @property
    def isPI(self) -> bool:
        return self.nodeType == NodeType.PROCESSING_INSTRUCTION_NODE
    isProcessingInstruction = isPI # b/c DOM.
    @property
    def isComment(self) -> bool:
        return self.nodeType == NodeType.COMMENT_NODE
    @property
    def isDocument(self) -> bool:
        return self.nodeType == NodeType.DOCUMENT_NODE
    @property
    def isDocumentType(self) -> bool:
        return self.nodeType == NodeType.DOCUMENT_TYPE_NODE
    @property
    def isFragment(self) -> bool:
        return self.nodeType == NodeType.DOCUMENT_FRAGMENT_NODE
    @property
    def isNotation(self) -> bool:
        return self.nodeType == NodeType.NOTATION_NODE

    @property
    def isWSN(self) -> bool:
        return (self.nodeType == NodeType.TEXT_NODE
        and (not self.data or self.data.isspace()))
    @property
    def isWhitespaceInElementContent(self) -> bool:
        return (self.nodeType == NodeType.TEXT_NODE
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
        steps = self.getNodeSteps(useId=useId)
        if not steps: return None
        return "/".join([ int(s) for s in steps ])

    def getNodeSteps(self, useId:bool=False) -> List:
        """Get a simple numeric path to the node, as a list.
        At option, start it at the nearest ancestral ID.
        TODO: Allow a final /@aname? Should useID take an attr name?
        """
        if self.isAttribute: cur = self.parentNode
        else: cur = self
        if cur.parentNode is None: return None

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
    # Multi-item sibling insertions (whence was this?
    #
    def before(self, stuff:List) -> None:
        par = self.parentNode
        beforeNum = self.getChildIndex()
        for i, s in enumerate(stuff):
            if isinstance(s, str):
                s = self.ownerDocument.createTextNode(s)
            par.insertBefore(s, beforeNum+i)  # Faster using int option

    def after(self, stuff:List) -> None:
        par = self.parentNode
        nxt = self.nextSibling
        beforeNum = nxt.getChildIndex() if nxt else -1
        for i, s in enumerate(stuff):
            if isinstance(s, str):
                s = self.ownerDocument.createTextNode(s)
            if nxt: par.insertBefore(s, beforeNum+i)
            else: par.appendChild(s)

    def replaceWith(self, stuff:List) -> None:
        self.before(stuff)
        self.removeNode()

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
            for v in self.attributes.values(): yield v

        if self.childNodes:
            for ch in self.childNodes:
                for chEvent in ch.eachNode(
                    attrs=attrs, exclude=exclude, depth=depth+1):
                    yield chEvent
        return

    ### Meta

    def unlink(self, keepAttrs:bool=False):
        """Break all internal references in the subtree, to help gc.
        Has to delete attributes, b/c they have ownerElement, ownerDocument.
        But with keepAttrs=True, it will unlink them instead.
        ELement overrides this to unlink attrs and childNodes, too.
        """
        super().unlink()
        self.userData         = None
        return

    def checkNode(self, deep:bool=True):  # Node
        """Be pretty thorough about making sure the tree is right.
        All subclasses do their own version, but all except Attr
        super() this first (Attr doesn't b/c of self.parentNode.childNodes)
        """
        assert isinstance(self.nodeType, NodeType)
        assert (self.nodeType != Node.ATTRIBUTE_NODE)
        if self.ownerDocument is not None:
            assert self.ownerDocument.isDocument
        if self.parentNode is not None:
            assert self.parentNode.isElement or self.parentNode.isDocument
            assert self in self.parentNode.childNodes
            assert self.ownerDocument == self.parentNode.ownerDocument
            assert self.parentNode.childNodes[self.getChildIndex()] is self
        if (len(self.childNodes) > 0):
            assert isinstance(self, (Element, NodeList))
        if self.userData is not None:
            assert isinstance(self.userData, dict)

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
    def __init__(self, namespaceUri:str, qualifiedName:NmToken,
        doctype:'DocumentType'=None, isFragment:bool=False):
        super().__init__(ownerDocument=None, nodeName="#document")

        self.nodeType           = Node.DOCUMENT_NODE
        self.namespaceUri       = namespaceUri
        self.doctype            = doctype
        if not XStr.isXmlQName(qualifiedName):
            raise ValueError("Document: qname '%s' isn't." % (qualifiedName))
        self.documentElement    = self.createElement(tagName=qualifiedName)

        self.impl               = 'BaseDOM'
        self.version            = __version__
        self.characterSet       = 'utf-8'
        self.options            = self.initOptions()

        self.nsIndex            = { "": namespaceUri }
        self.IdIndex            = None  # Lazy build
        self.loadedFrom         = None
        self.uri                = None
        self.mimeType           = 'text/XML'

    def clear(self):
        raise NotImplementedError("No clear() on Document nodes.")

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
    def inputEncoding(self) -> str:
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

    def createElement(self,
        tagName:NmToken,
        attributes:Dict=None,   # Extension
        parent:Node=None,
        text:str=None           # Extension
        ) -> 'Element':
        """Allow some shorthand for creating attributes and/or text, and.or
        to append the new element to a specified parent node.
        To put in whole chunks of XML, or insert lists of elements and text,
        there are other extensions.
        """
        elem = Element(ownerDocument=self, nodeName=tagName)
        if attributes:
            for a, v in attributes.items(): elem.setAttribute(a, v)
        if text: elem.appendChild(self.createTextNode(text))
        if parent: parent.appendChild(elem)
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
        if parentNode is not None: assert parentNode.iSElement
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
            % (self.documentElement.nodeName, pub, sys)
        )

    @property
    def outerXML(self) -> str:  # Document  # extension
        return self.xmlDcl + self.documentElement.outerXML

    @property
    def xmlDcl(self) -> str:  # extension
        return f"""<?xml version="1.0" encoding={self.characterSet}?>"""

    @property
    def docTypeDcl(self) -> str:  # extension
        if self.doctype: return self.doctype.outerXml
        return f"""<!DOCTYPE {self.documentElement.nodeName} []>"""

    @property
    def innerXML(self) -> str:  # Node  # extension
        # raise HIERARCHY_REQUEST_ERR() ? Everybody overrides...
        if not self.childNodes: return ""
        t = ""
        for ch in self.childNodes:
            t += ch.outerXML
        return t

    def outerJSON(self, indent:str="  ", depth:int=0) -> str:  # Node  # extension
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
        % (self.namespaceUri, self.documentElement.nodeName)
        + self.documentElement.outerJSON(indent, depth=depth+1)
        + "]\n"
        )

    def tostring(self) -> str:  # Document  # extension
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
            if self.ownerDocument.MLDeclaration.caseInsensitivee:
                IdValue = IdValue.casefold()
            if IdValue: theIndex[IdValue] = node
        return theIndex

    def checkNode(self, deep:bool=True):  # Document
        super().checkNode()
        assert self.nodeType == NodeType.DOCUMENT_NODE
        assert self.nodeName == "#document"
        assert self.parentNode is None
        assert self.attributes is None
        assert self.previousSibling is None and self.nextSibling is None
        if self.documentElement is not None:
            assert self.documentElement.isElement
            assert XStr.isXmlQName(self.documentElement.nodeName)
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
        super().__init__(ownerDocument, nodeName)
        self.nodeType = Node.ELEMENT_NODE
        self.attributes = None
        self.inScopeNamespaces = None

    def _addNamespace (self, name:str, uri:str=""):
        """Add the given ns def to this Element. Most elements just inherit,
        so they just get a ref to their parent's defs. But when one is added,
        a copy is created (even if the ns is already on the parent, b/c
        adding a ns explicitly is different than just inheriting.
        """
        prefix, _, local = name.partition(":")
        if (not local):
            local = prefix; prefix = ""
        if prefix not in [ "", "xmlns" ]:
            raise NAME_ERR("_addNamespace: Invalid prefix in '{name}' -> '{uri}'.")
        if not (local == "" or XStr.isXmName(local)):
            raise NAME_ERR("_addNamespace: Invalid local part in '{name}' -> '{uri}'.")

        if (self.parentNode and
            self.inScopeNamespaces is self.parentNode.inScopeNamespaces):
            self.inScopeNamespaces = self.parentNode.inScopeNamespaces.copy()
        self.inScopeNamespaces[name[6:]] = uri

    def cloneNode(self, deep:bool=False) -> 'Element':
        """NOTE: Default value for 'deep' has changed in spec and browsers!
         Don't copy the tree relationships.
         TODO: Move nodeType cases to the subclasses.
        """
        newNode = Element(ownerDocument=self.ownerDocument, nodeName=self.nodeName)
        if not self.attributes:
            newNode.attributes = None
        else:
            for k in self.attributes:
                newNode.setAttribute(k, self.attributes[k].value)

        if deep and self.childNodes:
            for ch in self.childNodes:
                newNode.appendChild(ch.cloneNode(deep=True))
        if self.userData:
            newNode.userData = self.userData
        return newNode

    def clear(self) -> None:  # extension
        #import pudb; pudb.set_trace()
        if self.attributes:
            for aname in self.attributes:
                self.removeAttribute(aname)
        while len(self.childNodes) > 0:
            ch = self.childNodes[0]
            assert ch.parentNode is self
            self.removeChild(ch)
            ch.unlink()

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
        cur = self
        while (cur is not None):
            if cur.prefix:
                if cur.prefix not in self.ownerDocument.nsIndex:
                    raise KeyError(f"Cannot map ns prefix '{cur.prefix}'.")
                return self.ownerDocument.nsIndex[cur.prefix]
            cur = cur.parentNode
        return None

    def isEqualNode(self, n2) -> bool:  # Element
        if not super().isEqualNode(n2): return False
        if self.attributes != n2.attributes: return False
        if len(self) != len(n2): return False
        for i, ch in enumerate(self.childNodes):
            if not ch.isEqualNode(n2.childNodes[i]): return False
        return True


    ###########################################################################
    # Manage attributes. They are a Dict (or None), keyed by nodeName.
    # The value is the whole Attr instance.

    ### Attribute plain
    #
    def _findAttr(self, ns:str, aname:str) -> 'Attr':
        """All attribute retrieval goes through here.
        """
        if not self.attributes: return None
        if aname in self.attributes:
            return self.attributes[aname]
        for _k, anode in self.attributes.items():
            localName = aname.partition(":")[2] or aname
            print(f"_findAttr ('{aname}') (ns '{ns}') vs. '{localName}' in {self.attributes}.")
            if (localName == aname):
                print("    localName matches, anode is %s." % (repr(anode)))
                if (not ns or ns == ANY_NS): return anode
                if (anode.namespaceURI == ns): return anode
                print("    yet fail on ns")
        return None

    def _presetAttr(self, aname:str, avalue:str):
        """Common precursor for all methods that add/set attributes.
        """
        if self.attributes is None:
            self.attributes = NamedNodeMap(
                ownerDocument=self.ownerDocument, parentNode=self)
        if aname.startswith("xmlns:"):
            self._addNamespace(aname, avalue)

    def hasAttribute(self, aname:NmToken) -> bool:
        return self._findAttr(ns=None, aname=aname) is not None

    def setAttribute(self, aname:NmToken, avalue:Any) -> None:
        self._presetAttr(aname, avalue)
        self.attributes.setNamedItem(aname, avalue)

    def getAttribute(self, aname:NmToken, castAs:type=str, default:Any=None) -> str:
        """Normal getAttribute, but can cast and default for caller.
        """
        anode = self._findAttr(ns=None, aname=aname)
        if anode is None: return default
        if castAs: return castAs(anode.value)
        return anode.value

    def removeAttribute(self, aname:NmToken) -> None:
        """Silent no-op if not present.
        """
        anode = self._findAttr(ns=None, aname=aname)
        if anode is None: return
        self.attributes.removeNamedItem(aname)
        if len(self.attributes) == 0: self.attributes = None

    ### Attribute Node
    #
    def setAttributeNode(self, anode:'Attr') -> 'Attr':
        assert isinstance(anode, Attr)
        self._presetAttr(anode.nodeName, anode.value)
        old = self._findAttr(ns=None, aname=anode.nodeName)
        self.attributes.setNamedItem(anode)
        if (old is not None): old.parentNode = None
        return old

    def getAttributeNode(self, aname:NmToken) -> 'Attr':
        # TODO Should this return a new disconnected Attr???
        return self._findAttr(ns=None, aname=aname)

    def removeAttributeNode(self, anode:'Attr') -> 'Attr':
        """Unlike removeAttribute and NS, this *can* raise an exception.
        """
        assert isinstance(anode, Attr)
        old = self._findAttr(ns=None, aname=anode.nodeName)
        if old is None:
            raise NOT_FOUND_ERR(
                f"Attribute node for '{anode.nodeName}' not found: {self.startTag}")
        if old is not anode:
            raise NOT_FOUND_ERR(
                "Node has attribute {anode.nodeName}, but not the Attr you passed.")
        anode.parentNode = None
        del self.attributes[anode.nodeName]

    ### Attribute NS
    #
    def hasAttributeNS(self, aname:NmToken, ns) -> bool:
        return self.hasAttribute(aname)

    def setAttributeNS(self, ns:str, aname:NmToken, avalue:str) -> None:
        self._presetAttr(aname, avalue)
        attrNode = Attr(aname, avalue, ownerDocument=self.ownerDocument,
            nsPrefix=ns, namespaceURI=None, parentNode=self)
        self.attributes.setNamedItem(attrNode)
        if ns == "xmlns":
            attrNode2 = Attr(aname[6:], avalue,
                ownerDocument=self.ownerDocument,
                nsPrefix=ns, namespaceURI=None, parentNode=self)
            self.inScopeNamespaces.setNamedItem(attrNode2)

    def getAttributeNS(self, ns:str, aname:NmToken, castAs:type=str, default:Any=None) -> str:
    # TODO Check/fix getAttributeNS
        assert not ns or ns == ANY_NS or NameSpaces.isNamespaceURI(ns)
        return self.getAttribute(aname, castAs, default)

    def removeAttributeNS(self, ns, aname:NmToken) -> None:
        if self.hasAttribute(aname):
            self.attributes[aname].parentNode = None
            del self.attributes[aname]

    ### Attribute NodeNS
    #
    def setAttributeNodeNS(self, ns, anode:'Attr') -> 'Attr':
        assert isinstance(anode, Attr)
        self._presetAttr(anode.nodeName, anode.value)
        old = self._findAttr(ns=None, aname=anode.nodeName)
        self.attributes.setNamedItem(anode)
        if (old is not None): old.parentNode = None
        return old

    def getAttributeNodeNS(self, ns:str, aname:NmToken) -> 'Attr':
        assert NameSpaces.isNamespaceURI(ns)
        return self._findAttr(ns=ns, aname=aname)

    ### Attribute Specials
    #
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


    ###########################################################################
    ####### Element: Descendant Selectors
    #
    def elementChildN(self, index:int) -> 'Element':
        """Return the nth *element* child of the Node
        TODO Delete? getitem will do this fine.  Whence?
        """
        if not self.childNodes: return None
        if index < 0:
            checkOrder = reversed(list(self.childNodes))
            index = -index
        else:
            checkOrder = list(self.childNodes)

        elementCount = 0
        for ch in checkOrder:
            if ch.nodeType != Node.ELEMENT_NODE: continue
            elementCount += 1
            if elementCount >= index: return ch
        return None

    def getElementById(self, IdValue:str) -> 'Element':  # DOM 2
        """TODO For HTML these should be case-insensitive.
        This is not on (XML) minidom.Element.
        """
        if self.ownerDocument.IdIndex is None:
            self.ownerDocument.IDIndex = self.buildIdIndex()
        if self.ownerDocument.MLDeclaration.caseInsensitive:
            IdValue = IdValue.casefold()
        if IdValue in self.ownerDocument.IdIndex:
            return self.ownerDocument.IdIndex[IdValue]
        return None

    def getElementsByClassName(self, className:str, nodeList=None) -> List:
        """Works even if it's just one of multiple class tokens.
        This is not on (XML) minidom.Element.
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
        This is on minidom.Element.
        """
        if nodeList is None: nodeList = []
        if self.nodeType != Node.ELEMENT_NODE: return nodeList
        if NameSpaces.nameMatch(self, tagName, ns=None):
            nodeList.append(self)
        for ch in self.childNodes:
            ch.getElementsByTagName(tagName, nodeList)
        return nodeList

    def getElementsByTagNameNS(self, tagName:NmToken, namespaceURI:str, nodeList=None) -> List:
        """This is on minidom.Element.
        """
        if not XStr.isXmlName(tagName):
            raise NAME_ERR("Bad attribute name '%s'." % (tagName))
        if nodeList is None: nodeList = []
        if self.nodeType != Node.ELEMENT_NODE: return nodeList
        if NameSpaces.nameMatch(self, tagName, ns=namespaceURI):
            nodeList.append(self)
        for ch in self.childNodes:
            ch.getElementsByTagNameNS(tagName, nodeList, namespaceURI)
        return nodeList


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
    def innerXML(self) -> str:  # Element
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

        print(f"\n####### innerXML setter for '{xml}'\ncreated doc: {doc.outerXML}.")
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
        if self.nodeType != NodeType.ELEMENT_NODE: return ''
        t = f"<{self.nodeName}"
        if self.attributes:
            names = self.attributes.keys()
            if sortAttrs: names = sorted(names)
            for k in names:
                t += f' {k}="{XStr.escapeAttribute(self.attributes[k].value)}"'
        return t + ("/" if empty else "") + ">"

    @property
    def endTag(self) -> str:
        return f"</{self.nodeName}>"

    ### Meta

    def unlink(self, keepAttrs:bool=False):
        super().unlink(keepAttrs=keepAttrs)
        if self.attributes:
            for attr in self.attributes.values(): attr.unlink()
            if not keepAttrs: self.attributes = None
        if self.childNodes:
            self.childNodes.clear()

    def checkNode(self, deep:bool=False):  # Element
        super().checkNode()

        if self.attributes is not None:
            assert isinstance(self.attributes, NamedNodeMap)
            for aname, anode in self.attributes.items():
                assert isinstance(anode, Attr)
                assert aname == anode.nodeName
                anode.checkNode()

        if self.childNodes:
            for i, ch in enumerate(self.childNodes):
                assert isinstance(ch, Node)
                assert ch.nodeType in [
                    NodeType.ELEMENT_NODE,
                    NodeType.ATTRIBUTE_NODE,
                    NodeType.TEXT_NODE,
                    NodeType.CDATA_SECTION_NODE,
                    NodeType.ENTITY_REFERENCE_NODE,
                    NodeType.PROCESSING_INSTRUCTION_NODE,
                    NodeType.COMMENT_NODE,
                ]
                assert ch.parentNode == self
                if i > 0: assert ch.previousSibling
                if i < len(self.childNodes)-1: assert ch.nextSibling
                if deep: ch.checkNode(deep)

    # End class Element


###############################################################################
#
class CharacterData(Node):
    """A cover class for Node sub-types that can only occur as leaf nodes
    (and not including Attr either):
        Text, CDATASection, PI, Comment
        (and EntityReference and Notation, now obsolete)
    """
    def __init__(self, ownerDocument=None, nodeName:NmToken=None):
        super().__init__(ownerDocument, nodeName)
        self.data = None

    def isEqualNode(self, n2) -> bool:  # CharacterData
        if not super().isEqualNode(n2): return False
        if self.data != n2.data: return False
        return True

    @property
    def length(self) -> int:
        return len(self.data)

    ### String mutators

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

    # Hide any methods that can't apply to leaves.
    # Don't know why DOM put them on Node instead of Element.
    #
    LeafChildMsg = "CharacterData nodes cannot have children."
    @property
    def firstChild(self):
        raise HIERARCHY_REQUEST_ERR(CharacterData.LeafChildMsg)
    @property
    def lastChild(self):
        raise HIERARCHY_REQUEST_ERR(CharacterData.LeafChildMsg)

    @hidden
    def __getitem__(self, *args):
        raise HIERARCHY_REQUEST_ERR(CharacterData.LeafChildMsg)
    @hidden
    def appendChild(self, newChild:Node):
        raise HIERARCHY_REQUEST_ERR(CharacterData.LeafChildMsg)
    @hidden
    def prependChild(self, newChild:Node):
        raise HIERARCHY_REQUEST_ERR(CharacterData.LeafChildMsg)
    @hidden
    def insertBefore(self, newChild:Node, oldChild:Union[Node, int]):
        raise HIERARCHY_REQUEST_ERR(CharacterData.LeafChildMsg)
    @hidden
    def removeChild(self, oldChild:Union[Node, int]):
        raise HIERARCHY_REQUEST_ERR(CharacterData.LeafChildMsg)
    @hidden
    def replaceChild(self, newChild:Node, oldChild:Union[Node, int]):
        raise HIERARCHY_REQUEST_ERR(CharacterData.LeafChildMsg)
    @hidden
    def append(self, newChild:Node) -> None:
        raise HIERARCHY_REQUEST_ERR(CharacterData.LeafChildMsg)

    def unlink(self, keepAttrs:bool=False):
        super().unlink()
        self.data             = None
        return


    def checkNode(self, deep:bool=True):  # CharacterData (see also Attr):
        super().checkNode()
        assert self.parentNode is None or self.parentNode.isElement
        #assert self.attributes is None and self.childNodes is None
        if self.isPI: assert XStr.isXmlName(self.target)


###############################################################################
#
class Text(CharacterData):
    def __init__(self, ownerDocument=None, data:str=""):
        super().__init__(ownerDocument=ownerDocument, nodeName="#text")
        self.nodeType = Node.TEXT_NODE
        self.data = data

    def cloneNode(self, deep:bool=False) -> 'Text':
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
        super().__init__(ownerDocument=ownerDocument, nodeName="#cdata-section")
        self.nodeType = Node.CDATA_SECTION_NODE
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
        istr = indent * depth
        return istr + '[ {"#name"="#cdata"}, "%s"]' % (escapeJsonStr(self.data))

    def tostring(self) -> str:  # CDATASection
        return self.outerXML


###############################################################################
#
class ProcessingInstruction(CharacterData):
    def __init__(self, ownerDocument=None, target=None, data:str=""):
        if target is not None and target!="" and not XStr.isXmlName(target):
            raise NAME_ERR("Bad PI target '%s'." % (target))
        super().__init__(ownerDocument=ownerDocument, nodeName=target)
        self.nodeType = Node.PROCESSING_INSTRUCTION_NODE
        self.data = data
        self.target = target

    def cloneNode(self, deep:bool=False) -> 'ProcessingInstruction':
        newNode = ProcessingInstruction(
            ownerDocument=self.ownerDocument,
            target=self.nodeName, data=self.data)
        if self.userData: newNode.userData = self.userData
        return newNode

    def isEqualNode(self, n2) -> bool:  # PI
        if not super().isEqualNode(n2): return False
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
        super().__init__(ownerDocument=ownerDocument, nodeName="#comment")
        self.nodeType=Node.COMMENT_NODE
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
        return (istr + '[ { "#name":"#comment", "#data":"%s" } ]'
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
        super().__init__(ownerDocument=ownerDocument, nodeName=name)
        self.nodeType = Node.ENTITY_REFERENCE_NODE
        self.data = data

    @property
    def nodeValue(self):  # EntityReference
        return self.data

    @nodeValue.setter
    def nodeValue(self, newData:str=""):  # EntityReference
        self.data = newData

    @property
    def outerXML(self) -> str:  # EntityReference
        return '&%s;' % (self.nodeName)

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
    def __init__(self, ownerDocument:Node, name:str, data:str="",
        systemId:str=None, publicId:str=None):
        super().__init__(ownerDocument=ownerDocument, nodeName=name)
        self.nodeType = Node.NOTATION_NODE
        self.data = data
        self.systemId = systemId
        self.publicId = publicId

    def cloneNode(self, deep:bool=False) -> 'Notation':
        newNode = Notation(ownerDocument=self.ownerDocument, name=self.nodeName,
            data=self.data, systemId=self.systemId, publicId=self.publicId)
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
            % (escapeJsonStr(self.nodeName), escapeJsonStr(self.publicID),
            escapeJsonStr(self.systemID)))

    def tostring(self) -> str:  # Notation
        return self.outerXML


###############################################################################
#
class Attr(Node):
    """This is a little weird, because each Element can own a NamedNodeMap
    (which is a Dict, not a Node), which then owns the Attr objects.
    TODO: namespace support
    """
    def __init__(self, name:NmToken, value:Any, ownerDocument:Document=None,
        nsPrefix:NmToken=None, namespaceURI:str=None, parentNode:Node=None,
        attrType:type=str):
        super().__init__(ownerDocument=ownerDocument, nodeName=name)
        self.nodeType = Node.ATTRIBUTE_NODE
        self.parentNode = parentNode  # extension
        self.ownerElement = parentNode
        if parentNode is not None and parentNode.nodeType != Node.ELEMENT_NODE:
            raise TypeError(
    f"parentNode for attribute '{name}' is nodeType {parentNode.nodeType}, not ELEMENT.")

        if not XStr.isXmlQName(name):
            raise NAME_ERR(f"Bad attribute name '{name}'.")
        if not isinstance(attrType, type):
            raise TypeError(f"attrType for '{name}' is not a type, but {type(attrType)}.")
        self.attrType = attrType
        self.value = attrType(value)  # TODO Move to nodeValue?
        self.inScopeNamespaces = None

    def bool(self):  # extension
        return bool(self.value)

    def clear(self):  # extension
        raise NotImplementedError("No clear() on Document nodes.")

    @property
    def prefix(self) -> str:
        return XStr.getPrefixPart(self.nodeName)
    @property
    def localName(self) -> str:
        return XStr.getLocalPart(self.nodeName)
    @property
    def namespaceURI(self) -> str:
        prefix = XStr.getPrefixPart(self.nodeName)
        if not prefix: return None
        if prefix not in self.ownerDocument.nsIndex: return None
        return self.ownerDocument.nsIndex[prefix]

    @property
    def isConnected(self) -> bool:  # Attr
        return False

    @property
    def nextSibling(self) -> 'Node':
        raise HIERARCHY_REQUEST_ERR("Attributes are not children.")

    @property
    def previousSibling(self) -> 'Node':
        raise HIERARCHY_REQUEST_ERR("Attributes are not children.")

    @property
    def next(self) -> 'Node':
        raise HIERARCHY_REQUEST_ERR("Attributes are not children.")

    @property
    def previous(self) -> 'Node':
        raise HIERARCHY_REQUEST_ERR("Attributes are not children.")

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
        """Could use the owning element's position, but that would also
        mean document order becomes a *partial* order.
        """
        raise HIERARCHY_REQUEST_ERR("Attributes do not have document positions.")

    def isEqualNode(self, n2:'Attr') -> bool:
        if not n2.isAttribute: raise ValueError("No n2 attr provided.")
        if not self.nodeNameMatches(n2): return False
        if not self.value == n2.value: return False
        return True

    def cloneNode(self, deep:bool=False) -> 'Attr':
        newAttr = Attr(name=self.nodeName, value=self.value,
            ownerDocument=self.ownerDocument, parentNode=None, attrType=self.attrType)
        return newAttr

    ### Serializers (minidom lacks these)  # extension
    #
    @property
    def outerXML(self) -> str:  # Attr
        """Includes the name, equal, and quoted/escaped value.
        (this is unlike innerHTML(), which doesn't exist for Attrs)
        """
        return f"{self.nodeName}={self.innerXML}"

    @property
    def innerXML(self) -> str:  # Attr
        """Includes just the quoted/escaped value.
        (this is unlike innerHTML(), which doesn't exist for Attrs)
        """
        return f'"{XStr.escapeAttribute(self.value)}"'

    def outerJSON(self, indent:str="  ", depth:int=0) -> str:  # Attr
        # This was handled on Element.
        raise HIERARCHY_REQUEST_ERR("outerJSON() not available on Attr.")

    def attrToJson(self, listAttrs:bool=False) -> str:
        """This uses JSON non-string types iff the value is actually
        of that type, or somebody declared the attr that way.
        not if it's a string that just looks like it.
        TODO: Move onto Attr?
        """
        aname = self.nodeName
        avalue = self.value
        buf = f'"{aname}":'
        if isinstance(avalue, float): buf += "%f" % (avalue)
        elif isinstance(avalue, int): buf += "%d" % (avalue)
        elif avalue is True: buf += "true"
        elif avalue is False: buf += "false"
        elif avalue is None: buf += "nil"
        elif isinstance(avalue, str): buf += escapeJsonStr(avalue)
        elif isinstance(avalue, list):  # Only for tokenized attrs
            if listAttrs:
                buf += "[ %s ]" % (
                    ", ".join([  escapeJsonStr(str(x)) for x in avalue ]))
            else:
                buf += '"%s"' % (
                    escapeJsonStr(" ".join([ str(x) for x in avalue ])))
        else:
            raise HIERARCHY_REQUEST_ERR(f"attrToJson got unsupported type {type(avalue)}.")
        return buf

    def tostring(self):  # Attr
        """Attr is not quoted or escaped for this.
        """
        return str(self.nodeValue)

    def checkNode(self, deep:bool=True):  # Attr
        assert self.isAttribute
        if self.ownerDocument is not None:
            assert self.ownerDocument.isDocument
        if self.parentNode is not None:
            assert self.parentNode.isElement
            assert self.ownerDocument == self.parentNode.ownerDocument
            if len(self.parentNode) > 0:
                for i, ch in enumerate(self.parentNode):
                    assert ch is not self, f"Attr '{self.nodeName}' got into childNodes[{i}]."
                if self.parentNode.childNodes.contains(self):
                    # 'contains' logic may be non-obvious, so double-check.
                    print(self.outerXML)
                    assert False, (
                        f"Attr '{self.nodeName}' got into childNodes (contains *only*)")

        assert self.inScopeNamespaces is None
        assert XStr.isXmlQName(self.nodeName)
        if self.attrType and self.value is not None:
            assert isinstance(self.attrType, type)
            assert isinstance(self.value, self.attrType)
        if self.userData is not None:
            assert isinstance(self.userData, dict)

        assert "attributes" not in dir(self)
        assert "data" not in dir(self) and "target" not in dir(self)

Attribute = Attr  # Attr vs. setAttribute


###############################################################################
#
class NamedNodeMap(OrderedDict):
    """This is really just a dict or OrderedDict (latter lets us retain
    order from source if desired). So let people do Python stuff with it.

    TODO: Problem is, Individual attributes need to know who owns them, so
    they kinda have to be an object so they can store that ref. Is there
    anything else Attr actually needs, though (besides namespace stuff)?

    So this stores a whole Attr instance as the value. Might be better to
    store just the nominal value there and rig it to have the rest accessible,
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

    def setNamedItem(self, attrNodeOrName:Union[str, Attr], avalue:Any=None,
        atype:type=str) -> None:
        """This can take either an Attr (as in the DOM version), which contains
        its own name; or a string name and then a value (in which case the Attr
        is constructed automatically).
        TODO: types
        """
        if isinstance(attrNodeOrName, Attr):
            assert avalue is None
            self[attrNodeOrName.nodeName] = attrNodeOrName
        else:
            assert XStr.isXmlName(attrNodeOrName)
            self[attrNodeOrName] = Attr(attrNodeOrName, avalue, attrType=atype,
                ownerDocument=self.ownerDocument, parentNode=self.parentNode, )

    def getNamedItem(self, name:NmToken) -> Attr:
        """Per DOM, this returns the entire Attr instance, not just value.
        No exception if assent.
        """
        if name not in self: return None
        theAttr = self[name]
        assert isinstance(theAttr, Attr)
        return theAttr

    def getNamedValue(self, name:NmToken) -> Any:  # extension
        """Returns just the actual value.
        """
        if name not in self: return None
        return self[name].value

    def removeNamedItem(self, name:NmToken) -> Attr:
        #import pudb; pudb.set_trace()
        if name not in self:
            raise KeyError(f"Named item to remove ('{name}') not found.")
        theAttrNode = self[name]
        theAttrNode.unlink()
        del self[name]
        theAttrNode.ownerElement = None
        return theAttrNode


    def setNamedItemNS(self, ns:str, attrNode:Node) -> None:  # TODO Implement setNamedItemNS
        assert NameSpaces.isNamespaceURI(ns)
        if not XStr.isXmlName(attrNode.nodeName):
            raise NAME_ERR("Bad name '%s'." % (attrNode.nodeName))
        raise NOT_SUPPORTED_ERR("NamedNodeMap.setNamedItemNS")

    def getNamedItemNS(self, ns:str, name:NmToken) -> Any:  # TODO Implement getNamedItemNS
        assert NameSpaces.isNamespaceURI(ns)
        raise NOT_SUPPORTED_ERR("NamedNodeMap.getNamedItemNS")

    def getNamedValueNS(self, ns:str, name:NmToken) -> Any:  # extension
        assert NameSpaces.isNamespaceURI(ns)
        raise NOT_SUPPORTED_ERR("NamedNodeMap.getNamedItemNS")

    def removeNamedItemNS(self, ns:str, name:NmToken) -> None:  # TODO Implement removeNamedItemNS
        assert NameSpaces.isNamespaceURI(ns)
        raise NOT_SUPPORTED_ERR("NamedNodeMap.removeNamedItemNS")


    def item(self, index:int) -> Attr:
        if index < 0: index = len(self) + index
        if index >= len(self): raise IndexError(
            f"NamedNodeMap item #{index} out of range ({len(self)}).")
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
        TODO: NS, incl. any?
        """
        for k, anode in enumerate(self):
            if anode.nodeName == name: return k
        return None

    def clear(self) -> None:
        for aname in self.keys():
            self.removeNamedItem(aname)
        assert len(self) == 0


###############################################################################
#
class NameSpaces(Dict):  # extension, sort of
    """Manage prefix <-> URI mappings.
    And the reverse -- though that can be 1:n, so uri2prefix[] contains lists!
    TODO: Check match semantics and integrate.
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
