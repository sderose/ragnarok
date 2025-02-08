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

from makeTestDoc import isEqualNode  # packXml

# See https://stackoverflow.com/questions/43842675/
#
if 'unittest.util' in __import__('sys').modules:
    # Show full diff in self.assertEqual.
    #pylint: disable=W0212
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
    for n in doc.eachNode(separateAttributes=True):
        if n.isAttribute:
            counts["@"+n.nodeName] += 1
        elif n.isPI:
            counts["?"+n.target] += 1
        else:
            counts[n.nodeName] += 1
    return counts

def roundTrip(s1:str, domImpl) -> bool:
    # Set up 2 copies of our DomBuilder, over the chosen DOM Impl.
    db1 = dombuilder.DomBuilder(
        parserClass=expat, domImpl=domImpl)
    db2 = dombuilder.DomBuilder(
        parserClass=expat, domImpl=domImpl)

    doc1 = db1.parse_string(s1)
    s2 = doc1.toprettyxml(indent="  ")
    db2 = dombuilder.DomBuilder(parserClass=expat, domImpl=domImpl)
    doc2 = db2.parse_string(s2)

    # dombuilder can use minidom.Node, which lacks isEqualNode. So use ours.
    if isEqualNode(doc1.documentElement, doc2.documentElement):
        return True

    print("\n\nDocument as read:\n" + s1)
    print("\n\nDocument as regenerated:\n" + s2)
    return False


###############################################################################
# Test the implementation
#
class TestDomBuilderM(unittest.TestCase):  # using minidom
    def setUp(self):
        self.maxDiff = 9999
        with codecs.open("../DATA/sampleHTML.xml", "rb", encoding="utf-8") as ifh:
            self.xmlText = ifh.read()

    def testTiny(self):
        x = """<?xml version="1.1" encoding="utf-8"?><doc>Hello</doc>"""
        di = minidom.getDOMImplementation()
        self.assertTrue(roundTrip(x, domImpl=di))

    def testEmptyRoot(self):
        x = """<emptyDoc class="spam baked_beans"/>"""
        di = minidom.getDOMImplementation()
        self.assertTrue(roundTrip(x, domImpl=di))

    def testRootSiblings(self):
        x = """<!-- My document -->
<?zoot sister="dingo"?>
<article><p>Naughty, bad, evil Zoot!</p>
</article>
<!-- Not to mention &dingo;. -->
"""
        with self.assertRaises(SyntaxError):
            di = minidom.getDOMImplementation()
            roundTrip(x, domImpl=di)


###############################################################################
#
class TestDomBuilderB(unittest.TestCase):
    def setUp(self):
        self.testPath = "../DATA/sampleHTML.xml"
        with codecs.open(self.testPath, "rb", encoding="utf-8") as ifh:
            self.xmlText = ifh.read()

    def testTiny(self):
        x = """<?xml version="1.1" encoding="utf-8"?><doc>Hello</doc>"""
        di = basedom.getDOMImplementation()
        self.assertTrue(roundTrip(x, domImpl=di))

    def testEmptyRoot(self):
        x = """<emptyDoc class="spam baked_beans"/>"""
        di = basedom.getDOMImplementation()
        self.assertTrue(roundTrip(x, domImpl=di))

    def testRootSiblings(self):
        x = """<!-- My document -->
<?zoot sister="dingo"?>
<article><p>Naughty, bad, evil Zoot!</p>
</article>
<!-- Not to mention &dingo;. -->
"""
        with self.assertRaises(SyntaxError):
            di = basedom.getDOMImplementation()
            roundTrip(x, domImpl=di)

class TestSelectors(unittest.TestCase):
    def setUp(self):
        self.testPath = "../DATA/sampleHTML.xml"
        with codecs.open(self.testPath, "rb", encoding="utf-8") as ifh:
            self.xmlText = ifh.read()

    @unittest.skip
    def test_selectorsB(self):
        di = basedom.getDOMImplementation()
        db1 = dombuilder.DomBuilder(
            parserClass=expat, domImpl=di)
        doc1 = db1.parse(self.testPath)
        self.assertIsInstance(doc1, basedom.Document)
        #import pudb; pudb.set_trace()

        self.assertEqual(doc1.documentElement, doc1.childNodes[0])
        docEl1 = doc1.documentElement
        self.assertIsInstance(docEl1, basedom.Element)

        cts = countStuff(doc1)
        if (cts != expectedCts):
            #for k, v in expectedCts.items():
                #print("%-12s  expected %3d, found %3d %s"
                #    % (k, v, cts[k], "***" if v != cts[k] else ""))
            #for k, v in cts.items():
                #if k in expectedCts: continue
                #print("%-12s  expected %3d, found %3d %s"
                #    % (k, 0, v, "***"))
            self.maxDiff = None
            self.assertEqual(dict(cts), dict(expectedCts))

if __name__ == '__main__':
    unittest.main()
