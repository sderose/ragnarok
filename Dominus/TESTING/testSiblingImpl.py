#!/usr/bin/env python3
#
#pylint: disable= W0212
#
import unittest
import logging

#from basedomtypes import HReqE, ICharE, NamespaceError

import basedom
from basedom import getDOMImplementation, SiblingImpl

from makeTestDoc import makeTestDoc0  #, DAT_DocBook, DBG

lg = logging.getLogger("testNode3")
logging.basicConfig(level=logging.INFO)

nsURI = "https://example.com/namespaces/foo"


###############################################################################
#
class TestCHNUM(unittest.TestCase):
    def setUp(self):
        basedom._siblingImpl = SiblingImpl.CHNUM

        self.impl = getDOMImplementation()
        self.doc = self.impl.createDocument(None, "html", None)
        self.docEl = self.doc.documentElement

    def testBasics(self):
        docEl = self.docEl
        self.assertTrue(hasattr(docEl, "_childNum"))
        self.assertFalse(hasattr(docEl, "_previousSibling"))
        self.assertFalse(hasattr(docEl, "_nextSibling"))
        docEl.checkNode(deep=True)

        for i in range(10):
            newb = self.doc.createElement("para")
            newb.setAttribute("n", str(i))
            docEl.appendChild(newb)

        self.assertTrue(docEl.hasChildNodes)
        self.assertFalse(docEl.hasTextNodes)
        self.assertEqual(len(docEl), 10)

        for i in range(1, 9):
            ch = docEl.childNodes[i]
            self.assertEqual(int(ch.getAttribute("n")), i)
            self.assertIs(ch.previousSibling, docEl.childNodes[i-1])
            self.assertIs(ch.nextSibling, docEl.childNodes[i+1])

        docEl.checkNode(deep=True)


class TestLINKS(unittest.TestCase):
    def setUp(self):
        basedom._siblingImpl = SiblingImpl.LINKS

        self.impl = getDOMImplementation()
        self.doc = self.impl.createDocument(None, "html", None)
        self.docEl = self.doc.documentElement

    def testBasics(self):
        docEl = self.docEl
        self.assertFalse(hasattr(docEl, "_childNum"))
        self.assertTrue(hasattr(docEl, "_previousSibling"))
        self.assertTrue(hasattr(docEl, "_nextSibling"))
        docEl.checkNode(deep=True)

        for i in range(10):
            newb = self.doc.createElement("para")
            newb.setAttribute("n", str(i))
            docEl.appendChild(newb)

        self.assertTrue(docEl.hasChildNodes)
        self.assertFalse(docEl.hasTextNodes)
        self.assertEqual(len(docEl), 10)

        for i in range(1, 9):
            ch = docEl.childNodes[i]
            self.assertEqual(int(ch.getAttribute("n")), i)
            self.assertIs(ch.previousSibling, docEl.childNodes[i-1])
            self.assertIs(ch.nextSibling, docEl.childNodes[i+1])

        docEl.checkNode(deep=True)

class TestChaning(unittest.TestCase):
    def setUp(self):
        madeDocObj = makeTestDoc0()
        self.n = madeDocObj.n
        self.n.fan = 25
        madeDocObj.addFullTree(self.n.docEl, n=self.n.fan, depth=3,
            withText="", withAttr={})  # Using default text/attrs

    def testChangingSiblingMethod(self):
        doc = self.n.doc
        doc.checkNode(deep=True)

        doc._updateChildSiblingImpl(which=SiblingImpl.PARENT)
        doc.checkNode(deep=True)
        doc._updateChildSiblingImpl(which=SiblingImpl.CHNUM)
        doc.checkNode(deep=True)
        doc._updateChildSiblingImpl(which=SiblingImpl.LINKS)
        doc.checkNode(deep=True)
        doc._updateChildSiblingImpl(which=SiblingImpl.PARENT)
        doc.checkNode(deep=True)

    #def testRemove(self):
    #    doc = self.n.doc

if __name__ == '__main__':
    unittest.main()
