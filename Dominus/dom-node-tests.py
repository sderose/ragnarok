#!/usr/bin/env python3
#
import unittest

if (0):
    from xml.dom.minidom import Node, Document
else:
    #import DocumentType
    #import DOMBuilder
    #import XMLStrings
    #import XMLRegexes
    #import BaseDOM
    from BaseDOM import Node, Document

class TestDOMNode(unittest.TestCase):
    def setUp(self):
        self.doc = Document()

        # Create a more complex document structure
        self.root = self.doc.createElement('root')
        self.doc.appendChild(self.root)

        self.child1 = self.doc.createElement('child1')
        self.child1.setAttribute('attr1', 'value1')
        self.root.appendChild(self.child1)

        self.child2 = self.doc.createElement('child2')
        self.root.appendChild(self.child2)

        self.grandchild = self.doc.createElement('grandchild')
        self.child2.appendChild(self.grandchild)

        self.text_node1 = self.doc.createTextNode('Some text content')
        self.child1.appendChild(self.text_node1)

        # Add empty node
        self.empty_node = self.doc.createElement('empty')
        self.root.appendChild(self.empty_node)

        # Add mixed content
        self.mixed_content = self.doc.createElement('mixed')
        self.mixed_content.appendChild(self.doc.createTextNode('Text before '))
        self.mixed_content.appendChild(self.doc.createElement('inline'))
        self.mixed_content.appendChild(self.doc.createTextNode(' and after'))
        self.root.appendChild(self.mixed_content)

    def test_empty_node(self):
        self.assertFalse(self.empty_node.hasChildNodes())
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
        assert self.child2.parentNode == self.root
        print("child2: %08x" % (id(self.child2)))
        for i, ch in enumerate(self.root.childNodes):
            print("ch %3d: %08x" % (i, id(ch)))
        removed_node = self.root.removeChild(self.child2)
        self.assertEqual(removed_node, self.child2)
        self.assertEqual(len(self.root.childNodes), 3)
        self.assertEqual(self.root.lastChild, self.mixed_content)
        self.assertIsNone(self.child2.parentNode)
        self.assertEqual(self.child1.nextSibling, self.empty_node)

        # Remove text node
        self.child1.removeChild(self.text_node1)
        self.assertFalse(self.child1.hasChildNodes())

        # Try to remove a node that's not a child
        with self.assertRaises(ValueError):
            self.root.removeChild(self.grandchild)

    # ... [previous tests remain unchanged] ...

    def test_node_type(self):
        self.assertEqual(self.root.nodeType, Node.ELEMENT_NODE)
        self.assertEqual(self.text_node1.nodeType, Node.TEXT_NODE)
        self.assertEqual(self.empty_node.nodeType, Node.ELEMENT_NODE)

    def test_node_name(self):
        self.assertEqual(self.root.nodeName, 'root')
        self.assertEqual(self.child1.nodeName, 'child1')
        self.assertEqual(self.text_node1.nodeName, '#text')
        self.assertEqual(self.empty_node.nodeName, 'empty')

    def test_node_value(self):
        self.assertIsNone(self.root.nodeValue)
        self.assertEqual(self.text_node1.nodeValue, 'Some text content')
        self.assertIsNone(self.empty_node.nodeValue)

    def test_parent_node(self):
        self.assertEqual(self.child1.parentNode, self.root)
        self.assertEqual(self.grandchild.parentNode, self.child2)
        self.assertEqual(self.empty_node.parentNode, self.root)

    def test_child_nodes(self):
        self.assertEqual(len(self.root.childNodes), 4)  # child1, child2, empty_node, mixed_content
        self.assertEqual(len(self.child2.childNodes), 1)
        self.assertEqual(len(self.empty_node.childNodes), 0)
        self.assertEqual(len(self.mixed_content.childNodes), 3)

    def test_first_child(self):
        self.assertEqual(self.root.firstChild, self.child1)
        self.assertEqual(self.child2.firstChild, self.grandchild)
        self.assertIsNone(self.empty_node.firstChild)
        self.assertEqual(self.mixed_content.firstChild.nodeValue, 'Text before ')

    def test_last_child(self):
        self.assertEqual(self.root.lastChild, self.mixed_content)
        self.assertEqual(self.child1.lastChild, self.text_node1)
        self.assertIsNone(self.empty_node.lastChild)
        self.assertEqual(self.mixed_content.lastChild.nodeValue, ' and after')

    # ... [other tests remain unchanged] ...

if __name__ == '__main__':
    unittest.main()
