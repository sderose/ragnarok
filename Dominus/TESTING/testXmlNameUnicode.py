#!/usr/bin/env python3
#
import sys
import unittest
import unicodedata

#from basedom import
from xmlstrings import XmlStrings

falsePosNameStart = []
falseNegNameStart = []
falsePosName = []
falseNegName = []

descr = """
The rules are in Section 2.3 of https://www.w3.org/TR/xml/#NT-NameStartChar.

[4]  NameStartChar ::= ":" | [A-Z] | "_" | [a-z] | [#xC0-#xD6] |
    [#xD8-#xF6] | [#xF8-#x2FF] | [#x370-#x37D] | [#x37F-#x1FFF] |
    [#x200C-#x200D] | [#x2070-#x218F] | [#x2C00-#x2FEF] | [#x3001-#xD7FF] |
    [#xF900-#xFDCF] | [#xFDF0-#xFFFD] | [#x10000-#xEFFFF]
[4a] NameChar ::= NameStartChar | "-" | "." | [0-9] | #xB7 |
    [#x0300-#x036F] | [#x203F-#x2040]
[5] Name     ::= NameStartChar (NameChar)*
[6] Names    ::= Name (#x20 Name)*
[7] Nmtoken  ::= (NameChar)+
[8] Nmtokens ::= Nmtoken (#x20 Nmtoken)*

"""

###############################################################################
#
class fromXmlRec:
    """Identify name and name start characters from the ranges given in
    the grammer in the XML REC, section 2.3.
    """
    nameStartRanges = [
        ( ord(':'), ord(':') ),
        ( ord('A'), ord('Z') ),
        ( ord("_"), ord("_") ),
        ( ord('a'), ord('z') ),
        ( 0x000C0, 0x000D6 ),
        ( 0x000D8, 0x000F6 ),
        ( 0x000F8, 0x002FF ),
        ( 0x00370, 0x0037D ),
        ( 0x0037F, 0x01FFF ),
        ( 0x0200C, 0x0200D ),
        ( 0x02070, 0x0218F ),
        ( 0x02C00, 0x02FEF ),
        ( 0x03001, 0x0D7FF ),
        ( 0x0F900, 0x0FDCF ),
        ( 0x0FDF0, 0x0FFFD ),
        ( 0x10000, 0xEFFFF )
    ]

    addlNameRanges = [
        ( ord("-"), ord("-") ),
        ( ord("."), ord(".") ),
        ( ord("0"), ord("9") ),
        ( 0x000B7, 0x000B7 ),
        ( 0x00300, 0x0036F ),
        ( 0x0203F, 0x02040 )
    ]

    @staticmethod
    def getNameStarts() -> str:
        buf = ""
        lastEnd = 0
        for rg in fromXmlRec.nameStartRanges:
            fr = rg[0]; to = rg[1]
            assert fr > lastEnd and fr <= to and to < sys.maxunicode
            for cp in range(fr, to):
                buf += chr(cp)
        return buf

    @staticmethod
    def getNameChars() -> str:
        buf = fromXmlRec.getNameStarts()
        lastEnd = 0
        for rg in fromXmlRec.addlNameRanges:
            fr = rg[0]; to = rg[1]
            assert fr > lastEnd and fr <= to and to < sys.maxunicode
            for cp in range(fr, to):
                buf += chr(cp)
        return buf

    @staticmethod
    def isNameStart(c:str) -> bool:
        """Undefined chars return False.
        """
        cp = ord(c)
        for rg in fromXmlRec.nameStartRanges:
            fr = rg[0]; to = rg[1]
            if (cp >= fr and cp <= to): return True
        return False

    @staticmethod
    def isNameChar(c:str) -> bool:
        """Undefined chars return False.
        """
        cp = ord(c)
        if isNameStart(cp): return True
        for rg in fromXmlRec.addlNameRanges:
            fr = rg[0]; to = rg[1]
            if (cp >= fr and cp <= to): return True
        return False


###############################################################################
#
nameStartCategories = ("Lu", "Ll", "Lt", "Lm", "Lo", "Nl")
addlNameCategories = ("Nd", "Mn", "Mc", "Nd", "Pc", "Sk")

class fromUnicodeCategories:
    """Identify name and name start characters from the character categories.
    the grammer in the XML REC.
    """
    @staticmethod
    def getNameStarts() -> str:
        nonUnicode = 0
        buf = ""
        for cp in range(0, sys.maxunicode):
            try:
                _ = unicodedata.name(cp)
            except ValueError:
                nonUnicode += 1
                continue
            cat = unicodedata.category(cp)
            if cat in nameStartCategories:
                buf += chr(cp)
        return buf

    @staticmethod
    def getNameChars() -> str:
        nonUnicode = 0
        buf = ""
        for cp in range(0, sys.maxunicode):
            try:
                _uname = unicodedata.name(cp)
            except ValueError:
                nonUnicode += 1
                continue
            cat = unicodedata.category(cp)
            if cat in nameStartCategories or cat in addlNameCategories:
                buf += chr(cp)
        return buf

    @staticmethod
    def isNameStart(c:str) -> bool:
        """Undefined chars return False.
        """
        cat = unicodedata.category(c)
        if cat in nameStartCategories:
            return True
        return False

    @staticmethod
    def isNameChar(c:str) -> bool:
        """Undefined chars return False.
        """
        cat = unicodedata.category(c)
        if cat in nameStartCategories or cat in addlNameCategories:
            return True
        return False


###############################################################################
#
class TestXMLNameChars(unittest.TestCase):
    #lastChar = sys.maxunicode + 1
    lastChar = 0x10100  # good enough for now

    def testClassVsRule(self):
        for c in cls.namestart_chars:
            self.assertTrue(isNameStartByCategory(c))
        for c in cls.name_chars:
            self.assertTrue(isNameCharByCategory(c))

    def test_xml_namestart_chars(self):
        nonUnicode = 0
        for c in range(TestXMLNameChars.lastChar):
            char = chr(c)
            try:
                uname = unicodedata.name(char)
            except ValueError:
                nonUnicode += 1
                continue

            with self.subTest(char=char):
                if char in self.namestart_chars:
                    self.assertTrue(XmlStrings.isXmlName(char),
                        f"Character U+{c:04X} ({uname}) should be a name start")
                    falseNegNameStart.append(ord(char))
                else:
                    self.assertFalse(XmlStrings.isXmlName(char),
                        f"Character U+{c:04X} ({uname}) should not be a name start")
                    falsePosNameStart.append(ord(char))
        sys.stderr.write(f"Non, Unicode chars skipped: {nonUnicode}.")

    def test_xml_name_chars(self):
        for c in range(TestXMLNameChars.lastChar):
            char = chr(c)
            try:
                uname = unicodedata.name(char)
            except ValueError:
                nonUnicode += 1
                continue

            with self.subTest(char=char):
                if char in self.name_chars:
                    self.assertTrue(XmlStrings.isXmlName('a' + char),
                        f"Character U+{c:04X} ({uname}) should be a name character")
                    falseNegName.append(ord(char))
                else:
                    self.assertFalse(XmlStrings.isXmlName('a' + char),
                        f"Character U+{c:04X} ({uname}) should not be a name character")
                    falsePosName.append(ord(char))
        sys.stderr.write(f"Non, Unicode chars skipped: {nonUnicode}.")

class TestCharReferences(unittest.TestCase):
    def test_valid_char_reference(self):
        self.assertEqual(XmlStrings.unescapeXml('&0x10FFFF;'), '\U0010FFFF')
        self.assertEqual(XmlStrings.unescapeXml('&#1114111;'), '\U0010FFFF')

    def test_invalid_char_reference(self):
        with self.assertRaises(ValueError):
            XmlStrings.unescapeXml('&0x110000;')

    def test_surrogate_char_reference(self):
        with self.assertRaises(ValueError):
            XmlStrings.unescapeXml('&0xD800;')
        with self.assertRaises(ValueError):
            XmlStrings.unescapeXml('&0xDFFF;')

class TestReport(unittest.TestCase):
    def test_display(self):
        print("\n======== False positive name starts:\n%s" % (falsePosNameStart))
        print("\n======== False negative name starts:\n%s" % (falseNegNameStart))
        print("\n======== False positive name:\n%s" % (falsePosName))
        print("\n======== False negative name:\n%s" % (falseNegName))

if __name__ == '__main__':
    unittest.main()
