#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# A modern pure Python DOM implementation, with parser, datatyping,....
#
# Geordi, I have spent my whole life trying to figure out crazy ways of
# doing things. I'm telling ya, as one engineer to another -- I can do this.
#            -- ST:TNG "Relics"
#
#pylint: disable=W0613, W0212, E1101
#
#import codecs
from collections import OrderedDict
from types import SimpleNamespace
from typing import Any, Callable, Dict, List, Union, Iterable, Tuple, IO
import functools
import unicodedata
import re
#from textwrap import wrap
from xml.parsers import expat

from basedomtypes import DOMException, HReqE, ICharE, NSuppE, FlexibleEnum
from basedomtypes import NamespaceError, NotFoundError, OperationError
from basedomtypes import DOMImplementation_P, NMTOKEN_t, QName_t, NodeType, dtr

from saxplayer import SaxEvent
from domenums import RWord
from dombuilder import DomBuilder
from xmlstrings import XmlStrings as Rune, CaseHandler, Normalizer
from xsdtypes import XSDDatatypes
from idhandler import IdHandler
from prettyxml import FormatOptions, FormatXml

__metadata__ = {
    "title"        : "BaseDOM",
    "description"  : "A more modern, Pythonic, fast DOM-ish implementation.",
    "rightsHolder" : "Steven J. DeRose",
    "creator"      : "http://viaf.org/viaf/50334488",
    "type"         : "http://purl.org/dc/dcmitype/Software",
    "language"     : "Python 3.11",
    "created"      : "2016-02-06",
    "modified"     : "2025-03",
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


###############################################################################
#
class RelPosition(FlexibleEnum):  # WHATWG
    """Places relative to element, mainly for insertAdjacentXML().

    "Now this is not the end. It is not even the beginning of the end.
    But it is, perhaps, the end of the beginning."
        -- Winston Churchhill, Lord Mayor's Day Luncheon, 10 November 1942
    """
    beforebegin = "beforebegin"
    afterbegin = "afterbegin"
    beforeend = "beforeend"
    afterend = "afterend"


###############################################################################
#
def getDOMImplementation(name:str=None) -> type:
    return DOMImplementation(name)

class DOMImplementation(DOMImplementation_P):
    name = "BaseDOM"
    version = "0.1"

    def __init__(self, name:str=None):
        if name: DOMImplementation.name = name

    def createDocument(self, namespaceURI:str=None, qualifiedName:NMTOKEN_t=None,
        doctype:'DocumentType'=None) -> 'Document':
        """Make a DOM Document object. IFF a qualifiedName is specified,
        also create a documentElement of that nodeName. Otherwise don't.
        """
        doc = Document(namespaceURI=namespaceURI,
            qualifiedName=qualifiedName, doctype=doctype)

        if not qualifiedName: return doc

        if not Rune.isXmlQName(qualifiedName):
            raise ICharE(f"Root element to be has bad qname '{qualifiedName}'.")
        prefix = Rune.getPrefixPart(qualifiedName)

        if prefix == "xml":
            if namespaceURI not in [ RWord.XML_PREFIX_URI, "" ]:
                raise NamespaceError(
                    f"URI for xml prefix is not '{RWord.XML_PREFIX_URI}'")
        doc.documentElement = doc.createElement(qualifiedName)
        if prefix:
            doc.documentElement.setAttribute(
                RWord.NS_PREFIX+":"+prefix, namespaceURI)
        if doc.doctype:
            doc.doctype.parentNode = doctype.ownerDocument = doc
        return doc

    def createDocumentType(self, qualifiedName:QName_t,
        publicId:str, systemId:str, htmlEntities:bool=False) -> 'DocumentType':
        """Create a schema object, which can they be loaded up by parsing or
        by API.
        """
        from documenttype import DocumentType
        return DocumentType(qualifiedName, publicId, systemId, htmlEntities)

    def registerDOMImplementation(self, name:str, factory) -> None:
        raise NSuppE

    @staticmethod
    def getImplementation() -> type:
        return DOMImplementation()

    # Put in some loaders

    def parse(self, f:Union[str, IO], parser=None, bufsize:int=None
        ) -> 'Document':
        #domImpl = getDOMImplementation()
        dbuilder = DomBuilder(parserClass=parser, domImpl=self)
        theDom = dbuilder.parse(f)
        return theDom

    def parse_string(self, s:str, parser=None) -> 'Document':
        domImpl = getDOMImplementation()
        dbuilder = DomBuilder(parserClass=parser, domImpl=domImpl)
        theDom = dbuilder.parse_string(s)
        return theDom


###############################################################################
#
class NodeList(list):
    """We pretty much just subclass Python list.
    Possibly need to add:  __eq__; sort to doc order; tostring;
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

    ### list adder/multipliers should work as-is for Nodelist, but not for Node.

    def writexml(self, writer:IO,
        indent:str='    ', addindent:str='  ', newl:str='\n') -> None:
        fo = FormatOptions.getDefaultFO(indent=indent, addindent=addindent, newl=newl)
        writer.write(self.toprettyxml(fo=fo))


    def toprettyxml(self, fo:FormatOptions=None, wrapper:NMTOKEN_t=None) -> str:
        return FormatXml.toprettyxml(node=self, fo=fo)


###############################################################################
#
class SiblingImpl(FlexibleEnum):
    """Set this (where??) to determine how siblings are found.  TODO
    PARENT tests faster than LINKS due to maintenance overhead, unless the
    trees are very wide/bushy. In theory, CHNUM should be faster when the
    tree is not changing much (but changes are slower).
    """
    PARENT = 0   # Scan parent
    CHNUM = 1    # Node maintain their child number
    LINKS = 2    # Doubly-linked siblings

# Do NOT change this mid-stream. Only before creating a document.
_siblingImpl       = SiblingImpl.PARENT


###############################################################################
#
class PlainNode(list):
    """The main (basically abstract) class for DOM, from which many are derived.
        https://www.w3.org/TR/2000/REC-DOM-Level-2-Core-20001113

    We make this a direct subclass of list (of its childNodes). This gets many
    useful and hopefully intuitive features. However, it has some side effects:
      * Since Nodes know where they are (parent/owner), insert/del are special.
      * Empty nodes (no childNode) are not usefully False, b/c they are not
        all identical. So bool() is special.
      * "contains" is nonrecursive in Python lists, but recursive in DOM.

    (the int codes for nodeType are pulled in by th @mirror_enum decorator).
    """
    ATTRIBUTE_NODE              = NodeType.ATTRIBUTE_NODE
    CDATA_SECTION_NODE          = NodeType.CDATA_SECTION_NODE
    COMMENT_NODE                = NodeType.COMMENT_NODE
    DOCUMENT_FRAGMENT_NODE      = NodeType.DOCUMENT_FRAGMENT_NODE
    DOCUMENT_NODE               = NodeType.DOCUMENT_NODE
    DOCUMENT_TYPE_NODE          = NodeType.DOCUMENT_TYPE_NODE
    ELEMENT_NODE                = NodeType.ELEMENT_NODE
    NOTATION_NODE               = NodeType.NOTATION_NODE
    PI_NODE                     = NodeType.PROCESSING_INSTRUCTION_NODE
    PROCESSING_INSTRUCTION_NODE = NodeType.PROCESSING_INSTRUCTION_NODE
    TEXT_NODE                   = NodeType.TEXT_NODE
    ABSTRACT_NODE               = NodeType.ABSTRACT_NODE
    ENTITY_REFERENCE_NODE       = NodeType.ENTITY_REFERENCE_NODE
    ENTITY_NODE                 = NodeType.ENTITY_NODE

    @property
    def canHaveChildren(self) -> bool:  # HERE
        return self.nodeType in [
            PlainNode.ABSTRACT_NODE,  # TODO Maybe not?
            PlainNode.ELEMENT_NODE, PlainNode.DOCUMENT_NODE,
            PlainNode.DOCUMENT_TYPE_NODE, PlainNode.DOCUMENT_FRAGMENT_NODE ]

    def __init__(self, ownerDocument:Document=None, nodeName:NMTOKEN_t=None):
        """PlainNode (and Node) shouldn't really be instantiated.
        minidom lets Node be, but with different parameters.
        I add the params for constructor consistency.
        Also, since here it is a list, there's not much need to distinguish
        Node, NodeList, and DocumentFragment -- mainly that only the first
        has to be the (unique) parentNode of all its members (and therefore
        the determiner of siblings, etc.).
        """
        super().__init__()
        self.ownerDocument = ownerDocument
        self.parentNode = None  # minidom Attr lacks....
        self.nodeType = Node.ABSTRACT_NODE
        if nodeName and nodeName[0] != "#" and not Rune.isXmlQName(nodeName):
            raise ICharE(f"nodeName '{nodeName}' isn't.")
        self.nodeName = nodeName
        self.inheritedNS = {}
        self.userData = None
        self.prevError:str = None  # Mainly for isEqualNode

        # Following dunders are only used if _siblingImpl is their way
        if _siblingImpl == SiblingImpl.CHNUM:
            self._childNum = None
        elif _siblingImpl == SiblingImpl.LINKS:
            self._previousSibling = None
            self._nextSibling = None

    def __contains__(self, item:'Node') -> bool:
        """Careful, Python and DOM "contains" are different:
            x.__contains__(y) is non-recursive.
            x.contains(y) is recursive.
        """
        return item.parentNode == self

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

    def __setitem__(self, picker:Union[int, slice], value: 'Node') -> None:
        """Regular list ops aren't even, as we have to set neighbor link(s).
        """
        if not isinstance(value, (Node, NodeList)): raise HReqE(
            f"Can't insert ({type(value)}) as child, must be Node or NodeList.")

        # Delete as needed
        if isinstance(picker, int):
            start = self._normalizeChildIndex(picker)
            self.removeChild(start)
        elif isinstance(picker, slice):
            start, stop, step = picker.indices(len(self))
            if step is not None and step not in [ -1, 1 ]: raise SyntaxError(
                "Step value {step} not (yet) supported in __setitem__.")
            for i in range(stop-1, start-1, -1 if step > 0 else 1):  # ewwwww TODO
                self.removeChild(i)
        # TODO more... @attr, nmtoken, #text, scheme:...
        else:
            raise TypeError(f"Unsupported type {type(picker)} for [] arg.")

        # Insert
        new_nodes = [value] if isinstance(value, Node) else value
        for i, node in enumerate(new_nodes):
            self.insert(start+i, node)

    def __getitem__(self, picker:Any) -> Union['Node', 'NodeList']:
        """Need to override so pylint doesn't think 'picker'
        absolutely has to be slice or int.
        """
        if isinstance(picker, int):
            return super().__getitem__(picker)
        if isinstance(picker, str):
            return self.__filter__(picker)
        if isinstance(picker, slice):
            if (isinstance(slice.start, str) and
                slice.stop is None and slice.step is None):
                return self.__filter__(picker)
            else:
                nl = NodeList()
                for node in super().__getitem__(picker):
                    nl.append(node)
                return nl
        raise TypeError(f"Unrecognized index/slice type {type(picker)} for __getitem__.")

    def __filter__(self, f:str) -> Any:
        """Pick some node via a selection mechanism.
        TODO Decide nodeName #text vs. CSS #id
        TODO Should @x return attr value or (probably) Attr node?
        """
        if f[0] in Rune.punc_set:
            if f == "*":                                # "*" for any element
                nl = NodeList()
                for ch in self.childNodes:
                    if ch.isElement: nl.append(ch)
                return nl
            if f == "**":                               # "**" for any element or text
                nl = NodeList()
                for ch in self.childNodes:
                    if ch.isElement or ch.isText: nl.append(ch)
                return nl
            if f == "/":                                # "/" for root
                return self.ownerDocument.documentElement
            if f == "..":                               # ".." for parent
                return self.parentNode
            if f.startswith("@"):                       # "*x" for attribute
                return self.getAttribute(f[1:])
            if f.startswith("#"):                       # "#text" etc.
                return self.getChildrenByTagName(f)
            raise ValueError("Unrecognized slice syntax '{f}'.")

        if Rune.isXmlName(f):                         # nodeNames
            return self.getChildrenByTagName(f)

        scheme, _colon, schemeData = f.partition(":")
        try:
            sh = self.ownerDocument.schemeHandlers[scheme]
            return sh(self, schemeData)
        except KeyError as e:
            raise TypeError("Unrecognized filter scheme '%s' (known: %s)."
                % (scheme, self.ownerDocument.schemeHandlers.keys())) from e

    def getChildIndex(self, onlyElements:bool=False, ofNodeName:bool=False,
        noWSN:bool=False) -> int:  # HERE
        """Return the position in order (from 0), among the node's siblings
        (or selected siblings). This is O(n). It is mainly used when not
        opting to use sibling pointers or explicit _childNum values.
        If self is not an element, it's considered to have position one
        greater than the nearest preceding matching node.
        """
        if self.parentNode is None: return None
        if hasattr(self, "_childNum"): return self._childNum
        i = 0
        for ch in self.parentNode.childNodes:
            if ch is self: return i
            if onlyElements and not ch.isElement: continue
            if noWSN and ch.isWSN: continue
            if ofNodeName and not ch._nodeNameMatches(self): continue
            i += 1
        return None

    def getRChildIndex(self, onlyElements:bool=False, ofNodeName:bool=False,
        noWSN:bool=False) -> int:  # HERE
        """Return the position from the end (from -1...) among
        the node's siblings or selected siblings (such as just Elements, or
        just nodes of the same nodeName.
        """
        if self.parentNode is None: return None
        if hasattr(self, "_childNum"):
            return self._childNum - len(self.parentNode.childNodes)
        i = -1
        for ch in reversed(self.parentNode.childNodes):
            if ch is self: return i
            if onlyElements and not ch.isElement: continue
            if noWSN and ch.isWSN: continue
            if ofNodeName and ch.nodeName != self.nodeName: continue  # TODO use nodeNameMatches
            i -= 1
        #raise HReqE("Child not found.")
        return None

     # Next three are defined here (PlainNode), but only work for Element and Attr.
    # (though constructors all takes nodeName for consistency...).
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
    def childNodes(self) -> 'Node':
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
    def parentElement(self) -> 'Node':  # WHATWG?  TODO Move?
        """Main case of non-None non-Element parent is Document (also Frag).
        """
        if self.parentNode is None or not self.parentNode.isElement: return None
        return self.parentNode

    @property
    def previousSibling(self) -> 'Node':
        """There are 3 obvious ways to manage siblings:
            * scan the parentNode to find where you are
            * each node knows its position in sibling order
            * siblings are in a doubly-linked list.
        These have serious tradeoffs depending on the shape of the document,
        how much it's changing, and how it's being accessed (and more).
        So we allow your choice. Just pick by setting _siblingImpl, but
        do it *before* creating any documents, please.
        """
        if self.parentNode is None: return None
        if _siblingImpl == SiblingImpl.PARENT:
            n = self.getChildIndex()
            if n <= 0: return None
            return self.parentNode.childNodes[n-1]
        elif _siblingImpl == SiblingImpl.CHNUM:
            n = self._childNum
            if n <= 0: return None
            return self.parentNode.childNodes[n-1]
        elif _siblingImpl == SiblingImpl.LINKS:
            return self._previousSibling
        else:
            raise DOMException(f"_siblingImpl got toasted: {repr(_siblingImpl)}.")

    @property
    def nextSibling(self) -> 'Node':
        """See also previousSibling().
        """
        if self.parentNode is None: return None
        if _siblingImpl == SiblingImpl.PARENT:
            n = self.getChildIndex() + 1
            if n >= len(self.parentNode.childNodes): return None
            return self.parentNode.childNodes[n]
        elif _siblingImpl == SiblingImpl.CHNUM:
            n = self._childNum + 1
            if n >= len(self.parentNode.childNodes): return None
            return self.parentNode.childNodes[n]
        elif _siblingImpl == SiblingImpl.LINKS:
            return self._nextSibling
        else:
            raise DOMException(f"_siblingImpl got toasted: {repr(_siblingImpl)}.")

    # See class Node for additional neighbor methods and XPath analogs.

    def isSameNode(self, n2) -> bool:
        return self is n2

    def isEqualNode(self, n2) -> bool:  # Node  # DOM3
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
            dtr.msg("other is None")
            return False
        if self.nodeType != n2.nodeType:
            dtr.msg(f"nodeType differs ({self.nodeType} vs. {n2.nodeType}).")
            return False
        if not self._nodeNameMatches(n2):
            dtr.msg(f"nodeName differs ({self.nodeName} vs. {n2.nodeName}).")
            return False
        if self.nodeValue != n2.nodeValue:
            dtr.msg("nodeValue differs:\n" +
                f"  ###{self.nodeValue}###\n  ###{n2.nodeValue}###")
            return False
        # Element does additional checks like attributes and childNodes
        return True

    def _nodeNameMatches(self, other:'Node') -> bool:  # HERE
        """Factor this out b/c with namespaces there can be a match even
        if the prefixes don't match (several could map to the same URI).
        When disconnecting a node keep relevant namespaces with it.
        """
        if (self.ownerDocument and self.ownerDocument.options.ElementCase):
            if self.ownerDocument.options.ElementCase.strnormcmp(
                self.localName, other.localName): return False
        else:
            if self.localName != other.localName: return False

        #if self.parentNode is None or other.parentNode is None: return True
        if (self.namespaceURI == RWord.NS_ANY
            or other.namespaceURI == RWord.NS_ANY): return True

        if (self.ownerDocument and self.ownerDocument.options.NSURICase):
            if self.ownerDocument.options.NSURICase.strnormcmp(
                self.namespaceURI, other.namespaceURI): return False
        else:
            if self.namespaceURI != other.namespaceURI: return False
        return True

    def cloneNode(self, deep:bool=False) -> 'Node':
        """NOTE: Default value for 'deep' has changed in spec and browsers!
        """
        raise NSuppE("Shouldn't really be cloning an abstract Node.")

    #### Mutators (PlainNode)

    def _expandChildArg(self, ch:Union['Node', int]) -> (int, 'Node'):
        """Let callers specify a child either by the object itself or position.
        See which they passed, calculate the other, and return both.
        This is b/c various methods are faster one way or the other, but the
        user should be able to just use what they have.
        """
        if isinstance(ch, Node):
            if (ch.parentNode != self): raise HReqE(
                "Putative child node isn't.")
            return ch.getChildIndex(), ch
        if isinstance(ch, int):
            n = ch
            if n < 0: n = len(self) + n
            if n >= 0 and n < len(self):
                return n, self.childNodes[n]
            raise IndexError(f"child number {ch}, but only {len(self)} there.")
        raise TypeError("Bad child specifier type '%s'." % (type(ch).__name__))

    def _normalizeChildIndex(self, key:int) -> int:
        """Accept positive or negative child indexes, but return the positive form.
        If out of range, raise an exception.
        """
        assert isinstance(key, int)
        ll = len(self)
        if key < 0:
            if key < -ll: raise IndexError(
                f"childNode index {key} for [] out of range (len {ll}).")
            return ll + key
        if key >= ll: raise IndexError(
            f"childNode index {key} for [] out of range (len {ll}).")
        return key

    def normalize(self) -> None:  # TODO Rename normalizeDocument? cf DOM 3
        """Scan the subtree and merge any adjacent text nodes.
        Run children backward so we don't miss when we delete.
        """
        if len(self.childNodes) == 0: return
        fsib = self.childNodes[-1]
        for i in reversed(range(len(self.childNodes)-1)):
            ch = self.childNodes[i]
            if ch.nodeType == Node.ELEMENT_NODE:
                ch.normalize()
            elif ch.nodeType == Node.TEXT_NODE:
                if fsib.nodeType == Node.TEXT_NODE:
                    ch.textContent += fsib.textContent
                    self.removeChild(fsib)
            fsib = ch

    def appendChild(self, newChild:'Node') -> None:  # PlainNode
        self.insert(len(self), newChild)

    def append(self, newChild:'Node') -> None:
        self.insert(len(self), newChild)

    def insertBefore(self, newChild:'Node', oldChild:Union['Node', int]) -> None:
        oNum, oChild = self._expandChildArg(oldChild)
        if oChild.parentNode != self: raise NotFoundError(
            f"Node to insert before (a {oChild.nodeName}) is not a child.")
        self.childNodes.insert(oNum, newChild)

    def insertAfter(self, newChild:'Node', oldChild:Union['Node', int]) -> None:  # HERE
        oNum, oChild = self._expandChildArg(oldChild)
        if oChild.parentNode != self: raise NotFoundError(
            f"Node to insert after (a {oChild.nodeName}) is not a child.")
        self.childNodes.insert(oNum+1, newChild)

    def insert(self, i:int, newChild:'Node') -> None:  # PlainNode
        """Note: Argument order is different than (say) insertBefore.
        This implementation does not link siblings, b/c tests showed
        the overhead wasn't worth it.
        NOTE: All insertions end up here.
        """
        if not self.canHaveChildren:
            raise HReqE(f"node type {type(self).__name__} cannot have children.")
        if not isinstance(newChild, Node) or isinstance(newChild, (Attr, Document)):
            raise HReqE(f"newChild is bad type {type(newChild).__name__}.")
        if newChild.parentNode is not None:
            raise HReqE("newChild already has parent (name %s)"
                % (newChild.parentNode.nodeName))
        if newChild.isElement: self._filterOldInheritedNS(newChild)
        if i < 0: i = len(self) + i
        #if i >= len(self): self.appendChild(newChild)  # ?
        else: super().insert(i, newChild)

        newChild.ownerDocument = self.ownerDocument
        newChild.parentNode = self

        if _siblingImpl == SiblingImpl.PARENT:
            pass
        elif _siblingImpl == SiblingImpl.CHNUM:
            newChild._childNum = i
            for sibNum in range(i+1, len(self.childNodes)):
                self.childNodes[sibNum]._childNum = sibNum
        elif _siblingImpl == SiblingImpl.LINKS:
            newChild._previousSibling = newChild._nextSibling = None
            if i > 0:
                self.childNodes[i-1]._nextSibling = newChild
                newChild._previousSibling = self.childNodes[i-1]
            if i < len(self)-1:
                self.childNodes[i+1]._previousSibling = newChild
                newChild._nextSibling = self.childNodes[i+1]
        else:
            raise DOMException(f"_siblingImpl got toasted: {repr(_siblingImpl)}.")

    ### Removers
    #
    def replaceChild(self, newChild:'Node', oldChild:Union['Node', int]) -> None:
        if newChild.parentNode is not None:
            hint = " Swapped arguments?" if oldChild.parentNode is None else ""
            raise HReqE("New child for replaceChild already has parent." + hint)
        oNum, oChild = self._expandChildArg(oldChild)
        self.removeChild(oChild)
        self.childNodes.insert(oNum, newChild)

    def clear(self) -> None:
        while len(self) > 0:
            self.removeChild(self.childNodes[0])

    def pop(self, i:int=-1) -> 'Node':
        return self.removeChild(self.childNodes[i])

    def remove(self, x:Any=None) -> 'Node':
        """Remove all members (child nodes) that match x.
        """
        if len(self.childNodes) == 0: return None
        for ch in self.childNodes:
            if ch._isOfValue(x): self.removeChild(ch)

    def removeNode(self) -> 'Node':
        """Remove the node itself from its parentNode, unlinking as needed.
        """
        if self.parentNode is None:
            raise HReqE(f"No parent in removeNode for {self.nodeName}.")
        return self.parentNode.removeChild(self)

    def removeChild(self, oldChild:Union['Node', int]) -> 'Node':  # PlainNode
        """Disconnect oldChild from this node, removing it from the tree,
        but not fromm the document. To destroy it, it should also unlinked.
        Namespaces are copied, not cleared (may be if/when re-inserted somewhere).
        All removals end up here.
        """
        if isinstance(oldChild, Node):
            if oldChild.parentNode != self: raise HReqE(
                f"Node to remove (a {oldChild.nodeName}) has wrong parent.")
        elif not isinstance(oldChild, int): raise HReqE(
            f"Child to remove is not a Node or int, but a {oldChild.type}.")
        oNum, oChild = self._expandChildArg(oldChild)
        del self.childNodes[oNum]
        oChild.parentNode = None

        if _siblingImpl == SiblingImpl.PARENT:
            pass
        elif _siblingImpl == SiblingImpl.CHNUM:
            for sibNum in range(self._childNum+1, len(self.parentNode.childNodes)):
                self.parentNode.childNodes[sibNum]._childNum = sibNum
            self._childNum = None
        elif _siblingImpl == SiblingImpl.LINKS:
            nSib = oldChild._nextSibling
            pSib = oldChild._previousSibling
            if nSib: nSib._previousSibling = pSib
            if pSib: pSib._nextSibling = nSib
            oldChild._previousSibling = oldChild._nextSibling = None
        else:
            raise DOMException(f"_siblingImpl got toasted: {repr(_siblingImpl)}.")

        if oChild.isElement: oChild._resetinheritedNS()
        return oChild

    # "del" can't just do a plain delete, 'cuz unlink. TODO: Enable del?
    #def __delitem__(self, i:int) -> None:
    #    self.removeChild(self.childNodes[i])

    def unlink(self, keepAttributes:bool=False) -> None:  # MINIDOM
        """Break all internal references in the subtree, to help gc.
        But with keepAttributes=True, it will unlink them instead.
        Element overrides this to unlink attrs and childNodes, too.
        """
        self.ownerDocument    = None
        self.parentNode       = None
        # TODO Is following redundant b/c of removeChild?
        if _siblingImpl == SiblingImpl.PARENT:
            pass
        elif _siblingImpl == SiblingImpl.CHNUM:
            self._childNum = None
        elif _siblingImpl == SiblingImpl.LINKS:
            self._previousSibling = None
            self._nextSibling = None
        else:
            raise DOMException(f"_siblingImpl got toasted: {repr(_siblingImpl)}.")

    def writexml(self, writer:IO,
        indent:str="", addindent:str="", newl:str="",
        encoding:str=None, standalone:bool=None) -> None:  # Node
        fo=FormatOptions(indent=addindent, newl=newl)
        writer.write(self.toprettyxml(fo=fo) or "")

    ### Python list operations (PlainNode)

    def count(self, x:Any) -> int:
        found = 0
        for ch in self.childNodes:
            assert isinstance(ch, Node)
            if ch._isOfValue(x): found += 1
        return found

    def index(self, x:Any, start:int=None, end:int=None) -> int:
        """Find the first child in [start:end] that satisfies x.
        If x is a Callable, it should take Node and return bool.
        """
        if start is None: start = 0
        elif start < 0: start = len(self.childNodes) + start
        if end is None: end = len(self.childNodes)
        elif end < 0: end = len(self.childNodes) + end
        if end > len(self.childNodes): end = len(self.childNodes)
        if end <= start: raise IndexError("index() range out of order.")
        for i in range(start, end):
            if self.childNodes[i]._isOfValue(x): return i
        raise ValueError("'%s' not satisfied in %s '%s' [%d:%d]."
            % (x, self.nodeType, self.nodeName, start, end))

    def _isOfValue(self, value:Any) -> bool:
        """Used by count, index, remove to pick node(s) to work on.
        What *should* the test be? Going with nodeName for now.
        """
        if value is None: return True  # TODO ???
        if callable(value): return value(self)
        if value == "*" and self.nodeType == Node.ELEMENT_NODE: return True
        if value == self.nodeName: return True
        return False

    def _resetinheritedNS(self) -> None:
        """When removed, the node loses parentNode but not ownerDocument, and
        has to retain all namespace dcls actually needed by it or any
        descendants (including attributes). This is a pain, and seems like it
        would require a full subtree search to prune. So we carry them all
        along, then trim duplicates when/if the node is pasted later (pruning
        right at that time still required a search).

        TODO The whole ns override/prune thing on insert().
        """
        if self.nodeType not in [ Node.ELEMENT_NODE, Node.DOCUMENT_NODE ]:
            raise HReqE(f"Don't reset ns on nodeType {self.nodeType}...")
        if self.inheritedNS:
            self.inheritedNS = self.inheritedNS.copy()

    def _filterOldInheritedNS(self, newChild:'Element') -> None:
        """If we're about to insert 'other', it may have inheritedNS left
        from when it was cut. We didn't filter them then since many
        removed nodes will just be discarded. But if we insert, any
        prefixes that the subtree actually uses have to get defined.

        We could search, but for the newChild to have been ok before,
        everything it needs to inherit should already be there in its
        .inheritedNS. So we just copy any of those that are not in the
        context already. BUT, that could propagate unneeded ones. So
        we do not propagate those directly -- we collect them by diffing,
        then if/while the list is not empty we traverse and drop any
        that are not actually referenced.

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

    ### More Python list operations, for PlainNode.
    #
    #def reverse(self) -> None: -- Should just work on superclass.

    def reversed(self) -> NodeList:
        """Create a NodeList of the childNodes in reverse order.
        """
        revCh = NodeList()
        if self.childNodes is not None:
            for cnum in reversed(range(len(self.childNodes))):
                revCh.append(self.childNodes[cnum])
        return revCh

    def sort(self, key:Callable=None, reverse:bool=False) -> None:
        """Sort the childNodes in place.
        """
        nl = NodeList()
        if len(self.childNodes) == 0: return nl
        origLen = len(self.childNodes)
        while len(self.childNodes) > 0:
            ch = self.removeChild(0)
            nl.append(ch)
        assert len(nl) == origLen
        sortedCh = sorted(nl, key=key, reverse=reverse)
        assert len(sortedCh) == origLen
        for ch in nl: self.appendChild(ch)
        assert len(self) == origLen

    def sorted(self, key:Callable=None, reverse:bool=False) -> None:
        """Sort the childNodes into a new Node List.
        NOTE: sorted() returns a plain list, even if called on a subclass.
        I think it makes more sense to return the subclass.
        """
        if len(self.childNodes) == 0: return NodeList()
        nl = NodeList(self.childNodes)
        sortedNL = NodeList(sorted(nl, key=key, reverse=reverse))
        return sortedNL

    # You can't put the identical element into a parent twice.
    # Though you *can* put them into NodeLists.
    # So __add__, __mul__, etc. have to become non-in-place.
    #
    def __mul__(self, x:int) -> 'NodeList':  # PlainNode
        """Well, I guess for completeness... We can't multiple in place
        (well, maybe for 0 or 1), so make a new NodeList.
        """
        if not isinstance(x, int): raise TypeError(
            f"Can't multiply sequence by non-int of type '{type(x)}'")
        newNL = NodeList()
        if x > 0:
            for _ in range(x): newNL.extend(self)
        return newNL

    def __rmul__(self, x) -> 'NodeList':
        return self.__mul__(x)

    def __imul__(self, x) -> 'NodeList':
        """This always has to make a copy...
        """
        raise NSuppE("Can't imul elements, they're already connected.")

    def __add__(self, other) -> 'NodeList':
        """This does not add in place -- it constructs a new NodeList. cf iadd.
        """
        newNL = NodeList()
        newNL.extend(self)
        newNL.extend(other)
        return newNL

    def __iadd__(self, other) -> 'NodeList':
        """This is an inplace add.
        """
        # TODO raise NSuppE("Can't iadd elements, they're already connected.")
        for ch in other:
            if ch.parentNode: ch = ch.cloneNode(deep=True)  # TODO???
            self.appendChild(ch)
        return self

    ### Misc (PlainNode)

    def getInterface(self) -> None:
        raise NSuppE("getInterface: obsolete.")

    def isSupported(self) -> bool:
        raise NSuppE("isSupported: obsolete.")


###############################################################################
#
class Node(PlainNode):
    # whatwgAdditions, EtAdditions, OtherAdditions,
    #CssSelectors,
    #__slots__ = ("nodeType", "nodeName", "ownerDocument", "parentNode")

    def __bool__(self) -> bool:
        """A node can be empty but still meaningful (think hr or br in HTML).
        That is not like 0, [], or {}, and so we want it to test True.

        In so far as one denies what is, one is possessed by what is not,
        the compulsions, the fantasies, the terrors that flock to fill the void.
                                                -- Ursula Le Guin
        """
        if isinstance(self, CharacterData): return bool(self.data)
        if isinstance(self, Attr): return bool(self.nodeValue)
        if isinstance(self, (Element, Document, Node)): return True
        else:
            raise DOMException(f"Unexpected type {type(self)} for bool.")

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
        assert self.ownerDocument == other.ownerDocument
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

    # Additional neighbor properties and synonyms
    #
    @property
    def previous(self) -> 'Node':  # XPATH
        """Find the previous node. If you're first it's your parent;
        otherwise it's your previous sibling's last descendant.
        """
        #dtr.msg("previous: At '%s' (cnum %d), is1st %s.",
        #    self.nodeName, self.getChildIndex(), self.isFirstChild)
        if self.parentNode is None: return None
        if self.isFirstChild: return self.parentNode
        pr = self.previousSibling.rightmost
        if pr is not None: return pr
        return self.previousSibling

    @property
    def next(self) -> 'Node':  # XPATH
        if len(self.childNodes) > 0: return self.childNodes[0]
        cur = self
        while (cur.parentNode is not None):
            if not cur.isLastChild: return cur.nextSibling
            cur = cur.parentNode
        return None

    # These return the whole axis
    #
    @property
    def previousSiblings(self) -> 'NodeList':
        myCNum = self.getChildIndex()
        return NodeList(self.parentNode.childNodes[0:myCNum])
    @property
    def nextSiblings(self) -> 'NodeList':
        myCNum = self.getChildIndex()
        return NodeList(self.parentNode.childNodes[myCNum+1:])
    @property
    def previousNodes(self) -> 'NodeList':
        raise NSuppE("Srsly?")
    @property
    def nextNodes(self) -> 'NodeList':
        raise NSuppE("Srsly?")

    # Equivalents named like XPath axes
    # (unlike the generators, these lack an includeSelf option)
    #
    @property
    def precedingSibling(self) -> 'Node':
        return self.previousSibling
    @property
    def followingSibling(self) -> 'Node':
        return self.nextSibling
    @property
    def preceding(self) -> 'Node':
        return self.previous
    @property
    def following(self) -> 'Node':
        return self.next
    @property
    def precedingSiblings(self) -> 'NodeList':
        return self.previousSiblings
    @property
    def followingSiblings(self) -> 'NodeList':
        return self.nextSiblings
    @property
    def precedingNodes(self) -> 'NodeList':
        return self.previousNodes
    @property
    def followingNodes(self) -> 'NodeList':
        return self.nextNodes

    # And the rest of XPath-like stuff
    #
    @property
    def parent(self) -> 'Node':
        return self.parentNode
    @property
    def ancestors(self) -> 'NodeList':
        nl = NodeList()
        cur = self.parentNode
        while (cur):
            nl.append(cur)
            cur = cur.parentNode
        return nl
    @property
    def children(self) -> 'NodeList':
        return NodeList(self.childNodes)
    @property
    def descendants(self, nl:NodeList=None) -> 'NodeList':  # TODO Optimize
        if nl is None: nl = NodeList()
        for ch in self.childNodes:
            nl.append(ch)
            ch.descendants(nl)
        return nl

    @property
    def textContent(self) -> str:  # Node
        return None  # Same as DOM says for Document.

    @textContent.setter
    def textContent(self, newData:str) -> None:  # Node
        raise NSuppE(
            f"Cannot set textContent on Node of type {self.nodeType}.")

    def compareDocumentPosition(self, other:'Node') -> int:  # DOM3
        """Returns -1, 0, or 1 to reflect relative document order.
        Two different nodes cannot be in the same places, nor the same node
        in two different places (like, say, electrons). Therefore, for
        equality it's enough to test identity instead of position.

        XPointers are good for this except that getChildIndex() can be O(fanout).

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
        try:
            return len(self.attributes) > 0
        except (AttributeError, TypeError):
            return False

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
        """Returns False for either None or [] (Nodes are lists).
        """
        return len(self.childNodes) > 0


    #######################################################################
    # Extras for Node
    #
    def getUserData(self, key:str) -> Any:  # DOM3 but later not
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
        return self.nodeType == Node.ELEMENT_NODE
    @property
    def isAttribute(self) -> bool:
        return self.nodeType == Node.ATTRIBUTE_NODE
    @property
    def isText(self) -> bool:
        return self.nodeType == Node.TEXT_NODE
    isTextNode = isText
    @property
    def isCDATA(self) -> bool:
        return self.nodeType == Node.CDATA_SECTION_NODE
    @property
    def isEntRef(self) -> bool:
        return self.nodeType == Node.ENTITY_REFERENCE_NODE
    isEntityReference = isEntRef
    @property
    def isPI(self) -> bool:
        return self.nodeType == Node.PROCESSING_INSTRUCTION_NODE
    isProcessingInstruction = isPI # b/c DOM.
    @property
    def isComment(self) -> bool:
        return self.nodeType == Node.COMMENT_NODE
    @property
    def isDocument(self) -> bool:
        return self.nodeType == Node.DOCUMENT_NODE
    @property
    def isDocumentType(self) -> bool:
        return self.nodeType == Node.DOCUMENT_TYPE_NODE
    @property
    def isFragment(self) -> bool:
        return self.nodeType == Node.DOCUMENT_FRAGMENT_NODE
    @property
    def isNotation(self) -> bool:
        return self.nodeType == Node.NOTATION_NODE

    @property
    def isWSN(self) -> bool:
        return (self.nodeType == Node.TEXT_NODE
        and (not self.data or self.data.isspace()))  # TOTO WSDefs
    @property
    def isWhitespaceInElementContent(self) -> bool:
        return (self.nodeType == Node.TEXT_NODE
        and (not self.data or self.data.isspace())  # TOTO WSDefs
        and self.parent.hasSubElements)

    # TODO isEmpty?

    @property
    def isFirstChild(self) -> bool:  # HERE
        """Don't do a full getChildIndex() if this is all you need.
        When _siblingImpl is set there may be slightly fast ways,
        but this is fast enough and always works.
        """
        if self.parentNode is None: return False
        return (self.parentNode.childNodes[0] is self)

    @property
    def isLastChild(self) -> bool:  # HERE
        if self.parentNode is None: return False
        return (self.parentNode.lastChild is self)

    @property
    def hasSubElements(self) -> bool:  # HERE
        if len(self.childNodes) == 0: return False
        for ch in self.childNodes:
            if ch.nodeType == Node.ELEMENT_NODE: return True
        return False

    @property
    def hasTextNodes(self) -> bool:  # HERE
        if len(self.childNodes) == 0: return False
        for ch in self.childNodes:
            if ch.nodeType == Node.TEXT_NODE: return True
        return False

    @property
    def firstChild(self) -> 'Node':
        if len(self.childNodes) == 0: return None
        return self.childNodes[0]

    @property
    def lastChild(self) -> 'Node':
        if len(self.childNodes) == 0: return None
        return self.childNodes[-1]

    @property
    def leftmost(self) -> 'Node':  # HERE
        """Deepest descendant along left branch of subtree  (never self).
        """
        if len(self.childNodes) == 0: return None
        cur = self
        while len(cur.childNodes) > 0: cur = cur.childNodes[0]
        return cur

    @property
    def rightmost(self) -> 'Node':  # HERE
        """Deepest descendant along right branch of subtree (never self).
        """
        if len(self.childNodes) == 0: return None
        cur = self
        while len(cur.childNodes) > 0: cur = cur.childNodes[-1]
        return cur

    def changeOwnerDocument(self, otherDocument:'Document') -> None:
        """Move a subtree to another document. This requires deleting it, too.
        """
        if self.parentNode is not None: self.removeNode()
        #self.unlink(keepAttributes=True)
        for node in self.eachNode(attrs=True):
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

    def toxml(self, indent:str="", newl:str="", encoding:str="",
        fo:FormatOptions=None) -> str:  # Node
        #import pudb; pudb.set_trace()
        return self.toprettyxml(indent=indent, newl=newl, encoding=encoding, fo=fo)

    def toprettyxml(self, indent:str='\t', newl:str='\n', encoding:str="utf-8",
        standalone=None, fo:FormatOptions=None) -> str:
        return FormatXml.toprettyxml(node=self, indent=indent,
            newl=newl, encoding=encoding, standalone=standalone, fo=fo)

    def tocanonicalxml(self) -> str:  # HERE
        return self.toprettyxml(fo=FormatOptions.getCanonicalFO())


    #######################################################################
    # Paths, pointers, etc. (Node)  TODO: Move to ranges
    #
    def getNodePath(self, useId:str=None, attrOk:bool=False, wsn:bool=True) -> str:  # XPTR
        steps = self.getNodeSteps(useId=useId, attrOk=attrOk, wsn=wsn)
        if not steps: return None
        return "/".join([ str(step) for step in steps ])

    def getNodeSteps(self, useId:bool=False, attrOk:bool=False, wsn:bool=True) -> List:
        """Get the child-number path to the node, as a list.  # XPTR
        At option, start it at the nearest ID (given an attr name for ids).
        Attributes yield the ownerElement unless 'attrOk' is set.
        """
        if self.nodeType == PlainNode.ABSTRACT_NODE:
            raise NSuppE("No paths to abstract Nodes.")
        cur = self
        f = []
        if self.isAttribute:
            if attrOk: f.insert(0, f"@{self.name}")
            cur = self.ownerElement
        while (cur is not None):
            if useId:
                anode = self.idHandler.getIdAttrNode(cur)
                if anode:
                    f.insert(0, anode.nodeValue)
                    break
            if cur.parentNode is None:
                f.insert(0, 1)
            elif wsn:
                f.insert(0, cur.getChildIndex() + 1)
            else:
                f.insert(0, cur.getChildIndex(noWSN=True) + 1)
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
                raise HReqE(f"Leading id '{steps[0]}' of path not found.") from e
            startAt = 1

        for i in range(startAt, len(steps)):
            # TODO support @aname?
            try:
                cnum = int(steps[i])
            except ValueError as e:
                raise HReqE(f"Non-integer in path: {steps}") from e
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

    # Generators (cf XPath)
    # TODO ? each desc, prec, foll, attr
    #
    @staticmethod
    def _isExcluded(node:'Node', excludeNodeNames:List) -> bool:
        """Help the following generators do node-exclusion as requested.
        """
        if not excludeNodeNames: return False
        if node.nodeName in excludeNodeNames: return True
        if not node.isElement:
            if "#" in excludeNodeNames: return True
            if (node.isText and "#wsn" in excludeNodeNames
                and node.data.strip()==""): return True
        return False

    def eachAncestor(self, excludeNodeNames:List=None, includeSelf:bool=False) -> 'Node':
        if isinstance(excludeNodeNames, str):  # HERE
            excludeNodeNames = excludeNodeNames.split()
        cur = self if includeSelf else self.parentNode
        while (cur):
            if not self._isExcluded(cur, excludeNodeNames): yield cur
            cur = cur.parentNode
        return None

    def eachChild(self, excludeNodeNames:List=None, includeSelf:bool=False) -> 'Node':
        if isinstance(excludeNodeNames, str):  # HERE
            excludeNodeNames = excludeNodeNames.split()
        if (includeSelf
            and not self._isExcluded(self, excludeNodeNames)): yield self
        if self.childNodes is None:
            return None
        for node in self.childNodes:
            if not node._isExcluded(node, excludeNodeNames): yield node
        return None

    def eachNode(self, attrs:bool=False,
        excludeNames:Union[List,str]=None, includeSelf:bool=False) -> 'Node':  # HERE
        """Generate all descendant nodes in document order.
        Don't include attribute nodes unless asked.
        @param exclude: Filter out any nodes whose names are in the list
        (their entire subtrees are skipped). #text, #cdata, #pi, "#" are ok.
        """
        if isinstance(excludeNames, str):
            excludeNames = excludeNames.split()

        if (includeSelf and not self._isExcluded(self, excludeNames)):
            yield self
            if attrs and self.isElement and self.attributes:
                for anode in self.attributes.values(): yield anode

        if self.isDocument: childList = self.documentElement
        elif self.isElement: childList = self.childNodes
        else: return

        if childList:
            for ch in childList:
                for chEvent in ch.eachNode(attrs=attrs,
                    excludeNames=excludeNames, includeSelf=True):
                    yield chEvent

        return


    def eachSaxEvent(self, attrTx:str="PAIRS",
        excludeNames:Union[List,str]=None) -> Tuple:  # HERE
        """Generate a series of SAX events as if subtree were being parsed.
        Each even is a tuple of a SaxEvent plus args:
            (INIT, )
            (START   name:str    attrname:str attrvalue:str,..., )
                (you can also request one event per attribute:
                    ATTRIBUTE   attrname:str attrvalue:str
            (END     name:str, )
            (CDATASTART, )
            (CHAR    text:str, )
            (CDATAEND, )
            (COMMENT text:str, )
            (PROC    target:str  data:str, )
            (FINAL, )

        Attributes can be handed back as any of:
            "PAIRS"  -- as 2n arguments on START
            "DICT"   -- as a single dict argument on START
            "EVENTS" -- as separate ATTRIBUTE events

        """
        if (attrTx not in [ "PAIRS", "DICT", "EVENTS" ]): raise DOMException(
            "Unknown attrTx value '{attrTx}'.")
        if isinstance(excludeNames, str):
            excludeNames = excludeNames.split()

        yield (SaxEvent.DOC, )
        for se in self.eachSaxEvent_R(attrTx=attrTx, excludeNames=excludeNames):
            #dtr.msg("SE: %s", repr(se))
            yield se
        yield (SaxEvent.DOCEND, )
        return

    def eachSaxEvent_R(self:'Node',
        attrTx:str, excludeNames:Union[List,str]) -> Tuple:  # HERE
        if excludeNames:
            if self.nodeName in excludeNames: return
            if "#" in excludeNames and not self.isElement: return
            if ("#wsn" in excludeNames
                and self.nodeName==RWord.NN_TEXT
                and self.data.strip()==""): return

        if self.nodeType == Node.ELEMENT_NODE:
            if not self.attributes:
                yield (SaxEvent.START, self.nodeName)
            elif attrTx == "EVENTS":
                yield (SaxEvent.START, self.nodeName)
                for k in self.attributes.keys():
                    yield (SaxEvent.ATTRIBUTE, k, self.getAttribute(k))
                if self.declaredNS:
                    for k in self.declaredNS:
                        yield (SaxEvent.ATTRIBUTE,
                            RWord.NS_PREFIX+k, self.getAttribute(k))
            elif attrTx == "DICT":
                adict = {}
                for k in self.attributes.keys():
                    adict[k] = self.getAttribute(k)
                yield (SaxEvent.START, self.nodeName, adict)
            elif attrTx == "PAIRS":
                vals = [ SaxEvent.START, self.nodeName ]
                for k in self.attributes.keys():
                    vals.append(k)
                    vals.append(self.getAttribute(k))
                if self.declaredNS:
                    for k in self.declaredNS:
                        vals.append(RWord.NS_PREFIX+k)
                        vals.append(self.getAttribute(k))
                yield tuple(vals)
            else:
                raise DOMException(f"Unexpected attrTx {attrTx}.")

            if self.childNodes is not None:
                for ch in self.childNodes:
                    for chEvent in ch.eachSaxEvent_R(
                        attrTx=attrTx, excludeNames=excludeNames):
                        yield chEvent
            yield (SaxEvent.END, self.nodeName)

        elif self.nodeType == Node.TEXT_NODE:
            yield (SaxEvent.CHAR, self.data)

        elif self.nodeType == Node.COMMENT_NODE:
            yield (SaxEvent.COMMENT, self.data)

        elif self.nodeType == Node.CDATA_SECTION_NODE:
            yield (SaxEvent.CDATASTART, )
            yield (SaxEvent.CHAR, self.data)
            yield (SaxEvent.CDATAEND, )

        elif self.nodeType == Node.PROCESSING_INSTRUCTION_NODE:
            yield (SaxEvent.PROC, self.target, self.data)

        elif self.nodeType == Node.DOCUMENT_NODE:
            for chEvent in self.documentElement.eachSaxEvent_R(
                attrTx=attrTx, excludeNames=excludeNames):
                yield chEvent

        else:
            raise DOMException(f"Unexpected nodeType {self.nodeType}.")

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
        # Document and Element do their own deep handling, so no 'deep' here.
        assert isinstance(self.nodeType, int)
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

        # For the alternative sibling implementations:
        if self.parentNode is not None:
            if hasattr(self, "_childNum"):
                assert self._childNum == self.getChildIndex()
            elif hasattr(self, "_previousSibling"):
                assert hasattr(self, "_nextSibling")
                if self._previousSibling is not None:
                    assert self._previousSibling._nextSibling == self
                if self._nextSibling is not None:
                    assert self._nextSibling._previousSibling == self

    # End class Node


###############################################################################
# Cf https://developer.mozilla.org/en-US/docs/Web/API/Document
#
class Document(Node):
    def __init__(
        self,
        namespaceURI:str=None,
        qualifiedName:NMTOKEN_t=None,
        doctype:'DocumentType'=None,
        isFragment:bool=False
        ):
        super().__init__(ownerDocument=None, nodeName=qualifiedName)

        self.nodeType           = Node.DOCUMENT_NODE
        self.nodeName           = qualifiedName
        #self.namespaceURI      = namespaceURI
        self.inheritedNS  = { }
        if namespaceURI:
            self.inheritedNS[""] = namespaceURI
        self.doctype            = doctype
        self.documentElement    = None
        if qualifiedName:
            if not Rune.isXmlQName(qualifiedName):
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
        self.schemeHandlers     = {}  # See registerFilterScheme()
        self.idHandler          = IdHandler(self)  # Lazy build
        self.loadedFrom         = None
        self.uri                = None
        self.mimeType           = 'text/XML'

    def clear(self) -> None:
        raise NSuppE("No clear() on Document nodes.")

    def _updateChildSiblingImpl(self, which:SiblingImpl=SiblingImpl.PARENT) -> None:
        """Change the sibling implementation method.
        Methods that check it:
            previousSibling, nextSibling, insert,
        """
        if not self.documentElement: return None

        _siblingImpl = SiblingImpl.PARENT
        if which == SiblingImpl.PARENT:
            self.documentElement._siblingsByParent()
        elif which == SiblingImpl.CHNUM:
            self.documentElement._siblingsByChildNum()
            _siblingImpl = SiblingImpl.CHNUM
        elif which == SiblingImpl.LINKS:
            self.documentElement._siblingsByLink()
            _siblingImpl = SiblingImpl.LINKS
        else:
            raise DOMException(f"Unrecognized siblingImpl '{which}'.")

    def _siblingsByParent(self) -> None:
        if hasattr(self, "_childNum"): delattr(self, "_childNum")
        if hasattr(self, "_previousSibling"): delattr(self, "_previousSibling")
        if hasattr(self, "_nextSibling"): delattr(self, "_nextSibling")
        if (self.childNodes):
            for ch in self.childNodes: ch._siblingsByParent()

    def _siblingsByChildNum(self) -> None:
            if hasattr(self, "_previousSibling"): delattr(self, "_previousSibling")
            if hasattr(self, "_nextSibling"): delattr(self, "_nextSibling")
            setattr(self, "_childNum", self.getChildIndex())
            if (self.childNodes):
                for ch in self.childNodes: ch._siblingsByChildNum()

    def _siblingsByLink(self) -> None:
            if hasattr(self, "_childNum"): delattr(self, "_childNum")
            setattr(self, "_previousSibling", self.previousSibling)
            setattr(self, "_nextSibling", self.nextSibling)
            if (self.childNodes):
                for ch in self.childNodes: ch._siblingsByLink()

    def insert(self, i:int, newChild:'Element') -> None:  # Document
        """There's no structural reason to limit to one element in Document,
        jsut that DOM says so. We'd get DocumentFragment for free,
        and the XML parser (if one is involved at all!) could still
        enforce that restriction. Document could also just be an Element.
        """
        if len(self.childNodes) > 0:
            raise HReqE("Can't insert child to Document, already contains [ %s ]."
                % (", ".join(x.nodeName for x in self.childNodes)))
        if not newChild.isElement: raise HReqE(
                f"Document element must not be a {newChild.nodeType.__name__}.")
        super().insert(i, newChild)
        self.documentElement = newChild

    def initOptions(self) -> SimpleNamespace:  # HERE
        return SimpleNamespace(**{
            "parser":         "lxml", # Default parser to use

            "ElementCase":    None,  # None, CaseHandler, Normalizer
            "AttributeCase":  None,  #                                # TODO
            "IdCase":         None,  # (pass to idhandler calls)      # TODO
            "EntityCase":     None,  # (to xsparser?)                 # TODO
            "NSURICase":      None,  #                                # TODO

            "NameTest":       None,  # None or a NameTest enum        # TODO

            "attributeTypes": False, # Attribute datatype check/cast  # TODO
            "xsdTypes":       True,  # impl option                    # TODO

            # API extensions
            "getItem":        True,  # Overload [] for child selection
            "CSSSelectors":   False, # Support CSS selectors          # TODO
            "XPathSelectors": False, # Support XPath selectors        # TODO
            "whatwgStuff":    True,  # Support whatwg calls           # TODO
            "BSStuff":        False, # Support bsoup/etree calls      # TODO

            # Namespace options
            "IdNameSpaces":   False, # Allow ns prefixes on ID values # TODO
            "ns_global":      False, # Limit ns dcls to doc element   # TODO
            "ns_redef":       True,  # Allow redefining a ns prefix?  # TODO
            "ns_never":       False, # No namespaces please           # TODO

            # Syntax extensions -- see xsparser
        })

    def setOption(self, k:str, v:Any):  # Document
        try:
            getattr(self.options, k)
        except AttributeError as e:
            raise KeyError(f"Document: unknown option '{k}'.") from e
        if (k.endswith("Case") and v is not None
            and not isinstance(v, ( CaseHandler, Normalizer ))):
            raise TypeError(f"Document: Bad value type {type(v)} for option '{k}'.")
        setattr(self.options, k, v)

    def getOption(self, k:str) -> Any:
        try:
            return getattr(self.options, k)
        except AttributeError as e:
            raise KeyError(f"Document: unknown option '{k}'.") from e

    def registerFilterScheme(self, name:NMTOKEN_t, handler:Callable) -> None:
        """Add a named scheme to be supported within []. The handler
        must take a Node and return a NodeList of selected child nodes,
        based on some selector string defined per sheme.
        For example:
            myNode["css:#chap_3"]
            myNode["xptr:chap_3/5/7/1"]
            myNode["xpath://footnote[@class='ref']"]
        """
        if not Rune.isXmlNCName(name): raise ICharE(
            f"Name for filter scheme in not an NCNAME: '{name}'.")
        if not callable(handler): raise TypeError(
            f"Hander for filter scheme '{name}' is {type(handler)}, not callable.")
        self.schemeHandlers[name] = handler

    @property
    def textContent(self) -> str:  # Document
        return None  # So says DOM...

    @textContent.setter
    def textContent(self, newData:str) -> None:  # Document
        raise NSuppE("textContent setter on Document")  # ???

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
        namespaceURI:str=None,
        qualifiedName:str="frag",
        doctype:str=None,
        isFragment:bool=True
        ) -> 'Document':
        df = Document(
            namespaceURI=namespaceURI,
            qualifiedName=qualifiedName, doctype=doctype, isFragment=True)
        df.isFragment = True
        return df

    def createAttribute(self, name:NMTOKEN_t, value:str=None, parentNode:Node=None) -> 'Attr':
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
    Element = createElement  # WHATWG?
    Attr = createAttribute  # WHATWG
    Text = createTextNode  # WHATWG
    Comment = createComment  # WHATWG
    CDATA = createCDATASection  # WHATWG
    PI = createProcessingInstruction   # WHATWG+HERE
    EntRef = createEntityReference  # WHATWG+HERE

    def writexml(self, writer:IO, indent:str="", addindent:str="", newl:str="",
        encoding:str=None, standalone:bool=None) -> None:  # Document  # MINIDOM
        assert encoding in [ None, "utf-8" ]
        if encoding is None: encoding = "utf-8"
        writer.write(self._getXmlDcl(encoding, standalone))
        if self.documentElement:
            self.documentElement.writexml(
                writer, indent, addindent, newl, encoding, standalone)

    def _getXmlDcl(self, encoding:str="utf-8", standalone:str=None) -> str:
        sa = ""
        if not standalone:
            if self.standalone in [ "yes", "no" ]:
                sa = f' standalone="{self.standalone}"'
        else:
            assert standalone in [ "yes", "no" ]
            sa = f' standalone="{standalone}"'
        return (f'<?xml version="1.0" encoding="{encoding}"{sa}?>')

    @property
    def xmlDcl(self) -> str:  # Document  # HERE
        return self._getXmlDcl(encoding=self.encoding)

    @property
    def doctypeDcl(self) -> str:  # Document  # HERE
        if self.doctype: return self.doctype.outerXml
        return f"<!DOCTYPE {self.documentElement.nodeName} []>"

    def buildIndex(self, enames:List=None, aname:NMTOKEN_t=None) -> None:
        """Build an index of all values of the given named attribute
        on the given element name(s). If ename is empty, all elements.
        """
        if enames is None: enames = [ "*" ]
        elif not isinstance(enames, Iterable): enames = [ enames ]
        for ename in enames:
            if ename != "*" and not Rune.isXmlNMTOKEN(ename): raise ICharE(
                f"Bad element name '{ename}' for buildIndex.")

        if not aname: aname = "id"
        elif not Rune.isXmlQName(aname): raise ICharE(
                f"Bad attribute name '{aname}' for buildIndex.")

        for ename in enames:
            self.idHandler.addAttrChoice(
                ens="##any", ename=ename, ans="##any", aname=aname)
        self.idHandler.buildIdIndex()

    def getElementById(self, idValue:str) -> Node:  # HTML
        return self.idHandler.getIndexedId(idValue)

    def getElementsByTagName(self, name:str) -> Node:  # HTML
        return self.documentElement.getElementsByTagName(name)  # TODO ????

    def getElementsByClassName(self, name:str, attrName:str="class") -> Node:  # HTML
        return self.documentElement.getElementsByClassName(name, attrName=attrName)

    def checkNode(self, deep:bool=True) -> None:  # Document  # DBG
        super().checkNode(deep=False)
        assert self.nodeType == Node.DOCUMENT_NODE
        assert Rune.isXmlQName(self.nodeName)
        assert self.parentNode is None
        assert not hasattr(self, "attributes")
        assert self.previousSibling is None and self.nextSibling is None
        if self.documentElement is not None:
            assert self.documentElement.isElement
            assert Rune.isXmlQName(self.documentElement.nodeName)
            if deep: self.documentElement.checkNode(deep)

    def containerize(self) -> None:
        """Take a document that has only headings, and not section containers,
        and fix it up.
        """
        pass  # TODO Finish containerize()

    # End class Document


###############################################################################
# Element
#
class Element(Node):
    """DOM Level 2 Core.
    https://www.w3.org/TR/2000/REC-DOM-Level-2-Core-20001113/core.html
    https://docs.python.org/2/library/xml.dom.html#dom-element-objects
    """
    def __init__(self, ownerDocument:Document=None, nodeName:NMTOKEN_t=None):
        super().__init__(ownerDocument, nodeName)
        self.nodeType:int = Node.ELEMENT_NODE
        self.attributes:'NameNodeMap' = None
        self.inheritedNS:dict = None
        self.declaredNS:dict = None
        self.prevError:str = None  # Mainly for isEqualNode

    def _addNamespace(self, name:str, uri:str="") -> None:
        """Add the given ns def to this Element. Most elements just inherit,
        so they just get a ref to their parent's defs. But when one is added,
        a copy is created (even if the ns is already on the parent, b/c
        adding a ns explicitly is different than just inheriting).
        NOTE: It might be cleaner (though slower) to just run up the
        ancestors when needed (say, using getInheritedAttribute()).
        """
        prefix, _, local = name.partition(":")
        if not local:
            local = prefix; prefix = ""
        if prefix not in [ "", RWord.NS_PREFIX ]:
            raise ICharE(
                f"_addNamespace: Invalid prefix in '{name}' -> '{uri}'.")
        if not (local == "" or Rune.isXmlName(local)):
            raise ICharE(
                f"_addNamespace: Invalid local part in '{name}' -> '{uri}'.")

        if self.inheritedNS is None:
            self.inheritedNS = { }
        elif (self.parentNode and self.inheritedNS is self.parentNode.inheritedNS):
            self.inheritedNS = self.parentNode.inheritedNS.copy()
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
                newNode.setAttribute(k, self.attributes[k].nodeValue)

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
        return Rune.getPrefixPart(self.nodeName)
    @property
    def localName(self) -> str:
        return Rune.getLocalPart(self.nodeName)
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

    def isEqualNode(self, n2:'Node') -> bool:  # Element  # DOM3
        """To help with debugging, versioning, etc. if the nodes differ
        we stash the reason/location in self.
        """
        if n2 is None: return False  # What minidom does for isSameNode(None).
        if not isinstance(n2, Node):
            raise HReqE(f"Other for isEqualNode is not a Node, but {type(n2)}.")
        dtr.msg(f"isEqualNode for name {self.nodeName} vs. {n2.nodeName}")
        #import pudb; pudb.set_trace()
        if self.isElement and n2.isElement:
            dtr.msg(f"###{self.toxml()}###\n###{n2.toxml()}###")
        if not super().isEqualNode(n2):
            dtr.msg("Element super() tests found unequal.")
            return False

        if len(self) != len(n2):
            dtr.msg(f"len unequal ({len(self)} vs. {len(n2)}.")
            return False

        # Careful, OrderedDict eq would test order, which we don't want.
        # TODO Should actually resolve ns to compare.
        if not self.attributes and not n2.attributes:
            pass  # That's a match (even None vs. {})
        elif not self.attributes or not n2.attributes:
            dtr.msg("Somebody's got no attributes.")
            return False
        elif len(self.attributes) != len(n2.attributes):
            dtr.msg("Unequal number of attrs.")
            return False
        else:
            # Because they have the same number of attrs, this suffices:
            for k in self.attributes:
                if self.getAttribute(k) != n2.getAttribute(k):
                    dtr.msg("Attribute '%s' differs: '%s' vs. '%s'."
                        % (k, self.getAttribute(k), n2.getAttribute(k)))
                    return False

        for i, ch in enumerate(self.childNodes):
            # TODO report depth somehow to _dtrace
            if not ch.isEqualNode(n2.childNodes[i]):
                dtr.msg(f"child #{i} ({ch.nodeName}) unequal.")
                return False
        return True


    ###########################################################################
    # Manage attributes. They are a Dict (or None), keyed by nodeName.
    # The value is the whole Attr instance.

    ### Attribute plain
    #
    def _findAttr(self, ns:str, aname:NMTOKEN_t) -> 'Attr':
        """All(?) attribute stuff goes through here.
        """
        if not aname or not Rune.isXmlQName(aname):
            raise ICharE(f"Attr name '{aname}' not an XML QName.")
        if not self.attributes: return None
        if aname in self.attributes: # If total match, we're ok. (?)
            return self.attributes[aname]
        if ":" in aname:
            _nsPrefix, _colon, lname = aname.partition(":")
        else:
            _nsPrefix = None; lname = aname
        for _k, anode in self.attributes.items():
            if anode.localName != lname: continue
            if not ns or ns == RWord.NS_ANY: return anode
            if anode.namespaceURI == ns: return anode
        return None

    def _presetAttr(self, aname:str, avalue:str) -> None:
        """Common precursor for all methods that add/set attributes.
        """
        if not Rune.isXmlQName(aname):
            raise ICharE(f"Attr name '{aname}' not an XML QName.")
        if self.attributes is None:
            self.attributes = NamedNodeMap(
                ownerDocument=self.ownerDocument, parentNode=self)
        if aname.startswith(RWord.NS_PREFIX+":"):
            self._addNamespace(aname, avalue)
        # TODO Update IdHandler to cover changing attrs
        # TODO Typecast if needed on setting attributes

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
        if castAs: return castAs(anode.nodeValue)
        return anode.nodeValue

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
        self._presetAttr(anode.nodeName, anode.nodeValue)
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
        assert Rune.isXmlName(aname)
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
        assert not ns or ns == RWord.NS_ANY or NameSpaces.isNamespaceURI(ns)
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
        self._presetAttr(anode.nodeName, anode.nodeValue)
        old = self._findAttr(ns=None, aname=anode.nodeName)
        self.attributes.setNamedItem(anode)
        if old is not None: old.parentNode = None
        return old

    def getAttributeNodeNS(self, ns:str, aname:NMTOKEN_t) -> 'Attr':
        NameSpaces.isNamespaceURI(ns, require=True)
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

    def getInheritedAttributeNS(self:Node,
        ns:str, aname:NMTOKEN_t, default:Any=None) -> 'Attr':  # HERE
        NameSpaces.isNamespaceURI(ns, require=True)
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
        return od.getElementById(IdValue)

    def getElementsByClassName(self, name:str, attrName:str="class",
        nodeListNodEList=None) -> NodeList:
        """Works even if it's just one of multiple class tokens.
        """
        if nodeList is None: nodeList = NodeList()
        if self.nodeType != Node.ELEMENT_NODE: return nodeList
        if self.hasAttribute(attrName) and name in self.getAttribute(attrName).split():
            nodeList.append(self)
        for ch in self.childNodes:
            if not ch.isElement: continue
            ch.getElementsByClassName(name, attrName=attrName, nodeList=nodeList)
        return nodeList

    def getElementsByTagName(self, tagName:NMTOKEN_t, nodeList:NodeList=None) -> NodeList:
        """Search descendants for nodes of the right name, and return them.
        This is on minidom.Element.
        """
        if nodeList is None: nodeList = NodeList()
        if self.nodeType != Node.ELEMENT_NODE: return nodeList
        if NameSpaces.nameMatch(self, tagName, ns=None):
            nodeList.append(self)
        for ch in self.childNodes:
            if not ch.isElement: continue
            ch.getElementsByTagName(tagName, nodeList)
        return nodeList

    def getChildrenByTagName(self, tagName:NMTOKEN_t) -> NodeList:  # HERE
        """Search just direct children for nodes of the right name, and return them.
        TODO Integrate this namematch logic w/ other places!
        """
        nodeList = NodeList()
        if self.nodeType != Node.ELEMENT_NODE: return nodeList
        for ch in self.childNodes:
            if "*" == tagName:
                if not ch.isElement: continue
            elif ":" not in tagName:
                if (tagName != ch.nodeName): continue
            elif not NameSpaces.nameMatch(ch, tagName): continue
            nodeList.append(ch)
        return nodeList

    def getElementsByTagNameNS(self, tagName:NMTOKEN_t,
        namespaceURI:str, nodeList=None) -> NodeList:
        """This is on minidom.Element.
        """
        if not Rune.isXmlQName(tagName):
            raise ICharE("Bad attribute name '%s'." % (tagName))
        if nodeList is None: nodeList = NodeList()
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
        #dtr.msg("Parsed string yields: %s", theWrapper.toxml())

        par = self.parentNode
        while len(theWrapper.childNodes) > 0:
            ch = theWrapper.childNodes[0]
            #dtr.msg("Moving %s", ch.toxml())
            theWrapper.removeChild(ch)
            #ch.changeOwnerDocument(otherDocument=par.ownerDocument)
            par.insertBefore(newChild=ch, oldChild=self)
        newDoc.unlink()
        par.removeChild(self)
        #dtr.msg("Deleted %s", self.toxml())

    @property
    def innerXML(self) -> str:  # Element  # HTML
        if len(self.childNodes) == 0: return ""
        return "".join([ch.toxml() for ch in self.childNodes ])

    @innerXML.setter
    def innerXML(self, xml:str) -> None:  # Element  # HTML
        newDoc = self._string2doc(xml)
        theWrapper = newDoc.documentElement
        while len(self.childNodes) > 0:
            self.removeChild(self.childNodes[0]).unlink()
        while len(theWrapper.childNodes) > 0:
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
        db = DomBuilder(parserClass=expat, domImpl=DOMImplementation())
        newDoc = db.parse_string(f"<wrapper>{xml}</wrapper>")
        if newDoc is None:
            raise ValueError("parse_string failed.")
        assert newDoc.documentElement.nodeName == "wrapper"
        return newDoc

    @property
    def startTag(self) -> str:  # HERE
        """Never produces empty-tags (use _startTag(empty=True) for that).
        """
        return self._startTag()

    def _startTag(self, empty:bool=False, includeNS:bool=False,
        fo:FormatOptions=None) -> str:  # HERE
        """Gets a correct start-tag for the element.
        If 'includeNS' is set, declare all in-scope namespaces even if inherited.
        """
        if not fo: fo = FormatOptions.getDefaultFO()  # TODO Faster to use const
        if self.nodeType != Node.ELEMENT_NODE:
            raise HReqE(f"_startTag request for non-Element {self.nodeType}.")
        #print(f"nn: {self.nodeName}")
        buf = f"<{self.nodeName}"
        if self.attributes:
            ws = fo.ws + fo.indent if (fo.breakAttrs) else " "
            names = self.attributes.keys()
            if fo.sortAttrs:
                names = sorted(names, key=lambda x: ' '+x if x.startswith("xmlns:") else x)
            for k in names:
                v = self.attributes[k].nodeValue
                if fo.normAttrs: v = str(v).strip()  # TODO Extend
                vEsc = FormatXml.escapeAttribute(v, addQuotes=True, fo=fo)
                buf += f'{ws}{k}={vEsc}'
        if includeNS:  # TODO Interleave if sorted
            for k, v in self.inheritedNS.items:
                vEsc = FormatXml.escapeAttribute(v, addQuotes=True, fo=fo)
                buf += f'{ws}{RWord.NS_PREFIX}:{k}={vEsc}'
        return buf + ((fo.spaceEmpty + "/") if empty else "") + ">"

    @property
    def endTag(self) -> str:  # HERE
        if self.nodeType != Node.ELEMENT_NODE:
            raise HReqE(f"_endTag request for non-Element {self.nodeType}.")
        return f"</{self.nodeName}>"

    ### Meta (Element)

    def unlink(self, keepAttributes:bool=False) -> None:  # MINIDOM
        # TODO Delete attributes?
        super().unlink(keepAttributes=keepAttributes)
        if self.attributes:
            for attr in self.attributes.values(): attr.unlink()
            if not keepAttributes: self.attributes = None
        if self.childNodes is not None:
            self.childNodes.clear()

    def checkNode(self, deep:bool=False) -> None:  # Element  # DBG
        super().checkNode(deep=False)

        if self.attributes is not None:
            assert isinstance(self.attributes, NamedNodeMap)
            for aname, anode in self.attributes.items():
                assert isinstance(anode, Attr)
                assert aname == anode.nodeName
                assert not aname.startswith("xmlns:")  # Should be elsewhere
                #nsp = anode.prefix is defined
                anode.checkNode()

        if self.childNodes is not None:
            for i, ch in enumerate(self.childNodes):
                assert isinstance(ch, Node)
                assert ch.nodeType in [
                    Node.ELEMENT_NODE,
                    Node.ATTRIBUTE_NODE,
                    Node.TEXT_NODE,
                    Node.CDATA_SECTION_NODE,
                    Node.ENTITY_REFERENCE_NODE,
                    Node.PROCESSING_INSTRUCTION_NODE,
                    Node.COMMENT_NODE,
                    # docfrag??? entref???
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
    def __init__(self, ownerDocument:Document=None, nodeName:NMTOKEN_t=None):
        super().__init__(ownerDocument, nodeName)
        self.data = None


    def isEqualNode(self, n2) -> bool:  # CharacterData  # DOM3
        if not super().isEqualNode(n2):
            dtr.msg("CharacterData super() tests found unequal.")
            return False
        if self.data != n2.data:
            dtr.msg("CharacterData data mismatch.")
            return False
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
    #
    LeafChildMsg = "CharacterData nodes cannot have children."
    @property
    def firstChild(self) -> Node:
        raise HReqE(CharacterData.LeafChildMsg)
    @property
    def lastChild(self) -> Node:
        raise HReqE(CharacterData.LeafChildMsg)

    @hidden
    def __getitem__(self, *args):  # CharacterData
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
        self.data = None
        return

    def checkNode(self, deep:bool=True) -> None:  # CharacterData (cf Attr):  # DBG
        super().checkNode(deep=False)
        assert self.parentNode is None or self.parentNode.isElement
        #assert self.attributes is None and self.childNodes is None
        if self.isPI: assert Rune.isXmlName(self.target)


###############################################################################
#
class Text(CharacterData):
    def __init__(self, ownerDocument:Document=None, data:str="", inCDATA:bool=False):
        super().__init__(ownerDocument=ownerDocument, nodeName=RWord.NN_TEXT)
        self.nodeType = Node.TEXT_NODE
        self.data = data
        self.inCDATA = inCDATA  # Allow for round-tripping

    def cloneNode(self, deep:bool=False) -> 'Text':
        newNode = Text(ownerDocument=self.ownerDocument, data=self.data)
        if self.userData: newNode.userData = self.userData
        return newNode

    def insertNode(self, node:Node, offset:int) -> None:  # HERE
        """Split the text Node at the given offset, and insert node between.
        """
        if self.parentNode is None: raise HReqE(
            "Cannot insert nodes into an unconnected Text node.")
        if node.parentNode is not None: raise HReqE(
            "Node to insert is already connected.")
        text2 = None
        if offset < len(self.data)-1:
            text2 = self.ownerDocument.createTextNode(self.data[offset:])
            self.data = self.data[0:offset]
            self.parentNode.insertAfter(oldchild=self, newChild=text2)
            self.parentNode.insertAfter(oldchild=self, newChild=node)

    def cleanText(self, unorm:str=None, normSpace:bool=True) -> str: # HERE
        """Apply Unicode normalization and or XML space normalization
        to the text of the node.
        TODO: Upgrade to handle all the UNorm, Case, WS options; dft from doc?
        """
        if unorm: buf =  unicodedata.normalize(unorm, self.data)
        else: buf = self.data
        if normSpace: buf = Rune.normalizeSpace(buf)
        self.data = buf
        return buf

    def tostring(self) -> str:  # Text
        return self.data


###############################################################################
#
class CDATASection(CharacterData):
    """These aren't normally used. For example, DomBuilder catches the SAX
    events for them, but just sets 'inCDATA' on the text nodes inside.
    That way text nodes are always just text nodes, but we can still export
    them as marked sections if desired.
    """
    def __init__(self, ownerDocument:Document, data:str):
        super().__init__(ownerDocument=ownerDocument, nodeName="#cdata-section")
        self.nodeType = Node.CDATA_SECTION_NODE
        self.data = data

    def tostring(self) -> str:  # CDATASection
        return self.data


###############################################################################
#
class ProcessingInstruction(CharacterData):
    def __init__(self, ownerDocument:Document=None,
        target:NMTOKEN_t=None, data:str=""):
        if target is not None and target!="" and not Rune.isXmlName(target):
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

    def isEqualNode(self, n2:Node) -> bool:  # PI  # DOM3
        if not super().isEqualNode(n2):
            dtr.msg("PI super() tests found unequal.")
            return False
        if self.target != n2.target:
            dtr.msg("PI target mismatch.")
            return False
        return True

    def tostring(self) -> str:  # PI
        return self.data

PI = ProcessingInstruction


###############################################################################
#
class Comment(CharacterData):
    def __init__(self, ownerDocument:Document=None, data:str=""):
        super().__init__(ownerDocument=ownerDocument, nodeName="#comment")
        self.nodeType=Node.COMMENT_NODE
        self.data = data

    def cloneNode(self, deep:bool=False) -> 'Comment':
        newNode = Comment(ownerDocument=self.ownerDocument, data=self.data)
        if self.userData: newNode.userData = self.userData
        return newNode

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
    be hooked up with the schema and the entity definition, or dropped.
    """
    def __init__(self, ownerDocument:Node, name:NMTOKEN_t, data:str=""):
        super().__init__(ownerDocument=ownerDocument, nodeName=name)
        if not Rune.isXmlName(name): raise ICharE(
            f"Bad name '{name}' for EntityReference node.")
        self.nodeType = Node.ENTITY_REFERENCE_NODE
        self.data = data

    def tostring(self) -> str:  # EntityReference
        return self.data

EntRef = EntityReference


###############################################################################
#
class Attr(Node):
    """Attrs are different:
        * They cannot be inserted into the tree, only set on an element.
        * They are unordered, accessed by name not position. If pressed re.
          document order, they can be treated as colocated with their element.
        * They have a discrete scalar (or maybe list of scalars) value.
        * They have a parentNode, but are not children or siblings.
        * They inherit namespace prefix definitions, but not the default ns.
        * They (may?) track whether they were explicit or defaulted.
        * They have methods to retrieve either the value, or the Attr object.
          (which is a Dict, not a Node), which then owns the Attr objects.
    TODO namespace support
    TODO way to tunnel defaulting info from xsparser.
    TODO Possibly do casefolding (when requested) only on the key for
    Element.attributes, not on Attr.node/name?
    TODO If options.attributeTypes is set, just when should casting happen?
    """
    def __init__(self, name:NMTOKEN_t, value:Any, ownerDocument:Document=None,
        nsPrefix:NMTOKEN_t=None, namespaceURI:str=None, ownerElement:Node=None,
        attrTypeName:str="string", readOrder:int=None, specified:bool=True):
        if not Rune.isXmlQName(name):
            raise ICharE(f"Bad attribute name '{name}'.")
        if ownerElement is not None and ownerElement.nodeType != Node.ELEMENT_NODE:
            raise TypeError(f"ownerElement for attribute '{name}' "
                "is {ownerElement.nodeType}, not ELEMENT.")

        super().__init__(ownerDocument=ownerDocument, nodeName=name)
        self.nodeType = Node.ATTRIBUTE_NODE
        self._nodeValue = None
        self.ownerDocument = ownerDocument  # TODO Drop?
        self.ownerElement = ownerElement
        self.parentNode = None  # True in DOM, though XPath @foo/parent::element
        self.inheritedNS = None  # Resolved via parent
        self.attrTypeName = attrTypeName
        self.readOrder = readOrder
        self.specified = specified  # Set explicitly, not defaulted. OBS
        self.isId = False

        if attrTypeName:
            if attrTypeName not in XSDDatatypes: raise TypeError(
                f"Unrecognized type name '{attrTypeName}' for Attr '{name}'.")
            try:
                attrTypeDef = XSDDatatypes[attrTypeName]
                pyType = attrTypeDef.pybase or str
                self.nodeValue = pyType(value)
                if self.attrTypeName == "ID":
                    self.isId = True
                elif (idh := self.ownerDocument.idHandler) is not None:
                    self.isId = idh.getIdAttrNode(ownerElement) is self
            except (ValueError, AttributeError):
                self.attrTypeName = None
                self.nodeValue = value  # TODO Cast to str or xsd string?

    def clear(self) -> None:
        raise NSuppE("No clear() on Attr nodes.")

    @property
    def name(self) -> str:
        return self.nodeName
    @property
    def prefix(self) -> str:
        return Rune.getPrefixPart(self.nodeName)
    @property
    def localName(self) -> str:
        return Rune.getLocalPart(self.nodeName)
    @property
    def namespaceURI(self) -> str:
        prefix = Rune.getPrefixPart(self.nodeName)
        if not prefix: return None
        try:
            return self.ownerElement.inheritedNS[prefix]
        except (KeyError, ValueError, TypeError, AttributeError):
            return None

    @property
    def nodeValue(self) -> str:  # Attr
        return self._nodeValue

    @nodeValue.setter
    def nodeValue(self, newData:str="") -> None:  # Attr
        self._nodeValue = newData

    @property
    def isConnected(self) -> bool:  # Attr  TODO Check?
        return False

    @property
    def textContent(self) -> None:  # Attr  # TODO Typecasting?
        return self.nodeValue

    @textContent.setter
    def textContent(self, newData:str) -> None:  # Attr  # TODO Typecasting?
        if self.attrTypeName: newData = self.attrTypeName(newData)  # TODO FIX!
        self.nodeValue = newData

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

    def isEqualNode(self, n2:'Attr') -> bool:  # DOM3
        """Equality of attributes is slightly fraught. If XSD datatypes
        are declared, DOM still compares on strings  If options.attributeTypes
        is set, then we'll need the cast back to string for this (which has
        other issues such as leading zero loss...).
        """
        # Do not test super, Attr is special.
        if not n2.isAttribute:
            msg = f"Node to compare is not also an Attr, but {type(n2)}."
            dtr.msg(msg)
            raise ValueError(msg)
        if not self._nodeNameMatches(n2):
            dtr.msg("Attr nodeName mismatch."
                f"  {self.nodeName}\n  {n2.nodeName}")
            return False
        if str(self.nodeValue) != str(n2.nodeValue):
            dtr.msg("Attr nodeValue mismatch:\n"
                f"  {self.nodeValue}\n  {n2.nodeValue}")
            return False
        return True

    def cloneNode(self, deep:bool=False) -> 'Attr':
        newAttr = Attr(name=self.nodeName, value=self.nodeValue,
            ownerDocument=self.ownerDocument,
            ownerElement=None, attrTypeName=self.attrTypeName)
        return newAttr

    def tostring(self) -> str:  # Attr
        """Attr is not quoted or escaped for this.
        """
        return str(self._nodeValue)

    def checkNode(self, deep:bool=True) -> None:  # Attr  # DBG
        assert self.isAttribute
        if self.ownerDocument is not None:
            assert self.ownerDocument.isDocument
        assert self.parentNode is None
        assert self.inheritedNS is None
        assert "attributes" not in dir(self)
        #assert "data" not in dir(self) and "target" not in dir(self)

        assert Rune.isXmlQName(self.nodeName)
        if self.attrTypeName and self.nodeValue is not None:
            assert isinstance(self.attrTypeName, type)
            assert isinstance(self.nodeValue, self.attrTypeName)
        if self.userData is not None:
            assert isinstance(self.userData, dict)

        if self.ownerDocument and self.ownerElement:
            assert self.ownerDocument == self.ownerElement.ownerDocument
        if self.ownerElement is None: return
        assert self.ownerElement.isElement
        if len(self.ownerElement) == 0: return
        if self in self.ownerElement.childNodes: raise OperationError(
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
    def __init__(self, ownerDocument:Document=None, parentNode:Element=None,
        aname:NMTOKEN_t=None, avalue:Any=None):
        """On creation, you can optionally set an attribute.
        """
        super(NamedNodeMap, self).__init__()
        self.ownerDocument = ownerDocument
        if aname: self.setNamedItem(aname, avalue)

    def __eq__(self, other:NamedNodeMap) -> bool:
        """NOTE: Python considers OrderedDicts unequal if order differs.
        But here we want OrderedDict only for serializing, so...
        """
        return dict(self) == dict(other)

    def __ne__(self, other:NamedNodeMap) -> bool:
        return not (self == other)

    def setNamedItem(self, attrNodeOrName:Union[str, Attr], avalue:Any=None,
        atype:str="string") -> None:
        """This can take either an Attr (as in the DOM version), which contains
        its own name; or a string name and then a value (in which case the Attr
        is constructed automatically).
        Note: This does nothing with types, since those are imposed by context.
        We just let the type info go, and can cast to str() and back if/when
        it's inserted into a new context. But ick.
        """
        if isinstance(attrNodeOrName, Attr):
            if avalue is not None:
                raise ValueError(f"Can't pass both avalue ({avalue}) AND Attr node.")
            if self.ownerDocument is None:
                self.ownerDocument = attrNodeOrName.ownerDocument
            elif attrNodeOrName.ownerDocument is None:
                attrNodeOrName.ownerDocument = self.ownerDocument
            elif attrNodeOrName.ownerDocument != self.ownerDocument:
                raise HReqE("Can't put Attr from different ownerDocument into NamedNodeMap.")
            self[attrNodeOrName.nodeName] = attrNodeOrName
        else:
            if not Rune.isXmlQName(attrNodeOrName): raise ICharE(
                f"Bad item name '{attrNodeOrName}'.")
            anode = Attr(attrNodeOrName, avalue, attrTypeName=atype,
                ownerDocument=self.ownerDocument, ownerElement=None)
            self[anode.nodeName] = anode

    def getNamedItem(self, name:NMTOKEN_t) -> Attr:
        """Per DOM, this returns the entire Attr instance, not just value.
        No exception if absent.
        TODO Anything for namespaces? Prob not since no inheritance needed?
        """
        if name not in self: return None
        theAttr = self[name]
        assert isinstance(theAttr, Attr)
        return theAttr

    def getNamedValue(self, name:NMTOKEN_t) -> Any:  # HERE
        """Returns just the actual value.
        """
        if name not in self: return None
        assert isinstance(self[name], Attr)
        return self[name].nodeValue

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
        NameSpaces.isNamespaceURI(ns, require=True)
        if not Rune.isXmlName(aname):
            raise ICharE("Bad name '%s'." % (aname))
        raise NSuppE("NamedNodeMap.setNamedItemNS")

    def getNamedItemNS(self, ns:str, name:NMTOKEN_t) -> Any:
        NameSpaces.isNamespaceURI(ns, require=True)
        raise NSuppE("NamedNodeMap.getNamedItemNS")

    def getNamedValueNS(self, ns:str, name:NMTOKEN_t) -> Any:  # extension
        NameSpaces.isNamespaceURI(ns, require=True)
        raise NSuppE("NamedNodeMap.getNamedItemNS")

    def removeNamedItemNS(self, ns:str, name:NMTOKEN_t) -> None:
        NameSpaces.isNamespaceURI(ns, require=True)
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

    def writexml(self, writer:IO,
        indent:str="", addindent:str="", newl:str="",
        encoding:str=None, standalone:bool=None) -> None: # MINIDOM
        writer.write(self.tostring())

    def tostring(self) -> str:
        """Produce the complete attribute list as would go in a start tag.
        """
        ks = self.keys()
        if self.ownerDocument and self.ownerDocument.options.sortAttrs:
            ks = sorted(ks)
        buf = ""
        for k in ks:
            buf += f" {k}={FormatXml.escapeAttribute(self[k].nodeValue)}"
        return buf


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
        assert Rune.isXmlName(prefix)
        assert self.isNamespaceURI(uri)
        if prefix in self:
            if self[prefix] == uri: return
            #dtr.msg("Prefix '%s' rebound from '%s' to '%s'.",
            #    prefix, self[prefix], uri)
        super().__setitem__(prefix, uri)

        if uri not in self.uri2prefix:
            self.uri2prefix[uri] = []
        elif self.uri2prefix.contains(uri):
            return
        self.uri2prefix[uri].append(prefix)

    def __delitem__(self, prefix:str) -> None:
        assert Rune.isXmlName(prefix)
        uri = self[prefix]
        del self.uri2prefix[uri]
        super().__delitem__(prefix)

    @staticmethod
    def isNamespaceURI(ns:str, require:bool=False) -> bool:
        """
        Rudimentary check for plausible URI (or ""/None).
        Make sure ##any is covered.
        """
        if not ns or ns == RWord.NS_ANY: return True
        if re.match(r"\w+://", ns): return True
        if require: raise SyntaxError(
            f"Not a recognized namespace: '{ns}'.")
        return False

    @staticmethod
    def nameMatch(node:Node, target:str, ns:str=None) -> bool:
        """Determine whether the node's name matches the target.
        TODO Should this also support #text/#pi/#comment?
        """
        if ":" in target:
            Tprefix, _, Tname = target.partition(":")
            Turi = node.ownerDocument.namespaceIndex[Tprefix]
        else:
            Tprefix = ""
            Tname = target
            Turi = None

        if ns:
            NameSpaces.isNamespaceURI(ns, require=True)
            assert Turi is None or Turi == ns

        if Turi and node.nsURI != Turi: return False
        if Tprefix == "#none":
            if node.prefix: return False
        elif Tprefix:
            if (not re.match(r"^(\*|#all|#any)$", Tprefix, flags=re.I)
                and node.prefix != Turi): return False
        if Tname and node.nodeName != Turi: return False   # TODO use nodeNameMatches
        return True
