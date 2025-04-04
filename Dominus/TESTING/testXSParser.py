#!/usr/bin/env python3
#
import os
#import re
#import codecs
import unittest
import logging
from typing import Dict
from types import ModuleType
from collections import defaultdict

from xml.parsers import expat

from documenttype import EntityDef, EntitySpace, EntityParsing
import xsparser
from xsparser import XSParser
from stackreader import InputFrame  #, StackReader
from runeheim import CaseHandler
from saxplayer import SaxEvent
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

myStack = []
eventCounts = defaultdict(int)


###############################################################################
#pylint: disable=W0613
#
def pr(s:str, *args):
    if args: s += " ".join(args)
    print("  " * len(myStack), "Event: ", s)

def common(typ:SaxEvent, name:str="") -> None:
    eventCounts[typ] += 1
    pr("%s:  %s", typ.name, name)

def StartElement(name:str, attrs:Dict=None) -> None:
    common(SaxEvent.START)
    myStack.append(name)
def EndElement(name:str) -> None:
    common(SaxEvent.END)
    myStack.pop()
def CharacterData(data:str="") -> None:
    common(SaxEvent.CHAR)
def StartCdataSection() -> None:
    common(SaxEvent.CDATA)
def EndCdataSection() -> None:
    common(SaxEvent.CDATAEND)
def ProcessingInstruction(target:str="", data:str="") -> None:
    common(SaxEvent.PROC)
def Comment(data:str="") -> None:
    common(SaxEvent.COMMENT)

def StartDoctypeDecl(doctypeName:str, systemId="", publicId="",
    has_internal_subset:bool=False) -> None:
    common(SaxEvent.DOCTYPE)
def EndDoctypeDecl() -> None:
    common(SaxEvent.DOCTYPEEND)

def Default(data:str="") -> None:
    common(SaxEvent.DEFAULT)

def ElementDecl(name:str, model:str="") -> None:
    common(SaxEvent.ELEMENTDCL)
def AttlistDecl(elname:str, attname, typ="", default="", required=False) -> None:
    common(SaxEvent.ATTLISTDCL)
def NotationDecl(notationName:str, base="", systemId="", publicId="") -> None:
    common(SaxEvent.NOTATIONDCL)
def EntityDecl(entityName:str, is_parameter_entity=False, value="", base="",
    systemId="", publicId="", notationName=None) -> None:
    common(SaxEvent.ENTITYDCL)
def UnparsedEntityDecl(entityName:str, value="", base="",
    systemId="", publicId="", notationName=None) -> None:
    common(SaxEvent.UENTITYDCL)

def EntityReference(context:str, base:str, systemId:str, publicId:str) -> None:
    common(SaxEvent.ENTREF)
def Entity(name:str="") -> None:
    common(SaxEvent.ENTITY)

def setHandlers(parser):
    parser.StartElementHandler = StartElement
    parser.EndElementHandler = EndElement
    parser.CharacterDataHandler = CharacterData
    parser.StartCdataSectionHandler = StartCdataSection
    parser.EndCdataSectionHandler = EndCdataSection
    parser.ProcessingInstructionHandler = ProcessingInstruction
    parser.CommentHandler = Comment

    parser.StartDoctypeDeclHandler = StartDoctypeDecl
    parser.EndDoctypeDeclHandler = EndDoctypeDecl
    parser.ElementDeclHandler = ElementDecl
    parser.AttlistDeclHandler = AttlistDecl
    parser.EntityDeclHandler = EntityDecl
    parser.NotationDeclHandler = NotationDecl

    #parser.ExternalEntityRefHandler = ExternalEntityRef
    parser.DefaultHandler = Default

    #parser.StartNamespaceDeclHandler(prefix, uri)
    #parser.EndNamespaceDeclHandler(prefix)

    #parser.DefaultHandlerExpand(data)
    #parser.SkippedEntityHandler(entityName, is_parameter_entity)

def runParser(pc:ModuleType, path:str=None, string:str=None, encoding:str="utf-8"):
    assert isinstance(expat, ModuleType)
    parser = pc.ParserCreate()
    setHandlers(parser)
    myStack.clear()
    eventCounts.clear()
    if (path):
        print(f"Parsing file {path} with {pc.__name__}.")
        assert os.path.isfile(path)
        with open(path, "rb") as ifh:
            parser.ParseFile(ifh)
    else:
        print(f"Parsing a string with {pc.__name__}.")
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

    def xxxtest_Basics(self):
        ch1 = EntityDef(
            entName="samp",
            entSpace=EntitySpace.GENERAL,
            entParsing=EntityParsing.PCDATA,
            systemId=sampleEnt)
        frame = InputFrame()
        frame.addEntity(ch1)
        thePath = frame.findLocalPath(eDef=ch1)
        self.assertTrue(os.path.isfile(thePath))

        #data="<chap><ti>Hello</ti></chap>"

        _soup = EntityDef(
            entName="soup",
            entSpace=EntitySpace.PARAMETER,
            data="i | b | tt | mono")

        with self.assertRaises(OSError):
            ch2 = EntityDef(
                entName="chap2",
                entSpace=EntitySpace.GENERAL,
                entParsing=EntityParsing.PCDATA,
                systemId=sampleEnt)

        frame = InputFrame()
        frame.addEntity(ch2)
        while (c := frame.consume()):
            assert len(c) == 1
            frame.skipSpaces()

        self.assertFalse(frame.readConst(
            "PUBLIC", thenSp=True, folder=CaseHandler.UPPER))
        self.assertFalse(frame.readBaseInt())
        self.assertFalse(frame.readInt())
        self.assertFalse(frame.readFloat())
        self.assertFalse(frame.readName())
        self.assertFalse(frame.readEnumName(names=[ "PUBLIC", "SYSTEM" ]))
        self.assertFalse(frame.readRegex(r'"\w+"'))
        self.assertFalse(frame.readToString(ender=">"))

    def test_basicDTD(self):
        options = { "emptyEnd": False, "elementFold": False, "xsdType": False }
        xsp = XSParser(options=options)
        xsp.ParseFile(sampleDTD)


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

        runParser(xsparser, path=sampleBoth)

        xml = """<?xml encoding="utf-8"?>
<html>
<head><title>Untitled</title></head>
<body><h1>by Anonymous</h1>
<p class="fo">Some text that's dumb &amp; <i>important</i></p>
</body>
</html>
"""

        with self.assertRaises(ValueError):
            xsp = XSParser(options={ "curlyQuote":True, "NotAnOption":False })
        xsp = XSParser()
        xsp.Parse(xml)

if __name__ == '__main__':
    unittest.main()
