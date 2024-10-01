#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# dombuilder:
# 2016-02-06: Written by Steven J. DeRose (based on my stuff back to the 80's).
#
#pylint: disable=W0613, W0603, W0212
#
import os
import re
import codecs
from typing import IO, Union, Dict
import logging

from xml.parsers import expat

#from basedom import Document, Element
#from xml.dom import minidom  # TODO Lose this
#from xml.dom.minidom import Node
#from documenttype import DocType

lg = logging.getLogger("dombuilder")

__metadata__ = {
    "title"        : "dombuilder",
    "rightsHolder" : "Steven J. DeRose",
    "creator"      : "http://viaf.org/viaf/50334488",
    "type"         : "http://purl.org/dc/dcmitype/Software",
    "language"     : "Python 3.7",
    "created"      : "2016-02-06",
    "modified"     : "2024-09",
    "publisher"    : "http://github.com/sderose",
    "license"      : "https://creativecommons.org/licenses/by-sa/3.0/"
}
__version__ = __metadata__["modified"]

descr = """
=Usage=

This is a version of the "glue" that connects an HTML, XML, or other parser
to a DOM implementation. It responds to parser events, and constructs the
corresponding DOM as it goes.

It can be hooked up to most any DOM implementation,
such as `Dominµs.py` and `basedom.py`, which have quite different
features than most other DOM implementations.


=Related Commands=

Uses `xml.parsers.expat`, but not quite the usual SAX interface.
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

So far, it only talks to `expat` for parsing.


=History=

* By Steven J. DeRose, ~Feb 2016.

* 2018-04-18: lint.

* 2019-12-20: Split out of basedom.py (nee RealDOM.py).
Hook to expat. Add test driver.

* 2024-08ff: Integrate with basedom.


=To do=

* Finish
* Hook up to other parsers


=Ownership=

This work by Steven J. DeRose is licensed under a Creative Commons
Attribution-Share Alike 3.0 Unported License. For further information on
this license, see L<http://creativecommons.org/licenses/by-sa/3.0/>.

For the most recent version, see [http://www.derose.net/steve/utilities]
or [http://github.com/sderose].


=Options=
"""

# So we can get at file offsets, errors, etc. from expat:
theDomB = None


###############################################################################
#
class DomBuilder():
    """Build a DOM structure by parsing something.
    Can hook to various DOM implementations.
    """
    XMLEntities = {
        "&quot;"  : '"',
        "&apos;" : "'",
        "&lt;"   : "<",
        "&gt;"   : ">",
        "&amp;"  : "&",
    }

    def __init__(self, domImpl=None, wsn:bool=False, verbose:int=1, nsSep:str=":"):
        """Set up to parse an XML file(s) and have the callbacks create a DOM.

        @param domImpl: a DOM implementation to use.
        @param wsn: Discard whitespace-only text nodes.
        @param verbose: Trace some stuff.
        """
        self.IdIndex = {}               # Keep index of ID attributes
        self.nodeStack = []             # Open Element objects
        self.wsn = wsn                  # Include whitespace-only nodes?
        self.verbose = verbose
        self.nsSep = nsSep

        # The first start tag event will trigger createDocument().
        self.domImpl = domImpl
        self.domDoc = None
        self.domDocType = None
        self.theParser = None


    def parse(self, path_or_fh:Union[IO, str]) -> 'Document':
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

        self.parser_setup()
        self.theParser.ParseFile(fh)
        if (not isinstance(path_or_fh, str)): fh.close()
        return self.domDoc

    def parse_string(self, s) -> 'Document':
        if (not isinstance(s, str)):
            raise ValueError("Not a string.")
        p = self.parser_setup()
        p.Parse(s)
        return self.domDoc

    def parser_setup(self, encoding:str="utf-8", dcls:bool=True) -> None:
        p = expat.ParserCreate(
            encoding=encoding, namespace_separator=self.nsSep)
        self.theParser = p

        p.StartElementHandler           = StartElementHandler
        p.EndElementHandler             = EndElementHandler
        p.CharacterDataHandler          = CharacterDataHandler
        p.ProcessingInstructionHandler  = ProcessingInstructionHandler
        p.CommentHandler                = CommentHandler

        if (dcls):
            p.XmlDeclHandler           = XmlDeclHandler
            p.StartDoctypeDeclHandler  = StartDoctypeDeclHandler
            p.EndDoctypeDeclHandler    = EndDoctypeDeclHandler

            p.ElementDeclHandler       = ElementDeclHandler
            p.AttlistDeclHandler       = AttlistDeclHandler
            p.EntityDeclHandler        = EntityDeclHandler
            p.UnparsedEntityDeclHandler= UnparsedEntityDeclHandler
            p.NotationDeclHandler      = NotationDeclHandler

        return p

    def tostring(self) -> str:
        #lg.info("DomBuilder, domDoc is a %s." , type(self.domDoc))
        return self.domDoc.collectAllXml2()

    def isCurrent(self, name) -> bool:
        """Is the innermost open element of the given type?
        """
        if (self.nodeStack and self.nodeStack[-1] == name):
            return True
        return False

    def isOpen(self, name) -> bool:
        """Is any element of the given type open?
        """
        if (name in self.nodeStack): return True
        return False

    def ind(self) -> bool:
        return("    " * len(self.nodeStack))


### Handlers ##############################################################
#
def StartElementHandler(p:DomBuilder, name, attributes=None):
    def addAttrs(node, attributes:Dict) -> 'Node':
        for n, v in attributes.items():
            node.setAttribute(n, v)
            if ("*@"+n in theDomB.IdIndex
                or node.nodeName+"@"+n in theDomB.IdIndex):
                #if (theDomB.theMLD.caseInsensitive): v = v.lower()
                if (v in theDomB.IdIndex):
                    raise ValueError("Duplicate ID value '%s' @ %s." %
                        (v, p.theParser.CurrentByteIndex))
                else:
                    theDomB.IdIndex[v] = node
        return node

    lg.info("StartElement: '%s'", name)
    if (len(theDomB.nodeStack) == 0):
        lg.info("Creating Document().")
        assert (theDomB is not None)
        theDomB.domDoc = theDomB.domImpl.createDocument(None, name, None)
        el = theDomB.domDoc.documentElement
    else:
        lg.info("Appending %s to a %s (depth %d, nChildren %d).",
            name, theDomB.nodeStack[-1].nodeName,
            len(theDomB.nodeStack), theDomB.nodeStack[-1].getNChildNodes())
        el = theDomB.domDoc.createElement(name)
        theDomB.nodeStack[-1].appendChild(el)

    el.startLoc = p.theParser.CurrentByteIndex
    if (attributes): addAttrs(el, attributes)
    theDomB.nodeStack.append(el)
    return

def EndElementHandler(p:DomBuilder, name) -> None:
    if (not theDomB.nodeStack):
        raise IndexError(
            "EndElementHandler: closing '%s' but empty nodeStack." % (name))

    if (theDomB.nodeStack[-1].nodeName != name):
        raise ValueError(
            "EndElementHandler: closing '%s' but open element is: %s" %
            (name, theDomB.nodeStack[-1].nodeName))

    theDomB.nodeStack.pop()
    lg.info("EndElement: '%s'", name)
    return

def EmptyElementHandler(p:DomBuilder, name, attributes) -> None:
    assert(False)
    lg.info("EmptyElement: got '%s'", name)
    StartElementHandler(p, name, attributes)
    EndElementHandler(p, name)
    return

def CharacterDataHandler(p:DomBuilder, data) -> None:  # FIX: Coalesce adjacent text nodes?
    if (not re.match(r"\S", data)):  # whitespace-only
        if (not theDomB.wsn): return
    else:
        if (not theDomB.nodeStack):
            raise("Found data outside any element: '%s'." % (data))
    lg.info("CharacterData: got '%s'", data)
    tn = theDomB.domDoc.createTextNode(data)
    theDomB.nodeStack[-1].appendChild(tn)
    return

def CommentHandler(p:DomBuilder, data) -> None:
    lg.info("Comment: got '%s'", data)
    newCom = theDomB.domDoc.createComment(data)
    theDomB.nodeStack[-1].appendChild(newCom)
    return

def DeclHandler(p:DomBuilder, data) -> None:  # TODO Handle Declarations
    lg.info("Decl: ignoring '%s'", data)
    #newDcl = theDomB.domDoc.create(data)
    #theDomB.nodeStack[-1].appendChild(newDcl)
    return

def ProcessingInstructionHandler(p:DomBuilder, target, data) -> None:
    lg.info("ProcessingInstruction: got '%s'", data)
    newPI = theDomB.domDoc.createProcessingInstruction(target, data)
    theDomB.nodeStack[-1].appendChild(newPI)
    return

def Unknown_declHandler(p:DomBuilder, data) -> None:
    lg.info("Unknown_decl: got '%s'", data)
    # raise ValueError("Unknown markup declaration: '%s'" % (data))
    newDcl = theDomB.domDoc.createComment(data)
    theDomB.nodeStack[-1].appendChild(newDcl)
    return


### Markup declaration handlers
#
def XmlDeclHandler(p:DomBuilder,
    version:str="", encoding:str="", standalone:str="") -> None:
    pass

def StartDoctypeDeclHandler(p:DomBuilder, name:str,
    literal=None, publicId:str=None, systemId:str=None) -> None:
    #p.domDocType = DocType(name, literal, publicId, systemId)
    # TODO Figure out circular import
    pass

def EndDoctypeDeclHandler(p:DomBuilder) -> None:
    pass

def ElementDeclHandler(p:DomBuilder, name:str, model:str="ANY") -> None:
    p.domDocType.ElementDef(name, aliasFor=None, model=model)

def AttlistDeclHandler(p:DomBuilder, ename:str, aname:str, atype:str, adefault:str) -> None:
    p.domDocType.AttributeDef(ename, aname, atype, adefault)

# TODO Special types etc.

def EntityDeclHandler(p:DomBuilder, name:str,
    literal=None, publicId:str=None, systemId:str=None) -> None:
    p.domDocType.EntityDef(name, literal, publicId, systemId)

def UnparsedEntityDeclHandler(p:DomBuilder, name:str,
    literal=None, publicId:str=None, systemId:str=None) -> None:
    p.domDocType.EntityDef(name, literal, publicId, systemId)

def NotationDeclHandler(p:DomBuilder, name:str,
    literal=None, publicId:str=None, systemId:str=None) -> None:
    p.domDocType.NotationDef(name, literal, publicId, systemId)
