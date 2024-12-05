#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# testDombuilder:
# 2024-09: Written by Steven J. DeRose.
#
import unittest
import codecs
from collections import defaultdict

from xml.dom import minidom
from xml.parsers import expat

import basedom
import dombuilder

from makeTestDoc import packXml, checkXmlEqual, isEqualNode

# See https://stackoverflow.com/questions/43842675/
#
if 'unittest.util' in __import__('sys').modules:
    # Show full diff in self.assertEqual.
    __import__('sys').modules['unittest.util']._MAX_LENGTH = 32000

# Can't trivially test CDATA since it isn't preserved.
#
sampleDoc = """<?xml version="1.0" encoding="utf-8"?><html>
    <body>
        <div class="container">
            <p id="first-paragraph">Hello</p>
            <p class="text">World <span class="highlight">!</span></p>
            <div class="blue">And some more AT&amp;T text.</div>
        </div>
        <!-- there be comment here -->
        <?tgt pidata="foo"?>
    </body>
</html>"""

expectedCts = {
    "div": 2,
    "p": 2,
    "html": 1,
    "body": 1,
    "span": 1,
    "#text": 4,  # 4 except for normalization at the character reference.
    "#comment": 1,
    "@class": 4,
    "@id" : 1,
    "?tgt": 1,  # PIs
}


def countStuff(doc) -> dict:
    counts = defaultdict(int)
    for n in doc.eachNode(includeAttributes=True):
        if n.isAttribute:
            counts["@"+n.nodeName] += 1
        elif n.isPI:
            counts["?"+n.target] += 1
        else:
            counts[n.nodeName] += 1
    return counts


###############################################################################
# Test the implementation
#
class TestDomBuilderM(unittest.TestCase):
    def setUp(self):
        self.maxDiff = 9999
        self.db = None
        self.doc = None
        with codecs.open("sample01.xml", "rb", encoding="utf-8") as ifh:
            self.xmlText = ifh.read()

        #print("\n\nDocument as read:\n" + self.xmlText)
        #self.xmlPacked = packXml(self.xmlText)
        #print("\n\nDocument packed: \n" + self.xmlPacked)

        print("\n")

    def testDefault(self):
        db1 = dombuilder.DomBuilder()
        try:
            doc1 = db1.parse_string(self.xmlText)
        except expat.ExpatError as e:
            print(f"\n======= Initial parse failed\n{self.xmlText}\n=======\n{e}\n")
            raise expat.ExpatError from e

        print("\n")
        xmlText2 = doc1.toprettyxml(indent="  ")
        db2 = dombuilder.DomBuilder()
        try:
            doc2 = db2.parse_string(xmlText2)
        except expat.ExpatError as e:
            print(f"\n=======Re-parse of output failed\n{xmlText2}\n=======\n{e}\n")
            raise expat.ExpatError from e

        isEqualNode(doc1.documentElement, doc2.documentElement)

    @unittest.skip
    def testEmptyRoot(self):
        xml = """<emptyDoc class="spam baked_beans"/>"""
        self.db = dombuilder.DomBuilder()
        self.doc = self.db.parse_string(xml)
        xml2 = self.doc.documentElement.outerXML
        checkXmlEqual(xml, xml2)

    @unittest.skip
    def testRootSiblings(self):
        xml = """<!-- My document -->
<?zoot sister="dingo"?>
<article><p>Naughty, bad, evil Zoot!</p>
</article>
<!-- Not to mention &dingo;. -->
"""
        self.db = dombuilder.DomBuilder()
        with self.assertRaises(SyntaxError):
            self.doc = self.db.parse_string(xml)

    @unittest.skip
    def testExplicitChoice(self):
        self.db = dombuilder.DomBuilder(
            parserCreator=expat.ParserCreate,
            domImpl=minidom.getDOMImplementation())
        self.doc = self.db.parse_string(self.xmlText)
        xmlText2 = self.doc.toxml()
        self.assertEqual(packXml(self.xmlText), packXml(xmlText2))


###############################################################################
#
class TestDomBuilderB(unittest.TestCase):
    def setUp(self):
        self.maxDiff = 9999
        self.db = None
        self.doc = None
        with codecs.open("sample01.xml", "rb", encoding="utf-8") as ifh:
            self.xmlText = ifh.read()

        #print("\n\nDocument as read:\n" + self.xmlText)
        #self.xmlPacked = packXml(self.xmlText)
        #print("\n\nDocument packed: \n" + self.xmlPacked)

        print("\n")

    def testDefault(self):
        db1 = dombuilder.DomBuilder(
            parserCreator=expat.ParserCreate,
            domImpl=basedom.getDOMImplementation(),
)
        try:
            doc1 = db1.parse_string(self.xmlText)
        except expat.ExpatError as e:
            print(f"\n======= Initial parse failed\n{self.xmlText}\n=======\n{e}\n")
            raise expat.ExpatError from e

        print("\n")
        xmlText2 = doc1.toprettyxml(indent="  ")
        db2 = dombuilder.DomBuilder()
        try:
            doc2 = db2.parse_string(xmlText2)
        except expat.ExpatError as e:
            print(f"\n=======Re-parse of output failed\n{xmlText2}\n=======\n{e}\n")
            raise expat.ExpatError from e

        isEqualNode(doc1.documentElement, doc2.documentElement)

    @unittest.skip
    def test_selectorsB(self):
        self.assertIsInstance(self.doc, basedom.Document)
        #import pudb; pudb.set_trace()
        self.assertEqual(self.doc.documentElement, self.doc.childNodes[0])
        docEl = self.doc.documentElement
        self.assertIsInstance(docEl, basedom.Element)
        xml2 = docEl.toxml()
        self.assertEqual(packXml(sampleDoc), packXml(xml2))

        cts = countStuff(self.doc)
        if (cts != expectedCts):
            for k, v in expectedCts.items():
                print("%-12s  expected %3d, found %3d %s"
                    % (k, v, cts[k], "***" if v != cts[k] else ""))
            for k, v in cts.items():
                if k in expectedCts: continue
                print("%-12s  expected %3d, found %3d %s"
                    % (k, 0, v, "***"))
            self.maxDiff = None
            self.assertEqual(dict(cts), dict(expectedCts))

if __name__ == '__main__':
    unittest.main()
