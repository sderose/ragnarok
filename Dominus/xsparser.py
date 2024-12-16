#!/usr/bin/env python3
#
# XSParser: An easily-tweakable XML parser, with DTD++ support.
# Original: multiXml written 2011-03-11 by Steven J. DeRose.
#
#pylint: disable=W1201
#
import os
#import sys
import codecs
import re
import logging
from typing import Union, List, Dict, Tuple, Iterable
from types import SimpleNamespace
from collections import OrderedDict

#import html
from html.entities import name2codepoint  # codepoint2name

from xmlstrings import XmlStrings as XStr, WSHandler, CaseHandler, UNormHandler
from saxplayer import SaxEvent
from basedomtypes import FlexibleEnum, NSuppE, NMTOKEN_t
from documenttype import Model, RepType, AttrTypes, ContentType  # ModelGroup

lg = logging.getLogger("EntityManager")
logging.basicConfig(level=logging.INFO, format='%(message)s')

__metadata__ = {
    "title"        : "XSParser",
    "description"  : "An easily-tweakable XML parser, with DTD++ support.",
    "rightsHolder" : "Steven J. DeRose",
    "creator"      : "http://viaf.org/viaf/50334488",
    "type"         : "http://purl.org/dc/dcmitype/Software",
    "language"     : "Python 3.7",
    "created"      : "2011-03-11",
    "modified"     : "2024-11-15",
    "publisher"    : "http://github.com/sderose",
    "license"      : "https://creativecommons.org/licenses/by-sa/3.0/"
}
__version__ = __metadata__['modified']


descr = """
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

* "oflags": False
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

* "COID"

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

* "uNormHandler": "NONE"

* "wsHandler": "XML"

* "radix": "."
Decimal point replacement for XSD floats.


===Namespace stuff===

* "nsSep": ":"
    Change the namespace-separator from ":" to something else.

* "nsUsage": None
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
"""

class LocType(FlexibleEnum):
    LITERAL = 1
    SYSTEM = 2
    PUBLIC = 3

class ParseType(FlexibleEnum):
    PARSED = 1
    CDATA = 2
    RCDATA = 3
    NDATA = 4

class EntSpace(FlexibleEnum):
    GENERAL = 1
    PARAMETER = 2
    NOTATION = 3
    SDATA = 4

EOF = -1


###############################################################################
class EntityDef:
    """Defining information re. a single entity or notation.
    We consider general ents, parameter ents, notations, and SDATA ents
    all to be sub-spaces of the same notion.
    """
    def __init__(self,
        space:EntSpace,
        name:str,
        parseType:ParseType=ParseType.PARSED,
        publicId:str=None, systemId:str=None,  encoding:str="utf-8",
        data:str=None,
        notationName:str=None
        ):
        assert isinstance(space, EntSpace)
        if not XStr.isXmlName(name):
            raise SyntaxError(f"Name '{name}' for entity is not valid.")
        assert isinstance(parseType, ParseType)
        if notationName: assert XStr.isXmlName(notationName)

        self.space = space
        self.name = name
        self.parseType = parseType

        self.encoding = encoding
        self.wsTx = WSHandler("XML")
        self.caseTx = CaseHandler("NONE")
        self.uNormTx = UNormHandler("NONE")

        if publicId: self.locType = LocType.PUBLIC
        elif systemId: self.locType = LocType.SYSTEM
        else: self.locType = LocType.LITERAL
        self.publicId = publicId
        self.systemId = systemId
        self.data = data
        self.notationName = notationName

        if self.locType == LocType.LITERAL:
            assert space != EntSpace.NOTATION
            self.path = None
        else:
            self.path = self.findLocalPath()

    def findLocalPath(self, trace:bool=False) -> str:
        """Catalog, path var, etc.
        TODO Add PUBLIC support
        """
        evName = "ENTITYPATH"  # TODO Move up to option
        if not self.systemId:
            raise IOError("No system ID for %s." % (self.name))
        if isinstance(self.systemId, Iterable): systemIds = self.systemId
        else: systemIds = [ self.systemId ]

        if trace: print(f"Seeking entity {self.name}:")
        for systemId in systemIds:
            if trace: print(f"  System id '{systemId}'")
            if os.path.isfile(self.systemId): return self.systemId
            if evName in os.environ:
                epaths = os.environ[evName].split(":")
                for epath in epaths:
                    cand = os.path.join(epath, self.systemId)
                    if trace: print(f"    Trying {cand}")
                    if os.path.isfile(cand): return cand
        raise IOError("No file found for %s (systemIds %s)." % (self.name, systemIds))


###############################################################################
#
class EntityFrame:
    """Used by EntityManager for one currently-open entity.
    TODO: How best to signal EOF on the current entity?

    Readers in here will not go past frame EOF, or expand any entities.
    So it's for things like name tokens, reserved words, single delimiters,
    qlits, comments,... If they fail to match, they return None and
    do not move the input cursor.
    """
    def __init__(self, eDef:EntityDef, encoding:str="utf-8", bufSize:int=1024):
        assert isinstance(eDef, EntityDef)
        assert bufSize > 100
        self.eDef = eDef
        self.encoding = encoding
        self.ifh = None
        self.bufSize = bufSize
        self.buf = ""
        self.bufPos = 0
        self.lineNum = 0
        self.offset = 0
        if self.eDef.data:
            self.buf = self.eDef.data  # TODO Copy?
        elif self.eDef.path:
            self.ifh = codecs.open(self.eDef.path, "rb", self.eDef.encoding)
            self.buf = self.ifh.read()

    def close(self) -> None:
        if self.ifh: self.ifh.close()
        self.buf = None

    @property
    def bufLeft(self) -> int:
        return len(self.buf) - self.bufPos

    def peek(self, n:int=1) -> str:
        """Return the next n characters (or fewer if EOF is coming),
        without actually consuming them. No skipSpaces options here,
        it could get circular.
        """
        if self.bufLeft < n:
            self.topOff()
            if self.bufLeft < n: return None
        return self.buf[self.bufPos:self.bufPos+n]

    def consume(self, n:int=1) -> str:
        """Same as peek except the characters really ARE consumed.
        But only if there are at least n available.No skipSpaces options here,
        it could get circular.
        """
        if self.bufLeft < n:
            self.topOff(n)
            if self.bufLeft < n: return None
        rc = self.buf[self.bufPos:self.bufPos+n]
        self.bufPos += n
        return rc

    def pushBack(self, s:str) -> None:
        """You can push back as much as memory permits. But if what you push
        back isn't what you read, that may not be good. Real file reading
        will pick up once the buffer (including the pushBack) is exhausted.
        Barely used.
        """
        n = len(s)
        self.buf = s + self.buf[self.bufPos:]
        self.bufPos = 0
        self.offset -= n
        self.lineNum -= s.count('\n')

    def topOff(self, n:int=0) -> bool:
        """We do not top off across entity boundaries here.
        Read more data (if there is any), to get at least n available chars.
        If EOF happens before n, buf ends up short.
        If EOF happens and there's nothing in buf, that's really EOF on the entity.
        """
        if not n: n = self.bufSize
        if self.bufLeft > n: return
        if not self.ifh:
            if self.bufPos >= len(self.buf):
                self.buf = ""
                return EOF
        newChars = self.ifh.read(n)
        #lg.info("\n  Topped off with: ###%s###", newChars)
        self.lineNum += newChars.count('\n')
        self.offset += len(newChars)
        self.buf = self.buf[self.bufPos:] + newChars
        self.bufPos = 0
        if not self.buf:
            self.ifh.close()
            return False  # EOF
        return True

    def skipSpaces(self, allowComments:bool=True) -> bool:
        """Calling this is key to keeping the buffer full.
        Since this is in EntityFrame, it doesn't handle parameter entities
        (they change the EntityFrame, so are handled one level up).
        XML eliminated in-markup --...-- comments.
        TODO: Option to return the actual space, for in document content?
        """
        while True:
            if self.bufLeft < self.bufSize>>2: self.topOff()
            if not self.bufLeft: return EOF
            if self.buf[self.bufPos] in " \t\r\n":
                self.bufPos += 1
            elif allowComments and self.peek(2) == "--":
                self.readSepComment()
            else:
                return True

    def readSepComment(self, ss:bool=True) -> str:
        """Read a comment that's just the --...-- part.
        """
        if ss: self.skipSpaces()
        # Or readToString("--")
        mat = re.match(r"^--([^-]|-[^-])+--", self.buf[self.bufPos:])
        if not mat: return None
        self.bufPos += len(mat.group(1))
        return mat.group(1)

    def readConst(self, const:str, ss:bool=True,
        thenSp:bool=False, fold:bool=False) -> str:
        """IF you want to do case-ignorant comparison, make sure your
        'const' is already in the desired case.
        """
        # TODO Case-ignoring option?
        if ss: self.skipSpaces()
        if self.bufLeft < len(const)+1:
            self.topOff()
            if self.bufLeft < len(const)+1: return None
        bufPart = self.peek(len(const))
        if fold: bufPart = CaseHandler.UPPER.normalize(bufPart)  # TODO Generalize
        if bufPart != const: return None
        if thenSp and not self.buf[self.bufPos+len(const)].isspace():
            return None
        self.bufPos += len(const)
        return bufPart

    def readInt(self,  ss:bool=True, signed:bool=True) -> int:
        """Read a (possibly signed) decimal int.
        """
        if ss: self.skipSpaces()
        expr = r"[-+]?\d+" if signed else r"\d+"
        mat = re.match(expr, self.buf[self.bufPos:])
        if not mat: return None
        tok = self.consume(len(mat.group()))
        return int(tok, 10)

    def readBaseInt(self,  ss:bool=True) -> int:
        """Read any of 999, 0xFFF, 0o777, 0b1111.
        """
        if ss: self.skipSpaces()
        mat = re.match(r"0x[\da-f]+|0o[0-7]+|0b[01]+|[-+]?\d+",
            self.buf[self.bufPos:], re.I)
        if not mat: return None
        tok = self.consume(len(mat.group()))
        return int(tok)

    def readFloat(self,  ss:bool=True, signed:bool=True,
        specialFloats:bool=False) -> float:
        """TODO: exponential notation? switch specialFloats to options.
        NIT: Consumes a sign even if no following number.
        """
        if ss: self.skipSpaces()
        if specialFloats:  # TODO specialFloats should ignore case
            if self.readConst("NaN"): return float("NaN")
            if self.readConst("-Inf"): return float("-Inf")
            if self.readConst("Inf"): return float("Inf")
        fToken = ""
        c = self.peek()
        if signed and c in "+-":
            fToken = self.consume()
            c = self.peek()
        while (c is not None):
            if c.isdigit(): fToken += self.consume()
            elif c == ".":
                if "." in fToken: break
                fToken += self.consume()
            c = self.peek()
        if fToken.strip("+-.") == "": return None  # Pushback?
        return float(fToken)

    def readName(self, ss:bool=True) -> str:
        """
        TODO Add options to allow/require initial "#"
        TODO Add option to require \\s, \\b, or \\W after? Meh.
        This doesn't recognize parameter entity refs. Must it?
        """
        if ss: self.skipSpaces()
        #lg.warning(f"readName: buf has '{self.buf[self.bufPos:]}'.\n")
        # Not re.fullmatch here!
        mat = re.match(XStr.isXmlQName_re, self.buf[self.bufPos:])
        if not mat: return None
        self.bufPos += len(mat.group())
        return mat.group()

    def readEnumName(self, names:Iterable, ss:bool=True) -> str:
        """See if the source starts with any of the names.
        For an Enum, you could pass enumType.__members__.keys().
        TODO option to require \\W after
        """
        if ss: self.skipSpaces()
        for name in names:
            if self.readConst(name): return name
        return None

    def readRegex(self, regex:Union[str, re.Pattern], ss:bool=True,
        fold:bool=True) -> re.Match:
        """Check if the regex matches immediately and return the match object
        (so captures can be distinguished) and consume the matched text.
        If no match, return None and consume nothing.
        TODO Won't match across buffer topOffs or entities.
        """
        if ss: self.skipSpaces()
        self.topOff()
        mat = re.match(regex, self.buf[self.bufPos:], flags=re.I if fold else 0)
        if not mat: return None
        self.bufPos += len(mat.group())
        return(mat)

    def readToString(self, ender:str, consumeEnder:bool=True) -> str:
        rbuf, ender = self.readToAnyOf([ ender ], consumeEnder)
        return rbuf

    def readToAnyOf(self, enders:List, consumeEnder:bool=True) -> (str, str):
        """Read to any of the given strings. Nothing else is recognized.
        Unlike most readers, this one doesn't leave things unchanged
        if it fails, because failure means we hit EOF.
        This shouldn't be used for one of several options for what comes next.
        Rather, it's for where you really, really have to have some stuff
        ended by this thing.
        This does not cross entity boundaries. Should it, for marked sections?
        """
        rbuf = ""
        while True:
            if self.bufLeft < self.bufSize>>2:
                self.topOff()
                if not self.bufLeft: return None, None
            ender, where = self.findFirst(self.buf, enders, self.bufPos)
            if ender is None:  # Keep going
                rbuf += self.buf[self.bufPos:]
                self.buf = ""
                self.bufPos = 0
                self.topOff()
            else:
                rbuf += self.buf[self.bufPos:where]
                moveTo = where + (len(ender) if consumeEnder else 0)
                self.buf = self.buf[moveTo:]
                self.bufPos = 0
                return rbuf, ender
        return rbuf, None  # TODO Notify EOF

    def findFirst(self, s:str, targets:List, start:int) -> (str, int):
        bestIndex = None
        bestTarget = None
        for target in targets:
            iLoc = s.find(target, start)
            if iLoc < 0: continue
            if bestIndex is None or iLoc < bestIndex:
                bestIndex = iLoc
                bestTarget = target
        return bestTarget, bestIndex


###############################################################################
#
class StackReader:
    """Keep dictionaries of entities and notations, and a stack of
    open ones being read. Support very basic read operations (leave the
    fancy stuff for a subclass to add), and support extensions.

    Shunt the deuterium from the main cryo-pump to the auxiliary tank.
    Er, the tank can't withstand that kind of pressure.
    Where'd you... where'd you get that idea?
    ...It's in the impulse engine specifications.
    Regulation 42/15 -- Pressure Variances on the IRC Tank Storage?
    Yeah.
    Forget it. I wrote it. Just... boost the flow. It'll work.
            -- ST:TNG "Relics"
    """
    attrTypes = {
        "CDATA":1, "ENTITY":1, "ENTITIES":2, "NOTATION":1,
        "ID":1, "IDREF":1, "IDREFS":2,
        "NAME":1, "NAMES":2, "NUMBER":1, "NUMBERS":2,
        "NMTOKEN":1, "NMTOKENS":2, "NUTOKEN":1, "NUTOKENS":2,
    }

    attrDefaults = {
        "#IMPLIED":1, "#REQUIRED":1, "#FIXED":1, "#CURRENT":1, "#CONREF":1,
    }

    def __init__(self, rootPath:str=None, encoding:str="utf-8",
        handlers:Dict=None, entPath:List=None, bufSize:int=1024,
        options:Dict=None):
        self.rootPath = rootPath
        self.encoding = encoding
        self.handlers = handlers or {}  # keyed off saxplayer.SaxEvent
        self.entPath = entPath  # dirs to look in
        self.bufSize = bufSize

        self.generalDefs = {}
        self.parameterDefs = {}
        self.notationDefs = {}
        self.sdataDefs = {}

        self.spaces = {
            EntSpace.GENERAL: self.generalDefs,
            EntSpace.PARAMETER: self.parameterDefs,
            EntSpace.NOTATION: self.notationDefs,
            EntSpace.SDATA: self.sdataDefs
        }

        # IO state
        self.rootDef = None
        self.rootFrame = None
        self.totLines = 0  # overall lines processed
        self.totChars = 0  # overall chars processed
        self.totEvents = 0

        # Parser state
        self.entStack = []
        self.msStack = []
        self.tagStack = []
        self.sawSubsetOpen = False
        self.bangAttrs = {}

        # Optional feature and extension switches
        # Switchable in XML DCL (iff "version" starts with "s.")
        #
        self.options = SimpleNamespace(**{
            ### Size limits and security
            "MAXEXPANSION": 1 << 20,# Limit expansion length of entities
            "MAXENTITYDEPTH": 1000, # Limit nesting of entities
            "charEntities": True,   # Only SDATA and CDATA entities (no recursion).  TODO
            "extEntities": True,    # Allow external entity refs  TODO
            "netEntities": True,    # Allow off-localhost external entity refs  TODO
            # TODO Limit system entities to subtree/vol/path?

            ### Schemas
            "schemaType": "DTD",    # <!DOCTYPE foo SYSTEM "" NDATA XSD>  TODO

            ### Elements
            "groupDcl": False,      # <!ELEMENT (x|y|z)...>             TODO
            "oflag": False,         # <!ELEMENT - O para...>
            "sgmlWord": False,      # CDATA, RCDATA, #CURRENT, etc.
            "mixel": False,         # Dcl content keyword ANYELEMENT    TODO
            "mixins": False,        # cf incl exceptions
            "repBrace": False,      # {min, max} for repetition
            "emptyEnd": False,      # </>
            "restart": False,       # <|> to close & reopen current element type
            "simultaneous": False,  # <b|i>, </i|/b>                    TODO
            "multiTag": False,      # <div/title>Introduction</title>   TODO
            "suspend": False,       # <x>...<-x>...<+x>...</x> (???)    TODO
            "olist": False,         # olist, not stack

            ### Attributes
            "globalAttr": False,    # <!ATTLIST * ...>                  TODO
            "xsdType": False,       # XSD builtins for attribute types
            "xsdPlural": False,     # Add list variants with a repetition suffix TODO
            "specialFloat": False,  # Nan, Inf, etc.
            "unQuotedAttr": False,  # <p x=foo>
            "curlyQuote": False,
            "booleanAttr": False,   # <x +border -foo>
            "bangAttr": False,      # != on first use to set dft        TODO
            "bangAttrType": False,  # !typ= to set datatype             TODO
            "coID": False,          # co-index logical elements frags   TODO
            "nsID": False,          # IDs can have ns prefix            TODO
            "stackID": False,       #                                   TODO

            ### Entities etc.
            "multiPath": False,     # Multiple SYSTEM IDs
            "charEnts": False,      # Enable HtML/Annex D named char refs
            "unameEnts": False,     # &em_quad; etc                     TODO
            "unameAbbr": False,     # &math_frak_r;                     TODO
            "multiSDATA": False,    # <!SDATA nbsp 160 msp 0x2003...>   TODO
            "setDcls": False,       # <!ENTITY % soup SET (i b tt)>     TODO
            "backslash": False,     # \n \xff \uffff                    TODO

            ### Case and Unicode
            "elementFold": "NONE",
            "entityFold": "NONE",
            "keywordFold": "NONE",
            "uNormHandler": "NONE", #                                   TODO
            "wsDef": "XML",         #                                   TODO
            "radix": ".",           # Decimal point choice              TODO
            "noC1":  False,         # No C1 controls                    TODO

            ### Other
            "piAttr": False,        # PI content is parsed like attributes. TODO
            "piAttrDcl": False,     # <!ATTLIST ?target ...>            TODO
            "nsSep": ":",           #                                   TODO
            "nsUsage": None,        # justone, global, noredef, regular TODO
        })

        if options:
            for k, v in options.items():
                setattr(self.options, k, v)

        if self.options.xsdType:
            for xsdt in AttrTypes.keys():
                if xsdt not in self.attrTypes: self.attrTypes[xsdt] = 1

        if rootPath:
            self.setupDocEntity(rootPath, encoding)
            self.parseTop()

    def SE(self, msg:str) -> None:
        """Deal with a syntax error.
        """
        raise SyntaxError(msg + " at \n$$$" + self.bufSample + "$$$")

    def doCB(self, typ:SaxEvent, *args) -> None:
        """Given an event type and its args, call the handler if any.
        """
        msg = ", ".join(f"{x}" for x in args)
        lg.info("%s: %s", typ, msg)
        if typ in self.handlers: self.handlers[typ](self, args)
        self.totEvents += 1

    def setupDocEntity(self, rootPath:str, encoding:str="utf-8") -> None:
        assert len(self.entStack) == 0
        if not os.path.isfile(rootPath):
            raise IOError(f"File not found: {rootPath}.")
        self.rootDef = EntityDef(space=EntSpace.GENERAL,
            name="_root", systemId=rootPath, encoding=encoding)
        self.rootFrame = EntityFrame(self.rootDef, encoding=encoding)
        self.entStack.append(self.rootFrame)

    def addEntity(self, eDef:EntityDef) -> None:
        tgt = self.spaces[eDef.space]
        if eDef.name in tgt:
            raise KeyError(f"{eDef.space} object already defined: '{eDef.name}'.")
        tgt[eDef.name] = eDef

    def findEntity(self, space:EntSpace, name:str) -> EntityDef:
        tgt = self.spaces[space]
        if name in tgt: return tgt[name]
        return None

    def expandPEntities(self, s:str) -> str:
        """Recursively expand parameter entity references in a string.
        But do it breadth-first.
        Fairly well protected against reference bombs.
        """
        totpasses = 0
        nestLevel = 0
        while "%" in s:
            if len(s) > self.options.MAXEXPANSION: raise ValueError(
                "Parameter entity expansion exceeds MAXEXPANSION (%d)."
                % (self.options.MAXEXPANSION))
            totpasses += 1
            s, n = re.subn(r"%([-_:.\w]+);", self.getParameterText, s)
            nestLevel += n
            # TODO: Hook up to isEntRefPermitted()!
            if nestLevel > self.options.MAXENTITYDEPTH:
                self.SE("Too many parameter entity substitutions, depth %d, count %d."
                    % (totpasses, nestLevel))
        return s

    def getParameterText(self, mat) -> str:
        peName = mat.group(1)
        if self.isOpen(EntSpace.PARAMETER, peName):
            self.SE(f"Parameter entity {peName} is already open.")
        try:
            peDef = self.parameterDefs[peName]
        except KeyError as e:
            raise KeyError(f"Unknown parameter entity '{peName}'.") from e
        if peDef.locType == LocType.LITERAL: return peDef.data
        with codecs.open(peDef.systemId, "rb", encoding=peDef.encoding) as pefh:
            return pefh.read()

    def isOpen(self, space:EntSpace, name:NMTOKEN_t) -> bool:
        eDef = self.findEntity(space, name)
        if eDef is None: return False
        for fr in self.entStack:
            if fr.eDef is eDef: return True
        return False

    def open(self, space:EntSpace, name:NMTOKEN_t) -> EntityFrame:
        """Open a new input source, generally an entity. Most entity-expansion
        security options happen here.
        """
        eDef = self.findEntity(space, name)
        if not eDef: raise KeyError(
            f"Unknown entity '{name}'.")
        if not self.isEntRefPermitted(eDef): return None
        lg.info("Opening entity '%s'.", name)
        ef = EntityFrame(eDef)
        self.entStack.append(ef)
        return ef

    def isEntRefPermitted(self, eDef:EntityDef) -> bool:
        """Implement some entity-expansion safety protocols.
        TODO: Should this skip the exceptions and just return False?
        """
        if self.isOpen(eDef.space, eDef.name):
            self.SE(f"Entity {eDef.name} is already open.")
        if self.depth >= self.options.MAXENTITYDEPTH:
            self.SE(f"Too much entity nesting, depth {self.depth}.")
        if (not self.options.extEntities
            and eDef.dataSource.systemId or eDef.dataSource.publicID):
            self.SE("Extnernal (PUBLIC and SYSTEM) entities are disabled.")
        if (not self.options.netEntities):
            sid = eDef.dataSource.systemId
            if "://" in sid and not sid.startswith("file://"):
                self.SE("Non-file URIs for SYSTEM identifiers are disabled.")
        # TODO Add limitations on local directory choice
        # TODO Add special case for XML 5 and HTML named
        return True

    def close(self) -> int:
        """Close the innermost open EntityFrame.
        """
        cf = self.curFrame
        if not cf: return False
        lg.info("Closing entity '%s'.", cf.eDef.name)
        cf.close()
        self.entStack.pop()
        return self.depth

    def closeAll(self) -> None:
        while (self.entStack):
            self.close()

    @property
    def curFrame(self) -> EntityFrame:
        if not self.entStack: return None
        return self.entStack[-1]

    @property
    def depth(self) -> int:
        return(len(self.entStack))

    def wholeLoc(self) -> str:
        buf = ""
        for i in reversed(range(0, self.depth)):
            buf += ("    %2d: Entity %-12s line %6d, file '%s'" %
                (i,
                self.entStack[i].eDef.name,
                self.entStack[i].lineNum,
                self.entStack[i].oeFilename))
        return(buf)

    ### Reading

    @property
    def buf(self) -> str:
        return self.curFrame.buf
    @property
    def bufPos(self) -> int:
        return self.curFrame.bufPos
    @bufPos.setter
    def bufPos(self, n:int) -> None:
        self.curFrame.bufPos = n
    @property
    def bufLeft(self) -> int:
        return self.curFrame.bufLeft
    @property
    def bufSample(self) -> str:
        preLen = min(80, self.bufPos)
        postLen = min(80, self.bufLeft)
        return (
            self.buf[self.bufPos-preLen:self.bufPos] +
            "^" +  # or "\uFE0E" +  # WHITE FROWNING FACE
            self.buf[self.bufPos:self.bufPos+postLen])

    # Forward small constructs to entity-frame-limited readers
    #
    def readConst(self, const:str, ss:bool=True, thenSp:bool=False) -> str:
        return self.curFrame.readConst(const, ss, thenSp)
    def readInt(self,  ss:bool=True, signed:bool=True) -> int:
        return self.curFrame.readInt(ss, signed)
    def readFloat(self,  ss:bool=True, signed:bool=True,
        specialFloats:bool=False) -> float:
        return self.curFrame.readFloat(
            ss=ss, signed=signed, specialFloats=specialFloats)
    def readName(self, ss:bool=True) -> str:
        return self.curFrame.readName(ss)
    def readRegex(self, regex:Union[str, re.Pattern],
        ss:bool=True, ignoreCase:bool=True) -> re.Match:
        return self.curFrame.readRegex(regex, ss, ignoreCase)
    def readToString(self, ender:str, consumeEnder:bool=True) -> str:
        return self.curFrame.readToString(ender, consumeEnder)
    def readSepComment(self, ss:bool=True) -> str:
        return self.curFrame.readSepComment(ss)

    def peek(self, n:int=1) -> str:
        return self.curFrame.peek(n)
    def consume(self, n:int=1) -> str:
        return self.curFrame.consume(n)
    def pushBack(self, s:str) -> None:
        return self.curFrame.pushBack(s)

    def topOff(self, n:int=None) -> bool:
        """Close until not at EOF, then top off first remaining frame.
        """
        if not n: n = self.bufSize
        while self.entStack:
            if self.curFrame.topOff(n) != EOF: return True
            self.close()
        return False

    def skipSpaces(self, allowComments:bool=False, allowParams:bool=False) -> bool:
        #crossEntityEnds:bool=False):  # TODO Implement stack!
        """Basically skip spaces, but at option also:
            * skip an embedded comment (for SGML not XML DTDs)
            * expand if we hit a parameter entity reference.
        """
        nFound = 0
        while (self.bufLeft):
            c = self.buf[self.bufPos]
            if c.isspace():
                self.bufPos += 1
                nFound += 1
            elif c == "-" and self.options.sgml and allowComments:
                com = self.readSepComment()
                if com:
                    self.bufPos += len(com)
                    # This event can occur mid-dcl....
                    self.doCB(SaxEvent.COMMENT, com)
                nFound += len(com)
            elif allowParams and c == "%":
                self.allowPE()
            else:
                break
            if self.bufLeft < self.bufSize>>2:
                self.topOff()
                if not self.entStack: break
        return nFound > 0

    def allowPE(self) -> None:
        """Used by skipSpaces and others when it's ok to have a parameter
        entity reference.
        """
        # skipspaces???? don't go circular
        if self.peek() != "%": return
        self.bufPos += 1
        pename = self.readName()
        if not pename:
            self.SE(f"Incomplete parameter entity reference name '{pename}').")
        if not self.consume() == ";":
            self.SE(f"Unterminated parameter entity reference to '{pename}'.")
        self.bufPos += 1
        if pename not in self.parameterDefs:
            self.SE(f"Unknown parameter entity '{pename}'.")
        self.open(space=EntSpace.PARAMETER, name=pename)
        self.entStack[-1].skipSpaces()
        return

    def readQLit(self, ss:bool=True, keepPunc:bool=False) -> str:
        """TODO: Who exands stuff inside qlits???? Do one pass at end?
        """
        if ss: self.skipSpaces(allowParams=True)
        openQ = self.peek()
        closeQ = None
        if openQ == "'" or openQ == '"':
            closeQ = openQ
        elif self.options.curlyQuote:
            # This isn't all the Unicode possibilities, just the main ones.
            if   openQ == "\u2018": closeQ = "\u2019"  # Curly single
            elif openQ == "\u201C": closeQ = "\u201D"  # Curly double
            elif openQ == "\u00AB": closeQ = "\u00BB"  # Double angle
        else:
            self.SE("Expected quoted string but found '{openQ}' ({ord(oenQ):04x}).")

        self.consume()
        dat = self.readToString(closeQ, consumeEnder=True)
        if dat is None:
            self.SE("Unclosed quoted string.")
        dat = self.expandPEntities(dat)
        if keepPunc: return openQ + dat + closeQ
        return dat

    def readNameGroup(self, ss:bool=False) -> List:
        """Allows and mix of [&|,] or space between names.
        This is slightly too permissive.
        This discard inter-name operators, so don't use for content models.
        """
        ngo = self.readConst("(", ss)
        if ngo is None: return None
        names = []
        while (True):
            self.skipSpaces(allowParams=True)
            name = self.readName()
            if name is None:
                self.SE("Expected a name in name group.")
            names.append(name)
            self.skipSpaces(allowParams=True)
            c = self.peek()
            if c == ")": break
            if c in "|&,": continue
        return names

    def readNameOrNameGroup(self, ss:bool=False) -> List:
        """Such as: <!ELEMENT...
            div
            (h1 | h2 | h3)
            (%soup;)
        """
        if ss: self.skipSpaces(allowParams=True)
        c = self.peek(1)
        if self.options.groupDcl and c == "(":
            names = self.readNameGroup(ss=True)
        else:
            names = [ self.readName() ]
        if not names: return None
        return names

    ### Readers for top-level DTD constructs
    #
    def readXmlDcl(self) -> (str, str):                         # <?xml ...?>
        # This is nearly the only case where ss=False.
        if not self.readConst("<?xml", ss=False, thenSp=True): return None
        props = {}
        while (True):
            aname, avalue, _ = self.readAttr(ss=True)
            if aname is None: break
            if aname in ("version", "encoding", "standalone"):
                props[aname] = avalue
            elif aname in self.options:
                self.options[aname] = avalue
            else:
                self.SE("Unrecognized item '{aname}' in XML DCL.")
        if not self.readConst("?>", ss=True):
            self.SE(f"Unterminated XML DCL, read {repr(props)}.")
        self.doCB(SaxEvent.XMLDCL, *props)
        return props

    def readPI(self) -> (str, Union[str, Dict]):                # <?tgt data??>
        pio = self.readConst("<?", ss=True)
        if pio is None: return None, None
        piTarget = self.readName()
        if self.options.piAttr:
            piData = self.readAttrs(ss=True)
            if not self.readConst("?>", ss=True): self.SE("Unterminated PI.")
        else:
            piData = self.readToString("?>", consumeEnder=True)
            if piData is None: self.SE("Unterminated PI.")
        return piTarget, piData

    def readComment(self) -> str:                               # <!-- txt -->
        como =  self.readConst("<!--", ss=True)
        if como is None: return None
        comData = self.readToString("-->", consumeEnder=True)
        if comData is None:
            self.SE("Unterminated Comment.")
        return comData

    def readNotationDcl(self) -> (str, str, str):               # <!NOTATION>
        if self.readConst("<!NOTATION", thenSp=True) is None: return None
        name = self.readName(ss=True)
        publicId, systemId = self.readLocation()
        if publicId is None: self.SE(
            f"Expected PUBLIC or SYSTEM identifier at {self.bufSample}.")
        if not self.readConst(">"): self.SE(
            "Expected '>' for NOTATION dcl at {self.bufSample}.")
        return (name, publicId, systemId)

    def readLocation(self) -> (str, Union[List, str]):          # PUBLIC/SYSTEM
        """The PUBLIC "" "", or SYSTEM "" syntax.
        Note: This returns the SYSTEM ID as a list iff 'multiPath' is on.
        """
        publicId = ""
        systemIds = []
        if self.readConst("PUBLIC", ss=True):
            publicId = self.readQLit(ss=True)
            systemIds = [ self.readQLit(ss=True) ]
        elif self.readConst("SYSTEM"):
            systemIds = [ self.readQLit(ss=True) ]
            if self.options.multiPath:
                while (s := self.readQLit(ss=True)):
                    systemIds.append(s)
        else:
            return None, None
        if self.options.multiPath: return (publicId, systemIds)
        return (publicId, systemIds[0])

    def readElementDcl(self) -> (                               # <!ELEMENT>
        List, bool, bool, List, List, List):
        """TODO Should these all do the construction, or leave to caller?
        """
        if self.readConst("<!ELEMENT", thenSp=True) is None: return None
        omitStart = omitEnd = False

        # TODO Switch to readNameOrNameGroup()?
        if self.options.groupDcl and self.peek() == "(":
            names = self.readNameGroup()
        else:
            names = [ self.readName() ]
        if names is None:
            self.SE("Expected element name or group at {self.bufSample}.")

        if self.options.oflag:
            omitStart = omitEnd = False
            # Doesn't handle PE refs in mid-omitFlags.
            mat = self.readRegex(r"\s+([-O])\s+([-0])")
            if mat:
                omitStart = mat.group(1) == "O"
                omitEnd = mat.group(2) == "O"

        model = self.readModel()
        if model is None: self.SE(
            "Expected model or declared content for {names}.")

        inclusions = exclusions = None
        if self.options.mixins:
            if self.peek() == "+":
                self.consume()
                mixins = self.readNameGroup()
                if mixins is None: self.SE(
                    "Expected name group after '+' for inclusions.")
                inclusions = mixins
            if self.peek() == "-":
                self.consume()
                mixins = self.readNameGroup()
                if mixins is None: self.SE(
                    "Expected name group after '-' for exclusions.")
                exclusions = mixins

        if not self.readConst(">"): self.SE("Expected '>' for ELEMENT dcl.")
        return (names, omitStart, omitEnd, model, inclusions, exclusions)

    def readModel(self) -> Model:                               # EMPTY | (...)
        """Read a parenthesized content model OR a declared content keyword.
        """
        mat = self.readRegex(r"#?\w+\b", ss=True)
        if mat:
            try:
                contentType = ContentType(mat.group().lstrip("#"))
                return Model(contentType=contentType)
            except ValueError:
                self.SE("Unrecognized declared content keyword '{mat.group}'.")
        mtokens = self.readModelGroup(ss=True)
        if mtokens is None: return None
        return Model(tokens=mtokens)

    def readModelGroup(self, ss:bool=True) -> List[str]:        # ( x | Y | z )
        """Extract and return a list of tokens from a balanced paren group
        like a content model, including sequence and repetition operators.
        Handily, you can't have parens as escaped data in there.
        Does not make an AST (see readModel(), which construct a Model object).
        TODO PE refs?
        """
        if ss: self.skipSpaces()
        if not self.readConst("("): return None
        tokens = [ "(" ]
        depth = 1
        while (True):
            self.skipSpaces(allowParams=True)
            c = self.peek()
            if curToken := self.readName():
                tokens.append(curToken)
            elif self.readConst("#PCDATA"):
                tokens.append("#PCDATA")
            elif c in "(":
                self.consume()
                tokens.append(c); depth += 1
            elif c == ")":
                self.consume()
                tokens.append(c); depth -= 1
                if depth == 0: break
            elif c in "|,&":
                self.consume()
                tokens.append(c)
            elif c in "+?*":
                self.consume()
                tokens.append(c)
            elif self.options.repBrace and (rep := self.readRepIndicator()):
                tokens.append(rep)
            else:
                self.SE(f"Unexpected character '{c}' in model at {tokens}.")
        if rep := self.readRegex(r"[*?+]", ss=True):
            tokens.append(rep.group())
        elif self.options.repBrace and (rep := self.readRepIndicator()):
            tokens.append(rep)
        return tokens

    def readRepIndicator(self, ss:bool=True) -> RepType:        # *|+|?|{}
        """The repetition operator (including the {} form extension).
        """
        if ss: self.skipSpaces()
        c = self.peek()
        if c not in "*?+{":
            return None
        self.consume()
        lims = [ 1, 1 ]
        if c == "*": lims = [ 0, -1 ]
        elif self.readConst("?"): lims = [ 0, 1 ]
        elif self.readConst("+"): lims = [ 0, -1 ]
        elif c == "{":
            if not self.options.repBrace:
                raise SyntaxError("repBraces extension is not enabled.")
            minO = self.readInt(ss=True)
            self.readConst(":", ss=True)
            maxO = self.readInt(ss=True)
            self.readConst("}", ss=True)
            lims = [ minO, maxO ]
        return RepType(*lims)

    def readAttListDcl(self) -> (List, Dict):                   # <!ATTLIST>
        """Example:
            <!ATTLIST para  class   NMTOKENS    #IMPLIED
                            level   NUMTOKEN    #REQUIRED
                            thing   (b|c|d)     "D"
                            spam    ENTITY      FIXED "chap1">
        """
        if self.readConst("<!ATTLIST", thenSp=True) is None: return None
        self.skipSpaces()
        if self.options.groupDcl and self.peek() == "(":
            names = self.readNameGroup()
        else:
            names = [ self.readName() ]

        atts = {}
        while (True):
            attDftKwd = dftVal = None
            if self.readConst(">", ss=True): break
            attName = self.readName(ss=True)
            if attName is None:
                self.SE(f"Expected attribute name in ATTLIST for {names}.")

            self.skipSpaces()
            if self.peek() == "(":
                attType = self.readModelGroup(ss=True)  # TODO: No nesting....
            elif not (attType := self.readName(ss=True)): self.SE(
                "Expected attribute type or enum-group.")
            elif attType not in self.attrTypes: self.SE(
                f"Unknown type {attType} for attribute {attName}.")

            self.skipSpaces(allowParams=True)
            c = self.peek()
            if c == "#":
                attDftKwd = self.consume()
                attDftKwd += self.readName() or ""
                if attDftKwd not in self.attrDefaults: self.SE(
                    f"Unknown attribute default {attDftKwd} for {attName}.")
                if attDftKwd == "#FIXED":
                    dftVal = self.readQLit(ss=True)
            elif c in '"\'':
                dftVal = self.readQLit()
            atts[attName] = ( attName, attType, attDftKwd, dftVal)

        self.skipSpaces()
        # TODO Allocate AttlistDef
        return names, atts

    def readEntityDcl(self) -> Tuple:                           # <!ENTITY>
        """Examples:
            <!ENTITY % foo "(i | b* | (tt, lang0))*">
            <!ENTITY XML "Extensible Markup Language">
            <!ENTITY chap1 PUbLIC "-//foo" "/tmp/chap1.xml">
            <!ENTITY if1 SYSTEM "/tmp/fig1.jpg" NDATA jpeg>
            <!ENTITY bull SDATA "&#x2022;">
        """
        if self.readConst("<!ENTITY", thenSp=True) is None: return None
        self.skipSpaces()
        isParam = (self.readConst("%") is not None)
        name = self.readName(ss=True)
        publicId = systemId = lit = ""
        publicId, systemId = self.readLocation()
        if publicId is None:
            lit = self.readQLit(ss=True)

        notn = None
        if self.readConst("NDATA", ss=True):
            notn = self.readName(ss=True)
            if notn is None: self.SE("Expected notation name after NDATA.")

        self.skipSpaces()
        if not self.readConst(">"): self.SE("Expected '>' for ENTITY dcl.")
        return (name, isParam, publicId, systemId, lit, notn)


    ###########################################################################
    # Readers for main document content
    #
    def readStartTag(self, ss:bool=True) -> (str, Dict, bool):
        """Returns a 3-tuple of:
            element type name
            dict of attributes
            whether it used empty-element syntax
        """
        if not self.readConst("<", ss): return None, None, None
        if not (name := self.readName(ss)):
            self.SE("Expected name in start-tag.")
        if self.options.elementFold: name = name.upper()

        attrs = self.readAttrs(ss=ss)

        empty = False
        if self.readConst("/>", ss): empty = True
        elif self.readConst(">", ss): empty = False
        else: self.SE("Unclosed start-tag for '{aname}'.")
        self.doCB(SaxEvent.START, name, attrs)
        if empty: self.doCB(SaxEvent.END, name)
        return name, attrs, empty

    def readAttrs(self, ss:bool=True) -> OrderedDict:
        attrs = OrderedDict()
        while (True):
            aname, avalue, _bang = self.readAttr(ss=ss)  # TODO Implement bang
            if aname is None: break
            if self.options.elementFold: aname = aname.upper()
            # TODO Fold and normalize and cast value per schema
            attrs[aname] = avalue  # Move to caller or pass in elem name?
            #if bang:
            #    if (name, aname) in self.bangAttrs:
            #        self.SE("!= previously used for '{aname}@{aname}'.")
            #    self.bangAttrs[(name, aname)] = avalue
        return attrs

    def readAttr(self, ss:bool=True, keepPunc:bool=False) -> (str, str, bool):
        """Used in start-tags and also in XML DCL.
        Supports optional extensions such as curly or unquoted values,
        boolean shorthand, and "!=" to set an enduring default.
        Extensions:
            <p +border -foo id=spam_37 zork!="1"
        Returns: name, value, and 'bang' -- bang is True iff we got "!=".
        """
        #lg.warning(f"readAttr, ss={ss}, buf starts '{self.peek(10)}'.")
        if ss: self.skipSpaces()
        #lg.warning(f"readAttr, after ss, buf starts '{self.peek(10)}'.")
        bang = False
        if self.options.booleanAttr and self.peek() in "+-":
            which = self.consume()
            if not (aname := self.readName(ss)):
                self.SE("Expected name after +/- for boolean attr.")
            lg.warning("Got boolean attr prefix '%s' for '%s'.", which, aname)
            return (aname, "1" if (which == "+") else "0", False)

        # TODO Maybe do case-folding here instead of in readStartTag()?
        aname = self.readName(ss)
        if not aname:
            return (None, None, bang)
        #lg.warning(f"Attr name '{aname}'.")

        if self.options.bangAttr and self.readConst("!=", ss):
            bang = True
        elif self.readConst("=", ss):
            bang = False
        else:
            self.SE("Expected '=' after attribute name.")

        avalue = self.readQLit(ss, keepPunc)
        if avalue:
            #lg.warning(f"Attr value is qlit '{avalue}' ({type(avalue)}).")
            return (aname, avalue, bang)
        if self.options.unQuotedAttr and (avalue := self.readName(ss)):
            lg.warning("Attr value for %s is unquoted (%s).", aname, avalue)
            return (aname, avalue, bang)

        return (None, None, bang)

    def readEndTag(self, ss:bool=True) -> str:
        if not self.readConst("</", ss): return None
        if not (name := self.readName(ss)):
            if not self.options.emptyEnd:
                self.SE("Expected name in end-tag.")
            else:
                name = self.tagStack[-1]
        if not self.readConst(">", ss):
            self.SE("Unclosed end-tag for '{aname}'.")
        if self.options.elementFold: name = name.upper()
        self.doCB(SaxEvent.END, name)
        return name

    def readCDATA(self, ss:bool=True) -> str:
        """This recognizes the full set of SGML keywords, but they're
        not fully implemented yet.
        """
        MSKeys = {
            "CDATA": 1,
            "RCDATA": 2,
            "IGNORE": 3,
            "INCLUDE": 4,
            "TEMP": 5,
        }
        if not self.readConst("<![", ss):
            return None
        elif self.readConst("CDATA["):  # TODO Case?
            # In XML these aren't nestable.
            data = self.readToString("]]>")
            if not data: self.SE("Unclosed CDATA section.")
            self.doCB(SaxEvent.CDATASTART)
            self.doCB(SaxEvent.CHAR, data)
            self.doCB(SaxEvent.CDATAEND)
            return data
        elif not self.options.markedSectionTypes:
            self.SE("Found '<![' but not '<![CDATA['.")
        else:
            # TODO Unfinished. rcdata is easy; include/temp are a pain
            if not (keys := self.readToString("[")):
                self.SE("Unfinished marked section start.")
            topKey = ""
            for key in self.expandPEntities(keys).split():
                if not topKey or MSKeys[key] < MSKeys[topKey]: topKey = key
            self.msStack.append(topKey)
            if topKey == "IGNORE":
                self.readToString("]]>", consumeEnder=True)
                # self.readToAny([ "<![", "]]>" ], consumeEnder=True)
            elif topKey == "CDATA":
                data = self.readToString("]]>", consumeEnder=True)
                self.doCB(SaxEvent.CDATASTART)
                self.doCB(SaxEvent.CHAR, data)
                self.doCB(SaxEvent.CDATAEND)
            else:
                raise NSuppE("Unsupported SGML MS Keyword {topKey}")
            self.msStack.pop()

    def parseTop(self) -> None:
        """Parse the start of an XML document, up through the declaration
        subset (the stuff between [] in the DOCTYPE). Return before actually
        parsing the document instance (caller can do parseDocument() for that).

        TODO Fix API so can use as just a normal parse/parse_string.
        """
        #import pudb; pudb.set_trace()
        self.doCB(SaxEvent.START)
        _props = self.readXmlDcl()

        if e := self.readConst("<!DOCTYPE", ss=True, thenSp=True):  # DOCTYPE
            doctypeName = self.readName(ss=True)
            if doctypeName is None:
                self.SE("Expected document type name in DOCTYPE.")
            self.skipSpaces()
            publicId, systemId = self.readLocation()
            self.skipSpaces()
            if self.peek(1) == "[":
                self.sawSubsetOpen = True
                self.consume(1)
            self.doCB(SaxEvent.DOCTYPE, doctypeName, publicId, systemId)

        while True:                                                 # SUBSET
            self.skipSpaces(allowParams=True)
            p = self.peek(1)
            #lg.info("AT %s", p)
            if p is None:
                self.SE("Unexpected EOF in DOCTYPE.")
            elif p == "]":
                self.consume()
                if self.readConst(">", ss=True):
                    self.consume()
                    self.doCB(SaxEvent.DOCTYPEFIN)
                    return
                self.SE("Expected '>' to end DOCTYPE.")
            elif p == "<":
                if e := self.readComment():
                    self.doCB(SaxEvent.COMMENT, e)
                elif e := self.readElementDcl():
                    self.doCB(SaxEvent.ELEMENTDCL, e)
                elif e := self.readAttListDcl():
                    # TODO by attr?
                    self.doCB(SaxEvent.ATTLISTDCL, e)
                elif e := self.readEntityDcl():
                    self.doCB(SaxEvent.ENTITYDCL, e)
                elif e := self.readNotationDcl():
                    self.doCB(SaxEvent.NOTATIONDCL, e)
                elif e := self.readPI():
                    self.doCB(SaxEvent.PROC, e)
                else:
                    self.SE("Unexpected content is DOCTYPE after '<'.")
            else:
                self.SE(f"Expected ']' or '<' in DOCTYPE, not '{p}'.")

        self.doCB(SaxEvent.FINAL)


    ###########################################################################
    # This seems to be all we need atop the DTD/entity parser, to do documents.
    #
    @property
    def inRCDATA(self) -> bool:
        return self.msStack and self.msStack[-1] == "RCDATA"

    def parseDocument(self) -> None:
        """Starts after parseTop.
        """
        buf = ""
        while c := self.peek(1) is not None:
            if c not in "&<":
                buf += self.consume()
                continue
            if buf:
                self.doCB(SaxEvent.CHAR, buf)
                buf = ""
            if c == "&":
                self.consume()
                if self.readConst("#"):
                    pass  # TODO
                elif name := self.readName(ss=False):
                    if not self.readConst(";"):
                        self.SE(f"Expected ';' after '{name}'.")
                    if self.options.entityFold: name = name.upper()
                    if self.options.charEnt and name in name2codepoint:
                        buf += name2codepoint[name]
                    else:
                        self.open(EntSpace.GENERAL, name)
                else:
                    self.SE("Expected '#' or name after '&'.")
            elif c == "<" and not self.inRCDATA:
                self.consume()
                c2 = self.peek()
                if c2 == "/":                               # ENDTAG
                    e = self.readEndTag()
                    if not e: self.SE("Expected name after '</'.")  # TODO </>
                    if self.options.elementFold: e = e.upper()
                    if self.options.olist:
                        foundAt = None
                        i = 0
                        for i in reversed(range(len(self.tagStack))):
                            if self.tagStack == e:
                                foundAt = i
                                break
                        if foundAt is not None:
                            del self.tagStack[i]
                        else: self.SE(
                            f"Element to close not found in open-list: '{e}'.")
                    else:
                        if not self.tagStack or e != self.tagStack[-1]: self.SE(
                            "End-tag for {e}, but {self.tagStack[-1]} is current.")
                        self.tagStack.pop()
                    self.doCB(SaxEvent.END, e)
                elif c2 == "!":                             # COMMENT, CDATA,...
                    # For SGML we'd have to check for USEMAP to
                    if self.peek(3) == "!--":
                        e = self.readComment()
                        if e: self.doCB(SaxEvent.COMMENT, e)
                    elif self.peek(2) == "![":
                        e = self.readCDATA()
                        if e:
                            self.doCB(SaxEvent.CDATASTART)
                            self.doCB(SaxEvent.CHAR, e or "")
                            self.doCB(SaxEvent.CDATAEND)
                elif c2 == "?":                             # PI
                    if not (e := self.readPI()):
                        self.SE("Expected target and data after '<?'.")
                    self.doCB(SaxEvent.PROC, *e)
                elif self.options.restart and self.peek(2) == "|>":
                    if not self.tagStack:
                        self.SE("Can't re-start with nothing open.")
                    e = self.tagStack[-1]
                    self.doCB(SaxEvent.END, e)
                    self.doCB(SaxEvent.START, e)
                elif c2 in "-+":                            # Suspend/resume
                    if not self.options.suspend:
                        self.SE("<+ and <- only allowed with 'suspend' extension.")
                    else:
                        raise NSuppE
                else:                                       # STARTTAG
                    e, attrs, emptySyntax = self.readStartTag()
                    if not (e): self.SE("Unexpected characters after '<'.")
                    #if self.doctype:
                    #    self.doctype.applyDefaults(e, attrs)  # TODO Attr Defaults
                    self.doCB(SaxEvent.START, e, attrs)
                    self.tagStack.append(e)
                    if emptySyntax:
                        self.doCB(SaxEvent.END, e)
                        self.tagStack.pop()

        if self.tagStack:
            self.SE(f"Unclosed elements at EOF: {self.tagStack}.")
        self.doCB(SaxEvent.FINAL)
        return


###############################################################################
#
#ifh = codecs.open("sample.dtd", "rb", encoding="utf-8")
#rawData = ifh.read()
pdt = StackReader("sample.dtd", encoding="utf-8")

print("Done.")
