#!/usr/bin/env python3
#
# profiling.py: Run some stress tests on a DOM implementation.
# 2024-08-10: Written by Steven J. DeRose.
#
import sys
#import os
#import codecs
import math
import time
import logging
from random import randrange
from typing import Dict, List

from cProfile import Profile
from pstats import SortKey, Stats

if (0):
    print("******* Using minidom")
    from xml.dom.minidom import getDOMImplementation, Node
else:
    print("******* Using BaseDOM")
    from BaseDOM import getDOMImplementation, Node

lg = logging.getLogger("profiling.py")

__metadata__ = {
    "title"        : "profiling.py",
    "description"  : "",
    "rightsHolder" : "Steven J. DeRose",
    "creator"      : "http://viaf.org/viaf/50334488",
    "type"         : "http://purl.org/dc/dcmitype/Software",
    "language"     : "Python 3.9",
    "created"      : "2024-08-10",
    "modified"     : "2024-08-10",
    "publisher"    : "http://github.com/sderose",
    "license"      : "https://creativecommons.org/licenses/by-sa/3.0/"
}
__version__ = __metadata__["modified"]

descr = """
=Name=

profiling.py

=Description=

==Usage==

    profiling.py [options] [files]


=See also=


=Known bugs and Limitations=


=To do=

Focus popular methods:
    get ElementByID / Class / TagName
    querySelector/All
    innerHTML / textContent
    classList???
    createElement, createTextNode
    appendChild
    getAttribute() / setAttribute()

==Tactics==
    Traversal threading
    Eliminate/cache namednodelist level


=History=

* 2024-08-10: Written by Steven J. DeRose.


=Rights=

Copyright 2024-08-10 by Steven J. DeRose. This work is licensed under a
Creative Commons Attribution-Share-alike 3.0 unported license.
See [http://creativecommons.org/licenses/by-sa/3.0/] for more information.

For the most recent version, see [http://www.derose.net/steve/utilities]
or [https://github.com/sderose].


=Options=
"""


###############################################################################
#
def warmup():
    buf = ""
    for _i in range(100):
        x = randomText(100)
        buf += x
    return buf

theAttrs = {  "id": "A12", "class":"foo", "style":"font:Courier;" }

def runTests(fanout:int, textLen:int):
    warmup()
    t0 = time.time()
    doc = buildDoc(fanout, textLen, attrs=theAttrs)
    #traverseDoc(doc.documentElement)  # BaseDOM ~40% faster
    t2 = recursive_traverse(doc.documentElement)  # BaseDOM ~43% faster
    dt = time.time() - t0
    return doc, dt

def buildDoc(fanout:int, textLen:int, attrs:Dict=None):
    """On my Mac: fanout 50 should take a few seconds.
    Total nodes created = 2 * fanout**3 + fanout**2 + fanout
    """
    #x = randomText(textLen)
    x = getSomeText(textLen)

    impl = getDOMImplementation()
    doc = impl.createDocument(namespaceURI="foo.com", qualifiedName="testDoc",
        doctype=None)
    docEl = doc.documentElement
    addNChildren(docEl, name="div1", n=fanout, attrs=attrs)
    for i1, ch1 in enumerate(docEl.childNodes):
        addNChildren(ch1, name="div2", n=fanout, attrs=attrs)
        for i2, ch2 in enumerate(ch1.childNodes):
            addNChildren(ch2, name="div3", n=fanout, attrs=attrs)
            for i3, ch3 in enumerate(ch2.childNodes):
                tn = doc.createTextNode("%s.%d.%d.%d" % (x, i1, i2, i3))
                ch3.appendChild(tn)
    return doc

def addNChildren(node, name:str="div", n:int=100, attrs:Dict=None, rev:bool=False):
    doc = node.ownerDocument
    for _i in range(n):
        ch = doc.createElement(name)
        if (attrs):
            for k, v in attrs.items(): ch.setAttribute(k, v)
        if (not node.childNodes): node.appendChild(ch)
        elif (rev): node.insertBefore(ch, node.childNodes[0])
        else: node.appendChild(ch)

def randomText(n:int):
    buf = ""
    for _i in range(n):
        buf += chr(randrange(32, 126))
    return buf

def getSomeText(n:int):
    buf = """Lorem ipsum dolor sit amet, consectetur adipisicing elit, sed do
eiusmod tempor incididunt ut labore et dolore magna aliqua. Ut
enim ad minim veniam, quis nostrud exercitation ullamco laboris
nisi ut aliquip ex ea commodo consequat. Duis aute irure dolor in
reprehenderit in voluptate velit esse cillum dolore eu fugiat
nulla pariatur. Excepteur sint occaecat cupidatat non proident,
sunt in culpa qui officia deserunt mollit anim id est laborum. """
    ncopies = math.ceil(n/len(buf))
    return (buf * ncopies)[0:n]

def traverseDoc(docEl:Node):
    if ('eachNode' not in dir(docEl)):
        print("Patching in eachNode")
        Node.eachNode = localEachNode
    tot = 0
    for node in docEl.eachNode():
        tot += len(node.nodeName)
        if (node.nodeType == Node.ELEMENT_NODE and node.hasAttributes()):
            for a in node.attributes.keys():
                tot += len(node.getAttribute(a))
    return tot

def recursive_traverse(root:Node):
    """
    """
    yield root
    tot = 1
    if (not root.childNodes): return
    for ch in root.childNodes:
        tot += recursive_traverse(ch)
        ch.checkNode()
    return tot

def localEachNode(self:'Node', exclude:List=None, depth:int=1) -> 'Node':
    """~40% faster with BaseDOM than minidom.
    """
    if (exclude):
        if (self.nodeName in exclude): return
        if ("#wsn" in exclude and self.nodeName=="#text"
            and self.data.strip()==""): return
    yield self

    if (self.hasChildNodes()):
        for ch in self.childNodes:
            for chEvent in ch.eachNode(exclude=exclude, depth=depth+1):
                yield chEvent
    return


###############################################################################
# Main
#
if __name__ == "__main__":
    import argparse

    def processOptions() -> argparse.Namespace:
        try:
            from BlockFormatter import BlockFormatter
            parser = argparse.ArgumentParser(
                description=descr, formatter_class=BlockFormatter)
        except ImportError:
            parser = argparse.ArgumentParser(description=descr)

        parser.add_argument(
            "--fanout", type=int, metavar="N", default=50,
            help="How many children to create for each node.")
        parser.add_argument(
            "--iencoding", type=str, metavar="E", default="utf-8",
            help="Assume this character coding for input. Default: utf-8.")
        parser.add_argument(
            "--ignoreCase", "-i", action="store_true",
            help="Disregard case distinctions.")
        parser.add_argument(
            "--oencoding", type=str, metavar="E", default="utf-8",
            help="Use this character coding for output. Default: iencoding.")
        parser.add_argument(
            "--quiet", "-q", action="store_true",
            help="Suppress most messages.")
        parser.add_argument(
            "--textLen", type=int, metavar="N", default=500,
            help="How many children to create for each node.")
        parser.add_argument(
            "--unicode", action="store_const", dest="iencoding",
            const="utf8", help="Assume utf-8 for input files.")
        parser.add_argument(
            "--verbose", "-v", action="count", default=0,
            help="Add more messages (repeatable).")
        parser.add_argument(
            "--version", action="version", version=__version__,
            help="Display version information, then exit.")

        parser.add_argument(
            "files", type=str, nargs=argparse.REMAINDER,
            help="Path(s) to input file(s)")

        args0 = parser.parse_args()
        if (lg and args0.verbose):
            logging.basicConfig(level=logging.INFO - args0.verbose)

        return(args0)


    ###########################################################################
    #
    args = processOptions()
    if (args.iencoding and not args.oencoding):
        args.oencoding = args.iencoding
    if (args.oencoding):
        # https://stackoverflow.com/questions/4374455/
        # sys.stdout = codecs.getwriter("utf-8")(sys.stdout.detach())
        sys.stdout.reconfigure(encoding="utf-8")

    # Sorting:
    # 'calls'       SortKey.CALLS           call count
    # 'cumulative'  SortKey.CUMULATIVE      cumulative time
    # 'filename'    SortKey.FILENAME        file name

    with Profile() as profile:
        doc0, elapsed = runTests(fanout=args.fanout, textLen=args.textLen)
        (
            Stats(profile)
            .strip_dirs()
            .sort_stats(SortKey.CALLS)
            .print_stats()
        )

    print("Built doc in %6.3f sec." % (elapsed))
