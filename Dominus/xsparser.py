#!/usr/bin/env python3
#
# XSParser: An easily-tweakable XML parser, with DTD++ support.
# Original: multiXml written 2011-03-11 by Steven J. DeRose.
#
# See https://www.balisage.net/Proceedings/vol8/print/Sperberg-McQueen01/BalisageVol8-Sperberg-McQueen01.html
#
#pylint: disable=W1201
#
import codecs
import os
import re
import logging
from typing import Union, List, Dict, Tuple, Iterable, IO
from types import SimpleNamespace
from collections import OrderedDict
import inspect

#import html
from html.entities import name2codepoint  # codepoint2name

from xmlstrings import XmlStrings as XStr, CaseHandler, Normalizer
from saxplayer import SaxEvent
from basedomtypes import NSuppE, NMTOKEN_t, DOMException
from documenttype import EntitySpace, EntityParsing, EntityDef
from documenttype import Model, RepType, ContentType  # ModelGroup
from xsdtypes import sgmlAttrTypes, sgmlAttrDefaults, XSDDatatypes
from basedom import Document

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
        self.offset = 0     # Global source offset to start of buf
        self.lineNum = 0    # Numer of \n's we've read
        self.noMoreToRead = False

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

        return ''.join(self.buf[start:end])

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

    def dropUsedPart(self) -> None:
        if self.bufPos == 0: return 0
        del self.buf[0:self.bufPos]
        self.bufPos = 0

    def topOff(self, n:int=0) -> int:
        """For a literal as input source (the base class case), this
        does nothing.
        Return how much data is left in the buffer.

        TODO Better to have a settable reader that's just None here, but
        a file handle in subclass?
        """
        return self.bufLeft

    def skipSpaces(self, allowComments:bool=True,
        allowPE:bool=False, allowGE:bool=False) -> bool:
        """Calling this is key to keeping the buffer full.
        Since this is in EntityFrame, it doesn't handle parameter entities
        (they change the EntityFrame, so are handled one level up).
        XML eliminated in-markup --...-- comments and in-dlc %entitites.
        Returns: False on EOF, else True (whether or not anything was skipped)
        """
        while True:
            if self.bufLeft < self.bufSize>>2: self.topOff()
            if not self.bufLeft: return False
            if self.buf[self.bufPos] in " \t\r\n":
                self.bufPos += 1
                if self.buf[self.bufPos] == "\n": self.lineNum += 1
            elif allowComments and self.peek(2) == "--":
                mat = self.matchRegex(r"^--([^-]|-[^-])+--")
                if not mat: return None
                self.bufPos += len(mat.group(1))
                self.lineNum += mat.group(1).count("\n")
                _comText = mat.group(1)
            elif allowPE and self.peek(1) == "%":
                raise NSuppE("param")
            elif allowGE and self.peek(1) == "&":
                raise NSuppE("general")
            else:
                return True

    def peek(self, n:int=1) -> str:
        """Return the next n characters (or fewer if EOF is coming),
        without actually consuming them. No skipSpaces options here,
        it could get circular.
        """
        if self.bufLeft < n:
            self.topOff()
            if self.bufLeft < n: return None
        return ''.join(self.buf[self.bufPos:self.bufPos+n])

    def consume(self, n:int=1) -> str:
        """Same as peek except the characters really ARE consumed.
        But only if there are at least n available.
        No skipSpaces options here, it could get circular.
        Use discard() instead when the data isn't needed.
        """
        if self.bufLeft < n:
            self.topOff(n)
            if self.bufLeft < n: return None
        rc = ''.join(self.buf[self.bufPos:self.bufPos+n])
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
        self.dropUsedPart()  # So offsets get updated
        self.buf = list(s) + self.buf[self.bufPos:]
        self.bufPos = 0
        self.offset -= n
        self.lineNum -= s.count('\n')

    def readAll(self) -> str:
        """Read all that's left. Mainly for CDATA/SDATA entities.
        """
        rc = ""
        while (True):
            self.topOff()
            if self.bufLeft == 0: break
            rc += ''.join(self.buf)
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
        if ss:
            if not self.skipSpaces(): return None
        if self.bufLeft < len(const)+1:
            self.topOff()
            if self.bufLeft < len(const)+1: return None

        if (1):
            if folder: const = folder.normalize(const)
            rc = self.peek(len(const))  # TODO could be faster
            if folder: rc = folder.normalize(rc)
            if rc != const: return None
            if thenSp and not ''.join(self.buf[self.bufPos+len(const)]).isspace():
                return None
            self.bufPos += len(const)
            return rc
        else:  # TODO Try this for speed; do same in other places?
            failed = False
            for i, c in enumerate(const):
                if c == self.buf[self.bufPos+i]: continue
                if folder and folder.strcasecmp(c, self.buf[self.bufPos+i]): continue
            if failed: return None
            if thenSp and not self.buf[self.bufPos+len(const)].isspace(): return None
            rc = ''.join(self.buf[self.bufPos:self.bufPos+len(const)])
            self.bufPos += len(const)
            return rc

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
        if ss: self.skipSpaces()
        expr = r"[-+]?\d+" if signed else r"\d+"
        mat = self.matchRegex(expr)
        if not mat: return None
        tok = self.consume(len(mat.group()))
        return int(tok, 10)

    def readBaseInt(self, ss:bool=True) -> int:
        """Read any of 999, 0xFFF, 0o777, 0b1111.
        """
        if ss: self.skipSpaces()
        mat = self.matchRegex(r"0x[\da-f]+|0o[0-7]+|0b[01]+|[-+]?\d+", flags=re.I)
        if not mat: return None
        tok = self.consume(len(mat.group()))
        return int(tok)

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
        #lg.info("*** %s, buf '%s'.", callerNames(), self.nextStuff)
        if ss: self.skipSpaces()
        #lg.warning(f"readName: buf has '{self.buf[self.bufPos:]}'.\n")
        # Not re.fullmatch here!
        mat = self.matchRegex(XStr.isXmlQName_re)
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
        mat = self.matchRegex(regex, flags=re.I if fold else 0)
        if not mat: return None
        self.bufPos += len(mat.group())
        return(mat)

    def matchRegex(self, regex:Union[str, re.Pattern], flags:int=0) -> re.Match:
        """Find a regex match at current buffer pos.
        Factor this out because the buffer is actually a list, not a string.
        TODO faster...
        """
        return re.match(regex, ''.join(self.buf[self.bufPos:]), flags=flags)

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

    @property
    def nextStuff(self):
        endAt = min(len(self.buf), self.bufPos+70)
        return re.sub("\n", "\u240a", self.buf[self.bufPos:endAt])


###############################################################################
#
class StringFrame(InputFrame):
    def __init__(self, s:str="", encoding:str="utf-8", bufSize:int=1024):
        super().__init__(encoding, bufSize)
        self.buf = s
        self.noMoreToRead = True

    #def close(self) -> None:
    #    super().close()

class FileFrame(InputFrame):  # TODO: Integrate w/ InputFrame, findLocalPath
    def __init__(self, theFile:Union[str, IO],
        encoding:str="utf-8", bufSize:int=1024):
        super().__init__(encoding, bufSize)
        if isinstance(theFile, str):
            self.ifh = open(theFile, "rb" )
            self.path = theFile
        else:
            self.ifh = theFile
            try:
                self.path = theFile.name
            except AttributeError:
                self.path = None
        self.topOff(n=self.bufSize)

    def close(self) -> None:  # TODO: Integrate w/ InputFrame
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

        lg.info("Seeking entity '%s'", eDef.entName)
        for systemId in systemIds:
            lg.info("  System id '%s'", systemId)
            if os.path.isfile(systemId):
                lg.info("    FOUND")
                lg.setLevel(old_level)
                return systemId
            if dirs:
                for epath in dirs:
                    cand = os.path.join(epath, systemId)
                    lg.info("    Trying dir '%s'", cand)
                    if os.path.isfile(cand):
                        lg.info("      FOUND")
                        lg.setLevel(old_level)
                        return cand
        raise OSError("No file found for %s (systemIds %s)."
            % (eDef.entName, systemIds))

    def topOffOLD(self, n:int=0) -> int:
        """Refill the buffer so has at least n characters available (if
        possible; there might not be that much).
        Unlike the base class, with file i/o this does something.
        We do not top off across entity boundaries here.

        If we already have enough data, do nothing. That way we can get called
        all the time at minimal cost.
        Read more data (if there is any), to get at least n available chars.
        If EOF happens before n, buf ends up short.
        If EOF happens and there's nothing in buf, that's really EOF on the entity.
        """
        lg.info("FileFrame.topOff, buf at '%s'." % (self.buf[self.bufPos:min(len(self.buf), 70)]))
        if not n: n = self.bufSize
        if self.bufLeft > n: return self.bufLeft

        self.dropUsedPart()
        newChars = self.ifh.read(n)
        if isinstance(newChars, bytes):
            newChars = newChars.decode(self.encoding)
            lg.info("topOff: decoded newChars (%s), buf '%s'.", type(newChars), type(self.buf))
        if (self.encoding != "utf-8"):  # TODO
            raise NSuppE("Unsupported encodoing (for now)")  #.decode(encoding=self.encoding)
        self.buf += newChars
        if not self.buf:
            self.ifh.close()
            return 0  # EOF
        return self.bufLeft

    def topOff(self, n:int=0) -> int:
        """Refill the buffer so has at least n characters available (if possible).
        We do not top off across entity boundaries here.
        If we already have enough data, do nothing. That way we can get called
        all the time at minimal cost.
        Read more data (if there is any), to get at least n available chars.
        If EOF happens before n, buf ends up short.
        If EOF happens and there's nothing in buf, that's really EOF on the entity.
        """
        #lg.info("FileFrame.topOff, buf '%s'.", self.nextStuff)
        if not n: n = self.bufSize
        if self.bufLeft > n or self.noMoreToRead:
            return self.bufLeft

        self.dropUsedPart()
        newChars = self.ifh.read(n)
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
        path = self.findLocalPath(eDef)
        super().__init__(theFile=path, encoding=encoding)

        self.eDef = eDef
        if self.eDef.literal:
            self.buf = self.eDef.literal
        elif path:
            # Entities may eventually be able to have their own encoding;
            # otherwise we use the overall one.
            curEncoding = self.eDef.encoding or encoding
            lg.warning("encoding for %s ends up '%s'.", eDef.entName, curEncoding)
            self.ifh = codecs.open(path, "rb", encoding=curEncoding)
            self.topOff()


###############################################################################
#
class TSEntry:
    def __init__(self, name:str, lineNum:int):
        self.name = name
        self.lineNum = lineNum
        self.isSuspended = False

class TagStack(list):
    """Mainly keeps the stack of open element type names, but has room for
    extra info like where the element started.
    With extensions like OLIST and suspend/resume, it's not exactly a stack.
    """
    def __insert__(self, *args):
        raise NotImplementedError("No manual insert on TagStack.")

    def __extend__(self, *args):
        raise NotImplementedError("No manual extend on TagStack.")

    def __setitem__(self, *args):
        raise NotImplementedError("No manual __setitem__ on TagStack.")

    def append(self, name:str, lineNum:int=None):
        tsentry = TSEntry(name, lineNum)
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
    def __init__(self, rootPath:str=None, encoding:str="utf-8",
        handlers:Dict=None, entPath:List=None, bufSize:int=1024,
        options:Dict=None):
        self.rootPath = rootPath
        self.encoding = encoding
        self.handlers = handlers or {}  # keyed off saxplayer.SaxEvent
        self.entPath = entPath  # dirs to look in
        self.bufSize = bufSize

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
        self.rootDef = None
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
        self.options = SimpleNamespace(**{
            ### Size limits and security (these are XML compatible)
            "MAXEXPANSION": 1 << 20,# Limit expansion length of entities
            "MAXENTITYDEPTH": 1000, # Limit nesting of entities
            "charEntities": True,   # Allow SDATA and CDATA entities
            "extEntities": True,    # Allow external entity refs
            "netEntities": True,    # Allow off-localhost external entity refs
            "entDirs": [],          # Permitted dirs (subtrees) to get ents from

            ### Case and Unicode
            "elementFold": None,
            "attributeFold": None,  # (attribute NAMEs)
            "entityFold": None,
            "keywordFold": None,
            "uNormHandler": None,   #                                   TODO
            "wsDef": None,          # (XML default)                     TODO
            "radix": ".",           # Decimal point choice              TODO
            "noC1":  False,         # No C1 controls                    TODO

            ### Schemas
            "schemaType": "DTD",    # <!DOCTYPE foo SYSTEM "" NDATA XSD>
            "fragComments": False,  # In-dcl like SGML
            #"setDcls": False,       # <!ENTITY % soup SET (i b tt)>     TODO

            ### Elements
            "groupDcl": False,      # <!ELEMENT (x|y|z)...>
            "oflag": False,         # <!ELEMENT - O para...>
            "sgmlWord": False,      # CDATA, RCDATA, #CURRENT, etc.
            "mixel": False,         # Dcl content keyword ANYELEMENT    TODO
            "mixins": False,        # cf incl exceptions
            "repBrace": False,      # {min, max} for repetition
            "emptyEnd": False,      # </>
            "restart": False,       # <|> to close & reopen current element
            "simultaneous": False,  # <b|i>, </i|/b>
            "multiTag": False,      # <div/title>...</title/div>        TODO
            "suspend": False,       # <x>...<-x>...<+x>...</x>
            "olist": False,         # olist, not stack

            ### Attributes
            "globalAttr": False,    # <!ATTLIST * ...>
            "xsdType": False,       # XSD builtins for attribute types
            "xsdPlural": False,     # builtin types have plurals too    TODO
            "specialFloat": False,  # Nan, Inf, etc.  (not really needed?)
            "unQuotedAttr": False,  # <p x=foo>
            "curlyQuote": False,
            "booleanAttr": False,   # <x +border -foo>
            "bangAttr": False,      # != on first use to set dft
            "bangAttrType": False,  # !typ= to set datatype             TODO
            "coID": False,          # co-index logical elements frags   TODO
            "nsID": False,          # IDs can have ns prefix            TODO
            "stackID": False,       # ID is cat(anc:@id)                TODO

            ### Entities and special characters
            "htmlNames": False,      # Enable HtML/Annex D named char refs
            "unicodeNames": False,  # Enable Raku-like unicode entities
            "multiPath": False,     # Multiple SYSTEM IDs
            "multiSDATA": False,    # <!SDATA nbsp 160 msp 0x2003...>   TODO
            "backslash": False,     # \n \xff \uffff (not yet \\x{}

            ### Other
            "emComments": False,    # Treat emdash as -- for comments   TODO
            "piAttr": False,        # PI parsed like attributes.        TODO
            "piAttrDcl": False,     # <!ATTLIST ?target ...>            TODO
            "nsSep": ":",           #                                   TODO
            "nsUsage": None,        # justone, global, noredef, regular TODO
            "markedSectionTypes": False,
        })

        if options:
            for k, v in options.items():
                self.setOption(k, v)

        if self.options.xsdType:
            self.attrTypes = XSDDatatypes
        else:
            self.attrTypes = sgmlAttrTypes

        if rootPath:
            self.setupDocEntity(rootPath, encoding)
            self.parseTop()

    @property
    def nextStuff(self):
        if not self.entStack: return "[EOF]"
        frame = self.entStack[-1]
        endAt = min(len(frame.buf), frame.bufPos+70)
        return frame.buf[frame.bufPos:endAt]

    def setOption(self, oname:str, ovalue):
        if oname.startswith("_") or not hasattr(self.options, oname):
            raise ValueError(f"Unknown option '{oname}'.")
        curVal = getattr(self.options, oname)
        if (curVal is not None
            and not isinstance(ovalue, type(curVal))): raise TypeError(
            f"Unexpected value type {type(ovalue)} (not {type(curVal)}) for '{oname}'.")
        if (oname == "entDirs"):
            for adir in ovalue: assert os.path.isdir(adir)
        setattr(self.options, oname, ovalue)

    def SE(self, msg:str) -> None:
        """Deal with a syntax error.
        """
        raise SyntaxError(msg + " at \n$$$" + self.bufSample + "$$$")

    def doCB(self, typ:SaxEvent, *args) -> None:
        """Given an event type and its args, call the handler if any.
        """
        #msg = ""
        #if (args): msg = ", ".join(f"{x}" for x in args)
        lg.info("doCB for %s (-> %s()) %s", typ.name, typ.value, args)
        if hasattr(self, typ.value): cb = getattr(self, typ.name)
        elif hasattr(self, SaxEvent.DEFAULT.value): cb = getattr(self, SaxEvent.DEFAULT)
        else: return
        cb(args)
        self.totEvents += 1

    # TODO ???
    def setupDocEntity(self, rootPath:str, encoding:str="utf-8") -> None:
        assert len(self.entStack) == 0
        if not os.path.isfile(rootPath):
            raise IOError(f"File not found: {rootPath}.")
        self.rootDef = EntityDef(
            entName="_root",
            entSpace=EntitySpace.GENERAL,
            systemId=rootPath, encoding=encoding)
        self.rootFrame = EntityFrame(self.rootDef, encoding=encoding)
        self.entStack.append(self.rootFrame)

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
        if (self.options.entDirs):
            if "../" in eDef.systemID:  # TODO Resolve first
                if fatal: self.SE(
                    "'../' not allowed when entDirs option is set: " + eDef.systemID)
                return False
            found = False
            for okDir in self.options.entDirs:
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
        return (
            self.buf[self.bufPos-preLen:self.bufPos] +
            "^" +  # or "\uFE0E" +  # WHITE FROWNING FACE
            self.buf[self.bufPos:self.bufPos+postLen])

    # Forward small constructs to entity-frame-limited readers
    #
    def readConst(self, const:str, ss:bool=True, thenSp:bool=False) -> str:
        return self.curFrame.readConst(const, ss, thenSp)
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
    def matchRegex(self, regex:Union[str, re.Pattern], flags:int=0) -> re.Match:
        return self.curFrame.matchRegex(regex, flags=flags)

    def topOff(self, n:int=None) -> int:
        """Close until not at EOF, then top off first remaining frame.
        """
        if not n: n = self.bufSize
        while self.entStack:
            if not self.curFrame.noMoreToRead: self.curFrame.topOff(n)
            if self.curFrame.bufLeft > 0: break
            self.close()
        return 0 if not self.entStack else self.curFrame.bufLeft

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
            elif c == "-" and self.options.fragComments and allowComments:
                mat = self.matchRegex(r"^--([^-]|-[^-])+--")
                if not mat: return None
                self.bufPos += len(mat.group(1))
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
        self.open(space=EntitySpace.PARAMETER, name=pename)
        self.entStack[-1].skipSpaces()
        return

    def readQLit(self, ss:bool=True, keepPunc:bool=False) -> str:
        """TODO: Who exands stuff inside qlits???? Do one pass at end?
        """
        #lg.info("*** %s, buf '%s'.", callerNames(), self.nextStuff)
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
        dat = self.expandPEntities(dat)
        if keepPunc: return openQ + dat + closeQ
        return dat

    def readNameGroup(self, ss:bool=False) -> List:
        """Allows and mix of [&|,] or space between names. This if for;
            * SGML-style <!ELEMENT (i, b, tt, mono) #PCDATA>
            * Parser feature 'simultaneous': <a|b|c>
        This is slightly too permissive.
        This discard inter-name operators, so don't use for content models.
        """
        #lg.info("*** %s, buf '%s'.", callerNames(), self.nextStuff)
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
        #lg.info("*** %s, buf '%s'.", callerNames(), self.nextStuff)
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
        #lg.info("*** %s, buf '%s'.", callerNames(), self.nextStuff)
        if not self.readConst("<?xml", ss=False, thenSp=True): return None
        props = { "version":"1.0", "encoding":"utf-8", "standalone":"yes" }
        while (True):
            aname, avalue, _ = self.readAttr(ss=True)
            if aname is None: break
            if aname in ("version", "encoding", "standalone"):
                props[aname] = avalue
            elif aname in self.options:
                self.options[aname] = avalue  # TODO Type-check
            else:
                self.SE("Unrecognized item '{aname}' in XML DCL.")
        if not self.readConst("?>", ss=True):
            self.SE(f"Unterminated XML DCL, read {repr(props)}.")
        self.doCB(SaxEvent.XMLDCL, props["version"], props["encoding"], props["standalone"])
        return props

    def readPI(self) -> (str, Union[str, Dict]):                # <?tgt data??>
        #lg.info("*** %s, buf '%s'.", callerNames(), self.nextStuff)
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
        #lg.info("*** %s, buf '%s'.", callerNames(), self.nextStuff)
        como =  self.readConst("<!--", ss=True)
        if como is None: return None
        comData = self.readToString("-->", consumeEnder=True)
        if comData is None:
            self.SE("Unterminated Comment.")
        return comData

    def readNotationDcl(self) -> (str, str, str):               # <!NOTATION>
        #lg.info("*** %s, buf '%s'.", callerNames(), self.nextStuff)
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
        #lg.info("*** %s, buf '%s'.", callerNames(), self.nextStuff)
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
        #lg.info("*** %s, buf '%s'.", callerNames(), self.nextStuff)
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
        return (names, omitStart, omitEnd, model, inclusions, exclusions)

    def readModel(self) -> Model:                               # EMPTY | (...)
        """Read a parenthesized content model OR a declared content keyword.
        """
        #lg.info("*** %s, buf '%s'.", callerNames(), self.nextStuff)
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
        #lg.info("*** %s, buf '%s'.", callerNames(), self.nextStuff)
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
            attName = self.readName(ss=True)
            if attName is None:
                self.SE(f"Expected attribute name in ATTLIST for {names}.")

            self.skipSpaces()
            if self.peek() == "(":
                attType = self.readModelGroup(ss=True)  # TODO: No nesting....
            elif not (attType := self.readName(ss=True)): self.SE(
                "Expected attribute type or enum-group.")
            elif attType not in self.attrTypes: self.SE(
                f"Unknown type '{attType}' for attribute '{attName}'." +
                f" Known: {list(self.attrTypes.keys())}.")

            self.skipSpaces(allowParams=True)
            c = self.peek()
            if c == "#":
                attDftKwd = self.consume()
                attDftKwd += self.readName() or ""
                if attDftKwd not in sgmlAttrDefaults: self.SE(
                    f"Unknown attribute default '{attDftKwd}' for '{attName}'.")
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
        #lg.info("*** %s, buf '%s'.", callerNames(), self.nextStuff)
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
        #lg.info("*** %s, buf '%s'.", callerNames(), self.nextStuff)
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
        self.doCB(SaxEvent.START, name, attrs, empty)
        if empty:
            self.doCB(SaxEvent.END, name)
        return name, attrs, empty

    def readAttrs(self, ss:bool=True) -> OrderedDict:
        #lg.info("*** %s, buf '%s'.", callerNames(), self.nextStuff)
        attrs = OrderedDict()
        while (True):
            aname, avalue, _bang = self.readAttr(ss=ss)  # TODO Implement bang
            if aname is None: break
            if self.options.attributeFold:
                aname = self.options.attributeFold.normalize(aname)
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
        #lg.info("*** %s, buf '%s'.", callerNames(), self.nextStuff)
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
        #lg.info("*** %s, buf '%s'.", callerNames(), self.nextStuff)
        if self.options.emptyEnd and self.readConst("</>"):
            name = self.tagStack.topName
            if not name: self.SE("</> with nothing open.")
            self.doCB(SaxEvent.END, name)
            return name
        if not self.readConst("</", ss):
            raise DOMException("readEndTag called but not at '</'.")

        name = self.readName(ss)
        if not name and self.options.simultaneous:
            name = self.readNameGroup()  # TODO ??? </(x|y)> or something else?
        if not name and self.options.emptyEnd:
            name = self.tagStack.topName
        if not name:
            self.SE("Expected name in end-tag.")
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
        """
        #lg.info("*** %s, buf '%s'.", callerNames(), self.nextStuff)
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
        if self.readConst("CDATA["):  # TODO Case?
            # In XML these aren't nestable.
            data = self.readToString("]]>")
            if not data: self.SE("Unclosed CDATA section.")
            self.doCB(SaxEvent.CDATA)
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
            if topKey == "IGNORE":
                self.readToString("]]>", consumeEnder=True)
                # self.readToAny([ "<![", "]]>" ], consumeEnder=True)
            elif topKey == "CDATA":
                self.msStack.append(topKey)  # TODO keep which frame started, to balance
                data = self.readToString("]]>", consumeEnder=True)
                self.doCB(SaxEvent.CDATA)
                self.doCB(SaxEvent.CHAR, data)
                self.doCB(SaxEvent.CDATAEND)
                del self.msStack[-1]
            elif topKey == "RCDATA":
                raise NSuppE("Unsupported SGML MS Keyword {topKey}")
            elif topKey == "INCLUDE" or topKey == "TEMP":
                self.msStack.append(topKey)  # TODO keep which frame, to balance
                raise NSuppE("Unsupported SGML MS Keyword {topKey}")
            else:
                raise NSuppE("Unknown SGML MS Keyword {topKey}")
            self.msStack.pop()

    def parseTop(self) -> Document:
        """Parse the start of an XML document, up through the declaration
        subset (the stuff between [] in the DOCTYPE). Return before actually
        parsing the document instance (caller can do parseDocument() for that).

        TODO Fix API so can use as just a normal parse/parse_string.
        """
        lg.info("\n\n\n" + ("#" * 60))
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
            schemaNotation = "DTD"
            if self.options.schemaType and self.readConst("NDATA"):
                schemaNotation = self.readName()
                if schemaNotation is None: self.SE(
                    "No notation name for schema after DOCTYPE...NDATA")
            if self.peek(1) == "[":
                self.sawSubsetOpen = True
                self.discard(1)
            # TODO: Do something with a parsed schemaNotation
            self.doCB(SaxEvent.DOCTYPE, doctypeName, publicId, systemId)

        while True:                                                 # SUBSET
            #lg.info("** READING: %s", self.nextStuff)
            self.skipSpaces(allowParams=True)
            p = self.peek(2)
            if p[0] == "<":                                             # COM/DCL/MS
                if  p == "<!":
                    p3 = self.peek(3)[2]
                    if p3 == "-":                                       # COM
                        if e := self.readComment():
                            self.doCB(SaxEvent.COMMENT, e)
                    elif p3 == "[":                                     # MS
                        if e :=  self.readCDATA():
                            self.doCB(SaxEvent.CDATA, e)
                    elif p3 in "EAN":                                   # DCL
                        if e := self.readElementDcl():
                            self.doCB(SaxEvent.ELEMENTDCL, e)
                        elif e := self.readAttListDcl():
                            # TODO by attr?
                            self.doCB(SaxEvent.ATTLISTDCL, e)
                        elif e := self.readEntityDcl():
                            self.doCB(SaxEvent.ENTITYDCL, e)
                        elif e := self.readNotationDcl():
                            self.doCB(SaxEvent.NOTATIONDCL, e)
                elif p == "<?":                                         # PI
                    if e := self.readPI():
                        self.doCB(SaxEvent.PROC, e)
                else:
                    self.SE("Unexpected content in DOCTYPE after '<'.")
            elif p[0] == "%":                                           # %ENT
                continue
            elif p[0] == "]":                                           # MSC
                self.discard()
                if self.readConst(">", ss=True):
                    self.discard()
                    self.doCB(SaxEvent.DOCTYPEEND)
                    return
                self.SE("Expected '>' to end DOCTYPE.")
            elif p is None:                                             # EOF
                if not self.entStack:
                    self.SE("Unexpected EOF in DOCTYPE - no more input frames")
                else:
                    self.SE("Unexpected EOF in DOCTYPE")
            else:
                self.SE(f"Expected ']' or '<' in DOCTYPE, not '{p}'.")

        self.doCB(SaxEvent.DOCEND)


    ###########################################################################
    # This seems to be all we need atop the DTD/entity parser, to do documents.
    #
    @property
    def recognizeEntities(self) -> bool:
        if not self.msStack: return True
        if self.msStack[-1] in [ "CDATA", "IGNORE" ]: return False
        return True

    @property
    def identifyPointy(self) -> bool:
        """Determine whether to recognize a "<" we're at; and if so, what it is.
        Return None if not recognized, else the kind of SAX event.

        Also account for MS state:
                       TEMP/INCL  IGN   RCDATA  CDATA   SAX
            <X   START        +    -      -       -     StartElementHandler
            </   END other    +    -      -       -     EndElementHandler
            <+X  Resume       +    -      -       -     RESUME
            <?   PI           +    -      -       -     ProcessingInstructionHandler
            <!-- COMMENT      +    -      -       -     CommentHandler
            <![  MSO          +    -      -       -     StartCdataSectionHandler

        Following specifically end (or suspend) the current element,
        and are recognized even inside MS.

            </X  END current  +    +      +       +     EndElementHandler
            </>  END current  +    +      +       +     EndElementHandler
            <|>  RESTART      +    +      +       +     EndElementHandler, StartElementHandler
            <-X  Suspend      +    +      +       +     SUSPEND

        Just FYI:
            ]]>  MSCLOSE      +    +      +       +     EndCdataSectionHandler
            &...;             +    -      +       -     ---

        """
        regular = True
        if self.msStack and self.msStack[-1] not in [ "INCLUDE", "TEMP" ]: regular = False

        lead2 = self.peek(2)
        if len(lead2) < 2:
            self.SE("EOF right after '<'.")

        c2 = lead2[-1]
        if XStr.isXmlName(c2):                                  # STARTTAG
            if regular: return SaxEvent.START
        elif c2 == "/":                                         # ENDTAG
            if regular: return SaxEvent.END
            # read </\w+  ??
            top = self.tagStack.topName or ""
            tag = self.peek(len(top)+3)
            if tag[2:-1] in [ top, ""]: return SaxEvent.END
        elif c2 == "?":                                         # PI
            if regular: return SaxEvent.PROC
        elif c2 == "!":                                         # COM / MS / DCL
            if regular:
                if self.peek(4) == "<!--": return SaxEvent.COMMENT
                if self.peek(3) == "<![": return SaxEvent.START
                self.SE("<! but not a comment or MS.")
        elif self.options.restart and c2 == "|":                # RESTART
            return (SaxEvent.END, SaxEvent.START)  # TODO
        elif self.options.restart:
            if c2 == "-": return SaxEvent.SUSPEND               # SUSPEND
            if c2 == "+" and regular: return SaxEvent.RESUME
        return None

    @property
    def ignoring(self) -> bool:
        if not self.msStack or self.msStack[-1] != "IGNORE": return False
        return True

    def issueText(self, buf:List) -> None:
        """Called whenever we hit markup, to issue any buffered text.
        Presently, not called on \\n or entity refs, unlike expat.
        """
        if not buf: return
        self.doCB(SaxEvent.CHAR, ''.join(buf))
        buf.clear(0)

    def parseDocument(self) -> None:
        """Starts after parseTop.
        """
        buf = []
        while c := self.peek(1) is not None:
            # TODO Specials?
            if c == "&" and self.recognizeEntities:             # ENTREF
                # self.issueText(buf)  # expat would....
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

            elif c == "<":                                      # MARKUP
                self.issueText(buf)
                c2 = self.peek(2)[1:]
                pType = self.identifyPointy
                if pType == SaxEvent.END:                           # ENDTAG
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
                elif pType == SaxEvent.COMMENT:
                    if e := self.readComment():                     # COMMENT
                        self.doCB(SaxEvent.COMMENT, e)
                    else:
                        self.SE("Invalid comment.")
                elif pType == SaxEvent.CDATA:
                    if e := self.readCDATA():                       # CDATA
                        self.doCB(SaxEvent.CDATA)
                        self.doCB(SaxEvent.CHAR, e or "")
                        self.doCB(SaxEvent.CDATAEND)
                    else:
                        self.SE("Invalid marked section.")
                elif pType == SaxEvent.PROC:                        # PI
                    if not (e := self.readPI()):
                        self.SE("Expected target and data after '<?'.")
                    self.doCB(SaxEvent.PROC, *e)
                elif pType == SaxEvent.RESTART:                     # RESTART
                    if not self.tagStack:
                        self.SE("Can't re-start with nothing open.")
                    top = self.tagStack.topName
                    self.doCB(SaxEvent.END, top)
                    self.doCB(SaxEvent.START, top)
                elif pType in [ SaxEvent.SUSPEND, SaxEvent.RESUME ]: # Suspend/resume
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
                elif pType == SaxEvent.START:                        # STARTTAG
                    e, attrs, emptySyntax = self.readStartTag()
                    if not (e): self.SE("Unexpected characters after '<'.")
                    #if self.doctype:
                    #    self.doctype.applyDefaults(e, attrs)  # TODO Attr Defaults
                    self.doCB(SaxEvent.START, e, attrs)
                    self.tagStack.append(e, self.entStack[i].lineNum)
                    if emptySyntax:  # <x/>
                        self.doCB(SaxEvent.END, e)
                        self.tagStack.pop()

            elif c == "]" and self.peek(3) == "]]>":            # MSC
                if not self.msStack: self.SE("']]>' found outside MS.")
                del self.msStack[-1]

            elif self.options.backslash and c == "\\":          # \\xFF etc.
                c = self.readBackslashChar()
                if not self.ignoring: buf.append(c)

            else:                                               # CONTENT
                if not self.ignoring: buf.append(self.consume())

        self.issueText(buf)
        if self.tagStack:
            self.SE(f"Unclosed elements at EOF: {self.tagStack}.")
        self.doCB(SaxEvent.DOCEND)
        return


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
def ParserCreate(
    encoding="utf-8",
    namespace_separator=None  # Leaves xmlns as attrs, and prefixes as-is.
    ) -> 'XSParser':
    return XSParser(encoding=encoding, namespace_separator=namespace_separator)

class XSParser:
    def __init__(self,
        encoding:str="utf-8",
        namespace_separator:str=None):
        self.encoding = encoding
        self.namespace_separator = namespace_separator

        self.sr = StackReader()
        self.errors:List[ErrorRecord] = []
        self.BOM = None
        self.sniffedEncoding = None
        self.setEncoding = None

    def Parse(self, s:str) -> None:
        if not isinstance(s, str) or not s.startswith("<"):
            raise SyntaxError("Parse not given a '<'-initial string.")
        topFrame = StringFrame(s)

    parse_string = ParseString = Parse

    def ParseFile(self, ifh:IO) -> None:
        """This is slightly awkward b/c we have to bootstrap the encoding.
        The XML dcl is define to be all ASCII, so works in almost any
        encoding (though beware UCS-2 and UCS-4). BUT there could be non-ASCII
        immediately after the "?.". And for files without an XML declaration
        (including external entities), we don't get any info at all.
        """
        if isinstance(ifh, str):
            lg.warning("ParseFile was given a str ('{ifh}'), not on open file.")
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

        topFrame = FileFrame(ifh)

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
