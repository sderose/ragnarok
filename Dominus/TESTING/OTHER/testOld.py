#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Exercise all DOM methods (I hope)....
#
#pylint: disable=W0613, W0212, W0603, W0641, W0123, W0703
#
import sys
import argparse
import string
import codecs
from collections import defaultdict
import xml

from xmlstrings import XmlStrings as XStr
import basedom
from basedom import getDOMImplementation, DOMImplementation, Node, NamedNodeMap
#Document, Element, Leaf, Text, \
#CDATASection, ProcessingInstruction, Comment, EntityReference, Notation,
#DocumentType, Attr, NodeList,

import dombuilder

descr = """
=Description=

Smoke-test DOM methods.

By default, this:

* only prints fail cases. Use `-v` for the rest.

* uses xml.dom.minidom. To test basedom instead, use `--basedom`.

* does only tests only methods that are included in `xml.dom.minidom`.
To test the basedom additions, use ``.

* does not test any of minidom's extension.
To test them, use `--testMinidomExtras`.


=References=

Actual DOM specs: [https://www.w3.org/DOM/DOMTR].

W3 test suites: [https://www.w3.org/DOM/Test/].

[https://developer.mozilla.org/en-US/docs/Web/API/Document_Object_Model/Introduction] claims to provide test examples for all DOM methods.


=Related Commands=

`testDomExtensions.py` -- similar, but to test my extensions.

=History=

* Written by Steven J. DeRose, ~Feb 2016.
* 2018-04-18: lint.
* 2019-12-30: Split out from basedom.
* 2020-01-20: Got to point of no crashing on entire minidom test.
* 2024-10-01: Start moving to unittest. Remove a lot covered elsewhere.


=Known bugs and limitations=

Lots of the tests don't do much yet.

Expected results are not yet included, which is kind of important.


=To do=

Finish.

Figure out how to hook up existing DOM test suites.


=Rights=

This work by Steven J. DeRose is licensed under a Creative Commons
Attribution-Share Alike 3.0 Unported License. For further information on
this license, see http://creativecommons.org/licenses/by-sa/3.0/.

For the most recent version, see [http://www.derose.net/steve/utilities] or
[http://github.com/sderose].

=Options=
"""

__metadata__ = {
    "title"        : "testDom",
    "rightsHolder" : "Steven J. DeRose",
    "creator"      : "http://viaf.org/viaf/50334488",
    "type"         : "http://purl.org/dc/dcmitype/Software",
    "language"     : "Python 3.7",
    "created"      : "2016-02-06",
    "modified"     : "2020-01-01",
    "publisher"    : "http://github.com/sderose",
    "license"      : "https://creativecommons.org/licenses/by-sa/3.0/"
}
__version__ = __metadata__["modified"]


FAIL_VALUE = -99999

domImpl = None
theOwnerDocument = None

# Set up "args" in case we're being called not as main. Caller can override.
#
args = argparse.Namespace(
    verbose = 0,
    useBaseDom = False,
    testMinidomExtras = False,    # The few additions minidom has
    testBaseDomAdditions = False, # To enable basedom but non-minidom tests
    testSelectors = False         # JQuery and similar selector support
)

# Sample Values
#
nsURI       = "http://derose.net/namespace/testNS",
nsPrefix    = "tst"
tagName     = "BLOCKQUOTE"
IDValue     = "chap1_id"
qname       = "foo:aDoc"
ukey        = "userDataKey"
udata       = "3.14159"
className   = "secret"
htmlSample  = """<p>The <i>quick</i> brown fox jumped the shark.</p>"""
someText    = "A bit more text."
someComment = "Quoth the walrus, 'Nevermore.'"
someCDATA   = "No need for escaping in here."
someTarget  = "myPITarget"
somePI      = "pi1='foo' xyzzy='plugh'"
entName     = "amp"
aname       = "class"
avalue      = "classy"

def fillDoc(docObj):  # TODO Move into makeTestDoc.
    """Use DOM to create a document from scratch, thus exercising the
    createXXX() methods.

    See also DomBuilder.
    """
    docEl = docObj.documentElement
    docEl.setAttribute("id", "rootID")
    docEl.setAttribute("class", "bigThing foo bar")
    docEl.setAttribute("style", "margin:10pt; font-size:12pt;")
    hed = docObj.createElement("HEAD")
    docEl.appendChild(hed)
    ttl = docObj.createElement("TITLE")
    hed.appendChild(ttl)
    txt = docObj.createTextNode("This is the title.")
    ttl.appendChild(txt)
    bod = docObj.createElement("BODY")
    docEl.appendChild(bod)
    div = docObj.createElement("DIV")
    bod.appendChild(div)
    hd1 = docObj.createElement("H1")
    hd1.setAttribute("CLASS", "myClass")
    hd1.setAttribute("STYLE", "font-weight:bold; font-size:24")
    hd1.setAttribute("QUOTES", '""""""""')
    hd1.setAttribute("ENTS", "&<[]>;")
    div.appendChild(hd1)

    par = docObj.createElement("P")
    par.setAttribute("id", "thePara")
    ita = docObj.createElement("i")
    tx1 = docObj.createTextNode("This is ")
    tx2 = docObj.createTextNode("very ")
    tx3 = docObj.createTextNode("important stuff.")
    com = docObj.createComment("A comment can have\na lot of text.")
    pro = docObj.createProcessingInstruction(
        "myTarget", "class=\"a\" medium=\"papyrus\"")

    ita.appendChild(tx2)
    par.appendChild(tx1)
    par.appendChild(ita)
    div.appendChild(com)
    par.appendChild(tx3)
    div.appendChild(pro)
    div.appendChild(par)


###############################################################################
#
def header(msg):
    print("\n******* Starting %s *******" % (msg))

def report(msg):
    sys.stderr.write(msg+"\n")

def showNamedNodeMap(nnm):
    n = len(nnm)
    for i in range(n):
        nod = nnm.item(i)
        print("    %-55s '%s'" % (nod.name, nod.value))


###############################################################################
#
def exercise(theDomImpl, docObj):
    docEl = docObj.documentElement

    header("exerciseNode")
    exerciseNode(docEl)

    header("exerciseDocument")
    exerciseDocument(docObj)
    header("exerciseDoctype")
    exerciseDoctype(docObj.doctype)
    header("exerciseElement")
    exerciseElement(docEl)

    return

def exerciseGetItem(self, docObj):
    n = docObj.documentElement

    self.assertIsInstance(n[0], Node)
    self.assertIsInstance(n[-1], Node)
    self.assertIsInstance(n['@id'], Node)
    self.assertIsInstance(n['@class'], Node)
    self.assertIsInstance(n['p'], Node)
    self.assertIsInstance(n['*'], Node)
    self.assertIsInstance(n['#text'], Node)
    self.assertIsInstance(n['#comment'], Node)
    self.assertIsInstance(n['#pi'], Node)

    self.assertIsInstance(n[0:-2], Node)
    self.assertIsInstance(n['p':2], Node)
    self.assertIsInstance(n[2:'p'], Node)
    self.assertIsInstance(n[2:8], Node)

    self.assertIsInstance(n['p':2:8], Node)
    self.assertIsInstance(n[2:8:'p'], Node)
    self.assertIsInstance(n[1:10:2], Node)

    # Fails
    self.assertIsNone(n[9999])
    self.assertIsNone(n[-9999])
    self.assertIsNone(n['@123'])
    self.assertIsNone(n['@no_such_attribute'])
    self.assertIsNone(n['xyzzy'])
    self.assertIsNone(n['*'])
    self.assertIsNone(n['#cdata'])
    self.assertIsNone(n['#spam'])
    self.assertIsNone(n['%$&'])

    self.assertIsNone(n[0:-9999])
    self.assertIsNone(n['p':9999])
    self.assertIsNone(n[0:'xyzzy'])
    self.assertIsNone(n[False:8])
    self.assertIsNone(n[0:3.14159])

    self.assertIsNone(n['p':2:9999])
    self.assertIsNone(n[-9999:8:'p'])
    self.assertIsNone(n[1:10:9999])

    return


###############################################################################
#
nodesSeen = None

def checkTreeStructure(n):
    """Check relation of Node to its parent, siblings, and children.
    """
    global nodesSeen
    nodesSeen = defaultdict(int)
    checkOneNode(n)

def checkOneNode(n):
    nodesSeen[n] += 1
    cur = n
    if (cur.nodeType==basedom.Node.ELEMENT_NODE):
        ls = cur.precedingSibling
        if (ls and ls.followingSibling!= cur):
            report("Bad sibling chain left")
        rs = cur.followingSibling
        if (rs and rs.precedingSibling!= cur):
            report("Bad sibling chain right")
        par = cur.parentNode
        if (par):
            found = 0
            for sib in par.childNodes:
                if (sib is cur): found += 1
            if (found != 1):
                report("Bad ancestor chain up")

        nch = len(cur.childNodes)
        if (nch == 0):
            if (cur.firstChild is not None):
                report("firstChild not None")
            if (cur.lsstChild is not None):
                report("latChild != childNodes[0]")
        else:
            if (cur.childNodes[0] != cur.firstChild):
                report("firstChild != childNodes[0]")
            if (cur.childNodes[-1] != cur.firstChild):
                report("lastChild != childNodes[-1]")
            chainChild = cur.childNodes[0]
            for i in range(len(cur.childNodes)):
                if (cur.childNodes[i] != chainChild):
                    report("Child list / chain toast")
                if (i==0 and cur.childNodes[i] is not None):
                    report("First child lsib not null")
                if (i>0 and
                    cur.childNodes[i].precedingSibling!=cur.childNodes[i-1]):
                    report("Child lsib wrong")
                if (i==nch-1 and cur.childNodes[i] is not None):
                    report("Last child rsib not null")
                if (i<nch-1 and
                    cur.childNodes[i].followingSibling!=cur.childNodes[i+1]):
                    report("Child rsib wrong")
                chainChild = chainChild.followingSibling

    for i in range(len(cur.childNodes)):
        checkOneNode(cur.childNodes[i])
    return


###############################################################################
#
def exerciseNode(self, n1):
    print("Exercising node, nodeType %d, nodeName %s." %
        (n1.nodeType, n1.nodeName))
    theDoc = n1.ownerDocument
    # basedom: Node.nameOfNodeType(n.nodeType)
    if (n1.ownerDocument != theDoc):
        report("Mismatched ownerDocument")

    n = n1
    n2 = n.ownerDocument.createElement("NEW_P")

    EQ = self.assertEqual

    EQ(theDoc.getElementById("thePara")            , 0)

    # R/O
    #EQ(n.hasIDAttribute(                          , 0)
    EQ(n.nodeName                                  , "P")
    EQ(n.cloneNode(deep=False)                     , 0)
    EQ(n.cloneNode(deep=True)                      , 0)
    #EQ(n.nodeCompare(n2)                          , 0)
    #EQ(n.getPath()                                , 0)
    #EQ(n.getMyIndex(onlyElements=True)            , 0)
    #EQ(n.getMyIndex(onlyElements=False)           , 0)
    #EQ(n.getFeature('OMNISCIENCE', '1.0')         , 0)
    #EQ(n.getUserData(ukey)                        , 0)
    EQ(n.hasAttributes()                           , 0)
    EQ(n.hasChildNodes()                           , 0)
    #EQ(n.isDefaultNamespace(nsURI)                , 0)
    #EQ(n.isEqualNode(n2)                          , 0)
    EQ(n.isSameNode(n)                             , 0)
    EQ(n.isSameNode(n2)                            , 0)
    #EQ(n.lookupNamespaceURI(nsURI)                , 0)
    #EQ(n.lookupPrefix(nsPrefix)                   , 0)

    # R/W
    EQ(n.appendChild(n2)                           , 0)
    EQ(n.insertBefore(n2, n.childNodes[1], )       , 0)
    EQ(n.normalize()                               , 0)
    EQ(n.removeChild(n.childNodes[1])              , 0)
    EQ(n.replaceChild(n2, n.childNodes[1])         , 0)
    EQ(n.setUserData(ukey, udata, handler=None)    , 0)

    #EQ("n.tostring()"                             , 0)


###############################################################################
#
def exerciseDocument(self, n):
    EQ = self.assertEqual

    EQ(n.createElement(tagName)                        , 0)
    EQ(n.createDocumentFragment()                      , 0)
    EQ(n.createTextNode(someText)                      , 0)
    EQ(n.createComment(someComment)                    , 0)
    EQ(n.createCDATASection(someCDATA)                 , 0)
    EQ(n.createProcessingInstruction(someTarget, somePI), 0)

    if (args.testBaseDomAdditions):
        attrs = { "id":"myId99", "alt":"some text" }
        EQ(n.charset()                         , 0)
        EQ(n.contentType()                     , 0)
        EQ(n.documentURI()                     , 0)
        EQ(n.domConfig()                       , 0)
        EQ(n.implementation()                  , 0)
        EQ(n.inputEncoding()                   , 0)
        EQ(n.createElement(tagName, attributes=attrs)  , 0)
        EQ(n.createEntityReference(entName)            , 0)
        EQ(n.tostring()                                , 0)

        #  "n.all()"                                    , 0),  # Obsolete


###############################################################################
#
def exerciseDoctype(self, n):
    EQ = self.assertEqual

    if (not n):
        print("    *** No doctype there ***")
        return
    if (n.ownerDocument):
        n2 = n.ownerDocument.createElement(tagName)
        EQ(n.isEqualNode(n2)               , 0)  # Doctype
        EQ(n.tostring()                    , 0)

    else:
        print("    *** doctype has no owner document ***")
        return

    print("Entities known:")
    showNamedNodeMap(n.entities)
    print("Notations known:")
    showNamedNodeMap(n.entities)

    if (args.testBaseDomAdditions):
        print("Elements known:")
        showNamedNodeMap(n.elements)
        print("Attributes known:")
        showNamedNodeMap(n.attributes)


###############################################################################
#
def exerciseElement(self, n):
    if (not XStr.isXmlName(n.nodeName)):
        report("Non XML Name")

    ns = "http://derose.net/namespace/testNS"
    n2 = None

    EQ = self.assertEqual

    EQ(n.getAttribute(aname)                      , 0)
    EQ(n.getAttributeNS(ns, aname)                , 0)
    EQ(n.getAttributeNode(aname)                  , 0)
    EQ(n.getAttributeNodeNS(ns,aname)             , 0)
    EQ(n.hasAttribute(aname)                      , 0)
    EQ(n.hasAttributeNS(aname, ns)                , 0)
    EQ(n.hasAttributes()                       , 0)
    EQ(n.removeAttribute(aname)                   , 0)
    EQ(n.setAttribute(aname, avalue)                  , 0)
    EQ(n.setAttributeNS(ns, aname, avalue)            , 0)

    anode = n.ownerDocument.createAttribute('class')
    anode.value = 'classValue'
    EQ(n.setAttributeNode(anode)               , 0)

    if (args.testMinidomExtras):
        EQ(n.getElementsByClassName(className, nodeList=None)  , 0)
        EQ(n.getElementById(IDValue)                   , 0)
        EQ(n.getElementsByTagName(tagName, nodeList=None)      , 0)
        EQ(n.getElementsByTagNameNS(tagName, nsURI, nodeList=None), 0)

    if (args.testBaseDomAdditions):
        EQ(n.removeAttributeNS(ns, aname)     , 0)
        EQ(n.removeAttributeNode(aname)       , 0)
        EQ(n.setAttributeNodeNS(ns, aname, avalue), 0)

        EQ(n.outerHTML()                   , 0)
        EQ(n.innerHTML()                   , 0)
        EQ(n.startTag()                    , 0)
        EQ(n.endTag()                      , 0)
        EQ(n.outerText()                   , 0)
        EQ(n.innerText(delim='')           , 0)
        EQ(n.nextElementSibling()          , 0)
        EQ(n.previousElementSibling()      , 0)
        EQ(n.childNumber()                 , 0)
        EQ(n.childElementNumber()          , 0)
        EQ(n.childElementCount()           , 0)
        EQ(n.firstElementChild()           , 0)
        EQ(n.lastElementChild()            , 0)
        EQ(n.elementChildNodes()           , 0)
        EQ(n.elementChildN(n)              , 0)
        EQ(n.isEqualNode(n2)               , 0)
        EQ(n.classList()                   , 0)
        EQ(n.className()                   , 0)
        EQ(n.id()                          , 0)

        EQ(n.remove()                      , 0)

    if (args.testSelectors):
        EQ(n.find()                        , 0)   # Whence?
        EQ(n.findAll()                     , 0)   # Whence?
        EQ(n.insertAdjacentHTML(htmlSample), 0)
        EQ(n.matches()                     , 0)
        EQ(n.querySelector()               , 0)
        EQ(n.querySelectorAll()            , 0)
        EQ(n.tostring()                    , 0)


###############################################################################
#
def exerciseNamedNodeMap2(self, odoc):
    anElem = odoc.createElement("attrHolder")
    #nnm = NamedNodeMap(ownerDocument=odoc)
    alph = string.ascii_letters

    print("Starting with %d attrs." % (len(anElem.attributes)))
    for i in range(len(alph)):
        nam = alph[i] * (i+1)
        val = i
        anElem.setAttribute(nam, val)
    print("Added %d attrs." % (len(anElem.attributes)))
    if (args.verbose):
        showNamedNodeMap(anElem.attributes)

    for i in range(len(alph)):
        nam = alph[i] * (i+1)
        val = i
        anElem.removeAttribute(nam)
    print("Deleted down to %d attrs." % (len(anElem.attributes)))

    for i in range(len(alph)):
        nam = alph[i] * (i+1)
        val = i
        if (args.testBaseDomAdditions):
            anode = odoc.createAttribute(
                nam, value=val, parentNode=anElem)
        else:
            anode = odoc.createAttribute(nam)
            anode.value = val
            anElem.setAttributeNode(anode)
        anElem.setAttributeNode(anode)
    print("Added %d attr nodes." % (len(anElem.attributes)))

    if (args.testBaseDomAdditions):
        for i in range(len(alph)):
            nam = alph[i] * (i+1)
            val = i
            anode = odoc.getAttributeNode(nam)
            anElem.removeAttributeNode(anode)
        print("Deleted down to %d attr nodes." % (len(anElem.attributes)))
    #EQ(anElem.setAttribute('id', 'myId37')                 , 0)
    #EQ(anElem.setAttribute('1234bad', 'spam', FAIL_VALUE)


def exerciseNamedNodeMap(self, n):
    assert isinstance(n, NamedNodeMap)

    EQ = self.assertEqual

    #n.__len__()
    nNodes = len(n)
    for i, name in enumerate(n.keys()):
        if (not XStr.isXmlName(name)):
            report("Non XML Name")
        if (args.testBaseDomAdditions):
            if (n.getIndexOf(name) != i):  # Extension
                report("getIndexOf fail")
        attrNode = n.getNamedItem(name)
        tstr = attrNode.name * i
        attrNode2 = attrNode.ownerDocument.createAttribute(name)
        attrNode2.value = tstr
        n.setNamedItem(attrNode2)  # TODO ???
        # cf https://docs.python.org/2/library/xml.dom.html#namednodemap-objects
        tstr2 = n.getNamedItem(name)
        if (tstr2 != tstr):
            report("setNamedItem fail")
        n.setNamedItem(attrNode)
        v2 = n.getNamedItem(name)
        if (v2 != attrNode.value):
            report("re-setNamedItem fail")

        n.removeNamedItem(name)
        if (n.getNamedItem(name)):
            report("removeNamedItem fail")
        n.setNamedItem(attrNode)

        for _ in range(nNodes):
            EQ(n.item(i)                            , 0)
            EQ(n.getNamedItemNS('p', 'class')       , 0)
                #( "n.setNamedItemNS(attrNode)"     , 0),
            EQ(n.removeNamedItemNS(aname, 'class')  , 0)

    if (args.testBaseDomAdditions):
        EQ(n.tostring(), 0)
        n2 = n.clone()
        nNodes = len(n)
        for an1 in n.keys():
            an2 = n2.getNamedItem(an1.name)
            if (an1.name != an2.name or an1.value != an2.value):
                report("Clone fail on named item '%s'." % (an1.name))


###############################################################################
#
if __name__ == "__main__":
    def processOptions():
        try:
            from BlockFormatter import BlockFormatter
            parser = argparse.ArgumentParser(
                description=descr, formatter_class=BlockFormatter)
        except ImportError:
            parser = argparse.ArgumentParser(description=descr)

        parser.add_argument(
            "--baseDom", "--BaseDom", action='store_true',
            help='Use BaseDom instead of xml.dom.minidom')
        parser.add_argument(
            "--quiet", "-q", action='store_true',
            help='Suppress most messages.')

        parser.add_argument(
            "--testMinidomExtras", action='store_true',
            help='')
        parser.add_argument(
            "--testBaseDomAdditions", action='store_true',
            help='')
        parser.add_argument(
            "--testSelectors", action='store_true',
            help='')

        parser.add_argument(
            "--verbose", "-v", action='count', default=0,
            help='Add more messages (repeatable).')
        parser.add_argument(
            "--version", action='version', version=__version__,
            help='Display version information, then exit.')

        parser.add_argument(
            'files', type=str,
            nargs=argparse.REMAINDER,
            help='Path(s) to input file(s)')

        args0 = parser.parse_args()
        return(args0)


    ###########################################################################
    #
    print("******* UNFINISHED *******")

    args = processOptions()

    if (len(args.files) > 0):
        for path0 in args.files:
            if (args.baseDom):
                db = None # TODO Fix DomBuilder.DomBuilder(path0)
                theDom = db.parse(path0)
                print("\nResults:")
                print(theDom.tostring())
            else:
                fh0 = codecs.open(path0, "rb", encoding="utf-8")
                theXML = xml.dom.minidom.parse(fh0)
                fh0.close()

    print("Getting a DOM implementation...")
    print("Getting getDOMImplementation()")
    domImpl = getDOMImplementation()

    print("Creating a Document and DocumentType...")
    theOwnerDocument = domImpl.createDocument(None, "HTML", None)
    theDoctype = domImpl.createDocumentType(
        "HTML",
        "-//W3C//DTD XHTML 1.0 Strict//EN",
        "http://www.w3.org/TR/xhtml1/DTD/xhtml1-strict.dtd")

    if (args.testBaseDomAdditions):
        theDoctype.addElement('i', '#PCDATA')
        theDoctype.addElement('b', '#PCDATA')
        theDoctype.addElement('tt', '#PCDATA')
        theDoctype.addElement('p',  '#PCDATA|i|b|tt')
        theDoctype.addElement('ol', '(li+)')
        theDoctype.addElement('li', '(p)*')

        theDoctype.addAttribute('p', 'id', atype='ID', adefault="IMPLIED")
        theDoctype.addAttribute('p', 'class', atype='CDATA')
        theDoctype.addAttribute('p', 'style', adefault="display:block;")
        theDoctype.addAttribute('p', 'mung', adefault=">escaped<")

        theDoctype.addEntity('chap1', "<div><h1>Introduction</h1></div>",
            parseType="XML")
        theDoctype.addNotation("joeg",
            publicId="-//example.com/ns/jpeg", systemId="jpeg.exe")

    theOwnerDocument.doctype = theDoctype
    print("    Doctype is: %s." % (theOwnerDocument.doctype))

    fillDoc(theOwnerDocument)

    exercise(domImpl, theOwnerDocument)

    print("\nResults:")
    #print(theOwnerDocument.tostring())

    print("\nDone (testDom, but not DomExtensions!).")
