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
from basedom import PlainNode, Node, Document, Element
from basedom import Attr, NamedNodeMap, NodeList

from makeTestDoc import makeTestDoc0, makeTestDoc2, DAT  #, DBG

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

    def EQ(self, first, second):
        return self.assertEqual(first, second)

    def NE(self, first, second):
        return self.assertNotEqual(first, second)

    def IS(self, first, second):
        return self.assertIs(first, second)

    def TY(self, first, second):
        return self.assertIsInstance(first, second)

    def RZ(self, first, fn, *args, **kwargs):
        assert(isinstance(first, type))
        print("assertRaises is weird...")
        return
        return self.assertRaises(first, *args, **kwargs)

class testByMethod(MyTestCase):
    def setUp(self):
        """Should make:
        <html xmlns:html="https://example.com/namespaces/foo">
            <child1 an_attr.name="this is an attribute value"
                class="c1 c2" id="docbook_id_17">
                Some text content.</child1>
            <child2>
                <grandchild></grandchild>
            </child2>
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

        #self.RZ(NotSupportedError, Node("self.dc.ns_uri", "abstraction"))

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
        n1 = self.n.child1
        n2 = self.n.child2
        n3 = self.n.child3
        d = self.n.docEl
        for x in range(10):
            ch = self.n.doc.createElement("P_{x}", attributes={ "seq":str(x) })
            n3.appendChild(ch)
        ch3 = n3[3]
        ch5 = n3[5]

        self.TR(n3.bool())  # Empty element!
        d.sort(lambda x: x.nodeName, reverse=False)
        self.TR(self.n.docEl[0].getAttribute("seq", "9"))
        d.clear()
        self.EQ(n3.length(), 10)

        self.FA(n1.__eq__(n2))
        self.TR(n3.__eq__(n3))
        self.FA(n2.__ne__(ch))
        self.TR(ch3.__ne__(ch5))
        self.TR(ch5.__ge__(ch3))
        self.FA(ch5.__gt__(ch3))
        self.FA(ch5.__le__(ch3))
        self.TR(ch5.__lt__(ch3))

        self.XX(n1.__reduce__())
        self.XX(n1.__reduce__ex__())

    def testListBasics(self):
        n1 = self.n.child1
        n2 = self.n.child2
        n3 = self.n.child3
        newList = NodeList()
        for x in range(10):
            ch = self.n.doc.createElement("P_{x}", attributes={ "seq":str(x) })
            newList.append(ch)
        newList2 = newList.copy()

        n1len = len(n1)
        n1.__add__(newList)  # TODO Should this work?
        self.EQ(len(n1), n1len + len(newList))
        self.TR(n1.__contains__(ch))
        n1.__delitem__(ch)
        self.FA(n1.__contains__(ch))
        #self.XX(n1.__getitem__(-2)
        self.XX(n1.__iadd__())

        nch = len(n1)
        n1.__imul__(2)
        self.EQ(len(n1), nch*2)

        self.XX(n1.__mul__(2))
        self.XX(n1.__rmul__(2))

        #self.XX(n1.__setitem__(prefix, uri))

        self.XX(n1.count(x))
        self.XX(n1.getIndexOf(name))
        self.XX(n1.index(x, 1, -2))
        self.XX(n1.item(2))
        self.XX(n1.pop(i=-1))
        #self.XX(n1.reverse())
        #self.XX(n1.reversed())

    def testInternals(self):
        n1 = self.n.child1
        n2 = self.n.child2
        n3 = self.n.child3
        #prefix = "foo"
        #self.XX(n1.initOptions())
        #self.XX(n1.NOTYET__getitem__())
        #self.XX(n1._addNamespace(prefix+"2", uri=self.dc.ns_uri))
        #self.EQ(n1._expandChildArg(n2), (2, n2))

        newChild = self.n.doc.createElement("p")
        self.XX(n1._filterOldInheritedNS(newChild))
        #self.XX(n1._findAttr(self.dc.ns_uri, tgtName))
        self.EQ(self.n.doc._getXmlDcl(encoding="utf-8"),
            """<?xml version="1.0" encoding="utf-8"?>\n""")
        self.TR(n1._isOfValue(self.dc.child1_name))
        #self.XX(n1._presetAttr(self.dc.at_name2, self.dc.at_value2))
        #self.XX(n1._resetinheritedNS())
        #self.XX(n1._startTag(empty=True, includeNS=False))
        #self.XX(n1._string2doc(self.dc.xml))
        self.XX(self.n.docEl.checkNode(deep=False))
        self.XX(self.n.docEl.checkNode(deep=True))
        self.XX(n1.getChildIndex(onlyElements=False, ofNodeName=False, noWSN=False))
        self.XX(n1.getRChildIndex(onlyElements=False, ofNodeName=False, noWSN=False))
        #self.XX(nameMatch(n3, self.dc.target_name, self.dc.ns_uri))
        #self.XX(n1.nodeNameMatches(other))
        #self.XX(n1.unlink(keepAttributes=False))
        #self.XX(wrapper(*args, **kwargs)

    def testBasicDOM(self):
        n1 = self.n.child1
        n2 = self.n.child2
        n3 = self.n.child3
        d = self.n.docEl
        #self.RZ(AttributeError, n1.charset)
        self.EQ(self.n.doc.charset, "utf-8")
        self.EQ(len(n1.childNodes), 1)
        self.EQ(self.n.doc.contentType, "text/XML")
        #self.RZ(HRE, n1.documentURI)
        self.FA(self.n.doc.documentURI)

        self.XX(n1.clone())
        self.EQ(n3, n3.cloneNode(deep=True))
        self.XX(n1.cloneNode(deep=False))
        #self.XX(n1.compareDocumentPosition(other))
        #self.XX(n1.domConfig())
        #self.XX(getImplementation())
        self.IS(n1.getRootNode(), self.n.docEl)
        self.EQ(n1.inputEncoding, "utf-8")
        self.EQ(d.length(), 3)
        self.EQ(n1.localName, self.dc.child1_name)
        self.XX(n1.lookupNamespaceURI(prefix))
        self.XX(n1.lookupPrefix(uri))
        #self.XX(n1.name())
        self.XX(n1.namespaceURI)
        self.EQ(n1.prefix, "")
        self.XX(n1.nodeValue)
        n1.nodeValue = "SomeReplacementText"
        self.EQ(n1.tagName, self.dc.child1_name)

    def testObsoleteDOM(self):
        n1 = self.n.child1
        n2 = self.n.child2
        n3 = self.n.child3
        udKey = "skeleton"
        udValue = "in the attrs"
        n1.setUserData(udKey, udValue, handler=None)
        self.EQ(n1.getUserData(udKey), udValue)
        #self.XX(n1.getInterface())
        #self.XX(n1.registerDOMImplementation(name, factory))

    def testTreeMutators(self):
        n1 = self.n.child1
        n2 = self.n.child2
        n3 = self.n.child3
        newChild = self.n.doc.createElement("p")
        newList = NodeList()
        for x in range(10):
            ch = self.n.doc.createElement("P_{x}", attributes={ "seq":str(x) })
            newList.append(ch)
        self.EQ(len(newList), 10)

        n1.after(newList)
        n1.append(newChild)
        self.RZ(HRE, n1.append, newChild)
        newChild2 = newChild.cloneNode()
        n1.appendChild(newChild2)

        newList = NodeList()
        for x in range(10):
            ch = self.n.doc.createElement("P2_{x}", attributes={ "seq":str(x) })
            newList.append(ch)
        self.XX(n1.before(newList))

        otherDocument = self.n.impl.createDocument(self.dc.ns_uri, "html", None)
        n1Copy = n1.cloneNode(deep=True)
        self.FA(n1Copy.isConnected)
        #n1Copy.changeOwnerDocument(otherDocument)
        #self.EQ(n1Copy.ownerDocument, otherDocument)
        #self.RZ(HRE, n1.changeOwnerDocument(n3))

        newChild = self.n.doc.createElement("p")
        n1.insert(3, newChild)
        n1.insertAdjacentXML("beforebegin", self.dc.xml)
        n1.insertAdjacentXML("afterbegin", self.dc.xml)
        n1.insertAdjacentXML("beforeend", self.dc.xml)
        n1.insertAdjacentXML("afterend", self.dc.xml)
        n1.insertAdjacentXML("xyzzy", self.dc.xml)
        n1.insertAfter(newChild, n1.childNodes[3])
        newChild2 = newChild.cloneNode()
        n1.insertBefore(newChild2, -2)
        newChild3 = newChild.cloneNode()
        n1.insertAfter(newChild3, 0)
        newChild4 = newChild.cloneNode()
        self.XX(n1.insertBefore(newChild4, n1.childNodes[5]))

        oldChild = n1.childNodes[2]
        self.XX(n1.normalize())
        newChild5 = newChild.cloneNode()
        self.XX(n1.prependChild(newChild5))
        self.XX(n1.remove(newChild5))
        self.XX(n1.removeChild(oldChild))
        self.XX(n1.removeChild(3))
        self.XX(n1.removeNode())
        newChild6 = newChild.cloneNode()
        self.XX(n1.replaceChild(newChild6, oldChild))
        newChild7 = newChild.cloneNode()
        self.XX(n1.replaceChild(newChild7, -2))

        newList = NodeList()
        for x in range(10):
            ch = self.n.doc.createElement("P_{x}", attributes={ "seq":str(x) })
            newList.append(ch)
        self.EQ(len(newList), 10)
        newList2 = newList.copy()
        newList2.reverse()
        self.XX(n1.replaceWith(newList2))

    def testCharacterDataMutators(self):
        n1 = self.n.child1
        n2 = self.n.child2
        n3 = self.n.child3
        origText = "some initial text data"
        tx = self.n.doc.createTextNode(origText)
        n3.appendChild(tx)
        s = "[Extended Data]"
        self.EQ(tx.data, origText)
        self.EQ(tx.data, n3.textContent)
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
        n1 = self.n.child1
        n2 = self.n.child2
        n3 = self.n.child3
        d = self.n.docEl
        self.TR(d.contains(n2))
        self.EQ(n1.depth, 2)
        self.IS(d.firstChild, n1)
        self.IS(d.lastChild, n3)
        self.IS(n1.parentElement, d)
        self.IS(n3.previousSibling, n2)
        self.IS(n1.nextSibling.nextSibling, n3)
        self.IS(n3.nextSibling, None)
        self.IS(d.leftmost, n1.childNodes[0])
        self.IS(d.rightmost, n3)
        self.IS(n3.previous, n2.rightmost)
        self.IS(n1.next, n1.firstChild)

    def testSearchers(self):
        n1 = self.n.child1
        n2 = self.n.child2
        n3 = self.n.child3
        d = self.n.docEl
        n3.setAttribute("id", "theIdValue")
        self.XX(d.eachChild(excludeNodeNames=["p"]))
        #self.XX(eachNode(self))
        self.IS(n1.getElementById("theIdValue"), n3)
        self.TY(n1.getElementsByClassName("big"), NodeList)
        self.TY(n1.getElementsByTagName("p"), NodeList)
        self.TY(n1.getElementsByTagNameNS("p", "##any"), NodeList)

    def testTreeLoaders(self):
        n1 = self.n.child1
        n2 = self.n.child2
        n3 = self.n.child3
        filename_or_file = self.dc.sampleXmlPath
        self.n.impl.parse(filename_or_file, bufsize=5000)
        self.n.impl.parse(filename_or_file)  # And with alt parser?
        self.n.impl.parse(filename_or_file)
        n1.parse_string(self.dc.xml)
        n1.parse_string(self.dc.xml)

    def testSerializers(self):
        n1 = self.n.child1
        n2 = self.n.child2
        n3 = self.n.child3

        #self.RZ(AttributeError, n1.xmlDcl)
        self.EQ(n1.ownerDocument.xmlDcl,
            """<?xml version="1.0" encoding="utf-8"?>\n""")
        #self.XX(n1.docTypeDcl)
        st = n1.startTag
        self.TR(st.startswith(f"<{self.dc.child1_name} "))
        print("startTag: {st}")
        self.TR(re.match(r" %s=\"%s\"" % (self.dc.at_name, self.dc.at_value), st))
        self.TR(re.match(r" %s=\"%s\"" % (self.dc.at_name2, self.dc.at_value2), st))
        self.TR(re.match(r" %s=\"%s\"" % (self.dc.at_name3, self.dc.at_value3), st))
        self.XX(n1.endTag, "</%s>" % (self.dc.child1_name))

        #self.XX(n1.innerXML)
        #self.XX(n1.innerXML = "")
        #self.XX(n1.outerXML)
        #self.XX(n1.outerXML = "")
        self.XX(n1.textContent)
        newData = "Just the text, ma'am."
        n1.textContent = newData
        self.EQ(n1.textContent, newData)
        self.XX(n1.tostring())
        self.XX(n1.tostring(canonical=True))
        self.XX(n1.collectAllXml())
        self.XX(n1.toxml())

        fo = FormatOptions(indent="____", quoteChar="'", newl="\r\n")
        fo.setInlines(None)
        self.XX(self.n.docEl.toprettyxml(foptions=fo))
        self.XX(n1.writexml(sys.stderr, indent="   ", addindent="   ", newl="\n"))

    def testJSON(self):
        j = self.n.docEl.outerJSON()

    def testPointers(self):
        n1 = self.n.child1
        n2 = self.n.child2
        n3 = self.n.child3
        doc = self.n.doc
        self.XX(self.n.doc.buildIdIndex("*", "id"))
        #self.XX(n1.getNodePath(useId, attrOk=False))
        #self.XX(n1.getNodeSteps(useId, attrOk=False, wsn=True))
        self.TY(doc.useNodePath("1/1"), TextNode)
        self.EQ(doc.useNodeSteps([ 1, 1 ]).nodeName, "#text")

    def randChars(self, chars:str, nc:int, n:int=5):
        buf = ""
        for _ in range(n):
            buf += chars[random.randrange(0, nc)]
        return buf

    def testAttributeStuff(self):
        n1 = self.n.child1
        n2 = self.n.child2
        n3 = self.n.child3
        nAttrs = 257
        nameChars = XStr.allNameChars()
        nnc = len(nameChars)
        self.EQ(nnc, 54128)

        for i in range(nAttrs):
            val = "zyz"+self.randChars(nameChars, nnc)
            n2.setAttribute(f"attr_{i}", val)
            n3.setAttributeNS("http://derose.net/namespaces/test", f"attr_{i}", val)
        self.EQ(len(n2.attributes), nAttrs)

        self.TR(n2.hasAttributes)
        self.TR(n1.hasAttribute(self.dc.at_name2))
        self.FA(n1.hasAttribute("notMyAttributeFerSure"))
        self.XX(n1.hasAttributeNS(self.dc.ns_uri, self.dc.at_name2))

        self.XX(n1.setAttribute(self.dc.at_name2, self.dc.at_value2))
        self.XX(n1.getAttribute(self.dc.at_name2, castAs=str))
        self.XX(n1.removeAttribute(self.dc.at_name2))

        self.XX(n1.setAttributeNS(self.dc.ns_uri, self.dc.at_name2, self.dc.at_value2))
        self.XX(n1.getAttributeNS(self.dc.ns_uri, self.dc.at_name2, castAs=str))
        self.XX(n1.removeAttributeNS(self.dc.ns_uri, self.dc.at_name2))

        anode = self.n.doc.createAttribute("alist", "1")
        self.XX(n1.setAttributeNode(anode))
        self.XX(n1.getAttributeNode(self.dc.at_name2))
        self.XX(n1.removeAttributeNode(anode))

        self.XX(n1.setAttributeNodeNS(self.dc.ns_uri, anode))
        self.XX(n1.getAttributeNodeNS(self.dc.ns_uri, self.dc.at_name2))

        attrs = n1.attributes
        self.TY(attrs, NamedNodeMap)

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
        cur = self.n.child3
        stackBuf = ""
        lastCh = None
        for i in range(10):
            ch = self.n.doc.createElement("deeper", { "id":f"idval_{i}" })
            stackBuf += f"/idval_{i}"
            cur.appendChild(ch)
            cur = ch
        self.EQ(cur.getStackedAttribute("id"), stackBuf)
        self.EQ(cur.getStackedAttribute("id", sep="%%%"), re.sub(r"/", "%%%", stackBuf))

        self.EQ(cur.getInheritedAttribute("id"), "idval_9")
        self.EQ(cur.getInheritedAttribute("no-such-id", default="x"), "x")
        self.XX(cur.getInheritedAttributeNS( self.dc.ns_uri, self.dc.at_name2))

    def testPredicates(self):
        n1 = self.n.child1
        n2 = self.n.child2
        n3 = self.n.child3
        d = self.n.docEl
        #self.XX(n1.hasChildNodes)
        self.FA(n1.hasDescendant(n3))
        self.TR(d.hasSubElements)
        self.TR(n1.hasTextNodes)
        self.TR(n1.isConnected)
        self.TR(n1.hasAttributes())
        self.TR(n1.hasAttribute(self.dc.at_name2))
        self.TR(n1.hasAttributeNS("", self.dc.at_name2))

        self.FA(n1.isAttribute)
        self.FA(n1.isCDATA)
        self.FA(n1.isComment)
        self.FA(n1.isDocument)
        self.FA(n1.isDocumentType)
        self.TR(n1.isElement)
        self.FA(n1.isEntRef)
        self.FA(n1.isFragment)
        self.FA(n1.isNotation)
        self.FA(n1.isPI)
        self.FA(n1.isText)

        self.TR(n1.getAttributeNode(self.dc.at_name2).isAttribute)
        self.TR(n1.childNodes[0].isTextNode)

        self.FA(n1.isWSN)
        self.FA(n1.isWhitespaceInElementContent)

        self.TR(n1.isDefaultNamespace(uri))

        self.FA(n1.isEqualNode(n2))
        self.FA(n1.isSameNode(n3))

        self.TR(n1.isFirstChild())
        self.TR(n3.isLastChild())
        self.FA(n3.isFirstChild())
        self.FA(n1.isLastChild())

        #self.TR(isNamespaceURI(self.dc.ns_uri))
        #self.XX(n1.isSupported())

    def testBadNames(self):
        n1 = self.n.child1
        n2 = self.n.child2
        n3 = self.n.child3
        doc = self.n.doc
        d = self.n.docEl
        n = self.n.child2
        badChars = "!@#$%^&*()/<>{}[];'?+=~`•"
        rbd = badChars[random.randrange(0, len(badChars))]
        badName = f"oops{rbd}ie"

        self.RZ(ICE, doc.createElement(badName))
        self.RZ(ICE, doc.createAttribute(badName, "999"))
        self.RZ(ICE, doc.createDocument(self.n.ns_uri, badName, doctype=None))
        self.RZ(ICE, doc.createDocumentFragment(self.n.ns_uri, badName))
        self.RZ(ICE, doc.createDocumentType(badName, "", ""))
        self.RZ(ICE, doc.createEntityReference(badName, "\u2022"))
        self.RZ(ICE, doc.createProcessingInstruction(badName, "p i d a t a "))

        self.XX(n1._addNamespace(name, uri=""))
        #self.XX(n1._findAttr(self.dc.ns_uri, tgtName))
        #self.XX(n1._presetAttr(self.dc.at_name2, self.dc.at_value2))
        #self.XX(n1._string2doc(self.dc.xml))
        #self.XX(nameMatch(n3, self.dc.target_name, self.dc.ns_uri))
        #self.XX(n1.nodeNameMatches(other))
        self.XX(n1.lookupNamespaceURI(prefix))
        self.XX(d[badName])
        self.XX(d["@"+badName])
        self.XX(d["#"+badName])
        self.XX(n1.getElementById(badName))  # ???
        fo = FormatOptions(indent="____", quoteChar="'", newl="\r\n")
        fo.setInlines([ badName ])

        self.TR(n2.hasAttributes())
        self.TR(n1.hasAttribute(badName))
        self.RZ(ICE, n1.hasAttributeNS(self.dc.ns_uri, badName))

        self.RZ(ICE, n1.setAttribute(badName, self.dc.at_value2))
        self.RZ(ICE, n1.getAttribute(badName, castAs=str))
        self.RZ(ICE, n1.removeAttribute(badName))

        self.RZ(ICE, n1.setAttributeNS(self.dc.ns_uri, badName, self.dc.at_value2))
        self.RZ(ICE, n1.getAttributeNS(self.dc.ns_uri, badName))
        self.RZ(ICE, n1.removeAttributeNS(self.dc.ns_uri, badName))

        anode = self.n.doc.createAttribute(badName, "1")
        self.RZ(ICE, n1.setAttributeNode(anode))
        self.RZ(ICE, n1.getAttributeNode(badName))
        self.RZ(ICE, n1.removeAttributeNode(anode))

        self.RZ(ICE, n1.setAttributeNodeNS(self.dc.ns_uri, anode))
        self.RZ(ICE, n1.getAttributeNodeNS(self.dc.ns_uri, badName))

        self.RZ(ICE, n1.setNamedItem(badName, "999"))
        self.RZ(ICE, n1.setNamedItemNS(self.dc.ns_uri, badName, self.dc.at_value2))
        self.RZ(ICE, n1.getNamedItem(badName))
        self.RZ(ICE, n1.getNamedItemNS(self.dc.ns_uri, badName))
        self.RZ(ICE, n1.getNamedValue(badName))
        self.RZ(ICE, n1.getNamedValueNS(self.dc.ns_uri, badName))
        self.RZ(ICE, n1.removeNamedItem(badName))
        self.RZ(ICE, n1.removeNamedItemNS(self.dc.ns_uri, badName))

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
            sortAttributes=True, normValues=False))
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
