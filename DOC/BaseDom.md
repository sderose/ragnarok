=Description=

A pure Python DOM, intended to cover all of DOM Level 2 Core, but be more
Pythonic/convenient than regular xml.dom.minidom.
This can be used independently, and is meant to be a backward-compatible
pluggable replacement for xml.dom.mindom.

It has pretty extensive unittest coverage.

It is about 40% faster than minidom on my testing (which emphasizes large
document structures), though individual methods vary.

==Pythonic features==

* Nodes look/act a lot like a list of their children (by my count
over half their methods and properties are easily covered by Python list ones
(append vs. appendChild, insertBefore vs. insert, cloneNode vs. copy,
len vs. length, etc.). So in BaseDom Node is a subclass of list, with
nearly all the normal operations doing the normal things, including
slice-assignment (which is much faster than iterative insertion).
Does not have __mul__ and __rmul__, though.

Note: A Node with no children
is falsish, just like any empty Python list; if you want to make sure
you haven't got a Node, use "if myNode is None", not just "if myNode".

* NamedNodeMap is a subclass of Python OrderedDict.

* Node types are a Python Enum named NodeTypes (with the same names and values
as in DOM Node). Methods accept either NodeTypes instances or ints.

* [] is supported so you can just walk down through trees in Python style:
    myDoc[0][27][4]

The index value can instead be a string representing an
element type name ("p"), attribute name ("@class"),
nodeType ("#text", "#comment", "#pi"], or a special selector (namely
"#nwsn" for all but whitespace-only text nodes, or "*" for all elements).

    myDoc['body']['div']['p']['@class']

This produces a NodeList containing Attr nodes,
like an XPath such as body/div/p/@class.

String and numeric indexes can be used together:
    node["p":3] gets the 3rd "P" child
    node[3:"p"] also gets the 3rd "P" child
    node["p":1:-1] gets all "P" children
    node["*":5] gets the fifth element child

* Node-generators. You can also tell them to filter by nodeType,
and to generator attributes right after each element, or not. They're
also pretty fast.

* Constructors are streamlined. For example, createElement can take a Dict
of attributes, and optional parent and text arguments.

* There are shorthand Node properties such as isElement, isPI, etc., so you
can just say the shorter of (maybe you don't care, but I find this really
annoying):
    if (x.isElement)...
    if (x.nodeType == Node.ELEMENT_NODE)

* Those properties include isNWSN, which returns true for text nodes that
are *not* just whitespace.

* Attributes can have values of regular Python types.

* "Symmetric" features are provided -- for example, not just appendChild()
but also prependChild().

* You can generate a SAX stream from any subtree, either as a generator
of (eventType, args) tuples, or via event-type callbacks.

* Methods that DOM defines on Node but that do not apply to certain
subclasses (such as manipulating child nodes on non-Elements) are consistently
overridden to raise an Exception. However, queries that are inapplicable
(such as hasAttributes on a non-Element) simply return False.

===Structure operations===

* A variety of handy/readable tests such as isFirstChild, isLastChild,
hasSubElements, hasTextNodes. leftmost and rightmost go all the way down
either subtree edge.

* getChildIndex() tells you your place among siblings.

* CSS selectors are largely supported, which is also much like JQuery "find".

* getNodeSteps() gives you a list of the child numbers that walk you from the
root down to a given node; getNodePath() gives you the same information
but as a "/"-separated string, per the W3C XPointer spec (so you have a simple
way to point to any place in a document, whether or not it has an ID on it).
At option, it will identify and use the nearest ancestor with an ID attribute
to save space, time, and potential breakage.

* useNodePath() and useNodeSteps() interpret such child-number lists to get you
to a particular node.

* Tokenized attributes are a thing, with add/remove/replace for tokens
supported (h/t whatwg). Inherited attributes are also available, where you can
ask for the value of attribute A as set on the nearest container 9if any).

* getAttribute() takes an optional "default" argument, which you get back
if the attribute does not exists.

* You might never need the "NS" calls like "addAttributeNS", etc. (though they
are available for backward-compatibility).
Namespace becomes just an optional attribute on the regular calls; if you don't
provide it, or you set it to "##any" (for compatibility with
various other implementations), any namespace is accepted.

* textContent recursively gathers the text of Element,
Text, CDATA, or Document nodes, optionally with separators for element boundaries.

* When gathering text, you can have a separator (say, " ") added between
text nodes.

===Familiarity===

* The whole DOM (at least through 2) is here, and is intended to work the same
so you don't have to learn anything new or rewrite prior code. But I've also
added popular methods from ELementTree, BeautifulSoup, XPath, etc.

* Where Python provides a conventional method with a different name from DOM's,
both are available. For example, you can do y = x.cloneNode() or y = x.copy()

==Separation of XML and Serialization==

* innerXML or outerXML are added, and you can assign an XML string to them.

* A separate XMLStrings library is used for XML syntax issues, such as testing
for legit XML NAMEs, escaping and unescaping, etc. Those methods are of course
available to use directly as well, and don't require instantiating DOM objects.

* escapeXML() only escapes ">" when it's in "]]>", not everywhere. There
are special escapers for comments, PIs, CDATA, and Attributes (the last of
which lets you specify whether you're using single or double quotes).
* XML restrictions on names are not automatically checked or enforced. You can
use other names, though XML serialization will complain.

* startTag and endTag properties provide the complete tags as needed.

* There is serialization to and from JSON, which guarantees idempotent
round-tripping. That is, you don't lose any XML information by serializing
to JSON and then back. This is not even close to true for any other XML-to-JSON
converters I've seen (most do not work (or work very badly, or are unreadable)
for any but unrealistically trivial XML, such as might be built mechanically
from a CSV file. Many lose child order or don't support
mixed content, PIs, comments, etc.


=To do=

Rename? Maybe SpamNX?
(like spam, spam, baked beans, 'n spam, it ain't got much spam in it)


* Speed
** compareDocumentPosition -- faster by not building all the way to
root, but co-recursing up both sides, only until we hit a common ancestor, then
back down?
** Any more places to avoid getChildIndex()? Already added int position for
insertBefore.
** Fallback to maintaining child-number when fanout gets very high?
*

* Structure and organization
** Segregate namespace into subclass?
** Clean way to make [] extensible -- pass it a callable?
** How to organize CSS, XPath, et, etc. into separate add-on-ish classes.
Protocols?
** Could NamedNodeMap just go away?

* Added functions?
** Add moveNode(s) operation? Meh
** Best way to incorporate case-ignorance.
** findDiffs(self, other)?

* Add cnum to Nodes? Update becomes O(lg2(fanout)). And only enable it when
insert/append takes it above some threshold.

* Would this bit from minidom be useful?

==Testing to beef up==

(see also testingNotes.md)

* Ramp up coverage
* Namespaces, esp. defaulting
* Doctype support
* Test that it generates the *same* Exception types as others?

==DOM compatibility==

* Element
**Add attributes (move from Node) removeAttributeNodeNS, schemaType
** setIdAttribute, setIdAttributeNS, setIdAttributeNode

* Document: ctualEncoding async_ CreateElementNS,
  encoding, errorHandler,
  importNode, load, loadXML, renameNode, saveXML, standalone, strictErrorChecking,
  version
* Keep anything for Ent, EntRef, Notation?
* Attr: isId, name, ownerElement, schemaType, specified, value?
* NodeList: length
* NamedNodeMap: itemNS, keysNS, length

==Node selection==

* More comparison ops for Nodes?
* Finish generalizing node-selection
* Possibly support Callables as arg to getitem? Or namespaced selectors?
** CSS: Selectors (see CSSSelectors.py)
** JQuery: selectors
** BS: find_matcher (see DOMExtensions.py)
** XPath
** ET: SubElement(parent, tag, attrs)
** whatwg: NodeIterator and TreeWalker [https://dom.spec.whatwg.org/#nodeiterator]

==Other==

* Move DOMImplementation, Node, Document, CharacterData to sep files?

* Segregate NS stuff?

* Segregate extensions

* Add from domextensions
    ** innerText
    ** getLeastCommonAncestor
    ** get fqgi
    ** compound attributes?
    ** generateSaxEvents

* Support 'canonical' option for tostring().


=Known bugs and limitations=

* Since Node is a subclass of List, a node with no childNodes is an empty
list, which is Falsish. So code has to specifically check for "is None",
not just t/f, to see if a Node doesn't exist. That why it overrides
__bool__ to return True. Maybe that should be optional, or just not there?


Namespace support is incomplete
* Implement the ...NS() methods (at present they just call the non-NS versions).
* Just make NS an optional arg to the non-NS versions (if no problem)


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
* 2024-06-28ff: Refactor, capitalize "DOM" in names, use instead of copy
XML utility packages, add test suites.


=Rights=

Copyright 2016, Steven J. DeRose. This work is licensed under a Creative Commons
Attribution-Share Alike 3.0 Unported License. For further information on
this license, see [http://creativecommons.org/licenses/by-sa/3.0].

For the most recent version, see [http://www.derose.net/steve/utilities] or
[http://github/com/sderose].


=Options=

