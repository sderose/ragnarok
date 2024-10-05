#!/usr/bin/python3
#
import unittest
import logging

#from xml.dom.minidom import getDOMImplementation
#from basedom import getDOMImplementation

from makeTestDoc import makeTestDoc0, DAT, DBG

lg = logging.getLogger("testNode")
#logging.basicConfig(level=logging.INFO)

class TestDOMNode(unittest.TestCase):
    def setUp(self):
        makeDocObj = makeTestDoc0()
        self.n = makeDocObj.n

    def test_node_props(self):
        lg.info("Starting test_node_props")
        self.assertEqual(self.n.docEl.nodeName, DAT.root_name)
        self.assertEqual(self.n.docEl.nodeType, self.n.docEl.ELEMENT_NODE)
        self.assertIsNone(self.n.docEl.nodeValue)

    def test_child_nodes(self):
        lg.info("Starting test_child_nodes")
        child = self.n.doc.createElement("child")
        self.n.docEl.appendChild(child)
        self.assertEqual(len(self.n.docEl.childNodes), 1)
        self.assertEqual(self.n.docEl.firstChild, child)
        self.assertEqual(self.n.docEl.lastChild, child)

        aname = "class"
        self.assertFalse(child.hasAttributes())
        child.setAttribute(aname, "x")
        self.assertTrue(child.hasAttributes)
        child.setAttribute(aname, "y")
        self.assertTrue(child.hasAttribute(aname))
        self.assertEqual(child.getAttribute(aname), "y")


    def test_sibling_nodes(self):
        lg.info("Starting test_sibling_nodes")
        child1 = self.n.doc.createElement(DAT.child1_name)
        child2 = self.n.doc.createElement(DAT.child2_name)
        self.n.docEl.appendChild(child1)
        self.n.docEl.appendChild(child2)

        DBG.dumpNodeData(child1, msg="child1")
        DBG.dumpNodeData(child2, msg="child2")
        self.assertEqual(child1.previousSibling, None)
        self.assertIs(child1.nextSibling, child2)
        self.assertIs(child2.previousSibling, child1)
        self.assertEqual(child2.nextSibling, None)

        self.assertTrue(child1.isFirstChild)
        self.assertFalse(child1.isLastChild)
        self.assertFalse(child2.isFirstChild)
        self.assertTrue(child2.isLastChild)

        self.assertIs(self.n.docEl.childNodes[0], self.n.docEl.firstChild)
        self.assertIs(self.n.docEl.childNodes[1], self.n.docEl.lastChild)
        #self.assertRaises(IndexError, self.n.docEl.childNodes[2])

    def test_text_node(self):
        lg.info("Starting test_text_node")
        text = self.n.doc.createTextNode("Hello, World!")
        self.n.docEl.appendChild(text)
        self.assertEqual(text.nodeType, text.TEXT_NODE)
        self.assertEqual(text.nodeValue, "Hello, World!")

    def test_extensions(self):
        lg.info("Starting test_extensions")
        child1 = self.n.doc.createElement(DAT.child1_name)
        child2 = self.n.doc.createElement(DAT.child2_name)
        self.n.docEl.appendChild(child1)
        self.n.docEl.appendChild(child2)

        #self.assertIs(child1.previous, self.n.doc)
        self.assertIs(child1.next, child2)
        self.assertIs(child2.previous, child1)
        self.assertIs(child2.next, None)

    def test_via_checkNode(self):
        lg.info("Starting test_via_checkNode")
        self.n.docEl.checkNode()

if __name__ == '__main__':
    unittest.main()
