#!/usr/bin/python3
#
import unittest
#from xml.dom.minidom import getDOMImplementation
from basedom import getDOMImplementation

class TestDOMNode(unittest.TestCase):
    def setUp(self):
        impl = getDOMImplementation()
        self.doc = impl.createDocument(None, "root", None)
        self.docEl = self.doc.documentElement
        for _i in range(20):
            el = self.doc.createElement("para")
            el.setAttribute("class", "paraThing")
            el.setAttribute("alt", "Nothing here.")
            pi = self.doc.createProcessingInstruction("tgt", "foo")
            tx = self.doc.createTextNode("When in the course of human events.")
            cm = self.doc.createComment("This is a comment.")
            cd = self.doc.createCDATASection("And a CDATA <z>section</z>")
            for ch in [ el, pi, tx, cm, cd ]:
                self.docEl.appendChild(el)
            for ch in [ el, pi, tx, cm, cd ]:
                ch2 = ch.cloneNode()
                self.docEl.appendChild(ch2)


    def test_getitem(self):
        nch = len(self.docEl)
        self.assertEqual(nch, 10)

        self.assertTrue(self.docEl[0].isELement)
        self.assertTrue(self.docEl[1].isPI)
        self.assertTrue(self.docEl[2].isText)
        self.assertTrue(self.docEl[3].isComment)
        self.assertTrue(self.docEl[4].isCdata)

        p1 = self.docEl.childNodes[0]
        self.assertEqual(p1.nodeName, "para")

        first5 = self.docEl.childNodes[0:5]
        self.assertEqual(len(first5), 5)
        x = self.docEl["zork"]
        x = self.docEl["para"]
        x = self.docEl["para":0]
        x = self.docEl["para":-1]
        x = self.docEl["para":1:]

        x = p1["subpara"]
        x = p1["@class"]
        x = p1["@class":1]

        x = self.docEl["*"]

        x = self.docEl["#text"]
        x = self.docEl["#pi"]
        x = self.docEl["#cdata"]
        x = self.docEl["#comment"]

unittest.main()
