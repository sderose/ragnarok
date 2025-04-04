#!/usr/bin/env python3
#
# JBook: Roundtrippable XML/JSON conversions.
#
#import sys
import codecs
import re
from typing import Any, List, IO, Union
from types import SimpleNamespace
import json
import logging

from runeheim import XmlStrings as Rune

lg = logging.getLogger("JBook")
logging.basicConfig(level=logging.INFO, format='%(message)s')


###############################################################################
# Constants
#
KEY_FLAG = "!"
VAL_FLAG = "#"

JKeys = SimpleNamespace(**{
    # The reserved key for what each item is
    #
    "J_NAME_KEY"       : f"~",  # or U+203B?

    # Reserved dictionary keys for ROOT node
    #
    "J_JBOOK_VER_KEY"  : f"{KEY_FLAG}jbookversion",
    "J_JSON_VER_KEY"   : f"{KEY_FLAG}jsonversion",
    "J_XML_VER_KEY"    : f"{KEY_FLAG}xmlversion",
    "J_ENCODING_KEY"   : f"{KEY_FLAG}encoding",
    "J_STANDALONE_KEY" : f"{KEY_FLAG}standalone",
    "J_DOCTYPE_KEY"    : f"{KEY_FLAG}doctype",  # E.g. "html"
    "J_PUBLICID_KEY"   : f"{KEY_FLAG}publicId",
    "J_SYSTEMID_KEY"   : f"{KEY_FLAG}systemId",
    "J_TARGET_KEY"     : f"{KEY_FLAG}target",

    # Root node property *values*
    "J_JBOOK_VER"      : "0.9",
    "J_XML_VER"        : "1.1",
    "J_ENCODING"       : "utf-8",
    "J_STANDALONE"     : "yes",

    # Reserved node-name ("J_NAME_KEY") *values*
    "J_NN_TOP"         : "JBook",
    "J_NN_TEXT"        : f"{VAL_FLAG}text",
    "J_NN_CDATA"       : f"{VAL_FLAG}cdata",
    "J_NN_PI"          : f"{VAL_FLAG}pi",
    "J_NN_DOCUMENT"    : f"{VAL_FLAG}document",
    "J_NN_COMMENT"     : f"{VAL_FLAG}comment",
    "J_NN_ENTREF"      : f"{VAL_FLAG}entref",
})

J_NODENAMES = [ JKeys.J_NN_TEXT, JKeys.J_NN_CDATA,
   JKeys.J_NN_PI, JKeys.J_NN_DOCUMENT, JKeys.J_NN_COMMENT ]

def getNodeName(jnode:List) -> str:
    if isinstance(jnode, (str, int, float, bool)): return JKeys.J_NN_TEXT
    if not isinstance(jnode, List):
        raise SyntaxError(f"That's not a jnode (it's type '{type(jnode)}').")
    if len(jnode) < 1:
        raise SyntaxError("That's not a proper jnode nde (no property dict).")
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
            raise SyntaxError(f"Bad type '{type(jdata)}' for jdata.")
        self.check_json(self.jroot)
        self.domDoc = self.JDomBuilder(self.jroot)

    def check_json_root(self, jroot:List) -> None:
        nn = getNodeName(jroot)
        if nn != JKeys.J_NN_DOCUMENT:
            raise SyntaxError(f"JSON top is not named '{nn}'.")
        props = jroot[0]
        if props[JKeys.J_NAME_KEY] != JKeys.NN_TOP: raise SyntaxError(
            f"Error, {JKeys.J_NAME_KEY} is '{nn}', not '{JKeys.NN_TOP}'.")
        assert len(self.jroot) == 2

    def check_json(self, jnode:Any, deep:bool=True) -> None:
        """See if this is really correct JSON usage for us.
        """
        if isinstance(jnode, (str, int, float, bool)):
            return
        elif not isinstance(jnode, list): raise SyntaxError(
            f"JSON component must be list or atom, not {type(jnode)}.")
        elif len(jnode) < 1 or not isinstance(jnode[0], dict):
            raise SyntaxError(f"No dict in first item of JSON component: {jnode}")
        elif JKeys.J_NAME_KEY not in jnode[0]:
            raise SyntaxError(f"No '{JKeys.J_NAME_KEY}' item in properties. "
                "Found %s." % (jnode[0]))
        else:
            nn = getNodeName(jnode)
            if not Rune.isXmlName(nn) and nn not in J_NODENAMES: raise SyntaxError(
                f"Component name '{nn}' is not reserved or QName.")
            if deep and len(jnode) > 1:
                for ch in jnode[1:]: self.check_json(ch)

    def JDomBuilder(self, jroot:List) -> 'Document':
        """Build a DOM by traversing loaded JSON.
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
            "Missing XML ver, encoding, standalone, or doctype.") from e

        self.domDoc.publicId = (jroot[0][JKeys.J_PUBLICID_KEY] if
            JKeys.J_PUBLICID_KEY in jroot[0] else None)
        self.domDoc.systemId = (jroot[0][JKeys.J_SYSTEMID_KEY] if
            JKeys.J_SYSTEMID_KEY in jroot[0] else None)

        self.JDoc2Dom_R(
            od=self.domDoc, par=self.domDoc.documentElement, jnode=jroot[1])
        return self.domDoc

    def JDoc2Dom_R(self, od:'Document', par:'Node', jnode:Any) -> None:
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
            elif Rune.isXmlQName(nodeName):                 # ELEMENT
                node = self.domDoc.createElement(
                    parent=par, tagName=nodeName)
                for k, v in jnode[0].items():
                    if Rune.isXmlQName(k): node.setAttribute(k, str(v))
                if par is not None: par.appendChild(node)
                for cNum in range(1, len(jnode)):
                    self.JDoc2Dom_R(od=od, par=node, jnode=jnode[cNum])
            else: raise SyntaxError(
                f"Unrecognized item{JKeys.J_NAME_KEY}='{nodeName}'.")
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
            ifh.write(self.DocumentToJ(
                domDoc=self.domDoc, indent=self.indent, depth=0))

    def tostring(self) -> str:
        return self.DocumentToJ(
            domDoc=self.domDoc, indent=self.indent, depth=0)

    # Converters for each node type

    def NodeToJ(self, node:'Node', depth:int=0) -> str:
        """Dispatch to a nodeType-specific method.
        """
        if node.isElement: return self.ElementToJ(node, depth)
        elif node.isTextNode: return self.TextToJ(node, depth)
        elif node.isCDATA: return self.CDATAToJ(node, depth)
        elif node.isPI: return self.PIToJ(node, depth)
        elif node.isComment: return self.CommentToJ(node, depth)
        elif node.isEntRef: return self.EntRefToJ(node, depth)
        else:
            raise SyntaxError(f"Unknown node type {node.nodeType}.")

    def DocumentToJ(self, domDoc:'Document', indent:str=None, depth:int=0) -> str:
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
            (JKeys.J_JBOOK_VER_KEY,  JKeys.J_JBOOK_VER),
            (JKeys.J_XML_VER_KEY,    JKeys.J_XML_VER),
            (JKeys.J_ENCODING_KEY,   JKeys.J_ENCODING),
            (JKeys.J_STANDALONE_KEY, JKeys.J_STANDALONE),
            (JKeys.J_DOCTYPE_KEY,    domDoc.nodeName),
            (JKeys.J_PUBLICID_KEY,   escapeJsonStr(pub)),
            (JKeys.J_SYSTEMID_KEY,   escapeJsonStr(sys)),
        ]
        buf = "[{ %s },\n" % (
            ", ".join(('"%s":"%s"' % (k, v)) for k, v in docInfo))
        buf += self.NodeToJ(domDoc.documentElement, depth=depth+1) + "]\n"
        return buf

    def DoctypeToJ(self) -> str:
        """Convert a Document type (if present).
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

    def ElementToJ(self, node:'Node', depth:int=0) -> str:
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
                buf += self.NodeToJ(ch, depth+1)
            # buf += "\n" + istr
        buf += "]"
        return buf

    def TextToJ(self, node:'Node', depth:int=0) -> str:
        istr = self.indent * depth
        return istr + '"%s"' % (escapeJsonStr(node.data))

    def CDATAToJ(self, node:'Node', depth:int=0) -> str:
        istr = self.indent * depth
        return ("""%s[ { "%s":"%s" }, "%s" ]"""
            % (istr, JKeys.J_NAME_KEY, JKeys.J_NN_CDATA, escapeJsonStr(node.data)))

    def PIToJ(self, node:'Node', depth:int=0) -> str:
        istr = self.indent * depth
        return ("""%s[ { "%s":"%s", "%s":"%s" }, "%s" ]"""
            % (istr, JKeys.J_NAME_KEY, JKeys.J_NN_PI,
            JKeys.J_TARGET_KEY, escapeJsonStr(node.target),
            escapeJsonStr(node.data)))

    def CommentToJ(self, node:'Node', depth:int=0) -> str:
        istr = self.indent * depth
        return ("""%s[ { "%s":"%s" }, "%s" ]"""
            % (istr, JKeys.J_NAME_KEY, JKeys.J_NN_COMMENT, escapeJsonStr(node.data)))

    def EntRefToJ(self, node:'Node', depth:int=0) -> str:
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
