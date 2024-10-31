#!/usr/bin/env python3
#
# xmlstrings: A bunch of (hopefully) useful additions to the DOM API.
# 2010-01-10: DOMExtensions written by Steven J. DeRose.
# 2024-08: Separated from rest of DOMExtensions.
#
import re
from typing import Union, Match, Dict, List

import unicodedata
from html.entities import codepoint2name, name2codepoint
from basedomtypes import NMTOKEN_t

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


=To do=

==Lower priority==

* Sync with XPLib.js

* Integrate validation of the XSD types into their NewType definitioons.


=Related commands=

`basedom.py` -- a pure Python DOM++ implementation that uses this.

`documenttype.py` -- some overlap on supported datatypes.

`domextensions.py` -- prior home of this package.

`domtabletools.py` -- DOM additions specifically for tables.

`Dominus.py` -- a disk-resident DOM implementation that can handle absurdly
large documents (in progress).

`xmloutput.pm` -- an easy way to produce WF XML output. Provides methods
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


=Options=
"""


###############################################################################
#
def rangelist2rangespec(ranges:List) -> str:
    """Convert a list of codepoint pairs (start, end) to the form to put
    inside [] in a regex. Doesn't insert the brackets themselves.
    TODO: Ssupport rest of Unicode past BMP.
    """
    buf = ""
    for r in ranges:
        if ( r[0] > r[1] or r[0] < 0 or r[1] > 0xFFFF):
            raise ValueError("Bad range, %04x to %04x." % (r[0], r[1]))
        if (r[0] == r[1]): buf += "\\u%04x" % (r[0])
        else: buf += "\\u%04x-\\u%04x" % (r[0], r[1])
    return buf

class XmlStrings:
    """This class contains static methods and variables for basic XML
    operations such as testing syntax forms, escaping strings, etc.
    """
    xmlSpaces_list = " \t\r\n"
    xmlSpaces_re = r"[" + xmlSpaces_list + r"]+"
    xmlSpaceOnly_re = re.compile("^[%s]*$" % (xmlSpaces_list))

    # This excludes colon (":"), since we want to distinguish QNames.
    _nameStartChar_rangelist = [
        ( ord("_"), ord("_") ),
        ( ord("A"), ord("Z") ),
        ( ord("a"), ord("z") ),
        ( 0x00C0, 0x00D6 ),
        ( 0x00D8, 0x00F6 ),
        ( 0x00F8, 0x02FF ),
        ( 0x0370, 0x037D ),
        ( 0x037F, 0x1FFF ),
        ( 0x200C, 0x200D ),     # ZERO WIDTH NON-JOINER, ZERO WIDTH JOINER
        ( 0x2070, 0x218F ),
        ( 0x2C00, 0x2FEF ),
        ( 0x3001, 0xD7FF ),
        # Private use?
        ( 0xF900, 0xFDCF ),
        ( 0xFDF0, 0xFFFD ),
        # ( "0x00010000, 0x000EFFFF" ),
    ]

    _nameCharAddl_rangelist = [
        ( ord("-"), ord("-") ), # Watch out for regex
        ( ord("."), ord(".") ),
        ( ord("0"), ord("9") ),
        ( 0x00B7, 0x00B7 ),     # MIDDLE DOT (e.g. for Catalan)
        ( 0x0300, 0x036F ),     # Combining Diacritical Marks
        ( 0x203F, 0x2040 ),     # Undertie and Char tie
    ]

    _nonXml_rangelist = [
        ( 0x0000, 0x0008 ),
        ( 0x000B, 0x000B ),
        ( 0x000E, 0x001F ),
        ( 0xD800, 0xDFFF ),
    ]

    _nameStartChar_rangespec = rangelist2rangespec(_nameStartChar_rangelist)
    _addl_rangespec = rangelist2rangespec(_nameCharAddl_rangelist)
    _nameChar_rangespec = _nameStartChar_rangespec + _addl_rangespec
    _nonXml_rangespec = rangelist2rangespec(_nonXml_rangelist)

    # These do not include ^...$, e.g. so can match against start of a buffer
    # regardless of what follows. Depending on the purpose, callers may have
    # to check -- for example, that a space follows a matching NCNAME.
    #
    NMTOKEN_re = r"[%s]+" % (_nameChar_rangespec)
    NCName_re  = r"[%s][%s]*" % (_nameStartChar_rangespec, _nameChar_rangespec)

    QName_re = r"%s(:%s)?" % (NCName_re, NCName_re)
    QQName_re = r"%s(:%s)*" % (NCName_re, NCName_re)
    PName_re = r"%s:%s" % (NCName_re, NCName_re)

    @staticmethod
    def allNameStartChars() -> str:
        """A string of all chars allowed as first char of XML NAME.
        """
        buf = ""
        for r in XmlStrings._nameStartChar_rangelist:
            buf += "".join([ chr(cp) for cp in range(r[0], r[1]+1) ])
        return buf

    @staticmethod
    def allNameCharAddls() -> str:
        """A string of *additional* chars allowed past first char of XML NAME.
        """
        buf = ""
        for r in XmlStrings._nameCharAddl_rangelist:
            buf += "".join([ chr(cp) for cp in range(r[0], r[1]+1) ])
        return buf

    @staticmethod
    def allNameChars() -> str:
        """A string of all chars allowed past first char of XML NAME.
        """
        return XmlStrings.allNameStartChars() + XmlStrings.allNameCharAddls()


    ###########################################################################
    # XML string predicates
    #
    isXmlChars_re = re.compile(r"[%s]" % (_nonXml_rangespec))
    isXmlName_re = re.compile(f"^{NCName_re}$")
    isXmlQName_re = re.compile(f"^{QName_re}$")
    isXmlQQName_re = re.compile(f"^{QQName_re}$")
    isXmlPName_re = re.compile(f"^{PName_re}$")
    isXmlNMTOKEN_re = re.compile(f"^{NMTOKEN_re}$")
    isXmlNumber_re = re.compile(r"^\d+$")

    @staticmethod
    def isXmlChars(s:str) -> bool:
        """At least one char, and all the individual chars are allowed.
        """
        return s and not re.search(XmlStrings.isXmlChars_re, s)

    @staticmethod
    def isXmlName(s:str) -> bool:
        """Return True for a NON-namespace-prefixed (aka) local name.
        """
        return bool(re.match(XmlStrings.isXmlName_re, s))
    isXmlLName = isXmlName

    @staticmethod
    def isXmlQName(s:str) -> bool:
        """Return True for a namespace-prefixed OR unprefixed name.
        """
        return bool(re.match(XmlStrings.isXmlQName_re, s))

    @staticmethod
    def isXmlQQName(s:str) -> bool:
        """Return True even for multiple prefixes.
        """
        return bool(re.match(XmlStrings.isXmlQQName_re, s))

    @staticmethod
    def isXmlPName(s:str) -> bool:
        """Return True only for a namespace-prefixed name.
        """
        return bool(re.match(XmlStrings.isXmlPName_re, s))

    @staticmethod
    def isXmlNMTOKEN(s:str) -> bool:
        return bool(re.match(XmlStrings.isXmlNMTOKEN_re, s))

    @staticmethod
    def isXmlNumber(s:str) -> bool:
        """Check whether the token is a number. This turns off re.Unicode,
        lest we get all the non-Arabic digits (category [Nd]).
        """
        return bool(re.match(XmlStrings.isXmlNumber_re, s, flags=re.ASCII))


    ###########################################################################
    # Escapers
    #
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
        """Delete truly prohibited chars, turn all non-ASCII characters
        into character references, then do a regular escapeText().
        @param width: zero-pad numbers to at least this many digits.
        @param base: 10 for decimal, 16 for hexadecimal.
        @param htmlNames: If True, use HTML 4 named entities when applicable.
        """
        assert base in [ 10, 16 ]
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

    ###########################################################################
    # Unescapers and cleaners
    #
    @staticmethod
    def dropNonXmlChars(s:str) -> str:
        """Remove the C0 control characters not allowed in XML.
        Unassigned Unicode characters higher up are left unchanged.
        """
        return re.sub(r"[%s]+" % (XmlStrings._nonXml_rangespec), "", s)

    entref_re = r"&(#[xX]?)?(\w+);"  # TODO Ok for common ent names, but...

    @staticmethod
    def unescapeXml(s:str) -> str:
        """Converted HTML named, and SGML/XML/HTML numeric character references,
        to the literal characters.
        """
        return re.sub(XmlStrings.entref_re, XmlStrings.unescapeXmlFunction, str(s))

    @staticmethod
    def unescapeXmlFunction(mat:Match) -> str:
        """Convert HTML entities and numeric character references to literal chars.
        group 1 is #, #x, or nothing; group 2 is the rest.
        TODO Add option for alt dict
        """
        if (mat.group(1) is None):
            if (mat.group(2) in name2codepoint):
                return chr(name2codepoint[mat.group(2)])
            raise ValueError("Unrecognized entity name: '%s'." % (mat.group(2)))
        if (len(mat.group(1)) == 2):
            return chr(int(mat.group(2), 16))
        else:
            return chr(int(mat.group(2), 10))


    ###########################################################################
    # XML syntax builders
    #
    @staticmethod
    def makeStartTag(gi:str, attrs:Union[str, Dict]="",
        empty:bool=False, sort:bool=False) -> str:
        tag = "<" + gi
        if (attrs):
            if (isinstance(attrs, str)):
                tag += " " + attrs.strip()
            else:
                tag += XmlStrings.dictToAttrs(attrs, sort=sort)
        tag += "/>" if empty else ">"
        return tag

    @staticmethod
    def dictToAttrs(dct:Dict, sort:bool=False, normValues:bool=False) -> str:
        """Turn a dict into a serialized attribute list (possibly sorted
        and/or space-normalized). Escape as needed.
        """
        sep = " "
        anames = dct.keys()
        if (sort): anames = sorted(list(anames))
        attrString = ""
        for a in (anames):
            v = dct[a]
            if (normValues): v = XmlStrings.normalizeSpace(v)
            attrString += f"{sep}{a}=\"{XmlStrings.escapeAttribute(v)}\""
        return attrString

    @staticmethod
    def makeEndTag(name:NMTOKEN_t) -> str:
        return f"</{name}>"


    ### TODO Integrate with more general space-handling below.
    #
    @staticmethod
    def normalizeSpace(s:str, allUnicode:bool=False) -> str:
        if (allUnicode):
            s = re.sub(r"\s+", " ", s, flags=re.UNICODE)
        else:
            s = re.sub(XmlStrings.xmlSpaces_re, " ", s)
        s = s.strip(" ")
        return s

    @staticmethod
    def replaceSpace(s:str, allUnicode:bool=False) -> str:
        """Per xmlschema-2, section 4.3.6
        """
        if (allUnicode): return re.sub(r"\s", " ", s, flags=re.UNICODE)
        return re.sub(r"[\t\r\n]", " ", s)

    @staticmethod
    def stripSpace(s:str, allUnicode:bool=False) -> str:
        """Remove leading and trailing space, but don't touch internal.
        """
        if (allUnicode):
            s = re.sub(r'^\s+|\s+$', "", s, flags=re.UNICODE)
        else:
            s = s.strip(XmlStrings.xmlSpaces_list)
        return s


    ###########################################################################
    # XML name manglers
    #
    @staticmethod
    def getPrefixPart(s:str) -> str:
        p, _, l = s.partition(":")
        return p if l else ""

    @staticmethod
    def getLocalPart(s:str) -> str:
        return s.partition(":")[2] or s  # This is faster


###############################################################################
#
class NameTest:
    """Name/identifier characters vary.

    "Stat rosa pristina nomine, nomina nuda tenemus"
        -- Umberto Ecu, Il nome d'rosa
    """
    _NameStyle = {
        "XML": 1,     # XML NAME
        "HTML": 2,    # Any but XML SPACE? For Class tokens, etc.
        "WHATWG": 3,  # Any but WHATWG__whitespace
        "ASCII": 4,   # XML except no non-ASCII
        "PYTHON": 5,  # Python identifiers
    }

    def __init__(self, nameStyle:str="XML"):
        assert nameStyle in NameTest._NameStyle
        self.nameStyle = nameStyle
        self.expr = None
        if nameStyle == "XML":
            self.expr = None
        elif nameStyle == "HTML":
            self.expr = re.compile(r"^[^ \t\r\n]+$")
        elif nameStyle == "WHATWG":
            self.expr = re.compile(r"^[^ \t\r\n\f]+$")
        elif nameStyle == "ASCII":
            self.expr = re.compile(r"^[_a-zA-Z][-_.a-zA-Z0-9]*$")
        elif nameStyle == "PYTHON":
            self.expr = None

    def isName(self, s:str) -> bool:
        if self.nameStyle == "XML":
            return XmlStrings.isXmlName(s)
        elif self.nameStyle == "PYTHON":
            return s.isidentifier()
        else:
            return re.match(self.expr, s)


###############################################################################
#
class UNormHandler:
    """Whether/how various tokens should be Unicode-normalized.

    "Lest one good custom should corrupt the world."
        -- Alfred Lord Tennyson, "The Passing of Arthur"
    """
    _UNormTx = {
        "NONE": None,
        "NFKC": "NFKC",
        "NFKD": "NFKD",
        "NFC": "NFC",
        "NFD": "NFD",
    }

    def __init__(self, how:str="NONE"):
        if not how: how = "NONE"
        if how not in UNormHandler._UNormTx:
            raise KeyError(f"Unknown Unicode normalization form '{how}'.")
        self.formName = UNormHandler._UNormTx[how]
        # or lambda s: unicodedata.normalize(UNormHandler._UNormTx[how], s)

    def normalize(self, s:str) -> str:
        if not self.formName: return s
        return unicodedata.normalize(self.formName, s)


###############################################################################
#
class CaseHandler:
    """How case should be handled.

    "You've got to know when to hold 'em,
    know when to fold 'em,
    know when to walk away
    know when to run."
        -- Don Schlitz, The Gambler
    """
    _CaseTx = {
        "NONE": None,
        "FOLD": str.casefold,
        "LOWER": str.lower,
        "UPPER": str.upper,
    }

    def __init__(self, how:str="NONE"):
        if how in CaseHandler._CaseTx:
            self.how = CaseHandler._CaseTx[how]
        else:
            self.how = None
        self.foldFn = CaseHandler._CaseTx[how]

    def normalize(self, s:str) -> str:
        if not self.how: return s
        return self.foldFn(s)


###############################################################################
#
class WSDef:
    """Ways to define blank space.

    “And then I have a secret. Did you know what will happen if you
    eliminate the empty spaces from the universe, eliminate the  empty
    spaces in all the atoms? The universe will become as big as my fist."
        -- Umberto Ecu, Interview with Mukund Padmanabhan, Oct 23, 2005
    """
    _xmlSpaces = XmlStrings.xmlSpaces_list
    _unicodeZs = ( ""
        # TAB LF CR are all Cc
        #"\u0020"  # (Zs) SPACE
        + "\u00a0"  # (Zs) NO-BREAK SPACE
        + "\u1680"  # (Zs) OGHAM SPACE MARK
        + "\u2000"  # (Zs) EN QUAD
        + "\u2001"  # (Zs) EM QUAD
        + "\u2002"  # (Zs) EN SPACE
        + "\u2003"  # (Zs) EM SPACE
        + "\u2004"  # (Zs) THREE-PER-EM SPACE
        + "\u2005"  # (Zs) FOUR-PER-EM SPACE
        + "\u2006"  # (Zs) SIX-PER-EM SPACE
        + "\u2007"  # (Zs) FIGURE SPACE
        + "\u2008"  # (Zs) PUNCTUATION SPACE
        + "\u2009"  # (Zs) THIN SPACE
        + "\u200a"  # (Zs) HAIR SPACE
        + "\u202f"  # (Zs) NARROW NO-BREAK SPACE
        + "\u205f"  # (Zs) MEDIUM MATHEMATICAL SPACE
        + "\u3000"  # (Zs) IDEOGRAPHIC SPACE
    )
    _unicodeAll = (
        _xmlSpaces
        + _unicodeZs
        + "\x0C"    # FORM FEED (Cc)
        + "\x0B"    # LINE TABULATION (Cc)
        + "\x85"    # NEXT LINE (Cc) -- beware PC ELLIPSIS, Mac O+diaeresis
        + "\u2028"  # LINE SEPARATOR (Zl)
        + "\u2029"  # PARAGRAPH SEPARATOR (Zp)
    )

    # Possible additions (none are in Python str.isspace())
    _aggressive = (
          "\u0008"  # BACKSPACE (Cc)
        + "\u1361"  # ETHIOPIC WORDSPACE (Po)
        + "\u180E"  # MONGOLIAN VOWEL SEPARATOR (was Zs (?), now Cf)
        + "\u200B"  # ZERO WIDTH SPACE (Cf)
        + "\u200C"  # ZERO WIDTH NON-JOINER (Cf)
        + "\u200D"  # ZERO WIDTH JOINER (Cf)
        + "\u2060"  # WORD JOINER (???)
        + "\u303F"  # IDEOGRAPHIC HALF FILL SPACE (So)
        + "\u3164"  # HANGUL FILLER (Lo)
        + "\uFE0F"  # VARIATION SELECTOR-16 (Mn)
        + "\uFEFF"  # ZERO WIDTH NO-BREAK SPACE (Cf)
        + "\uFFA0"  # HALFWIDTH HANGUL FILLER (Lo)
    )

    _WSChoices = {
        "XML": _xmlSpaces,
        "WHATWG": _xmlSpaces + "\f",
        "CPP": _xmlSpaces + "\f\x0B",
        "UNICODE_ALL": _unicodeAll,
        "JAVASCRIPT": _unicodeAll,
        "PY_ISSPACE": _unicodeAll,
        "AGGRESSIVE": _unicodeAll + _aggressive,
    }

    def __init__(self, how:str="XML"):
        assert how in WSDef._WSChoices
        self.how = how
        self.spaceList = WSDef._WSChoices[how]

    @property
    def spaces(self) -> str:
        """Return the list of all characters in the designated spaceList.
        """
        return self.spaceList

    def isSpace(self, s:str) -> bool:
        """Like Python is___(), True if non-empty and all chars in category.
        """
        return s and not re.search(f"[^{self.spaceList}]", s)

    def hasSpace(self, s:str) -> bool:
        """True if there is at least one space character in s.
        """
        return re.search(f"[{self.spaceList}]", s)


###############################################################################
#
class WSHandler:
    """Make functions to do one of the space cleanups given a spaceDef.

    "And the people did whatever seemed right in their own eyes."
        -- Judges 21:25
    """
    def __init__(self, spaceDef:str="XML", tgtChar:str=" "):
        self.spaceList = WSDef(how=spaceDef).spaces
        assert len(tgtChar) == 1
        self.tgtChar = tgtChar

    def lstrip(self, s:str) -> str:
        return s.lstrip(self.spaceList)

    def rstrip(self, s:str) -> str:
        return s.lstrip(self.spaceList)

    def strip(self, s:str) -> str:
        return s.strip(self.spaceList)

    def replace(self, s:str) -> str:
        return re.sub(f"[{self.spaceList}]", self.tgtChar, s)

    def normalize(self, s:str) -> str:
        """Reduce internal spaces/runs to a single tgtChar and
        drop leading and trailing spaces.
        """
        return re.sub(f"[{self.spaceList}]+", self.tgtChar, s).strip(self.tgtChar)
    collapse = normalize


###############################################################################
#
class Normalizer:
    """Do a selected set of normalizations (case, unicode, and/or whitespace).

    Nobody realizes that some people expend tremendous energy
    merely to be normal.
        -- Albert Camus, Notebook 4, quoting Blanche Balain
    """
    def __init__(self, unorm:str="NONE", case:str="NONE", wsDef:str="XML",
        tgtChar:str=" "):
        self.unorm = UNormHandler(unorm)
        self.case = CaseHandler(case)
        self.wsDef = WSDef(wsDef)
        self.tgtChar = tgtChar
        self.wsHandler = WSHandler(spaceDef=self.wsDef, tgtChar=tgtChar)

    def normalize(self, s:str) -> str:
        s = self.unorm.normalize(s)
        s = self.case.normalize(s)
        s = self.wsHandler.normalize(s)
        return s

    def cmp(self, s1:str, s2:str) -> int:
        s1 = self.normalize(s1)
        s2 = self.normalize(s2)
        return (s1 > s2) - (s1 < s2)
