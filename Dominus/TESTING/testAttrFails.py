#!/usr/bin/env python3
#
#pylint: disable=E1120,E1121, W0718
#
import unittest
import basedom
from basedom import Attr
from basedom import HIERARCHY_REQUEST_ERR

class TestAttr(unittest.TestCase):

    def setUp(self):
        self.impl = basedom.getDOMImplementation()
        self.doc = self.impl.createDocument("https://example.com", "article", None)
        self.docEl = self.doc.documentElement
        self.para = self.doc.createElement("para")
        self.docEl.appendChild(self.para)
        self.para.setAttribute("class", "cvalue")
        self.obj = self.para.getAttributeNode("class")

        self.okValues = {
            bool:       True,
            int:        0,
            float:      3.14,
            str:        'aardvark',
            Document:   self.doc,
            Element:    self.para
            Attr:       self.obj
        }

    def test_self_obj_attrToJson(self):
        self.assertRaises(Exception, self.obj.attrToJson())
        self.assertRaises(Exception, self.obj.attrToJson([1, 2, 3]))
        self.assertTrue(isinstance(self.obj.attrToJson('test_string'), str))


    def test_self_obj_checkNode(self):
        self.assertRaises(Exception, self.obj.checkNode())
        self.assertRaises(Exception, self.obj.checkNode('test_string', True))
        self.assertRaises(Exception, self.obj.checkNode(True, 42))


    def test_self_obj_cloneNode(self):
        #self.assertRaises(Exception, self.obj.cloneNode())
        #self.assertRaises(Exception, self.obj.cloneNode(3.14, False))
        #self.assertRaises(Exception, self.obj.cloneNode([1, 2, 3], 3.14))
        self.assertTrue(isinstance(self.obj.cloneNode(), Attr))


    def test_self_obj_compareDocumentPosition(self):
        #self.assertRaises(Exception, self.obj.compareDocumentPosition())
        self.assertRaises(Exception, self.obj.compareDocumentPosition([1, 2, 3]))
        self.assertRaises(Exception, self.obj.compareDocumentPosition(3.14, True))
        self.assertRaises(Exception, self.obj.compareDocumentPosition([1, 2, 3], True))
        self.assertTrue(isinstance(self.obj.compareDocumentPosition(3.14, True), int))


    def test_self_obj_getChildIndex(self):
        self.assertRaises(HIERARCHY_REQUEST_ERR, self.obj.getChildIndex())
        self.assertRaises(Exception, self.obj.getChildIndex(True, False, False, False))
        self.assertRaises(Exception, self.obj.getChildIndex('test_string', 3.14, False, False))
        self.assertRaises(Exception, self.obj.getChildIndex([1, 2, 3], False, 42, False))
        self.assertRaises(Exception, self.obj.getChildIndex(True, False, False, 'test_string'))
        self.assertTrue(isinstance(self.obj.getChildIndex([1, 2, 3], False, False, False), int))


    def test_innerXML_property(self):
        try:
            _value = self.obj.innerXML
        except Exception as e:
            self.fail(f"Accessing property innerXML raised: {e}")


    def test_isConnected_property(self):
        try:
            _value = self.obj.isConnected
        except Exception as e:
            self.fail(f"Accessing property isConnected raised: {e}")


    def test_self_obj_isEqualAttr(self):
        #self.assertRaises(Exception, self.obj.isEqualAttr())
        self.assertRaises(Exception, self.obj.isEqualAttr([1, 2, 3]))
        self.assertRaises(Exception, self.obj.isEqualAttr([1, 2, 3], 'test_string'))
        self.assertRaises(Exception, self.obj.isEqualAttr(True, 3.14))
        self.assertTrue(isinstance(self.obj.isEqualAttr(42, 'test_string'), bool))


    def test_self_obj_outerJSON(self):
        #self.assertRaises(Exception, self.obj.outerJSON())
        self.assertRaises(Exception, self.obj.outerJSON(True, '  ', 0))
        self.assertRaises(Exception, self.obj.outerJSON(True, [1, 2, 3], 0))
        self.assertRaises(Exception, self.obj.outerJSON(42, '  ', True))
        self.assertTrue(isinstance(self.obj.outerJSON(3.14, '  ', 0), str))


    def test_outerXML_property(self):
        try:
            _value = self.obj.outerXML
        except Exception as e:
            self.fail(f"Accessing property outerXML raised: {e}")


    def test_self_obj_tostring(self):
        self.assertTrue(isinstance(self.obj.tostring(), str))


if __name__ == '__main__':
    unittest.main()
