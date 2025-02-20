#!/usr/bin/env python3
#
# prettyxml: Support nice serialization for basedom.
#
#pylint: disable=W0613, W0212
#
import codecs
import re
import logging
from typing import Dict, Any, Union, Iterable, IO, Match, Mapping
from textwrap import wrap
from html.entities import codepoint2name

from basedomtypes import DOMException, NSuppE, ICharE, NodeType
from xmlstrings import XmlStrings as XStr #, CaseHandler

#from basedom import Node, NamedNodeMap, NodeList

lg = logging.getLogger("prettyxml")

__metadata__ = {
    "title"        : "prettyxml",
    "description"  : "Support nice serialization for basedom",
    "rightsHolder" : "Steven J. DeRose",
    "creator"      : "http://viaf.org/viaf/50334488",
    "type"         : "http://purl.org/dc/dcmitype/Software",
    "language"     : "Python 3.11",
    "created"      : "2016-02-06 (within basedom)",
    "modified"     : "2025-01-18",
    "publisher"    : "http://github.com/sderose",
    "license"      : "https://creativecommons.org/licenses/by-sa/3.0/"
}
__version__ = __metadata__['modified']


###############################################################################
#
class FormatOptions:
    """Options for toprettyxml. Callers can pass like-named
    keywords args, or construct and pass an object.
    Warning: 'depth' gets modified during traversals, so is not thread-safe.

    TODO: Add options for what to do with "?>?" "--". "]]>"

    See XSParser for options applicable to DTD and document syntax.
    """
    def __init__(self, **kwargs):
        self.depth = 0                  # (changes during traversals)

        # Whitespace insertion
        self.newl:str = "\n"            # String for line-breaks
        self.indent:str = "  "          # String to repeat for indent
        self.addindent:str = None       # Make minidom happy
        self.stripTextNodes = False     #
        self.wrapTextAt:int = 0         # Wrap text near this interval
        self.dropWS:bool = False        # Drop whitespace-only text nodes
        self.breakBB:bool = True        # Newline before start tags
        self.breakAB:bool = False       # Newline after start tags
        self.breakAttrs:bool = False    # Newline before each attribute
        self.breakBText:bool = False    #
        self.breakBE:bool = False       # Newline before end tags
        self.breakAE:bool = False       # Newline after end tags

        self.tagInfos = {}              # Dict from nodeName to CSS display type

        # Canonicalization (see Canoncal XML, esp. 1.4.3 and 2.2)
        self.canonical:bool = False     # Use Canonical XML syntax?         TODO
        self.IgnoreComments = False
        self.TrimTextNodes = False      #   same as stripTextNodes?         TODO
        self.PrefixRewrite = False
        self.QNameAware = None

        # Syntax alternatives
        self.encoding:str = "utf-8"     # utf-8. Just utf-8.
        self.includeXmlDcl = True
        self.standalone = None          # 'cuz toprettyxml wants it
        self.includeDoctype = True
        self.useEmpty:bool = True       # Use XML empty-element syntax
        self.emptySpace:bool = True     # Include a space before the /
        self.quoteChar:str = '"'        # Char to quote attributes
        self.sortAttrs:bool = False     # Alphabetical order (cf readOrder)
        self.normAttrs = False          # Normalize whitespace in attributes
        self.useCDATA:bool = True       # Use CDATA when textNode.isCDATA

        # Escaping
        self.escapeGT:bool = False      # Escape > in content
        self.ASCII = False              # Escape all non-ASCII
        self.charBase:int = 16          # Char refs in decimal or hex?
        self.hexUpperCase:bool = True   # &#X00FF; or &#x00ff;?
        self.charPad:int = 4            # Min width for numeric char refs
        self.htmlChars:bool = True      # Use HTML named special characters
        self.forPI = "?&gt;"            # Use in place of ?> in PIs
        self.forCOM = "-&#x2d;"         # Use in place of -- in comments
        self.forMSC = "]]&gt;"          # Use in place of ]]>
        self.translateTable:Mapping = {} # Let caller control escaping (content)

        self._charFormat = self.deriveCharFormat()

        # TODO: Format for float attrs
        # TODO: Pull in options like repBrace, xsdType, emptyEnd, unQuotedAttr...

        for k, v in kwargs.items():
            self.setOption(k, v)

    def deriveCharFormat(self) -> str:
        """Update cached % format string whenever certain options change.
        """
        if self.charBase==10:
            cf = f'&#%0{self.charPad}d;'
        else:
            xFlag = "X" if self.hexUpperCase else "x"
            cf = f'&#{xFlag}%0{self.charPad}{xFlag};'
        #lg.info("Numeric character format set to '{self._charFormat}'.")
        return cf

    def setOption(self, k:str, v:Any) -> None:  # FormatOptions
        if k == "tagInfos":
            self.setTagInfos(v)
        elif k not in self.__dict__:
            raise KeyError(f"FormatOptions: Unknown option '{k}'.")
        elif k in [ "charBase", "charPad", "hexUpperCase" ]:
            assert isinstance(v, int)
            self.__dict__[k] = v
            self._charFormat = self.deriveCharFormat()
        elif self.__dict__[k] is not None and not isinstance(v, type(self.__dict__[k])):
            if isinstance(v, FormatOptions): raise TypeError(
                f"FormatOptions: got an FO instance for option {k}."
                " Perhaps you forgot 'fo=' in the call?")
            raise TypeError(f"FormatOptions: option '{k}' expected type "
                f"{type(self.__dict__[k])}, not {type(v)}.")
        else:
            self.__dict__[k] = v

    def setInlines(self, v:Union[str, Iterable]=None) -> Dict:
        """Shorthand to add the passed names to tagInfos as 'inline'.
        If v is a str, it can be a space-separated list of element types.
        """
        if v is None: return self.tagInfos
        if isinstance(v, str):
            v = v.split()
        for tag in v:
            if not XStr.isXmlNMTOKEN(tag): raise ICharE(
                f"Bad name '{tag}' for setInlines().")
            self.tagInfos[tag] = "inline"
        return self.tagInfos

    def setTagInfos(self, source:Union[Dict, str, IO]) -> int:
        """Add a bunch of tagname:displayType pairs to tagInfos.
        Accepts either a dict, a str path, or an open file handle.
        Returns the numbers of tags in the resulting list.

        The file format has one tagname, value pair per line, and
        lines beginning with (space and) "#" are ignored as comments.
        The values are expected to be as for the CSS "display" property.
        The important ones here are:
            inline: makes the element type exempt from breakXX settings
            pre: Not a "display" value, but prevents re-wrapping.
        """
        if isinstance(source, dict):
            for tag, disp in source.items():
                if not XStr.isXmlNMTOKEN(tag): raise ICharE(
                    f"Bad name '{tag}' for setInlines().")
                self.tagInfos[tag] = disp
            return self.tagInfos
        elif isinstance(source, str):
            ifh = codecs.open(source, "rb", encoding="utf-8")
        else:
            ifh = source

        for i, rec in enumerate(ifh.readlines()):
            rec = rec.strip()
            if rec.startswith("#") or rec == "": continue
            tag, _com, disp = rec.partition(",")
            if not disp: raise SyntaxError(
                f"line {i}: taginfo file record lacks comma: {rec}.")
            tag = tag.strip()
            disp = disp.strip()
            if not XStr.isXmlNMTOKEN(tag): raise ICharE(
                f"Bad name '{tag}' for setInlines().")
            self.tagInfos[tag] = disp

        if isinstance(source, str): ifh.close()
        return self.tagInfos

    @property
    def ws(self) -> str:
        return self.newl + self.indent * self.depth

    # Global FormatOptions objects for default and for canonical XML output.
    # TODO: fix attr order to do namespace dcl before other attrs, by ns URI
    # TODO: Only make one of these....
    @staticmethod
    def getCanonicalFO():
        return FormatOptions(
            canonical = True,
            stripTextNodes = True,
            QNameAware = True,
            PrefixRewrite = True,
            sortAttrs = True, normAttrs = True,
            newl = "\n", quoteChar = '"', htmlChars = False,
            includeDoctype = False, useEmpty = False,
            indent = "", wrapTextAt = 0,
            breakBB = False, breakAB = False, breakAttrs = False,
            breakBE = False, breakAE = False,
            useCDATA = False)

    @staticmethod
    def getDefaultFO(**kwargs):
        fo = FormatOptions(
            sortAttrs = True, normAttrs = True,
            newl = "\n", quoteChar = '"', htmlChars = False,
            includeDoctype = False, useEmpty = False,
            indent = "  ", wrapTextAt = 0,
            breakBB = True, breakAB = False, breakAttrs = False,
            breakBE = False, breakAE = False)
        for k, v in kwargs.items():
            fo.setOption(k, v)
        return fo

    def tostring(self):
        buf = "FormatOptions:\n"
        for k in sorted(list(dir(self))):
            if k.startswith("_"): continue
            v = getattr(self, k)
            if callable(v): continue
            if isinstance(v, str): v = f"'{v}'"
            pv = re.sub(r"[\x00-\x1F]",
                lambda x: "\\x%02x" % ord(x.group()), str(v))

            buf += "    %-16s %s\n" % (k, pv)
        return buf


###############################################################################
#
class FormatXml:
    @staticmethod
    def toprettyxml(node:'Node',
        indent:str='\t', newl:str='\n', encoding:str="utf-8", standalone=None,
        fo:FormatOptions=None) -> str:

        if not fo:
            fo = FormatOptions.getDefaultFO(
                indent=indent, newl=newl, encoding=encoding, standalone=standalone)
            #lg.info(fo.tostring())

        try:
            ntype = node.nodeType
        except AttributeError:
            if node.__class__.__name__ == 'NamedNodeMap':
                return FormatXml._prettyNamedNodeMap(node, fo)
            elif node.__class__.__name__ == 'NodeList':
                return FormatXml._prettyNodeList(node, fo)
            return ""

        if ntype == NodeType.ELEMENT_NODE:
            return FormatXml._prettyElement(node, fo)
        elif ntype == NodeType.ATTRIBUTE_NODE:
            return FormatXml._prettyAttribute(node, fo)
        elif ntype == NodeType.TEXT_NODE:
            return FormatXml._prettyText(node, fo)
        elif ntype == NodeType.PROCESSING_INSTRUCTION_NODE:
            return FormatXml._prettyPI(node, fo)
        elif ntype == NodeType.COMMENT_NODE:
            return FormatXml._prettyComment(node, fo)
        elif ntype == NodeType.CDATA_SECTION_NODE:
            return FormatXml._prettyCdataSection(node, fo)
        elif ntype == NodeType.DOCUMENT_NODE:
            return FormatXml._prettyDocument(node, fo)
        elif ntype == NodeType.DOCUMENT_TYPE_NODE:
            return FormatXml._prettyDocType(node, fo)
        elif ntype == NodeType.ENTITY_REFERENCE_NODE:
            return FormatXml._prettyEntRef(node, fo)
        elif ntype == NodeType.ENTITY_NODE:
            return FormatXml._prettyEntity(node, fo)
        elif ntype == NodeType.DOCUMENT_FRAGMENT_NODE:
            return FormatXml._prettyDocFrag(node, fo)
        elif ntype == NodeType.NOTATION_NODE:
            return FormatXml._prettyNotation(node, fo)
        elif ntype == NodeType.ABSTRACT_NODE:
            return FormatXml._prettyAbstract(node, fo)
        else:
            raise DOMException("Unknown nodeType.")


    @staticmethod
    def _prettyNamedNodeMap(node:'Node', fo:FormatOptions=None) -> str:
        ks = node.keys()
        if node.ownerDocument and node.ownerDocument.options.sortAttrs:
            ks = sorted(ks)
        buf = ""
        for k in ks:
            escVal = FormatXml.escapeAttribute(
                node[k].nodeValue, addQuotes=True, fo=fo)
            buf += f" {k}={escVal}"
        return buf

    @staticmethod
    def _prettyNodeList(node, fo, wrapper:str="nodeList") -> str:
        buf = ""
        if wrapper: buf += "<{wrapper}>" + (fo.newl if fo.breakAB else "")
        if len(node) > 0:
            for node in node:
                buf += node.toprettyxml(fo=fo)
        if wrapper: buf += (fo.newl if fo.breakBE else "") + "</{wrapper}>"
        return buf


    @staticmethod
    def _prettyElement(node:'Node', fo:FormatOptions=None) -> str:
        buf = ""
        ws = "" if node.nodeName in fo.tagInfos else fo.ws
        if fo.breakBB: buf += ws
        stag = node._startTag(fo=fo)  # TODO Specify ns behavior
        if len(node.childNodes) == 0:
            if not fo.useEmpty: buf += stag + node.endTag
            elif fo.emptySpace: buf += f"{stag[0:-1]} />"
            else: buf += f"{stag[0:-1]}/>"
        else:
            buf += stag
            if fo.breakAB: buf += ws
            fo.depth += 1
            for ch in node.childNodes:
                buf += ch.toprettyxml(fo=fo) or ""
            fo.depth -= 1
            if fo.breakBE: buf += ws
            buf += node.endTag
        if fo.breakAE: buf += ws
        return buf

    @staticmethod
    def _prettyAttribute(node:'Node', fo:FormatOptions=None) -> str:
        escVal = FormatXml.escapeAttribute(
            node.nodeValue, addQuotes=True, fo=fo)
        return f"{node.nodeName}={escVal}"

    @staticmethod
    def _prettyText(node:'Node', fo:FormatOptions=None) -> str:
        """TODO indent? Remove newlines before wrap? Preformatted elements?
        """
        if fo.dropWS and node.data.strip() == "": return ""
        ws = fo.ws if fo.breakBText else ""
        if fo.translateTable:
            txt = node.data.translate(fo.translateTable)
        else:
            txt = node.data
        if fo.stripTextNodes: txt = txt.strip()
        if fo.wrapTextAt > 0:
            txt = "\n".join(wrap(txt, width=fo.wrapTextAt,
                break_long_words=False, break_on_hyphens=False))
        if node.inCDATA and fo.useCDATA:
            buf = f"<![CDATA[{FormatXml.escapeCDATA(txt)}]]>"
        else:
            buf = FormatXml.escapeText(txt, fo)
        return ws + buf

    @staticmethod
    def _prettyPI(node:'Node', fo:FormatOptions=None) -> str:
        return f"<?{FormatXml.escapePI(node.target)} {FormatXml.escapePI(node.data)}?>"

    @staticmethod
    def _prettyComment(node:'Node', fo:FormatOptions=None) -> str:
        return fo.ws + f"<!--{FormatXml.escapeComment(node.data) or ''}-->"

    @staticmethod
    def _prettyCdataSection(node:'Node', fo:FormatOptions=None):
        return f"<![CDATA[{FormatXml.escapeCDATA(node.data)}]]>"

    @staticmethod
    def _prettyDocument(node:'Node', fo:FormatOptions) -> str:
        buf = ""
        if fo.includeXmlDcl: buf += node.xmlDcl
        if fo.includeDoctype: buf += fo.newl + node.doctypeDcl
        if node.documentElement:
            #import pudb; pudb.set_trace()
            buf += node.documentElement.toprettyxml(fo=fo)
        return buf + fo.newl

    @staticmethod
    def _prettyDocType(node:'Node', fo:FormatOptions=None) -> str:
        raise NSuppE("No toprettyxml on DocType.")  # TODO

    @staticmethod
    def _prettyEntRef(node:'Node', fo:FormatOptions=None) -> str:
        return f"&{node.nodeName};"

    @staticmethod
    def _prettyEntity(node:'Node', fo:FormatOptions=None) -> str:
        raise NSuppE("No toprettyxml on Entity.")

    @staticmethod
    def _prettyDocFrag(node:'Node', fo:FormatOptions=None) -> str:
        raise NSuppE("No toprettyxml on DocFrag.")

    @staticmethod
    def _prettyNotation(node:'Node', fo:FormatOptions=None) -> str:
        raise NSuppE("No toprettyxml on Notation.")

    @staticmethod
    def _prettyAbstract(node:'Node', fo:FormatOptions=None) -> str:
        raise NSuppE("No toprettyxml on abstract node.")


    ###########################################################################
    # Escapers (TODO Move into prettyxml)
    #
    @staticmethod
    def escapeAttribute(s:str, addQuotes:bool=True,
        fo:FormatOptions=None) -> str:
        """Turn characters special in (double-quoted) attributes, into char refs.
        If 'addQuotes' is set, also add the quotes.
        """
        if not fo: fo = fo = FormatOptions.getDefaultFO()
        s = XStr.dropNonXmlChars(s)
        s = s.replace('&', "&amp;")
        s = s.replace('<', "&lt;")
        # TODO Impl fo.escapeGT
        if fo.quoteChar == '"':
            s = s.replace('"', "&quot;")
        else:
            tgtChar = FormatXml.escapeOneChar(fo.quoteChar, fo=fo)
            s = s.replace(fo.quoteChar, tgtChar)
        if fo.ASCII: s = FormatXml.escapeASCII(s, fo=fo)
        if addQuotes: return fo.quoteChar + s + fo.quoteChar
        return s
    escapeXmlAttribute = escapeAttribute

    @staticmethod
    def escapeText(s:str, fo:FormatOptions=None) -> str:
        """Turn things special in text content, into char refs.
        This always uses the predefined XML named special character references.
        """
        if not fo: fo = fo = FormatOptions.getDefaultFO()
        s = XStr.dropNonXmlChars(s)
        s = s.replace('&',   "&amp;")
        s = s.replace('<',   "&lt;")
        s = s.replace(']]>', fo.forMSC)
        if fo.escapeGT: s = s.replace('>', "&gt;")
        if fo.ASCII: s = FormatXml.escapeASCII(s, fo=fo)
        return s
    escapeXmlText = escapeText

    @staticmethod
    def escapeCDATA(s:str, fo:FormatOptions=None) -> str:
        """XML Defines no particular escaping for this, we use char-ref syntax,
        although that's not recognized within CDATA.
        """
        if not fo: fo = fo = FormatOptions.getDefaultFO()
        s = XStr.dropNonXmlChars(s)
        s = s.replace(']]>', fo.forMSC)
        if fo.ASCII: s = FormatXml.escapeASCII(s, fo=fo)
        return s

    @staticmethod
    def escapeComment(s:str, fo:FormatOptions=None) -> str:
        """XML Defines no particular escaping for this, we use char-ref syntax,
        although that's not recognized within CDATA.
        """
        if not fo: fo = fo = FormatOptions.getDefaultFO()
        s = XStr.dropNonXmlChars(s)
        s = s.replace('--', fo.forCOM)
        if fo.ASCII: s = FormatXml.escapeASCII(s, fo=fo)
        return s

    @staticmethod
    def escapePI(s:str,fo:FormatOptions=None) -> str:
        """XML Defines no particular escaping for this..
        """
        if not fo: fo = fo = FormatOptions.getDefaultFO()
        s = XStr.dropNonXmlChars(s)
        s = s.replace('?>', fo.forPI)
        if fo.ASCII: s = FormatXml.escapeASCII(s, fo=fo)
        return s

    @staticmethod
    def escapeASCII(s:str,
        width:int=4, base:int=16, htmlNames:bool=True, fo:FormatOptions=None) -> str:
        """Delete truly prohibited chars, turn all non-ASCII characters
        into character references, including the usual escapeText().
        Also escaped: U+7E since it's weird (DEL)
        """
        if not fo: fo = FormatOptions.getDefaultFO()

        def escASCIIFunction(mat:Match) -> str:
            nonlocal fo
            return FormatXml.escapeOneChar(mat.group(1), fo=fo)

        s = XStr.dropNonXmlChars(s)
        s = re.sub(r'([^\x00-\x7E])', escASCIIFunction, s)
        #s = FormatXml.escapeText(s)
        return s

    @staticmethod
    def escapeOneChar(c:str, fo:FormatOptions=None) -> str:
        if fo.htmlChars and ord(c) in codepoint2name:
            return f"&{codepoint2name[ord(c)]};"
        return fo._charFormat % (ord(c))

    @staticmethod
    def makeStartTag(gi:str, attrs:Union[str, Dict]="",
        empty:bool=False, sort:bool=False) -> str:
        tag = "<" + gi
        if attrs:
            if isinstance(attrs, str):
                tag += " " + attrs.strip()
            else:
                tag += FormatXml.dictToAttrs(attrs, sort=sort)
        tag += "/>" if empty else ">"
        return tag

    @staticmethod
    def dictToAttrs(dct:Dict, sort:bool=False, normValues:bool=False) -> str:
        """Turn a dict into a serialized attribute list (possibly sorted
        and/or space-normalized). Escape as needed.
        """
        sep = " "
        anames = dct.keys()
        if sort: anames = sorted(list(anames))
        attrString = ""
        for a in (anames):
            v = dct[a]
            #if normValues: v = XmlStrings.normalizeSpace(v)
            attrString += f"{sep}{a}={FormatXml.escapeAttribute(v)}"
        return attrString

    @staticmethod
    def makeEndTag(name:str) -> str:
        return f"</{name}>"
