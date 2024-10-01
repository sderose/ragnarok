#!/usr/bin/env python3
#
#import sys
import unittest
#import logging
from typing import List

#from xml.dom.minidom import getDOMImplementation, DOMImplementation, Document, Node, Element
#from basedom import getDOMImplementation, DOMImplementation, Document, Node, Element

from maketestdoc import makeTestDoc0, DAT, DAT_DocBook

whatWG = True
correctCaseFold = True

class TextExtensions(unittest.TestCase):

    def setUp(self):
        self.makeDocObj = makeTestDoc0(dc=DAT_DocBook)
        self.n = self.makeDocObj.n

        self.impl       = self.n.impl
        self.doc        = self.n.doc
        self.docEl      = self.n.docEl
        self.child1     = self.n.child1
        self.child2     = self.n.child2
        self.grandchild = self.n.grandchild
        self.textNode1  = self.n.textNode1
        self.emptyNode  = self.n.emptyNode
        self.mixedNode  = self.n.mixedNode

    def test_nodeType_predicates(self, el, ok:List):
        self.assertEqual(el.isElement,      el.isElement in ok)
        self.assertEqual(el.isAttribute,    el.isAttribute in ok)
        self.assertEqual(el.isText,         el.isText in ok)
        self.assertEqual(el.isCDATA,        el.isCDATA in ok)
        self.assertEqual(el.isEntRef,       el.isEntRef in ok)
        self.assertEqual(el.isPI,           el.isPI in ok)
        self.assertEqual(el.isComment,      el.isComment in ok)
        self.assertEqual(el.isDocument,     el.isDocument in ok)
        self.assertEqual(el.isDocumentType, el.isDocumentType in ok)
        self.assertEqual(el.isFragment,     el.isFragment in ok)
        self.assertEqual(el.isNotation,     el.isNotation in ok)

    def test_whatwg(self):
        self.child2.setAttribute("class", "Foo bar baz  \t ba" + DAT.final_sigma)
        dtl = self.child2.classList
        self.assertTrue("Foo" in dtl)
        self.assertTrue("fOo" in dtl)
        if (correctCaseFold):
            self.assertTrue("ba"+DAT.final_sigma in dtl)
            self.assertTrue("ba"+DAT.lc_sigma in dtl)
            self.assertFalse("ba" in dtl)
        else:
            self.assertTrue("ba"+DAT.final_sigma in dtl)
            self.assertFalse("ba"+DAT.lc_sigma in dtl)
            self.assertFalse("ba" in dtl)

        el = self.n.docEl

        self.assertTrue(el.lastElementChild)
        self.assertTrue(el.elementChildNodes)
        self.assertIs(el.elementChildN(5), el.childNodes[5])
        self.assertEqual(el.classList, "myClass")

        self.assertTrue(el.className)
        self.assertTrue(el.Id)
        self.assertTrue(el.hasIdAttribute)

        # On all CharacterData types and Attrs etc.:
        self.assertTrue(el.hasIdAttribute)

        ch10 = el[10]
        self.assertFalse(ch10.hasIdAttribute())
        ch10.setAttribute("xml:id", "SomeIdValue_37")
        self.assertTrue(ch10.hasIdAttribute())
        ch10.removeAttribute("xml:id")
        self.assertFalse(ch10.hasIdAttribute())
        self.assertFalse(ch10.hasAttribute("xml:id"))

        ner = self.doc.createEntityReference(name="chap1")
        self.assertTrue(ner.isEntRef)
