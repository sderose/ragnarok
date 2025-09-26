==Information on Loki==

In this library, Loki is a subclass of Thor, not his brother.

Loki is not an XML parser. In fact it can parse XML, and for any well-formed
XML document it will produce the same thing an XML parser (such as Thor) would
so long as you don't turn on any Loki options.

However, Loki is, like its namesake, a shape-changer. There are many, many
options you can set, giving special behaviors.

===Usage===

You use Loki just like you'd use Thor, but you'll probably only do that if
you want some options. In that case, you need to turn the options on,
either like this:

    from loki import Loki

    parser = loki.parserCreate()

The simplest, perhaps, is turning on recognition of the usual SGML/HTML
named characters. These are not known by default in XML, and defining them
takes a large number of

==Extensions==

There are a bunch of experimental/additional features, all disabled by default.
You can turn them on by adding a quasi-attribute to the XML declaration
for each desired extension, giving it a value.

For example:
    <?xml version="1.1" encoding="utf-8" curlyQuotes="1"?>

That makes this library handle curly single, curly double, and double angle
quotation marks around literals (such as SYSTEM identifiers, attributes, etc.).
Note that because XML does not allow extra items in the XML declaration,
an XML parser will stop immediately on seeing it. This is by design, so that
a document using XSParser extensions will fail rather than produce incorrect
results if put through a regular XML parser.

By definition, if you turn on any of these extensions XSParser is no longer
an XML parser. It becomes a parser for a slightly different language, which
can truthfully be called "XML-like", but is not XML. However, if you do not
turn any extensions on, XSParser is designed to be a fully-conforming
regular XML parser. If you have data that uses the XSParser extensions and
want to transform it to regular XML, just load it with XSParser into a DOM
implementation of your choice (such as minidom or basedom), and then export
XML in the usual way.

THe definitive list of options is the LokiOptions class in loki.py.

==DTD extensions==

===Size limits===

* "MAXENTITYDEPTH": 4
Do not let entity references nest more than this deeply.

* "MAXSIZE": 1 << 20,
Limit document total length (including expanded entities).

* "repBraces": False
Allow {min, max} to be used for repetition
in content models, not just the usual [+*?].

* "xsdTypes": False
Recognize XSD built-in datatype names as attribute types in ATTLIST declarations.


===Elements===

* "groupDcls": False
    <!ELEMENT (x|y|z)...>

* "oflag": False
    Parse past SGML-style omission flags, as for a DTD originating with SGML:
    <!ELEMENT - O foo...>

* "sgmlWords": False
    Permit CDATA, RCDATA, #CURRENT, etc.

* "markedSectionTypes": False
    Recognize marked section keywords other than CDATA.
(though so far, only CDATA and IGNORE are effective).

* "repBraces": False
    {min, max} for repetition

* "emptyEnd": False
    </>

* "restart": False
    Provide shorthand to close & reopen current element type,
for brevity in analogy to MarkDown tables or SGML OMITTAG + <>:
    <|>

* "simultaneous": False
    Allow simultaneous starting and ending of elements, for example:

* "suspend": False
    <x>...<-x>...<+x>...</x>
This recognizes such tags and returns SUSPEND and RESUME events for them.


===Attributes===

* "xsdTypes": False
    Support XSD builtin types for attributes.

* "specialFloats": False
    With "xsdTypes" active, accept special IEEE values such as Nan, Inf, etc.
for float types. For example:
    <foo x="1.2" y="-Inf">

* "unQuotedAttr": False
This allows omitting quotation marks around an attribute value when
the value is an XML NAME or NUMBER token:
    <p x=foo>

* "curlyQuotes" : False
    Allow additional quote characters around SYSTEM IDs, attributes, etc.

* "booleanAttrs": False
    Allow attributes to be set to "1" or "0" by giving just a sign prefixed
to their name:
    <x +border -foo>

* "bangAttrs": False
    "!=" on first use to set attr default.

* "bangTypes": False
    "!typename=" on first use to set attr default and type. -- NOT YET

* "COID": for milestones, join, etc. -- NOT YET

* "STACKID": for ID-ish values that accumulate through ancestors-- NOT YET


===Entities etc.===

* "multiPath": False
    Multiple SYSTEM IDs:
    <!ENTITY chap1  SYSTEM "path1" "path2"...>


===Case and Unicode===

* "elementFold": False
Case-fold element and attribute names -- NOT YET

* "entityFold": False
Case-fold entity names -- NOT YET

* "keywordFold": False
Case-fold #PCDATA, ANY, etc. -- NOT YET

* "uNormHandler": "NONE" -- NOT YET

* "wsHandler": "XML" -- NOT YET

* "radix": "." -- NOT YET
Decimal point replacement for XSD floats.


===Namespace stuff===

* "nsSep": ":"
    Change the namespace-separator from ":" to something else. -- NOT YET

* "nsUsage": None NOT YET
    Restrict where namesapces can be defined.
Expected to include: justone, global, noredef, regular.


==Document syntax extensions==

* "multiPath": False
Allows multiple SYSTEM IDs in declarations (tried in order):
    <!ENITY foo SYSTEM "c:\\myDocs\\chap1.xml" "/Users/abc/Documents/XML/chap1.xml"?>
