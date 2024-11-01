==Reference Manual==

Overview

This is a pure python implementation of several tools for XML, HTML, and
related languages. It includes:

    * A more Pythonic "DOM++" interface
    * An XML/HTML parser with support for DTDs, attribute defaults,
internal and external entities, etc.
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

It also provides a range of separately-chooseable extensions. All of them are
off by default, so unless you specifically turn them off, the package
follows all the normal rules. The mechanism for turning them on goes inside
the document, and ensures that an unaware XML processor will find a WF error
and stop (rather than incorrectly processing a document that uses extensions).

Extensions related to attributes

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
    * Id attributs have additional features available throughout the system.
In short:
    ** You can have multiple independent ID spaces.
    ** A few simple types of compound IDs are defined, such as IDs that
are accumulated from the like-named attribute on all ancestors, and only
need to be unique in that aggregate form.

Extensions related to document markup syntax

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

Extensions related to DTD/declaration syntax

    * loaded doctypes retain the order of declarations so exports can mimic it.
    * ELEMENT and ATTLIST declarations allow name-groups, so you can declare
multiple names at once.
    * Element declarations accept not just the keywords EMPTY and ANY, but
also ELEMENTS (which is like ANY but does not include #PCDATA.
    * The usual *, +, and ? repetitioin operators in content models
are joined by {min,max} (as in XML Schema and PCRE regexes.
    * Attributes whose value does not permit spaces (basically everything but
CDATA) may also take a repetition suffix, which defines how many tokens are
permitted (?)
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


Extensions related to overlapping markup

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

