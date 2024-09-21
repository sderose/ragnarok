#!/usr/bin/env python3
#
#pylint: disable=W0212,E1101
#
import unittest

from basedom import getDOMImplementation

NCH = 10

if (1):
    """Handle linked list updates (OBSOLETE, this didn't help speed)
    """
    def buildSiblingChain(self):
        """This can be used if you turn on sibling threading after stuff exists.
        """
        if (not self.siblingThread): return
        if (not self.childNodes): return
        for i, ch in enumerate(self.childNodes):
            assert ch.ownerDocument == self.ownerDocument
            assert ch.parentNode == self
            ch.spliceIn(i)

    def spliceOut(self):
        """Call this *after* removing self from self.parent.childNodes.
        """
        assert self not in self.parentNode.childNodes
        if (self._previousSibling is not None):
            self._previousSibling._nextSibling = self._nextSibling
        if (self._nextSibling is not None):
            self._nextSibling._previousSibling = self._previousSibling
        self._previousSibling = self._nextSibling = self.parentNode = None

    def spliceIn(self, n:int=None):
        """Call this *after* inserting self into self.parent.childNodes
        AND setting self.parentNode.
        """
        if (n is None): n = self.getChildIndex()
        assert self.parentNode.childNodes[n] is self
        if (n > 0):
            self._previousSibling = self.parentNode.childNodes[n-1]
            self._previousSibling._nextSibling = self
        else:
            self._previousSibling = None
        if (n < len(self.parentNode.childNodes)-1):
            self._nextSibling = self.parentNode.childNodes[n+1]
            self._nextSibling._previousSibling = self
        else:
            self._nextSibling = None



class TestNode(unittest.TestCase):
    def setUp(self):
        self.impl = getDOMImplementation()
        self.doc = self.impl.createDocument(None, "article", None)
        self.root = self.doc.documentElement

        #for _i in range(NCH):
        #    ch = self.doc.createElement("para")
        #    self.root.appendChild(ch)

        self.child1 = self.doc.createElement("foo1")
        self.child2 = self.doc.createElement("foo2")
        self.child3 = self.doc.createElement("foo3")
        self.root.appendChild(self.child1)
        self.root.appendChild(self.child2)
        self.root.appendChild(self.child3)

    def test_buildSiblingChain(self):
        self.root.buildSiblingChain()

        self.assertIsNone(self.child1.previousSibling)
        self.assertEqual(self.child1.nextSibling, self.child2)
        self.assertEqual(self.child2.previousSibling, self.child1)
        self.assertEqual(self.child2.nextSibling, self.child3)
        self.assertEqual(self.child3.previousSibling, self.child2)
        self.assertIsNone(self.child3.nextSibling)

    def test_spliceOut(self):
        self.root.buildSiblingChain()

        self.child2.spliceOut()

        self.assertEqual(self.child1.nextSibling, self.child3)
        self.assertEqual(self.child3.previousSibling, self.child1)
        self.assertIsNone(self.child2.previousSibling)
        self.assertIsNone(self.child2.nextSibling)
        self.assertIsNone(self.child2.parentNode)

        self.root.buildSiblingChain()

        self.root.childNodes.insert(1, self.child2)
        self.child2.parentNode = self.root
        self.child2.spliceIn(1)

        self.assertEqual(self.child1.nextSibling, self.child2)
        self.assertEqual(self.child2.previousSibling, self.child1)
        self.assertEqual(self.child2.nextSibling, self.child3)
        self.assertEqual(self.child3.previousSibling, self.child2)

    def test_removeNode(self):
        self.root.buildSiblingChain()

        self.root.removeChild(self.root.childNodes[5])

        self.assertEqual(len(self.root.childNodes), 2)
        self.assertEqual(self.child1.nextSibling, self.child3)
        self.assertEqual(self.child3.previousSibling, self.child1)
        self.assertIsNone(self.child2.parentNode)
        self.assertIsNone(self.child2.previousSibling)
        self.assertIsNone(self.child2.nextSibling)

    def test_getChildIndex(self):
        self.assertEqual(self.child1.getChildIndex(), 0)
        self.assertEqual(self.child2.getChildIndex(), 1)
        self.assertEqual(self.child3.getChildIndex(), 2)

    def test_spliceIn_with_optional_n(self):
        self.root.buildSiblingChain()

        self.root.childNodes.insert(1, self.child3)
        self.child3.parentNode = self.root
        self.child3.spliceIn()  # n is not provided

        self.assertEqual(self.child1.nextSibling, self.child3)
        self.assertEqual(self.child3.previousSibling, self.child1)
        self.assertEqual(self.child3.nextSibling, self.child2)
        self.assertEqual(self.child2.previousSibling, self.child3)

if __name__ == '__main__':
    unittest.main()
