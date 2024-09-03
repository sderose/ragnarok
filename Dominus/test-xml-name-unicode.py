#!/usr/bin/env python3
#
import unittest
import unicodedata

#from BaseDOM import
from xmlstrings import XMLStrings

falsePosNameStart = []
falseNegNameStart = []
falsePosName = []
falseNegName = []

class TestXMLNameChars(unittest.TestCase):
    #lastChar = sys.maxunicode + 1
    lastChar = 0x10100  # good enough for now

    @classmethod
    def setUpClass(cls):
        cls.namestart_chars = cls.generate_xml_namestart_chars()
        cls.name_chars = cls.generate_xml_name_chars()

    @staticmethod
    def generate_xml_namestart_chars():
        return (
            set(chr(c) for c in range(TestXMLNameChars.lastChar)
                if unicodedata.category(chr(c)) in {'Lu', 'Ll', 'Lo', 'Lt', 'Nl'})
            | {':'}
            | {chr(c) for c in range(0xC0, 0xD7) if c != 0xD7}
            | {chr(c) for c in range(0xD8, 0xF7) if c != 0xF7}
            | {chr(c) for c in range(0xF8, 0x300)}
            | {chr(0x37F), chr(0x1FFF), chr(0x200C), chr(0x200D)}
            | {chr(c) for c in range(0x2070, 0x218F)}
            | {chr(c) for c in range(0x2C00, 0x2FEF)}
            | {chr(c) for c in range(0x3001, 0xD7FF)}
            | {chr(c) for c in range(0xF900, 0xFDCF)}
            | {chr(c) for c in range(0xFDF0, 0xFFFD)}
            | {chr(c) for c in range(0x10000, 0xEFFFF)}
        )

    @classmethod
    def generate_xml_name_chars(cls):
        return (
            cls.generate_xml_namestart_chars()
            | {'-', '.', '0', '1', '2', '3', '4', '5', '6', '7', '8', '9', '\xB7'}
            | {chr(c) for c in range(0x0300, 0x036F)}
            | {chr(c) for c in range(0x203F, 0x2040)}
        )

    def test_xml_namestart_chars(self):
        for c in range(TestXMLNameChars.lastChar):
            char = chr(c)
            with self.subTest(char=char):
                if char in self.namestart_chars:
                    self.assertTrue(XMLStrings.isXmlName(char),
                        f"Character U+{c:04X} should be a name start character")
                    falseNegNameStart.append(ord(char))
                else:
                    self.assertFalse(XMLStrings.isXmlName(char),
                        f"Character U+{c:04X} should not be a name start character")
                    falsePosNameStart.append(ord(char))

    def test_xml_name_chars(self):
        for c in range(TestXMLNameChars.lastChar):
            char = chr(c)
            with self.subTest(char=char):
                if char in self.name_chars:
                    self.assertTrue(XMLStrings.isXmlName('a' + char),
                        f"Character U+{c:04X} should be a name character")
                    falseNegName.append(ord(char))
                else:
                    self.assertFalse(XMLStrings.isXmlName('a' + char),
                        f"Character U+{c:04X} should not be a name character")
                    falsePosName.append(ord(char))

class TestCharReferences(unittest.TestCase):
    def test_valid_char_reference(self):
        self.assertEqual(XMLStrings.unescapeXml('&#x10FFFF;'), '\U0010FFFF')
        self.assertEqual(XMLStrings.unescapeXml('&#1114111;'), '\U0010FFFF')

    def test_invalid_char_reference(self):
        with self.assertRaises(ValueError):
            XMLStrings.unescapeXml('&#x110000;')

    def test_surrogate_char_reference(self):
        with self.assertRaises(ValueError):
            XMLStrings.unescapeXml('&#xD800;')
        with self.assertRaises(ValueError):
            XMLStrings.unescapeXml('&#xDFFF;')

class TestReport(unittest.TestCase):
    def test_display(self):
        print("\n======== False positive name starts:\n%s" % (falsePosNameStart))
        print("\n======== False negative name starts:\n%s" % (falseNegNameStart))
        print("\n======== False positive name:\n%s" % (falsePosName))
        print("\n======== False negative name:\n%s" % (falseNegName))

if __name__ == '__main__':
    unittest.main()
