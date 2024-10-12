#!/usr/bin/env python3
#
# EntityManager.py
# multiXml written 2011-03-11 by Steven J. DeRose.
# Broken out from multiXML.py, 2013-02-25.
#
#pylint: disable=W1201
#
import os
import sys
import codecs
import re
from enum import Enum
import logging
from typing import Union, List

#import html
#from html.entities import codepoint2name

from xmlstrings import XmlStrings as XStr

lg = logging.getLogger("EntityManager")

__metadata__ = {
    "title"        : "EntityManager",
    "rightsHolder" : "Steven J. DeRose",
    "creator"      : "http://viaf.org/viaf/50334488",
    "type"         : "http://purl.org/dc/dcmitype/Software",
    "language"     : "Python 3.7",
    "created"      : "2011-03-11",
    "modified"     : "2024-10-11",
    "publisher"    : "http://github.com/sderose",
    "license"      : "https://creativecommons.org/licenses/by-sa/3.0/"
}
__version__ = __metadata__['modified']


descr = """
=Description=

''(unfinished)''

EntityManager.py (Python)

Manage Entity and Notation definitions for an XML parser, including
reading with respect to them.

=Usage=

    from entitymanager import EntityManager
    em = EntityManager()
    em.readDtd(path)
    em.openEntity()
    ...read...


=Methods=

* ''appendEntityPath''(path)

Add '''path''' to the end of the list of directories, in which to search
for external entities. First added, is first searched.

* ''entityDepth''()

Returns the number of open entities.


=Known bugs and limitations=


=Related commands=


=History=

* 2011-03-11 `multiXml` written by Steven J. DeRose.
* 2013-02-25: EntityManager broken out from `multiXML.py`.
* 2015-09-19: Close to real, syntax ok, talks to `multiXML.py`.
* 2020-08-27: New layout.
* 2022-03-11: Lint. Update logging.
* 2024-08-09: Split Manager from Reader. Use for dtdParser.


=To do=

* Get it running.


=Rights=

Copyright 2011-03-11 by Steven J. DeRose. This work is licensed under a
Creative Commons Attribution-Share-alike 3.0 unported license.
For further information on this license, see
[https://creativecommons.org/licenses/by-sa/3.0].

For the most recent version, see [http://www.derose.net/steve/utilities]
or [https://github.com/sderose].


=Options
"""

def allXmlChars(s:str) -> bool:
    """Just determine if all the individual chars are allowed.
    """
    for c in s:
        n = ord(c)
        if (n > 0x1FFFF or n > sys.maxunicode): return False
        if (n < 0x20 and c not in [ "\t", "\r", "\n" ]): return False
    return True

class LocType(Enum):
    LITERAL = 1
    SYSTEM = 2
    PUBLIC = 3

class ParseType(Enum):
    PARSED = 1
    CDATA = 2
    RCDATA = 3
    NDATA = 4

class SpaceType(Enum):
    GENERAL = 1
    PARAMETER = 2
    NOTATION = 3
    SDATA = 4

EOF = -1


###############################################################################
class EntityDef:
    """Defining information re. a single entity or notation.
    We consider general ents, parameter ents, notations, and sdata ents
    all to be sub-spaces of the same notion.
    """
    def __init__(self,
        space:SpaceType,
        name:str,
        parseType:ParseType=ParseType.PARSED,
        publicId:str=None, systemId:str=None,  encoding:str="utf-8",
        data:str=None,
        notationName:str=None
        ):
        assert isinstance(space, SpaceType)
        assert XStr.isXmlName(name)
        assert isinstance(parseType, ParseType)
        if notationName: assert XStr.isXmlName(notationName)

        self.space = space
        self.name = name
        self.parseType = parseType
        if publicId: self.locType = LocType.PUBLIC
        elif systemId: self.locType = LocType.SYSTEM
        else: self.locType = LocType.LITERAL

        self.publicId = publicId
        self.systemId = systemId
        self.encoding = encoding
        self.data = data
        self.notationName = notationName

        if (self.locType == LocType.LITERAL):
            self.path = None
        else:
            self.path = self.findLocalPath()

    def findLocalPath(self) -> str:
        """Catalog, $ENTITY_PATH, etc.
        TODO: how to access pathlist or catalog?
        """
        if (not self.systemId):
            raise IOError("No system ID for %s." % (self.name))
        if (os.path.isfile(self.systemId)): return self.systemId
        if ("ENTITY_PATH" in os.environ):
            epaths = os.environ["ENTITY_PATH"].split(";")
            for epath in epaths:
                cand = os.path.join(epath, self.systemId)
                if (os.path.isfile(cand)): return cand
        raise IOError("No file found for %s (systemId %s)." % (self.name, self.systemId))


###############################################################################
#
class EntityFrame:
    """Used by EntityManager for one currently-open entity.
    TODO: How best to signal EOF on the current entity?

    Readers in here will not go past frame EOF, or expand any entities.
    So that's for things like name tokens, reserved words, single delimiters,
    qlits, comments,... If they fail to match, they should return None and
    not move the input cursor.
    """
    def __init__(self, eDef:EntityDef, encoding:str="utf-8"):
        self.eDef = eDef
        self.encoding = encoding
        self.ifh = None
        self.buf = ""
        self.bufPos = 0
        self.lineNum = 0
        self.offset = 0
        if (self.eDef.literal):
            self.buf = self.eDef.literal  # TODO Copy?
        elif (self.eDef.path):
            self.ifh = codecs.open(self.eDef.path, "rb", self.eDef.encoding)
            self.buf = self.ifh.read()

    def close(self):
        if (self.ifh): self.ifh.close()
        self.buf = None

    @property
    def bufLeft(self):
        return len(self.buf) - self.bufPos

    def peek(self, n:int=1):
        """Return the next n characters (or fewer if EOF is coming),
        without actually consuming them.
        """
        if self.bufLeft < n: self.topOff()
        if self.bufLeft < n: return None
        return self.buf[self.bufPos:self.bufPos+n]

    def consume(self, n:int=1):
        """Same as peek except the characters really ARE consumed.
        But only if there are at least n available.
        """
        if self.bufLeft < n: self.topOff(n)
        if self.bufLeft < n: return None
        rc = self.buf[self.bufPos:self.bufPos+n]
        self.bufPos += n
        return rc

    def pushBack(self, s:str):
        """You can push back as much as memory permits. But if what you push
        back isn't what you read, that may not be good. Real file reading
        will pick up once the buffer (including the pushBack) is exhausted.
        """
        n = len(s)
        self.buf = s + self.buf[self.bufPos:]
        self.bufPos = 0
        self.offset -= n
        self.lineNum -= s.count('\n')

    def topOff(self, n:int=1000) -> bool:
        """We do not top off across entity boundaries here.
        Read more data (is there is any), to get at least n available.
        If EOF happens before n, buf ends up short.
        If EOF happens and there's nothing in buf, that's really EOF.
        """
        if not self.ifh:
            if self.bufPos >= len(self.buf):
                self.buf = ""
                return EOF

        self.buf = self.buf[self.bufPos:]
        self.bufPos = 0
        if len(self.buf) < n:
            newChars = self.ifh.read(n)
            self.lineNum += newChars.count('\n')
            self.offset += len(newChars)
            self.buf += newChars
        if not self.buf:
            self.ifh.close()
            return False  # EOF
        return True

    def skipSpaces(self, allowComments:bool=True):
        while True:
            if self.bufLeft < 1:
                self.topOff()
                if not self.bufLeft: return EOF
            if self.buf[self.bufPos] in " \t\r\n":
                self.bufPos += 1
            elif allowComments and self.peek(2) == "--":
                self.consume(2)
                self.readToString("--")
            else:
                return True

    def readConst(self, const:str, ss:bool=True):
        if ss: self.skipSpaces()
        if not self.buf[self.bufPos:].startswith(const): return None
        self.bufPos += len(const)
        return const

    def readName(self, ss:bool=True) -> str:
        """TODO: What if we're at a % ref?
        TODO: Add options to allow/require initial "#"
        """
        if ss: self.skipSpaces()
        mat = re.match(XStr._xmlName, self.buf[self.bufPos:])
        if not mat: return None
        self.bufPos += len(mat.group(1))
        return mat.group(1)

    def readSepComment(self, ss:bool=True):
        """Read a comment that's just the --...-- part.
        """
        if ss: self.skipSpaces()
        mat = re.match(r"--([^-]|-[^-])+--", self.buf[self.bufPos:])
        if not mat: return None
        self.bufPos += len(mat.group(1))
        return mat.group(1)

    def readQLit(self, ss:bool=True, keepPunc:bool=False) -> str:
        # allowParams:bool=True,  # TODO ???
        if ss: self.skipSpaces()
        mat = re.match(r"'[^']*'|\"[^\"]*\"", self.buf[self.bufPos:])
        if (mat is None): return None
        self.bufPos += len(mat.group(1))
        return mat.group(1) if keepPunc else mat.group(1)[1:-1]

    def readQLitOrName(self, ss:bool=True) -> str:
        if ss: self.skipSpaces()
        rc = self.readQLit(ss)
        if rc is not None: return rc
        rc = self.readName()
        if rc is not None: return rc
        return None

    def readRegex(self, regex:Union[str, re.Pattern], ss:bool=True,
        ignoreCase:bool=True) -> re.Match:
        """Check if the regex matches immediately. If so, return the match object
        (so captures can be distinguished) and consume the matched text.
        If not, return None and consume nothing.
        """
        if ss: self.skipSpaces()
        mat = re.match(regex, self.buf[self.bufPos:], flags=re.I if ignoreCase else 0)
        if (not mat): return None
        self.bufPos += len(mat.group())
        return(mat)

    def readToString(self, s:str, consumeEnder:bool=True) -> str:
        """Unlike the above, this one doesn't leave things unchanged
        if we fail -- because failure means we hit EOF without ever
        finding the string. So this shouldn't be tried as one of
        several options for what comes next. Rather, it's for where you
        really, really have to have some stuff ended by this thing.
        Also doesn't know about quoted cases of the thing that shouldn't count.
        """
        rbuf = ""
        while True:
            if self.bufLeft < 1:
                self.topOff()
                if not self.bufLeft: return None
            where = self.buf.find(s, self.bufPos)
            if (where >= 0):
                rbuf += self.buf[self.bufPos:where]
                moveTo = where + (len(s) if consumeEnder else 0)
                self.buf = self.buf[moveTo:]
                self.bufPos = 0
                return rbuf
            rbuf += self.buf[self.bufPos:]
            self.buf = ""
            self.bufPos = 0
        return None  # TODO Notify EOF; Also return what we did get?


###############################################################################
#
class StackReader(EntityFrame):
    """Keep dictionaries of entities and notations, and a stack of
    open ones being read. Support very basic read operations (leave the
    fancy stuff for a subclass to add).
    """
    def __init__(self, rootPath:str, encoding:str="utf-8"):
        super().__init__(rootPath, encoding)
        self.entPath    = []    # dirs to look in
        self.generalDefs = {}
        self.parameterDefs = {}
        self.notationDefs = {}
        self.sdataDefs = {}

        self.spaces = {
            SpaceType.GENERAL: self.generalDefs,
            SpaceType.PARAMETER: self.parameterDefs,
            SpaceType.NOTATION: self.notationDefs,
            SpaceType.SDATA: self.sdataDefs
        }

        self.entStack = []
        self.totLines = 0       # overall lines processed
        self.totChars = 0       # overall chars processed

        self.sgml = False

        if rootPath:
            if not os.path.isfile(rootPath):
                raise IOError(f"File not found: {rootPath}.")
            self.rootEDef = EntityDef(space=SpaceType.GENERAL,
                name="#root", systemId=rootPath, encoding=encoding)
            self.entStack.append(self.rootEDef)

        self.MAXEXPANSION = 1 << 20
        self.MAXSUBS = 1000

    def addEntity(self, eDef:EntityDef) -> None:
        tgt = self.spaces[eDef.space]
        if eDef.ename in tgt:
            raise KeyError(f"{eDef.space} object already defined: '{eDef.name}'.")
        tgt[eDef.ename] = eDef

    def findEntity(self, space:SpaceType, ename:str) -> EntityDef:
        tgt = self.spaces[space]
        if ename in tgt: return tgt[ename]
        return None

    def expandPEntities(self, s:str):
        """Recursively expand parameter entity references in a string.
        But do it breadth-first.
        Fairly well protected against reference bombs.
        """
        totpasses = 0
        totsubs = 0
        while "%" in s:
            if len(s) > self.MAXEXPANSION: raise ValueError(
                "Parameter entity expansion exceeds MAXEXPANSION (%d)."
                % (self.MAXEXPANSION))
            totpasses += 1
            s, n = re.subn(r"%([-_:.\w]+);", self.getParameterText, s)
            totsubs += n
            if (totsubs > self.MAXSUBS): raise SyntaxError(
                "Too many parameter entity substitutions, depth %d, count %d."
                    % (totpasses, totsubs))
        return s

    def getParameterText(self, mat):
        peName = mat.group(1)
        if self.isOpen(SpaceType.PARAMETER, peName): raise SyntaxError(
            "Parameter entity {peName} is already open.")
        try:
            peDef = self.parameterDefs[peName]
        except KeyError as e:
            raise KeyError(f"Unknown parameter entity '{peName}'.") from e
        if peDef.locType == LocType.LITERAL: return peDef.data
        with codecs.open(peDef.systemId, "rb", encoding=peDef.encoding) as pefh:
            return pefh.read()

    def isOpen(self, space, eName) -> bool:
        eDef = self.findEntity(space, eName)
        if (eDef is None): return False
        for fr in self.entStack:
            if fr.eDef is eDef: return True
        return False

    def open(self, space:SpaceType, ename:str) -> EntityFrame:
        eDef = self.findEntity(space, ename)
        if not eDef: raise KeyError(
            f"Unknown entity '{ename}'.")
        if self.isOpen(space, ename): raise SyntaxError(
            "Entity {peName} is already open.")
        ef = EntityFrame(eDef)
        self.entStack.append(ef)
        return ef

    def close(self) -> int:
        """Close the innermost open EntityFrame.
        """
        cf = self.curFrame
        if not cf: return False
        lg.info("Closing entity '%s'." % cf.eDef.ename)
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

    # The basic peek and consume just have the current frame do it,
    # except that they call our stack-aware topOff first.
    #
    def peek(self, n:int=1) -> str:
        """Return the next n characters (or fewer if EOF is coming),
        without actually consuming them.
        """
        if self.bufLeft < n: self.topOff()
        return self.curFrame.peek(n)

    def consume(self, n:int=1) -> str:
        """Same as peek except the characters really ARE consumed.
        But only if there are at least n available.
        """
        if self.bufLeft < n: self.topOff(n)
        return self.curFrame.consume(n)

    def pushBack(self, s:str) -> None:
        return self.curFrame.pushBack(s)

    def topOff(self, n:int=1000) -> bool:
        while self.entStack:
            if self.curFrame.topOff(n) != EOF: return
            self.curFrame.close()
            self.close()

    def skipSpaces(self, allowComments:bool=True, allowParams:bool=True):
        #crossEntityEnds:bool=False):  # TODO Implement stack!
        """Basically skip spaces, but at option, also:
            * skip a comment
            * expand if we hit a parameter entity reference.
        """
        nFound = 0
        while (self.bufPos < len(self.buf)):
            c = self.buf[self.bufPos]
            if c.isspace():
                self.bufPos += 1
                nFound += 1
            elif (allowComments and c == "-"):
                com = self.readSepComment()
                if (com): self.bufPos += len(com)
                nFound += len(com)
            elif (allowParams and c == "%"):
                self.allowPE()
            else:
                return

    def allowPE(self):
        """Used by skipSpaces and others when it's ok to have a parameter
        entity reference.
        """
        # skipspaces???? don't go circular
        if (self.peek() != "%"): return False
        self.bufPos += 1
        pename = self.readName()
        if (not pename): raise SyntaxError(
            f"Incomplete parameter entity reference name at '{pename}'.")
        if (not self.consume() == ";"): raise SyntaxError(
            f"Unterminated parameter entity reference to '{pename}'.")
        if (pename not in self.parameterDefs): raise SyntaxError(
            f"Unknown parameter entity '{pename}'.")
        self.open(space=SpaceType.PARAMETER, ename=pename)
        self.entStack[-1].skipSpaces()
        return

    def readNameGroup(self, ss:bool=False) -> List:
        """How
        """
        ngo = self.readConst("(", ss)
        if ngo is None: return None
        names = []
        while (True):
            name = self.readName(ss=True)
            if name is None: raise SyntaxError(
                "Expected a name is name group.")
            names.append(name)
            self.skipSpaces()
            c = self.consume()
            if (c == ")"): break
            if c not in "|&,": raise SyntaxError(
                f"Unexpected operator '{c}'.")
        return names

    def readNameOrNameGroup(self, ss:bool=False) -> List:
        if ss: self.skipSpaces()
        c = self.peek(1)
        if c == "(":
            names = self.readNameGroup(ss=True)
        else:
            names = [ self.readName() ]
        if not names: return None
        return names


###############################################################################
#
class Parser(StackReader):

    ### Readers for top-level DTD constructs
    #
    def readPI(self) -> (str, str):                     # PI
        pio = self.readConst("<?", ss=True)
        if pio is None: return None, None
        piTarget = self.readName()
        piData = self.readToString("?>", consumeEnder=True)
        if piData is None:
            raise SyntaxError("Unterminated PI")
        return piTarget, piData

    def readComment(self) -> str:                       # COMMENT
        como =  self.readConst("<!--", ss=True)
        if como is None: return None
        comData = self.readToString("-->", consumeEnder=True)
        if comData is None:
            raise SyntaxError("Unterminated Comment")
        return comData

    def readElementDcl(self):                           # ELEMENT DCL
        if self.readConst("<!ELEMENT", ss=True) is None: return None
        omitStart = omitEnd = False
        names = self.readNameOrNameGroup(ss=True)
        if names is None: raise SyntaxError(
            "Expected element name or group.")
        if self.sgml:
            omitStart = omitEnd = False
            mat = self.readRegex(r"\s+([-O])\s+([-0])")
            if mat:
                omitStart = mat.group(1) == "O"
                omitEnd = mat.group(2) == "O"
        mat = self.readModel()
        return (names, omitStart, omitEnd, mat.group())

    def readNotationDcl(self):                          # NOTATION DCL
        if self.readConst("<!NOTATION") is None: return None
        name = self.readName(ss=True)
        publicId = systemId = ""
        if self.readConst("PUBLIC", ss=True):  # TODO Sw all to readName?
            publicId = self.readQLit(ss=True)
            systemId = self.readQLit(ss=True)
        elif self.readConst("SYSTEM"):
            systemId = self.readQLit(ss=True)
        else:
            raise SyntaxError("Expected PUBLIC or SYSTEM identifier.")
        return (name, publicId, systemId)

    def readModel(self):
        mat = self.readRegex(r"ANY|EMPTY|CDATA|RCDATA|#PCDATA)", ss=True)
        if (mat): return mat.group()
        model = self.readModelGroup(ss=True)
        rep = self.readRegex(r"[*?+]", ss=True)
        rep = rep.group() if rep else ""
        return model + rep

    def readModelGroup(self, ss:bool=True):
        """Extract and return a balanced paren group like a content model.
        Handily, you can't have parens as escaped data in there.
        """
        if ss: self.skipSpaces()
        if (self.peek() != "("): return None
        self.consume()
        depth = 1
        endsAt = None
        for i in range(self.bufPos, len(self.buf)):
            c = self.buf[i]
            if (c == "("): depth += 1
            elif (c == ")"): depth -= 1
            if (depth == 0):
                endsAt = i
                break
        if (not endsAt): return None
        mod = self.buf[self.bufPos:endsAt+1]
        self.curFrame.bufPos = endsAt + 1
        return mod

    attrTypes = {
        "NMTOKEN":1, "NMTOKENS":1, "NUMTOKEN":1, "NUMTOKENS":1,
        "IDREF":1, "IDREFS":1, "ID":1,
        "CDATA":1, "ENTITY":1, "ENTITIES":1, "NOTATION":1, }

    attrDefaults = {
        "#IMPLIED":1, "#REQUIRED":1, "#FIXED":1, "#CURRENT":1, "#CONREF":1, }

    def readAttListDcl(self):                           # ATTLIST DCL
        """Example:
            <!ATTLIST para  class   NMTOKENS    #IMPLIED
                            level   NUMTOKEN    #REQUIRED
                            thing   (b|c|d)     "D"
                            spam    ENTITY      FIXED "chap1">
        """
        if (self.readConst("<!ATTLIST") is None): return None
        self.skipSpaces()
        if (self.peek() == "("):
            elNames = self.readNameGroup()
        else:
            elNames = [ self.readName() ]

        atts = {}
        while (True):
            attDftKwd = dftVal = None
            attName = self.readName(ss=True)
            if attName is None: raise SyntaxError(
                "Expected attribute name.")

            attType = self.readName(ss=True)
            if attType is None: raise SyntaxError(
                "Expected attribute type.")
            if attType not in self.attrTypes: raise SyntaxError(
                f"Unknown attribute type {attType}.")

            self.skipSpaces()
            self.allowPE()
            c = self.peek()
            if c == "#":
                attDftKwd = self.consume()
                attDftKwd += self.readName() or ""
                if attDftKwd not in self.attrDefaults: raise SyntaxError(
                    f"Unknown attribute default {attDftKwd}.")
                if attDftKwd == "#FIXED":
                    dftVal = self.readQLit(ss=True)
            elif c in '"\'':
                dftVal = self.readQLit()

            atts[attName] = ( attName, attType, attDftKwd, dftVal)
            self.skipSpaces()
            if self.peek() != ">": raise SyntaxError
            return elNames, atts

    def readEntityDcl(self):                            # ENTITY DCL
        """Examples:
            <!ENTITY % foo "(i | b | tt)">
            <!ENTITY XML "Extensible Markup Language">
            <!ENTITY chap1 SYSTEM "/tmp/chap1.xml">
            <!ENTITY if1 SYSTEM "/tmp/fig1.jpg" NDATA jpeg>
        """
        if self.readConst("<!ENTITY") is None:
            return None
        self.skipSpaces()
        isParam = (self.readConst("%") is not None)
        name = self.readName(ss=True)
        publicId = systemId = lit = ""
        key = self.readName(ss=True)
        if key == "PUBLIC":
            publicId = self.readQLit(ss=True)
            systemId = self.readQLit(ss=True)
        elif key == "SYSTEM":
            systemId = self.readQLit(ss=True)
        else:
            lit = self.readQLit(ss=True)

        notn = None
        if self.readConst("NDATA", ss=True):
            notn = self.readName(ss=True)
            if notn is None: raise SyntaxError(
                "Expected notation name after NDATA.")

        self.skipSpaces()
        if not self.readConst(">"): raise SyntaxError(
            "Expected '>' to close declaration.")
        return (name, isParam, publicId, systemId, lit, notn)


###############################################################################
#

ifh = codecs.open("../sample.dtd", "rb", encoding="utf-8")
rawData = ifh.read()
pdt = ParseDocType(rawData)
