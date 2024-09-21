#!/usr/bin/env python3
#
import sys
import unittest
import logging

#from xml.dom.minidom import getDOMImplementation, DOMImplementation, Document, Node, Element
#from basedom import getDOMImplementation, DOMImplementation, Document, Node, Element

from testNode2 import DAT

whatWG = True
correctCaseFold = True

class TextExtensions(unittest.TestCase):

    def setUp(self):
        dat = DAT()
        self.impl       = dat.impl
        self.doc        = dat.doc
        self.docEl      = dat.docEl
        self.child1     = dat.child1
        self.child2     = dat.child2
        self.grandchild = dat.grandchild
        self.textNode1  = dat.textNode1
        self.emptyNode  = dat.emptyNode
        self.mixedNode  = dat.mixedNode

    def testHasFeature(self):
        """See also testExtensions
        """
        self.assertTrue(self.impl.hasFeature("caseSensitive", True))
        self.assertTrue(self.impl.hasFeature("verbose", 0))
        self.assertTrue(self.impl.hasFeature("prev-next", 1))
        self.assertTrue(self.impl.hasFeature("getitem-n", 1))
        self.assertTrue(self.impl.hasFeature("getitem-name", 1))
        self.assertTrue(self.impl.hasFeature("getitem-attr", 1))
        self.assertTrue(self.impl.hasFeature("nodeTypeProps", 1))
        self.assertTrue(self.impl.hasFeature("NodeTypesEnum", 1))
        self.assertTrue(self.impl.hasFeature("attr-types", 1))
        self.assertTrue(self.impl.hasFeature("constructor-content", 1))
        self.assertTrue(self.impl.hasFeature("NS-any", 1))
        self.assertTrue(self.impl.hasFeature("value-indexer", 1))
        self.assertTrue(self.impl.hasFeature("jsonx", 1))

    def test_nodeType_predicates(self, el, ok:List):
        self.assertEqual(el.isElement,   el.isElement in ok)
        self.assertEqual(el.isAttribute, el.isAttribute in ok)
        self.assertEqual(el.isText,      el.isText in ok)
        self.assertEqual(el.isCDATA,     el.isCDATA in ok)
        self.assertEqual(el.isEntRef,    el.isEntRef in ok)
        self.assertEqual(el.isEntity,    el.isEntity in ok)
        self.assertEqual(el.isPI,        el.isPI in ok)
        self.assertEqual(el.isComment,   el.isComment in ok)
        self.assertEqual(el.isDocument,  el.isDocument in ok)
        self.assertEqual(el.isDoctype,   el.isDoctype in ok)
        self.assertEqual(el.isFragment,  el.isFragment in ok)
        self.assertEqual(el.isNotation,  el.isNotation in ok)


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

        self.assertTrue(el.lastElementChild)
        self.assertTrue(el.elementChildNodes)
        self.assertIs(el.elementChildN(5), el.childNodes[5])
        self.assertEqual(el.classList, "myClass")

        self.assertTrue(el.className)
        self.assertTrue(el.Id)
        self.assertTrue(el.hasIdAttribute)

        # On all CharacterData types and Attrs etc.:
        self.assertTrue(el.hasIdAttribute)

        self.assertFalse(ch10.hasIdAttribute())
        ch10.setAttribute("xml:id", "SomeIdValue_37")
        self.assertTrue(ch10.hasIdAttribute())
        ch10.removeAttribute("xml:id")
        self.assertFalse(ch10.hasIdAttribute())
        self.assertFalse(ch10.hasAttribute("xml:id"))

        ner = self.doc.createEntityReference(name="chap1")
        self.tryAllIsA(ner, Node.isEntRef)
