#!/usr/bin/env python3
#
# xmlstrings: A bunch of (hopefully) useful additions to the DOM API.
# 2010-01-10: DOMExtensions written by Steven J. DeRose.
# 2024-08: Separated from rest of DOMExtensions.
#
import re
from typing import Union, Match, Dict, List

from html.entities import codepoint2name, name2codepoint

__metadata__ = {
    "title"        : "xmlstrings",
    "description"  : "Escapers and isa() testers for XML constructs.",
    "rightsHolder" : "Steven J. DeRose",
    "creator"      : "http://viaf.org/viaf/50334488",
    "type"         : "http://purl.org/dc/dcmitype/Software",
    "language"     : "Python 3.11",
    "created"      : "2010-01-10; separate module since 2024-08",
    "modified"     : "2024-08-14",
    "publisher"    : "http://github.com/sderose",
    "license"      : "https://creativecommons.org/licenses/by-sa/3.0/"
}
__version__ = __metadata__['modified']


descr = """
=Description=

This small package provides escapers specific to each relevant XML
construct, and test for various kinds of XML tokens.

All the methods are static, so you don't have to instantiate the XmlStrings
class.


==Methods==

* '''escapeAttribute'''(string, quoteChar='"')

Escape the string as needed for it to
fit in an attribute value. The crucial thing is to escape the 'quoteChar' to
be used around the value. Most people seem to use double quote, but single
quote is allowed in XML. You can specify which you plan to use, and that
one will be escaped in 'string'. 'string' should not already be quoted.

* '''escapeText'''(string)

Escape the string as needed for it to
fit in XML text content ("&", "<", and "]]>").
Some software escapes all ">", but that is not required. This method only
escape ">" when it follows "]]".

* '''escapeCDATA'''(string)

Escape the string as needed for it to
fit in a CDATA marked section (only ']]>' is not allowed).
XML does not specify a way to escape this. The result produced here is "]]&gt;".

* '''escapeComment'''(string)

Escape the string as needed for it to
fit in a comment, where '--' is not allowed.
XML does not specify a way to escape this. The result produced here is "-&#x2d;".

* '''escapePI'''(string)

Escape the string as needed for it to
fit in a processing instruction (just '?>').
XML does not specify a way to escape this. The result produced here is "?&gt;".

* '''escapeASCII'''(s, width=4, base=16, htmlNames=True))

Escape the string as needed for it to fit in XML text content,
''and'' recode any non-ASCII characters as XML
entities and/or numeric character references.
`width` is the minimum number of digits to be used for numeric character references.
`base` must be 10 or 16, to choose decimal or hexadecimal references.
If `htmlNames` is True, HTML 4 named entities are used when applicable,
with numeric character references used otherwise.

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


==Useful variables==

* _nameStartCharRanges: A list of 2-tuples of code point integers,
each defining a range of characters that are XML name start characters.

* _nameCharAddlRanges: Like _nameStartCharRanges, but including only
the *additional* ranges allowed as XML name characters.

* _nameStartCharReList: A single string expressing the same ranges
as _nameStartCharRanges, in the form to go inside [] in a regex.

* _nameCharAddlReList: A single string expressing the same ranges
as _nameStartCharRanges, in the form to go inside [] in a regex.

* _xmlName: A complete (uncompiled) regex that matches XML NAME
(that is, a name start character plus zero or more name characters).

* _xmlQName: A complete (uncompiled) regex that matches Qnames
(an XML NAME, possibly preceded by another XML NAME and a colon).

* _xmlPName: Like _xmlQName except that the prefix is required, not optional.

* _xmlNmtoken: A complete (uncompiled) regex that matches XML NAME TOKEN.
This is like XML NAME except that all name characters are allowed, even
in first position.

* _xmlSpaceChars: A string containing only the XML space characters,
namely SPACE, TAB, LF, and CR. This does not include other Unicode space chars.

* _xmlSpaceExpr: A regex that matches one or more XML space characters.

* _xmlSpaceOnlyRegex: A regex that matches a string if it
consists entirely of XML space characters (this can also be approximated by
testing is str.strip() is empty/falsish).

In addition, you can call `allNameStartChars()` and/or `allNameCharAddls()`
to get strings containing all of the characters in the given category (this is
much less compact than the regex-style range notation).


=Known bugs and limitations=


=To do=

==Lower priority==

* Sync with XPLib.js
* Support a "*"/"#all"/"#any" namespace?


=Related commands=

`DomExtension.py` -- prior home of this package.

`domtabletools.py` -- DOM additions specifically for tables.

`BaseDom.py` -- A more Pythonic DOM++ implementation.

`Dominus.py` -- a disk-resident DOM implementation that can handle absurdly
large documents.

`XmlOutput.pm` -- Makes it easy to produce WF XML output. Provides methods
for escaping data correctly for each relevant context; knows about character
references, namespaces, and the open-element context; has useful methods for
inferring open and close tags to keep things in sync.


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

Separate package extracted 2024-08.
* 2024-08-14: Clean up extracted XmlStrings package, add and pass unit tests.
Fix bugs with name-start character list.


=Rights=

Copyright 2010, 2020, Steven J. DeRose. This work is licensed under a Creative
Commons Attribution-Share Alike 3.0 Unported License. For further information on
this license, see http://creativecommons.org/licenses/by-sa/3.0/.

For the most recent version, see [http://www.derose.net/steve/utilities] or
[http://github/com/sderose].


=Options=
"""

def rangesToReList(ranges:List):
    """Convert a list of codepoint (start, end) pairs to the form to put
    inside [] in a regex. Doesn't insert the brackets themselves.
    """
    buf = ""
    for r in ranges:
        if ( r[0] > r[1] or r[0] <= 0 or r[1] > 0xFFFF):
            raise ValueError("Bad range, %04x to %04x." % (r[0], r[1]))
        buf += "\\u%04x-\\u%04x" % (r[0], r[1])
    return buf


###############################################################################
#
class XmlStrings:
    """This class contains static methods and variables for basic XML
    operations such as testing syntax forms, escaping strings, etc.
    """
    _xmlSpaceChars = " \t\r\n"
    _xmlSpaceExpr = r"[" + _xmlSpaceChars + r"]+"
    _xmlSpaceOnlyRegex = re.compile("^[%s]*$" % (_xmlSpaceChars))

    # This excludes colon (":"), since we want to distinguish QNames.
    _nameStartCharRanges = [
        ( ord("_"), ord("_") ),
        ( ord("A"), ord("Z") ),
        ( ord("a"), ord("z") ),
        ( 0x00C0, 0x00D6 ),
        ( 0x00D8, 0x00F6 ),
        ( 0x00F8, 0x02FF ),
        ( 0x0370, 0x037D ),
        ( 0x037F, 0x1FFF ),
        ( 0x200C, 0x200D ),
        ( 0x2070, 0x218F ),
        ( 0x2C00, 0x2FEF ),
        ( 0x3001, 0xD7FF ),
        ( 0xF900, 0xFDCF ),
        ( 0xFDF0, 0xFFFD ),
        # ( "0x00010000, 0x000EFFFF" ),
    ]

    _nameCharAddlRanges = [
        ( ord("-"), ord("-") ),
        ( ord("."), ord(".") ),
        ( ord("0"), ord("9") ),
        ( 0x00B7, 0x00B7 ),
        ( 0x0300, 0x036F ),
        ( 0x203F, 0x2040 ),
    ]

    _nameStartCharReList = rangesToReList(_nameStartCharRanges)
    _nameCharAddlReList = (_nameStartCharReList +
        rangesToReList(_nameCharAddlRanges))

    _xmlName  = r"^[%s][%s]*$" % (
        _nameStartCharReList, _nameStartCharReList+_nameCharAddlReList)
    _xmlQName = r"^(%s(:%s)?$" % (_xmlName, _xmlName)
    _xmlPName = r"^(%s)(:%s)$" % (_xmlName, _xmlName)
    _xmlNmtoken = r"^[%s]+$" % (_nameCharAddlReList)

    @staticmethod
    def allNameStartChars() -> str:
        """A string of all chars allowed as first char of XML NAME.
        """
        buf = ""
        for r in XmlStrings._nameStartCharRanges:
            buf += "".join([ chr(cp) for cp in range(r[0], r[1]+1) ])
        return buf

    @staticmethod
    def allNameCharAddls() -> str:
        """A string of *additional* chars allowed past first char of XML NAME.
        """
        buf = ""
        for r in XmlStrings._nameCharAddlRanges:
            buf += "".join([ chr(cp) for cp in range(r[0], r[1]+1) ])
        return buf

    @staticmethod
    def allNameChars() -> str:
        """A string of all chars allowed past first char of XML NAME.
        """
        return XmlStrings.allNameStartChars() + XmlStrings.allNameCharAddls()


    ###########################################################################
    #
    @staticmethod
    def isXmlName(s:str) -> bool:
        """Return True for a NON-namespace-prefixed (aka) local name.
        """
        return bool(re.match(XmlStrings._xmlName, s))

    @staticmethod
    def isXmlQName(s:str) -> bool:
        """Return True for a namespace-prefixed OR unprefixed name.
        """
        parts = s.partition(":")
        if (parts[2] and not XmlStrings.isXmlName(parts[2])): return False
        return XmlStrings.isXmlName(parts[0])
        #if (re.match(XmlStrings._xmlQName, s)): return True
        #return False

    @staticmethod
    def isXmlPName(s:str) -> bool:
        """Return True only for a namespace-prefixed name.
        """
        parts = s.partition(":")
        return XmlStrings.isXmlName(parts[0]) and XmlStrings.isXmlName(parts[2])
        #if (re.match(XmlStrings._xmlPName, s)): return True
        #return False

    @staticmethod
    def isXmlNmtoken(s:str) -> bool:
        return bool(re.match(XmlStrings._xmlNmtoken, s))

    @staticmethod
    def isXmlNumber(s:str) -> bool:
        """Check whether the token is a number. This unsets re.Unicode,
        which would add all the non-Arabic digits (category [Nd]).
        """
        return bool(re.match(r"\d+$", s, re.ASCII))

    @staticmethod
    def escapeAttribute(s:str, quoteChar:str='"') -> str:
        """Turn characters special in (double-quoted) attributes, into char refs.
        Set to "'" if you prefer single-quoting your attributes, in which case
        that character is replaced by a character reference instead.
        This always uses the predefined XML named special character references.
        """
        s = XmlStrings.dropNonXmlChars(s)
        s = s.replace('&', "&amp;")
        s = s.replace('<', "&lt;")
        if (quoteChar == '"'): s = s.replace('"', "&quot;",)
        else: s = s.replace("'", "&apos;")
        return s
    escapeXmlAttribute = escapeAttribute

    @staticmethod
    def escapeText(s:str, escapeAllGT:bool=False) -> str:
        """Turn things special in text content, into char refs.
        This always uses the predefined XML named special character references.
        """
        s = XmlStrings.dropNonXmlChars(s)
        s = s.replace('&',   "&amp;")
        s = s.replace('<',   "&lt;")
        if (escapeAllGT): s = s.replace('>', "&gt;")
        else: s = s.replace(']]>', "]]&gt;")
        return s

    escapeXmlText = escapeText

    @staticmethod
    def escapeCDATA(s:str, replaceWith:str="]]&gt;") -> str:
        """XML Defines no particular escaping for this, we use char-ref syntax.
        """
        s = XmlStrings.dropNonXmlChars(s)
        s = s.replace(']]>', replaceWith)
        return s

    @staticmethod
    def escapeComment(s:str, replaceWith:str="-&#x2d;") -> str:
        """XML Defines no particular escaping for this, we use char-ref syntax.
        """
        s = XmlStrings.dropNonXmlChars(s)
        s = s.replace('--', replaceWith)
        return s

    @staticmethod
    def escapePI(s:str, replaceWith:str="?&gt;") -> str:
        """XML Defines no particular escaping for this, we use char-ref syntax.
        """
        s = XmlStrings.dropNonXmlChars(s)
        s = s.replace('?>', replaceWith)
        return s

    @staticmethod
    def escapeASCII(s:str, width:int=4, base:int=16, htmlNames:bool=True) -> str:
        """Turn all non-ASCII characters into character references,
        and then do a regular escapeText().
        @param width: zero-pad numbers to at least this many digits.
        @param base: 10 for decimal, 16 for hexadecimal.
        @param htmlNames: If True, use HTML 4 named entities when applicable.
        """
        def escASCIIFunction(mat:Match) -> str:
            """Turn all non-ASCII chars to character refs.
            """
            code = ord(mat.group[1])
            nonlocal width, base, htmlNames
            if (htmlNames and code in codepoint2name):
                return "&%s;" % (codepoint2name[code])
            if (base == 10):
                return "&#%*d;" % (width, code)
            return "&#x%*x;" % (width, code)

        s = XmlStrings.dropNonXmlChars(s)
        s = re.sub(r'([^[:ascii:]])r', escASCIIFunction, s)
        s = XmlStrings.escapeText(s)
        return s

    @staticmethod
    def dropNonXmlChars(s:str) -> str:
        """Remove the C0 control characters not allowed in XML.
        Unassigned Unicode characters higher up are left unchanged.
        """
        return re.sub("[\x00-\x08\x0b\x0c\x0e-\x1f]", "", str(s))

    @staticmethod
    def unescapeXml(s:str) -> str:
        """Converted HTML named, and SGML/XML/HTML numeric character references,
        to the literal characters.
        """
        assert isinstance(s, str)
        return re.sub(r'&(#[xX]?)?(\w+);', XmlStrings.unescapeXmlFunction, s)

    @staticmethod
    def unescapeXmlFunction(mat:Match) -> str:
        """Convert HTML entities and numeric character references to literal chars.
        group 1 is #, #x, or nothing; group 2 is the rest.
        """
        if (mat.group(1) is None):
            if (mat.group(2) in name2codepoint):
                return chr(name2codepoint[mat.group(2)])
            raise ValueError("Unrecognized entity name: '%s'." % (mat.group(2)))
        if (len(mat.group(1)) == 2):
            return chr(int(mat.group(2), 16))
        else:
            return chr(int(mat.group(2), 10))

    @staticmethod
    def normalizeSpace(s:str, allUnicode:bool=False) -> str:
        """By default, this only normalizes *XML* whitespace,
        per the XML spec, section 2.3, grammar rule 3.

        NOTE: Many methods of removing whitespace in Python do not suffice
        for Unicode. See https://stackoverflow.com/questions/1832893/

        U+200B ZERO WIDTH SPACE is left untouched below.
        """
        if (allUnicode):
            s = re.sub(r"\s+", " ", s, flags=re.UNICODE)
        else:
            s = re.sub(XmlStrings._xmlSpaceExpr, " ", s)
        s = s.strip(" ")
        return s

    @staticmethod
    def stripSpace(s:str, allUnicode:bool=False) -> str:
        """Remove leading and trailing space, but don't touch internal.
        """
        if (allUnicode):
            s = re.sub(r'^\s+|\s+$', "", s, flags=re.UNICODE)
        else:
            s = s.strip(XmlStrings._xmlSpaceChars)
        return s


    @staticmethod
    def makeStartTag(gi:str, attrs:Union[str, Dict]="",
        empty:bool=False, sort:bool=False) -> str:
        tag = "<" + gi
        if (attrs):
            if (isinstance(attrs, str)):
                tag += " " + attrs.strip()
            else:
                tag += XmlStrings.dictToAttrs(attrs, sortAttributes=sort)
        tag += "/>" if empty else ">"
        return tag

    @staticmethod
    def dictToAttrs(dct, sortAttributes: bool=None, normValues: bool=False) -> str:
        """Turn a dict into a serialized attribute list (possibly sorted
        and/or space-normalized). Escape as needed.
        """
        sep = " "
        anames = dct.keys()
        if (sortAttributes): anames.sort()
        attrString = ""
        for a in (anames):
            v = dct[a]
            if (normValues): v = XmlStrings.normalizeSpace(v)
            attrString += f"{sep}{a}=\"{XmlStrings.escapeAttribute(v)}\""
        return attrString

    @staticmethod
    def makeEndTag(name:str) -> str:
        return f"</{name}>"

    @staticmethod
    def getLocalPart(s:str) -> str:
        #if (not s): return ""
        #return re.sub(r'^.*:', '', s)
        return s.partition(":")[2] or s  # This is 10x faster.

    @staticmethod
    def getPrefixPart(s:str) -> str:
        #if (not s): return ""
        return s.partition(":")[0] or ""
