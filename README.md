Ragnarok is a pure Python XML stack implementation, with Pythonic extensions.

Currently it should be considered pre-release, though you are welcome to try it
out and send feedback, additional unittest cases, fixes, etc. Thanks!

You can read more about it in: DeRose, Steven J. “Ragnarok: An Experimental
XML environment.” Presented at Balisage: The Markup Conference 2025,
Washington, DC, August 4-8, 2025. In Proceedings of Balisage: The
Markup Conference 2025. Balisage Series on Markup Technologies, vol. 30 (2025). https://doi.org/10.4242/BalisageVol30.DeRose01.

The main components are listed below (the names are from Norse mythology, and
make some sense if you think about them):

* Yggdrasil (aka Dominµs): A DOM 3 implementation. Yggdrasil is plug-compatible with
minidom, but is DOM 3 not just 2, and considerably faster. It also has many
methods drawn from the HTML DOM, WhatWH, lxml/etree, XPath, XPointer,
and other sources. Python developers may like the fact that Elements really are
a subclass of Python list and the whole list API works (unlike in minidom, where
using normal Python list methods to modify a Node corrupts the data).

* Thor (Tag Hierarchy Object Retriever, aka xsparser):
Thor is a normal XML parser, with entity-stack and DTD support.
It is in pure Python, with the attendant advantages for Python devs.
It's also recursive descent, so relatively easy to modify.

* Schemera: An implementation of the Document Type object, not really provided
by minidom. A schema can be loaded from XML DTD syntax or created via the API.
Code is also here for loading from XSD, but is not yet finished. The internals
are the same in any case. You can enable
extensions to (for example) allow all the built-in XSD datatypes for attributes,
and they are checked.

* Heimdall: A validator. So far it handles attributes, and of course the parser
catches WF errors and such. Content model validation is unfinished.

* Gleipnir: A DOM-to-XML serializer that you call like minidom's toprettyxml(), but
allows one more parameter: a FormatOptions object (kind of like Python csv "dialects").

* Bifrost: A DOM-to-JSON serializer that is complete (even can do DTDs), and
fairly readable (imho). You can also read the resulting JSON back, getting
the same DOM.

* Runeheim: This factors out rules about tag, attribute, and other names (allowing
you to ignore case, do Unicode normalization, or change the set of name characters),
as well as accommodate varying definitions of "whitespace".

* Loki is a highly extensible and extended XML-like parser. It supports a lot
of added syntax (which you can enable piece by piece as desired). Among my favorites
are accepting curly quotes around attributes (for when editors "prettify" your
XML for you), unquoted attributes, case-ignoring, "<|>" to close then restart
the current element, PIs that can be parsed like
attributes (and can have character entities recognized validated),
and some support for overlapping markup such as olists
(like MECS) and suspend/resume (like TagML). Loki is highly experimental,
so be careful around it as you would with its namesake.

* Sleipnir: This is an unfinished persistent binary DOM, modelled loosely on
one I invented last millenium, except this one is modifiable. I also hope to
include an implementation of "virtual elements" to support overlap in Yggdrasil
fashion.


==More on Yggdrasil / Dominµs==

The DOM implementation is named Yggdrasil, after the great world tree.
But it can be called Dominµs.
The correct spelling uses Greek mu (U+3b), but 'u' (U+75) is acceptable in a pinch.
It may be pronounced as "dominus" (how it looks to the English eye),
and the name is called "DOM in muse"; it actually *is* "DOM in microseconds"
(or so I hope).
Just go with Yggdrasil.
My profiling shows it about 40% faster than minidom, but I expect that will
vary greatly depending on document size and what you're actually doing.

All the normal DOM calls (DOM 3 Core) should work, but many Python developers
may want to use the extensions. Among which:

* Node is a subclass of list: All the normal Python list operations should
work (very unlike minidom). You also don't have to say myNode.childNodes[2] (though
you can) -- just say myNode[2].

* There are synonyms for what WhatWG, ElementTree, and XPath call things,
including generators for all the XPath axes.

* There are node type testers, so you can say
    if myNode.isElement: ...
  instead of
    if myNode.nodeType == Node.ELEMENT_NODE:

* List slicing is supported and extended, and works on the left-hand side too:

** [int] gets you a member of childNodes.
** [int:int] gets you the usual sublist.
** ["name"] gets you a NodeList with all nodes of nodename [name].
nodeNames of course include #TEXT, #COMMENT, and #PI.
"*" means all child elements, but no other nodeTypes.
** ["@name"] gets you that named attribute.
** ["name":int] gets you the n'th child of the nodeName
** ["name":int:int] gets you the given slice among children of the nodeName

* Many DOM methods can be ignored in favor of familiar Python operations:
    appendChild() -> someNode.append(child)
    for x in xx: someNode.append(child)  -> someNode.extend(xx)
    hasChildNodes() -> someNode -- empty list are False in Python)
    removeChild() -> del someNode[5] (or other indices)
    insertBefore(new, old) -> someNode[old:old] = new

* Attributes that are sets of tokens (like HTML class), or important scalar
types like boolean, int, and float, have direct support.

* NamedNodeList is a subclass of OrderedDict, so you can deal with
  attributes like a dict (and can preserve source order if desired).

* The values for nodeType (and various other things) are in an Enum
(though they have the regular DOM values, and methods accept either those or the Enums).

* There are short synonyms for a lot of methods:
    parent = parentNode
    createPI = createProcessingInsruction

* Methods I think useful from XPath, ElementTree, Node.js, etc. are added
(ask or submit a patch if you have a favorite that's not covered):

  outerXML(), innerXML(), and the familiar Python tostring()

  text() gets you *all* the text of the element, including any buried in
descendants. Optionally puts a separator (say, space) between.


