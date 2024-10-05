#!/usr/bin/env python3
#
# makeDefChart.py
# 2024-10-05: Written by Steven J. DeRose.
#
import sys
import codecs
from collections import defaultdict
from typing import Dict
import re
import logging

from xml.dom import minidom
import basedom

lg = logging.getLogger("makeDefChart.py")

__metadata__ = {
    "title"        : "makeDefChart.py",
    "description"  : "Make a chart of what defs each class does.",
    "rightsHolder" : "Steven J. DeRose",
    "creator"      : "http://viaf.org/viaf/50334488",
    "type"         : "http://purl.org/dc/dcmitype/Software",
    "language"     : "Python 3.9",
    "created"      : "2024-10-05",
    "modified"     : "2024-10-05",
    "publisher"    : "http://github.com/sderose",
    "license"      : "https://creativecommons.org/licenses/by-sa/3.0/"
}
__version__ = __metadata__["modified"]

descr = """
=Name=

makeDefChart.py

Go through one or my Python files, and collect property and method definitions
by class. Make a chart.

You can request a more detailed report for DOM modules
using --showMinidom or --showBasedom. This will include methods and properties,
and the methods are categorized as:

    ABS   -- method is not defined on cl or any superclass
    INH   -- method is just inherited from a superclass
    NEW   -- method is defined on cl, but no superclass
    OVR   -- method is overridden vs. a superclass

Hidden methods are not a "thing" in Python, and are not called out, they'll
just show up as "OVR" (pylint, however, can notice ones that just call
NotImplementedError

=Description=

==Usage==

    makeDefChart.py [options] [files]


=See also=

compareClassDirs.py.


=Known bugs and Limitations=

Doesn't deal with class lines where superclass list includes newline(s).


=To do=

Also check inheritance on properties.


=History=

* 2024-10-05: Written by Steven J. DeRose.


=Rights=

Copyright 2024-10-05 by Steven J. DeRose. This work is licensed under a
Creative Commons Attribution-Share-alike 3.0 unported license.
See [http://creativecommons.org/licenses/by-sa/3.0/] for more information.

For the most recent version, see [http://www.derose.net/steve/utilities]
or [https://github.com/sderose].


=Options=
"""


###############################################################################
#
def doOneFile(fh, byClass:Dict) -> int:
    """Read a source file looking for class and def lines.
    """
    curClass = "(top-level)"
    curDef = ""
    curSupers = ""
    if curClass not in byClass: byClass[curClass] = {}

    recnum = 0
    continuingDef = ""
    for rec in fh.readlines():
        recnum += 1
        if continuingDef:
            rec = continuingDef + " " + rec
            continuingDef = ""
        rec = rec.strip()

        if rec.startswith("class "):
            mat = re.match(r"class (\w+)(\(.*?\))?", rec)
            if not mat:
                lg.warning(f"%d: Unparsed line: {rec}")
            else:
                curClass = mat.group(1)
                curSupers = mat.group(2)
                curDef = ""
                if curClass in byClass:
                    lg.warning("Duplicate def for class '{curClass}'.")
                byClass[curClass] = {}
            lg.info(rec)

        #lg.info("***line: %s", rec)
        if rec.startswith("def "):
            opens = len(re.sub(r"[^(]", "", rec))
            closes = len(re.sub(r"[^)]", "", rec))
            if opens > closes:
                lg.info("unclosed def: %s", rec)
                continuingDef = rec
                continue
            mat = re.search(r"\bdef (\w+)", rec)
            curDef = mat.group(1)
            byClass[curClass][curDef] = rec
            lg.info(rec)

        if rec.startswith("raise NotSupportedError"):
            byClass[curClass][curDef] += " [[[NOTSUPPORTED]]]"
            lg.error(byClass[curClass][curDef] + " on " + curClass)
    return byClass


###############################################################################
#
def showModule(md, depth:int=0):
    if md is object: return
    try:
        b = str(md.__bases__)
    except AttributeError:
        b = ""

    print("\n%s####### Items locally defined in %s %s"
        % ("  "*depth, md.__name__, b))

    typeCounts = defaultdict(int)
    for x in sorted(md.__dict__.keys()):
        if x in [ "__builtins__", "__doc__" ]: continue
        thing = getattr(md, x)  #md.__dict__[x]
        typ = type(thing)
        val = ""
        if typ in [ str, int, float, bool, complex ]:
            val = f"({str(thing)})"
        elif (callable(thing) and typ not in [ type ]):
            val = f"({getMethodStatus(md, x)})"
        print("  %-36s %s %s" % (x, typ.__name__, val))
        typeCounts[typ.__name__] += 1

    print(typeCounts)

    for x in sorted(md.__dict__.keys()):
        if x in [ "str", "Any", "NmToken", "object", "List", "Dict",
            "OrderedDict", "defaultdict",
            ]: continue
        if x.endswith("Error"): continue
        thing = md.__dict__[x]
        if not isinstance(thing, type): continue
        showModule(thing, depth+1)

def mapModule(md):
    classes = {}
    for x in dir(md):
        if not isinstance(x, type): continue
        classes[x] = {}
        cl = getattr(md, x)
        for y in dir(cl):
            try:
                yobj = getattr(cl, y)
                classes[x][y] = type(yobj).__name__
            except AttributeError:
                classes[x][y] = "???"


###############################################################################
#
def getClassByName(impl:type, clName:str):
    try:
        return getattr(impl, clName)
    except AttributeError:
        return None

def getMethodStatus(cl:type, mName:str) -> bool:
    """Return implementation status as:
        ABS   -- method is not defined on cl or any superclass
        INH   -- method is just inherited from a superclass
        NEW   -- method is defined on cl, but no superclass
        OVR   -- method is overridden vs. a superclass
        (HID   -- method is __hidden__) -- Not easily supported.

    Examples for each:
        Node.appendChild
    """
    if not availableAtAll(cl, mName):
        return "ABS"
    if not local_def(cl, mName):
        return "INH"
    if not in_any_superclass(cl, mName):
        return "NEW"
    meth = getattr(cl, mName)
    return "OVR"

def availableAtAll(cl:type, mName:str) -> bool:
    """Inherited methods DO show up in a subclass and instance dir.
    They do NOT show up in the subclass's __dict__.
    dir(None) gives you build-in dunders, apparently.

    Instance variables (or anything create by __init__()? do NOT show up
    on the class, only on an actual instance.
    """
    return mName in dir(cl)

def in_any_superclass(cls:type, mName:str) -> bool:
    """Can pass cls as a class or Instance.
    E.g., Element or Element("P")
    Only instances will have instance variables.
    BUT, instances will show their superclass not having those, since you'd
    have to instantiate to see them!
    """
    try:
        s = cls.__bases__
    except AttributeError:
        s = type(cls).__bases__
    if (len(s) < 1):
        lg.warning(f"No base class for {cls}:\n    {s}")
        return False
    elif (len(s) > 1):
        lg.info(f"Non-unitary base class for {cls}:\n    {s}")
        s = [ s[-1] ]
    return mName in dir(s[0])

def local_def(cl:type, mName:str) -> bool:
    return mName in cl.__dict__

def testStatusInspectors():
    d = basedom
    for checkCl in [ d.Node, d.Element, d.Attr, d.Comment ]:
        try:
            nam = checkCl.__name__
        except AttributeError:
            nam = type(checkCl)
        print(f"\nFor {nam}:")
        for m in [ "appendChild", "getAttribute", "innerXML" ]:
            print(f"  Method {m}:")
            print("    availableAtAll:    ", availableAtAll(checkCl, m))
            print("    in_any_superclass: ", in_any_superclass(checkCl, m))
            print("    local_def:         ", local_def(checkCl, m))
            print("    getMethodStatus:   ", getMethodStatus(checkCl, m))


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
            "--quiet", "-q", action="store_true",
            help="Suppress most messages.")
        parser.add_argument(
            "--showBasedom", action="store_true",
            help="Show what's in basedom.")
        parser.add_argument(
            "--showMinidom", action="store_true",
            help="Show what's in minidom.")
        parser.add_argument(
            "--testMethodStatus", action="store_true",
            help="See if the code to determine inheritance works.")
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

    if (args.testMethodStatus):
        testStatusInspectors()
        sys.exit()

    if (args.showBasedom):
        showModule(basedom)
        sys.exit()

    if (args.showMinidom):
        showModule(minidom)
        sys.exit()

    theInfo = {}

    if (len(args.files) == 0):
        lg.warning("makeDefChart.py: No files specified....")
        doOneFile(sys.stdin, theInfo)
    else:
        for path0 in args.files:
            lg.info("******* Starting file '%s'.\n", path0)
            ifh = codecs.open(path0, "rb", encoding="utf-8")
            doOneFile(ifh, theInfo)

        if (not args.quiet):
            lg.info("makeDefChart.py: Done, %d files.\n", len(args.files))

    byMethod = {}
    for cl0, mdict in theInfo.items():
        for m in mdict.keys():
            if m not in byMethod: byMethod[m] = {}
            byMethod[m][cl0] = mdict[m]

    print("""<html>
<head>
    <title>Which classes define which methods</title>
    <style type="text/css">
        table     { border-collapse: collapse; }
        tr, th    { border:thin black solid; }
        td        { border:thin black solid; text-align:center; font:Courier; }
        td.Element { background-color:lightgreen; }
        td.Attr { background-color:red; }
        td.CharacterData, td.EntityReference, td.PlainNode { background-color:yellow; }
    </style>
</head>
<body>
<table>
""")

    clAbbrs = {
        "DOMImplementation":    "DOMImpl",
        "NodeList":             "NodeList",
        "PlainNode":            "PlainN",
        "Node":                 "Node",
        "Document":             "Doc",
        "Element":              "Elem",
        "CharacterData":        "CharData",
        "Text":                 "Text",
        "CDATASection":         "CDATA",
        "ProcessingInstruction": "PI",
        "Comment":              "Comm",
        "EntityReference":      "EntRef",
        "Notation":             "Notn",
        "Attr":                 "Attr",
        "NamedNodeMap":         "NNMap",
        "NameSpaces":           "NmSp",
    }

    classOrder = [
        "DOMImplementation",
        "NodeList",             # list
        "PlainNode",            # list
        "Node",                 # PlainNode
        "Document",             # Node
        "Element",              # Node
        "Attr",                 # Node
        "CharacterData",        # Node
        "Text",                 # CharacterData
        "CDATASection",         # CharacterData
        "ProcessingInstruction", # CharacterData
        "Comment",              # CharacterData
        "EntityReference",      # CharacterData
        #"Notation",
        #"NamedNodeMap",
        #"NameSpaces",
    ]

    buf = "<th><i>Method</i></th>"
    for cl0 in classOrder:
        displayName = clAbbrs[cl0] if cl0 in clAbbrs else cl0
        buf += f"<th>{displayName}</th>"
    print(f"<thead>\n<tr>{buf}<th>n defs</th></tr>\n</thead>")

    print("<tbody>")
    defsInClass = defaultdict(int)
    for m in sorted(list(byMethod.keys())):
        clist = byMethod[m]
        buf = ""
        nClasses = 0
        for cl0 in classOrder:
            if cl0 in clist:
                if re.search(r"NOTSUPPORTED", clist[cl0]):
                    flag = "HID"
                else:
                    inBasedom = True
                    defsInClass[cl0] += 1
                    nClasses += 1
                    flag = "+"
            else:
                inBasedom = False
                flag = "-"

            classObj = getClassByName(minidom, cl0)
            if (0 and classObj is not None):
                inMinidom = getMethodStatus(classObj, m)
                if inMinidom is not None and inMinidom != inBasedom:
                    flag += " X" if inBasedom else " O"
            buf += f"""<td class="{cl0}">{flag}</td>"""
        if nClasses > 0:
            print(f"<tr><th>{m}</th>{buf}<td><i>{nClasses}</i></td></tr>")
    print("</tbody>")

    buf = ""
    for cl0 in classOrder:
        buf += f"<td>{defsInClass[cl0]}</td>"
    print(f"<tfoot><tr><th><i>{len(byMethod)} methods</th>{buf}</tr></tfoot>")
    print("</table>/</body>\n</html>")
