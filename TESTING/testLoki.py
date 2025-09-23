#!/usr/bin/env python3
#
import os
#import re
#import codecs
import unittest
import logging
from typing import Dict, Any
from types import ModuleType
from collections import defaultdict

from xml.parsers import expat

from documenttype import EntityDef, EntitySpace, EntityParsing
import loki
from loki import Loki
from stackreader import InputFrame, StackReader
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
class TestLoki(unittest.TestCase):
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
        thePath = frame.source.findLocalPath(entDef=ch1)
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
        xsp = Loki(options=options)
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
class TestLokiDocs(unittest.TestCase):
    def setup(self):
        print("In TestXSP")

    def testXSP(self):
        who = loki
        runParser(who, string=tdoc)

        runParser(who, path=sampleGE)

        runParser(who, path=sampleDoc)

        runParser(who, path=sampleDTD)

        runParser(who, path=sampleBoth)

        xml = """<?xml encoding="utf-8"?>
<html>
<head><title>Untitled</title></head>
<body><h1>by Anonymous</h1>
<p class="fo">Some text that's dumb &amp; <i>important</i></p>
</body>
</html>
"""

        with self.assertRaises(ValueError):
            xsp = Loki(options={ "curlyQuote":True, "NotAnOption":False })
        xsp = Loki()
        xsp.Parse(xml)


###############################################################################
#
class TestXSPExtensions(unittest.TestCase):
    def setup(self):
        print("In TestXSP")

    def tryOption(self, xml:str, optName:str, optValue:Any=True) -> None:
        """Parse and find syntax error; then set option and it should pass.
        """
        with self.assertRaises(SyntaxError):
            xsp = Loki()
            #import pudb; pudb.set_trace()
            xsp.Parse(xml)

        xsp = Loki(options={optName:optValue})
        xsp.Parse(xml)

    def passOption(self, xml:str, optName:str, optValue:Any=True) -> None:
        """These don't create a syntax error without the options, but should
        come out different.
        """
        xsp = Loki(options={optName:optValue})
        xsp.Parse(xml)

    def XtryOption(self, *args):
        return

    #@unittest.skip
    def testXLimits(self):
        ### Limits
        #
        self.XtryOption("""<doc><p id="foo">Ok.</p></doc>""",
            "MAXEXPANSION", 1<<20)  # Limit expansion length of entities
        self.XtryOption("""<doc><p id="foo">Ok.</p></doc>""",
            "MAXENTITYDEPTH", 1000)  # Limit nesting of entities
        self.XtryOption("""<doc><p id="foo">Ok.</p></doc>""",
            "charEntities", True)  # Allow SDATA and CDATA entities
        self.XtryOption("""<doc><p id="foo">Ok.</p></doc>""",
            "extEntities", True)  # External entity refs?
        self.XtryOption("""<doc><p id="foo">Ok.</p></doc>""",
            "netEntities", True)  # Off-localhost entity refs?
        self.XtryOption("""<doc><p id="foo">Ok.</p></doc>""",
            "entityDirs", [])  # Permitted dirs to get ents from

    #@unittest.skip
    def testXCase(self):
        ### Case and Unicode
        #
        self.XtryOption("""<doc><p id="foo">Ok.</P></doc>""",
            "elementFold", CaseHandler.UPPER)
        self.XtryOption("""<doc><p ID="foo">Ok.</p></doc>""",
            "attrFold", CaseHandler.LOWER)
        self.XtryOption("""<doc><p id="foo">Ok.</p></doc>""",
            "entityFold", CaseHandler.UPPER)
        self.XtryOption("""<doc><p id="foo">Ok.</p></doc>""",
            "keywordFold", CaseHandler.UPPER)
        self.XtryOption("""<doc><p id="foo">Ok.&#260;</p></doc>""",
            "noC1", False)  # No C1 controls

    #@unittest.skip
    def testXCase2(self):  # TODO Add cases
        self.XtryOption("""<doc><p id="foo">Ok.</p></doc>""",
            "uNormHandler", CaseHandler.UPPER)
        self.XtryOption("""<doc><p id="foo">Ok.</p></doc>""",
            "wsDef", None)
        self.XtryOption("""<doc><p id="foo">Ok.</p></doc>""",
            "radix", ".")

    #@unittest.skip
    def testXSchema(self):
        ### Schemas
        #
        self.XtryOption("""<doc><p id="foo">Ok.</p></doc>""",
            "schemaType", "DTD")  # <!DOCTYPE foo SYSTEM "" NDATA XSD>
        self.XtryOption("""<doc><p id="foo">Ok.</p></doc>""",
            "fragComments", True)  # In-dcl like SGML
        #self.XtryOption("""<!DOCTYPE foo [ <!ENTITY soup (i b tt mono)> ]>""",
        #    "setDcls", True)  # <!ENTITY % x SET (i b tt)>

    #@unittest.skip
    def testXElements(self):  # TODO Add cases
        ### Elements
        #
        self.XtryOption("""<!DOCTYPE foo [ <!ELEMENT (x|y|z) #PCDATA> ]>""",
            "groupDcl", True)  #
        self.XtryOption("""<!DOCTYPE foo [ <!ELEMENT p - - ANY> ]>""",
            "oflag", True)
        self.XtryOption("""<!DOCTYPE foo [ <!ELEMENT p RCDATA> ]>""",
            "sgmlWord", True)  # CDATA RCDATA #CURRENT etc.
        self.XtryOption("""<doc><p id="foo">Ok.</p></doc>""",
            "mixel", True)  # Dcl content ANYELEMENT
        self.XtryOption("""<!DOCTYPE foo [ <!ELEMENT x ANY -(p|q) +(i)> ]>""",
            "mixins", True)  # cf incl exceptions
        self.XtryOption("""<!DOCTYPE foo [ <!ELEMENT p (x|y{3,9)|z){1,}>""",
            "repBrace", True)  # {min,max} for repetition
        self.XtryOption("""<!DOCTYPE foo [ <!ELEMENT p (x|y{a!})|z)>""",
            "repBrace", True)  # {min,max} for repetition

        self.tryOption("""<doc><p id="foo">Ok.</></doc>""",
            "emptyEnd", True)  # </>
        self.tryOption("""<doc><p id="foo">Ok.<|>right<|>ok.</p></doc>""",
            "restart", True)
        self.XtryOption("""<doc><p|q id="foo">Ok.</p|q></doc>""",
            "simultaneous", True)
        self.XtryOption("""<doc><p id="foo">Ok.</p></doc>""",
            "multiTag", True)  # <div/title>...</title/div>
        self.tryOption("""<doc><p id="foo">Ok.<-p>not there<+p> but there</p></doc>""",
            "suspend", True)   # TODO
        self.tryOption("""<doc><p id="foo">Ok, <i>dude, </p> there.</i></doc>""",
            "olist", True)

    #@unittest.skip
    def testXAttributes(self):
        ### Attributes
        #
        self.tryOption("""<!DOCTYPE X [
            <!ATTLIST * id ID #IMPLIED> ]>""",
            "globalAttr", True)  #
        self.tryOption("""<!DOCTYPE X [
            <!ATTLIST foo #ANY CDATA #IMPLIED> ]>""",
            "anyAttr", True)
        self.tryOption("""<!DOCTYPE X [
            <!ATTLIST foo x float #IMPLIED> ]>""",
            "xsdType", True)
        self.XtryOption("""<!DOCTYPE X [
            <!ATTLIST foo x floats #IMPLIED> ]>""",
            "xsdPlural", True)
        self.XtryOption("""<doc><p id="foo">Ok.</p></doc>""",
            "specialFloat", True)  # Nan Inf etc. (needed?)
        self.XtryOption("""<!DOCTYPE X [
            <!ATTLIST quo cid COID #IMPLIED> ]>""",
            "coID", True)
        self.XtryOption("""<!DOCTYPE X [
            <!ATTLIST quo id ID #IMPLIED qid QID #IMPLIED> ]>
            <X xmlns:ns1="http://example.com/ns"><quo id="ns1:myId">eh?</quo></X>""",
            "nsID", True)
        self.XtryOption("""<!DOCTYPE X [
            <!ATTLIST quo sid STACKID #IMPLIED> ]>
            <X><quo id="l1"><quo id="l2"><quo id="l3">eh?</quo></quo></quo></X>""",
            "stackID", True)
        self.tryOption("""<doc><p id=foo>Ok.</p></doc>""",
            "unQuotedAttr", True)  # <p x=foo>
        self.tryOption("""<doc><p id=“foo”>Ok.</p></doc>""",
            "curlyQuote",True)
        self.tryOption("""<doc><p +border id="p1" -foo>Ok.</p></doc>""",
            "booleanAttr", True)
        with self.assertRaises(SyntaxError):
            self.tryOption("""<doc><p + id="p1">Ok.</p></doc>""",
                "booleanAttr", True)
            self.tryOption("""<doc><p id="p1" ->Ok.</p></doc>""",
                "booleanAttr", True)
        self.tryOption("""<doc><p id!="foo">Ok.</p><p>Got it?</p></doc>""",
            "bangAttr", True)  # != on first use to set dft
        self.tryOption("""<doc><p id!int8="99">Ok.</p><p>Got it?</p></doc>""",
            "bangAttrType", True)

    def testWF(self):
        with self.assertRaises(SyntaxError):
            # XML dcl
            Loki().Parse('<?xml version="1.1" encoding="utf-8" ?')
            Loki().Parse('<?xml version="1. ?>')
            Loki().Parse('<?xml version="2.0" ?>')
            Loki().Parse('<?xml encoding="utf-8" ?>')

            # DOCTYPE
            Loki().Parse('<!DOCTYPE []>')
            Loki().Parse('<!DOCTYPE html ]>')
            Loki().Parse('<!DOCTYPE [ ] <book>')
            Loki().Parse('<!DOCTYPE [ Hello ]>')

            # Dcls
            Loki().Parse('<!DOCTYPE [ <!ELEMENT> ]>')
            Loki().Parse('<!DOCTYPE [ <!ATTLIST> ]>')
            Loki().Parse('<!DOCTYPE [ <!ENTITY> ]>')
            Loki().Parse('<!DOCTYPE [ <!NOTATION> ]>')

            # Start tags
            Loki().Parse('<book><p>Hello.</q></book>')
            Loki().Parse('<book><p>Hello.</q></book>')
            Loki().Parse('<book><p><q>Hello.</p></book>')
            Loki().Parse('<book><p/Hello.</q></book>')
            Loki().Parse('<book><p>Hello.')

            # End tags
            Loki().Parse('<book><p>Hello.</</book>')
            Loki().Parse('<book><p>Hello.</p id="a1"></book>')
            Loki().Parse('<book><p>Hello.</p></book></book>')
            Loki().Parse('<book><p>Hello.</p></book>Junk')

            # Attributes
            Loki().Parse('<book><p 12="a" >Hello.</p></book>')
            Loki().Parse('<book><p q:rs_12+a="a">Hello.</p></book>')
            Loki().Parse('<book><p id= >Hello.</p></book>')
            Loki().Parse('<book><p id=" >Hello.</p></book>')
            Loki().Parse('<book><p border>Hello.</p></book>')

            # Marked sections
            Loki().Parse('<book><p>Hello.]]></book>')
            Loki().Parse('<book><![CD[ This is it.]]></book>')
            Loki().Parse('<book><![CDATA[ This is it.</book>')
            Loki().Parse('<book><![RCDATA[ This is it. ]]></book>')
            Loki().Parse('<book><![INCLUDE[ This is it. ]]></book>')
            Loki().Parse('<book><![IGNORE[ This is it. ]]></book>')
            Loki().Parse('<book><![TEMP[ This is it. ]]></book>')
            Loki().Parse('<book><![XYZZY[ This is it. ]]></book>')
            Loki().Parse('<book><![%foo;[ This is it. ]]></book>')

            # PIs and comments
            Loki().Parse('<book><?tei rend=12?</book>')
            Loki().Parse('<book><!-- hello -></book>')

            # Entity refs
            Loki().Parse('<book><p>&#;.</book>')
            Loki().Parse('<book><p>&#BEEF;.</book>')
            Loki().Parse('<book><p>&#xBEEF></book>')
            Loki().Parse('<book><p>&#x.</book>')

    #@unittest.skip
    def testXVal(self):
        ### Validation (beyond WF!)
        #
        self.XtryOption("""<doc><p id="foo">Ok.</p></doc>""",
            "valElementNames", True)  # Must be declared
        #self.XtryOption("""<doc><p id="foo">Ok.</p></doc>""",
        #    "valModels", True)
        self.XtryOption("""<doc><p id="foo">Ok.</p></doc>""",
            "valAttrNames", True)  # Must be declared
        self.XtryOption("""<doc><p id="foo">Ok.</p></doc>""",
            "valAttrTypes", True)  # Must match datatype

    #@unittest.skip
    def testXEntities(self):
        ### Entities and special characters
        #
        self.tryOption("""<doc><p class="foo">Ok &bull;</p></doc>""",
            "htmlNames", True)
        self.tryOption("""<doc>Ok &LEFT_POINTING_DOUBLE_ANGLE_QUOTATION_MARK;</doc>""",
            "unicodeNames", True)
        self.tryOption("""<doc>Ok &LEFT_POIN_DOUBL_ANGL_QUOT_MARK;</doc>""",
            "unicodeNames", True)
        self.tryOption("""<!DOCTYPE X SYSTEM "foo.xml" "foo.htm">"""
            "multiPath", True)  # Multiple SYSTEM IDs
        self.XtryOption("""<!DOCTYPE X [
            <!SDATA nbsp 160 bull 0u2022> ]>""",
            "multiSDATA", True)
        self.passOption("""<doc><p class="foo">Ok \u2022 \U00002022\t\\</p></doc>""",
            "backslash", True)

    def testXOther(self):
        ### Other
        #
        print("******* In testXOther")
        self.XtryOption("""<doc><p id="foo">Ok.</p></doc>""",
            "expatBreaks", True)  # Break at \n and entities like expat
        self.tryOption("""<doc><p id="foo">Ok.<!—emcomm—></p></doc>""",
            "emComments", True)

    @unittest.skip
    def testXOther2(self):
        self.tryOption("""<doc><p id="foo">Ok.<?foo left="12" bar="abc"</p></doc>""",
            "piAttr", True)
        self.passOption("""<!DOCTYPE doc [
            <!ATTLIST ?troff width NUTOKEN #IMPLIED>
            ]><doc><p id="foo"><?troff width="12"?>Ok.</p></doc>""",
            "piAttrDcl", True)
        self.XtryOption("""<doc xmlns:a="http://foo.com"><p id="foo">Ok.</p></doc>""",
            "nsUsage", "global")      # one/global/noredef/regular
        self.tryOption("""<doc><p id="foo"><![IGNORE[Ok.]]></p></doc>""",
           "MSTypes", True)
        self.tryOption("""<doc><p id="foo"><![INCLUDE[Ok.]]></p></doc>""",
           "MSTypes", True)
        self.tryOption("""<doc><p id="foo"><![TEMP RCDATA[Ok.]]></p></doc>""",
           "MSTypes", True)

    def testMisc(self):
        sr = StackReader()

        entDef = EntityDef("ent1", entSpace=EntitySpace.GENERAL, data="ent1 value")
        self.assertEqual(entDef.entName, "ent1")

        pedef = EntityDef("pent1", entSpace=EntitySpace.PARAMETER, data="xxx")
        self.assertEqual(pedef.entName, "pent1")

        #x = sr.expandPEntities("hello %pent1; there %pent1; world.")
        #self.assertEqual(x, "hello xxx there xxx world.")

        self.assertEqual(sr.depth, 0)
        wl = sr.wholeLoc()
        self.assertEqual(wl, "")
        sr.closeAll()

if __name__ == '__main__':
    unittest.main()
