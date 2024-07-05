#!/usr/bin/python3
#
import unittest
#from xml.dom.minidom import getDOMImplementation
import DOMImplementation

class TestDOMNode(unittest.TestCase):
    def setUp(self):
        impl = DOMImplementation.getDOMImplementation()
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
        self.assertEqual(child1.nextSibling, child2)
        self.assertEqual(child2.previousSibling, child1)

    def test_text_node(self):
        text = self.doc.createTextNode("Hello, World!")
        self.root.appendChild(text)
        self.assertEqual(text.nodeType, text.TEXT_NODE)
        self.assertEqual(text.nodeValue, "Hello, World!")

if __name__ == '__main__':
    unittest.main()
