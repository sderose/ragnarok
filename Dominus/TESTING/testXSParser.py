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
import xsparser
from xsparser import StackReader, EntityFrame, XSParser
from xmlstrings import CaseHandler
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

depth = 0
eventCounts = defaultdict(int)


###############################################################################
#pylint: disable=W0613
#
def pr(s:str, *args):
    if args: s += " ".join(args)
    print("  " * depth, "Event: ", s)

def common(typ:SaxEvent, name:str="") -> None:
    eventCounts[typ] += 1
    pr("%s:  %s", typ.name, name)

def StartElement(name:str, attrs:Dict=None) -> None:
    global depth
    common(SaxEvent.START)
    depth += 1
def EndElement(name:str) -> None:
    global depth
    common(SaxEvent.END)
    depth -= 1
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
    global depth
    assert isinstance(expat, ModuleType)
    parser = pc.ParserCreate()
    setHandlers(parser)
    depth = 0
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
        eframe = EntityFrame(eDef=ch1)
        thePath = eframe.findLocalPath(eDef=ch1)
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

        self.assertFalse(ef.readConst(
            "PUBLIC", thenSp=True, folder=CaseHandler.UPPER))
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
            options={ "emptyEnd": False, "elementFold": False, "xsdType": False })
        print(repr(sr))
        sr.isOpen(space=EntitySpace.GENERAL, name="chap1")

    def xxxtest_doc(self):
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


###############################################################################
#
class TestXSPExtensions(unittest.TestCase):
    def setup(self):
        print("In TestXSP")

    def tryOption(self, xml:str, optName:str, optValue:Any=True) -> None:
        """Parse and find syntax error; then set option and it should pass.
        """
        with self.assertRaises(SyntaxError):
            import pudb; pudb.set_trace()
            xsp = XSParser()
            xsp.Parse(xml)

        xsp = XSParser(options={optName:optValue})
        xsp.Parse(xml)

    def passOption(self, xml:str, optName:str, optValue:Any=True) -> None:
        """These don't create a syntax error without the options, but should
        come out different.
        """
        xsp = XSParser(options={optName:optValue})
        xsp.Parse(xml)

    def XtryOption(self, *args):
        return

    @unittest.skip
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

    @unittest.skip
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
        self.XtryOption("""<doc><p id="foo">Ok.</p></doc>""",
            "uNormHandler", CaseHandler.UPPER)  #                       TODO
        self.XtryOption("""<doc><p id="foo">Ok.</p></doc>""",
            "wsDef", None)  # (XML default)                             TODO
        self.XtryOption("""<doc><p id="foo">Ok.</p></doc>""",
            "radix", ".")  # Decimal point choice                       TODO
        self.XtryOption("""<doc><p id="foo">Ok.</p></doc>""",
            "noC1", False)  # No C1 controls                            TODO

    @unittest.skip
    def testXSchema(self):
        ### Schemas
        #
        self.XtryOption("""<doc><p id="foo">Ok.</p></doc>""",
            "schemaType", "DTD")  # <!DOCTYPE foo SYSTEM "" NDATA XSD>
        self.XtryOption("""<doc><p id="foo">Ok.</p></doc>""",
            "fragComments", True)  # In-dcl like SGML
        self.XtryOption("""<!DOCTYPE foo [ <!ENTITY soup (i b tt mono)> ]>""",
            "setDcls", True)  # <!ENTITY % x SET (i b tt)>              TODO

    @unittest.skip
    def testXElements(self):
        ### Elements
        #
        self.XtryOption("""<!DOCTYPE foo [ <!ELEMENT (x|y|z) #PCDATA> ]>""", # TODO
            "groupDcl", True)  #
        self.XtryOption("""<!DOCTYPE foo [ <!ELEMENT p - - ANY> ]>""",  # TODO
            "oflag", True)
        self.XtryOption("""<doc><p id="foo">Ok.</p></doc>""",
            "sgmlWord", True)  # CDATA RCDATA #CURRENT etc.
        self.XtryOption("""<doc><p id="foo">Ok.</p></doc>""",
            "mixel", True)  # Dcl content ANYELEMENT                    TODO
        self.XtryOption("""<doc><p id="foo">Ok.</p></doc>""",
            "mixins", True)  # cf incl exceptions
        self.XtryOption("""<doc><p id="foo">Ok.</p></doc>""",
            "repBrace", True)  # {min max} for repetition
        self.tryOption("""<doc><p id="foo">Ok.</></doc>""",
            "emptyEnd", True)  # </>
        self.tryOption("""<doc><p id="foo">Ok.<|>right<|>ok.</p></doc>""",  # TODO
            "restart", True)
        self.XtryOption("""<doc><p|q id="foo">Ok.</p|q></doc>""",  # TODO
            "simultaneous", True)
        self.XtryOption("""<doc><p id="foo">Ok.</p></doc>""",
            "multiTag", True)  # <div/title>...</title/div>             TODO
        self.tryOption("""<doc><p id="foo">Ok.<-p>not there<+p> but there</p></doc>""",
            "suspend", True)   # TODO
        self.tryOption("""<doc><p id="foo">Ok, <i>dude, </p> there.</i></doc>""",
            "olist", True)

    @unittest.skip
    def testXAttributes(self):
        ### Attributes
        #
        self.tryOption("""<!DOCTYPE X [
            <!ATTLIST * id ID #IMPLIED> ]>""",
            "globalAttr", True)  #
        self.tryOption("""<!DOCTYPE X [
            <!ATTLIST foo #ANY CDATA #IMPLIED> ]>""",
            "anyAttr", True)
        self.XtryOption("""<doc><p id="foo">Ok.</p></doc>""",
            "undeclaredAttrs", True)  #                                 TODO
        self.tryOption("""<!DOCTYPE X [
            <!ATTLIST foo x float #IMPLIED> ]>""",
            "xsdType", True)
        self.XtryOption("""<!DOCTYPE X [
            <!ATTLIST foo x floats #IMPLIED> ]>""",
            "xsdPlural", True)                                        # TODO
        self.XtryOption("""<doc><p id="foo">Ok.</p></doc>""",
            "specialFloat", True)  # Nan Inf etc. (needed?)
        self.XtryOption("""<!DOCTYPE X [
            <!ATTLIST quo cid COID #IMPLIED> ]>""",
            "coID", True)                                             # TODO
        self.XtryOption("""<!DOCTYPE X [
            <!ATTLIST quo id ID #IMPLIED qid QID #IMPLIED> ]>""",
            "nsID", True)                                             # TODO
        self.XtryOption("""<!DOCTYPE X [
            <!ATTLIST quo sid STACKID #IMPLIED> ]>""",
            "stackID", True)                                          # TODO
        self.tryOption("""<doc><p id=foo>Ok.</p></doc>""",
            "unQuotedAttr", True)  # <p x=foo>
        self.tryOption("""<doc><p id=“foo”>Ok.</p></doc>""",
            "curlyQuote",True)
        self.tryOption("""<doc><p +border id="p1" -foo>Ok.</p></doc>""",
            "booleanAttr", True)
        self.tryOption("""<doc><p id!="foo">Ok.</p></doc>""",
            "bangAttr", True)  # != on first use to set dft
        self.tryOption("""<doc><p id!int8="99">Ok.</p></doc>""",
            "bangAttrType", True)  # !typ= to set datatype              TODO

    @unittest.skip
    def testXVal(self):
        ### Validation (beyond WF!)
        #
        self.XtryOption("""<doc><p id="foo">Ok.</p></doc>""",
            "valElementNames", True)  # Must be declared
        self.XtryOption("""<doc><p id="foo">Ok.</p></doc>""",
            "valModels", True)     # Child sequences                    TODO
        self.XtryOption("""<doc><p id="foo">Ok.</p></doc>""",
            "valAttrNames", True)  # Must be declared
        self.XtryOption("""<doc><p id="foo">Ok.</p></doc>""",
            "valAttrTypes", True)  # Must match datatype

    @unittest.skip
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
            "multiSDATA", True) #                                       TODO
        self.passOption("""<doc><p class="foo">Ok \u2022 \U00002022\t\\</p></doc>""",
            "backslash", True)

    def testXOther(self):
        ### Other
        #
        self.XtryOption("""<doc><p id="foo">Ok.</p></doc>""",
            "expatBreaks", True)  # Break at \n and entities like expat
        self.tryOption("""<doc><p id="foo">Ok.<!—emcomm—></p></doc>""",
            "emComments", True)   # emdash as -- for comments           TODO

        return

        self.tryOption("""<doc><p id="foo">Ok.<?foo left="12" bar="abc"</p></doc>""",
            "piAttr", True)       # PI parsed like attributes.          TODO
        self.passOption("""<doc><p id="foo">Ok.</p></doc>""",
            "piAttrDcl", True)    # <!ATTLIST ?target ...>              TODO
        self.XtryOption("""<doc><p id="foo">Ok.</p></doc>""",
            "nsSep", ":")         #                                     TODO
        self.XtryOption("""<doc><p id="foo">Ok.</p></doc>""",
            "nsUsage", True)      # one/global/noredef/regular          TODO
        self.tryOption("""<doc><p id="foo"><![IGNORE[Ok.]]></p></doc>""",
           "MSTypes", True)
        self.tryOption("""<doc><p id="foo"><![INCLUDE[Ok.]]></p></doc>""",
           "MSTypes", True)
        self.tryOption("""<doc><p id="foo"><![TEMP RCDATA[Ok.]]></p></doc>""",
           "MSTypes", True)

if __name__ == '__main__':
    unittest.main()
