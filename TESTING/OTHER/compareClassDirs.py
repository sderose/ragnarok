#!/usr/bin/env python3
#
# Doesn't check instance variables
# What of stuff inherited from list/dict?
#
import sys
from collections import defaultdict, namedtuple

from xml.dom import minidom
import basedom

descr = """
Compare the dir() items in minidom vs. basedom.

[unfinished; rewrite?]

See also makeDefChart.py.
"""
whLib = minidom
theClasses = [
   whLib.DOMImplementation,
   whLib.NodeList,
   whLib.Node,
   whLib.Document,
   whLib.Element,
   whLib.CharacterData,
   whLib.Text,
   whLib.CDATASection,
   whLib.ProcessingInstruction,
   whLib.Comment,
   whLib.Attr,
   whLib.NamedNodeMap,

   #whLib.NameSpaces,
   #whLib.DOMTokenList,
   #whLib.EntityReference,
   #whLib.Notation,
]


domStuff = namedtuple("domStuff",
    [ "impl", "doc", "el", "attr" ])

def setupMinidom():
    mimpl = minidom.getDOMImplementation()
    mdoc = mimpl.createDocument("", "html", None)
    mEl = mdoc.createElement("p")
    mEl.setAttribute("class", "high")
    return domStuff(mimpl, mdoc, mEl, mEl.getAttribute)

def setupBasedom():
    bimpl = basedom.getDOMImplementation()
    bdoc = bimpl.createDocument("", "html", None)
    bEl = bdoc.createElement("p")
    bEl.setAttribute("class", "high")
    return domStuff(bimpl, bdoc, bEl, bEl.getAttribute)


##############################################################################
#
def getAncestors(cl):
    ancs = []
    cur = cl
    while (bases := cur.__bases__):
        if (len(bases) > 1):
            print("Warning: %s multiple inherits from %s" % (cur, bases))
        ancs += bases[-1]
    return ancs

def showChains():
    for cl in theClasses:
        print("%-24s << %s" % (cl, getAncestors(cl)))


##############################################################################
#
nope = "----"
fail = "FAIL"

probs = defaultdict(int)

def compareDir(inst1, inst2) -> int:
    """Take two instances of the same / similar class, and
    compare their inventories. This pretty much assumes the args are
    instances of two very similar classes, such as two implementations
    of the same API, or a class and subclass.
    But they don't actually have to be.
    """
    fulldir1 = dir(inst1)
    fulldir2 = dir(inst2)

    clName1 = inst1.__class__.__name__
    clName2 = inst2.__class__.__name__

    dir1 = sorted([ x for x in fulldir1
        if not x.startswith("_") and not x.endswith("_NODE") ])
    dir2 = sorted([ x for x in fulldir2
        if not x.startswith("_") and not x.endswith("_NODE") ])
    set1 = set(dir1)
    set2 = set(dir2)
    dirUnion = sorted(list(set1.union(set2)))

    #print(f"\n\n{dir1}\n\n{dir2}\n\n{dirUnion}")

    fmt = "  %-30s %16s %16s %s"
    print("\n" + fmt
        % ("="*24, "minidom "+clName1, "basedom "+clName2, ""))

    nReported = 0
    for x in dirUnion:
        msg1 = getStatus(inst1, x)
        msg2 = getStatus(inst2, x)

        supMsg1 = in_superclass(inst1, x)
        supMsg2 = in_superclass(inst2, x)

        rel = getRelation(msg1, msg2, x)

        # Skip lines per options.
        #
        if legit(supMsg1) and legit(supMsg2):
            if args.omitInherited: continue
        if rel == "PYLIST":
            if args.omitPylist: continue
        if rel == "EXTENSION":
            if args.omitExtensions: continue
        elif rel == "NOWHERE":
            print("Uh, what?")
        elif rel == "MISSING":
            pass  # Always report
        elif rel == "BOTH":
            if args.omitBothHave: continue
            if (msg1 == msg2):
                if args.omitMatches: continue

        nReported += 1
        probs[x] += 1
        print(fmt % (x, msg1, msg2, rel))
    print("Total items: cl1 %d, cl2 %d, union %d, reported %d"
        % (len(dir1), len(dir2), len(dirUnion), nReported))
    return nReported

def getStatus(ob, x):
    try:
        if x in dir(ob):
            tname = type(getattr(ob, x)).__name__
            if tname == "builtin_function_or_method": return "builtin"
            return tname
    except Exception:
        return fail
    return nope

def in_superclass(cls, x):
    try:
        if x in set(dir(cls.__base__)) & set(dir(cls)):
            return type(getattr(cls.__base__, x)).__name__
    except AttributeError:
        return fail
    return nope

def legit(s):
    return (s not in [ fail, nope ])

def getRelation(st1, st2, x):
    if not legit(st1):
        if not legit(st2):
            return "NOWHERE"
        else:
            if x in dir([1,2,3]): return "PYLIST"
            return "EXTENSION"
    else:
        if not legit(st2):
            return "MISSING"
        else:
            return "BOTH"


##############################################################################
#
def compareMinidomVsBaseDom(m, b):
    """Run an object comparison for each DOM class, and report diffs.
    """
    compareDir(m.el,                   b.el)
    compareDir(m.el.getAttributeNode("class"),
               b.el.getAttributeNode("class"))
    compareDir(m.doc.createTextNode("lorem ipsum"),
               b.doc.createTextNode("lorem ipsum"))
    compareDir(m.doc.createCDATASection("foo&bar"),
               b.doc.createCDATASection("foo&bar"))
    compareDir(m.doc.createProcessingInstruction("tgt1", "data1"),
               b.doc.createProcessingInstruction("tgt1", "data1"))
    compareDir(m.doc.createComment("nothing to see here"),
               b.doc.createComment("nothing to see here"))

    compareDir(m.doc,                  b.doc)

    compareDir(minidom.NodeList(),
               basedom.NodeList())

    attrs = { "class":"hige", "alt":"foo" }
    compareDir(minidom.NamedNodeMap(attrs, "", m.el),
               basedom.NamedNodeMap(attrs, "", b.el))
    compareDir(minidom.Node(),
               basedom.Node())

    #compareDir(minidom.Notation("png", "-//foo", "/tmp/viewer"),
    #           basedom.Notation("png", "-//foo", "/tmp/viewer"))
    #compareDir(minidom.EntityReference("foo"),
    #           basedom.EntityReference("foo"))

    print("\nTotals:")
    for k, v in probs.items():
        print("    %-30s %6d" % (k, v))


##############################################################################
#
def compareDomNodeClasses(m, b):
    """Run an object comparison for each DOM class, and report diffs.
    """


##############################################################################
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
            "--omitBothHave", action="store_true",
            help="Don't display items both versions (see also --omitMatches).")
        parser.add_argument(
            "--omitExtensions", action="store_true",
            help="Don't display basedom extensions.")
        parser.add_argument(
            "--omitInherited", action="store_true",
            help="Don't display items in both superclasses.")
        parser.add_argument(
            "--omitMatches", action="store_true",
            help="Don't display items where both have same type.")
        parser.add_argument(
            "--omitPylist", action="store_true",
            help="Don't display items from Python List.")
        parser.add_argument(
            "--quiet", "-q", action="store_true",
            help="Suppress most messages.")
        parser.add_argument(
            "--verbose", "-v", action="count", default=0,
            help="Add more messages (repeatable).")
        parser.add_argument(
            "--version", action="version", version="0.9",
            help="Display version information, then exit.")

        args0 = parser.parse_args()
        return(args0)


    ###########################################################################
    #
    args = processOptions()

    mStuff = setupMinidom()
    bStuff = setupBasedom()

    showChains()

    #compareMinidomVsBaseDom(mStuff, bStuff)

