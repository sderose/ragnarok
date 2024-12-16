#!/usr/bin/env python3
#
#pylint: disable=W0201, C2801, W0612, W0212
#
# TODO: Group classes by source standard
#
#pylint: disable=W0401,W0611,W0621
import sys
#import os
import unittest
#import math
import random
import re
#import unicodedata
#from collections import defaultdict
#from typing import List

from basedomtypes import HReqE, ICharE, NSuppE, NodeType
#from basedomtypes import NotFoundError
from xmlstrings import NameTest, WSHandler, CaseHandler, UNormHandler
from xmlstrings import XmlStrings as XStr

import basedom
from basedom import DOMImplementation, FormatOptions, _CanonicalFO
from basedom import PlainNode, Node, Document, Element, Attr
from basedom import CharacterData, Text, NamedNodeMap, NodeList

from documenttype import DocumentType

from makeTestDoc import makeTestDoc0, makeTestDoc2, DAT, DBG

s = "Lorem ipsum dolor sit amet"
name = "some.Name"
prefix = "foo"
uri = "https://example.com/random/uris"

descr = """
Test to add:

Integrate __getitem__

==Namespaces==
    createDocument w/ ns

==Doctypes==
    Test all the XSD datatypes
    createDocument with doctype
    Hook up createDocumentType
    registerDOMImplementation
    getImplementation

==other==
    formatOptions inlineTags, bad option, type mismatch, setInlines HTML and Docbook

NodeList

PlainNode
    getChildIndex / getRChildIndex fail
    _resetinheritedNS bad
    isEqualNode w/ each mismatch -- nodeName, path len, no/one/!= attrs
    cloneNode N/A
    _expandChildArg bad int
    clear N/A
    reverse
    reversed
    getInterface OBS
    isSupported OBS
    textContent N/A
    textContent setter N/A

Node
    bool on CharacterData* and Attr
    lt/le/ge/gt
    compareDocumentPosition different doc, other not connected, diff path lengths
    lookupPrefix w/ inheritance
    replaceChild w/ swapped args
    hasSubElements w/ only non-elements
    hasTextNodes w/ only non-text
    outerXML.setter N/A
    __reduce__ / __reduce__ex__
    getNodeSteps N/A to Node
    getNodeSteps for Attr
    getNodeSteps w/ wsn:bool=False FAIL
    useNodeSteps, useNodePath w/ bogus types, extra steps past non-elem
    before/after w/ strings                 LOTS
    after last item
    replaceWith                             LOTS
    eachChild                               LOTS
    eachNode w/ separateAttributes=True
    eachSaxEvent, incl. separateAttributes  LOTS

Document
    construct w/ qualifiedName
    clear N/A
    createDocumentFragment
    getXmlDcl w/ bad
    doctypeDcl w/ doctype
    _buildIndex, _buildIdIndex
    getElementsByTagName &c
    getElementsByTagNameNS &c
    getElementsByClassName &c
    checkNode

Element
    _addNamespace w/ bad prefix;/name
    namespaceURI w/ inheritance
    innerXML w/ non-WF.

cleanText w/ each UNormHandler and spaceNorm

Attr
    prefix, namespaceURI, nodeValue, textContent (and setters)
    nextSibling previousSibling next previous isFirstChild isLastChild
    getChildIndex compareDocumentPosition N/A
    isConnected

NamedNodeMap
    eq, ne
    setNamedItem bad args
    getNamedValueNS removeNamedItemNS
    item tostring clone (???) clear
    getIndexOf FAIL

NameSpaces
    [all]

Serializers on all node types
    toxml
    writexml
    tocanonicalxml
    toprettyxml

Non-child, bad index, non-Node
    insertBefore
    insertAfter
    insert
    __contains__
    __delitem__
    isEqualNode
    removeChild
    isSameNode
    isEqualNode
    append
    insert
    _filterOldInheritedNS                   LOTS
    pop
    __imul__ mul < 0
    deleteData, insertData, replaceData, substringData bad offset
    characterdata.remove w/ arg

DomBuilder
    parse, for non-file, bad type
    parse_string for non-string
    isCurrent isOpen ind
    handlers w/ ns
    AttrHandler w/ dup
    EndElementHandler fails
    CharacterDataHandler outside element
    all dcl handlers
    bad xml dcls
"""


class testByMethod(unittest.TestCase):
    def XX(self, *_args, **_kwargs):
        return

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
        impl = self.n.impl
        doc = self.n.doc

        self.assertIsInstance(self.n.impl.createDocument(
            self.dc.ns_uri, self.dc.root_name, doctype=None), Document)

        #self.assertIsInstance(
        #    doc.createDocumentFragment(self.n.ns_uri, qualifiedName="frag",
        #        doctype=None), basedom.DocumentFragment)
        self.assertIsInstance(impl.createDocumentType("html", None, None), DocumentType)
        self.assertIsInstance(doc.createAttribute("style", "font-weight:bold;"), Attr)
        self.assertIsInstance(doc.createCDATASection("icky][&<stuff"), basedom.CDATASection)
        self.assertIsInstance(doc.createComment(
            "this comment intentionally left blank"), basedom.Comment)
        self.assertIsInstance(doc.createElement("This_is.42."), Element)
        self.assertIsInstance(doc.createEntityReference(
            "bull", "\u2022"), basedom.EntityReference)
        self.assertIsInstance(doc.createProcessingInstruction(
            "piTarget", "p i d a t a "), basedom.PI)
        self.assertIsInstance(doc.createTextNode(" lorem ipsum"), basedom.Text)

        #with self.assertRaises(NotSupportedError): Node("self.dc.ns_uri", "abstraction")

    @unittest.skip
    def testWhatWGConstructors(self):
        from basedom import (CDATASection, Comment, ProcessingInstruction,
            EntityReference, NameSpaces)
        self.assertIsInstance(Document(), Document)
        self.assertIsInstance(Element("P27"), Element)
        self.assertIsInstance(Attr("alt", "A picture."), Attr)
        self.assertIsInstance(CharacterData("aardvark"), CharacterData)

        self.assertIsInstance(
            CDATASection(ownerDocument=self.n.doc, data="basilisk"), CDATASection)
        self.assertIsInstance(Text("catoblepas"), Text)
        self.assertIsInstance(Comment("dryad"), Comment)
        self.assertIsInstance(
            ProcessingInstruction("ettin", "fire giant"), ProcessingInstruction)
        self.assertIsInstance(
            EntityReference("chap1", "c:\\ents\\chapter1.xml"), EntityReference)

        self.assertIsInstance(NodeList(), NodeList)

        self.assertIsInstance(DOMImplementation(), DOMImplementation)
        self.assertIsInstance(FormatOptions(), FormatOptions)
        self.assertIsInstance(NameSpaces(), NameSpaces)
        self.assertIsInstance(NamedNodeMap(), NamedNodeMap)

    def testListBuiltins(self):
        n0 = self.n.child0
        n1 = self.n.child1
        n2 = self.n.child2
        ID_ATTR = "xml:id"
        for x in range(10):
            ch = self.n.doc.createElement(f"P_{x}",
                attributes={ ID_ATTR:"id_"+str(x), "width":"0.5" })
            n2.appendChild(ch)
            self.assertEqual(ch.parentNode, n2)
        self.assertEqual(n2.length, 10)
        #DBG.dumpNode(n2, msg="Attrs on 10 ch?")
        ch3 = n2[3]
        ch5 = n2[5]
        self.assertTrue(ch3.isElement and ch5.isElement)

        self.assertTrue(bool(n2))  # Empty element!
        self.n.docEl.sort(lambda x: x.nodeName, reverse=False)
        self.assertEqual(n2[0].getAttribute(ID_ATTR), "id_0")
        self.assertEqual(n2[0].getAttribute("width", castAs=float), 0.5)

        self.assertFalse(n0.__eq__(n1))
        self.assertTrue(n2.__eq__(n2))
        self.assertTrue(n1.__ne__(ch))
        self.assertTrue(ch3.__ne__(ch5))
        self.assertFalse(ch5.__le__(ch3))
        self.assertTrue(ch5.__ge__(ch3))
        self.assertTrue(ch5.__gt__(ch3))
        self.assertFalse(ch5.__gt__(ch5))

        self.assertFalse(n0 == n1)
        self.assertTrue(n2 == n2)
        self.assertTrue(n1 != ch)
        self.assertTrue(ch3 != ch5)
        self.assertTrue(ch5 >= ch3)
        self.assertFalse(ch3 > ch3)
        self.assertFalse(ch5 <= ch3)
        self.assertFalse(ch5 < ch3)

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
        self.assertEqual(len(zork), n1len + len(newList))
        self.assertTrue(zork.__contains__(ch))
        self.assertFalse(n0.__contains__(ch))
        zork.__delitem__(ch)
        self.assertFalse(zork.__contains__(ch))

        newList = NodeList()
        ch7 = None
        for x in range(10):
            ch = self.n.doc.createElement(f"P_{x}", attributes={ "seq":str(x) })
            if x == 7: ch7 = ch
            newList.append(ch)
        preLen = len(n0)

        nPlus = n0.__iadd__(newList)
        self.assertEqual(len(nPlus), preLen + len(newList))
        self.assertEqual(nPlus.count("P_5"), 1)
        with self.assertRaises(ValueError): nPlus.index("xyzzy", 2, -4)
        #DBG.dumpNode(nPlus, msg="nPlus")
        self.assertEqual(nPlus.index("P_6", 1, -2), 7)
        self.assertEqual(nPlus[2].nodeName, "P_1")

        nch = len(n0)
        n0.__imul__(2)
        self.assertEqual(len(n0), nch*2)

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
        #self.XX(n0._addNamespace(prefix+"2", uri=self.dc.ns_uri))
        #self.assertEqual(n0._expandChildArg(n1), (2, n1))

        newChild = self.n.doc.createElement("p")
        self.XX(n0._filterOldInheritedNS(newChild))
        #self.XX(n0._findAttr(self.dc.ns_uri, tgtName))
        self.assertEqual(self.n.doc._getXmlDcl(encoding="utf-8"),
            """<?xml version="1.0" encoding="utf-8"?>""")
        self.assertTrue(n0._isOfValue(self.dc.child0_name))
        #self.XX(n0._presetAttr(self.dc.at_name2, self.dc.at_value2))
        #self.XX(n0._resetinheritedNS())
        #self.XX(n0._startTag(empty=True, includeNS=False))
        #self.XX(n0._string2doc(self.dc.xml))
        self.XX(self.n.docEl.checkNode(deep=False))
        self.XX(self.n.docEl.checkNode(deep=True))
        self.XX(n0.getChildIndex(onlyElements=False, ofNodeName=False, noWSN=False))
        self.XX(n0.getRChildIndex(onlyElements=False, ofNodeName=False, noWSN=False))
        #self.XX(nameMatch(n2, self.dc.target_name, self.dc.ns_uri))
        #self.XX(n0._nodeNameMatches(other))
        #self.XX(n0.unlink(keepAttributes=False))
        #self.XX(wrapper(*args, **kwargs)

    def testBasicDOM(self):
        n0 = self.n.child0
        n1 = self.n.child1
        n2 = self.n.child2
        d = self.n.docEl
        self.assertTrue(n0.isElement and n1.isElement and n2.isElement and d.isElement)

        #self.RZ(AttributeError, n0.charset)
        self.assertEqual(self.n.doc.charset, "utf-8")
        self.assertEqual(len(n0.childNodes), 1)
        self.assertEqual(self.n.doc.contentType, "text/XML")
        #self.RZ(HReqE, n0.documentURI)
        self.assertFalse(self.n.doc.documentURI)

        self.XX(n0.cloneNode())
        self.assertNotEqual(n2, n2.cloneNode(deep=True))
        self.XX(n0.cloneNode(deep=False))
        #self.XX(n0.compareDocumentPosition(other))
        #self.XX(n0.domConfig())
        #self.XX(getImplementation())
        self.assertIs(n0.getRootNode(), self.n.doc)
        self.assertEqual(n0.ownerDocument.inputEncoding, "utf-8")
        self.assertEqual(d.length, 3)
        self.assertEqual(n0.localName, self.dc.child0_name)
        self.XX(n0.lookupNamespaceURI(prefix))
        self.XX(n0.lookupPrefix(uri))
        #self.XX(n0.name())
        self.assertEqual(n0.namespaceURI, None)
        self.assertEqual(n0.prefix, "")
        self.XX(n0.nodeValue)
        try:
            n0.nodeValue = "SomeReplacementText"
            self.assertEqual(n0, "Non-CharacterData don't take nodeValue assignment.")
        except AttributeError:
            pass
        self.assertEqual(n0.tagName, self.dc.child0_name)

    def testObsoleteDOM(self):
        n0 = self.n.child0
        n1 = self.n.child1
        n2 = self.n.child2
        udKey = "skeleton"
        udValue = "in the attrs"
        n0.setUserData(udKey, udValue, handler=None)
        self.assertEqual(n0.getUserData(udKey), udValue)
        #self.XX(n0.getInterface())
        #self.XX(n0.registerDOMImplementation(name, factory))

    def testSlices(self):
        n0 = self.n.child0
        n1 = self.n.child1
        n2 = self.n.child2
        for i in range(len(self.n.docEl)):
            self.assertEqual(self.n.docEl[i], self.n.docEl.childNodes[i])
        self.assertEqual(self.n.docEl[-2], self.n.docEl.childNodes[-2])
        self.assertEqual(self.n.docEl[0:2], self.n.docEl.childNodes[0:2])
        self.assertEqual(self.n.docEl[0:-1], self.n.docEl.childNodes[0:-1])

        # and __setitem__ -- which has to do all the right patching
        nl = NodeList()
        nnodes = 10
        for i in range(nnodes):
            nl.append(self.n.doc.createElement("newb"))
        self.assertEqual(len(nl), nnodes)

        self.n.docEl[1] = nl[0]
        # TODO Add many more cases
        self.assertFalse(n1.isConnected)
        self.n.docEl.checkNode(deep=True)

    def testTreeMutators(self):
        n0 = self.n.child0
        n1 = self.n.child1
        n2 = self.n.child2
        newChild = self.n.doc.createElement("p")
        newList = NodeList()
        for x in range(10):
            ch = self.n.doc.createElement("P_{x}", attributes={ "seq":str(x) })
            newList.append(ch)
        self.assertEqual(len(newList), 10)

        n0.after(newList)
        n0.append(newChild)
        with self.assertRaises(HReqE): n0.append(newChild)
        newChild2 = newChild.cloneNode()
        n0.appendChild(newChild2)

        newList = NodeList()
        for x in range(10):
            ch = self.n.doc.createElement("P2_{x}", attributes={ "seq":str(x) })
            newList.append(ch)
        self.XX(n0.before(newList))

        otherDocument = self.n.impl.createDocument(self.dc.ns_uri, "html", None)
        n1Copy = n0.cloneNode(deep=True)
        self.assertFalse(n1Copy.isConnected)
        #n1Copy.changeOwnerDocument(otherDocument)
        #self.assertEqual(n1Copy.ownerDocument, otherDocument)
        #with self.assertRaises(HReqE): n0.changeOwnerDocument(n2)

        newChild = self.n.doc.createElement("p")
        n0.insert(3, newChild)
        n0.insertAdjacentXML("beforebegin", self.dc.xml)
        n0.insertAdjacentXML("afterbegin", self.dc.xml)
        n0.insertAdjacentXML("beforeend", self.dc.xml)
        n0.insertAdjacentXML("afterend", self.dc.xml)
        #with self.assertRaises(ValueError): n0.insertAdjacentXML("xyzzy", self.dc.xml)

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
        self.assertEqual(len(newList), 10)
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
        self.assertEqual(tx.data, origText)
        self.assertEqual(tx.data, n2.textContent)
        tx.appendData(s)
        self.assertEqual(tx.data, origText+s)
        tx.insertData(0, "staht ")
        self.assertEqual(tx.data[0:6], "staht ")
        tx.deleteData(0, 3)
        self.assertEqual(tx.data[0:3], "ht ")
        tx.replaceData(0, 3, "ahting")
        self.assertEqual(tx.data[0:9], "ahtingsom")
        self.assertEqual(tx.substringData(4, 3), "ngs")

        with self.assertRaises(IndexError):
            tx.insertData(65537, "staht ")
            tx.deleteData(-35, 32767)
            tx.replaceData(999, 3, "ahting")

        origText = "  \tThe Quick\xA0\xA0Blue\rFox.  "
        expect = "The Quick\xA0\xA0Blue Fox."
        tx2 = self.n.doc.createTextNode(origText)
        self.assertEqual(tx2.cleanText(), expect)
        self.assertEqual(tx2.data, expect)

    def testTreeNeighbors(self):
        n0 = self.n.child0
        n1 = self.n.child1
        n2 = self.n.child2
        d = self.n.docEl
        self.assertTrue(d.contains(n1))
        self.assertEqual(n0.depth, 2)
        self.assertIs(d.firstChild, n0)
        self.assertIs(d.lastChild, n2)
        self.assertIs(n0.parentElement, d)
        self.assertIs(n2.previousSibling, n1)
        self.assertIs(n0.nextSibling.nextSibling, n2)
        self.assertIs(n2.nextSibling, None)
        self.assertIs(d.leftmost, n0.childNodes[0])
        self.assertIs(d.rightmost, n2)
        self.assertIs(n2.previous, n1.rightmost)
        self.assertIs(n0.next, n0.firstChild)

    def testSearchers(self):
        n0 = self.n.child0
        n1 = self.n.child1
        n2 = self.n.child2
        d = self.n.docEl
        doc = self.n.doc

        id1 = "theXIdValue"
        n1.setAttribute("xml:id", id1)
        #DBG.dumpNode(n1, msg="should have xml:id")
        id2 = "theIdValue"
        n2.setAttribute("id", id2)
        #DBG.dumpNode(n2, msg="should have id")

        doc.idHandler.clearIndex()
        doc.idHandler.addAttrChoice("##any", "*", "##any", "id")
        doc.idHandler.addAttrChoice("https://docbook.com", "chap", "##any", "idThing")
        doc.idHandler.delAttrChoice("https://docbook.com", "chap", "##any", "idThing")

        doc.idHandler.buildIdIndex()

        self.assertIs(doc.getElementById(id1), n1)
        self.assertIs(doc.getElementById(id2), n2)

        self.assertIsInstance(doc.getElementsByClassName("big"), NodeList)

        self.assertIsInstance(doc.getElementsByTagName("p"), NodeList)
        #self.assertIsInstance(doc.getElementsByTagNameNS("##any", "p"), NodeList)

        self.XX(d.eachChild(excludeNodeNames=["p"]))
        #self.XX(eachNode(self))

    def testIdStuff(self):
        doc = self.n.doc
        docEl = self.n.docEl

        # Add a bunch of nodes with ids
        idDiv = doc.createElement("idDiv")
        docEl.appendChild(idDiv)
        fan = 10
        for i in range(fan):
            idHolder = doc.createElement("p")
            if i < 5:
                idHolder.setAttribute("xml:id", f"idVal_{i}")
            else:
                idHolder.setAttribute("id", f"idVal_{i}")
            idDiv.appendChild(idHolder)
            txt = doc.createTextNode("hello.")
            idHolder.appendChild(txt)
        DBG.msg("\nDOC:\n" + doc.toprettyxml())

        # Traverse the doc and make an id:node dict
        idSec = self
        idMap = {}
        elementsFound = 0
        for n in docEl.eachNode():
            if not n.isElement: continue
            elementsFound += 1
            idValue = n.getAttribute("id")
            if not idValue: continue
            self.assertFalse(idValue in idMap)
            idMap[idValue] = n
        self.assertEqual(elementsFound, fan+5)
        self.assertEqual(len(idMap), fan+1)

        # Update the index
        doc.buildIndex()
        #doc.idHandler.addAttrChoice(ens="##any", ename="*", ans="##any", aname="id")
        #doc.idHandler.buildIdIndex()

        # Check that getElementById() can see them all
        self.assertIsInstance(doc.idHandler.theIndex, dict)
        self.assertGreater(len(doc.idHandler.theIndex), fan)
        idsFound = 0
        for idVal, theNode in idMap.items():
            self.assertFalse(idVal is None or theNode is None)
            if doc.getElementById(idVal) is theNode:
                idsFound += 1
            elif doc.getElementById(idVal) is not None:
                self.assertFalse(f"Id '{idVal}' points to wrong element.")
            else:
                self.assertFalse(f"Id '{idVal}' not found.")
        self.assertEqual(idsFound, len(idMap))

        # NS complications
        #self.assertIs(doc.getElementById("##any:"+id2), n2)
        #self.assertIsNone(doc.getElementById("no_ns:id"))
        #self.assertIsNone(doc.getElementById("no_such_id_value"))

        # TODO: Test IDs with other names, namespaces.
        # xml:id
        # self.doctype.

    def testTreeLoaders(self):
        n0 = self.n.child0
        n1 = self.n.child1
        n2 = self.n.child2
        filename_or_file = self.dc.sampleXmlPath
        #DBG.msg("Parsing file {filename_or_file}")
        self.n.impl.parse(filename_or_file, bufsize=5000)
        #self.n.impl.parse(filename_or_file)  # And with alt parser?
        #DBG.msg("Parsing string")
        self.n.impl.parse_string(self.dc.xml)
        #DBG.msg("Past parsing")

    def testSerializers(self):
        n0 = self.n.child0
        n1 = self.n.child1
        n2 = self.n.child2

        #self.RZ(AttributeError, n0.xmlDcl)
        self.assertEqual(n0.ownerDocument.xmlDcl,
            """<?xml version="1.0" encoding="utf-8"?>""")
        #self.XX(n0.doctypeDcl)
        st = n0.startTag
        self.assertTrue(st.startswith(f"<{self.dc.child0_name} "))
        #print(f"\nstartTag: {st}\n    an '{self.dc.at_name}' = av '{self.dc.at_value}'.")
        self.assertTrue(re.search(r" %s=\"%s\"" % (self.dc.at_name, self.dc.at_value), st))
        self.assertTrue(re.search(r" %s=\"%s\"" % (self.dc.at_name2, self.dc.at_value2), st))
        self.assertTrue(re.search(r" %s=\"%s\"" % (self.dc.at_name3, self.dc.at_value3), st))
        self.XX(n0.endTag, "</%s>" % (self.dc.child0_name))

        #self.XX(n0.innerXML)
        #self.XX(n0.innerXML = "")
        #self.XX(n0.outerXML)
        #self.XX(n0.outerXML = "")
        self.XX(n0.textContent)
        newData = "Just the text, ma'am."
        n0.textContent = newData
        self.assertEqual(n0.textContent, newData)
        self.XX(n0.tostring())
        self.XX(n0.collectAllXml())
        self.XX(n0.toxml())

        fo = FormatOptions(indent="____", quoteChar="'", newl="\r\n")
        fo.setInlines(None)
        self.XX(self.n.docEl.toprettyxml(foptions=fo))
        self.XX(self.n.docEl.toprettyxml(foptions=_CanonicalFO))

        # TODO Add a serious test of canonicity

        print("\n\n" + "="*79
            + "\n####### writexml output (test5ByMethod testSerializers):")
        self.XX(n0.writexml(sys.stderr, indent="   ", addindent="   ", newl="\n"))

    def testPointers(self):
        n0 = self.n.child0
        n1 = self.n.child1
        n2 = self.n.child2
        doc = self.n.doc
        self.XX(self.n.doc.idHandler.buildIdIndex())
        #self.XX(n0.getNodePath(useId, attrOk=False))
        #self.XX(n0.getNodeSteps(useId, attrOk=False, wsn=True))
        self.assertIsInstance(doc.useNodePath("1/1"), Text)
        self.assertEqual(doc.useNodeSteps([ 1, 1 ]).nodeName, "#text")

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
        self.assertEqual(nnc, 54128)

        for i in range(nAttrs):
            val = "zyz"+self.randChars(nameChars, nnc)
            n1.setAttribute(f"attr_{i}", val)
            n2.setAttributeNS("http://derose.net/namespaces/test", f"attr_{i}", val)
        self.assertEqual(len(n1.attributes), nAttrs)

        self.assertTrue(n1.hasAttributes())
        self.assertTrue(n0.hasAttribute(self.dc.at_name2))
        self.assertFalse(n0.hasAttribute("notMyAttributeFerSure"))
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
        self.assertIsInstance(attrs, NamedNodeMap)
        #DBG.dumpNode(n0, msg="attrs for getIndex")
        self.assertEqual(attrs.getIndexOf("alist"), 2)

        aname2 = self.dc.at_name2
        avalue2 = "aardvarks"
        self.XX(attrs.setNamedItem(aname2, avalue2))  # avalueAny,atype=str))
        self.XX(attrs.getNamedItem(aname2))
        self.assertEqual(attrs.getNamedValue(aname2), avalue2)
        self.XX(attrs.removeNamedItem(aname2))

        #self.XX(attrs.setNamedItemNS(self.dc.ns_uri, self.dc.at_name2, self.dc.at_value2))
        #self.XX(attrs.getNamedItemNS(self.dc.ns_uri, name))
        #self.XX(attrs.getNamedValueNS(self.dc.ns_uri, name))
        #self.XX(attrs.removeNamedItemNS(self.dc.ns_uri, name))

    def testPredicates(self):
        n0 = self.n.child0
        n1 = self.n.child1
        n2 = self.n.child2
        d = self.n.docEl
        #self.XX(n0.hasChildNodes)
        self.assertFalse(n0.hasDescendant(n2))
        self.assertTrue(d.hasSubElements)
        self.assertTrue(n0.hasTextNodes)
        self.assertTrue(n0.isConnected)
        self.assertTrue(n0.hasAttributes())
        self.assertTrue(n0.hasAttribute(self.dc.at_name2))
        self.assertTrue(n0.hasAttributeNS("", self.dc.at_name2))

    def testNodeTypePredicates(self):  # HERE
        n0 = self.n.child0
        n1 = self.n.child1
        n2 = self.n.child2
        self.assertFalse(n0.isAttribute)
        self.assertFalse(n0.isCDATA)
        self.assertFalse(n0.isComment)
        self.assertFalse(n0.isDocument)
        self.assertFalse(n0.isDocumentType)
        self.assertTrue(n0.isElement)
        self.assertFalse(n0.isEntRef)
        self.assertFalse(n0.isFragment)
        self.assertFalse(n0.isNotation)
        self.assertFalse(n0.isPI)
        self.assertFalse(n0.isText)

        self.assertTrue(n0.getAttributeNode(self.dc.at_name2).isAttribute)
        self.assertTrue(n0.childNodes[0].isTextNode)

        self.assertFalse(n0.isWSN)
        self.assertFalse(n0.isWhitespaceInElementContent)

        self.assertFalse(n0.isEqualNode(n1))
        self.assertFalse(n0.isSameNode(n2))

        self.assertTrue(n0.isFirstChild)
        self.assertTrue(n2.isLastChild)
        self.assertFalse(n2.isFirstChild)
        self.assertFalse(n0.isLastChild)

        #self.assertTrue(isNamespaceURI(self.dc.ns_uri))
        #self.XX(n0.isSupported())

        #self.assertTrue(n0.isDefaultNamespace(uri))

    def testWonkyAttrs(self):  # HERE
        cur = self.n.child2
        stackBuf = ""
        lastCh = None
        for i in range(5):
            ch = self.n.doc.createElement("deeper", { "id":f"idval_{i}" })
            stackBuf += f"/idval_{i}"
            cur.appendChild(ch)
            cur = ch
        self.assertEqual(cur.getStackedAttribute("id"), stackBuf)
        self.assertEqual(cur.getStackedAttribute("id", sep="%%%"), re.sub(r"/", "%%%", stackBuf))

        self.assertEqual(cur.getInheritedAttribute("id"), "idval_4")
        self.assertEqual(cur.getInheritedAttribute("no-such-id", default="x"), "x")
        self.XX(cur.getInheritedAttributeNS( self.dc.ns_uri, self.dc.at_name2))

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

        with self.assertRaises(ICharE):
            self.n.impl.createDocument(self.dc.ns_uri, badName, None)

        try:
            doc.createElement(badName)
        except ICharE:
            pass

        with self.assertRaises(ICharE):
            doc.createAttribute(badName, "999")
        with self.assertRaises(ICharE):
            doc.createDocumentFragment(self.dc.ns_uri, badName)
        with self.assertRaises(ICharE):
            doc.createEntityReference(badName, "\u2022")
        with self.assertRaises(ICharE):
            doc.createProcessingInstruction(badName, "p i d a t a ")

        self.XX(n0._addNamespace(name, uri=""))
        #self.XX(n0._findAttr(self.dc.ns_uri, tgtName))
        #self.XX(n0._presetAttr(self.dc.at_name2, self.dc.at_value2))
        #self.XX(n0._string2doc(self.dc.xml))
        #self.XX(nameMatch(n2, self.dc.target_name, self.dc.ns_uri))
        #self.XX(n0._nodeNameMatches(other))
        self.XX(n0.lookupNamespaceURI(prefix))
        self.XX(n0.getElementById(badName))  # ???
        fo = FormatOptions(indent="____", quoteChar="'", newl="\r\n")
        with self.assertRaises(ICharE):
            fo.setInlines([ badName ])

       #DBG.dumpNode(n1, "n1 got attrs?")
        self.assertFalse(n1.hasAttributes())
        with self.assertRaises(ICharE):
            n0.hasAttribute(badName)
        #with self.assertRaises(ICharE): n0.hasAttributeNS(self.dc.ns_uri, badName)

        with self.assertRaises(ICharE):
            n0.setAttribute(badName, self.dc.at_value2)
        with self.assertRaises(ICharE):
            n0.getAttribute(badName, castAs=str)
        with self.assertRaises(ICharE):
            n0.removeAttribute(badName)

        with self.assertRaises(ICharE):
            n0.setAttributeNS(self.dc.ns_uri, badName, self.dc.at_value2)
        with self.assertRaises(ICharE):
            n0.getAttributeNS(self.dc.ns_uri, badName)
        with self.assertRaises(ICharE):
            n0.removeAttributeNS(self.dc.ns_uri, badName)

        with self.assertRaises(ICharE):
            self.n.doc.createAttribute(badName, "1")
        #with self.assertRaises(ICharE): n0.setAttributeNode(anode)
        #with self.assertRaises(ICharE): n0.getAttributeNode(badName)
        #with self.assertRaises(ICharE): n0.removeAttributeNode(anode)
        #with self.assertRaises(ICharE): n0.setAttributeNodeNS(self.dc.ns_uri, anode)
        with self.assertRaises(ICharE):
            n0.getAttributeNodeNS(self.dc.ns_uri, badName)

        nnm = NamedNodeMap()
        with self.assertRaises(ICharE):
            nnm.setNamedItem(badName, "999")
        with self.assertRaises(ICharE):
            nnm.setNamedItemNS(self.dc.ns_uri, badName, self.dc.at_value2)

        #self.assertIsNone(nnm.getNamedItem, badName)
        #self.assertIsNone(nnm.getNamedItemNS(self.dc.ns_uri, badName))  # TODO Finish/enable
        self.assertIsNone(nnm.getNamedValue(badName))
        #self.assertIsNone(nnm.getNamedValueNS(self.dc.ns_uri, badName))
        with self.assertRaises(KeyError):
            nnm.removeNamedItem(badName)
        #with self.assertRaises(ICharE): nnm.removeNamedItemNS(self.dc.ns_uri, badName)

    @unittest.skip
    def testgetitem(self):
        d = self.n.docEl
        badChars = "!@#$%^&*()/<>{}[];'?+=~`•"
        rbd = badChars[random.randrange(0, len(badChars))]
        badName = f"oops{rbd}ie"
        self.XX(d[badName])
        self.XX(d["@"+badName])
        self.XX(d["#"+badName])

    def testCharacterDatas(self):
        """Try things that are special on these subclasses.
        """
        #pylint: disable=W0104
        doc = self.n.doc
        el = doc.createElement("_xyzzy_")
        pi = doc.createProcessingInstruction(
                          "my_Target", "No pi data was here")
        comm = doc.createComment      ("Nothing to see here")
        text = doc.createTextNode     ("Nothing to txt here")
        cdata = doc.createCDATASection("Nothing to tag here")
        chardata = CharacterData      ("No abstraction here")

        with self.assertRaises(AttributeError):
            pi._startTag
        with self.assertRaises(AttributeError):
            pi._endTag
        self.assertTrue(pi.hasChildNodes is False)
        self.assertTrue(pi.hasAttributes() is False)
        self.assertTrue(pi.hasAttribute("id") is False)
        self.assertTrue(pi.count("P") == 0)
        self.assertTrue(pi.index("P") is None)
        self.assertTrue(pi.clear() is None)
        with self.assertRaises(HReqE):
            pi.firstChild  # TODO Huh?
        with self.assertRaises(HReqE):
            pi.lastChild
        with self.assertRaises(AttributeError):
            pi.appendChild(el)
        with self.assertRaises(AttributeError):
            pi.prependChild(el)
        with self.assertRaises(AttributeError):
            pi.insertBefore(el)
        with self.assertRaises(AttributeError):
            pi.removeChild(el)
        with self.assertRaises(AttributeError):
            pi.replaceChild(el)
        with self.assertRaises(AttributeError):
            pi.append(el)
        with self.assertRaises(AttributeError):
            pi.__getitem__(0)
        self.assertFalse(pi.contains(el))
        self.assertEqual(pi.length, 19)
        self.assertEqual(pi.nodeValue, pi.data)

        with self.assertRaises(AttributeError):
            comm._startTag
        with self.assertRaises(AttributeError):
            comm._endTag
        self.assertTrue(comm.hasChildNodes is False)
        self.assertTrue(comm.hasAttributes() is False)
        self.assertTrue(comm.hasAttribute("id") is False)
        self.assertTrue(comm.count("P") == 0)
        self.assertTrue(comm.index("P") is None)
        self.assertTrue(comm.clear() is None)
        with self.assertRaises(HReqE):
            comm.firstChild
        with self.assertRaises(HReqE):
            comm.lastChild
        with self.assertRaises(AttributeError):
            comm.appendChild(el)
        with self.assertRaises(AttributeError):
            comm.prependChild(el)
        with self.assertRaises(AttributeError):
            comm.insertBefore(el)
        with self.assertRaises(AttributeError):
            comm.removeChild(el)
        with self.assertRaises(AttributeError):
            comm.replaceChild(el)
        with self.assertRaises(AttributeError):
            comm.append(el)
        with self.assertRaises(AttributeError):
            comm.__getitem__(0)
        self.assertFalse(comm.contains(el))
        self.assertEqual(comm.length, 19)
        self.assertEqual(comm.nodeValue, comm.data)

        with self.assertRaises(AttributeError):
            text._startTag
        with self.assertRaises(AttributeError):
            text._endTag
        self.assertTrue(text.hasChildNodes is False)
        self.assertTrue(text.hasAttributes() is False)
        self.assertTrue(text.hasAttribute("id") is False)
        self.assertTrue(text.count("P") == 0)
        self.assertTrue(text.index("P") is None)
        self.assertTrue(text.clear() is None)
        with self.assertRaises(HReqE):
            text.firstChild
        with self.assertRaises(HReqE):
            text.lastChild
        with self.assertRaises(AttributeError):
            text.appendChild(el)
        with self.assertRaises(AttributeError):
            text.prependChild(el)
        with self.assertRaises(AttributeError):
            text.insertBefore(el)
        with self.assertRaises(AttributeError):
            text.removeChild(el)
        with self.assertRaises(AttributeError):
            text.replaceChild(el)
        with self.assertRaises(AttributeError):
            text.append(el)
        with self.assertRaises(AttributeError):
            text.__getitem__(0)
        self.assertFalse(text.contains(el))
        self.assertEqual(text.length, 19)
        self.assertEqual(text.nodeValue, text.data)

        with self.assertRaises(AttributeError):
            cdata._startTag
        with self.assertRaises(AttributeError):
            cdata._endTag
        self.assertTrue(cdata.hasChildNodes is False)
        self.assertTrue(cdata.hasAttributes() is False)
        self.assertTrue(cdata.hasAttribute("id") is False)
        self.assertTrue(cdata.count("P") == 0)
        self.assertTrue(cdata.index("P") is None)
        self.assertTrue(cdata.clear() is None)
        with self.assertRaises(HReqE):
            cdata.firstChild
        with self.assertRaises(HReqE):
            cdata.lastChild
        with self.assertRaises(AttributeError):
            cdata.appendChild(el)
        with self.assertRaises(AttributeError):
            cdata.prependChild(el)
        with self.assertRaises(AttributeError):
            cdata.insertBefore(el)
        with self.assertRaises(AttributeError):
            cdata.removeChild(el)
        with self.assertRaises(AttributeError):
            cdata.replaceChild(el)
        with self.assertRaises(AttributeError):
            cdata.append(el)
        with self.assertRaises(AttributeError):
            cdata.__getitem__(0)
        self.assertFalse(cdata.contains(el))
        self.assertEqual(cdata.length, 19)
        self.assertEqual(cdata.nodeValue, cdata.data)

        #with self.assertRaises(AttributeError):
        #    chardata._startTag
        #with self.assertRaises(AttributeError):
        #    chardata._endTag
        self.assertTrue(chardata.hasChildNodes is False)
        self.assertTrue(chardata.hasAttributes() is False)
        self.assertTrue(chardata.hasAttribute("id") is False)
        self.assertTrue(chardata.count("P") == 0)
        self.assertTrue(chardata.index("P") is None)
        self.assertTrue(chardata.clear() is None)

        newch = self.n.doc.createTextNode("Zoot")
        with self.assertRaises(HReqE):
            chardata.firstChild
        with self.assertRaises(HReqE):
            chardata.lastChild
        with self.assertRaises(AttributeError):
            chardata.appendChild(newch)
        with self.assertRaises(AttributeError):
            chardata.prependChild(newch)
        with self.assertRaises(AttributeError):
            chardata.insertBefore(newch, oldChild=el)
        with self.assertRaises(AttributeError):
            chardata.removeChild(el)
        with self.assertRaises(AttributeError):
            chardata.replaceChild(newch, oldChild=el)
        with self.assertRaises(AttributeError):
            chardata.append(newch)
        with self.assertRaises(AttributeError):
            chardata.__getitem__(0)
        self.assertFalse(chardata.contains(el))
        self.assertEqual(chardata.length, 0)
        self.assertEqual(chardata.nodeValue, chardata.data)


if __name__ == '__main__':
    unittest.main()
