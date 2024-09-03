#!/usr/bin/env python3
#
import unittest

from xml.dom.minidom import Document

#import BaseDOM
#from BaseDOM import Node
#from BaseDOM import Document

class TestDOMNode(unittest.TestCase):
    def setUp(self):
        self.doc = Document()
        self.root = self.doc.createElement('root')
        self.doc.appendChild(self.root)
        self.kids = []
        for i in range(0, 10):
            ch = self.doc.createElement('child%d' % (i))
            ch.setAttribute('attr1', 'value1')
            self.kids.append(ch)
            self.root.appendChild(ch)

    def test_node_removal(self):
        ch2 = self.root.childNodes[2]
        assert ch2 is not None
        assert ch2.parentNode == self.root
        print("child2: %08x" % (id(ch2)))
        for i, ch in enumerate(self.root.childNodes):
            print("ch %3d: %08x" % (i, id(ch)))
        removed_node = self.root.removeChild(ch2)
        self.assertEqual(id(removed_node), id(ch2))
        self.assertEqual(removed_node, ch2)

if __name__ == '__main__':
    unittest.main()
