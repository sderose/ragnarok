A pure Python DOM implementation, with Pythonic API extensions.
All the normal DOM calls should work, but Python developers may want to
use the extensions. Among which:

    * Node is a subclass of list:
        * [int] gets you a member of childNodes
        * [int:int] gets you the usual sublist
        * ["name"] gets you a sublist with all nodes of nodename [name].
            This includes #TEXT, #COMMENT, and #PI.
            "*" means all elements, but no other nodeTypes.
        * ["@name"] gets you that named attribute (attributes are different
          from children, and are not part of childNodes). THose who prefer, can
          still use set/getAttribute(), or the shorter attrs[].
        * ["name":int] gets you the int'th child of the nodeName
        * ["name":int:int] gets you the given slice among children of the nodeName

        * Many DOM methods can be ignored in favor of familiar Python operations:
            appendChild() -> someNode.append(child)
            for x in xx: someNode.append(child)  -> someNode.extend(xx)
            hasChildNodes() -> someNode -- empty list are False in Python)
            removeChild() -> del someNode[5] (or other indices)
            insertBefore(new, old) -> someNode[old:old] = new
    * Because every element has a name not starting with "#", and each non-element
    node has a "#"-initial name equivalent to its nodeType, nodeType is redundant.
    The exception is attributes, which in DOM (reasonably) use nodeName for their
    name. But imho, attributes are hot ice and wondrous strange snow:

        * they are the only named things that aren't elements
        * ther are the only named things that can't have children
        * they have special semantics such as tokenization, ID/IDREF (though
        DOM doesn't help much with those)
        * they have a parent, but are not children of that parent
        * they are unordered and name-unique
        * they can (at least with a schema) have default values
        * they necessitate several classes like NamedNodeList, that don't
        seem to buy much over ubiquitous built-in types such as dict.
        * Semantically, they commonly apply to an entire element, rather than
        only to their own contents.

    Thus, here attributes just form a dict associated with each element. The usual
    DOM API is supported as far as I can easily do so, but I really never use it
    for attributes.

    * Attributes that are set of tokens (like HTML class), or important scalar
    types like boolean, int, and float, have direct support here (such as
    the usual set operations)

    * NamedNodeList is a subclass of OrderedDict, so you can just deal with
      attributes like a dict (and can preserve source order if desired).

    * The values for nodeType are an Enum (though they have the regular DOM
      values, and methods accept either the ints or the Enum)

    * There are short synonyms for a lot of methods:
        parent = parentNode
        createPI = createProcessingInsruction
        ownerDocument = oDoc

    * At option, the minidom Exceptions can be simply synonyms for built-in
      Python ones.


    * Methods I think useful from XPath, ElementTree, Node.js, etc. are added
      (ask or submit a patch if you have a favorite that's not covered)
      outerXML(), and the familiar Python tostring()
      innerXML()
      text() gets you *all* the text of the element, including any buried in
          descendants. Optionally puts a separate (say, space) between.

    * A separate XMLStrings package provides useful basic tasks such as
      escaping and unescaping string to fit in XML content, attributes, etc.

    * A separate XMLRegexes package provides regexes for many XML constructs,
    such as quoted literals, attributes, tags, and so on; and lists of all
    the Unicode characters in various categories such as NAME and NMSTART.

    * You can just construct instances of various nodeTypes, such as elements),
    rather than going through Document.createElement. Their ownerDocument is
    of course None, but they can be inserted by appendChild() etc (or just
    Python append()), and ownerDocument is set automatically then.

    * There are some shorthand element constructor options, such as a List
    of children to insert. That list can also include text strings, which
    will automatically construct text nodes.

    * I would probably make text nodes just a subclass of string, but string
    is hard to subclass, and they'd still need to inherit from Node, too, so
    I haven't done this (yet).

    * I've created an independent unittest suite.

    * One-step export/import of a round-trippable JSON form. This does NOT mean
    you can just put any old JSON in; there is a deterministic mapping, where
    each node is an array of [ {attrs}, (childNode|string)* ]. So [0] is always a dict
    of the attrs, and that dict always has a "#" item for the nodeName (which
    also covers #PI, etc. as above). At option, you can have text nodes as
    either [ { "#":"#TEXT" }, "str" ] instead; import accepts either.

    * All the XPath axes are available as virtual lists of the same kind (the
    equivalent of minidom NodeLists), and can be indexed in the same ways.
    But they have shorter names available, too. To get the next following
    sibling *element* (ignoring comments, PIs, text nodes, etc):
        someNode.rsib("*":1)

    * The indexes can also count backwards in the usual Python style:
        someNode.rsib("*":-3)

The JSON transformation puts childNodes[0] in position [1]. This is not ideal.
However, since everything else is a scaler of list, and [0] is a dict, maybe
it's not so bad? And it only effects you if you load the JSON via a mechanism
that doesn't pull them out for you.

Classes:
    DOMImplementation

    Node
      Element
      Leaf
        Attr
        CDATASection
        Comment
        Document
        DocumentFragment
        DocumentType
        Entity                 (not really used)
        Notation
        ProcessingInstruction (with synonym "PI")
        Text

    NodeList
    StringTypes          <class 'tuple'>
    TypeInfo

    AttributeList        (OrderedDict)
    CharacterData        (str)
    Childless            (Leaf)
    DOMImplementationLS  ?
    DocumentLS           ?
    ElementInfo          ?
    EmptyNodeList        ?
    Identified           ?
    NamedNodeMap         (OrderedDict)

Some support for schemas -- mainly intended to allow catching undeclared items,
and to associate datatypes and default values with attributes. Classes:

    Dcl:
        AttrTypes(Enum):
        ElementDcl(Dcl):
        AttributeDcl(Dcl):
        BaseEntityDcl(Dcl):
            EntityDcl(BaseEntityDcl):
            PEntityDcl(BaseEntityDcl):
            NotationDcl(BaseEntityDcl):


Possibles:
    Factor so all construction can be overridden by subclasses!
    ??? what happens if you combine @ with indices?  node["@p":3:01]?
    JSON-like i/o but in Python syntax
    Attribute Datatyping (how best to set?)
        <?pydom:defaults table@border:bool=True...?>
    == for isEqualNode
    node Order comparisons

Meh:
    WF and validity checkers that work on the JSON (well, at first they'd
        transform).
    A disk-resident variant.
    hasAttribute(x) -> "@"+x in someNode ?  nah, just x in someNode.attrs
    [[x]] for descendent vs. child
    [".val"] for class attribute selection (but then # conflicts) -- nah


Reference:

DeRose, Steven J. “JSOX: A Justly Simple Objectization for XML: Or: How to do better with Python and XML.” Presented at Balisage: The Markup Conference 2014, Washington, DC, August 5 - 8, 2014. In Proceedings of Balisage: The Markup Conference 2014. Balisage Series on Markup Technologies, vol. 13 (2014). https://doi.org/10.4242/BalisageVol13.DeRose02.
