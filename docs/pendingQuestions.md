(this needs to be reorganized and divided up by component)


===============================================================================
==Thor==

* Escaping for qlits in entity dcls
* [gs]getNamedItemNS...
* Finish defusedxml-like features
* Add support for xml.sax.reader?                                       ***
* Let error reporting provide whole tagStack of locations               ***



===============================================================================
==Loki==

* Decide Option switching

    <?xml ... opt1=val1...?>
    <?loki ...?>
    <?loki bull=0x2022 AGr=0x0391... ?>
    <?loki ename=para aname="class:NMTOKENS=normal" ?>

* finish nestable comments                                              ***

* attribute ns: xmlns@path=svg ? <!ATTLIST foo svg:path CDATA IMPLIED> ?

* To-straight-XML driver for xsparser (incl. non-hier mapping)

* build in xinclude (switchable)? meh

* SHORTREF-ish? Say, rules applied via XPath (kind of like XSLT)
Limit to punctuation? MarkDown and/or CSV support this way, or as NDATA?

* Map *just* newlines, as shorthand for poetry?
    <!MAP (...) #LINE TO lb

* Add named LokiOptions profiles, ditch Flag enum draft.

* <!ELEMENT foo/ #PCDATA /regex/>

* UUENCODE Marked sections

* Tabular inheritance of some kind?
    <table predicate="tr/td/@class == [ col1type, col2type,...  ]">



===============================================================================
==Runeheim==

* Check Unicode name abbreviations collision rate with added rules.

* Unicode normalization -- decide how best to integrate with case handling.

* switchable xml 1.0 v 1.1 names                                        ***

* Should entities (either with 'extraDcl' headers or not) be able to
declare/use a different encoding?

* Raku-like char refs
    Drop "letter" and "form" tokens entirely
    "Unified Canadian Aboriginal Syllabics" → UCAS
    "CJK Unified Ideographs" → CJK


===============================================================================
==Schemera==

* Improve storage of minoccurs/maxoccurs

* sync doctype to tree.docinfo.internalDTD?                             ***

* mixin/inclusions -- dcl like incl exceptions?                         ***

* plural XSD types?

* typed attributes: when to cast. Lose or keep original string?
Semantics for isEqualNode with cast vs. uncast values?

* abbreviated element/attribute names? meh

* Autogenerate wrappers from heads?                                     ***

* <!SDATA [ name1 int1, name2 int2... ]>

* Parameter entity references cannot occur within declarations
in the internal DTD subset - they're only allowed between declarations there. (4.4.1?)

ATTLIST dcl for inheritable

What are the "special" attributes: global, apply to text, universal, ...
    * class/type (and style, but that's cheating)
    * lang (and dir for rtl/ltr)
    * id
    * hidden
    * tabindex (and focus keybind)
    * all the events
    * editable, draggable
    * spellcheck, translate
    * (html5 has a ton more)


===============================================================================
==Yggdrasil==

* Update ID index dynamically

* Finish 'mirror-serialization-of-STAGs' ==> saveMarkup

* __contains__ vs. contains

* what about a string() vs. text() like the XPath distinction? we do have
textContent()...
And a good i/f for checking/finding contained text or regex?

* Check textContent per-class vs.
https://developer.mozilla.org/en-US/docs/Web/API/Node/nodeValue     ***

* method to increment/decrement rank ints in various guises:
    h1...
    div1
    div n="1"
    div class="level-1"

    options: padding, startLevel, forceToMonotonic

textContent returns .nodeValue for CDATA, Comment, PI, and Text;
None for Document and Doctype; and
"For other node types (including Element), textContent returns the concatenation of the textContent of every child node, excluding comments and processing instructions." DocumentFragment has nodeValue None but textContent as concatenated. For DocumentType both return None. For Attribute both return the attribute value. NamedNodeMap and NodeList are not subclasses of Node at all).

* Should PlainNode/Node be constructable? at all?

* Make sure splicing multiples in/out doesn't go n**2 on sibling update ***

* Should lack of attrs/ns/etc be empty or None?

* Should removeAttribute___ unlink from ownerDoc/ownerEl?

* Should getitem work for virtual XPath axes? Not just childNodes, but
maybe: Ancestors, PSibs, FSibs, Prec, Foll, Desc, Attrs (and |self)

* With getitem and registerFilterSchema, don't use ":" for the schema sep
because it's also the qname sep. maybe "::" or "?"

* XML allows stuff outside the document element, why shouldn't DOM?     ***

* Should `cloneNode()` copy `userData`?

* What should test for bad names? Maybe only on write.
    has/get/set/removeAttribute
    create Element / Attr / Document / PI target
    ID methods???

* Should the whatwg CharacterData ...data calls return the result?      ***
Range errors? Negatives?

* Sync forEachSaxEvent with lxml.sax.saxify                             ***

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
    getUserData()/setUserData()                                         ***
    The whole Node.DOCUMENT_POSITION_* constants                        ***
    normalizeDocument()                                                 ***
    renameNode()                                                        ***
    adoptNode()                                                         ***
    strict error checking modes
    DOM 3 Load and Save                                                 ***

* Consider adding:

===HTML DOM===
    document.querySelector(): Returns first matching CSS selector
    document.querySelectorAll(): Returns all matching CSS selectors

Navigation Properties
    Element.children: Returns child elements (not text nodes)
    Element.firstElementChild: Returns first child element
    Element.lastElementChild: Returns last child element
    Element.nextElementSibling: Next sibling element
    Element.previousElementSibling: Previous sibling element
    Element.childElementCount: Number of child elements

===whatwg===

Node Interface
    replaceWith(...nodes) - Replaces this node with nodes
    remove() - Removes this node from its parent
    before(...nodes) - Inserts nodes before this node
    after(...nodes) - Inserts nodes after this node

Element Interface
    closest(selectors) - Returns the closest ancestor that matches selectors
    matches(selectors) - Returns whether this element would be selected by selectors
    toggleAttribute(qualifiedName, force) - Toggles presence of an attribute
    replaceChildren(...nodes) - Replaces all children with nodes

Document Interface
    querySelector(selectors) - Returns the first element matching selectors
    querySelectorAll(selectors) - Returns all elements matching selectors
    getElementsByClassName(classNames) - Returns elements with given class names


===============================================================================
==Heimdall==


===============================================================================
==Gleipnir==

* Finish last details for canonical XML FormatOption
* Which Thor or Loki options should also be available in FormatOptions?   ***
* How best to control line-breaking? So far it has:
    * choice of newline and indent-string
    * breaking before text nodes (TODO: Check for adjacent text n, CDATA,...)
        ** especially when adjacent to inlines.
    * text node stripping and whitespace node discarding
    * preserve-space (pre, etc.)                            ***
    * no break between adjacent end-tags (or start-tags)
    * breaking around PI, comment, CDATA, etc.
        or treat [PI/com/ms] as [text/inline/block] ??
    * breaking by what things are *meeting*
    * [ +/- element, attr, text, pi, comment, ms, dcl ] crossed w/ same set.
        But that would be 14**2 = 196 cases....



===============================================================================
==Bifrost==

Document the JSON equivalents better


===============================================================================
===============================================================================
==Bugs==

Consistent Naming
    \b(a|at|att|attribute)(node|name|value|def|ns) -> attr
    \b(e|el|elem|element)(node|name|def|ns) -> elem
    \b(e|en|ent|entity)(node|name|def) -> ent
    pent...
    n|not|notn|notation)(name|def) -> notation

* Interface XPath impl from https://pypi.org/project/elementpath/



===============================================================================
==Non-hierarchy==

* Serialization using extensions?
    ** end/resume daisychaining                                         ***
    ** annotation structure (to and from)                               ***
    ** DAG/graph not just tree
    ** maintain entity structure
    ** should end milestone require coid if it's closing most recent?

* Option to write Loki options into the XML dcl?

* Integrate OLIST, TagML, Clix into Dominµs.                            ***

* Support full-fledged XPointer ranges.                                 ***

* Simultaneity and co-location
    * If these are truly co-located, then should <|> be, too?           ***
    * Is <a/b/c> also co-location? Pretty sure no.
    * Can you combine olist and multiTag?
    * Can you mix starts and ends in multiTag?

* <|li> closes through li and then opens all the same stuff down

* Could a transclusion node be introduced, to allow DAGs or even graphs?
    Traversal would have to prevent circularities; affected methods?
    childInex works if you can only transclude one subtree per
    nodeSteps, parentNode, depth
    searches
    ?subclass of characterData so it doesn't "have" children

* turn olist or suspend/resume into an annotation, join, etc.?

* Should there be a way to assert that a specific element's children do
not have a conceptual order? So they get stuck in a set maybe, not a list?
    <!ELEMENT bibitem #BAG (au+, ti, da, vol, pp. pubname, publoc, uri*, ...)>

* Rules for CoID (one on a start, susp/res/end must match               ***
Milestone variants to consider:
    <q-start key="foo"/>...<q-end key="foo">
    <q type="start" key="foo"/>...<q type="end" key="foo">
    <milestone gi="q" type="start" key="foo"/>...<milestone gi="q" type="end" key="foo">
    <milestone-start gi="q" key="foo"/>...<milestone-end gi="q" key="foo">
    <q sId="foo"/>...<q eId="foo"/>
    <q id="foo1" next="foo2"/>... <q this="foo2" prev="foo1"/>
    <q id="q1" next="q2">...</q>...<q id="q2" prev="q1">...</q>

* Virtual scope for intervals between (e.g.) page boundaries:
    <pb n="12">...<pb n=13">

    ** Incl. some way to check for contiguous/monotonic series?

* Dcls?                                                                 ***
    <!ELEMENT q (...)>
    <!ATTLIST q sId  STARTID        #IMPLIED
                uId  SUSPENDID      #IMPLIED
                rId  RESUMEID       #IMPLIED
                eId  ENDID          #IMPLIED
                pb   BOUNDARYID     #IMPLIED
                mid  COID           IMPLIED
    >

    Limitation:
        ** no reordering
    Constraints:
        ** If any is set, only one, and element must be empty.
        ** order is:  sId (uId rId)* eId
        ** all same type (or of co-declared types?)
        ** no other elements can use that id (maybe via IDREF?)
    Dominµs representation:
        ** index from ID to ordered list of empty nodes
        ** index from nodes to the ID list and place in list

    <!ELEMENT q (...) OLISTABLE>                            ***
    This permits 'q' to be closed without closing whatever's still open inside.

    <!ELEMENT q (...) SUSPENDABLE>                          ***
    This permits 'q' to be suspended and resumed.


===============================================================================
==ID extensions==

* How to trigger update of IdIndex?                         ***
* Option for IDs with namespace prefixes?                   ***
* Suffix @ID to element type?  para@p12  or # ^ * ~ ???
  * "#" to be like CSS?  <p#myId> or <p #myId> (might as well permit both)
  * (maybe ID is "the nameless attribute")
  * IDREF? class? alt? lang?

* Numeric IDs, non-names,...

*  Need attr types (cf Claude discussion):
    "NAMESPACEID"  # NS prefixes on ID values          TODO
    "STACKID"      # value is '/'.join(anc:@id)        TODO
    "TYPEID"       # value unique for element type     TODO
    "XPATHID"      # value from evaluating an XPath    TODO
    "COID"         # co-index start and end milestones TODO
    "STARTID"      # Only on starts (like Trojan sId)  TODO
    "SUSPENDID"    # Only on suspends                  TODO
    "RESUMEID"     # Only on resumes                   TODO
    "ENDID"        # Only on ends (like Trojan eId)    TODO
  Need element types:
    Supendable
    Olistable

* Validate these for:
    ** Milestones are in fact empty
    ** Start (Suspend, Resume)* End
    ** Value unique to a given chains
    ** Uniqueness after all the wonky processing
    ** Safety of join char (shown here as "/")
    ** What to do with STACKID if not on all levels

* Issues/questions
    ** Limit STACKID to set of element types?
    ** Limit what types the virtual elements can cross (or vice/versa)
    ** Where does XPATHID set the XPath expr? In the ATTLIST?
    ** Option for joins of synch or non-sync? ordered or not?
    ** Space/case normalization
    ** Is type to enforce uniqueness over just a QName?
    ** Anything different/special for IDs on end-tags? Prob. not.
    ** COID with re-usable values (say, you just use [a-z])?




===============================================================================
==Reify text?==

* allow something like <#lang>.... or maybe <#[inlineletter]@lang>
    ** this is a predefined CDATA element
    ** only <#/ ends it, so no escaping
    ** its name is treated as xml:lang
        *** but, speifically permits non-human languages, incl. programming
        *** might allow embedded notations, dcl Python etc as NOTATIONS
    ** This is allowed style name or properties as attributes
        *** But limited to font-level / inline control:
            font-x      -- i/b/tt/strike/u/rom   family
            f-size      -- small/big (where to put actual size?)
            v-align     -- sup/sub
            caps        -- sc
            color       -- (where to put value?)
        *** q? maybe with a "enclose" prop of some kind?
        *** not br/hr/a/abbr/acronym/
        *** or could just say in this, you're in CSS land:
            <t style="" lang="" id=""> -- and that's it


===============================================================================
==Table issues==

* Schemera capability to insist that all rows in a table are the same, a la
RDB, CSV, etc. -- say, "all children of a given instance of a table must
have the same sequence (set?) of child-types (or @class, or @colnum, or just
the number (and datatype?).

* But you also want be able to make different tables use the same set of
cols.

    lastCheckVal = None
    for rowNum, row in enumerate(thisTable):
        checkVal = []  # or ()
        for colNum, cell in enumerate(row):
            checkVal.append(myXPath[cell])
        if lastCheckVal and checkVal != lastCheckVal: raise ValidationError
        lastCheckVal = checkVal

Sets and unordered
    <{bibentry}>...</{bibentry>
    See also Note "Set/bag elements"


===============================================================================
==Uncategorized==


What would happen if text was just an element?
    * Say, nodeType ELEMENT, nodeName #TEXT (or just "#), nodeValue the text.
    * Why does text have to be LEAVES? It contains inlines!!!
    * Text could have attributes, too: lang, id
    * This:
        * eliminates the text/element distinction for the API
        * makes correct traveral trivial
        * lets text know stuff (lang!)
        * avoids having to create <foreign> and <q>
    *-- Where do you put the attributes?
        <#text lang="he">  (is "/>" optional/redundant?)
        <$>...</$>  for <#text>

* switch suspend/resume and milestones to?
    <<p>>... <-p>... <+p>... <</p>>  ?
    The doubling suggests "super-element"
    This avoids having to re-interpret a regular start-tag when you hit <-p>
    These are shorthand for <#overlap-start>, etc.
    Maybe allow:
        U+000ab  «  LEFT-POINTING DOUBLE ANGLE QUOTATION MARK
        U+000bb  »  RIGHT-POINTING DOUBLE ANGLE QUOTATION MARK
        U+027ea  ⟪  MATHEMATICAL LEFT DOUBLE ANGLE BRACKET
        U+027eb  ⟫  MATHEMATICAL RIGHT DOUBLE ANGLE BRACKET
        U+0300a  《  LEFT DOUBLE ANGLE BRACKET
        U+0300b  》  RIGHT DOUBLE ANGLE BRACKET


* Rig NDATA to pass selected things through ixml.

* XSD export

* Integrate XSD via DOCTYPE NDATA

* virtualize(e1, e2)
    for two empty elements, create a virtual element for that range
    similar for case where e1 is on the stack during dombuild, and e2 just
        made us realize it's virtual, so we have to move things
    probably keep the milestones?
    unvirtualize(velement)
        frags? susp/resume? just async?

operations on virtual elements:
    iterate ranges
    iterate milestones
    consolidate tangent parts (say, for fragged things)
    order comparisons
    containment tests
    consolidate/split things like b/i, i/b, bi

*should case-folded names be returned normalized, or is this just going to be
a validation thing?

* Finish full charset/encoding support (esp. MacRoman and CP1252)
