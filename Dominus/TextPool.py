#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
import re
import os
from collections import OrderedDict
import codecs
#import struct
#import array
from typing import Dict, Any

from xmlstrings import XMLStrings as XStr
#import BaseDOM
#import DOMBuilder

__metadata__ = {
    "title"        : "TextPool",
    "description"  : "A disk-resident set of strings, like DynaText's .tdir",
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

This maintains a pool of text chunks, intended to store the attribute lists
and text data of nodes for Dominμs.

The nodes simply refer to offsets and lengths in the file. For the moment,
the files just appends new items as needed; later it will maintain a freelist
or do garbage-collection.

Strings on disk have newlines changes to SUB (U+1A), and a real newline
added on the end. This means we can just use readline(), and then
translate back.
SUB is not an allowed XML character, and is also not NULL.
The \n is there for readability if one ever has to look in the file.


=Known Bugs and Limitations; To do=

Should perhaps support compressed files directly.

Should perhaps integrates with StrBuf (mutable string class).

Option to coalesce identical strings? Copy on write?

=Notes=


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
* 2019-12-30: Integrate with DomExtensions, DOMBuilder, etc.
* 2023-11-21: lint, type-hints.
* 2024-06-28: Split these classes out of Dominus.


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
class TextPool(OrderedDict):
    """Manage a file that contains the non-fixed-length info for each node,
    keyed by their starting offsets. They are used for:
        * the text of text nodes
        * the content of comments
        * the target and content of pis.
        * the attribute list of start tags

    To get at a string, just do myTextPool[offset]. If it's not cached it
    will be loaded.

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

    def __init__(self, path:str=None):
        # the dict itself, is keyed by offset, and serves as a cache.
        self.path = path
        self.tph = codecs.open(self.path, "rb", encoding="utf-8")
        self.freeList = []
        self.clearFreeSpace = True
        self.totalSize = 0

    def findEOF(self) -> int:
        cur = self.tph.tell()
        self.tph.seek(0, 2)
        size = self.tph.tell()
        self.tph.seek(cur)
        return size

    def __missing__(self, offset:int):
        """Handle a request for the text at a given offset, that failed
        (presumably because it hasn't been loaded yet). Move it to the
        end of the OrderedDict order, since it's now "most recent".
        """
        self.tph.seek(offset)
        buf = self.tph.readline()
        self[offset] = re.sub("\x1A", "\n", buf[0:-1])
        self.totalSize += len(self[offset])
        self.move_to_end(offset)
        return self[offset]

    def addString(self, buf) -> int:
        #needed = len(buf)
        #offset, avail = self.findFreeBlock(needed)
        offset = self.findEOF()
        self.writeStringAt(offset, buf)
        self[offset] = buf
        self.totalSize += len(self[offset])
        return offset

    def writeStringAt(self, offset, buf):
        self.tph.seek(offset)
        toWrite = buf.replace("\n", "\x1a") + "\n"
        self.tph.write(toWrite)

    def freeSpace(self, keepAmount:int=2<<20):
        """Drop the least-recently-used strings.
        """
        for k in self:
            self.totalSize -= len(self[k]+1)
            del self[k]
            if (self.totalSize <= keepAmount): return

    # As yet unused, manage a free space list
    #
    def freeStringAt(self, offset):
        buf = self[offset]
        buflen = len(buf)
        if (self.clearFreeSpace):
            self.writeStringAt(offset, TextPool.FILL_CHAR * len(buf))
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
class TextishPieces(TextPool):
    """Also support internal structure of attribute strings.
    For now, just escape/unescape as needed; could instead ditch XML syntax
    and store as a series of alternating name and value strings, separated
    by some non-XML character.
    """
    ATTR = r"\s*(\w[-:.\s]*)\s*=\s*(\"[^\"]*\"|'[^']*')"

    def readAttrAt(self, offset:int, aname:str) -> str:
        attrs = self.readAttrsAt(offset)
        if (aname in attrs): return attrs[aname]
        return None

    def readAttrsAt(self, offset:int) -> Dict:
        attrs = {}
        buf = self[offset]
        for mat in re.finditer(TextishPieces.ATTR, buf):
            avalue = mat.group(2)[1:-1]
            attrs[mat.group(1)] = XStr.unescapeXml(avalue)
        return attrs

    def setAttrAt(self, offset:int, aname:str, avalue:Any) -> (int, int):
        attrs = self.readAttrsAt(offset)
        attrs[aname] = avalue
        offset, sz = self.writeAttrs(attrs)
        return offset, sz

    def writeAttrs(self, attrs:Dict) -> (int, int):
        buf = self.encodeAttrs(attrs)
        offset, sz = self.addString(buf)
        return offset, sz

    def encodeAttrs(self, attrs:Dict) -> str:
        buf = ""
        for k, v in attrs.items():
            buf += " %s=\"%s\"" % (k, XStr.escapeAttribute(v))
        return buf


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
            "--iencoding", type=str, default="UTF-8",
            choices=[ "UTF-8", "UTF-16", "ISO-8859-1", "ASCII" ],
            help="Encoding to assume for the input. Default: UTF-8.")
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
        raise ValueError("No file specified.")

    for thePath in args.files:
        if (not os.path.isfile(thePath)):
            print("No file at '%s'." % (thePath))
            continue
        print("Building for '%s'." % (thePath))
        print("\nResults:")
