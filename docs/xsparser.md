=Description=

A pure Python parser and schema tool for XML. It's mainly meant for parsing
a DTD and creating a simple representation of it (see doctype.py).
But that includes doing nearly everything a regular XML WF parse needs, so I
added those and you can use this as an XML parser as well.

It also supports a bunch of extensions, but all are off by default. Afaict,
it's a fully conforming XML parser if you leave the extensions turned off.

=Usage=

    from xsparser import XSParser
    xsp = XSParser()
    xsp.readDtd("someDTD.dtd")
    xsp.openEntity("someDocument.xml")
    ...


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
The value must be an XML NAME or NUMBER token:
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


* "namespaceSep" : ":"
Colon replacement.


=To Do=

I may add a validator, too.


* Rename
* See if https://pypi.org/project/fastenum/ would be useful.
* Add global option(s) to control extensions.
* Maybe add a compact SDATA-like thing, and/or a switch to enable HTML char ents.
* Option to require something in XML DCL to enable extensions.
* Case-ignoring


=Known bugs and limitations=

* A few constructs (like QLit) do a regex match against the buffer, which will
fail if the target is longer than bufSize.
* A few context don't recognize PE refs where they should. Let me know if you
hit one (in most (all?) cases it should merely require a call to allowPE(),
or setting the allowParams options to skipSpaces().


=Related commands=


=History=

* 2011-03-11 `multiXml` written by Steven J. DeRose.
* 2013-02-25: EntityManager broken out from `multiXML.py`.
* 2015-09-19: Close to real, syntax ok, talks to `multiXML.py`.
* 2020-08-27: New layout.
* 2022-03-11: Lint. Update logging.
* 2024-08-09: Split Manager from Reader. Use for dtdParser.
* 2024-10: Finish parsing infrastructure, DTD and extensions.
Add generally-useful non-terminals (attribute, int, float, tags,...)


=To do=

* Finish.
* Check the specific attributes in the XML DCL
* Add document parsing -- mainly gen ent support


=Rights=

Copyright 2011-03-11 by Steven J. DeRose. This work is licensed under a
Creative Commons Attribution-Share-alike 3.0 unported license.
For further information on this license, see
[https://creativecommons.org/licenses/by-sa/3.0].

For the most recent version, see [http://www.derose.net/steve/utilities]
or [https://github.com/sderose].


=Options
