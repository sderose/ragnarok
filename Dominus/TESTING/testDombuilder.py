#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# testddombuilder:
# 2024-09: Written by Steven J. DeRose.
#
import unittest
import re
from collections import defaultdict

from xml.dom import minidom

import basedom
import dombuilder

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

def packXml(s:str) -> str:
    s = re.sub(r"""<\?xml .*?\?>""", "", s)
    s = re.sub(r">\s*<", ">\n<", s).strip()
    return s

def countStuff(doc) -> dict:
    counts = defaultdict(int)
    for n in doc.eachNode(attrs=True):
        if n.isAttribute:
            counts["@"+n.nodeName] += 1
        elif n.isPI:
            counts["?"+n.target] += 1
        else:
            counts[n.nodeName] += 1
    return counts


###############################################################################
# Test the implementation
 # TODO: Normalize space, attr order.
#
class TestDomBuilderM(unittest.TestCase):
    def setUp(self):
        self.db = dombuilder.DomBuilder(theDocumentClass=minidom.Document)
        self.doc = self.db.parse_string(sampleDoc)
        self.maxDiff = 9999

    def test_selectorsM(self):
        self.assertIsInstance(self.doc, minidom.Document)
        docEl = self.doc.documentElement
        self.assertIsInstance(docEl, minidom.Element)
        xml2 = docEl.toxml()
        self.assertEqual(packXml(sampleDoc), packXml(xml2))

class TestDomBuilderB(unittest.TestCase):
    def setUp(self):
        self.db = dombuilder.DomBuilder(theDocumentClass=basedom.Document)
        self.doc = self.db.parse_string(sampleDoc)
        self.maxDiff = None

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
