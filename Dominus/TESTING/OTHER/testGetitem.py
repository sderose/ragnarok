#!/usr/bin/python3
#
import unittest
from typing import Any

#from xml.dom.minidom import getDOMImplementation
from basedom import getDOMImplementation

class sliceTester(list):
    def __init__(self):
        self.stuff = [ 1, 2, "p", "q" ]

    def __getitem__(self, v:Any):
        print("Type of arg is %s." % (type(v)))


class TestDOMNode(unittest.TestCase):
    nreps = 20

    def setUp(self):
        impl = getDOMImplementation()
        self.doc = impl.createDocument(None, "root", None)
        self.docEl = self.doc.documentElement

        for i in range(TestDOMNode.nreps):
            el = self.doc.createElement("para")
            el.setAttribute("class", "paraThing")
            el.setAttribute("alt", "Nothing here.")
            el.setAttribute("id", f"para_{i}")
            pi = self.doc.createProcessingInstruction("tgt", "foo")
            tx = self.doc.createTextNode("When in the course of human events.")
            cm = self.doc.createComment("This is a comment.")
            cd = self.doc.createCDATASection("And a CDATA <z>section</z>")
            for ch in [ el, pi, tx, cm, cd ]:
                self.docEl.appendChild(ch)
            for ch in [ el, pi, tx, cm, cd ]:
                ch2 = ch.cloneNode()
                if ch2.isElement:
                    ch2.setAttribute("id", "para_B" + ch2.getAttribute("id"))
                self.docEl.appendChild(ch2)

    def test_getitem(self):
        nch = len(self.docEl)
        self.assertEqual(nch, TestDOMNode.nreps*5)

        self.assertTrue(self.docEl[0].isELement)
        self.assertTrue(self.docEl[1].isPI)
        self.assertTrue(self.docEl[2].isText)
        self.assertTrue(self.docEl[3].isComment)
        self.assertTrue(self.docEl[4].isCdata)

        p1 = self.docEl.childNodes[0]
        self.assertEqual(p1.nodeName, "para")

        first5 = self.docEl.childNodes[0:5]
        self.assertIsInstance(first5, list)
        self.assertEqual(len(first5), 5)
        self.assertTrue(first5[0].isElement)
        self.assertTrue(first5[1].isPI)
        self.assertTrue(first5[2].isTextNode)
        self.assertTrue(first5[3].isComment)
        self.assertTrue(first5[4].isCData)

        nreps = TestDOMNode.nreps
        self.assertEqual(self.docEl["zork"], None)
        self.assertEqual(len(self.docEl["para"]), nreps)
        self.assertEqual(len(self.docEl["#text"]), nreps)
        self.assertEqual(len(self.docEl["#pi"]), nreps)
        self.assertEqual(len(self.docEl["#cdata"]), nreps)
        self.assertEqual(len(self.docEl["#comment"]), nreps)

        self.assertTrue(self.docEl["para":0].isElement)
        self.assertTrue(self.docEl["para":-1].isElement)
        self.assertTrue(self.docEl["para":1:].isElement)
        self.assertTrue(len(self.docEl["para":1:3]), 2)

        self.assertEqual(p1["subpara"], None)
        self.assertEqual(p1["@class"], None)
        self.assertEqual(p1["@class":1], None)

        self.assertEqual(self.docEl["*"], nch)


print("Starting")
x = sliceTester()
assert x[1]
assert x["p"]
assert x["p":1]
print("Done")
print(x)

#unittest.main()
