#!/usr/bin/env python3
#
# StackReader: An input module that handles inclusions, such as via entities.
# Original: multiXml written 2011-03-11 by Steven J. DeRose.
#
#pylint: disable=W1201
#
#import codecs
import sys
import re
import logging
from typing import Union, List, Dict, Iterable, IO, Callable
from types import SimpleNamespace
import inspect

from runeheim import XmlStrings as Rune, CaseHandler, Normalizer  #, UNormHandler, WSHandler
from ragnaroktypes import NSuppE, ICharE , NMTOKEN_t, SepChar #, DOMException,
from documenttype import (
    EntityDef , EntitySpace,  # EntityParsing
    # ElementDef, ContentType, ModelGroup, Model, RepType,
    DocumentType)

lg = logging.getLogger("StackReader")
logging.basicConfig(level=logging.INFO, format='%(message)s')

EOF = -1

__metadata__ = {
    "title"        : "StackReader",
    "description"  : "An input module that handles includes, such as entities.",
    "rightsHolder" : "Steven J. DeRose",
    "creator"      : "http://viaf.org/viaf/50334488",
    "type"         : "http://purl.org/dc/dcmitype/Software",
    "language"     : "Python 3.11",
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
# ignoring case), as character references (~entities).
#
# Note: It's possible, if unlikely, that someone declares an entity with
# the same abbreviated name as some Unicode character. If you're going to
# do that, don't enable the 'unicodeNames' option. If it's a problem I can
# make sure that explicit dcls take priority.
#
# Cost/benefit to support planes past BMP?
# TODO Upgrade to a class with own normalizer command?
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

def elemNameMatches(elemName:str, uname:str) -> bool:
    """Return true if every token of the entity name is a prefix of
    the corresponding token of the unicode name (treating any runs of
    hyphen, underscore, space, and dot as equivalent to a space).
    This is used to distinguish among collisions (user could just add
    enough extra to disambiguate, and we'd catch it).
    """
    etokens = re.sub(r"[-. _]+", " ", elemName).split()
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
        raise SyntaxError(f"Unrecognized (unicode?) entity name '{name}'.")
    x = abbrname2char[normname]
    if isinstance(x, int): return x

    # Otherwise the fully-abbreviated form collided. But maybe the user
    # provided more than that to disambiguate. Let's see.
    matches = []
    for cp in x:
        if elemNameMatches(name, unicodedata.name(chr(cp))): matches.append(cp)
    if len(matches) == 1:
        return matches[0]
    elif len(matches) == 0:
        raise SyntaxError(f"No full match for (unicode?) entity name '{name}'.")
    else:
        raise SyntaxError(f"Unicode entity name '{name}' is ambiguous among [ %s ]."
            % (", ".join(unicodedata.name(chr(cp)) for cp in matches)))


###############################################################################
#
class InputFrame:
    """A (stackable) input source, which has a read buffer with position info,
    and the most basic read operations. This only reads simple things like
    n chars, a constant passed in (or one of a set passed in), etc.

    Nothing in here reads across frame boundaries (even readAll()).

    Nothing in here really knows any syntax rules except for whitespace.

    Readers for token-ish things like ints, qnames, entity references, qlits,
    etc. are handled higher up.
    """
    def __init__(self, encoding:str="utf-8", bufSize:int=1024,
        options:SimpleNamespace=None):
        self.encoding = encoding
        self.bufSize = max(bufSize, 512)
        self.options = options or SimpleNamespace()

        self.buf:str = ""           # Data buffer
        self.bufPos:int = 0         # Next char to read from buf
        self.offset:int = 0         # Source offset to start of buf (see dropUsedPart()
        self.lineNum:int = 1        # Number of \n's we've read
        self.spaceDef = " \t\r\n"
        self.newlineDef = "\\n"
        self.entDef = None          # If source is an entity, the definition
        self.path:str = None        # If a file, the path
        self.ifh:IO = None          # Open file handle if any

        self.noMoreToRead = False
        self._oldWay = True         # Config case-handling method

    def frameLoc(self) -> str:
        """Return a description of the location in this frame.
        (see also StackReader.wholeLoc).
        """
        entName = self.entDef.entName if self.entDef else "[NONE]"
        buf = "Line %5d of entity '%s'" % (self.lineNum, entName)
        if self.path: buf += f"(file '{self.path}')"
        return buf

    def description(self) -> str:
        """Make a string to describe/identify the frame, like in messages.
        """
        if self.entDef:
            p = "parameter " if self.entDef.space == EntitySpace.PARAMETER else ""
            return "%sentity %s" % (p, self.entDef.entName)
        elif self.path:
            return "file '%s'" % (self.path)
        else:
            return "string"

    def addEntity(self, entDef:EntityDef) -> None:
        self.entDef = entDef
        if entDef.literal is not None:
            if self.buf: self.buf += entDef.literal
            else: self.buf = entDef.literal
            return
        # Find the system object and attach
        path = self.entDef.source.findLocalPath(entDef=entDef)
        self.addFile(path)

    def addFile(self, theFile:Union[str, IO]) -> None:
        if isinstance(theFile, str):
            self.path = theFile
            self.ifh = open(theFile, "rb" )
        else:
            self.ifh = theFile
            try:
                self.path = theFile.name
            except AttributeError:
                self.path = None
        self.topOff(n=self.bufSize)

    def addData(self, literal:str="") -> None:
        self.buf += literal

    def close(self) -> None:
        self.buf = None
        if self.ifh:
            self.ifh.close(); self.ifh = None
        if self.entDef: self.entDef = None

    def clear(self) -> None:
        self.buf = ""
        self.bufPos = 0

    @property
    def bufLeft(self) -> int:
        """This returns the amount left in the *currently loaded portion* (buf).
        Some subclasses (files) may have more out there to load.
        """
        return len(self.buf) - self.bufPos

    @property
    def fullOffset(self) -> int:
        """The global character offset to the read point.
        """
        return self.offset + self.bufPos

    @property
    def fullLineNum(self) -> int:
        """The global line number to the read point.
        """
        return self.lineNum + self.buf[0:self.bufPos].count(self.newlineDef)

    def __bool__(self) -> bool:
        return self.bufLeft > 0

    def __str__(self) -> str:
        """The remaining part of the loaded buffer.
        """
        return self.buf[self.bufPos:]

    def __getitem__(self, ind:Union[int, slice]) -> str:
        """With lists or strings, out-of-bounds requests:
            raise IndexError for singletons like myString[999]
            return an empty list for ranges like myString[999:1000]
        We do the same.
        """
        if isinstance(ind, int):
            start = ind
            return self.buf[start]
        elif isinstance(ind, slice):
            start = ind.start
            stop = ind.stop
            if ind.step: raise IndexError("step not supported.")
            return self.buf[start:stop]
        else:
            raise TypeError(f"Only use int or slice, not {type(ind)}.")

    def __setitem__(self, *args) -> None:
        raise NSuppE("No __setitem__ for now.")

    def topOff(self, n:int=0) -> int:
        """Refill so at least n characters are available.
        If this source is just a literal string, does nothing.
        Return how much actually ends up being available.

        Drops any used part then loads bufSize chars; but only if
        avail < n, with n defaulting to bufSize/4, so we don't do i/o so often.
        TODO: not sure that really helps -- need to profile more

        If EOF happens first, buf ends up short.
        If EOF happens and there's nothing in buf, that's really end.
        Does NOT top off across entity boundaries.
         """
        if not self.ifh: return self.bufLeft

        #lg.info("InputFrame.topOff, buf '%s'.", self.bufSample)
        if not n: n = self.bufSize / 4
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
            raise NSuppE(f"Unsupported encoding '{self.encoding}' (for now).")
        if self.options.noC0 and re.search(Rune.c0NonXml_re, newChars):
            raise ICharE("C0 control characters are disabled.")
        if self.options.noC1 and re.search(Rune.c1_re, newChars):
            raise ICharE("C1 control characters are disabled. Is this CP1252?")
        if self.options.noPrivateUse and re.search(Rune.privateUse_re, newChars):
            raise ICharE("Private use characters are disabled.")
        self.buf += newChars
        return self.bufLeft

    def dropUsedPart(self, allow:int=100) -> None:
        """Discard some buffer, AND move the offset of the start.
        If the used part is smaller than 'allow', don't bother.
        """
        if self.bufPos < allow: return
        self.lineNum += self.buf[0:self.bufPos].count('\n')  # TODO Earlier?
        self.offset += self.bufPos
        self.buf = self.buf[self.bufPos:]
        self.bufPos = 0

    def skipSpaces(self,
        allowComments:bool=True,        # Can skip comments, too
        entOpener:Callable=None         # Can see entities?
        ) -> None:
        """Basically skip spaces, but at option also:
            * skip an embedded comment (for SGML not XML DTDs)
            * callback to expand if we hit an entity reference.
        TODO Add a way to return comment events.
        Calling this is key to keeping the buffer full.
        XML eliminated in-markup --...-- comments and in-dcl %entitites.
        Returns: False on EOF, else True (whether or not anything was skipped)
        """
        while True:
            if not self.bufLeft:
                self.topOff()
                if not self.bufLeft: return
            c = self.buf[self.bufPos]
            if c in self.spaceDef:
                if self.buf[self.bufPos] == self.newlineDef: self.lineNum += 1
                self.bufPos += 1
            elif entOpener and c in "%&":
                entOpener()            # TODO How to switch between & and %?
            elif allowComments and self.peek(2) == "--":  # TODO emComments
                mat = self.readRegex(StackReader.commExpr, self.buf[self.bufPos:])
                if not mat: return None
                self.bufPos += len(mat.group())
                self.lineNum += mat.group().count(self.newlineDef)
                _comText = mat.group(1)
            else:
                break
        return

    def peek(self, n:int=1) -> str:
        """Return the next n characters (or None if EOF is hit),
        without actually consuming them. No skipSpaces option here,
        it could get circular.
        """
        if self.bufLeft < n:
            self.topOff()
            if self.bufLeft < n: return None
        return self.buf[self.bufPos:self.bufPos+n]

    def consume(self, n:int=1) -> str:
        """Same as peek() except the characters really ARE consumed.
        """
        if self.bufLeft < n:
            self.topOff(n)
            if self.bufLeft < n: return None
        rc = self.buf[self.bufPos:self.bufPos+n]
        self.bufPos += n
        return rc

    def discard(self, n:int=1) -> None:
        """Same as consume() except the characters aren't cast or returned.
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
        self.dropUsedPart()  # updates offset
        self.lineNum -= s.count('\n')
        self.offset -= len(s)
        self.buf = s + self.buf[self.bufPos:]
        self.bufPos = 0

    def readConst(self, const:str, ss:bool=True,
        thenSp:bool=False, folder:Union[CaseHandler, Normalizer]=None) -> str:
        """Try to read a specific constant string and consume it.
        If 'ss' is set, skip whitespace first.
        If 'thenSP' is set, require whitespace after the const (for
        example, to ensure that it's a complete token).
        If 'folder' is set, use it for comparison, to ignore case.
        TODO: Generalize 'thenSP' to also do thenNonAl(num).
        """
        if ss: self.skipSpaces()
        if self.bufLeft < len(const)+1:
            self.topOff()
            if self.bufLeft < len(const): return None

        if self._oldWay:
            if folder: const = folder.normalize(const)
            rc = self.peek(len(const))  # TODO could be faster
            if folder: rc = folder.normalize(rc)
            if rc != const: return None
            if thenSp and not self.buf[self.bufPos+len(const)].isspace():
                return None
            self.bufPos += len(const)
            return rc
        else:  # TODO Try this for speed; do same in other places?
            for i, c in enumerate(const):
                if c == self.buf[self.bufPos+i]: continue
                if folder and folder.strcasecmp(c, self.buf[self.bufPos+i]) == 0:
                    continue
                return None
            if thenSp and not self.buf[self.bufPos+len(const)].isspace():
                return None
            rc = self.buf[self.bufPos:self.bufPos+len(const)]
            self.bufPos += len(const)
            return rc

    def readToString(self, ender:str, consumeEnder:bool=True) -> str:
        """Read to the given string. Nothing else is recognized.
        Unlike most readers, this one doesn't leave things unchanged
        if it fails, because failure means we hit EOF.
        For where you really, really have to have some stuff ended by this thing.
        """
        rbuf = []
        while True:
            if self.bufLeft < self.bufSize>>2:
                self.topOff()
                if not self.bufLeft: return None  # TODO Raise SE on readToString fail?
            where = self.buf.find(ender, self.bufPos)
            if where < 0:  # Keep going
                rbuf.extend(self.buf[self.bufPos:])
                self.discard(self.bufLeft)
                self.dropUsedPart()
                self.topOff()
            else:
                rbuf.extend(self.buf[self.bufPos:where])
                moveTo = where + (len(ender) if consumeEnder else 0)
                self.buf = self.buf[moveTo:]
                self.bufPos = 0
                break
        return ''.join(rbuf) or None

    def readAll(self) -> str:
        """Read all that's left IN THIS FRAME. Mainly for CDATA/SDATA entities.
        """
        rc = ""
        while (True):
            self.topOff()
            if self.bufLeft == 0: break
            rc += self.buf
            self.bufPos = len(self.buf)
        return rc


    ###########################################################################
    ### TOKEN LEVEL
    ###

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
        # no skipSpaces as we've already seen the \\?
        start = self.peek(2)
        if start is None or start[0] != "\\": return None
        if start not in InputFrame.hardBackslashes:
            self.discard(2)
            return start[1]
        x = InputFrame.hardBackslashes[start]
        if isinstance(x, str): return x
        self.discard(2)
        try:
            hexString = self.consume(x)
            c = chr(int(hexString, 16))
        except (TypeError, ValueError) as e:
            raise SyntaxError("Backslash hex code '{hexString}' invalid.") from e
        if not Rune.isXmlChars(c): raise SyntaxError(
            "Backslash encoded a non-XML character (0x%s)." % (hexString))
        return c

    def readNumericChar(self, ss:bool=True) -> str:
        """XML numeric char ref (not including named).
        """
        if ss: self.skipSpaces()
        if not self.readConst("&#"): return None
        base = 10
        if self.peek(1) in "xX":
            base = 16
            self.consume(1)
        n = self.readInt(ss=False, signed=False, base=base)
        if self.peek(1) != ";": raise SyntaxError(
            "Missing semicolon for numeric character ref (n = 0x%x)." % (n))
        self.consume(1)
        if n > sys.maxunicode: raise SyntaxError(
            "Numeric character ref (d%d, x%x) beyond Unicode range." % (n, n))
        return chr(n)

    def readBaseInt(self, ss:bool=True) -> int:
        """Read any of 999, 0xFFF, 0o777, 0b1111.
        """
        if ss: self.skipSpaces()
        start = self.peek(2)
        if start == "0x":   base = 16
        elif start == "0o": base = 8
        elif start == "0b": base = 2
        else:               base = 10
        if base != 10: self.consume(2)
        val = self.readInt(ss=False, signed=False, base=base)
        return val

    def readInt(self, ss:bool=True, signed:bool=True, base:int=10) -> int:
        """Read a (possibly signed) int in one of the usual bases.
        Returns the actual int value, not the string.
        """
        if base not in [ 2, 8, 10, 16 ]:
            raise ValueError(f"Unsupported base {base}.")
        okDigits = "0123456789ABCDEFabcdef"
        if base < 16: okDigits = okDigits[0:base]
        if ss: self.skipSpaces()

        # First make sure we've got an int to read
        c = self.peek()
        if c in okDigits:
            negated = False
        elif (signed and c in "-+" and self.peek(2)[1] in okDigits):
            self.consume()  # Just the sign
            negated = c == "-"
        else:
            return None

        # Now we're at the first digit -- skip any 0s and collect rest
        while self.peek() == "0":
            self.consume()
        buf = "0"
        while self.peek() in okDigits:
            buf += self.consume()
        val = int(buf, base)
        return -val if negated else val

    def readFloat(self, ss:bool=True, signed:bool=True,
        specialFloats:bool=False, exp:bool=False) -> float:
        """Read floats, optionally including IEEE specials (ignoring case),
         signs, and exponential notation.
        """
        if ss: self.skipSpaces()
        if specialFloats:
            if self.readConst("NaN", folder=CaseHandler.UPPER, thenSp=True):
                return float("NaN")
            if self.readConst("-Inf", folder=CaseHandler.UPPER, thenSp=True):
                return float("-Inf")
            if self.readConst("Inf", folder=CaseHandler.UPPER, thenSp=True):
                return float("Inf")
        intVal = self.readInt(signed=signed, base=10)
        if intVal is None: return None
        if self.readConst(".") is None: return float(intVal)
        fstr = "%d." % (intVal)
        while c := self.peek():
            if not c.isdigit(): break
            fstr += self.consume()
        if exp and self.peek(1) == "E":
            self.consume()
            expVal = self.readInt(signed=True, base=10) or 0
            return float(fstr) * 10**expVal
        return float(fstr)

    firstDelims = "<&%]\\"
    allDelims = "<>[]\\/!?#|-+\u2014"  # & and % not ok in non-first pos.

    def peekDelimPlus(self, ss:bool=True) -> (str, str):  # TODO To parser
        """Return initial punctuation marks, and following character.
        TODO Maybe take % and & out of allDelims?
        TODO Maybe move up to Token level?
        Don't trip over "</>", "<|>", etc.
        """
        if ss: self.skipSpaces()
        self.topOff(100)
        if self.bufLeft < 1: return None, None

        i = self.bufPos

        c = self.buf[i]
        if c not in self.firstDelims: return None, None

        delimString = ""
        while (True):
            delimString += c
            i += 1
            c = self.buf[i]
            if c not in self.allDelims: break
        return delimString, c

    def readName(self, ss:bool=True) -> str:
        """
        TODO Add options to allow/require initial "#"
        TODO Add option to require \\s, \\b, or \\W after? Meh.
        This doesn't recognize parameter entity refs. Must it?
        """
        if ss: self.skipSpaces()
        #lg.info("*** %s, buf '%s'.", callerNames(), self.bufSample)
        #lg.warning(f"readName: buf has '{self.buf[self.bufPos:]}'.\n")
        # Not re.fullmatch here!
        mat = self.readRegex(Rune.QName_re, ss=ss)
        if not mat: return None
        return mat.group()

    def readEnumName(self, names:Iterable, ss:bool=True) -> str:
        """See if the source starts with any of the strings.
        For an actual Enum, pass enumType.__members__.keys().
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
        Used for QName, SGML embedded comments, declared content, repetition flags.
        """
        if ss: self.skipSpaces()
        self.topOff()
        mat = re.match(regex, self.buf[self.bufPos:], flags=re.I if fold else 0)
        if not mat: return None
        self.bufPos += len(mat.group())
        return(mat)


###############################################################################
#
class StackReader:
    """Keep dictionaries of entities and notations, and a stack of
    open ones being read. Support very basic read operations (leave the
    fancy stuff for a subclass to add), and support extensions.

    TODO Maybe make this a subclass of InputFrame, which just is the innermost
    one, with links to the others. Except when it pops, the ref has to change
    """
    commExpr = r"^--([^-]|-[^-])+--"

    def __init__(self, encoding:str="utf-8",
        handlers:Dict=None, entDirs:List=None, bufSize:int=1024,
        options:Dict=None, path:str=None):
        if path: lg.info("\n******* StackReader for path '%s'.", path)
        self.bufSize = bufSize
        self.options = options
        self.path = path
        self.encoding = encoding
        self.handlers = handlers or {}  # keyed off saxplayer.SaxEvent
        self.entDirs = entDirs  # dirs to look in

        self.doctype = DocumentType()
        self.sdataDefs = {  # TODO Hook up dcls and a set method
            "lt":   "<",
            "gt":   ">",
            "amp":  "&",
            "quot": '"',
            "apos": "'",
        }

        self.spaces = {
            EntitySpace.GENERAL: {},
            EntitySpace.PARAMETER: {},
            EntitySpace.NOTATION: {},
        }

        # IO state
        self.rootFrame = None
        self.totLines = 0  # overall lines processed
        self.totChars = 0  # overall chars processed
        self.totEvents = 0

        self.frames:List[InputFrame] = []

    def open(self, frame:InputFrame) -> InputFrame:
        self.frames.append(frame)

    def isEntityOpen(self, space:EntitySpace, name:NMTOKEN_t) -> bool:
        entDef = self.spaces[space][name]
        if entDef is None: return False
        for frame in self.frames:
            if frame.entDef is entDef: return True
        return False

    def close(self) -> int:
        """Close the innermost open InputFrame.
        """
        frame = self.curFrame
        if not frame: return False
        lg.info("Closing frame '%s'.", frame.description)
        frame.close()
        self.frames.pop()
        return self.depth

    def closeAll(self) -> None:
        while (self.frames):
            self.close()

    @property
    def curFrame(self) -> InputFrame:
        # TODO Maybe add a null string outer frame if nobody home?
        if not self.frames: return None
        return self.frames[-1]

    @property
    def depth(self) -> int:
        return(len(self.frames))

    def wholeLoc(self, sep:str="\n    ") -> str:
        """Describe the entire entity stack context we're reading at.
        """
        buf = ""
        for i in reversed(range(0, self.depth)):
            buf += sep + self.frames[i].frameLoc()
        return(buf)

    ### Reading
    ###
    @property
    def buf(self) -> str:
        if not self.curFrame: return None
        return self.curFrame.buf
    @property
    def bufPos(self) -> int:
        if not self.curFrame: return None
        return self.curFrame.bufPos
    @bufPos.setter
    def bufPos(self, n:int) -> None:
        if not self.curFrame: return None
        self.curFrame.bufPos = n
    @property
    def bufLeft(self) -> int:
        if not self.curFrame: return None
        return self.curFrame.bufLeft
    @property
    def bufSample(self) -> str:
        if not self.buf: return ""
        preLen = min(80, self.bufPos)
        postLen = min(80, self.bufLeft)
        rc = SepChar.qcat(self.buf[self.bufPos-preLen:self.bufPos],
            self.buf[self.bufPos:self.bufPos+postLen])
        #rc = re.sub("\n", "\u240a", rc)
        return rc

    def peek(self, n:int=1) -> str:
        if not self.curFrame: return None
        return self.curFrame.peek(n)
    def consume(self, n:int=1) -> str:
        if not self.curFrame: return None
        return self.curFrame.consume(n)
    def discard(self, n:int=1) -> None:
        if not self.curFrame: return None
        return self.curFrame.discard(n)
    def pushBack(self, s:str) -> None:
        if not self.curFrame: return None
        return self.curFrame.pushBack(s)

    def topOff(self, n:int=None) -> int:
        """Close until not at EOF, then top off first remaining frame.
        """
        if not n: n = self.bufSize
        while self.frames:
            if not self.curFrame.noMoreToRead: self.curFrame.topOff(n)
            if self.curFrame.bufLeft > 0: break
            self.close()
        return 0 if not self.frames else self.curFrame.bufLeft

    def skipSpaces(self, allowComments:bool=False, entOpener:Callable=None) -> None:
        #crossEntityEnds:bool=False):  # TODO Implement stack!
        """Basically skip spaces, but at option also:
            * skip an embedded comment (for SGML not XML DTDs)
            * expand if we hit a parameter entity reference.
        TODO Add a way to return comment events.
        """
        nFound = 0
        while (self.bufLeft):
            c = self.buf[self.bufPos]
            if c.isspace():
                self.bufPos += 1
                nFound += 1
            elif c == "-" and self.options.fragComments and allowComments:
                mat = self.curFrame.readRegex(StackReader.commExpr)
                if not mat: return
                self.bufPos += len(mat.group())
                com = mat.group(1)
                if com:
                    self.bufPos += len(com)
                    #self.doCB(SaxEvent.COMMENT, com)  # SGML only...
                nFound += len(com)
            elif entOpener and c in "%&":
                entOpener()                 # TODO how switch?
            else:
                break
            if self.bufLeft < self.bufSize>>2:
                self.topOff()
                if not self.frames: break
        return
