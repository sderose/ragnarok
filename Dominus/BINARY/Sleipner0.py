#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
import re
import os
#from collections import defaultdict
import codecs
#import struct
#import array
from typing import Union, Dict

from EDir import EDir, EDirRec, HeaderInfo

from xmlstrings import XmlStrings as XStr
import basedom
from nodetype import NodeType
from dombuilder import DomBuilder

NmToken = str

__metadata__ = {
    "title"        : "Dominus",
    "description"  : "A disk-resident DOM implementation, similar to DynaText's.",
    "rightsHolder" : "Steven J. DeRose",
    "creator"      : "http://viaf.org/viaf/50334488",
    "type"         : "http://purl.org/dc/dcmitype/Software",
    "language"     : "Python 3.7",
    "created"      : "2016",
    "modified"     : "2023-11-21",
    "publisher"    : "http://github.com/sderose",
    "license"      : "https://creativecommons.org/licenses/by-sa/3.0/"
}
__version__ = __metadata__["modified"]

descr = """
=Description=

Dominμs (actually DOMin&mu;s, or "DOM in μs") provides a persistent,
random-access representation of
the DOM information expressed by HTML or XML documents. It can handle very
large documents. Because it parses a document once and saves a direct
represenation of the DOM structure, the document can be opened to any point
very rapidly.

If you don't need to modify the document in compiled form, the records can
be considerably smaller -- like the first-child id only needs a bit.

The API is DOM, plus a number of additions to make things more readable
and more Pythonic.


=Classes=

==Node==

Node has a subclass for each other node type, as usual in DOM.

Each Node in principle has an array of its childNodes (which may be empty),
and a dict of its attributes.
BUt in addition, [] notation is supported for easy/Pythonic access
to child nodes, attributes, etc. So if you prefer, you can just say:

    ch = curNode[3]
    last = curNode[-1]
    p1 = curNode["p", 1]
    cl = curNode["@class"]

Attributes can be accessed in the same way, merely prefixing "@" to their names
(since "@" can never start an element type name or a number).

==Document==

This class owns document-level information, and provides a convenient way to
get to the document underneath. Minimally, it points to the document's topmost
element, but in the case of forests in may point to several, and it also
encapsulates global information such as the character encoding.

==PDocument==

This is a variant of Document, which keeps the data as a persistent structure,
and updates as needed. It is best for very large documents (including ones where
the DOM won't fit in main memory), and for document that do not greatly change
(changes gradually degrade locality of reference, making things slower).\

* Construct
* Parse
* Serialize
* Rebuild


=Known Bugs and Limitations=

Needs to save byte-order type in header.

Very long sibling chains can be slow. This could be fixed with skip-lists, but
seems a rare enough requirement that I haven't bothered.

Tables of contents on very large documents may have poor locality of reference.

Should perhaps support compressed files directly.


=Notes=

Python XML-B

Pack text to one string
    space as block elements?
    normalize whitespace (but pre)
    tx of generated text, hidden (strike, del,…)
    unicode normalize

pack names to dicts:
    element types
    namespaces
    attr names (gi@attr?)
    attr values
    pi targets
    pi values
    comments

pack elements to tree:
    gi | #text | #pi | #com | #meta
        #meta is trojan+/-, cdata, entity, nsprefix?
    ->attrs
    parent
    fchild
    lchild
    lsib
    rsib
    fnonChild
    #trojanStart | #trojanEnd

represent ‘hidden’ strings?

lose:
    cdata and entity structure
    possibly track general entity boundaries


=References=

This is similar to a method pioneered by "DynaText", which was very
popular for large-scale document delivery in the late 80s through 90s.
See US Patents including 5557722 (apparently expired).

DeRose, Steven J. “JSOX: A Justly Simple Objectization for XM.”
Presented at Balisage: The Markup Conference 2014,
Washington, DC, August 5 - 8, 2014. In I<Proceedings of Balisage: The Markup Conference 2014>. Balisage Series on Markup Technologies, vol. 13 (2014). [https://doi.org/10.4242/BalisageVol13.DeRose02].


=History=

* Written ~2016 by Steven J. DeRose. Largely based on binaryXM<L.pl,
a Perl version I wrote beginning around 2009-12-31.

* 2019-12-30: Integrate with DomExtensions, DomBuilder, etc.

* 2023-11-21: lint, type-hints.


=Rights=

Copyright 2016, 2019 by Steven J. DeRose.
Licensed under Creative Commons Attribution-Sharealike unported.
See [http://creativecommons.org/licenses/by-sa/3.0/ for more information].

For the most recent version, see [http://www.derose.net/steve/utilities]
or [http://github.com/sderose].


=Options=
"""


###############################################################################
#
class NodeNames(dict):
    """Keep a file that lists all the known element type names, in an order
    that doesn't change, so the edir can refer to them by number.

    This could be stored in the text file.
    """

    # Each node *type* has a corresponding *name*, which is the type name
    # with "#" on the front. Not sure all of them are needed, but this way
    # we've got them in case, and the numbers are as expected, so we could
    # even save the nodeType field entirely.
    #
    # Elements have an actual name; those names are assigned higher numbers,
    # and never begin with "#" (like the singleton reserved DOM nodeNames).
    # If attributes, entities, notations, doctype, and/or PI target end up in
    # the edir as full-fledged nodes, they would need prefixes, too.
    #
    RESERVED_NAMES = [
        # nodeType                      Num   Pfx  NodeName
        # =====================================================================
        "#UNSPECIFIED_NODE",             # 0     #  #none [free list]
        "#ELEMENT_NODE",                 # 1        ELEMENT TYPE NAME
        "#ATTRIBUTE_NODE",               # 2        ATTRIBUTE NAME
        "#text_NODE",                    # 3     #  #text
        "#CDATA_SECTION_NODE",           # 4     #  #cdata-section
        "#ENTITY_REFERENCE_NODE",        # 5     &  ENTITY REFERENCE NAME
        "#ENTITY_NODE",                  # 6     +  ENTITY NAME
        "#PROCESSING_INSTRUCTION_NODE",  # 7     ?  TARGET
        "#comment_NODE",                 # 8     #  #comment
        "#DOCUMENT_NODE",                # 9     #  #document
        "#DOCUMENT_TYPE_NODE",           # 10    !  DOCUMENT TYPE NAME
        "#DOCUMENT_FRAGMENT_NODE",       # 11    #  #document-fragment
        "#NOTATION_NODE",                # 12    *  NOTATION NAME
    ]

    def __init__(self, path=None):
        super(NodeNames, self).__init__()
        self.path = path
        self.num2name = []
        if (not os.path.exists(path)):
            for r in NodeNames.RESERVED_NAMES: self.addName(r)
            return
        fh = codecs.open(path, "r", encoding="utf-8")
        for tag in fh.readlines(): self.addName(tag)
        fh.close()

    def write(self):
        fh = codecs.open(self.path, "w", encoding="utf-8")
        for tag in self.num2name: fh.write(tag)
        fh.close()

    def addName(self, tag):
        tag = tag.strip()
        n = len(self.num2name)
        self.num2name.append(tag)
        self[tag] = n

    def close(self):
        pass


###############################################################################
#
class TextPieces:
    """Manage a file that contains the non-fixed-length info for each node,
    including:
        * the text of text nodes
        * the content of comments
        * the target and content of pis.
        * the attribute list of start tags
    This does *not* include the element type name, which is stored as an index
    into an array of such names, kept in a separate file (it could, however,
    be just as well kept as a block in the TextPieces file).

    NOTE: In order to be able to use plain readline() to read each string, all
    literal newlines in texst content get turned into some illegal XML char.

    Optimizing this file once it gets fragmented and re-ordered, is probably
    best done by traversing the owning edir, and just copying to a new file as
    you go, then swapping in the new file and discarding the old one.

    TODO: Better way to manager rewrite-in-place when possible. Perhaps just
    cache the last-place-freed and use it if it fits?
    """
    NEWLINE_PROXY = chr(26)
    FILL_CHAR = chr(1)

    def __init__(self, path=None):
        self.path = path
        self.tph = codecs.open(self.path, "r", encoding="utf-8")
        self.freeList = []
        self.clearFreeSpace = True

    def readStringAt(self, offset):
        self.tph.seek(offset)
        piece = self.tph.readline()
        return piece.replace(TextPieces.NEWLINE_PROXY, "\n")

    def writeString(self, buf):
        needed = len(buf)
        offset, avail = self.findFreeBlock(needed)
        self.writeStringAt(offset, buf)
        return offset, max(avail, needed)

    def writeStringAt(self, offset, buf):
        self.tph.seek(offset)
        self.tph.write(TextPieces.FILL_CHAR * len(buf))

    def freeStringAt(self, offset):
        buf = self.readStringAt(offset)
        buflen = len(buf)
        if (self.clearFreeSpace):
            self.writeStringAt(offset, TextPieces.FILL_CHAR * len(buf))
        self.freeList.append((offset, buflen))
        return buflen

    def findFreeBlock(self, needed):
        """Find where you can write a text piece of a given size. Either
        take the best fit from the freeList, or pass back the offset to EOF.
        """
        best = None
        bestOffset = None
        bestSize = None
        for i in range(len(self.freeList)):
            sz = self.freeList[i][1]
            if (sz < needed): continue
            if (bestSize is not None and bestSize < sz): continue
            best = i
            bestOffset = self.freeList[i][0]
            bestSize = sz
        if (bestSize is not None):
            del self.freeList[best]
        else:
            self.tph.seek(0, os.SEEK_END)
            bestOffset = self.tph.tell()
            bestSize = 0
        return bestOffset, bestSize

    def close(self):
        self.tph.close()


###############################################################################
#
class TextishPieces(TextPieces):
    """Also support internal structure of attribute strings.
    For now, just escape/unescape as needed; could instead ditch XML syntax
    and store as a series of alternating name and value strings, separated
    by some non-XML character.
    """
    ATTR = r"\s*(\w[-:.\s]*)\s*=\s*(\"[^\"]*\"|'[^']*')"

    def readAttrAt(self, offset, aname):
        attrs = self.readAttrsAt(offset)
        if (aname in attrs): return attrs[aname]
        return None

    def readAttrsAt(self, offset):
        attrs = {}
        buf = self.readStringAt(offset)
        for mat in re.finditer(TextishPieces.ATTR, buf):
            avalue = mat.group(2)[1:-1]
            attrs[mat.group(1)] = XStr.unescapeXml(avalue)
        return attrs

    def setAttrAt(self, offset, aname, avalue):
        attrs = self.readAttrsAt(offset)
        attrs[aname] = avalue
        offset, sz = self.writeAttrs(attrs)
        return offset, sz

    def writeAttrs(self, attrs):
        buf = self.encodeAttrs(attrs)
        offset, sz = self.writeString(buf)
        return offset, sz

    def encodeAttrs(self, attrs):
        buf = ""
        for k, v in attrs.items():
            buf += " %s=\"%s\"" % (k, XStr.escapeAttribute(v))
        return buf


###############################################################################
#
# Node, Document, Element, Text, CDATASection,
# ProcessingInstruction, Comment, EntityReference, Notation

class Node(basedom.Node):
    """This maps 1:1 to nodes as represented on disk, though the size of ints
    stored can be changed. The disk records are fixed-size so they can be
    addressed rapidly by serial number (= element id = eid).

    TODO: Integrate code from Node.py from basedom.py (nee RealDOM.py).

    So, how do we dereference a node, when all we have is the number?
    Presumably, xxx.__getitem__ just gets called to get us the real node,
    then we operate on it per usual? But Nodes aren't really an array anyway,
    they're supposed to be objects. So we really have to trap the attempt
    to reference a memory address when all we have is an int. How?

    Like when user writes myNode.parentNode.nodeType, what happens?
    We can make a legit node and then refer to it, but what do we do for the
    ones that aren't loaded yet?
    """

    def __init__(self, nodeType:Union[int, NodeTypes],
        ownerDocument:'Document'=None, nodeName:NmToken=None):
        super(Node, self).__init__(nodeType=nodeType,
            ownerDocument=ownerDocument, nodeName=nodeName)

        self.eid             = 0
        self.parentNode      = 0
        self.previousSibling = 0
        self.nextSibling     = 0
        self.fchild          = 0
        self.tstart          = 0
        self.nodeType           = 0
        self.flags           = 0

        #self.attributes      = None  # ELEMENT only
        #self.text            = None  # TEXT, COMMENT, CDATA, PI only
        #self.target          = None  # PI only (maybe also entref, doctype, etc.?)

        self.nsPrefix        = None
        self.nsURI           = None
        self.nodeValue       = None  # TODO
        self.nsAttributes    = None  # TODO
        self.data            = None

        self.ownerDocument   = None
        self.childNodes      = None  # TODO: Lazy evaluation?

    def fromRawNode(self, pdocument, rawNode:EDirRec) -> Node:
        """Construct a Node object from an edir record. The EDirRec already
        has the disk format divided into fields, but indirect items (like
        names) have not yet been retrived and filled in). TODO: Change?
        """
        unpackedNode = pdocument.edir.unpackEDR(rawNode)
        nodeType = unpackedNode.nodeType
        nodeName = pdocument.fetchText(unpackedNode.nameStart)
        n = self.makeNodeByType(pdocument, nodeType, nodeName)

        n = Node(nodeType=nodeType)
        n.nodeName        = nodeName
        n.eid             = unpackedNode.eid
        n.parentNode      = unpackedNode.parent
        n.previousSibling = unpackedNode.previousSibling
        n.nextSibling     = unpackedNode.nextSibling
        n.fchild          = unpackedNode.fchild
        n.tstart          = unpackedNode.tstart
        n.flags           = unpackedNode.flags
        n.ownerDocument   = pdocument

        if (n.nodeType == Node.ELEMENT_NODE):
            if (n.tstart): n.attributes = pdocument.tPieces.readAttrsAt(n.tstart)
        elif (n.nodeType == Node.TEXT_NODE):
            if (n.tstart): n.data = pdocument.tPieces.readStringAt(n.tstart)
        elif (n.nodeType == Node.CDATA_SECTION_NODE):
            if (n.tstart): n.data = pdocument.tPieces.readStringAt(n.tstart)
        elif (n.nodeType == Node.PROCESSING_INSTRUCTION_NODE):
            if (n.tstart):
                buf = pdocument.tPieces.readStringAt(n.tstart)
                mat = re.match(r"^(\S*)(.*)", buf)
                if (mat):
                    n.target = mat.group(1)
                    n.data = mat.group(2).strip()
                else:
                    n.data = buf
        elif (n.nodeType == Node.COMMENT_NODE):
            if (n.tstart): n.data = pdocument.tPieces.readStringAt(n.tstart)
        return n

    def makeNodeByType(self, pdocument, typ, name:str=""):
        if (typ == Node.ELEMENT_NODE):
            return pdocument.Element(name)
        elif (typ == Node.TEXT_NODE):
            return pdocument.Text()
        elif (typ == Node.CDATA_SECTION_NODE):
            return pdocument.CDATA()
        elif (typ == Node.PROCESSING_INSTRUCTION_NODE):
            return pdocument.PI()
        elif (typ == Node.COMMENT_NODE):
            return pdocument.Comment()
        else:
            assert False, "Shouldn't be making node type %s." % (typ)


###############################################################################
#
class Document(basedom.Document):
    def __init__(self,
        namespaceUri:str="http://example.com",
        qualifiedName:str="root",
        doctype:str="root",
        isFragment:bool=False
        ):
        super(Document, self).__init__(
            namespaceUri=namespaceUri,
            qualifiedName=qualifiedName,
            doctype=doctype,
            isFragment=isFragment)

        self.isFragment = isFragment
        self.impl       = "sjd2016"
        self.version    = __version__
        self.language   = "XML"
        self.version    = "1.0"
        self.encoding   = "utf-8"
        self.standalone = True

        self.IDIndex       = {}        # Optional caseInsensitive
        self.loadedFrom    = None
        self.characterSet2 = "utf-8"
        self.mimeType      = "text/HTML"
        self.uri           = None
        self.iString       = "    "    # For indenting with tostring()

        self.doctypeNode   = None  #basedom.Doctype(self, doctype)

    @property
    def all(self):  # Obsolete, but trivial to support
        return(self.IDIndex)
    #@property
    #def async(self):
    #    raise NotImplementedError
    @property
    def characterSet(self):
        return self.characterSet
    @property
    def charset(self):
        return self.characterSet
    @property
    def compatMode(self):
        raise NotImplementedError
    @property
    def contentType(self):
        return self.mimeType
    @property
    def doctype(self):
        return self.doctypeNode
    @property
    def documentElement(self):
        return self
    @property
    def documentURI(self):
        return self.uri
    @property
    def domConfig(self):
        raise NotImplementedError
    @property
    def fullscreen(self):
        raise NotImplementedError
    @property
    def hidden(self):
        raise NotImplementedError
    @property
    def implementation(self):
        raise NotImplementedError
    @property
    def inputEncoding(self):
        return self.characterSet

    # Browser-specific-ish stuff:
    @property
    def lastStyleSheetSet(self):
        raise NotImplementedError
    @property
    def pointerLockElement(self):
        raise NotImplementedError
    @property
    def preferredStyleSheetSet(self):
        raise NotImplementedError
    @property
    def scrollingElement(self):
        raise NotImplementedError
    @property
    def selectedStyleSheetSet(self):
        raise NotImplementedError
    @property
    def styleSheets(self):
        raise NotImplementedError
    @property
    def styleSheetSets(self):
        raise NotImplementedError
    @property
    def timeline(self):
        raise NotImplementedError
    @property
    def undoManager(self):
        raise NotImplementedError
    @property
    def URL(self):
        return self.uri
    @property
    def visibilityState(self):
        raise NotImplementedError
    @property
    def xmlEncoding(self):
        return self.xmlEncoding

    # Methods
    #
    # Note: The "create..." methods pass "self" as an extra argument,
    # because this is class *Document*, and all the nodes created in a
    # Document store a pointer back, as "ownerDocument".
    #
    def createElement(self, tagName:NmToken, attributes:Dict=None,
        parent:Node=None, text:str=None) -> 'basedom.Element':
        newNode = Element(self, nodeName=tagName)
        if attributes:
            for a, v in attributes.items():
                newNode.setAttribute(a, v)
        return(newNode)

    # TODO ??? createDocumentFragment()

    def createTextNode(self, data):
        newNode = Text(data, self)
        return(newNode)

    def createComment(self, data):
        newNode = Comment(data, self)
        return(newNode)

    def createCDATASection(self, data):
        newNode = CDATASection(self, data)
        return(newNode)

    def createProcessingInstruction(self, target, data):
        newNode = ProcessingInstruction(self, target, data)
        return(newNode)

    def createEntityReference(self, name):
        newNode = EntityReference(self, name)
        return(newNode)

    def tostring(self):  # Document
        indent = ""  #self.iString * depth
        buf = indent + """<?xml version="1.0" encoding="utf-8"?>\n"""
        buf += self.doctypeNode.tostring() + "\n"
        buf += "\n<!-- n children: %d -->\n" % (len(self.childNodes))
        for ch in self.childNodes:
            buf += ch.tostring()
        return(buf)

    # End class Document


###############################################################################
#
class Element(basedom.Element):
    _Dominus = True

    def find(self):
        pass

    def findAll(self):
        pass

    def getAttributeNodeNS(self, ns, an):
        pass

    def insertAdjacentHTML(self, html):
        pass

    def matches(self):
        pass

    def querySelector(self):
        pass

    def querySelectorAll(self):
        pass

    def removeChild(self, oldChild:'Node') -> 'Node':
        pass

    def setAttributeNode(self, an, av):
        pass

    def setAttributeNodeNS(self, ns, an, av):
        pass

class Text(basedom.Text):
    _Dominus = True

class CDATASection(basedom.CDATASection):  # data
    _Dominus = True

class ProcessingInstruction(basedom.ProcessingInstruction):
    _Dominus = True

class Comment(basedom.Comment):
    _Dominus = True

class EntityReference(basedom.EntityReference):
    _Dominus = True

class Notation(basedom.Notation):
    _Dominus = True


###############################################################################
#
class Dominus():
    """The DOM implementation itself, which works with persistent disk data.
    Nodes (not including attribute/namespace) are numbered from *1*,
    (leaving 0 to represent NULL). They are kept in a fixed-size-record file.
    Text (content, attrs, comments, pis content, etc) are packed into a
    separate file.
    """
    def __init__(self, dirPath:str, eidSize:int=4):
        assert os.path.isdir(dirPath)
        assert eidSize in [ 2, 4, 8 ]

        self.dirPath  = dirPath
        self.eidSize  = eidSize
        self.edirPath = os.path.join(dirPath, "edir.dat")
        self.textPath = os.path.join(dirPath, "text.dat")
        self.namePath = os.path.join(dirPath, "name.dat")

        self.theDoc   = None
        self.theIndex = []
        self.curEID   = None
        self.header   = HeaderInfo()

        self.nameCounts   = None

        self.edir = EDir(self.edirPath)
        self.tPieces = TextishPieces(self.edirPath)
        self.nodeNames = NodeNames(self.namePath)
        self.headerInfo = HeaderInfo(self.edir.edirFH)

        # All the nodes we've loaded.
        self.nodes = {}

    def parse_file(self, path):
        pass
        # Pull code in from basedom.py (nee RealDOM.py).

    def close(self):
        self.edir.close()
        self.tPieces.close()
        self.nodeNames.close()

    def msg(self, m:str) -> None:
        print(m)

    def getDOMImplementation(self):
        return Dominus(args.dirPath)

    def createDocument(self, name:str):
        self.theDoc = Document(name)


    ##############################################################################
    #
    def loadXML(self, path:str):
        self.theDoc = DomBuilder.DomBuilder(path)


###############################################################################
#
if __name__ == "__main__":
    import argparse
    def processOptions():
        try:
            from BlockFormatter import BlockFormatter
            parser = argparse.ArgumentParser(
                description=descr, formatter_class=BlockFormatter)
        except ImportError:
            parser = argparse.ArgumentParser(description=descr)

        parser.add_argument(
            "--dirPath", type=str,
            help="Where to find/put the disk-resident DOM.")
        parser.add_argument(
            "--echo", action="store_true",
            help="Reconstruct and print the XML.")
        parser.add_argument(
            "--iencoding", type=str, default="UTF-8",
            choices=[ "UTF-8", "UTF-16", "ISO-8859-1", "ASCII" ],
            help="Encoding to assume for the input. Default: UTF-8.")
        parser.add_argument(
            "--istring", type=str, default="    ",
            help="String to repeat to make indentation.")
        parser.add_argument(
            "--ns", action="store_true",
            help="Activate expat namespace handling.")
        parser.add_argument(
            "--quiet", "-q", action="store_true",
            help="Suppress most messages.")
        parser.add_argument(
            "--verbose", "-v", action="count", default=0,
            help="Add more messages (repeatable).")
        parser.add_argument(
            "--version", action="version", version=__version__,
            help="Display version information, then exit.")

        parser.add_argument(
            "files", nargs=argparse.REMAINDER,
            help="Path(s) to input file(s).")
        args0 = parser.parse_args()
        return args0

    args = processOptions()

    if (len(args.files) == 0):
        testFile = os.path.join(os.environ["sjdUtilsDir"],
            "Data/boilerplate/XMLRegexes")
        if (not os.path.exists(testFile)):
            raise ValueError("No file specified, and default %s not found." %
                (testFile))
        args.files.append(testFile)

    for thePath in args.files:
        if (not os.path.isfile(thePath)):
            print("No file at '%s'." % (thePath))
            continue
        print("Building the DOM for '%s'." % (thePath))
        theDom = DomBuilder.DomBuilder(
            #thePath, domImpl=xml.dom.minidom, verbose=args.verbose)
            thePath, verbose=args.verbose)
        print("\nResults:")
        print(theDom.tostring())
