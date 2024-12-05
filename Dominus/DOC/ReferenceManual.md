==Reference Manual==

===Overview===

This is a pure python implementation of several tools for XML, HTML, and
related languages. It includes:

    * A more Pythonic "DOM++" interface
    * An XML/HTML parser with support for DTDs, attribute defaults,
internal and external entities, configrable case-folding, etc.
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

* Pythonic -- for example, you can get at the children of any node
with [] (and do the other Python list operations) and Enums and generators
are available where appropriate.

* Fast -- my benchmarks show the DOM replacement about 40% faster than minidom.

* Reliable -- there is an accompanying unittest suite, which provides over
80% coverage so far.

* Backward compatible -- this should work as a drop-in replacement
for minidom, lxml, and some other tools. Even obsolete features are
usually included where they don't lead to direct conflicts.
If you find places where it doesn't work as expected, please let me know.

* Modern -- the API includes a lot of more modern features. It follows much
more recent DOM versions than xml.dom.minidom.
Obvious cases include
    ** whatwg exception names (though the older ones are available as synonyms)
    ** innerXML and outerXML (similar to the HTML DOM),
    ** predicates like node.isElement (instead of node.nodeType == Node.ELEMENT_NODE)
    ** a wide range of element-finders including native implementations
of CSS selectors, XPointers, and several of ETree's query features.
    ** additional tree operations such as leftmost and rightmost descendants,
non-sibling previous/next, etc.

* Extensible -- the parser is handcrafted recursive descent, with specific
Python methods directly corresponding to XML concepts.
Extensions typically sit inside one such method each, under one "if" to
test if they are active. It's really easy to experiment, and with the test suite
you're likely to catch it if something breaks.

It also provides many separately-choosable extensions. All of them are
off by default, so unless you specifically turn them on the package
follows all the normal rules. The mechanism for turning them on goes inside
the document and ensures that an unaware XML processor will find a WF error
and stop (rather than incorrectly processing a document that uses extensions).


===Extensions related to attributes===

    * attribute datatypes (optionally, including all the XSD builtin types,
whose names can also be specified in ATTLIST declarations). With XSD float,
the IEEE special values such as NaN and -Inf are recognized.
    * Unquoted attributes where the value is an XML NAME or NUMBER.
    * Boolean attributes abbreviated to just +name or -name
    * The very first use of an attribute may use "!=" instead of "=", to
make the given value the default thereafter.
    * The API provides a notion of inherited attributes, so you can request
a named attribute and get the value from the nearest ancestor (or self) with it.
    * Methods to get attributes can be passes a "default" argument, which is
returned if the requested attribute does not exist.
    * Id attributes have additional features available throughout the system.
In short:
    ** You can have multiple independent ID spaces.
    ** A few simple types of compound IDs are defined, such as IDs that
are accumulated from the like-named attribute on all ancestors, and only
need to be unique in that aggregate form.
    ** Flexible choice of attributes to be treated as IDs:
    AttrChoice = namedtuple("AttChoice", [
        "ens",     # Element's namespace URI, or "##any"
        "ename",   # An element type name, or "*"
        "ans",     # Attribute's namespace URI, or "##any"
        "aname",   # An attribute name (no "*")
        "valgen"   # A callback to calculate an ID string given a node
    ])


===Extensions related to Schemas and DTDs===

    * DOCTYPE accepts an NDATA argument to specify a schema language,
and predefines DTD, XSD, RelaxNG, and Schematron.
    * There is a new validator that leverages Python regex processing.
    * The API suppports getting at schema/DTD info, and setting it up
or changing it at will.
    * Loaded doctypes retain the order of declarations so exports can mimic it.
    * ELEMENT and ATTLIST declarations allow name-groups, so you can declare
multiple names at once.
    * Element declarations accept not just the keywords EMPTY and ANY, but
also ANY_ELEMENTS (which is like ANY but does not include #PCDATA).
    * The usual *, +, and ? repetition operators in content models
are joined by {min,max} (as in PCRE regexes and like XML Schema min/maxOccurs).
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

===Extensions related to document markup syntax===

    * </> ends the current element regardless of name.
    * <|> ends the current element and starts a new one of the same name.
    * Slightly more powerful marked sections, such as the IGNORE keyword
(including control via entities). May add a nesting option.
    * Case-folding can be turned on and off separately for element/attribute
names, entity names, and reserved words (like #PCDATA). There is a choice of
folding to upper, to lower, or via case_fold, all of which have slightly
different effects in Unicode edge cases.
    * SYSTEM identifiers can have multiple following qlits, to be tried in
order. This is because I constantly have to swap them out when sending
documents back and forth with colleagues; this way we can both put our paths
in there and forget about it.
    * For those who dislike colons for namespaces, you can swap in a different
character.


===Extensions related to overlapping markup===

A few accommodations may be provided for specialized applications involving
markup overlap.
    * You can choose "olist" mode, in which is it possible to close any
element type that is open, not just the current element. The closed element
is removed from the list of open elements (hence the name), but the list
is not popped back to there. This allows certain kinds of overlapping
structures, discussed in various papers on the MECS system.
    * You can open or close multiple elements truly simultaneously, via syntax
like <b~i> and </b~i>.
    * I am considering adding suspend and resume (inspired by but not
identical to TagML), like <p>...<-p>...<+p>...</p>, and/or direct support for
Trojan-style milestones. The DOM++ implementation will daisy-chain the
items (tbd).


==Conventions==

===Layout===

* Everybody gets a shebang line.

* 1 blank lines ahead of defs (skipped for groups of one-liners).
2 blank lines and a line of "#" before classes or other major divisions.

* If-conditions and return values not parenthesized; for and while usually are.

* If there a bunch of inits together, I line up the values for readability.
Yeah, I know I'm weird on that.


===Names===

Files are all lower case, classes are camelcase with initial cap.
For example, class XmlStrings is found in xmlstrings.py.

* Names with acronyms camelcase them (such as "XmlStrings" and "Id"), unless there's
a preexisting one to follow (such as innerHTML going to innerXML, not innerXml).

* Names I find too long (such as "createProcessingInstruction" normally
have a synonym (such as "createPI").

* Attr vs. Attribute

* P...I.... vs. Proc vs. PI

* Variables for character lists, syntactic constructs, etc.
(such as namechars, spacechars, etc.,

** Plain lists of characters as strings end in "_list".

** Arrays of (start,end) pairs used to make regexes for things like Xml name
start characters end in "_rangelist" (these are all in xmlstrings).

** Variables holding regexes end in "_re".

** Types created by NewType to help with type-hinting (these generally
correspond to XSD built-in datatypes) end in "_t".

** Protocol classes are defined above class that are expected to be
"pluggable", and are named the same but with "_P" appended:
    DOMImplementation_P --> DOMImplementation
    XMLParser_P --> XMLParser

TODO: I may switch PlainNode to be a protocol class (and rename it
Node_P).


===Types===

* Typehints everywhere.

* XSD types are defined as NewTypes (in typesForHints.py). They are named
by the (casely-correct) XSD names, plus "_t" to be clear they're types.
Regexes to match them (ending in "_re"), constraints, etc. are defined in documentType.py.


===Classes and subclasses===

* Methods that are defined in multiple classes (for example, serializers),
and often labelled on the "def" line with a comment giving the class. I find
this helpful for readability.

* Methods that are not part of DOM proper, are tagged by a comment on their
"def" lines, saying where they're from.

    def isElement(self) -> bool:  # HERE
    def innerXML(self) -> str:  # HTML (even though the name there is innerHTML)
    def Text(text:str) -> TextNode:  # WHATWG
    def checkNode(self):  # DBG
    def tail(self) -> str:  # ET
    def writexml(self): # MINIDOM

This is not done everywhere yet, and I'm debating how best to flag methods
that are in (say) DOM but here added to other classes, methods that add new
parameters, and infrastructure (like Enums, XStrings, etc). I have not
generally labelled methods that are normal Python ones, such as built-in
list or dict operations that Node and NamedNodeMap (respectively) get.


===Methods vs. Properties vs. Instance variables===

* Properties that don't need arguments are that way, unless a prior spec
defines them otherwise. If there's a variation with arguments, it's the
same but with "_" added on the front.


===Enumerated options===

* Keyword options are generally an Enum (defined in domenums.py except for
some done locally where used). Methods that take them accept
either an instance of the enum, or the equivalent string.


===Class overview: basedom.py===

(standard DOM methods are not listed here)

====class DOMImplementation(DOMImplementation_P)====
    name = "BaseDOM"
    version = "0.1"

====class FormatOptions====

    (see below)


====class NodeList(list)====

This is essentially just a list of Node. It is never the parent of those
nodes. However, as with Node, __contains__() is non-recursive, while
contains() is recursive, and synonymous with


====class PlainNode(list)====

This is an abstract superclass for Node, which is limited to basic DOM
functionality.

    self.ownerDocument:Document
    self.parentNode:Node
    self.nodeType:NodeType = NodeType.NONE
    self.nodeName:NmToken_t
    self.inheritedNS:dict
    self.userData:dict
    self.prevError:str (really just for debugging)

This has a few extra methods:

    __setitem__() is overridden so it correctly updates the old and new
nodes (for example, changing parentNode, siblings, etc.). Thus you can
just do item/slice assignment to modify a nodes childNodes list.
__setitem__ accepts signed integer indexes, or Python slice objects.
It uses replaceChild(), removeChild(), and insert() to do the real work.

    __getitem__() is overridden as well. It doesn't have to mess with
parentNode etc (because none of that changes), but does for adding extensions
which allow other things inside the [].
For example:

    myNode["para"]         [ x for x in myNode if x.isElement and x.nodeName=="para" ]
    myNode["para":2:-1]    [ x for x in myNode if x.isElement and x.nodeName=="para" ][2:-1]
    myNode[2:-1:"para"]    [ x for x in myNode[2:-1] if x.isElement and x.nodeName=="para" ]
    myNode["*"]            [ x for x in myNode if x.isElement ]
    myNode["#text"]        [ x for x in myNode if x.isText ]
    myNode["@class"]       myNode.getAttribute("class")

CSS locators would want to include #id, but that would conflict with #text etc.
For that any other cases, something would have to indicate the right interpretation.
Many models are possible:
    URI-like:  ["css:#chap1"] or ["css":"#chap1"] or ["css://#chap1"]
    XPointer-like:  ["css(#chap1)"]


Further generalization could be added, but would have to avoid syntax conflicts.
One possibility is having a prefix, maybe like ["css(ul li[secret=0])"].
It may also be feasible to allow
registering a callback so users of the library can add their own method(s).
As elsewhere, no extension (beyond the usual numeric indexes and slices)
is on by default, and turning this extension on only gets you the cases
exemplified above (for discussion of this approach see
DeRose, Steven J. “JSOX: A Justly Simple Objectization for XML.”
Balisage 2014, Washington, DC, August 5-8, 2014.
https://doi.org/10.4242/BalisageVol13.DeRose02.

    getChildIndex(self, onlyElements:bool=False, ofNodeName:bool=False,
        noWSN:bool=False) -> int

    This returns the position of the node within its parent (or None if unattached).
The options can be used to count only among certain kinds of nodes, such
as determining that this is the Nth element, or Nth "para" element
(or "#text" node, since that's a nodeName too), or ignoring whitespace-only
nodes in counting.

    getRChildIndex() -- just like getChildIndex() but counting back from
the end and returning a negative index.

    _expandChildArg(self, ch:Union['Node', int]) -> (int, 'Node' -- Called
on a parent Node, it takes either a child Node per se (like removeChild()),
or the (signed) integer index of the relevant child. It returns both, and is
just a handy way for other methods to accept either and then use whichever they
prefer. There is a slight cost if you give it a child Node, as it searches
for it among its sibling; but in most cases you probably had to do that
anyway. If the caller happens to know and pass the int, the time is saved;
plus it makes many normal list operations work fine on Node.

    insertBefore()
    insertAfter() -- added just for symmetry.
    removeChild()

All these can take the actual child Node (as if DOM), or the index. Indexes
work as for regular Python lists. For example, although appendChild() is
of course provided you never need it; you can just insert at any position
greater than the length.

The usual Python list operations work, and do the correct patching of
siblings and such: count, index, append, insert, clear, pop, remove,
reverse, reversed (which necessarily has to clone a copy), sort,
__mul__, __rmul__, __add__, __iadd__

    unlink() -- like minidom, and for the same reason.


====class Node(PlainNode)====

This is the main (still abstract) Node class, from which other Node types
classes are derived. Beyond PlainNode, it add the NodeType constant
and adds lots of extensions.

    bool() -- Unlike typical Python lists, XML empty elements can have lots
of data (type, attributes, context,...). So casting them to boolean False
could be super confusing. Node overrides bool() to extant empty elements do
not come out the same as None.

    __eq__() and the rest of the comparisons are provided, and use
document order as the criterion. Since a node can only appear in one place
in document order, eq and ne also amount to identity comparison.

    __getitem__() is added here, to enable using [] much more flexibly.
All the usual slicing already works, but this adds selecting child nodes
by nodeName ("p", "#text", etc), selecting attributes by name ("@id"), etc.

    next() and previous() -- return the specified nodes as defined in XPath.

    compareDocumentPosition() -- like DOM3
    getRootNode() -- like WHATWG
    isDefaultNamespace() -- like DOM3
    prependChild() -- for symmetry with appendChild()
    removeNode() -- Nodes know where their parent is, so you can call them
to remove themselves.

    isElement etc. -- shorthand properties for all the NodeTypes
    isWSN -- is the node a whitespace-only text node?
    isWhitespaceInElementContent, isFirstChild, hasSubElements, hasTextNodes -- extensions
    leftmost, rightmost -- return the further descendant along left/right tree edge
    outerXML (getter and setter) -- by analogy with HTML DOM

    A variety of serializers, which all eventually got to toprettyxml():
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

    eachChild((self:'Node', excludeNodeNames:Union[List,str]=None) -> 'Node':
Generate the children of the Node, in document order.
If excludeNodeNames is set, skip childNodes
whose names are list there (in str form, separated by spaces).

    eachNode(self, includeAttributes:bool=False,
        excludeNodeNames:Union[List,str]=None) -> 'Node':
Like eachChild(), but all descendants. If 'includeAttributes' is set, also
generate the attributes immediately after the start tag for their element.

    eachSaxEvent(self:'Node', separateAttributes:bool=False,
        excludeNodeNames:Union[List,str]=None) -> Tuple:
Generate tuples that corresponds to the SAX events that would be returned from
parsing the XML equivalent of the DOM subtree. If 'separateAttributes' is set,
generate a separate events for each attribute rather than passing all the
attributes as additional parameters on starttag events. The tuples
generated include a SaxEvent instance identifying the type, following by
the usual data for that event type.

    checkNode(depp:bool=True) -- run a fairly thorough check on the node.
If 'deep' is set, recurse to check all descendants.


====class FormatOptions====

This is a big batch of options for how serialization of a DOM to XML happens.
Ones marked "TODO" are not yet implemented, though the names are known.

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

    self.inlineTags:List = []       # List of inline elements, no breakXX.

    # Syntax alternatives
    self.canonical:bool = False     # Use canonical XML syntax?         TODO
    self.encoding:str = "utf-8"     # utf-8. Just utf-8.
    self.includeXmlDcl = True
    self.includeDoctype = True
    self.useEmpty:bool = True       # Use XML empty-element syntax
    self.emptySpace:bool = True     # Include a space before the /
    self.quoteChar:str = '"'        # Char to quote attributes          TODO
    self.sortAttrs:bool = False     # Alphabetical order for attributes
    self.normAttrs = False          # Normalize whitespace in attributes

    # Escaping
    self.escapeGT:bool = False      # Escape > in content               TODO
    self.ASCII = False              # Escape all non-ASCII              TODO
    self.charBase:int = 16          # Char refs in decimal or hex?      TODO
    self.charPad:int = 4            # Min width for numeric char refs
    self.htmlChars:bool = True      # Use HTML named special characters
    self.translateTable:Mapping = {} # Let caller control escaping


====class Document====

        nodeType:NodeType
        nodeName:NmToken_t
        inheritedNS:Dict
        doctype:Documenttype
        documentElement:Node
        documentElement:Node

        encoding:str
        version:str
        standalone:str

        impl:str = 'BaseDOM'
        implVersion:str
        options:SimpleNameSpace
        idHandler:IdHandler
        loadedFrom:str
        uri:str
        mimeType:str = 'text/XML'


====class Element(Node)====

In addition to the usual createElement() etc., has the WHATWG synonyms
like Attr(), Text(), etc.

    xmDcl -- this property returns the text of the XML declaration.
    doctypeDcl -- this property returns the text of the doctype declaration.
    _buildIndex()
    getElementById()
    getElementsByTagName()
    getElementsByClassName()


====class CharacterData(Node)====

A cover class for Node sub-types that can only occur as leaf nodes
(and not including Attr). These all have a string value as .dat
(plus .target for PIs).

    deleteData(self, offset:int, count:int) -> None
    insertData(self, offset:int, s:str) -> None
    remove(self, x:Any=None)
    replaceData(self, offset:int, count:int, s:str) -> None
    substringData(self, offset:int, count:int) -> str

This also overrides several inapplicable methods:

    Always return False: contains, hasChildNodes, hasAttributes, hasAttribute
    Always return 0: count
    Always return None: index
    Aways raise HReqE: firstChild, lastChild, __getitem__, append, appendChild, insertBefore, prependChild, removeChild, replaceChild


====class Text(CharacterData)====

    cleanText


====class CDATASection(CharacterData)====


====class ProcessingInstruction(CharacterData)====


====class Comment(CharacterData)====


====class EntityReference(CharacterData)====

Present but not used or fully implemented.

====class Attr(Node)====

This represents an attribute Node, which has the usual trappings
of Node, except that attributes have no siblings or children
    name
    value
    ownerElement

so these raise:
    def compareDocumentPosition(self, other:'Node') -> int:  # Attr
    def getChildIndex(self, onlyElements:bool=False, ofNodeName:bool=False,
    def isFirstChild(self) -> bool:
    def isLastChild(self) -> bool:
    def next(self) -> 'Node':  # XPATH
    def nextSibling(self) -> 'Node':
    def previous(self) -> 'Node':  # XPATH
    def previousSibling(self) -> 'Node':


====class NamedNodeMap(OrderedDict)====


====class NameSpaces(Dict)====



========

========

========

========

========
