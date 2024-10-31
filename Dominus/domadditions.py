#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Extensions for basedom. Mainly these are node-selection methods, drawn
# from a variety of existing APIs.
#
#pylint: disable=W0613, W0212
#pylint: disable=E1101
#
import re
from typing import List, Iterable, Union
import logging

from basedomtypes import InvalidCharacterError, NotSupportedError
from xmlstrings import NameTest  #XmlStrings as XStr, UNormHandler, CaseHandler
lg = logging.getLogger("BaseDOM")

# Provide synonym types for type-hints these common args
#
NodeType = int
NmToken = str

__metadata__ = {
    "title"        : "domadditions",
    "description"  : "Higher-level additions for basedom.",
    "rightsHolder" : "Steven J. DeRose",
    "creator"      : "http://viaf.org/viaf/50334488",
    "type"         : "http://purl.org/dc/dcmitype/Software",
    "language"     : "Python 3.7",
    "created"      : "2016-02-06",
    "modified"     : "2024-10-08",
    "publisher"    : "http://github.com/sderose",
    "license"      : "https://creativecommons.org/licenses/by-sa/3.0/"
}
__version__ = __metadata__['modified']

descr = """See BaseDom.md"""


###############################################################################
#
class EtAdditions:
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

    def set(self, aname:str, avalue:str) -> None:
        return self.setAttribute(aname, avalue)

    def get(self, aname:str) -> str:
        return self.getAttribute(aname)

    @property
    def getroot(self):
        return self.ownerDocument.documentElement

    @property
    def tag(self):
        return self.nodeName  # localName?

    def matches(self):
        raise NotSupportedError("Element.matches")

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
class whatwgAdditions:
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
        raise NotSupportedError("Element.querySelector")

    def querySelectorAll(self):
        """Find all matches to CSS selector
        """
        raise NotSupportedError("Element.querySelectorAll")

    def matches(self:'Node', selector:str) -> bool:
        """Test whether the node is matched bt the selector.
        """
        raise NotSupportedError("Element.matches")

    def children(self:'Node') -> List:
        """Returns only elements.
        """
        theChosen = []
        for ch in self.childNodes:
            if ch.isElement: theChosen.append(ch)
        return theChosen or None

    def closest(self:'Node', selector:str) -> 'Node':
        cur = self
        while (cur is not None):
            if cur.matches(selector): return cur
            cur = cur.parentNode
        return None

    # The classlist then has add/remove/toggle
    @property
    def classList(self) -> List[NmToken]:  # (from whatwg; why hard-code class?)
        return re.split(r'\s+', self.getAttribute('class'))

    @property
    def className(self) -> str:
        return self.getAttribute('class')


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
    def __init__(self, ownerElement:'Node'=None, ownerAttribute:str=None,
        unormTx=None, caseTx=None, naming:NameTest=None,
        vals:Union=None):
        super(DOMTokenList, self).__init__()
        self.ownerElement = ownerElement
        self.ownerAttribute = ownerAttribute
        self.unormTx = unormTx
        self.caseTx = caseTx
        self.naming = naming
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
        if self.unormTx: key = self.unormTx.normalize(key)
        if self.caseTx: key = self.caseTx.normalize()
        if self.naming and not self.naming.nameTest(key):
            raise InvalidCharacterError(f"Key '{key}' is not a valid NAME.")
        return key


###############################################################################
#
class Synonyms:  # TODO: Implement Synonyms?
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
class OtherAdditions:
    """Add hypertext and ID extensions.
        * Way to identify ID attrs via schema
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

    ### Whence?
    ### TODO: Not element specifically, but support sel by type

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

    # Whence?

    @property
    def Id(self) -> str: # ???
        idName = self.hasIdAttribute
        if idName: return self.getAttribute(idName)
        return None

    @property
    def getIdAttribute(self) -> str:
        """This was apparently an old IE addition, now obsolete. But
        if you have a schema handy it can be pretty useful.... Should be doable
        via attr datatyping.
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
