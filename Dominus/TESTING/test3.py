#!/usr/bin/env python3
#
import unittest
import logging
from typing import Any

#from xml.dom.minidom import getDOMImplementation, DOMImplementation,Element
from basedomtypes import NodeType, HReqE

from basedom import NodeList, Element

from makeTestDoc import makeTestDoc0, DAT_DocBook, DBG

lg = logging.getLogger("testNode3")
logging.basicConfig(level=logging.INFO)

nsURI = "https://example.com/namespaces/foo"


###############################################################################
#
class TestDOMNode(unittest.TestCase):
    """This focuses on testing basic creation and properties of Elements.
    It isn't all that adversarial.
    """
    alreadyShowedSetup = False

    def setUp(self):
        self.makeDocObj = makeTestDoc0(dc=DAT_DocBook)
        self.n = self.makeDocObj.n

    def test_create(self):
        pType = "para"
        attrs = { "class":"x1", "alt":"Hello there", "width":"24pt" }
        for i in range(100):
            attrs["n"] = str(i)
            ch = self.n.doc.createElement(pType, attributes=attrs)
            self.n.docEl.appendChild(ch)
            nte = self.n.doc.createTextNode("This is the #%d thing." % (i))
            self.assertFalse(ch.contains(nte))
            ch.appendChild(nte)
            self.assertTrue(ch.contains(nte))

        self.assertEqual(len(self.n.docEl.childNodes), 100)
        self.assertEqual(len(self.n.docEl), 100)

        ch10 = self.n.docEl.childNodes[10]
        self.assertEqual(ch10.getAttribute("n"), "10")
        self.assertEqual(ch10.getChildIndex(), 10)
        self.assertEqual(ch10.hasAttributes(), True)
        self.assertEqual(ch10.hasAttribute("width"), True)
        ch10.setAttribute("width", "36pt")
        self.assertEqual(ch10.getAttribute("width"), "36pt")

        # Test basic properties of the para nodes (cf Node.checkNode())
        for i in range(1, 99):
            prv = self.n.docEl.childNodes[i-1]
            cur = self.n.docEl.childNodes[i]
            nxt = self.n.docEl.childNodes[i+1]
            self.assertEqual(cur.nodeType, NodeType.ELEMENT_NODE)
            self.assertEqual(cur.nodeName, pType)
            self.assertEqual(len(cur.childNodes), 1)

            self.assertEqual(prv.nextSibling, cur)
            self.assertEqual(cur.nextSibling, nxt)
            self.assertEqual(nxt.previousSibling, cur)
            self.assertEqual(cur.previousSibling, prv)
            self.assertEqual(cur.parentNode, self.n.docEl)
            self.assertEqual(cur.ownerDocument, self.n.doc)

    def test_checkNode(self):
        docEl = self.n.docEl
        self.makeDocObj.addFullTree(node=docEl, n=10, depth=3, withText=True)
        docEl.checkNode(deep=True)

    def testAttrStatus(self):
        """A lot of tree mutators get basic testing just by making the tree
        in the first place. Here, make sure Attrs can be inserted as children.
        """
        def tryInsertions(self, tgt:Element, badThing:Any) -> None:
            with self.assertRaises(HReqE):
                tgt.appendChild(badThing)
                tgt.prependChild(badThing)
                tgt.insert(0, badThing)
                tgt.append(badThing)
                tgt.extend([badThing])
                self.n.docEl.insertBefore(badThing, tgt)
                self.n.docEl.insertAfter(badThing, tgt)

        doc = self.n.doc
        docEl = self.n.docEl
        self.assertFalse(docEl.hasChildNodes)
        self.makeDocObj.addChildren(node=docEl, n=10, withText=True)
        self.assertTrue(docEl.hasChildNodes)
        ch = docEl.childNodes[5]

        tryInsertions(self, tgt=ch, badThing=doc.createAttribute("alt", "hello"))
        tryInsertions(self, tgt=ch, badThing=NodeList())
        tryInsertions(self, tgt=ch, badThing=self)
        tryInsertions(self, tgt=ch, badThing=ch)
        #tryInsertions(self, tgt=ch, badThing=doc)
        #tryInsertions(self, tgt=ch, badThing=docEl)
        tryInsertions(self, tgt=ch, badThing=None)
        tryInsertions(self, tgt=ch, badThing=8)
        tryInsertions(self, tgt=ch, badThing=3.14+1j)
        tryInsertions(self, tgt=ch, badThing=False)
        tryInsertions(self, tgt=ch, badThing="nope")
        tryInsertions(self, tgt=ch, badThing=[ ])

    def test_allNodeTypes(self):
        """At least try creating one of everything.
         cf makeTestDoc2.addAllTypes(troot)
        """
        troot = self.n.doc.createElement("div")
        self.tryAllIsA(troot, NodeType.ELEMENT_NODE)

        ncd = self.n.doc.createCDATASection("Whew, I'm a <section>.")
        self.tryAllIsA(ncd, NodeType.CDATA_SECTION_NODE)
        troot.appendChild(ncd)

        nco = self.n.doc.createComment("So, comments are needed, too.")
        self.tryAllIsA(nco, NodeType.COMMENT_NODE)
        troot.appendChild(nco)

        npi = self.n.doc.createProcessingInstruction(target="myTarget", data="duh")
        self.tryAllIsA(npi, NodeType.PROCESSING_INSTRUCTION_NODE)
        troot.appendChild(npi)

        nat = self.n.doc.createAttribute("class", "someClass", parentNode=None)
        self.tryAllIsA(nat, NodeType.ATTRIBUTE_NODE)

        #ndf = createDocumentFragment()
        #self.tryAllIsA(ndf, NodeType.FRAGMENT_NODE)

        #ndt = self.n.impl.createDocumentType("docbook")
        #self.tryAllIsA(ndt, NodeType.DOCTYPE_NODE)

        # NodeList, NamedNodeMap, ....

    def tryAllIsA(self, node, expectedNodeType:NodeType):
        """Try all the nodeType test properties; only one should be true.
        But they're properties.
        """
        self.assertTrue(node.nodeType == expectedNodeType)

        bits = [
            node.isAttribute,
            node.isCDATA,
            node.isComment,
            node.isDocumentType,
            node.isDocument,
            node.isElement,
            node.isEntRef,
            node.isFragment,
            node.isNotation,
            node.isPI,
            node.isText,
        ]
        hot = sum(bits)
        self.assertEqual(hot, 1)

    def testPrevNextSibling(self):
        par = self.n.docEl
        nch = len(par.childNodes)
        cur = self.n.docEl.firstChild
        for i in range(nch):
            self.assertTrue(cur is par.childNodes[i])
            self.assertTrue(cur.previousSibling is
                par.childNodes[i-1] if (i > 0) else None)
            self.assertTrue(cur.nextSibling is
                par.childNodes[i+1] if (i+1 < nch) else None)
            cur = cur.nextSibling()

    def TODO_test_regular_list_methods(self):  # TODO Finish
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
        for _i in range(10):
            nn = self.n.doc.createElement("newb")
            self.n.docEl.append(nn)

        _nch = len(self.n.docEl.childNodes)
        self.makeDocObj.addChildren(self.n.docEl, n=10)
        DBG.dumpNode(self.n.docEl)
        e5 = self.n.docEl[5]
        #if (e5 is not None): ee7 = e5[0]

        xptr = e5.getNodePath(useId=False)
        self.assertEqual(xptr, [ 1, 5 ])
        xptr = e5.getNodePath(useId=True)
        self.assertEqual(xptr, [ 1, 5 ])

        # TODO Test with something that *does* have an id.

if __name__ == '__main__':
    unittest.main()
