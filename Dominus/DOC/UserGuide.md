==User guide to BaseDom==

BaseDom is a pure Python implementation of DOM 2, plus a variety of
enhancements (at least, the author considers them enhancements!) to make it:

* more Pythonic,
* about 40% faster than minidom
* more convenient
* fairly thorough unittests, typehints, and other modern Python features.

I have aimed to keep all the standard DOM methods and variables intact, so if
you're used to that it should all just work. However, some standard methods
have additional, optional parameters. If you find something that doesn't
work, let me know.

===DOM modernization===

BaseDom implements a lot of more recent DOM additions, as well as many
whatwg additions (see below).

* Exceptions are named as in whatwg, not minidom (although the others
are available as synonyms so you don't have to update prior code).

* EntityReference and Entity nodes are not supported, though the relevant
nodeType values are still defined.

===Pythonicity===

* Node types are now defined as an Enum called NodeType, with the usual
identifiers and integer values. They are also copied into Node, so either
of these works:

    x.nodeType == NodeType.ELEMENT_NODE
    x.nodeType == Node.ELEMENT_NODE

* Reserved words ("#text" etc) are defined in an RWords Enum.

* There are node generators, which let you filter by nodeType.
    x.eachChild()
    x.eachNode()

eachNode() also has an option to include attributes if desired, which are
generated immediately following the even for their ownerElement.

* Although Python does not have a specific way for a subclass to eliminate
a method supported on its superclass, I have tried to make sure inapplicable
classes always raise UnsupportedError, with a useful message.

* Nodes are a subclass of list, with their children as their members.
This is mainly because of Document and Element. This means that you can
walk around using the normal list methods. Most obviously, instead of

    x.childNodes[1].childNodes[0].childNodes[3]

you can just say:

    x[1][0][3]

But you can also do things like this:
    x[-3]
    x[3:-1]

* All of the methods that take a specific child Node as an argument, allow
either that, or an integer position:
    x.insertBefore(newThing, childToPutItBefore)
    x.insertBefore(newThing, 12)
    x.insertBefore(newThing, -1)

Python programmers will already have noticed that the latter usage is just
like Python's list.insert() except for the order of arguments (sorry, I didn't
decide the order either for DOM or for Python).
As you by now might expect, you can also just use that:

    x.insert(12, newThing)

That also means that you don't need x.appendChild(y) -- though it's there. You can
instead use regular append(y), or extend([y, z, w]), or insert(99999, y).


===HTML DOM conveniences===

* Useful interfaces from the HTML DOM are included (though of course called "XML"
instead of "HTML"), such as:
    outerXML getter and setter on all node types
    innerXML getter and setter on Element
    getElementById
    getElementsByTagName
    getELementsByClassName (which knows about tokenization)


===elementtree-like features===

ElementTree has some nice conveniences, particularly supporting CSS selectors.
Such selectors, and several nice ElementTree shorthand methods, are available.
    textContent()
    find()
    findAll()
    set() and get() (meaning for attributes)
    getroot
    tag
    matches()

ElementTree's treatment of text as (two separate) properties on Elements
is different from every other treatment I know of, and results in big
differences such as child-counting, and actually leads to more complicated
algorithms for basic operations like collecting all the text from a subtree,
making a word in mid-paragraph italic (for example), applying any software
the refers to relative positions or order.... Nevertheless, I've also
provide .text and .tail for those used to them. Just don't think that asking
for the n-th child means the same thing anywhere else as it does in ElementTree.


===whatwg features===

Many features inspired by whatwg (not all original to whatwg, of course)
are included:

    querySelector
    querySelectorAll
    matches
    children (element only; you can also get this via node["*"]
    closest()
    classList
    className

Features for dealing with token-list
attributes are there, but include not just @class, but any attributes you like.

* insertAdjacentXML().
The relative positions are defined by a RelPosition Enum.


==General Conveniences==

* There are nodeType predicates, named "is" plus the normal name
(but minus "_NODE" and CamelCase).
Because I find "ProcessingInstruction" annoying, and everybody I know just
calls them PIs", there is also a synonym "isPI".
    x.isElement
    x.isTextNode
    ...

* Python uses the same [] notation for accessing dicts, and conveniently,
XML elements and attributes can never have integer names. So if you like, you can
use [] to access children by nodeName, or attributes by "@" plus their name.
I find this very intuitive, but you can of course still use the standard
DOM methods if you prefer.

    c = x["@class"]  # gets the class attribute (or "")
    c = x["p"]

* A variety of requests than can fail, such as getAttribute(), can take
an additional "default" parameter whose value is returned if the requested
item cannot be found.

* There is getChildIndex(), which returns the position of the node within
its parentNode. It also has boolean options:
** noWSN" to ignore white-space-only text nodes,
** onlyElements: to count only among elements, or
** ofNodeName: to count only items of the same nodeName (this can of course
be an element type name, or a reserved name such as "#text", "#pi", etc.).

* getRChildIndex() does the same things but counting back from the end.
It returns a negative number, such as you can use with Python lists.

* An XmlStrings library isolates knowledge of XML Syntax details such as:

** sets of name and name-start characters (as lists of (start, end) ranges,
as regex [] expressions, as raw character lists, and as predicates)
** methods to escape and unescape strings to fit into
various contexts such as attribute values, text contents, comments, etc.,
with options for decimal or hexadecimal, or use of the usual HTML named characters.
** methods to normalize or strip whitespace. These use the XML rules, but
you can also use other whitespace definitions supported via
the "WSDefs" Enum and its static methods such as isspace, containsspace, normspace,
and spaces.
** methods to construct attributes or entire start tags (including empty tags)
given an element type name and a dict of attributes, with all the right
escaping applied.
** functions to test the various kinds of prefixed, qualified, and local names,
and to do the splitting.

There is separate unittesting for XmlStrings, including full testing of
Unicode support.

* Serialization is separated out a bit more, and toprettyxml() has many
more layout options. The options are packaged into a FormatOptions object,
much like Python csv's "dialect".

* Complete serialization to JSON is provided, and such JSON can be read back
to reconstruct DOM.
This is completely round-trippable. You'll get the same DOM if you export
to JSON using BaseDom, and then load it back. I looked for other JSON/XML
conversions that could do that, and found none (everything I found could only
do some cases, or lost data on the way).

* You can generate a SAX event stream from any subtree. In addition, you
can


===Better schema support===

* Attributes can have associated datatypes. All the XSD built-in types are
allowed, or you can use any Python type. The expected datatype can be
provided by a schema, or by calling AttributeDef directly. This also enables
attribute defaulting.

* A schema loader for DTD is also provided in case your parser ignores DTDs.
It provides small additions to DTD syntax, such as extending the
repetition operators with {}
