#!/usr/bin/env python3
#
import sys
import re
from urllib.parse import urlparse
from typing import Union, Dict, Any

from xmlstrings import XmlStrings as XStr

descr = """
    <?pyx:default [elem@attr:type=default]*?>

elem ::= xmlname | *
attr ::= xmlname
type ::= builtInType | XMLType
builtInType ::= bool | int | float | complex | date | time | datetime
XMLType ::= nmtoken | nmtokens | cdata | ustr | lstr | id | idref | idrefs | uri
default ::= \\w+ | qlit

(see support in XmlTuples, fsplit, Datatypes)

local default via attribute?

TODO:
    namespaces?
    unify treatment of bultin vs. xml types.
"""

def isXmlNames(s:str) -> bool:
    tokens = re.split(r"\s+", s.strip())
    for token in tokens:
        if (not XStr.isXmlName(token)): return False
    return True

def isURI(s:str) -> bool:
    try:
        urlparse(s)
        return True
    except ValueError:
        return False

XMLTypes = {
    "nmtoken":  XStr.isXmlName,
    "nmtokens": isXmlNames,
    "cdata":    str,
    "ustr":     lambda x: x.upper(),
    "lstr":     lambda x: x.lower(),
    "id":       XStr.isXmlName,
    "idref":    XStr.isXmlName,
    "idrefs":   isXmlNames,
    "uri":      isURI,
}

class AttrDefault:
    """Represent type info for a single element@attr.
    If element name is empty, it applies to all.
    If type is not set, it's a string.
    """
    rawExpr = r"""([-.:\w]*)@([-.:\w]+)(:\w+)?(=(\w+|"[^"]*"|'[^']*'))?"""

    def __init__(self, raw:str):
        mat = re.match(self.rawExpr, raw, re.U)
        assert mat, "Cannot parse attribute default spec '%s'." % (raw)

        self.ename = mat.group(1)
        self.aname = mat.group(2)
        typeName = mat.group(3)
        dftVal = mat.group(4)

        # Gotta map type-name to actual type...
        self.atype = str
        self.subtype = None
        if (typeName):
            if (typeName in XMLTypes):
                self.subtype = typeName
            else:
                try:
                    theType =  getattr(__builtins__, typeName)
                    self.atype = theType
                except AttributeError:
                    sys.stderr.write("Type in '%s' ('%s') not known." % (raw, typeName))
                    sys.exit()

        self.adft = None
        if (dftVal):
            try:
                self.adft = self.atype(dftVal)
            except ValueError:
                sys.stderr.write("Default in '%s' ('%s') not castable to %s." %
                    (raw, dftVal, typeName))
                sys.exit()


class AllDefaults:
    def __init__(self, owner:'Document'=None):
        self.owner = owner
        self.byElement = {}

    def add(self, src:Union[AttrDefault, str]):
        """Construct and save the defaulter object for elem?@attr.
        """
        if (isinstance(src, str)):
            src = AttrDefault(src)
        if (src.element not in self.byElement):
            self.byElement[src.element] = {}
        self.byElement[src.element][src.aname] =src

    def find(self, ename:str, aname:str) -> AttrDefault:
        if (ename in self.byElement): dftList = self.byElement
        elif ("" in self.byElement): dftList = self.byElement
        else: return None
        if (aname in dftList): return dftList[aname]
        return None

    def applyDefaults(self, ename:str, attlist:Dict) -> Dict:
        if (ename in self.byElement):
            dftsForElement = self.byElement[ename]
        elif ("" in self.byElement):
            dftsForElement = self.byElement[""]
        else:
            return attlist

        for dftObj in dftsForElement:
            if (dftObj.aname in attlist): continue
            attlist[dftObj.aname] = dftObj.dftVal
        return attlist

    def castAttrs(self, ename:str, attlist:Dict) -> Dict:
        for k, v in attlist.items():
            dftObj = self.find(ename, k)
            if (dftObj and dftObj.atype):
                attlist[k] = dftObj.atype(v)

    def getType(self, ename:str, aname:str) -> Any:
        dftObj = self.find(ename, aname)
        if (dftObj): return dftObj.atype
        return None

    def getDft(self, ename:str, aname:str) -> Any:
        dftObj = self.find(ename, aname)
        if (dftObj): return dftObj.adft
        return None
