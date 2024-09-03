#!/usr/bin/env python3
#
import sys
import unittest
import logging
from typing import Callable

#from xml.dom.minidom import getDOMImplementation, DOMImplementation, Document, Node, Element
from BaseDOM import getDOMImplementation, DOMImplementation, Document, Node, Element, NodeTypes

#import DocumentType
#import DOMBuilder
#import XMLStrings
#import XMLRegexes
#import BaseDOM
#from BaseDOM import Node

lg = logging.getLogger("testNode3")
logging.basicConfig(level=logging.INFO)

nsURI = "https://example.com/namespaces/foo"

class TestDOMNode(unittest.TestCase):
    alreadyShowedSetup = False

    @staticmethod
    def dumpNode(node:Node, msg:str=""):
        sys.stderr.write("%s (%s)\n" % (msg, node.nodeName))
        node.writexml(sys.stderr, indent='    ', addindent='  ', newl='\n')
        try:
            getattr(Node, "toJsonX")
            sys.stderr.write("\n\n" + node.toJsonX(indent='  ') + "\n")
        except AttributeError:
            pass

    def setUp(self):
        #print("Starting setup, using %s", DOMImplementation.__file__)
        impl:DOMImplementation = getDOMImplementation()
        assert isinstance(impl, DOMImplementation)

        DOCELTYPE = "docbook"
        self.doc:Document = impl.createDocument("http://example.com/ns", DOCELTYPE, None)
        assert isinstance(self.doc, Document)
        assert self.doc.ownerDocument is None

        self.docEl:Element = self.doc.documentElement


    def test_create(self):
        pType = "para"
        attrs = { "class":"x1", "alt":"Hello there", "width":"24pt" }
        for i in range(100):
            attrs["n"] = str(i)
            ch = self.doc.createElement(pType, attributes=attrs)
            self.docEl.appendChild(ch)
            nte = self.doc.createTextNode("This is the #%d thing." % (i))
            self.assertFalse(ch.contains(nte))
            ch.appendChild(nte)
            self.assertTrue(ch.contains(nte))

        self.assertEqual(len(self.docEl.childNodes), 100)
        self.assertEqual(len(self.docEl), 100)

        ch10 = self.docEl.childNodes[10]
        self.assertEqual(ch10.getAttribute("n"), "10")
        self.assertEqual(ch10.getChildIndex(), 10)
        self.assertEqual(ch10.hasAttributes(), True)
        self.assertEqual(ch10.hasAttribute("width"), True)
        ch10.setAttribute("width", "36pt")
        self.assertEqual(ch10.getAttribute("width"), "36pt")
        self.assertFalse(ch10.hasIdAttribute())
        ch10.setAttribute("xml:id", "SomeIdValue_37")
        self.assertTrue(ch10.hasIdAttribute())
        ch10.removeAttribute("xml:id")
        self.assertFalse(ch10.hasIdAttribute())
        self.assertFalse(ch10.hasAttribute("xml:id"))

        # Test basic properties of the para nodes
        for i in range(1, 99):
            prv = self.docEl.childNodes[i-1]
            cur = self.docEl.childNodes[i]
            nxt = self.docEl.childNodes[i+1]
            self.assertEqual(cur.nodeType, NodeTypes.ELEMENT_NODE)
            self.assertEqual(cur.nodeName, pType)
            self.assertEqual(len(cur.childNodes), 1)

            self.assertEqual(prv.nextSibling, cur)
            self.assertEqual(cur.nextSibling, nxt)
            self.assertEqual(nxt.previousSibling, cur)
            self.assertEqual(cur.previousSibling, prv)
            self.assertEqual(cur.parentNode, self.docEl)
            self.assertEqual(cur.ownerDocument, self.docEl)

        # At least try creating one of everything
        ncd = self.doc.createCDATASection("Whew, I'm a <section>.")
        self.tryAllIsA(ncd, Node.isCDATA)
        ch10.appendChild(ncd)
        nco = self.doc.createComment("So, comments are needed, too.")
        self.tryAllIsA(nco, Node.isComment)
        ch10.appendChild(nco)
        npi = self.doc.createProcessingInstruction(target="myTarget", data="duh")
        self.tryAllIsA(npi, Node.isPI)
        ch10.appendChild(npi)
        self.tryAllIsA(ch10, Node.isElement)

        nat = self.doc.createAttribute("class", "someClass", parentNode=None)
        self.tryAllIsA(nat, Node.isAttribute)
        #ndf = createDocumentFragment()
        #self.tryAllIsA(ndf, Node.isFragment)
        #ndt = self.impl.createDocumentType("docbook")
        #self.tryAllIsA(ndt, Node.isDoctype)
        ner = self.doc.createEntityReference(name="chap1")
        self.tryAllIsA(ner, Node.isEntRef)


    typeTesters = [
        Node.isAttribute,
        Node.isCDATA,
        Node.isComment,
        Node.isDoctype,
        Node.isDocument,
        Node.isElement,
        Node.isEntRef,
        Node.isEntity,
        Node.isFragment,
        Node.isNotation,
        Node.isPI,
        Node.isText,
    ]

    def tryAllIsA(self, node, which:Callable):
        for tester in TestDOMNode.typeTesters:
            if (tester is which):
                self.assertTrue(node.tester())
            else:
                self.assertFalse(node.tester())

    def testPrevNext(self):
        n = self.docEl
        ct = 0
        while (n):
            n = n.next()
            ct += 1

        n = self.docEl.rightmost
        ct2 = 0
        while (n):
            n = n.previous()
            ct2 += 1

        assert ct == ct2

    def test_regular_list_methods(self):
        """
        append
        extend
        insert
        remove
        pop
        clear
        index
        count
        sort
        reverse
        copy
        del
        slice assignment
        """
        newNodes = []
        for _i in range(3):
            nn = self.doc.createElement("newb")
            newNodes.append(nn)

        newPar = self.docEl[5][7]
        xptr = newPar.getPath()
        self.assertEqual(xptr, [ 1, 5, 7 ])


if __name__ == '__main__':
    unittest.main()
