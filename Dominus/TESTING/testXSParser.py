#!/usr/bin/env python3
#
import os
import unittest
import logging
#from typing import Callable

#from basedomtypes import NodeType
import xsparser
from xsparser import StackReader, EntSpace, ParseType

#from xml.dom.minidom import getDOMImplementation, DOMImplementation,Element
#from basedom import Node

from makeTestDoc import makeTestDoc0, DAT_DocBook  #, DBG

lg = logging.getLogger("testNode3")
logging.basicConfig(level=logging.INFO)

nsURI = "https://example.com/namespaces/foo"

class TestXSP(unittest.TestCase):
    alreadyShowedSetup = False

    def setUp(self):
        self.makeDocObj = makeTestDoc0(dc=DAT_DocBook)
        self.n = self.makeDocObj.n

    def test_Basics(self):
        ch1 = xsparser.EntityDef(EntSpace.GENERAL, "samp", ParseType.PARSED,
            systemId="sample00.xml")
        thePath = ch1.findLocalPath(trace=True)
        self.assertTrue(os.path.isfile(thePath))

        #data="<chap><ti>Hello</ti></chap>"

        _ch2 = xsparser.EntityDef(EntSpace.GENERAL, "chap1", ParseType.PARSED,
            systemId="/Users/xyz/Documents/chap1.xml")
        _soup = xsparser.EntityDef(EntSpace.PARAMETER, "soup",
            data="i | b | tt | mono")

        ef = xsparser.EntityFrame(ch1)
        while (c := ef.consume):
            assert len(c) == 1
            ef.skipSpaces()

        self.assertFalse(ef.readSepComment())
        self.assertFalse(ef.readConst("PUBLIC", thenSp=True, fold=True))
        self.assertFalse(ef.readBaseInt())
        self.assertFalse(ef.readInt())
        self.assertFalse(ef.readFloat())
        self.assertFalse(ef.readName())
        self.assertFalse(ef.readEnumName(names=[ "PUBLIC", "SYSTEM" ]))
        self.assertFalse(ef.readRegex(r'"\w+"'))
        self.assertFalse(ef.readToString(ender=">"))
        self.assertFalse(ef.readToAnyOf(enders=[ "\n", "$" ]))

    def test_basicDTD(self):
        sr = StackReader(rootPath="./sample.dtd",
            options={ "emptyEnd": True, "elementFold": True, "xsdType": True })
        print(repr(sr))
        sr.isOpen(space=EntSpace.GENERAL, name="chap1")

    def test_doc(self):
        StackReader(rootPath="./sample.dtd",
            options={ "emptyEnd": True, "elementFold": True, "xsdType": True })

class TestWholeDocument(unittest.TestCase):
    def setup(self):
        pass

    def testdoc(self):
        tdoc = """<html>
<head><title>Eine Kleine NachtSchrift</title>
</head>
<body>
<h1>Here <i>it</i> is.</h1>
<p>For what it's worth &amp; costs.</p>
<p id="zork" class="big blue" />
<!-- comments, too? -->
<?and a PI?>
<p>-30</p>
</body>
</html>
"""
        StackReader(tdoc)
        #sp.parseDocument(tdoc)

if __name__ == '__main__':
    unittest.main()
