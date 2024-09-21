#!/usr/bin/env python3
#
# Unit tests for xmlstrings package.
# 2024-08-14: Written by Steven J. DeRose.
#
#pylint: disable=W0613, W0212, E1101
#
import unittest

from xmlstrings import XmlStrings

x = XmlStrings

class TestXmlStrings(unittest.TestCase):
    def setup(self):
        return

    def test_isa(self):
        self.assertTrue(x.isXmlName("para3"))
        self.assertTrue(x.isXmlName("óhello"))
        self.assertTrue(x.isXmlName("_hello"))
        self.assertFalse(x.isXmlName(":hello"))  # TODO: Choose here
        self.assertFalse(x.isXmlName("-hello"))
        self.assertFalse(x.isXmlName(".hello"))
        self.assertFalse(x.isXmlName("7hello"))
        self.assertFalse(x.isXmlName("#hello"))
        self.assertFalse(x.isXmlName("hello#"))

        self.assertTrue(x.isXmlQName("docbook:para.2"))
        self.assertTrue(x.isXmlQName("spam.1_eggs-2"))
        self.assertFalse(x.isXmlQName("spam.1:2eggs"))
        # TODO: Allow multiple colons?

        self.assertTrue(x.isXmlPName("svg:u_2"))
        self.assertFalse(x.isXmlPName(""))
        self.assertFalse(x.isXmlPName("12"))
        self.assertFalse(x.isXmlPName("abc,foo"))
        self.assertFalse(x.isXmlPName("n**2"))
        self.assertFalse(x.isXmlPName("#text"))
        self.assertFalse(x.isXmlPName(".foo"))

        self.assertTrue(x.isXmlNmtoken("-hellö-"))

        #self.assertTrue(x.isNodeKindChoice(s:str))

        self.assertTrue(x.isXmlNumber("1234567890"))
        self.assertFalse(x.isXmlNumber("12345 67890"))
        self.assertFalse(x.isXmlNumber("-12"))
        self.assertFalse(x.isXmlNumber("3.14159"))
        self.assertFalse(x.isXmlNumber(""))
        self.assertFalse(x.isXmlNumber("footnote_3"))
        self.assertFalse(x.isXmlNumber("123:para"))

    def test_escapers(self):
        self.assertEqual(x.escapeAttribute(
            "this is  fine"),
            "this is  fine")
        self.assertEqual(x.escapeAttribute(
            '"this is "also" \'just\' fine"', quoteChar='"'),
            '&quot;this is &quot;also&quot; \'just\' fine&quot;')
        self.assertEqual(x.escapeAttribute(
            "this is  fine", quoteChar="'"),
            "this is  fine")
        self.assertEqual(x.escapeAttribute(
            '"this is "also" \'just\' fine"', quoteChar="'"),
            '"this is "also" &apos;just&apos; fine"')

        self.assertEqual(x.escapeText(
            "The tags <para> & </para> &c are data, as is ]]>."),
            "The tags &lt;para> &amp; &lt;/para> &amp;c are data, as is ]]&gt;.")
        self.assertEqual(x.escapeText(
            "The tags <para> & </para> &c are data, as is ]]>.", escapeAllGT=True),
            "The tags &lt;para&gt; &amp; &lt;/para&gt; &amp;c are data, as is ]]&gt;.")

        self.assertEqual(x.escapeCDATA(
            "The tags <para> & </para> &c are data, as is ]]>."),
            "The tags <para> & </para> &c are data, as is ]]&gt;.")

        self.assertEqual(x.escapeComment(
            "This is a comment -- or is it?"),
            "This is a comment -&#x2d; or is it?")

        self.assertEqual(x.escapePI(
            "I'm a pi with illegal -- ?> stuff."),
            "I'm a pi with illegal -- ?&gt; stuff.")

        #self.assertEqual(x.escapeASCII(
            #"¡Líons ünd tigers ünd •s, oh ﬂy!", width=4, base=16, htmlNames=True),
            #"¡Líons ünd tigers ünd •s, oh ﬂy!")

    def test_other(self):
        self.assertEqual(
            x.dropNonXmlChars(
                "hello\x03\x06there\x1F"),
                "hellothere")
        self.assertEqual(
            x.unescapeXml(
                "<p>&#000065; day &#x2022; &lt; or so."),
                "<p>A day • < or so.")
        self.assertEqual(
            x.normalizeSpace("  x  \t\r\n  y  \t", allUnicode=False), "x y")
        self.assertEqual(x.stripSpace(
            "  x  \t\r\n  y\u2004  \t", allUnicode=False),
              "x  \t\r\n  y\u2004")
        self.assertEqual(x.stripSpace(
            "  x  \t\r\n  y\u2004  \t", allUnicode=True),
              "x  \t\r\n  y")

    def test_makers(self):
        self.assertEqual(x.makeStartTag(
            "p", 'id="id12" class="indented" style="font-family:Courier New;"'),
            '<p id="id12" class="indented" style="font-family:Courier New;">')
        self.assertEqual(x.makeStartTag(
            "p", 'id="id12" class="indented" style="font-family:Courier New;"', empty=True),
            '<p id="id12" class="indented" style="font-family:Courier New;"/>')
        # TODO: Add a bunch

if __name__ == "__main__":
    print("Running basic unit tests...")
    unittest.main()
