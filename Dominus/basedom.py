#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# A fairly simple native Python DOM implementation. Basically DOM 2
# plus a bunch of Pythonic, xpath, etree, etc. conveniences.
#
#pylint: disable=W0613, W0212
#pylint: disable=E1101
#
#import sys
import re
from collections import OrderedDict
from types import SimpleNamespace
import unicodedata
from typing import Any, Callable, Dict, List, Union, Iterable, Tuple
import functools
import logging

from basedomtypes import HReqE, ICharE, NSuppE
from basedomtypes import NamespaceError
from basedomtypes import NotFoundError
from basedomtypes import OperationError

from basedomtypes import NMTOKEN_t

from saxplayer import SaxEvents
from domenums import NodeType, RelPosition, RWord
from dombuilder import DomBuilder
from xmlstrings import XmlStrings as XStr, CaseHandler
from idhandler import IdHandler

#from domgetitem import __domgetitem__  # NodeSelKind
#from domadditions import whatwgAdditions, EtAdditions, OtherAdditions
#from cssselectors import CssSelectors

lg = logging.getLogger("BaseDOM")

# Reserved names, etc.
ANY_NS = "##any"  # See https://qt4cg.org/specifications/xquery-40/xpath-40.html

__metadata__ = {
    "title"        : "BaseDOM",
    "description"  : "A more modern, Pythonic, fast DOM-ish implementation.",
    "rightsHolder" : "Steven J. DeRose",
    "creator"      : "http://viaf.org/viaf/50334488",
    "type"         : "http://purl.org/dc/dcmitype/Software",
    "language"     : "Python 3.7",
    "created"      : "2016-02-06",
    "modified"     : "2024-10",
    "publisher"    : "http://github.com/sderose",
    "license"      : "https://creativecommons.org/licenses/by-sa/3.0/"
}
__version__ = __metadata__['modified']

descr = """See BaseDom.md"""

def _dtrace(msg):
    return
    #if __debug__: sys.stderr.write(msg + "\n")

def hidden(func):
    """Define "@hidden" decorator to signal that a method is hiding
    a superclass method. This could also be set up to make it uncallable.
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        raise AttributeError(f"'{func.__name__}' is a hidden method")
    wrapper.__is_hidden__ = True
    return wrapper

def escapeJsonStr(s:str) -> str:
    return re.sub(r'([\\"])', "\\\\1", s)


###############################################################################
#
def getDOMImplementation(name:str=None) -> type:
    return DOMImplementation()

class DOMImplementation:
    name = "BaseDOM"
    version = "0.1"

    def __init__(self, name:str=None):
        if name: DOMImplementation.name = name

    def createDocument(self, namespaceURI:str, qualifiedName:NMTOKEN_t,
        doctype:'DocumentType'
        ) -> 'Document':

        if namespaceURI is None:
            namespaceURI = ""
            if not qualifiedName:  # fetch from doctype?
                raise ICharE("Root element to be has no name")
        prefix = XStr.getLocalPart(qualifiedName)
        if prefix == "xml":
            if namespaceURI in [ RWord.XML_NS_URI, "" ]:
                namespaceURI = RWord.XML_NS_URI
            else:
                raise NamespaceError(f"URI for xml: is not '{RWord.XML_NS_URI}'")

        doc = Document()
        doc.documentElement = doc.createElement(qualifiedName)
        if prefix:
            doc.documentElement.setAttribute(
                RWord.NS_PREFIX+":"+prefix, namespaceURI)
        if doctype:
            doctype.parentNode = doctype.ownerDocument = doc
        doc.doctype = doctype
        return doc

    def createDocumentType(self, qualifiedName:NMTOKEN_t,
        publicId:str, systemId:str) -> 'DocumentType':
        """TODO Implement createDocumentType
        """
        raise NSuppE
        #import DocumentType
        #loc = XStr.getLocalPart(qualifiedName)
        #return DocumentType.DocumentType(qualifiedName, publicId, systemId)

    def registerDOMImplementation(self, name:str, factory) -> None:
        raise NSuppE

    @staticmethod
    def getImplementation() -> type:
        return DOMImplementation

    # Put in some loaders

    def parse(self, filename_or_file:str, parser=None, bufsize:int=None
        ) -> 'Document':
        dbuilder = DomBuilder(domImpl=Document)
        theDom = dbuilder.parse(filename_or_file)
        return theDom

    def parse_string(self, s:str, parser=None) -> 'Document':
        dbuilder = DomBuilder(domImpl=Document)
        theDom = dbuilder.parse_string(s)
        return theDom


###############################################################################
#
class FormatOptions:  # HERE
    """Pass around for toprettyxml. Callers can pass like-named
    keywords args, or construct it once and pass the object.
    Warning: 'depth' gets modified during traversals, so is not thread-safe.
    """
    def __init__(self, **kwargs):
        self.depth = 0                  # (changes during traversals)

        # Whitespace insertion
        self.newl:str = ""              # String for line-breaks
        self.indent:str = ""            # String to repeat for indent
        self.wrapTextAt:int = 0         # Wrap text near this interval NOTYET
        self.breakBB:bool = True        # Newline before start tags
        self.breakAB:bool = False       # Newline after start tags
        self.breakAttrs:bool = False    # Newline before each attribute
        self.breakBE:bool = False       # Newline before end tags
        self.breakAE:bool = False       # Newline after end tags

        self.inlineTags:List = []       # List of inline elements, no breakXX.

        # Syntax alternatives
        self.canonical:bool = False     # Use canonical XML syntax? NOTYET
        self.encoding:str = "utf-8"     # utf-8. Just utf-8.
        self.includeXmlDcl = True
        self.includeDocType = True
        self.useEmpty:bool   = True     # Use XML empty-element syntax
        self.emptySpace:bool = True     # Include a space before the /
        self.quoteChar:str = '"'        # Char to quote attributes NOTYET
        self.sortAttrs:bool = False     # Alphabetical order for attributes
        self.normAttrs = False

        # Escaping (TODO: Hook up FormatOptions and XmlStrings)
        self.escapeGT:bool = False      # Escape > in content NOTYET
        self.ASCII = False              # Escape all non-ASCII NOTYET
        self.charBase:int = 16          # Numeric char refs in decimal or hex? NOTYET
        self.charPad:int = 4            # Min width for numberic char refs
        self.htmlChars:bool = True      # Use HTML named special characters

        for k, v in kwargs.items():
            if k == "inlineTags":
                self.setInlines(v)
            elif k not in self.__dict__ or not k.isascii() or not k.isalnum():
                raise KeyError(f"FormatOptions: Unknown kw arg '{k}'.")
            elif not isinstance(v, type(self.__dict__[k])):
                raise TypeError(f"FormatOptions: kw arg '{k}' expected type "
                    f"{type(self.__dict__[k])}, not {type(v)}.")
            self.__dict__[k] = v

    @staticmethod
    def canonicalFO() -> 'FormatOptions':
        """Return a FormatOptions object set up to ensure Canonical XML output.
        """
        fo = FormatOptions()
        fo.canonical = True
        fo.sortAttrs = True
        fo.normAttrs = True
        fo.newl = "\n"
        fo.quoteChar = '"'
        fo.htmlChars = False
        fo.includeDocType = False
        fo.useEmpty = False
        # TODO: namespace dcl before other attrs

        fo.indent:str = ""
        fo.wrapTextAt = 0
        fo.breakBB = fo.breakAB = fo.breakAttrs = fo.breakBE = fo.breakAE = False

        return fo

    def setInlines(self, v:Union[Iterable, str]) -> int:
        """Accept either a known schema name, a space-separate name list,
        or an Iterable of names.
        Returns the numbers of tags in the resulting list.
        """
        if not v:
            self.inlineTags = []
            return 0
        if isinstance(v, str):
            if v == "HTML": v = """
                a abbr acronym b bdo big cite code dfn em i img input kbd
                q s small span strike strong sub sup tt var"""
            elif v == "DocBook": v = """
                bi font foreign rom u"""
            self.inlineTags = v.split()
        else:
            self.inlineTags = v

        badt = [ tag for tag in self.inlineTags if not XStr.isXmlQName(tag) ]
        if badt: raise ICharE(f'Bad inlineTags [ {", ".join(badt)} ].')

    @property
    def ws(self) -> str:
        return self.newl + self.indent * self.depth


###############################################################################
#
class NodeList(list):
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
        """Careful, Python and DOM "contains" are different!
        x.__contains__(y) is non-recursive.
        x.contains(y) is recursive, but NodeList != Element anyway.
        """
        assert isinstance(item, Node)
        for x in self:
            if x is item: return True
        return False

    def __delitem__(self, item:Union[int, 'Node']) -> None:
        if isinstance(item, Node):
            try:
                item = self.index(item)
            except ValueError as e:
                raise HReqE("Node for __delitem__ is not in NodeList.") from e
            super().__delitem__(item)

    ### list adder/multipliers should work as-is for Nodelist, but not Node.


###############################################################################
#
class PlainNode(list):
    """The main (basically abstract) class for DOM, from which many are derived.
        https://www.w3.org/TR/2000/REC-DOM-Level-2-Core-20001113

    We make this a direct subclass of list, of its childNodes. This gets many
    useful and hopefully intuitive features. However, it has some side effects:
      * Since Nodes know where they are (parent/owner), ins/del are special
      * Inserting a connected node can't just insert a ref, but must copy.
      * Empty nodes (no childNode) are not usefully False, b/c they are not
        all identical. So bool() is special.
      * "contains" is nonrecursive in Python lists, but recursive in DOM.

    """
    DOCUMENT_NODE                = NodeType.DOCUMENT_NODE
    ELEMENT_NODE                 = NodeType.ELEMENT_NODE
    ATTRIBUTE_NODE               = NodeType.ATTRIBUTE_NODE
    TEXT_NODE                    = NodeType.TEXT_NODE
    CDATA_SECTION_NODE           = NodeType.CDATA_SECTION_NODE
    PROCESSING_INSTRUCTION_NODE  = NodeType.PROCESSING_INSTRUCTION_NODE
    COMMENT_NODE                 = NodeType.COMMENT_NODE

    def __init__(self, ownerDocument=None, nodeName:NMTOKEN_t=None):
        """PlainNode (and Node) shouldn't really be instantiated.
        minidom let it be, but with different parameters.
        I add the params for constructor consistency.
        Also, since here it is a list, there's not much need to distinguish
        Node, NodeList, and DocumentFragment -- mainly that only the first
        has to be the (unique) parentNode of all its members (and therefore
        the determiner of siblings, etc.).
        """
        super().__init__()
        self.ownerDocument = ownerDocument
        self.parentNode = None  # minidom Attr lacks....
        self.nodeType = NodeType.NONE
        self.nodeName = nodeName
        self.inheritedNS = {}
        self.userData = None
        self.prevError:str = None  # Mainly for isEqualNode


    def __contains__(self, item:'Node') -> bool:
        """Careful, Python and DOM "contains" are different!
        x.__contains__(y) is non-recursive.
        x.contains(y) is recursive.
        I don't like this, and suggest using x.hasDescendant(y).
        """
        assert isinstance(item, Node)
        for x in self:
            if x is item: return True
        return False

    def contains(self, other:'Node') -> bool:
        """UNLIKE __contains__, this includes indirect descendants!
        Do NOT search all descendants, just check reverse ancestry.
        Nodes do NOT contain self, nor elements attributes.
        Using the synonym 'hasDescendant' may help avoid confusion.
        """
        if other is self or isinstance(other, Attr): return False
        other = other.parentNode
        while (other is not None):
            if other is self: return True
            other = other.parentNode
        return False

    def hasDescendant(self, other:'Node') -> bool:  # HERE
        """Provided b/c 'contains' vs. '__contains__' may be confusing.
        """
        return self.contains(other)

    def __getitem__(self, picker:Any) -> 'NodeList':
        """Need to override so pylint doesn't think 'picker'
        absolutely has to be slice or int.
        """
        if not isinstance(picker, (slice, int)):
            raise TypeError("Fancy __getitem__ not enabled.")
        return super().__getitem__(picker)

    ### TODO Add the dunders from NodeList to PlainNode?

    def getChildIndex(self, onlyElements:bool=False, ofNodeName:bool=False,
        noWSN:bool=False) -> int:  # HERE
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
            if ofNodeName and ch.nodeName != self.nodeName: continue
            i += 1
        #raise HReqE("Child not found.")
        return None

    def getRChildIndex(self, onlyElements:bool=False, ofNodeName:bool=False,
        noWSN:bool=False) -> int:  # HERE
        """Return the position from the end (from -1...) among
        the node's siblings or selected siblings.
        """
        if self.parentNode is None: return None
        i = -1
        for ch in reversed(self.parentNode.childNodes):
            if ch is self: return i
            if onlyElements and not ch.isElement: continue
            if noWSN and ch.isWSN: continue
            if ofNodeName and ch.nodeName != self.nodeName: continue
            i -= 1
        #raise HReqE("Child not found.")
        return None

     # Next three are defined here (PlainNode), but only work for Element and Attr.
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
    def nodeValue(self) -> str:  # PlainNode
        """null for Document, Frag, Doctype, Element, NamedNodeMap.
        """
        return None

    @nodeValue.setter
    def nodeValue(self, newData:str="") -> None:
        raise NSuppE(
            "Cannot set nodeValue on nodeType %s." % (self.nodeType.__name__))

    @property
    def parentElement(self) -> 'Node':  # WHATWG?
        """Main case of non-None non-Element parent is Document (also Frag).
        """
        if self.parentNode is None or not self.parentNode.isElement: return None
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
        if n2 is None:
            _dtrace("other is None")
            return False
        if self.nodeType != n2.nodeType:
            _dtrace(f"nodeType differs ({self.nodeType} vs. {n2.nodeType}).")
            return False
        if not self.nodeNameMatches(n2):
            _dtrace(f"nodeName differs ({self.nodeName} vs. {n2.nodeName}).")
            return False
        if self.nodeValue != n2.nodeValue:
            _dtrace(f"nodeValue differs:\n###{self.nodeValue}###\n###{n2.nodeValue}###")
            return False
        # Element does additional checks like attributes and childNodes
        return True

    def cloneNode(self, deep:bool=False) -> 'Node':
        """NOTE: Default value for 'deep' has changed in spec and browsers!
        """
        raise NSuppE("Shouldn't really be cloning abstract Node.")

    #### Mutators (PlainNode)

    def _expandChildArg(self, ch:Union['Node', int]) -> (int, 'Node'):
        """Let callers specify a child either by object itself or position.
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
                return n, self.childNodes[n]
            raise IndexError(f"child number {ch}, but only {len(self)} there.")
        raise TypeError("Bad child specifier type '%s'." % (type(ch).__name__))

    def normalize(self) -> None:
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

    def appendChild(self, newChild:'Node') -> None:
        self.insert(len(self), newChild)

    def insertBefore(self, newChild:'Node', oldChild:Union['Node', int]) -> None:
        oNum, oChild = self._expandChildArg(oldChild)
        if oChild.parentNode != self:
            raise NotFoundError("Node to insert before is not a child.")
        self.childNodes.insert(oNum, newChild)

    def insertAfter(self, newChild:'Node', oldChild:Union['Node', int]) -> None:  # HERE
        oNum, oChild = self._expandChildArg(oldChild)
        if oChild.parentNode != self:
            raise NotFoundError("Node to insert before is not a child.")
        self.childNodes.insert(oNum+1, newChild)

    def removeChild(self, oldChild:Union['Node', int]) -> 'Node':  # PlainNode
        """Disconnect oldChild from this node, removing it from the tree,
        but not fromm the document. To destroy it, it should also unlinked.
        Namespaces are copied, not cleared (may be if/when re-inserted somewhere).
        """
        if isinstance(oldChild, Node):
            if oldChild.parentNode != self:
                raise HReqE("Node to remove has wrong parent.")
        elif not isinstance(oldChild, int):
            raise HReqE(f"Child to remove is not a Node or int, but a {oldChild.type}.")
        oNum, oChild = self._expandChildArg(oldChild)
        del self.childNodes[oNum]
        oChild.parentNode = None
        if oChild.isElement: oChild._resetinheritedNS()
        #lg.warning("    afterward: %d children.", len(self.childNodes))
        return oChild

    def _resetinheritedNS(self) -> None:
        """When removed, the node loses parentNode but not ownerDocument, and
        has to retain all namespace dcls actually needed by it or any
        descendants (including attributes). This is a pain, and seems like it
        would require a full subtree search to prune. So we carry them all
        along, then trim duplicates when/if the node is pasted later (pruning
        right at that time still required a search).

        TODO The whole ns override/prune thing on insert().
        """
        if self.nodeType not in [ NodeType.ELEMENT_NODE, NodeType.DOCUMENT_NODE ]:
            raise HReqE(f"Don't reset ns on nodeType {self.nodeType}...")
        if self.inheritedNS:
            self.inheritedNS = self.inheritedNS.copy()

    def writexml(self, writer, indent:str="", addindent:str="", newl:str="",
        encoding:str=None, standalone:bool=None) -> None:  # Node
        writer.write(self.toprettyxml(indent=addindent, newl=newl))


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
        elif start < 0: start = len(self.childNodes) + start
        if end is None or end > len(self.childNodes): end = len(self.childNodes)
        if end < 0: end = len(self.childNodes) + end
        if (end <= start): raise IndexError("index range out of order.")
        for i in range(start, end):
            if self.childNodes[i]._isOfValue(x): return i
        raise ValueError("'%s' not found in %s '%s' [%d:%d]."
            % (x, self.nodeType, self.nodeName, start, end))

    def append(self, newChild:'Node') -> None:
        self.insert(len(self), newChild)

    def insert(self, i:int, newChild:'Node') -> None:  # PlainNode
        """Note: Argument order is different that (say) insertBefore.
        """
        if not isinstance(newChild, Node):
            raise HReqE(f"newChild is  bad type {type(newChild).__name__}.")
        if newChild.parentNode is not None:
            raise HReqE("newChild already has parent (type %s)"
                % (newChild.parentNode.nodeType))
        if not isinstance(newChild, Node) or newChild.isAttribute:
            raise HReqE(f"Only insert Nodes, not {type(newChild)}")
        newChild.ownerDocument = self.ownerDocument
        if newChild.isElement: self._filterOldInheritedNS(newChild)
        if i < 0: i = len(self) + i
        #if i >= len(self): self.appendChild(newChild)  # ?
        else: super().insert(i, newChild)
        newChild.parentNode = self

    def _filterOldInheritedNS(self, newChild:'Element') -> None:
        """If we're about to insert 'other', it may have inheritedNS left
        from when it was cut. We didn't filter them then, since many
        removed nodes will just be discarded. But if we insert, any
        prefixes that the subtree actually uses have to get defined.

        We could search, but for the newChild to have been ok before,
        everything it needs to inherit should already be there in its
        .inheritedNS. So we just copy any of those that aren't in the
        context already. BUT, that could propagate unneeded ones. So
        we don't propagate those directly -- we collect them by diffing,
        then if/while the list is not empty, we traverse and drop any
        that aren't actually referenced.

        This is probably the goriest semantics of the whole thing.

        # TODO: Finish the search/copy code.
        """
        if not newChild.inheritedNS:  # Doesn't need any
            return
        tempNS = newChild.inheritedNS
        newChild.inheritedNS = self.inheritedNS.copy()
        extrasFromPriorContext = set(tempNS.keys()) - newChild.inheritedNS.keys()
        if len(extrasFromPriorContext) == 0:
            return
        for k, v in tempNS.items():
            if k in newChild.inheritedNS: continue
            if newChild.declaredNS and k in newChild.declaredNS: continue
            if newChild.declaredNS is None: newChild.declaredNS = {}
            newChild.declaredNS[k] = v

    def clear(self) -> None:
        raise HReqE("Can't clear() abstract Node.")

    # "del" can't just do a plain delete, 'cuz unlink. TODO: Enable del
    #def __delitem__(self, i:int) -> None:
    #    self.removeChild(self.childNodes[i])
    #    for other in others:
    #        self.appendChild(other)

    def pop(self, i:int=-1) -> 'Node':
        try:
            toDel = self.childNodes[i]
            return self.removeChild(toDel)
        except IndexError as e:
            raise NotFoundError from e

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
        if self.childNodes is not None:
            for cnum in reversed(range(len(self.childNodes))):
                revCh.append(self.childNodes[cnum])
        return revCh

    def sort(self, key:Callable=None, reverse:bool=False) -> None:
        if not self.childNodes: return
        origLen = len(self.childNodes)
        nl = NodeList()
        while len(self.childNodes) > 0:
            ch = self.removeChild(0)
            nl.append(ch)
        assert len(nl) == origLen
        sortedCh = sorted(nl, key=key, reverse=reverse)
        assert len(sortedCh) == origLen
        for ch in nl: self.appendChild(ch)
        assert len(self) == origLen

    def _isOfValue(self, value:Any) -> bool:
        """Used by count, index, remove to pick node(s) to work on.
        What *should* the test be? Going with nodeName for now.
        """
        if value is None: return True
        if callable(value): return value(self)
        if value == "*" and self.nodeType == NodeType.ELEMENT_NODE: return True
        if value == self.nodeName: return True
        return False

    # You can't put the identical element into a parent twice.
    # Though you *can* do that with NodeList.
    # So what should __add__, __mul__, etc. do? We clone.
    # If we allowed entity reference, transclusion, etc., though?
    #
    def __mul__(self, x:int) -> 'NodeList':  # PlainNode
        """Well, I guess for completeness...
        """
        if not isinstance(x, int): raise TypeError(
            f"Can't multiply sequence by non-int of type '{type(x)}'")
        newNL = NodeList()
        if x > 0:
            nch = len(self)
            for _ in range(x):
                for cnum in range(nch):
                    self.appendChild(self[cnum].cloneNode(deep=False))
        return newNL

    def __imul__(self, x) -> 'NodeList':
        if not isinstance(x, int): raise TypeError(
            f"Can't multiply sequence by non-int of type '{type(x)}'")
        if x <= 0:
            self.clear()
        else:
            nch = len(self)
            for _ in range(x-1):
                for cnum in range(nch):
                    self.appendChild(self[cnum].cloneNode(deep=False))
        return self

    def __rmul__(self, x) -> 'NodeList':
        return self.__mul__(x)

    def __add__(self, other) -> 'NodeList':
        """add does not add in place -- it constructs a new NodeList. cf iadd.
        """
        newNL = NodeList()
        newNL.extend(self)
        newNL.extend(other)
        return newNL

    def __iadd__(self, other) -> 'NodeList':
        for ch in other:
            if ch.parentNode: ch = ch.cloneNode(deep=True)  # TODO???
            self.appendChild(ch)
        return self

    def getInterface(self) -> None:
        raise NSuppE("getInterface: obsolete.")

    def isSupported(self) -> None:
        raise NSuppE("isSupported: obsolete.")

    ### Meta (PlainNode)

    def unlink(self, keepAttributes:bool=False) -> None:  # MINIDOM
        """Break all internal references in the subtree, to help gc.
        Has to delete attributes, b/c they have ownerElement, ownerDocument.
        But with keepAttributes=True, it will unlink them instead.
        ELement overrides this to unlink attrs and childNodes, too.
        """
        self.ownerDocument    = None
        self.parentNode       = None


###############################################################################
#
class Node(PlainNode):
    # whatwgAdditions, EtAdditions, OtherAdditions,
    #CssSelectors,
    #__slots__ = ("nodeType", "nodeName", "ownerDocument", "parentNode")

    NONE                        = NodeType.NONE
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

    def bool(self) -> bool:
        """A node can be empty but still meaningful (think hr or br in HTML).
        That is not like 0, [], or {}, and so we want it to test True.

        In so far as one denies what is, one is possessed by what is not,
        the compulsions, the fantasies, the terrors that flock to fill the void.
                                                -- Ursula Le Guin
        """
        if isinstance(self, (Element, Document, Node)): return True
        if isinstance(self, CharacterData): return bool(self.data)
        if isinstance(self, Attr): return bool(self.value)

    @property
    def length(self) -> int:
        return len(self)

    def __contains__(self, item:'Node') -> bool:
        """Careful, the Python built-in "contins"/"in" is wrong for node
        containment, because all empty lists are considered equal.
        Thus an element with any empty node "contains" *all* empty nodes.
        """
        return item.parentNode == self

    # There is no ordering for nodes except document ordering, so I'm using
    # it for all the comparison operators.
    #
    def __eq__(self, other:'Node') -> bool:  # Node
        """Two different nodes cannot be in the same place, nor the same node
        in two different places, so eq/ne are same for order vs. identity.
        """
        return self is other

    def __ne__(self, other:'Node') -> bool:
        return self is not other

    def __lt__(self, other:'Node') -> bool:
        assert self.ownerDocument == other.ownerDocument  # TODO
        return self.compareDocumentPosition(other) < 0

    def __le__(self, other:'Node') -> bool:
        assert self.ownerDocument == other.ownerDocument
        return self.compareDocumentPosition(other) <= 0

    def __ge__(self, other:'Node') -> bool:
        assert self.ownerDocument == other.ownerDocument
        return self.compareDocumentPosition(other) >= 0

    def __gt__(self, other:'Node') -> bool:
        assert self.ownerDocument == other.ownerDocument
        return self.compareDocumentPosition(other) > 0

    # Overload [] to be more useful.
    def NOTYET__getitem__(self, key: Union[int, slice, str]) -> Union[List, 'Node']:  # HERE/PY
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
            raise NSuppE("[] not hooked up yet")
        else:
            raise IndexError("Unexpected [] arg type: %s" % (type(key)))

    @property
    def depth(self) -> int:
        """How deeply nested are we in the tree?
        """
        d = 0
        cur = self.ownerElement if self.isAttribute else self
        while (cur is not None):
            d += 1
            cur = cur.parentNode
        return d

    @property
    def previous(self) -> 'Node':  # XPATH
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
    def next(self) -> 'Node':  # XPATH
        if self.childNodes: return self.childNodes[0]
        cur = self
        while (cur.parentNode is not None):
            if not cur.isLastChild: return cur.nextSibling
            cur = cur.parentNode
        return None

    def nodeNameMatches(self, other) -> bool:  # HERE
        """Factor this out b/c with namespaces there can be a match even
        if the prefixes don't match, because they could map to the same URI!.
        Apparently when you disconnect a node, you're supposed to keep all
        relevant namespaces with it
        TODO: Is this where to add case-ignoring?
        """
        if self.localName != other.localName: return False
        if self.parentNode is None or other.parentNode is None: return True
        if self.namespaceURI == ANY_NS or other.namespaceURI == ANY_NS: return True
        if self.namespaceURI != other.namespaceURI: return False
        return True

    @property
    def textContent(self) -> str:  # Node
        raise NSuppE(
            f"Cannot set textContent on Node of type {self.nodeType}.")

    @textContent.setter
    def textContent(self, newData:str) -> None:  # Node
        raise NSuppE(
            f"Cannot set textContent on Node of type {self.nodeType}.")

    def compareDocumentPosition(self, other:'Node') -> int:
        """Returns -1, 0, or 1 to reflect relative document order.
        Two different nodes cannot be in the same places, nor the same node
        in two different places (like, say, electrons). Therefore, for
        equality it's enough to test identity instead of position.

        XPointers are good for this, except that getChildIndex() is O(fanout).

        Does not apply to Attribute nodes (overridden).
        """
        self.checkNode()
        other.checkNode()
        if self.ownerDocument != other.ownerDocument:
            raise HReqE("No common document for compareDocumentPosition")
        if self.parentNode is None:
            raise HReqE("self Node is not connected.")
        if other.parentNode is None:
            raise HReqE("other Node is not connected.")

        if self is other: return 0  # Could do this even in failure cases above

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

    def getRootNode(self) -> 'Node':  # WHATWG
        """This seems mainly useful for HTML shadow stuff.
        """
        return self.ownerDocument

    def hasAttributes(self) -> bool:  # Not a property.
        return (self.attributes is not None and len(self.attributes) > 0)

    def isDefaultNamespace(self, uri:str) -> bool:  # DOM 3
        return self.lookupNamespaceURI("") == uri

    def lookupNamespaceURI(self, prefix:NMTOKEN_t) -> str:
        """This assumes we accumulate inheritedNS down the tree.
        Each node gets at least a pointer to its parent's one (copy on change).
        It gets set/cleared at the same times as parentNode, b/c inheritance.
        Non-elements can't declare any ns, so don't get a dict.
        """
        if (self.isFragment
            or self.isDocumentType
            or (self.isDocument and len(self) == 0)
            or (self.isAttribute and self.ownerElement is None)): return None
        if prefix == "xml": return "http://www.w3.org/XML/1998/namespace"
        if prefix == "xmlns": return "http://www.w3.org/2000/xmlns/"
        bearer = self if self.isElement else self.parent
        if not prefix: prefix = ""
        if bearer.inheritedNS and prefix in bearer.inheritedNS:
            return bearer.inheritedNS[prefix]
        return ""

    def lookupPrefix(self, uri:str) -> str:
        if self.inheritedNS is None: return None
        for k, v in self.inheritedNS.items():
            if v == uri: return k
        return None

    #### Mutators (Node) CharacterData hides all these)

    def prependChild(self, newChild:'Node') -> None:  # HERE
        assert newChild.parentNode is None
        self.childNodes.insert(0, newChild)

    @property
    def hasChildNodes(self) -> bool:
        """Rreturns False for either None or [] (Nodes are lists).
        """
        return bool(self.childNodes)

    def removeNode(self) -> 'Node':
        """Remove the node itself from its parentNode, unlinking as needed.
        Not sure; should the subtree be left intact, or not?
        """
        if self.parentNode is None:
            raise HReqE("No parent in removeNode.")
        return self.parentNode.removeChild(self)

    def replaceChild(self, newChild:'Node', oldChild:Union['Node', int]) -> None:
        if newChild.parentNode is not None:
            hint = " Swapped arguments?" if oldChild.parent is None else ""
            raise HReqE("New child for replaceChild already has parent." + hint)
        oNum, oChild = self._expandChildArg(oldChild)
        self.removeChild(oChild)
        self.childNodes.insert(oNum, newChild)


    #######################################################################
    # Extras for Node
    #
    def getUserData(self, key:str) -> Any:
        if not self.userData: return None
        return self.userData[key][0]

    def setUserData(self, key:NMTOKEN_t, data:Any, handler:Callable=None) -> None:
        if self.userData is None: self.userData = {}
        self.userData[key] = (data, handler)


    # Shorter checking for node types:  # HERE
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
    isTextNode = isText
    @property
    def isCDATA(self) -> bool:
        return self.nodeType == NodeType.CDATA_SECTION_NODE
    @property
    def isEntRef(self) -> bool:
        return self.nodeType == NodeType.ENTITY_REFERENCE_NODE
    isEntityReference = isEntRef
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
        and (not self.data or self.data.isspace()))  # TOTO WSDefs
    @property
    def isWhitespaceInElementContent(self) -> bool:
        return (self.nodeType == NodeType.TEXT_NODE
        and (not self.data or self.data.isspace())  # TOTO WSDefs
        and self.parent.hasSubElements)

    # TODO isEmpty?

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
    def leftmost(self) -> 'Node':  # HERE
        """Deepest descendant along left branch of subtree  (never self).
        """
        if not self.childNodes: return None
        cur = self
        while (cur.childNodes): cur = cur.childNodes[0]
        return cur

    @property
    def rightmost(self) -> 'Node':  # HERE
        """Deepest descendant along right branch of subtree (never self).
        """
        if not self.childNodes: return None
        cur = self
        while (cur.childNodes): cur = cur.childNodes[-1]
        return cur

    def changeOwnerDocument(self, otherDocument:'Document') -> None:
        """Move a subtree to another document. This requires deleting it, too.
        """
        if self.ownerDocument is not None: self.removeNode()
        #self.unlink(keepAttributes=True)
        for node in self.eachNode(includeAttributes=True):
            node.ownerDocument = otherDocument

    # Serialization (Node)
    #
    @property
    def outerXML(self) -> str:  # Node  # HTML
        return self.toxml()

    @outerXML.setter
    def outerXML(self, xml:str) -> None:  # Node  # HTML
        raise NSuppE(f"No outerXML setter on {self.nodeType}.")

    def collectAllXml(self) -> str:  # Node
        return self.toxml()

    def __reduce__(self) -> str:  # Node
        return self.toxml()

    def __reduce__ex__(self) -> str:  # Node
        return self.__reduce__()

    def tostring(self) -> str:  # Node
        return self.toxml()

    def toxml(self, indent:str="", newl:str="", encoding:str="utf-8") -> str:  # Node
        return self.toprettyxml( indent=indent, newl=newl,encoding=encoding)

    def tocanonicalxml(self) -> str:  # HERE
        return self.toprettyxml(FormatOptions.canonical())

    def toprettyxml(self, foptions:FormatOptions=None, **kwargs) -> str:  # Node
        raise NSuppE(f"No toprettyxml on Node (from {self.nodeType}).")

    def outerJSON(self, indent:str="  ", depth:int=0) -> str:  # Node  # HERE
        """Convert a subtree to isomorphic JSON.
        Intended to be idempotently round-trippable.
        Defined in each subclass.
       """
        raise NSuppE("outerJSON called on abstract Node.")


    #######################################################################
    # Paths, pointers, etc. (Node)
    #
    def getNodePath(self, useId:str=None, attrOk:bool=False) -> str:  # XPTR
        steps = self.getNodeSteps(useId=useId)
        if not steps: return None
        return "/".join([ str(step) for step in steps ])

    def getNodeSteps(self, useId:bool=False, attrOk:bool=False, wsn:bool=True) -> List:  # XPTR
        """Get the child-numer path to the node, as a list.
        At option, start it at the nearest ID (given an attr name for ids).
        Attributes yield the ownerElement unless 'attrOk' is set.
        TODO: Option to skip counting wsn?
        """
        if self.nodeType == NodeType.NONE:
            raise NSuppE("No paths to abstract Nodes.")
        cur = self
        f = []
        if self.isAttribute:
            if attrOk: f.insert(0, f"@{self.name}")
            cur = self.ownerElement
        while (cur is not None):
            if useId:
                anode = self.idHandler.getIdAttrNode(cur)
                if (anode):
                    f.insert(0, anode.value)
                    break
            if cur.parentNode is None:
                f.insert(0, "1")
            elif wsn:
                f.insert(0, cur.getChildIndex() + 1)
            else:
                raise NSuppE("Counting without wsn not yet supported.")
            cur = cur.parentNode
        return f

    def useNodePath(self, npath:str) -> 'Node':  # XPTR
        steps = npath.split(r'/')
        if steps[0] == "": del steps[0]
        return self.useNodeSteps(steps)

    def useNodeSteps(self, steps:List) -> 'Node':  # XPTR
        document = self if self.isDocument else self.ownerDocument
        try:
            cnum = int(steps[0])
            node = document.documentElement
            startAt = 0
        except ValueError as e:
            node = document.getElementById(steps[0])
            if node is None:
                raise HReqE("Leading id '%s' of path not found." % (steps[0])) from e
            startAt = 1

        for i in range(startAt, len(steps)):
            # TODO support @aname?
            try:
                cnum = int(steps[i])
            except ValueError as e:
                raise HReqE("Non-integer in path: %s" % (steps)) from e
            if node.nodeType not in [ Node.ELEMENT_NODE, Node.DOCUMENT_NODE ]:
                raise HReqE("Node path step %d from non-node (%s) in: %s"
                    % (i, type(node), steps))
            nChildren = len(node.childNodes)
            if cnum<=0 or cnum>nChildren:
                raise HReqE("Node path step %d to #%d out of range (%d) in: %s."
                    % (i, cnum, nChildren, steps))
            node = node.childNodes[cnum-1]
        return node


    ###########################################################################
    # Multi-item sibling insertions (whence was this?
    #
    def before(self, stuff:List) -> None:  # WHATWG
        par = self.parentNode
        beforeNum = self.getChildIndex()
        for i, s in enumerate(stuff):
            if isinstance(s, str):
                s = self.ownerDocument.createTextNode(s)
            par.insertBefore(s, beforeNum+i)  # Faster using int option

    def after(self, stuff:List) -> None:  # WHATWG
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

    def eachChild(self:'Node', excludeNodeNames:List=None) -> 'Node':
        if isinstance(excludeNodeNames, str):  # HERE
            excludeNodeNames = excludeNodeNames.split()
        if self.childNodes is None: return None
        for ch in self.childNodes:
            if self.nodeName in excludeNodeNames: continue
            if "#" in excludeNodeNames and not self.isElement: return
            yield ch
        return None

    def eachNode(self:'Node', includeAttributes:bool=False,
        excludeNodeNames:List=None) -> 'Node':  # HERE
        """Generate all descendant nodes in document order.
        Don't include attribute nodes unless asked.
        @param exclude: Filter out any nodes whose names are in the list
        (their entire subtrees are skipped). #text, #cdata, #pi, "#".
        """
        if isinstance(excludeNodeNames, str):
            excludeNodeNames = excludeNodeNames.split()
        if excludeNodeNames:
            if self.nodeName in excludeNodeNames: return
            if "#" in excludeNodeNames and not self.isElement: return
            if ("#wsn" in excludeNodeNames and self.nodeName==RWord.NN_TEXT
                and self.data.strip()==""): return

        yield self
        if self.isElement and includeAttributes and self.attributes:
            for anode in self.attributes.values(): yield anode

        if self.childNodes is not None:
            for ch in self.childNodes:
                for chEvent in ch.eachNode(
                    includeAttributes=includeAttributes,
                    excludeNodeNames=excludeNodeNames):
                    yield chEvent
        return

    def eachSaxEvent(self:'Node', separateAttributes:bool=False,
        excludeNodeNames:List=None) -> 'Node':  # HERE
        """Generate a series of SAX events as if subtree were being parsed.
        """
        if isinstance(excludeNodeNames, str):
            excludeNodeNames = excludeNodeNames.split()

        yield (SaxEvents.INIT, )
        for se in self.eachSaxEvent_R(separateAttributes, excludeNodeNames):
            yield se
        yield (SaxEvents.FINAL, )
        return

    def eachSaxEvent_R(self:'Node', separateAttributes:bool=False,
        excludeNodeNames:List=None) -> Tuple:  # HERE
        if excludeNodeNames:
            if self.nodeName in excludeNodeNames: return
            if "#" in excludeNodeNames and not self.isElement: return
            if ("#wsn" in excludeNodeNames and self.nodeName==RWord.NN_TEXT
                and self.data.strip()==""): return

        # TODO Add entref, doctype, etc?

        if self.nodeType == Node.TEXT_NODE:
            yield (SaxEvents.CHAR, self.data)
        elif self.nodeType == Node.COMMENT_NODE:
            yield (SaxEvents.COMMENT, self.data)
        elif self.nodeType == Node.CDATA_NODE:
            yield (SaxEvents.CDATASTART, )
            yield (SaxEvents.CHAR, self.data)
            yield (SaxEvents.CDATAEND, )
        elif self.nodeType == Node.PROCESSING_INSTRUCTION_NODE:
            yield (SaxEvents.PROC, self.target, self.data)
        elif self.nodeType == Node.ELEMENT_NODE:
            if separateAttributes:
                yield (SaxEvents.START, self.nodeName)
                for k in self.attributes:
                    yield (SaxEvents.ATTRIBUTE, k, self.getAttribute[k])
                if self.declaredNS:
                    for k in self.declaredNS:
                        yield (SaxEvents.ATTRIBUTE,
                            RWord.NS_PREFIX+k, self.getAttribute[k])
            else:
                vals = [ SaxEvents.START, self.nodeName ]
                for k in self.attributes:
                    vals.append(k)
                    vals.append(self.getAttribute[k])
                if self.declaredNS:
                    for k in self.declaredNS:
                        vals.append(RWord.NS_PREFIX+k)
                        vals.append(self.getAttribute[k])
                yield tuple(vals)

            if self.childNodes is not None:
                for ch in self.childNodes:
                    for chEvent in ch.eachSaxEvent_R(
                        separateAttributes, excludeNodeNames):
                        yield chEvent
            yield (SaxEvents.END, self.nodeName)
        return

    ### Meta (Node)

    def unlink(self, keepAttributes:bool=False) -> None:  # MINIDOM
        """Break all internal references in the subtree, to help gc.
        Has to delete attributes, b/c they have ownerElement, ownerDocument.
        But with keepAttributes=True, it will unlink them instead.
        ELement overrides this to unlink attrs and childNodes, too.
        """
        super().unlink()
        self.userData = None
        return

    def checkNode(self, deep:bool=True) -> None:  # Node  # DBG
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
        if self.childNodes is not None and len(self.childNodes) > 0:
            assert isinstance(self, (Element, Node, Document)), (
                f"{self.__class__} has children.")
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
    def __init__(
        self,
        namespaceUri:str=None,
        qualifiedName:NMTOKEN_t=None,
        doctype:'DocumentType'=None,
        isFragment:bool=False
        ):
        super().__init__(ownerDocument=None, nodeName="#document")

        self.nodeType           = Node.DOCUMENT_NODE
        self.nodeName           = "#document"
        #self.namespaceUri      = namespaceUri
        self.inheritedNS  = { }
        if namespaceUri:
            self.inheritedNS[""] = namespaceUri
        self.doctype            = doctype
        self.documentElement    = None
        if qualifiedName:
            if not XStr.isXmlQName(qualifiedName):
                raise ICharE(
                    "Document: qname '%s' isn't." % (qualifiedName))
            root = self.createElement(tagName=qualifiedName)
            self.appendChild(root)
            self.documentElement = root

        self.encoding           = 'utf-8'
        self.version            = None
        self.standalone         = None

        self.impl               = 'BaseDOM'
        self.implVersion        = __version__
        self.options            = self.initOptions()
        self.idHandler          = IdHandler(self)  # Lazy build
        self.loadedFrom         = None
        self.uri                = None
        self.mimeType           = 'text/XML'

    def clear(self) -> None:
        raise NSuppE("No clear() on Document nodes.")

    def insert(self, i:int, newChild:'Element') -> None:  # Document
        if len(self.childNodes) > 0:
            raise HReqE("Can't insert child to non-empty Document.")
        if not newChild.isElement:
            raise HReqE(
                f"document element must not be a {newChild.nodeType.__name__}.")
        super().insert(i, newChild)
        self.documentElement = newChild

    def initOptions(self) -> SimpleNamespace:  # HERE
        return SimpleNamespace(**{
            "parser":           "lxml",

            "IdCase":           "NONE",
            "ElementCase":      "NONE",
            "AttributeCase":    "NONE",
            "EntityCase":       "NONE",
            # TODO Also UNorm, wsDef
            #
            "attributeTypes":   False,
            "ws_nodes":         True,
            #
            "nodeType_p":       True,
            "getItem":          True,
            "cssSelectors":     False,
            "XPathSelectors":   False,
            "IdNameSpaces":     False,
            #
            "json-x":           True,
            "xmlProperties":    True,
            "whatwgExceptions": True,

            "ns_global":        False,
            "ns_redef":         True,
            "ns_attr_def":      False,
            "ns_never":         False,
        })

    @property
    def textContent(self) -> str:  # Document
        if self.documentElement is None: return ""
        return self.documentElement.textContent()

    @textContent.setter
    def textContent(self, newData:str) -> None:  # Document
        return None

    @property
    def charset(self) -> str:
        return self.encoding
    @property
    def inputEncoding(self) -> str:
        return self.encoding
    @property
    def contentType(self) -> str:
        return self.mimeType
    @property
    def documentURI(self) -> str:
        return self.uri
    @property
    def domConfig(self) -> None:
        raise NSuppE("Document.domConfig")

    def createElement(self,
        tagName:NMTOKEN_t,
        attributes:Dict=None,   # HERE
        parent:Node=None,
        text:str=None           # HERE
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

    def createAttribute(self, name:NMTOKEN_t, value=None, parentNode=None) -> 'Attr':
        if parentNode is not None: assert parentNode.iSElement
        return Attr(name, value, ownerDocument=self,
            nsPrefix=None, namespaceURI=None, ownerElement=parentNode)

    def createTextNode(self, data:str) -> 'Text':
        return Text(ownerDocument=self, data=data)

    def createComment(self, data:str) -> 'Comment':
        return Comment(ownerDocument=self, data=data)

    def createCDATASection(self, data:str) -> 'CDATASection':
        return CDATASection(ownerDocument=self, data=data)

    def createProcessingInstruction(self, target:NMTOKEN_t, data:str
        ) -> 'ProcessingInstruction':
        return ProcessingInstruction(
            ownerDocument=self, target=target, data=data)

    def createEntityReference(self, name:NMTOKEN_t, value:str=None) -> 'EntityReference':
        """Instantiate it and fetch value either from arg or schema.
        These are not commonly supported. Most things should just treat them
        like text nodes or CDATA.
        """
        return EntityReference(ownerDocument=self, name=name)

    ####### EXTENSIONS (Document)

    # shorthand creation -- use the class constructors or these
    Attr = createAttribute  # WHATWG
    Text = createTextNode  # WHATWG
    Comment = createComment  # WHATWG
    CDATA = createCDATASection  # WHATWG
    PI = createProcessingInstruction   # WHATWG+HERE
    EntRef = createEntityReference  # WHATWG+HERE

    def writexml(self, writer, indent:str="", addindent:str="", newl:str="",
        encoding:str=None, standalone:bool=None) -> None:  # Document  # MINIDOM
        assert encoding in [ None, "utf-8" ]
        if encoding is None: encoding = "utf-8"
        writer.write(self.getXmlDcl(encoding, standalone))
        if self.documentElement:
            self.documentElement.writexml(indent, addindent, newl,
                encoding, standalone)

    def _getXmlDcl(self, encoding:str="utf-8", standalone:str=None) -> str:
        sa = ""
        if not standalone:
            if self.standalone in [ "yes", "no" ]:
                sa = f' standalone="{self.standalone}"'
        else:
            assert standalone in [ "yes", "no" ]
            sa = f' standalone="{standalone}"'
        return (f'<?xml version="1.0" encoding="{encoding}"{sa}?>\n')

    @property
    def xmlDcl(self) -> str:  # Document  # HERE
        return self._getXmlDcl(encoding=self.encoding)

    @property
    def docTypeDcl(self) -> str:  # Document  # HERE
        if self.doctype: return self.doctype.outerXml
        return f"<!DOCTYPE {self.documentElement.nodeName} []>"

    def toprettyxml(self, foptions:FormatOptions=None, **kwargs) -> str:  # Document
        if not foptions: foptions = FormatOptions(**kwargs)
        t = ""
        if foptions.includeXmlDcl: t += self.xmlDcl
        if foptions.includeDoctype: t += self.docTypeDcl
        if self.documentElement: t += self.documentElement.toprettyxml(foptions)
        return t + foptions.newl

    def outerJSON(self, indent:str="  ", depth:int=0) -> str:  # Document  # HERE
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

    def _buildIndex(self, enames:List=None, aname:NMTOKEN_t=None) -> Dict:
        """Build an index of all values of the given named attribute
        on the given element name(s). If ename is empty, all elements.
        """
        assert XStr.isXmlQName(aname)
        theIndex = {}
        for node in self.documentElement.eachNode(excludeNodeNames="#"):
            if enames and node.nodeName not in enames: continue
            value = node.getAttribute(aname)
            if value: theIndex[value] = node
        return theIndex

    def getElementById(self, idValue:str) -> Node:  # HTML
        return self.idHandler.getIndexedId(idValue)

    def getElementsByTagName(self, name:str) -> Node:  # HTML
        return self.documentElement.getElementsByTagName(name)

    def getElementsByClassName(self, name:str, attrName:str="class") -> Node:  # HTML
        return self.documentElement.getElementsByClassName(name, attrName=attrName)

    def checkNode(self, deep:bool=True) -> None:  # Document  # DBG
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
    def __init__(self, ownerDocument=None, nodeName:NMTOKEN_t=None):
        super().__init__(ownerDocument, nodeName)
        self.nodeType:NodeType = NodeType.ELEMENT_NODE
        self.attributes:'NameNodeMap' = None
        self.inheritedNS:dict = None
        self.declaredNS:dict = None
        self.prevError:str = None  # Mainly for isEqualNode

    def _addNamespace(self, name:str, uri:str="") -> None:
        """Add the given ns def to this Element. Most elements just inherit,
        so they just get a ref to their parent's defs. But when one is added,
        a copy is created (even if the ns is already on the parent, b/c
        adding a ns explicitly is different than just inheriting).
        """
        prefix, _, local = name.partition(":")
        if not local:
            local = prefix; prefix = ""
        if prefix not in [ "", RWord.NS_PREFIX ]:
            raise ICharE(
                f"_addNamespace: Invalid prefix in '{name}' -> '{uri}'.")
        if not (local == "" or XStr.isXmlName(local)):
            raise ICharE(
                f"_addNamespace: Invalid local part in '{name}' -> '{uri}'.")

        if (self.parentNode and
            self.inheritedNS is self.parentNode.inheritedNS):
            self.inheritedNS = self.parentNode.inheritedNS.copy()
        if self.inheritedNS is None: self.inheritedNS = {}
        self.inheritedNS[local] = uri

    def cloneNode(self, deep:bool=False) -> 'Element':
        """NOTE: Default value for 'deep' has changed in spec and browsers!
         Don't copy the tree relationships.
         TODO: Move nodeType cases to the subclasses.
        """
        newNode = Element(ownerDocument=self.ownerDocument, nodeName=self.nodeName)
        if self.declaredNS:
            newNode.declaredNS = self.declaredNS.copy()
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

    def clear(self) -> None:
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
    def tagName(self) -> NMTOKEN_t: return self.nodeName
    @property
    def prefix(self) -> str:
        return XStr.getPrefixPart(self.nodeName)
    @property
    def localName(self) -> str:
        return XStr.getLocalPart(self.nodeName)
    @property
    def namespaceURI(self) -> str:
        """Map the nodeName's prefix to its URI.
        If it is not in scope, return None.
        """
        cur = self
        while (cur is not None):
            if cur.prefix:
                try:
                    return self.inheritedNS[cur.prefix]
                except (TypeError, ValueError, KeyError):
                    pass
            cur = cur.parentNode
        return None

    @property
    def textContent(self) -> None:  # Element
        """Cat together all descendant text nodes.
        See https://kellegous.com/j/2013/02/27/innertext-vs-textcontent/
        (I have not done innerText because it involves layout).
        """
        textBuf = ""
        if self.childNodes is not None:
            for ch in self.childNodes:
                textBuf += ch.textContent
        return textBuf

    @textContent.setter
    def textContent(self, newData:str) -> None:  # Element
        while (len(self) > 0): self.removeChild(-1)
        tn = self.ownerDocument.createTextNode(newData)
        self.appendChild(tn)

    def isEqualNode(self, n2) -> bool:  # Element
        """To help with debugging, versioning, etc. if the nodes differ
        we stash the reason/location in self.
        """
        #if path is None: path = [ 1 ]
        _dtrace(f"isEqualNode for name {self.nodeName} vs. {n2.nodeName}")
        #import pudb; pudb.set_trace()
        if self.isElement and n2.isElement:
            _dtrace(f"###{self.toxml()}###\n###{n2.toxml()}###")
        if not super().isEqualNode(n2):
            _dtrace("super tests found unequal.")
            return False
        #import pudb; pudb.set_trace()

        if len(self) != len(n2):
            _dtrace(f"len unequal ({len(self)} vs. {len(n2)}.")
            return False

        # Careful, OrderedDict eq would test order, which we don't want.
        # TODO Should actually resolve ns to compare.
        if not self.attributes and not n2.attributes:
            pass  # That's a match (even None vs. {})
        elif not self.attributes or not n2.attributes:
            _dtrace("Somebody's got no attributes.")
            return False
        elif len(self.attributes) != len(n2.attributes):
            _dtrace("unequal number of attrs.")
            return False
        else:
            for k in self.attributes:
                if self.getAttribute(k) != n2.getAttribute(k):
                    _dtrace("attr '%s' differs: '%s' vs. '%s'."
                        % (k, self.getAttribute(k), n2.getAttribute(k)))
                    return False

        for i, ch in enumerate(self.childNodes):
            if not ch.isEqualNode(n2.childNodes[i]):
                _dtrace(f"({ch.nodeName}) unequal.")
                return False
        return True


    ###########################################################################
    # Manage attributes. They are a Dict (or None), keyed by nodeName.
    # The value is the whole Attr instance.

    ### Attribute plain
    #
    def _findAttr(self, ns:str, aname:str) -> 'Attr':
        """All(?) attribute stuff goes through here.
        """
        if not aname or not XStr.isXmlQName(aname):
            raise ICharE(f"Attr name '{aname}' not an XML QName.")
        if not self.attributes: return None
        if aname in self.attributes: # If total match, we're ok. (?)
            return self.attributes[aname]
        tgtLocalName = aname.partition(":")[2] or aname
        for _k, anode in self.attributes.items():
            if anode.localName != tgtLocalName: continue
            if not ns or ns == ANY_NS: return anode
            if anode.namespaceURI == ns: return anode
        return None

    def _presetAttr(self, aname:str, avalue:str) -> None:
        """Common precursor for all methods that add/set attributes.
        """
        if not XStr.isXmlQName(aname):
            raise ICharE(f"Attr name '{aname}' not an XML QName.")
        if self.attributes is None:
            self.attributes = NamedNodeMap(
                ownerDocument=self.ownerDocument, parentNode=self)
        if aname.startswith(RWord.NS_PREFIX+":"):
            self._addNamespace(aname, avalue)
        # TODO UPdate IdHandler

    def hasAttribute(self, aname:NMTOKEN_t) -> bool:
        return self._findAttr(ns=None, aname=aname) is not None

    def setAttribute(self, aname:NMTOKEN_t, avalue:Any) -> None:
        self._presetAttr(aname, avalue)
        self.attributes.setNamedItem(aname, avalue)

    def getAttribute(self, aname:NMTOKEN_t, castAs:type=str, default:Any=None) -> str:
        """Normal getAttribute, but can cast and default for caller.
        """
        anode = self._findAttr(ns=None, aname=aname)
        if anode is None: return default
        if castAs: return castAs(anode.value)
        return anode.value

    def removeAttribute(self, aname:NMTOKEN_t) -> None:
        """Silent no-op if not present.
        """
        #if aname.startswith(RWord.NS_PREFIX+":"):
        #    raise NSuppE("Not a good idea to remove a Namespace attr.")
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
        if old is not None: old.parentNode = None
        return old

    def getAttributeNode(self, aname:NMTOKEN_t) -> 'Attr':
        if not isinstance(aname, str):
            raise HReqE(f"getAttributeNode() take a name, not a {type(aname)}.")
        return self._findAttr(ns=None, aname=aname)

    def removeAttributeNode(self, anode:'Attr') -> 'Attr':
        """Unlike removeAttribute and NS, this *can* raise an exception.
        """
        assert isinstance(anode, Attr)
        #if anode.nodeName.startswith(RWord.NS_PREFIX):
        #    raise NSuppE("Not a good idea to remove a Namespace attr.")
        old = self._findAttr(ns=None, aname=anode.nodeName)
        if old is None: return None
        if old is not anode:
            raise NotFoundError(
                f"Node has attribute matching {anode.nodeName}, but not the one passed.")
        anode.parentNode = None
        del self.attributes[anode.nodeName]

    ### Attribute NS
    #
    def hasAttributeNS(self, ns:str, aname:NMTOKEN_t) -> bool:
        assert XStr.isXmlName(aname)
        return self.hasAttribute(aname)

    def setAttributeNS(self, ns:str, aname:NMTOKEN_t, avalue:str) -> None:
        self._presetAttr(aname, avalue)
        attrNode = Attr(aname, avalue, ownerDocument=self.ownerDocument,
            nsPrefix=ns, namespaceURI=None, ownerElement=self)
        self.attributes.setNamedItem(attrNode)
        if ns == RWord.NS_PREFIX:
            attrNode2 = Attr(aname[len(RWord.NS_PREFIX)+1:], avalue,
                ownerDocument=self.ownerDocument,
                nsPrefix=ns, namespaceURI=None, ownerElement=self)
            self.inheritedNS.setNamedItem(attrNode2)

    def getAttributeNS(self, ns:str, aname:NMTOKEN_t, castAs:type=str, default:Any=None) -> str:
    # TODO Check/fix getAttributeNS
        assert not ns or ns == ANY_NS or NameSpaces.isNamespaceURI(ns)
        return self.getAttribute(aname, castAs, default)

    def removeAttributeNS(self, ns, aname:NMTOKEN_t) -> None:
        #if aname.startswith(RWord.NS_PREFIX):
        #    raise NSuppE("Not a good idea to remove a Namespace attr.")
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
        if old is not None: old.parentNode = None
        return old

    def getAttributeNodeNS(self, ns:str, aname:NMTOKEN_t) -> 'Attr':
        assert NameSpaces.isNamespaceURI(ns)
        return self._findAttr(ns=ns, aname=aname)

    ### Attribute extensions
    #
    def getInheritedAttribute(self:Node, aname:NMTOKEN_t, default:Any=None) -> str:  # HERE
        """Search upward to find the attribute.
        Return the first one found, otherwise the default (like xml:lang).
        """
        cur = self
        while (cur is not None):
            if cur.hasAttribute(aname): return cur.getAttribute(aname)
            cur = cur.parentNode
        return default

    def getInheritedAttributeNS(self:Node, ns:str, aname:NMTOKEN_t, default:Any=None) -> 'Attr':  # HERE
        assert NameSpaces.isNamespaceURI(ns)
        return self.getInheritedAttribute(aname, default)

    def getStackedAttribute(self:Node, aname:NMTOKEN_t, sep:str="/") -> str:  # HERE
        """Accumulate the attribute across self and all ancestors.
        Assumes the same name; uses "" if not present.
        """
        docEl = self.ownerDocument.documentElement
        vals = []
        cur = self
        while (cur is not None and cur is not docEl):
            vals.insert(0, cur.getAttribute(aname) or "")
            cur = cur.parentNode
        return sep.join(vals)


    ###########################################################################
    ####### Element: Descendant Selectors
    #
    def getElementById(self, IdValue:str) -> 'Element':  # DOM 2
        """TODO For HTML these should be case-insensitive. Elsewhere,
        """
        od = self.ownerDocument
        if od.idHandler is None:
            caseH = CaseHandler(od.options.IdCase)
            od.idHandler = IdHandler(od, caseHandler=caseH)
            lg.info("\n##### Built id index, %d entries.", len(od.idHandler.theIndex))
        return od.getElementById(IdValue)

    def getElementsByClassName(self, name:str, attrName:str="class", nodeList=None) -> List:
        """Works even if it's just one of multiple class tokens.
        """
        if nodeList is None: nodeList = []
        if self.nodeType != Node.ELEMENT_NODE: return nodeList
        if self.hasAttribute(attrName) and name in self.getAttribute(attrName).split():
            nodeList.append(self)
        for ch in self.childNodes:
            ch.getElementsByClassName(name, attrName=attrName, nodeList=nodeList)
        return nodeList

    def getElementsByTagName(self, tagName:NMTOKEN_t, nodeList:NodeList=None) -> List:
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

    def getElementsByTagNameNS(self, tagName:NMTOKEN_t, namespaceURI:str, nodeList=None) -> List:
        """This is on minidom.Element.
        """
        if not XStr.isXmlQName(tagName):
            raise ICharE("Bad attribute name '%s'." % (tagName))
        if nodeList is None: nodeList = []
        if self.nodeType != Node.ELEMENT_NODE: return nodeList
        if NameSpaces.nameMatch(self, tagName, ns=namespaceURI):
            nodeList.append(self)
        for ch in self.childNodes:
            if ch.isElement:
                ch.getElementsByTagNameNS(tagName, nodeList, namespaceURI)
        return nodeList


    ###########################################################################
    ####### (de)serializers (Element)
    #
    def insertAdjacentXML(self, position:RelPosition, xml:str) -> None:  # WHATWG
        """TODO: Can you do this (for positions inside) on the document element,
        or outside on CharacterData?)
        """
        assert self.isElement
        if isinstance(position, str): position = RelPosition[position]
        if not isinstance(position, RelPosition):
            raise SyntaxError(f"Unknown position argument {position}.")
        newDoc = self._string2doc(xml)
        par = self.parentNode
        if position == RelPosition.beforebegin:
            insertAt = self.getChildIndex()
            while len(newDoc.childNodes) > 0:
                moving = newDoc.removeChild(0)
                par.insert(insertAt, moving)
                insertAt += 1
        elif position == RelPosition.afterbegin:
            while len(newDoc.childNodes) > 0:
                moving = newDoc.removeChild(0)
                self.insert(0, moving)
        elif position == RelPosition.beforeend:
            while len(newDoc.childNodes) > 0:
                moving = newDoc.removeChild(0)
                self.appendChild(moving)
        elif position == RelPosition.afterend:
            insertAt = self.getChildIndex() + 1
            while len(newDoc.childNodes) > 0:
                moving = newDoc.removeChild(0)
                self.parentNode.insert(insertAt, moving)
                insertAt += 1
        else:
            raise HReqE(f"Unrecognized insert position {position}.")

    @property
    def outerXML(self) -> str:  # Element  # HTML
        return self.toxml()

    @outerXML.setter
    def outerXML(self, xml:str) -> None:  # Element  # HTML
        """To assign, we have to parse the XML first.
        TODO Remove the <wrapper> here and in innerXML.
        WAIT A SEC -- how we we delete ourself?
        """
        newDoc = self._string2doc(xml)
        theWrapper = newDoc.documentElement
        assert theWrapper.nodeName == "wrapper"
        #lg.warning("Parsed string yields: %s", theWrapper.toxml())

        par = self.parentNode
        while (len(theWrapper.childNodes) > 0):
            ch = theWrapper.childNodes[0]
            #lg.warning("Moving %s", ch.toxml())
            theWrapper.removeChild(ch)
            #ch.changeOwnerDocument(otherDocument=par.ownerDocument)
            par.insertBefore(newChild=ch, oldChild=self)
        newDoc.unlink()
        par.removeChild(self)
        #lg.warning("Deleted %s", self.toxml())

    @property
    def innerXML(self) -> str:  # Element  # HTML
        if not self.childNodes: return ""
        return "".join([ch.toxml() for ch in self.childNodes ])

    @innerXML.setter
    def innerXML(self, xml:str) -> None:  # Element  # HTML
        newDoc = self._string2doc(xml)
        theWrapper = newDoc.documentElement
        while (len(self.childNodes) > 0):
            self.removeChild(self.childNodes[0]).unlink()
        while (len(theWrapper.childNodes) > 0):
            ch = theWrapper.childNodes[0]
            theWrapper.removeChild(ch)
            ch.changeOwnerDocument(otherDocument=self.ownerDocument)
            self.appendChild(ch)
        newDoc.unlink()

    def _string2doc(self, xml:str) -> Document:
        """Put a wrapper (in case it's Text or some other non-element),
        and then parse. Used for inner/outerXML setters
        and for insertAdjacentXML.
        """
        db = DomBuilder(domImpl=Document)
        newDoc = db.parse_string(f"<wrapper>{xml}</wrapper>")
        if newDoc is None:
            raise ValueError("parse_string failed.")
        assert newDoc.documentElement.nodeName == "wrapper"
        return newDoc

    def toprettyxml(self, foptions:FormatOptions=None, **kwargs) -> str:  # Element
        # TODO: de-dup whitespace between element
        if not foptions: foptions = FormatOptions(**kwargs)
        t = ""
        ws = "" if self.nodeName in foptions.inlineTags else foptions.ws
        if foptions.breakBB: t += ws
        t += self._startTag(foptions=foptions)
        if foptions.breakAB: t += ws
        if len(self.childNodes) > 0:
            foptions.depth += 1
            for ch in self.childNodes:
                t += ch.toprettyxml(foptions)
            foptions.depth -= 1
        if foptions.breakBE: t += ws
        t += self.endTag
        if foptions.breakAE: t += ws
        return t

    def outerJSON(self, indent:str="  ", depth:int=0) -> str:  # Element  # HERE
        """TODO: Support Fragments?
        """
        istr = indent * depth
        buf = '%s[ { "#name":"%s"' % (
            istr, self.nodeName)
        if self.attributes:
            for k in self.attributes:
                anode = self.getAttributeNode(k)
                # If the values are actual int/float/bool/none, use JSON vals.
                buf += ', ' + anode.attrToJson()
        buf += " }"
        if self.childNodes is not None:
            for ch in self.childNodes:
                buf += ",\n" + istr + ch.outerJSON(indent, depth+1)
            buf += "\n" + istr
        buf += "]"
        return buf

    @property
    def startTag(self) -> str:  # HERE
        """Never produces empty-tags (use _startTag(empty=True) for that).
        """
        return self._startTag()

    def _startTag(self, empty:bool=False, includeNS:bool=False,
        foptions=None, **kwargs) -> str:  # HERE
        """Gets a correct start-tag for the element. If 'includeNS' is set,
        declare all in-scope namespaces even if inherited.
        """
        if not foptions: foptions = FormatOptions(**kwargs)
        if self.nodeType != NodeType.ELEMENT_NODE:
            raise HReqE(f"_startTag request for non-Element {self.nodeType}.")
        t = f"<{self.nodeName}"
        if self.attributes:
            ws = foptions.ws + foptions.indent if (foptions.breakAttrs) else " "
            names = self.attributes.keys()
            if foptions.sortAttrs or foptions.canonical:
                names = sorted(names)
            q = foptions.quoteChar
            for k in names:
                vEsc = XStr.escapeAttribute(self.attributes[k].value)
                t += f'{ws}{k}={q}{vEsc}{q}'
        if includeNS:  # TODO Interleave if sorted
            for k, v in self.inheritedNS.items:
                vEsc = XStr.escapeAttribute(v)
                t += f'{ws}{RWord.NS_PREFIX}:{k}={q}{vEsc}{q}'
        return t + ((foptions.spaceEmpty + "/") if empty else "") + ">"

    @property
    def endTag(self) -> str:  # HERE
        if self.nodeType != NodeType.ELEMENT_NODE:
            raise HReqE(f"_endTag request for non-Element {self.nodeType}.")
        return f"</{self.nodeName}>"

    ### Meta (Element)

    def unlink(self, keepAttributes:bool=False) -> None:  # MINIDOM
        super().unlink(keepAttributes=keepAttributes)
        if self.attributes:
            for attr in self.attributes.values(): attr.unlink()
            if not keepAttributes: self.attributes = None
        if self.childNodes is not None:
            self.childNodes.clear()

    def checkNode(self, deep:bool=False) -> None:  # Element  # DBG
        super().checkNode()

        if self.attributes is not None:
            assert isinstance(self.attributes, NamedNodeMap)
            for aname, anode in self.attributes.items():
                assert isinstance(anode, Attr)
                assert aname == anode.nodeName
                anode.checkNode()

        if self.childNodes is not None:
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
                if i > 0: assert ch.previousSibling is not None
                if i < len(self.childNodes)-1: assert ch.nextSibling is not None
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
    def __init__(self, ownerDocument=None, nodeName:NMTOKEN_t=None):
        super().__init__(ownerDocument, nodeName)
        self.data = None


    def isEqualNode(self, n2) -> bool:  # CharacterData
        if not super().isEqualNode(n2): return False
        if self.data != n2.data: return False
        return True

    @property
    def length(self) -> int:
        if not self.data: return 0
        return len(self.data)

    @property
    def nodeValue(self) -> str:  # CharacterData
        return self.data

    @nodeValue.setter
    def nodeValue(self, newData:str="") -> None:
        self.data = newData

    ### String mutators

    def appendData(self, s:str) -> None:  # WHATWG
        if not self.data: self.data = s
        else: self.data += s

    @property
    def textContent(self) -> None:  # CharacterData
        return self.data

    @textContent.setter
    def textContent(self, newData:str) -> None:  # CharacterData
        self.data = newData

    def deleteData(self, offset:int, count:int) -> None:  # WHATWG
        if (self.data is None or
            not (0 <= offset <= offset+count < len(self.data))):
            raise IndexError("Bad offset(%d)/count(%d) for deleteData (len %d)."
                % (offset, count, len(self.data)))
        self.data = self.data[0:offset] + self.data[offset+count:]

    def insertData(self, offset:int, s:str) -> None:  # WHATWG
        if self.data is None or not (0 <= offset <= len(self.data)):
            raise IndexError("Bad offset(%d) for insertData (len %d)."
                % (offset, len(self.data)))
        self.data = self.data[0:offset] + s + self.data[offset:]

    def remove(self, x:Any=None) -> None:
        if x is not None:
            raise KeyError("CharacterData.remove is not like list.remove!")
        self.data = ""

    def replaceData(self, offset:int, count:int, s:str) -> None:  # WHATWG
        if self.data is None or not (0 <= offset <= offset+count < len(self.data)):
            raise IndexError("Bad offset(%d)/count(%d) for replaceData (len %d)."
                % (offset, count, len(self.data)))
        self.data = self.data[0:offset] + s + self.data[offset+count:]

    def substringData(self, offset:int, count:int) -> str:  # WHATWG
        if self.data is None or not (0 <= offset <= offset+count < len(self.data)):
            raise IndexError("Bad offset(%d)/count(%d) for substringData (len %d)."
                % (offset, count, len(self.data)))
        return self.data[offset:offset+count]

    @property
    def hasChildNodes(self) -> bool:
        return False
    def contains(self, other:'Node') -> bool:
        return False
    def hasAttributes(self) -> bool:
        return False
    def hasAttribute(self, aname:NMTOKEN_t) -> bool:
        return False

    def count(self, x) -> int:
        return 0
    def index(self, x, start:int=None, end:int=None) -> int:
        return None
    def clear(self) -> None:
        return

    def tostring(self) -> str:  # CharacterData (PI overrides too)
        return self.data

    # Hide any methods that can't apply to leaves.
    # Don't know why DOM put them on Node instead of Element.
    #
    LeafChildMsg = "CharacterData nodes cannot have children."
    @property
    def firstChild(self) -> Node:
        raise HReqE(CharacterData.LeafChildMsg)
    @property
    def lastChild(self) -> Node:
        raise HReqE(CharacterData.LeafChildMsg)

    @hidden
    def __getitem__(self, *args):
        raise HReqE(CharacterData.LeafChildMsg)
    @hidden
    def appendChild(self, newChild:Node) -> None:
        raise HReqE(CharacterData.LeafChildMsg)
    @hidden
    def prependChild(self, newChild:Node) -> None:
        raise HReqE(CharacterData.LeafChildMsg)
    @hidden
    def insertBefore(self, newChild:Node, oldChild:Union[Node, int]) -> None:
        raise HReqE(CharacterData.LeafChildMsg)
    @hidden
    def removeChild(self, oldChild:Union[Node, int]) -> Node:
        raise HReqE(CharacterData.LeafChildMsg)
    @hidden
    def replaceChild(self, newChild:Node, oldChild:Union[Node, int]) -> None:
        raise HReqE(CharacterData.LeafChildMsg)
    @hidden
    def append(self, newChild:Node) -> None:
        raise HReqE(CharacterData.LeafChildMsg)

    def unlink(self, keepAttributes:bool=False) -> None:  # MINIDOM
        super().unlink()
        self.data             = None
        return

    def checkNode(self, deep:bool=True) -> None:  # CharacterData (cf Attr):  # DBG
        super().checkNode()
        assert self.parentNode is None or self.parentNode.isElement
        #assert self.attributes is None and self.childNodes is None
        if self.isPI: assert XStr.isXmlName(self.target)


###############################################################################
#
class Text(CharacterData):
    def __init__(self, ownerDocument=None, data:str=""):
        super().__init__(ownerDocument=ownerDocument, nodeName=RWord.NN_TEXT)
        self.nodeType = Node.TEXT_NODE
        self.data = data

    def cloneNode(self, deep:bool=False) -> 'Text':
        newNode = Text(ownerDocument=self.ownerDocument, data=self.data)
        if self.userData: newNode.userData = self.userData
        return newNode

    ####### EXTENSIONS for Text

    def cleanText(self, unorm:str=None, normSpace:bool=True) -> str: # HERE
        """Apply Unicode normalization and or XML space normalization
        to the text of the node.
        TODO: Upgrade to handle all the UNorm, Case, WS options; dft from doc?
        TODO: Move up to CharacterData?
        """
        if unorm: buf =  unicodedata.normalize(unorm, self.data)
        else: buf = self.data
        if normSpace: buf = XStr.normalizeSpace(buf)
        self.data = buf
        return buf

    def toprettyxml(self, foptions:FormatOptions=None, **kwargs) -> str:  # Text
        if not foptions: foptions = FormatOptions(**kwargs)
        return foptions.ws + XStr.escapeText(self.data)

    def outerJSON(self, indent:str="  ", depth:int=0) -> str:  # Text  # HERE
        istr = indent * depth
        return istr + '"%s"' % (escapeJsonStr(self.data))

    def tostring(self) -> str:  # Text
        return self.data


###############################################################################
#
class CDATASection(CharacterData):
    def __init__(self, ownerDocument, data:str):
        super().__init__(ownerDocument=ownerDocument, nodeName="#cdata-section")
        self.nodeType = Node.CDATA_SECTION_NODE
        self.data = data

    ####### EXTENSIONS

    def toprettyxml(self, foptions:FormatOptions=None, **kwargs) -> str:  # CDATASection
        if not foptions: foptions = FormatOptions(**kwargs)
        return f"<![CDATA[{XStr.escapeCDATA(self.data)}]]>"

    def outerJSON(self, indent:str="  ", depth:int=0) -> str:  # CDATASection  # HERE
        istr = indent * depth
        return istr + '[ {"#name"="#cdata"}, "%s"]' % (escapeJsonStr(self.data))

    def tostring(self) -> str:  # CDATASection
        return self.data


###############################################################################
#
class ProcessingInstruction(CharacterData):
    def __init__(self, ownerDocument=None, target=None, data:str=""):
        if target is not None and target!="" and not XStr.isXmlName(target):
            raise ICharE("Bad PI target '%s'." % (target))
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

    ####### EXTENSIONS PI

    def toprettyxml(self, foptions:FormatOptions=None, **kwargs) -> str:  # PI
        if not foptions: foptions = FormatOptions(**kwargs)
        return f"<?{XStr.escapePI(self.target)} {XStr.escapePI(self.data)}?>"

    def outerJSON(self, indent:str="  ", depth:int=0) -> str:  # PI  # HERE
        istr = indent * depth
        return (istr + '[ { "#name":"#pi", "#target":"%s", "#data":"%s" } ]'
             % (escapeJsonStr(self.target), escapeJsonStr(self.data)))

    def tostring(self) -> str:  # PI
        return self.data

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

    ####### EXTENSIONS

    def toprettyxml(self, foptions:FormatOptions=None, **kwargs) -> str:  # Comment
        if not foptions: foptions = FormatOptions(**kwargs)
        return foptions.ws + f"<!--{XStr.escapeComment(self.data)}-->"

    def outerJSON(self, indent:str="  ", depth:int=0) -> str:  # Comment  # HERE
        istr = indent * depth
        return (istr + '[ { "#name":"#comment", "#data":"%s" } ]'
            % (escapeJsonStr(self.data)))

    def tostring(self) -> str:  # Comment
        return self.data


###############################################################################
#
class EntityReference(CharacterData):  # OBS DOM
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

    def toprettyxml(self, foptions:FormatOptions=None, **kwargs) -> str:  # EntityReference
        if not foptions: foptions = FormatOptions(**kwargs)
        return f"&{self.nodeName};"

    def outerJSON(self, indent:str="  ", depth:int=0) -> str:  # EntityReference  # HERE
        istr = indent * depth
        return istr + '[ { "#name":"#entref, "#ref":"%s" } ]' % (escapeJsonStr(self.data))

    def tostring(self) -> str:  # EntityReference
        return self.data

EntRef = EntityReference


###############################################################################
#
class Attr(Node):
    """This is a little weird, because each Element can own a NamedNodeMap
    (which is a Dict, not a Node), which then owns the Attr objects.
    TODO: namespace support
    """
    def __init__(self, name:NMTOKEN_t, value:Any, ownerDocument:Document=None,
        nsPrefix:NMTOKEN_t=None, namespaceURI:str=None, ownerElement:Node=None,
        attrType:type=str):
        super().__init__(ownerDocument=ownerDocument, nodeName=name)
        self.nodeType = Node.ATTRIBUTE_NODE
        self.parentNode = None
        self.inheritedNS = None  # Resolved via parent
        self.ownerElement = ownerElement
        if ownerElement is not None and ownerElement.nodeType != Node.ELEMENT_NODE:
            raise TypeError(f"ownerElement for attribute '{name}' "
                "is {ownerElement.nodeType}, not ELEMENT.")

        if not XStr.isXmlQName(name):
            raise ICharE(f"Bad attribute name '{name}'.")
        if attrType:
            try:
                if not isinstance(attrType, type): raise TypeError(
                    f"attrType for '{name}' is not a type, but {type(attrType)}.")
                self.value = attrType(value)
                self.attrType = self.ownerDocument.doctype.attrType(
                    ownerElement.nodeName, name)
                self.isId = self.attrType == "ID"  # TODO hook up to idhandler
            except (ValueError, AttributeError):
                self.attrType = attrType  # TODO ???

    def clear(self) -> None:
        raise NSuppE("No clear() on Attr nodes.")

    @property
    def name(self) -> str:
        return self.nodeName
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
        try:
            return self.ownerElement.inheritedNS[prefix]
        except (KeyError, ValueError, TypeError, AttributeError):
            return None

    @property
    def nodeValue(self) -> str:  # Attr
        return self.value

    @nodeValue.setter
    def nodeValue(self, newData:str="") -> None:  # Attr
        self.value = newData

    @property
    def isConnected(self) -> bool:  # Attr
        return False

    @property
    def textContent(self) -> None:  # Attr
        return self.value

    @textContent.setter
    def textContent(self, newData:str) -> None:  # Attr
        if self.attrType: newData = self.attrType(newData)
        self.value = newData

    @property
    def nextSibling(self) -> 'Node':
        raise HReqE("Attributes are not children.")

    @property
    def previousSibling(self) -> 'Node':
        raise HReqE("Attributes are not children.")

    @property
    def next(self) -> 'Node':  # XPATH
        raise HReqE("Attributes are not children.")

    @property
    def previous(self) -> 'Node':  # XPATH
        raise HReqE("Attributes are not children.")

    @property
    def isFirstChild(self) -> bool:
        raise HReqE("Attributes are not children.")

    @property
    def isLastChild(self) -> bool:
        raise HReqE("Attributes are not children.")

    def getChildIndex(self, onlyElements:bool=False, ofNodeName:bool=False,
        noWSN:bool=False) -> int:  # Attr  # HERE
        raise HReqE("Attributes are not children.")

    def compareDocumentPosition(self, other:'Node') -> int:  # Attr
        """Could use the owning element's position, but that would also
        mean document order becomes a *partial* order.
        """
        raise HReqE("Attributes do not have document positions.")

    def isEqualNode(self, n2:'Attr') -> bool:
        if not n2.isAttribute: raise ValueError("No n2 attr provided.")
        if not self.nodeNameMatches(n2): return False
        if not self.value == n2.value: return False
        return True

    def cloneNode(self, deep:bool=False) -> 'Attr':
        newAttr = Attr(name=self.nodeName, value=self.value,
            ownerDocument=self.ownerDocument,
            ownerElement=None, attrType=self.attrType)
        return newAttr

    ### Serializers (Attr)
    #
    def toprettyxml(self, foptions:FormatOptions=None, **kwargs) -> str:  # Attr
        #if not foptions: foptions = FormatOptions(**kwargs)
        return f"{self.nodeName}=\"{XStr.escapeAttribute(self.value)}\""

    def outerJSON(self, indent:str="  ", depth:int=0) -> str:  # Attr  # HERE
        # This was handled on Element.
        raise HReqE("outerJSON() not available on Attr.")

    def attrToJson(self, listAttrs:bool=False) -> str:  # HERE
        """This uses JSON non-string types iff the value is actually
        of that type, or somebody declared the attr that way.
        Not if it's a string that just looks like it (say, "99").
        """
        aname = self.nodeName
        avalue = self.value
        buf = f'"{aname}":'
        if isinstance(avalue, float): buf += "%f" % (avalue)
        elif isinstance(avalue, int): buf += "%d" % (avalue)
        elif avalue is True: buf += "true"
        elif avalue is False: buf += "false"
        elif avalue is None: buf += "nil"
        elif isinstance(avalue, str): buf += f'"{escapeJsonStr(avalue)}"'
        elif isinstance(avalue, list):  # Only for tokenized attrs
            if listAttrs:
                buf += "[ %s ]" % (
                    ", ".join([  escapeJsonStr(str(x)) for x in avalue ]))
            else:
                buf += '"%s"' % (
                    escapeJsonStr(" ".join([ str(x) for x in avalue ])))
        else:
            raise HReqE(f"attrToJson got unsupported type {type(avalue)}.")
        return buf

    def tostring(self) -> str:  # Attr
        """Attr is not quoted or escaped for this.
        """
        return str(self.nodeValue)

    def checkNode(self, deep:bool=True) -> None:  # Attr  # DBG
        assert self.isAttribute
        if self.ownerDocument is not None:
            assert self.ownerDocument.isDocument
        assert self.parentNode is None
        assert self.inheritedNS is None
        assert "attributes" not in dir(self)
        assert "data" not in dir(self) and "target" not in dir(self)

        assert XStr.isXmlQName(self.nodeName)
        if self.attrType and self.value is not None:
            assert isinstance(self.attrType, type)
            assert isinstance(self.value, self.attrType)
        if self.userData is not None:
            assert isinstance(self.userData, dict)

        if self.ownerElement is None: return
        assert self.ownerElement.isElement
        assert self.ownerDocument == self.ownerElement.ownerDocument
        if len(self.ownerElement) == 0: return
        for i, ch in enumerate(self.ownerElement):
            assert ch is not self, f"Attr '{self.nodeName}' got into childNodes[{i}]."
        if self.ownerElement.childNodes.contains(self):
            # 'contains' logic may be non-obvious, so double-check.
            print(self.outerXML)
            raise OperationError(
                f"Attr '{self.nodeName}' got into childNodes (contains *only*)")


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
        aname:NMTOKEN_t=None, avalue:Any=None):
        """On creation, you can optionally set an attribute.
        """
        super(NamedNodeMap, self).__init__()
        self.ownerDocument = ownerDocument
        self.parentNode    = parentNode
        if aname: self.setNamedItem(aname, avalue)

    def __eq__(self, other) -> bool:
        """NOTE: Python considers OrderedDicts unequal if order differs.
        But here we want OrderedDict only for serializing, so...
        """
        return dict(self) == dict(other)

    def __ne__(self, other) -> bool:
        return not (self == other)

    def setNamedItem(self, attrNodeOrName:Union[str, Attr], avalue:Any=None,
        atype:type=str) -> None:
        """This can take either an Attr (as in the DOM version), which contains
        its own name; or a string name and then a value (in which case the Attr
        is constructed automatically).
        TODO: types
        """
        if isinstance(attrNodeOrName, Attr):
            if avalue is not None:
                raise ValueError(f"Can't pass avalue ({avalue}) AND Attr node.")
            self[attrNodeOrName.nodeName] = attrNodeOrName
        else:
            if not XStr.isXmlQName(attrNodeOrName):
                raise ICharE(
                    f"Bad item name '{attrNodeOrName}'.")
            self[attrNodeOrName] = Attr(attrNodeOrName, avalue, attrType=atype,
                ownerDocument=self.ownerDocument, ownerElement=self.parentNode)

    def getNamedItem(self, name:NMTOKEN_t) -> Attr:
        """Per DOM, this returns the entire Attr instance, not just value.
        No exception if absent.
        """
        if name not in self: return None
        theAttr = self[name]
        assert isinstance(theAttr, Attr)
        return theAttr

    def getNamedValue(self, name:NMTOKEN_t) -> Any:  # HERE
        """Returns just the actual value.
        """
        if name not in self: return None
        return self[name].value

    def removeNamedItem(self, name:NMTOKEN_t) -> Attr:
        #import pudb; pudb.set_trace()
        if name not in self:
            raise KeyError(f"Named item to remove ('{name}') not found.")
        theAttrNode = self[name]
        theAttrNode.unlink()
        del self[name]
        theAttrNode.ownerElement = None
        return theAttrNode

    # TODO Implement getNamedItemNS, setNamedItemNS, removeNamedItemNS
    # NamedNodeMap
    #
    def setNamedItemNS(self, ns:str, aname:NMTOKEN_t, avalue:Any) -> None:
        assert NameSpaces.isNamespaceURI(ns)
        if not XStr.isXmlName(aname):
            raise ICharE("Bad name '%s'." % (aname))
        raise NSuppE("NamedNodeMap.setNamedItemNS")

    def getNamedItemNS(self, ns:str, name:NMTOKEN_t) -> Any:
        assert NameSpaces.isNamespaceURI(ns)
        raise NSuppE("NamedNodeMap.getNamedItemNS")

    def getNamedValueNS(self, ns:str, name:NMTOKEN_t) -> Any:  # extension
        assert NameSpaces.isNamespaceURI(ns)
        raise NSuppE("NamedNodeMap.getNamedItemNS")

    def removeNamedItemNS(self, ns:str, name:NMTOKEN_t) -> None:
        assert NameSpaces.isNamespaceURI(ns)
        raise NSuppE("NamedNodeMap.removeNamedItemNS")


    def item(self, index:int) -> Attr:
        if index < 0: index = len(self) + index
        if index >= len(self): raise IndexError(
            f"NamedNodeMap item #{index} out of range ({len(self)}).")
        for i, key in enumerate(self.keys()):
            if i >= index: return self[key]
        raise IndexError(f"NamedNodeMap item #{index} not found.")

    def clone(self) -> 'NamedNodeMap':
        other = NamedNodeMap(
            ownerDocument=self.ownerDocument, parentNode=self.parentNode)
        for name, value in self.items():
            assert isinstance(name, str) and isinstance(value, Attr)
            attrNodeCopy = value.cloneNode()
            other.setNamedItem(attrNodeCopy)
        return other

    copy = clone

    def getIndexOf(self, name:NMTOKEN_t) -> int:  # NamedNodeMap  # HERE
        """Return the position of the node in the source/creation order.
        TODO: NS, incl. any?
        """
        for i, curName in enumerate(self.keys()):
            if curName == name: return i
        return None

    def clear(self) -> None:
        for name in self.keys():
            self.removeNamedItem(name)
        assert len(self) == 0

    def writexml(self, writer, indent:str="", addindent:str="", newl:str="",
        encoding:str=None, standalone:bool=None) -> None: # MINIDOM
        writer.write(self.tostring())

    def tostring(self) -> str:
        """Produce the complete attribute list as would go in a start tag.
        """
        s = ""
        ks = self.keys()
        if self.ownerDocument and self.ownerDocument.options.sortAttrs:
            ks = sorted(ks)
        for k in ks:
            s += ' %s="%s"' % (k, XStr.escapeAttribute(self[k].value))
        return s


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
            #lg.warning("Prefix '%s' rebound from '%s' to '%s'.",
            #    prefix, self[prefix], uri)
        super().__setitem__(prefix, uri)

        if uri not in self.uri2prefix:
            self.uri2prefix[uri] = []
        elif self.uri2prefix.contains(uri):
            return
        self.uri2prefix[uri].append(prefix)

    def __delitem__(self, prefix:str) -> None:
        assert XStr.isXmlName(prefix)
        uri = self[prefix]
        del self.uri2prefix[uri]
        super().__delitem__(prefix)

    @staticmethod
    def isNamespaceURI(ns:str) -> bool:
        """
        TODO: Is setting to "" ok?
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
            if (not re.match(r"^(\*|#all|#any)$", Tprefix, flags=re.I)
                and node.prefix != Turi): return False
        if Tname and node.nodeName != Turi: return False
        return True
