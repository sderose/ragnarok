#!/usr/bin/env python3
#
#pylint: disable=W0201
#
import codecs
import unittest
import logging
#from typing import Dict, Any
#from types import ModuleType
#from collections import defaultdict

from ragnaroktypes import HReqE, ICharE, NSuppE
from basedom import (DOMImplementation, getDOMImplementation,
    Node, Document, Element, Text, NodeList)
from schemera import DocumentType

from makeTestDoc import makeTestDoc2  #, DAT_DocBook, DBG

lg = logging.getLogger("testYggdrasil")
logging.basicConfig(level=logging.INFO)

nsURI = "https://example.com/namespaces/foo"

# Internal sample document
#
tdoc = """<html>
<head><title>Eine Kleine NachtSchrift</title>
</head>
<body>
<h1>Here <i>it</i> is.</h1>
<p>For what it's worth &amp; costs.</p>
<p id="zork" class="big blue" />
<!-- comments, too? -->
<?and a PI?>
<p>-30-</p>
</body>
</html>
"""


###############################################################################
#
class TestDOMImplementation(unittest.TestCase):
    """Most is already pretty thoroughly tested by test1...test5.
    """
    alreadyShowedSetup = False

    def setUp(self):
        print("In TestDOMImplementation")

    def test_Residue(self):
        di = getDOMImplementation()

        with self.assertRaises(ICharE):
            di.createDocument(qualifiedName="12345")

        self.assertIsInstance(
            di.createDocument(
                namespaceURI="http://www.example.com/namespaces/fooNS",
                qualifiedName="stuff"),
            Document)

        doctype = DocumentType()
        self.assertIsInstance(
            di.createDocument(
                namespaceURI="http://www.example.com/namespaces/fooNS",
                qualifiedName="foo:stuff",
                doctype=doctype),
            Document)


###############################################################################
#
class TestNodeList(unittest.TestCase):
    def setup(self):
        print("In TestNodeList")
        makeDocObj = makeTestDoc2(nchildren=20)
        self.n = makeDocObj.n
        #self.docEl = makeDocObj.n.docEl

    def testNL(self):
        nl = NodeList()
        for ch in self.n.docEl.childNodes:
            nl.append(ch)

        self.assertEqual(nl.length(), 20)

        with self.assertRaises(ValueError):
            nl.__delitem__(self.docEl)

        self.assertTrue(nl.textContent)
        self.assertTrue(len(nl.textContent(sep="#")) > 10)  # TODO FIX

        with self.assertRaises(NSuppE):
            nl.textContent = "Can't do this."

        px = self.docEl.toprettyxml()
        self.assertTrue(px.startswith("<?xml"))

        with codecs.open("/temp/writexml37.xml", "wb", encoding="utf-8") as ofh:
            self.docEl.writexml(
                ofh, indent='\t', addindent='\t', newl='\r\n')


###############################################################################
#
class TestYggdrasil(unittest.TestCase):
    def setup(self):
        print("In TestYggdrasil")
        makeDocObj = makeTestDoc2(nchildren=20)
        self.n = makeDocObj.n

    def test_Ygg(self):
        docEl = self.n.docEl
        lastCh = docEl[-1]
        #lcn = lastCh.nodeName
        self.assertTrue(docEl.hasDescendant(lastCh))

        # Test __filter__ as used by __getitem__ when [] was handed
        # a string or a slice (not just an int).
        self.assertTrue(docEl[15].isElement)
        self.assertTrue(docEl[-5].isElement)
        self.assertIsNone(docEl[25])

        self.assertIsInstance(docEl["*":None:None], NodeList)
        self.assertIsInstance(docEl["**":None:None], NodeList)
        self.assertIsInstance(docEl["//"], NodeList)
        self.assertIsInstance(lastCh[".."], Node)
        self.assertEqual(lastCh[".."], docEl)
        self.assertIsInstance(lastCh["@class"], str)

        with self.assertRaises(ValueError):
            x = docEl["$$$"]

        # TODO Add testing for custom sliceHandlers
        # TODO wsn:bool=True, coalesceText:bool=False)

        self.assertEqual(
            lastCh.getChildIndex(), 20)
        self.assertEqual(
            lastCh.getChildIndex(onlyElements=True, ofNodeName=False), 20)
        self.assertEqual(
            lastCh.getChildIndex(onlyElements=True, ofNodeName=True), 18)
        self.assertEqual(
            lastCh.getChildIndex(self, onlyElements=False, ofNodeName=True), 18)
        self.assertEqual(
            lastCh.getChildIndex(self, onlyElements=False, ofNodeName=True), 18)

        self.assertEqual(
            lastCh.getRChildIndex(), 0)
        self.assertEqual(
            lastCh.getRChildIndex(onlyElements=True, ofNodeName=False), 0)
        self.assertEqual(
            lastCh.getRChildIndex(onlyElements=True, ofNodeName=True), 0)
        self.assertEqual(
            lastCh.getRChildIndex(self, onlyElements=False, ofNodeName=True), 0)

        tn = self.docEl.ownerDocument.createTextNode("Some text")
        self.docEl.appendNode(tn)
        self.assertEqual(
            lastCh.getChildIndex(self, onlyElements=False, ofNodeName=True), 1)
        self.assertEqual(
            lastCh.getRChildIndex(self, onlyElements=False, ofNodeName=True), 0)

        with self.assertRaises(NSuppE):
            docEl.nodeValue = "5"

        with self.assertRaises(HReqE):
            lastCh.unlink()

        with self.assertRaises(HReqE):
            tn._resetinheritedNS()

        self.assertIsInstance(tn.removeNode(), Text)

        with self.assertRaises(NSuppE):
            self.impl.getInterface()

        with self.assertRaises(NSuppE):
            self.impl.isSupported

        ch4 = docEl[4]
        ch8 = docEl[8]

        self.assertTrue(ch4 << ch8)
        self.assertTrue(ch8 >> ch4)
        self.assertFalse(ch4 >> ch8)
        self.assertFalse(ch8 << ch4)

        oDoc = self.impl.createDcument(qualifiedName="otherDoc")
        e0 = oDoc.createElement("p")
        oDoc.appendChild(e0)

        with self.assertRaises(HReqE):
            lastCh.compareDocumentPosition(e0)

        self.assertFalse(tn.isConnected)
        with self.assertRaises(HReqE):
            lastCh.compareDocumentPosition(tn)

        tn2 = self.doc.createTextNode("Another text node")
        docEl.appendChild(tn2)

        with self.assertRaises(HReqE):
            tn2.renameNode(namespaceURI="http://example.com/ns", qualifiedName="p")
        self.assertIsInstance(lastCh.renameNode("http://example.com/ns", "p"), Element)


###############################################################################
#
class TestYggdrasil2(unittest.TestCase):
    def setup(self):
        print("In TestYggdrasil2")

    def testYgg(self):
        ns = "https://namespacesRus.org/ns/someNS"
        impl = getDOMImplementation()
        doc = impl.createDocument(namespaceURI=ns, qualifiedName="doc3.14-a")
        docEl = doc.documentElement

        # Alternating <thing> and #text nodes.
        for i in range(10):
            ch = doc.createElement("thing")
            docEl.appendChild(ch)
            tn = doc.createTextNode("Another text node")
            docEl.appendChild(tn)

        nCh = len(docEl)
        self.assertEqual(nCh, 20)
        fCh = docEl[0]
        mCh = docEl[nCh >> 1]
        lCh = docEl[-1]

        # TODO Move __filter__ cases into here from earlier

        self.assertEqual(lCh.preceding, lCh.previousSibling)
        self.assertEqual(lCh.following, lCh.nextSibling)

        self.assertEqual(len(list(mCh.previousSiblings())), 10)
        self.assertEqual(len(list(mCh.nextSiblings())), 9)
        self.assertEqual(len(list(mCh.previousNodes())), 11)
        self.assertEqual(len(list(mCh.nextNodes())), 9)
        self.assertEqual(len(list(mCh.parents())), 1)
        self.assertEqual(len(list(mCh.precedingSiblings())), 10)
        self.assertEqual(len(list(mCh.followingSiblings())), 10)
        self.assertEqual(len(list(mCh.precedingNodes())), 10)
        self.assertEqual(len(list(mCh.followingNodes())), 10)

        #for method in methods:
        #    n = 0
        #    while (method()): n += 1
        #    self.assertEqual(n, 10)

        # TODO Try with 'test' arg

        # TODO nextElementSibling
        # TODO previousElementSibling

        self.assertTrue(fCh.isDefaultNamespace(ns))

        self.assertIsNone(fCh.lookupPrefix(ns))

        self.assertTrue(tn.isCharacterData)
        self.assertFalse(fCh.isCharacterData)

        n = Node()
        with self.assertRaises(NSuppE):
            n.outerXML = "<p/>"

        with self.assertRaises(NSuppE):
            n.getNodeSteps()

        self.assertIsInstance(docEl.tocanonicalxml(), str)

        # TODO replaceWith


if __name__ == '__main__':
    unittest.main()
