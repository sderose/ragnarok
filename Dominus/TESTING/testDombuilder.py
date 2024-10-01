#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# testddombuilder:
# 2024-09: Written by Steven J. DeRose.
#
import unittest
import dombuilder

sampleDoc = """
<html>
    <body>
        <div class="container">
            <p id="first-paragraph">Hello</p>
            <p class="text">World <span class="highlight">!</span></p>
            <div class="blue">Blue div</div>
        </div>
    </body>
</html>
"""


###############################################################################
# Test the implementation
#
class TestDomBuilder(unittest.TestCase):
    def setUp(self):
        self.db = dombuilder.DomBuilder()
        self.aDom = self.db.parse_string(sampleDoc)

    def test_selectors(self):
        xml2 = self.aDom.documentElement.outerXML
        # TODO: Normalize space, attr order.
        self.assertEqual(xml2, sampleDoc)
