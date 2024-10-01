#!/usr/bin/env python3
#
#pylint: disable=W0201, C2801
#
import sys
import os
import unittest
#import math
#import random
from collections import defaultdict
from typing import List

from makeTestDoc import makeTestDoc0, makeTestDoc2, DAT, DBG

from domexceptions import *
from domenums import NodeType
from xmlstrings import XmlStrings as XStr

from basedom import DOMImplementation
from basedom import PlainNode, Node, Document, Element
from basedom import Attr, NamedNodeMap, NodeList

descr = """
To Do:

* Add tests for the CharacterData methods.
"""


###############################################################################
# Constants for document generator
#
dataDir = os.environ["sjdUtilsDir"] + "/Data"

class K(DAT):
    doc_path = "file://%s/TextFormatSamples/sample.xml" % (dataDir)

    root_name = 'article'
    p_name = "para"
    inline_name = "q"

    ns_prefix = "docbook"
    ns_uri = "http://docbook.org/ns/docbook"

    pi_target = "someTarget"
    pi_data = """someData='foo' bar="baz" 12.1?"""
    com_data = "Comments are cool. Lots of potassium."
    cdata_data = "For example, in XML you say <p>foo</p> [[sometimes]]."
    base_attr_name = "anAttrName"
    new_name = "newb"
    attr1_name = "class"
    attr1_value = "important"
    text1 = "aardvark"
    udk1_name = "myUDKey"
    udk1_value = "999"

    outer = f"""<{p_name} id="foo">From xml string</{p_name}>"""


###############################################################################
#
class makeTestDocEachMethod(makeTestDoc0):
    """Make a common starting doc. Superclass makes just root element.
    Add 10 children, same type, @n numbered, and one more attr plus text.
    TODO: Move to makeTestDoc.
    """
    def __init__(self, dc:type=DAT, show:bool=False):
        super().__init__(dc=dc)
        assert isinstance(self.n.impl, DOMImplementation)
        assert isinstance(self.n.doc, Document)
        assert isinstance(self.n.docEl, Element)

        for i in range(10):
            p = self.n.doc.createElement(self.dc.p_name)
            p.setAttribute(self.dc.attr1_name, self.dc.attr1_value)
            p.setAttribute("n", i)
            t = self.n.doc.createTextNode(self.dc.text1)
            p.appendChild(t)
            self.n.docEl.appendChild(p)

        #DBG.dumpNode(self.n.docEl)
        #y = self.makeSampleDoc()
        #x = self.makeSampleDoc()

        if show: sys.stderr.write(
            "makeTestDocEachMethod produced: " + self.n.doc.outerXML)


###############################################################################
#
class TestExceptions(unittest.TestCase):
    def setUp(self):
        madeDocObj = makeTestDocEachMethod(dc=K)
        self.n = madeDocObj.n

    @staticmethod
    def makeSampleDoc():
        pass

    def testExceptions(self):
        self.assertTrue(isinstance(HIERARCHY_REQUEST_ERR(), Exception))
        self.assertTrue(isinstance(WRONG_DOCUMENT_ERR(), Exception))
        self.assertTrue(isinstance(INVALID_CHARACTER_ERR(), Exception))
        self.assertTrue(isinstance(NOT_FOUND_ERR(), Exception))
        self.assertTrue(isinstance(NOT_SUPPORTED_ERR(), Exception))
        self.assertTrue(isinstance(NAMESPACE_ERR(), Exception))


###############################################################################
#
class test_NodeType(unittest.TestCase):
    def setUp(self):
        madeDocObj = makeTestDocEachMethod(dc=K)
        self.n = madeDocObj.n

    def tests(self):
        from xml.dom.minidom import Node as MN

        for n in range(13):
            self.assertTrue(NodeType.okNodeType(NodeType(n), die=False))
            self.assertTrue(NodeType.okNodeType(NodeType(n), die=False))
            self.assertTrue(NodeType.tostring(NodeType(n)))

        AEQ = self.assertEqual
        AEQ(Node.ELEMENT_NODE,                 NodeType(MN.ELEMENT_NODE))
        AEQ(Node.ATTRIBUTE_NODE,               NodeType(MN.ATTRIBUTE_NODE))
        AEQ(Node.TEXT_NODE,                    NodeType(MN.TEXT_NODE))
        AEQ(Node.CDATA_SECTION_NODE,           NodeType(MN.CDATA_SECTION_NODE))
        AEQ(Node.ENTITY_REFERENCE_NODE,        NodeType(MN.ENTITY_REFERENCE_NODE))
        AEQ(Node.ENTITY_NODE,                  NodeType(MN.ENTITY_NODE))
        AEQ(Node.PROCESSING_INSTRUCTION_NODE,
            NodeType(MN.PROCESSING_INSTRUCTION_NODE))
        AEQ(Node.COMMENT_NODE,                 NodeType(MN.COMMENT_NODE))
        AEQ(Node.DOCUMENT_NODE,                NodeType(MN.DOCUMENT_NODE))
        AEQ(Node.DOCUMENT_TYPE_NODE,           NodeType(MN.DOCUMENT_TYPE_NODE))
        AEQ(Node.DOCUMENT_FRAGMENT_NODE,       NodeType(MN.DOCUMENT_FRAGMENT_NODE))
        AEQ(Node.NOTATION_NODE,                NodeType(MN.NOTATION_NODE))


###############################################################################
#
class TestDOMImplementation(unittest.TestCase):
    def setUp(self):
        madeDocObj = makeTestDoc2()
        self.n = madeDocObj.n

    def NOTYET_testDImpl(self):
        x = self.n.impl.createDocument("exampl", "html", None)
        self.assertTrue(x.isDocument)

        x = self.n.impl.createDocumentType("html", None, "c:\\foo.dtd")
        self.assertTrue(x.isDocumentType)

        x = self.n.impl.registerDOMImplementation(self, "BaseDom", factory=None)

        #x = self.n.impl.parse("/tmp/x.xml", parser=None, bufsize=1024)
        #self.assertTrue(x.isDocument)

        x = self.n.impl.parse_string(
            self, s="<article id='a1'>foo></article>", parser=None)
        self.assertTrue(x.isDocument)


###############################################################################
#
class test_DomBuilder(unittest.TestCase):
    def setUp(self):
        pass

    def NOTYET_testDBuild(self):
        import dombuilder
        #_create_document(self)
        #el.registerDOMImplementation(name, factory)

        #adoc = self.n.impl.parse(self.dc.doc_path)
        dbuilder = dombuilder.DomBuilder()

        theSamplePath = "./TESTING/docForTestEachMethod_testDI.xml"
        assert os.path.exists(theSamplePath)
        theDom = dbuilder.parse(theSamplePath)
        self.assertTrue(isinstance(theDom. Document))

        dum_doc = """<?xml version="1.0"?><doc>Hello</doc>"""
        theDom = dbuilder.parse_string(s=dum_doc)
        self.assertTrue(isinstance(theDom, Document))
        self.assertEqual(theDom.documentElement.toxml(), dum_doc)


###############################################################################
#
class test_NodeList(unittest.TestCase):
    def setUp(self):
        madeDocObj = makeTestDocEachMethod(dc=K)
        self.n = madeDocObj.n

        madeDocObj.addChildren(self.n.docEl, n=20)

        self.nl1 = NodeList(self.n.docEl[0:-1:2])
        self.nl2 = NodeList(self.n.docEl[0:-1:3])

        for ch in self.n.docEl.childNodes: self.assertTrue(ch.isElement)
        for ch in self.nl1: self.assertTrue(ch.isElement)
        for ch in self.nl2: self.assertTrue(ch.isElement)

    def tests(self):
        origLen = len(self.n.docEl.childNodes)
        nl = NodeList()
        for n in reversed(self.n.docEl.childNodes):
            nl.append(n)
        self.assertEqual(len(nl), origLen)

        for n in range(len(nl)):
            self.assertEqual(nl.item(n), self.n.docEl.childNodes[origLen-n-1])

        #self.assertRaises(NotImplementedError, nl.__mul__, 2)
        #self.assertRaises(NotImplementedError, nl.__rmul__, 2)


###############################################################################
#
class test_PlainNode(unittest.TestCase):
    def setUp(self):
        madeDocObj = makeTestDocEachMethod(dc=K)
        self.dc = K
        self.n = madeDocObj.n

    def tests(self):
        el8 = self.n.docEl.childNodes[8]
        pnode = PlainNode(ownerDocument=None, nodeName="aPlainNodeToTry")

        #self.assertRaises(IndexError, self.n.docEl.childNodes[200])
        #self.assertRaises(IndexError, self.n.docEl.childNodes[-200])

        if (0):
            self.assertEqual(None, pnode.prefix)
            #self.assertEqual("notAnElement", pnode.localName)
            self.assertEqual(None, pnode.namespaceURI)
        else:
            self.assertEqual(None, pnode.prefix)
            self.assertEqual(None, pnode.localName)
            self.assertEqual(None, pnode.namespaceURI)

        self.assertFalse(pnode.isConnected)

        self.assertEqual(None, pnode.nextSibling)
        self.assertEqual(None, pnode.previousSibling)
        self.assertFalse(pnode.childNodes)  # None or [] is ok.

        self.assertEqual(None, pnode.nodeValue)

        self.assertFalse(el8.isEqualNode(pnode))
        self.assertFalse(el8.isSameNode(pnode))

        self.assertFalse(pnode.contains(pnode))
        self.assertFalse(pnode.contains(el8))
        self.assertFalse(pnode.contains(self.n.docEl))
        self.assertFalse(self.n.docEl.contains(pnode))  # Unconnected

        self.assertIs(el8.getRootNode(), self.n.doc)

        self.assertFalse(pnode.isSameNode(el8))
        self.assertTrue(pnode.isSameNode(pnode))

        #pnode.lookupNamespaceURI(uri)
        #pnode.lookupPrefix(prefix)

        self.n.docEl.normalize()

        el = self.n.docEl.childNodes[7]
        priorLen = len(el)
        for _ in range(10):
            n = self.n.doc.createElement(self.dc.p_name)
            el.prependChild(n)
        self.assertEqual(len(el), priorLen+10)

        #pnode.insertBefore(newNode, ch)
        #pnode.removeChild(oldChild)
        #pnode.replaceChild(newChild, oldChild)

        #pnode.unlink(keepAttrs=False)

        #pnode.toxml()
        #pnode.toprettyxml()

        # pnode is still detached
        self.assertFalse(pnode.isConnected)
        self.assertEqual(pnode.getChildIndex(), None)

        nch = len(pnode)
        x = self.dc.p_name
        self.assertEqual(pnode.count(x), 0)
        #self.assertRaises(ValueError, pnode.index, x, 1, 2)
        newChild = self.n.doc.createElement(self.dc.new_name)
        pnode.append(newChild)
        self.assertEqual(len(pnode), nch+1)

        newChild2 = self.n.doc.createElement(self.dc.new_name)
        pnode.insert(999, newChild2)
        self.assertEqual(len(pnode), nch+2)
        self.assertEqual(newChild2.parentNode, pnode)
        self.assertEqual(newChild2.getChildIndex(), len(pnode)-1)
        pnode.pop()
        self.assertEqual(len(pnode), nch+1)

        #pnode.remove(x)
        #pnode.reverse()
        #pnode.sort("a", reverse=False)
        #pnode._isOfValue(x)
        #pnode.clear()
        #pnode.checkNode()  # Node


###############################################################################
#
class test_Node(unittest.TestCase):
    def setUp(self):
        madeDocObj = makeTestDocEachMethod(dc=K)
        self.dc = K
        self.n = madeDocObj.n

    def tests(self):
        el8 = self.n.docEl.childNodes[8]
        node = Node(ownerDocument=None, nodeName="notAnElement")

        #self.assertRaises(IndexError, self.n.docEl.childNodes[200])
        #self.assertRaises(IndexError, self.n.docEl.childNodes[-200])

        if (0):
            self.assertEqual(None, node.prefix)
            #self.assertEqual("notAnElement", node.localName)
            self.assertEqual(None, node.namespaceURI)
        else:
            self.assertEqual(None, node.prefix)
            self.assertEqual(None, node.localName)
            self.assertEqual(None, node.namespaceURI)

        self.assertFalse(node.isConnected)

        self.assertEqual(None, node.nextSibling)
        self.assertEqual(None, node.previousSibling)
        self.assertEqual(None, node.previous)
        self.assertEqual(None, node.next)
        self.assertFalse(node.childNodes)  # None or [] is ok.
        self.assertEqual(None, node.firstChild)
        self.assertEqual(None, node.lastChild)

        self.assertEqual(None, node.nodeValue)
        #node.nodeValue(newData:str="")
        self.assertFalse(node.textContent)
        #node.textContent(newData:str)

        self.assertFalse(el8.isEqualNode(node))
        self.assertFalse(el8.isSameNode(node))

        # Not in any ownerDocument, so can't test position.
        #self.assertEqual(node.compareDocumentPosition(el8), -1)
        #self.assertEqual(node.compareDocumentPosition(node), 0)
        #self.assertEqual(node.compareDocumentPosition(el8), -1)

        self.assertFalse(node.contains(node))
        self.assertFalse(node.contains(el8))
        self.assertFalse(node.contains(self.n.docEl))
        self.assertFalse(self.n.docEl.contains(node))  # Unconnected

        self.assertIs(el8.getRootNode(), self.n.doc)

        self.assertTrue(node.hasAttributes)
        self.assertFalse(node.isSameNode(el8))
        self.assertTrue(node.isSameNode(node))

        #node.lookupNamespaceURI(uri)
        #node.lookupPrefix(prefix)

        self.n.docEl.normalize()

        el = self.n.docEl.childNodes[7]
        priorLen = len(el)
        for i in range(10):
            n = self.n.doc.createElement(self.dc.p_name)
            el.prependChild(n)
        self.assertEqual(len(el), priorLen+10)

        self.assertFalse(node.hasChildNodes())
        #node.insertBefore(newNode, ch)
        #node.removeChild(oldChild)
        #node.replaceChild(newChild, oldChild)

        #node.unlink(keepAttrs=False)

        #node.toxml()
        #node.toprettyxml()

        # node is still detached
        self.assertFalse(node.isConnected)
        self.assertEqual(node.rightmost, None)
        self.assertEqual(node.getChildIndex(), None)

        #node.moveToOtherDocument(otherDocument)

        self.assertEqual(node.getUserData(self.dc.udk1_name), None)
        node.setUserData(self.dc.udk1_name, self.dc.udk1_value)
        self.assertEqual(node.getUserData(self.dc.udk1_name), self.dc.udk1_value)

        #self.assertEqual(node.collectAllXml(), stag+etag)
        self.assertEqual(node.getNodeSteps(), None)
        self.assertEqual(node.getNodePath(), None)
        self.assertRaises(HIERARCHY_REQUEST_ERR, node.removeNode)

        nch = len(node)
        x = self.dc.p_name
        i = 4
        self.assertEqual(node.count(x), 0)
        #self.assertRaises(ValueError, node.index, x, 1, 2)
        newChild = self.n.doc.createElement(self.dc.new_name)
        node.append(newChild)
        self.assertEqual(len(node), nch+1)
        node.pop()
        self.assertEqual(len(node), nch)
        newChild2 = self.n.doc.createElement(self.dc.new_name)
        node.insert(i, newChild2)
        self.assertEqual(len(node), nch+1)
        #node.remove(x)
        #node.reverse()
        #node.sort("a", reverse=False)
        #node._isOfValue(x)
        #node.clear()
        node.checkNode()  # Node


class test_NodeType_Predicates(unittest.TestCase):
    def setUp(self):
        madeDocObj = makeTestDocEachMethod(dc=K)
        self.dc = K
        self.n = madeDocObj.n

    def testSet(self):
        el = self.n.docEl.childNodes[5]
        for ch in self.n.docEl.childNodes:
            if (ch.nodeType == NodeType.UNSPECIFIED_NODE):
                self.allPreds(ch, [ ])
            elif (ch.nodeType == NodeType.ELEMENT_NODE):
                self.allPreds(ch, [ el.isElement ])
            elif (ch.nodeType == NodeType.ATTRIBUTE_NODE):
                self.allPreds(ch, [ el.isAttribute ])
            elif (ch.nodeType == NodeType.TEXT_NODE):
                self.allPreds(ch, [ el.isTest ])
            elif (ch.nodeType == NodeType.CDATA_SECTION_NODE):
                self.allPreds(ch, [ el.isCData ])
            elif (ch.nodeType == NodeType.ENTITY_REFERENCE_NODE):
                self.allPreds(ch, [ el.isEntRef ])
            elif (ch.nodeType == NodeType.PROCESSING_INSTRUCTION_NODE):
                self.allPreds(ch, [ el.isPI ])
            elif (ch.nodeType == NodeType.COMMENT_NODE):
                self.allPreds(ch, [ el.isComment ])
            elif (ch.nodeType == NodeType.DOCUMENT_NODE):
                self.allPreds(ch, [ el.isDocument ])
            elif (ch.nodeType == NodeType.DOCUMENT_TYPE_NODE):
                self.allPreds(ch, [ el.isDocumentType ])
            elif (ch.nodeType == NodeType.DOCUMENT_FRAGMENT_NODE):
                self.allPreds(ch, [ el.isFragment ])
            elif (ch.nodeType == NodeType.NOTATION_NODE):
                self.allPreds(ch, [ el.isNotation ])
            else:
                assert ValueError, "Unexpected nodeType %d." % (ch.nodeType)

    def allPreds(self, el, ok:List):
        self.assertEqual(el.isElement,   el.isElement in ok)
        self.assertEqual(el.isAttribute, el.isAttribute in ok)
        self.assertEqual(el.isText,      el.isText in ok)
        self.assertEqual(el.isCDATA,     el.isCDATA in ok)
        self.assertEqual(el.isEntRef,    el.isEntRef in ok)
        self.assertEqual(el.isPI,        el.isPI in ok)
        self.assertEqual(el.isComment,   el.isComment in ok)
        self.assertEqual(el.isDocument,  el.isDocument in ok)
        self.assertEqual(el.isDocumentType, el.isDocumentType in ok)
        self.assertEqual(el.isFragment,  el.isFragment in ok)
        self.assertEqual(el.isNotation,  el.isNotation in ok)


###############################################################################
#
class test_Document(unittest.TestCase):
    def setUp(self):
        madeDocObj = makeTestDocEachMethod(dc=K)
        self.dc = K
        self.n = madeDocObj.n

    def tests(self):
        theDoc = self.n.doc
        self.assertEqual(theDoc.charset, "utf-8")
        #self.assertTrue(theDoc.contentType)
        self.assertTrue(theDoc.documentElement.isElement)
        self.assertTrue(XStr.isXmlQName(theDoc.documentElement.nodeName))
        #self.assertEqual(None, theDoc.documentURI)
        #self.assertEqual(None, theDoc.domConfig)
        self.assertEqual("utf-8", theDoc.inputEncoding)
        #theDoc.getXmlDcl(encoding:str="utf-8", standalone:bool=None)
        #theDoc.buildIdIndex()
        #self.assertEqual(len(theDoc.IdIndex), 0)


###############################################################################
#
class test_Element(unittest.TestCase):
    def setUp(self):
        madeDocObj = makeTestDocEachMethod(dc=K)
        self.dc = K
        self.n = madeDocObj.n

    def tests(self):
        # an = self.dc.attr1_name
        # av = "myClass big wow"
        # ns = self.dc.ns_uri
        # anode = Attr(an, av)

        el0 = self.n.docEl.childNodes[0]
        el5 = self.n.docEl.childNodes[5]
        el8 = self.n.docEl.childNodes[8]
        zzz = self.n.doc.createTextNode("xyzzy")
        el8.appendChild(zzz)

        self.assertTrue(el0.isElement)

        cl = el5.cloneNode(deep=True)
        self.assertTrue(cl.isElement)
        DBG.dumpNode(cl, msg="post-clione")
        self.assertTrue(cl.isEqualNode(el5))
        self.assertFalse(cl.isSameNode(el8))

        self.assertEqual(el5.compareDocumentPosition(el8), -1)
        self.assertEqual(el5.compareDocumentPosition(el5), 0)
        self.assertEqual(el5.compareDocumentPosition(el0), +1)

        self.assertFalse(el0.contains(el5))
        self.assertTrue(self.n.docEl.contains(el8))
        self.assertTrue(self.n.docEl.contains(zzz))  # DOM counts indirects
        self.assertFalse(el5.contains(self.n.docEl))

        self.assertFalse(el0.__contains__(el5))
        self.assertTrue(self.n.docEl.__contains__(el8))
        self.assertFalse(self.n.docEl.__contains__(zzz))  # But Python doesn't.

        xel = self.n.doc.createElement("xml:predef")
        xel.setAttribute("xmlns:foo", "w3example.org/made-up")

    def test_attributes(self):
        an = self.dc.attr1_name
        av = "myClass big wow"
        ns = self.dc.ns_uri
        anode = Attr(an, av)

        #el0 = self.n.docEl.childNodes[0]
        el5 = self.n.docEl.childNodes[5]
        el8 = self.n.docEl.childNodes[8]
        zzz = self.n.doc.createTextNode("xyzzy")
        el8.appendChild(zzz)

        # Attributes / plain
        el5.setAttribute(an, av)
        self.assertTrue(el5.hasAttribute(an))
        self.assertEqual(el5.getAttribute(an), av)

        DBG.dumpNode(el5, msg=f"Before deleting attr '{an}'.")
        self.assertEqual(el5.removeAttribute(an), None)
        DBG.dumpNode(el5, msg="After (attr: %s)" % (repr(el5.attributes)))
        self.assertFalse(el5.hasAttribute(an))

        self.assertEqual(el5.getAttribute(an), None)
        el5.removeAttribute(an)  # No exception please.

        # Attributes / Node
        el5.setAttributeNode(anode)
        self.assertTrue(el5.hasAttribute(an))
        self.assertEqual(el5.getAttributeNode(an), anode)
        el5.removeAttributeNode(anode)
        self.assertFalse(el5.hasAttribute(an))
        self.assertRaises(NOT_FOUND_ERR, el5.getAttributeNode, anode)
        import pudb; pudb.set_trace()
        self.assertRaises(NOT_FOUND_ERR, el5.removeAttributeNode, anode)

        # Attributes / NS
        el5.setAttributeNS(ns, an, av)
        self.assertEqual(el5.getAttributeNS(ns, an), av)
        el5.removeAttributeNS(ns, an)
        self.assertFalse(el5.hasAttributeNS(ns, an))
        self.assertEqual(el5.getAttributeNS(ns, an), None)
        self.assertRaises(NOT_FOUND_ERR, el5.removeAttributeNS, ns, an)

        # Attributes / NodeNS
        el5.setAttributeNodeNS(ns, anode)
        self.assertEqual(el5.getAttributeNodeNS(ns, an), anode)
        el5.removeAttributeNode(anode)
        self.assertFalse(el5.hasAttributeNS(ns, an))
        self.assertEqual(el5.getAttributeNodeNS(ns, an), None)

        el5.setAttribute("att1", "val1")
        val2 = "Some longer -- maybe real! long, value."
        el5.setAttribute("att2.3", val2)

    def test_serializers(self):
        #an = self.dc.attr1_name
        #av = "myClass big wow"
        #ns = self.dc.ns_uri
        #anode = Attr(an, av)

        #el0 = self.n.docEl.childNodes[0]
        el5 = self.n.docEl.childNodes[5]
        el8 = self.n.docEl.childNodes[8]
        zzz = self.n.doc.createTextNode("xyzzy")
        el8.appendChild(zzz)

        # TODO Deal with attr order....
        stag = el5.startTag
        self.assertEqual(stag, """<para class="important" n="5">""")
        etag = el5.endTag
        self.assertEqual(etag, "</para>")
        self.assertEqual(el5.innerXML, "aardvark")
        self.assertEqual(el5.outerXML, stag + el5.innerXML + etag)

        el5.outerXML = self.dc.outer
        self.assertEqual(len(el5.childNodes), 1)
        self.assertTrue(el5.childNodes[0].isText)

        el5.innerXML = "hello"
        DBG.dumpNode(el5, msg=f"after innerXML set, len {len(el5)}")
        self.assertEqual(len(el5.childNodes[0].data), 5)
        self.assertEqual(el5.startTag, "<%s>" % (self.dc.p_name))

        #el5._startTag(sortAttrs=True, empty=False)
        self.assertEqual(el5.endTag, f"</{self.dc.p_name}>")
        self.assertTrue(el5.firstElementChild)

        el5.getElementsByTagName("p")
        el5.getElementsByClassName("myClass")
        el5.getElementsByTagNameNS("p", "html")
        el5.insertAdjacentHTML('<p id="html_9">foo</p>')

    def test_fetchers(self):
        #an = self.dc.attr1_name
        #av = "myClass big wow"
        #ns = self.dc.ns_uri
        #anode = Attr(an, av)

        #el0 = self.n.docEl.childNodes[0]
        #el5 = self.n.docEl.childNodes[5]
        el8 = self.n.docEl.childNodes[8]
        zzz = self.n.doc.createTextNode("xyzzy")
        el8.appendChild(zzz)

        # TODO Add fetcher tests
        #
        #append
        #extend
        #el5.matches()
        #el5.querySelector()
        #el5.querySelectorAll()

    def testListStuff(self):
        nch = 10
        el = self.n.docEl
        self.assertEqual(len(el), nch)
        cname = self.dc.p_name
        i = 4
        self.assertEqual(el.count(cname), nch)
        self.assertEqual(el.count("xyzzy"), 0)
        self.assertEqual(el.index(cname, 1, 2), 1)

        newChild = self.n.doc.createElement(self.dc.new_name)
        el.append(newChild)
        self.assertEqual(len(el), nch+1)
        self.assertEqual(el.index(self.dc.new_name), nch)
        el.remove(self.dc.new_name)
        self.assertEqual(len(el), nch)

        self.assertTrue(el[5]._isOfValue(cname))

        rnodelist = el.reversed()
        self.assertEqual(type(rnodelist), NodeList)
        for i, node in enumerate(rnodelist):
            self.assertTrue(node.isSameNode(el[nch-i-1]))

        el.reverse()
        for i, node in enumerate(rnodelist):
            self.assertTrue(node.isSameNode(el[i]))

    def test_clear(self):
        nch = 10
        el = self.n.docEl
        self.assertEqual(len(el), nch)

        el.checkNode()
        el.clear()
        self.assertEqual(len(el), 0)
        self.assertRaises(HIERARCHY_REQUEST_ERR, el.insert, 1, "Just a string")
        newb = self.n.doc.createComment("no comment.")
        el.insert(1, newb)
        self.assertEqual(len(el), 1)
        el.pop()
        self.assertEqual(len(el), 0)
        self.assertFalse(newb.isConnected)


###############################################################################
#
class test_Text(unittest.TestCase):
    def setUp(self):
        madeDocObj = makeTestDocEachMethod(dc=K)
        self.dc = K
        self.n = madeDocObj.n

    def tests(self):
        txText = "Lorem ipsum and all that\u2026stuff."
        tx = self.n.doc.createTextNode(txText)
        el = self.n.docEl.childNodes[5]
        el.appendChild(tx)

        tx.checkNode()

        txNow = el.lastChild
        self.assertTrue(tx is txNow)

        self.assertTrue(tx.isText)
        self.assertEqual(tx.nodeValue, txText)
        self.assertEqual(tx.outerXML, txText)
        self.assertEqual(tx.innerXML, txText)
        #txTextJ = BaseDom.escapeJsonStr(txText)
        #self.assertEqual(tx.outerJSON(), f'"{txTextJ}"')
        self.assertEqual(tx.tostring(), txText)

        tx2 = tx.cloneNode()
        self.assertTrue(tx2.isEqualNode(tx))
        self.assertFalse(tx2.isSameNode(tx))
        tx2.data += "TTT"
        self.assertFalse(tx2.isEqualNode(tx))

        tx.nodeValue = ""
        self.assertEqual(tx.nodeValue, "")


###############################################################################
#
class test_CDATASection(unittest.TestCase):
    def setUp(self):
        madeDocObj = makeTestDocEachMethod(dc=K)
        self.dc = K
        self.n = madeDocObj.n

    def tests(self):
        cdText = """I am <a> CDATA thingie & "should" work."""
        cd = self.n.doc.createCDATASection(cdText)
        el = self.n.docEl.childNodes[5]
        el.appendChild(cd)
        #DBG.dumpNode(el, msg="test_CDATASection, nodeValue: ")

        cd.checkNode()

        self.assertTrue(cd.isCDATA)
        self.assertEqual(cd.nodeValue, cdText)
        self.assertEqual(cd.outerXML, f"<![CDATA[{cdText}]]>")
        self.assertEqual(cd.innerXML, cdText)
        #cdTextJ = BaseDom.escapeJsonStr(cdText)
        #self.assertEqual(cd.outerJSON(indent="  "),
        #    f"""[ \{"#name":"#cdata"\}, "{cdTextJ}" ]""")
        self.assertEqual(cd.tostring(), f"<![CDATA[{cdText}]]>")

        cd.nodeValue = ""
        self.assertEqual(cd.nodeValue, "")


###############################################################################
#
class test_ProcessingInstruction(unittest.TestCase):
    def setUp(self):
        madeDocObj = makeTestDocEachMethod(dc=K)
        self.dc = K
        self.n = madeDocObj.n

    def tests(self):
        piTarget = "troff"
        piData = "margin:12pt, skip:<12>, color=chartreuse"
        pi = self.n.doc.createProcessingInstruction(piTarget, piData)
        el = self.n.docEl.childNodes[5]
        el.appendChild(pi)

        pi.checkNode()

        self.assertTrue(pi.isProcessingInstruction)
        self.assertTrue(pi.isPI)
        self.assertEqual(pi.nodeValue, piData)
        self.assertEqual(pi.outerXML, f"<?{piTarget} {piData}?>")
        self.assertEqual(pi.innerXML, piData)
        #piDataJ = BaseDom.escapeJsonStr(piData)
        #self.assertEqual(pi.outerJSON(indent="  "),
        #    """[ \{"#name":"#pi", "#target":"{piTarget}"\}, "{piDataJ}" ]""")
        self.assertEqual(pi.tostring(), f"<?{piTarget} {piData}?>")

        pi2 = pi.cloneNode()
        self.assertTrue(pi2.isEqualNode(pi))
        self.assertFalse(pi2.isSameNode(pi))
        pi2.target += "\u03d6"  # pi
        self.assertFalse(pi2.isEqualNode(pi))
        pi2.target = pi2.target[0:-1]
        self.assertTrue(pi2.isEqualNode(pi))
        pi2.data += "\u03d6"  # pi
        self.assertFalse(pi2.isEqualNode(pi))

        pi.nodeValue = ""
        self.assertEqual(pi.data, "")


###############################################################################
#
class test_Comment(unittest.TestCase):
    def setUp(self):
        madeDocObj = makeTestDocEachMethod(dc=K)
        self.dc = K
        self.n = madeDocObj.n

    def tests(self):
        comText = "The proof won't fit in the margin."
        com = self.n.doc.createComment(comText)
        self.n.docEl.appendChild(com)
        com.checkNode()

        com2 = com.cloneNode(deep=False)
        com3 = com.cloneNode(deep=True)
        com3.data += " Or will it?"
        self.assertTrue(com.isEqualNode(com2))
        self.assertFalse(com.isEqualNode(com3))
        self.assertFalse(com.isEqualNode(self.n.docEl))

        self.assertEqual(com.nodeValue, comText)
        self.assertEqual(com.outerXML, f"<!--{comText}-->")
        self.assertEqual(com.innerXML, comText)
        self.assertEqual(com.outerJSON(indent="  "),
            """[ { "#name":"#comment", "#data":"%s" } ]""" % (comText))
        self.assertEqual(com.tostring(),
            f"<!--{comText}-->")

        com.nodeValue = ""
        self.assertEqual(com.outerXML, "<!---->")
        self.assertEqual(com.innerXML, "")


###############################################################################
#
class test_EntityReference(unittest.TestCase):
    """TODO What else to support for test_EntityReference, if anything?
    """
    def setUp(self):
        madeDocObj = makeTestDocEachMethod(dc=K)
        self.dc = K
        self.n = madeDocObj.n

    def tests(self):
        sys.stderr.write("\n******* EntRef tests skipped *******\n")
        return
        #er = self.n.doc.createEntityReference("bull", "\u2022")
        #el = self.n.docEl.childNodes[5]
        #el.appendChild(er)
        #self.assertTrue(er.isEntRef)


###############################################################################
#
class test_Notation(unittest.TestCase):  # Meh
    def setUp(self):
        madeDocObj = makeTestDocEachMethod(dc=K)
        self.dc = K
        self.n = madeDocObj.n

    def tests(self):
        sys.stderr.write("\n******* Notation tests skipped *******\n")
        return
        #nn = self.n.doc.createNotation(
        #    "nname", publicId="-//foo", systemId="http://example.com/png")
        #el = self.n.docEl.childNodes[5]
        #el.setAttribute("notn", nn)


###############################################################################
#
class test_Attr(unittest.TestCase):
    def setUp(self):
        madeDocObj = makeTestDocEachMethod(dc=K)
        self.dc = K
        self.n = madeDocObj.n

    attrExpr = r'\w+="[^"]*"$'

    def tests(self):
        aname = "class"
        el = self.n.docEl.childNodes[2]
        aval = el.getAttribute(aname)
        self.assertEqual(aval, "important")

        anode1 = self.n.docEl.childNodes[2].getAttributeNode(aname)
        anode2 = self.n.docEl.childNodes[5].getAttributeNode(aname)
        self.assertEqual(anode1.nodeName, aname)
        self.assertEqual(anode2.nodeName, aname)

        #el.compareDocumentPosition(other)
        self.assertTrue(anode1.isEqualNode(anode2))
        anode3 = anode2.cloneNode()
        eqBit = anode1.isEqualNode(anode3)
        if (not eqBit):
            DBG.dumpNode(anode1, msg="anode 1 v. 3:")
            DBG.dumpNode(anode3)
        self.assertTrue(eqBit)

        #self.assertTrue(attrExpr, attr1.outerXML)
        #self.assertTrue(attrExpr, attr1.innerXML)
        #self.assertTrue(re.match(attrExpr, attr1.tostring()))
        #el.outerJSON(indent="  ", depth=0)
        #el.attrToJson()

        if (0):
            self.assertRaises(HIERARCHY_REQUEST_ERR, anode3.getChildIndex)
            self.assertRaises(HIERARCHY_REQUEST_ERR, anode3.previousSibling)
            self.assertRaises(HIERARCHY_REQUEST_ERR, anode3.nextSibling)
            self.assertRaises(HIERARCHY_REQUEST_ERR, anode3.previous)
            self.assertRaises(HIERARCHY_REQUEST_ERR, anode3.next)
            self.assertRaises(HIERARCHY_REQUEST_ERR, anode3.firstChild)
            self.assertRaises(HIERARCHY_REQUEST_ERR, anode3.lastChild)
            newChild = self.n.doc.createElement("newb")
            self.assertRaises(HIERARCHY_REQUEST_ERR, anode3.appendChild, newChild)
            self.assertRaises(HIERARCHY_REQUEST_ERR, anode3.insertBefore, newChild, el)

        DBG.dumpNode(anode2, msg="anode2")
        anode2.checkNode()


###############################################################################
#
class test_NamedNodeMap(unittest.TestCase):
    def setUp(self):
        madeDocObj = makeTestDocEachMethod(dc=K)
        self.dc = K
        self.n = madeDocObj.n

    def tests(self):
        nnm = NamedNodeMap()
        self.assertEqual(nnm.getNamedItem("class"), None)

        nnm.setNamedItem("class")
        anAttr = nnm.getNamedItem("class")
        self.assertTrue(isinstance(anAttr, Attr))
        self.assertEqual(anAttr.nodeName, "class")
        self.assertEqual(anAttr.value, "classy")

        self.assertEqual(nnm.tostring(), "class=\"classy\"")
        nnm.removeNamedItem("class")
        self.assertRaises(KeyError, nnm.getNamedItem, "class")
        self.assertRaises(IndexError, nnm.item, 3)
        nnm.clear()
        self.assertEqual(nnm.tostring(), "")


###############################################################################
#
class test_Generators(unittest.TestCase):
    def setUp(self):
        madeDocObj = makeTestDocEachMethod(dc=K)
        self.dc = K
        self.n = madeDocObj.n

    def tests(self):
        nNodes = 0
        nodeTypeCounts = defaultdict(int)
        for node in self.n.docEl.eachNode():
            #DBG.msg("nodeType {node.nodeType}")
            nNodes += 1
            nodeTypeCounts[node.nodeName] += 1

        #DBG.msg("nodesTypes: total %d, distinct %d." % (nNodes, len(nodeTypeCounts)))
        #DBG.dumpNode(self.n.docEl, msg="Tree to generate from:")

        self.assertEqual(nNodes, 21)

        nexpected = {
            "article":   1,
            "para":     10,
            "#text":    10,
            "#pi":       0,
            "#comment":  0,
            "#cdata":    0,
        }
        for k in nexpected:
            nfound = nodeTypeCounts[k] if k in nodeTypeCounts else 0
            if (nfound != nexpected[k]):
                DBG.msg(f"Expect {nexpected[k]} of '{k}'. but found {nfound}.")
                self.assertEqual(nfound, nexpected[k])
        self.assertTrue(set(nodeTypeCounts.keys()), set(nexpected.keys()))


if __name__ == '__main__':
    unittest.main()
