==To decide or do==

==Option switching==

    <?xml ... opt1=val1...?>

    <?loki ...?>

    <?loki bull=0x2022 AGr=0x0391... ?>

    <?loki ename=para aname="class:NMTOKENS=normal" ?>


==XmlStrings==

* switchable xml 1.0 v 1.1 names?

* Charset vs. inputencoding vs. encoding


==Parsing Options==

Does piAttrs mean all PI must conform, or just targets with ATTLIST dcls?

limits like maxName, maxElementDepth, maxMSDepth, maxAttrs, maxChildren?

* nestable comments

consider defusedxml features

attribute ns: xmlns@path=svg ? <!ATTLIST foo svg:path CDATA IMPLIED> ?

* Change RepType.... prob. not an Enum, just a small obj, with a
smart constructor. Add the {} parsing to xsparser.

* To-straight-XML driver for xsparser (incl. non-hier mapping)

* build in xinclude (switchable)? meh

* Let error reporting provide whole tagStack of locations


==Schema stuff==

* sync doctype to tree.docinfo.internalDTD?

* mixin/inclusions -- dcl like incl exceptions?

* plural XSD types?

* typed attributes: when to cast. Lose or keep original string?
Semantics for isEqualNode? Separate methods/options for cast vs. str values?

* abbreviated attr names? meh

* Accept \& and \<? ok?

* Autogenerate wrappers from heads?

* <!SDATA [ name1 int1, name2 int2... ]>

* Should entity declarations have an encoding parameter?

* Parameter entity references cannot occur within declarations in the internal DTD subset - they're only allowed between declarations there. (4.4.1?)


==Dominµs stuff==

* __contains__ vs. contains

* Should PlainNode/Node be constructable?

* Make sure splicing multiples in/out doesn't go n**2 on sibling update

* Should lack of attrs/ns/etc be empty or None?

* Should removeAttribute___ unlink from ownerDoc/ownerEl?

* Should getitem work for virtual XPath axes? Not just childNodes, but
maybe: Ancestors, PSibs, FSibs, Prec, Foll, Desc, Attrs (and |self)

* With getitem and registerFilterSchema, don't use ":" for the schema sep
because it's also the qname sep. maybe "::" or "?"

* XML allows stuff outside the document element, why shouldn't DOM?

* Should `cloneNode()` copy `userData`?

* What should test for bad names? Maybe only on write.
    has/get/set/removeAttribute
    create Element / Attr / Document / PI target
    ID methods???

* Should the whatwg CharacterData ...data calls return the result?
Range errors? Negatives?

* Sync forEachSaxEvent with lxml.sax.saxify

* Should useNodePath() count from the node it's invoked on? Or maybe it should
only be on Document anyway?

* set operations for class-like atttrs?

* Additional slicing operators?
    ** "**" or asterism for element + text (non-wsn?)
    ** "/" for root
    ** ".." for parent
    ** "^^" for ancestors?

* DOM 3
    baseURI property
    getUserData()/setUserData()
    The whole Node.DOCUMENT_POSITION_* constants
    normalizeDocument()
    renameNode()
    adoptNode()
    strict error checking modes
    DOM 3 Load and Save


==Non-hierarchy==

* Serialization using extensions?
    ** suspend/resume daisychaining
    ** annotation structure (to and from)
    ** DAG/graph not just tree
    ** stuff outside document element
    ** maintain entity structure

Which xsparser options should also be available in FormatOptions?

* Option to write Loki options into the XML dcl?

* Integrate OLIST, TagML, Clix into Dominµs.

* Support full-fledged XPointer ranges.

* Simultaneity and co-location
    * If these are truly co-located, then should <|> be, too?
    * Should <a/b/c> also define co-location?
    * Can you combine olist and multiTag?
    * Can you mix starts and ends in multiTag?

* Could a transclusion node be introduced, to allow DAGs or even graphs?
    Traversal would have to prevent circularities; affected methods?
    childInex works if you can only transclude one subtree per
    nodeSteps, parentNode, depth
    searches
    ?subclass of characterData so it doesn't "have" children

* turn olist or suspend/resume into an annotation, join, etc.?

* Should there be a way to assert that a specific element's children do
not have a defined order? So they get stuck in a set maybe, not a list?

* Rules for CoID (one on a start, susp/res/end must match

* Dcls?
    <!ELEMENT q (...)>
    <!ATTLIST q sId  TROJAN_START
                uId  TROJAN_SUSPEND
                rId  TROJAN_RESUME
                eId  TROJAN_END>
    'q' can be a regular element , with none of the TROJANs; or consists of
    an even number of empties, the first with sId, last with eId, rest alt'g uId/rId.

    <!ELEMENT q (...) OLISTABLE>
    This permits 'q' to be closed without closing whatever's still open inside.

    <!ELEMENT q (...) SUSPENDABLE>
    This permits 'q' to be suspended and resumed.


==ID extensions==

* StackID (accumulate down tree, only need to be unique in context)
* CoID (for overlap or other co-indexing)
* How to trigger update of IdIndex?
* Option for IDs with namespace prefixes?
* Shortcut to suffix ID to element type?  <p@para12>  or #^*~


==Serializers==

How best to control line-breaking? So far it has:
    * choice of newline and indent-string
    * breaking for before and after begin and end-tags
    * breaking before text nodes (TODO: Check for adjacent text n, CDATA,...)
        ** especially when adjacent to inlines.
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

==unittesting==

* Push up the coverage
* Add testing specified in Canonical XML 2.0 [https://www.w3.org/TR/xml-c14n2/]
* NS cases
