#!/usr/bin/env python3
#
#pylint: disable=W0201, C2801, W0612, W0212
#
# TODO: Group classes by source standard
#
import sys
#import os
import unittest
#import math
import random
import re
#from collections import defaultdict
#from typing import List

#pylint: disable=W0401,W0611,W0621
from domexceptions import HierarchyRequestError
from domexceptions import InvalidCharacterError
from domexceptions import NotSupportedError
#from domexceptions import NotFoundError
from domenums import NodeType
from xmlstrings import XmlStrings as XStr

import basedom
from basedom import DOMImplementation, FormatOptions
from basedom import PlainNode, Node, Document, Element, Text
from basedom import Attr, NamedNodeMap, NodeList

from makeTestDoc import makeTestDoc0, makeTestDoc2, DAT, DBG

HRE = HierarchyRequestError
ICE = InvalidCharacterError

s = "Lorem ipsum dolor sit amet"
name = "some.Name"
prefix = "foo"
uri = "https://example.com/random/uris"

class MyTestCase(unittest.TestCase):
    def XX(self, *_args, **_kwargs):
        return

    def TR(self, expr):
        return self.assertTrue(expr)

    def FA(self, expr):
        return self.assertFalse(expr)

    def NONE(self, first):
        return self.assertIsNone(first)

    def EQ(self, first, second):
        return self.assertEqual(first, second)

    def NE(self, first, second):
        return self.assertNotEqual(first, second)

    def IS(self, first, second):
        return self.assertIs(first, second)

    def TY(self, first, second):
        return self.assertIsInstance(first, second)

    def RZ(self, first, fn, *args, **kwargs):
        assert(issubclass(first, Exception))
        return self.assertRaises(first, fn, *args, **kwargs)

class testByMethod(MyTestCase):
    def setUp(self):
        """Should make:
        <html xmlns:html="https://example.com/namespaces/foo">
            <child0 an_attr.name="this is an attribute value"
                class="c1 c2" id="docbook_id_17">
                Some text content.</child0>
            <child1>
                <grandchild></grandchild>
            </child1>
            <empty></empty>
        </html>
        """
        madeDocObj = makeTestDoc2(dc=DAT, show=False)
        self.dc = DAT
        self.n = madeDocObj.n

    def testConstructors(self):
        doc = self.n.doc

        self.TY(self.n.impl.createDocument(
            self.dc.ns_uri, self.dc.root_name, doctype=None), Document)

        #self.TY(doc.createDocumentFragment(self.n.ns_uri, qualifiedName="frag",
        #        doctype=None), basedom.DocumentFragment)
        #self.TY(doc.createDocumentType("html"), basedom.DocumentType)
        self.TY(doc.createAttribute("style", "font-weight:bold;"), Attr)
        self.TY(doc.createCDATASection("icky][&<stuff"), basedom.CDATASection)
        self.TY(doc.createComment("this comment intentionally left blank"), basedom.Comment)
        self.TY(doc.createElement("This_is.42."), Element)
        self.TY(doc.createEntityReference("bull", "\u2022"), basedom.EntityReference)
        self.TY(doc.createProcessingInstruction("piTarget", "p i d a t a "), basedom.PI)
        self.TY(doc.createTextNode(" lorem ipsum"), basedom.Text)

        #self.RZ(NotSupportedError, Node, "self.dc.ns_uri", "abstraction")

        #self.TY(Document(), Document)
        #self.TY(Element(), Element)
        #self.TY(Attr(), Attr)
        #self.TY(CharacterData(), CharacterData)

        #self.TY(CDATASection(), CDATASection)
        #self.TY(Text(), Text)
        #self.TY(Comment(), Comment)
        #self.TY(ProcessingInstruction(), ProcessingInstruction)
        #self.TY(EntityReference(), EntityReference)

        #self.TY(NodeList(), NodeList)

        #self.TY(DOMImplementation(), DOMImplementation)
        #self.TY(FormatOptions(), FormatOptions)
        #self.TY(NameSpaces(), NameSpaces)
        #self.TY(NamedNodeMap(), NamedNodeMap)

    def testBuiltins(self):
        n0 = self.n.child0
        n1 = self.n.child1
        n2 = self.n.child2
        for x in range(10):
            ch = self.n.doc.createElement(f"P_{x}", attributes={ "seq":str(x) })
            n2.appendChild(ch)
        self.EQ(n2.length, 10)
        ch3 = n2[3]
        ch5 = n2[5]
        self.TR(ch3.isElement and ch5.isElement)

        self.TR(n2.bool())  # Empty element!
        self.n.docEl.sort(lambda x: x.nodeName, reverse=False)
        #DBG.dumpNode(n2[0], msg="Attr seq?")
        self.EQ(n2[0].getAttribute("seq"), "0")
        self.EQ(n2[0].getAttribute("seq", castAs=int), 0)
        self.n.docEl.clear()

        self.FA(n0.__eq__(n1))
        self.TR(n2.__eq__(n2))
        self.TR(n1.__ne__(ch))
        self.TR(ch3.__ne__(ch5))
        self.TR(ch5.__ge__(ch3))
        self.FA(ch5.__gt__(ch3))
        self.FA(ch5.__le__(ch3))
        self.TR(ch5.__lt__(ch3))

        self.FA(n0 == n1)
        self.TR(n2 == n2)
        self.TR(n1 != ch)
        self.TR(ch3 != ch5)
        self.TR(ch5 >= ch3)
        self.FA(ch5 > ch3)
        self.FA(ch5 <= ch3)
        self.TR(ch5 < ch3)

        self.XX(n0.__reduce__())
        self.XX(n0.__reduce__ex__())

    def testListBasics(self):
        n0 = self.n.child0
        n1 = self.n.child1
        n2 = self.n.child2
        newList = NodeList()
        for x in range(10):
            ch = self.n.doc.createElement("P_{x}", attributes={ "seq":str(x) })
            newList.append(ch)
        newList2 = newList.copy()

        # add is not in-place, it constructs a new NodeList.
        n1len = len(n0)
        zork = n0.__add__(newList)
        self.EQ(len(zork), n1len + len(newList))
        self.TR(zork.__contains__(ch))
        self.FA(n0.__contains__(ch))
        zork.__delitem__(ch)
        self.FA(zork.__contains__(ch))

        newList = NodeList()
        ch7 = None
        for x in range(10):
            ch = self.n.doc.createElement(f"P_{x}", attributes={ "seq":str(x) })
            if x == 7: ch7 = ch
            newList.append(ch)
        preLen = len(n0)

        nPlus = n0.__iadd__(newList)
        self.EQ(len(nPlus), preLen + len(newList))
        self.EQ(nPlus.count("P_5"), 1)
        self.RZ(ValueError, nPlus.index, "xyzzy", 2, -4)
        #DBG.dumpNode(nPlus, msg="nPlus")
        self.EQ(nPlus.index("P_6", 1, -2), 7)
        self.EQ(nPlus[2].nodeName, "P_1")

        nch = len(n0)
        n0.__imul__(2)
        self.EQ(len(n0), nch*2)

        self.XX(n0.__mul__(2))
        self.XX(n0.__rmul__(2))

        #self.XX(n0.__setitem__(prefix, uri))

        self.XX(n0.pop(i=-1))
        #self.XX(n0.reverse())
        #self.XX(n0.reversed())

    def testInternals(self):
        n0 = self.n.child0
        n1 = self.n.child1
        n2 = self.n.child2
        #prefix = "foo"
        #self.XX(n0.initOptions())
        #self.XX(n0.NOTYET__getitem__())
        #self.XX(n0._addNamespace(prefix+"2", uri=self.dc.ns_uri))
        #self.EQ(n0._expandChildArg(n1), (2, n1))

        newChild = self.n.doc.createElement("p")
        self.XX(n0._filterOldInheritedNS(newChild))
        #self.XX(n0._findAttr(self.dc.ns_uri, tgtName))
        self.EQ(self.n.doc._getXmlDcl(encoding="utf-8"),
            """<?xml version="1.0" encoding="utf-8"?>\n""")
        self.TR(n0._isOfValue(self.dc.child0_name))
        #self.XX(n0._presetAttr(self.dc.at_name2, self.dc.at_value2))
        #self.XX(n0._resetinheritedNS())
        #self.XX(n0._startTag(empty=True, includeNS=False))
        #self.XX(n0._string2doc(self.dc.xml))
        self.XX(self.n.docEl.checkNode(deep=False))
        self.XX(self.n.docEl.checkNode(deep=True))
        self.XX(n0.getChildIndex(onlyElements=False, ofNodeName=False, noWSN=False))
        self.XX(n0.getRChildIndex(onlyElements=False, ofNodeName=False, noWSN=False))
        #self.XX(nameMatch(n2, self.dc.target_name, self.dc.ns_uri))
        #self.XX(n0.nodeNameMatches(other))
        #self.XX(n0.unlink(keepAttributes=False))
        #self.XX(wrapper(*args, **kwargs)

    def testBasicDOM(self):
        n0 = self.n.child0
        n1 = self.n.child1
        n2 = self.n.child2
        d = self.n.docEl
        self.TR(n0.isElement and n1.isElement and n2.isElement and d.isElement)

        #self.RZ(AttributeError, n0.charset)
        self.EQ(self.n.doc.charset, "utf-8")
        self.EQ(len(n0.childNodes), 1)
        self.EQ(self.n.doc.contentType, "text/XML")
        #self.RZ(HRE, n0.documentURI)
        self.FA(self.n.doc.documentURI)

        self.XX(n0.cloneNode())
        self.NE(n2, n2.cloneNode(deep=True))
        self.XX(n0.cloneNode(deep=False))
        #self.XX(n0.compareDocumentPosition(other))
        #self.XX(n0.domConfig())
        #self.XX(getImplementation())
        self.IS(n0.getRootNode(), self.n.doc)
        self.EQ(n0.ownerDocument.inputEncoding, "utf-8")
        self.EQ(d.length, 3)
        self.EQ(n0.localName, self.dc.child0_name)
        self.XX(n0.lookupNamespaceURI(prefix))
        self.XX(n0.lookupPrefix(uri))
        #self.XX(n0.name())
        self.EQ(n0.namespaceURI, None)
        self.EQ(n0.prefix, "")
        self.XX(n0.nodeValue)
        try:
            n0.nodeValue = "SomeReplacementText"
            self.EQ(n0, "Non-CharacterData don't take nodeValue assignment.")
        except AttributeError:
            pass
        self.EQ(n0.tagName, self.dc.child0_name)

    def testObsoleteDOM(self):
        n0 = self.n.child0
        n1 = self.n.child1
        n2 = self.n.child2
        udKey = "skeleton"
        udValue = "in the attrs"
        n0.setUserData(udKey, udValue, handler=None)
        self.EQ(n0.getUserData(udKey), udValue)
        #self.XX(n0.getInterface())
        #self.XX(n0.registerDOMImplementation(name, factory))

    def testTreeMutators(self):
        n0 = self.n.child0
        n1 = self.n.child1
        n2 = self.n.child2
        newChild = self.n.doc.createElement("p")
        newList = NodeList()
        for x in range(10):
            ch = self.n.doc.createElement("P_{x}", attributes={ "seq":str(x) })
            newList.append(ch)
        self.EQ(len(newList), 10)

        n0.after(newList)
        n0.append(newChild)
        self.RZ(HRE, n0.append, newChild)
        newChild2 = newChild.cloneNode()
        n0.appendChild(newChild2)

        newList = NodeList()
        for x in range(10):
            ch = self.n.doc.createElement("P2_{x}", attributes={ "seq":str(x) })
            newList.append(ch)
        self.XX(n0.before(newList))

        otherDocument = self.n.impl.createDocument(self.dc.ns_uri, "html", None)
        n1Copy = n0.cloneNode(deep=True)
        self.FA(n1Copy.isConnected)
        #n1Copy.changeOwnerDocument(otherDocument)
        #self.EQ(n1Copy.ownerDocument, otherDocument)
        #self.RZ(HRE, n0.changeOwnerDocument, n2)

        newChild = self.n.doc.createElement("p")
        n0.insert(3, newChild)
        n0.insertAdjacentXML("beforebegin", self.dc.xml)
        n0.insertAdjacentXML("afterbegin", self.dc.xml)
        n0.insertAdjacentXML("beforeend", self.dc.xml)
        n0.insertAdjacentXML("afterend", self.dc.xml)
        #self.RZ(ValueError, n0.insertAdjacentXML, "xyzzy", self.dc.xml)

        newChild1 = self.n.doc.createElement("p")
        n0.insertAfter(newChild1, n0.childNodes[3])
        newChild2 = newChild.cloneNode()
        n0.insertBefore(newChild2, -2)
        newChild3 = newChild.cloneNode()
        n0.insertAfter(newChild3, 0)
        newChild4 = newChild.cloneNode()
        self.XX(n0.insertBefore(newChild4, n0.childNodes[5]))

        oldChild = n0.childNodes[2]
        self.XX(n0.normalize())
        newChild5 = newChild.cloneNode()
        self.XX(n0.prependChild(newChild5))
        self.XX(n0.remove(newChild5))
        self.XX(n0.removeChild(oldChild))
        self.XX(n0.removeChild(3))
        self.XX(n0.removeNode())

        oldChild = n0.childNodes[2]
        newChild6 = newChild.cloneNode()
        #DBG.dumpNode(newChild6, msg="newChild6")
        self.XX(n0.replaceChild(newChild6, oldChild))
        newChild7 = newChild.cloneNode()
        self.XX(n0.replaceChild(newChild7, -2))

        newList = NodeList()
        for x in range(10):
            ch = self.n.doc.createElement("P_{x}", attributes={ "seq":str(x) })
            newList.append(ch)
        self.EQ(len(newList), 10)
        newList2 = newList.copy()
        newList2.reverse()
        #self.XX(n0.replaceWith(newList2))

    def testCharacterDataMutators(self):
        n0 = self.n.child0
        n1 = self.n.child1
        n2 = self.n.child2
        origText = "some initial text data"
        tx = self.n.doc.createTextNode(origText)
        n2.appendChild(tx)
        s = "[Extended Data]"
        self.EQ(tx.data, origText)
        self.EQ(tx.data, n2.textContent)
        tx.appendData(s)
        self.EQ(tx.data, origText+s)
        tx.insertData(0, "staht ")
        self.EQ(tx.data[0:6], "staht ")
        tx.deleteData(0, 3)
        self.EQ(tx.data[0:3], "ht ")
        tx.replaceData(0, 3, "ahting")
        self.EQ(tx.data[0:9], "ahtingsom")
        self.EQ(tx.substringData(4, 3), "ngs")
        #self.XX(tx.cleanText(unorm, normSpace=False))
        #self.TR(tx.data.startswith("stahting ")

    def testTreeNeighbors(self):
        n0 = self.n.child0
        n1 = self.n.child1
        n2 = self.n.child2
        d = self.n.docEl
        self.TR(d.contains(n1))
        self.EQ(n0.depth, 2)
        self.IS(d.firstChild, n0)
        self.IS(d.lastChild, n2)
        self.IS(n0.parentElement, d)
        self.IS(n2.previousSibling, n1)
        self.IS(n0.nextSibling.nextSibling, n2)
        self.IS(n2.nextSibling, None)
        self.IS(d.leftmost, n0.childNodes[0])
        self.IS(d.rightmost, n2)
        self.IS(n2.previous, n1.rightmost)
        self.IS(n0.next, n0.firstChild)

    def testSearchers(self):
        n0 = self.n.child0
        n1 = self.n.child1
        n2 = self.n.child2
        d = self.n.docEl
        doc = self.n.doc
        n2.setAttribute("id", "theIdValue")
        self.IS(doc.getElementById("theIdValue"), n2)
        self.NONE(doc.getElementById("no_such_id_value", ))

        self.TY(doc.getElementsByClassName("big"), NodeList)

        self.TY(doc.getElementsByTagName("p"), NodeList)
        self.TY(doc.getElementsByTagNameNS("##any", "p"), NodeList)

        self.XX(d.eachChild(excludeNodeNames=["p"]))
        #self.XX(eachNode(self))

    def testTreeLoaders(self):
        n0 = self.n.child0
        n1 = self.n.child1
        n2 = self.n.child2
        filename_or_file = self.dc.sampleXmlPath
        self.n.impl.parse(filename_or_file, bufsize=5000)
        self.n.impl.parse(filename_or_file)  # And with alt parser?
        self.n.impl.parse_string(self.dc.xml)

    def testSerializers(self):
        n0 = self.n.child0
        n1 = self.n.child1
        n2 = self.n.child2

        #self.RZ(AttributeError, n0.xmlDcl)
        self.EQ(n0.ownerDocument.xmlDcl,
            """<?xml version="1.0" encoding="utf-8"?>\n""")
        #self.XX(n0.docTypeDcl)
        st = n0.startTag
        self.TR(st.startswith(f"<{self.dc.child0_name} "))
        print(f"\nstartTag: {st}\n    an '{self.dc.at_name}' = av '{self.dc.at_value}'.")
        self.TR(re.search(r" %s=\"%s\"" % (self.dc.at_name, self.dc.at_value), st))
        self.TR(re.search(r" %s=\"%s\"" % (self.dc.at_name2, self.dc.at_value2), st))
        self.TR(re.search(r" %s=\"%s\"" % (self.dc.at_name3, self.dc.at_value3), st))
        self.XX(n0.endTag, "</%s>" % (self.dc.child0_name))

        #self.XX(n0.innerXML)
        #self.XX(n0.innerXML = "")
        #self.XX(n0.outerXML)
        #self.XX(n0.outerXML = "")
        self.XX(n0.textContent)
        newData = "Just the text, ma'am."
        n0.textContent = newData
        self.EQ(n0.textContent, newData)
        self.XX(n0.tostring())
        self.XX(n0.collectAllXml())
        self.XX(n0.toxml())

        fo = FormatOptions(indent="____", quoteChar="'", newl="\r\n")
        fo.setInlines(None)
        self.XX(self.n.docEl.toprettyxml(foptions=fo))
        self.XX(self.n.docEl.toprettyxml(foptions=FormatOptions.canonicalFO()))
        # TODO Add a serious test of canonicity
        self.XX(n0.writexml(sys.stderr, indent="   ", addindent="   ", newl="\n"))

    def testJSON(self):
        j = self.n.docEl.outerJSON()

    def testPointers(self):
        n0 = self.n.child0
        n1 = self.n.child1
        n2 = self.n.child2
        doc = self.n.doc
        self.XX(self.n.doc.buildIdIndex("id"))
        #self.XX(n0.getNodePath(useId, attrOk=False))
        #self.XX(n0.getNodeSteps(useId, attrOk=False, wsn=True))
        self.TY(doc.useNodePath("1/1"), Text)
        self.EQ(doc.useNodeSteps([ 1, 1 ]).nodeName, "#text")

    def randChars(self, chars:str, nc:int, n:int=5):
        buf = ""
        for _ in range(n):
            buf += chars[random.randrange(0, nc)]
        return buf

    def testAttributeStuff(self):
        n0 = self.n.child0
        n1 = self.n.child1
        n2 = self.n.child2
        nAttrs = 257
        nameChars = XStr.allNameChars()
        nnc = len(nameChars)
        self.EQ(nnc, 54128)

        for i in range(nAttrs):
            val = "zyz"+self.randChars(nameChars, nnc)
            n1.setAttribute(f"attr_{i}", val)
            n2.setAttributeNS("http://derose.net/namespaces/test", f"attr_{i}", val)
        self.EQ(len(n1.attributes), nAttrs)

        self.TR(n1.hasAttributes)
        self.TR(n0.hasAttribute(self.dc.at_name2))
        self.FA(n0.hasAttribute("notMyAttributeFerSure"))
        self.XX(n0.hasAttributeNS(self.dc.ns_uri, self.dc.at_name2))

        self.XX(n0.setAttribute(self.dc.at_name2, self.dc.at_value2))
        self.XX(n0.getAttribute(self.dc.at_name2, castAs=str))
        self.XX(n0.removeAttribute(self.dc.at_name2))

        self.XX(n0.setAttributeNS(self.dc.ns_uri, self.dc.at_name2, self.dc.at_value2))
        self.XX(n0.getAttributeNS(self.dc.ns_uri, self.dc.at_name2, castAs=str))
        self.XX(n0.removeAttributeNS(self.dc.ns_uri, self.dc.at_name2))

        anode = self.n.doc.createAttribute("alist", "1")
        self.XX(n0.setAttributeNode(anode))
        self.XX(n0.getAttributeNode(self.dc.at_name2))
        self.XX(n0.removeAttributeNode(anode))

        self.XX(n0.setAttributeNodeNS(self.dc.ns_uri, anode))
        self.XX(n0.getAttributeNodeNS(self.dc.ns_uri, self.dc.at_name2))

        attrs = n0.attributes
        self.TY(attrs, NamedNodeMap)
        #DBG.dumpNode(n0, msg="attrs for getIndex")
        self.EQ(attrs.getIndexOf("alist"), 2)

        aname2 = self.dc.at_name2
        avalue2 = "aardvarks"
        self.XX(attrs.setNamedItem(aname2, avalue2))  # avalueAny,atype=str))
        self.XX(attrs.getNamedItem(aname2))
        self.EQ(attrs.getNamedValue(aname2), avalue2)
        self.XX(attrs.removeNamedItem(aname2))

        #self.XX(attrs.setNamedItemNS(self.dc.ns_uri, self.dc.at_name2, self.dc.at_value2))
        #self.XX(attrs.getNamedItemNS(self.dc.ns_uri, name))
        #self.XX(attrs.getNamedValueNS(self.dc.ns_uri, name))
        #self.XX(attrs.removeNamedItemNS(self.dc.ns_uri, name))

    def testWonkyIDs(self):
        cur = self.n.child2
        stackBuf = ""
        lastCh = None
        for i in range(5):
            ch = self.n.doc.createElement("deeper", { "id":f"idval_{i}" })
            stackBuf += f"/idval_{i}"
            cur.appendChild(ch)
            cur = ch
        self.EQ(cur.getStackedAttribute("id"), stackBuf)
        self.EQ(cur.getStackedAttribute("id", sep="%%%"), re.sub(r"/", "%%%", stackBuf))

        self.EQ(cur.getInheritedAttribute("id"), "idval_4")
        self.EQ(cur.getInheritedAttribute("no-such-id", default="x"), "x")
        self.XX(cur.getInheritedAttributeNS( self.dc.ns_uri, self.dc.at_name2))

    def testPredicates(self):
        n0 = self.n.child0
        n1 = self.n.child1
        n2 = self.n.child2
        d = self.n.docEl
        #self.XX(n0.hasChildNodes)
        self.FA(n0.hasDescendant(n2))
        self.TR(d.hasSubElements)
        self.TR(n0.hasTextNodes)
        self.TR(n0.isConnected)
        self.TR(n0.hasAttributes())
        self.TR(n0.hasAttribute(self.dc.at_name2))
        self.TR(n0.hasAttributeNS("", self.dc.at_name2))

        self.FA(n0.isAttribute)
        self.FA(n0.isCDATA)
        self.FA(n0.isComment)
        self.FA(n0.isDocument)
        self.FA(n0.isDocumentType)
        self.TR(n0.isElement)
        self.FA(n0.isEntRef)
        self.FA(n0.isFragment)
        self.FA(n0.isNotation)
        self.FA(n0.isPI)
        self.FA(n0.isText)

        self.TR(n0.getAttributeNode(self.dc.at_name2).isAttribute)
        self.TR(n0.childNodes[0].isTextNode)

        self.FA(n0.isWSN)
        self.FA(n0.isWhitespaceInElementContent)

        self.TR(n0.isDefaultNamespace(uri))

        self.FA(n0.isEqualNode(n1))
        self.FA(n0.isSameNode(n2))

        self.TR(n0.isFirstChild())
        self.TR(n2.isLastChild())
        self.FA(n2.isFirstChild())
        self.FA(n0.isLastChild())

        #self.TR(isNamespaceURI(self.dc.ns_uri))
        #self.XX(n0.isSupported())

    def testBadNames(self):
        n0 = self.n.child0
        n1 = self.n.child1
        n2 = self.n.child2
        doc = self.n.doc
        d = self.n.docEl
        n = self.n.child1
        badChars = "!@#$%^&*()/<>{}[];'?+=~`•"
        rbd = badChars[random.randrange(0, len(badChars))]
        badName = f"oops{rbd}ie"

        #self.RZ(ICE, self.n.impl.createDocument, self.n.ns_uri, badName, None)
        #self.RZ(ICE, doc.createElement, badName)
        self.RZ(ICE, doc.createAttribute, badName, "999")
        self.RZ(ICE, doc.createDocumentFragment, self.dc.ns_uri, badName)
        #self.RZ(ICE, doc.createDocumentType, badName, "", "")
        #self.RZ(ICE, doc.createEntityReference, badName, "\u2022")
        self.RZ(ICE, doc.createProcessingInstruction, badName, "p i d a t a ")

        self.XX(n0._addNamespace(name, uri=""))
        #self.XX(n0._findAttr(self.dc.ns_uri, tgtName))
        #self.XX(n0._presetAttr(self.dc.at_name2, self.dc.at_value2))
        #self.XX(n0._string2doc(self.dc.xml))
        #self.XX(nameMatch(n2, self.dc.target_name, self.dc.ns_uri))
        #self.XX(n0.nodeNameMatches(other))
        self.XX(n0.lookupNamespaceURI(prefix))
        self.XX(n0.getElementById(badName))  # ???
        fo = FormatOptions(indent="____", quoteChar="'", newl="\r\n")
        self.RZ(ICE, fo.setInlines, [ badName ])

        if (False):  # Only once I enable __getitem__()
            self.XX(d[badName])
            self.XX(d["@"+badName])
            self.XX(d["#"+badName])

        #DBG.dumpNode(n1, "n1 got attrs?")
        self.FA(n1.hasAttributes())
        self.RZ(ICE, n0.hasAttribute, badName)
        #self.RZ(ICE, n0.hasAttributeNS, self.dc.ns_uri, badName)

        self.RZ(ICE, n0.setAttribute, badName, self.dc.at_value2)
        self.RZ(ICE, n0.getAttribute, badName, castAs=str)
        self.RZ(ICE, n0.removeAttribute, badName)

        self.RZ(ICE, n0.setAttributeNS, self.dc.ns_uri, badName, self.dc.at_value2)
        self.RZ(ICE, n0.getAttributeNS, self.dc.ns_uri, badName)
        self.RZ(ICE, n0.removeAttributeNS, self.dc.ns_uri, badName)

        self.RZ(ICE, self.n.doc.createAttribute, badName, "1")
        #self.RZ(ICE, n0.setAttributeNode, anode)
        #self.RZ(ICE, n0.getAttributeNode, badName)
        #self.RZ(ICE, n0.removeAttributeNode, anode)
        #self.RZ(ICE, n0.setAttributeNodeNS, self.dc.ns_uri, anode)
        self.RZ(ICE, n0.getAttributeNodeNS, self.dc.ns_uri, badName)

        nnm = NamedNodeMap()
        self.RZ(ICE, nnm.setNamedItem, badName, "999")
        self.RZ(ICE, nnm.setNamedItemNS, self.dc.ns_uri, badName, self.dc.at_value2)

        #self.NONE(nnm.getNamedItem, badName)
        #self.NONE(nnm.getNamedItemNS(self.dc.ns_uri, badName))  # TODO Finish/enable
        self.NONE(nnm.getNamedValue(badName))
        #self.NONE(nnm.getNamedValueNS(self.dc.ns_uri, badName))
        self.RZ(KeyError, nnm.removeNamedItem, badName)
        #self.RZ(ICE, nnm.removeNamedItemNS, self.dc.ns_uri, badName)

    def testXStr(self):
        allNS = XStr.allNameStartChars()
        allNCA = XStr.allNameCharAddls()
        allNC = XStr.allNameChars()
        self.EQ(len(allNS), 54001)
        self.EQ(len(allNCA), 127)
        self.EQ(len(allNC), 54128)

        self.TR(XStr.isXmlName("Rainbow.1"))
        self.TR(XStr.isXmlQName("lb"))
        self.TR(XStr.isXmlQName("tei:lb"))
        self.TR(XStr.isXmlPName("svg:g"))
        self.TR(XStr.isXmlNmtoken("-foo-"))
        self.TR(XStr.isXmlNumber("0123456789"))

        self.FA(XStr.isXmlName("Rain•bow'1"))
        self.FA(XStr.isXmlQName("2lb"))
        self.FA(XStr.isXmlQName("tei:lb:c"))  # ???
        self.FA(XStr.isXmlPName("g"))
        self.FA(XStr.isXmlPName("1svg:g"))
        self.FA(XStr.isXmlNmtoken("-f#o-"))
        self.FA(XStr.isXmlNumber("abc"))
        self.FA(XStr.isXmlNumber("{}"))

        self.TR(XStr.escapeAttribute(s, quoteChar='"'))
        self.TR(XStr.escapeText(s, escapeAllGT=False))
        self.TR(XStr.escapeCDATA(s, replaceWith="]]&gt;"))
        self.TR(XStr.escapeComment(s, replaceWith="-&#x2d;"))
        self.TR(XStr.escapePI(s, replaceWith="?&gt;"))
        self.TR(XStr.escapeASCII(s, width=4, base=16, htmlNames=True))
        #self.TR(XStr.escASCIIFunction(mat))

        self.TR(XStr.dropNonXmlChars(s))
        self.TR(XStr.unescapeXml(s))
        #self.TR(XStr.unescapeXmlFunction(mat))
        self.TR(XStr.normalizeSpace(s, allUnicode=False))
        self.TR(XStr.stripSpace(s, allUnicode=False))

        self.TR(XStr.makeStartTag("spline", attrs="", empty=False, sort=False))
        self.TR(XStr.dictToAttrs({ "id":"foo", "border":"border" },
            sort=True, normValues=False))
        self.TR(XStr.makeEndTag(name))

        self.EQ(XStr.getLocalPart("foo:bar"), "bar")
        self.EQ(XStr.getPrefixPart("foo:bar"), "foo")

        failed = []
        for c in allNS:
            if (not XStr.isXmlName(c+"restOfName")):
                failed.append("U+%04x" % (ord(c)))
        if (failed):
            self.RZ(ICE, print("Chars should be namestart but aren't: [ %s ]"
                % (" ".join(failed))))

        failed = []
        for c in allNCA:
            if (XStr.isXmlName(c+"restOfName")):
                failed.append("U+%04x" % (ord(c)))
        if (failed):
            self.RZ(ICE, print("Chars should not be namestart but are: [ %s ]"
                % (" ".join(failed))))

        self.TR(XStr.isXmlName(allNS*2))

        self.TR(XStr.isXmlName("A"+allNC))


if __name__ == '__main__':
    unittest.main()
