#!/usr/bin/env python3
#
# EntityManager
# multiXml written 2011-03-11 by Steven J. DeRose.
# Broken out from multiXML.py, 2013-02-25.
#
#pylint: disable=W1201
#
import os
#import sys
import codecs
import re
from enum import Enum
import logging
from typing import Union, List, Dict

#import html
#from html.entities import codepoint2name

from xmlstrings import XmlStrings as XStr
from saxplayer import SaxEvents

lg = logging.getLogger("EntityManager")
logging.basicConfig(level=logging.INFO)

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

* Finish.

* Add readers for attr, starttag, endtag, text, gen ent

=Rights=

Copyright 2011-03-11 by Steven J. DeRose. This work is licensed under a
Creative Commons Attribution-Share-alike 3.0 unported license.
For further information on this license, see
[https://creativecommons.org/licenses/by-sa/3.0].

For the most recent version, see [http://www.derose.net/steve/utilities]
or [https://github.com/sderose].


=Options
"""

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
        if not XStr.isXmlName(name):
            raise SyntaxError(f"Name '{name}' for entity is not valid.")
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

        if self.locType == LocType.LITERAL:
            assert space != SpaceType.NOTATION
            self.path = None
        else:
            self.path = self.findLocalPath()

    def findLocalPath(self) -> str:
        """Catalog, path var, etc.
        """
        evName = "ENTITYPATH"
        if not self.systemId:
            raise IOError("No system ID for %s." % (self.name))
        if os.path.isfile(self.systemId): return self.systemId
        if evName in os.environ:
            epaths = os.environ[evName].split(":")
            for epath in epaths:
                cand = os.path.join(epath, self.systemId)
                if os.path.isfile(cand): return cand
        raise IOError("No file found for %s (systemId %s)." % (self.name, self.systemId))


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
    def __init__(self, eDef:EntityDef, encoding:str="utf-8"):
        assert isinstance(eDef, EntityDef)
        self.eDef = eDef
        self.encoding = encoding
        self.ifh = None
        self.buf = ""
        self.bufPos = 0
        self.lineNum = 0
        self.offset = 0
        if self.eDef.data:
            self.buf = self.eDef.data  # TODO Copy?
        elif self.eDef.path:
            self.ifh = codecs.open(self.eDef.path, "rb", self.eDef.encoding)
            self.buf = self.ifh.read()

    def close(self):
        if self.ifh: self.ifh.close()
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
        If EOF happens and there's nothing in buf, that's really EOF on the entity.
        """
        if not self.ifh:
            if self.bufPos >= len(self.buf):
                self.buf = ""
                return EOF

        self.buf = self.buf[self.bufPos:]
        self.bufPos = 0
        if len(self.buf) < n:
            newChars = self.ifh.read(n)
            #lg.info("\n  Topped off with: ###%s###", newChars)
            self.lineNum += newChars.count('\n')
            self.offset += len(newChars)
            self.buf += newChars
        if not self.buf:
            self.ifh.close()
            return False  # EOF
        return True

    def skipSpaces(self, allowComments:bool=True):
        """XML eliminated in-space --...-- comments.
        Since this is in EntityFrame, it doesn't handle parameter entities
        (they change the EntityFrame, so are hanled one level up).
        """
        while True:
            if self.bufLeft < 1:
                self.topOff()
                if not self.bufLeft: return EOF
            if self.buf[self.bufPos] in " \t\r\n":
                self.bufPos += 1
            elif allowComments and self.peek(2) == "--":
                self.readSepComment()
            else:
                return True

    def readSepComment(self, ss:bool=True):
        """Read a comment that's just the --...-- part.
        """
        if ss: self.skipSpaces()
        # Or readToString("--")
        mat = re.match(r"--([^-]|-[^-])+--", self.buf[self.bufPos:])
        if not mat: return None
        self.bufPos += len(mat.group(1))
        return mat.group(1)

    def readConst(self, const:str, ss:bool=True, thenSp:bool=False):
        # TODO Case-ignoring option?
        if ss: self.skipSpaces()
        if self.bufLeft < len(const)+1: self.topOff()
        if not self.buf[self.bufPos:].startswith(const): return None
        if thenSp and not self.buf[self.bufPos+len(const)].isspace(): return None
        self.bufPos += len(const)
        return const

    def readName(self, ss:bool=True) -> str:
        """
        TODO Add options to allow/require initial "#"
        TODO Add option to require \\s, \\b, or \\W after? Meh.
        This doesn't recognize parameter entity refs. Must it?
        """
        if ss: self.skipSpaces()
        mat = re.match(XStr._xmlName, self.buf[self.bufPos:])
        if not mat: return None
        self.bufPos += len(mat.group(1))
        return mat.group(1)

    def readQLit(self, ss:bool=True, keepPunc:bool=False) -> str:
        # Support curly quotes?
        # allowParams:bool=True,  # TODO ???
        if ss: self.skipSpaces()
        mat = re.match(r"('[^']*'|\"[^\"]*\")", self.buf[self.bufPos:])
        if (mat is None): return None
        self.bufPos += len(mat.group())
        return mat.group(1) if keepPunc else mat.group(1)[1:-1]

    def readQLitOrName(self, ss:bool=True, keepPunc:bool=False) -> str:
        # TODO Distinguish which it found.
        if ss: self.skipSpaces()
        rc = self.readQLit(ss, keepPunc)
        if rc is not None: return rc
        rc = self.readName(ss)
        if rc is not None: return rc
        return None

    def readRegex(self, regex:Union[str, re.Pattern], ss:bool=True,
        ignoreCase:bool=True) -> re.Match:
        """Check if the regex matches immediately. If so, return the match object
        (so captures can be distinguished) and consume the matched text.
        If not, return None and consume nothing.
        TODO Won't match across buffer topOffs or entities.
        """
        if ss: self.skipSpaces()
        self.topOff()
        mat = re.match(regex, self.buf[self.bufPos:],
            flags=re.I if ignoreCase else 0)
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
class StackReader:
    """Keep dictionaries of entities and notations, and a stack of
    open ones being read. Support very basic read operations (leave the
    fancy stuff for a subclass to add).
    """
    def __init__(self, rootPath:str=None, encoding:str="utf-8", entPath:List=None):
        self.entPath    = entPath    # dirs to look in
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

        self.rootDef = None
        self.rootFrame = None
        self.entStack = []
        self.totLines = 0       # overall lines processed
        self.totChars = 0       # overall chars processed

        self.sgml = False
        self.sawSubsetOpen = False

        self.MAXEXPANSION = 1 << 20
        self.MAXSUBS = 1000

        self.handlers = {}  # keyed off saxplayer.SaxEvents

        if rootPath:
            self.setupDocEntity(rootPath, encoding)
            self.parseTop()

    def SE(self, msg:str):
        """Report a syntax error.
        """
        raise SyntaxError(msg + " at \n$$$" + self.bufSample + "$$$")

    def setupDocEntity(self, rootPath:str, encoding:str="utf-8"):
        assert len(self.entStack) == 0
        if not os.path.isfile(rootPath):
            raise IOError(f"File not found: {rootPath}.")
        self.rootDef = EntityDef(space=SpaceType.GENERAL,
            name="_root", systemId=rootPath, encoding=encoding)
        self.rootFrame = EntityFrame(self.rootDef, encoding=encoding)
        self.entStack.append(self.rootFrame)

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
            if (totsubs > self.MAXSUBS):
                self.SE("Too many parameter entity substitutions, depth %d, count %d."
                    % (totpasses, totsubs))
        return s

    def getParameterText(self, mat):
        peName = mat.group(1)
        if self.isOpen(SpaceType.PARAMETER, peName):
            self.SE("Parameter entity {peName} is already open.")
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
        if self.isOpen(space, ename):
            self.SE("Entity {peName} is already open.")
        ef = EntityFrame(eDef)
        lg.info("Opening entity {ename}.")
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

    @property
    def buf(self):
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
            "$$$" +  #"\uFE0E" +  # WHITE FROWNING FACE+
            self.buf[self.bufPos:self.bufPos+postLen])

    def readConst(self, const:str, ss:bool=True, thenSp:bool=False):
        return self.curFrame.readConst(const, ss, thenSp)
    def readName(self, ss:bool=True):
        return self.curFrame.readName(ss)
    def readQLit(self, ss:bool=True, keepPunc:bool=False):
        return self.curFrame.readQLit(ss, keepPunc)
    def readRegex(self, regex:Union[str, re.Pattern], ss:bool=True, ignoreCase:bool=True):
        return self.curFrame.readRegex(regex, ss, ignoreCase)
    def readToString(self, s:str, consumeEnder:bool=True):
        return self.curFrame.readToString(s, consumeEnder)
    def readSepComment(self, ss:bool=True):
        return self.curFrame.readSepComment(ss)

    def peek(self, n:int=1):
        return self.curFrame.peek(n)
    def consume(self, n:int=1) -> str:
        return self.curFrame.consume(n)
    def pushBack(self, s:str) -> None:
        return self.curFrame.pushBack(s)

    def topOff(self, n:int=1000) -> bool:
        while self.entStack:
            if self.curFrame.topOff(n) != EOF: return
            self.curFrame.close()
            self.close()

    def skipSpaces(self, allowComments:bool=True, allowParams:bool=False):
        #crossEntityEnds:bool=False):  # TODO Implement stack!
        """Basically skip spaces, but at option, also:
            * skip a comment
            * expand if we hit a parameter entity reference.
        """
        nFound = 0
        while True:
            if not self.bufLeft:
                if self.topOff() == EOF: self.close()
                if not self.entStack: break
            c = self.buf[self.bufPos]
            if c.isspace():
                self.bufPos += 1
                nFound += 1
            elif allowComments and c == "-":
                com = self.readSepComment()  # TODO Save or return?
                if com: self.bufPos += len(com)
                nFound += len(com)
            elif allowParams and c == "%":
                self.allowPE()
            else:
                break
        return

    def allowPE(self):
        """Used by skipSpaces and others when it's ok to have a parameter
        entity reference.
        """
        # skipspaces???? don't go circular
        if self.peek() != "%": return False
        self.bufPos += 1
        pename = self.readName()
        if not pename:
            self.SE(f"Incomplete parameter entity reference name '{pename}').")
        if not self.consume() == ";":
            self.SE(f"Unterminated parameter entity reference to '{pename}'.")
        self.bufPos += 1
        if pename not in self.parameterDefs:
            self.SE(f"Unknown parameter entity '{pename}'.")
        self.open(space=SpaceType.PARAMETER, ename=pename)
        self.entStack[-1].skipSpaces()
        return

    def readNameGroup(self, ss:bool=False) -> List:
        """Allows and mix of [&|,] or space between names.
        t/his is slightly too permissive.
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
            self.skipSpaces()
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
        if c == "(":
            names = self.readNameGroup(ss=True)
        else:
            names = [ self.readName() ]
        if not names: return None
        return names


    def parseTop(self):
        #import pudb; pudb.set_trace()
        self.doCB(SaxEvents.START)
        # TODO Swap all 'ss' to default to True, this is the exception
        if e := self.readConst("<?xml", ss=False, thenSp=True):
            e = self.readToString("?>", consumeEnder=True)
            if e is None:
                self.SE("Unexpected EOF in XML DCL.")
            self.doCB(SaxEvents.XMLDCL, e)
        if e := self.readConst("<!DOCTYPE", ss=True, thenSp=True):
            docTypeName = self.readName(ss=True)
            if docTypeName is None:
                self.SE("Expected document type name in DOCTYPE.")
            self.skipSpaces()
            publicId, systemId = self.readLocation()
            self.skipSpaces()
            if self.peek(1) == "[":
                self.sawSubsetOpen = True
                self.consume(1)
            self.doCB(SaxEvents.DOCTYPE, docTypeName, publicId, systemId)

        while True:
            self.skipSpaces(allowParams=True)
            p = self.peek(1)
            #lg.info("AT %s", p)
            if p is None:
                self.SE("Unexpected EOF in DOCTYPE.")
            elif p == "]":
                self.consume()
                if self.readConst(">", ss=True):
                    self.consume()
                    self.doCB("DOCTYPEFIN")
                    return
                self.SE("Expected '>' to end DOCTYPE.")
            elif p == "<":
                if e := self.readComment():
                    self.doCB(SaxEvents.COMMENT, e)
                elif e := self.readElementDcl():
                    self.doCB(SaxEvents.ELEMENTDCL, e)
                elif e := self.readAttListDcl():
                    # TODO by attr?
                    self.doCB(SaxEvents.ATTLISTDCL, e)
                elif e := self.readEntityDcl():
                    self.doCB(SaxEvents.ENTITYDCL, e)
                elif e := self.readNotationDcl():
                    self.doCB(SaxEvents.NOTATIONDCL, e)
                elif e := self.readPI():
                    self.doCB(SaxEvents.PROC, e)
                else:
                    self.SE("Unexpected content is DOCTYPE after '<'.")
            else:
                self.SE(f"Expected ']' or '<' in DOCTYPE, not '{p}'.")
        self.doCB(SaxEvents.FINAL)

    def doCB(self, typ:SaxEvents, *args):
        print(typ, *args)
        if typ not in self.handlers:
            pass
        else:
            self.handlers[typ](self, args)

    ### Readers for top-level DTD constructs
    #
    def readPI(self) -> (str, str):                     # PI
        pio = self.readConst("<?", ss=True)
        if pio is None: return None, None
        piTarget = self.readName()
        piData = self.readToString("?>", consumeEnder=True)
        if piData is None:
            self.SE("Unterminated PI.")
        return piTarget, piData

    def readComment(self) -> str:                       # COMMENT
        como =  self.readConst("<!--", ss=True)
        if como is None: return None
        comData = self.readToString("-->", consumeEnder=True)
        if comData is None:
            self.SE("Unterminated Comment.")
        return comData

    def readElementDcl(self):                           # ELEMENT DCL
        if self.readConst("<!ELEMENT", thenSp=True) is None: return None
        omitStart = omitEnd = False
        names = self.readNameOrNameGroup(ss=True)
        if names is None:
            self.SE("Expected element name or group at {self.bufSample}.")
        if self.sgml:
            omitStart = omitEnd = False
            mat = self.readRegex(r"\s+([-O])\s+([-0])")
            if mat:
                omitStart = mat.group(1) == "O"
                omitEnd = mat.group(2) == "O"
        model = self.readModel()
        if model is None: self.SE("Expected model or declared content for {names}.")
        if not self.readConst(">"): self.SE("Expected '>' for ELEMENT dcl.")
        return (names, omitStart, omitEnd, model)

    def readNotationDcl(self) -> (str, str, str):       # NOTATION DCL
        if self.readConst("<!NOTATION", thenSp=True) is None: return None
        name = self.readName(ss=True)
        publicId, systemId = self.readLocation()
        if publicId is None:
            self.SE(f"Expected PUBLIC or SYSTEM identifier at {self.bufSample}.")
        if not self.readConst(">"): self.SE("Expected '>' for NOTATION dcl.")
        return (name, publicId, systemId)

    def readLocation(self) -> (str, str):
        publicId = systemId = ""
        if self.readConst("PUBLIC", ss=True):
            publicId = self.readQLit(ss=True)
            systemId = self.readQLit(ss=True)
        elif self.readConst("SYSTEM"):
            systemId = self.readQLit(ss=True)
        else:
            return None, None
        return (publicId, systemId)

    def readModel(self) -> Union[List[str], str]:
        # Perhaps add a readKeyWord(keys:Union(List, Dict, Enum))?
        # TODO Refactor into NameTuple(typ, rep, List)?
        mat = self.readRegex(r"(ANY|EMPTY|CDATA|RCDATA|#PCDATA)\b", ss=True)
        if mat: return mat.group()
        model = self.readModelGroup(ss=True)
        if model is None: return None
        if rep := self.readRegex(r"[*?+]", ss=True): model.append(rep.group())
        return model

    def readModelGroup(self, ss:bool=True) -> str:
        """Extract and return a balanced paren group like a content model.
        Handily, you can't have parens as escaped data in there.
        Does not check that each group is uniform on [,|&].
        TODO PE refs?
        """
        if ss: self.skipSpaces()
        if not self.readConst("("): return None
        tokens = [ "(" ]
        depth = 1
        endsAt = None
        curToken = ""
        for i in range(self.bufPos, len(self.buf)):
            c = self.consume()
            if XStr.isXmlName(curToken+c):
                curToken += c
                continue
            if curToken:  # Anything BUT more of the token.
                tokens.append(curToken)
                curToken = ""
            if c.isspace():
                continue
            elif c == "#":
                if not (kwd := self.readConst("PCDATA", ss=False)):
                    self.SE(f"'#' but not #PCDATA' in model.")
                if curToken:
                    self.SE(f"Misplaced '#PCDATA' in model.")
                tokens.append("#PCDATA")
            elif c == "(":
                if XStr.isXmlName(tokens[-1]):
                    self.SE("Misplaced ')' in model.")
                tokens.append(c); depth += 1
            elif c == ")":
                if tokens[-1] in "|,&" or tokens[-1] == "#PCDATA":
                    self.SE("Misplaced ')' in model.")
                tokens.append(c); depth -= 1
                if depth == 0: endsAt = i; break
            elif c in "|,&":
                if (tokens[-1] not in  ")+?*" and tokens[-1] != "#PCDATA"
                    and not XStr.isXmlName(tokens[-1])):
                    self.SE(f"Misplaced op '{c}' in model.")
                tokens.append(c)
            elif c in "+?*":
                if tokens[-1] != ")" and not XStr.isXmlName(tokens[-1]):
                    self.SE(f"Misplaced repetition op '{c}' in model.")
                tokens.append(c)
            else:
                self.SE(f"Unexpected character '{c}' in model.")
        if not endsAt: return None
        return tokens

    attrTypes = {
        "NMTOKEN":1, "NMTOKENS":1, "NUMTOKEN":1, "NUMTOKENS":1,
        "IDREF":1, "IDREFS":1, "ID":1,
        "CDATA":1, "ENTITY":1, "ENTITIES":1, "NOTATION":1, }

    # DocumentType.AttrType for XSD additions

    attrDefaults = {
        "#IMPLIED":1, "#REQUIRED":1, "#FIXED":1, "#CURRENT":1, "#CONREF":1, }

    def readAttListDcl(self):                           # ATTLIST DCL
        """Example:
            <!ATTLIST para  class   NMTOKENS    #IMPLIED
                            level   NUMTOKEN    #REQUIRED
                            thing   (b|c|d)     "D"
                            spam    ENTITY      FIXED "chap1">
        """
        if self.readConst("<!ATTLIST", thenSp=True) is None: return None
        self.skipSpaces()
        if self.peek() == "(":
            eNames = self.readNameGroup()
        else:
            eNames = [ self.readName() ]

        atts = {}
        while (True):
            attDftKwd = dftVal = None
            if self.readConst(">", ss=True): break
            attName = self.readName(ss=True)
            if attName is None:
                self.SE(f"Expected attribute name in ATTLIST for {eNames}.")

            self.skipSpaces()
            if self.peek() == "(":
                enumItems = self.readModelGroup(ss=True)  # TODO: No nesting....
            elif not (attType := self.readName(ss=True)):
                self.SE("Expected attribute type or enum-group.")
            elif attType not in self.attrTypes:
                # TODO Option for XSD builtins, too?
                self.SE(f"Unknown type {attType} for attribute {attName}.")

            self.skipSpaces(allowParams=True)
            c = self.peek()
            if c == "#":
                attDftKwd = self.consume()
                attDftKwd += self.readName() or ""
                if attDftKwd not in self.attrDefaults:
                    self.SE(f"Unknown attribute default {attDftKwd} for attribute {attName}.")
                if attDftKwd == "#FIXED":
                    dftVal = self.readQLit(ss=True)
            elif c in '"\'':
                dftVal = self.readQLit()
            atts[attName] = ( attName, attType, attDftKwd, dftVal)

        self.skipSpaces()
        return eNames, atts

    def readEntityDcl(self):                            # ENTITY DCL
        """Examples:
            <!ENTITY % foo "(i | b | tt)">
            <!ENTITY XML "Extensible Markup Language">
            <!ENTITY chap1 SYSTEM "/tmp/chap1.xml">
            <!ENTITY if1 SYSTEM "/tmp/fig1.jpg" NDATA jpeg>
        """
        if self.readConst("<!ENTITY", thenSp=True) is None: return None
        self.skipSpaces()
        isParam = (self.readConst("%") is not None)
        name = self.readName(ss=True)
        publicId = systemId = lit = ""
        publicId, systemId = self.readLocation()
        if (publicId is None):
            lit = self.readQLit(ss=True)

        notn = None
        if self.readConst("NDATA", ss=True):
            notn = self.readName(ss=True)
            if notn is None: self.SE("Expected notation name after NDATA.")

        self.skipSpaces()
        if not self.readConst(">"): self.SE("Expected '>' for ENTITY dcl.")
        return (name, isParam, publicId, systemId, lit, notn)


    ###########################################################################
    #
    def readStartTag(self, ss:bool=True) -> (str, Dict, bool):
        attrs = {}
        if not self.readConst("<", ss): return None, None, None
        if not (aname := self.readName(ss)):
            self.SE("Expected name in end-tag.")
        while (True):
            aname, avalue = self.readAttr(ss=True)
            if aname is None: break
            attrs[aname] = avalue
        empty = False
        if self.readConst("/>", ss): empty = True
        elif self.readConst(">", ss): empty = False
        else: self.SE("Unclosed start-tag for '{aname}'.")
        self.doCB(SaxEvents.START, aname, attrs)
        if empty: self.doCB(SaxEvents.END, aname)
        return aname, attrs, empty

    def readAttr(self, ss:bool=True, keepPunc:bool=False) -> (str, str):
        if not (aname := self.readName(ss)): return None, None
        if not self.readConst("=", ss):
            self.SE("Expected '=' after attribute name.")
        if not (avalue := self.readQLit(ss, keepPunc)): return None, None
        return aname, avalue

    def readEndTag(self, ss:bool=True) -> str:
        if not self.readConst("</", ss): return None
        if not (aname := self.readName(ss)):
            self.SE("Expected name in end-tag.")
        if not self.readConst(">", ss):
            self.SE("Unclosed end-tag for '{aname}'.")
        self.doCB(SaxEvents.END, aname)
        return aname

    def readCDATA(self, ss:bool=True) -> str:
        if not self.readConst("<![CDATA[", ss): return None
        data = self.readToString("]]>")
        if not data: self.SE("Unclosed CDATA section.")
        self.doCB(SaxEvents.CDATASTART)
        self.doCB(SaxEvents.CHAR, data)
        self.doCB(SaxEvents.CDATAEND)
        return data


###############################################################################
#
#ifh = codecs.open("sample.dtd", "rb", encoding="utf-8")
#rawData = ifh.read()
pdt = StackReader("sample.dtd", encoding="utf-8")

print("Done.")
