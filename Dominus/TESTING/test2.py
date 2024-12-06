#!/usr/bin/env python3
#
import sys
import unittest
import logging

from basedom import Node
from makeTestDoc import makeTestDoc2, DAT, DBG

lg = logging.getLogger("testNode2")
logging.basicConfig(level=logging.WARNING)

debug = False


class TestDOMNode(unittest.TestCase):

    def setUp(self):
        makeDocObj = makeTestDoc2()
        self.n = makeDocObj.n

    def addMixedContent(self):
        """Call after setup() if desired.
        """
        t1 = self.n.doc.createTextNode(DAT.text_before)
        t2 = self.n.doc.createTextNode(DAT.text_inside)
        t3 = self.n.doc.createTextNode(DAT.text_after)

        c2 = self.n.doc.createElement(DAT.inline_name)
        c2.appendChild(t2)

        self.n.mixedNode = self.n.doc.createElement('mixedChild')
        self.n.mixedNode.appendChild(t1)
        self.n.mixedNode.appendChild(c2)
        self.n.mixedNode.appendChild(t3)

        self.n.docEl.appendChild(self.n.mixedNode)

    def test_child2(self):
        #DBG.dumpNode(self.n.child2, "Empty node:")
        self.assertFalse(self.n.child2.hasChildNodes)
        #sys.stderr.write("%s" % (dir(Element)))

        self.assertIsNone(self.n.child2.firstChild)
        self.assertIsNone(self.n.child2.lastChild)
        self.assertEqual(len(self.n.child2.childNodes), 0)

    # This fails with minidom, saying the node isn't there. Eh?
    def test_node_removal(self):
        # Make sure child1 is hooked up right to start with
        assert self.n.child1 is not None
        assert self.n.child1.parentNode == self.n.docEl
        assert self.n.child1 in self.n.docEl.childNodes
        nch = len(self.n.docEl.childNodes)
        nextSib = self.n.child1.nextSibling

        if (debug): DBG.dumpChildNodes(self.n.docEl, "removing child1", True)
        removedNode = self.n.docEl.removeChild(self.n.child1)
        self.assertEqual(removedNode, self.n.child1)
        if (debug): DBG.dumpChildNodes(self.n.docEl, "after", True)
        if (self.n.child1 in self.n.docEl.childNodes):
            sys.stderr.write("    WHAT? pn None? %s (child1 id %x)\n"
                % (self.n.child1.parentNode is None, id(self.n.child1)))
            DBG.dumpChildNodes(self.n.docEl, "after", True)

        self.assertEqual(len(self.n.docEl.childNodes), nch - 1)
        self.assertIsNone(self.n.child1.parentNode)
        self.assertEqual(self.n.child0.nextSibling, nextSib)
        if (nextSib is not None):
            self.assertEqual(nextSib.previousSibling, self.n.child0)
        self.assertFalse(self.n.child1 in self.n.docEl.childNodes)

        # Remove text node
        self.n.child0.removeChild(self.n.textNode1)
        self.assertFalse(self.n.child0.hasChildNodes)

        # Try to remove a node that's not a child
        with self.assertRaises(Exception):
            self.n.docEl.removeChild(self.n.grandchild)

    def test_node_type(self):
        self.assertEqual(self.n.docEl.nodeType, Node.ELEMENT_NODE)
        self.assertEqual(self.n.textNode1.nodeType, Node.TEXT_NODE)
        self.assertEqual(self.n.child2.nodeType, Node.ELEMENT_NODE)

    def test_node_name(self):
        self.assertEqual(self.n.docEl.nodeName, DAT.root_name)
        self.assertEqual(self.n.child0.nodeName, DAT.child0_name)
        self.assertEqual(self.n.textNode1.nodeName, '#text')
        self.assertEqual(self.n.child2.nodeName, DAT.child2_name)

    def test_node_value(self):
        self.assertIsNone(self.n.docEl.nodeValue)
        self.assertEqual(self.n.textNode1.nodeValue, DAT.some_text)
        self.assertIsNone(self.n.child2.nodeValue)

    def test_parent_node(self):
        self.assertEqual(self.n.child0.parentNode, self.n.docEl)
        self.assertEqual(self.n.grandchild.parentNode, self.n.child1)
        self.assertEqual(self.n.child2.parentNode, self.n.docEl)

    ### Mixed content stuff
    #
    def test_mixedNode(self):
        self.addMixedContent()
        self.assertEqual(len(self.n.mixedNode.childNodes), 3)
        self.assertEqual(self.n.mixedNode.firstChild.nodeType, Node.TEXT_NODE)
        self.assertEqual(self.n.mixedNode.firstChild.nodeValue, DAT.text_before)
        self.assertEqual(self.n.mixedNode.childNodes[1].nodeType, Node.ELEMENT_NODE)
        self.assertEqual(self.n.mixedNode.childNodes[1].nodeName, DAT.inline_name)
        self.assertEqual(self.n.mixedNode.lastChild.nodeType, Node.TEXT_NODE)
        self.assertEqual(self.n.mixedNode.lastChild.nodeValue, DAT.text_after)

    def test_first_child(self):
        self.addMixedContent()
        self.assertEqual(self.n.docEl.firstChild, self.n.child0)
        self.assertEqual(self.n.child1.firstChild, self.n.grandchild)
        self.assertIsNone(self.n.child2.firstChild)
        self.assertEqual(self.n.mixedNode.firstChild.nodeValue, DAT.text_before)

    def test_child_nodes(self):
        self.addMixedContent()
        self.assertEqual(len(self.n.docEl.childNodes), 4)
        self.assertEqual(len(self.n.child1.childNodes), 1)
        self.assertEqual(len(self.n.child2.childNodes), 0)
        self.assertEqual(len(self.n.mixedNode.childNodes), 3)

    def test_last_child(self):
        self.addMixedContent()
        self.assertEqual(self.n.docEl.lastChild, self.n.mixedNode)
        self.assertEqual(self.n.child0.lastChild, self.n.textNode1)
        self.assertIsNone(self.n.child2.lastChild)
        self.assertEqual(self.n.mixedNode.lastChild.nodeValue, DAT.text_after)
    #
    ###

    def test_previous_sibling(self):
        self.assertEqual(self.n.child1.previousSibling, self.n.child0)
        self.assertIsNone(self.n.child0.previousSibling)

    def test_next_sibling(self):
        self.assertEqual(self.n.child0.nextSibling, self.n.child1)
        self.assertIsNone(self.n.docEl.childNodes[-1].nextSibling)

    def test_attributes(self):
        self.assertIsNotNone(self.n.child0.attributes)
        self.assertEqual(self.n.child0.attributes[DAT.at_name].nodeValue, DAT.at_value)

    def test_owner_document(self):
        self.assertEqual(self.n.docEl.ownerDocument, self.n.doc)
        self.assertEqual(self.n.grandchild.ownerDocument, self.n.doc)

    def test_has_attributes(self):
        self.assertTrue(self.n.child0.hasAttributes())
        self.assertFalse(self.n.child1.hasAttributes())

    def test_has_child_nodes(self):
        self.assertTrue(self.n.docEl.hasChildNodes)
        self.assertFalse(self.n.grandchild.hasChildNodes)

    def test_normalize(self):
        newTextNode = self.n.doc.createTextNode(DAT.more_text)
        self.n.child0.appendChild(newTextNode)
        self.assertEqual(len(self.n.child0.childNodes), 2)
        lg.info("2 text nodes? %s",
            [ ("%s: '%s'" % (x.nodeName, x.data)) for x in self.n.child0.childNodes ])

        self.n.child0.normalize()
        lg.info("   post norm  %s",
            [ ("%s: '%s'" % (x.nodeName, x.data)) for x in self.n.child0.childNodes ])
        self.assertEqual(len(self.n.child0.childNodes), 1)
        self.assertEqual(self.n.child0.firstChild.nodeValue,
            DAT.some_text + DAT.more_text)

    def test_clone_node(self):
        clonedNode = self.n.docEl.cloneNode(deep=False)
        self.assertEqual(clonedNode.nodeName, DAT.root_name)
        self.assertEqual(len(clonedNode.childNodes), 0)

        selfLen = len(self.n.docEl.childNodes)
        deep_clonedNode = self.n.docEl.cloneNode(deep=True)
        self.assertEqual(deep_clonedNode.nodeName, DAT.root_name)
        cloneLen = len(deep_clonedNode.childNodes)
        if (cloneLen != selfLen):
            lg.warning("Origl: [ %s ]",
                ", ".join([ x.nodeName for x in self.n.docEl.childNodes ]))
            lg.warning("Clone: [ %s ]",
                ", ".join([ x.nodeName for x in deep_clonedNode.childNodes ]))
        self.assertEqual(cloneLen, selfLen)

    def test_is_same_node(self):
        self.assertTrue(self.n.docEl.isSameNode(self.n.docEl))
        self.assertFalse(self.n.docEl.isSameNode(self.n.child0))

if __name__ == '__main__':
    unittest.main()
