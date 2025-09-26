##README for Ragnarok##

Ragnarok is a pure Python XML stack implementation, with Pythonic extensions.

Currently it should be considered pre-release, though you are welcome to try it
out and send feedback, additional unittest cases, fixes, etc. Thanks!

You can read more about it in: DeRose, Steven J. “Ragnarok: An Experimental
XML environment.” Presented at Balisage: The Markup Conference 2025,
Washington, DC, August 4-8, 2025. In Proceedings of Balisage: The
Markup Conference 2025. Balisage Series on Markup Technologies, vol. 30 (2025). [https://doi.org/10.4242/BalisageVol30.DeRose01].

###Components###

The main components are listed below. The names are mainly from Norse mythology, and
make some sense if you think about them:

* **Thor** (Text Hierarchy Object Reader, nee xsparser):
Thor is a normal XML parser, with entity-stack and DTD support.
It is in pure Python, with the attendant advantages for Python devs.
The interface is like expat (the parser typically under minidom).
It uses recursive descent, so is relatively easy to modify.

* **Yggdrasil** (aka Dominµs): A DOM 3 implementation. Yggdrasil is plug-compatible with
minidom, but is DOM 3 not just 2, and considerably faster. It also has many
methods drawn from the HTML DOM, WhatWH, lxml/etree, XPath, XPointer,
and other sources. Python developers may like the fact that Elements really are
a subclass of Python list and the whole list API works (unlike minidom, where
using normal Python list methods to modify childNodes corrupts the data).

* **Schemera**: An implementation of the Document Type object, not really provided
by minidom. A schema can be loaded from XML DTD syntax or created via the API.
Code is also here for loading from XSD, but is not yet finished. The internal
data is the same in either case. You can also enable
extensions to (for example) allow all the built-in XSD datatypes for DTD ATTLIST
declarations, and they are checked.

* **Heimdall**: A validator. So far it handles attributes, and of course the parser
catches WF errors and such. Content model validation is unfinished.

* **Gleipnir**: A DOM-to-XML serializer that you call like minidom's `toprettyxml()`, but
allows one more parameter: a FormatOptions object (kind of like Python csv "dialects").

* **Bifrost**: A DOM-to-JSON serializer that is complete (even can do DTDs), and
fairly readable (imho). You can also read the resulting JSON back, getting
the same DOM.

* **Runeheim**: This factors out rules about tag, attribute, and other names, allowing
you to ignore case, do Unicode normalization, or change the set of name characters,
as well as accommodate varying definitions of "whitespace".

* **Loki** is a highly extensible and extended XML-like parser. It supports a lot
of added syntax (which you can enable piece by piece as desired). Among my favorites
are accepting curly quotes around attributes (for when editors "prettify" your
XML for you), unquoted attributes, case-ignoring, "<|>" to close then restart
the current element, PIs that can be parsed and checked like
attributes (and can have character references recognized),
and some support for overlapping markup such as olists
(like MECS) and suspend/resume (like TagML). There are also conveniences like
turning on all the HTML4 or 5 character entities, and/or Raku-like and abbreviated
Unicode character names, with the flick of an option.
Loki is highly experimental,
so be careful around it as you would be around its namesake.

* **Sleipnir**: This is an unfinished persistent binary DOM, modelled loosely on
one I invented last millenium, except this one is modifiable. I also hope to
include an implementation of "virtual elements" to support overlap in Yggdrasil
fashion.


##More detail##


###Thor###

Thor is a regular XML parser. The API is like that of expat (which is the one
typically used by minidom). The unittests including running Yggdrail on top
of regular expat, as well as minidom on top of Thor; so they should be highly
compatible. One difference is that Thhor does not break text into separate
SAX events at very entity reference and newline (but ythere's an option to turn
that back on if you want to).

The SAX events are listed in saxplayer.py,
and are like expat (Python's xml.parsers.expat):

Main documentation: See docs/thor.md.

Simple example: See examples/ThorDriver.py.



###Yggdrasil / Dominµs###

The DOM implementation is named Yggdrasil, after the great world tree.
But it can also be called Dominµs.
The correct spelling uses Greek mu (U+3b), but 'u' (U+75) is acceptable in a pinch.
It may be pronounced as "dominus" (how it looks to the English eye),
and the name is called "DOM in muse"; it actually *is* "DOM in microseconds"
(or so I hope).
Just go with Yggdrasil.
My profiling shows it about 40% faster than minidom, but I expect that will
vary greatly depending on document size and what you're actually doing.

An simple example loading Yggdrasil via expat or Thor and then doing some simple
processing, is in examples/YggdrasilDriver.py.

All the normal DOM calls (DOM 3 Core) should work, but many Python developers
may want to use the extensions. Among which:

* Node is a subclass of list: All the normal Python list operations should
work (very unlike minidom). You also don't have to say myNode.childNodes[2] (though
you can) -- just say myNode[2].

* There are synonyms for what WhatWG, ElementTree, and XPath call things,
including generators for all the XPath axes.

* There are node type testers, so you can say

```
    if myNode.isElement: ...
```

instead of

```
if myNode.nodeType == Node.ELEMENT_NODE:
```

* List slicing is supported and extended, and basic slicing
works on the left-hand side too:

    * [int] gets you a member of childNodes.

    * [int:int] gets you the usual sublist.

    * ["name"] gets you a NodeList with all nodes of nodename [name].
      nodeNames of course include #TEXT, #COMMENT, and #PI.
      "*" means all child elements, but no other nodeTypes.

    * ["@name"] gets you that named attribute.

    * ["name":int] gets you the n'th child of the nodeName

    * ["name":int:int] gets you the given slice among children of the nodeName

* Many DOM methods can be ignored in favor of familiar Python operations:

    appendChild() -> someNode.append(child)
    for x in xx: someNode.append(child)  -> someNode.extend(xx)
    hasChildNodes() -> someNode -- empty list are False in Python)
    removeChild() -> del someNode[5] (or other indices)
    insertBefore(new, old) -> someNode[old:old] = new

* Attributes that are sets of tokens (like HTML class) have direct support.

* NamedNodeList is a subclass of OrderedDict, so you can deal with
  attributes like a dict (and can preserve source order if desired).

* The values for nodeType (and various other things) are in an Enum
(though they have the regular DOM values, and methods accept either those or the Enums).

* There are short synonyms for methods:

    parent = parentNode
    createPI = createProcessingInsruction

* Methods I think useful from XPath, ElementTree, Node.js, etc. are added
(ask or submit a patch if you have a favorite that's not covered):

  outerXML(), innerXML(), insertAdjacentXML(), and the familiar Python tostring().

  text() gets you *all* the text of the element, including any buried in
descendants. Optionally puts a separator (say, space) between.


###Runeheim###

You can switch between upper, lower, full Unicode, and no case-folding.
You can switch separately for element names, attributes names, entity
names, keywords (like in a DTD), and ID values. You can also apply the
4 main Unicode normalization forms if desired, and reconfigure what counts
as whitespace.

There is also infrastructure for changing the set of allowed name and name-start
characters, but it's not fully interfaced yet.

Runeheim and Loki also know the full list of HTML 4 and 5 named special
characters, which you can enable with a single switch. In addition, actual
Unicode character names can be used (substituting underscore, hyphen, or dot for
any spaces). All tokens except the last one in such names can be abbreviated
down as far as 4 characters (there are a very few additional rules for name parts
that are common and long, like "CJK UNIFIED IDEOGRAPH" to "CJK".

Oh, Loki can also be set up to accept Python-like backslash codes, in addition
to or instead of XML's entity-reference syntax.

###Loki minimization###

Loki (but not Thor) has options to enable some abbreviations in tags.
Most of this is like what was once called "shorttag", but not "omittag", and
none of it breaks the key XML principle that you must be able to parse
correctly without knowing the particular schema.

By setting certain options:

* Quotes around attribute values can be omitted if the value consists entirely
of XML NAME characters (this is usually true of IDs, class attributes, numbers,
etc.

* Curly quotes can be used around attribute values.

* Attributes can be set to "0" via just -name, or "1" via +name. This is not quite the
same as the HTML convention (itself a legacy of SGML) that enumerated
values can be given, such as border meaning border="border". Schemera of course
also lets you declare attributes as type boolean, per the XSD definition.

* You can omit end-tags at EOF (this is mainly useful for append-only
log files, and for cases similar to JSON-:L.

* You can omit end-tags immediately before another end-tag; but this may go away.


###Loki overlap support###

Loki can be configured to accept end-tags for elements that are open but are
not the innermost element (if you do this, you definitely cannot also omit
end-tags immediately before other eend-tags!). This is very like the "olist"
discipline in MECS.

Other options allow suspend/resume markup, similar to TagML:

    <q>...<-q>...<+q>...</q>

In both these cases, you may have to co-index tags together (for example, there could be multiple interleaved but separate discontinuous quotations). For that reason, you can
also enable ID-like attributes in suspend, resume, and end-tags.

Schemera provides additional types to declare attributes as being of
this co-indexing kind. They differ, for example, because they go on multiple milestones
that represent the (overlapping) element -- that's not the same as IDREFs that
point from elsewhere to the element. However, these types are still
pretty experimental.

Although Loki can parse such constructs and return a series of SAX events as
appropriate, Yggdrasil cannot store them other than as milestones. I am working
toward a "virtual element" package that will look much like Yggdrasil, but
integrate such (quasi-) elements from a separate store. This is emphatically
not finished.

###Controlling Loki options###

The full list of options is declared in loki.py. Almost all are boolean, and
default to 0 (off). You turn them on either via the API, or by setting them
with (quasi-) attribute syntax inside the XML declaration (analogous to
version, encoding, and standalone).

