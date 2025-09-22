#!/usr/bin/env python3
#
import sys
import struct
from typing import Dict, IO

from basedom import Node, CharacterData

class Sleip:
    """A class whose instances are bundles of the 8 fields of a node
    to be packed. Thse can be handed around, but also packed to just
    8*size bytes, or unpacked from those.
    """
    def __init__(self,
        eid:int, nsNum:int, ntNum:int, data:int,
        up:int, left:int, right:int, down:int):
        self.eid = eid
        self.nsNum = nsNum
        self.ntNum = ntNum
        self.data = data
        self.up = up
        self.left = left
        self.right = right
        self.down = down

    def fromNode(self, node:Node, nsnames:Dict, nodeNames:Dict) -> 'Sleip':
        eid = node.eid if hasattr(node, "eid") else id(node)
        nsNum = nsnames(node.nsURI) or 0
        ntNum = nodeNames(node.localName) or 0
        data = node.data or 0
        up = node.parentNode.eid or 0
        left = node.precedingSibling.eid or 0
        right = node.followingSibling.eid or 0
        down = node.childNodes[0] or 0
        return Sleip(eid, nsNum, ntNum, data, up, left, right, down)

    def packNode(self, fieldSize:int=4) -> bytes:
        if fieldSize not in [ 2, 4, 8 ]: raise ValueError(
            "Bad field size %d." % (fieldSize))
        key = "HIL"[ fieldSize >> 2 ]
        packed = struct.pack("!"+key*8,
            self.eid, self.nsNum, self.ntNum, self.data,
            self.up, self.left, self.right, self.down)
        return packed

    @staticmethod
    def fromPacked(packed) -> 'Sleip':
        s = sys.getsizeof(packed)
        if s == 16: key = "H"
        elif s == 32: key = "I"
        elif s == 64: key = "L"
        else: raise ValueError("Bad packed node size %d." % (s))
        return Sleip(*(struct.unpack("!"+key*8, packed)))

class BXML:
    """Support a packed binary interface to Dominµs Nodes.
    This is the top-level object, which knows:
        * a DOM to work with
        * a size (2/4/8) for nodes packed via Sleip
        * Dict of namespaces and names, assigning them codes
        * ? dict of text with offsets into a big buffer ?

    This is largely based on: DeRose, Steven et al. 1996. Data processing
    system and method for representing, generating a representation of and
    random access rendering of electronic documents.
    U.S. patent number 5,557,722 (expired). .

    However, it has some improvements:
        * Because fChild is not just a bit, nodes can be numbered arbitrarily,
          which allows tree modifications without renumbering.
        * It is size-adjustable (2/4/8 bytes node ids)
        * The total size is always a multiple of 8
        * Attributes are treated as full-fledged nodes, not just strings
        * It has namespace support
        * eids are opaque, so can be file offsets, array indices, or pointers.
    """
    ALIGN = 8
    SEPCHAR = "\uEDDA"

    def __init__(self, theDoc, size:int=4):
        self.doc = theDoc
        self.size = size
        self.eids = {}
        self.nsnames = None
        self.elemNames = None
        self.attrNames = None
        self.textMap = None

    def numberNodes(self) -> int:
        """Add a sequence number to every node (in order).
        """
        nodeNum = 0
        for node in self.doc.documentElement.descendants():
            nodeNum += 1
            node.eid = nodeNum
            if node.isElement and node.hasAttributes:
                for attrNode in sorted(node.attributes.keys()):
                    nodeNum += 1
                    attrNode.eid = nodeNum
        return nodeNum

    def makeTextMap(self, tgt:IO) -> int:
        """Pack all the text (incl. text node, pi, and comment data,
        attribute values,...) into one big file. No nulls, maybe round each
        piece to 2**n to later support compaction. Meh.
        """
        theMap = {}
        offset = 0
        for node in self.doc.documentElement.descendants(attrs=True):
            if isinstance(node, CharacterData):
                buf = node.data
            elif node.isAttribute:
                buf = node.nodeValue
            elif node.isElement:
                continue
            theMap[id(node)] = offset
            pad = 0  #len(buf) % BXML.ALIGN  # TODO Fix padding for utf-8
            tgt.write(buf + BXML.SEPCHAR*pad)
        return offset
