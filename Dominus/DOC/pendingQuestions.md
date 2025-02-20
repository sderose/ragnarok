==TO DO==

* make NewType via traversing XSDDatatypes (?)
* datatypes vs. units (like wikipedia macro
* more testing for xsparser, documenttype, JBook


==Construction and setup API==

It's a mess -- can I support all of them?

    from xml.dom.minidom import parseString, parse
    dom = parseString(xmlText)
    dom = parse('file.xml')

    from lxml import etree
    tree = etree.fromstring(xmlText)
    tree = etree.parse('file.xml')

    # ElementTree (built-in)
    import xml.etree.ElementTree as ET
    tree = ET.fromstring(xmlText)

    from bs4 import BeautifulSoup
    soup = BeautifulSoup(xmlText, 'xml')
    soup = BeautifulSoup(xmlText, 'html.parser')
    with open('file.xml') as f:
       soup = BeautifulSoup(f, 'xml')

    from pyquery import PyQuery
    pq = PyQuery(xmlText)
    pq = PyQuery(filename='file.xml')

    # Just parsing

    import xml.parsers.expat
    p = xml.parsers.expat.ParserCreate()
    p.Parse(xmlText)

    # SAX (event-based)
    from xml.sax import parse, parseString
    parseString(xmlText, handler)


==General DOM Issues==

* import; getDomImplementation; createDocument; parse; use
* Issue of creating doc vs. docElement
* Case is not fully factored out
* Lack of DTD and schema integration
    * Hence weakening attribute typing, ID finding
* Variety of SAX event names and usage
* Whitespace issues
* Verbose names: ProcessingInstruction, EntityReference, DocumentType,
parentNode, previousSibling, nextSibling (and vs. preceding/following),
ownerDocument, CharacterData, [exception names],...
* Why should documentElement have to be a singleton?
    ** XML requires it, but there's no reason it had to.
    ** It forces unnecessary Document/DocumentFragment distinction.
    ** Without that rule, Document would just be an Element with a few added properties.


==DOM 3==

    baseURI property
    getUserData()/setUserData() methods
    The whole Node.DOCUMENT_POSITION_* constants
    normalizeDocument()
    renameNode()
    adoptNode()
    strict error checking modes
    DOM 3 Load and Save

==Issues with contains==

* __contains__ vs. contains

* empty lists are falsish -- but it seems like empty nodes/elements shouldn't be.

* Python "contains" and "in" work for testing whether one node is a
child of another. This means they are UNLIKE how they work for regular lists.
If you check whether list L2 is inside list L1 in Python, L2 is cast to a
boolean value (True if not empty, False if empty) -- by that rule a Node that
contained one empty node and one non-empty one, would seem to contain any other
node you checked (even nodes from other documents). That's pretty useless in
this context, so "contains" and "in" are overridden for Node and its
subclasses, to check whether the actual node is an actual child.

* This raises an issue with what the boolean values of nodes should be.
An empty list in Python is conventionally false; but an empty Element in DOM
can still have all kinds of information via attributes, so probably should be
True -- it's not "empty" in the same way as a bare list of dict.
Similarly, Attr nodes implement bool() as the bool() of their *value*, so
testing "if myNode.getAttribute("x")" tells you if the attribute exists and
is non-empty, which sure seems Pythonic to me.

* On the other hand, DOM has a "contains" method (not an infix operator),
and "node1.contains(node2)" checks whether node2 is a *descendant*, not
just a child. That method is also available, and does what DOM days. However,
to avoid confusion the author recommends you use the synonymous
"node1.hasDescendant(node2)" instead.


==Semantic questions==

* ABC or Protocols?
* Should PlainNode/Node be constructable?
* Should lack of attrs/ns/etc be empty or None?
* Should removeAttribute___ unlink from ownerDoc/ownerEl?
* removeNode vs. removeSelf vs. del
* child counts in the face of non-normalized text nodes!

    # A Node is its own context manager, to ensure that an unlink() call occurs.
    # This is similar to how a file object works.
    def __enter__(self):
        return self

    def __exit__(self, et, ev, tb):
        self.unlink()

* Should entities declarations have an encoding parameter?

* Parameter entity references cannot occur within declarations in the internal DTD subset - they're only allowed between declarations there. (4.4.1?)

* Should there be a little gadget for giving you the open element stack
disaggregated by namespace? sort of like XCONCUR?

* Add testing specified in Canonical XML 2.0 [https://www.w3.org/TR/xml-c14n2/]

==ID extensions==

** StackID (accumulate down tree, only need to be unique in context)
** CoID (for overlap or other co-indexing)
** How to trigger update of IdIndex?
** Option for IDs with namespace prefixes?


==Namespaces==

* How should ns matching in the face of None and "" work?
* Effect of changing xmlns: attributes.

* Options for:
** ns dcls only at top
** no redefining prefixes
** no ns at all
** ns on ids per se
** alt ways for attr ns
** hierarchical ns
** inherit element ns onto attrs

==Entity stuff==

* Should extEntities and CharEntities be on/off or reject/preserve/expand?

==Classes==

* Should PlainNode include the list dunders? Merge PlainNode w/ Node?

* Split PlainNode and Node from rest of file?

* Whether/how to support EntityRef, DocFrag nodes

* auto entities, unicode-name entities


==Methods==

* Should `cloneNode()` copy `userData`?

* Charset vs. inputencoding vs. encoding

* What should test for bad names? Maybe only on write.
    has/get/set/removeAttribute
    create Element / Attr / Document / PI target
    ID methods???

* Should the whatwg CharacterData ...data calls return the result?
Range errors? Negatives?

* Sync forEachSaxEvent with lxml.sax.saxify

* How best to make case, whitespace, unorm, name def switchable?

* Should useNodePath() count from the node it's invoked on? Or maybe it should
only be on Document anyway?

* What should eq/ne/lt/le/ge/gt do?
For Elements, document order; for Character data, like for str.

* set operations for class-like atttrs?

* xml.etree.ElementTree.canonicalize()? No.


==Exceptions==

* Should inner/outerXml
raise HierarchyRequestError, TypeError, or NotSupportedError?

* build in xinclude (switchable)? meh


==Schema stuff==

* sync doctype to tree.docinfo.internalDTD

* mixin/inclusions -- dcl like incl exceptions?

* Option to make plural attrs be list/dicts/sets? cf xsd

* finish global attribute support and ##anyAttribute

* Vector attrs (maybe just float{n} xsd list type with bounded length?)

* typed attributes: when to cast. Lose or keep original string?
Semantics for isEqualNode? Separate methods/options for cast vs. str values?

* abbreviated attr names? meh

* JBook mapping for DTDs

* Something like "+ANY(namespace, namespace)" -- useful enough to bother?

* Compact way to declare special-char entities:
    ** HTML ones en masse (from option in XML decl)
    ** Unicode-name-derived ones (stock abbrs, or min unique tokens?)
    ** <!SDATA [ name1 int1, ... ]>  Maybe allow multiple ints, and/or 'c'?

Let the property-list dict be empty (or even ommitted?)
if it (a) would only have "~", and with the same value as it's immediate
prior sibling (this is a pretty common case in documents, and is very
like the "<|>" extension).

        [{ "~":"body" },
          [{ "~":"p" }, "This is a short paragraph." ]
          [{}, "And so is this." ]
          [{}, "And this." ]
        ]


==Parsing==

Which XML++ options should also be available in prettyXml?

Treatment/dcl of HTML named entities

unicode name entities? Cf Test/unicodeAbbrs.py, showing that abbreviating
each token but the last to the first 4 characters, only leads to

options to set boolean attribute value? or just base on XSD?


==Other==

* Should getitem work for virtual XPath axes? Not just childNodes, but
maybe: Ancestors, PSibs, FSibs, Prec, Foll, Desc, Attrs (and |self)

* Change RepType.... prob. not an Enum, just a small obj, with a
smart constructor. Add the {} parsing to xsparser.

* With getitem and registerFilterSchema, don't use ":" for the schema sep
because it's also the qname sep. maybe "::" or "?"

* XML allows stuff outside the document element, why shouldn't DOM?


==Options rationale

* Are they sorted right between parsing, formatting, and data structure?

    ** suspend/resume daisychaining
    ** annotation structure (to and from)
    ** DAG/graph not just tree
    ** stuff outside document element
    ** maintain entity structure

==Non-hierarchy==

* Integrate OLIST, TagML, Clix into Dominµs.

* Support full-fledge XPointer ranges as a separate co-ordinated data structure.

* Support export of annotations, inline or out.

* Could a transclusion node be introduced, to allow DAGs or even graphs?
    Traversal would have to prevent circularities; affected methods?
    childInex works if you can only transclude one subtree per
    nodeSteps, parentNode, depth
    searches
    ?subclass of characterData so it doesn't "have" children

* Simultaneity? attrs?

* basedom (?) methods to turn olist or suspend/resume into an annotation, or
into a join of part. So if you get an open, create an element, then later get
a suspend or olist close....


==Serializers==

For FormatOptions, how best to control line-breaking? Most just have a single
'indent' setting. I so far have:
    * choice of newline and indent-string
    * breaking for before and after begin and end-tags
    * breaking before text nodes (TODO: Check for adjacent text n, CDATA,...)
    * breaking before attributes
    * excluding node from boundary breaking (say, for inlines)
    * text wrapping
    * text node stripping and whitespace node discarding

That leaves:
    * preserve-space (pre, etc.)
    * no break between adjacent end-tags (or start-tags)
    * breaking around PI, comment, CDATA, etc.
    * breaking by what things are *meeting*
    [ +/- element, attr, text, pi, comment, ms, dcl ] crossed w/ same set.
But that would be 14**2 = 196 cases.
=========

See also note "Changes I've heard suggested for XML"
