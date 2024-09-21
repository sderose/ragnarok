#!/usr/bin/env python3
#
#pylint: disable=W0201, C2801
#
import os
import unittest
#import math
#import random
from collections import OrderedDict
from typing import List

from makeTestDoc import makeTestDoc0, makeTestDoc2, DAT  #, DBG

from nodetypes import NodeTypes

#from xmlstrings import XmlStrings

from basedom import DOMImplementation
from basedom import Document, Node, Element, Attr, NamedNodeMap, NodeList
from basedom import HIERARCHY_REQUEST_ERR
from basedom import WRONG_DOCUMENT_ERR
from basedom import INVALID_CHARACTER_ERR
from basedom import NOT_FOUND_ERR
from basedom import NOT_SUPPORTED_ERR
from basedom import NAMESPACE_ERR

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
    def __init__(self, dc:type=DAT):
        super(makeTestDocEachMethod, self).__init__(dc=dc)
        assert isinstance(self.n.impl, DOMImplementation)
        assert isinstance(self.n.doc, Document)
        assert isinstance(self.n.docEl, Element)

        for _i in range(10):
            p = self.n.doc.createElement(self.dc.p_name)
            p.setAttribute(self.dc.attr1_name, self.dc.attr1_value)
            t = self.n.doc.createTextNode(self.dc.text1)
            p.appendChild(t)
            self.n.docEl.appendChild(p)

        #DBG.dumpNode(self.n.docEl)
        #y = self.makeSampleDoc()
        #x = self.makeSampleDoc()


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
class test_NodeTypes(unittest.TestCase):
    def setUp(self):
        madeDocObj = makeTestDocEachMethod(dc=K)
        self.n = madeDocObj.n

    def tests(self):
        from xml.dom.minidom import Node as MN

        for n in range(13):
            self.assertTrue(NodeTypes.okNodeType(NodeTypes(n), die=False))
            self.assertTrue(NodeTypes.okNodeType(NodeTypes(n), die=False))
            self.assertTrue(NodeTypes.tostring(NodeTypes(n)))

        AEQ = self.assertEqual
        AEQ(Node.ELEMENT_NODE,                 NodeTypes(MN.ELEMENT_NODE))
        AEQ(Node.ATTRIBUTE_NODE,               NodeTypes(MN.ATTRIBUTE_NODE))
        AEQ(Node.TEXT_NODE,                    NodeTypes(MN.TEXT_NODE))
        AEQ(Node.CDATA_SECTION_NODE,           NodeTypes(MN.CDATA_SECTION_NODE))
        AEQ(Node.ENTITY_REFERENCE_NODE,        NodeTypes(MN.ENTITY_REFERENCE_NODE))
        AEQ(Node.ENTITY_NODE,                  NodeTypes(MN.ENTITY_NODE))
        AEQ(Node.PROCESSING_INSTRUCTION_NODE,
            NodeTypes(MN.PROCESSING_INSTRUCTION_NODE))
        AEQ(Node.COMMENT_NODE,                 NodeTypes(MN.COMMENT_NODE))
        AEQ(Node.DOCUMENT_NODE,                NodeTypes(MN.DOCUMENT_NODE))
        AEQ(Node.DOCUMENT_TYPE_NODE,           NodeTypes(MN.DOCUMENT_TYPE_NODE))
        AEQ(Node.DOCUMENT_FRAGMENT_NODE,       NodeTypes(MN.DOCUMENT_FRAGMENT_NODE))
        AEQ(Node.NOTATION_NODE,                NodeTypes(MN.NOTATION_NODE))


###############################################################################
#
class TestDOMImplementation(unittest.TestCase):
    def setUp(self):
        madeDocObj = makeTestDoc2()
        self.n = madeDocObj.n

    def testHasFeature(self):
        """See also testExtensions
        """
        self.assertTrue(self.n.impl.hasFeature("core", "1.0"))
        self.assertTrue(self.n.impl.hasFeature("core", "2.0"))
        self.assertTrue(self.n.impl.hasFeature("core", None))
        self.assertTrue(self.n.impl.hasFeature("xml", "1.0"))
        self.assertTrue(self.n.impl.hasFeature("xml", "2.0"))
        self.assertTrue(self.n.impl.hasFeature("xml", None))

    def testDI(self):
        import dombuilder
        #el.getInterface(feature)
        #_create_document(self)
        #el.registerDOMImplementation(name, factory)

        el = self.n.docEl

        #adoc = self.n.impl.parse(self.dc.doc_path)
        dbuilder = dombuilder.DOMBuilder()

        theSamplePath = "./docForTestEachMethod_testDI.xml"
        assert os.path.exists(theSamplePath)
        theDom = dbuilder.parse(theSamplePath)
        self.assertTrue(isinstance(theDom. Document))

        dum_doc = """<?xml version="1.0"?><doc>Hello</doc>"""
        theDom = el.parse_string(s=dum_doc)
        self.assertTrue(isinstance(theDom, Document))


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

        #self.assertRaises(NotImplementedError, nl.__mul__(2))
        #self.assertRaises(NotImplementedError, nl.__rmul__(2))


###############################################################################
#
class test_Node(unittest.TestCase):
    def setUp(self):
        madeDocObj = makeTestDocEachMethod(dc=K)
        self.dc = K
        self.n = madeDocObj.n

    def tests(self):
        el5 = self.n.docEl.childNodes[5]
        el8 = self.n.docEl.childNodes[8]
        node = Node("ns", "notAnElement", None)

        #self.assertRaises(IndexError, self.n.docEl.childNodes[200])
        #self.assertRaises(IndexError, self.n.docEl.childNodes[-200])

        self.assertEqual(None, node.prefix)
        self.assertEqual(None, node.localName)
        self.assertEqual(None, node.namespaceURI)
        self.assertFalse(node.isConnected)

        self.assertEqual(None, node.nextSibling)
        self.assertEqual(None, node.previousSibling)
        self.assertEqual(None, node.previous)
        self.assertEqual(None, node.next)
        self.assertFalse(node.childNodes)
        self.assertFalse(node.firstChild)
        self.assertFalse(node.lastChild)

        self.assertEqual(None, node.nodeValue)
        #node.nodeValue(newData:str="")
        self.assertFalse(node.textContent)
        #node.textContent(newData:str)

        cl = node.cloneNode(deep=True)
        self.assertTrue(cl.isEqualNode(node))
        self.assertFalse(cl.isSameNode(node))

        self.assertEqual(node.compareDocumentPosition(el8), -1)
        self.assertEqual(node.compareDocumentPosition(node), 0)
        self.assertEqual(node.compareDocumentPosition(el8), -1)

        self.assertFalse(node.contains(node.))
        self.assertFalse(node.contains(el8))
        self.assertFalse(node.contains(self.n.docEl))
        self.assertTrue(self.n.docEl.contains(node.))

        self.assertIs(el8.getRootNode(), self.n.docEl)

        self.assertTrue(node.hasAttributes)
        self.assertFalse(node.isSameNode(el8))
        self.assertTrue(node.isSameNode(node.))

        #node.isSupported(feature, version)
        #node.lookupNamespaceURI(uri)
        #node.lookupPrefix(prefix)

        self.n.docEl.normalize()

        el = self.n.docEl.childNodes[7]
        for i in range(10):
            n = self.n.doc.createElement(self.dc.p_name)
            node.prependChild(n)

        self.assertTrue(node.hasChildNodes())
        #node.insertBefore(newNode, ch)
        #node.removeChild(oldChild)
        #node.replaceChild(newChild, oldChild)

        #node.unlink(keepAttrs=False)

        node.toxml()
        node.toprettyxml()

        self.assertTrue(node.rightmost)

        node.getChildIndex()
        #node.moveToOtherDocument(otherDocument)
        node.getFeature("attr-types")

        node.getUserData(self.dc.udk1_name)
        node.setUserData(self.dc.udk1_name, self.dc.udk1_value)
        node.getUserData(self.dc.udk1_name)

        node.collectAllXml(self)
        node.getNodePath(self)
        node.getNodeSteps(self)
        node.removeNode(self)

        x = self.dc.p_name
        i = 4
        node.count(x)
        node.index(x, 1, 2)
        newChild = self.n.doc.createElement(self.dc.new_name)
        node.append(newChild)
        node.clear()
        node.insert(i, x)
        node.pop(i)
        node.remove(x)
        node.reverse()
        node.sort("a", reverse=False)
        node.isOfValue(x)
        node.checkNode()


class test_NodeType_Predicates(unittest.TestCase):
    def setUp(self):
        madeDocObj = makeTestDocEachMethod(dc=K)
        self.dc = K
        self.n = madeDocObj.n

    def testSet(self):
        el = self.n.docEl.childNodes[5]
        for ch in self.n.docEl.childNodes:
            if (ch.nodeType == NodeTypes.UNSPECIFIED_NODE):
                self.allPreds(ch, [ ])
            elif (ch.nodeType == NodeTypes.ELEMENT_NODE):
                self.allPreds(ch, [ el.isElement ])
            elif (ch.nodeType == NodeTypes.ATTRIBUTE_NODE):
                self.allPreds(ch, [ el.isAttribute ])
            elif (ch.nodeType == NodeTypes.TEXT_NODE):
                self.allPreds(ch, [ el.isTest ])
            elif (ch.nodeType == NodeTypes.CDATA_SECTION_NODE):
                self.allPreds(ch, [ el.isCData ])
            elif (ch.nodeType == NodeTypes.ENTITY_REFERENCE_NODE):
                self.allPreds(ch, [ el.isEntRef ])
            elif (ch.nodeType == NodeTypes.ENTITY_NODE):
                self.allPreds(ch, [ el.isEntity ])
            elif (ch.nodeType == NodeTypes.PROCESSING_INSTRUCTION_NODE):
                self.allPreds(ch, [ el.isPI ])
            elif (ch.nodeType == NodeTypes.COMMENT_NODE):
                self.allPreds(ch, [ el.isComment ])
            elif (ch.nodeType == NodeTypes.DOCUMENT_NODE):
                self.allPreds(ch, [ el.isDocument ])
            elif (ch.nodeType == NodeTypes.DOCUMENT_TYPE_NODE):
                self.allPreds(ch, [ el.isDoctype ])
            elif (ch.nodeType == NodeTypes.DOCUMENT_FRAGMENT_NODE):
                self.allPreds(ch, [ el.isFragment ])
            elif (ch.nodeType == NodeTypes.NOTATION_NODE):
                self.allPreds(ch, [ el.isNotation ])
            else:
                assert False, "Unexpected nodeType %d." % (ch.nodeType)

    def allPreds(self, el, ok:List):
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


###############################################################################
#
class test_Document(unittest.TestCase):
    def setUp(self):
        madeDocObj = makeTestDocEachMethod(dc=K)
        self.dc = K
        self.n = madeDocObj.n

    def tests(self):
        el = self.n.doc
        self.assertTrue(el.charset)
        self.assertTrue(el.contentType)
        self.assertTrue(el.documentURI)
        self.assertTrue(el.domConfig)
        self.assertTrue(el.inputEncoding)
        #el.getXmlDcl(encoding:str="utf-8", standalone:bool=None)
        self.assertTrue(el.buildIdIndex)


###############################################################################
#
class test_Element(unittest.TestCase):
    def setUp(self):
        madeDocObj = makeTestDocEachMethod(dc=K)
        self.dc = K
        self.n = madeDocObj.n

    def tests(self):
        an = self.dc.attr1_name
        av = "myClass big wow"
        ns = self.dc.ns_uri
        anode = Attr(an, av)

        el0 = self.n.docEl.childNodes[0]
        el5 = self.n.docEl.childNodes[5]
        el8 = self.n.docEl.childNodes[8]

        self.assertTrue(el0.isElement)


        cl = el5.cloneNode(deep=True)
        self.assertTrue(cl.isElement)
        self.assertTrue(cl.isEqualNode(node))
        self.assertFalse(cl.isSameNode(node))

        self.assertEqual(el5.compareDocumentPosition(el8), -1)
        self.assertEqual(el5.compareDocumentPosition(el), 0)
        self.assertEqual(el5.compareDocumentPosition(el0), +1)

        self.assertFalse(node.contains(node.))
        self.assertFalse(node.contains(el8))
        self.assertFalse(node.contains(self.n.docEl))
        self.assertTrue(self.n.docEl.contains(node.))


        el5.setAttribute(an, av)
        self.assertTrue(el5.hasAttribute(an))
        self.assertEqual(el5.getAttribute(an), av)
        el5.removeAttribute(an)
        self.assertFalse(el5.hasAttribute(an))
        self.assertEqual(el5.getAttribute(an), None)
        self.assertRaises(NOT_FOUND_ERR, el5.removeAttribute(an))

        el5.setAttributeNode(anode)
        self.assertTrue(el5.hasAttribute(an))
        self.assertEqual(el5.getAttributeNode(an), anode)
        el5.removeAttributeNode(anode)
        self.assertFalse(el5.hasAttribute(an))
        self.assertRaises(NOT_FOUND_ERR, el5.getAttributeNode(anode))
        self.assertRaises(NOT_FOUND_ERR, el5.removeAttributeNode(anode))

        el5.setAttributeNS(ns, an, av)
        self.assertEqual(el5.getAttributeNS(ns, an), av)
        el5.removeAttributeNS(ns, an)
        self.assertFalse(el5.hasAttributeNS(ns, an))
        self.assertEqual(el5.getAttributeNS(ns, an), None)
        self.assertRaises(NOT_FOUND_ERR, el5.removeAttributeNS(ns, an))

        el5.setAttributeNodeNS(ns, anode)
        self.assertEqual(el5.getAttributeNodeNS(ns, an), anode)
        el5.removeAttributeNode(anode)
        self.assertFalse(el5.hasAttributeNS(ns, an))
        self.assertEqual(el5.getAttributeNodeNS(ns, an), None)

        el5.setAttribute("att1", "val1")
        val2 = "Some longer -- maybe real! long, value."
        el5.setAttribute("att2.3", val2)
        # TODO Deal with attr order....
        self.assertEqual(el5.outerXML, """<p att1="val1" att2.3="{val2}" />""")
        self.assertEqual(el5.innerXML, "")
        el5.outerXML = self.dc.outer
        self.assertEqual(len(el5.childNodes), 1)
        self.assertTrue(el5.childNodes[0].isTextNode)

        el5.innerXML = "hello"
        self.assertEqual(len(el5.childNodes[0].data), 5)
        self.assertEqual(el5.startTag, "<%s>" % (self.dc.p_name))

        #el5._startTag(sortAttrs=True, empty=False)
        self.assertEqual(el5.endTag, f"</{self.dc.p_name}>")
        self.assertTrue(el5.firstElementChild)

        el5.getElementsByTagName("p")
        el5.getElementsByClassName("myClass")
        el5.getElementsByTagNameNS("p", "html")
        el5.insertAdjacentHTML('<p id="html_9">foo</p>')

        #el5.matches()
        #el5.querySelector()
        #el5.querySelectorAll()


###############################################################################
#
class test_Leaf(unittest.TestCase):  # AKA CharacterData
    def setUp(self):
        madeDocObj = makeTestDocEachMethod(dc=K)
        self.dc = K
        self.n = madeDocObj.n

    def tests(self):
        el = self.n.docEl.childNodes[5]
        el7 = self.n.docEl.childNodes[7]

        self.assertFalse(el.hasChildNodes())
        self.assertFalse(el.contains(el7))
        self.assertFalse(el.hasAttributes())
        el.count(self.dc.p_name)
        el.index(self.dc.inline_name, start=None, end=None)
        el.clear()
        el.tostring()
        self.assertTrue(el.firstChild)
        self.assertTrue(el.lastChild)
        el.__getitem__()

        oldChild = self.n.docEl.childNodes[3]
        newChild = self.n.doc.createElement(self.dc.new_name)

        # All these should fail
        self.assertRaises(HIERARCHY_REQUEST_ERR, el.appendChild(newChild))
        self.assertRaises(HIERARCHY_REQUEST_ERR, el.prependChild(newChild))
        self.assertRaises(HIERARCHY_REQUEST_ERR, el.insertBefore(oldChild, newChild))
        self.assertRaises(HIERARCHY_REQUEST_ERR, el.removeChild(oldChild))
        self.assertRaises(HIERARCHY_REQUEST_ERR, el.replaceChild(newChild, oldChild))
        self.assertRaises(HIERARCHY_REQUEST_ERR, el.append(newChild))


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

        txNow = el.lastChild()
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
        #    f"""[ \{"#name"="#cdata"\}, "{cdTextJ}" ]""")
        self.assertEqual(cd.tostring(), "<![CDATA[{cdText}]]>")

        cd2 = cd.cloneNode()
        self.assertTrue(cd2.isEqualNode(cd))
        self.assertFalse(cd2.isSameNode(cd))
        cd2.data += "XXX"
        self.assertFalse(cd2.isEqualNode(cd))

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

        self.assertTrue(pi.isPROCESSINGINSTRUCTION)
        self.assertTrue(pi.isPI)
        self.assertEqual(pi.nodeValue, piData)
        self.assertEqual(pi.outerXML, f"<?{piTarget} {piData}?>")
        self.assertEqual(pi.innerXML, piData)
        #piDataJ = BaseDom.escapeJsonStr(piData)
        #self.assertEqual(pi.outerJSON(indent="  "),
        #    """[ \{"#name"="#pi", "#target"="{piTarget}"\}, "{piDataJ}" ]""")
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
            """[ {"#name"="#comment"}, "{comText}" ]""")
        self.assertEqual(com.tostring(),
            f"<!--{comText}-->")

        com.nodeValue = ""
        self.assertEqual(com.outerXML, "<!---->")
        self.assertEqual(com.innerXML, "")


###############################################################################
#
class test_EntityReference(unittest.TestCase):
    def setUp(self):
        madeDocObj = makeTestDocEachMethod(dc=K)
        self.dc = K
        self.n = madeDocObj.n

    def tests(self):
        sys.stderr.write("\n******* EntRef tests skipped *******\n")
        return
        er = self.n.doc.createEntityReference("bull", "\u2022")
        el = self.n.docEl.childNodes[5]
        el.appendChild(er)

        self.assertTrue(er.isEntRef)

        # TODO What else to support, if anything?


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
        self.assertEqual(anode1.name, aname)
        self.assertEqual(anode2.name, aname)

        #el.compareDocumentPosition(other)
        self.assertTrue(anode1.isEqualAttr(anode2))
        anode3 = anode2.cloneNode()
        self.assertTrue(anode1.isEqualAttr(anode3))

        #self.assertTrue(attrExpr, attr1.outerXML)
        #self.assertTrue(attrExpr, attr1.innerXML)
        #self.assertTrue(re.match(attrExpr, attr1.tostring()))
        #el.outerJSON(indent="  ", depth=0)
        #el.attrToJson()

        self.assertRaises(HIERARCHY_REQUEST_ERR, anode3.getChildIndex())
        self.assertRaises(HIERARCHY_REQUEST_ERR, anode3.previousSibling())
        self.assertRaises(HIERARCHY_REQUEST_ERR, anode3.nextSibling())
        self.assertRaises(HIERARCHY_REQUEST_ERR, anode3.previous())
        self.assertRaises(HIERARCHY_REQUEST_ERR, anode3.next())
        self.assertRaises(HIERARCHY_REQUEST_ERR, anode3.firstChild())
        self.assertRaises(HIERARCHY_REQUEST_ERR, anode3.lastChild())
        newChild = self.n.doc.createElement("newb")
        self.assertRaises(HIERARCHY_REQUEST_ERR, anode3.appendChild(newChild))
        self.assertRaises(HIERARCHY_REQUEST_ERR, anode3.insertBefore(newChild, el))

        anode2.checkNode()


###############################################################################
#
class test_NamedNodeMap(OrderedDict):
    def setUp(self):
        madeDocObj = makeTestDocEachMethod(dc=K)
        self.dc = K
        self.n = madeDocObj.n

    def tests(self):
        el = NamedNodeMap()
        el.getNamedItem("class")
        el.setNamedItem("class", "classy")
        el.removeNamedItem("class")
        el.item(3)
        el.tostring()
        el.clear()


if __name__ == '__main__':
    unittest.main()
