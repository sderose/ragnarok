#!/usr/bin/python3
#
import unittest
import logging

#from xml.dom.minidom import getDOMImplementation
#from basedom import getDOMImplementation

from makeTestDoc import makeTestDoc0, DAT  #, DBG

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
        self.assertEqual(len(self.n.docEl.childNodes), 0)
        self.n.docEl.appendChild(child)
        #DBG.dumpNode(self.n.docEl, msg="test_child_nodes")
        self.assertIs(child.parentNode, self.n.docEl)
        self.assertEqual(child.getChildIndex(), 0)
        self.assertEqual(len(self.n.docEl.childNodes), 1)
        #for i, x in enumerate(self.n.docEl.childNodes):
        #    DBG.msg("  %2d: %s" % (i, x.toxml()))
        #DBG.msg("Eh? " + self.n.docEl.childNodes[0].toxml())
        self.assertEqual(self.n.docEl.childNodes[0], child)
        self.assertEqual(self.n.docEl.firstChild, child)
        self.assertEqual(self.n.docEl.lastChild, child)

        aname = "class"
        self.assertFalse(child.hasAttributes())
        child.setAttribute(aname, "x")
        self.assertTrue(child.hasAttributes())
        child.setAttribute(aname, "y")
        self.assertTrue(child.hasAttribute(aname))
        self.assertEqual(child.getAttribute(aname), "y")


    def test_sibling_nodes(self):
        lg.info("Starting test_sibling_nodes")
        child0 = self.n.doc.createElement(DAT.child0_name)
        child1 = self.n.doc.createElement(DAT.child1_name)
        self.n.docEl.appendChild(child0)
        self.n.docEl.appendChild(child1)
        #DBG.dumpNode(self.n.docEl, msg="test_sibling_nodes")

        self.assertEqual(child1.getChildIndex(), 1)
        self.assertEqual(child1.parentNode, self.n.docEl)
        self.assertTrue(child1 in self.n.docEl.childNodes)
        self.assertTrue(child1 in self.n.docEl)

        self.assertEqual(child0.getChildIndex(), 0)
        self.assertEqual(child0.parentNode, self.n.docEl)
        self.assertTrue(child0 in self.n.docEl.childNodes)
        self.assertTrue(child0 in self.n.docEl)

        self.assertFalse(child1 in child0)

        #DBG.dumpNodeData(child0, msg="child0")
        #DBG.dumpNodeData(child1, msg="child1")
        self.assertEqual(child0.previousSibling, None)
        self.assertIs(child0.nextSibling, child1)
        self.assertIs(child1.previousSibling, child0)
        self.assertEqual(child1.nextSibling, None)

        self.assertTrue(child0.isFirstChild)
        self.assertFalse(child0.isLastChild)
        self.assertFalse(child1.isFirstChild)
        self.assertTrue(child1.isLastChild)

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
        child0 = self.n.doc.createElement(DAT.child0_name)
        child1 = self.n.doc.createElement(DAT.child1_name)
        self.n.docEl.appendChild(child0)
        self.n.docEl.appendChild(child1)

        #self.assertIs(child0.previous, self.n.doc)
        self.assertIs(child0.next, child1)
        self.assertIs(child1.previous, child0)
        self.assertIs(child1.next, None)

    def test_via_checkNode(self):
        lg.info("Starting test_via_checkNode")
        self.n.docEl.checkNode()

if __name__ == '__main__':
    unittest.main()
