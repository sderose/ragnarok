#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
import re
import os
from collections import namedtuple
#import codecs
import struct
import array
from typing import IO, Dict

from runeheim import XmlStrings as Rune
from prettyxml import FormatXml
#import BaseDOM
from basedom import Node
import DomBuilder

__metadata__ = {
    "title"        : "Edir",
    "description"  : "A disk-resident DOM Node tree, similar to DynaText's 'edir'.",
    "rightsHolder" : "Steven J. DeRose",
    "creator"      : "http://viaf.org/viaf/50334488",
    "type"         : "http://purl.org/dc/dcmitype/Software",
    "language"     : "Python 3.7",
    "created"      : "2016",
    "modified"     : "2024-06-28",
    "publisher"    : "http://github.com/sderose",
    "license"      : "https://creativecommons.org/licenses/by-sa/3.0/"
}
__version__ = __metadata__["modified"]

descr = """
=Description=

This class is part of Dominμs, and manages a single disk file, which is
an array of node-recors.

=Classes=


=Known Bugs and Limitations=

Needs to save byte-order type in header.

Very long sibling chains can be slow. This could be fixed with skip-lists, but
seems a rare enough requirement that I haven't bothered.

Tables of contents on very large documents may have poor locality of reference.

Should perhaps support compressed files directly.


=Notes=

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

* 2024-06-28: Split these classes out from Sleipner0.py.


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
class NodePool(array.array):
    """Keep some nodes, indexed by EID. This is parallel to the EDir on
    disk, but is only sparsely loaded (demand cached).

    A request for a node by its EID can just be made via []. If the node is
    already in memory, the real pointer comes back; if not, the Thing King
    first fetches it from the warehouse to the workshop, then it is zarked.

    For now the caching strategy will be simple -- like keep up to a specified
    number of nodes around, then flush those farthest from recent requests.
    """
    def __init__(self):
        super(NodePool, self).__init__("o", 1000)

    def __getitem__(self, n, m=None):
        # TODO: Finish
        if m is None:
            self.ensureLoaded(m)
            return self[m]
        assert m > n
        for i in range(m, n):
            self.ensureLoaded(i)
        return self[n:m]

    def ensureLoaded(self, n):
        """Check whether the specified entry is loaded (not None), and load
        it if needed. If there is no such index available, return None.
        """


###############################################################################
#
class EDir:
    """A file of Nodes on disk. This can be read and written,
    but to make a "real" Node you have to expand some other things, like
    the actual text, attributes, element type names, the eid you got it from.
    """
    FIELD_COUNT = 8

    def __init__(self, edirPath:str, eidSize:int=4):
        self.edirPath = edirPath
        self.eidSize = eidSize
        self.edirFH = open(edirPath, "wb")
        self.header = HeaderInfo(fh=self.edirFH, eidSize=eidSize)
        self.edirRecSize = self.eidSize * EDir.FIELD_COUNT

        # Lay out (non-header) records for the index file:
        self.bytesToSpare = HeaderInfo.HEADER_BYTES - (8 + 4 + 1*4 + 2*2 + 2*1)
        self.headerFormat = "!8s4sihhbb%ds" % (self.bytesToSpare)

    def getNode(self, eid) -> Node:
        """Read a given packed EDirRec from disk, construct a regular Node
        from it, and hand that back.
        """
        pdocument = None  # TODO ???
        offs = self.getOffset(eid)
        self.edirFH.seek(offs)
        buf = self.edirFH.read(self.edirRecSize)
        rawNode = EDirRec(self, buf)    # TODO: theSleipner0 needed?
        fullNode = EDirRec.fromRawNode(pdocument, rawNode)
        return fullNode

    def getOffset(self, eid):
        assert (eid > 0)
        return HeaderInfo.HEADER_BYTES + (eid * self.edirRecSize)

    def close(self):
        self.edirFH.close()

    def readHeader(self, ifh:IO):
        ifh.seek(0, 0)
        buf = ifh.read(HeaderInfo.HEADER_BYTES)
        hfields = struct.unpack(self.headerFormat, buf)
        return hfields

    def makeNewEdirFile(self):
        assert False

###############################################################################
#
class HeaderInfo:
    """EDir fle header information object and I/O.
    Can fit in 32 bytes, but then node data (nodeName, attr n/v, text...)
    will rarely fit, and be bumped to external file.
    nodeName could also be repalced by a short code, mapped somewhere.
    """
    HEADER_BYTES = 64
    HEADER_USED = 32
    HEADER_PAD = HEADER_BYTES - HEADER_USED
    HEADER_FORMAT = "!QHHHHIIQ%dx" % (HEADER_PAD)

    if (struct.calcsize(HEADER_FORMAT) != HEADER_BYTES):
        raise ValueError("HEADER actual size is %d." %
            (struct.calcsize(HEADER_FORMAT)))

    def __init__(self, fh:IO=None, eidSize:int=4):
        self.magic        = "VOBISCUM" # %-8s  -- identify file type
        self.endianity    = bytes("NETW")     # %-4s  -- how to read numbers
        self.majorVersion = 0
        self.minorVersion = 1
        self.majorOld     = 0
        self.minorOld     = 1

        self.encoding     = 0
        self.eidSize      = 4
        self.recordSize   = 32         # short
        self.freeList     = 0          # int   -- -> chain of free nodes (unused)

        if (fh): self.read(fh)

    def read(self, fh):
        fh.seek(0)
        buf = fh.read(64)
        (
            self.magic,
            self.majorVersion,
            self.minorVersion,
            self.majorOld,
            self.minorOld,
            self.encoding,
            self.eidSize,
            self.freeList
            ) = struct.unpack(buf, HeaderInfo.HEADER_FORMAT)

    def write(self, fh):
        buf = struct.pack(HeaderInfo.HEADER_FORMAT,
            self.magic,
            self.majorVersion,
            self.minorVersion,
            self.majorOld,
            self.minorOld,
            self.encoding,
            self.eidSize,
            self.freeList
        )
        assert len(buf) == HeaderInfo.HEADER_BYTES
        fh.seek(0, 0)
        fh.write(buf)


###############################################################################
#
EDRInfo = namedtuple("EDRInfo", [
    "parent",
    "previousSibling",
    "nextSibling",
    "fchild",
    "tstart",
    "nodeType",  # OR nodeName?
    "nodeName",
    "childNum",
    "flags"
])

class EDirRec:
    """Just handles unpacking a record from the EDir into an object. This is
    not a full-fledged Node, because it has not decoded the element type,
    fetched attributes or content, filled in all the extra DOM properties, etc.
    But it can be coded back into a record again.

    Contents of such records (16, 26, or 46 byte records):
        eidSize parent    EID of parent node
        eidSize lsib      Left sibling
        eidSize rsib      Right sibling
        eidSize fchild    First child
        eidSize tstart    Start of attlist or leaf data in "text" file
              2 nodeType  nodeType
              2 nodeName  node/name, as index into saved list.
              2 childNum  childnum among siblings; if 65535 calculate on the fly.
              4 flags     (reserved)

    TO DO: Look into adding skip-list pointers; more to maintain but faster.
    """
    EDIR_FORMAT_2 = "!5HHHI"  # 20
    EDIR_FORMAT_4 = "!5IHHI"  # 30
    EDIR_FORMAT_8 = "!5QHHI"  # 50

    @staticmethod
    def eidSizeToBufSize(eidSize:int=4) -> int:
        fmt = EDirRec.getPackFormat(eidSize)
        return struct.calcsize(fmt)

    @staticmethod
    def getPackFormat(eidSize:int=4) -> int:
        if (eidSize==4): return EDirRec.EDIR_FORMAT_4
        if (eidSize==2): return EDirRec.EDIR_FORMAT_2
        if (eidSize==8): return EDirRec.EDIR_FORMAT_8
        raise IOError("Bad eidSize %d." % (eidSize))

    def __init__(self, theSleipner0:'Sleipner0', buf, eidSize:int=4, eid:int=0):
        assert len(buf) == EDirRec.eidSizeToBufSize(eidSize)
        self.theSleipner0 = theSleipner0
        self.eid = eid
        self.eidSize = eidSize
        self.dat = None  # Lazy loading from tstart?
        self.attlist = None
        #self.type = None

        self.recordSize   = 64
        self.eidSize     = (self.recordSize - (5*4 + 2*2 + 1*1))
        self.recordFormat = "!iiiiihhb%ds" % (self.eidSize)

        edrt = self.unpackEDR(buf)
        (
            self.parent,
            self.previousSibling,
            self.nextSibling,
            self.fchild,
            self.tstart,   # TODO Add tlen? or use NUL & C0?
            self.nodeType,
            self.nodeName,
            self.childNum,
            self.flags
        ) = edrt
        if (self.tstart):
            self.dat = self.fetchData()

    def fetchData(self):
        """Get the text data for a node (#text for text, attrs for elements)
        These are just supposed to be \\0-terminated.
        """
        self.theSleipner0.dfh.seek(self.tstart, 0)
        self.dat = self.theSleipner0.dfh.readToChar()
        if (self.nodeType == Node.ELEMENT_NODE):
            self.attlist = self.parseAttlist(self.dat)
            self.dat = None
        return self.dat

    def parseAttlist(self, attlist:str) -> Dict:
        attrs = {}
        for mat in re.finditer(
            r"""([-.:\w]+)\s*=\s*('[^']*'|"[^"]*")\s*""", attlist):
            attrs[mat.group(1)] = mat.group(1)
        return attrs

    def readToChar(self, ifh:IO, char:str=chr(0)) -> str:
        """Read until we hit a NULL, remove it, and return the rest.
        """
        buf = array.array()
        while (True):
            c = ifh.read(chars=1)
            if (len(c)==0 or c==char): break
            buf.append(c)
        return "".join(buf)

    def unpackEDR(self, buf, eidSize:int=4) -> tuple:
        fmt =self.getPackFormat(eidSize)
        edrt = EDRInfo(struct.unpack(buf, fmt))
        return edrt

    def packEDR(self, eidSize:int=4) -> bytes:
        fmt =self.getPackFormat(eidSize)
        edrt = EDRInfo(
            self.parent,
            self.previousSibling,
            self.nextSibling,
            self.fchild,
            self.tstart,
            self.nodeType,
            self.nodeName,
            self.childNum,
            self.flags
        )
        buf = struct.pack(fmt, edrt)
        assert len(buf) == struct.calcsize(fmt)
        return buf

    def readRecord(self, theSleipner0):
        buf = theSleipner0.edir.edirFH.read(theSleipner0.header.recordSize)
        return EDirRec(buf, theSleipner0.header.eidSize)

    def writeRecord(self, ofh:IO, dfh:IO, node:'Node'):
        # Figure out where to write other node data
        dat = None
        if (node.nodeType==Node.ELEMENT_NODE):
            #nat = len(node.attributes)
            dat = node.nodeName
        elif (node.nodeType==Node.ATTRIBUTE_NODE):
            aname = node.name
            avalue = FormatXml.escapeAttribute(node.value)
            dat = "%s=%s" % (aname, avalue)
        elif (node.nodeType==Node.PROCESSING_INSTRUCTION_NODE):
            tgt = node.target
            pidata = FormatXml.escapePI(node.data)
            dat = "%s %s" % (tgt, pidata)
        else:  # Other nodeTypes
            dat = node.data
        if (dat is None):
            dat = "@[0x%x,0x%s]" % (dfh.tell(), len(node.data))

        buf = self.packEDR()
        ofh.write(buf)

    @staticmethod
    def fromRawNode(pdocument, rawNode:EDirRec):
        """Construct a Node object from an edir record. The EDirRec already
        has the disk format divided into fields, but indirect items (like
        names) have not yet been retrived and filled in). TODO: Change?
        """
        n = Node(rawNode.nodeType)
        n.eid             = rawNode.eid
        n.parentNode      = rawNode.parent
        n.previousSibling = rawNode.previousSibling
        n.nextSibling     = rawNode.nextSibling
        n.fchild          = rawNode.fchild
        n.tstart          = rawNode.tstart
        #n.nodeType        = rawNode.nodeType
        n.flags           = rawNode.flags

        if (n.nodeType == Node.ELEMENT_NODE):
            if (n.tstart): n.attributes = pdocument.tPieces.readAttrsAt(n.tstart)
        elif (n.nodeType == Node.ATTRIBUTE_NODE):
            assert(False)
        elif (n.nodeType == Node.TEXT_NODE):
            if (n.tstart): n.text = pdocument.tPieces.readStringAt(n.tstart)
        elif (n.nodeType == Node.CDATA_SECTION_NODE):
            if (n.tstart): n.text = pdocument.tPieces.readStringAt(n.tstart)
        elif (n.nodeType == Node.ENTITY_REFERENCE_NODE):
            assert(False)
        elif (n.nodeType == Node.ENTITY_NODE):
            assert(False)
        elif (n.nodeType == Node.PROCESSING_INSTRUCTION_NODE):
            if (n.tstart):
                buf = pdocument.tPieces.readStringAt(n.tstart)
                mat = re.match(r"^(\S*)(.*)", buf)
                if (mat):
                    n.target = mat.group(1)
                    n.text = mat.group(2).strip()
                else:
                    n.text = buf
        elif (n.nodeType == Node.COMMENT_NODE):
            if (n.tstart): n.text = pdocument.tPieces.readStringAt(n.tstart)
        elif (n.nodeType == Node.DOCUMENT_NODE):
            assert(False)
        elif (n.nodeType == Node.DOCUMENT_TYPE_NODE):
            assert(False)
        elif (n.nodeType == Node.DOCUMENT_FRAGMENT_NODE):
            assert(False)
        elif (n.nodeType == Node.NOTATION_NODE):
            assert(False)
        else:
            assert(False)

    def readRecordN(self, edirFH:IO, eid:int=None):
        """Read the nth EDir record, unpack, and make a Node. If eid is None,
        don't seek, just read the next one.
        """
        try:
            if (eid):
                edirFH.seek(self.recordSize*eid + HeaderInfo.HEADER_BYTES)
            stuff = edirFH.READ(self.recordSize)
            #unpack
            return(stuff)
        except IOError:  # Should just be EOF
            return(False)


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
