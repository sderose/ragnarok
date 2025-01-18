#!/usr/bin/env python3
#
import os
import re
#import codecs
import unittest
import logging
from typing import Dict
from types import ModuleType
from collections import defaultdict

from xml.parsers import expat

from documenttype import EntityDef, EntitySpace, EntityParsing
import xsparser
from xsparser import StackReader
from xmlstrings import CaseHandler
#from saxplayer import SaxEvent
#from makeTestDoc import makeTestDoc0, DAT_DocBook  #, DBG

lg = logging.getLogger("testNode3")
logging.basicConfig(level=logging.INFO)

nsURI = "https://example.com/namespaces/foo"

sampleDoc = "../DATA/sampleHTML.xml"
sampleGE = "../DATA/sampleGE.xml"
sampleDTD = "../DATA/sampleHTML.dtd"
sampleBoth = "../DATA/sampleHTMLWithDTD.xml"
sampleEnt = "../DATA/sampleExtEntity.xml"

# Internal sample document
#
tdoc = """<html>
<head><title>Eine Kleine NachtSchrift</title>
</head>
<body>
<h1>Here <i>it</i> is.</h1>
<p>For what it's worth &amp; costs.</p>
<p id="zork" class="big blue" />
<!-- comments, too? -->
<?and a PI?>
<p>-30-</p>
</body>
</html>
"""

depth = 0
eventCounts = defaultdict(int)


###############################################################################
#pylint: disable=W0613
#
def pr(s:str):
    print("  " * depth, s)

def START(name:str, attrs:Dict=None) -> None:
    global depth
    eventCounts["START"] += 1
    pr(f"START:  {name}, {attrs}")
    depth += 1
def END(name:str) -> None:
    global depth
    eventCounts["END"] += 1
    depth -= 1
    pr(f"END:  {name}")
def CHAR(data:str="") -> None:
    if (data.strip() == ""): return
    pdata = re.sub(r"\n", "\\\\n", data)
    eventCounts["CHAR"] += 1
    pr(f"CHAR:  (len {len(data)}): '{pdata}'")
def CDATA() -> None:
    eventCounts["CDATA"] += 1
    pr("CDATA")
def CDATAEND() -> None:
    eventCounts["CDATAEND"] += 1
    pr("CDATAEND")
def PROC(target:str="", data:str="") -> None:
    eventCounts["PROC"] += 1
    pr(f"PROC:  {target}: {data}")
def COMMENT(data:str="") -> None:
    eventCounts["COMMENT"] += 1
    pr(f"COMMENT:  {data}")

def DOCTYPE(doctypeName:str, systemId="", publicId="", has_internal_subset:bool=False) -> None:
    eventCounts["DOCTYPE"] += 1
    pr(f"DOCTYPE:  {doctypeName}")
def DOCTYPEEND() -> None:
    eventCounts["DOCTYPEEND"] += 1
    pr("DOCTYPEEND")

def DEFAULT(data:str="") -> None:
    eventCounts["DEFAULT"] += 1
    pr(f"DEFAULT:  {data}")

def ELEMENTDCL(name:str, model:str="") -> None:
    eventCounts["ELEMENTDCL"] += 1
    pr(f"ELEMENTDCL:  {name}")
def ATTLISTDCL(elname:str, attname, typ="", default="", required=False) -> None:
    eventCounts["ATTLISTDCL"] += 1
    pr(f"ATTLISTDCL:  {elname}@{attname}")
def ENTITYDCL(entityName:str, is_parameter_entity=False, value="", base="",
    systemId="", publicId="", notationName=None) -> None:
    eventCounts["ENTITYDCL"] += 1
    pr(f"ENTITYDCL:  {entityName}")
def NOTATIONDCL(notationName:str, base="", systemId="", publicId="") -> None:
    eventCounts["NOTATIONDCL"] += 1
    pr(f"NOTATIONDCL:  {notationName}")

def ENTREF(context:str, base:str, systemId:str, publicId:str) -> None:
    eventCounts["ENTREF"] += 1
    pr(f"ENTREF:  {context}")
def ENTITY(name:str="") -> None:
    eventCounts["ENTITY"] += 1
    pr(f"ENTITY:  {name}")

def NOTATION(name:str, *args) -> None:
    eventCounts["NOTATION"] += 1
    print(f"NOTATION:  {name}")

def setHandlers(parser):
    parser.StartElementHandler = START
    parser.EndElementHandler = END
    parser.CharacterDataHandler = CHAR
    parser.StartCdataSectionHandler = CDATA
    parser.EndCdataSectionHandler = CDATAEND
    parser.ProcessingInstructionHandler = PROC
    parser.CommentHandler = COMMENT

    parser.StartDoctypeDeclHandler = DOCTYPE
    parser.EndDoctypeDeclHandler = DOCTYPEEND
    parser.ElementDeclHandler = ELEMENTDCL
    parser.AttlistDeclHandler = ATTLISTDCL
    parser.EntityDeclHandler = ENTITYDCL
    parser.NotationDeclHandler = NOTATIONDCL
    parser.ExternalEntityRefHandler = ENTREF
    parser.DefaultHandler = DEFAULT

    #StartNamespaceDeclHandler(prefix, uri)
    #EndNamespaceDeclHandler(prefix)

    #DefaultHandlerExpand(data)
    #SkippedEntityHandler(entityName, is_parameter_entity)
    #StackReader(tdoc)    # TODO: Upgrade to handle parses....
    #sp.parseDocument(tdoc)

def runParser(pc:ModuleType, path:str=None, string:str=None, encoding:str="utf-8"):
    global depth
    assert isinstance(expat, ModuleType)
    parser = pc.ParserCreate()
    setHandlers(parser)
    depth = 0
    eventCounts.clear()
    if (path):
        print(f"\n\nParsing file {path} with {pc.__name__}.")
        assert os.path.isfile(path)
        with open(path, "rb") as ifh:
            parser.ParseFile(ifh)
    else:
        print(f"\n\nParsing a string with {pc.__name__}.")
        parser.Parse(string)

    showEventCounts()

def showEventCounts():
    for k, v in eventCounts.items():
        print("    %-16s %4d" % (k, v))


###############################################################################
#
class TestXSP(unittest.TestCase):
    alreadyShowedSetup = False

    def setUp(self):
        print("In TestXSP")

    def test_Basics(self):
        ch1 = EntityDef(
            entName="samp",
            entSpace=EntitySpace.GENERAL,
            entParsing=EntityParsing.PCDATA,
            systemId=sampleEnt)
        thePath = ch1.dataSource.findLocalPath(eDef=ch1, trace=True)
        self.assertTrue(os.path.isfile(thePath))

        #data="<chap><ti>Hello</ti></chap>"

        _soup = EntityDef(
            entName="soup",
            entSpace=EntitySpace.PARAMETER,
            data="i | b | tt | mono")

        with self.assertRaises(OSError):
            _ch2 = EntityDef(
                entName="chap2",
                entSpace=EntitySpace.GENERAL,
                entParsing=EntityParsing.PCDATA,
                systemId=sampleEnt)

        ef = xsparser.EntityFrame(ch1)
        while (c := ef.consume()):
            assert len(c) == 1
            ef.skipSpaces()

        self.assertFalse(ef.readConst("PUBLIC", thenSp=True, folder=CaseHandler.UPPER))
        self.assertFalse(ef.readBaseInt())
        self.assertFalse(ef.readInt())
        self.assertFalse(ef.readFloat())
        self.assertFalse(ef.readName())
        self.assertFalse(ef.readEnumName(names=[ "PUBLIC", "SYSTEM" ]))
        self.assertFalse(ef.readRegex(r'"\w+"'))
        self.assertFalse(ef.readToString(ender=">"))
        self.assertFalse(ef.readToAnyOf(enders=[ "\n", "$" ]))

    def test_basicDTD(self):
        sr = StackReader(rootPath=sampleDTD,
            options={ "emptyEnd": True, "elementFold": True, "xsdType": True })
        print(repr(sr))
        sr.isOpen(space=EntitySpace.GENERAL, name="chap1")

    def test_doc(self):
        StackReader(rootPath=sampleDTD,
            options={ "emptyEnd": True, "elementFold": True, "xsdType": True })


###############################################################################
#
@unittest.skip
class TestExpat(unittest.TestCase):
    def setup(self):
        print("In TestExpat")

    def testExpat(self):
        runParser(expat, string=tdoc)

        runParser(expat, path=sampleDoc)


###############################################################################
#
class TestXSPDocs(unittest.TestCase):
    def setup(self):
        print("In TestXSP")

    def testXSP(self):
        runParser(xsparser, string=tdoc)

        runParser(xsparser, path=sampleGE)

        runParser(xsparser, path=sampleDoc)

        runParser(xsparser, path=sampleDTD)

        #runParser(xsparser, path=sampleBoth)

if __name__ == '__main__':
    unittest.main()
