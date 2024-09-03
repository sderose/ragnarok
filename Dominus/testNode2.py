#!/usr/bin/env python3
#
import sys
import unittest
import logging

#from xml.dom.minidom import getDOMImplementation, DOMImplementation, Document, Node, Element
from BaseDOM import getDOMImplementation, DOMImplementation, Document, Node, Element

#import DocumentType
#import DOMBuilder
#import XMLStrings
#import XMLRegexes
#import BaseDOM
#from BaseDOM import Node

lg = logging.getLogger("testNode2")
logging.basicConfig(level=logging.INFO)

nsURI = "https://example.com/namespaces/foo"
whatWG = True
correctCaseFold = True

class TestDOMNode(unittest.TestCase):
    alreadyShowedSetup = False

    @staticmethod
    def once(*args):
        if (TestDOMNode.alreadyShowedSetup): return
        lg.info(*args)

    @staticmethod
    def dumpNode(node:Node, msg:str=""):
        sys.stderr.write("%s (%s)\n" % (msg, node.nodeName))
        node.writexml(sys.stderr, indent='    ', addindent='  ', newl='\n')
        try:
            x = getattr(Node, "toJsonX")
            sys.stderr.write("\n\n" + node.toJsonX(indent='  ') + "\n")
        except AttributeError:
            pass

    def setUp(self):
        #print("Starting setup, using %s", DOMImplementation.__file__)
        impl:DOMImplementation = getDOMImplementation()
        self.once("getDOMImplementation() returned a %s @ %x.", type(impl), id(impl))
        assert isinstance(impl, DOMImplementation)

        DOCELTYPE = "html"
        self.doc:Document = impl.createDocument("http://example.com/ns", DOCELTYPE, None)
        self.once("createDocument() returned a %s @ %x", type(self.doc), id(self.doc))
        assert isinstance(self.doc, Document)
        assert self.doc.ownerDocument is None

        self.docEl:Element = self.doc.documentElement
        self.once("documentElement is a %s @ %x: name %s",
            type(self.docEl), id(self.docEl), self.docEl.nodeName)
        assert isinstance(self.docEl, Element)
        assert (self.docEl.nodeName == DOCELTYPE)
        assert len(self.docEl.childNodes) == 0

        # Add some more nodes

        self.child1 = self.doc.createElement('child1')
        self.child1.setAttribute('attr1', 'value1')
        self.docEl.appendChild(self.child1)

        self.child2 = self.doc.createElement('child2')
        self.docEl.appendChild(self.child2)
        assert len(self.docEl.childNodes) == 2
        assert self.docEl.childNodes[1] == self.child2

        self.grandchild = self.doc.createElement('grandchild')
        self.child2.appendChild(self.grandchild)

        self.text_node1 = self.doc.createTextNode('Some text content')
        self.child1.appendChild(self.text_node1)

        # Add empty node
        self.empty_node = self.doc.createElement('empty')
        self.docEl.appendChild(self.empty_node)

        # Add mixed content
        self.mixed_content = self.doc.createElement('mixed')
        self.mixed_content.appendChild(self.doc.createTextNode('Text before '))
        self.mixed_content.appendChild(self.doc.createElement('inline'))
        self.mixed_content.appendChild(self.doc.createTextNode(' and after'))
        self.docEl.appendChild(self.mixed_content)

        if (not TestDOMNode.alreadyShowedSetup):
            TestDOMNode.dumpNode(self.docEl, "Setup produced:")
            TestDOMNode.alreadyShowedSetup = True

    def test_empty_node(self):
        #TestDOMNode.dumpNode(self.empty_node, "Empty node:")
        self.assertFalse(self.empty_node.hasChildNodes())
        #sys.stderr.write("%s" % (dir(Element)))

        self.assertIsNone(self.empty_node.firstChild)
        self.assertIsNone(self.empty_node.lastChild)
        self.assertEqual(len(self.empty_node.childNodes), 0)

    def test_mixed_content(self):
        self.assertEqual(len(self.mixed_content.childNodes), 3)
        self.assertEqual(self.mixed_content.firstChild.nodeType, Node.TEXT_NODE)
        self.assertEqual(self.mixed_content.firstChild.nodeValue, 'Text before ')
        self.assertEqual(self.mixed_content.childNodes[1].nodeType, Node.ELEMENT_NODE)
        self.assertEqual(self.mixed_content.childNodes[1].nodeName, 'inline')
        self.assertEqual(self.mixed_content.lastChild.nodeType, Node.TEXT_NODE)
        self.assertEqual(self.mixed_content.lastChild.nodeValue, ' and after')

    # This fails with minidom, saying the node isn't there. Eh?
    def test_node_removal(self):
        # Remove child2
        assert self.child2 is not None
        assert self.child2.parentNode == self.docEl
        print("child2: %08x" % (id(self.child2)))
        for i, ch in enumerate(self.docEl.childNodes):
            print("ch %3d: %08x" % (i, id(ch)))
        removed_node = self.docEl.removeChild(self.child2)
        self.assertEqual(removed_node, self.child2)
        self.assertEqual(len(self.docEl.childNodes), 3)
        self.assertEqual(self.docEl.lastChild, self.mixed_content)
        self.assertIsNone(self.child2.parentNode)
        self.assertEqual(self.child1.nextSibling, self.empty_node)

        # Remove text node
        self.child1.removeChild(self.text_node1)
        self.assertFalse(self.child1.hasChildNodes())

        # Try to remove a node that's not a child
        with self.assertRaises(Exception):
            self.docEl.removeChild(self.grandchild)

    def test_node_type(self):
        self.assertEqual(self.docEl.nodeType, Node.ELEMENT_NODE)
        self.assertEqual(self.text_node1.nodeType, Node.TEXT_NODE)
        self.assertEqual(self.empty_node.nodeType, Node.ELEMENT_NODE)

    def test_node_name(self):
        self.assertEqual(self.docEl.nodeName, 'html')
        self.assertEqual(self.child1.nodeName, 'child1')
        self.assertEqual(self.text_node1.nodeName, '#text')
        self.assertEqual(self.empty_node.nodeName, 'empty')

    def test_node_value(self):
        self.assertIsNone(self.docEl.nodeValue)
        self.assertEqual(self.text_node1.nodeValue, 'Some text content')
        self.assertIsNone(self.empty_node.nodeValue)

    def test_parent_node(self):
        self.assertEqual(self.child1.parentNode, self.docEl)
        self.assertEqual(self.grandchild.parentNode, self.child2)
        self.assertEqual(self.empty_node.parentNode, self.docEl)

    def test_child_nodes(self):
        self.assertEqual(len(self.docEl.childNodes), 4)  # child1, child2, empty_node, mixed_content
        self.assertEqual(len(self.child2.childNodes), 1)
        self.assertEqual(len(self.empty_node.childNodes), 0)
        self.assertEqual(len(self.mixed_content.childNodes), 3)

    def test_first_child(self):
        self.assertEqual(self.docEl.firstChild, self.child1)
        self.assertEqual(self.child2.firstChild, self.grandchild)
        self.assertIsNone(self.empty_node.firstChild)
        self.assertEqual(self.mixed_content.firstChild.nodeValue, 'Text before ')

    def test_last_child(self):
        self.assertEqual(self.docEl.lastChild, self.mixed_content)
        self.assertEqual(self.child1.lastChild, self.text_node1)
        self.assertIsNone(self.empty_node.lastChild)
        self.assertEqual(self.mixed_content.lastChild.nodeValue, ' and after')

    def test_previous_sibling(self):
        self.assertEqual(self.child2.previousSibling, self.child1)
        self.assertIsNone(self.child1.previousSibling)

    def test_next_sibling(self):
        self.assertEqual(self.child1.nextSibling, self.child2)
        self.assertIsNone(self.mixed_content.nextSibling)

    def test_attributes(self):
        self.assertIsNotNone(self.child1.attributes)
        self.assertEqual(self.child1.attributes['attr1'].value, 'value1')

        if (whatWG):  # Specifies lower-casing; but lower() != casefold()....
            finalSigma = "\u03C2"; sigma = "\u03C3"
            self.child2.setAttribute("class", "Foo bar baz  \t ba" + finalSigma)
            dtl = self.child2.classList()
            self.assertTrue("Foo" in dtl)
            self.assertTrue("fOo" in dtl)
            if (correctCaseFold):
                self.assertTrue("ba"+finalSigma in dtl)
                self.assertTrue("ba"+sigma in dtl)
                self.assertFalse("ba" in dtl)
            else:
                self.assertTrue("ba"+finalSigma in dtl)
                self.assertFalse("ba"+sigma in dtl)
                self.assertFalse("ba" in dtl)

    def test_owner_document(self):
        self.assertEqual(self.docEl.ownerDocument, self.doc)
        self.assertEqual(self.grandchild.ownerDocument, self.doc)

    def test_has_attributes(self):
        self.assertTrue(self.child1.hasAttributes())
        self.assertFalse(self.child2.hasAttributes())

    def test_has_child_nodes(self):
        self.assertTrue(self.docEl.hasChildNodes())
        self.assertFalse(self.grandchild.hasChildNodes())

    def test_normalize(self):
        new_text = self.doc.createTextNode(' More text')
        self.child1.appendChild(new_text)
        self.assertEqual(len(self.child1.childNodes), 2)
        lg.info("2 text nodes? %s",
            [ ("%s: '%s'" % (x.nodeName, x.data)) for x in self.child1.childNodes ])

        self.child1.normalize()
        lg.info("   post norm  %s",
            [ ("%s: '%s'" % (x.nodeName, x.data)) for x in self.child1.childNodes ])
        self.assertEqual(len(self.child1.childNodes), 1)
        self.assertEqual(self.child1.firstChild.nodeValue, 'Some text content More text')

    def test_clone_node(self):
        cloned_root = self.docEl.cloneNode(deep=False)
        self.assertEqual(cloned_root.nodeName, 'html')
        self.assertEqual(len(cloned_root.childNodes), 0)

        deep_cloned_root = self.docEl.cloneNode(deep=True)
        self.assertEqual(deep_cloned_root.nodeName, 'html')
        self.assertEqual(len(deep_cloned_root.childNodes), 4)

    def test_is_same_node(self):
        self.assertTrue(self.docEl.isSameNode(self.docEl))
        self.assertFalse(self.docEl.isSameNode(self.child1))

if __name__ == '__main__':
    unittest.main()
