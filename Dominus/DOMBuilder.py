#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
#pylint: disable=W0613, W0603, W0212
#
import sys
import os
import re
import codecs
import xml.dom.minidom
from xml.parsers import expat

import DomExtensions

__metadata__ = {
    "title"        : "DOMBuilder",
    "rightsHolder" : "Steven J. DeRose",
    "creator"      : "http://viaf.org/viaf/50334488",
    "type"         : "http://purl.org/dc/dcmitype/Software",
    "language"     : "Python 3.7",
    "created"      : "2016-02-06",
    "modified"     : "2020-01-11",
    "publisher"    : "http://github.com/sderose",
    "license"      : "https://creativecommons.org/licenses/by-sa/3.0/"
}
__version__ = __metadata__["modified"]

descr = """
=Usage=

This is a version of the "glue" that connects an HTML, XML, or other parser
to a DOM implementation. It responds to parser events, and constructs the
corresponding DOM as it goes.

It can be hooked up to `xml.dom.minidom`, which is great for testing but not
all that useful in general, because the equivalent is built in. But it can also
talk to things like `Dominµs.py`, and `BaseDOM.py`, which have quite different
features than most other DOM implementations.


=Related Commands=

Uses `xml.parsers.expat`. This does not use quite the usual SAX interface.
'''Note''': See [https://docs.python.org/3/library/pyexpat.html],
[https://svn.apache.org/repos/asf/apr/apr-util/vendor/expat/1.95.7/doc/reference.html],
and L<https://libexpat.github.io> for details about this parser.

My `DomExtensions` is a set of API additions that can be monkey-patched
straight onto a DOM implementation, providing a wide variety of convenience
functions, as well as allowing the children and/or attributes or any Element
to be accessed using the normal Python list accessors, as described in

My `Dominµs.py` is a DOM implementation that can handle documents larger
than memory, by using a reasonably fast persistent representation of the DOM,
similar to the general approach once used by `DynaText`. However, `Dominµs.py`
differs in being dynamically updatable.


=Known bugs and limitations=

So far, it only talks to `expat` for parsing, and `xml.dom.minidom`. Next addition is to hook it to Dominus.


=History=

By Steven J. DeRose, ~Feb 2016.

2018-04-18: lint.

2019-12-20: Split out of BaseDOM.py (nee RealDOM.py).
Hook to expat, minidom, DomExtensions. Add test driver.


=To do=

* Finish
* Hook up to other parsers
* Integrate with Dominµs
* Add option to utilize DomExtensions where it might save time.


=Ownership=

This work by Steven J. DeRose is licensed under a Creative Commons
Attribution-Share Alike 3.0 Unported License. For further information on
this license, see L<http://creativecommons.org/licenses/by-sa/3.0/>.

For the most recent version, see [http://www.derose.net/steve/utilities]
or [http://github.com/sderose].


=Options=
"""

# So we can get at file offsets, errors, etc. from expat:
theParser = None
theDomB = None
args = None


###############################################################################
#
class DOMBuilder():
    """Build a DOM structure by parsing something.
    Can hook to various DOM implementations.
    """
    XMLEntities = {
        "&quo;"  : '"',
        "&apos;" : "'",
        "&lt;"   : "<",
        "&gt;"   : ">",
        "&amp;"  : "&",
    }

    def __init__(self, domImpl=None, nodeClass=None, wsn=False,
        verbose=1, useDomExtensions=False, nsSep=None
        ):
        """Set up to parse an XML file(s) and have the callbacks create a DOM.

        @param domImpl: a class.
        @param wsn: Discard whitespace-only text nodes.
        @param verbose: Trace some stuff.
        """
        super(DOMBuilder, self).__init__()
        global theDomB
        theDomB = self                  # So callbacks can see us

        # The first start tag event will trigger createDocument().
        if (domImpl):
            self.domImpl = domImpl
            self.nodeClass = nodeClass
        else:
            self.domImpl = xml.dom.getDOMImplementation()
            self.nodeClass = xml.dom.Node

        if (useDomExtensions):
            DomExtensions.DomExtensions.patchDom(self.nodeClass)

        self.IdIndex = {}               # Keep index of ID attributes
        self.nodeStack = []             # Open Element objects
        self.wsn = wsn                  # Include whitespace-only nodes?
        self.verbose = verbose
        self.nsSep = nsSep
        self.domDoc = None


    def parse(self, path_or_fh):
        """Actually run the parser.

        @param path_or_fh: Path or file handle to XML file to parse.
        Iff it is a path, it is both opened and closed here.
        @return A DOM object representing the document.
        """
        import _io
        if (isinstance(path_or_fh, str)):
            if (not os.path.isfile(path_or_fh)):
                raise IOError("'%s' is not a regular file." % (path_or_fh))
            fh = codecs.open(path_or_fh, "rb")
        elif (isinstance(path_or_fh,
            (_io.TextIOWrapper, _io.BufferedWriter))):
            fh = path_or_fh
        else:
            raise ValueError(
                "Not a path or file handle, but %s." % (type(path_or_fh)))

        p = self.parser_setup()
        p.ParseFile(fh)
        if (not isinstance(path_or_fh, str)): fh.close()
        return self.domDoc

    def parse_string(self, s):
        if (not isinstance(s, str)):
            raise ValueError("Not a string.")
        p = self.parser_setup()
        p.Parse(s)
        return self.domDoc

    def parser_setup(self):

        p = expat.ParserCreate(
            encoding=args.iencoding, namespace_separator=self.nsSep)

        global theParser # For getting at location and error info
        theParser = p

        p.StartElementHandler          = StartElementHandler
        p.EndElementHandler            = EndElementHandler
        p.CharacterDataHandler         = CharacterDataHandler
        p.ProcessingInstructionHandler = ProcessingInstructionHandler
        p.CommentHandler               = CommentHandler

        #p.XmlDeclHandler               = XmlDeclHandler
        #p.StartDoctypeDeclHandler      = StartDoctypeDeclHandler
        #p.EndDoctypeDeclHandler        = EndDoctypeDeclHandler

        #p.ElementDeclHandler           = ElementDeclHandler
        #p.AttlistDeclHandler           = AttlistDeclHandler
        #p.EntityDeclHandler            = EntityDeclHandler
        #p.UnparsedEntityDeclHandler    = UnparsedEntityDeclHandler
        #p.NotationDeclHandler          = NotationDeclHandler

        return p

    def tostring(self):
        #self.trace(1, "DOMBuilder, domDoc is a %s." % (type(self.domDoc)))
        return self.domDoc.collectAllXml2()

    def isCurrent(self, name):
        """Is the innermost open element of the given type?
        """
        if (self.nodeStack and self.nodeStack[-1] == name):
            return True
        return False

    def isOpen(self, name):
        """Is any element of the given type open?
        """
        if (name in self.nodeStack): return True
        return False

    def trace(self, lvl, msg):
        if (self.verbose >= lvl): sys.stderr.write(self.ind()+msg+"\n")

    def ind(self):
        return("    " * len(self.nodeStack))


### Handlers ##############################################################
#
def StartElementHandler(name, attributes=None):
    theDomB.trace(1, "StartElement: '%s'" % (name))
    if (len(theDomB.nodeStack) == 0):
        theDomB.trace(1, "Creating Document().")
        e = makeDocument(name)
    else:
        theDomB.trace(1, "Appending %s to a %s (depth %d, nChildren %d)." % (
            name, theDomB.nodeStack[-1].nodeName,
            len(theDomB.nodeStack), theDomB.nodeStack[-1].getNChildNodes()))
        e = theDomB.domDoc.createElement(name)
        theDomB.nodeStack[-1].appendChild(e)

    e.startLoc = theParser.CurrentByteIndex
    if (attributes): addAttrs(e, attributes)
    theDomB.nodeStack.append(e)
    return

def makeDocument(name):
    assert (theDomB is not None)
    print("domImpl type is %s" % (type(theDomB.domImpl)))
    theDomB.domDoc = theDomB.domImpl.createDocument(None, name, None)
    return theDomB.domDoc.documentElement

def addAttrs(node, attributes):
    for n, v in attributes.items():
        node.setAttribute(n, v)
        if ("*@"+n in theDomB.IdIndex
            or node.nodeName+"@"+n in theDomB.IdIndex):
            #if (theDomB.theMLD.caseInsensitive): v = v.lower()
            if (v in theDomB.IdIndex):
                raise ValueError("Duplicate ID value '%s' @ %s." %
                    (v, theParser.CurrentByteIndex))
            else:
                theDomB.IdIndex[v] = node
    return node

def EndElementHandler(name):
    if (not theDomB.nodeStack):
        raise IndexError(
            "EndElementHandler: closing '%s' but empty nodeStack." % (name))

    if (theDomB.nodeStack[-1].nodeName != name):
        raise ValueError(
            "EndElementHandler: closing '%s' but open element is: %s" %
            (name, theDomB.nodeStack[-1].nodeName))

    theDomB.nodeStack.pop()
    theDomB.trace(1, "EndElement: '%s'" % (name))
    return

def EmptyElementHandler(name, attributes):
    assert(False)
    theDomB.trace(1, "EmptyElement: got '%s'" % (name))
    StartElementHandler(name, attributes)
    EndElementHandler(name)
    return

def CharacterDataHandler(data):     # FIX: Coalesce adjacent text nodes?
    if (not re.match(r"\S", data)):  # whitespace-only
        if (not theDomB.wsn): return
    else:
        if (not theDomB.nodeStack):
            raise("Found data outside any element: '%s'." % (data))
    theDomB.trace(1, "CharacterData: got '%s'" % (data))
    tn = theDomB.domDoc.createTextNode(data)
    theDomB.nodeStack[-1].appendChild(tn)
    return

def CommentHandler(data):
    theDomB.trace(1, "Comment: got '%s'" % (data))
    newCom = theDomB.domDoc.createComment(data)
    theDomB.nodeStack[-1].appendChild(newCom)
    return

def DeclHandler(data):
    theDomB.trace(1, "Decl: ignoring '%s'" % (data))
    #newDcl = theDomB.domDoc.create(data)
    #theDomB.nodeStack[-1].appendChild(newDcl)
    return

def ProcessingInstructionHandler(target, data):
    theDomB.trace(1, "ProcessingInstruction: got '%s'" % (data))
    newPI = theDomB.domDoc.createProcessingInstruction(target, data)
    theDomB.nodeStack[-1].appendChild(newPI)
    return

def Unknown_declHandler(data):
    theDomB.trace(1, "Unknown_decl: got '%s'" % (data))
    # raise ValueError("Unknown markup declaration: '%s'" % (data))
    newDcl = theDomB.domDoc.createComment(data)
    theDomB.nodeStack[-1].appendChild(newDcl)
    return


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
            "--baseDom", action="store_true",
            help="Try building using BaseDOM instead of xml.dom.minidom.")
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

        DomExtensions.addArgsForCollectorOptions(parser)
        args0 = parser.parse_args()
        return args0

    if (os.environ["PYTHONIOENCODING"] != "utf_8"):
        theDomB.trace(0, "Warning: PYTHONIOENCODING is not utf_8.\n")

    args = processOptions()

    if (len(args.files) == 0):
        tfileName = "testDoc.xml"
        print("No files specified, trying %s." % (tfileName))
        args.files.append(tfileName)

    for thePath in args.files:
        if (not os.path.isfile(thePath)):
            theDomB.trace(0, "No file at '%s'." % (thePath))
            continue
        print("Building the DOM for '%s'." % (thePath))

        if (args.baseDom):
            import BaseDOM
            whichDomImpl = BaseDOM.DOMImplementation
            whichNode = BaseDOM.Node
        else:
            whichDomImpl = xml.dom.minidom
            whichNode = xml.dom.Node

        theDBuilder = DOMBuilder(domImpl=whichDomImpl,
            nodeClass=whichNode, verbose=args.verbose,
            nsSep = ":" if (args.ns) else None
        )
        theDom = theDBuilder.parse(thePath)
        print("\nResults:")
        print(theDom.tostring())
