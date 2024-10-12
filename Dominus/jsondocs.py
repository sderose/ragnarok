#!/usr/bin/env python3
#
# jsondocs: Roundtrippable XML/JSON conversions.
#
import sys
import codecs
#from enum import Enum
from typing import Any
import json

from xmlstrings import XmlStrings as XStr
from saxplayer import SaxEvents

#from xml.dom import minidom as theDOMmodule
import basedom as theDOMmodule

impl = theDOMmodule.getDOMImplementation()
Document = theDOMmodule.Document
Node = theDOMmodule.Node
Element = theDOMmodule.Element


###############################################################################
#
# See domgetitem.NodeSelKind, which covers these as well as special
# names for things like @attr, @, #wsn,...
#
reservedWords = {
    "#text":    Node.TEXT_NODE,
    "#cdata":   Node.CDATA_SECTION_NODE,
    "#pi":      Node.PROCESSING_INSTRUCTION_NODE,
    "#comment": Node.COMMENT_NODE,
}


###############################################################################
#
class JsonX(list):
    """An isomorphic mapping between JSON and XML.
    TODO:
        cdata special?
        entrefs preservable?
        doctype?
        wsn?
        nsprefixes
    """
    def __init__(self):
        self.jroot = None
        self.domDoc = None
        self.callbacks = None

    def parse_jsonx(self, path:str) -> 'Document':
        # TODO: Support passing handle instead of path
        try:
            fh = codecs.open(path, "rb", encoding="utf-8")
            self.jroot = json.load(fh)
            fh.close()
        except json.decoder.JSONDecodeError as e:
            sys.stderr.write("JSON load failed for %s:\n    %s\n", path, e)
            sys.exit()

    def jsonx2dom(self):
        self.check_jsonx(self)
        self.domDoc = self.jsonDom(self.jroot)
        return self.domDoc

    def jsonx2Xml(self, jsonxpath:str, xmlpath:str):
        self.parse_jsonx(jsonxpath)
        self.domDoc.writexml(xmlpath)

    ### Separate class for whole doc vs. node?

    @property
    def nodeType(self):
        if self.nodeName.startswith("#"):
            return reservedWords[self.nodeName]
        return Node.ELEMENT_NODE

    @property
    def nodeName(self):
        return self[0]["name"]

    def check_jsonx(self, jroot):
        """Want elements like
            [{"#name":para, "class":"foo"}, [...], "txt"]
        """
        if not isinstance(jroot, list):
            assert isinstance(jroot, (str, int, float, bool))
            return

        assert isinstance(jroot, list)
        assert isinstance(jroot[0], dict)
        nam = jroot.nodeName
        assert XStr.isXmlName(nam) or reservedWords[nam]
        if len(jroot) > 1:
            for ch in jroot[1:]: self.check_jsonx(ch)

    def jsonDom(self, jroot):
        """Run jsonSax and build a DOM.
        """
        self.domDoc = None
        self.setSaxCallbacks()
        self.jsonSax(jroot)
        return self.domDoc

    def setSaxCallbacks(self):
        self.callbacks = DomBuilder.getCallBackDict()

    def jsonSax(self, jroot):
        """Generate a SAX stream from a JSON-X document.
        """
        self.tryEvent(SaxEvents.INIT)
        self.jsonSax_R(jroot)
        self.tryEvent(SaxEvents.FINAL)
        return

    def jsonSax_R(self, jroot:Any):
        nn = jroot.nodeName()
        if not isinstance(jroot, list):
            self.tryEvent(SaxEvents.CHAR, str(jroot))
        elif not nn.startswith("#"):
            self.tryEvent(SaxEvents.START, nn, *jroot[0])
            for ch in self[1:]: self.jsonSax(ch)
            self.tryEvent(SaxEvents.END, nn, *jroot[0])
        elif nn == "text":
            self.tryEvent(SaxEvents.CHAR, self.getLeafText())
        elif nn == "#pi":
            self.tryEvent(SaxEvents.CHAR, self.getLeafText())
        elif nn == "#cdata":
            self.tryEvent(SaxEvents.CDATASTART)
            self.tryEvent(SaxEvents.CHAR, self.getLeafText())
            self.tryEvent(SaxEvents.CDATAEND)
        elif nn == "#comment":
            self.tryEvent(SaxEvents.COMMENT, self.getLeafText())
        elif nn == "#doctype":
            return  # TODO Doctype???

    def getLeafText(self) -> str:
        if isinstance(self, list):
            return "".join([ str(s) for s in self[1:]])
        return str(self)

    def tryEvent(self, eventType:SaxEvents, *args):
        if eventType in self.callbacks:
            self.callbacks[eventType](args)

    def makeStartTag(self, empty:bool=False):
        buf = "<" + self.nodeName
        for k, v in self[0].items():
            buf += ' %s="%s"' % (k, v)
        return buf + ("/>" if empty else ">")

    def makeEndTag(self):
        return "</" + self.nodeName + ">"

class DomBuilder:
    """A set of SAX callbacks to create the corresponding DOM.
    """
    def __init__(self, domImplementation):
        self.domImplementation = domImplementation or impl
        self.domDoc = None
        self.tagStack = []

    @staticmethod
    def getCallBackDict():
        """Return a Dict mapping the SAXEvents Enum items, to the
        corresponding DomBuilder callbacks.
        """
        cbd = {
            SaxEvents.INIT: DomBuilder.INIT,
            SaxEvents.START: DomBuilder.START,
            SaxEvents.CHAR: DomBuilder.CHAR,
            SaxEvents.PROC: DomBuilder.PROC,
            SaxEvents.COMMENT: DomBuilder.COMMENT,
            SaxEvents.CDATASTART: DomBuilder.CDATASTART,
            SaxEvents.CDATAEND: DomBuilder.CDATAEND,
            SaxEvents.END: DomBuilder.END,
            SaxEvents.FINAL: DomBuilder.FINAL,
        }
        return cbd

    def INIT(self):
        self.domDoc = self.domImplementation.createDocument(None, "temp", None)
        self.tagStack.append(self.domDoc.documentElement)

    def START(self, name:str, **attrs):
        newNode = self.domDoc.createElement(name)
        for k, v in attrs.items():
            newNode.setAttribute(k, v)
        self.tagStack[-1].appendChild(newNode)
        self.tagStack.append(newNode)

    def END(self, name:str=None):
        assert self.tagStack[-1].nodeName == name
        self.tagStack[-1].pop()

    def CDATASTART(self):
        newNode = self.domDoc.createTextNode("")
        self.tagStack[-1].appendChild(newNode)

    def CDATAEND(self):
        assert self.tagStack[-1].nodeName == "#text"
        self.tagStack[-1].pop()

    def CHAR(self, text:str=None):
        newNode = self.domDoc.createTextNode(text)
        self.tagStack[-1].appendChild(newNode)

    def PROC(self, target:str=None, data:str=None):
        newNode = self.domDoc.createProcessingInstruction(target, data)
        self.tagStack[-1].appendChild(newNode)

    def COMMENT(self, data:str=None):
        newNode = self.domDoc.createComment(data)
        self.tagStack[-1].appendChild(newNode)

    def FINAL(self):
        assert len(self.tagStack) == 0
