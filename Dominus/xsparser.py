#!/usr/bin/env python3
#
# XSParser: An easily-tweakable XML parser, with DTD++ support.
# Original: multiXml written 2011-03-11 by Steven J. DeRose.
#
# See https://www.balisage.net/Proceedings/vol8/print/
#     Sperberg-McQueen01/BalisageVol8-Sperberg-McQueen01.html
#
#pylint: disable=W1201
#
import codecs
import os
import re
import logging
from typing import Union, List, Dict, Tuple, IO
from collections import OrderedDict
import inspect

#import html
from html.entities import name2codepoint  # codepoint2name

from xmlstrings import XmlStrings as XStr, CaseHandler, UNormHandler, WSHandler, Normalizer
from saxplayer import SaxEvent
from basedomtypes import NSuppE, NMTOKEN_t, DOMException, SepChar
from documenttype import EntitySpace, EntityParsing, EntityDef
from documenttype import DocumentType, Model, RepType, ContentType  # ModelGroup
import xsdtypes
from xsdtypes import (sgmlAttrTypes, sgmlAttrDefaults, XSDDatatypes,
    fixedKeyword, anyAttrKeyword)
from basedom import Document
from stackreader import InputFrame, FileFrame, EntityFrame, uname2codepoint

lg = logging.getLogger("EntityManager")
logging.basicConfig(level=logging.INFO, format='%(message)s')

EOF = -1

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


def callerNames(n1:int=3, n2:int=1) -> str:
    buf = ""
    for i in range(n1, n2, -1): buf += "." + inspect.stack()[i].function
    return buf

class TagStackEntry:
    """For the moment, we're planning to do validation on close, so also
    keep the list of sibling types.
    """
    def __init__(self, name:str, lineNum:int):
        self.name = name
        self.lineNum = lineNum
        self.isSuspended = False
        self.childTypes = []

class TagStack(list):
    """Mainly keeps the stack of open element type names, but has room for
    extra info like where the element started.
    With extensions like OLIST and suspend/resume, it's not exactly a stack.
    """
    def __init__(self, trackChildTypes:bool=False):
        super().__init__()
        self.trackChildTypes = trackChildTypes

    def __insert__(self, *args):
        raise NotImplementedError("No manual insert on TagStack.")

    def __extend__(self, *args):
        raise NotImplementedError("No manual extend on TagStack.")

    def __setitem__(self, *args):
        raise NotImplementedError("No manual __setitem__ on TagStack.")

    def append(self, name:str, lineNum:int=None):
        """Push the new element onto the open stack.
        BUT ALSO add it to the parent's list of childTypes.
        TODO: Maybe just keep repetition counts, not full list?
        """
        if self.trackChildTypes: self[-1].childTypes.append(name)
        tsentry = TagStackEntry(name, lineNum)
        super().append(tsentry)

    def rindex(self, name:str):
        for i in reversed(range(len(self))):
            if self[i].name == name: return i
        return None

    @property
    def topName(self):
        """Conveniently avoid IndexError.
        """
        return self[-1].name if len(self) > 0 else None

    def suspend(self, n:int, lineNum:int=None):
        self[n].isSuspended = True
        if lineNum is not None: self[n].lineNum = lineNum

    def resume(self, n:int, lineNum:int=None):
        self[n].isSuspended = False
        if lineNum is not None: self[n].lineNum = lineNum


###############################################################################
#
class XSPOptions:
    """Keep track of parser extensions in use (if any).

    Shunt the deuterium from the main cryo-pump to the auxiliary tank.
    Er, the tank can't withstand that kind of pressure.
    Where'd you... where'd you get that idea?
    ...It's in the impulse engine specifications.
    Regulation 42/15 -- Pressure Variances on the IRC Tank Storage?
    Yeah.
    Forget it. I wrote it. Just... boost the flow. It'll work.
            -- ST:TNG "Relics"
    """
    def __init__(self, options:Dict=None):
        ### Size limits and security (these are XML compatible)
        self.MAXEXPANSION    = 1<<20  # Limit expansion length of entities
        self.MAXENTITYDEPTH  = 1000   # Limit nesting of entities
        self.charEntities    = True   # Allow SDATA and CDATA entities
        self.extEntities     = True   # External entity refs?
        self.netEntities     = True   # Off-localhost entity refs?
        self.entityDirs      = []     # Permitted dirs to get ents from

        ### Case and Unicode
        NM = Union[ CaseHandler, UNormHandler, WSHandler, Normalizer ]
        self.elementFold:NM  = None
        self.attrFold:NM     = None   # (attribute NAMEs)
        self.entityFold:NM   = None
        self.keywordFold:NM  = None
        self.uNormHandler    = None   #                                 TODO
        self.wsDef           = None   # (XML default)                   TODO
        self.radix           = "."    # Decimal point choice            TODO
        self.noC1            = False  # No C1 controls                  TODO

        ### Schemas
        self.schemaType      = "DTD"  # <!DOCTYPE foo SYSTEM "" NDATA XSD>
        self.fragComments    = False  # In-dcl like SGML
        #self.setDcls        = False  # <!ENTITY % x SET (i b tt)>      TODO

        ### Elements
        self.groupDcl        = False  # <!ELEMENT (x|y|z)...>
        self.oflag           = False  # <!ELEMENT - O para...>
        self.sgmlWord        = False  # CDATA RCDATA #CURRENT etc.
        self.mixel           = False  # Dcl content ANYELEMENT          TODO
        self.mixins          = False  # cf incl exceptions
        self.repBrace        = False  # {min max} for repetition
        self.emptyEnd        = False  # </>
        self.omitEnd         = False  #                                 TODO
        self.omitAtEOF       = False  #                                 TODO
        self.restart         = False  # <|> to close & reopen current element
        self.simultaneous    = False  # <b|i> </i|/b>
        self.multiTag        = False  # <div/title>...</title/div>      TODO
        self.suspend         = False  # <x>...<-x>...<+x>...</x>
        self.olist           = False  # olist not stack

        ### Attributes
        self.globalAttr      = False  # <!ATTLIST * ...>
        self.anyAttr         = False  # <!ATTLIST foo #ANY CDATA #IMPLIED>
        self.xsdType         = False  # XSD builtins for attr types
        self.xsdPlural       = False  # XSD types + plurals             TODO
        self.specialFloat    = False  # Nan Inf etc. (needed?)
        self.unQuotedAttr    = False  # <p x=foo>
        self.curlyQuote      = False
        self.booleanAttr     = False  # <x +border -foo>
        self.bangAttr        = False  # != on first use to set dft
        self.bangAttrType    = False  # !typ= to set datatype           TODO
        self.coID            = False  # co-index Trojans                TODO
        self.nsID            = False  # IDs can have ns prefix          TODO
        self.stackID         = False  # ID is cat(anc:@id)              TODO

        ### Validation (beyond WF!)
        self.valElementNames = False  # Must be declared
        self.valModels       = False  # Child sequences                 TODO
        self.valAttrNames    = False  # Must be declared
        self.valAttrTypes    = False  # Must match datatype
        self.undeclaredAttrs = False  #                                 TODO

        ### Entities and special characters
        self.htmlNames       = False  # Enable HtML/Annex D named char refs
        self.unicodeNames    = False  # Enable Raku-like unicode entities
        self.multiPath       = False  # Multiple SYSTEM IDs
        self.multiSDATA      = False  # <!SDATA nbsp 160 z 0x9D>        TODO
        self.backslash       = False  # \n \xff \uffff (not yet \\x{}

        ### Other
        self.expatBreaks     = False  # Break at \n and entities like expat
        self.emComments      = False  # emdash as -- for comments       TODO
        self.piAttr          = False  # PI parsed like attributes.      TODO
        self.piAttrDcl       = False  # <!ATTLIST ?target ...>          TODO
        self.nsSep           = ":"    #                                 TODO
        self.nsUsage         = None   # one/global/noredef/regular      TODO
        self.MSTypes         = False  # Allow other than CDATA?

        if options:
            for k, v in options.items():
                self.setOption(k, v)

    def setOption(self, oname:str, ovalue):
        if oname.startswith("_") or not hasattr(self, oname):
            raise ValueError(f"Unknown option '{oname}'.")
        curVal = getattr(self, oname)
        if (curVal is not None
            and not isinstance(ovalue, type(curVal))): raise TypeError(
            f"Unexpected value type {type(ovalue)} (not {type(curVal)}) for '{oname}'.")
        if (oname == "entityDirs"):
            for adir in ovalue: assert os.path.isdir(adir)
        setattr(self, oname, ovalue)


###############################################################################
#
class ErrorRecord:
    def __init__(self, theParser, code:int):
        self.theParser = theParser
        self.code = code
        self.entName = theParser.CurrentEntityName
        self.byteIndex = theParser.CurrentByteIndex
        self.lineNumber = theParser.CurrentLineNumber
        self.columnNumber = theParser.CurrentColumnNumber

    def tostring(self) -> str:
        return "ERROR {%d}: In entity '{%s}' @%d:%d (offset %d)." % (
            self.code, self.entName,
            self.lineNumber, self.columnNumber, self.byteIndex)


###############################################################################
#
class StackReader:
    """Keep dictionaries of entities and notations, and a stack of
    open ones being read. Support very basic read operations (leave the
    fancy stuff for a subclass to add), and support extensions.
    """
    def __init__(self, rootPath:str=None, encoding:str="utf-8",
        handlers:Dict=None, entPath:List=None, bufSize:int=1024,
        options:Dict=None):
        lg.info("\n******* StackReader for path '%s'.", rootPath)
        self.rootPath = rootPath
        self.encoding = encoding
        self.handlers = handlers or {}  # keyed off saxplayer.SaxEvent
        self.entPath = entPath  # dirs to look in
        self.bufSize = bufSize

        self.doctype = DocumentType()
        self.generalDefs = { }
        self.parameterDefs = {}
        self.notationDefs = {}
        self.sdataDefs = {  # TODO Hook up dcls and a set method
            "lt":   "<",
            "gt":   ">",
            "amp":  "&",
            "quot": '"',
            "apos": "'",
        }

        self.spaces = {
            EntitySpace.GENERAL: self.generalDefs,
            EntitySpace.PARAMETER: self.parameterDefs,
            EntitySpace.NOTATION: self.notationDefs,
        }

        # IO state
        self.rootFrame = None
        self.totLines = 0  # overall lines processed
        self.totChars = 0  # overall chars processed
        self.totEvents = 0

        # Parser state
        self.entStack:EntityFrame = []
        self.msStack = []
        self.tagStack = TagStack()
        self.sawSubsetOpen:bool = False
        self.bangAttrs:dict = {}

        # Optional feature and extension switches. The default is intended to
        # always match the XML spec.
        # Switchable in XML DCL (iff "version" starts with "s.")
        #
        self.options = XSPOptions(options)
        if self.options.xsdType:
            self.attrTypes = XSDDatatypes
        else:
            self.attrTypes = sgmlAttrTypes
        if rootPath: self.ParseFile(rootPath)

    @property
    def nextStuffOBS(self) -> str:
        if not self.entStack: return "[EOF]"
        frame = self.entStack[-1]
        endAt = min(len(frame.buf), frame.bufPos+70)
        return frame.buf[frame.bufPos:endAt]

    def SE(self, msg:str) -> None:
        """Deal with a syntax error.
        """
        raise SyntaxError(msg + " at:\n    " + self.bufSample)

    def VE(self, msg:str) -> None:
        """Deal with a validation error.
        """
        raise SyntaxError("Validation Error: " + msg)

    def setOption(self, oname:str, ovalue) -> None:
        self.options.setOption(oname, ovalue)

    def doCB(self, typ:SaxEvent, *args) -> None:
        """Given an event type and its args, call the handler if any.
        """
        if (1):
            if typ == SaxEvent.ATTLISTDCL:
                lg.info("doCB for ATTLISTDCL: %s", args[0])
                for tup in args[1]:
                    lg.info("    %s", tup)
            elif typ == SaxEvent.COMMENT:
                lg.info("doCB for COMMENT: %s", args[0])
            elif len(args) == 0:
                lg.info("doCB for %s", typ.name)
            else:
                lg.info("doCB for %s: %s", typ.name, args)

        self.totEvents += 1
        if hasattr(self, typ.value): cb = getattr(self, typ.value)
        elif hasattr(self, SaxEvent.DEFAULT.value): cb = getattr(self, SaxEvent.DEFAULT.value)
        else: return
        if cb: cb(*args)

    def Parse(self, s:str) -> None:  # StackReader
        if not isinstance(s, str) or not s.startswith("<"):
            raise SyntaxError("Parser not given a '<'-initial string.")
        self.rootFrame = InputFrame()
        self.rootFrame.addData(s)
        self.entStack.append(self.rootFrame)
        self.parseTop()

    def ParseFile(self, ifh:IO) -> None:  # StackReader
        assert len(self.entStack) == 0
        if isinstance(ifh, str):
            lg.warning("ParseFile was given a str ('{ifh}'), not on open file.")
            ifh = open(ifh, "rb")
        if not hasattr(ifh, "read"):
            raise IOError(f"Cannot read from {ifh}.")
        self.rootFrame = FileFrame()
        self.rootFrame.addFile(ifh)
        self.entStack.append(self.rootFrame)
        self.parseTop()


####################### Move to stackreader

    def addEntity(self, eDef:EntityDef) -> None:
        tgt = self.spaces[eDef.entSpace]
        if eDef.entName in tgt:
            raise KeyError(f"{eDef.entSpace} object already defined: '{eDef.entName}'.")
        tgt[eDef.entName] = eDef

    def findEntity(self, space:EntitySpace, name:str) -> EntityDef:
        tgt = self.spaces[space]
        if name in tgt: return tgt[name]
        return None

    peRefExpr = r"%(\w[-_.\w]*);"  # TODO Upgrade to use XmlStrings

    def expandPEntities(self, s:List, depth:int=0) -> str:
        """Expand parameter entity references in a string.
        TODO: Save the list/str conversions?
        """
        if depth > self.options.MAXENTITYDEPTH:
            self.SE("Parameter entity too deep ({depth}).")

        s = ''.join(s)
        expBuf = re.sub(self.peRefExpr, self.getPEText, s)
        if len(expBuf) > self.options.MAXEXPANSION: raise ValueError(
            "Parameter entity expansion exceeds MAXEXPANSION (%d)."
            % (self.options.MAXEXPANSION))
        if re.search(self.peRefExpr, expBuf):
            expBuf = self.expandPEntities(expBuf, depth=depth+1)
        return expBuf

    def getPEText(self, mat) -> str:
        peName = mat.group()
        try:
            peDef = self.parameterDefs[peName]
        except KeyError as e:
            raise KeyError(f"Unknown parameter entity '{peName}'.") from e
        if not self.isEntRefPermitted(peName):
            return f"<?rejected PE='{peName}'?>"
        if peDef.literal is not None:
            return peDef.literal
        peFrame = EntityFrame(peDef)
        peText = peFrame.readAll()
        peFrame.close()
        return peText

    def isOpen(self, space:EntitySpace, name:NMTOKEN_t) -> bool:
        eDef = self.findEntity(space, name)
        if eDef is None: return False
        for fr in self.entStack:
            if fr.eDef is eDef: return True
        return False

    def open(self, space:EntitySpace, name:NMTOKEN_t) -> EntityFrame:
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

    def isEntRefPermitted(self, eDef:EntityDef, fatal:bool=False) -> bool:
        """Implement some entity-expansion safety protocols.
        """
        if self.isOpen(eDef.entSpace, eDef.entName):  # Always fatal
            self.SE(f"Entity {eDef.entName} is already open.")
            return False
        if self.depth >= self.options.MAXENTITYDEPTH:
            if fatal: self.SE(f"Too much entity nesting, depth {self.depth}.")
            return False
        if (not self.options.charEntities
            and eDef.entParsing == EntityParsing.SDATA):
            if fatal: self.SE("Character entities are disabled.")
            return True

        if not (eDef.publicID or eDef.systemId):
            return True

        # Rest is just for external entities
        if (not self.options.extEntities):
            if fatal: self.SE("External (PUBLIC and SYSTEM) entities are disabled.")
            return False
        if (not self.options.netEntities):
            sid = eDef.systemId
            if "://" in sid and not sid.startswith("file://"):
                self.SE("Non-file URIs for SYSTEM identifiers are disabled.")
        if (self.options.entityDirs):
            if "../" in eDef.systemID:  # TODO Resolve first
                if fatal: self.SE(
                    "'../' not allowed when entityDirs option is set: " + eDef.systemID)
                return False
            found = False
            for okDir in self.options.entityDirs:
                if eDef.systemID.startswith(okDir):
                    found = okDir
                    break
            if (not found): self.SE(
                "'systemId for '{self.eDef.entName}' not in an allowed entDir.")
        return True

    def close(self) -> int:
        """Close the innermost open EntityFrame.
        """
        cf = self.curFrame
        if not cf: return False
        lg.info("Closing entity '%s'.", cf.eDef.entName)
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
        buf = ''.join(
            "    %2d: Entity %-12s line %6d, file '%s'" %
                (i,
                self.entStack[i].eDef.entName,
                self.entStack[i].lineNum,
                self.entStack[i].oeFilename)
            for i in reversed(range(0, self.depth)))
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
        rc = SepChar.qcat(self.buf[self.bufPos-preLen:self.bufPos],
            self.buf[self.bufPos:self.bufPos+postLen])
        #rc = re.sub("\n", "\u240a", rc)
        return rc

    # Forward small constructs to entity-frame-limited readers
    #
    def readConst(self, const:str, ss:bool=True, thenSp:bool=False) -> str:
        return self.curFrame.readConst(const, ss, thenSp)
    def peekDelimPlus(self, ss:bool=True) -> (str, str):
        return self.curFrame.peekDelimPlus(ss=ss)
    def readBackslashChar(self) -> str:
        return self.curFrame.readBackslashChar()
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

    def peek(self, n:int=1) -> str:
        if not self.curFrame: return None
        return self.curFrame.peek(n)
    def consume(self, n:int=1) -> str:
        return self.curFrame.consume(n)
    def discard(self, n:int=1) -> None:
        return self.curFrame.discard(n)
    def pushBack(self, s:str) -> None:
        return self.curFrame.pushBack(s)

    def topOff(self, n:int=None) -> int:
        """Close until not at EOF, then top off first remaining frame.
        """
        if not n: n = self.bufSize
        while self.entStack:
            if not self.curFrame.noMoreToRead: self.curFrame.topOff(n)
            if self.curFrame.bufLeft > 0: break
            self.close()
        return 0 if not self.entStack else self.curFrame.bufLeft

    def skipSpaces(self, allowComments:bool=False, allowParams:bool=False) -> None:
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
            elif c == "-" and self.options.fragComments and allowComments:
                mat = self.readRegex(r"^--([^-]|-[^-])+--")
                if not mat: return
                self.bufPos += len(mat.group())
                com = mat.group(1)
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
        return

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
        self.open(space=EntitySpace.PARAMETER, name=pename)
        self.entStack[-1].skipSpaces()
        return

    def readQLit(self, ss:bool=True, keepPunc:bool=False) -> str:
        """TODO: Who exands stuff inside qlits???? Do one pass at end?
        """
        #lg.info("*** %s, buf '%s'.", callerNames(), self.bufSample)
        if ss: self.skipSpaces()  # TODO allowParams=True ??? SGML only?
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

        self.discard()
        dat = self.readToString(closeQ, consumeEnder=True)
        if dat is None:
            self.SE("Unclosed quoted string.")
        # TODO Only do PEntities if in subset, not in document.
        dat = self.expandPEntities(dat)
        if keepPunc: return openQ + dat + closeQ
        return dat

####################### Move to stackreader


    def readNameGroup(self, ss:bool=False) -> List:
        """Allows and mix of [&|,] or space between names. This if for;
            * SGML-style <!ELEMENT (i, b, tt, mono) #PCDATA>
            * Parser feature 'simultaneous': <a|b|c>
        This is slightly too permissive.
        This discard inter-name operators, so don't use for content models.
        """
        #lg.info("*** %s, buf '%s'.", callerNames(), self.bufSample)
        ngo = self.readConst("(", ss)
        if ngo is None: return None
        names = []
        while (True):
            self.skipSpaces(allowParams=True)
            name = self.readName()
            if name is None:
                self.SE("Expected a name in name group.")
            names.append(name)
            self.skipSpaces(allowParams=True)  # TODO
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
        #lg.info("*** %s, buf '%s'.", callerNames(), self.bufSample)
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
        #lg.info("*** %s, buf '%s'.", callerNames(), self.bufSample)
        if not self.readConst("<?xml", ss=False, thenSp=True): return None
        props = { "version":"1.0", "encoding":"utf-8", "standalone":"yes" }
        while (True):
            aname, avalue, _ = self.readAttr(ss=True)
            if aname is None: break
            if aname in ("version", "encoding", "standalone"):
                props[aname] = avalue
            else:
                self.setOption(aname, avalue)
        if not self.readConst("?>", ss=True):
            self.SE(f"Unterminated XML DCL, read {repr(props)}.")
        self.doCB(SaxEvent.XMLDCL, props["version"], props["encoding"], props["standalone"])
        return props

    def readPI(self) -> (str, Union[str, Dict]):                # <?tgt data??>
        #lg.info("*** %s, buf '%s'.", callerNames(), self.bufSample)
        pio = self.readConst("<?", ss=True)
        if pio is None: return None, None
        piTarget = self.readName()
        if self.options.piAttr:
            piData = self.readAttrs(ss=True)
            # TODO What about entity refs?
            if not self.readConst("?>", ss=True): self.SE("Unterminated PI.")
        else:
            piData = self.readToString("?>", consumeEnder=True)
            if piData is None: self.SE("Unterminated PI.")
        return piTarget, piData

    def readComment(self) -> str:                               # <!-- txt -->
        lg.info("*** %s, buf '%s'.", callerNames(), self.bufSample)
        como =  self.readConst("<!--", ss=True)
        if como is None and self.options.emComments: como = self.readConst("<!—", ss=False)
        if como is None: return None
        if self.options.emComments:    # TODO Break if internal --
            comData = self.readToAnyOf(["-->", "—>"], consumeEnder=True)
        else:
            comData = self.readToString("-->", consumeEnder=True)
        if comData is None:
            self.SE("Unterminated Comment.")
        return comData

    def readNotationDcl(self) -> (str, str, Union[str, List]):  # <!NOTATION>
        #lg.info("*** %s, buf '%s'.", callerNames(), self.bufSample)
        if self.readConst("<!NOTATION", thenSp=True) is None: return None
        name = self.readName(ss=True)
        #lg.info("Got notation '%s', at %s", name, self.bufSample)
        publicId, systemId = self.readLocation()
        #lg.info("    Got pub '%s', sys '%s'.", publicId, systemId)

        if publicId is None and systemId is None: self.SE(
            f"Expected PUBLIC or SYSTEM identifier at {self.bufSample}.")
        if not self.readConst(">"): self.SE(
            "Expected '>' for NOTATION dcl at {self.bufSample}.")
        return (name, publicId, systemId)

    def readLocation(self) -> (str, Union[str, List]):          # PUBLIC/SYSTEM
        """The PUBLIC "" "" or SYSTEM "" syntax.
        Note: This returns the SYSTEM ID as a list iff 'multiPath' is on.
        """
        #lg.info("*** %s, buf '%s'.", callerNames(), self.bufSample)
        publicId = ""
        systemIds = []
        #lg.info("readloc, at %s", self.bufSample)
        if self.readConst("PUBLIC", ss=True):
            #lg.info("PUBLIC")
            publicId = self.readQLit(ss=True)
            systemIds = [ self.readQLit(ss=True) ]
        elif self.readConst("SYSTEM"):
            #lg.info("SYSTEM")
            systemIds = [ self.readQLit(ss=True) ]
            if self.options.multiPath:
                while (s := self.readQLit(ss=True)):
                    systemIds.append(s)
        else:
            return None, None
        if self.options.multiPath: return (publicId, systemIds)
        return (publicId, systemIds[0])

    def readElementDcl(self) -> (                               # <!ELEMENT>
        List, Model, bool, bool, List, List):
        """Returns tuple of:
            [name] being declared
            Model tokens or object
            omitStart
            omitEnd
            [inclusions]
            [exclusions]
        """
        #lg.info("*** %s, buf '%s'.", callerNames(), self.bufSample)
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
                self.discard()
                mixins = self.readNameGroup()
                if mixins is None: self.SE(
                    "Expected name group after '+' for inclusions.")
                inclusions = mixins
            if self.peek() == "-":
                self.discard()
                mixins = self.readNameGroup()
                if mixins is None: self.SE(
                    "Expected name group after '-' for exclusions.")
                exclusions = mixins

        if not self.readConst(">"): self.SE("Expected '>' for ELEMENT dcl.")
        return (names, model, omitStart, omitEnd, inclusions, exclusions)

    def readModel(self) -> Model:                               # EMPTY | (...)
        """Read a parenthesized content model OR a declared content keyword.
        """
        #lg.info("*** %s, buf '%s'.", callerNames(), self.bufSample)
        mat = self.readRegex(r"#?\w+\b", ss=True)
        if mat:
            try:
                contentType = ContentType(mat.group().lstrip("#"))
                return contentType  #Model(contentType=contentType)
            except ValueError:
                self.SE("Unrecognized declared content keyword '{mat.group}'.")
        mtokens = self.readModelGroup(ss=True)
        if mtokens is None: return None
        return ''.join(mtokens)  #Model(tokens=mtokens)

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
                self.discard()
                tokens.append(c); depth += 1
            elif c == ")":
                self.discard()
                tokens.append(c); depth -= 1
                if depth == 0: break
            elif c in "|,&":
                self.discard()
                tokens.append(c)
            elif c in "+?*":
                self.discard()
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
        self.discard()
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
                            spam    ENTITY      #FIXED "chap1">
        """
        #lg.info("*** %s, buf '%s'.", callerNames(), self.bufSample)
        if self.readConst("<!ATTLIST", thenSp=True) is None:
            return None
        self.skipSpaces()
        if self.options.groupDcl and self.peek() == "(":
            names = self.readNameGroup()
        elif self.options.globalAttr and self.peek() == "*":
            names = [ "*" ]
        else:
            names = [ self.readName() ]
        if names is None:
            self.SE("Expected an element name in ATTLIST.")

        atts = {}
        while (True):
            attDftKwd = dftVal = None
            if self.readConst(">", ss=True): break

            # Attribute name
            if self.options.anyAttr and self.readConst(anyAttrKeyword):
                attName = anyAttrKeyword
            else:
                attName = self.readName(ss=True)
            if attName is None:
                self.SE(f"Expected attribute name in ATTLIST for {names}.")

            # Attribute type or enumerated token list
            self.skipSpaces()
            if self.peek() == "(":
                attType = self.readModelGroup(ss=True)  # TODO: No nesting....
            elif not (attType := self.readName(ss=True)): self.SE(
                "Expected attribute type or enum-group.")
            elif attType not in self.attrTypes: self.SE(
                f"Unknown type '{attType}' for attribute '{attName}'." +
                f" Known: {list(self.attrTypes.keys())}.")

            # Attribute default
            self.skipSpaces(allowParams=True)
            c = self.peek()
            if c == "#":
                attDftKwd = self.consume()
                attDftKwd += self.readName() or ""
                if attDftKwd == fixedKeyword:
                    dftVal = self.readQLit(ss=True)
                elif attDftKwd not in sgmlAttrDefaults: self.SE(
                    f"Unknown attribute default '{attDftKwd}' for '{attName}'.")
            elif c in '"\'':
                dftVal = self.readQLit()
            atts[attName] = ( attName, attType, attDftKwd, dftVal)
            #lg.info("ATTLIST now at: %s", self.bufSample)

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
        #lg.info("*** %s, buf '%s'.", callerNames(), self.bufSample)
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
    def readStartTag(self, ss:bool=True) -> (Union[str, List], Dict, bool):
        """Returns a 3-tuple of:
            element type name (or a List if 'simultaneous' is set)
            dict of attributes
            whether it used empty-element syntax
        """
        #lg.info("*** %s, buf '%s'.", callerNames(), self.bufSample)
        if not self.readConst("<", ss): return None, None, None
        name = self.readName(ss)
        if name is None and self.options.simultaneous:  # <a|b...>
            name = self.readNameGroup()
            if self.options.elementFold:
                for i in range(len(name)):
                    name[i] = self.options.elementFold.normalize(name[i])
        elif name is None:
            self.SE("Expected name in start-tag.")
        elif self.options.elementFold:
            name[i] = self.options.elementFold.normalize(name)

        attrs = self.readAttrs(ss=ss)

        empty = False
        if self.readConst("/>", ss): empty = True
        elif self.readConst(">", ss): empty = False
        else: self.SE("Unclosed start-tag for '{name}'.")

        # Validation (content model checked later, once element is complete)
        elDcl = None
        if self.doctype and name in self.doctype.elementDefs:
            elDcl = self.doctype.elementDefs[name]
        if not elDcl:
            if self.options.valElementNames:
                self.VE("Undeclared element '{name}'.")
        else:
            self.doctype.applyDefaults(elDcl=elDcl, attrs=attrs)
            if self.options.valAttrTypes:
                for k, v in attrs.items():
                    if k not in elDcl.attributes: continue
                    if not elDcl.attributes.type: continue
                    badFacet = xsdtypes.facetCheck(v, elDcl.attributes.type)
                    if badFacet: self.VE(
                        "Attribute {k}=\"{v}\" of element type '{name}' violates "
                        "facet {badFacet} of XSD type {elKnown.attributes.type}.")
            elif self.options.valAttrNames:
                if not elDcl.attributes:
                    self.VE("No ATTLIST for element '{name}'.")
                for k, v in attrs.items():
                    if k in elDcl.attributes: continue
                    if "#anyAttr" in elDcl.attributes: continue
                    self.VE("Undeclared attribute '{k}' for element '{name}'.")

        self.doCB(SaxEvent.START, name, attrs, empty)
        if empty: self.doCB(SaxEvent.END, name)
        return name, attrs, empty

    def readAttrs(self, ss:bool=True) -> OrderedDict:
        """This is purely a syntax read, so it can be used for start-tags,
        but also for quasi-attribute lists such as the XML declaration,
        optional PIs declared to work like that, etc. No validation/types here.
        """
        #lg.info("*** %s, buf '%s'.", callerNames(), self.bufSample)
        attrs = OrderedDict()
        while (True):
            aname, avalue, _bang = self.readAttr(ss=ss)  # TODO Implement bang
            if aname is None: break
            if self.options.attrFold:
                aname = self.options.attrFold.normalize(aname)
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
        Does not do anything about attribute type.
        """
        #lg.info("*** %s, buf '%s'.", callerNames(), self.bufSample)
        if ss: self.skipSpaces()
        #lg.warning(f"readAttr, after ss, buf starts '{self.peek(10)}'.")
        bang = False
        if self.options.booleanAttr and self.peek() in "+-":
            which = self.consume()
            if not (aname := self.readName(ss)):
                self.SE("Expected name after +/- for boolean attr.")
            lg.warning("Got boolean attr prefix '%s' for '%s'.", which, aname)
            return (aname, "1" if (which == "+") else "0", False)

        aname = self.readName(ss)
        if not aname:
            return (None, None, bang)
        #lg.warning(f"Attr name '{aname}'.")

        # TODO Add bangAttrType !typename=...
        if self.options.bangAttr and self.readConst("!=", ss):  # Set default
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
        #lg.info("*** %s, buf '%s'.", callerNames(), self.bufSample)
        if self.options.emptyEnd and self.readConst("</>"):
            name = self.tagStack.topName
            if not name: self.SE("</> with nothing open")
            self.doCB(SaxEvent.END, name)
            return name
        if not self.readConst("</", ss):
            raise DOMException("readEndTag called but at '{self.bufSample}'.")

        name = self.readName(ss)
        if not name and self.options.simultaneous:
            name = self.readNameGroup()  # TODO ??? </(x|y)> or something else?
        if not name and self.options.emptyEnd:
            name = self.tagStack.topName
        if not name:
            self.SE("Expected name in end-tag")
        if self.options.elementFold:
            if len(name) == 1:
                name = self.options.elementFold.normalize(name)
            else:
                for i in range(len(name)):
                    name[i] = self.options.elementFold.normalize(name[i])

        if not self.readConst(">", ss):
            self.SE(f"Unclosed end-tag for '{name}'.")
        self.doCB(SaxEvent.END, name)
        return name

    def readCDATA(self, ss:bool=True) -> str:
        """This optionally recognizes the full set of SGML marked section
        keywords, but they're not all fully implemented yet.  TODO
        Simple ones like IGNORE and CDATA are done entirely here, and
        consume the ]]>.
        Ones that require parsing (INCLUDE, TEMP, RCDATA) are pushed onto
        a stack, which should be popped when we see the ]]>.
        """
        #lg.info("*** %s, buf '%s'.", callerNames(), self.bufSample)
        MSKeys = {
            "CDATA": 1,
            "RCDATA": 2,
            "IGNORE": 3,
            "INCLUDE": 4,
            "TEMP": 5,
        }
        if not self.readConst("<![", ss):
            return None

        # TODO allowParams
        if not (keys := self.readToString("[")):
            self.SE("Unfinished marked section start.")
        topKey = ""
        if self.options.keywordFold: keys = keys.upper()
        for key in self.expandPEntities(keys).split():
            if not topKey or MSKeys[key] < MSKeys[topKey]: topKey = key

        if topKey == "CDATA":
            # In XML these aren't nestable.
            data = self.readToString("]]>", consumeEnder=True)
            if not data: self.SE("Unclosed CDATA section.")
            self.doCB(SaxEvent.CDATA)
            self.doCB(SaxEvent.CHAR, data)
            self.doCB(SaxEvent.CDATAEND)
            return data
        elif not self.options.MSTypes:
            self.SE(f"Found '<![' but with keyword '{topKey}', not '<![CDATA['.")
        # TODO Unfinished. rcdata is easy; include/temp are a pain
        elif topKey == "IGNORE":
            self.readToString("]]>", consumeEnder=True)
            # self.readToAny([ "<![", "]]>" ], consumeEnder=True)
        elif topKey == "RCDATA":
            raise NSuppE(f"Unsupported SGML MS Keyword {topKey}")  # TODO
        elif topKey == "INCLUDE" or topKey == "TEMP":
            self.msStack.append(topKey)
            raise NSuppE(f"Unsupported SGML MS Keyword {topKey}")
        else:
            raise NSuppE(f"Unknown SGML MS Keyword {topKey}")

    @property
    def ignoring(self) -> bool:
        """Are we in an ignored MS?
        """
        if not self.msStack or self.msStack[-1] != "IGNORE": return False
        return True

    @property
    def recognizePointy(self) -> bool:
        """These all work the same: tags and extended tags, pi, comment, MS, DCL.
        """
        if not self.msStack: return True
        if self.msStack[-1] in [ "CDATA", "IGNORE", "RCDATA" ]: return False
        return True

    @property
    def recognizeEntities(self) -> bool:
        """Are ent refs allowed? Not CDATA or IGNORE MS.
        """
        if not self.msStack: return True
        if self.msStack[-1] in [ "CDATA", "IGNORE" ]: return False
        return True

    def issueText(self, buf:List) -> None:
        """Called whenever we hit markup, to issue buffered text as a SAX event.
        Not called at \\n or entity refs, unless options.expatBreaks.
        """
        if not buf: return
        self.doCB(SaxEvent.CHAR, ''.join(buf))
        buf.clear()


    ###########################################################################
    #
    def parseTop(self) -> Document:
        """Parse the start of an XML document, up through the declaration
        subset (the stuff between [] in the DOCTYPE). Return before actually
        parsing the document instance (caller can do parseDocument() for that).

        TODO Fix API so can use as just a normal parse/parse_string.
        """
        lg.info("\n" + ("#" * 60) + " parseTop()")
        #import pudb; pudb.set_trace()
        self.doCB(SaxEvent.DOC)
        _props = self.readXmlDcl()

        e = self.readConst("<!DOCTYPE", ss=True, thenSp=True)
        if e:
            doctypeName = self.readName(ss=True)
            if doctypeName is None:
                self.SE("Expected document type name in DOCTYPE")
            self.skipSpaces()
            publicId, systemId = self.readLocation()
            self.skipSpaces()
            schemaNotation = "DTD"
            if self.options.schemaType and self.readConst("NDATA"):
                schemaNotation = self.readName()
                if schemaNotation is None: self.SE(
                    "No notation name for schema after DOCTYPE...NDATA")

            self.doCB(SaxEvent.DOCTYPE, doctypeName, publicId, systemId)
            # TODO handle external schema
            if self.peek(1) == "[":
                self.parseSubset()
            if not self.readConst(">", ss=True):
                self.SE("Expected '>' to end DOCTYPE")
            self.doCB(SaxEvent.DOCTYPEEND)

        self.parseDocument()

    def parseSubset(self):
        if not self.readConst("["): self.SE("Missing subset open")

        while True:  # SUBSET
            lg.info("** READING: %s", self.bufSample)
            self.skipSpaces(allowParams=True)  # TODO add to buf? Not for subset
            delim, nextChar = self.peekDelimPlus()
            if delim in [ "<!--", "<!\u2014" ]:                     # COM
                if txt := self.readComment():
                    self.doCB(SaxEvent.COMMENT, txt)
            elif delim == "<![":                                    # MS
                if txt := self.readCDATA():
                    self.doCB(SaxEvent.CDATA, txt)
                    break
            elif delim == "<!" and nextChar in "EAN":               # DCL
                if e := self.readElementDcl():
                    self.doCB(SaxEvent.ELEMENTDCL, e[0], e[1])
                elif e := self.readAttListDcl():
                    # TODO by attr?
                    self.doCB(SaxEvent.ATTLISTDCL, e[0], e[1])
                elif e := self.readEntityDcl():
                    self.doCB(SaxEvent.ENTITYDCL, *e)
                elif e := self.readNotationDcl():
                    self.doCB(SaxEvent.NOTATIONDCL, *e)
            elif delim == "<?":                                     # PI
                if pair := self.readPI():
                    self.doCB(SaxEvent.PROC, *pair)
            elif delim == "%":                                      # %ENT
                continue
            elif delim == "]]>":                                    # MSC
                self.msStack.pop()
            elif delim.startswith("]"):                             # SUBSET END
                self.discard(1)
                return
            else:
                if not self.entStack:
                    self.SE("Unexpected EOF in DOCTYPE, no more input frames")
        self.doCB(SaxEvent.DOCEND)

    def parseDocument(self) -> None:
        """Starts after parseTop.
        TODO Better to maintain bits for < & \\ recog?
        """
        buf = []  # Use List for performance
        while c := self.peek(1) is not None:
            delim, nextChar = self.peekDelimPlus()
            if not delim:
                c = self.consume(1)
                if self.ignoring: continue
                if c == "\n" and self.options.expatBreaks: self.issueText(buf)
                buf.append(c)
                continue
            c = delim[0]; c2 = delim[1] if len(delim)>1 else ""
            if c == "&" and self.recognizeEntities:             # ENTREF
                if self.options.expatBreaks: self.issueText(buf)
                self.discard()
                if self.readConst("#"):
                    pass  # TODO
                elif name := self.readName(ss=False):
                    if not self.readConst(";"):
                        self.SE(f"Expected ';' after entity name '{name}'.")
                    if self.options.entityFold:
                        name = self.options.entityFold.normalize(name)
                    if self.options.htmlNames and name in name2codepoint:
                        buf.append(chr(name2codepoint[name]))
                    if (self.options.unicodeNames
                        and (cp := uname2codepoint(name))):
                        buf.append(chr(cp))
                    elif name in self.sdataDefs:
                        buf.append(self.sdataDefs[name])
                    else:
                        self.open(EntitySpace.GENERAL, name)
                else:
                    self.SE("Expected '#' or name after '&'.")

            # TODO CDATA, IGNORE?
            elif c == "<":                                      # MARKUP
                self.issueText(buf)
                if c2 == "/":                                   # ENDTAG
                    e = self.readEndTag()
                    if not e: self.SE("Expected name after '</'.")
                    if self.options.elementFold:
                        e = self.options.elementFold.normalize(e)
                    if self.options.olist:
                        foundAt = None
                        i = 0
                        for i in reversed(range(len(self.tagStack))):
                            if self.tagStack[i] == e:
                                foundAt = i
                                break
                        if foundAt is not None:
                            del self.tagStack[foundAt]
                            self.doCB(SaxEvent.END_OLIST, e)
                        else: self.SE(
                            f"Element to close not found in open-list: '{e}'.")
                    else:
                        top = self.tagStack.topName
                        if e and e != top: self.SE(
                            f"End-tag for {e}, but open are: {self.tagStack}.")
                        self.tagStack.pop()
                    self.doCB(SaxEvent.END, e)
                elif delim == "<!--" or (
                    self.options.emComments and delim == "<!\u2014"):
                    if e := self.readComment():                     # COMMENT
                        self.doCB(SaxEvent.COMMENT, e)
                    else:
                        self.SE("Invalid comment.")
                elif delim == "<![":
                    if e := self.readCDATA():                       # CDATA
                        self.doCB(SaxEvent.CDATA)
                        self.doCB(SaxEvent.CHAR, e or "")
                        self.doCB(SaxEvent.CDATAEND)
                    else:
                        self.SE("Invalid marked section.")
                elif c2 == "?":                                     # PI
                    if not (e := self.readPI()):
                        self.SE("Expected target and data after '<?'.")
                    self.doCB(SaxEvent.PROC, *e)
                elif c2 == "|":                                     # RESTART
                    if not self.tagStack:
                        self.SE("Can't re-start with nothing open.")
                    top = self.tagStack.topName
                    self.doCB(SaxEvent.END, top)
                    self.doCB(SaxEvent.START, top)
                elif c2 in "-+":                                    # Suspend/resume
                    self.discard(2)
                    e = self.readName
                    if e is None: self.SE(f"No name at '{c2}' in suspend/resume.")
                    if self.readConst(">", ss=True) is None:
                        self.SE(f"Unclosed suspend/resume for {e}.")
                    n = self.tagStack.rindex(e)
                    if not n: self.SE("Cannot suspect or resume '{e}' (not open).")
                    if c2 == "-":
                        self.doCB(SaxEvent.SUSPEND, e)
                        self.tagStack[n].suspend(self.entStack[-1].lineNum)
                    else:
                        self.doCB(SaxEvent.RESUME, e)
                        self.tagStack[n].resume(self.entStack[-1].lineNum)
                elif XStr.isXmlName(c2):                            # STARTTAG
                    e, attrs, emptySyntax = self.readStartTag()
                    if not (e): self.SE("Unexpected characters after '<'.")
                    #if self.doctype:
                    #    self.doctype.applyDefaults(e, attrs)  # TODO Attr Defaults
                    self.doCB(SaxEvent.START, e, attrs)
                    self.tagStack.append(e, self.entStack[i].lineNum)
                    if emptySyntax:  # <x/>
                        self.doCB(SaxEvent.END, e)
                        self.tagStack.pop()
                else:
                    self.SE("Unrecognized markup after '<'")

            elif delim == "]]>":                                # MSC
                if not self.msStack: self.SE("']]>' found outside MS.")
                del self.msStack[-1]

            elif self.options.backslash and c == "\\":          # \\xFF etc.
                c = self.readBackslashChar()
                if not self.ignoring: buf.append(c)

            else:                                               # CONTENT
                c = self.consume(1)
                if c == "\n" and self.options.expatBreaks: self.issueText(buf)
                if not self.ignoring: buf.append(c)

        self.issueText(buf)
        if self.tagStack:
            self.SE(f"Unclosed elements at EOF: {self.tagStack}.")
        self.doCB(SaxEvent.DOCEND)
        return


###############################################################################
#
def ParserCreate(
    encoding="utf-8",
    namespace_separator=None  # Leaves xmlns as attrs, and prefixes as-is.
    ) -> 'XSParser':
    return XSParser(encoding=encoding, namespace_separator=namespace_separator)

class XSParser(StackReader) :
    def __init__(self,
        encoding:str="utf-8",
        namespace_separator:str=None,
        options:Dict=None):
        self.encoding = encoding
        self.namespace_separator = namespace_separator

        self.sr = StackReader(options=options)
        self.errors:List[ErrorRecord] = []
        self.BOM = None
        self.sniffedEncoding = None
        self.setEncoding = None

    def Parse(self, s:str) -> None:
        if not isinstance(s, str) or not s.startswith("<"):
            raise SyntaxError("Parser not given a '<'-initial string.")
        self.sr.Parse(s)

    parse_string = ParseString = Parse

    def ParseFile(self, ifh:IO) -> None:
        """This is slightly awkward b/c we have to bootstrap the encoding.
        The XML dcl is define to be all ASCII, so works in almost any
        encoding (though beware UCS-2 and UCS-4). BUT there could be non-ASCII
        immediately after the "?.". And for files without an XML declaration
        (including external entities), we don't get any info at all.
        """
        if isinstance(ifh, str):
            lg.warning("ParseFile was given a str ('%s'), not on open file.", ifh)
            ifh = open(ifh, "rb")
        dclBytes, encoding = XSParser.sniffXmlDcl(ifh)
        self.sniffedEncoding = encoding or "utf-8"
        if not dclBytes:
            self.setEncoding = self.sniffedEncoding
        else:
            dclStr = dclBytes.decode(encoding=self.sniffedEncoding)
            mat = re.search(r"""\sencoding\s*=\s*('[^']*'|"[^"]*")""", dclStr)
            self.setEncoding = mat.group(1).strip("'\"") if mat else "utf-8"

        # Double-check that the encoding is known (else LookupError)
        codecs.lookup(encoding)
        self.sr.ParseFile(ifh)

    parse_file = ParseFile

    @staticmethod
    def sniffXmlDcl(ifh: IO) -> tuple[bytes, str | None]:
        """Sneak a look at the file. Returns (bytes_read, encoding).
        If an XML declaration is found, sets encoding based on leading bytes.
        If no XML declaration is found, returns (bytes_read, None).
        Does not parse out the 'encoding=xxx' part. Does not decode from bytes().
        """
        encoding = None

        # Read BOM if any, then "<?xml" (also if any)
        rawBuf = bytearray(ifh.read(2))
        if (rawBuf[0] == 0xFE and rawBuf[1] == 0xFF):  # UTF-16 BE
            encoding = "UTF-16BE"
            rawBuf.extend(ifh.read(5))
        elif (rawBuf[0] == 0xFF and rawBuf[1] == 0xFE):  # UTF-16 LE
            encoding = "UTF-16LE"
            rawBuf.extend(ifh.read(5))
        elif (rawBuf[0] == 0xEF and rawBuf[1] == 0xBB):  # Possible UTF-8
            third = ifh.read(1)
            if third == 0xBF:
                encoding = "UTF-8"
                rawBuf.extend(third + ifh.read(5))
        else:
            rawBuf.extend(ifh.read(3))

        if rawBuf == b"<?xml":
            encoding = encoding or "ASCII"
            # Read until end of XML declaration
            while True:
                b = ifh.read(1)
                if not b:  # EOF
                    break
                rawBuf.extend(b)
                if b == b">":
                    break
        elif rawBuf == b"\x4C\x6F\xA7\x94\x93":
            encoding = "EBCDIC"
        elif rawBuf[0] == 0:
            raise SyntaxError("Leading NUL -- UCS-2 or UCS-4 missing BOM?")

        return bytes(rawBuf), encoding

    @property
    def CurrentEntityName(self) -> str:
        return self.sr.entStack[-1].name

    @property
    def CurrentByteIndex(self) -> int:
        return self.sr.entStack[-1].fullOffset

    @property
    def CurrentLineNumber(self) -> int:
        return self.sr.entStack[-1].lineNum

    @property
    def CurrentColumnNumber(self) -> int:  # TODO
        return 0

    @property
    def ErrorCode(self) -> int:
        if not self.errors: return None
        return self.errors[-1].code

    @property
    def ErrorByteIndex(self) -> int:
        if not self.errors: return None
        return self.errors[-1].byteIndex

    @property
    def ErrorLineNumber(self) -> int:
        if not self.errors: return None
        return self.errors[-1].lineNumber

    @property
    def ErrorColumnNumber(self) -> int:
        if not self.errors: return None
        return self.errors[-1].columnNumber
