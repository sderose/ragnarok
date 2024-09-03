#!/usr/bin/env python3
#
#pylint: disable=W0201, C2801
#
import unittest
import math
import random
from collections import OrderedDict
from typing import List

from xml.dom import minidom

#import xml.dom.minidom
#from xml.dom.minidom import getDOMImplementation

from xmlstrings import XMLStrings
from BaseDOM import getDOMImplementation, NodeTypes, Node, Document, NamedNodeMap
from BaseDOM import HIERARCHY_REQUEST_ERR
from BaseDOM import WRONG_DOCUMENT_ERR
from BaseDOM import INVALID_CHARACTER_ERR
from BaseDOM import NOT_FOUND_ERR
from BaseDOM import NOT_SUPPORTED_ERR
from BaseDOM import NAMESPACE_ERR
from BaseDOM import DOMImplementation


# Sample document generators
#     Add different child mixes
#     Add namespace, userdata
#     Add long names, depth, breadth, attr types
#

def makeAllTypes():
    impl, doc, docEl = TestExceptions.makeSampleDoc()
    el = docEl.childNodes[5]

    x = doc.createProcessingInstruction(
        "someTarget", """someData='foo' bar="baz" 12.1?""")
    el.appendChild(x)

    x = doc.createComment(
        "Comments are cool. Lots of potassium.")
    el.appendChild(x)

    x = doc.createCdataSection(
        "For example, in XML you say <p>foo</p> [[sometimes]].")
    el.appendChild(x)

    # EntityReference, Notation, DocType

    return impl, doc, docEl

def getAttrNames(n:int, randomize:bool=False):
    """Generate several attribute names, fixed or random.
    """
    names = []
    baseName = "anAttrName"
    for i in range(n):
        if (randomize): baseName = randomName()
        names.append(baseName + str(i))
    return names

#nmStartCharExpr = re.compile("["+XMLStrings._nameStartChar+"]")
#nmCharExpr = re.compile("["+XMLStrings._nameChar+"]")

nameStartChars = XMLStrings.allNameStartChars()
nameChars = nameStartChars + XMLStrings.allNameChars()

def randomName(maxLen:int=64):
    """Generate a random valid XML NAME, incl. Unicode.
    """
    cp = random.randint(len(nameStartChars))
    name = chr(cp)
    length = math.floor(random.betavariate(1, 3) * maxLen) + 2
    for i in range(length):
        cp = random.randint(len(nameChars))
        name += chr(cp)
    return name


###############################################################################
#
class TestExceptions(unittest.TestCase):
    def setup(self):
        impl = getDOMImplementation()
        doc = impl.createDocument(None, "x", None)
        docEl = doc.documentElement
        for i in range(10):
            p = doc.createElement("para")
            p.setAttribute("class", "alpha")
            t = doc.createTextNode("aardvark")
            p.appendChild(t)
            doc.documentElement.appendChild(p)
        #return impl, doc, docEl

        y = self.makeSampleDoc()
        #x = self.makeSampleDoc()
        self.impl = impl
        self.doc = doc
        self.docEl = doc.documentElement

    @staticmethod
    def makeSampleDoc():
        pass

    def testExceptions(self):
        self.assertTrue(isinstance(HIERARCHY_REQUEST_ERR, Exception))
        self.assertTrue(isinstance(WRONG_DOCUMENT_ERR, Exception))
        self.assertTrue(isinstance(INVALID_CHARACTER_ERR, Exception))
        self.assertTrue(isinstance(NOT_FOUND_ERR, Exception))
        self.assertTrue(isinstance(NOT_SUPPORTED_ERR, Exception))
        self.assertTrue(isinstance(NAMESPACE_ERR, Exception))
        self.assertTrue(isinstance(DOMImplementation, Exception))


###############################################################################
#
class TestDOMImplementation(unittest.TestCase):
    def setup(self):
        self.impl, self.doc, self.docEl = TestExceptions.makeSampleDoc()

    def testHasFeature(self):
        self.assertTrue(self.impl.hasFeature("core", "1.0"))
        self.assertTrue(self.impl.hasFeature("core", "2.0"))
        self.assertTrue(self.impl.hasFeature("core", None))
        self.assertTrue(self.impl.hasFeature("xml", "1.0"))
        self.assertTrue(self.impl.hasFeature("xml", "2.0"))
        self.assertTrue(self.impl.hasFeature("xml", None))
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

    def testDI(self):
        import DOMBuilder
        #el.getInterface(feature)
        #_create_document(self)
        #el.registerDOMImplementation(name, factory)

        el = self.docEl.childNodes[4]

        path = "file:///Users/sderose/_sjdUtils/Data/TextFormatSamples/sample.xml"
        adoc = self.impl.parse(path)
        dbuilder = DOMBuilder.DOMBuilder()
        theDom = dbuilder.parse(path)
        self.assertTrue(isinstance(theDom. Document))

        dumbDoc = """<?xml version="1.0"?><doc>Hello</doc>"""
        theDom = el.parse_string(s=dumbDoc)
        self.assertTrue(isinstance(theDom, Document))


###############################################################################
#
class test_NodeTypes(unittest.TestCase):
    def setup(self):
        self.impl, self.doc, self.docEl = TestExceptions.makeSampleDoc()

    def tests(self):
        for n in range(13):
            self.assertTrue(NodeTypes(n).okNodeType(die=False))
            self.assertTrue(NodeTypes(n).okNodeType(die=False))
            self.assertTrue(NodeTypes(n).tostring())


        self.assertEqual(Node.ELEMENT_NODE,                 minidom.Node.ELEMENT_NODE)
        self.assertEqual(Node.ATTRIBUTE_NODE,               minidom.Node.ATTRIBUTE_NODE)
        self.assertEqual(Node.TEXT_NODE,                    minidom.Node.TEXT_NODE)
        self.assertEqual(Node.CDATA_SECTION_NODE,           minidom.Node.CDATA_SECTION_NODE)
        self.assertEqual(Node.ENTITY_REFERENCE_NODE,        minidom.Node.ENTITY_REFERENCE_NODE)
        self.assertEqual(Node.ENTITY_NODE,                  minidom.Node.ENTITY_NODE)
        self.assertEqual(Node.PROCESSING_INSTRUCTION_NODE,
            minidom.Node.PROCESSING_INSTRUCTION_NODE)
        self.assertEqual(Node.COMMENT_NODE,                 minidom.Node.COMMENT_NODE)
        self.assertEqual(Node.DOCUMENT_NODE,                minidom.Node.DOCUMENT_NODE)
        self.assertEqual(Node.DOCUMENT_TYPE_NODE,           minidom.Node.DOCUMENT_TYPE_NODE)
        self.assertEqual(Node.DOCUMENT_FRAGMENT_NODE,       minidom.Node.DOCUMENT_FRAGMENT_NODE)
        self.assertEqual(Node.NOTATION_NODE,                minidom.Node.NOTATION_NODE)


###############################################################################
#
class test_NodeList(unittest.TestCase):
    def setup(self):
        self.impl, self.doc, self.docEl = TestExceptions.makeSampleDoc()

    def tests(self):
        origLen = len(self.docEl.childNodes)
        nl = self.doc.createNodeList()
        for n in reversed(self.docEl.childNodes):
            nl.append(n)
        self.assertEqual(len(nl), origLen)

        for n in range(len(nl.childNodes)):
            self.assertEqual(nl.item(n), self.docEl.childNodes[origLen-n-1])

        self.assertRaises(nl.__mul__(2), NotImplementedError)
        self.assertRaises(nl.__rmul__(2), NotImplementedError)


###############################################################################
#
class test_Node(unittest.TestCase):
    def setup(self):
        self.impl, self.doc, self.docEl = TestExceptions.makeSampleDoc()

    def tests(self):
        el5 = self.docEl.childNodes[5]
        el8 = self.docEl.childNodes[8]

        # TODO: Do we allow negative indices?
        self.assertRaises(self.docEl.childNodes[200])
        self.assertRaises(self.docEl.childNodes[-200])

        self.assertTrue(el5.nextSibling)
        self.assertTrue(el5.previousSibling)
        self.assertTrue(el5.previous)
        self.assertTrue(el5.next)
        self.assertFalse(el5.prefix)
        self.assertEqual(el5.localName, "para")
        self.assertTrue(el5.namespaceURI)
        self.assertTrue(el5.isConnected)
        self.assertFalse(el5.childNodes)
        self.assertFalse(el5.firstChild)
        self.assertFalse(el5.lastChild)
        self.assertTrue(el5.nodeValue)
        #el5.nodeValue(newData:str="")
        self.assertFalse(el5.textContent)
        #el5.textContent(newData:str)

        cl = el5.cloneNode(deep=True)
        self.assertTrue(cl.isEqualNode(el5))
        self.assertFalse(cl.isSameNode(el5))

        self.assertEqual(el5.compareDocumentPosition(el8), -1)
        self.assertEqual(el5.compareDocumentPosition(el5), 0)
        self.assertEqual(el5.compareDocumentPosition(el8), -1)

        self.assertFalse(el5.contains(el8))
        self.assertFalse(el5.contains(self.docEl))
        self.assertTrue(self.docEl.contains(el5))

        self.assertIs(el8.getRootNode(), self.docEl)

        self.assertTrue(el5.hasAttributes)
        self.assertFalse(el5.isSameNode(el8))
        self.assertTrue(el5.isSameNode(el5))

        #el.isSupported(feature, version)
        #el.lookupNamespaceURI(uri)
        #el.lookupPrefix(prefix)

        self.docEl.normalize(self)

        el = self.docEl.childNodes[7]
        for i in range(10):
            n = self.doc.createElement("p")
            el.prependChild(n)

        self.assertTrue(el.hasChildNodes())
        #el.insertBefore(newNode, ch)
        #el.removeChild(oldChild)
        #el.replaceChild(newChild, oldChild)

        #el.unlink(keepAttrs=False)

        el.toxml()
        el.toprettyxml()

        self.assertTrue(el.rightmost)

        el.getChildIndex()
        #el.moveToOtherDocument(otherDocument)
        el.getFeature("attr-types")

        udk = "myUDKey"
        el.getUserData(udk)
        el.setUserData(udk, "999")
        el.getUserData(udk)

        el.collectAllXml(self)
        el.getNodePath(self)
        el.getNodeSteps(self)
        el.removeNode(self)

        x = "p"
        i = 4
        el.count(x)
        el.index(x, 1, 2)
        newChild = self.doc.createELement("newb")
        el.append(newChild)
        el.clear()
        el.insert(i, x)
        el.pop(i)
        el.remove(x)
        el.reverse()
        el.sort("a", reverse=False)
        el.isOfValue(x)
        el.checkNode()


class test_NodeType_Predicates(unittest.TestCase):
    def setup(self):
        self.impl, self.doc, self.docEl = makeAllTypes()

    def testSet(self):
        el = self.docEl.childNodes[5]
        for ch in self.docEl.childNodes():
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
    def setup(self):
        self.impl, self.doc, self.docEl = TestExceptions.makeSampleDoc()

    def tests(self):
        el = self.doc
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
    def setup(self):
        self.impl, self.doc, self.docEl = TestExceptions.makeSampleDoc()

    def tests(self):
        an = "class"
        av = "myClass big wow"
        ns = "html"
        el = self.docEl.childNodes[5]

        el.getAttribute(an)
        el.getAttributeNode(an)
        el.getAttributeNS(ns, an)
        el.getAttributeNodeNS(ns, an)
        el.setAttribute(an, av)
        el.setAttributeNode(an, av)
        el.setAttributeNS(ns, an, av)
        el.setAttributeNodeNS(ns, an, av)
        el.removeAttribute(an)
        el.removeAttributeNode(an)
        el.removeAttributeNS(ns, an)
        el.hasAttribute(an)
        el.hasAttributeNS(an, ns)
        self.assertTrue(el.outerXML)
        self.assertTrue(el.innerXML)
        el.outerXML = "<p/>"
        el.innerXML = "hello"
        self.assertTrue(el.startTag)
        #el._startTag(sortAttrs=True, empty=False)
        self.assertTrue(el.endTag)
        self.assertTrue(el.firstElementChild)

        self.assertTrue(el.lastElementChild)
        self.assertTrue(el.elementChildNodes)
        self.assertIs(el.elementChildN(5), el.childNodes[5])
        self.assertEqual(el.classList, "myClass")

        self.assertTrue(el.className)
        self.assertTrue(el.Id)
        self.assertTrue(el.hasIdAttribute)
        el.getElementsByTagName("p")
        el.getElementsByClassName("myClass")
        el.getElementsByTagNameNS("p", "html")
        el.insertAdjacentHTML('<p id="html_9">foo</p>')
        #el.matches()
        #el.querySelector()
        #el.querySelectorAll()


###############################################################################
#
class test_Leaf(unittest.TestCase):  # AKA CharacterData?
    def setup(self):
        self.impl, self.doc, self.docEl = TestExceptions.makeSampleDoc()

    def tests(self):
        el = self.docEl.childNodes[5]
        el7 = self.docEl.childNodes[7]

        el.hasChildNodes()
        self.assertFalse(el.contains(el7))
        el.hasAttributes()
        self.assertTrue(el.hasIdAttribute)
        el.count("p")
        el.index("q", start=None, end=None)
        el.clear()
        el.tostring()
        self.assertTrue(el.firstChild)
        self.assertTrue(el.lastChild)
        el.__getitem__()

        oldChild = self.docEl.childNodes[3]
        newChild = self.doc.createElement("newb")
        el.appendChild(newChild)
        el.prependChild(newChild)
        el.insertBefore(oldChild, newChild)
        el.removeChild(oldChild)
        el.replaceChild(newChild, oldChild)
        el.append(newChild)


###############################################################################
#
class test_Text(unittest.TestCase):
    def setup(self):
        self.impl, self.doc, self.docEl = TestExceptions.makeSampleDoc()

    def tests(self):
        el = self.docEl.childNodes[5]

        el.cloneNode(deep=False)

        self.assertTrue(el.nodeValue)
        el.nodeValue(newData="")
        el.cleanText(unorm=None, normSpace=False)
        self.assertTrue(el.outerXML)
        self.assertTrue(el.innerXML)
        el.outerJSON(indent="  ")
        el.tostring()


###############################################################################
#
class test_CDATASection(unittest.TestCase):
    def setup(self):
        self.impl, self.doc, self.docEl = TestExceptions.makeSampleDoc()

    def tests(self):
        el = self.docEl.childNodes[5]

        self.assertTrue(el.nodeValue)
        el.nodeValue(newData="")
        self.assertTrue(el.outerXML)
        self.assertTrue(el.innerXML)
        el.outerJSON(indent="  ")
        el.tostring()


###############################################################################
#
class test_ProcessingInstruction(unittest.TestCase):
    def setup(self):
        self.impl, self.doc, self.docEl = TestExceptions.makeSampleDoc()

    def tests(self):
        el = self.docEl.childNodes[5]

        self.assertTrue(el.nodeValue)
        el.nodeValue(newData="")
        self.assertTrue(el.outerXML)
        self.assertTrue(el.tostring)


###############################################################################
#
class test_Comment(unittest.TestCase):
    def setup(self):
        self.impl, self.doc, self.docEl = TestExceptions.makeSampleDoc()

    def tests(self):
        el = self.docEl.childNodes[5]

        el.cloneNode(deep=False)

        self.assertTrue(el.nodeValue)
        el.nodeValue(newData="")
        self.assertTrue(el.outerXML)
        self.assertTrue(el.innerXML)
        el.outerJSON(indent="  ")
        el.tostring()


###############################################################################
#
class test_EntityReference(unittest.TestCase):
    def setup(self):
        self.impl, self.doc, self.docEl = TestExceptions.makeSampleDoc()

    def tests(self):
        el = self.docEl.childNodes[5]

        self.assertTrue(el.nodeValue)
        el.nodeValue(newData="")
        self.assertTrue(el.outerXML)
        self.assertTrue(el.innerXML)
        el.outerJSON(indent="  ")
        el.tostring()


###############################################################################
#
class test_Notation(unittest.TestCase):
    def setup(self):
        self.impl, self.doc, self.docEl = TestExceptions.makeSampleDoc()

    def tests(self):
        el = self.docEl.childNodes[5]

        self.assertTrue(el.outerXML)
        self.assertTrue(el.innerXML)
        el.outerJSON(indent="  ")
        el.tostring()


###############################################################################
#
class test_Attr(unittest.TestCase):
    def setup(self):
        self.impl, self.doc, self.docEl = TestExceptions.makeSampleDoc()

    attrExpr = r'\w+="[^"]*"$'

    def tests(self):
        attr1 = self.docEl.childNodes[2].getAttribute("class")
        attr2 = self.docEl.childNodes[5].getAttribute("class")

        self.assertTrue(XMLStrings.isXmlName(attr1.name))

        #el.compareDocumentPosition(other)
        self.assertTrue(attr1.isEqualAttr(attr2))
        attr3 = attr2.cloneNode()
        self.assertTrue(attr1.isEqualAttr(attr3))

        #self.assertTrue(attrExpr, attr1.outerXML)
        #self.assertTrue(attrExpr, attr1.innerXML)
        #self.assertTrue(re.match(attrExpr, attr1.tostring()))
        #el.outerJSON(indent="  ", depth=0)
        #el.attrToJson()

        self.assertRaises(attr3.getChildIndex(), HIERARCHY_REQUEST_ERR)

        attr2.checkNode()


###############################################################################
#
class test_NamedNodeMap(OrderedDict):
    def setup(self):
        self.impl, self.doc, self.docEl = TestExceptions.makeSampleDoc()

    def tests(self):
        el = NamedNodeMap()
        el.getNamedItem("class")
        el.setNamedItem("class", "classy")
        el.removeNamedItem("class")
        el.item(3)
        el.tostring()
        el.clear()
