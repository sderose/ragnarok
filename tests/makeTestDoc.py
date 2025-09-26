#!/usr/bin/env python3
#
import sys
import os
import re
import html
import random
import math
from typing import Dict
from types import SimpleNamespace
import logging

from xml.dom import minidom

from runeheim import XmlStrings as Rune
#from xml.dom.minidom import getDOMImplementation, DOMImplementation, Document, Node, Element
from basedom import getDOMImplementation, DOMImplementation, Document, Node, Element

#from gendoc import genDoc
#from alogging import FormatRec


lg = logging.getLogger("makeTestDoc")
#fr = FormatRec()

nameStartChars = Rune.allNameStartChars()
nameChars = nameStartChars + Rune.allNameChars()

firstSetup = True

dataDir = os.environ["sjdUtilsDir"] + "/Data"


###############################################################################
# Some general testing helpers.
#
def packXml(s:str) -> str:
    """Make 2 xml strings more comparable (doesn't deal with attribute order).
    TODO: Canonicalize.
    """
    s = re.sub(r"""<\?xml .*?\?>""", "", s)
    s = re.sub(r"\s*<", "\n<", s).strip()
    s = html.unescape(s)
    return "\n\n" + s

def checkXmlEqual(xml:str, xml2:str):
    p1 = packXml(xml)
    p2 = packXml(xml2)
    if (p1 == p2): return

    p1Lines = p1.splitlines()
    p2Lines = p2.splitlines()

    print("Mismatch:")
    for i in range(len(p1Lines)):
        if p1Lines[i] == p2Lines[i]: continue
        print("Line %3d: " % (i) + p1Lines[i])
        print("          " + p2Lines[i])

def isEqualNode(n1, n2) -> bool:
    """Provide equivalent of the DOM 3 method, since minidom lacks it
    and I want to be able to test with either that or basedom.
    TODO Anything special for Document, DocFrag, EntRef?
    """
    if n2 is n1: return True
    if n2 is None: return False
    if n1.nodeType != n2.nodeType: return False
    if n1.nodeName != n2.nodeName: return False
    if n1.nodeValue != n2.nodeValue: return False
    if isinstance(n1, minidom.Attr):
        return n1.name == n2.name and n1.value == n2.value
    elif isinstance(n1, minidom.CharacterData):
        if isinstance(n1, minidom.ProcessingInstruction):
            if n1.target != n2.target: return False
        return n1.data == n2.data
    elif (isinstance(n1, minidom.Element)):
        sAts = n1.attributes or {}
        nAts = n2.attributes or {}
        # Can't just compare, b/c the values are Attr Nodes.
        sKeys = set(list(sAts.keys()))
        nKeys = set(list(nAts.keys()))
        if sKeys != nKeys: return False
        for k in sKeys:
            if n1.getAttribute(k) != n2.getAttribute(k): return False
        if len(n1.childNodes) != len(n2.childNodes): return False
        for i in range(len(n1.childNodes)):
            if not isEqualNode(n1.childNodes[i], n2.childNodes[i]): return False
    return True

def compareAttrs(node1:Node, node2:Node) -> bool:
    """Test if all the attributes of two nodes match.
    """
    s1 = set(node1.attributes.keys())
    s2 = set(node2.attributes.keys())
    if s1 != s2: return False
    for aname in s1:
        if node1.getAttribute(aname) != node2.getAttribute(aname): return False
    return True


###############################################################################
#
class DBG:
    """Debug printing stuff.
    """
    @staticmethod
    def msg(msg:str=""):
        lg.warning("\n####### %s\n", msg)

    @staticmethod
    def dumpNode(node:Node, msg:str=""):
        lg.warning("\n####### %s: ",  msg)
        node.writexml(sys.stderr, indent='    ', addindent='  ', newl='\n')

    @staticmethod
    def dumpNodeData(node:Node, msg:str=""):
        lg.warning("\n####### %s\n", msg)
        if node.parentNode is None:
            pname = lname = rname = "None"
            cnum = cof = -1
        else:
            pname = node.parentNode.nodeName
            cnum = node.getChildIndex()
            cof = len(node.parentNode)
            try:
                lname = node.previousSibling.nodeName
            except AttributeError:
                lname = "None"
            try:
                rname = node.nextSibling.nodeName
            except AttributeError:
                rname = "None"
        if (node.childNodes is not None):
            ctypes = list(c.nodeName for c in node.childNodes)
        else:
            ctypes = []

        if (node.attributes):
            attrs = " ".join([f"{k}=\"{v}\"" for k, v in node.attributes.items()])
        else:
            attrs = ""

        lg.warning("\n".join([
            "  nodeType     %s (%s)"
                % (node.nodeType, node.nodeType.value),
            "  nodeName     %s (prefix %s, local %s)"
                % (node.nodeName, node.prefix, node.localName),
            "  index        %d of %d (parent type %s)" % (cnum, cof, pname),
            "  l/r sibs     %s, %s" % (lname, rname),
            "  attributes   { %s }" % (attrs),
            "  children     [ %s ]" % (", ".join(ctypes)),
            "  path         %s" % (node.getNodePath())
        ]))

    @staticmethod
    def dumpChildNodes(node:Node, msg:str="", addrs:bool=False):
        if (addrs):
            lg.warning("\n####### %s [ %s ]\n", msg, ", ".join(
                [ "%s[%x]" % (x.nodeName, id(x)) for x in node.childNodes ]))
        else:
            chList = ", ".join([ x.nodeName for x in node.childNodes ])
            lg.warning("%s [ %s ]\n", msg, chList)

    @staticmethod
    def dumpNodeAsJsonX(node:Node, msg:str=""):
        lg.warning("\n####### %s", msg)
        try:
            getattr(Node, "toJsonX")
            lg.warning("\n####### %s: %s\n", msg, node.toJsonX(indent='  '))
        except AttributeError:
            lg.warning("\n*** toJsonX not available ***\n")


###############################################################################
#
class DAT:
    """Element names and other consts used in the sample document.
    """
    sampleXmlPath = "sampleData/sampleHTML.xml"
    ns_uri = "https://example.com/namespaces/foo"

    root_name = 'html'
    child0_name = 'child0'
    child1_name = 'child1'
    child2_name = 'child2'
    grandchild_name = 'grandchild'
    p_name = "para"
    inline_name = 'i'

    at_name = 'an_attribute.name'
    at_value = 'this is an attribute value'
    at_name2 = "class"
    at_value2 = "class1 class2"
    at_name3 = 'id'
    at_value3 = 'html_id_17'

    text_before = 'Text before '
    text_inside = '(text inside)'
    text_after = ' and after'
    some_text = 'Some text content.'
    more_text = ' More text'

    target_name = "pi-target"

    # Sigma is a case where .lower() and .casefold() differ.
    final_sigma = "\u03C2"
    lc_sigma = "\u03C3"

    xml = "<div n='1'><p>hello, <i>big</i> tester.</p><br /></div>"

class DAT_HTML(DAT):
    ns_uri = "https://w3.org/namespaces/xhtml4"

    root_name = 'html'
    child0_name = 'head'
    child1_name = 'body'
    child2_name = 'br'
    grandchild_name = 'div'
    p_name = "p"

class DAT_DocBook(DAT):
    ns_uri = "https://docbook.org/namespaces/article"

    root_name = 'article'
    child0_name = 'sec'
    child1_name = 'sec'
    child2_name = 'br'
    grandchild_name = 'para'
    p_name = "para"

    inline_name = 'emph'

class DAT_K(DAT):
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
    base_att_name = "anAttrName"
    new_name = "newb"
    attr_name = "class"
    attr_value = "important"
    text1 = "aardvark"
    udk1_name = "myUDKey"
    udk1_value = "999"

    outer = """<para id="foo">From xml string</para>"""


###############################################################################
#
class makeTestDoc0:
    """Create a bare minimum document. Subclasses start from this and add.
        <html></html>

    Also provides construction utilities, such as methods to add a bunch
    of nodes of certain kinds, etc.

    TODO: Move all the self.nodes into a dict?
    """
    def __init__(self, dc:type=DAT, show:bool=False):
        global firstSetup
        self.alreadyShowedSetup = True

        # Define some names to use across various subclasses, even though
        # we're leaving them at None to start.
        #
        self.dc = dc

        self.n = SimpleNamespace(**{
            "impl":        None,
            "doc":         None,
            "docEl":       None,

            "child0":      None,
            "child1":      None,
            "child2":      None,
            "grandchild":  None,
            "textNode1":   None,
            "mixedNode":   None,

            "attNode":    None,

            "PiNode":      None,
            "CommNode":    None,
            "CDATANode":   None,
        })

        #print("Starting setup, using %s", DOMImplementation.__file__)
        self.n.impl = getDOMImplementation()
        self.once("getDOMImplementation() returned a %s @ %x.",
            type(self.n.impl), id(self.n.impl))
        assert isinstance(self.n.impl, DOMImplementation)

        self.n.doc:Document = self.n.impl.createDocument(
            self.dc.ns_uri, self.dc.root_name, None)
        self.once("createDocument() returned a %s @ %x",
            type(self.n.doc), id(self.n.doc))
        assert isinstance(self.n.doc, Document)
        assert self.n.doc.ownerDocument is None

        self.n.docEl:Element = self.n.doc.documentElement
        self.once("documentElement is a %s @ %x: name %s",
            type(self.n.docEl), id(self.n.docEl), self.n.docEl.nodeName)
        assert isinstance(self.n.docEl, Element)
        assert (self.n.docEl.nodeName == self.dc.root_name)
        assert len(self.n.docEl.childNodes) == 0

        if show and firstSetup: lg.warning(
            "makeTestDoc0 produced: %s", self.n.doc.toprettyxml())
        firstSetup = False

    def once(self, *args):
        if (self.alreadyShowedSetup): return
        lg.warning(*args, "\n")

    @staticmethod
    def addFullTree(node:Node, n:int=10, depth:int=2, types:list=None,
        withText:Dict=None, withAttr:Dict=None) -> None:
        """Recursively create a subtree, adding 'depth' levels, with the tags
        for each level taken from 'types', and each node having 'n' children.
        If 'withText' is set, add a level for text nodes at the bottom.
        If 'withAttrs' is set, also add attributes from it. If any have value
        "*", they'll be modified so they're not all the same.
        """
        if (0): print(f"\nIn addFullTree(width={n}, depth={depth}, types={types}, "
            f"withText='{withText}', withAttr={withAttr})")
        if not types: types = [ f"para{d}" for d in range(depth+1) ]
        makeTestDoc0.addChildren(
            node, n, types[0],
            withText=withText if depth == 0 else None,
            withAttr=withAttr)
        if depth > 0:
            for ch in node.childNodes:
                assert ch.isElement
                makeTestDoc0.addFullTree(ch, n, depth=depth-1, types=types[1:],
                    withText=withText, withAttr=withAttr)
        return

    @staticmethod
    def addChildren(node:Node, n:int=10, nodeName:str="p",
        withText:str=None, withAttr:Dict=None):
        """Add 'n' children to the node, of a given nodeName.

        If 'withText' is set, add text under each new node. Specific text can
        be passed, or if it is "" (not None), default text is used. The child
        number is appended to the text.

        If 'withAttr' is set, add its members as attributes, or
        if it is empty ({}, not None), default attributes are used.
        Attribute values of "*" are replace so they're not always the same.
        """
        if not isinstance(node, Element):
            raise TypeError(f"addChildren requires an Element, not {type(node)}.")
        if withText == "":
            withText = "for the snark was a boojum"
        if withAttr == {}:
            withAttr = { "n":"*" }
        d = node.ownerDocument

        for i in range(n):
            newEl = d.createElement(nodeName)
            if withText:
                newEl.appendChild(d.createTextNode(f"{withText} ({i})"))
            if withAttr:
                for k, v in withAttr.items():
                    if v == "*": v = f"sys_{i}"
                    newEl.setAttribute(k, v)
            node.appendChild(newEl)

    @staticmethod
    def addAllTypes(node:Node, dc:type=DAT, n:int=1, specials:bool=False):
        """Add children with even the less-usual node types.
        """
        doc = node.ownerDocument

        for _ in range(n):
            x = doc.createProcessingInstruction(dc.pi_target, dc.pi_data)
            node.appendChild(x)
            x = doc.createComment(dc.com_data)
            node.appendChild(x)
            x = doc.createCDATASection(dc.cdata_data)
            node.appendChild(x)
            x = doc.createTextNode("Some text.")
            node.appendChild(x)

            if (not specials):
                x = doc.createEntityReference
                node.appendChild(x)
                x = doc.createNotation
                node.appendChild(x)
                x = doc.createDocType
                node.appendChild(x)

    @staticmethod
    def getAttNames(n:int, baseName:str="anAttribute", randomize:bool=False):
        """Generate several attribute names, fixed or random.
        """
        names = []
        for i in range(n):
            if (randomize): baseName = makeTestDoc0.randomName()
            names.append(baseName + str(i))
        return names

    @staticmethod
    def randomName(minLen:int=1, maxLen:int=64):
        """Generate a random valid XML NAME, incl. Unicode.
        Tend toward shorter names, but long once in a while.
        """
        assert 0 < minLen < maxLen
        cp = random.randint(0, len(nameStartChars)-1)
        name = chr(cp)
        lenRange = maxLen-minLen+1
        length = minLen + math.floor(random.betavariate(1, 3) * lenRange)
        for _i in range(length):
            cp = random.randint(0, len(nameChars)-1)
            name += chr(cp)
        return name


###############################################################################
#
class makeTestDoc2(makeTestDoc0):
    """Create a document with 3 child nodes:
        <?xml version="1.0" encoding="utf-8"?>
        <!DOCTYPE html []>
        <html xmlns:html="https://example.com/namespaces/foo">
            <child0 an_att.name="this is an attribute value"
                class="class1 class2" id="html_id_17">
                Some text content.</child0>
            <child1>
                <grandchild></grandchild>
            </child1>
            <child2/>
        </html>
    """
    beenShown = False

    def __init__(self, dc=DAT, show:bool=False):
        super().__init__(dc)
        assert isinstance(self.n.impl, DOMImplementation)
        assert isinstance(self.n.doc, Document)
        assert isinstance(self.n.docEl, Element)
        assert len(self.n.docEl.childNodes) == 0

        self.createRestOfDocument()
        if show and not beenShown:
            lg.warning("makeTestDoc2 produced: %s", self.n.doc.outerXML)
            beenShown = True

    def createRestOfDocument(self):
        """Store stuff we want to refer back to, in self.docItems.
        """
        self.n.child0 = self.n.doc.createElement(self.dc.child0_name)
        self.n.child0.setAttribute(self.dc.at_name, self.dc.at_value)
        self.n.child0.setAttribute(self.dc.at_name2, self.dc.at_value2)
        self.n.child0.setAttribute(self.dc.at_name3, self.dc.at_value3)
        self.n.docEl.appendChild(self.n.child0)

        self.n.child1 = self.n.doc.createElement(self.dc.child1_name)
        self.n.docEl.appendChild(self.n.child1)
        assert len(self.n.docEl.childNodes) == 2
        assert self.n.docEl.childNodes[1] == self.n.child1

        self.n.grandchild = self.n.doc.createElement(self.dc.grandchild_name)
        self.n.child1.appendChild(self.n.grandchild)

        self.n.textNode1 = self.n.doc.createTextNode(self.dc.some_text)
        self.n.child0.appendChild(self.n.textNode1)

        # Add empty node
        self.n.child2 = self.n.doc.createElement(self.dc.child2_name)
        self.n.docEl.appendChild(self.n.child2)

        if (not self.alreadyShowedSetup):
            self.dumpNode(self.n.docEl, "Setup produced:")
            self.alreadyShowedSetup = True

        # Nodes used later
        self.n.mixedNode = None


###############################################################################
#
class makeTestDocEachMethod(makeTestDoc0):
    """Make a common starting doc. Superclass makes just root element.
    This adds 10 children, same type, @n numbered, attributes, text.
    TODO: Move to makeTestDoc.
    """
    def __init__(self, dc:type=DAT, show:bool=False):
        super().__init__(dc=dc)
        assert isinstance(self.n.impl, DOMImplementation)
        assert isinstance(self.n.doc, Document)
        assert isinstance(self.n.docEl, Element)

        for i in range(10):
            p = self.n.doc.createElement(self.dc.p_name)
            p.setAttribute(self.dc.attr_name, self.dc.attr_value)
            p.setAttribute("n", i)
            t = self.n.doc.createTextNode(self.dc.text1)
            p.appendChild(t)
            self.n.docEl.appendChild(p)

        #DBG.dumpNode(self.n.docEl)
        #y = self.makeSampleDoc()
        #x = self.makeSampleDoc()

        if show: sys.stderr.write(
            "makeTestDocEachMethod produced: " + self.n.doc.outerXML)
