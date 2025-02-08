#!/usr/bin/env python3
#
import unittest
import random
import re
import unicodedata

#from basedomtypes import HReqE, ICharE, NSuppE  # NotFoundError
from xmlstrings import XmlStrings as XStr
from xmlstrings import NameTest, WSHandler, CaseHandler, UNormHandler, Normalizer
from prettyxml import FormatOptions, FormatXml
#import basedom
#from basedom import DOMImplementation, PlainNode, Node
#from basedom import FormatOptions, Document, Element, Attr
#from basedom import CharacterData, Text, NamedNodeMap, NodeList

from makeTestDoc import makeTestDoc2, DAT  #, DBG


class testByMethod(unittest.TestCase):
    def setUp(self):
        """Should make:
        <html xmlns:html="https://example.com/namespaces/foo">
            <child0 an_attr.name="this is an attribute value"
                class="c1 c2" id="docbook_id_17">
                Some text content.</child0>
            <child1>
                <grandchild></grandchild>
            </child1>
            <empty></empty>
        </html>
        """
        madeDocObj = makeTestDoc2(dc=DAT, show=False)
        self.dc = DAT
        self.n = madeDocObj.n

    @staticmethod
    def showDiff(s1, s2, s3):
        print("Orig: %s\nNorm: %s\nExpd: %s" % (s1, s2, s3))
        print("    Orig      Norm        Expected")
        maxlen = max(len(s1), len(s2), len(s3))
        for i in range(maxlen):
            s1c = s1[i] if i < len(s1) else "?"
            s2c = s2[i] if i < len(s2) else "?"
            s3c = s3[i] if i < len(s3) else "?"
            print("    %04x (%s) -> %04x (%s)  exp  %04x (%s)  %s"
                % (ord(s1c), s1c, ord(s2c), s2c, ord(s3c), s3c,
                "***" if s2c != s3c else ""))

    def testUNormHandler(self):
        # TODO Also test via cleanText().
        # See unorm.py for isolated unorm mapping.
        testPairs1 = {
           "NFD": ("caf\u00e9 na\u00efve", "cafe\u0301 nai\u0308ve"),
           "NFC": ("scho\u0308n mu\u0308de", "sch\u00f6n m\u00fcde"),
           "NFKD": ("\u2168 \u2169", "IX X"),
           "NFKC": ("\ufb03 \ufb02", "ffi fl")
        }
        testPairs2 = {
            "NFC": (
                "cafe\u0301, e\u0301clair, pin\u0303a, an\u0303o, " +
                "nai\u0308ve, re\u0301sume\u0301",
                "caf\u00e9, \u00e9clair, pi\u00f1a, a\u00f1o, " +
                "na\u00efve, r\u00e9sum\u00e9"),
            "NFD": (
                "caf\u00e9, \u00e9clair, pi\u00f1a, a\u00f1o, " +
                "na\u00efve, r\u00e9sum\u00e9",
                "cafe\u0301, e\u0301clair, pin\u0303a, an\u0303o, " +
                "nai\u0308ve, re\u0301sume\u0301"),
            "NFKC": (
                "\ufb03\ufb04\u210e\u2171\u33d2",
                "ffifflhiilog"),
            "NFKD": (
                "\ufb03\ufb04" + "\u2460\u2461\u2462",
                "ffiffl" + "123")
        }
        nonorm = UNormHandler("NONE")
        for tp in [ testPairs1, testPairs2 ]:
            for k, v in tp.items():
                self.assertEqual("NONE"+nonorm.normalize(v[0]), "NONE"+v[0])
                self.assertNotEqual("NONE"+nonorm.normalize(v[0]), "NONE"+v[1])
                un = UNormHandler(k)
                normed = un.normalize(v[0])
                if normed != v[1]:
                    print(f"UNorm '{k}' not as expected:")
                    self.showDiff(v[0], normed, v[1])
                    self.assertEqual(un.normalize(v[0]), v[1])

    def testCaseHandler(self):
        SIGMA = 0x003a3  # "GREEK CAPITAL LETTER SIGMA"
        final = 0x003c2  # "GREEK SMALL LETTER FINAL SIGMA"
        sigma = 0x003c3  # "GREEK SMALL LETTER SIGMA"
        lunat = 0x003f2  # "GREEK LUNATE SIGMA SYMBOL"
        LUNAT = 0x003f9  # "GREEK CAPITAL LUNATE SIGMA SYMBOL"
        sigmai = f"UC {SIGMA} fin {final} lc {sigma} lun {lunat} LUN {LUNAT}"

        s = "aBcDeF #$_- " + sigmai
        self.assertEqual(CaseHandler.NONE.normalize(s), s)
        self.assertEqual(CaseHandler.LOWER.normalize(s), s.lower())
        self.assertEqual(CaseHandler.UPPER.normalize(s), s.upper())
        self.assertEqual(CaseHandler.FOLD.normalize(s), s.casefold())


        self.assertEqual(CaseHandler.NONE.strcasecmp("XYZ", "xyz"), -1)
        self.assertEqual(CaseHandler.LOWER.strcasecmp("XYZ", "xyz"), 0)
        self.assertEqual(CaseHandler.UPPER.strcasecmp("XYZ", "xyz"), 0)
        self.assertEqual(CaseHandler.FOLD.strcasecmp("XYZ", "xyz"), 0)

        self.assertEqual(CaseHandler.LOWER.strcasecmp("xyz0", "XYZ1"), -1)
        self.assertEqual(CaseHandler.LOWER.strcasecmp("xyz0", "XYZ0"), 0)
        self.assertEqual(CaseHandler.LOWER.strcasecmp("xyz", "XYY"), 1)

    def testWSDef(self):
        """Check that the whitespace variants are right.
        """
        testOptions = {
            "XML":         4,   # space, tab, lf, cr
            "WHATWG":      5,   # Adds U+0C (form feed)
            "CPP":         6,   # Adds U+0B (vertical tab)
            "UNICODE_ALL": 25,  # Adds U+A0, U+2028, U+2029
            "PY_ISSPACE":  25,
            "JAVASCRIPT":  25,
        }
        for wh, expectedLen in testOptions.items():
            wsh = WSHandler(wh)
            spaceChars = wsh.spaces
            #visChars = ", ".join("U+%04x" % (ord(c)) for c in spaceChars)
            self.assertFalse(re.search(r"(.).*\1", spaceChars)) # No dups, please.
            #msg=f"{wh} has dup: [ {visChars} ]")
            self.assertEqual(len(spaceChars), expectedLen)      # Right count?
            #msg=f"{wh}, sp='{visChars}'.")
            for c in spaceChars:                       # All spaces?
                self.assertTrue(unicodedata.category(c)[0] in "CZ")
            self.assertTrue(wsh.isSpace(spaceChars*3))
            self.assertFalse(wsh.isSpace(""))
            self.assertFalse(wsh.isSpace("\x2022"))  # BULLET
            self.assertFalse(wsh.isSpace(None))
            self.assertFalse(wsh.isSpace("\u200B   \t\r\n"))

            self.assertTrue(wsh.hasSpace("abc\t"))
            self.assertEqual(wsh.lstrip(" \t\n\rabc \t\n\r"), "abc \t\n\r")
            self.assertEqual(wsh.rstrip(" \t\n\rabc \t\n\r"), " \t\n\rabc")
            self.assertEqual(wsh.strip(" \t\n\rabc \t\n\r"), "abc")
            self.assertEqual(wsh.replace(" \t\n\rabc \t\n\r"), "    abc    ")
            self.assertEqual(wsh.normalize(" \t\n\rab\t\r  c \t\n\r"), "ab c")
            self.assertEqual(wsh.collapse( " \t\n\rab\t\r  c \t\n\r"), "ab c")
            #
        self.assertEqual(WSHandler.xstripSpace(" \t\n\rabc \t\n\r"), "abc")

    def testNormalizer(self):
        nzr = Normalizer(unorm="NONE", case="UPPER", wsDef="WHATWG")
        self.assertEqual(nzr.normalize(" \t\n\rab\t\r  c \t\n\r"), "AB C")

    def testNameTest(self):
        from string import ascii_letters, digits
        which = {
            "XML": 1,
            "HTML": 2,
            "WHATWG": 3,
            "ASCII": 4,
            "PYTHON": 5,
        }
        asciiStart = ascii_letters + "_"
        asciiName = asciiStart + digits  # ".-:" for some
        for wh in which:
            nt = NameTest(wh)
            self.assertTrue(nt.isName(asciiName))
            #msg=f"asciiName should pass {wh}: '{asciiName}'.")

        # Sample the Unicode "L" category (could add Mn and a few others)
        randName = "eh_"
        for _i in range(20):
            cp = random.randrange(0, 0xDFFF)
            if unicodedata.category(chr(cp)).startswith("L"):
                randName += chr(cp)

        for wh in [ "XML", "HTML", "WHATWG" ]:
            # PYTHON allows Unicode, but we don't test it.
            nt = NameTest(wh)
            self.assertTrue(nt.isName(randName))
            #msg=f"randName should pass for {wh}: {randName}'.")

    def testXStr(self):
        allNS = XStr.allNameStartChars()
        allNCA = XStr.allNameCharAddls()
        allNC = XStr.allNameChars()
        self.assertEqual(len(allNS), 54001)
        self.assertEqual(len(allNCA), 127)
        self.assertEqual(len(allNC), 54128)

        self.assertTrue(XStr.isXmlChars("aArdVarK7.\x2022"))
        self.assertFalse(XStr.isXmlChars("aArd\x04VarK7"))
        self.assertFalse(XStr.isXmlChars(""))

        self.assertTrue(XStr.isXmlName("Rainbow.1"))
        self.assertTrue(XStr.isXmlName("_Rainbow.1"))
        self.assertTrue(XStr.isXmlQName("lb"))
        self.assertTrue(XStr.isXmlQName("tei:lb"))
        self.assertTrue(XStr.isXmlQQName("tei"))
        self.assertTrue(XStr.isXmlQQName("tei:lb"))
        self.assertTrue(XStr.isXmlQQName("tei:lb:c"))
        self.assertTrue(XStr.isXmlPName("svg:g"))
        self.assertTrue(XStr.isXmlNMTOKEN("-foo-"))
        self.assertTrue(XStr.isXmlNumber("0123456789"))

        self.assertFalse(XStr.isXmlName("Rain•bow'1"))
        self.assertFalse(XStr.isXmlName("-Rain"))
        self.assertFalse(XStr.isXmlName(".Rain"))
        self.assertFalse(XStr.isXmlName("1Rain"))
        self.assertFalse(XStr.isXmlName("1Rain"))
        self.assertFalse(XStr.isXmlQName("  zork "))
        self.assertFalse(XStr.isXmlQName("tei:lb:c"))
        self.assertFalse(XStr.isXmlQQName("tei:lb:-c"))
        self.assertFalse(XStr.isXmlPName("g"))
        self.assertFalse(XStr.isXmlPName("1svg:g"))
        self.assertFalse(XStr.isXmlNMTOKEN("-f#o-"))
        self.assertFalse(XStr.isXmlNumber("a999"))
        self.assertFalse(XStr.isXmlNumber("{45}"))

    def testXStrOther(self):
        allNS = XStr.allNameStartChars()
        allNCA = XStr.allNameCharAddls()
        allNC = XStr.allNameChars()
        self.assertEqual(XStr.dropNonXmlChars("abc\x05d\x1Ee\x02f"), "abcdef")
        self.assertEqual(XStr.unescapeXml("a&#65;-&bull;-&lt;.&#x2022;"), "aA-•-<.•")
        with self.assertRaises(ValueError):
            XStr.unescapeXml("a&zerg;-&lt;.")

        self.assertTrue(c in XStr.xmlSpaces_list for c in " \t\r\n")
        self.assertTrue(c not in XStr.xmlSpaces_list for c in "z4-.\xA0\u2003")

        self.assertEqual(XStr.normalizeSpace(
            "  a   b\t\n c\rd  ", allUnicode=False), "a b c d")
        self.assertEqual(XStr.normalizeSpace(
            "  \u2007a   b\t\u2002\n\u2003\u2004\u2005 c\rd  \u2006\u2008\u2009\u200A",
            allUnicode=True), "a b c d")

        self.assertEqual(XStr.replaceSpace(
            "  a   b\t\n c\rd  ", allUnicode=False),
            "  a   b   c d  ")
        self.assertEqual(XStr.replaceSpace(
            "  \u2007ab\t\u2002\n\u2003\u2004\u2005 c\rd\u2006\u2008\u2009\u200A\u200b",
            allUnicode=True),
            "   ab       c d    \u200b")

        self.assertEqual(XStr.stripSpace("\r\n\t  a b  \t\n \r  ", allUnicode=False), "a b")
        self.assertEqual(XStr.stripSpace("  a\n \rb  ", allUnicode=False), "a\n \rb")
        self.assertEqual(XStr.stripSpace(
            "  \u2007a   b\t\u2002\n\u2003\u2004\u2005 c\rd  \u2006\u2008\u2009\u200A",
            allUnicode=True),
            "a   b\t\u2002\n\u2003\u2004\u2005 c\rd")

        # TODO Make these handle attribute re-ordering.
        self.assertEqual(FormatXml.makeStartTag(
            "spline", attrs="", empty=False, sort=False), "<spline>")
        self.assertEqual(FormatXml.makeStartTag(
            "spline", attrs={"id":"A1", "class":"foo"}, empty=True, sort=False),
            '<spline id="A1" class="foo"/>')
        self.assertEqual(FormatXml.makeStartTag(
            "spline", attrs={"id":"A1", "class":"foo&bar"}, empty=True, sort=True),
            '<spline class="foo&amp;bar" id="A1"/>')
        self.assertEqual(FormatXml.makeStartTag(
            "spline", attrs='id="A1" class="foo and bar"', empty=True, sort=True),
            '<spline id="A1" class="foo and bar"/>')
        self.assertEqual(FormatXml.dictToAttrs(
            { "id":"foo", "border":"border<1 " }, sort=True, normValues=False),
            ' border="border&lt;1 " id="foo"')
        self.assertEqual(FormatXml.makeEndTag("DiV"), "</DiV>")

        self.assertEqual(XStr.getLocalPart("foo:bar"), "bar")
        self.assertEqual(XStr.getPrefixPart("foo:bar"), "foo")

        failed = []
        for c in allNS:
            if (not XStr.isXmlName(c+"restOfName")):
                failed.append("U+%04x" % (ord(c)))
        if (failed):
            self.assertFalse(
                print("Chars should be namestart but aren't: [ %s ]"
                    % (" ".join(failed))))

        failed = []
        for c in allNCA:
            if (XStr.isXmlName(c+"restOfName")):
                failed.append("U+%04x" % (ord(c)))
        if (failed):
            self.assertFalse(
                print("Chars should not be namestart but are: [ %s ]"
                    % (" ".join(failed))))

        self.assertTrue(XStr.isXmlName(allNS*2))

        self.assertTrue(XStr.isXmlName("A"+allNC))

    def testEscapers(self):
        self.assertEqual(FormatXml.escapeAttribute(
            'Alfred <"E"> Neuman.', addQuotes=False),
            'Alfred &lt;&quot;E&quot;> Neuman.')

        self.assertEqual(FormatXml.escapeText(
            'abc<tag> AT&T xyz'),
            'abc&lt;tag> AT&amp;T xyz')
        self.assertEqual(FormatXml.escapeText(
            'abc \u2022y AT&T zz', fo=FormatOptions(ASCII=True, htmlChars=True)),
            'abc &bull;y AT&amp;T zz')
        self.assertEqual(FormatXml.escapeText(
            'abc ]]> zz'),
            'abc ]]&gt; zz')
        self.assertEqual(FormatXml.escapeText(
            'abc >>> zz'),
            'abc >>> zz')
        self.assertEqual(FormatXml.escapeText(
            'abc >>> zz', fo=FormatOptions(escapeGT=True)),
            'abc &gt;&gt;&gt; zz')

        self.assertEqual(FormatXml.escapeCDATA(
            "1234<[!CDATA[m<n> AT&T]]>, right?"),
            "1234<[!CDATA[m<n> AT&T]]&gt;, right?")
        self.assertEqual(FormatXml.escapeCDATA(
            "1234<[!CDATA[m<n> AT&T]]>, right?", fo=FormatOptions(forMSC="]]&gt;")),
            "1234<[!CDATA[m<n> AT&T]]&gt;, right?")
        self.assertEqual(FormatXml.escapeCDATA(
            "1234<[!CDATA[m<n> AT&T]]>, right?", fo=FormatOptions(forMSC="\u2022")),
            "1234<[!CDATA[m<n> AT&T\u2022, right?")

        self.assertEqual(FormatXml.escapeComment(
            "some <p>s fr-om AT&T are -- well?> -- ok."),
            "some <p>s fr-om AT&T are -&#x2d; well?> -&#x2d; ok.")
        self.assertEqual(FormatXml.escapeComment(
            "some <p>s fr-om AT&T are -- well?> -- ok.", fo=FormatOptions(forCOM="- -")),
            "some <p>s fr-om AT&T are - - well?> - - ok.")

        self.assertEqual(FormatXml.escapePI(
            "Pis should?> not have this?>", fo=FormatOptions(forPI="?&gt;")),
            "Pis should?&gt; not have this?&gt;")
        self.assertEqual(FormatXml.escapePI(
            "Pis should?> not have this?>", fo=FormatOptions(forPI="")),
            "Pis should not have this")

        self.assertEqual(FormatXml.escapeASCII(
            "abc\u2022xyz.\u278e.",
            fo=FormatOptions(charPad=6, charBase=16, htmlChars=True)),
            "abc&bull;xyz.&#X00278E;.")
        self.assertEqual(FormatXml.escapeASCII(
            "abc\u2022xyz.\u278e.",
            fo=FormatOptions(charPad=6, charBase=16, htmlChars=False)),
            "abc&#X002022;xyz.&#X00278E;.")
        self.assertEqual(FormatXml.escapeASCII(
            "abc\u2022xyz.\u278e.",
            fo=FormatOptions(charBase=16, htmlChars=False, hexUpperCase=False)),
            "abc&#x2022;xyz.&#x278e;.")
        self.assertEqual(FormatXml.escapeASCII(
            "abc\u2022xyz.\u278e.",
            fo=FormatOptions(charPad=6, charBase=10, htmlChars=False)),
            "abc&#008226;xyz.&#010126;.")


if __name__ == '__main__':
    unittest.main()
