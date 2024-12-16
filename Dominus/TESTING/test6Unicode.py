#!/usr/bin/env python3
#
import unittest
import random
import re
import unicodedata

#from basedomtypes import HReqE, ICharE, NSuppE  # NotFoundError
#from basedomtypes import NodeType
from xmlstrings import XmlStrings as XStr
from xmlstrings import NameTest, WSHandler, CaseHandler, UNormHandler

#import basedom
#from basedom import DOMImplementation, PlainNode, Node
#from basedom import FormatOptions, Document, Element, Attr
#from basedom import CharacterData, Text, NamedNodeMap, NodeList

from makeTestDoc import makeTestDoc2, DAT  #, DBG


class MyTestCase(unittest.TestCase):
    def TR(self, expr):
        return self.assertTrue(expr)

    def FA(self, expr):
        return self.assertFalse(expr)

    def EQ(self, first, second):
        return self.assertEqual(first, second)


class testByMethod(MyTestCase):
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
        # TODO ALSO VIA cleanText
        textPairs = {
            "NFC": (
                "caf\xe9, e\u0301clair, pi\xf1a, a\xf1o, " +
                "na\xefve, r\xe9sum\xe9",
                "caf\xe9, \xe9clair, pi\xf1a, a\xf1o, na\xefve, r\xe9sum\xe9"),
            "NFD": (
                "caf\xe9, \xe9clair, pi\xf1a, a\xf1o, na\xefve, r\xe9sum\xe9",
                "cafe\u0301, e\u0301clair, pin\u0303a, an\u0303o, " +
                "nai\u0308ve, re\u0301sume\u0301"),
            "NFKC": (  # TODO Add halfwidth, mu-A, etc.?
                #lig   lig   dubH  roman log
                "\ufb03\ufb04\u210d\u2171\u33d2",
                "ffifflHiilog"),
            "NFKD": (
                "\u00c5\u01fa\u1e36\u1fcd\u1fc4",
                "A\u030aA\u030a\u0301L\u0323"),
        }

        nonorm = UNormHandler("NONE")
        for k, v in textPairs.items():
            self.EQ("NONE"+nonorm.normalize(v[0]), "NONE"+v[0])
            self.assertNotEqual("NONE"+nonorm.normalize(v[0]), "NONE"+v[1])
            un = UNormHandler(k)
            normed = un.normalize(v[0])
            if normed != v[1]:
                print(f"UNorm '{k}' not as expected:")
                self.showDiff(v[0], normed, v[1])
                self.EQ(un.normalize(v[0]), v[1])

    def testCaseHandler(self):
        SIGMA = 0x003a3  # "GREEK CAPITAL LETTER SIGMA"
        final = 0x003c2  # "GREEK SMALL LETTER FINAL SIGMA"
        sigma = 0x003c3  # "GREEK SMALL LETTER SIGMA"
        lunat = 0x003f2  # "GREEK LUNATE SIGMA SYMBOL"
        LUNAT = 0x003f9  # "GREEK CAPITAL LUNATE SIGMA SYMBOL"
        sigmai = f"UC {SIGMA} fin {final} lc {sigma} lun {lunat} LUN {LUNAT}"

        s = "aBcDeF #$_- " + sigmai
        self.EQ(CaseHandler.NONE.normalize(s), s)
        self.EQ(CaseHandler.LOWER.normalize(s), s.lower())
        self.EQ(CaseHandler.UPPER.normalize(s), s.upper())
        self.EQ(CaseHandler.FOLD.normalize(s), s.casefold())

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
            self.FA(re.search(r"(.).*\1", spaceChars)) # No dups, please.
            #msg=f"{wh} has dup: [ {visChars} ]")
            self.EQ(len(spaceChars), expectedLen)      # Right count?
            #msg=f"{wh}, sp='{visChars}'.")
            for c in spaceChars:                       # All spaces?
                self.TR(unicodedata.category(c)[0] in "CZ")
            self.TR(wsh.isSpace(spaceChars*3))
            self.FA(wsh.isSpace(""))
            self.FA(wsh.isSpace("\x2022"))  # BULLET
            self.FA(wsh.isSpace(None))
            self.FA(wsh.isSpace("\u200B   \t\r\n"))

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
            self.TR(nt.isName(asciiName))
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
            self.TR(nt.isName(randName))
            #msg=f"randName should pass for {wh}: {randName}'.")

    def testXStr(self):
        allNS = XStr.allNameStartChars()
        allNCA = XStr.allNameCharAddls()
        allNC = XStr.allNameChars()
        self.EQ(len(allNS), 54001)
        self.EQ(len(allNCA), 127)
        self.EQ(len(allNC), 54128)

        self.TR(XStr.isXmlName("Rainbow.1"))
        self.TR(XStr.isXmlName("_Rainbow.1"))
        self.TR(XStr.isXmlQName("lb"))
        self.TR(XStr.isXmlQName("tei:lb"))
        self.TR(XStr.isXmlQQName("tei"))
        self.TR(XStr.isXmlQQName("tei:lb"))
        self.TR(XStr.isXmlQQName("tei:lb:c"))
        self.TR(XStr.isXmlPName("svg:g"))
        self.TR(XStr.isXmlNMTOKEN("-foo-"))
        self.TR(XStr.isXmlNumber("0123456789"))

        self.FA(XStr.isXmlName("Rain•bow'1"))
        self.FA(XStr.isXmlName("-Rain"))
        self.FA(XStr.isXmlName(".Rain"))
        self.FA(XStr.isXmlName("1Rain"))
        self.FA(XStr.isXmlName("1Rain"))
        self.FA(XStr.isXmlQName("  zork "))
        self.FA(XStr.isXmlQName("tei:lb:c"))
        self.FA(XStr.isXmlQQName("tei:lb:-c"))
        self.FA(XStr.isXmlPName("g"))
        self.FA(XStr.isXmlPName("1svg:g"))
        self.FA(XStr.isXmlNMTOKEN("-f#o-"))
        self.FA(XStr.isXmlNumber("a999"))
        self.FA(XStr.isXmlNumber("{45}"))

        self.EQ(XStr.escapeAttribute(
            'Alfred <"E"> Neuman.', quoteChar='"', addQuotes=False),
            'Alfred &lt;&quot;E&quot;> Neuman.')

        self.EQ(XStr.escapeText(
            'abc<tag> AT&T xyz'),
            'abc&lt;tag> AT&amp;T xyz')
        self.EQ(XStr.escapeText(
            'abc \u2022y AT&T zz', escapeAllPast=0x2000),
            'abc &#x2022;y AT&amp;T zz')
        self.EQ(XStr.escapeText(
            'abc ]]> zz'),
            'abc ]]&gt; zz')
        self.EQ(XStr.escapeText(
            'abc >>> zz'),
            'abc >>> zz')
        self.EQ(XStr.escapeText(
            'abc >>> zz', escapeAllGT=True),
            'abc &gt;&gt;&gt; zz')

        self.EQ(XStr.escapeCDATA(
            "1234<[!CDATA[m<n> AT&T]]>, right?"),
            "1234<[!CDATA[m<n> AT&T]]&gt;, right?")
        self.EQ(XStr.escapeCDATA(
            "1234<[!CDATA[m<n> AT&T]]>, right?", replaceWith="]]&gt;"),
            "1234<[!CDATA[m<n> AT&T]]&gt;, right?")
        self.EQ(XStr.escapeCDATA(
            "1234<[!CDATA[m<n> AT&T]]>, right?", replaceWith="\u2022"),
            "1234<[!CDATA[m<n> AT&T\u2022, right?")

        self.EQ(XStr.escapeComment(
            "some <p>s fr-om AT&T are -- well?> -- ok."),
            "some <p>s fr-om AT&T are -&#x2d; well?> -&#x2d; ok.")
        self.EQ(XStr.escapeComment(
            "some <p>s fr-om AT&T are -- well?> -- ok.", replaceWith="- -"),
            "some <p>s fr-om AT&T are - - well?> - - ok.")

        self.EQ(XStr.escapePI(
            "Pis should?> not have this?>", replaceWith="?&gt;"),
            "Pis should?&gt; not have this?&gt;")
        self.EQ(XStr.escapePI(
            "Pis should?> not have this?>", replaceWith=""),
            "Pis should not have this")

        self.EQ(XStr.escapeASCII(
            "abc\u2022xyz.\u278e.", width=6, base=16, htmlNames=True),
            "abc&bull;xyz.&#x00278e;.")
        self.EQ(XStr.escapeASCII(
            "abc\u2022xyz.\u278e.", width=2, base=10, htmlNames=False),
            "abc&#8226;xyz.&#10126;.")
        self.EQ(XStr.escapeASCII(
            "abc\u2022xyz.\u278e.", width=2, base=10, htmlNames=False),
            "abc&#8226;xyz.&#10126;.")

        self.EQ(XStr.dropNonXmlChars("abc\x05d\x1Ee\x02f"), "abcdef")
        self.EQ(XStr.unescapeXml("a&#65;-&bull;-&lt;.&#x2022;"), "aA-•-<.•")
        #self.TR(XStr.unescapeXmlFunction(mat))

        self.assertTrue(c in XStr.xmlSpaces_list for c in " \t\r\n")
        self.EQ(XStr.normalizeSpace("  a   b\t\n c\rd  ", allUnicode=False), "a b c d")
        self.EQ(XStr.stripSpace("\r\n\t  a b  \t\n \r  ", allUnicode=False), "a b")
        self.EQ(XStr.stripSpace("  a\n \rb  ", allUnicode=False), "a\n \rb")

        self.EQ(XStr.makeStartTag(
            "spline", attrs="", empty=False, sort=False), "<spline>")
        self.EQ(XStr.makeStartTag(
            "spline", attrs={"id":"A1", "class":"foo"}, empty=True, sort=False),
            '<spline id="A1" class="foo"/>')
        self.EQ(XStr.makeStartTag(
            "spline", attrs={"id":"A1", "class":"foo"}, empty=True, sort=True),
            '<spline class="foo" id="A1"/>')
        self.EQ(XStr.dictToAttrs(
            { "id":"foo", "border":"border<1 " }, sort=True, normValues=False),
            ' border="border&lt;1 " id="foo"')
        self.EQ(XStr.makeEndTag("DiV"), "</DiV>")

        self.EQ(XStr.getLocalPart("foo:bar"), "bar")
        self.EQ(XStr.getPrefixPart("foo:bar"), "foo")

        failed = []
        for c in allNS:
            if (not XStr.isXmlName(c+"restOfName")):
                failed.append("U+%04x" % (ord(c)))
        if (failed):
            self.assertFalse(
                print("Chars should be namestart but aren't: [ %s ]" % (" ".join(failed))))

        failed = []
        for c in allNCA:
            if (XStr.isXmlName(c+"restOfName")):
                failed.append("U+%04x" % (ord(c)))
        if (failed):
            self.assertFalse(
                print("Chars should not be namestart but are: [ %s ]" % (" ".join(failed))))

        self.TR(XStr.isXmlName(allNS*2))

        self.TR(XStr.isXmlName("A"+allNC))


if __name__ == '__main__':
    unittest.main()
