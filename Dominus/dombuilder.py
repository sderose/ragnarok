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
from typing import Union, IO
import logging
#from xml.parsers import expat
#from xml.dom import minidom

from basedomtypes import NMTOKEN_t, NCName_t, XMLParser_P, NodeType, DOMException
from domenums import RWord
from runeheim import XmlStrings as Rune
#import xsparser

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
=Description=

This is the "glue" that connects an HTML, XML, or other parser
to an implementation of docment structures. The parsers and structure
implementations are swappable, and many pre-existing calling sequences can
be used with little or no change.


==Usage==

First, to just get things up and running:

You might have your XML in a literal or variable:
    xmlText = "<p>Hello</p>"

or in a file:
    xmlPath = "myFile.xml"

===ElementTree style===

    from dombuilder import DomBuilder
    ...
    theDocument = DomBuilder(xmlText)
        OR
    theDocument = DomBuilder.fromstring(xmlText)
        OR
    with open(xmlPath, "rb", encoding="utf-8") as ifh:
        theDocument = DomBuilder(ifh)

You can also specify a different parser, for example like:
    theDocument = DomBuilder(xmlText, parser=someOtherParser)


===Traditional DOM style===

    from dombuilder import DomBuilder
    theDocument = DomBuilder.parsestring(xmlText)
        OR
    theDocument = DomBuilder.parse(xmlPath)
        OR
    with open("myFile.xml", "rb", encoding="utf-8") as ifh:
        impl.parse(ifh)

Or you can be even more explicit:

    from dombuilder import DomBuilder
    from basedom import getDOMImplementation
    ...
    impl = basedom.getDOMImplementation()
    impl.parse_string(xmlText)
        OR
    impl.parse("myFile.xml")
        OR
    with open("myFile.xml", "rb", encoding="utf-8") as ifh:
        impl.parse(ifh)


===DIY style===

    from xml.parsers import expat
    from basedom import getDOMImplementation
    from dombuilder import DomBuilder
    theDocument = DomBuilder(parser=expat, domImpl=minidom)
    theDom = theDocument.ParseFile(xmlPath)

Or you can override the built-in expat event handlers to do other stuff.


==The rest==

The library includes its own XML parser, which can (at option) read DTDs.
It also has a variety of extensions that can be turned on via the API or
via flags inserted in the XML declaration (that's desirable because an XML
parser that doesn't know about them will stop rather than doing the wrong
thing).

That parser can do regular DTDs (internal and external) and documents.
The extensions include allowing all built-in XSD datatypes as attributes
types -- and if you declare them, they'll show up as the right Python types
in the DOM, with default values, etc. It also adds {m,n} to the usual
[*+?] operators in content models.

I expect also to add support for
loading XSDs (the parsing, of course, is easy), and making both look largely
the same inside.

The parser also includes a (still experimental) validator. Or you can create
part or all of a schema via API (for example, just declaring a bunch of ATTLISTs
to get defaulting and typed values, or (with one call) turning on HTML named
special characters.

There are also a few simple shorthand markup syntax options, most
obviously </> and unquoted (or curly-quoted) attributes.

Finally, there is round-trippable JSON export, that handles all XML Node types
and structures.


=Related Commands=

Uses `xml.parsers.expat` or my `xsparser`, which is largely API-compatible.
'''Note''': See [https://docs.python.org/3/library/pyexpat.html],
[https://svn.apache.org/repos/asf/apr/apr-util/vendor/expat/1.95.7/doc/reference.html],
and L<https://libexpat.github.io> for details about this parser.


=Known bugs and limitations=


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

def showInvisibles(s:str) -> str:
    return re.sub(r"[\x00-\x20]", lambda m: chr(ord(m.group()) + 0x2400), s)


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

    def __init__(
        self,
        parserClass:type,   # Typically expat or xsparser
        domImpl:type,       # Typically from x.getDOMImplementation()
        wsn:bool=False,
        verbose:int=1,
        ):
        """Set up an XML parser and a DOM implementation, and provide
        methods to parse XML and return DOM documents.

        @param parserClass:
            Can specify something with a ParserCreate(), or the result of that.
        @param domImpl: a DOM implementation instance to use.
        @param wsn: Discard whitespace-only text nodes.
        @param verbose: Trace some stuff.

        # TODO Switch to take getDOMImplementation instead of module?
        """
        if not parserClass:
            from xml.parsers import expat
            parserClass = expat
        if hasattr(parserClass, "ParserCreate"):
            self.parser = parserClass.ParserCreate(
                encoding="utf-8", namespace_separator=None)
        elif hasattr(parserClass, "Parse") or hasattr(parserClass, "ParseFile"):
            self.parser = parserClass
        else:
            raise AttributeError(
                f"parserClass passed ({parserClass}) has no ParserCreate() or Parse().")

        if not domImpl:
            from xml.dom import minidom
            domImpl = minidom.getDOMImplementation()
        self.parserClass = parserClass

        self.domImpl = domImpl
        if not hasattr(domImpl, "createDocument"):
            raise AttributeError(
                "domImpl passed ({domImpl}) has no createDocument().")

        self.wsn = wsn          # Include whitespace-only nodes?
        self.verbose = verbose
        self.nodeStack = []     # Open Nodes, incl. Document
        self.IdIndex = {}       # Keep index to validate ID attributes  # TODO Drop?
        self.inCDATA = False    # To get parser CDATA state onto text nodes.

        self.domDoc = None
        self.domDocumentType = None

    def parse(self, path_or_fh:Union[IO, str]) -> 'Document':
        """Run the parser on a FILE.

        @param path_or_fh: Path or file handle to XML file to parse.
        Iff it is a path, it is both opened and closed here.
        @return A DOM object representing the document.
        """
        lg.warning("Start basedom dombuilder.parse")
        import _io
        if isinstance(path_or_fh, str):
            if not os.path.isfile(path_or_fh):
                raise IOError("'%s' is not a regular file." % (path_or_fh))
            fh = codecs.open(path_or_fh, "rb")  # No encoding for expat
        elif isinstance(path_or_fh, (_io.TextIOWrapper, _io.BufferedWriter)):
            fh = path_or_fh
        else:
            raise ValueError(
                "Not a path or file handle, but %s." % (type(path_or_fh)))

        self.parser_setup(encoding="utf-8", dcls=True)
        self.domDoc = self.domImpl.createDocument(None, None, None)
        self.nodeStack = [ ]
        self.parser.ParseFile(fh)
        if isinstance(path_or_fh, str): fh.close()
        return self.domDoc

    ParseFile = parse

    def parse_string(self, s:str) -> 'Document':
        assert isinstance(s, str)
        self.parser_setup(encoding="utf-8", dcls=True)
        self.domDoc = self.domImpl.createDocument(None, None, None)
        assert self.domDoc is not None
        #print(f"\nFor Document from {self.domImpl.__module__}:\n{dir(self.domDoc)}")
        self.nodeStack = [ ]
        self.parser.Parse(s)
        return self.domDoc

    Parse = parse_string

    def parser_setup(self, encoding:str="utf-8", dcls:bool=True) -> XMLParser_P:
        """Construct a parser instance and hook up SAX event handlers.
        """
        p = self.parser

        # Element Handlers
        p.StartElementHandler = self.StartElementHandler
        p.EndElementHandler = self.EndElementHandler

        # Leaf node Handlers
        p.CharacterDataHandler = self.CharacterDataHandler
        p.ProcessingInstructionHandler = self.ProcessingInstructionHandler
        p.CommentHandler = self.CommentHandler

        p.StartCdataSectionHandler = self.StartCdataSectionHandler
        p.EndCdataSectionHandler = self.EndCdataSectionHandler
        #p.StartNamespaceDeclHandler = self.StartNamespaceDeclHandler
        #p.EndNamespaceDeclHandler = self.EndNamespaceDeclHandler

        p.StartDoctypeDeclHandler = self.StartDoctypeDeclHandler
        p.EndDoctypeDeclHandler = self.EndDoctypeDeclHandler
        #p.StartNamespaceDeclHandler = None  #self.StartNSDeclHandler  # TODO
        #p.EndNamespaceDeclHandler = None  #self.EndNSDeclHandler  # TODO

        # Special Cases
        p.DefaultHandler = None  # self.DefaultHandler
        p.DefaultHandlerExpand = None  #self.DefaultHandlerExpand

        p.NotStandaloneHandler = None  #self.NotStandaloneHandler
        p.SkippedEntityHandler = None  #self.SkippedEntityHandler

        # DTD Handlers
        if (dcls):
            #p.ExternalEntityRefHandler = self.EntityDeclHandler
            p.EntityDeclHandler = self.EntityDeclHandler
            p.UnparsedEntityDeclHandler = self.UnparsedEntityDeclHandler
            p.NotationDeclHandler = self.NotationDeclHandler
            p.ElementDeclHandler = self.ElementDeclHandler
            p.AttlistDeclHandler = self.AttlistDeclHandler

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
    def StartElementHandler(self, name:NMTOKEN_t, *args) -> None:
        """Create a new element and append to the currently-open element.
        Attributes can be done 3 ways:
            * Pass a dict
            * Pass varargs with alternating names and values
            * Don't pass here at all, but generate a separate event for
              each attribute, immediatey following this event (see AttrHandler).
        The DOM Document itself, but no documentElement, must already be there.
        """
        lg.info("StartElement for '%s' (depth %d).", name, len(self.nodeStack))
        #el.startLoc = self.parser.CurrentByteIndex

        if not Rune.isXmlQName(name): raise SyntaxError(
            f"Parser returned non-QName element name '{name}'.")
        el = self.domDoc.createElement(name)

        if len(args) > 0:  # Deal with attributes
            if isinstance(args[0], dict):
                assert len(args) == 1
                attrDict = args[0]
            else:
                assert len(args) % 2 == 0
                attrDict = {}
                for i in range(0, len(args), 2):
                    attrDict[args[i]] = args[i+1]

            nsp = RWord.NS_PREFIX+":"
            for n, v in attrDict.items():
                if n.startswith(nsp):
                    if el.declaredNS is None: el.declaredNS = {}
                    lName = n[len(nsp):]
                    el.declaredNS[lName] = v
                    continue
                assert Rune.isXmlName(n)
                el.setAttribute(n, v)

        if self.domDoc.documentElement is None:
            if self.nodeStack: raise DOMException(
                "No document element, but stack has [%s]." % (self.nodeStack))
            self.domDoc.appendChild(el)
        else:
            if not self.nodeStack: raise DOMException(
                f"Document element is '{self.domDoc.documentElement}', but no stack.")
            self.nodeStack[-1].appendChild(el)
        self.nodeStack.append(el)

        return

    def AttrHandler(self, aname:NMTOKEN_t, avalue:str) -> None:
        """Support option of parser returning attributes as separate events.
        SAX parsers generally bundle them in with start-tags, which means fewer
        events but an unbounded number of args per event. Take your pick.
        """
        curElement = self.nodeStack[-1]
        if curElement.hasAttribute(aname):
            raise SyntaxError(f"Duplicate attribute '{aname}'.")
        curElement.setAttribute(aname, avalue)

    def EndElementHandler(self, name:NMTOKEN_t) -> None:
        lg.info("EndElement '%s'.", name)
        if not self.nodeStack: raise IndexError(
            f"Endtag for element '{name}' but no elements open.")
        if self.nodeStack[-1].nodeName != name:  # TODO use nodeNameMatches
            # TODO Report where the current element started
            raise ValueError(
                "Endtag for element '%s' but open element is '%s'" %
                (name, self.nodeStack[-1].nodeName))

        self.nodeStack.pop()
        return

    def CharacterDataHandler(self, data:str) -> None:
        """Not to be confused with the minidom class which is a superclass
        of several nodeTypes.
        expat seems to hand back newlines, char-refs, etc separately,
        so we coalesce.
        """
        lg.info("CharacterData '%s'", showInvisibles(data))
        if not re.match(r"\S", data):  # whitespace-only
            if not self.wsn: return
        else:
            if not self.nodeStack: raise SyntaxError(
                f"CharacterData found outside any element: '{data}'.")
        curNode = self.nodeStack[-1]
        if (len(curNode.childNodes) > 0
            and curNode.childNodes[-1].nodeType == NodeType.TEXT_NODE):
            curNode.childNodes[-1].data += data
        else:
            tn = self.domDoc.createTextNode(data)
            if self.inCDATA: tn.inCDATA = True
            curNode.appendChild(tn)
        return

    # CDATA status is recorded on text nodes, rather than making actual DOM
    # CDATA nodes (no one expects the CDatish imposition!).
    def StartCdataSectionHandler(self, *args) -> None:
        self.inCDATA = True
    def EndCdataSectionHandler(self, *args) -> None:
        self.inCDATA = False

    def CommentHandler(self, data:str) -> None:
        lg.info("Comment '%s'", data)
        newCom = self.domDoc.createComment(data)
        if not self.nodeStack: raise SyntaxError(
            "Comment found with no root element open.")
        self.nodeStack[-1].appendChild(newCom)
        return

    def ProcessingInstructionHandler(self, target:NCName_t, data:str) -> None:
        lg.info("ProcessingInstruction: got '%s'", data)
        newPI = self.domDoc.createProcessingInstruction(target, data)
        if not self.nodeStack: raise SyntaxError(
            "PI found with no root element open.")
        self.nodeStack[-1].appendChild(newPI)
        return

    ### Markup declaration handlers
    #
    def XmlDeclHandler(self,
        version:str="", encoding:str="", standalone:str="") -> None:
        if version in [ "1.0", "1.1" ]:
            self.domDoc.version = version
        else:
            raise ValueError(f"Unexpected xml version '{version}'.")
        if encoding in [ "utf-8", "utf8" ]:
            self.domDoc.encoding = "utf-8"
        elif encoding:
            raise ValueError(f"Unexpected encoding '{encoding}'.")
        if standalone in [ "yes", "no" ]:
            self.domDoc.standalone = standalone
        elif standalone in [ -1, None, "" ]:  # expat seems to like -1
            pass
        else:
            raise ValueError(f"Unexpected standalone '{standalone}'.")
        self.domDoc.version = version
        self.domDoc.encoding = encoding
        self.domDoc.standalone = standalone

    def StartDoctypeDeclHandler(self, name:NMTOKEN_t,
        literal:str=None, publicId:str=None, systemId:str=None) -> None:
        #self.domDocumentType = DocType(name, literal, publicId, systemId)
        pass

    def EndDoctypeDeclHandler(self) -> None:
        pass

    def ElementDeclHandler(self, name:NMTOKEN_t, model:str="ANY") -> None:
        self.domDocumentType.ElementDef(name, aliasFor=None, model=model)

    def AttlistDeclHandler(self, ename:NMTOKEN_t,
        aname:NMTOKEN_t, atype:str, adefault:str) -> None:
        self.domDocumentType.AttributeDef(ename, aname, atype, adefault)

    def EntityDeclHandler(self, name:NMTOKEN_t,
        literal:str=None, publicId:str=None, systemId:str=None) -> None:
        self.domDocumentType.EntityDef(name, literal, publicId, systemId)

    def UnparsedEntityDeclHandler(self, name:NMTOKEN_t,
        literal:str=None, publicId:str=None, systemId:str=None) -> None:
        self.domDocumentType.EntityDef(name, literal, publicId, systemId)

    def SDATAEntityDeclHandler(self, name:NMTOKEN_t, literal:str=None) -> None:
        self.domDocumentType.EntityDef(name, literal)

    def NotationDeclHandler(self, name:NMTOKEN_t,
        literal:str=None, publicId:str=None, systemId:str=None) -> None:
        self.domDocumentType.NotationDef(name, literal, publicId, systemId)
