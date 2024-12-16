#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# 2024-11: Written by Steven J. DeRose.
#
import unittest
import codecs
import re
from collections import defaultdict
from typing import Mapping

import html
#from xml.dom import minidom
#from xml.parsers import expat

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

def packXml(s:str) -> str:
    """Make 2 xml strigs more comparable (but doesn't deal with attribute
    order).
    TODO: Canonicalize: attr order.
    """
    s = re.sub(r"""<\?xml .*?\?>""", "", s)
    s = re.sub(r">\s*<", ">\n<", s).strip()
    s = html.unescape(s)
    return s

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


###############################################################################
#
class TestDomBuilderM(unittest.TestCase):
    def setUp(self):
        self.maxDiff = 9999
        with codecs.open("sample01.xml", "rb", encoding="utf-8") as ifh:
            self.xmlText = ifh.read()
        impl = basedom.getDOMImplementation()
        self.db = dombuilder.DomBuilder(domImpl=impl)
        self.doc = self.db.parse_string(self.xmlText)
        self.docEl = self.doc.documentElement

    def testDefault(self):
        xmlText2 = self.doc.toxml()
        doc2 = self.db.parse_string(xmlText2)
        xmlText3 = doc2.toxml()
        self.assertEqual(xmlText2, xmlText3)

        somePath = "/tmp/testSerializers.writexml.xml"
        with codecs.open(somePath, "wb", encoding="utf-8") as ofh:
            self.doc.writexml(writer=ofh)

        self.assertIsInstance(self.doc.toxml(), str)
        self.assertIsInstance(self.doc.tostring(), str)
        self.assertIsInstance(self.docEl.collectAllXml(), str)
        self.assertIsInstance(self.docEl.innerXML, str)
        self.assertIsInstance(self.docEl.outerXML, str)

        self.assertIsInstance(self.docEl.toprettyxml(), str)

    def testFO(self):
        """This flips most values to non-defaults.
        """
        fo = basedom.FormatOptions()
        self.assertTrue(isinstance(fo.translateTable, Mapping))

        fo = basedom.FormatOptions(
            # Whitespace insertion
            newl = "\r\n",        # String for line-breaks
            indent = "  ",        # String to repeat for indent
            wrapTextAt = 80,      # Wrap text near this interval NOTYET
            dropWS = True,        # Drop ws-only text nodes
            breakBB = True,       # Newline before start tags
            breakAB = True,       # Newline after start tags
            breakAttrs = True,    # Newline before each attribute
            breakBE = True,       # Newline before end tags
            breakAE = True,       # Newline after end tags

            inlineTags = "i,b,tt,sup,sub,span".split(","),

            # Syntax alternatives
            canonical = False,    # Use canonical XML syntax? NOTYET
            encoding = "utf-8",   # utf-8. Just utf-8.
            includeXmlDcl = False,
            includeDoctype = False,
            useEmpty   = False,   # Use XML empty-element syntax
            emptySpace = False,   # Include a space before the /
            quoteChar = "'",      # Char to quote attributes NOTYET
            sortAttrs = True,     # Alphabetical order for attributes
            normAttrs = True,

            # Escaping
            escapeGT = True,      # Escape > in content NOTYET
            ASCII = True,         # Escape all non-ASCII NOTYET
            charBase = 10,        # Numeric char refs in decimal or hex? NOTYET
            charPad = 1,          # Min width for numeric char refs
            htmlChars = False,    # Use HTML named special characters
            translateTable = { "A": "&#x41;", "e": None}
        )
        self.doc.toprettyxml(foptions=fo)

        with self.assertRaises(KeyError):
            fo = basedom.FormatOptions(notAnOption="foo")
        with self.assertRaises(TypeError):
            fo = basedom.FormatOptions(breakAE="foo")


if __name__ == '__main__':
    unittest.main()
