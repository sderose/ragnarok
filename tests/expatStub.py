#!/usr/bin/env python3
#
from xml.parsers import expat
from typing import Dict
import re

descr = """
Details on expat

* Parser can't be re-used.

* Special character references generate separate text events.

* Newlines generate a separate text event.

* Model is a 4-tuple per token or group:
    (type, rep, name, tuple)
    type: 1=empty, 2=any, 3=pcdata, 4=token, 5=orgroup, 6=seqgroup/single
        cf expat.model.XML_CTYPE_MIXED
    rep: 0=none, 1=?, 2=*, 3=+
    name: For tokens, name; else None
    group: a list of subitem tuples

* Entities have several event types, but seem to get:
    name, isparam, literal,  ???, sysId, pubId, notation

* DefaultHandler seem to be called with whitespace between dcls.

* A separate attlist event per attribute.

* To deal with namespace, you have to set namespace_separator = " " on
ParserCreate(). It then:
    * Issues StartNamespaceDeclHandler 'pfx', 'uri') for each newly-declared xmlns...,
immediately before the declaring element's StartElementHandler.
    * substitutes namespace uris for explicit prefixes, separated by the
given character.
    * Issues EndNamespaceDeclHandler 'pfx' i,ediately after the EndElementHandler
at which a prefix goes out of scope (including root ones after the end of the
document element)
"""

reps = {
    0: "",
    1: "?",
    2: "*",
    3: "+",
}

def decodeModel(tup) -> str:
    """Every decoding is another encoding.
        -- Morris Zapp
    """
    assert len(tup) == 4
    buf = ""
    typ = tup[0]
    if typ == 1: return "EMPTY"
    if typ == 2: return "ANY"
    if typ == 4:
        return tup[2] + reps[tup[1]]
    if typ == 5 or typ == 3:
        buf = "(" + ("#PCDATA | " if typ == 3 else "")
        for sub in tup[3]: buf += decodeModel(sub) + " | "
        buf = buf[0:-3] + ")" + reps[tup[1]]
        return buf
    if typ == 6:
        buf = "("
        for sub in tup[3]: buf += decodeModel(sub) + ", "
        buf = buf[0:-2] + ")" + reps[tup[1]]
        return buf
    raise KeyError("Unrecognized model type %s" % (typ))


class Handlers:
    def __init__(self):
        self.depth = 0

    def StartElementHandler(self, name:str, attrs:Dict) -> None:
        pattrs = ""
        if attrs:
            for k, v in attrs.items():
                pattrs += ' %s="%s"' % (k, v)
        print("%s<%s%s>" % ("    " * self.depth, name, pattrs))
        self.depth += 1

    def EndElementHandler(self, name:str) -> None:
        self.depth -= 1
        print("%s</%s>" % ("    " * self.depth, name))

    def CharacterDataHandler(self, data:str) -> None:
        print("%s%s" % ("    " * self.depth, re.sub(r"\n", "\\n", data)))

    def CommentHandler(self, data:str) -> None:
        print("%s<!--%s-->" % ("    " * self.depth, data))

    def ProcessingInstructionHandler(self, target:str, data:str) -> None:
        print("%s<?%s %s?>" % ("    " * self.depth, target, data))

    def StartCdataSectionHandler(self) -> None:
        print("<![CDATA[")
    def EndCdataSectionHandler(self) -> None:
        print("]]>")

    def StartNamespaceDeclHandler(self, name:str, *args) -> None:
        print(f"StartNamespaceDeclHandler: '{name}' {args}")
    def EndNamespaceDeclHandler(self, name:str, *args) -> None:
        print(f"EndNamespaceDeclHandler: '{name}' {args}")


    def XmlDeclHandler(self, version, encoding, standalone) -> None:
        print("%s<?xml version='%s' encoding='%s' standalone='%s'?>"
            % ("    " * self.depth, version, encoding, standalone))

    def StartDoctypeDeclHandler(self, name, pubId, sysId, _hasSubset) -> None:
        print("%s<!DOCTYPE %s PUBLIC '%s' '%s' ["
            % ("    " * self.depth, name, pubId, sysId,))

    def EndDoctypeDeclHandler(self) -> None:
        print("%s]>" % ("    " * self.depth))

    def ElementDeclHandler(self, name:str, model:str="ANY") -> None:
        pmodel = decodeModel(model)
        print("%s<!ELEMENT %-8s %s>" % ("    " * self.depth, name, pmodel))

    def AttlistDeclHandler(self, ename:str, aname, atype, adft, req) -> None:
        print("%s<!ATTLIST %-8s %-8s %-8s %s %s>"
            % ("    " * self.depth, ename, aname, atype, adft if adft else "''",
            "#REQUIRED" if req else "#IMPLIED"))

    def NotationDeclHandler(self, name:str, *args) -> None:
        print("%s<!NOTATION %s %s>" % ("    " * self.depth, name, args))

    def EntityDeclHandler(self, name:str, isParam,
        literal, _xxx, sysId="", pubId="", notation="") -> None:
        if pubId is None: pubId = ""
        loc = f'"{literal}"' if literal else f'PUBLIC "{pubId}" "{sysId}"'
        ind = "    " * self.depth
        pFlag = " %" if isParam else ""
        ndata = f" NDATA {notation}" if notation else ""
        msg = "%s<!ENTITY%s %-8s %s%s?" % (ind, pFlag, name, loc, ndata)
        print(msg)

    def UnparsedEntityDeclHandler(self, name:str, isParam,
        literal, _xxx, sysId="", pubId="", notation="") -> None:
        if pubId is None: pubId = ""
        loc = f'"{literal}"' if literal else f'PUBLIC "{pubId}" "{sysId}"'
        print("%s<!ENTITY%s %-8s %s NDATA %s>"
            % ("    " * self.depth, " %" if isParam else "",
            name, loc, notation))

    def ExternalEntityRefHandler(self, name:str, *args) -> None:
        print(f"ExternalEntityRefHandler '{name}' {args}")

    def SkippedEntityHandler(self, name:str, *args) -> None:
        print(f"SkippedEntityHandler: '{name}' {args}")

    def DefaultHandler(self, *args) -> None:
        print("DefaultHandler: '%s'" % (args or ""))
    def DefaultHandlerExpand(self, name:str, *args) -> None:
        print(f"DefaultHandlerExpand: '{name}' {args}")

h = Handlers()
p = expat.ParserCreate(
    encoding="utf-8",
    namespace_separator=None  # Leaves xmlns as attrs, and prefixes as-is.
)

p.StartElementHandler = h.StartElementHandler
p.EndElementHandler = h.EndElementHandler
p.CharacterDataHandler = h.CharacterDataHandler
p.CommentHandler = h.CommentHandler
p.ProcessingInstructionHandler = h.ProcessingInstructionHandler
p.StartCdataSectionHandler = h.StartCdataSectionHandler
p.EndCdataSectionHandler = h.EndCdataSectionHandler
p.StartNamespaceDeclHandler = h.StartNamespaceDeclHandler
p.EndNamespaceDeclHandler = h.EndNamespaceDeclHandler

p.XmlDeclHandler = h.XmlDeclHandler
p.StartDoctypeDeclHandler = h.StartDoctypeDeclHandler
p.EndDoctypeDeclHandler = h.EndDoctypeDeclHandler
p.ElementDeclHandler = h.ElementDeclHandler
p.AttlistDeclHandler = h.AttlistDeclHandler
p.NotationDeclHandler = h.NotationDeclHandler
p.EntityDeclHandler = h.EntityDeclHandler
p.UnparsedEntityDeclHandler = h.UnparsedEntityDeclHandler
p.ExternalEntityRefHandler = h.ExternalEntityRefHandler
p.SkippedEntityHandler = h.SkippedEntityHandler

p.DefaultHandler = h.DefaultHandler
p.DefaultHandlerExpand = h.DefaultHandlerExpand

samples = {
    "minimal":
"""<a><b><c id=" foo " xml:id="  bar  ">Hello</c></b></a>""",

    "leaves":
"""<a><b><c id=" foo " xml:id="  bar  ">Hello, &#x77;orld.<![CDATA[mstext]]>
    <?tgt piData?></c></b></a>""",

    "doctype":
"""<?xml version="1.0" encoding="utf-8"?>
    <!DOCTYPE a PUBLIC "pub" "sys">
    <a><b><c id=" foo " xml:id="  bar  ">Hello, world.</c></b></a>""",

    "dcls":
"""<?xml version="1.0" encoding="utf-8"?>
    <!-- Try a few things. -->
    <!DOCTYPE a PUBLIC "pub" "sys" [
    <!ELEMENT e EMPTY>
    <!ELEMENT a ANY>
    <!ELEMENT p (#PCDATA)>
    <!ELEMENT b11 (b)>
    <!ELEMENT b01 (b?)>
    <!ELEMENT b02 (b*)>
    <!ELEMENT b12 (b+)>
    <!ELEMENT seq (a, b, c)>
    <!ELEMENT ors (a | b | c)>
    <!ELEMENT c (#PCDATA | a | b | c)*>
    <!ELEMENT d ((a, b) | (c, d))>
    <!ELEMENT f (a | b | c)*>

    <!ATTLIST c id    ID      #IMPLIED
                class CDATA   #IMPLIED
                alt   CDATA   #REQUIRED
                nname NMTOKEN "c"
                type  (A | B | C) "A"
                >
    <!NOTATION jpeg    SYSTEM 'gview.app'>

    <!ENTITY   mash    "M*A*S*H">
    <!ENTITY   fig1    SYSTEM 'fig1.jpg' NDATA jpeg>
    <!ENTITY   chap1   PUBLIC "-//foo" 'chap1.xml'>
    <!ENTITY   % dcls  SYSTEM 'moreDcls.xml'>
    ]>
    <a><b><c id=" foo " xml:id="  bar  ">Hello, world.<![CDATA[mstext]]>
    <?tgt piData?></c></b></a>""",

    "ns":
"""<zork xmlns:tei="https://tei-c.org/ns/P3" xmlns:db="http://docbook.net/ns/db5.0">
<db:div1><title>Intro</title>
<tei:poem>Shall I compare thee to an <i>empty</i> tag?</tei:poem>
<para tei:rend="bold">Eh?</para>
<tei:div2 xmlns:svg="http://svg.net/ns"><speech><svg:rect path="1 1 1 1"/></speech>
</tei:div2>
</db:div1>
</zork>
""",

}

p.Parse(samples["ns"])
