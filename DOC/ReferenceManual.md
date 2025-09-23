==Reference Manual==

===Overview===

This is a pure python implementation of several tools for XML, HTML, and
related languages. It includes:

    * A more Pythonic/modern "DOM++" interface
    * An XML/HTML parser with support for DTDs, attribute defaults,
internal and external entities, configurable case-folding, etc.
    * Convenience features like being able to turn on all the ISO/HTML
named special characters in one step
    * DTD validation (plus some XSD additions)
    * Many element-selection tools drawn from HTML, CSS, whatwg, ETree, etc.
    * Hooks for convenient loading, unloading, pickling, and fully
round-trippable JSON export and re-import.
    * Flexible control of XML output using an option bundle (similar to
Python csv's "Dialect" feature). There are a couple pre-defined dialects,
including one that produces Canonical XML.

This package focuses on a few main goals:

* Pythonic -- for example, getting/setting children of a node with [] just works
(including negative offsets and slices).
So do the other Python list operations.
Enums and generators are available where appropriate.

* Fast -- my benchmarks on fairly large structures show basedom is about
40% faster than minidom.
Of course this will vary depending on countless factors.

* Configurable space/time tradeoffs. Profiling showed that for typical
DOM structures it costs more to create and maintain sibling chains, than
they save. basedom can be set to handle siblings three different ways,
by changing _siblingImpl before creating a document (you cannot safely
change it later, though that wouldn't be too bad to add).

** SiblingImpl.PARENT (the default): siblings are found by searching
the (typically fairly short) parent.childNodes. This saves space and update
time, but will be slow on very wide/bushy trees.

** SiblingImpl.CHNUM: each node stores its position among its siblings. This
makes it things like previousSibling and nextSibling really fast, but
inserting and deleting nodes is slower (all following siblings have to have
their position numbers updated). Operations like getChildIndex() just return
the value instead of having to search.

** SiblingImpl.LINKS: each node stores a direct pointer to its previousSibling
and nextSibling. This costs a little space, and non-trivial update time
when the tree is modified (including during the initial build. NOT doing
this accounts for much of the speed buff over minidom.

* Reliable. Nearly everything is type-hinted. Lint scores are
nearly all 10 (excluding deductions for "TODO" notes).
There is an accompanying unittest suite with about 80% coverage so far.

* Backward compatible -- this should work as a drop-in replacement
for minidom, lxml, and some other tools. Even obsolete features are
usually included where they don't lead to direct conflicts. A few methods
support additional (optional) keyword parameters (for example, a FormatOptions
object can be passed to toprettyxml() to give much more layout and syntax
control.

* Sideways compatible -- basedom provides roundtrippable mapping to and
from JSON. This is implemented in jsonx.py, and
can be hooked to this or another DOM implementation. It uses a specific
mapping for XML structure and semantics, which I call "JSON-X".
It supports all XML node types, such that XML always becomes valid JSON,
and the JSON can be reloaded to get the same DOM back. I have been unable to
find any other XML-to-JSON convertor that handles everything and can round-trip.
If you find places where JSON-X doesn't work as expected, please let me know.

* Modern -- the API includes a lot of more modern features. It supports the
features of more recent DOM versions than does xml.dom.minidom, and includes
many methods from whatWG, HTML DOM, etree, and so on.
Obvious cases include:
    ** whatwg exception names (though the older ones are available as synonyms)
    ** innerXML and outerXML (similar to the HTML DOM),
    ** predicates like node.isElement (instead of node.nodeType == Node.ELEMENT_NODE)
    ** a wide range of element-finders including native implementations
of CSS selectors, XPointers, and several of ETree's query features.
    ** additional tree operations such as leftmost and rightmost descendants,
non-sibling previous/next, etc.

* Character-set aware: SGML (with optional settings), XML,
and HTML (in various versions), have slightly different definitions for
case-ignoring and definition of whitespace and names. None of them directly
support Unicode normalization (for example, you can't set any of them up in
a standard way to handle tags like "fieldset" if the "fi" is a ligature, or countless
other cases. Probably such cases "should" not happen -- but with auto-correct
and many layers of text processing and conversion, they do. If you want,
you can turn on Unicode normalization as well as case-folding (though this may
not yet work in every corner of the API -- it hasn't been a testing priority).

* Extensible -- the parser is handcrafted recursive descent, with specific
Python methods directly corresponding to XML concepts.
Extensions typically sit inside one such method each, under one "if" to
test if they are active. It's really easy to experiment, and with the test suite
you're likely to catch it if something breaks. even [] support for elements
provides a way to register new filter syntaxes, with a prefix scheme so that
many can be supported at once (like URL or XPointer schemes).

* Conforming by default -- basedom provides many separately-choosable
extensions, but ones that affect
what/how XML is parsed (as opposed, say, to added optional arguments
to methods), are off by default.
So unless you specifically turn them on the package
follows all the normal rules, things should be just as you'd expect.
The mechanism for turning them on goes inside
the document (specifically, inside the XML declaration) so that an unaware
XML processor will find a WF error and stop
rather than incorrectly processing a document that uses extensions. If other
tools want to support one or more of the extensions (á la carte), they can recognize
the setting(s) in the XML declaration and interoperate, without messing up
their handling of unextended data.

* Helpful -- Exception messages display offending values or types, and often
say what values or types are expected. I think this saves time,
whether the problem is in my code or the user's.


===Extensions related to attributes===

    * attribute datatypes (optionally including all the XSD builtin types,
whose names can also be specified in ATTLIST declarations). With XSD floats,
the IEEE special values such as NaN and -Inf are recognized.
    * Unquoted attributes where the value is an XML NMTOKEN or
unsigned integer.
    * Attributes to be set to "0" or "1" can be abbreviated to just +name or -name.
    * The very first use of an attribute may use "!=" instead of "=", to
make the given value the default thereafter.
    * Methods to get attributes can be passed a "default" argument, as common
    in modern programming languages, which is
returned if the requested attribute does not exist.
    * Id attributes have optional features available throughout the system.
In short:
    ** You can have ID namespaces.
    ** A few simple types of compound IDs are defined, such as IDs that
are accumulated from the like-named attribute on all ancestors, and only
need to be unique in that aggregate form, and "COID"s, with the specific
intent of support co-indexing of elements for overlapping and discontiguous markup.
    ** The API supports a notion of inherited attributes, so you can request
a named attribute and get the value from the nearest ancestor (or self) with it.
    ** Flexible choice of attributes to be treated as IDs:
    AttrChoice = namedtuple("AttChoice", [
        "ens",     # Element's namespace URI, or "##any"
        "ename",   # An element type name, or "*"
        "ans",     # Attribute's namespace URI, or "##any"
        "aname",   # An attribute name (no "*")
        "valgen"   # A callback to calculate an ID string given a node
    ])


===Extensions related to Schemas and DTDs===

    * DOCTYPE can have (when the option is activated)
an NDATA argument to specify a schema language.
DTD, XSD, RelaxNG, and Schematron are predefined.
    * The API suppports getting at schema/DTD info, and setting it up
or changing it at will (for example, even without a DTD you can tell the API
that certain attributes are ID or other XML or XSD types, have defaults, etc.).
    * Loaded doctypes retain the order of declarations so exports can mimic it.
    * ELEMENT and ATTLIST declarations allow name-groups, so you can declare
multiple names at once.
    * Element declarations accept not just the keywords EMPTY and ANY, but
also ANY_ELEMENTS (which is like ANY but does not include #PCDATA).
    * The usual *, +, and ? repetition operators in content models
are joined by {min,max} (like PCRE regexes and XML Schema min/maxOccurs).
    * A new <!IDSPACE spaceName attrName> to declare what attribute
name (other than the special xml:id case) holds IDs. 'spaceName' can be
used to define multiple, non-interacting ID spaces (that is, IDs in one
space can have the same lexical values as IDs in another without colliding).
    * ENTITY declarations have a few new subtypes:
    ** SDATA is extended to
support declaring any number of names (simple for brevity).
    ** CTYPE is added to distinguish parameter entities that consist of
a list of names (possibly with connectors, as in SGML) -- this is to
make it much easier to map between XSD and DTD.
    * There is a new content model validator that leverages Python regex processing.

===Extensions related to document markup syntax===

    * </> ends the current element regardless of name.
    * <|> ends the current element and starts a new one of the same name.
    * Marked sections can do slightly more, such as the IGNORE keyword
(including control via entities).
    * Case-folding can be turned on and off separately for element/attribute
names, entity names, reserved words (like #PCDATA), and namespace URIs.
There is a choice of
folding to upper, to lower, or via case_fold, all of which have slightly
different effects in Unicode edge cases.
    * Whitespace can be switched between the definitions used in XML, HTML,
WHATWG, etc.), so tokenizing and normalizing List attributes adjusts.
    * SYSTEM identifiers can have multiple following qlits, to be tried in
order. This is because I constantly have to swap them out when sending
documents back and forth with colleagues, and this way we can both put our paths
in there and forget about it.


===Extensions related to overlapping markup===

A few accommodations are provided, mosty in the parser, for specialized
applications involving markup overlap.
    * You can switch the parser to "olist" mode, in which is it possible to close
any element type that is open, not just the current element. The closed element
is removed from the list of open elements (hence the name), but the list
is not popped back to there. This allows certain kinds of overlapping
structures, discussed in various papers on the MECS system.
    * You can open or close multiple elements truly simultaneously, via syntax
like <b~i> and </b~i>.
    * The parse can track suspend and resume events (inspired by but not
identical to TagML), like <p>...<-p>...<+p>...</p>.
    * I plan to add support for these features and for
Trojan-style milestones in the DOM++ implementation, such as daisy-chain the
items (tbd).


===Layout===

* Everybody gets a shebang line.

* 1 blank line ahead of defs (skipped for groups of one-liners).
2 blank lines and a line of "#" before classes or other major divisions.

* If-conditions and return values not parenthesized; for and while usually are.

* If there is a bunch of inits together, I line up the values for readability.
Yeah, I know I'm weird on that.

and often labelled on the "def" line with a comment giving the class. I find
this helpful for readability.

* Methods that are not part of DOM proper, are tagged by a comment on their
"def" lines, saying where they're from. For

    isElement(self) -> bool:  # HERE
    innerXML(self) -> str:  # HTML
    Text(text:str) -> TextNode:  # WHATWG
    tail(self) -> str:  # ETREE
    writexml(self):  # MINIDOM

This is not done everywhere yet, and I'm debating how best to flag methods
that are in (say) DOM but here added to other classes, methods that add new
parameters, and infrastructure (like Enums, XStrings, etc). I have not
generally labelled methods that are normal Python ones, such as built-in
list or dict operations that Node and NamedNodeMap (respectively) get.


===Names===

Filenames are all lower case, classes are camelcase with initial cap.
For example, class XmlStrings is found in xmlstrings.py.

* Names with acronyms camelcase them (such as "XmlStrings" and "Id"), unless there's
a preexisting one to follow (such as innerHTML going to innerXML, not innerXml).

* Names I find too long (such as "createProcessingInstruction"
commonly have synonyms (such as "createPI").

* I don't like that XPath uses "preceding" and "following" but
DOM uses "previous" and "next". So either form works.

* Attr vs. Attribute, DocType vs. Documenttype, cdataMarkedSection,...

* Variables for character lists, syntactic constructs, etc.
(such as namechars, spacechars, etc.:

** Plain lists of characters as strings end in "_list".

** Arrays of (start,end) pairs used to make regexes for things like Xml name
start characters end in "_rangelist" (these are all in xmlstrings).

** Variables holding regexes end in "_re".

** Types created by NewType to help with type-hinting (these generally
correspond to XSD built-in datatypes) end in "_t". These exist but are not
fully integrated with the XSD type handling in general (yet), since NewType
normally only affects things like pylint.

** Protocol or ABC classes are defined above class that are expected to be
"pluggable", and are named the same but with "_P" appended:
    DOMImplementation_P --> DOMImplementation
    XMLParser_P --> XMLParser

TODO: I may switch PlainNode to be a protocol class or ABC.


===Methods vs. Properties vs. Instance variables===

* Properties that don't need arguments are that way, unless a prior spec
defines them otherwise. If there's a variation with arguments, it's the
same but with "_" added on the front.


===Enumerated options===

* Keyword options that take reserved string values mostly use an Enum
(defined in basedomtypes.py except for some done locally where used).
They subclass from FlexibleEnu, so that methods that take them accept
either an instance of the enum, or the equivalent string or value:
E.A form, but also E("A"), E(E.A), and even E(value) for the value of E.A.
Mainly this is so callers don't have to care which they use, while having
backward compatibility.


========================================================================
===Class overview: basedom.py===

========================================================================
====class DOMImplementation(DOMImplementation_P)====
    name = "BaseDOM"
    version = "0.1"

    createDocument(self, namespaceURI:str=None, qualifiedName:NMTOKEN_t=None,
        doctype:'DocumentType'=None) -> 'Document':
    createDocumentType(self, qualifiedName:QName_t,
        publicId:str, systemId:str, htmlEntities:bool=False) -> 'DocumentType':
    getImplementation() -> type:
    parse(self, f:Union[str, IO], parser=None, bufsize:int=None) -> 'Document':
    parse_string(self, s:str, parser=None) -> 'Document':


========================================================================
====class NodeList(list)====

This is essentially just a list of Node objects. It is never the parent of those
nodes. However, as with Node, __contains__() is non-recursive, while
contains() is recursive, and synonymous with hasDescendant().

A NodeList can be passed to a left-hand side [] slice (though not (yet) with
a "step" argument):
    myNode[2:-5] = NodeList(...)


========================================================================
====class PlainNode(list)====

This is an abstract superclass for Node, which is mostly limited to basic DOM
functionality (not extensions). However, it does include some mainly-internal
methods such as getChildIndex(), which it needs as infrastructure.

    ELEMENT_NODE, etc.
    ABSTRACT_NODE (0) is used for PlainNode and Node instances)

    ownerDocument:Document
    parentNode:Node
    nodeType:NodeType = NodeType.NONE
    nodeName:NmToken_t
    inheritedNS:dict
    userData:dict
    prevError:str (really just for debugging)

Note: There are no attributes or other Element-specific fields here.

Constructor
    __init__(self, ownerDocument=None, nodeName:NMTOKEN_t=None)

Predicates
    canHaveChildren(self) -> bool
    __contains__(self, item:Node) -> bool
    contains(self, other:Node) -> bool
    hasDescendant(self, other:Node) -> bool
    isSameNode(self, n2) -> bool
    isEqualNode(self, n2) -> bool

Properties
    (property) prefix(self) -> str
    (property) localName(self) -> str
    (property) namespaceURI(self) -> str
    (property) childNodes(self) -> Node (this just returns self!)
    (property) isConnected(self) -> bool
    (property) nodeValue(self) -> str
    (property) nodeValue(self, newData:str="") -> str (always returns None for PlainNode)
    (property) parentElement(self) -> Node

Sibling properties -- Profiling found that it takes more time to maintain
a doubly-linked list of siblings than to just look them up in the parent
via getChildIndex() when needed, unless the tree gets extremely bushy.
Also, a large share of nextSibling/previousSibling use is for iteration,
which can be done easily and quickly via "for childNode in myNode" or
"for i in range(len(self))" or similar.
    (property) nextSibling(self) -> Node
    (property) previousSibling(self) -> Node

Changing to explicit sibling links should only require changing the constructors,
insert(), and remove(). They could also use lazy setting (say,
only setting them when insert() adds to a very wide node):
    @property
    nextSibling(self):
        if hasattr(self, '_NSib'): return self._NSib
        n = self.getChildIndex()
        if n < len(self.parentNode)-1: return self.parentNode[n+1]
        return None

Child-list methods
    __setitem__(self, picker:Union[int, slice], value: Node) -> None
    __getitem__(self, picker:Any) -> Union[Node, 'NodeList']
    __filter__(self, f:str) -> Any (see below)
    getChildIndex(self, onlyElements:bool=False, ofNodeName:bool=False,noWSN:bool=False) -> int
    getRChildIndex(self, onlyElements:bool=False, ofNodeName:bool=False,noWSN:bool=False) -> int
    appendChild(self, newChild:Node) -> None
    append(self, newChild:Node) -> None

Several methods accept either an actual child Node, or a signed int position.
    insertBefore(self, newChild:Node, oldChild:Union[Node, int]) -> None
    insertAfter(self, newChild:Node, oldChild:Union[Node, int]) -> None
    removeChild(self, oldChild:Union[Node, int]) -> Node
    _expandChildArg(self, ch:Union[Node, int]) -> (int, Node)
-- given either a child node or an int, this returns both.
    _normalizeIntIndex(self, key:int)
-- given a signed int index, this returns the non-negative form.

    insert(self, i:int, newChild:Node) -> None
    clear(self) -> None
    pop(self, i:int=-1) -> Node
    remove(self, x:Any=None) -> Node
    reverse(self) -> None
    sort(self, key:Callable=None, reverse:bool=False) -> None

These are standard list methods, exceot that those which would have been
in-place (the dunders) return NodeLists instead. This is because you can't
put the identical node at multiple places in the same tree):
    reversed(self) -> NodeList
    sorted(self, key:Callable=None, reverse:bool=False) -> NodeList
    __imul__(self, x) -> 'NodeList'
    __rmul__(self, x) -> 'NodeList'
    __add__(self, other) -> 'NodeList'
    __iadd__(self, other) -> 'NodeList'

Other mutators
    cloneNode(self, deep:bool=False) -> Node
    normalize(self) -> None
    _resetinheritedNS(self) -> None
-- this is an internal method to manage namespace inheritance when elements
are moved to new contexts.
    _filterOldInheritedNS(self, newChild:'Element') -> None

Other
    writexml(self, writer:IO,indent:str="", addindent:str="", newl:str="",encoding:str=None, standalone:bool=None) -> None
    count(self, x:Any) -> int
    index(self, x, start:int=None, end:int=None) -> int
    _isOfValue(self, value:Any) -> bool
    __mul__(self, x:int) -> 'NodeList'
    getInterface(self) -> None (raises NotSupportedError)
    isSupported(self) -> bool (raises NotSupportedError)
    unlink(self, keepAttributes:bool=False) -> None

Notes on [] support

    __setitem__() is overridden so it correctly updates the old and new
nodes (for example, changing parentNode). Thus you can
just do item/slice assignment to modify a node's childNodes list.
__setitem__ accepts signed integer indexes or Python slice objects.
It uses replaceChild(), removeChild(), and insert() to do the real work.

    __getitem__() is overridden as well. It doesn't have to mess with
parentNode, but does add extensions which allow other things besides integers
and integer slices inside the [].
For discussion of this approach see
DeRose, Steven J. “JSOX: A Justly Simple Objectization for XML.”
Balisage 2014, Washington, DC, August 5-8, 2014.
https://doi.org/10.4242/BalisageVol13.DeRose02.

Some examples:

    myNode["para"]         [ x for x in myNode if x.isElement and x.nodeName=="para" ]
    myNode["para":2:-1]    [ x for x in myNode if x.isElement and x.nodeName=="para" ][2:-1]
    myNode[2:-1:"para"]    [ x for x in myNode[2:-1] if x.isElement and x.nodeName=="para" ]
    myNode["*"]            [ x for x in myNode if x.isElement ]
    myNode["#text"]        [ x for x in myNode if x.isText ] -- and #pi, etc.
    myNode["@class"]       myNode.getAttribute("class")

CSS locators would want to include #id, but that would conflict with #text etc.
For that any other cases, something would have to indicate the right interpretation.
For now I'm going with a URL-like scheme prefix, separated by a colon:
    ["css:#chap1"]
    ["xpath://para[@class='foo']

Such scheme names and handlers can be registered via Document.registerFilterScheme().

    getChildIndex(self, onlyElements:bool=False, ofNodeName:bool=False,
        noWSN:bool=False) -> int

    This returns the position of the node within its parent (or None if unattached).
The options can be used to count only among certain kinds of nodes, such
as determining that this is the Nth element, or Nth "para" element
(or "#text" node, since that's a nodeName too), or ignoring whitespace-only
nodes in counting.

    getRChildIndex() -- just like getChildIndex() but counting back from
the end and returning a negative index.

    _expandChildArg(self, ch:Union[Node, int]) -> (int, Node -- Called
on a parent Node, it takes either a child Node per se (like removeChild()),
or the (signed) integer index of the relevant child. It returns both, and is
just a handy way for other methods to accept either and then use whichever they
prefer. There is a slight cost if you give it a child Node, as it searches
for it among its sibling; but in most cases you probably had to do that
anyway. If the caller happens to know and pass the int, the time is saved;
plus it makes many normal list operations work fine on Node.

    insertBefore(self, newChild:Node, oldChild:Union[Node, int]) -> None
    insertAfter(self, newChild:Node, oldChild:Union[Node, int]) -> None -- added just for symmetry.
    removeChild(self, oldChild:Union[Node, int]) -> Node

All these can take the actual child Node (as if DOM), or the index as
described above. Thus although appendChild() is provided you never need it;
you can just insert at any position greater than the length as with regular lists.


========================================================================
====class Node(PlainNode)====

This is the main (still abstract) Node class, from which other Node type
classes are derived. Beyond PlainNode, it adds lots of extensions.

Properties
    length(self) -> int:
    depth(self) -> int:
    previous(self) -> Node
    next(self) -> Node
    hasChildNodes(self) -> bool:

Node status checks -- these properties make it shorter/more readable than
saying things like "if myNode.nodeType == Node.ELEMENT_NODE...":
    isElement(self) -> bool:
    isAttribute(self) -> bool:
    isText(self) -> bool:
    isCDATA(self) -> bool:
    isEntRef(self) -> bool:
    isPI(self) -> bool:
    isComment(self) -> bool:
    isDocument(self) -> bool:
    isDocumentType(self) -> bool:
    isFragment(self) -> bool:
    isNotation(self) -> bool:
    isWSN(self) -> bool:
    isWhitespaceInElementContent(self) -> bool:
    isFirstChild(self) -> bool
    isLastChild(self) -> bool
    hasSubElements(self) -> bool
    hasTextNodes(self) -> bool
    firstChild(self) -> Node:
    lastChild(self) -> Node:
    leftmost(self) -> Node
    rightmost(self) -> Node

    bool() -- Unlike typical Python lists, XML empty elements can have lots
of data (type, attributes, context,...). Empty ones are in principle not
equivalent. So casting all empty elements to boolean as False (merely because
they have no children) could be super confusing.
Node overrides bool() so empty elements do not come out the same as None.

Neighbor/axis extensions

Besides the DOM "previousSibling" and "nextSibling" properties already on PlainNode,
Node defines "previous" and "next" to get the adjacent node in document order,
whether or not it's a sibling. For example, from the very last descendant
of a node N, "next" gets N's following sibling, or if there is no
such sibling, N's parent's next sibling, and so on.

Node also add properties to get the first item along the XPath axes via
their XPath names (though without hyphens because
you can't have hyphens in Python identifiers). So you also have:
    "precedingSibling" = "previousSibling"
    "followingSibling" = "nextSibling"
    "preceding" = "previous"
    "following" = "next"
    "parent" = "parentNode"

The XPath "self" axis is not included, because "self" is not only a Python
reserved word, but not typically needed (you already have a named for that node
if you're calling these methods on it in the first place). Nor are attributes
provided in this fashion, since they'd need a parameter, which is inconvenient
for Python properties, and there's already a ton of way to get at them.

Node also provides methods (not properties) to return the entirety of an
XPath axis as a NodeList, names as plurals:
    "precedingSiblings" or "previousSiblings"
    "followingSiblings" or "nextSiblings"
    "precedingNodes" or "previousNodes" (not yet)
    "followingNodes" or "nextNodes" (not yet)
    "ancestors"
    "children" (this is NodeList(n.childNodes), not merely n.childNodes)
    "descendants"

And finally, there are generators. They also have some options:
    * excludeNodeNames takes a string or list of nodeNames to be skipped;
the entries can be localnames, qnames, reserved names like #text, or "*"
for elements-only (these are the same values that work in __getitem__ and [].
    * includeSelf can be set to True to add the subject node
    * separateAttributes can be set to also get Attr items immediately
after each yielded Element node (so far, just on eachNode and eachSaxEvent)

    eachAncestor()
    eachChild()
    eachNode()
    eachSaxEvent()

I'll likely add the rest of the axis generators, but haven't yet.

    __eq__() and the rest of the comparisons are provided, and use
document order as the criterion. Since a node can only appear in one place
in document order, eq and ne also amount to identity comparison.

    nodeNameMatches(self, other) -> bool:
    textContent(self) -> str
    textContent(self, newData:str) -> None
    compareDocumentPosition() -- like DOM3
    getRootNode() -- like WHATWG
    isDefaultNamespace() -- like DOM3
    lookupNamespaceURI(self, prefix:NMTOKEN_t) -> str:
    lookupPrefix(self, uri:str) -> str:
    prependChild() -- for symmetry with appendChild()

    changeOwnerDocument(self, otherDocument:'Document') -> None:
    replaceChild(self, newChild:Node, oldChild:Union[Node, int]) -> None:
    getUserData(self, key:str) -> Any
    setUserData(self, key:NMTOKEN_t, data:Any, handler:Callable=None) -> None:

Serializers, which all eventually got to toprettyxml():
    outerXML (getter and setter) -- by analogy with HTML DOM
    collectAllXml(self) -> str
    __reduce__(self) -> str
    __reduce__ex__(self) -> str
    tostring(self) -> str
    toxml(self, indent
    tocanonicalxml(self) -> str
    toprettyxml(self, foptions, **kwargs) -> str -- this takes a wide
range of options, either as a FormatOptions object (see next) or
individual keyword parameters.

    getNodePath(self, useId:str=None, attrOk:bool=False, wsn:bool=True) -> str:
Create an XPointer.XPointer path to the Node. If 'useId' is set,
start it with the ID of the lowest ancestor that has one. If 'attrOk'
is set and the Node is an Attribute Node, identify the attribute
by a last component of /@name.

    getNodeSteps(self, useId:bool=False, attrOk:bool=False, wsn:bool=True) -> List:
Like getNodePath(), but return the items as a List instead of joining them
into a "/"-separated string.

    useNodePath(), useNodeSteps() -- interpret a result from getNodePath() or
getNodeSteps() to obtain an actual Node (or None on failure).

    before(), after(), replaceWith() -- per WHATWG

Generators
    eachChild((self:Node, excludeNodeNames:Union[List,str]=None) -> Node:
Generate the children of the Node, in document order.
If excludeNodeNames is set, skip childNodes
whose names are list there (in str form, separated by spaces).

    eachNode(self, separateAttributes:bool=False,
        excludeNodeNames:Union[List,str]=None) -> Node:
Like eachChild(), but all descendants. If 'separateAttributes' is set, also
generate the attributes immediately after the start tag for their element.

    eachSaxEvent(self:Node, separateAttributes:bool=False,
        excludeNodeNames:Union[List,str]=None) -> Tuple:
Generate tuples that corresponds to the SAX events that would be returned from
parsing the XML equivalent of the DOM subtree. The tuples
generated include a SaxEvent instance identifying the type, following by
the usual data for that event type. If 'separateAttributes' is set,
generate a separate events for each attribute rather than passing all the
attributes as additional parameters on starttag events.

    checkNode(depp:bool=True) -- run a fairly thorough check on the node.
If 'deep' is set, recurse to check all descendants.


========================================================================
====class FormatOptions====

This provides options for how serialization of a DOM to XML happens.
It mainly affects toprettyxml(), but most other serializers use that
anyway.

To use these options, create a FormatOptions object and pass it to the
"foptions" option of toprettyxml() or various other methods:

    myFO = FormatOptions(opt1=val1,...)

Format options marked "TODO" are not yet implemented, though the names are
defined.

    # Whitespace insertion
    self.newl:str = "\n"            # String for line-breaks
    self.indent:str = ""            # String to repeat for indent
    self.wrapTextAt:int = 0         # Wrap text near this interval      TODO
    self.dropWS:bool = False        # Drop existing whitespace-only text nodes
    self.breakBB:bool = True        # Newline before start tags
    self.breakAB:bool = False       # Newline after start tags
    self.breakAttrs:bool = False    # Newline before each attribute
    self.breakBText:bool = False    # Newline before each text node
    self.breakBE:bool = False       # Newline before end tags
    self.breakAE:bool = False       # Newline after end tags

    # Syntax alternatives
    self.canonical:bool = False     # Use canonical XML syntax?         TODO
    self.encoding:str = "utf-8"     # utf-8. Just utf-8.
    self.includeXmlDcl = True
    self.includeDoctype = True
    self.useEmpty:bool = True       # Use XML empty-element syntax
    self.emptySpace:bool = True     # Include a space before the /
    self.quoteChar:str = '"'        # Char to quote attributes
    self.sortAttrs:bool = False     # Alphabetical order for attributes
    self.normAttrs = False          # Normalize whitespace in attributes

    # Escaping
    self.escapeGT:bool = False      # Escape > in content               TODO
    self.ASCII = False              # Escape all non-ASCII              TODO
    self.charBase:int = 16          # Char refs in decimal or hex?      TODO
    self.charPad:int = 4            # Min width for numeric char refs   TODO
    self.htmlChars:bool = True      # Use HTML named special characters TODO
    self.translateTable:Mapping = {} # Let caller control escaping

There are no current options for controlling newlines around PIs, comments,
or CDATA sections.

One more option, tagInfos, is a dict that maps element type names to
CSS "display" property values ("inline", "block", etc). This is mainly
useful in the case of inlines: any tag names assigned the value "inline"
are exempt from the "breakXX" options. There are methods to set a string
or list of tag names to "inline", to assign a dict of name:displayvalue pairs,
or to read a simple listing such pairs (some are provided in the DATA/
directory.


========================================================================
====class Document====

As you'd expect, this is the Document as a whole, not the root element.
At the moment, the documentElement must be a single Node -- you cannot, for
example, put comments or PIs before or after it. The XML declaration and Doctype
are special, and owned by the Document object.

    doctype:Documenttype
    documentElement:Node
    encoding:str
    version:str
    standalone:str
    impl:str = 'BaseDOM'
    implVersion:str
    idHandler:IdHandler -- an Object to handler an index of ID values.
    loadedFrom:str
    uri:str
    mimeType:str = 'text/XML'

    options:SimpleNameSpace -- this controls all the optional features.
-- They can be set by adding pseudo-addtributes in the XML declaration. This
put them up front, easy to find; and means that a non-extended XML processor will
stop immediately (upon seeing non-WF values in there), rather than processing
the data incorrectly. For example:
    <!xml version="1.1" encoding="utf=8" IdCase="UPPER" xsdTypes="1"?>

    initOptions(self) -> SimpleNamespace
    registerFilterScheme(self, name:NMTOKEN_t, handler:Callable)
-- lets callers add a new scheme prefix for use in [] with elements.
    domConfig(self) -> None:

Node cconstructors. The usual DOM ones are provided.
So are the WHATWG synonyms like Attr(), Text(), etc (those are just the normal
constructors for those classes, or synonyms to them).

    createElement(self, tagName:NMTOKEN_t, attributes:Dict=None, parent:Node=None,text:str=None) -> 'Element'
    createDocumentFragment(self, namespaceURI:str=None, qualifiedName:str="frag", doctype:str=None, isFragment:bool=True) -> 'Document'
    createAttribute(self, name:NMTOKEN_t, value=None, parentNode=None) -> 'Attr'
    createTextNode(self, data:str) -> 'Text'
    createComment(self, data:str) -> 'Comment'
    createCDATASection(self, data:str) -> 'CDATASection'
    createProcessingInstruction(self, target:NMTOKEN_t, data:str) -> 'ProcessingInstruction':
    createEntityReference(self, name:NMTOKEN_t, value:str=None) -> 'EntityReference':
    writexml(self, writer:IO, indent:str="", addindent:str="", newl:str="", encoding:str=None, standalone:bool=None) -> None

    _getXmlDcl(self, encoding:str="utf-8", standalone:str=None) -> str
    @property
    xmlDcl(self) -> str
    @property
    doctypeDcl(self) -> str
    toprettyxml(self, foptions:FormatOptions=None, **kwargs) -> str
    buildIndex(self, enames:List=None, aname:NMTOKEN_t=None) -> None

Tree searches
    getElementById(self, idValue:str) -> Node
    getElementsByTagName(self, name:str) -> Node
    getElementsByClassName(self, name:str, attrName:str="class") -> Node


========================================================================
====class Element(Node)====

    xmDcl -- this property returns the text of the XML declaration.
    doctypeDcl -- this property returns the text of the doctype declaration.
    _buildIndex() -- forwards to the Document to make an index of IDs.

    index(self, value:Any, start:int, end:int) -> Node
-- This is like the normal list.index() method. However, since an
Element can only occur in one place in a Document, it is less commonly useful
to pass an actual Element to look for. index() therefore merely checks 'value'
against each child's nodeName, so can find the first "p", "#text", etc.
However, if the value passed as target is a Callable, it will be called
for each childNode in the range until it returns True, and that node
will be returned (or None if that never happens).

    getElementById()
    getElementsByTagName()
    getElementsByClassName()

    _addNamespace(self, name:str, uri:str="") -> None:

    @property
    tagName(self) -> NMTOKEN_t: return self.nodeName

    _presetAttr(self, aname:str, avalue:str) -> None -- internal helper

Attributes first appear here (because only Element can have attributes)

DOM needs a range of forms due to the distinction between attribute names,
values, and objects, and attribute's unusual relationship to namespaces.

    hasAttributes(self) -> bool

    hasAttribute(self, aname:NMTOKEN_t) -> bool
    setAttribute(self, aname:NMTOKEN_t, avalue:Any) -> None
    getAttribute(self, aname:NMTOKEN_t, castAs:type=str, default:Any=None) -> str
    removeAttribute(self, aname:NMTOKEN_t) -> None

    setAttributeNode(self, anode:'Attr') -> 'Attr'
    getAttributeNode(self, aname:NMTOKEN_t) -> 'Attr'
    removeAttributeNode(self, anode:'Attr') -> 'Attr'

    hasAttributeNS(self, ns:str, aname:NMTOKEN_t) -> bool
    setAttributeNS(self, ns:str, aname:NMTOKEN_t, avalue:str) -> None
    getAttributeNS(self, ns:str, aname:NMTOKEN_t, castAs:type=str, default:Any=None) -> str
    removeAttributeNS(self, ns, aname:NMTOKEN_t) -> None

    setAttributeNodeNS(self, ns, anode:'Attr') -> 'Attr'
    getAttributeNodeNS(self, ns:str, aname:NMTOKEN_t) -> 'Attr'

Support for a few extended kinds of attributes. Main
    getInheritedAttribute(self:Node, aname:NMTOKEN_t, default:Any=None) -> str
    getInheritedAttributeNS(self:Node,ns:str, aname:NMTOKEN_t, default:Any=None) -> 'Attr'
    getStackedAttribute(self:Node, aname:NMTOKEN_t, sep:str="/") -> str
    getElementById(self, IdValue:str) -> 'Element'

Serializing and loading XML

There are setters and getters for inner and outer XML, similar to the HTML DOM.
The getters are overridden on the various other Node subclasses, so they generate
the correct syntax for those constructs.
The setters use _string2doc() to parse the XML string, first wrapping it so that
it works ok even for just text.

    insertAdjacentXML(self, position:RelPosition, xml:str) -> None
    outerXML(self) -> str
    outerXML(self, xml:str) -> None
    innerXML(self) -> str
    innerXML(self, xml:str) -> None
    _string2doc(self, xml:str) -> Document

Convenience functions create the correct start or end tag for Elements. If you
want options (including FormatOptions options that apply), use _startTag instead
of the startTag propety:
    startTag(self) -> str
    _startTag(self, empty:bool=False, includeNS:bool=False, foptions=None, **kwargs) -> str
    endTag(self) -> str


========================================================================
====class CharacterData(Node)====

A cover class for Node sub-types that can only occur as leaf nodes
(and not including Attr). WHATWG (?) added a number of string operations
for the .data, which are included.

    data -- a string value
    target -- (only for ProcessingInstruction)
    deleteData(self, offset:int, count:int) -> None
    insertData(self, offset:int, s:str) -> None
    remove(self, x:Any=None)
    replaceData(self, offset:int, count:int, s:str) -> None
    substringData(self, offset:int, count:int) -> str

This also overrides several inapplicable methods

    Always return False: contains, hasChildNodes, hasAttributes, hasAttribute
    Always return 0: count
    Always return None: index
    Aways raise HReqE: firstChild, lastChild, __getitem__, append, appendChild, insertBefore, prependChild, removeChild, replaceChild


========================================================================
====class Text(CharacterData)====

    insertNode(self, node:Node, offset:int)
Split the text node at the given offset, and insert node there.
    cleanText(self, unorm:str=None, normSpace:bool=True) -> str


========================================================================
====class CDATASection(CharacterData)====


========================================================================
====class ProcessingInstruction(CharacterData)====


========================================================================
====class Comment(CharacterData)====


========================================================================
====class EntityReference(CharacterData)====

Present but not used or fully implemented.


========================================================================
====class Attr(Node)====

This represents an attribute Node, which has the usual trappings
of Node -- but not of Element (no attributes, siblings, or children.
    name
    value
    ownerElement

Many methods inherited from Node do not apply, and raise Exceptions if used:
    compareDocumentPosition(self, other:Node) -> int
    getChildIndex(self, onlyElements:bool=False, ofNodeName:bool=False,
    isFirstChild(self) -> bool
    isLastChild(self) -> bool
    next(self) -> Node
    nextSibling(self) -> Node
    previous(self) -> Node
    previousSibling(self) -> Node

    clear(self) -> None
    name(self) -> str
    prefix(self) -> str
    localName(self) -> str
    namespaceURI(self) -> str
    nodeValue(self) -> str
    nodeValue(self, newData:str="") -> None
    isConnected(self) -> bool
    textContent(self) -> None
    textContent(self, newData:str) -> None
    nextSibling(self) -> Node
    previousSibling(self) -> Node
    next(self) -> Node
    previous(self) -> Node
    isFirstChild(self) -> bool
    isLastChild(self) -> bool
    getChildIndex(self, onlyElements:bool=False, ofNodeName:bool=False,noWSN:bool=False) -> int

compareDocumentPosition() also raises an Exception, though one could use the
ownerElement's position fairly sensibly instead:
    compareDocumentPosition(self, other:Node) -> int

    toprettyxml(self, foptions:FormatOptions=None, **kwargs) -> str
-- this returns the attribute as it would appear in a start tag (including
escaping as needed).

    tostring(self) -> str
-- this returns *just* the value literally cast to str, and not escaped.
Attributes which do not have an assigned type will already be strings.


========================================================================
====class NamedNodeMap(OrderedDict)====

    __eq__(self, other) -> bool
    __ne__(self, other) -> bool

    setNamedItem(self, attrNodeOrName:Union[str, Attr], avalue:Any=None,atype:str="string") -> None
    getNamedItem(self, name:NMTOKEN_t) -> Attr
    getNamedValue(self, name:NMTOKEN_t) -> Any
    removeNamedItem(self, name:NMTOKEN_t) -> Attr

    setNamedItemNS(self, ns:str, aname:NMTOKEN_t, avalue:Any) -> None
    getNamedItemNS(self, ns:str, name:NMTOKEN_t) -> Any
    getNamedValueNS(self, ns:str, name:NMTOKEN_t) -> Any
    removeNamedItemNS(self, ns:str, name:NMTOKEN_t) -> None

    item(self, index:int) -> Attr
    clone(self) -> 'NamedNodeMap'
    getIndexOf(self, name:NMTOKEN_t) -> int
    clear(self) -> None
    writexml(self, writer:IO,indent:str="", addindent:str="", newl:str="", encoding:str=None, standalone:bool=None) -> None: # MINIDOM
    tostring(self) -> str


========================================================================
====class NameSpaces(Dict)====

    __setitem__(self, prefix:str, uri:str) -> None
    __delitem__(self, prefix:str) -> None
    @staticmethod
    isNamespaceURI(ns:str, require:bool=False) -> bool
    @staticmethod
    nameMatch(node:Node, target:str, ns:str=None) -> bool
