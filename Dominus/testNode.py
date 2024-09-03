#!/usr/bin/python3
#
import unittest
#from xml.dom.minidom import getDOMImplementation
from BaseDOM import getDOMImplementation

class TestDOMNode(unittest.TestCase):
    def setUp(self):
        impl = getDOMImplementation()
        self.doc = impl.createDocument(None, "root", None)
        self.root = self.doc.documentElement

    def test_node_attributes(self):
        self.assertEqual(self.root.nodeName, "root")
        self.assertEqual(self.root.nodeType, self.root.ELEMENT_NODE)
        self.assertIsNone(self.root.nodeValue)

    def test_child_nodes(self):
        child = self.doc.createElement("child")
        self.root.appendChild(child)
        self.assertEqual(len(self.root.childNodes), 1)
        self.assertEqual(self.root.firstChild, child)
        self.assertEqual(self.root.lastChild, child)

    def test_sibling_nodes(self):
        child1 = self.doc.createElement("child1")
        child2 = self.doc.createElement("child2")
        self.root.appendChild(child1)
        self.root.appendChild(child2)

        self.assertEqual(child1.previousSibling, None)
        self.assertIs(child1.nextSibling, child2)
        self.assertIs(child2.previousSibling, child1)
        self.assertEqual(child2.nextSibling, None)

        self.assertIs(child1.previous, self.doc)
        self.assertIs(child1.next, child2)
        self.assertIs(child2.previous, child1)
        self.assertIs(child2.next, None)

        self.assertTrue(child1.isFirstChild)
        self.assertFalse(child1.isLastChild)
        self.assertFalse(child2.isFirstChild)
        self.assertTrue(child2.isLastChild)

        self.assertIs(self.doc.childNodes[0], self.doc.firstChild)
        self.assertIs(self.doc.childNodes[1], self.doc.lastChild)

    def test_text_node(self):
        text = self.doc.createTextNode("Hello, World!")
        self.root.appendChild(text)
        self.assertEqual(text.nodeType, text.TEXT_NODE)
        self.assertEqual(text.nodeValue, "Hello, World!")

    #def test_via_checkNode(self):
    #    self.root.checkNode()

if __name__ == '__main__':
    unittest.main()
