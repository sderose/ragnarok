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
import os
import codecs
import re
import logging
from typing import Union, List, Dict, Tuple, IO, Any
from types import SimpleNamespace
from collections import OrderedDict  #, namedtuple
import inspect

#import html
from html.entities import name2codepoint  # codepoint2name

from runeheim import XmlStrings as Rune  #CaseHandler, UNormHandler, WSHandler, Normalizer
from saxplayer import SaxEvent
from ragnaroktypes import NSuppE, DOMException, NMTOKEN_t, QName_t
from schemera import (
    # (DocumentType is owned by StackReader)
    ElementDef, Model,  RepType, ContentType,  # ModelGroup
    AttrDef,  AttlistDef, EntitySpace, EntityDef, EntityParsing, NotationDef
    )
import xsdtypes
from xsdtypes import sgmlAttrDefaults, fixedKeyword, anyAttributeKeyword
from xsdtypes import getSgmlAttrTypes  # , XSDDatatypes
from basedom import Document
from stackreader import InputFrame, StackReader, uname2codepoint

lg = logging.getLogger("EntityManager")
logging.basicConfig(level=logging.INFO, format='%(message)s')

EOF = -1

__metadata__ = {
    "title"        : "XSParser",
    "description"  : "An extensible XML parser.",
    "rightsHolder" : "Steven J. DeRose",
    "creator"      : "http://viaf.org/viaf/50334488",
    "type"         : "http://purl.org/dc/dcmitype/Software",
    "language"     : "Python 3.11",
    "created"      : "2011-03-11",
    "modified"     : "2025-04-01",
    "publisher"    : "http://github.com/sderose",
    "license"      : "https://creativecommons.org/licenses/by-sa/3.0/"
}
__version__ = __metadata__['modified']

def callerNames(n1:int=3, n2:int=1) -> str:
    buf = ""
    for i in range(n1, n2, -1): buf += "." + inspect.stack()[i].function
    return buf


###############################################################################
#
class TagStackEntry:
    """The stack of open element instances, with their nodeNames and some
    extra information to help with error checking and reporting.
    """
    def __init__(self, elemName:str, lineNum:int):
        self.elemName = elemName    # Element type name
        self.lineNum = lineNum      # Where it started
        self.isSuspended = False    # Is it suspended?
        self.childTypes = []        # List of child types for validation
        self.attrs = {}              # To check against COID

class TagStack(list):
    """Mainly keeps the stack of open element type names, but has room for
    extra info like where the element started.
    With extensions like OLIST and suspend/resume, it's not exactly a stack.
    """
    def __init__(self, trackChildTypes:bool=False):
        super().__init__()
        self.trackChildTypes = trackChildTypes

    def __insert__(self, *args) -> None:
        raise NotImplementedError("No manual insert on TagStack.")

    def __extend__(self, *args) -> None:
        raise NotImplementedError("No manual extend on TagStack.")

    def __setitem__(self, *args) -> None:
        raise NotImplementedError("No manual __setitem__ on TagStack.")

    def append(self, elemName:str, lineNum:int=None) -> None:
        """Push the new element onto the open stack.
        BUT ALSO add it to the parent's list of childTypes.
        TODO: Maybe just keep repetition counts, not full list?
        """
        if self.trackChildTypes: self[-1].childTypes.append(elemName)
        tsentry = TagStackEntry(elemName, lineNum)
        super().append(tsentry)

    def rindex(self, elemName:NMTOKEN_t) -> int:
        for i in reversed(range(len(self))):
            if self[i].elemName == elemName: return i
        return None

    @property
    def topName(self) -> str:
        """Conveniently avoid IndexError.
        """
        return self[-1].elemName if len(self) > 0 else None

    def getTagStackEntry(self, elemName:NMTOKEN_t, coId:NMTOKEN_t=None) -> TagStackEntry:
        """Find and return the stack frame (if any) with the given nodeName.
        If coId is set, also require the returned frame have an "id" attribute
        that matches it (this is for suspend/resume/endTag coindexing).
        """
        for tse in reversed(self):
            if tse.elemName is not elemName: continue
            if coId and "id" not in tse.attrs or tse.attrs["id"] != coId: continue
            return tse
        return None

    def suspend(self, n:int, lineNum:int=None) -> None:
        self[n].isSuspended = True
        if lineNum is not None: self[n].lineNum = lineNum

    def resume(self, n:int, lineNum:int=None) -> None:
        self[n].isSuspended = False
        if lineNum is not None: self[n].lineNum = lineNum


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
        return "ERROR %d: In entity '%s' @%d:%d (offset %d)." % (
            self.code, self.entName,
            self.lineNumber, self.columnNumber, self.byteIndex)


###############################################################################
#
XSParserOptionDefs = {
    "utgard":           (bool, False ),  # Any Loki stuff going?

    ### Size limits and security (these are XML compatible),
    "MAXEXPANSION":     (int,  1<<20 ),  # Limit expansion length of entities
    "MAXENTITYDEPTH":   (int,  16    ),  # Limit nesting of entities
    "charEntities":     (bool, True  ),  # Allow SDATA and CDATA entities
    "extEntities":      (bool, True  ),  # External entity refs?
    "netEntities":      (bool, True  ),  # Off-localhost entity refs?
    "entityDirs":       (List, None  ),  # Permitted dirs to get ents from
    "extSchema":        (bool, True  ),  # Fetch and process external schema

    "noC0":             (bool, True  ),  # No C0 controls (XML 1.0),
    "noC1":             (bool, False ),  # No C1 controls (b/c CP1252),
    "noPrivateUse":     (bool, False ),  # No Private Use chars
    "langChecking":     (bool, False ),  # Content matches xml:lang?    TODO

    ### Attributes
    "saxAttribute":     (bool, False ),  # Separate SAX event per attribute
    "attributeCast":    (bool, False ),  # Cast to declared type        TODO

    ### Validation (beyond WF!),
    "useDTD":           (bool, False ),  # Use external DTD if available
    "valElemNames":  (bool, False ),  # Element must be declared
    "valModels":        (bool, False ),  # Check child sequences        TODO
    "valAttributeNames":(bool, False ),  # Attributes must be declared
    "valAttributeTypes":(bool, False ),  # Attribute values must match datatype

    ### Other
    "expatBreaks":      (bool, False ),  # Break at \n and entities like expat
    "nsUsage":          (bool, None  ),  # one/global/noredef/regular    TODO
}

class XSPOptions(SimpleNamespace):
    """Keep track of parser extensions in use (if any).
    By default, this just adds options that do not touch XML syntax at all.
    For example, constraints on entity security, extra charset restrictions,
    tweaks to how SAX events are generated, etc.

    To get Loki extensions, explicitly call addLokiOptions().

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
        for k, v in XSParserOptionDefs.items():
            assert v[1] is None or isinstance(v[1], v[0])
            setattr(self, k, v[1])
        if options:
            for k, v in options.items():
                setattr(self, k, v)

    def __getattr__(self, name:str) -> Any:
        """If an unknown option is accessed (such as a Loki option in xsparser),
        return None.
        """
        return None

    def setOption(self, optName:str, optValue:Any) -> None:
        if optName not in XSParserOptionDefs:
            raise AttributeError(f"No such option: '{optName}'.")
        optType = XSParserOptionDefs[optName][0]
        if optType == bool:
            optValue = XSPOptions.boolOption(optName, optValue)
        if optValue is not None and not isinstance(optValue, optType):
            raise AttributeError(
                f"Option '{optName}' takes '{optType}', not '{type(optValue)}'.")
        setattr(self, optName, optValue)

        if (optName == "entityDirs"):
            for adir in optValue: assert os.path.isdir(adir)
        setattr(self, optName, optValue)

    @staticmethod
    def boolOption(optName:str, optValue:Any, strict:bool=True) -> bool:
        """Recognize a small range of boolean values. Unknowns mean false,
        unless 'strict' is set.
        """
        if optValue in [ True, "yes", "1", 1 ]: return True
        if optValue in [ False, "no", "0", 0 ]: return False
        if strict: raise SyntaxError(
            f"Unrecognized boolean value '{optValue}' for option '{optName}'.")
        return False


###############################################################################
#
def ParserCreate(
    encoding="utf-8",
    namespace_separator=None  # Leaves xmlns as attrs, and prefixes as-is.
    ) -> 'XSParser':
    return XSParser(encoding=encoding, namespace_separator=namespace_separator)

class XSParser():  # StackReader?? TODO Check
    def __init__(self,
        encoding:str="utf-8",
        namespace_separator:str=None,
        options:Dict=None):
        #super().__init__(encoding, namespace_separator, options)  # TODO Check
        self.encoding = encoding
        self.namespace_separator = namespace_separator

        self.sr = StackReader(options=options)
        self.errors:List[ErrorRecord] = []
        self.BOM = None
        self.sniffedEncoding = None
        self.setEncoding = None
        self.utgard = False                 # Loki extensions enabled?

        # Set up options for xsparser or Loki, as needed
        self.options = XSPOptions(options)
        self.attrTypes = getSgmlAttrTypes()

        # Parser state
        self.msStack = []                   # Open marked sections
        self.tagStack = TagStack()          # Open elements
        self.sawSubsetOpen:bool = False     # Pending lsqb?
        self.totEvents = 1                  # Callback count
        self.dclCount = 0                   # For markup dcl ordering

    def SynErr(self, msg:str) -> None:
        """Deal with a syntax error.
        """
        raise SyntaxError(
            "Syntax error: %s at %s:\n    %s\n" %
            (msg, self.sr.wholeLoc(), self.sr.bufSample))

    def ValErr(self, msg:str) -> None:
        """Deal with a validation error.
        """
        raise SyntaxError(
            "Validation error: %s at %s:\n    %s\n" %
            (msg, self.sr.wholeLoc, self.sr.bufSample))

    def EntErr(self, msg:str) -> None:
        raise SyntaxError(
            "Entity error: %s at %s:\n    %s\n" %
            (msg, self.sr.wholeLoc, self.sr.bufSample))

    def setOption(self, optName:str, optValue) -> None:
        self.options.setOption(optName, optValue)

    ### Location reporting (forwards to sr)
    ###
    @property
    def CurrentEntityName(self) -> str:
        return self.sr.curFrame.entName

    @property
    def CurrentByteIndex(self) -> int:
        return self.sr.curFrame.fullOffset

    @property
    def CurrentLineNumber(self) -> int:
        return self.sr.curFrame.lineNum

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


    ### Internal recognition-mode checkers
    ###
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

    ### Top-level parser methods
    ###
    def Parse(self, s:str) -> None:
        if not isinstance(s, str) or not s.startswith("<"):
            raise SyntaxError("Parser not given a '<'-initial string.")
        iframe = InputFrame(options=self.options)
        iframe.addData(s)
        self.sr.open(iframe)
        self.parseTop()

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
        if not hasattr(ifh, "read"):
            raise IOError(f"Cannot read from {ifh}.")

#         if False:
#             dclBytes, encoding = XSParser.sniffXmlDcl(ifh)
#             self.sniffedEncoding = encoding or "utf-8"
#             if not dclBytes:
#                 self.setEncoding = self.sniffedEncoding
#             else:
#                 dclStr = dclBytes.decode(encoding=self.sniffedEncoding)
#                 mat = re.search(r"""\sencoding\s*=\s*('[^']*'|"[^"]*")""", dclStr)
#                 self.setEncoding = mat.group(1).strip("'\"") if mat else "utf-8"
#             # Double-check that the encoding is known (else LookupError)
#             codecs.lookup(encoding)

        iframe = InputFrame(options=self.options)
        iframe.addFile(ifh)
        self.sr.open(iframe)
        self.parseTop()

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

    def parseTop(self) -> Document:
        """Parse the start of an XML document, up through the declaration
        subset (the stuff between [] in the DOCTYPE). Return before actually
        parsing the document instance (caller can do parseDocument() for that).

        TODO Fix API so can use as just a normal parse/parse_string.
        """
        #lg.info("\n####### parseTop()")
        #import pudb; pudb.set_trace()
        self.doCB(SaxEvent.DOC)

        _props = self.readXmlDcl()                              # XML declaration

        while (e := self.readComment()):                        # Comments/space
            self.doCB(SaxEvent.COMMENT, e[0])
            self.sr.skipSpaces()

        e = self.readConst("<!DOCTYPE", ss=True, thenSp=True)   # DOCTYPE
        if e:
            doctypeName = self.readName(ss=True)
            if doctypeName is None:
                self.SynErr("Expected document type name in DOCTYPE")
            self.sr.skipSpaces()
            publicId, systemId = self.readLocation()
            self.sr.skipSpaces()
            schemaNotation = "DTD"
            if self.options.schemaType and self.readConst("NDATA"):
                schemaNotation = self.readName()
                if schemaNotation is None: self.SynErr(
                    "No notation name for schema after DOCTYPE...NDATA")
            self.doCB(SaxEvent.DOCTYPE, doctypeName, publicId, systemId)

            # TODO handle external schema

            if self.sr.peek(1) == "[":                          # DCL SUBSET
                self.sr.consume(1)
                self.parseDTD()
                if self.sr.peek(1) == "]":
                    self.sr.consume(1)
                else:
                    self.SynErr("Expected ']' to end internal dcl subset.")

            if not self.readConst(">", ss=True):                # MDC
                self.SynErr("Expected '>' to end DOCTYPE")

            if (self.options.useDTD and
                (self.sr.doctype.publicId or self.sr.doctype.systemId)):
                # TODO Find and open the DTD, then call parseDTD on it.
                pass

            self.doCB(SaxEvent.DOCTYPEEND)

        self.parseDocument()                                    # DOCUMENT

    def parseDTD(self) -> None:
        """This can parse either an internal subset or an external DTD.
        """
        while True:
            #lg.info("** subset at: %s", self.sr.bufSample)
            self.sr.skipSpaces(entOpener=True)  # TODO add to buf? Not for subset
            if self.sr.bufLeft <= 0: break
            delim, _nextChar = self.peekDelimPlus()
            #lg.info("Delim: '%s'.", delim)
            if not delim:
                self.SynErr("Unexpected content in subset")
            elif delim[0] == "<":                               # <...
                if delim == "<!--" or (                                 # COM
                    self.options.emComment and delim == "<!\u2014"):
                    if txt := self.readComment():
                        self.doCB(SaxEvent.COMMENT, txt)

                elif delim == "<![":                                    # MSO
                    if txt := self.readMSOpening():
                        self.doCB(SaxEvent.CDATA, txt)
                        break

                elif delim == "<!":                                     # DCL
                    # TODO Factor out doctype interaction for dcls?
                    #lg.info("Looks like a dcl")
                    if e := self.readElementDcl():
                        # -> (names, Model, omit1, omit2, includes, excludes)
                        self.addElementToDoctype(e)
                        self.doCB(SaxEvent.ELEMENTDCL, e)
                    elif e := self.readAttlistDcl():
                        # -> ( [elemName+], [AttrDef+] )
                        self.addAttlistToDoctype(elemNames=e[0], attrDefs=e[1])
                        self.doCB(SaxEvent.ATTLISTDCL, e)
                    elif e := self.readEntityDcl():
                        lg.warning("EntityDcl: %s" % (repr(e)))
                        self.addEntityToDoctype(e)
                        self.doCB(SaxEvent.ENTITYDCL, e)
                    elif e := self.readNotationDcl():
                        (name, publicId, systemId) = e
                        self.addNotationToDoctype(name, publicId, systemId)
                        self.doCB(SaxEvent.NOTATIONDCL, e)
                    else:
                        self.SynErr("Unrecognized dcl.")
                elif delim == "<?":                                     # PI
                    if pair := self.readPI():
                        self.doCB(SaxEvent.PROC, *pair)
                    else:
                        self.SynErr("Incomplete PI.")
                else:
                    self.SynErr("Unrecognized dcl type.")

            elif delim == "]]>":                                    # MSC
                if len(self.msStack) == 0:
                    self.SynErr("']]>' found but no marked section is open.")
                self.msStack.pop()

            elif delim.startswith("]"):                             # SUBSET END
                return

            else:                                                   # Fail
                if not self.sr.depth:
                    self.SynErr("Unexpected EOF in DOCTYPE, no more input frames.")
        self.doCB(SaxEvent.DOCEND)

    def addElementToDoctype(self, e:List) -> bool:
        """Take the parsed info from a markup declaration, and add to the doctype.
        TODO: Duplicate dcls need not be fatal.
        TODO: Move ElementDef, EntityDef, NotationDef down to reader?
        TODO: Show location of prior dcl in case of duplicates.
        """
        dt = self.sr.doctype
        self.dclCount += 1
        for name in list(e[0]):  # Allow for multiDcl
            if name in dt.elementDefs: self.SynErr(
                f"Duplicate declaration for element '{name}'.")
            theDef = ElementDef(name=name, model=e[1],
                ownerSchema=dt, readOrder=self.dclCount)
            dt.elementDefs[name] = theDef
        return True

    def addAttlistToDoctype(self, elemNames:List, attrDefs:List) -> bool:
        """Unlike other dcls, for ATTLISTs individual AttrDef objects were
        created by stackReader; it's just easier.
        """
        dt = self.sr.doctype
        self.dclCount += 1
        attrListObj = AttlistDef(
            elemNames=elemNames, ownerSchema=dt, readOrder=self.dclCount)
        for attrDef in attrDefs:
            attrListObj.addAttrDef(attrDef)

        # Now attach the ATTLIST to the element(s)
        dupFails = []
        for elemName in list(elemNames):
            if elemName in dt.elementDefs:
                eDef = dt.elementDefs[elemName]
            else:
                eDef = dt.elementDefs[elemName] = ElementDefs(name=elemName,
                    model=None, ownerSchema=dt, readOrder=self.dclCount)
            if not eDef.attrDefs: eDef.attrDefs = {}
            for attrDef in attrDefs:
                if attrDef.attrName in eDef.attrDefs:
                    dupFail.append( (elemName, attrDef.attrName) )
                else:
                    eDef.attrDefs[attrDef.attrName] = attrDef

        if len(dupFails) > 0:
            self.SynErr(f"Duplicate attribute for element: {dupFails}.")
        return True

    def addEntityToDoctype(self, e:List) -> bool:
        dt = self.sr.doctype
        self.dclCount += 1
        for entName in list(e[0]):
            if entName in dt.entityDefs: self.SynErr(
                f"Duplicate declaration for entity '{entName}'.")
            theDef = EntityDef(
                entName=entName,
                entSpace=EntitySpace.GENERAL,       # TODO Finish ent space cases
                entParsing=EntityParsing.PCDATA,
                publicId=None,                      # TODO ent loc stuff
                systemId=None,
                data=None,
                notationName=None,
                encoding="utf-8",
                ownerSchema=dt,
                readOrder=self.dclCount
            )
            dt.entityDefs[entName] = theDef
        return True

    def addNotationToDoctype(self,
        name:Union[QName_t, List], publicId:str, systemId:str) -> bool:
        dt = self.sr.doctype
        self.dclCount += 1
        for notationName in list(name):
            if notationName in dt.notationDefs: self.SynErr(
                f"Duplicate declaration for notation '{notationName}'.")
            theDef = NotationDef(name=notationName, publicId=publicId,
                systemId=systemId, ownerSchema=dt, readOrder=self.dclCount)
            dt.notationDefs[notationName] = theDef
        return True

    ### TODO Copy to Loki then remove extensions here.
    ###
    def parseDocument(self) -> None:
        """Starts after doctype if any.
        """
        tBuf = []  # Use List for performance
        while c := self.sr.peek(1) is not None:
            delim, _nextChar = self.peekDelimPlus()
            #lg.info("delim '%s', then '%s'.", delim, nextChar)
            if not delim:
                while True:
                    c = self.sr.peek(1)
                    if c is None or c in InputFrame.firstDelims: break
                    if c == "\n" and self.options.expatBreaks: self.issueText(tBuf)
                    if not self.ignoring: tBuf.append(c)
                    self.sr.consume(1)
                continue

            c = delim[0]
            if c == "&" and self.recognizeEntities:             # ENTREF
                if self.options.expatBreaks: self.issueText(tBuf)
                if delim == "&#":
                    tBuf.append(self.readNumericChar())
                else:
                    self.sr.consume(1)
                    if not (entName := self.readName(ss=False)):
                        self.SynErr("Expected '#' or entity name after '&'.")
                    if not self.readConst(";"):
                        self.SynErr("Expected ';' after entity name '%s'"
                            ", but found '%s'." % (entName, self.sr.peek(1)))
                    if self.options.entityFold:
                        entName = self.options.entityFold.normalize(entName)
                    if self.options.htmlNames and entName in name2codepoint:
                        # TODO Have to case-fold lookup, too
                        tBuf.append(chr(name2codepoint[entName]))
                    elif (self.options.unicodeNames
                        and (cp := uname2codepoint(entName))):
                        tBuf.append(chr(cp))
                    elif entName in self.sr.sdataDefs:
                        tBuf.append(self.sr.sdataDefs[entName])
                    else:
                        self.openEntity(space=EntitySpace.GENERAL, entName=entName)

            # TODO CDATA, IGNORE?
            elif c == "<":                                      # Most MARKUP
                self.issueText(tBuf)
                if delim == "<":                                    # STARTTAG
                    elemName, attrs, emptySyntax = self.readStartTag()
                    if not (elemName): self.SynErr("Unexpected characters after '<'.")
                    #if self.sr.doctype:
                    #    self.sr.doctype.applyDefaults(elemName, attrs)  # TODO defaults

                    if self.options.saxAttribute:
                        self.doCB(SaxEvent.START, elemName, None, emptySyntax)
                        for attrName, attrValue in attrs.items():
                            assert not isinstance(attrValue, tuple)
                            self.doCB(SaxEvent.ATTRIBUTE, attrName, attrValue)
                    else:
                        self.doCB(SaxEvent.START, elemName, attrs)

                    self.tagStack.append(elemName, self.sr.curFrame.lineNum)
                    if emptySyntax:  # <x/>
                        self.doCB(SaxEvent.END, elemName)
                        self.tagStack.pop()

                elif delim == "</":                                 # ENDTAG
                    if self.options.unordered:
                        self.SynErr("Unordered is not yet working.")  # TODO
                    elemName = self.readEndTag()
                    if not elemName: self.SynErr("Expected name after '</'.")
                    if self.options.elementFold:
                        elemName = self.options.elementFold.normalize(elemName)
                    foundAt = self.tagStack.rindex(elemName)
                    if foundAt is None: self.SynErr(
                        f"End-tag for non-open type '{elemName}'. [ {self.tagStack} ].")
                    elif self.options.olist:
                        self.doCB(SaxEvent.END_OLIST, elemName)
                        del self.tagStack[foundAt]
                    elif self.options.omitEnd:
                        while len(self.tagStack) > foundAt:
                            self.doCB(SaxEvent.END, self.tagStack.topName)
                            self.tagStack.pop()
                    elif foundAt == len(self.tagStack) - 1:
                        self.doCB(SaxEvent.END, self.tagStack.topName)
                        self.tagStack.pop()
                    else: self.SynErr(
                        f"End-tag for {elemName}, but open are: {self.tagStack}.")

                elif delim == "<!--":                               # COMMENT
                    if comData := self.readComment(endAt="-->"):
                        self.doCB(SaxEvent.COMMENT, comData)
                    else: self.SynErr("Invalid comment.")
                elif self.options.emComment and delim == "<!\u2014":
                    if comData := self.readComment(endAt="\u2014>"):
                        self.doCB(SaxEvent.COMMENT, comData)
                    else: self.SynErr("Invalid em comment.")
                elif self.options.poundComment and delim == "#>":
                    if comData := self.readComment(endAt=delim):
                        self.doCB(SaxEvent.COMMENT, comData)
                    else: self.SynErr("Invalid # comment.")

                elif delim == "<![":                                # MARKED SEC
                    # TODO Support additional marked section types
                    if self.sr.peek(9) != "<![CDATA[":
                        self.SynErr("Invalid marked section opening.")
                    # Unlike most constructs, this stays open (see below for ]]>).
                    # For CDATA is doesn't need to, but consider SGML types.
                    if e := self.readMSOpening():
                        self.doCB(SaxEvent.CDATA)
                        self.doCB(SaxEvent.CHAR, e or "")
                        self.doCB(SaxEvent.CDATAEND)
                    else:
                        self.SynErr("Invalid marked section.")

                elif delim == "<!":                                 # Dcl
                    self.SynErr("Unexpected markup declaration.")

                elif delim == "<?":                                 # PI
                    if not (piItems := self.readPI()):
                        self.SynErr("Expected target and data after '<?'.")
                    self.doCB(SaxEvent.PROC, *piItems)

                elif delim == "<|":                                 # RESTART
                    if not self.tagStack:
                        self.SynErr("Can't re-start with nothing open.")
                    self.sr.discard(2)
                    tgtName = self.readName() or self.tagStack.topName
                    n = self.tagStack.rindex(tgtName)
                    if n is None:
                        self.SynErr(f"Can't re-start '{tgtName}' (not open.")
                    if not self.options.restartName and n != len(self.tagStack)-1:
                        self.SynErr(f"Can't re-start '{tgtName}' "
                            "(not current, and restartName option is not set.")
                    self.trySpecialAttributes(e)
                    if self.readConst(">", ss=True) is None:
                        self.SynErr(f"Unclosed restart for {tgtName}.")
                    popped = []
                    for _i in reversed(range(len(self.tagStack), n)):
                        popped.append(self.tagStack[-1])
                        self.doCB(SaxEvent.END, self.tagStack.topName)
                        self.tagStack.pop()
                    for p in reversed(popped):
                        # TODO Save attributes too, e.g. for restart
                        self.tagStack.append(p)
                        self.doCB(SaxEvent.START, p)
                    popped = None

                elif self.options.unordered and delim == "<{":      # Unordered
                    self.SynErr("Unordered is not yet working.")
                    # TODO Unordered: Enough to save flag and validate later?
                elif delim == "<-":                                 # Suspend
                    self.sr.discard(2)
                    e = self.readName
                    if e is None: self.SynErr("No name in suspend.")
                    self.trySpecialAttributes(e)
                    if self.readConst(">", ss=True) is None:
                        self.SynErr(f"Unclosed suspend for {e}.")
                    n = self.tagStack.rindex(e)
                    if not n: self.SynErr(
                        f"Cannot suspend or resume '{e}' (not open).")
                    self.doCB(SaxEvent.SUSPEND, e)
                    self.tagStack[n].suspend(self.sr.curFrame.lineNum)

                elif delim == "<+":                                 # Resume
                    self.sr.discard(2)
                    e = self.readName
                    if e is None: self.SynErr("No name in resume.")
                    self.trySpecialAttributes(e)
                    if self.readConst(">", ss=True) is None:
                        self.SynErr(f"Unclosed resume for {e}.")
                    n = self.tagStack.rindex(e)
                    if not n: self.SynErr(
                        f"Cannot suspend or resume '{e}' (not open).")
                    self.doCB(SaxEvent.RESUME, e)
                    self.tagStack[n].resume(self.sr.curFrame.lineNum)

                else:                                               # Fail
                    self.SynErr("Unrecognized markup after '<'")

            elif delim == "]]>":                                # MSC
                self.issueText(tBuf)
                if not self.msStack: self.SynErr("']]>' found outside MS.")
                del self.msStack[-1]

            elif self.options.backslash and c == "\\":          # \\xFF etc.
                if self.options.expatBreaks: self.issueText(tBuf)
                c = self.readBackslashChar()
                if not self.ignoring: tBuf.append(c)

            else:                                               # Inactive delim
                lg.info("Inactive delimiter? '%s'.", delim)
                tBuf.append(delim)

        # Should be at EOF
        if tBuf: self.issueText(tBuf)
        if self.tagStack:
            if not self.options.omitAtEOF:
                self.SynErr(f"Unclosed elements at EOF: {self.tagStack}.")
            while len(self.tagStack) > foundAt:
                self.doCB(SaxEvent.END, self.tagStack.topName)
                self.tagStack.pop()
        self.doCB(SaxEvent.DOCEND)
        return

    def trySpecialAttributes(self, name:NMTOKEN_t) -> Dict:
        """Parse any attrs found in non-start tags. Only ID/COID attributes are
        allowed there (and only when enabled, for Loki), to co-index suspends,
        resumes, and ends with their start-tags.
        TODO: Distinguish tx of check-ID vs. COID vs. (xSTART/SUSP/RES/END)ID
        """
        attrs = self.readAttributes()
        if not attrs: return None
        if len(attrs) > 1 or "id" not in attrs:
            self.SynErr("No non-'id' attrs in resumes.")
        coId = attrs['id']
        tse = self.tagStack.getTagStackEntry(name, coId=coId)
        if not tse: self.SynErr(f"Co-id'd element for {coId} not open.")
        return attrs

    def doCB(self, typ:SaxEvent, *args) -> None:
        """Given an event type and its args, call the handler if any.
        """
#         if typ == SaxEvent.ATTLISTDCL:
#             lg.info("doCB for ATTLISTDCL: %s", args[0])
#             for tup in args[1]:
#                 lg.info("    %s", tup)
#         elif typ == SaxEvent.COMMENT:
#             lg.info("doCB for COMMENT: %s", args[0])
#         elif len(args) == 0:
#             lg.info("doCB for %s", typ.name)
#         else:
#             lg.info("doCB for %s: %s", typ.name, args)

        self.totEvents += 1
        if hasattr(self, typ.value):
            cb = getattr(self, typ.value)
        elif hasattr(self, SaxEvent.DEFAULT.value):
            cb = getattr(self, SaxEvent.DEFAULT.value)
        else:
            return
        if cb: cb(*args)

    def issueText(self, tBuf:List) -> None:
        """Called whenever we hit markup, to issue buffered text as a SAX event.
        Not called at \\n or entity refs, unless options.expatBreaks.
        """
        if tBuf is None or len(tBuf) == 0: return
        self.doCB(SaxEvent.CHAR, ''.join(tBuf))
        tBuf.clear()

    # Forward small constructs to entity-frame-limited readers
    #
    def readConst(self, const:str, ss:bool=True, thenSp:bool=False) -> str:
        if not self.sr.curFrame: return None
        return self.sr.curFrame.readConst(const, ss=ss, thenSp=thenSp)
    def peekDelimPlus(self, ss:bool=True) -> (str, str):
        if not self.sr.curFrame: return None
        return self.sr.curFrame.peekDelimPlus(ss=ss)
    def readBackslashChar(self) -> str:
        if not self.sr.curFrame: return None
        return self.sr.curFrame.readBackslashChar()
    def readNumericChar(self, ss:bool=True) -> str:
        if not self.sr.curFrame: return None
        return self.sr.curFrame.readNumericChar(ss=ss)
    def readInt(self,  ss:bool=True, signed:bool=True) -> int:
        if not self.sr.curFrame: return None
        return self.sr.curFrame.readInt(ss, signed)
    def readFloat(self,  ss:bool=True, signed:bool=True,
        specialFloats:bool=False) -> float:
        if not self.sr.curFrame: return None
        return self.sr.curFrame.readFloat(
            ss=ss, signed=signed, specialFloats=specialFloats)
    def readName(self, ss:bool=True) -> str:
        if not self.sr.curFrame: return None
        return self.sr.curFrame.readName(ss)

    def readQGI(self, ss:bool=True) -> (str, NMTOKEN_t):
        """Read a qualified name, like sec/ul/li/p.
        Watch out for empty element syntax.
        Caller should check context then strip.
        """
        if not self.sr.curFrame: return None
        qgi = self.sr.curFrame.readName(ss)
        while self.sr.peek(1) == "/" and self.sr.peek(2) != "/>":
            self.sr.consume(1)
            nextQgi = self.sr.curFrame.readName(ss)
            if nextQgi is None:
                self.SynErr(f"Name expected after '/' in Qgi at {qgi}.")
            qgi += "/" + nextQgi
        return qgi, nextQgi

    def readRegex(self, regex:Union[str, re.Pattern],
        ss:bool=True, ignoreCase:bool=True) -> re.Match:
        if not self.sr.curFrame: return None
        return self.sr.curFrame.readRegex(regex, ss, ignoreCase)
    def readToString(self, ender:str, consumeEnder:bool=True) -> str:
        if not self.sr.curFrame: return None
        return self.sr.curFrame.readToString(ender, consumeEnder)

    def readQLit(self, ss:bool=True, keepPunc:bool=False, expandPE:bool=False) -> str:
        """TODO: Who exands stuff inside qlits???? Do one pass at end?
        """
        #lg.info("*** %s, buf '%s'.", callerNames(), self.sr.bufSample)
        if ss: self.sr.skipSpaces()  # TODO entOpener=self.readPEntRef ??? SGML only?
        lQuote = self.sr.peek()
        rQuote = None
        if lQuote == "'" or lQuote == '"':
            rQuote = lQuote
        elif self.options.curlyQuote:
            # This isn't all the Unicode possibilities, just the main ones.
            if   lQuote == "\u2018": rQuote = "\u2019"  # Curly single
            elif lQuote == "\u201C": rQuote = "\u201D"  # Curly double
            elif lQuote == "\u00AB": rQuote = "\u00BB"  # Double angle
        else:
            self.SynErr(f"Expected quoted string but found '{lQuote}' (U+{ord(lQuote):04x}).")

        self.sr.discard()
        dat = self.readToString(rQuote, consumeEnder=True)
        if dat is None:
            self.SynErr("Unclosed quoted string.")
        if expandPE: dat = self.expandPEntities(dat)
        if keepPunc: return lQuote + dat + rQuote
        return dat

    def readNameGroup(self, ss:bool=False) -> List:
        """Allows and mix of [&|,] or space between names. This if for;
            * SGML-style <!ELEMENT (i, b, tt, mono) #PCDATA>
            * Parser feature 'simultaneous': <a|b|c>
        This is slightly too permissive.
        This discard inter-name operators, so don't use for content models.
        """
        #lg.info("*** %s, buf '%s'.", callerNames(), self.sr.bufSample)
        ngo = self.readConst("(", ss)
        if ngo is None: return None
        names = []
        while (True):
            self.sr.skipSpaces(entOpener=self.readPEntRef)
            name = self.readName()
            if name is None:
                self.SynErr("Expected a name in name group.")
            names.append(name)
            self.sr.skipSpaces(entOpener=self.readPEntRef)
            c = self.sr.peek()
            if c == ")": break
            if c in "|&,": continue
        return names

    def readNameOrNameGroup(self, ss:bool=False) -> List:
        """Such as: <!ELEMENT...
            div
            (h1 | h2 | h3)
            (%soup;)
        """
        #lg.info("*** %s, buf '%s'.", callerNames(), self.sr.bufSample)
        if ss: self.sr.skipSpaces(entOpener=self.readPEntRef)
        c = self.sr.peek(1)
        if self.options.groupDcl and c == "(":
            names = self.readNameGroup(ss=True)
        else:
            names = [ self.readName() ]
        if not names: return None
        return names

    ### Readers for top-level DTD constructs
    #
    def readXmlDcl(self) -> (str, str):                         # <?xml ...?>
        """Parse the XML declaration, including the possibility of extended
        (quasi-)attributes to set options.
        This is nearly the only case where ss=False.
        """
        if not self.readConst("<?xml", ss=False, thenSp=True): return None
        props = { "version":"1.0", "encoding":"utf-8", "standalone":"yes" }
        while (True):
            attrName, attrValue, _ = self.readAttribute(ss=True)
            if attrName is None: break
            if attrName == "version":
                if attrValue not in [ "1.0", "1.1" ]: self.SynErr(
                    f"Unrecognized version value: '{attrValue}'.")
                props[attrName] = attrValue
            elif attrName == "encoding":
                try:
                    codecs.lookup(attrValue)
                    props[attrName] = attrValue
                except LookupError as e:
                    raise DOMException(f"Unrecognized encoding value '{attrValue}'.") from e
            elif attrName == "standalone":
                if attrValue not in [ "yes", "no" ]: self.SynErr(
                    f"Unknown standalone value: '{attrValue}'.")
                props[attrName] = attrValue
            else:
                self.setOption(attrName, attrValue)

        if not self.readConst("?>", ss=True):
            self.SynErr(f"Unterminated XML DCL, read {repr(props)}.")
        self.doCB(SaxEvent.XMLDCL,
            props["version"], props["encoding"], props["standalone"])
        return props

    def readPI(self) -> (str, Union[str, Dict]):                # <?tgt data??>
        #lg.info("*** %s, buf '%s'.", callerNames(), self.sr.bufSample)
        pio = self.readConst("<?", ss=True)
        if pio is None: return None, None
        piTarget = self.readName()
        # TODO Implement piEscapes
        if self.options.piAttribute:
            piData = self.readAttributes(ss=True)
            if not self.readConst("?>", ss=True): self.SynErr("Unterminated PI.")
        else:
            piData = self.readToString("?>", consumeEnder=True)
            if piData is None: self.SynErr("Unterminated PI.")
        return piTarget, piData

    def readComment(self, endAt:str="-->") -> str:         # <!-- txt -->
        #lg.info("*** %s, buf '%s'.", callerNames(), self.sr.bufSample)
        como =  self.readConst("<!--", ss=True)
        if como is None and self.options.emComment:
            como = self.readConst("<!—", ss=False)
        if como is None: return None
        # If opened w/ em, has to close with it too.
        comData = self.readToString(endAt, consumeEnder=True)
        if comData is None: self.SynErr("Unterminated Comment.")
        return comData

    def readNotationDcl(self) -> (str, str, Union[str, List]):  # <!NOTATION>
        #lg.info("*** %s, buf '%s'.", callerNames(), self.sr.bufSample)
        if self.readConst("<!NOTATION", thenSp=True) is None: return None
        name = self.readName(ss=True)
        #lg.info("Got notation '%s', at %s", name, self.sr.bufSample)
        publicId, systemId = self.readLocation()
        #lg.info("    Got pub '%s', sys '%s'.", publicId, systemId)

        if publicId is None and systemId is None: self.SynErr(
            f"Expected PUBLIC or SYSTEM identifier at {self.sr.bufSample}.")
        if not self.readConst(">"): self.SynErr(
            f"Expected '>' for NOTATION dcl at {self.sr.bufSample}.")
        return (name, publicId, systemId)

    def readLocation(self) -> (str, Union[str, List]):          # PUBLIC/SYSTEM
        """The PUBLIC "" "" or SYSTEM "" syntax.
        Note: This returns the SYSTEM ID as a list iff 'multiPath' is on.
        It does not read a QLit or the MDC delimiter.
        """
        #lg.info("*** %s, buf '%s'.", callerNames(), self.sr.bufSample)
        publicId = None
        systemId = None
        #lg.info("readloc, at %s", self.sr.bufSample)
        if self.readConst("PUBLIC", ss=True):
            publicId = self.readQLit(ss=True, expandPE=True)
            systemId = self.readQLit(ss=True, expandPE=True)
        elif self.readConst("SYSTEM"):
            systemId = self.readQLit(ss=True, expandPE=True)
            #if self.options.multiPath:
        else:
            return None, None
        return (publicId, systemId)

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
        #lg.info("*** %s, buf '%s'.", callerNames(), self.sr.bufSample)
        if self.readConst("<!ELEMENT", thenSp=True) is None: return None

        # TODO Switch to readNameOrNameGroup()?
        if self.options.groupDcl and self.sr.peek() == "(":
            names = self.readNameGroup()
        else:
            names = [ self.readName() ]
        if names is None:
            self.SynErr(f"Expected element name or group at {self.sr.bufSample}.")

        omitStart = omitEnd = None
        if self.options.oflag:
            # Doesn't handle PE refs in mid-omitFlags.
            self.sr.skipSpaces()
            omitStart = self.readConst("-")
            if omitStart is None: omitStart = self.readConst("O")
            if omitStart:
                self.sr.skipSpaces()
                omitEnd = self.readConst("-")
                if omitEnd is None: omitEnd = self.readConst("O")
                if not omitEnd: self.SynErr("Invalid second omission flag.")

        model = self.readModel()
        if model is None: self.SynErr(
            f"Expected model or declared content for {names}.")

        inclusions = exclusions = None
        if self.options.mixin:
            if self.sr.peek() == "+":
                self.sr.discard()
                mixins = self.readNameGroup()
                if mixins is None: self.SynErr(
                    "Expected name group after '+' for inclusions.")
                inclusions = mixins
            if self.sr.peek() == "-":
                self.sr.discard()
                mixins = self.readNameGroup()
                if mixins is None: self.SynErr(
                    "Expected name group after '-' for exclusions.")
                exclusions = mixins

        if not self.readConst(">"): self.SynErr("Expected '>' for ELEMENT dcl.")
        return (names, model, omitStart, omitEnd, inclusions, exclusions)

    def readModel(self) -> Model:                               # EMPTY | (...)
        """Read a parenthesized content model OR a declared content keyword.
        """
        #lg.info("*** %s, buf '%s'.", callerNames(), self.sr.bufSample)
        mat = self.readRegex(r"#?\w+\b", ss=True)
        if mat:
            try:
                contentType = ContentType(mat.group().lstrip("#"))
                return contentType  #Model(contentType=contentType)
            except ValueError:
                self.SynErr(f"Unrecognized declared content keyword '{mat.group}'.")
        mtokens = self.readModelGroup(ss=True)
        if mtokens is None: return None
        return ''.join(mtokens)  #Model(tokens=mtokens)

    def readModelGroup(self, ss:bool=True) -> List[str]:        # ( x | Y | z )
        """Extract and return a list of tokens from a balanced paren group
        like a content model, including sequence and repetition operators.
        Handily, you can't have parens as escaped data in there.
        Does not make an AST (see readModel(), which construct a Model object).
        TODO PE refs?
        TODO Switchable nesting, to use for nameGroup?
        """
        if ss: self.sr.skipSpaces(entOpener=self.readPEntRef)
        if not self.readConst("("): return None
        tokens = [ "(" ]
        depth = 1
        while (True):
            self.sr.skipSpaces(entOpener=self.readPEntRef)
            c = self.sr.peek()
            if curToken := self.readName():
                tokens.append(curToken)
            elif self.readConst("#PCDATA"):
                tokens.append("#PCDATA")
            elif c in "(":
                self.sr.discard()
                tokens.append(c); depth += 1
            elif c == ")":
                self.sr.discard()
                tokens.append(c); depth -= 1
                if depth == 0: break
            elif c in "|,&":
                self.sr.discard()
                tokens.append(c)
            elif c in "+?*":
                self.sr.discard()
                tokens.append(c)
            elif self.options.repBrace and (rep := self.readRepIndicator()):
                tokens.append(rep)
            else:
                self.SynErr(f"Unexpected character '{c}' in model at {tokens}.")
        if rep := self.readRegex(r"[*?+]", ss=True):
            tokens.append(rep.group())
        elif self.options.repBrace and (rep := self.readRepIndicator()):
            tokens.append(rep)
        return tokens

    def readRepIndicator(self, ss:bool=True) -> RepType:        # *|+|?|{}
        """The repetition operator (including the {}-form extension).
        """
        if ss: self.sr.skipSpaces()
        c = self.sr.peek()
        if c not in "*?+{":
            return None
        self.sr.discard()
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

    def readAttlistDcl(self) -> (List, List):                   # <!ATTLIST>
        """This reads an entire ATTLIST, which may declare multiple
        attributes, for one or several elements. It returns:
            * a list of element names (usually one), and
            * a list of documenttype.AttrDef objects (one for each attribute.
        It does NOT create an Attlist object, or add anything to the doctype.

        Example:
            <!ATTLIST (para, p)
                id      ID          #IMPLIED
                level   NUMTOKEN    #REQUIRED
                thing   (b|c|d)     "d"
                spam    ENTITY      #FIXED "chap1">

        Returns:
            ( [ para, p ],
              [ aInfo("id",    ID,       #IMPLIED,  None),
                aInfo("level", NUMTOKEN, #REQUIRED, None),
                aInfo("thing", (b|c|d),  #IMPLIED,  "d"),
                aInfo("spam",  ENTITY,   #FIXED,    "chap1"),
            ])
        """
        #lg.info("*** %s, buf '%s'.", callerNames(), self.sr.bufSample)
        if self.readConst("<!ATTLIST", thenSp=True) is None:
            return None
        self.sr.skipSpaces()

        thisIsForAPI = self.options.piAttlist and self.readConst("?")

        if self.options.groupDcl and self.sr.peek() == "(":
            elemNames = self.readNameGroup()
        elif self.options.globalAttribute and self.sr.peek() == "*":
            elemNames = [ "*" ]
        else:
            elemNames = [ self.readName() ]
        if elemNames is None:
            self.SynErr("Expected an element name in ATTLIST.")

        attrDefs = []
        while (True):
            attrDftKwd = dftVal = None
            if self.readConst(">", ss=True): break

            # Attribute name
            if self.options.anyAttribute and self.readConst(anyAttributeKeyword):
                attrName = anyAttributeKeyword
            else:
                attrName = self.readName(ss=True)
            if attrName is None:
                self.SynErr(f"Expected attribute name in ATTLIST for {elemNames}.")

            # Attribute type or enumerated token list
            self.sr.skipSpaces()
            if self.sr.peek() == "(":
                attrType = self.readModelGroup(ss=True)  # TODO: No nesting....
            elif not (attrType := self.readName(ss=True)): self.SynErr(
                "Expected attribute type or enum-group.")
            elif attrType not in self.attrTypes: self.SynErr(
                f"Unknown type '{attrType}' for attribute '{attrName}'." +
                f" Known: {list(self.attrTypes.keys())}.")

            # Attribute default
            self.sr.skipSpaces(entOpener=self.readPEntRef)
            c = self.sr.peek()
            if c == "#":
                attrDftKwd = self.sr.consume()
                attrDftKwd += self.readName() or ""
                if attrDftKwd == fixedKeyword:
                    dftVal = self.readQLit(ss=True, expandPE=True)
                elif attrDftKwd not in sgmlAttrDefaults: self.SynErr(
                    f"Unknown attribute default '{attrDftKwd}' for '{attrName}'.")
            elif c in '"\'':
                dftVal = self.readQLit(expandPE=True)

            # Save this attribute definition's info
            attrDefs.append(AttrDef(
                elemNS=None, elemName=elemNames, attrNS=None, attrName=attrName,
                attrType=attrType, attrDft=attrDftKwd, literal=dftVal,
                ownerSchema=None, readOrder=None))

        self.sr.skipSpaces()
        if thisIsForAPI: self.SynErr(
            f"piAttlist for {elemNames} read, but not fully implemented yet.")
        return elemNames, attrDefs

    def readEntityDcl(self) -> Tuple:                           # <!ENTITY>
        """Examples:
            <!ENTITY % foo "(i | b* | (tt, lang0))*">
            <!ENTITY XML "Extensible Markup Language">
            <!ENTITY chap1 PUbLIC "-//foo" "/tmp/chap1.xml">
            <!ENTITY if1 SYSTEM "/tmp/fig1.jpg" NDATA jpeg>
            <!ENTITY bull SDATA "&#x2022;">
        """
        #lg.info("*** %s, buf '%s'.", callerNames(), self.sr.bufSample)
        if self.readConst("<!ENTITY", thenSp=True) is None: return None
        self.sr.skipSpaces()
        isParam = (self.readConst("%", thenSp=True) is not None)
        entName = self.readName(ss=True)
        publicId = systemId = lit = ""
        publicId, systemId = self.readLocation()
        if publicId is None and systemId is None:
            lit = self.readQLit(ss=True, expandPE=True)

        notn = None
        if self.readConst("NDATA", ss=True):
            notn = self.readName(ss=True)
            if notn is None: self.SynErr("Expected notation name after NDATA.")

        self.sr.skipSpaces()
        if not self.readConst(">"): self.SynErr("Expected '>' for ENTITY dcl.")
        return (entName, isParam, publicId, systemId, lit, notn)


    ###########################################################################
    # Readers for main document content
    #
    def readStartTag(self, ss:bool=True) -> (Union[str, List], Dict, bool):
        """Calll while still pointing at '<'.
        Returns a 3-tuple of:
            element type elemName (or a List if 'simultaneous' is set)
            dict of attributes
            whether it used empty-element syntax
        """
        #lg.info("*** %s, buf '%s'.", callerNames(), self.sr.bufSample)
        if not self.readConst("<", ss): return None, None, None
        if self.options.qgi: elemName = self.readQGI(ss)
        else: elemName = self.readName(ss)
        if elemName is None and self.options.simultaneous:  # <a|b...>
            elemName = self.readNameGroup()
            if self.options.elementFold:
                for i in range(len(elemName)):
                    elemName[i] = self.options.elementFold.normalize(elemName[i])
        elif elemName is None:
            self.SynErr("Expected elemName in start-tag.")
        elif self.options.elementFold:
            elemName[i] = self.options.elementFold.normalize(elemName)

        # Attributes
        attrs = self.readAttributes(ss=ss)
        attrs = self.normalizeAttributeValues(elemName, attrs)

        # Close of start tag
        empty = False
        if self.readConst("/>", ss): empty = True
        elif self.readConst(">", ss): empty = False
        else: self.SynErr(f"Unclosed start-tag for '{elemName}'.")

        # Validation (content model checked later, once element is complete)
        elDcl = None
        if self.sr.doctype and elemName in self.sr.doctype.elementDefs:
            elDcl = self.sr.doctype.elementDefs[elemName]
        if not elDcl:
            if self.options.valElemNames:
                self.ValErr(f"Undeclared element '{elemName}'.")
        else:
            self.sr.doctype.applyDefaults(elDcl=elDcl, attrs=attrs)
            if self.options.valAttributeTypes:
                for k, v in attrs.items():
                    if k not in elDcl.attributes: continue
                    if not elDcl.attributes.type: continue
                    badFacet = xsdtypes.facetCheck(v, elDcl.attributes.type)
                    if badFacet: self.ValErr(
                        f"Attribute {k}=\"{v}\" of element type '{elemName}' violates "
                        f"facet {badFacet} of XSD type {elDcl.attributes.type}.")
            elif self.options.valAttributeNames:
                if not elDcl.attributes:
                    self.ValErr(f"No ATTLIST for element '{elemName}'.")
                for k, v in attrs.items():
                    if k in elDcl.attributes: continue
                    if "#anyAttribute" in elDcl.attributes: continue
                    self.ValErr(f"Undeclared attribute '{k}' for element '{elemName}'.")

#         if self.options.saxAttribute:
#             self.doCB(SaxEvent.START, elemName, None, empty)
#             for k, v in attrs.items():
#                 self.doCB(SaxEvent.ATTRIBUTE, k, v)
#         else:
#             self.doCB(SaxEvent.START, elemName, attrs)
#         if empty: self.doCB(SaxEvent.END, elemName)

        return elemName, attrs, empty

    def readAttributes(self, ss:bool=True, elemName:NMTOKEN_t=None) -> OrderedDict:
        """This is purely a syntax read, so it can be used for start-tags,
        but also for quasi-attribute lists such as the XML declaration,
        optional PIs declared to work like that, etc. No validation/types here.
        """
        #lg.info("*** %s, buf '%s'.", callerNames(), self.sr.bufSample)
        attrs = OrderedDict()
        while (True):
            attrName, attrValue, bang = self.readAttribute(ss=ss)
            if attrName is None: break
            if self.options.attributeFold:
                attrName = self.options.attributeFold.normalize(attrName)
            # TODO Fold and normalize and cast value per schema
            attrs[attrName] = attrValue  # Move to caller or pass in elem name?
            if bang:
                if (elemName, attrName) in self.bangAttrs:  # TODO Pass in elemName
                    self.SynErr(f"!= previously used for '{attrName}@{attrName}'.")
                self.bangAttrs[(elemName, attrName)] = attrValue
        return attrs

    def readAttribute(self, ss:bool=True, keepPunc:bool=False) -> (str, str, bool):
        """Used in start-tags and also in XML DCL.
        Supports optional extensions such as curly or unquoted values,
        boolean shorthand, and "!=" to set an enduring default.
        Extensions:
            <p +border -foo id=spam_37 zork!="1"
        Returns: name, value, and 'bang' -- bang is True iff we got "!=".
        Does not do anything about attribute type.
        """
        #lg.info("*** %s, buf '%s'.", callerNames(), self.sr.bufSample)
        if ss: self.sr.skipSpaces()
        #lg.warning(f"readAttribute, after ss, buf starts '{self.sr.peek(10)}'.")
        bang = False
        if self.options.booleanAttribute and self.sr.peek() in "+-":
            which = self.sr.consume()
            if not (attrName := self.readName(ss)):
                self.SynErr("Expected name after +/- for boolean attribute.")
            lg.warning("Got boolean attribute prefix '%s' for '%s'.", which, attrName)
            if (self.options.booleanIsName):
                val = "1" if (which == "+") else "0"
            else:
                val = attrName if (which == "+") else ""
            return (attrName, val, bang)

        attrName = self.readName(ss)
        if not attrName:
            return (None, None, bang)
        #lg.warning(f"Attribute name '{attrName}'.")

        # TODO Add bangAttrType !typename=...
        if self.options.bangAttribute and self.readConst("!=", ss):  # Set default
            # TODO Warn if conflicts with a prior, or isn't first use.
            bang = True
        elif self.readConst("=", ss):
            bang = False
        else:
            self.SynErr("Expected '=' after attribute name.")

        attrValue = self.readQLit(ss, keepPunc)
        if attrValue:
            #lg.warning(f"Attribute value is qlit '{attrValue}' ({type(attrValue)}).")
            return (attrName, attrValue, bang)
        if self.options.unQuotedAttribute and (attrValue := self.readName(ss)):
            lg.warning("Attribute value for %s is unquoted (%s).", attrName, attrValue)
            return (attrName, attrValue, bang)

        return (None, None, bang)

    def normalizeAttributeValues(self, elemName:QName_t, attrs:Dict):
        """Do declareation-dependent processing on attributes. Includes:
            space norm; case norm; ws norml type cast; add default attrs.

        TODO: Is this the right behavior in detail for attr norm?
            if no attlist for this element
                if not noAttributeNorm: norm whitespace
            elif no attlist for this attribute:
                if not undclAttributes: syntax error
                if not noAttributeNorm: norm whitespace
            else:  # got a dcl to try
                if dcl.datatype.whitespacenorm:
                    norm whitespace
                if dcl.datatype.type is ID or k == "xml:id":
                    if idFold: fold
                    if non-unique: syntax error
                if xsdTypes:
                    cast
        """
        try:
            attrDclsForElem = self.sr.doctype.elemDcls[elemName]
        except (AttributeError, KeyError):
            attrDclsForElem = None

        # Apply any defaults
        if attrDclsForElem is not None:
            for attrName, attrDcl in attrDclsForElem.items():
                if attrName not in attrs: attrs[attrName] = attrDcl.default

        # Check and normalize what we've got
        attrNames = attrs.keys()
        for k in attrNames:
            try:
                theDcl = attrDclsForElem[k]
            except (IndexError, KeyError, TypeError):
                theDcl = None
            if attrDclsForElem is None:  # Normalize space, only.
                if self.options.noAttributeNorm: continue
                if normFn := self.options.wsNorm:
                    attrs[k] = normFn.normalize(attrs[k])
            elif attrDclsForElem and k not in attrDclsForElem:
                self.SynErr(f"Undeclared attribute '{k}' for element '{elemName}'.")

        return attrs

    def readEndTag(self, ss:bool=True) -> str:
        #lg.info("*** %s, buf '%s'.", callerNames(), self.sr.bufSample)
        if self.options.emptyEnd and self.readConst("</>"):
            name = self.tagStack.topName
            if not name: self.SynErr("</> with nothing open")
            self.doCB(SaxEvent.END, name)
            return name
        if not self.readConst("</", ss):
            raise DOMException(f"readEndTag called but at '{self.sr.bufSample}'.")

        name = self.readName(ss)
        if not name and self.options.simultaneous:
            name = self.readNameGroup()  # TODO ??? </(x|y)> or something else?
        if not name and self.options.emptyEnd:
            name = self.tagStack.topName
        if not name:
            self.SynErr("Expected name in end-tag")
        if self.options.elementFold:
            if len(name) == 1:
                name = self.options.elementFold.normalize(name)
            else:
                for i in range(len(name)):
                    name[i] = self.options.elementFold.normalize(name[i])

        if not self.readConst(">", ss):
            self.SynErr(f"Unclosed end-tag for '{name}'.")
        #self.doCB(SaxEvent.END, name)
        return name

    def readMSOpening(self, ss:bool=True) -> str:
        """This optionally recognizes the full set of SGML marked section
        keywords, but they're not all fully implemented yet.  TODO

        * IGNORE and CDATA are done entirely here, and consume the ]]>.
        * Others (INCLUDE, TEMP, RCDATA) are nestable andrequire parsing, so
          they get stacked. The caller pops on seeing "]]>".
        """
        #lg.info("*** %s, buf '%s'.", callerNames(), self.sr.bufSample)
        MSKeys = {
            "CDATA": 1,
            "RCDATA": 2,
            "IGNORE": 3,
            "INCLUDE": 4,
            "TEMP": 5,
        }
        if not self.readConst("<![", ss):
            return None

        # TODO support parameter entities?
        # skipSpaces(entOpener=readPEntRef)

        if not (keys := self.readToString("[")):
            self.SynErr("Unfinished marked section start.")
        topKey = ""
        if self.options.keywordFold: keys = keys.upper()
        for key in self.expandPEntities(keys).split():
            if not topKey or MSKeys[key] < MSKeys[topKey]: topKey = key

        if topKey == "CDATA":
            # In XML these aren't nestable.
            data = self.readToString("]]>", consumeEnder=True)
            if not data: self.SynErr("Unclosed CDATA section.")
            self.doCB(SaxEvent.CDATA)
            self.doCB(SaxEvent.CHAR, data)
            self.doCB(SaxEvent.CDATAEND)
            return data
        elif not self.options.MSType:
            self.SynErr(f"Found '<![' but with keyword '{topKey}', not '<![CDATA['.")
        # TODO Unfinished. rcdata is easy; include/temp are a pain
        elif topKey == "IGNORE":
            self.readToString("]]>", consumeEnder=True)
        elif topKey == "RCDATA":
            raise NSuppE(f"Unsupported SGML MS Keyword {topKey}")  # TODO
        elif topKey == "INCLUDE" or topKey == "TEMP":
            self.msStack.append(topKey)
            raise NSuppE(f"Unsupported SGML MS Keyword {topKey}")
        else:
            raise NSuppE(f"Unknown SGML MS Keyword {topKey}")
        return topKey

    def readEntRef(self) -> None:
        """Passed to skipSpaces 'entOpener' arg as a callback, when
        an entity ref may be recognized.
        Reads the reference and tries to find/open the entity.
        """
        if not self.readConst("&"): return
        # TODO &#...
        entName = self.readName()
        if not entName:
            self.EntErr(f"Incomplete entity reference name '{entName}').")
        if not self.readConst(";"):
            self.EntErr(f"Unterminated entity reference to '{entName}'.")

        try:
            entDef = self.sr.spaces[EntitySpace.GENERAL][entName]
        except KeyError:
            self.EntErr("Unknown entity '%s'. Known: %s." % (entName))
        # TODO Who checks isEntRefPermitted?
        frame = InputFrame(options=self.options)
        frame.addEntity(entDef)
        return

    def readPEntRef(self) -> None:
        """Passed to skipSpaces as a callback, when it should detect and
        handle a parameter entity ref.
        Reads the reference and try to find/open the entity.
        """
        if not self.readConst("%"): return
        entName = self.readName()
        if not entName:
            self.EntErr(f"Incomplete parameter entity reference name '{entName}').")
        if not self.readConst(";"):
            self.EntErr(f"Unterminated parameter entity reference to '{entName}'.")

        try:
            entDef = self.sr.spaces[EntitySpace.PARAMETER][entName]
        except KeyError:
            self.EntErr("Unknown parameter entity '%s'. Known: %s." % (entName))
        # TODO Who checks isEntRefPermitted?
        frame = InputFrame(options=self.options)
        frame.addEntity(entDef)
        return

    def openEntity(self, space:EntitySpace, entName:NMTOKEN_t) -> None:
        assert space in self.sr.spaces
        try:
            entDef = self.sr.spaces[space][entName]
        except KeyError as e:
            raise SyntaxError(f"Unknown {space.name} entity '{entName}'.") from e
        if not self.isEntRefPermitted(entDef):
            # TODO Ignore, warn, or terminate?
            return None
        lg.info("Opening {space.name} entity '%s'.", entName)
        frame = InputFrame(options=self.options)
        frame.addEntity(entDef)
        self.sr.open(frame)

    def expandPEntities(self, s:List, depth:int=0) -> str:
        """Expand parameter entity references in a string.
        's' is a list of chars, not a regular string.
        """
        if depth > self.options.MAXENTITYDEPTH:
            self.EntErr(f"Parameter entity too deep ({depth}).")

        s = ''.join(s)
        expBuf = re.sub(Rune.pentref_re, self.getPEText, s)
        if len(expBuf) > self.options.MAXEXPANSION: raise ValueError(
            "Parameter entity expansion exceeds MAXEXPANSION (%d)."
            % (self.options.MAXEXPANSION))
        if re.search(Rune.pentref_re, expBuf):
            expBuf = self.expandPEntities(expBuf, depth=depth+1)
        return expBuf

    def getPEText(self, mat:re.Match) -> str:
        return self.getEntityText(mat.group(), space=EntitySpace.PARAMETER)

    def getEntityText(self, entName:NMTOKEN_t, space:EntitySpace) -> str:
        try:
            entDef = self.sr.spaces[space][entName]
            if not self.isEntRefPermitted(entName):
                return f"<?rejected SPACE='{entDef.entSpace.name}' ENTITY='{entName}'?>"
            if entDef.literal is not None:
                return entDef.literal
            frame = InputFrame(entDef, options=self.options)
            text = frame.readAll()
            frame.close()
        except KeyError as e:
            raise KeyError(f"Unknown {entDef.entSpace.name} entity '{entName}'.") from e
        return text

    def isEntRefPermitted(self, entDef:EntityDef, fatal:bool=False) -> bool:
        """Implement some entity-expansion safety protocols.
        """
        if self.sr.isEntityOpen(entDef.entSpace, entDef.entName):  # Always fatal
            self.EntErr(f"{entDef.entSpace.name} entity {entDef.entName} is already open.")
            return False
        if self.sr.depth >= self.options.MAXENTITYDEPTH:
            if fatal: self.EntErr(f"Too much entity nesting, depth {self.sr.depth}.")
            return False
        if (not self.options.charEntities
            and entDef.entParsing == EntityParsing.SDATA):
            if fatal: self.EntErr("Character entities are disabled.")
            return True

        if not (entDef.publicId or entDef.systemId):
            return True

        # Rest is just for external entities
        if (not self.options.extEntities):
            if fatal: self.EntErr(
                "External (PUBLIC and SYSTEM) entities are disabled.")
            return False
        if (not self.options.netEntities):
            sid = entDef.systemId
            if "://" in sid and not sid.startswith("file://"):
                self.EntErr("Non-file URIs for SYSTEM identifiers are disabled.")
        if (self.options.entityDirs):
            if "../" in entDef.systemId:  # TODO Resolve realpath first?
                if fatal: self.EntErr(
                    "'../' but entityDirs option is set: " + entDef.systemId)
                return False
            found = False
            for okDir in self.options.entityDirs:
                if entDef.systemId.startswith(okDir):
                    found = okDir
                    break
            if (not found): self.EntErr(
                f"systemId for '{entDef.entName}' not in an allowed entDir.")
        return True
