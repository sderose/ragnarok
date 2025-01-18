#!/usr/bin/env python3
#
import unittest
import logging
#from typing import Callable

#from xml.dom.minidom import getDOMImplementation, DOMImplementation, Element
from basedomtypes import NodeType

#from basedom import Node
#
from makeTestDoc import makeTestDoc0, DAT_DocBook  #, DBG

lg = logging.getLogger("testNode3")
logging.basicConfig(level=logging.INFO)

nsURI = "https://example.com/namespaces/foo"

"""
class IdHandler:
    def __init__(self, ownerDocument:'Document', caseHandler:CaseHandler=None,valgen:Callable=None):
    def lockChoices(self) -> None:
    def addAttrChoice(self, ens:str, ename:NMTOKEN_t, ans:str, aname:NMTOKEN_t) -> None:
    def delAttrChoice(self, ens:str, ename:NMTOKEN_t, ans:str, aname:NMTOKEN_t) -> None:
    def getIdAttrNode(self, elem:'Node') -> 'Attr':
    def buildIdIndex(self) -> Dict:
    def clearIndex(self) -> None:
    def getIndexedId(self, idval:str) -> 'Element':
"""

class TestIdHandler(unittest.TestCase):
    alreadyShowedSetup = False

    def setUp(self):
        self.makeDocObj = makeTestDoc0(dc=DAT_DocBook)
        self.n = self.makeDocObj.n

    def test_idh(self):
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
            self.assertEqual(cur.nodeType, NodeType.ELEMENT_NODE.value)
            self.assertEqual(cur.nodeName, pType)
            self.assertEqual(len(cur.childNodes), 1)

            self.assertEqual(prv.nextSibling, cur)
            self.assertEqual(cur.nextSibling, nxt)
            self.assertEqual(nxt.previousSibling, cur)
            self.assertEqual(cur.previousSibling, prv)
            self.assertEqual(cur.parentNode, self.n.docEl)
            self.assertEqual(cur.ownerDocument, self.n.doc)

if __name__ == '__main__':
    unittest.main()
