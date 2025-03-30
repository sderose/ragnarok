#!/usr/bin/env python3
#
#pylint: disable=W0201, C2801, W0401, W0614, W0212
#
import sys
import unittest
from collections import defaultdict
from typing import List, Tuple, Callable

from basedomtypes import *
from xmlstrings import XmlStrings as XStr
from saxplayer import SaxEvent

from basedom import DOMImplementation, getDOMImplementation
from basedom import PlainNode, Node, Document, Element
from basedom import Attr, NamedNodeMap, NodeList, RelPosition

from makeTestDoc import (makeTestDoc0, makeTestDoc2, makeTestDocEachMethod,
    DAT, DAT_K, DBG)

descr = """
To Do:

* Add tests for the CharacterData methods.
"""


###############################################################################
#
class TestExceptions(unittest.TestCase):
    """This only tests that all the whatwg-defined ones exist,
    not whether there are extras, and not the legacy DOM ones.
    """
    def setUp(self):
        madeDocObj = makeTestDocEachMethod(dc=DAT_K)
        self.n = madeDocObj.n

    def isEx(self, theClass:type):
        self.assertIsInstance(theClass(), Exception)

    def tests(self):
        self.isEx(DOMException)
        self.isEx(RangeError)
        self.isEx(IndexSizeError)
        self.isEx(HierarchyRequestError)
        self.isEx(WrongDocumentError)
        self.isEx(InvalidCharacterError)
        self.isEx(NoModificationAllowedError)
        self.isEx(NotFoundError)
        self.isEx(NotSupportedError)
        self.isEx(InUseAttributeError)
        self.isEx(InvalidStateError)
        self.isEx(InvalidModificationError)
        self.isEx(NamespaceError)
        self.isEx(InvalidAccessError)
        self.isEx(TypeMismatchError)
        self.isEx(SecurityError)
        self.isEx(NetworkError)
        self.isEx(AbortError)
        self.isEx(QuotaExceededError)
        self.isEx(InvalidNodeTypeError)
        self.isEx(DataCloneError)
        self.isEx(EncodingError)
        self.isEx(NotReadableError)
        self.isEx(UnknownError)
        self.isEx(ConstraintError)
        self.isEx(DataError)
        self.isEx(TransactionInactiveError)
        self.isEx(ReadOnlyError)
        self.isEx(VersionError)
        self.isEx(OperationError)
        self.isEx(NotAllowedError)
        self.isEx(OptOutError)


###############################################################################
#
class testNodeType(unittest.TestCase):
    def setUp(self):
        madeDocObj = makeTestDocEachMethod(dc=DAT_K)
        self.n = madeDocObj.n

    def tests(self):
        from xml.dom.minidom import Node as MN

        for n in range(1, 13):
            self.assertTrue(NodeType.okNodeType(NodeType(n), die=False))
            self.assertTrue(NodeType.okNodeType(NodeType(n), die=False))
            self.assertTrue(NodeType.tostring(NodeType(n)))

        AEQ = self.assertEqual
        AEQ(Node.ELEMENT_NODE,            NodeType(MN.ELEMENT_NODE).value)
        AEQ(Node.ATTRIBUTE_NODE,          NodeType(MN.ATTRIBUTE_NODE).value)
        AEQ(Node.TEXT_NODE,               NodeType(MN.TEXT_NODE).value)
        AEQ(Node.CDATA_SECTION_NODE,      NodeType(MN.CDATA_SECTION_NODE).value)
        AEQ(Node.ENTITY_REFERENCE_NODE,   NodeType(MN.ENTITY_REFERENCE_NODE).value)
        AEQ(Node.ENTITY_NODE,             NodeType(MN.ENTITY_NODE).value)
        AEQ(Node.PROCESSING_INSTRUCTION_NODE,
            NodeType(MN.PROCESSING_INSTRUCTION_NODE).value)
        AEQ(Node.COMMENT_NODE,            NodeType(MN.COMMENT_NODE).value)
        AEQ(Node.DOCUMENT_NODE,           NodeType(MN.DOCUMENT_NODE).value)
        AEQ(Node.DOCUMENT_TYPE_NODE,      NodeType(MN.DOCUMENT_TYPE_NODE).value)
        AEQ(Node.DOCUMENT_FRAGMENT_NODE,  NodeType(MN.DOCUMENT_FRAGMENT_NODE).value)
        AEQ(Node.NOTATION_NODE,           NodeType(MN.NOTATION_NODE).value)


###############################################################################
#
class TestDOMImplementation(unittest.TestCase):
    def setUp(self):
        madeDocObj = makeTestDoc2()
        self.n = madeDocObj.n

    def testBasics(self):
        domImpl = getDOMImplementation("someName")
        with self.assertRaises(NSuppE):
            domImpl.registerDOMImplementation("someName", factory=None)
        self.assertIsInstance(domImpl.getImplementation(), DOMImplementation)

    def tests(self):
        x = self.n.impl.createDocument("exampl", "html", None)
        self.assertTrue(x.isDocument)

        x = self.n.impl.createDocumentType("html", None, "c:\\foo.dtd")
        self.assertTrue(x.isDocumentType)

        with self.assertRaises(NSuppE):
            x = self.n.impl.registerDOMImplementation("BaseDom", factory=None)

        #x = self.n.impl.parse("/tmp/x.xml", parser=None, bufsize=1024)
        #self.assertTrue(x.isDocument)

        x = self.n.impl.parse_string(
            s="<article id='a1'>foo></article>", parser=None)
        self.assertTrue(x.isDocument)


###############################################################################
#
class testNodeList(unittest.TestCase):
    def setUp(self):
        madeDocObj = makeTestDocEachMethod(dc=DAT_K)
        self.n = madeDocObj.n

        madeDocObj.addChildren(self.n.docEl, n=20)

        self.nl1 = NodeList(self.n.docEl[0:-1:2])
        self.nl2 = NodeList(self.n.docEl[0:-1:3])

        for ch in self.n.docEl.childNodes: self.assertTrue(ch.isElement)
        for ch in self.nl1: self.assertTrue(ch.isElement)
        for ch in self.nl2: self.assertTrue(ch.isElement)

    def tests(self):
        docEl = self.n.docEl
        origLen = len(docEl.childNodes)
        nl = NodeList()
        for n in reversed(docEl.childNodes):
            nl.append(n)
        self.assertEqual(len(nl), origLen)

        for n in range(len(nl)):
            self.assertEqual(nl.item(n), docEl.childNodes[origLen-n-1])

        #with self.assertRaises(NotSupportedError): nl.__mul__(2)
        #with self.assertRaises(NotSupportedError): nl.__rmul__(2)


###############################################################################
#
class testPlainNode(unittest.TestCase):
    def setUp(self):
        madeDocObj = makeTestDocEachMethod(dc=DAT_K)
        self.dc = DAT_K
        self.n = madeDocObj.n

    def tests(self):
        docEl = self.n.docEl
        el8 = docEl.childNodes[8]
        pnode = PlainNode(ownerDocument=None, nodeName="aPlainNodeToTry")

        with self.assertRaises(AttributeError):
            pnode.__contains__(12)

        #with self.assertRaises(IndexError): docEl.childNodes[200])  # TODO
        #with self.assertRaises(IndexError): docEl.childNodes[-200])

        if (0):
            self.assertIsNone(pnode.prefix)
            #self.assertEqual("notAnElement", pnode.localName)
            self.assertIsNone(pnode.namespaceURI)
        else:
            self.assertIsNone(pnode.prefix)
            self.assertIsNone(pnode.localName)
            self.assertIsNone(pnode.namespaceURI)

        self.assertFalse(pnode.isConnected)

        self.assertIsNone(pnode.nextSibling)
        self.assertIsNone(pnode.previousSibling)
        self.assertFalse(pnode.childNodes)  # None or [] is ok.

        self.assertIsNone(pnode.nodeValue)

        #self.assertFalse(el8.isEqualNode(pnode))
        self.assertFalse(el8.isSameNode(pnode))

        self.assertFalse(pnode.contains(pnode))
        self.assertFalse(pnode.contains(el8))
        self.assertFalse(pnode.contains(docEl))
        self.assertFalse(docEl.contains(pnode))  # Unconnected

        self.assertIs(el8.getRootNode(), self.n.doc)

        self.assertFalse(pnode.isSameNode(el8))
        self.assertTrue(pnode.isSameNode(pnode))

        #pnode.lookupNamespaceURI(uri)
        #pnode.lookupPrefix(prefix)

        docEl.normalize()

        el = docEl.childNodes[7]
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
        self.assertIsNone(pnode.getChildIndex())

        nch = len(pnode)
        x = self.dc.p_name
        self.assertEqual(pnode.count(x), 0)
        #with self.assertRaises(ValueError): pnode.index, x, 1, 2)
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
class testNode(unittest.TestCase):
    def setUp(self):
        madeDocObj = makeTestDocEachMethod(dc=DAT_K)
        self.dc = DAT_K
        self.n = madeDocObj.n

    def testsNode(self):
        docEl = self.n.docEl
        el8 = docEl.childNodes[8]
        node = Node(ownerDocument=None, nodeName="notAnElement")

        #with self.assertRaises(IndexError): docEl.childNodes[200]
        #with self.assertRaises(IndexError): docEl.childNodes[-200]

        self.assertIsNone(node.prefix)
        self.assertIsNone(node.localName)
        self.assertIsNone(node.namespaceURI)

        self.assertFalse(node.isConnected)

        self.assertIsNone(node.nextSibling)
        self.assertIsNone(node.previousSibling)
        self.assertIsNone(node.previous)
        self.assertIsNone(node.next)
        self.assertFalse(node.hasChildNodes)
        self.assertIsNone(node.firstChild)
        self.assertIsNone(node.lastChild)
        self.assertIsNone(node.nodeValue)
        self.assertIsNone(node.textContent)
        with self.assertRaises(NSuppE):
            node.textContent = "xyzzy"
        with self.assertRaises(NSuppE):
            _ = node.cloneNode()

        self.assertFalse(el8.isEqualNode(node))
        self.assertFalse(el8.isSameNode(node))
        self.assertFalse(el8.isEqualNode(None))
        with self.assertRaises(HReqE):
            el8.isEqualNode(561)

        # Not in any ownerDocument, so can't test position.
        #self.assertEqual(node.compareDocumentPosition(el8), -1)
        #self.assertEqual(node.compareDocumentPosition(node), 0)
        #self.assertEqual(node.compareDocumentPosition(el8), -1)

        self.assertFalse(node.contains(node))
        self.assertFalse(node.contains(el8))
        self.assertFalse(node.contains(docEl))
        self.assertFalse(docEl.contains(node))  # Unconnected

        self.assertIs(el8.getRootNode(), self.n.doc)

        self.assertFalse(node.hasAttributes())
        self.assertFalse(node.isSameNode(el8))
        self.assertTrue(node.isSameNode(node))

        #node.lookupNamespaceURI(uri)
        #node.lookupPrefix(prefix)

        docEl.normalize()

        el = docEl.childNodes[7]
        priorLen = len(el)
        for _i in range(10):
            n = self.n.doc.createElement(self.dc.p_name)
            el.prependChild(n)
        self.assertEqual(len(el), priorLen+10)

        self.assertFalse(node.hasChildNodes)
        #node.insertBefore(newNode, ch)
        #node.removeChild(oldChild)
        #node.replaceChild(newChild, oldChild)

        #node.unlink(keepAttrs=False)

        #node.toxml()
        #node.toprettyxml()

        # node is still detached
        self.assertFalse(node.isConnected)
        self.assertIsNone(node.rightmost)
        self.assertIsNone(node.getChildIndex())
        self.assertTrue(bool(node))

        #node.moveToOtherDocument(otherDocument)

    def testsNode2(self):
        #docEl = self.n.docEl
        #el8 = docEl.childNodes[8]
        node = Node(ownerDocument=None, nodeName="notAnElement")

        self.assertIsNone(node.getUserData(self.dc.udk1_name))
        node.setUserData(self.dc.udk1_name, self.dc.udk1_value)
        node.checkNode()
        self.assertEqual(node.getUserData(self.dc.udk1_name), self.dc.udk1_value)

        with self.assertRaises(HierarchyRequestError): node.removeNode()

        nch = len(node)
        self.assertEqual(nch, 0)
        x = self.dc.p_name
        self.assertEqual(node.count(x), 0)
        #with self.assertRaises(ValueError): node.index(x, 1, 2)

    def testsNode3(self):
        #docEl = self.n.docEl
        #el8 = docEl.childNodes[8]
        node = Node(ownerDocument=None, nodeName="notAnElement")
        nch = 5
        for _x in range(nch):
            ch = Node(ownerDocument=None, nodeName="genericChildNode")
            node.append(ch)
        self.assertEqual(len(node), nch)
        node.pop()
        self.assertEqual(len(node), nch-1)
        node.checkNode(deep=False)

        first = node[0]
        node.reverse()
        self.assertEqual(len(node), nch-1)
        self.assertIs(node[-1], first)

        node.clear()
        self.assertEqual(len(node), 0)
        node.checkNode()  # Node
        self.assertTrue(bool(node))  # b/c it makes more sense

class testNodeType_Predicates(unittest.TestCase):
    def setUp(self):
        madeDocObj = makeTestDocEachMethod(dc=DAT_K)
        self.dc = DAT_K
        self.n = madeDocObj.n
        madeDocObj.addAllTypes(self.n.docEl, dc=DAT_K, n=1, specials=True)

    def tests(self):
        docEl = self.n.docEl
        el = docEl.childNodes[5]
        for ch in docEl.childNodes:
            if (ch.nodeType == Node.ABSTRACT_NODE):
                self.allPreds(ch, [ ])
            elif (ch.nodeType == Node.ELEMENT_NODE):
                self.allPreds(ch, [ Node.ELEMENT_NODE ])
            elif (ch.nodeType == Node.ATTRIBUTE_NODE):
                self.allPreds(ch, [ Node.ATTRIBUTE_NODE ])
            elif (ch.nodeType == Node.TEXT_NODE):
                self.allPreds(ch, [ Node.TEXT_NODE ])
            elif (ch.nodeType == Node.CDATA_SECTION_NODE):
                self.allPreds(ch, [ Node.CDATA_SECTION_NODE ])
            elif (ch.nodeType == Node.ENTITY_REFERENCE_NODE):
                self.allPreds(ch, [ Node.ENTITY_REFERENCE_NODE ])
            elif (ch.nodeType == Node.PROCESSING_INSTRUCTION_NODE):
                self.allPreds(ch, [ Node.PROCESSING_INSTRUCTION_NODE ])
            elif (ch.nodeType == Node.COMMENT_NODE):
                self.allPreds(ch, [ Node.COMMENT_NODE ])
            elif (ch.nodeType == Node.DOCUMENT_NODE):
                self.allPreds(ch, [ Node.DOCUMENT_NODE ])
            elif (ch.nodeType == Node.DOCUMENT_TYPE_NODE):
                self.allPreds(ch, [ el.isDocumentType ])
            elif (ch.nodeType == Node.DOCUMENT_FRAGMENT_NODE):
                self.allPreds(ch, [ Node.DOCUMENT_FRAGMENT_NODE ])
            elif (ch.nodeType == Node.NOTATION_NODE):
                self.allPreds(ch, [ el.isNotation ])
            else:
                assert ValueError, "Unexpected nodeType %d." % (ch.nodeType)

    def allPreds(self, el, ok:List):
        self.assertEqual(el.isElement,      Node.ELEMENT_NODE in ok)
        self.assertEqual(el.isAttribute,    Node.ATTRIBUTE_NODE in ok)
        self.assertEqual(el.isText,         Node.TEXT_NODE in ok)
        self.assertEqual(el.isCDATA,        Node.CDATA_SECTION_NODE in ok)
        self.assertEqual(el.isEntRef,       Node.ENTITY_REFERENCE_NODE in ok)
        self.assertEqual(el.isPI,           Node.PROCESSING_INSTRUCTION_NODE in ok)
        self.assertEqual(el.isComment,      Node.COMMENT_NODE in ok)
        self.assertEqual(el.isDocument,     Node.DOCUMENT_NODE in ok)
        self.assertEqual(el.isDocumentType, Node.DOCUMENT_TYPE_NODE in ok)
        self.assertEqual(el.isFragment,     Node.DOCUMENT_FRAGMENT_NODE in ok)
        self.assertEqual(el.isNotation,     Node.NOTATION_NODE in ok)


###############################################################################
#
class testDocument(unittest.TestCase):
    def setUp(self):
        madeDocObj = makeTestDocEachMethod(dc=DAT_K)
        self.dc = DAT_K
        self.n = madeDocObj.n

    def tests(self):
        theDoc = self.n.doc
        self.assertEqual(theDoc.charset, "utf-8")
        #self.assertTrue(theDoc.contentType)
        self.assertTrue(theDoc.documentElement.isElement)
        self.assertTrue(XStr.isXmlQName(theDoc.documentElement.nodeName))
        #self.assertIsNone(theDoc.documentURI)
        #self.assertIsNone(theDoc.domConfig)
        self.assertEqual("utf-8", theDoc.inputEncoding)
        #theDoc.getXmlDcl(encoding:str="utf-8", standalone:bool=None)
        #theDoc.buildIdIndex()
        #self.assertEqual(len(theDoc.IdIndex), 0)
        self.assertIsNone(theDoc.textContent)
        with self.assertRaises(NSuppE):
            theDoc.textContent = "xyzzy"
        self.assertTrue(bool(theDoc))  # b/c it makes more sense

    def test_nodeSteps(self):
        docEl = self.n.docEl
        el5 = docEl[5]
        newChild2 = self.n.doc.createElement(self.dc.new_name)

        el5.getNodeSteps()
        newChild2.getNodeSteps(wsn=False)

        nodeSteps0 = [ 1 ]
        self.assertTrue(docEl.useNodeSteps(nodeSteps0).isElement)

        nodeSteps1 = [ "not_an_ID", 1, 3 ]
        nodeSteps2 = [ 1, 3, 200 ]
        nodeSteps3 = [ -1 ]
        with self.assertRaises(HReqE):
            docEl.useNodeSteps(nodeSteps1)
            docEl.useNodeSteps(nodeSteps2)
            docEl.useNodeSteps(nodeSteps3)

    def testFilterScheme(self):
        self.n.doc.registerFilterScheme("all", lambda x: True)
        with self.assertRaises(ICharE):
            self.n.doc.registerFilterScheme("---", lambda x: True)


###############################################################################
#
class testElement(unittest.TestCase):
    def setUp(self):
        madeDocObj = makeTestDocEachMethod(dc=DAT_K)
        self.dc = DAT_K
        self.n = madeDocObj.n

    def tests(self):
        # an = self.dc.attr1_name
        # av = "myClass big wow"
        # ns = self.dc.ns_uri
        # anode = Attr(an, av)
        docEl = self.n.docEl

        el0 = docEl.childNodes[0]
        el5 = docEl.childNodes[5]
        el8 = docEl.childNodes[8]
        zzz = self.n.doc.createTextNode("xyzzy")
        el8.appendChild(zzz)

        self.assertTrue(el0.isElement)

        cl = el5.cloneNode(deep=True)
        self.assertTrue(cl.isElement)
        #DBG.dumpNode(cl, msg="el5")
        #DBG.dumpNode(cl, msg="cl")
        eqBit = cl.isEqualNode(el5)
        #DBG.msg("Error: %s" % (el5.prevError))
        self.assertTrue(eqBit)
        self.assertFalse(cl.isSameNode(el5))

        self.assertFalse(el0.contains(el5))
        self.assertTrue(docEl.contains(el8))
        self.assertTrue(docEl.contains(zzz))  # DOM counts indirects
        self.assertFalse(el5.contains(docEl))

        self.assertFalse(el0.__contains__(el5))
        self.assertTrue(docEl.__contains__(el8))
        self.assertFalse(docEl.__contains__(zzz))  # But Python doesn't.

        xel = self.n.doc.createElement("xml:predef")
        xel.setAttribute("xmlns:foo", "w3example.org/made-up")

        self.assertEqual(el5.textContent, self.dc.text1)
        el5.textContent = "something else"
        self.assertEqual(el5.textContent, "something else")

    def testInternals(self):
        docEl = self.n.docEl
        el5 = docEl[5]

        with self.assertRaises(IndexError):
            docEl._expandChildArg(999)
            docEl._expandChildArg(-999)

        with self.assertRaises(HReqE):
            el5._expandChildArg(docEl)
            el5._expandChildArg(el5)

        with self.assertRaises(TypeError):
            el5._expandChildArg(3.2)
            el5._expandChildArg(None)
            el5._expandChildArg(True)

        self.assertTrue(bool(docEl))  # b/c it makes more sense

        #DBG.dumpNode(docEl, msg="docEl")
        #DBG.dumpNode(docEl[-1], msg="docEl[-1]")

    def test_neighbors(self):
        docEl = self.n.docEl
        assert len(docEl) == 10
        el0 = docEl.childNodes[0]
        el7 = docEl.childNodes[7]
        el8 = docEl.childNodes[8]
        el9 = docEl.childNodes[9]

        # The normal DOM names
        self.assertEqual(el7.parentNode, docEl)
        self.assertEqual(el0.previousSibling, None)
        self.assertEqual(el8.previousSibling, el7)
        self.assertEqual(el8.nextSibling, el9)
        self.assertEqual(el9.previousSibling, el8)
        self.assertEqual(el9.nextSibling, None)

        # XPAth axis names
        self.assertEqual(el7.parent, docEl)
        self.assertEqual(el0.precedingSibling, None)
        self.assertEqual(el8.precedingSibling, el7)
        self.assertEqual(el8.followingSibling, el9)
        self.assertEqual(el9.precedingSibling, el8)
        self.assertEqual(el9.followingSibling, None)

        # Whole-axis fetches
        self.assertEqual(el0.precedingSiblings, [])
        self.assertEqual(el8.precedingSiblings, docEl[0:8])
        self.assertEqual(el7.followingSiblings, docEl[8:10])
        self.assertEqual(el9.followingSiblings, [])
        self.assertEqual(el7.ancestors, [ docEl ])
        self.assertEqual(docEl.children, docEl.childNodes)
        # descendants TODO

    def test_position(self):
        docEl = self.n.docEl
        el0 = docEl.childNodes[0]
        el5 = docEl.childNodes[5]
        el8 = docEl.childNodes[8]
        self.assertEqual(el5.compareDocumentPosition(el8), -1)
        self.assertEqual(el5.compareDocumentPosition(el5), 0)
        self.assertEqual(el5.compareDocumentPosition(el0), +1)

        doc2 = self.n.impl.createDocument(None, "svg", None)
        docEl2 = doc2.documentElement
        removed = docEl.removeChild(-1)
        with self.assertRaises(HReqE):
            docEl.compareDocumentPosition(docEl2)
            docEl.compareDocumentPosition(docEl2)
            docEl2.compareDocumentPosition(docEl)
            removed.removeNode()

        docEl2.changeOwnerDocument(docEl.ownerDocument)
        docEl.appendChild(docEl2)

        # TODO More....

    def test_Element_mutators(self):
        docEl = self.n.docEl
        el0 = docEl.childNodes[0]
        el5 = docEl.childNodes[5]
        el8 = docEl.childNodes[8]
        zzz = self.n.doc.createTextNode("xyzzy")
        zzz2 = self.n.doc.createTextNode("plough")
        zzz3 = self.n.doc.createTextNode("plough")

        docEl.insertBefore(zzz, el5)
        docEl.replaceChild(newChild=zzz2, oldChild=zzz)
        docEl.removeChild(zzz2)

        with self.assertRaises(AttributeError):
            docEl.replaceChild(newChild=None, oldChild=el8)
            docEl.replaceChild(newChild=12, oldChild=el8)
            docEl.replaceChild(newChild=None, oldChild=None)
            docEl.replaceChild(newChild=None, oldChild=docEl)
        with self.assertRaises(HReqE):
            docEl.replaceChild(newChild=el8, oldChild=el8)
            docEl.replaceChild(el0, zzz3)  # bad order

        revnl = docEl.reversed()
        self.assertIsInstance(revnl, NodeList)
        #DBG.dumpNode(revnl, msg="revnl")
        self.assertEqual(len(revnl), len(docEl))
        self.assertIs(revnl[0], docEl[-1])

        nl = sorted(docEl)
        self.assertEqual(len(docEl), len(nl))
        emp = docEl.ownerDocument.createElement("br")
        nl = sorted(emp)
        self.assertEqual(len(nl), 0)

        nl = docEl * -1
        self.assertEqual(len(nl), 0)

    def test_attributes(self):
        docEl = self.n.docEl
        an = self.dc.attr1_name
        av = "myClass big wow"
        ns = self.dc.ns_uri
        anode = Attr(an, av)

        #el0 = docEl.childNodes[0]
        el5 = docEl.childNodes[5]
        el8 = docEl.childNodes[8]
        zzz = self.n.doc.createTextNode("xyzzy")
        el8.appendChild(zzz)

        # Attributes / plain
        el5.setAttribute(an, av)
        self.assertTrue(el5.hasAttribute(an))
        self.assertEqual(el5.getAttribute(an), av)

        #DBG.dumpNode(el5, msg=f"Before deleting attr '{an}'.")
        self.assertIsNone(el5.removeAttribute(an))
        #DBG.dumpNode(el5, msg="After (attr: %s)" % (repr(el5.attributes)))
        #import pudb; pudb.set_trace()
        self.assertFalse(el5.hasAttribute(an))

        self.assertIsNone(el5.getAttribute(an))
        el5.removeAttribute(an)  # No exception please.

        # Attributes / Node
        el5.setAttributeNode(anode)
        self.assertTrue(el5.hasAttribute(an))
        self.assertEqual(el5.getAttributeNode(an), anode)
        el5.removeAttributeNode(anode)
        self.assertFalse(el5.hasAttribute(an))
        self.assertIsNone(el5.getAttributeNode(anode.name))
        self.assertIsNone(el5.removeAttributeNode(anode))

        # Attributes / NS
        el5.setAttributeNS(ns, an, av)
        self.assertEqual(el5.getAttributeNS(ns, an), av)
        el5.removeAttributeNS(ns, an)
        self.assertFalse(el5.hasAttributeNS(ns, an))
        self.assertIsNone(el5.getAttributeNS(ns, an))
        self.assertIsNone(el5.removeAttributeNS(ns, an))

        # Attributes / NodeNS
        el5.setAttributeNodeNS(ns, anode)
        self.assertEqual(el5.getAttributeNodeNS(ns, an), anode)
        el5.removeAttributeNode(anode)
        self.assertFalse(el5.hasAttributeNS(ns, an))
        self.assertIsNone(el5.getAttributeNodeNS(ns, an))

        el5.setAttribute("att1", "val1")
        val2 = "Some longer -- maybe real! long, value."
        el5.setAttribute("att2.3", val2)
        self.assertTrue(bool(el5))  # b/c it makes more sense

    def test_serializers(self):
        doc = self.n.doc
        docEl = self.n.docEl
        #el0 = docEl.childNodes[0]
        el5 = docEl.childNodes[5]
        el8 = docEl.childNodes[8]
        zzz = doc.createTextNode("xyzzy")
        el8.appendChild(zzz)

        # TODO Deal with attr order.... cf makeTestDoc.compareAttrs
        stag = el5.startTag
        self.assertEqual(stag, """<para class="important" n="5">""")
        etag = el5.endTag
        self.assertEqual(etag, "</para>")
        self.assertEqual(el5.innerXML, "aardvark")
        self.assertEqual(el5.outerXML, stag + el5.innerXML + etag)

        #DBG.dumpNode(el5, msg="before outerXML")
        el5.outerXML = self.dc.outer
        #DBG.dumpNode(el5, msg="after outerXML assignment")
        self.assertFalse(el5.isConnected)
        newOne = docEl.childNodes[5]
        self.assertFalse(newOne is el5)
        self.assertEqual(len(newOne.childNodes), 1)
        self.assertTrue(newOne.childNodes[0].isText)

        #import pudb; pudb.set_trace()
        el5StartTag = el5.startTag
        el5EndTag = el5.endTag
        el5.innerXML = "hello"
        #DBG.dumpNode(el5, msg=f"after innerXML set: {el5.outerXML}")
        self.assertEqual(len(el5.childNodes), 1)
        self.assertTrue(el5.childNodes[0].isTextNode)
        self.assertEqual(el5.childNodes[0].data, "hello")
        self.assertEqual(el5.startTag, el5StartTag)
        self.assertEqual(el5.endTag, el5EndTag)

    def test_getitem(self):
        doc = self.n.doc
        docEl = self.n.docEl
        #el0 = docEl.childNodes[0]
        el5 = docEl.childNodes[5]
        #el8 = docEl.childNodes[8]
        #zzz = doc.createTextNode("xyzzy")

        an = self.dc.attr1_name
        av = "myClass big wow"
        #ns = self.dc.ns_uri
        #anode = Attr(an, av)

        for i in range(len(docEl)):
            self.assertTrue(docEl[i].isElement)
            self.assertTrue(docEl[-i].isElement)
        el5.setAttribute(an, av)
        self.assertEqual(el5["@"+an], av)
        nl = docEl[3:7]
        self.assertIsInstance(nl, NodeList)
        self.assertEqual(len(nl), 4)
        for i in range(len(nl)):
            self.assertIs(nl[i], docEl[i+3])

        nl = docEl[3:8:2]
        self.assertIsInstance(nl, NodeList)
        self.assertEqual(len(nl), 3)

        self.assertEqual(len(docEl["#text"]), 0)
        self.assertEqual(len(docEl["nope"]), 0)
        #print(f"\nself.dc.p_name: {self.dc.p_name}: {docEl.toprettyxml()}")
        #import pudb; pudb.set_trace()
        nl = docEl[self.dc.p_name]
        #print(f"The nodelist:")
        #for i, n in enumerate(nl): print("    %2d: %s" % (i, n.toxml()))
        self.assertEqual(len(nl), 10)

        with self.assertRaises(TypeError):
            nl = docEl[3+4j]
        with self.assertRaises(TypeError):
            docEl[3.14+4j] = doc.createElement("p")

        self.assertFalse(docEl.isEqualNode(None))

    def test_getitem2(self):
        doc = self.n.doc
        docEl = self.n.docEl
        self.assertEqual(len(docEl), 10)
        txt = doc.createTextNode("hmmmm")
        docEl.appendChild(txt)
        #print(docEl.toprettyxml())
        self.assertEqual(docEl[1]["@n"], "1")
        self.assertEqual(len(docEl["para"]), 10)
        self.assertEqual(len(docEl["#text"]), 1)
        self.assertEqual(len(docEl["#pi"]), 0)
        self.assertEqual(len(docEl["#comment"]), 0)

        with self.assertRaises(TypeError):
            _ = docEl["unknown:oracle(99)"]

        # TODO SchemeHandlers

    def test_setitemSingle(self):
        doc = self.n.doc
        docEl = self.n.docEl
        #el5 = docEl.childNodes[5]

        newb = doc.createElement("newb")
        docEl[5] = newb
        self.assertEqual(docEl.childNodes[5], newb)
        docEl.checkNode(deep=True)

    def test_setitemSlice(self):
        doc = self.n.doc
        docEl = self.n.docEl
        #el5 = docEl.childNodes[5]

        nl = NodeList()
        for _ in range(5):
            nl.append(doc.createElement("newb"))
        self.assertEqual(len(nl), 5)

        prevLen = len(docEl)
        docEl[0:2] = nl
        self.assertEqual(len(docEl), prevLen - 2 + 5)
        docEl.checkNode(deep=True)

    def test_fetchers(self):
        doc = self.n.doc
        docEl = self.n.docEl
        #el0 = docEl.childNodes[0]
        el5 = docEl.childNodes[5]
        el8 = docEl.childNodes[8]
        zzz = doc.createTextNode("xyzzy")
        el8.appendChild(zzz)

        # TODO More fetcher tests
        #
        el5.getElementsByTagName("p")
        el5.getElementsByClassName("myClass")
        #self.n.doc.getElementsByTagNameNS("p", "html")

        el5.insertAdjacentXML(RelPosition.beforebegin,
            xml='<p id="html_9">foo</p>')

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

        #append
        #extend

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
        self.assertTrue(el.isElement)
        self.assertEqual(len(el), 0)
        self.assertRaises(HierarchyRequestError, el.insert, 1, "Just a string")
        newb = self.n.doc.createComment("no comment.")
        newel = self.n.doc.createElement("p")
        el.insert(1, newb)
        with self.assertRaises(HReqE):
            newb.insert(newel, 1)
        self.assertEqual(len(el), 1)
        with self.assertRaises(IndexError):
            el.pop(9999)
        el.pop()
        self.assertEqual(len(el), 0)
        self.assertFalse(newb.isConnected)

    # end TestElement


###############################################################################
#
class testText(unittest.TestCase):
    def setUp(self):
        madeDocObj = makeTestDocEachMethod(dc=DAT_K)
        self.dc = DAT_K
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
        self.assertEqual(tx.tostring(), txText)

        tx2 = tx.cloneNode()
        self.assertTrue(tx2.isEqualNode(tx))
        self.assertFalse(tx2.isSameNode(tx))
        tx2.data += "AddedText"
        self.assertFalse(tx2.isEqualNode(tx))

        self.assertEqual(tx.textContent, txText)
        el.textContent = "something else"
        self.assertEqual(el.textContent, "something else")

        tx2.nodeValue = ""
        self.assertEqual(tx2.nodeValue, "")
        self.assertFalse(bool(tx2))


###############################################################################
#
class testCDATASection(unittest.TestCase):
    def setUp(self):
        madeDocObj = makeTestDocEachMethod(dc=DAT_K)
        self.dc = DAT_K
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
        self.assertEqual(cd.tostring(), cdText)
        self.assertTrue(bool(cd))

        self.assertEqual(cd.textContent, cdText)
        cd.textContent = "something else"
        self.assertEqual(cd.textContent, "something else")

        cd.nodeValue = ""
        self.assertEqual(cd.nodeValue, "")
        self.assertFalse(bool(cd))


###############################################################################
#
class testProcessingInstruction(unittest.TestCase):
    def setUp(self):
        madeDocObj = makeTestDocEachMethod(dc=DAT_K)
        self.dc = DAT_K
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
        expect = f"<?{piTarget} {piData}?>"
        self.assertEqual(pi.outerXML, expect)
        self.assertEqual(pi.tostring(), piData)

        pi2 = pi.cloneNode()
        self.assertTrue(pi2.isEqualNode(pi))
        self.assertFalse(pi2.isSameNode(pi))
        pi2.target += "\u03d6"  # pi
        self.assertFalse(pi2.isEqualNode(pi))
        pi2.target = pi2.target[0:-1]
        self.assertTrue(pi2.isEqualNode(pi))
        pi2.data += "\u03d6"  # pi
        self.assertFalse(pi2.isEqualNode(pi))
        self.assertTrue(bool(pi2))

        self.assertEqual(pi.textContent, piData)
        pi.textContent = "something else"
        self.assertEqual(pi.textContent, "something else")

        pi.nodeValue = ""
        self.assertEqual(pi.data, "")
        self.assertFalse(bool(pi))


###############################################################################
#
class testComment(unittest.TestCase):
    def setUp(self):
        madeDocObj = makeTestDocEachMethod(dc=DAT_K)
        self.dc = DAT_K
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
        self.assertEqual(com.tostring(), comText)
        self.assertTrue(bool(com))

        self.assertEqual(com.textContent, comText)
        com.textContent = "something else"
        self.assertEqual(com.textContent, "something else")

        com.nodeValue = ""
        self.assertEqual(com.outerXML.strip(), "<!---->")
        self.assertFalse(bool(com))


###############################################################################
#
class testEntityReference(unittest.TestCase):
    """TODO What else to support for test_EntityReference, if anything?
    """
    def setUp(self):
        madeDocObj = makeTestDocEachMethod(dc=DAT_K)
        self.dc = DAT_K
        self.n = madeDocObj.n

    def tests(self):
        er = self.n.doc.createEntityReference("bull", "\u2022")
        self.assertTrue(er.isEntRef)
        el = self.n.docEl.childNodes[5]
        el.appendChild(er)
        self.assertTrue(er.isEntRef)
        return


###############################################################################
#
class testAttr(unittest.TestCase):
    def setUp(self):
        madeDocObj = makeTestDocEachMethod(dc=DAT_K)
        self.dc = DAT_K
        self.n = madeDocObj.n

    attrExpr = r'\w+="[^"]*"$'

    def tests(self):
        docEl = self.n.docEl
        aname = "class"
        el = docEl.childNodes[2]
        aval = el.getAttribute(aname)
        self.assertEqual(aval, "important")

        anode1 = docEl.childNodes[2].getAttributeNode(aname)
        anode2 = docEl.childNodes[5].getAttributeNode(aname)
        self.assertEqual(anode1.nodeName, aname)
        self.assertEqual(anode2.nodeName, aname)

        #self.assertTrue(attrExpr, attr1.outerXML)
        #self.assertTrue(re.match(attrExpr, attr1.tostring()))

        newChild = self.n.doc.createElement("newb")
        with self.assertRaises(HierarchyRequestError):
            _x = anode2.getChildIndex
            _x = anode2.previousSibling
            _x = anode2.nextSibling
            _x = anode2.previous
            _x = anode2.next
            _x = anode2.firstChild
            _x = anode2.lastChild
            anode2.appendChild(newChild)
            anode2.insertBefore(newChild, el)

        self.assertEqual(anode1.textContent, "important")
        anode1.textContent = "something else"
        self.assertEqual(anode1.textContent, "something else")

        #el.compareDocumentPosition(other)

    @unittest.skip
    def testCompare(self):
        docEl = self.n.docEl
        aname = "class"

        print("\n********")
        print("testCompare: ", docEl.toprettyxml())
        anode1 = docEl.childNodes[2].getAttributeNode(aname)
        anode2 = docEl.childNodes[5].getAttributeNode(aname)
        eqBit = anode1.isEqualNode(anode2)
        if (not eqBit):
            DBG.dumpNode(anode1, msg="anode 1:")
            DBG.dumpNode(anode2, msg="anode 2:")
        self.assertTrue(eqBit)

        #anode3 = anode2.cloneNode(deep=True)

        anode2.checkNode()
        self.assertTrue(bool(anode2))


###############################################################################
#
class testNamedNodeMap(unittest.TestCase):
    def setUp(self):
        madeDocObj = makeTestDocEachMethod(dc=DAT_K)
        self.dc = DAT_K
        self.n = madeDocObj.n

    def tests(self):
        nnm = NamedNodeMap()
        self.assertIsNone(nnm.getNamedItem("class"))

        nnm.setNamedItem("class", "classy")
        anAttr = nnm.getNamedItem("class")
        self.assertIsInstance(anAttr, Attr)
        self.assertEqual(anAttr.nodeName, "class")
        self.assertEqual(anAttr.nodeValue, "classy")

        self.assertEqual(nnm.tostring().strip(), "class=\"classy\"")
        nnm.removeNamedItem("class")
        self.assertIsNone(nnm.getNamedItem("class"))
        self.assertRaises(IndexError, nnm.item, 3)
        nnm.clear()
        self.assertEqual(nnm.tostring(), "")


###############################################################################
#
class testGenerator1(unittest.TestCase):
    def setUp(self):
        madeDocObj = makeTestDocEachMethod(dc=DAT_K)
        self.dc = DAT_K
        self.n = madeDocObj.n

    def tests(self):
        nNodes = 0
        nodeTypeCounts = defaultdict(int)
        for node in self.n.docEl.eachNode(includeSelf=True):
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
                #DBG.msg(f"Expect {nexpected[k]} of '{k}'. but found {nfound}.")
                self.assertEqual(nfound, nexpected[k])
        self.assertTrue(set(nodeTypeCounts.keys()), set(nexpected.keys()))


###############################################################################
#
class testGenerator2(unittest.TestCase):
    def setUp(self):
        madeDocObj = makeTestDoc0(dc=DAT_K)
        self.n = madeDocObj.n
        self.n.fan = 5
        madeDocObj.addFullTree(self.n.docEl, n=self.n.fan, depth=2,
            withText="", withAttr={})  # Using default text/attrs

    def testGens(self):
        docEl = self.n.docEl
        origLen = len(docEl.childNodes)
        self.assertFalse(docEl.hasTextNodes)

        #print("docEl: \n" + docEl.toxml())

        p0 = docEl[0]
        self.assertEqual(p0.nodeName, "para0")
        self.assertTrue(p0.hasSubElements)
        self.assertFalse(p0.hasTextNodes)

        p1 = p0[3]
        self.assertEqual(p1.nodeName, "para1")
        self.assertTrue(p1.hasSubElements)
        self.assertFalse(p1.hasTextNodes)

        p2 = p1[3]
        self.assertEqual(p2.nodeName, "para2")
        self.assertFalse(p2.hasSubElements)
        self.assertTrue(p2.hasTextNodes)

        self.assertEqual(docEl._normalizeChildIndex(self.n.fan-2), self.n.fan-2)
        self.assertEqual(docEl._normalizeChildIndex(-2), self.n.fan-2)

        with self.assertRaises(IndexError):
            _x = docEl._normalizeChildIndex(999)
            _x = docEl._normalizeChildIndex(-999)

        nch = 0
        for ch in docEl.eachChild():
            self.assertTrue(ch.isElement)
            nch += 1
        self.assertEqual(nch, origLen)

        nanc = 0
        for ch in docEl[3].eachAncestor():
            self.assertTrue(ch.isElement)
            nanc += 1
        self.assertEqual(nanc, 1)

        #print("\n********")
        #print("testGenerator2: ", self.n.docEl.toprettyxml())
        #import pudb; pudb.set_trace()
        self.tryOptions(docEl.eachSaxEvent, attrTx="PAIRS")
        self.tryOptions(docEl.eachSaxEvent, attrTx="EVENTS")
        self.tryOptions(docEl.eachSaxEvent, attrTx="DICT")

    def tryOptions(self, gen:Callable, attrTx:bool):
        eventCounts = defaultdict(int)
        for se in gen(attrTx=attrTx):
            self.assertIsInstance(se, Tuple)
            tlen = len(se)
            seType = se[0]
            eventCounts[seType] += 1
            if seType == SaxEvent.DOC: self.assertEqual(tlen, 1)
            elif seType == SaxEvent.START:
                if attrTx == "EVENTS":
                    self.assertTrue(tlen == 2)
                elif attrTx == "DICT":
                    if tlen == 2:
                        pass
                    elif tlen == 3:
                        self.assertIsInstance(se[2], dict)
                    else:
                        self.assertFalse(f"Extra event args with attrDict: {se}.")
                elif attrTx == "PAIRS":
                    self.assertEqual(tlen % 2, 0)
                else:
                    raise DOMException("Bad attrTx")
            elif seType == SaxEvent.END: self.assertEqual(tlen, 2)
            elif seType == SaxEvent.CDATA: self.assertEqual(tlen, 1)
            elif seType == SaxEvent.CHAR: self.assertEqual(tlen, 2)
            elif seType == SaxEvent.CDATAEND: self.assertEqual(tlen, 1)
            elif seType == SaxEvent.COMMENT: self.assertEqual(tlen, 2)
            elif seType == SaxEvent.PROC: self.assertEqual(tlen, 3)
            elif seType == SaxEvent.ATTRIBUTE:
                self.assertEqual(tlen, 3)
            elif seType == SaxEvent.DOCEND: self.assertEqual(tlen, 1)
            else:
                raise ValueError("Unknown SaxEvent {seType}.")

        #DBG.msg("Events:\n    %s" % (repr(eventCounts)))
        # Check the actual counts
        self.assertEqual(eventCounts[SaxEvent.DOC], 1)
        self.assertEqual(eventCounts[SaxEvent.START], 156)
        self.assertEqual(eventCounts[SaxEvent.END], 156)
        self.assertEqual(eventCounts[SaxEvent.CDATA], 0)
        self.assertEqual(eventCounts[SaxEvent.CHAR], 125)
        self.assertEqual(eventCounts[SaxEvent.CDATAEND], 0)
        self.assertEqual(eventCounts[SaxEvent.COMMENT], 0)
        self.assertEqual(eventCounts[SaxEvent.PROC], 0)
        self.assertEqual(eventCounts[SaxEvent.DOCEND], 1)

        if attrTx == "EVENTS":
            self.assertEqual(eventCounts[SaxEvent.ATTRIBUTE], 155)
        else:
            self.assertEqual(eventCounts[SaxEvent.ATTRIBUTE], 0)


if __name__ == '__main__':
    unittest.main()
