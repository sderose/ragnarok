#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# testddombuilder:
# 2024-09: Written by Steven J. DeRose.
#
import unittest
import re
from xml.dom import minidom
import basedom

import dombuilder


# Can't trivially test CDATA since it isn't preserved.
#
sampleDoc = """<?xml version="1.0" encoding="utf-8"?>
<html>
    <body>
        <div class="container">
            <p id="first-paragraph">Hello</p>
            <p class="text">World <span class="highlight">!</span></p>
            <div class="blue">And some more AT&amp;T text.</div>
        </div>
        <!-- there be comment here -->
        <?tgt pidata="foo"?>
    </body>
</html>
"""

def packXml(s:str) -> str:
    s = re.sub(r"""<\?xml .*?\?>""", "", s)
    s = re.sub(r">\s*<", ">\n<", s).strip()
    return s


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
        self.maxDiff = 9999

    def test_selectorsB(self):
        self.assertIsInstance(self.doc, basedom.Document)
        #import pudb; pudb.set_trace()
        self.assertEqual(self.doc.documentElement, self.doc.childNodes[0])
        docEl = self.doc.documentElement
        self.assertIsInstance(docEl, basedom.Element)
        xml2 = docEl.toxml()
        self.assertEqual(packXml(sampleDoc), packXml(xml2))


if __name__ == '__main__':
    unittest.main()
