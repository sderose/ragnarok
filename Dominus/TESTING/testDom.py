#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Exercise all DOM methods (I hope)....
#
#pylint: disable=W0613, W0212, W0603, W0641, W0123, W0703
#
import sys
import re
import argparse
import string
import codecs
from collections import defaultdict
import xml

import ColorManager
import basedom
from basedom import Node, NamedNodeMap
#DOMImplementation, Document, Element, Leaf, Text, \
#CDATASection, ProcessingInstruction, Comment, EntityReference, Notation, \
#DocumentType, Attr, NodeList,

import DOMBuilder

cm = ColorManager.ColorManager()

descr = """
=Description=

Exercise all DOM methods (I hope).... For the moment, this just does
smoke-testing, to see if things obviously fail.

By default, this:

* only prints fail cases. Use `-v` for the rest.

* uses xml.dom.minidom. To test basedom instead, use `--basedom`.

* does only tests only methods that are included in `xml.dom.minidom`.
To test the basedom additions, use ``.

* does not test any of minidom's extension.
To test them, use `--testMinidomExtras`.

* does not test `DomExtensions` methods. For that use `testDomExtensions.py`.

* does not test JQuery or other selection extensions.
To test them use `testSelectors` (not yet supported).
=References=

Actual DOM specs: [https://www.w3.org/DOM/DOMTR].

W3 test suites: [https://www.w3.org/DOM/Test/].

[https://developer.mozilla.org/en-US/docs/Web/API/Document_Object_Model/Introduction] claims to provide test examples for all DOM methods.

'''Note''': This uses ''eval()'' on most test expressions, so don't put
anything bad in there.

=Related Commands=

`testDomExtensions.py` -- similar, but to test my extensions.

=History=

* Written by Steven J. DeRose, ~Feb 2016.
* 2018-04-18: lint.
* 2019-12-30: Split out from basedom.
* 2020-01-20: Got to point of no crashing on entire minidom test.

=Known bugs and limitations=

Lots of the tests don't do much yet.

Expected results are not yet included, which is kind of important.

Some minidoom vs. dom issues are unclear:

* Where's NamedNodeMap.setNamedItem(), and what does it take?

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
    useBaseDOM = False,
    testMinidomExtras = False,    # The few additions minidom has
    testBaseDOMAdditions = False, # To enable basedom but non-minidom tests
    testSelectors = False         # JQuery and similar selector support
)

sampleValues = {
    "nsURI": "http://derose.net/namespace/testNS",
    "nsPrefix": "tst",
    "tagName": "BLOCKQUOTE",
    "IDValue": "chap1_id",
    "qname": "foo:aDoc",
    "ukey": "userDataKey",
    "udata": "3.14159",
    "className": "secret",
    "htmlSample": """<p>The <i>quick</i> brown fox jumped the shark.</p>""",
    "someText": "A bit more text.",
    "someComment": "Quoth the walrus, 'Nevermore.'",
    "someCDATA": "No need for escaping in here.",
    "someTarget": "myPITarget",
    "somePI": "pi1='foo' xyzzy='plugh'",
    "entName": "amp",
}

def fillDoc(docObj):
    """Use DOM to create a document from scratch, thus exercising the
    createXXX() methods.

    See also DOMBuilder, which maps SAX events from a parser, to the DOM
    calls needed to create the corresponding DOM structure.
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

def exercise(theDomImpl, docObj):
    exerciseDOMImplementation(theDomImpl)
    docEl = docObj.documentElement

    header("exerciseNode")
    exerciseNode(docEl)

    header("exerciseDocument")
    exerciseDocument(docObj)
    header("exerciseDoctype")
    exerciseDoctype(docObj.doctype)
    header("exerciseElement")
    exerciseElement(docEl)

    header("exerciseLeaf")
    someTextNode = findDesc(docEl, Node.TEXT_NODE)
    exerciseLeaf(someTextNode)
    header("exerciseText")
    exerciseText(someTextNode)

    header("exerciseProcessingInstruction")
    somePINode = findDesc(docEl, Node.PROCESSING_INSTRUCTION_NODE)
    exerciseProcessingInstruction(somePINode)

    header("exerciseComment")
    someCommentNode = findDesc(docEl, Node.COMMENT_NODE)
    exerciseComment(someCommentNode)

    # TODO: These aren't showing up for the moment....
    #header("exerciseCDATASection")
    #print("    #OMITTED")
    ##exerciseCDATASection(docEl)
    #header("exerciseEntityReference")
    #print("    #OMITTED")
    ##exerciseEntityReference(docObj)
    #header("exerciseNotation")
    #print("    #OMITTED")
    ##exerciseNotation(docObj)

    #header("exerciseNodeList")
    #exerciseNodeList(docEl.childNodes)
    #header("exerciseAttr")
    #exerciseAttr(docEl)
    #header("exerciseNamedNodeMap")
    #exerciseNamedNodeMap(docEl.attributes)
    #header("exerciseNamedNodeMap2")
    #exerciseNamedNodeMap2(docObj)

    return

def header(msg):
    print("\n******* Starting %s *******" % (msg))

def exerciseGetItem(docObj):
    n = docObj.documentElement

    testBracket(n, "n[0]")
    testBracket(n, "n[-1]")
    testBracket(n, "n['@id']")
    testBracket(n, "n['@class']")
    testBracket(n, "n['p']")
    testBracket(n, "n['*']")
    testBracket(n, "n['#text']")
    testBracket(n, "n['#comment']")
    testBracket(n, "n['#pi']")

    testBracket(n, "n[0:-2]")
    testBracket(n, "n['p':2]")
    testBracket(n, "n[2:'p']")
    testBracket(n, "n[2:8]")

    testBracket(n, "n['p':2:8]")
    testBracket(n, "n[2:8:'p']")
    testBracket(n, "n[1:10:2]")

    # Fails
    testBracket(n, "n[9999]", result=FAIL_VALUE)
    testBracket(n, "n[-9999]", result=FAIL_VALUE)
    testBracket(n, "n['@123']", result=FAIL_VALUE)
    testBracket(n, "n['@no_such_attribute]", result=FAIL_VALUE)
    testBracket(n, "n['xyzzy']", result=FAIL_VALUE)
    testBracket(n, "n['*']", result=FAIL_VALUE)
    testBracket(n, "n['#cdata']", result=FAIL_VALUE)
    testBracket(n, "n['#spam']", result=FAIL_VALUE)
    testBracket(n, "n['%$&']", result=FAIL_VALUE)

    testBracket(n, "n[0:-9999]", result=FAIL_VALUE)
    testBracket(n, "n['p':9999]", result=FAIL_VALUE)
    testBracket(n, "n[0:'xyzzy']", result=FAIL_VALUE)
    testBracket(n, "n[False:8]", result=FAIL_VALUE)
    testBracket(n, "n[0:3.14159]", result=FAIL_VALUE)

    testBracket(n, "n['p':2:9999]", result=FAIL_VALUE)
    testBracket(n, "n[-9999:8:'p']", result=FAIL_VALUE)
    testBracket(n, "n[1:10:9999]", result=FAIL_VALUE)  # Is this ok or not? Phase?

    return


def testBracket(n, expr, result=0):
    try:
        n2 = None
        eval('n2 = ' + expr)
        if (result == FAIL_VALUE):
            eprint("*** Should have failed but didn't: %s." % (expr))
        elif (args.verbose):
            print("Succeeded: %s (got '%s')." % (expr, n2))
    except IndexError as e:
        if (result is not FAIL_VALUE):
            eprint("*** Unexpected fail on '%s':\n    %s" % (expr, e))
        elif (args.verbose):
            print("Got expected fail on %s." % (expr))
    return


def show(expr, result=0, locs=None):
    """Caller passes in locals() so we have it to pass to eval().
    """
    try:
        ###
        print("==> %s" % (expr))
        rc = eval(expr, globals(), locs)
        ###
        if (result is FAIL_VALUE):
            eprint("*** Should have failed but didn't: %s." % (expr))
        elif (args.verbose):
            print("Succeeded: %s (got '%s')." % (expr, rc))
    except Exception as e:
        if (result is not FAIL_VALUE):
            eprint("*** Unexpected fail on '%s':\n    %s" % (expr, e))
        elif (args.verbose):
            print("Got expected fail on %s" % (expr))
    return

def findDesc(n, nodeType):
    """Cheesy way to scan for the first node of a given nodeType.
    """
    if (n.nodeType == nodeType): return n
    if (n.nodeType == basedom.Node.ELEMENT_NODE):
        for ch in n.childNodes:
            cand = findDesc(ch, nodeType)
            if (cand is not None): return cand
        return None
    return None

def eprint(msg):
    print(cm.colorize('red', msg))


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

def exerciseDOMImplementation(theDomImpl):
    theDomImpl.createDocumentType(sampleValues["qname"],
        "+//ISBN 978-0000000000//foo",
        "/tmp/nofile.xml")

    theDomImpl.hasFeature("OMNISCIENCE", "1.0")
    theDomImpl.createDocument(sampleValues["nsURI"], sampleValues["qname"], None)
    theDomImpl.createDocumentType(sampleValues["qname"], "aPublicId", "http://derose.net")


###############################################################################
#
def exerciseNode(n1):
    print("Exercising node, nodeType %d, nodeName %s." %
        (n1.nodeType, n1.nodeName))
    theDoc = n1.ownerDocument
    # basedom: Node.nameOfNodeType(n.nodeType)
    if (n1.ownerDocument != theDoc):
        report("Mismatched ownerDocument")

    n = n1
    n2 = n.ownerDocument.createElement("NEW_P")

    ukey = "myUserDataKey"
    udata = "myUserDataValue"

    #print(locals())

    tests = [
        ( "theDoc.getElementById(\"thePara\")"          , 0),

        # R/O
        #[n.hasIDAttribute(                             , 0),
        ( "n.nodeName"                                  , "P"),
        ( "n.cloneNode(deep=False)"                     , 0),
        ( "n.cloneNode(deep=True)"                      , 0),
        #( "n.nodeCompare(n2)"                          , 0),
        #( "n.getPath()"                                , 0),
        #( "n.getMyIndex(onlyElements=True)"            , 0),
        #( "n.getMyIndex(onlyElements=False)"           , 0),
        #( "n.getFeature('OMNISCIENCE', '1.0')"         , 0),
        #( "n.getUserData(ukey)"                        , 0),
        ( "n.hasAttributes()"                           , 0),
        ( "n.hasChildNodes()"                           , 0),
        #( "n.isDefaultNamespace(nsURI)"                , 0),
        #( "n.isEqualNode(n2)"                          , 0),
        ( "n.isSameNode(n)"                             , 0),
        ( "n.isSameNode(n2)"                            , 0),
        #( "n.lookupNamespaceURI(nsURI)"                , 0),
        #( "n.lookupPrefix(nsPrefix)"                   , 0),

        # R/W
        ( "n.appendChild(n2)"                           , 0),
        ( "n.insertBefore(n2, n.childNodes[1], )"       , 0),
        ( "n.normalize()"                               , 0),
        ( "n.removeChild(n.childNodes[1])"              , 0),
        ( "n.replaceChild(n2, n.childNodes[1])"         , 0),
        ( "n.setUserData(ukey, udata, handler=None)"    , 0),

        #  "n.tostring()"                               , 0),
    ]

    for tup in tests:
        print("expr '%s', res '%s'" % (tup[0], tup[1]))
        show(tup[0], tup[1], locals())
    print("******* End exerciseNode *******")
    return


###############################################################################
#
def exerciseDocument(n):
    tests = [
        ( "n.createElement(tagName)"                        , 0),
        ( "n.createDocumentFragment()"                      , 0),
        ( "n.createTextNode(someText)"                      , 0),
        ( "n.createComment(someComment)"                    , 0),
        ( "n.createCDATASection(someCDATA)"                 , 0),
        ( "n.createProcessingInstruction(someTarget, somePI)", 0),
    ]
    if (args.testBaseDOMAdditions):
        tests.extend([
            ( "n.charset()"                         , 0),
            ( "n.contentType()"                     , 0),
            ( "n.documentURI()"                     , 0),
            ( "n.domConfig()"                       , 0),
            ( "n.implementation()"                  , 0),
            ( "n.inputEncoding()"                   , 0),
            ( "n.createElement(tagName, attributes=attrs)"  , 0),
            ( "n.createEntityReference(entName)"            , 0),
            ( "n.tostring()"                                , 0),

            #  "n.all()"                                    , 0),  # Obsolete
        ])

    for tup in tests:
        print("expr '%s', res '%s'" % (tup[0], tup[1]))
        show(tup[0], tup[1], locals())
    print("******* End exerciseDocument *******")
    return


###############################################################################
#
def exerciseDoctype(n):
    if (not n):
        print("    *** No doctype there ***")
        return
    if (n.ownerDocument):
        #n2 = n.ownerDocument.createElement(sampleValues["tagName"])
        tests = [
            ( "n.isEqualNode(n2)"               , 0),  # Doctype
            ( "n.tostring()"                    , 0),
        ]

    else:
        print("    *** doctype has no owner document ***")
        return

    for tup in tests:
        print("expr '%s', res '%s'" % (tup[0], tup[1]))
        show(tup[0], tup[1], locals())

    print("Entities known:")
    showNamedNodeMap(n.entities)
    print("Notations known:")
    showNamedNodeMap(n.entities)

    if (args.testBaseDOMAdditions):
        print("Elements known:")
        showNamedNodeMap(n.elements)
        print("Attributes known:")
        showNamedNodeMap(n.attributes)
    print("******* End exerciseDoctype *******")

def showNamedNodeMap(nnm):
    n = len(nnm)
    for i in range(n):
        nod = nnm.item(i)
        print("    %-55s '%s'" % (nod.name, nod.value))


###############################################################################
#
def exerciseElement(n):
    if (not isXmlName(n.nodeName)):
        report("Non XML Name")

    an = "class"
    av = "zork"
    ns = "http://derose.net/namespace/testNS"
    n2 = None
    aTagName = "p"
    i = 1
    attrs = {
        "id":'myID9', 'class':'foo bar baz', 'href': 'http://example.com&foo' }

    tests = [
        ( "n.getAttribute(an)"                      , 0),
        ( "n.getAttributeNS(ns, an)"                , 0),
        ( "n.getAttributeNode(an)"                  , 0),
        ( "n.getAttributeNodeNS(ns,an)"             , 0),
        ( "n.hasAttribute(an)"                      , 0),
        ( "n.hasAttributeNS(an, ns)"                , 0),
        ( "n.hasAttributes()"                       , 0),
        ( "n.removeAttribute(an)"                   , 0),
        ( "n.setAttribute(an, av)"                  , 0),
        ( "n.setAttributeNS(ns, an, av)"            , 0),
    ]
    anode = n.ownerDocument.createAttribute('class')
    anode.value = 'classValue'
    tests.extend([
        ( "n.setAttributeNode(anode)"               , 0),
    ])

    if (args.testMinidomExtras):
        tests.extend([
            ( "n.getElementsByClassName(className, nodeList=None)"  , 0),
            ( "n.getElementById(IDValue)"                   , 0),
            ( "n.getElementsByTagName(tagName, nodeList=None)"      , 0),
            ( "n.getElementsByTagNameNS(tagName, nsURI, nodeList=None)", 0),
        ])

    if (args.testBaseDOMAdditions):
        tests.extend([
            ( "n.removeAttributeNS(ns, an)"     , 0),
            ( "n.removeAttributeNode(an)"       , 0),
            ( "n.setAttributeNodeNS(ns, an, av)", 0),

            ( "n.outerHTML()"                   , 0),
            ( "n.innerHTML()"                   , 0),
            ( "n.startTag()"                    , 0),
            ( "n.endTag()"                      , 0),
            ( "n.outerText()"                   , 0),
            ( "n.innerText(delim='')"           , 0),
            ( "n.nextElementSibling()"          , 0),
            ( "n.previousElementSibling()"      , 0),
            ( "n.childNumber()"                 , 0),
            ( "n.childElementNumber()"          , 0),
            ( "n.childElementCount()"           , 0),
            ( "n.firstElementChild()"           , 0),
            ( "n.lastElementChild()"            , 0),
            ( "n.elementChildNodes()"           , 0),
            ( "n.elementChildN(n)"              , 0),
            ( "n.isEqualNode(n2)"               , 0),
            ( "n.classList()"                   , 0),
            ( "n.className()"                   , 0),
            ( "n.id()"                          , 0),

            ( "n.remove()"                      , 0),
            ])

    if (args.testSelectors):
        tests.extend([
            ( "n.find()"                        , 0),   # Whence?
            ( "n.findAll()"                     , 0),   # Whence?
            ( "n.insertAdjacentHTML(htmlSample)", 0),
            ( "n.matches()"                     , 0),
            ( "n.querySelector()"               , 0),
            ( "n.querySelectorAll()"            , 0),
            ( "n.tostring()"                    , 0),
        ])

    for tup in tests:
        if (len(tup) != 2):
            print("Bad tuple (len %d): %s" % (len(tup), tup))
            continue
        print("expr '%s', res '%s'" % (tup[0], tup[1]))
        show(tup[0], tup[1], locals())
    print("******* End exerciseElement *******")


###############################################################################
#
def exerciseLeaf(n):
    """This is really an abstract class, to cover the several subclasses of Node
    that can only be leaf nodes in a document. It shouldn't be instantiated.
    """
    if (not n):
        print("    *** No Leaf there ***")
        return
    if (len(n.childNodes) != 0):
        report("Non-empty childNodes in Leaf")
    n2 = n.ownerDocument.createElement(sampleValues["tagName"])

    if (args.testBaseDOMAdditions):
        n.isEqualNode(n2)
        n.tostring()
    print("******* End exerciseLeaf *******")


###############################################################################
#
def exerciseText(n):
    if (not n):
        print("    *** No Text there ***")
        return
    if (n.nodeName != "#text"):
        report("Bad nodeName for Text node")
    if (re.match(r'&(#\d+|#x[\dabcdef]+|\w+);', n.data)):
        report("Entity-reference-like string in text, possible problem?")

    if (args.testBaseDOMAdditions):
        n.tostring()
    print("******* End exerciseText *******")


###############################################################################
#
def exerciseCDATASection(n):
    if (not n):
        print("    *** No CDATASection there ***")
        return
    if (n.nodeName != "#cdata"):
        report("Bad nodeName for CDATASection node")
    if (args.testBaseDOMAdditions):
        n.tostring()
    print("******* End exerciseCDATASection *******")


###############################################################################
#
def exerciseProcessingInstruction(n):
    if (not n):
        print("    *** No PI there ***")
        return
    if (n.nodeName != "#pi"):
        report("Bad nodeName for ProcessingInstruction node")
    if (args.testBaseDOMAdditions):
        n.tostring()
    print("******* End exerciseProcessingInstruction *******")


###############################################################################
#
def exerciseComment(n):
    if (not n):
        print("    *** No comment there ***")
        return
    if (n.nodeName != "#comment"):
        report("Bad nodeName for Comment node")
    if (args.testBaseDOMAdditions):
        n.tostring()
    print("******* End exerciseComment *******")


###############################################################################
#
def exerciseEntityReference(n):
    if (not n):
        print("    *** No ent ref there ***")
        return
    if (n.nodeName != n.data):
        report("Bad nodeName for EntityReference node")
    if (args.testBaseDOMAdditions):
        n.tostring()
    print("******* End exerciseEntityReference *******")


###############################################################################
#
def exerciseNotation(n):
    if (not n):
        print("    *** No notation there ***")
        return
    if (n.nodeName != "#text"):
        report("Bad nodeName for Notation node")
    if (args.testBaseDOMAdditions):
        n.tostring()
    print("******* End exerciseNotation *******")


###############################################################################
#
def exerciseNodeList(n):
    if (not n):
        print("    *** No nodelist there ***")
        return
    if (not isinstance(n, list)):
        print("    *** Not a list ***")
        return
    nNodes = len(n)
    # TODO: vs. n.length
    for i in range(nNodes):
        if (not isinstance(n.item(i),
            ( xml.dom.minidom.Node, BaseDOM.Node ))):
            report("Non-Node in NodeList, type is %s" % (type(n.item(i))))
    print("******* End exerciseNodeList *******")


###############################################################################
#
def exerciseAttr(n):
    if (not n):
        print("    *** No attr there ***")
        return
    n2 = n.ownerDocument.createElement(sampleValues["tagName"])
    if (args.testBaseDOMAdditions):
        n.isEqualAttr(n2)
    print("******* End exerciseAttr *******")


###############################################################################
#
def exerciseNamedNodeMap2(odoc):
    anElem = odoc.createElement("attrHolder")
    nnm = NamedNodeMap(ownerDocument=odoc)
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
        if (args.testBaseDOMAdditions):
            anode = odoc.createAttribute(
                nam, value=val, parentNode=anElem)
        else:
            anode = odoc.createAttribute(nam)
            anode.value = val
            anElem.setAttributeNode(anode)
        anElem.setAttributeNode(anode)
    print("Added %d attr nodes." % (len(anElem.attributes)))

    if (args.testBaseDOMAdditions):
        for i in range(len(alph)):
            nam = alph[i] * (i+1)
            val = i
            anode = odoc.getAttributeNode(nam)
            anElem.removeAttributeNode(anode)
        print("Deleted down to %d attr nodes." % (len(anElem.attributes)))
    #tests = [
    #    ( "anElem.setAttribute('id', 'myId37')"                 , 0),
    #    ( "anElem.setAttribute('1234bad', 'spam'", FAIL_VALUE),
    #]
    print("******* End exerciseNamedNodeMap2 *******")


def exerciseNamedNodeMap(n):
    if (not n):
        print("    *** No NamedNodeMap there ***")
        return
    if (not isinstance(n, (xml.dom.minidom.NamedNodeMap,
        BaseDOM.NamedNodeMap))):
        print("    *** Not a NamedNodeMap, but a %s" % (type(n)))

    #n.__len__()
    nNodes = len(n)
    for i, name in enumerate(n.keys()):
        if (not isXmlName(name)):
            report("Non XML Name")
        if (args.testBaseDOMAdditions):
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

        tests = []
        for ii in range(nNodes):
            tests.extend([
                ( "n.item(i)"                   , 0),
                ( "n.getNamedItemNS('p', 'class')"              , 0),
                #( "n.setNamedItemNS(attrNode)"                 , 0),
                ( "n.removeNamedItemNS(an, 'class')"            , 0),
            ])

    if (args.testBaseDOMAdditions):
        tests.extend([
            ( "n.tostring()"                    , 0),
        ])
        n2 = n.clone()
        nNodes = len(n)
        for an1 in n.keys():
            an2 = n2.getNamedItem(an1.name)
            if (an1.name != an2.name or an1.value != an2.value):
                report("Clone fail on named item '%s'." % (an1.name))

    for tup in tests:
        if (len(tup) != 2):
            print("Bad tuple (len %d): %s" % (len(tup), tup))
        print("expr '%s', res '%s'" % (tup[0], tup[1]))
        show(tup[0], tup[1], locals())
    print("******* End exerciseNamedNodeMap *******")


###############################################################################
#
def report(msg):
    sys.stderr.write(msg+"\n")


###############################################################################
# Regexes from my XMLparserInOneRegex.py.
#
nameStartChar = str("[:_A-Za-z" +                            # 4
    "\u00C0-\u00D6" + "\u00D8-\u00F6" + "\u00F8-\u02FF" +
    "\u0370-\u037D" + "\u037F-\u1FFF" + "\u200C-\u200D" +
    "\u2070-\u218F" + "\u2C00-\u2FEF" + "\u3001-\uD7FF" +
    "\uF900-\uFDCF" + "\uFDF0-\uFFFD" +
    "\u10000-\uEFFFF" +
    ']')
nameChar  = re.sub(                                              # 4a
    '^\\[', '[-.0-9\u00B7\u0300-\u036F\u203F-\u2040', nameStartChar)

xname     = "%s%s*" % (nameStartChar, nameChar)

def isXmlName(s):
    if (re.match(xname, s, flags=re.UNICODE)): return True
    return False


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
            "--baseDom", "--BaseDOM", action='store_true',
            help='Use BaseDOM instead of xml.dom.minidom')
        parser.add_argument(
            "--quiet", "-q", action='store_true',
            help='Suppress most messages.')

        parser.add_argument(
            "--testMinidomExtras", action='store_true',
            help='')
        parser.add_argument(
            "--testBaseDOMAdditions", action='store_true',
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
                db = DOMBuilder.DOMBuilder(path0)
                theDom = db.parse(path0)
                print("\nResults:")
                print(theDom.tostring())
            else:
                fh0 = codecs.open(path0, "rb", encoding="utf-8")
                theXML = xml.dom.minidom.parse(fh0)
                fh0.close()

    print("Getting a DOM implementation...")
    if (args.baseDom):
        print("Getting BaseDOM().getDOMImplementation()")
        domImpl = BaseDOM.BaseDOM().getDOMImplementation()
    else:
        print("Getting xml.dom.minidom.getDOMImplementation()")
        domImpl = xml.dom.minidom.getDOMImplementation()

    print("Creating a Document and DocumentType...")
    theOwnerDocument = domImpl.createDocument(None, "HTML", None)
    theDoctype = domImpl.createDocumentType(
        "HTML",
        "-//W3C//DTD XHTML 1.0 Strict//EN",
        "http://www.w3.org/TR/xhtml1/DTD/xhtml1-strict.dtd")

    if (args.testBaseDOMAdditions):
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
