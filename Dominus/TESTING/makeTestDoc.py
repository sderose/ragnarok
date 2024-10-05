#!/usr/bin/env python3
#
import sys
#import unittest
#import logging
import random
import math
from types import SimpleNamespace
import logging

from xmlstrings import XmlStrings as XStr
#from xml.dom.minidom import getDOMImplementation, DOMImplementation, Document, Node, Element
from basedom import getDOMImplementation, DOMImplementation, Document, Node, Element

#from gendoc import genDoc
from alogging import FormatRec


lg = logging.getLogger("makeTestDoc")
fr = FormatRec()

nameStartChars = XStr.allNameStartChars()
nameChars = nameStartChars + XStr.allNameChars()


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
        lg.warning("\n####### %s (nodeName %s)",msg, node.nodeName)
        node.writexml(sys.stderr, indent='    ', addindent='  ', newl='\n')

    @staticmethod
    def dumpNodeData(node:Node, msg:str=""):
        lg.warning("\n####### %s (nodeName %s, addr %x)",
            msg, node.nodeName, id(node))
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

        lg.warning("\n".join([
            "  nodeType     %s (%s)"
                % (node.nodeType, node.nodeType.value),
            "  nodeName     '%s' (prefix '%s', local '%s')"
                % (node.nodeName, node.prefix, node.localName),
            "  index        %d of %d (parent type %s)" % (cnum, cof, pname),
            "  l/r sibs     '%s', '%s'" % (lname, rname),
            "  children     [ %s ]" % (", ".join(ctypes)),
            "  path         %s" % (node.getNodePath())
        ]))

    @staticmethod
    def dumpChildNodes(node:Node, msg:str="", addrs:bool=False):
        if (addrs):
            lg.warning("\n####### %s [ %s ]\n", msg, ", ".join(
                [ "%s[%x]" % (x.nodeName, id(x)) for x in node.childNodes ]))
        else:
            lg.warning("%s [ %s ]\n",
                msg, ", ".join([ x.nodeName for x in node.childNodes ]))

    @staticmethod
    def dumpNodeAsJsonX(node:Node, msg:str=""):
        lg.warning("\n######## %s", msg)
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
    ns_uri = "https://example.com/namespaces/foo"

    root_name = 'html'
    child1_name = 'child1'
    child2_name = 'child2'
    empty_node_name = 'empty'
    grandchild_name = 'grandchild'
    p_name = "para"

    at_name = 'an_attr.name'
    at_value = 'this is an attribute value'

    text_before = 'Text before '
    inline_name = 'i'
    text_inside = '(text inside)'
    text_after = ' and after'
    some_text = 'Some text content.'
    more_text = ' More text'

    final_sigma = "\u03C2"
    lc_sigma = "\u03C3"

class DAT_HTML(DAT):
    ns_uri = "https://w3.org/namespaces/xhtml4"

    root_name = 'html'
    child1_name = 'head'
    child2_name = 'body'
    empty_node_name = 'br'
    grandchild_name = 'div'

    at_name = 'class'
    at_value = 'class1 class2'

class DAT_DocBook(DAT):
    ns_uri = "https://docbook.org/namespaces/article"

    root_name = 'article'
    child1_name = 'sec'
    child2_name = 'sec'
    empty_node_name = 'br'
    grandchild_name = 'para'

    at_name = 'id'
    at_value = 'docbook_id_17'

    inline_name = 'em'


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
        self.alreadyShowedSetup = True

        # Define some names to use across various subclasses, even though
        # we're leaving them at None to start.
        #
        self.dc = dc

        self.n = SimpleNamespace(**{
            "impl":        None,
            "doc":         None,
            "docEl":       None,

            "child1":      None,
            "child2":      None,
            "grandchild":  None,
            "textNode1":   None,
            "emptyNode":   None,
            "mixedNode":   None,

            "attrNode":    None,

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

        if show: lg.warning(
            "makeTestDoc0 produced: %s", self.n.doc.outerXML)

    def once(self, *args):
        if (self.alreadyShowedSetup): return
        lg.warning(*args, "\n")


    @staticmethod
    def addFullTree(node:Node, n:int=10, depth:int=3,
        types:list=None, withText:bool=False):
        """Recursively create a subtree, adding 'n' more levels (possibly plus
        one for text nodes at the bottom), each node having n children.
        """
        if not types: types = [ "p", "bq" ]
        od = node.ownerDocument
        if (depth == 0):
            if (withText):
                tx = od.createTextNode("Some text")
                node.appendChild(tx)
            return
        makeTestDoc0.addChildren(node, n, types, withText)
        for ch in node.childNodes:
            makeTestDoc0.addFullTree(ch, n, depth-1, types, withText)
        return node

    @staticmethod
    def addChildren(node:Node, n:int=10, types:list=None, withText:bool=False):
        if not types: types = [ "p", "bq" ]
        d = node.ownerDocument
        for i in range(n):
            ename = types[i % len(types)]
            newEl = d.createElement(ename)
            if (withText):
                newEl.appendChild(d.createTextNode("for the snark was a boojum"))
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

            if (not specials):
                x = doc.createEntityReference
                node.appendChild(x)
                x = doc.createNotation
                node.appendChild(x)
                x = doc.createDocType
                node.appendChild(x)

    @staticmethod
    def getAttrNames(n:int, baseName:str="anAttr", randomize:bool=False):
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
    def __init__(self, dc=DAT, show:bool=False):
        super().__init__(dc)
        assert isinstance(self.n.impl, DOMImplementation)
        assert isinstance(self.n.doc, Document)
        assert isinstance(self.n.docEl, Element)
        assert self.n.child1 is None

        self.createRestOfDocument()

        if show: lg.warning(
            "makeTestDoc2 produced: %s", self.n.doc.outerXML)


    def createRestOfDocument(self):
        """Store stuff we want to refer back to, in self.docItems.
        """

        # Add some more nodes

        self.n.child1 = self.n.doc.createElement(self.dc.child1_name)
        self.n.child1.setAttribute(self.dc.at_name, self.dc.at_value)
        self.n.docEl.appendChild(self.n.child1)

        self.n.child2 = self.n.doc.createElement(self.dc.child2_name)
        self.n.docEl.appendChild(self.n.child2)
        assert len(self.n.docEl.childNodes) == 2
        assert self.n.docEl.childNodes[1] == self.n.child2

        self.n.grandchild = self.n.doc.createElement(self.dc.grandchild_name)
        self.n.child2.appendChild(self.n.grandchild)

        self.n.textNode1 = self.n.doc.createTextNode(self.dc.some_text)
        self.n.child1.appendChild(self.n.textNode1)

        # Add empty node
        self.n.emptyNode = self.n.doc.createElement(self.dc.empty_node_name)
        self.n.docEl.appendChild(self.n.emptyNode)

        if (not self.alreadyShowedSetup):
            self.dumpNode(self.n.docEl, "Setup produced:")
            self.alreadyShowedSetup = True

        # Nodes used later
        self.n.mixedNode = None
