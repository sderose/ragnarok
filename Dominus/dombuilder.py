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
from typing import Dict, Any, Union,  IO, Protocol
import logging

from xml.parsers import expat

from basedomtypes import NMTOKEN_t, NCName_t, QName_t
from domenums import RWord

lg = logging.getLogger("dombuilder")
#logging.basicConfig(level=logging.INFO)

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
to a DOM implementation to create a Document.
It responds to parser events, and constructs the corresponding DOM as it goes.


=Related Commands=

Uses `xml.parsers.expat`, but not quite the usual SAX interface.
'''Note''': See [https://docs.python.org/3/library/pyexpat.html],
[https://svn.apache.org/repos/asf/apr/apr-util/vendor/expat/1.95.7/doc/reference.html],
and L<https://libexpat.github.io> for details about this parser.


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


###############################################################################
#
class XMLParser(Protocol):
    def Parse(self, data: str) -> None: ...
    def ParseFile(self, file: IO) -> None: ...


###############################################################################
#
class DomBuilder():
    """Build a DOM structure by parsing something.
    """
    XMLEntities = {
        "&quot;"  : '"',
        "&apos;" : "'",
        "&lt;"   : "<",
        "&gt;"   : ">",
        "&amp;"  : "&",
    }

    def __init__(self, domImpl:type,
        wsn:bool=False, verbose:int=1, nsSep:str=":"):
        """Set up to parse an XML file(s) and have SAX callbacks create a DOM.

        @param domImpl: a DOM implementation to use.
        @param wsn: Discard whitespace-only text nodes.
        @param verbose: Trace some stuff.
        """
        assert isinstance(domImpl, type)

        self.IdIndex = {}       # Keep index of ID attributes
        self.nodeStack = []     # Open Element objects
        self.wsn = wsn          # Include whitespace-only nodes?
        self.verbose = verbose
        self.nsSep = nsSep

        # The first start tag event will construct a Document().
        self.domImpl = domImpl
        self.domDoc = None
        self.domDocType = None
        self.theParser = None

        self.encoding = 'utf-8'
        self.version = "1.1"
        self.standalone = None

    def parse(self, path_or_fh:Union[IO, str]) -> 'Document':
        """Actually run the parser.

        @param path_or_fh: Path or file handle to XML file to parse.
        Iff it is a path, it is both opened and closed here.
        @return A DOM object representing the document.
        """
        import _io
        if isinstance(path_or_fh, str):
            if not os.path.isfile(path_or_fh):
                raise IOError("'%s' is not a regular file." % (path_or_fh))
            fh = codecs.open(path_or_fh, "rb")
        elif isinstance(path_or_fh, (_io.TextIOWrapper, _io.BufferedWriter)):
            fh = path_or_fh
        else:
            raise ValueError(
                "Not a path or file handle, but %s." % (type(path_or_fh)))

        self.parser_setup()
        self.theParser.ParseFile(fh)
        if not isinstance(path_or_fh, str): fh.close()
        return self.domDoc

    def parse_string(self, s:str) -> 'Document':
        if not isinstance(s, str):
            raise ValueError("Not a string.")
        self.theParser = self.parser_setup()
        self.theParser.Parse(s)
        return self.domDoc

    def dom_setup(self, namespaceURI:str=None, qualifiedName:QName_t=None,
        docType:'DocumentType'=None):
        self.domDoc = self.domImpl.createDocument(
            namespaceURI=namespaceURI, qualifiedName=qualifiedName,
            docType=docType)
        self.domDoc.encoding = self.encoding
        self.domDoc.version = self.version
        self.domDoc.standalone = self.standalone

    def parser_setup(self, encoding:str="utf-8", dcls:bool=True) -> XMLParser:
        """Construct a parser instance and hook up SAX events handlers.
        """
        self.theParser = expat.ParserCreate(
            encoding=encoding, namespace_separator=self.nsSep)
        p = self.theParser

        # Init and Final

        p.StartElementHandler           = self.StartElementHandler
        p.EndElementHandler             = self.EndElementHandler
        p.CharacterDataHandler          = self.CharacterDataHandler
        p.ProcessingInstructionHandler  = self.ProcessingInstructionHandler
        p.CommentHandler                = self.CommentHandler

        if dcls:
            p.XmlDeclHandler            = self.XmlDeclHandler
            p.StartDoctypeDeclHandler   = self.StartDoctypeDeclHandler
            p.EndDoctypeDeclHandler     = self.EndDoctypeDeclHandler

            p.ElementDeclHandler        = self.ElementDeclHandler
            p.AttlistDeclHandler        = self.AttlistDeclHandler
            p.EntityDeclHandler         = self.EntityDeclHandler
            p.UnparsedEntityDeclHandler = self.UnparsedEntityDeclHandler
            p.NotationDeclHandler       = self.NotationDeclHandler

        return p

    def tostring(self) -> str:
        #lg.info("DomBuilder, domDoc is a %s." , type(self.domDoc))
        return self.domDoc.collectAllXml2()

    def isCurrent(self, name:NMTOKEN_t) -> bool:
        """Is the innermost open element of the given type?
        """
        if self.nodeStack and self.nodeStack[-1] == name:
            return True
        return False

    def isOpen(self, name:NMTOKEN_t) -> bool:
        """Is any element of the given type open?
        """
        if name in self.nodeStack: return True
        return False

    def ind(self) -> bool:
        """Return the indentation string for the current depth.
        """
        return("    " * len(self.nodeStack))


    ### Handlers ##############################################################
    #
    def StartElementHandler(self, name:NMTOKEN_t, attributes:Dict=None) -> None:
        if self.domDoc is None:
            lg.info("Creating Document via {self.domImpl.__name__}.")
            self.dom_setup(
                namespaceURI=None, qualifiedName=name, docType=None)
        else:
            lg.info("Appending %s to a %s (depth %d, nChildren %d).",
                name, self.nodeStack[-1].nodeName,
                len(self.nodeStack), len(self.nodeStack[-1].childNodes))

        lg.info("StartElement: '%s'", name)
        el = self.domDoc.createElement(name)
        #el.startLoc = self.theParser.CurrentByteIndex
        if attributes:
            nsp = RWord.NS_PREFIX+":"
            for n, v in attributes.items():
                if n.startswith(nsp):
                    if el.declaredNS is None: el.declaredNS = {}
                    lName = n[len(nsp):]
                    el.declaredNS[lName] = v
                    continue
                el.setAttribute(n, v)
                # TODO factor out indexing
                if "*@"+n in self.IdIndex or el.nodeName+"@"+n in self.IdIndex:
                    #if self.theParser.theMLD.caseInsensitive: v = v.lower()
                    if v in self.IdIndex:
                        raise ValueError("Duplicate ID value '%s' @ %s." %
                            (v, self.theParser.CurrentByteIndex))
                    else:
                        self.IdIndex[v] = el

        if self.nodeStack: self.nodeStack[-1].appendChild(el)
        else: self.domDoc.appendChild(el)
        self.nodeStack.append(el)
        return

    def AttrHandler(self, aname:NMTOKEN_t, avalue:str) -> None:
        """Support option of parser returning attributes as separate events.
        """
        curElement = self.nodeStack[-1]
        if curElement.hasAttribute(aname):
            raise SyntaxError(f"Duplicate attribute '{aname}'.")
        curElement.setAttribute(aname, avalue)

    def EndElementHandler(self, name:NMTOKEN_t) -> None:
        lg.info("EndElement: '%s'", name)
        if not self.nodeStack:
            raise IndexError(
                f"EndElementHandler: closing '{name}' but empty nodeStack.")

        if self.nodeStack[-1].nodeName != name:
            raise ValueError(
                "EndElementHandler: closing '%s' but open element is: %s" %
                (name, self.nodeStack[-1].nodeName))

        self.nodeStack.pop()
        return

    def EmptyElementHandler(self, name:NMTOKEN_t, attributes) -> None:
        assert(False)
        lg.info("EmptyElement: got '%s'", name)
        self.StartElementHandler(name, attributes)
        self.EndElementHandler(name)
        return

    def CharacterDataHandler(self, data:str) -> None:
        lg.info("CharacterData: got '%s'", data.strip())
        if not re.match(r"\S", data):  # whitespace-only
            if not self.wsn: return
        else:
            if not self.nodeStack:
                raise("Found data outside any element: '%s'." % (data))
        tn = self.domDoc.createTextNode(data)
        self.nodeStack[-1].appendChild(tn)
        return

    def CommentHandler(self, data:str) -> None:
        lg.info("Comment: got '%s'", data)
        newCom = self.domDoc.createComment(data)
        self.nodeStack[-1].appendChild(newCom)
        return

    def DeclHandler(self, data:str) -> None:
        lg.info("Decl: ignoring '%s'", data)
        #newDcl = self.domDoc.create(data)
        #self.nodeStack[-1].appendChild(newDcl)
        return

    def ProcessingInstructionHandler(self, target:NCName_t, data:str) -> None:
        lg.info("ProcessingInstruction: got '%s'", data)
        newPI = self.domDoc.createProcessingInstruction(target, data)
        self.nodeStack[-1].appendChild(newPI)
        return

    def Unknown_declHandler(self, data:Any) -> None:
        lg.warning("Unknown_decl: got '%s'", data)
        # raise ValueError("Unknown markup declaration: '%s'" % (data))
        newDcl = self.domDoc.createComment(data)
        self.nodeStack[-1].appendChild(newDcl)
        return


    ### Markup declaration handlers
    #
    def XmlDeclHandler(self,
        version:str="", encoding:str="", standalone:str="") -> None:
        if version in [ "1.0", "1.1" ]:
            self.version = version
        else:
            raise ValueError(f"Unexpected xml version '{version}'.")
        if encoding in [ "utf-8", "utf8" ]:
            self.encoding = "utf-8"
        elif encoding:
            raise ValueError(f"Unexpected encoding '{encoding}'.")
        if standalone in [ "yes", "no" ]:
            self.standalone = standalone
        elif standalone in [ -1, None, "" ]:  # expat seems to like -1
            pass
        else:
            raise ValueError(f"Unexpected standalone '{standalone}'.")
        # TODO Store them

    def StartDoctypeDeclHandler(self, name:NMTOKEN_t,
        literal:str=None, publicId:str=None, systemId:str=None) -> None:
        #self.domDocType = DocType(name, literal, publicId, systemId)
        pass

    def EndDoctypeDeclHandler(self) -> None:
        pass

    def ElementDeclHandler(self, name:NMTOKEN_t, model:str="ANY") -> None:
        self.domDocType.ElementDef(name, aliasFor=None, model=model)

    def AttlistDeclHandler(self, ename:NMTOKEN_t, aname:NMTOKEN_t, atype:str, adefault:str) -> None:
        self.domDocType.AttributeDef(ename, aname, atype, adefault)

    def EntityDeclHandler(self, name:NMTOKEN_t,
        literal:str=None, publicId:str=None, systemId:str=None) -> None:
        self.domDocType.EntityDef(name, literal, publicId, systemId)

    def UnparsedEntityDeclHandler(self, name:NMTOKEN_t,
        literal:str=None, publicId:str=None, systemId:str=None) -> None:
        self.domDocType.EntityDef(name, literal, publicId, systemId)

    def NotationDeclHandler(self, name:NMTOKEN_t,
        literal:str=None, publicId:str=None, systemId:str=None) -> None:
        self.domDocType.NotationDef(name, literal, publicId, systemId)
