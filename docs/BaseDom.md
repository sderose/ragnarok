=Information on Yggdrasil (nee basedom)=

Yggdrasil (named after the great world tree of Norse mythology),
is a pure Python DOM 3 implementation.
It is intended to be plug-compatible with Python's `xml.dom.minidom`, but
has several of what I consider advantages:

* Yggdrasil covers nearly all of DOM Level 3 Core, not just DOM 2.

* My profiling finds Yggdrasil is much faster than minidom (about 40%)

* Elements and Documents are true subclasses of Python list, and support
all list operations. A few operations differ slightly; for example
multiplying a Node returns a NodeList, because you can't have the identical
node in multiple places (as would be just fine with, say, scalars).

* Unlike minidom's `Element.childNodes`, the whole list API works. You can
insert and delete nodes in the usual Python ways without corrupting the DOM.

* All the usual DOM mutators are there, but those that take a "reference"
child, such as `insertBefore()`, can take either that or a signed integer position.

* Slicing is supported and extended, with the usual Python-style numeric arguments,
as well as string arguments reminiscent of XPath:

    myNode["p"]       -- selects all "p" direct subelements
    myNode["#text"]   -- selects all text node children
    myNode["@class"]  -- selects the `class` attribute
    myNode["*"]       -- selects all element children

There is also provision for registering your own "scheme prefixes", so that
string slicing arguments beginning with that a certain prefix are passed to
a callback of your own, returning whatever NodeList they like.

* Yggdrasil has a complete DocumentType objects (via Schemera),
making that information readily available to users.

* The Schemera representation (q.v.) covers all XML DTD features, and most of XSD.
It can be created:
    * directly via an API
    * loaded from a regular DTD
    * loaded from an XSD (see `xsdload.py`, which is not yet finished),
    * loaded from an extended DTD-like syntax that adds XSD datatypes,
      minOccurs and maxOccurs (via {} in content models); and so on.

* Yggdrasil has Pythonic shortcuts

    * `contains` and `in` work
    * Test document order with `<` and `>` (or with `<<` and `>>` to be like XPath)
    * Test nodeType with predicates like `n.isElement`, `n.isPI`, etc.; and a few
      special ones like `isWSN` and `isWhitespaceInElementContent`
    * Generators and neighbor-getters for all the XPath axes
    * A generator for the SAX events corresponding to any subtree
    * `tostring` on most things, and `toprettyxml` with flexible control
      of formatting via a `FormatOptions` object (similar to csv `dialects`).
    * Constructors are streamlined. For example, `createElement` can take a dict
      of attributes, and optional parent and text arguments.


* Yggdrasil is loaded with methods familiar from the HTML and WhatWG DOM,
XPath, XPointer, and even ElementTree and CSS.

    * `innerXML` and `outerXML`
    * `insertAdjacentXML`, insertBefore, insertAfter, insert
    * `compareDocumentPosition`
    * `.text` and `.tail` setters and getters
    * `parentElement`, `getRootNode`, `firstChild`, `lastChild`, `children`, `descendants`
    * string operations on text and other CharacterData nodes
    * `hasSubElements`, `hasChildNodes`, `hasTextNodes`
    * `getChildIndex` counting from either end, with options to filter by
      nodeType, white-space-onliness, etc.
    * Set operations for multi-token attributes (such as HTML `class`)
    * preceding/following and previous/next are synonymous
    * XPointer child-sequence creation and interpretation, including ID support
    * `replaceChild`
    * `removeNode` (instead of only `x.parentNode.removeChild(x)`)
    * `writexml`; `starttag` and `endtag` properties
    * `depth`, `isFirstChild`,`isLastChild`
    * `leftmost`, `rightmost`

Besides slicing, a variety of searchers:
    * `getElementById`, `getElementsByClassName`, `getElementsByTagName`, `getChildrenByTagName`
    * `querySelect`, `querySelectAll` (substantial but incomplete)

Yggdrasil has pretty extensive unittest coverage, and is tested head-to-head against
minidom (with each on top of either Thor or xml.parsers.expat).


==Pythonic features==

* Nodes look/act a lot like a list of their children (by my count
over half their methods and properties are easily covered by Python list ones
(`append` vs. `appendChild`, `insertBefore` vs. `insert`, `cloneNode` vs. `copy`,
`len` vs. `length`, etc.).

Given that, it sure seems that DOM Element (and Document) should be subclasses
of Python list; but in DOM they are subclasses of Node. Commonly, this means
all the child-related things are implement on Node itself (likely to avoid requiring
multiple inheritance). This has a few problems:

* In minidom the methods and variables related to child nodes (and attributes)
inherit on to lots of things that can't use them. Then you either have
to override them or let them fail.

* Node gets really big, and the bloat is really all about one thing: The
natural distinction of node types that can vs. can't have children (or attributes).

So in Yggdrasil the child-related stuff is segregated into a `Branchable` class,
and attribute-related stuff into an `Attributable` class. Thus two big pieces
of Node become much more cohesive and smaller classes. Then those
classes are mixed in just where needed. For example:

```
    class Branchable(list)
    class Document(Branchable, Node)
    class DocumentFragment(Branchable, Node)
    class Element(Branchable, Attributable, Node)
    class CharacterData(Node)
```

This doesn't look different to the user (except that unlike minidom,
methods are available yet broken where inapplicable). But the code is much
easier to deal with.

Caveat: An Element with no children (an empty element)
casts to boolean True, not False like an empty Python list; that's because it
isn't just "empty" in quite the same way a list or dict is. For example, any two
empty lists or dicts compare equal, while two empty Elements can differ in
nodeName, attributes, etc. To be extra clear, you can test hasChildren instead.


* NamedNodeMap is a subclass of Python OrderedDict.

* Node types are a Python Enum named NodeTypes (with the same names and values
as in DOM Node). Methods accept either NodeTypes instances or ints.

* [] is supported so you can just walk down through trees in Python style:

```
    myDoc[0][27][4]
```

The index value can instead be a string representing an
element type name ("p"), attribute name ("@class"),
nodeType ("#text", "#comment", "#pi"], or a special selector (namely
"#nwsn" for all but whitespace-only text nodes, or "*" for all elements).

```
    myDoc['body']['div']['p']['@class']
```

This produces a NodeList containing Attr nodes,
like an XPath such as body/div/p/@class.

String and numeric indexes can be used together:
    `node["p":3]` gets the 3rd "P" child
    `node[3:"p"]` also gets the 3rd "P" child
    `node["p":1:-1]` gets all "P" children
    `node["*":5]` gets the fifth element child

* Attributes can have values of regular Python types.

* "Symmetric" features are provided -- for example, not just `appendChild`
but also `prependChild`.


===Structure operations===

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

* The whole DOM 3 Core is here, and is intended to work the same
so you don't have to learn anything new or rewrite prior code. But I've also
added popular methods from ElementTree, BeautifulSoup, XPath, WhatWG, etc.

* Where Python provides a conventional method with a different name from DOM's,
both are available. For example, you can do `y = x.cloneNode()` or `y = x.copy()`.


==Separation of XML and Serialization==

* innerXML or outerXML are added, and you can assign an XML string to them.

* A separate Runeheim library is used for XML syntax issues, such as testing
for legit XML NAMEs, case-folding, unescaping, etc. Those methods are of course
available to use directly as well, and don't require instantiating DOM objects.

* Escapers are parts of XML output, so in Gleipnir, not Runeheim.
escapeXML() only escapes ">" when it's in "]]>", not everywhere. There
are special escapers for comments, PIs, CDATA, and Attributes (the last of
which lets you specify whether you're using single or double quotes).
* XML restrictions on names are not automatically checked or enforced. You can
use other names, though XML serialization will complain.

* There is serialization to and from JSON, via Bifrost.
It does idempotent
round-tripping. That is, you don't lose any XML information by serializing
to JSON and then back. This is not even close to true for any other XML-to-JSON
converters I've seen (most do not work (or work very badly, or are unreadable)
for any but unrealistically trivial XML, such as might be built mechanically
from a CSV file. Many lose child order or don't support
mixed content, PIs, comments, etc.


==Yggdrasil sibling chains==

There are (at least) 3 obvious ways to keep track of siblings, and getting
from a given node to an adjacent sibling:

* Just store them in parent.childNodes (and here, just parent[] works the same).

* Have each node know it's current child number.

* Keep a linked list of siblings.

These all have performance tradeoffs, with big differences for building vs.
re-organizing and modifying trees.

In Yggdrasil all 3 methods are available. That doesn't mean all 3 are maintained
all the time -- that would really be slow. But you can pick which one you want.
You can set this at the start, but you can also change it later. The act of changing
it requires a pass over the whole tree, but then it's back to fast again.


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

