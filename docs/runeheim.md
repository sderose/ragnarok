==Information on Runeheim==

This small package provides character set definitions, testers, patterns,
and normalizers for XML constructs, and test for various kinds of XML tokens.

Many of the methods are static.

Note: Methods to escape strings for use in various context (content,
attributes, comments, etc) are not here, but in Gleipnir (nee toprettyxml).
*un*escapers, however, are here.


==Synopsis==

Note: Class 'FlexibleEnum' is defined in ragnaroktypes.py. The main difference
from regular Python Enum is that it recognizes the string value of an enum
member, as well as the name as identifier.

===class XmlStrings===

    allNameStartChars() -> str
    allNameCharAddls() -> str
    allNameChars() -> str
    isXmlChars(s:str) -> bool
    isXmlName(s:str) -> bool
    isXmlQName(s:str) -> bool
    isXmlQQName(s:str) -> bool
    isXmlPName(s:str) -> bool
    isXmlNMTOKEN(s:str) -> bool
    isXmlNumber(s:str) -> bool
    dropNonXmlChars(s:str) -> str
    unescapeXml(s:str) -> str
    unescapeXmlFunction(mat:Match) -> str
    normalizeSpace(s:str, allUnicode:bool=False) -> str
    replaceSpace(s:str, allUnicode:bool=False) -> str
    stripSpace(s:str, allUnicode:bool=False) -> str
    getPrefixPart(s:str) -> str
    getLocalPart(s:str) -> str

===class NameTest(FlexibleEnum)===

This provides alternate definitions for the XML NAME construct (element,
attribute, entity, and other names). The values (of which only XML and PYTHON
are actually implemented so far), are:

    NAME_XML
    NAME_XML10
    NAME_XML11
    NAME_PYTHON
    NAME_HTML
    NAME_WHATWG
    NAME_ASCII

This class also has a method, which tests a string for whether it is a
valid NAME given the chosen definition/;

    isName(self, s:str) -> bool


===class UNormHandler(FlexibleEnum)===

Determines whether and how Unicode normalization should be applied.
The values are as listed here (see Unicode itself for the definitions):

    NONE = None
    NFKC = "NFKC"
    NFKD = "NFKD"
    NFC = "NFC"
    NFD = "NFD"

    normalize(self, s:str) -> str: Apply the normalization.

    strnormcmp(self, s1:str, s2:str) -> int: Apply the normalization to
both arguments, then compare the results.


===class CaseHandler(FlexibleEnum)===

Perform the chosen type of case-folding:

    NONE = None
    FOLD = "FOLD"
    LOWER = "LOWER"
    UPPER = "UPPER"

    normalize(self, s: str) -> str
    strcasecmp(self, s1:str, s2:str) -> int


===class WSHandler(FlexibleEnum)===

Manage white space under the chosen set of rules, from among:

    XML
    WHATWG
    CPP
    UNICODE_ALL
    JAVASCRIPT
    PY_ISSPACE

    spaces(self) -> str
    isSpace(self, s:str) -> bool
    hasSpace(self, s:str) -> bool
    lstrip(self, s:str) -> str
    rstrip(self, s:str) -> str
    strip(self, s:str) -> str
    replace(self, s:str) -> str
    normalize(self, s:str) -> str

The above, invoked on an instance of the Enum, apply the right rules for
that instance. The following are static methods, and apply the usual XML rules:

    xstripSpace(s:str) -> str
    xreplaceSpace(s:str) -> str
    xcollapseSpace(s:str) -> str


===class Normalizer===

This is a convenience class that bundles a CaseHandler, a UNormHandler,
and WSHandler. 'tgtChar' specifies what particular character whitespace
characters normalize to (hard for me to imagine setting it to something
other than ' ' (U+20), but it's there).

    __init__(self, unorm:str="NONE", case:str="NONE", wsDef:str="XML", tgtChar:str=" ")
    normalize(self, s:str) -> str
    strnormcmp(self, s1:str, s2:str) -> int


==Runeheim Methods==

Runeheim proper has quite a few methods, nearly all static.


* '''unescapeXml'''(string)

Change XML numeric character references, as
well as references to the 5 pre-defined XML named entities and the usual
HTML 4 ones, into the corresponding literal characters.

* '''normalizeSpace'''(self, s, allUnicode=False)

Do the usual XML white-space normalization on the string ''s''.
If ''allUnicode'' is set, include not just the narrow set of `[ \t\r\n]`,
but all Unicode whitespace (which, in Python regexes with re.UNICODE,
does not include ZERO WIDTH SPACE U+200b).

* '''stripSpace'''(self, s, allUnicode=False)

Like `normalizeSpace`, but only remove leading and trailing whitespace.
Internal whitespace is left unchanged.


==Useful sets of characters==

How these are represented is indicated by a suffix on the name:

* '''_list''' is just a list of characters as a string.
For example,
    xmlSpaces_list = " \\n\\r\\t".

* '''_rangelist''' is a list of (start, end) codepoint pairs.
For example,
    _nameStartChar_rangelist = [ (0x00, 0x1F), (0x80, 0x9F), ... ].

* '''_rangespec''' is generally derived from a _rangelist, using
''rangelist2rangespec()''. It is ready to put inside regex [], but does not
include the brackets (to make it trivial to combine specs when needed).
For example,
    _nameStartChar_rangespec = "\\u005f\\u0041-\\u005A..."

* '''_re''' is an entire usable regex (compiled or not). Perhaps just [...], or
perhaps fancier. For example,
    NMTOKEN_re = r"[%s]+" % (_nameChar_rangespec)

Thus:

* xmlSpace_list: A string containing only the XML space characters,
namely SPACE, TAB, LF, and CR. No other Unicode space chars (see the
''WsDefs'' class for fancier space-handling options).

* _nameStartChar_rangelist: A list of the ranges of characters that are
XML name start characters. This is straight from the XML REC (see the
''NameTest'' class for fancier name definition options).

* _nameCharAddl_rangelist: Like _nameStartChar_rangelist, but including only
the *additional* ranges allowed as XML name characters.

* _nameStartChar_rangespec: A single string expressing the same ranges
as _nameStartChar_rangelist, in the form to go inside [] in a regex.

In addition, `allNameStartChars()` and `allNameCharAddls()`
return strings containing all of the characters in the given category (this is
much less compact than the regex-style range notation).


==Useful regexes==

* xmlSpaces_re: A regex that matches one or more XML space characters.

* xmlSpaceOnly_re: A regex that matches a string if it
consists entirely of XML space characters (this can also be approximated by
testing is str.strip() is empty/falsish).



=Known bugs and limitations=

QName does not allow for "##any", "#text", or other reserved names.


=History=

Originally a part of DomExtensions:

* Written 2010-04-01~23 by Steven J. DeRose (originally in Perl).
* ...
* 2012-01-10 sjd: Start port to Python.
* 2016-01-05: Fix previous/next. Add monkey-patching.
* 2018-02-07: Sync with new AJICSS Javascript API. Add/fix various.
* 2018-04-11: Support unescaping HTML named special character entities.
* 2019-12-13ff: Clean up inline doc. Emitter class. collectAllXml2. lint.
Pull in other extensions implemented in my BaseDom.py (nee RealDOM.py).
Generate SAX.
* 2020-05-22: Add a few items from BS4, and a few new features.
* 2021-01-02: Add NodeTypes class, improve XPointer support.
* 2021-03-17: Add getContentType().
* 2021-07-08: Add some methods omitted from patchDom(). Add checking for such.
Type-hinting. Proof and sort patchDom list vs. reality.
* 2021-07-20: Fix eachNode for attribute nodes. Add removeNodesByNodeType().
* 2022-01-27: Fix various annoying bugs with NodeTypes Enum. Remember that the Document
element is really an element. Improve handling for bool and for multi-token values
in getAttributeAs(). Turn off default of appending id comment in getEndTag().
* 2023-02-06: Clean up parent/sibling insert/wrap methods.
* 2023-04-28; Move table stuff to domtabletools.py. Implement comparison operators.
* 2023-07-21: Fix getFQGI(), getContentType(). Add getTextLen().

* 2024-08: Separate package extracted
* 2024-08-14: Clean up extracted XmlStrings package, add and pass unit tests.
Fix bugs with name-start character list.
* 2024-09: Tighter integration with other packages. Normalize name casing.
Add actual types for NMTOKEN etc. via NewType.


=Rights=

Copyright 2010, 2020, Steven J. DeRose. This work is licensed under a Creative
Commons Attribution-Share Alike 3.0 Unported License. For further information on
this license, see http://creativecommons.org/licenses/by-sa/3.0/.

For the most recent version, see [http://www.derose.net/steve/utilities] or
[http://github/com/sderose].

"""
