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
import logging

import traceback, sys

#from textwrap import wrap
from xml.parsers import expat

from ragnaroktypes import DOMException, HReqE, ICharE, NSuppE, FlexibleEnum
from ragnaroktypes import NamespaceError, NotFoundError, OperationError
from ragnaroktypes import DOMImplementation_P, NMTOKEN_t, QName_t, NodeType, dtr

from saxplayer import SaxEvent
from domenums import RWord
from dombuilder import DomBuilder
from runeheim import XmlStrings as Rune, CaseHandler, Normalizer
from xsdtypes import XSDDatatypes
from idhandler import IdHandler
from prettyxml import FormatOptions, FormatXml

from domadditions import ElementTreeAdditions

lg = logging.getLogger("basedom")

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
        Why are all args required when 2 are often None?
        """
        doc = Document(namespaceURI=namespaceURI,
            qualifiedName=qualifiedName, doctype=doctype)

        if not qualifiedName: return doc

        if not Rune.isXmlQName(qualifiedName):
            raise ICharE(f"Root element to be has bad qname '{qualifiedName}'.")
        prefix = Rune.getPrefixPart(qualifiedName)

        if not prefix:
            doc.documentElement = doc.createElement(qualifiedName)
        else:
            if prefix == "xml" and  namespaceURI not in [ RWord.XML_PREFIX_URI, "", None ]:
                raise NamespaceError(
                    f"URI for xml prefix is not '{RWord.XML_PREFIX_URI}'")
            doc.documentElement = doc.createElementNS(namespaceURI, qualifiedName)
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


class NodeList(list):
    """We pretty much just subclass Python list.
    """
    def __contains__(self, item:'Node') -> bool:  # NodeList
        """Careful, Python and DOM "contains" are different!
        x.__contains__(y) is non-recursive.
        x.contains(y) is recursive, but NodeList != Element anyway.
        What's the best i/f for testing for contained text or regex?
        """
        assert isinstance(item, Node)
        for x in self:
            if x is item: return True
        return False

    def __delitem__(self, item:Union[int, 'Node']) -> None:  # NodeList
        if isinstance(item, Node):
            try:
                item = self.index(item)
            except ValueError as e:
                raise HReqE("Node for __delitem__ is not in NodeList.") from e
            super().__delitem__(item)

    @property
    def textContent(self, sep:str="") -> None:  # NodeList
        """Cat together all the members' text
        """
        if sep is None: sep = ""
        textBuf = ""
        if len(self) > 0:
            for ch in self:
                textBuf += ch.textContent + sep
        return textBuf

    @textContent.setter
    def textContent(self, newData:str) -> None:  # NodeList
        raise NSuppE("Setting textContent is not allowed on NodeList")

    def length(self) -> int:
        return len(self)

    def item(self, index:int) -> 'Node':
        if index < 0: index = len(self) + index
        if index >= len(self): raise IndexError(
            f"NodeList item #{index} out of range ({len(self)}).")
        return self[index]

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
    """Set this on Document to determine how siblings are found.  TODO
    PARENT tests faster than LINKS due to maintenance overhead, unless the
    trees are very wide/bushy. In theory, CHNUM should be faster when the
    tree is not changing much (but changes are slower).
    """
    COUNT = 0   # Scan parent
    CHNUM = 1   # Node maintain their child number
    LINKS = 2   # Doubly-linked siblings


###############################################################################
#
# TODO: Ditch list as a superclass here. Add NodeList as a 2nd superclass
# for Element and Document, but not others. Move all the list operations
# from Yggdrasil into NodeList (or an intermediate subclass??) *MOVE*
#
class Yggdrasil(list):
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

    def __init__(self, ownerDocument:'Document'=None, nodeName:NMTOKEN_t=None):
        """  (and Node) shouldn't really be instantiated.
        minidom lets Node be, but with different parameters.
        I add the params for constructor consistency.
        Also, since here it is a list, there's not much need to distinguish
        Node, NodeList, and DocumentFragment -- mainly that only the first
        has to be the (unique) parentNode of all its members (and therefore
        the determiner of siblings, etc.).
        """
        super().__init__()
        self.ownerDocument = ownerDocument
        self.parentNode = None  # minidom Attr class lacks....
        self.nodeType = Node.ABSTRACT_NODE
        if nodeName and nodeName[0] != "#" and not Rune.isXmlQName(nodeName):
            raise ICharE(f"nodeName '{nodeName}' isn't.")
        self.nodeName = nodeName
        self.inheritedNS = {}
        self.userData = None
        self.prevError:str = None  # Mainly for isEqualNode
        # Sibling count/pointers are only set once inserted into a parentNode.

    @property
    def canHaveChildren(self) -> bool:  # *MOVE*
        return self.nodeType in [
            Yggdrasil.ABSTRACT_NODE,  # TODO Maybe not?
            Yggdrasil.ELEMENT_NODE, Yggdrasil.DOCUMENT_NODE,
            Yggdrasil.DOCUMENT_TYPE_NODE, Yggdrasil.DOCUMENT_FRAGMENT_NODE ]

    def __contains__(self, item:'Node') -> bool:
        """Careful, Python and DOM "contains" are different:
            x.__contains__(y) is non-recursive.
            x.contains(y) is recursive.
        """
        return item.parentNode == self

    def contains(self, other:'Node') -> bool:  # Yggdrasil
        """Overridden by Branchable.
        """
        return False

    def hasDescendant(self, other:'Node') -> bool:  # *MOVE*
        """Provided b/c 'contains' vs. '__contains__' may be confusing.
        """
        return self.contains(other)

    def __filter__(self, f:str) -> Any:
        """Pick some node via a selection mechanism.
        TODO Decide nodeName #text vs. CSS #id
        TODO Should @x return attribute value or (probably) Attr node?
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
            raise ValueError(f"Unrecognized slice syntax '{f}'.")

        if Rune.isXmlName(f):                         # nodeNames
            return self.getChildrenByTagName(f)

        scheme, _colon, schemeData = f.partition(":")
        try:
            sh = self.ownerDocument.sliceHandlers[scheme]
            return sh(self, schemeData)
        except KeyError as e:
            raise TypeError("Unrecognized filter scheme '%s' (known: %s)."
                % (scheme, self.ownerDocument.sliceHandlers.keys())) from e

    def getChildIndex(self, onlyElements:bool=False, ofNodeName:bool=False,
        wsn:bool=True, coalesceText:bool=False) -> int:
        """Return the position in order (from 0), among the node's siblings
        (or selected siblings). This is O(n). It is mainly used when not
        opting to use sibling pointers or explicit _childNum values.
        If self is not an element, it's considered to have position one
        greater than the nearest preceding matching node.
        If 'coalesceText' is set, adjacent text nodes count as 1.
        """
        if self.parentNode is None: return None
        if hasattr(self, "_childNum"): return self._childNum
        i = 0
        for ch in self.parentNode.childNodes:
            if ch is self: return i
            if onlyElements and not ch.isElement: continue
            if ch.isTextNode:
                if coalesceText and ch.nextSibling and ch.nextSibling.isTextNode: continue
                if not wsn and ch.isWSN: continue
            if ofNodeName and not ch._nodeNameMatches(self): continue
            i += 1
        return None

    def getRChildIndex(self, onlyElements:bool=False, ofNodeName:bool=False,
        wsn:bool=True, coalesceText:bool=False) -> int:
        """Return the position from the end (from -1...) among
        all or selected siblings.
        """
        if self.parentNode is None: return None
        if hasattr(self, "_childNum"):
            return self._childNum - len(self.parentNode.childNodes)
        i = -1
        for ch in reversed(self.parentNode.childNodes):
            if ch is self: return i
            if onlyElements and not ch.isElement: continue
            if ch.isTextNode:
                if coalesceText and ch.previousSibling and ch.previousSibling.isTextNode:
                    continue
                if not wsn and ch.isWSN: continue
            if ofNodeName and ch._nodeNameMatches(self): continue
            i -= 1
        #raise HReqE("Child not found.")
        return None

     # Next three are defined here (Yggdrasil), but only work for Element and
     # Attr (though constructors all takes nodeName for consistency...).
    @property
    def prefix(self) -> str:
        return None
    @property
    def localName(self) -> str:
        return None
    @property
    def namespaceURI(self) -> str:
        return None

    #@property
    #def childNodes(self) -> 'Node':
    #    return None

    @property
    def isConnected(self) -> bool:
        """Overridden for Attr nodes. (HTML DOM ONLY)
        """
        if self.ownerDocument is None: return False
        if self.ownerDocument.documentElement is self: return True
        if self.parentNode is None: return False
        return True

    @property
    def nodeValue(self) -> str:  # Yggdrasil
        """null for Document, Frag, Doctype, Element, NamedNodeMap.
        """
        return None

    @nodeValue.setter
    def nodeValue(self, newData:str="") -> None:
        raise NSuppE(
            "Cannot set nodeValue on nodeType %s." % (self.nodeType.__name__))

    @property
    def previousSibling(self) -> 'Node':
        """There are 3 obvious ways to manage siblings:
          * COUNT: scan the parentNode to find where you are
          * CHNUM: each node knows its position in sibling order
          * LINKS: siblings are in a doubly-linked list.
        These have serious tradeoffs depending on the shape of the document,
        how much it's changing, how it's being accessed, etc.
        To change, call _updateChildSiblingImpl() on the Document.
        """
        if self.parentNode is None: return None
        if hasattr(self, "_previousSibling"):
            return self._previousSibling

        if hasattr(self, "_childNum"): n = self._childNum
        else: n = self.getChildIndex()

        if n <= 0: return None
        return self.parentNode.childNodes[n-1]

    @property
    def nextSibling(self) -> 'Node':
        """See also previousSibling().
        """
        if self.parentNode is None: return None
        if hasattr(self, "_nextSibling"):
            return self._nextSibling

        if hasattr(self, "_childNum"): n = self._childNum
        else: n = self.getChildIndex()
        if n >= len(self.parentNode.childNodes) - 1: return None
        return self.parentNode.childNodes[n+1]

    # See class Node for additional neighbor methods and XPath analogs.

    def isSameNode(self, n2) -> bool:
        return self is n2

    def isEqualNode(self, n2) -> bool:  # Node  # DOM3
        """Check the common properties that matter.
        Subclasses may override to check more, but should call this, too!
        See also https://dom.spec.whatwg.org/#concept-node-equals.
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
            dtr.msg(f"nodeType differs ('{self.nodeType}' vs. '{n2.nodeType}').")
            return False
        if not self._nodeNameMatches(n2):
            dtr.msg(f"nodeName differs ('{self.nodeName}' vs. '{n2.nodeName}').")
            return False
        if self.nodeValue != n2.nodeValue:
            dtr.msg("nodeValue differs:\n" +
                f"  ###{self.nodeValue}###\n  ###{n2.nodeValue}###")
            return False
        # Element does additional checks like attributes and childNodes
        return True

    def _nodeNameMatches(self, other:'Node') -> bool:
        """Factor this out b/c with namespaces there can be a match even
        if the prefixes don't match (several could map to the same URI).
        When disconnecting a node keep relevant namespaces with it.
        """
        if (self.ownerDocument and self.ownerDocument.options.elementFold):
            if self.ownerDocument.options.elementFold.strnormcmp(
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

    #### Mutators (Yggdrasil)

    def _expandChildArg(self, ch:Union['Node', int]) -> (int, 'Node'):  # *MOVE*
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

    def normalize(self) -> None:  # *MOVE*
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

    normalizeDocument = normalize  # DOM 3

    def removeNode(self) -> 'Node':
        """Remove the node itself from its parentNode, unlinking as needed.
        """
        if self.parentNode is None:
            raise HReqE(f"No parent in removeNode for a '{self.nodeName}'.")
        return self.parentNode.removeChild(self)

    def unlink(self, keepAttributes:bool=False) -> None:  # MINIDOM
        """Break all internal references in the subtree, to help gc.
        But with keepAttributes=True, it will unlink them instead.
        Element overrides this to unlink attributes and childNodes, too.
        """
        self.ownerDocument = None
        if self.parentNode is not None:
            # self.removeNode()
            raise HReqE("Cannot unlink until you remove the node.")

    def writexml(self, writer:IO,
        indent:str="", addindent:str="", newl:str="",
        encoding:str=None, standalone:bool=None) -> None:  # Node
        fo=FormatOptions(indent=addindent, newl=newl)
        writer.write(self.toprettyxml(fo=fo) or "")

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
            raise HReqE(f"Don't reset ns on nodeType '{self.nodeType}'.")
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

    ### Misc (Yggdrasil)

    def getInterface(self) -> None:
        raise NSuppE("getInterface: obsolete.")

    def isSupported(self) -> bool:
        raise NSuppE("isSupported: obsolete.")


###############################################################################
#
class Node(Yggdrasil):
    """The base class for all the node types. This does NOT include the
    methods and variables needed to support having children or attributes,
    b/c only a few subclasses need them. Those subclasses use multiple
    inheritance to bring in that stuff from Branchable and/or AttributedNode.
    """
    def __init__(self, ownerDocument:'Document'=None, nodeName:NMTOKEN_t=None):
        super().__init__(ownerDocument=ownerDocument, nodeName=nodeName)

    def __bool__(self) -> bool:  # Node
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
            raise DOMException(f"Unexpected type '{type(self)}' for __bool__.")

    def __contains__(self, item:'Node') -> bool:  # Node
        """Careful, the Python built-in "contins"/"in" is wrong for node
        containment, because all empty lists are considered equal.
        Thus an element with any empty node "contains" *all* empty nodes.
        """
        return item.parentNode == self

    # I'm using:
    #     << and >> for document order
    #     == and != for isEqualNode (equal ORDER only happens with identity)
    #     <= and >= for document order (equal order is identity
    #
    def __eq__(self, other:'Node') -> bool:  # Node
        """Two different nodes cannot be in the same place, nor the same node
        in two different places, so eq/ne are same for order vs. identity.
        HOWEVER, there is a notion of isEqualNode (though it does not generalize
        to lt/gt).
        """
        return self.isEqualNode(other)

    def __ne__(self, other:'Node') -> bool:
        return not self.isEqualNode(other)

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

    def __lshift__(self, other:'Node') -> bool:
        assert self.ownerDocument == other.ownerDocument
        return self.compareDocumentPosition(other) < 0

    def __rshift__(self, other:'Node') -> bool:
        assert self.ownerDocument == other.ownerDocument
        return self.compareDocumentPosition(other) > 0

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

    def renameNode(self, namespaceURI:str, qualifiedName:QName_t):
        if not (self.isElement or self.isAttribute): raise HReqE(
            f"Can't renameNode for nodeType '{self.nodeType}'.")
        self.namespaceURI = namespaceURI
        self.nodeName = qualifiedName
        return self

    # Child-related methods fail for subclasses that don't also subclass
    # from Branchable.
    #
    @property
    def hasChildNodes(self) -> bool:
        return False
    def contains(self, other:'Node') -> bool:
        return False
    def hasAttributes(self) -> bool:
        return False
    def hasAttribute(self, attrName:NMTOKEN_t) -> bool:
        return False


    # Neighbor (not incl. child) properties and synonyms
    #
    @property
    def parent(self) -> 'Node':
        return self.parentNode

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
        if isinstance(self, Branchable) and len(self.childNodes) > 0:
            return self.childNodes[0]
        cur = self
        while (cur.parentNode is not None):
            if not cur.isLastChild: return cur.nextSibling
            cur = cur.parentNode
        return None

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


    # These return a whole axis (possibly filtered)
    # Not properties 'cuz need to allow options.
    # TODO: For symmetry, should these all allow 'includeSelf'?
    # Except as generators, it's almost as easy for the caller....
    #
    def previousSiblings(self, test:Callable=None) -> 'NodeList':
        cur = self.previousSibling
        while cur is not None:
            if test is None or test(cur): yield cur
            cur = cur.previousSibling
        return
    def nextSiblings(self, test:Callable=None) -> 'NodeList':
        cur = self.nextSibling
        while cur is not None:
            if test is None or test(cur): yield cur
            cur = cur.nextSibling
        return
    def previousNodes(self, test:Callable=None) -> 'NodeList':
        """Sorry, "previouses" just sounds too weird.
        """
        cur = self.previous
        while (cur is not None):
            if test is None or test(cur): yield cur
            cur = cur.previous
        return
    def nextNodes(self, test:Callable=None) -> 'NodeList':
        cur = self.next
        while (cur is not None):
            if test is None or test(cur): yield cur
            cur = cur.previous
        return
    def ancestors(self, test:Callable=None, includeSelf:bool=False) -> 'NodeList':
        if includeSelf and (test is None or test(self)): yield self
        cur = self.parentNode
        while (cur):
            if test is None or test(cur): yield cur
            cur = cur.parentNode
        return
    @staticmethod
    def nodeNameFilter(nodeNames:Iterable[str], exclude:bool=False) -> Callable[[str], bool]:
        """Returns a test function that will return True for nodes
        whose nodeNames are in (or out of, if 'exclude' is set), a given set.
        Usage:
          for n in doc.descendants(test=nodeNameFilter(["ul", "ol", "dl"]))...
        """
        nodeName_set = set(nodeNames)  # Convert to set for O(1) lookup
        def filter_fn(node_name: str) -> bool:
            if (exclude): return node_name not in nodeName_set
            else: return node_name in nodeName_set
        return filter_fn


    # Equivalents named like XPath axes
    #
    def parents(self, test:Callable=None, includeSelf:bool=False) -> 'NodeList':
        return self.ancestors(test=test, includeSelf=includeSelf)
    def precedingSiblings(self, test:Callable=None) -> 'NodeList':
        return self.previousSiblings(test=test)
    def followingSiblings(self, test:Callable=None) -> 'NodeList':
        return self.nextSiblings(test=test)
    def precedingNodes(self, test:Callable=None) -> 'NodeList':
        return self.previousNodes(test=test)
    def followingNodes(self, test:Callable=None) -> 'NodeList':
        return self.nextNodes(test=test)


    @property
    def textContent(self) -> str:  # Node
        return None  # Same as DOM says for Document.

    @textContent.setter
    def textContent(self, newData:str) -> None:  # Node
        raise NSuppE(
            f"Cannot set textContent on node of type '{self.nodeType}'.")

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


    #######################################################################
    # Extras for Node
    #
    def getUserData(self, key:str) -> Any:  # DOM3 but later not
        if not self.userData: return None
        return self.userData[key][0]

    def setUserData(self, key:NMTOKEN_t, data:Any, handler:Callable=None) -> None:
        if self.userData is None: self.userData = {}
        self.userData[key] = (data, handler)


    # Shorter checking for node types:
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
    def isCharacterData(self) -> bool:
        return isinstance(self, CharacterData)
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
    def isFirstChild(self) -> bool:
        """Don't do a full getChildIndex() if this is all you need.
        """
        if self.parentNode is None: return False
        return (self.parentNode.childNodes[0] is self)

    @property
    def isLastChild(self) -> bool:
        if self.parentNode is None: return False
        return (self.parentNode.lastChild is self)

    def changeOwnerDocument(self, otherDocument:'Document') -> None:
        """Move a subtree to another document. This requires deleting it, too.
        """
        if self.parentNode is not None: self.removeNode()
        #self.unlink(keepAttributes=True)
        if isinstance(self, Branchable):
            for node in self.descendants(attrs=True):
                node.ownerDocument = otherDocument


    # Serialization (Node)
    #
    @property
    def outerXML(self) -> str:  # Node
        x = self.toxml()
        #print(f"Node.outerXML -> '{x}'")
        return x

    @outerXML.setter
    def outerXML(self, xml:str) -> None:  # Node
        raise NSuppE(f"No outerXML setter on node type '{self.nodeType}'.")

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
        px = self.toprettyxml(indent=indent, newl=newl, encoding=encoding, fo=fo)
        #print(f"Node.toxml for '{self.nodeName}' -> '{px}'.")
        return px

    def toprettyxml(self, indent:str='\t', newl:str='\n', encoding:str="utf-8",
        standalone=None, fo:FormatOptions=None) -> str:
        return FormatXml.toprettyxml(node=self, indent=indent,
            newl=newl, encoding=encoding, standalone=standalone, fo=fo)

    def tocanonicalxml(self) -> str:
        return self.toprettyxml(fo=FormatOptions.getCanonicalFO())


    #######################################################################
    # Paths, pointers, etc. (Node)  TODO: Move to ranges
    #
    def getNodePath(self, useId:str=None, attrOk:bool=False,
        wsn:bool=True, typed:bool=False) -> str:
        """Get a basic XPounter child-sequence string.
        """
        steps = self.getNodeSteps(useId=useId, attrOk=attrOk, wsn=wsn, typed=typed)
        if not steps: return None
        return "/".join([ str(step) for step in steps ])

    def getNodeSteps(self, useId:bool=False, attrOk:bool=False,
        wsn:bool=True, typed:bool=False) -> List:
        """Get the child-number path to the node, as a list. Options:
            'useId': start it at the nearest ID (given an attribute name for ids)
            'attrOk': Support attribute node via '@{name}' (else use ownerElement)
            'wsn': whitespace-only text nodes count
            'typed': suffix element type to the child number
        """
        if self.nodeType == Yggdrasil.ABSTRACT_NODE:
            raise NSuppE("No paths to abstract Nodes.")
        cur = self
        f = []
        if self.isAttribute:
            if attrOk: f.insert(0, f"@{self.name}")
            cur = self.ownerElement
        while (cur is not None):
            if useId:
                attrNode = self.idHandler.getIdattrNode(cur)
                if attrNode:
                    f.insert(0, attrNode.nodeValue)
                    break
            if cur.parentNode is None:
                f.insert(0, 1)
            else:
                f.insert(0, cur.getChildIndex(wsn=wsn) + 1)
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
            # TODO support @attrName?
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
    # WHATWG methods, incl. multi-item sibling insertions
    #
    @property
    def nextElementSibling(self) -> 'Element':  # WHATWG
        cur = self.nextSibling
        while (cur is not None):
            if cur.isELement: return cur
            cur = self.nextSibling
        return None
    @property
    def previousElementSibling(self) -> 'Element':  # WHATWG
        cur = self.previousSibling
        while (cur is not None):
            if cur.isELement: return cur
            cur = self.previousSibling
        return None

    @property
    def parentElement(self) -> 'Element':  # DOM2, WHATWG
        if self.parentNode is None or not self.parentNode.isElement: return None
        return self.parentNode

    def getRootNode(self) -> 'Document':  # WHATWG
        return self.ownerDocument

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


    ###########################################################################
    #
    def eachSaxEvent(self, attrTx:str="PAIRS", test:Callable=None) -> Tuple:
        """Generate a series of SAX events as if subtree were being parsed.
        Each even is a tuple of a SaxEvent plus args:
            (INIT, )
            (START   name:str    attrName:str attrValue:str,..., )
                (you can also request one event per attribute:
                    ATTRIBUTE   attrName:str attrValue:str
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
            f"Unknown attrTx value '{attrTx}'.")

        yield (SaxEvent.DOC, )
        for se in self.eachSaxEvent_R(attrTx=attrTx, test=test):
            #dtr.msg("SE: %s", repr(se))
            yield se
        yield (SaxEvent.DOCEND, )
        return

    def eachSaxEvent_R(self:'Node', attrTx:str, test:Callable=None) -> Tuple:
        if test and not self.test():
            return
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
                raise DOMException(f"Unexpected attrTx '{attrTx}'.")

            if self.childNodes is not None:
                for ch in self.childNodes:
                    for chEvent in ch.eachSaxEvent_R(attrTx=attrTx, test=test):
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
            for chEvent in self.documentElement.eachSaxEvent_R(attrTx=attrTx, test=test):
                yield chEvent

        else:
            raise DOMException(f"Unexpected nodeType '{self.nodeType}'.")

        return

    ### Meta (Node)

    def unlink(self, keepAttributes:bool=False) -> None:  # MINIDOM
        """Break all internal references in the subtree, to help gc.
        Has to delete attributes, b/c they have ownerElement, ownerDocument.
        But with keepAttributes=True, it will unlink them instead.
        Element overrides this to unlink attrs and childNodes, too.
        """
        super().unlink()
        self.userData = None
        return

    def checkNode(self, deep:bool=True) -> None:  # Node
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
            self.checkSiblings(self.ownerDocument._siblingImpl)

        if isinstance(self, Branchable):
            if self.childNodes is not None and len(self.childNodes) > 0:
                assert isinstance(self, (Element, Node, Document)), (
                    f"{self.__class__} has children.")
                assert self not in self.childNodes
        if self.userData is not None:
            assert isinstance(self.userData, dict)

    def checkSiblings(self, impl:SiblingImpl):
        chIndex = self.getChildIndex()
        if impl == SiblingImpl.COUNT:
            assert not hasattr(self, "_childNum")
            assert not hasattr(self, "_previousSibling")
            assert not hasattr(self, "_nextSibling")
        elif impl == SiblingImpl.CHNUM:
            assert hasattr(self, "_childNum")
            assert not hasattr(self, "_previousSibling")
            assert not hasattr(self, "_nextSibling")
            assert self.parentNode.childNodes[self._childNum] == self
        elif impl == SiblingImpl.LINKS:
            assert not hasattr(self, "_childNum")
            assert hasattr(self, "_previousSibling")
            assert hasattr(self, "_nextSibling")
            if self._previousSibling is None:
                assert chIndex == 0
            else:
                assert isinstance(self._previousSibling, Node)
                assert self._previousSibling._nextSibling == self
            if self._nextSibling is None:
                assert chIndex == len(self.parentNode.childNodes) - 1
            else:
                assert isinstance(self._nextSibling, Node)
                assert self._nextSibling._previousSibling == self
        else:
            assert False, f"Unrecognized SiblingImpl value '{impl}'."

    # End class Node


###############################################################################
### TODO Consider DictNode(dict)?
#
class Keyable(dict):
    """
    A mixin like Branchable -- cf attributes, dcls, ...
    Nature of keys? Vector of
        attributes? (incl stack and inherited)
        XPointers or XPaths


    XPointer and XPath extensions?
    Schemera dcl? define keys?
    Relation to SQL compound keys?
    Subclass of Branchable?
    """


###############################################################################
#
class Branchable(list, ElementTreeAdditions):
    """This class encapsulates stuff that applies only to Nodes that can
    have children: Document, DocumentFragment, Element.
    So only those inherit from it.
    TODO: should predicates like hasChildNodes() be on Node?
    """
    def __setitem__(self, picker:Union[int, slice], value: 'Node') -> None:
        """Regular list ops aren't enough, as we have to set neighbor link(s),
        prevent inserting one node in multiple places, etc.
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
                f"Step value '{step}' not (yet) supported in __setitem__.")
            for i in range(stop-1, start-1, -1 if step > 0 else 1):  # ewwwww TODO
                self.removeChild(i)
        # TODO more... @attr, nmtoken, #text, scheme:...
        else:
            raise TypeError(f"Unsupported type '{type(picker)}' for [] arg.")

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
        raise TypeError(f"Unrecognized index/slice type '{type(picker)}' for __getitem__.")

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

    @property
    def length(self) -> int:
        return len(self)

    @property
    def childNodes(self) -> 'Node':  # *MOVE*
        """Unlike what the DOM IDL says, childNodes here is just the Node,
        not an instance variable *in* a Node. That means it's not a subclass
        of NodeList (b.c. Node itself isn't). But it has all the operations,
        as it turns out.

        Considering having Element and Document be subclasses ALSO of NodeList.
        Any conflicts?
        """
        return self

    @property
    def hasSubElements(self) -> bool:
        if len(self.childNodes) == 0: return False
        for ch in self.childNodes:
            if ch.nodeType == Node.ELEMENT_NODE: return True
        return False

    @property
    def hasChildNodes(self) -> bool:
        """Returns False for either None or [] (Nodes are lists).
        """
        return len(self.childNodes) > 0

    @property
    def hasTextNodes(self) -> bool:
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

    def contains(self, other:'Node') -> bool:  # Branchable
        """UNLIKE __contains__, this includes indirect descendants!
        Do NOT search all descendants, just check reverse ancestry.
        Nodes do NOT contain self, nor elements attributes.
        Using the synonym 'hasDescendant' may help avoid confusion.
        """
        if not isinstance(other, Node): raise TypeError(
            f"Branchable.contains was given a '{type(other)}', not a Node.")
        if other is self or isinstance(other, Attr): return False
        other = other.parentNode
        while (other is not None):
            if other is self: return True
            other = other.parentNode
        return False

    def children(self, test:Callable=None) -> 'NodeList':
        """Note: HTML DOM has same name to return all *element* children.
        Whence this idea that text doesn't count?
        """
        if not isinstance(self.childNodes, list): raise DOMException(
            f"{self.nodeName}.childNodes is a '{type(self.childNodes)}', not a list.")
        if len(self.childNodes) == 0: return
        for cur in self.childNodes:
            if test is None or test(cur): yield cur
        return

    def descendants(self, test:Callable=None,
        includeSelf:bool=False, attrs:bool=False) -> 'NodeList':
        """Generate all descendants in document order.
        If 'test' is set, only the ones for which it returns Trueish
        (see nodeNameFilter() following, for a pre-made test).
        Also can yield attributes at caller option.
        """
        if not isinstance(self.childNodes, list): raise DOMException(
            f"{self.nodeName}.childNodes is a '{type(self.childNodes)}', not a list.")
        if includeSelf and (test is None or test(self)): yield self
        if len(self.childNodes) == 0: return
        for cur in self.childNodes:
            if test is None or test(cur):
                yield cur
                if attrs and self.isElement and self.attributes:
                    for attrNode in self.attributes.values(): yield attrNode
            if isinstance(cur, Branchable):
                for curch in cur.descendants(test=test, attrs=attrs): yield curch
        return

    @property
    def leftmost(self) -> 'Node':
        """Deepest descendant along left branch of subtree  (never self).
        """
        cur = self
        while True:
            try:
                cur = cur.childNodes[0]
            except (AttributeError, TypeError, IndexError):
                return cur

    @property
    def rightmost(self) -> 'Node':
        """Deepest descendant along right branch of subtree (never self).
        """
        cur = self
        while True:
            try:
                cur = cur.childNodes[-1]
            except (AttributeError, TypeError, IndexError):
                return cur


    ### Mutators
    #
    def prependChild(self, newChild:'Node') -> None:
        self.insert(0, newChild)

    def appendChild(self, newChild:'Node') -> None:  # Branchable
        self.insert(len(self), newChild)

    def append(self, newChild:'Node') -> None:
        self.insert(len(self), newChild)

    def insertBefore(self, newChild:'Node', oldChild:Union['Node', int]) -> None:
        oNum, oChild = self._expandChildArg(oldChild)
        if oChild.parentNode != self: raise NotFoundError(
            f"Node to insert before (a '{oChild.nodeName}') is not a child.")
        self.childNodes.insert(oNum, newChild)

    def insertAfter(self, newChild:'Node', oldChild:Union['Node', int]) -> None:
        oNum, oChild = self._expandChildArg(oldChild)
        if oChild.parentNode != self: raise NotFoundError(
            f"Node to insert after (a '{oChild.nodeName}') is not a child.")
        self.childNodes.insert(oNum+1, newChild)

    def insert(self, i:int, newChild:'Node') -> None:  # Branchable
        """Note: Argument order is different than (say) insertBefore.
        This implementation does not link siblings, b/c tests showed
        the overhead wasn't worth it.
        NOTE: All insertions end up here.
        TODO: siblingImpl should be matched to the parent -- we might have
        adopted a node from elsewhere!
        """
        if not self.canHaveChildren:
            raise HReqE(f"node type '{type(self).__name__}' cannot have children.")
        if i < 0: i = len(self) + i
        if i >= len(self): i = len(self)

        if isinstance(newChild, DocumentFragment):
            for cur in reversed(newChild):
                self.insert(i, cur)
                return
        elif not isinstance(newChild,
            (Element, Text, Comment, ProcessingInstruction, CDATASection,
             EntityReference)):
            raise HReqE(f"newChild is bad type '{type(newChild).__name__}'.")

        if newChild.parentNode is not None: raise HReqE(
            f"newChild already has parent (name '{newChild.parentNode.nodeName}')")

        if newChild.isElement: self._filterOldInheritedNS(newChild)
        super().insert(i, newChild)

        newChild.ownerDocument = self.ownerDocument  # Or exception?
        newChild.parentNode = self

        # Apply to the child node, the parentNode's way of doing siblings.
        #
        if hasattr(self, "_previousSibling"):
            newChild._previousSibling = newChild._nextSibling = None
            if i > 0:
                self.childNode[i-1]._nextSibling = newChild
                newChild._previousSibling = self.childNode[i-1]
            if i < len(newChild)-1:
                self.childNode[i+1]._previousSibling = newChild
                newChild._nextSibling = self.childNode[i+1]
        elif hasattr(self, "_childNum"):
            newChild._childNum = i
            for sibNum in range(i+1, len(self)):
                self.childNodes[sibNum]._childNum = sibNum
        else:
            return


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

    def remove(self, x:Any=None) -> 'Node':  # Branchable
        """Remove all members (child nodes) that match x.
        (not to be confused with removeNode()).
        """
        if len(self.childNodes) == 0: return None
        for ch in self.childNodes:
            if ch._isOfValue(x): self.removeChild(ch)

    def removeChild(self, oldChild:Union['Node', int]) -> 'Node':
        """Disconnect oldChild from this node, removing it from the tree,
        but not fromm the document. To destroy it, it should also unlinked.
        Namespaces are copied, not cleared (may be if/when re-inserted somewhere).
        All removals end up here.
        """
        if isinstance(oldChild, Node):
            if oldChild.parentNode != self: raise HReqE(
                f"Node to remove (a '{oldChild.nodeName}') has wrong parent.")
        elif not isinstance(oldChild, int): raise HReqE(
            f"Child to remove is not a Node or int, but a '{oldChild.type}'.")
        oNum, oChild = self._expandChildArg(oldChild)
        del self.childNodes[oNum]
        oChild.parentNode = None

        if hasattr(oldChild, "_nextSibling"):
            nSib = oldChild._nextSibling
            pSib = oldChild._previousSibling
            if nSib: nSib._previousSibling = pSib
            if pSib: pSib._nextSibling = nSib
            oldChild._previousSibling = oldChild._nextSibling = None
        elif hasattr(oldChild, "_childNum"):
            for sibNum in range(self.oldChild, len(self.parentNode.childNodes)):
                self.parentNode.childNodes[sibNum]._childNum -= 1
            delattr(oldChild, "childNum")
        else:
            pass

        if oChild.isElement: oChild._resetinheritedNS()
        return oChild

    # "del" can't just do a plain delete, 'cuz unlink. TODO: Enable del?
    #def __delitem__(self, i:int) -> None:
    #    self.removeChild(self.childNodes[i])

    ### Python list operations (Yggdrasil)

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

    ### More Python list operations, for Yggdrasil.
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
    def __mul__(self, x:int) -> 'NodeList':  # Yggdrasil
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

    ### Branchable additions for lxml compatibility


###############################################################################
#
class NonBranchable:
    """Supply stubs for the Branchable methods.
    """
    def children(self, test:Callable=None) -> 'NodeList':
        return None

    def descendants(self, test:Callable=None,
        includeSelf:bool=False, attrs:bool=False) -> 'NodeList':
        return None

    @property
    def msg(self):
        return f"Can't do child operations on node type '{self.nodeType}'."

    @property
    def childNodes(self) -> 'Node':
        return None
    @property
    def hasSubElements(self) -> bool:
        return False
    @property
    def hasChildNodes(self) -> bool:
        return False
    @property
    def hasTextNodes(self) -> bool:
        return False
    @property
    def firstChild(self) -> 'Node':
        return None
    @property
    def lastChild(self) -> 'Node':
        return None
    @property
    def leftmost(self) -> 'Node':
        return None
    @property
    def rightmost(self) -> 'Node':
        return None


    def prependChild(self, newChild:'Node') -> None:
        raise HReqE(self.msg)

    def appendChild(self, newChild:'Node') -> None:
        raise HReqE(self.msg)

    def append(self, newChild:'Node') -> None:
        raise HReqE(self.msg)

    def insertBefore(self, newChild:'Node', oldChild:Union['Node', int]) -> None:
        raise HReqE(self.msg)

    def insertAfter(self, newChild:'Node', oldChild:Union['Node', int]) -> None:
        raise HReqE(self.msg)

    def insert(self, i:int, newChild:'Node') -> None:  # NonBranchable
        raise HReqE(self.msg)

    ### Removers
    #
    def replaceChild(self, newChild:'Node', oldChild:Union['Node', int]) -> None:
        raise HReqE(self.msg)

    def clear(self) -> None:
        raise HReqE(self.msg)

    def pop(self, i:int=-1) -> 'Node':
        raise HReqE(self.msg)

    def remove(self, x:Any=None) -> 'Node':
        raise HReqE(self.msg)

    def removeChild(self, oldChild:Union['Node', int]) -> 'Node':
        raise HReqE(self.msg)

    def __delitem__(self, i:int) -> None:
        raise HReqE(self.msg)

    ### More Python list operations
    #
    def count(self, x:Any) -> int:
        raise HReqE(self.msg)

    def index(self, x:Any, start:int=None, end:int=None) -> int:
        raise HReqE(self.msg)

    def reverse(self) -> None:
        raise HReqE(self.msg)

    def reversed(self) -> NodeList:
        raise HReqE(self.msg)

    def sort(self, key:Callable=None, reverse:bool=False) -> None:
        raise HReqE(self.msg)

    def sorted(self, key:Callable=None, reverse:bool=False) -> None:
        raise HReqE(self.msg)

    def __mul__(self, x:int) -> 'NodeList':  # Yggdrasil
        raise HReqE(self.msg)

    def __rmul__(self, x) -> 'NodeList':
        raise HReqE(self.msg)

    def __imul__(self, x) -> 'NodeList':
        raise HReqE(self.msg)

    def __add__(self, other) -> 'NodeList':
        raise HReqE(self.msg)

    def __iadd__(self, other) -> 'NodeList':
        raise HReqE(self.msg)


###############################################################################
#
class Attributable:
    """Supply the methods needed for a Node subclass that supports attributes.
    """
    def __init__(self):
        self.attributes:'NameNodeMap' = None  # Lazy creation _presetAttribute().

    def _findAttr(self, ns:str, attrName:NMTOKEN_t) -> 'Attr':
        """All(?) attribute stuff goes through here.
        """
        if not attrName or not Rune.isXmlQName(attrName):
            raise ICharE(f"Attr name '{attrName}' not an XML QName.")
        if not self.attributes: return None
        if attrName in self.attributes: # If total match, we're ok. (?)
            return self.attributes[attrName]
        if ":" in attrName:
            _nsPrefix, _colon, lname = attrName.partition(":")
        else:
            _nsPrefix = None; lname = attrName
        for _k, attrNode in self.attributes.items():
            if attrNode.localName != lname: continue
            if not ns or ns == RWord.NS_ANY: return attrNode
            if attrNode.namespaceURI == ns: return attrNode
        return None

    def _presetAttribute(self, attrName:NMTOKEN_t, attrValue:str) -> None:
        """Common precursor for all methods that add/set attributes.
        """
        if not Rune.isXmlQName(attrName):
            raise ICharE(f"Attr name '{attrName}' not an XML QName.")
        if self.attributes is None:
            self.attributes = NamedNodeMap(
                ownerDocument=self.ownerDocument, parentNode=self)
        if attrName.startswith(RWord.NS_PREFIX+":"):
            self._addNamespace(attrName, attrValue)
        # TODO Update IdHandler to cover changing attrs
        # TODO Typecast if needed on setting attributes

    def hasAttributes(self) -> bool:
        return bool(self.attributes)

    def hasAttribute(self, attrName:NMTOKEN_t) -> bool:
        return self._findAttr(ns=None, attrName=attrName) is not None


    ### Attribute plain
    #
    def setAttribute(self, attrName:NMTOKEN_t, attrValue:Any) -> None:
        self._presetAttribute(attrName, attrValue)
        self.attributes.setNamedItem(attrName, attrValue)

    def getAttribute(self, attrName:NMTOKEN_t, castAs:type=str, default:Any=None) -> str:
        """Normal getAttribute, but can cast and default for caller.
        """
        attrNode = self._findAttr(ns=None, attrName=attrName)
        if attrNode is None: return default
        if castAs: return castAs(attrNode.nodeValue)
        return attrNode.nodeValue

    def removeAttribute(self, attrName:NMTOKEN_t) -> None:
        """Silent no-op if not present.
        """
        #if attrName.startswith(RWord.NS_PREFIX+":"):
        #    raise NSuppE("Not a good idea to remove a Namespace attribute.")
        attrNode = self._findAttr(ns=None, attrName=attrName)
        if attrNode is None: return
        self.attributes.removeNamedItem(attrName)
        if len(self.attributes) == 0: self.attributes = None

    ### Attribute Node
    #
    def setAttributeNode(self, attrNode:'Attr') -> 'Attr':
        assert isinstance(attrNode, Attr)
        self._presetAttribute(attrNode.nodeName, attrNode.nodeValue)
        old = self._findAttr(ns=None, attrName=attrNode.nodeName)
        self.attributes.setNamedItem(attrNode)
        if old is not None: old.parentNode = None
        return old

    def getAttributeNode(self, attrName:NMTOKEN_t) -> 'Attr':
        if not isinstance(attrName, str):
            raise HReqE(f"getAttributeNode() take a name, not a '{type(attrName)}'.")
        return self._findAttr(ns=None, attrName=attrName)

    def removeAttributeNode(self, attrNode:'Attr') -> 'Attr':
        """Unlike removeAttribute and NS, this *can* raise an exception.
        """
        assert isinstance(attrNode, Attr)
        #if attrNode.nodeName.startswith(RWord.NS_PREFIX):
        #    raise NSuppE("Not a good idea to remove a Namespace attribute.")
        old = self._findAttr(ns=None, attrName=attrNode.nodeName)
        if old is None: return None
        if old is not attrNode:
            raise NotFoundError(
                f"Node has attribute matching '{attrNode.nodeName}', but not the one passed.")
        attrNode.parentNode = None
        del self.attributes[attrNode.nodeName]

    ### Attribute NS
    #
    def hasAttributeNS(self, ns:str, attrName:NMTOKEN_t) -> bool:
        assert Rune.isXmlName(attrName)
        return self.hasAttribute(attrName)

    def setAttributeNS(self, ns:str, attrName:NMTOKEN_t, attrValue:str) -> None:
        self._presetAttribute(attrName, attrValue)
        attrNode = Attr(attrName, attrValue, ownerDocument=self.ownerDocument,
            nsPrefix=ns, namespaceURI=None, ownerElement=self)
        self.attributes.setNamedItem(attrNode)
        if ns == RWord.NS_PREFIX:
            attrNode2 = Attr(attrName[len(RWord.NS_PREFIX)+1:], attrValue,
                ownerDocument=self.ownerDocument,
                nsPrefix=ns, namespaceURI=None, ownerElement=self)
            self.inheritedNS.setNamedItem(attrNode2)

    def getAttributeNS(self, ns:str, attrName:NMTOKEN_t, castAs:type=str, default:Any=None) -> str:
    # TODO Check/fix getAttributeNS
        assert not ns or ns == RWord.NS_ANY or NameSpaces.isNamespaceURI(ns)
        return self.getAttribute(attrName, castAs, default)

    def removeAttributeNS(self, ns, attrName:NMTOKEN_t) -> None:
        #if attrName.startswith(RWord.NS_PREFIX):
        #    raise NSuppE("Not a good idea to remove a Namespace attribute.")
        if self.hasAttribute(attrName):
            self.attributes[attrName].parentNode = None
            del self.attributes[attrName]

    ### Attribute NodeNS
    #
    def setAttributeNodeNS(self, ns, attrNode:'Attr') -> 'Attr':
        assert isinstance(attrNode, Attr)
        self._presetAttribute(attrNode.nodeName, attrNode.nodeValue)
        old = self._findAttr(ns=None, attrName=attrNode.nodeName)
        self.attributes.setNamedItem(attrNode)
        if old is not None: old.parentNode = None
        return old

    def getAttributeNodeNS(self, ns:str, attrName:NMTOKEN_t) -> 'Attr':
        NameSpaces.isNamespaceURI(ns, require=True)
        return self._findAttr(ns=ns, attrName=attrName)

    ### Attribute extensions
    #
    def getInheritedAttribute(self:Node, attrName:NMTOKEN_t, default:Any=None) -> str:
        """Search upward to find the attribute.
        Return the first one found, otherwise the default (like xml:lang).
        """
        cur = self
        while (cur is not None):
            if cur.hasAttribute(attrName): return cur.getAttribute(attrName)
            cur = cur.parentNode
        return default

    def getInheritedAttributeNS(self:Node,
        ns:str, attrName:NMTOKEN_t, default:Any=None) -> 'Attr':
        NameSpaces.isNamespaceURI(ns, require=True)
        return self.getInheritedAttribute(attrName, default)

    def getStackedAttribute(self:Node, attrName:NMTOKEN_t, sep:str="/") -> str:
        """Accumulate the attribute across self and all ancestors.
        Assumes the same name; uses "" if not present.
        """
        docEl = self.ownerDocument.documentElement
        vals = []
        cur = self
        while (cur is not None and cur is not docEl):
            vals.insert(0, cur.getAttribute(attrName) or "")
            cur = cur.parentNode
        return sep.join(vals)


###############################################################################
# Cf https://developer.mozilla.org/en-US/docs/Web/API/Document
#
class Document(Branchable, Node):
    def __init__(
        self,
        namespaceURI:str=None,
        qualifiedName:NMTOKEN_t=None,
        doctype:'DocumentType'=None,
        isFragment:bool=False
        ):
        Node.__init__(self, ownerDocument=None, nodeName=qualifiedName)
        Branchable.__init__(self)
        self._siblingImpl = SiblingImpl.COUNT

        # namespaceURI is looked up from default or prefix, not a static var.
        self.inheritedNS:Dict        = { }
        if namespaceURI: self.inheritedNS[""]   = namespaceURI
        self.nodeType:NodeType       = Node.DOCUMENT_NODE
        self.nodeName:QName_t        = qualifiedName
        self.doctype                 = doctype

        self.documentElement         = None
        if qualifiedName:
            if not Rune.isXmlQName(qualifiedName): raise ICharE(
                "Document: qname '%s' isn't." % (qualifiedName))
            if ":" in qualifiedName:
                root = self.createElementNS(namespaceURI=None, tagName=qualifiedName)
            else:
                root = self.createElement(tagName=qualifiedName)
            self.appendChild(root)
            self.documentElement     = root

        # minidom vars
        self.actualEncoding:str      = 'utf-8'
        self.async_                  = None
        self.documentURI:str         = None
        self.encoding:str            = 'utf-8'
        self.errorHandler:Callable   = None
        self.standalone:bool         = None
        self.strictErrorChecking     = None
        self.version:str             = None

        # our vars
        self.implName:str            = 'BaseDOM'
        self.implVersion:str         = __version__
        self.options:SimpleNamespace = self.initOptions()
        self.sliceHandlers:Dict      = {}  # See registerFilterScheme()
        self.idHandler:Callable      = IdHandler(self)  # Lazy build
        self.loadedFrom:str          = None
        self.uri:str                 = None
        self.mimeType:str            = 'text/XML'

    @property
    def implementation(self):
        return DOMImplementation.getImplementation()
    @property
    def contentType(self) -> str:
        return self.mimeType
    @property
    def domConfig(self) -> None:
        raise NSuppE("Document.domConfig")
    @property
    def inputEncoding(self) -> str:  # DOM 3
        return self.actualEncoding
    @property
    def xmlEncoding(self) -> None:  # DOM 3
        return self.encoding
    @property
    def xmlStandalone(self) -> None:  # DOM 3
        return self.standalone
    @property
    def xmlVersion(self) -> None:  # DOM 3
        return self.version

    @property
    def textContent(self) -> str:
        return None  # So says DOM...
    @textContent.setter
    def textContent(self, newData:str) -> None:
        raise NSuppE("Setting textContent is not allowed on Document")  # ???

    def clear(self) -> None:
        raise NSuppE("No clear() on Document nodes.")

    def _updateChildSiblingImpl(self, which:SiblingImpl=SiblingImpl.COUNT) -> None:
        """Change the Document's sibling implementation method.
        Methods that check it:
            previousSibling, nextSibling, insert,
        """
        if not self.documentElement:
            return None
        if which == SiblingImpl.COUNT:
            self._siblingsByParent(self.documentElement)
            self._siblingImpl = SiblingImpl.COUNT
        elif which == SiblingImpl.CHNUM:
            self._siblingsByChildNum(self.documentElement)
            self._siblingImpl = SiblingImpl.CHNUM
        elif which == SiblingImpl.LINKS:
            self._siblingsByLink(self.documentElement)
            self._siblingImpl = SiblingImpl.LINKS
        else:
            raise DOMException(f"Unrecognized siblingImpl '{which}'.")

    def _siblingsByParent(self, node:Node) -> None:
        if hasattr(node, "_childNum"): delattr(node, "_childNum")
        if hasattr(node, "_previousSibling"): delattr(node, "_previousSibling")
        if hasattr(node, "_nextSibling"): delattr(node, "_nextSibling")
        if (node.childNodes):
            for ch in node.childNodes: self._siblingsByParent(ch)

    def _siblingsByChildNum(self, node:Node) -> None:
        if hasattr(node, "_previousSibling"): delattr(node, "_previousSibling")
        if hasattr(node, "_nextSibling"): delattr(node, "_nextSibling")
        setattr(node, "_childNum", node.getChildIndex())
        if (node.childNodes):
            for ch in node.childNodes: self._siblingsByChildNum(ch)

    def _siblingsByLink(self, node:Node) -> None:
        if hasattr(node, "_childNum"): delattr(node, "_childNum")
        setattr(node, "_previousSibling", node.previousSibling)
        setattr(node, "_nextSibling", node.nextSibling)
        if (node.childNodes):
            for ch in node.childNodes: self._siblingsByLink(ch)

    def importNode(self, node:'Node', deep:bool=False) -> 'Node':  # WHATWG?
        myCopy = node.cloneNode(deep=deep)
        self.adopt(myCopy)
        return myCopy

    def adopt(self, node:'Node') -> 'Node':
        """Move a subtree from another document.
        """
        if node.parentNode is not None: node.removeNode()
        for node in self.descendants(attrs=True):
            node.ownerDocument = self
        return node

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
                f"Document element must not be a '{newChild.nodeType.__name__}'.")
        super().insert(i, newChild)
        self.documentElement = newChild

    def initOptions(self) -> SimpleNamespace:
        return SimpleNamespace(**{
            "parser":         "lxml", # Default parser to use
            "NameTest":       None,  # None or a NameTest enum        # TODO

            # API extensions
            "getItem":        True,  # Overload [] for child selection
            "CSSSelectors":   False, # Support CSS selectors          # TODO
            "XPathSelectors": False, # Support XPath selectors        # TODO
            "whatwgStuff":    True,  # Support whatwg calls           # TODO
            "BSStuff":        False, # Support bsoup/etree calls      # TODO

            # TODO Merge w/ Loki options
            "elementFold":    None,  # None, CaseHandler, Normalizer
            "attributeFold":       None,  #                                # TODO
            "entityFold":     None,  # (to xsparser?)                 # TODO
            "idFold":         None,  # (pass to idhandler calls)      # TODO
            "xsdFold":        None,  # (true, nan, ...) to xsdtypes   # TODO

            "NSURICase":      None,  #                                # TODO
            "attributeTypes": False, # Attribute datatype check/cast  # TODO ???
            "xsdTypes":       True,  # impl option                    # TODO

            # Namespace options (move to parser?)
            "idNameSpaces":   False, # Allow ns on ID values?         # TODO
            "ns_global":      False, # Limit ns dcls to doc element   # TODO
            "ns_redef":       True,  # Allow redefining a ns prefix?  # TODO
            "ns_never":       False, # No namespaces please           # TODO
        })

    def setOption(self, k:str, v:Any):  # Document
        try:
            getattr(self.options, k)
        except AttributeError as e:
            raise KeyError(f"Document: unknown option '{k}'.") from e
        if (k.endswith("Case") and v is not None
            and not isinstance(v, ( CaseHandler, Normalizer ))):
            raise TypeError(f"Document: Bad value type '{type(v)}' for option '{k}'.")
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
            f"Hander for filter scheme '{name}' is '{type(handler)}', not callable.")
        self.sliceHandlers[name] = handler

    def createElement(self,
        tagName:NMTOKEN_t,
        attributes:Dict=None,
        parent:Node=None,
        text:str=None
        ) -> 'Element':
        if ":" in tagName: raise SyntaxError(
            f"QName '{tagName}' not expected (use createElementNS instead?).")
        return self.createElementNS(
            namespaceURI=None, tagName=tagName,
            attributes=attributes, parent=parent, text=text)

    def createElementNS(self,
        namespaceURI:str,
        tagName:QName_t,
        attributes:Dict=None,
        parent:Node=None,
        text:str=None
        ) -> 'Element':
        """Allow some shorthand for creating attributes and/or text, and.or
        to append the new element to a specified parent node.
        To put in whole chunks of XML, or insert lists of elements and text,
        there are other extensions.
        """
        elem = Element(ownerDocument=self, nodeName=tagName)
        elem._addNamespace(name=elem.prefix, namespaceURI=namespaceURI)
        if attributes:
            for a, v in attributes.items(): elem.setAttribute(a, v)
        if text: elem.appendChild(self.createTextNode(text))
        if parent: parent.appendChild(elem)
        return elem

    def createDocumentFragment(
        self,
        namespaceURI:str=None,
        qualifiedName:QName_t="frag",
        doctype:str=None,
        isFragment:bool=True
        ) -> 'Document':
        return DocumentFragment(
            namespaceURI=namespaceURI,
            qualifiedName=qualifiedName, doctype=doctype, isFragment=True)

    def createAttribute(self, name:NMTOKEN_t, value:str=None, parentNode:Node=None) -> 'Attr':
        return self.createAttributeNS(namespaceURI=None,
            name=name, value=value, parentNode=parentNode)

    def createAttributeNS(self, namespaceURI:str,
        name:NMTOKEN_t, value:str=None, parentNode:Node=None) -> 'Attr':
        if parentNode is not None: assert parentNode.isElement
        return Attr(name, value, ownerDocument=self,
            nsPrefix=None, namespaceURI=namespaceURI, ownerElement=parentNode)  # TODO ???

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
    def xmlDcl(self) -> str:  # Document
        return self._getXmlDcl(encoding=self.encoding)

    @property
    def doctypeDcl(self) -> str:  # Document
        if self.doctype: return self.doctype.outerXml
        return f"<!DOCTYPE {self.documentElement.nodeName} []>"

    def buildIndex(self, elemNames:List=None, attrName:NMTOKEN_t=None) -> None:
        """Build an index of all values of the given named attribute
        on the given element name(s). If elemName is empty, all elements.
        """
        if elemNames is None: elemNames = [ "*" ]
        elif not isinstance(elemNames, Iterable): elemNames = [ elemNames ]
        for elemName in elemNames:
            if elemName != "*" and not Rune.isXmlNMTOKEN(elemName): raise ICharE(
                f"Bad element name '{elemName}' for buildIndex.")

        if not attrName: attrName = "id"
        elif not Rune.isXmlQName(attrName): raise ICharE(
                f"Bad attribute name '{attrName}' for buildIndex.")

        for elemName in elemNames:
            self.idHandler.addAttrChoice(
                elemNS="##any", elemName=elemName, attrNS="##any", attrName=attrName)
        self.idHandler.buildIdIndex()

    def getElementById(self, idValue:str) -> Node:  # HTML
        return self.idHandler.getIndexedId(idValue)

    def getElementsByTagName(self, name:NMTOKEN_t) -> Node:  # HTML
        return self.documentElement.getElementsByTagName(name)  # TODO ????

    def getElementsByClassName(self, name:NMTOKEN_t, attrName:NMTOKEN_t="class") -> Node:  # HTML
        return self.documentElement.getElementsByClassName(name, attrName=attrName)

    def checkNode(self, deep:bool=True) -> None:  # Document
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
        raise NSuppE  # TODO Finish containerize()

    # End class Document


###############################################################################
# DocumentFragment
#
class DocumentFragment(Branchable, Node):
    """TODO: Do the magic "insert" where if you insert a DocumentFragment,
    its children get inserted instead.
    """
    def __init__(
        self,
        namespaceURI:str=None,
        qualifiedName:NMTOKEN_t=None,
        doctype:'DocumentType'=None,
        isFragment:bool=False
        ):
        super().__init__(ownerDocument=None, nodeName=qualifiedName)
        self.nodeType = Node.DOCUMENT_FRAGMENT_NODE


###############################################################################
# Element
#
class Element(Branchable, Attributable, Node):
    """DOM Level 2 Core.
    https://www.w3.org/TR/2000/REC-DOM-Level-2-Core-20001113/core.html
    https://docs.python.org/2/library/xml.dom.html#dom-element-objects
    """
    def __init__(self, ownerDocument:Document=None, nodeName:NMTOKEN_t=None):
        Branchable.__init__(self)
        Attributable.__init__(self)
        Node.__init__(self, ownerDocument, nodeName)

        self.nodeType:int = Node.ELEMENT_NODE
        self.inheritedNS:dict = None
        self.declaredNS:dict = None
        self.prevError:str = None  # Mainly for isEqualNode

    def _addNamespace(self, name:NMTOKEN_t, namespaceURI:str="") -> None:
        """Add the given ns def to this Element. Most elements just inherit,
        so they just get a ref to their parent's defs. But when one is added,
        a copy is created (even if the ns is already on the parent, b/c
        adding a namespace explicitly is different than just inheriting).
        NOTE: It might be cleaner (though slower) to just run up the
        ancestors when needed (say, using getInheritedAttribute()).
        """
        prefix, _, local = name.partition(":")
        if not local:
            local = prefix; prefix = ""
        elif Rune.isXmlName(prefix): raise ICharE(
            f"Prefix for '{name}' is not a valid NCNAME.")
        elif prefix == RWord.NS_PREFIX:  raise ICharE(
            f"Can't use prefix '{RWord.NS_PREFIX}' on an element (for '{name}').")

        if not local: local = self.nodeName
        if not Rune.isXmlName(local): raise ICharE(
            f"_addNamespace: Invalid local part '{local}' in '{name}' -> '{namespaceURI}'.")

        if self.inheritedNS is None:
            self.inheritedNS = { }
        elif (self.parentNode and self.inheritedNS is self.parentNode.inheritedNS):
            self.inheritedNS = self.parentNode.inheritedNS.copy()
        self.inheritedNS[prefix] = namespaceURI

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
            self.attributes.clear()
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
        TODO: Perhaps a "sep" argument?
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
            raise HReqE(f"Other for isEqualNode is not a Node, but '{type(n2)}'.")
        dtr.msg(f"isEqualNode for name '{self.nodeName}' vs. '{n2.nodeName}'.")
        #import pudb; pudb.set_trace()
        if self.isElement and n2.isElement:
            dtr.msg(f"###{self.toxml()}###\n###{n2.toxml()}###")
        if not super().isEqualNode(n2):
            dtr.msg("Element super() tests found unequal.")
            return False

        if len(self) != len(n2):
            dtr.msg(f"len unequal ({len(self)} vs. {len(n2)}).")
            return False

        # Careful, OrderedDict eq would test order, which we don't want.
        # TODO Should actually resolve ns to compare.
        if not self.attributes and not n2.attributes:
            pass  # That's a match (even None vs. {})
        elif not self.attributes or not n2.attributes:
            dtr.msg("Somebody's got no attributes.")
            return False
        elif len(self.attributes) != len(n2.attributes):
            dtr.msg("Unequal number of attributes.")
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
    ####### Element: Descendant Selectors
    #
    def getElementById(self, IdValue:str) -> 'Element':  # DOM 2
        """TODO For HTML these should be case-insensitive. Elsewhere,
        """
        od = self.ownerDocument
        if od.idHandler is None:
            caseH = CaseHandler(od.options.idFold)
            od.idHandler = IdHandler(od, caseHandler=caseH)
        return od.getElementById(IdValue)

    def getElementsByClassName(self, name:NMTOKEN_t, attrName:NMTOKEN_t="class",
        nodeList:NodeList=None) -> NodeList:
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

    def getChildrenByTagName(self, tagName:NMTOKEN_t) -> NodeList:
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
            raise SyntaxError(f"Unknown position argument '{position}'.")
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
            raise HReqE(f"Unrecognized insert position '{position}'.")

    @property
    def outerXML(self) -> str:  # Element  # HTML
        x = self.toxml()
        #print(f"Element.outerXML -> '{x}'")
        return x

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
    def startTag(self) -> str:
        """Never produces empty-tags (use _startTag(empty=True) for that).
        """
        return self._startTag()

    @property
    def endTag(self) -> str:
        """Remember not to call this if the start used empty-element form.
        """
        if self.nodeType != Node.ELEMENT_NODE:
            raise HReqE(f"_endTag request for non-Element '{self.nodeType}'.")
        return f"</{self.nodeName}>"

    # TODO Move to prettyxml.FormatXml? Or swap with the ones there?

    def _startTag(self, empty:bool=False, includeNS:bool=False,
        fo:FormatOptions=None) -> str:  # Element
        """Gets a correct start-tag for the element.
        If 'includeNS' is set, declare all in-scope namespaces even if inherited?
        """
        if self.nodeType != Node.ELEMENT_NODE:
            raise HReqE(f"_startTag request for non-Element '{self.nodeType}'.")
        #print(f"nn: {self.nodeName}")
        if fo: return FormatXml.startTag(theNode=self, fo=fo)

        buf = f"<{self.nodeName}"
        if self.attributes:
            buf += self.formatAttributes(fo=fo)
        if includeNS:  # TODO Interleave if sorted
            for k, v in self.inheritedNS.items:
                if isinstance(v, list): v = ' '.join(v)
                vEsc = FormatXml.escapeAttribute(v, addQuotes=True, fo=fo)
                buf += f' {RWord.NS_PREFIX}:{k}={vEsc}'
        buf += ((fo.spaceEmpty + " /") if empty else "") + ">"
        #print(f"Element._startTag -> '{buf}'.")
        return buf

    def formatAttributes(self, fo:FormatOptions=None) -> str:
        """Turn a dict into a serialized attribute list (possibly sorted
        and/or space-normalized). Escape as needed.
        """
        if not self.attributes: return ""
        sep = " "
        attrNames = list(self.attributes.keys())
        if fo and fo.sortAttributes: attrNames = sorted(attrNames)
        attrString = ""
        for attrName in attrNames:
            attrNode = self.attributes[attrName]
            #print(f"\n    attribute '{a}' = {self.attributes[a]} ({type(self.attributes[a])}.")
            attrValue = attrNode.nodeValue
            if isinstance(attrValue, list): attrValue = ' '.join(attrValue)
            #print(f"formatAttributes[{a}] gets a {type(attrValue)}: '{attrValue}' -> "
            #    f"{FormatXml.escapeAttribute(attrValue, fo=fo)}.")
            #if normValues: attrValue = Rune.normalizeSpace(attrValue)
            fValue = FormatXml.escapeAttribute(attrValue, addQuotes=True, fo=fo)
            #print(f"fValue: '{fValue}'.")
            attrString += f"{sep}{attrName}={fValue}"
        #print(f"Element.formatAttributes -> '{attrString}'.")
        return attrString

    ### Meta (Element)

    def unlink(self, keepAttributes:bool=True) -> None:  # MINIDOM
        """This was provided in minidom b/c the Python gc wasn't smart
        about circular refs, such as x.childNodes[0].parentNode and
        sibling chains. But those should be ok these days.
        This is provided so old code won't needlessly fail.
        Could also use weakrefs for siblings and/or parents.
        """
        super().unlink(keepAttributes=keepAttributes)
        if self.attributes and not keepAttributes:
            for attr in self.attributes.values(): attr.unlink()
            self.attributes = None
        if self.childNodes is not None:
            self.childNodes.clear()

    def checkNode(self, deep:bool=False) -> None:  # Element
        super().checkNode(deep=False)

        if self.attributes is not None:
            assert isinstance(self.attributes, NamedNodeMap)
            for attrName, attrNode in self.attributes.items():
                assert isinstance(attrNode, Attr)
                assert attrName == attrNode.nodeName
                assert not attrName.startswith("xmlns:")  # Should be elsewhere
                #nsp = attrNode.prefix is defined
                attrNode.checkNode()

        if self.childNodes:
            assert isinstance(self.childNodes, list)
            prevChild = None
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
                ps = ch.previousSibling
                if i > 0: assert ps is prevChild
                if i < len(self.childNodes)-1:
                    assert isinstance(ch.nextSibling, Node)
                if deep:
                    #lg.info(f"Recursing to check: {ch.getNodePath(typed=True)}.")
                    ch.checkNode(deep)
                prevChild = ch

    # End class Element


###############################################################################
#
class CharacterData(Node):   # , NonBranchable
    """A cover class for Node sub-types that can only occur as leaf nodes
    (and not including Attr either):
        Text, CDATASection, PI, Comment
        (and EntityReference and Notation, now obsolete)

    TODO: Careful of the inheritance order. Currently Node < Yggdrasil < list,
    but then NonBranchable can't override lisst ops. Better to take list off
    of the top, and only bring it in via Branchable < list. That also probably
    makes NonBranchable completely unnecessary.
    """
    def __init__(self, ownerDocument:Document=None, nodeName:NMTOKEN_t=None):
        super().__init__(ownerDocument, nodeName)
        self.data = None

    def _isOfValue(self, value:Any) -> bool:
        return self.data == value

    def count(self, x) -> int:
        return 0
    def index(self, x, start:int=None, end:int=None) -> int:
        return None
    def clear(self) -> None:
        return

    def tostring(self) -> str:  # CharacterData (PI overrides too)
        return self.data

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

    def isEqualNode(self, n2) -> bool:  # CharacterData  # DOM3
        if not super().isEqualNode(n2):
            dtr.msg(f"CharacterData super() unequal for {self.nodeName} vs. {n2.nodeName}.")
            return False
        if self.data != n2.data:
            dtr.msg("CharacterData data mismatch:\n    {self.data}\n    {n2.data}")
            return False
        return True

    ### String mutators

    @property
    def textContent(self) -> None:  # CharacterData
        return self.data

    @textContent.setter
    def textContent(self, newData:str) -> None:  # CharacterData
        self.data = newData

    def appendData(self, s:str) -> None:  # WHATWG
        if not self.data: self.data = s
        else: self.data += s

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


    def remove(self, x:Any=None) -> None:
        if x is not None:
            raise KeyError("CharacterData.remove is not like list.remove!")
        self.data = ""


    # Hide any methods that can't apply to leaves.
    #
    LeafChildMsg = "CharacterData nodes cannot have children."
    @property
    def firstChild(self) -> Node:
        raise HReqE(CharacterData.LeafChildMsg)
    @property
    def lastChild(self) -> Node:
        raise HReqE(CharacterData.LeafChildMsg)

    def unlink(self, keepAttributes:bool=False) -> None:  # MINIDOM
        super().unlink()
        self.data = None
        return

    def checkNode(self, deep:bool=True) -> None:  # CharacterData (cf Attr):
        super().checkNode(deep=False)
        assert self.parentNode is None or self.parentNode.isElement
        #assert self.attributes is None and self.childNodes is None
        if self.isPI: assert Rune.isXmlName(self.target)

    obsolete = """
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
    """


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

    def insertNode(self, node:Node, offset:int) -> None:
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
    """Attributes are different:
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
                f"is node type '{ownerElement.nodeType}', not element.")

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
                    self.isId = idh.getIdattrNode(ownerElement) is self
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
        wsn:bool=True, coalesceText:bool=False) -> int:  # Attr
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
            msg = f"Node to compare is not also an Attr, but '{type(n2)}'."
            dtr.msg(msg)
            raise ValueError(msg)
        if not self._nodeNameMatches(n2):
            dtr.msg(f"Attr nodeName mismatch: '{self.nodeName}' vs. '{n2.nodeName}'.")
            return False
        if str(self.nodeValue) != str(n2.nodeValue):
            dtr.msg(f"Attr nodeValue mismatch: '{self.nodeValue}' vs. '{n2.nodeValue}'.")
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

    def checkNode(self, deep:bool=True) -> None:  # Attr
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
        attrName:NMTOKEN_t=None, attrValue:Any=None):
        """On creation, you can optionally set an attribute.
        """
        super(NamedNodeMap, self).__init__()
        self.ownerDocument = ownerDocument
        if attrName: self.setNamedItem(attrName, attrValue)

    def __eq__(self, other:'NamedNodeMap') -> bool:
        """NOTE: Python considers OrderedDicts unequal if order differs.
        But here we want OrderedDict only for serializing, so...
        """
        return dict(self) == dict(other)

    def __ne__(self, other:'NamedNodeMap') -> bool:
        return not (self == other)

    def setNamedItem(self, attrNodeOrName:Union[str, Attr], attrValue:Any=None,
        attrType:str="string") -> None:
        """This can take either an Attr (as in the DOM version), which contains
        its own name; or a string name and then a value (in which case the Attr
        is constructed automatically).
        Note: This does nothing with types, since those are imposed by context.
        We just let the type info go, and can cast to str() and back if/when
        it's inserted into a new context. But ick.
        """
        if isinstance(attrNodeOrName, Attr):
            if attrValue is not None:
                raise ValueError(f"Can't pass both attrValue ({attrValue}) AND Attr node.")
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
            attrNode = Attr(attrNodeOrName, attrValue, attrTypeName=attrType,
                ownerDocument=self.ownerDocument, ownerElement=None)
            self[attrNode.nodeName] = attrNode

    def getNamedItem(self, name:NMTOKEN_t) -> Attr:
        """Per DOM, this returns the entire Attr instance, not just value.
        No exception if absent.
        TODO Anything for namespaces? Prob not since no inheritance needed?
        """
        if name not in self: return None
        theAttr = self[name]
        assert isinstance(theAttr, Attr)
        return theAttr

    def getNamedValue(self, name:NMTOKEN_t) -> Any:
        """Returns just the actual value.
        """
        if name not in self: return None
        assert isinstance(self[name], Attr)
        return self[name].nodeValue

    def removeNamedItem(self, name:NMTOKEN_t) -> Attr:
        #import pudb; pudb.set_trace()
        if name not in self:
            raise KeyError(f"Named item to remove ('{name}') not found.")
        theattrNode = self[name]
        theattrNode.unlink()
        del self[name]
        theattrNode.ownerElement = None
        return theattrNode

    # TODO Implement getNamedItemNS, setNamedItemNS, removeNamedItemNS
    # NamedNodeMap
    #
    def setNamedItemNS(self, ns:str, attrName:NMTOKEN_t, attrValue:Any) -> None:
        NameSpaces.isNamespaceURI(ns, require=True)
        if not Rune.isXmlName(attrName):
            raise ICharE("Bad name '%s'." % (attrName))
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

    def getIndexOf(self, name:NMTOKEN_t) -> int:  # NamedNodeMap
        """Return the position of the node in the source/creation order.
        TODO: NS, incl. any?
        """
        for i, curName in enumerate(self.keys()):
            if curName == name: return i
        return None

    def clear(self) -> None:
        names = list(self.keys())
        for name in names: self.removeNamedItem(name)

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
        if Tname and node.nodeName != Turi: return False   # TODO cf nodeNameMatches
        return True
