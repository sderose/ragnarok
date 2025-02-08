#!/usr/bin/env python3
#
# JsonX: Roundtrippable XML/JSON conversions.
#
#import sys
import codecs
import re
from typing import Any, List, IO, Union
from types import SimpleNamespace
import json
import logging

from xmlstrings import XmlStrings as XStr
#from dombuilder import DomBuilder
#from domenums import RWord #, NodeType

# DOMImplementation

lg = logging.getLogger("jsonx")
logging.basicConfig(level=logging.INFO, format='%(message)s')

descr = """
==Description==

Load some JsonX to make a DOM, or save a DOM to JsonX.
JSonX is a JSON structure that can round-trip with XML.
An example:

[ { "#name":"JSONX", "#jsonxversion":"0.9",
    "#xmlversion":"1.1", "#encoding":"utf-8", "#standalone":"yes",
    "#doctype":"html", "#systemId":"http://w3.org/html" },
  [ { "#name":"html", "xmlns:html":"http://www.w3.org/1999/xhtml" },
    [ { "#name":"html:head" },

      [ { "#name":"title" },
        "My document" ]
    ],
    [ { "#name":"body" },
      [ { "#name":"p", "id":"stuff" },
        "This is a ",
        [ { "#name":"i" }, "very" ],
        " short document."
      ]
    ],
    [ { "#name":"hr" } ],
    [ { "#name":"#cdata" }, "This is some \"literal\" <text>." ],
    [ { "#name":"#comment" }, "Pay no attention to the comment behind the curtains." ],
    [ { "#name":"#pi", "#target":"myApp" }, "foo='bar' version='1.0'" ]
  ]
]


==Doctype?==

Something like:

[ { "#name":"DOCTYPE", "root":"html", "systemId":"...",
    "elementFold":true, "entityFold":false },

  [ { "#name":"ELEMENT", "name":"br", "type:"EMPTY" } ],
  [ { "#name":"ELEMENT", "name":"i", "type:"PCDATA" } ],
  [ { "#name":"ELEMENT", "name":"div", "type:"ANY" } ],
  [ { "#name":"ELEMENT", "name":"html", "type:"MODEL",
      "model":"(head, body)" } ],

  [ { "#name":"ENTITY", "type":"parameter", "name":"chap1", "systemId":"..." } ],
  [ { "#name":"ENTITY", "name":"em", "data":" -- " } ],
  [ { "#name":"ATTLIST", "for":"p" },
    [ { "#name":"ATT", "name":"id", "type":"ID", "dft":"#IMPLIED" } ],
    [ { "#name":"ATT", "name":"class", "type":"NMTOKENS", "use":"#FIXED",
        "default":"normal" } ]
    [ { "#name":"ATT", "name":"just",
        type:"(left|right|center)", default:"left" } ]
  ]
  [ { "#name":"NOTATION", name:"png", "publicId":"..." } ]
]
"""


###############################################################################
# Constants for JSONX format (similar to domenums.RWord)
#
JKeys = SimpleNamespace(**{
    # Reserved JsonX pseudo-attribute *names*
    #
    "J_NAME_KEY"       : "#name",
    "J_TARGET_KEY"     : "#target",

    # Reserved JsonX pseudo-attribute *names* for ROOT node
    #
    "J_JSONX_VER_KEY"  : "#jsonxversion",
    "J_XML_VER_KEY"    : "#xmlversion",
    "J_ENCODING_KEY"   : "#encoding",
    "J_STANDALONE_KEY" : "#standalone",
    "J_DOCTYPE_KEY"    : "#doctype",    # DOCTYPE name, e.g. "html"
    "J_PUBLICID_KEY"   : "#publicId",
    "J_SYSTEMID_KEY"   : "#systemId",

    # Root node property values
    "J_JSONX_VER"      : "0.9",
    "J_XML_VER"        : "1.1",
    "J_ENCODING"       : "utf-8",
    "J_STANDALONE"     : "yes",

    # Reserved node-name ("J_NAME_KEY") *values* (cf DOM nodeNames)
    "J_NN_TOP"         : "JSONX",
    "J_NN_TEXT"        : "#text",
    "J_NN_CDATA"       : "#cdata",
    "J_NN_PI"          : "#pi",
    "J_NN_DOCUMENT"    : "#document",
    "J_NN_COMMENT"     : "#comment",
    "J_NN_ENTREF"      : "#entref",

    # Potential properties (not in JSON, might add for navigation):
    "J_PARENT"         : "#parent",
    "J_OWNERDOC"       : "#odoc",
    "J_PSIB"           : "#psib",
    "J_NSIB"           : "#nsib",
})

J_NODENAMES = [ JKeys.J_NN_TEXT, JKeys.J_NN_CDATA,
   JKeys.J_NN_PI, JKeys.J_NN_DOCUMENT, JKeys.J_NN_COMMENT ]

def getNodeName(jnode:List) -> str:
    if isinstance(jnode, (str, int, float, bool)): return JKeys.J_NN_TEXT
    if not isinstance(jnode, List):
        raise SyntaxError(f"That's not a JsonX node, but a '{type(jnode)}'.")
    if len(jnode) < 1:
        raise SyntaxError("That's not a JsonX node, no property dict.")
    try:
        return jnode[0][JKeys.J_NAME_KEY]
    except (TypeError, AttributeError, IndexError, KeyError) as e:
        raise SyntaxError("Cannot get '%s' property." % (JKeys.J_NAME_KEY)) from e


###############################################################################
#
class Loader:
    def __init__(self, domImpl:'DOMImplementation',
        jdata:Union[str, IO, List]=None):
        self.domImpl = domImpl
        self.domDoc = None
        self.jroot = None
        if not jdata:
            return
        elif isinstance(jdata, str):
            self.jroot = json.loads(jdata)
        elif isinstance(jdata, IO):
            self.jroot = json.load(jdata)
        elif isinstance(jdata, list):
            self.jroot = jdata
        else:
            raise SyntaxError(f"Bad type '{type(jdata)}' for JSONX constructor.")
        self.check_jsonx(self.jroot)
        self.domDoc = self.JDomBuilder(self.jroot)

    def check_jsonx_root(self, jroot:List):
        nn = getNodeName(jroot)
        if nn != JKeys.J_NN_DOCUMENT:
            raise SyntaxError(f"Not a JSONX root node, name is not '{nn}'.")
        props = jroot[0]
        if props[JKeys.J_NAME_KEY] != JKeys.NN_TOP: raise SyntaxError(
            f"Not JSONX, {JKeys.J_NAME_KEY} is '{nn}', not '{JKeys.NN_TOP}'.")
        assert len(self.jroot) == 2

    def check_jsonx(self, jnode:Any) -> None:
        """See if this is really correct JsonX.
        We want elements like
            [{"#name":para, "someAttr":"foo"}, [...], "some text"]
        """
        if isinstance(jnode, (str, int, float, bool)):
            return
        elif not isinstance(jnode, list): raise SyntaxError(
            f"JSONX Node must be list or atom, not {type(jnode)}.")
        elif len(jnode) < 1 or not isinstance(jnode[0], dict):
            raise SyntaxError(f"No dict in first item of JSONX node: {jnode}")
        elif JKeys.J_NAME_KEY not in jnode[0]:
            raise SyntaxError(f"No '{JKeys.J_NAME_KEY}' item in JSONX properties. "
                "Found %s." % (jnode[0]))
        else:
            nn = getNodeName(jnode)
            if not XStr.isXmlName(nn) and nn not in J_NODENAMES: raise SyntaxError(
                f"JSONX node name '{nn}' is not reserved or QName.")
            if len(jnode) > 1:
                for ch in jnode[1:]: self.check_jsonx(ch)

    def JDomBuilder(self, jroot:List) -> 'Document':
        """Build a DOM by traversing loaded JSONX.
        """
        jDocEl = jroot[1]
        assert isinstance(jDocEl, list)
        self.domDoc = self.domImpl.createDocument(None, None, None)

        lg.info("jroot[0]: %s", jroot[0])
        try:
            self.domDoc.version = jroot[0][JKeys.J_XML_VER_KEY]
            self.domDoc.encoding = jroot[0][JKeys.J_ENCODING_KEY]
            self.domDoc.standalone = jroot[0][JKeys.J_STANDALONE_KEY]
            self.domDoc.doctype = jroot[0][JKeys.J_DOCTYPE_KEY]
        except KeyError as e:
            raise KeyError(
            "JSONX missing XML ver, encoding, standalone, or doctype.") from e

        self.domDoc.publicId = (jroot[0][JKeys.J_PUBLICID_KEY] if
            JKeys.J_PUBLICID_KEY in jroot[0] else None)
        self.domDoc.systemId = (jroot[0][JKeys.J_SYSTEMID_KEY] if
            JKeys.J_SYSTEMID_KEY in jroot[0] else None)

        self.jsonSax_R(
            od=self.domDoc, par=self.domDoc.documentElement, jnode=jroot[1])
        return self.domDoc

    def jsonSax_R(self, od:'Document', par:'Node', jnode:Any):
        if isinstance(jnode, list):
            nodeName = jnode[0][JKeys.J_NAME_KEY]
            if nodeName == JKeys.J_NN_TEXT:
                # Save (below) doesn't produce these, but someone could, and
                # it's no sweat to allow it.
                txt = self.gatherAtomTexts(jnode)
                node = self.domDoc.createTextNode(ownerDocument=od, data=txt)
                par.appendChild(node)
            elif nodeName == JKeys.J_NN_CDATA:
                txt = self.gatherAtomTexts(jnode)
                node = self.domDoc.createCDATASection(
                    ownerDocument=od, data=txt)
                par.appendChild(node)
            elif nodeName == JKeys.J_NN_COMMENT:
                txt = self.gatherAtomTexts(jnode)
                node = self.domDoc.createComment(
                    ownerDocument=od, data=txt)
                par.appendChild(node)
            elif nodeName == JKeys.J_NN_PI:
                tgt = jnode[0][JKeys.J_TARGET_KEY]
                txt = self.gatherAtomTexts(jnode)
                node = self.domDoc.createprocessingInstruction(
                    ownerDocument=od, parentNode=par, target=tgt, data=txt)
                par.appendChild(node)
            elif XStr.isXmlQName(nodeName):                 # ELEMENT
                node = self.domDoc.createElement(
                    parent=par, tagName=nodeName)
                for k, v in jnode[0].items():
                    if k.startswith("#"): continue
                    node.setAttribute(k, str(v))
                if par is not None: par.appendChild(node)
                for cNum in range(1, len(jnode)):
                    self.jsonSax_R(od=od, par=node, jnode=jnode[cNum])
            else: raise SyntaxError(
                f"Unrecognized JSONX item{JKeys.J_NAME_KEY}='{nodeName}'.")
        else: # Scalars
            node = self.domDoc.createTextNode(ownerDocument=od, data=str(jnode))
            par.appendChild(node)

    @staticmethod
    def gatherAtomTexts(jnode:List) -> str:
        """Really should only be a single str, but we'll be generous.
        """
        buf = ""
        for i in range(1, len(jnode)):
            assert isinstance(jnode[i], (bool, int, float, str))
            buf += str(jnode[i])
        return buf


###############################################################################
#
def escapeJsonStr(s:str) -> str:
    return re.sub(r'([\\"])', "\\\\1", s)

class Saver:
    """Convert a subtree to isomorphic JSON.
    Intended to be idempotently round-trippable.
    """
    def __init__(self, domDoc:'Document', encoding:str="utf-8", indent:str="  "):
        self.domDoc = domDoc
        self.encoding = encoding
        self.indent = indent

    def tofile(self, path:str) -> None:
        with codecs.open(path, "wb", encoding=self.encoding) as ifh:
            ifh.write(self.DocumentToJsonX(
                domDoc=self.domDoc, indent=self.indent, depth=0))

    def tostring(self) -> str:
        return self.DocumentToJsonX(
            domDoc=self.domDoc, indent=self.indent, depth=0)

    # Converters for each node type

    def NodeToJsonX(self, node:'Node', depth:int=0) -> str:
        """Dispatch to a nodeType-specific method.
        """
        if node.isElement: return self.ElementToJsonX(node, depth)
        elif node.isTextNode: return self.TextToJsonX(node, depth)
        elif node.isCDATA: return self.CDATAToJsonX(node, depth)
        elif node.isPI: return self.PIToJsonX(node, depth)
        elif node.isComment: return self.CommentToJsonX(node, depth)
        elif node.isEntRef: return self.EntRefToJsonX(node, depth)
        else:
            raise SyntaxError(f"Unknown node type {node.nodeType}.")

    def DocumentToJsonX(self, domDoc:'Document', indent:str=None, depth:int=0) -> str:
        """Intended to be idempotently round-trippable.
        TODO: Add in Doctype or at least its reference.
        """
        if indent is not None: self.indent = indent
        try:
            pub = domDoc.publicId
        except AttributeError:
            pub = ""
        try:
            sys = domDoc.systemId
        except AttributeError:
            sys = ""

        docInfo = [
            (JKeys.J_NAME_KEY,       JKeys.J_NN_TOP),
            (JKeys.J_JSONX_VER_KEY,  JKeys.J_JSONX_VER),
            (JKeys.J_XML_VER_KEY,    JKeys.J_XML_VER),
            (JKeys.J_ENCODING_KEY,   JKeys.J_ENCODING),
            (JKeys.J_STANDALONE_KEY, JKeys.J_STANDALONE),
            (JKeys.J_DOCTYPE_KEY,    domDoc.nodeName),
            (JKeys.J_PUBLICID_KEY,   escapeJsonStr(pub)),
            (JKeys.J_SYSTEMID_KEY,   escapeJsonStr(sys)),
        ]
        buf = "[{ %s },\n" % (
            ", ".join(('"%s":"%s"' % (k, v)) for k, v in docInfo))
        buf += self.NodeToJsonX(domDoc.documentElement, depth=depth+1) + "]\n"
        return buf

    def DoctypeToJsonX(self) -> str:
        """Convert the Document type (if present) to JSONX.
        """
        dt = self.domDoc.doctype
        if not dt: return None
        buf = ""
        for dcl in self.domDoc.doctype.pentityDefs:
            buf += '[ { "#dcl":"PENTITY", "#name":"%s", ' % (dcl.name)
            if dcl.literal is not None:
                buf += '"#literal":"%s" }],\n' % (dcl.literal)
            else:
                buf += '"#publicId":"%s", "#systemId":"%s" }],\n' % (
                    dcl.publicId, dcl.systemId)

        for dcl in dt.entityDefs:
            buf += '[ { "#dcl":"ENTITY", "#name":"%s", ' % (dcl.name)
            if dcl.literal is not None:
                buf += '"#literal":"%s" }],\n' % (dcl.literal)
            else:
                buf += '"#publicId":"%s",  "#systemId":"%s" }],\n' % (
                    dcl.publicId, dcl.systemId)

        for dcl in dt.notationDefs:
            buf += '[ { "#dcl":"NOTATION", "#name":"%s", ' % (dcl.name)
            if dcl.literal is not None:
                buf += '"#literal":"%s" }],\n' % (dcl.literal)
            else:
                buf += '"#publicId":"%s",  "#systemId":"%s" }],\n' % (
                    dcl.publicId, dcl.systemId)

        # TODO What about attrs for undeclared elements?, optional global attrs?
        for dcl in dt.elementDefs:
            buf += '[ { "#dcl":"ELEMENT", "#name":"%s", ' % (dcl.name)
            buf += '"#model":"%s" }],\n' % (dcl.model.tostring())
            if dcl.attributes:
                buf += '[ { "#dcl":"ATTLIST", "#name":"%s" },\n' % (dcl.name)
                for adcl in dcl.attributes: buf += (""
                    '[ { "#dcl":"ATT", "#name":"%s", "#type":"%s", "#default":"%s" }],\n'
                    % (adcl.name, adcl.type, adcl.default))
                buf += "],\n"

        return buf

    def ElementToJsonX(self, node:'Node', depth:int=0) -> str:
        istr = self.indent * depth
        buf = '%s[ { "%s":"%s"' % (istr, JKeys.J_NAME_KEY, node.nodeName)
        if node.attributes:
            for k in node.attributes:
                anode = node.getAttributeNode(k)
                # If the values are actual int/float/bool/none, use JSON vals.
                buf += ', ' + self.attrToJson(anode)
        buf += " }"
        if node.childNodes is not None:
            for ch in node.childNodes:
                buf += ",\n" + istr
                buf += self.NodeToJsonX(ch, depth+1)
            # buf += "\n" + istr
        buf += "]"
        return buf

    def TextToJsonX(self, node:'Node', depth:int=0) -> str:
        istr = self.indent * depth
        return istr + '"%s"' % (escapeJsonStr(node.data))

    def CDATAToJsonX(self, node:'Node', depth:int=0) -> str:
        istr = self.indent * depth
        return ("""%s[ { "%s":"%s" }, "%s" ]"""
            % (istr, JKeys.J_NAME_KEY, JKeys.J_NN_CDATA, escapeJsonStr(node.data)))

    def PIToJsonX(self, node:'Node', depth:int=0) -> str:
        istr = self.indent * depth
        return ("""%s[ { "%s":"%s", "%s":"%s" }, "%s" ]"""
            % (istr, JKeys.J_NAME_KEY, JKeys.J_NN_PI,
            JKeys.J_TARGET_KEY, escapeJsonStr(node.target),
            escapeJsonStr(node.data)))

    def CommentToJsonX(self, node:'Node', depth:int=0) -> str:
        istr = self.indent * depth
        return ("""%s[ { "%s":"%s" }, "%s" ]"""
            % (istr, JKeys.J_NAME_KEY, JKeys.J_NN_COMMENT, escapeJsonStr(node.data)))

    def EntRefToJsonX(self, node:'Node', depth:int=0) -> str:
        istr = self.indent * depth
        return ("""%s[ { "%s":"%s" }, "%s" ]"""
            % (istr, JKeys.J_NAME_KEY, JKeys.J_NN_ENTREF, escapeJsonStr(node.data)))

    def attrToJson(self, anode:'Attr', listAttrs:bool=False) -> str:
        """This uses JSON non-string types iff the value is actually
        of that type, or somebody declared the attr that way.
        Not if it's a string that just looks like it (say, "99").
        """
        buf = f' "{anode.name}":'
        avalue = anode.nodeValue
        if isinstance(avalue, float): buf += "%f" % (avalue)
        elif isinstance(avalue, int): buf += "%d" % (avalue)
        elif avalue is True: buf += "true"
        elif avalue is False: buf += "false"
        elif avalue is None: buf += "nil"
        elif isinstance(avalue, str): buf += f'"{escapeJsonStr(avalue)}"'
        elif isinstance(avalue, list):  # Only for tokenized attrs
            if listAttrs:
                buf += "[ %s ]" % (
                    ", ".join([  escapeJsonStr(str(x)) for x in avalue ]))
            else:
                buf += '"%s"' % (
                    escapeJsonStr(" ".join([ str(x) for x in avalue ])))
        else:
            raise SyntaxError(
                f"attrToJson got unsupported type {type(avalue)}.")
        return buf
