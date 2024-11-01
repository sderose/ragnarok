#!/usr/bin/env python3
#
# jsondocs: Roundtrippable XML/JSON conversions.
#
import sys
import codecs
from enum import Enum
from typing import Any  #, List
import json

from xmlstrings import XmlStrings as XStr
from saxplayer import SaxEvent
from dombuilder import DomBuilder
from domenums import RWord, NodeType

# DOMImplementation

descr = """
==Description==

Load some JsonX: a JSON structure that can round-trip with XML.
An example:

[ { "#name":"#document", "#format":"JSONX",
    "#version":"1.1", "#encoding":"utf-8", "#standalone":"yes",
    "#doctype":"html", "#systemId":"http://w3.org/html" },
  [ { "#name": "html", "xmlns:html": "http://www.w3.org/1999/xhtml" },
    [ { "#name": "html:head" },
      [ { "#name": "title" },
        "My document" ]
    ],
    [ { "#name": "body" },
      [ { "#name": "p", "id":"stuff" },
        "This is a ",
        [ { "#name": "i" }, "very" ],
        " short document."
      ]
    ],
    [ { "#name": "hr" } ],
    [ { "#name": "#cdata" }, "This is some \"literal\" <text>." ],
    [ { "#name": "#comment" }, "Pay no attention to the comment behind the curtains." ],
    [ { "#name": "#pi", "#target":"myApp" }, "foo='bar' version='1.0'" ]
  ]
]


==Doctype?==

[ { "#name"="DOCTYPE", "root"="html", "systemId"="...",
    "elementFold":true, "entityFold":false },

  [ { "#name"="ELEMENT", "name"="br", "type="EMPTY" } ],
  [ { "#name"="ELEMENT", "name"="i", "type="PCDATA" } ],
  [ { "#name"="ELEMENT", "name"="div", "type="ANY" } ],
  [ { "#name"="ELEMENT", "name"="html", "type="MODEL",
      "model"="(head, body)" } ],

  [ { "#name"="ENTITY", "type"="parameter", "name"="chap1", "systemId"="..." } ],
  [ { "#name"="ENTITY", "name"="em", "data"=" -- " } ],
  [ { "#name"="ATTLIST", "for"="p" },
    [ { "#name"="ATT", "name"="id", "type"="ID", "use"="#IMPLIED" } ],
    [ { "#name"="ATT", "name"="class", "type"="NMTOKENS", "use"="#FIXED",
        "default"="normal" } ]
    [ { "#name"="ATT", "name"="just",
        type="(left|right|center)", default="left" } ]
  ]
  [ { "#name"="NOTATION", name="png", "publicId"="..." } ]
]


==To Do==

* Maybe shorten "#name" to "#" or "." or something?
* Specify doctype mapping
* How to pick documentElement among children of doc
* Separate JSONX vs. XML version
* Reserve a place for stylesheet pi or content
* Enable link() to bump strings/ints/floats/bools to jnodes
* Move jsonx support from basedom to here
"""


###############################################################################
#
class JKeys(Enum):
    # JsonX pseudo-attribute names
    #
    J_NAME      = "#name"
    J_PARENT    = "#parent"
    J_ODOC      = "#odoc"
    J_PSIB      = "#psib"
    J_NSIB      = "#nsib"
    J_VERSION   = "#version"
    J_ENCODING  = "#encoding"
    J_STANDALONE= "#standalone"
    J_DOCTYPE   = "#doctype"
    J_PUBLICID  = "#publicId"
    J_SYSTEMID  = "#systemId"
    J_FORMAT    = "#format"  # Const value "JSONX"
    J_TARGET    = "#target"

    # #name values are same a DOM nodeType: #text #cdata #pi #document #comment


###############################################################################
#
class JNode(list):
    """The equivalent of an XML Node, in JsonX as loaded. That's a list,
    where [0] is a dict with attrs and a few reserved items like "#name",
    and [1:] are children, which are JNodes or atomic types like strings:
        [ { "#name"="P", "id"="myId" }, "Hello, world" ]
    Since there are no cross-references (pointers, IDs) available in JSON,
    once a tree is loaded key ones can be added by calling link().
    """
    def __init__(self, domImpl:'DOMImplementation'):
        self.domImpl = domImpl
        self.jroot = None
        self.loader = None

    def loadJsonX2Dom(self, path:str):
        self.loader = Loader(domImpl=self.domImpl)
        self.loader.parse_jsonx(path)
        self.loader.check_jsonx(self.jroot)
        self.jroot.link()

    @property
    def nodeType(self):
        if self.nodeName.startswith("#"):
            return RWord[self.nodeName]
        return NodeType.ELEMENT_NODE
    @property
    def nodeName(self):
        return self[0][JKeys.J_NAME]
    @property
    def prefix(self):
        if ":" not in self.nodeName: return
        return self.nodeName.partition(":")[0]
    @property
    def localName(self):
        if ":" not in self.nodeName: return self.nodeName
        return self.nodeName.partition(":")[2]

    def hasAttributes(self) -> bool:
        return bool(self[0])
    def hasAttribute(self, aname:str) -> bool:
        return aname in self[0]
    def getAttribute(self, aname:str) -> Any:
        if aname not in self[0]: return None
        return self[0][aname]
    def setAttribute(self, aname:str, avalue:Any) -> None:
        self[0][aname] = avalue

    def hasChildNodes(self) -> bool:
        return bool(len(self) > 1)
    def childNodes(self):
        return self[1:]


    ##########################################################################
    # To get location-related properties, need to run link() first.
    #
    def link(self, oDoc:'JNode'):
        """Add all the pointers that plain JSON rep lacks.
        But, there are no Attr and Text nodes (the attr Dict has oDoc).
        """
        for i, ch in enumerate(self):
            if not isinstance(ch, JNode): continue
            ch[0][JKeys.J_ODOC] = oDoc
            ch[0][JKeys.J_PARENT] = self
            if i == 0: continue
            ch[0][JKeys.J_PSIB] = self[i-1]
            if i < len(self)-1: ch[0][JKeys.J_NSIB] = self[i+1]
            ch.annotate(oDoc=oDoc)

    def unlink(self):
        del self[0][JKeys.J_ODOC]
        del self[0][JKeys.J_PARENT]
        del self[0][JKeys.J_PSIB]
        del self[0][JKeys.J_NSIB]
        for ch in self:
            if isinstance(ch, JNode): ch.unlink()

    @property
    def ownerDocument(self):
        return self.getAttribute(JKeys.J_ODOC)
    @property
    def parentNode(self):
        return self.getAttribute(JKeys.J_PARENT)
    @property
    def previousSibling(self):
        return self.getAttribute(JKeys.J_PSIB)
    @property
    def nextSibling(self):
        return self.getAttribute(JKeys.J_NSIB)


###############################################################################
#
class Loader:
    def __init__(self, domImpl:'DOMImplementation'):
        self.domDoc = None
        self.jroot = JNode(domImpl)
        self.domBuilder = DomBuilder(
            domImpl=domImpl, wsn=False, verbose=1, nsSep=":")
        self.callbacks = self.domBuilder.getHandlerDict()
        self.jsonSax(self.jroot)

    def parse_jsonx(self, path:str) -> 'Document':
        """Just load the JSON en mass, into self.jroot.
        TODO: Support passing handle instead of path.
        """
        try:
            fh = codecs.open(path, "rb", encoding="utf-8")
            self.jroot = json.load(fh)
            fh.close()
        except json.decoder.JSONDecodeError as e:
            sys.stderr.write("JSON load failed for %s:\n    %s\n", path, e)
            sys.exit()

    def check_jsonx(self, node:'Node'):
        """Want elements like
            [{"#name":para, "class":"foo"}, [...], "txt"]
        """
        if not isinstance(self.jroot, list):
            assert isinstance(self.jroot, (str, int, float, bool))
            return

        assert isinstance(node, list)
        assert isinstance(node[0], dict)
        assert JKeys.J_NAME in node[0]
        assert XStr.isXmlName(node.nodeName) or RWord(node.nodeName)
        if len(self.jroot) > 1:
            for ch in self.jroot[1:]: self.check_jsonx(ch)

    def jsonSax(self, jroot):
        """Generate a SAX stream from a JSON-X document.
        """
        self.tryEvent(SaxEvent.INIT)
        self.jsonSax_R(jroot)
        self.tryEvent(SaxEvent.FINAL)
        return

    def jsonSax_R(self, jroot:Any):
        nn = jroot.nodeName()
        if not isinstance(jroot, list):
            self.tryEvent(SaxEvent.CHAR, str(jroot))
        elif not nn.startswith("#"):
            self.tryEvent(SaxEvent.START, nn, *jroot[0])
            for ch in self.jroot[1:]: self.jsonSax(ch)
            self.tryEvent(SaxEvent.END, nn, *jroot[0])
        elif nn == RWord.NN_TEXT:
            self.tryEvent(SaxEvent.CHAR, self.getLeafText())
        elif nn == RWord.NN_PI:
            self.tryEvent(SaxEvent.CHAR, self.getLeafText())
        elif nn == RWord.NN_CDATA:
            self.tryEvent(SaxEvent.CDATASTART)
            self.tryEvent(SaxEvent.CHAR, self.getLeafText())
            self.tryEvent(SaxEvent.CDATAEND)
        elif nn == RWord.NN_COMMENT:
            self.tryEvent(SaxEvent.COMMENT, self.getLeafText())
        elif nn == RWord.NN_DOCTYPE:
            return  # TODO Doctype???

    def getLeafText(self) -> str:
        if isinstance(self, list):
            return "".join([ str(s) for s in self.jroot[1:]])
        return str(self)

    def tryEvent(self, eventType:SaxEvent, *args):
        """If there's a handler, call it.
        """
        if eventType in self.callbacks:
            self.callbacks[eventType](args)

    def makeStartTag(self, empty:bool=False):
        buf = "<" + self.jroot.nodeName
        for k, v in self.jroot[0].items():
            buf += ' %s="%s"' % (k, v)
        return buf + ("/>" if empty else ">")

    def makeEndTag(self):
        return "</" + self.jroot.nodeName + ">"
