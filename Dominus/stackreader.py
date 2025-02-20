#!/usr/bin/env python3
#
# StackReader: An input module that handles inclusions, such as via entities.
# Original: multiXml written 2011-03-11 by Steven J. DeRose.
#
#pylint: disable=W1201
#
#import codecs
import os
import re
import logging
from typing import Union, List, Iterable, IO
import inspect

#import html
#from html.entities import name2codepoint  # codepoint2name

from xmlstrings import XmlStrings as XStr, CaseHandler, Normalizer
# UNormHandler, WSHandler,
#from saxplayer import SaxEvent
from basedomtypes import NSuppE  #, NMTOKEN_t, DOMException, SepChar
from documenttype import EntityDef  # EntitySpace, EntityParsing
#from documenttype import DocumentType, Model, RepType, ContentType  # ModelGroup
#import xsdtypes
#from xsdtypes import (sgmlAttrTypes, sgmlAttrDefaults, XSDDatatypes,
#    fixedKeyword, anyAttrKeyword)
#from basedom import Document

lg = logging.getLogger("StackReader")
logging.basicConfig(level=logging.INFO, format='%(message)s')

EOF = -1

__metadata__ = {
    "title"        : "StackReader",
    "description"  : "An input module that handles inclusions, such as via entities.",
    "rightsHolder" : "Steven J. DeRose",
    "creator"      : "http://viaf.org/viaf/50334488",
    "type"         : "http://purl.org/dc/dcmitype/Software",
    "language"     : "Python 3.7",
    "created"      : "2011-03-11",
    "modified"     : "2025-02-18",
    "publisher"    : "http://github.com/sderose",
    "license"      : "https://creativecommons.org/licenses/by-sa/3.0/"
}
__version__ = __metadata__['modified']


def callerNames(n1:int=3, n2:int=1) -> str:
    buf = ""
    for i in range(n1, n2, -1): buf += "." + inspect.stack()[i].function
    return buf


###############################################################################
# Support for recognizing Unicode character names (incl. abbreviation and
# ignoring case), as character reference entities.
#
# Note: It's possible, if unlikely, that someone declares an entity with
# the same abbreviated name as some Unicode character. If you're going to
# do that, don't enable the 'unicodeNames' option.
#
# Support planes past BMP?
# TODO Upgrade to a class or whole separate package and normalizer command?
# Could also normalize:
#    LATIN -> 0; CAPITAL LETTER -> UC; SMALL LETTER -> LC;
#    MODIFIER LETTER -> ML; WITH -> W; ....
#
abbrname2char = {}

def abbreviate(s:str, length:int=4) -> str:
    """Counting hyphen and space as separators, shorten all but the last
    token of a Unicode character name to the first 'length' chars. For n=4
    this only leads to 11 collisions in the BMP.
    """
    if " " not in s: return s
    s = s.replace("-", " ")  # E.g. CJK UNIFIED IDEOGRAPH-XXXX
    parts = s.rsplit()
    last = parts[-1]
    del parts[-1]
    return ' '.join(part[0:min(len(part), length)] for part in parts) + " " + last

def enameMatches(ename:str, uname:str) -> bool:
    """Return true if every token of the entity name is a prefix of
    the corresponding token of the unicode name (treating any runs of
    hyphen, underscore, space, and dot as equivalent to a space).
    This is used to distinguish among collisions (user could just add
    enough extra to disambiguate, and we'd catch it).
    """
    etokens = re.sub(r"[-. _]+", " ", ename).split()
    utokens = re.sub(r"[-. _]+", " ", uname).split()
    if len(etokens) != len(utokens): return False
    for i in range(len(utokens)):
        if not utokens[i].startswith(etokens[i]): return False
    return True

def uname2codepoint(name:str) -> int:
    """Suppport entity-like references to unicode names, treating all
    of [-. _] as synonyms for space.
    """
    import unicodedata

    # Allow xml name chars in place of space
    spaceName = re.sub(r"[-. _]+", " ", name.upper())

    # Try the full name first
    try:
        return unicodedata.lookup(spaceName)
    except KeyError:
        pass

    # Built our index of abbreviated names the first time it's needed.
    # In case of collisions, store all of them.
    if not abbrname2char:
        for cp in range(65534):
            try:
                fullname = unicodedata.name(chr(cp))
                abbr = abbreviate(fullname)
                if abbr not in abbrname2char:
                    abbrname2char[abbr] = cp
                else:  # COLLISION
                    if not isinstance(abbrname2char[abbr], list):
                        abbrname2char[abbr] = [ abbrname2char[abbr], cp ]
                    else:
                        abbrname2char[abbr].append(cp)
            except ValueError:
                continue

    # Abbreviate the name and look up.
    normname = abbreviate(name)
    if normname not in abbrname2char:
        raise SyntaxError("Unrecognized (unicode?) entity name '{name}'.")
    x = abbrname2char[normname]
    if isinstance(x, int): return x

    # Otherwise the fully-abbreviated form collided. But maybe the user
    # provided more than that to disambiguate. Let's see.
    matches = []
    for cp in x:
        if enameMatches(name, unicodedata.name(chr(cp))): matches.append(cp)
    if len(matches) == 1:
        return matches[0]
    elif len(matches) == 0:
        raise SyntaxError("No full match for (unicode?) entity name '{name}'.")
    else:
        raise SyntaxError("Unicode entity name '{name}' is ambiguous among [ %s ]."
            % (", ".join(unicodedata.name(chr(cp)) for cp in matches)))


###############################################################################
#
class InputFrame:
    """A (stackable) input source, which has a read buffer with position info,
    and the most basic read operations. This base class just takes a single
    string; subclasses extend to handle entities and files.

    This includes readers for basic items that are not allowed to break
    across entity boundaries, or recognize entity references within them.
    For example, name tokens, delimiter strings, numbers, qlits (which may
    have entity references but they'd be expanded later), etc.
    """
    def __init__(self, encoding:str="utf-8", bufSize:int=1024):
        self.encoding = encoding
        self.bufSize = max(bufSize, 512)
        self.buf = ""       # Data source
        self.bufPos = 0     # Next char to read from buf
        self.offset = 0     # Source offset to start of buf (see dropUsedPart()0
        self.lineNum = 0    # Numer of \n's we've read

        self.noMoreToRead = False

    def addData(self, literal:str=""):
        self.buf += literal

    def close(self) -> None:
        self.buf = None

    def clear(self) -> None:
        self.buf.truncate(0)
        # TODO Reset offset and lineNum?

    def __str__(self):
        return self.buf.getValue()

    def __bool__(self):
        return len(self.buf) > 0

    def __getitem__(self, ind:Union[int, slice]):
        if isinstance(ind, int):
            start = ind
            end = ind+1
        else:
            start = ind.start
            end = ind.end
            if ind.step: raise ValueError("step not supported.")

        return self.buf[start:end]

    def __setitem__(self, *args):
        raise NSuppE("No __setitem__ for now.")

    # def pushBack?

    @property
    def bufLeft(self) -> int:
        """This returns the amount left in the *currently loaded portion* (buf).
        Some subclasses (files) may have more out there to load.
        """
        return len(self.buf) - self.bufPos

    @property
    def fullOffset(self) -> int:
        """This is the global character offset to the read point.
        """
        return self.offset + self.bufPos

    @property
    def fullLineNum(self) -> int:
        """This is the global line number to the read point.
        """
        return self.lineNum + self.buf[0:self.bufPos].count("\n")

    def dropUsedPart(self) -> None:
        """Discard some buffer, AND move the offset of the start.
        (no-op for literal data source)
        """
        return

    def topOff(self, n:int=0) -> int:
        """For a literal as input source (the base class case), do nothing.
        Return how much data is left in the buffer.
        """
        return self.bufLeft

    def skipSpaces(self, allowComments:bool=True,
        allowPE:bool=False, allowGE:bool=False) -> None:
        """Calling this is key to keeping the buffer full.
        Since this is in EntityFrame, it doesn't handle parameter entities
        (they change the EntityFrame, so are handled one level up).
        XML eliminated in-markup --...-- comments and in-dlc %entitites.
        Returns: False on EOF, else True (whether or not anything was skipped)
        """
        while True:
            if self.bufLeft < self.bufSize>>2: self.topOff()
            if not self.bufLeft: return
            if self.buf[self.bufPos] in " \t\r\n":
                self.bufPos += 1
                if self.buf[self.bufPos] == "\n": self.lineNum += 1
            elif allowComments and self.peek(2) == "--":
                mat = self.readRegex(r"^--([^-]|-[^-])+--", self.buf[self.bufPos:])
                if not mat: return None
                self.bufPos += len(mat.group())
                self.lineNum += mat.group().count("\n")
                _comText = mat.group(1)
            elif allowPE and self.peek(1) == "%":
                raise NSuppE("param")
            elif allowGE and self.peek(1) == "&":
                raise NSuppE("general")
            else:
                break
        return

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
        But only if there are at least n available.
        No skipSpaces options here, it could get circular.
        Use discard() instead when the data isn't needed.
        """
        if self.bufLeft < n:
            self.topOff(n)
            if self.bufLeft < n: return None
        rc = self.buf[self.bufPos:self.bufPos+n]
        self.bufPos += n
        return rc

    def discard(self, n:int=1) -> None:
        """Same as consume except the characters aren't cast or returned.
        """
        if self.bufLeft < n:
            self.topOff(n)
            if self.bufLeft < n: return None
        self.bufPos += n
        return

    def pushBack(self, s:str) -> None:
        """You can push back as much as memory permits. But if what you push
        back isn't what you read, that may not be good. Real file reading
        will pick up once the buffer (including the pushBack) is exhausted.
        Barely used.
        """
        n = len(s)
        self.dropUsedPart()  # So offset gets updated
        self.lineNum -= s.count('\n')
        self.offset -= n
        self.buf = s + self.buf[self.bufPos:]
        self.bufPos = 0

    def readAll(self) -> str:
        """Read all that's left. Mainly for CDATA/SDATA entities.
        """
        rc = ""
        while (True):
            self.topOff()
            if self.bufLeft == 0: break
            rc += self.buf
            self.bufPos = len(self.buf)
        return rc

    def readConst(self, const:str, ss:bool=True,
        thenSp:bool=False, folder:Union[CaseHandler, Normalizer]=None) -> str:
        """Try to read a specific constant string and consume it.
        If 'ss' is set, skip whitespace first.
        If 'thenSP' is set, require whitespace after the const (for
        example, to ensure that it's a complete token).
        If 'folder' is set, use it for comparison, to ignore case.
        """
        if ss: self.skipSpaces()
        if self.bufLeft < len(const)+1:
            self.topOff()
            if self.bufLeft < len(const)+1: return None

        if (1):
            if folder: const = folder.normalize(const)
            rc = self.peek(len(const))  # TODO could be faster
            if folder: rc = folder.normalize(rc)
            if rc != const: return None
            if thenSp and not self.buf[self.bufPos+len(const)].isspace():
                return None
            self.bufPos += len(const)
            return rc
        else:  # TODO Try this for speed; do same in other places?
            failed = False
            for i, c in enumerate(const):
                if c == self.buf[self.bufPos+i]: continue
                if folder and folder.strcasecmp(c, self.buf[self.bufPos+i]) == 0:
                    continue
                failed = True
                break
            if failed: return None
            if thenSp and not self.buf[self.bufPos+len(const)].isspace():
                return None
            rc = self.buf[self.bufPos:self.bufPos+len(const)]
            self.bufPos += len(const)
            return rc

    _firstDelims = "<&%]\\"
    _allDelims = "<>[]\\/!?#|-+\u2014"  # & and % not ok in non-first pos.

    def peekDelimPlus(self, ss:bool=True) -> (str, str):
        """Return initial punctuation marks, and following character.
        TODO Maybe take % and & out of _allDelims?
        """
        if ss: self.skipSpaces()
        delimString = ""
        i = self.bufPos
        if self.buf[i] not in self._firstDelims: return None, None

        while (i < len(self.buf)):
            if self.buf[i] not in self._allDelims: break
            delimString += self.buf[i]
            i += 1
        return delimString, self.buf[i]

    hardBackslashes = {
        "\\n": "\n",
        "\\r": "\r",
        "\\t": "\t",
        "\\f": "\f",
        "\\v": "\v",
        "\\\\": "\\",
        "\\x": 2,
        "\\u": 4,
        "\\U": 8,
    }

    def readBackslashChar(self) -> str:
        """Only when 'backslash' option is set.
        \\z for unrecognized z just produces z.
        Does not yet support \\x{...}.
        """
        # no ss as we've already seen the \\?
        start = self.peek(2)
        if start not in InputFrame.hardBackslashes:
            self.discard(2)
            return start[1]
        x = InputFrame.hardBackslashes[start]
        if isinstance(x, str): return x
        self.discard(2)
        hexString = self.consume(x)
        c = chr(int(hexString, 16))
        if not XStr.isXmlChars(c): raise SyntaxError(
            "Backslash encoded a non-XML character (0x%s)." % (hexString))
        return c

    def readInt(self, ss:bool=True, signed:bool=True) -> int:
        """Read a (possibly signed) decimal int.
        """
        mat = self.readRegex(r"[-+]?\d+" if signed else r"\d+", ss=ss)
        if not mat: return None
        return int(mat.group(), 10)

    def readBaseInt(self, ss:bool=True) -> int:
        """Read any of 999, 0xFFF, 0o777, 0b1111.
        """
        mat = self.readRegex(r"0x[\da-f]+|0o[0-7]+|0b[01]+|[-+]?\d+",
            fold=True, ss=ss)
        if not mat: return None
        return int(mat.group())

    def readFloat(self, ss:bool=True, signed:bool=True,
        specialFloats:bool=False) -> float:
        """TODO: exponential notation?
        TODO: Consumes a sign even if no following number.
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
            if c.isdigit():
                fToken += self.consume()
            elif c == ".":
                if "." in fToken: break
                fToken += self.consume()
            c = self.peek()
        if fToken.strip("+-.") == "":
            self.pushBack(fToken)
            return None
        return float(fToken)

    def readName(self, ss:bool=True) -> str:
        """
        TODO Add options to allow/require initial "#"
        TODO Add option to require \\s, \\b, or \\W after? Meh.
        This doesn't recognize parameter entity refs. Must it?
        """
        #lg.info("*** %s, buf '%s'.", callerNames(), self.bufSample)
        #lg.warning(f"readName: buf has '{self.buf[self.bufPos:]}'.\n")
        # Not re.fullmatch here!
        mat = self.readRegex(XStr.QName_re, ss=ss)
        if not mat: return None
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
        This does not cross entity boundaries (up or down).
        TODO: Don't use this for marked sections.
        """
        rbuf = []
        while True:
            if self.bufLeft < self.bufSize>>2:
                self.topOff()
                if not self.bufLeft: return None, None
            ender, where = self.findFirst(self.buf, enders, self.bufPos)
            if ender is None:  # Keep going
                rbuf.extend(self.buf[self.bufPos:])
                self.discard(self.bufLeft)
                self.dropUsedPart()
                self.topOff()
            else:
                rbuf.extend(self.buf[self.bufPos:where])
                moveTo = where + (len(ender) if consumeEnder else 0)
                self.buf = self.buf[moveTo:]
                self.bufPos = 0
                return ''.join(rbuf), ender
        return ''.join(rbuf), None  # TODO Notify EOF

    def findFirst(self, s:str, targets:List, start:int) -> (str, int):
        """Return the index of the first occurrence of any of the strings
        in 'targets', that is part the 'start' point in the buffer.
        """
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
class FileFrame(InputFrame):
    def __init__(self, encoding:str="utf-8", bufSize:int=1024):
        super().__init__(encoding, bufSize)
        self.path = None
        self.ifh = None

    def addData(self, literal:str=""):
        raise AttributeError("Don't do that.")

    def addFile(self, theFile:Union[str, IO, EntityDef]=None):
        if isinstance(theFile, str):
            self.path = theFile
            self.ifh = open(theFile, "rb" )
        elif isinstance(theFile, EntityDef):
            self.path = self.findLocalPath(eDef=theFile)
            self.ifh = open(self.path, "rb" )
        else:
            self.ifh = theFile
            try:
                self.path = theFile.name
            except AttributeError:
                self.path = None
        self.topOff(n=self.bufSize)

    def close(self) -> None:
        self.ifh.close()
        self.ifh = None
        super().close()

    def findLocalPath(self, eDef:'EntityDef', dirs:List[str]=None, trace:bool=1) -> str:
        """Resolve a set of publicID/systemID(s) to an actual absolute path.
        TODO: Pulled from xsparser, finish integrating
        Who holds the catalog, pwd, whatever?
        """
        old_level = lg.getEffectiveLevel()
        if (trace): lg.setLevel(logging.INFO)

        if not eDef.systemId:
            raise IOError("No system ID for %s." % (eDef.entName))
        if isinstance(eDef.systemId, list): systemIds = eDef.systemId
        else: systemIds = [ eDef.systemId ]

        #lg.info("Seeking entity '%s'", eDef.entName)
        for systemId in systemIds:
            #lg.info("  System id '%s'", systemId)
            if os.path.isfile(systemId):
                #lg.info("    FOUND")
                lg.setLevel(old_level)
                return systemId
            if dirs:
                for epath in dirs:
                    cand = os.path.join(epath, systemId)
                    #lg.info("    Trying dir '%s'", cand)
                    if os.path.isfile(cand):
                        #lg.info("      FOUND")
                        lg.setLevel(old_level)
                        return cand
        raise OSError("No file found for %s (systemIds %s)."
            % (eDef.entName, systemIds))

    def dropUsedPart(self, allow:int=0) -> None:
        """Discard some buffer, AND move the offset of the start.
        TODO raise default 'allow'
        """
        if self.bufPos < allow: return
        self.lineNum += self.buf[0:self.bufPos].count('\n')
        self.offset += self.bufPos
        self.buf = self.buf[self.bufPos:]
        self.bufPos = 0

    def topOff(self, n:int=0) -> int:
        """Refill the buffer so has at least n characters available (if possible),
        and return how much is then available.
        We do not top off across entity boundaries here.
        If we already have enough data, do nothing. That way we can get called
        all the time at minimal cost.
        Read more data (if there is any), to get at least n available chars,
        and preferably a bunch more so we don't read/copy so often.
        If EOF happens first, buf ends up short.
        If EOF happens and there's nothing in buf, that's really EOF on the entity.
        """
        #lg.info("FileFrame.topOff, buf '%s'.", self.bufSample)
        n = max(n or (self.bufSize / 4), 80)
        if self.bufLeft > n or self.noMoreToRead:
            return self.bufLeft

        self.dropUsedPart()  # TODO Combine with newChars assign?
        newChars = self.ifh.read(self.bufSize)
        if not newChars:  # EOF reached
            self.noMoreToRead = True
            if not self.buf:  # No more data at all
                self.ifh.close()
            return self.bufLeft

        if isinstance(newChars, bytes):
            newChars = newChars.decode(self.encoding)
        if (self.encoding != "utf-8"):
            raise NSuppE("Unsupported encoding (for now)")
        self.buf += newChars

        return self.bufLeft


###############################################################################
#
class EntityFrame(FileFrame):
    """Used by EntityManager for one currently-open (non-SDATA) entity.
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
        if self.eDef.literal is not None:
            super().__init__(encoding=encoding)
            self.addData(self.eDef.literal)
            return

        path = self.findLocalPath(eDef)
        if not path:
            raise IOError("No file found for entity '%s'." % (eDef.name))

        # Entities may eventually be able to have their own encoding;
        # otherwise we use the overall one.
        curEncoding = self.eDef.encoding or encoding
        super().__init__(encoding=encoding)
        self.addFile(path)
        #self.ifh = codecs.open(path, "rb", encoding=curEncoding)
        self.topOff()
