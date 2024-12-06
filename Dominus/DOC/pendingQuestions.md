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

* import; getDomImpl; createDoc; parse; use
* Issue of creating doc vs. docElement
* Case is not factored out
* Lack of DTD and schema integration
    * Hence weakening attribute typing, ID finding
* Variety of SAX event names and usage
* Whitespace issues
* Verbose names: ProcessingInstruction, EntityReference, DocumentType,
parentNode, previousSibling, nextSibling (and vs. preceding/following),
ownerDocument, CharacterData, [exception names],...
* Why should documentElement have to be a singleton?
    ** XML requires it, but there's no reason it had to; the grammar would be
just fine.
    ** It forces a Document/DocumentFragment distinction, which complicates
the class structure for little gain (and arguable loss).
    ** Without that rule, Document would just be an Element with no parent,
which is normal for trees. Oh, and a few added properties vars (encoding, etc).


==DOM 3==

    baseURI property
    getUserData()/setUserData() methods
    The whole Node.DOCUMENT_POSITION_* constants
    normalizeDocument()
    renameNode()
    adoptNode()
    strict error checking modes
    Most of the DOM Level 3 Load and Save capabilities

==issues with contains==

* __contains__ vs. contains

* removeNode vs. removeSelf vs. del

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
* Should Node be constructable?
* Should lack of attrs/ns/etc be empty or None?
* Should removeAttribute___ unlink from ownerDoc/ownerEl?

    # A Node is its own context manager, to ensure that an unlink() call occurs.
    # This is similar to how a file object works.
    def __enter__(self):
        return self

    def __exit__(self, et, ev, tb):
        self.unlink()


==ID extensions==

** StackID (accumulate down tree, only need to be unique in context)
** CoID (for overlap or other co-indexing)
** How to trigger update of IdIndex?
** IDs take namespace prefixes?


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


==Classes==

* Perhaps derive from UserList instead of list?

* Should PlainNode include the list dunders?

* Split PlainNode and Node from rest of file?

* Whether/how to support EntityRef nodes==

* auto entities, unicode-name ents


==Methods==

* Should toprettyxml() offer options to wrap text/comments?

* should `cloneNode()` copy `userData`?

* charset vs. inputencoding vs. encoding

* Should things test for bad names?
    has/get/set/removeAttribute
    create Element / Attr / Document / PI target
    ID methods???

* Should the whatwg CharacterData ...data calls return the result?
Range errors? Negatives?

* Sync forEachSaxEvent with lxml.sax.saxify

* How best to make case, whitespace, etc. switchable?

* Should useNodePath() count from the node it's invoked on? Or maybe it should
only be on Document anyway?

* What should eq/ne/lt/le/ge/gt do?
For Elements document order seems far
more useful; but what of text, attrs, maybe other CharacterData, where
normal string compare might be better? Order on Attrs is weird -- all attrs
of same node would compare equal. Maybe hide these for CharacterData?

* set operations for class-like atttrs.

* xml.etree.ElementTree.canonicalize()?


==Exceptions==

* Should inner/outerXml
raise HierarchyRequestError, TypeError, or NotSupportedError?

* Should (e.g.) child-related calls on CharacterData raise
HierarchyRequestError (as now and in minidom),
or NotImplementedError vs. DOM NotSupportedError
or InvalidModificationError or TypeError or InvalidNodeTypeError?

* build in xinclude (switchable)?


==Schema stuff==

* global attributes?

* sync doctype to tree.docinfo.internalDTD

* mixin/inclusions -- dcl like incl exceptions?

* Option to make plural attrs be list/dicts/sets? cf xsd

* Vector attrs (maybe just float{3,3}?)

* JsonX mapping for DTDs?


==Other==

* Should I add back sibling threading as an option? Say,
    @property
    def nextSibling:
        return self._NSib if hasattr(self, '_NSib') else self.findNSib()
        getattr(self, '_NSib', self.findNSib())
    @nextSibling.setter:
    def nextSibling(self, theSib:Node):
        if hasattr(self, '_NSib'): self._NSib = theSib
