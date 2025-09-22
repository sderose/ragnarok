#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
from typing import Callable, Dict, List, Any, Union
import re

from ragnaroktypes import NMTOKEN_t, dtr
from ragnaroktypes import HReqE, NSE
from domenums import RWord
from runeheim import XmlStrings as Rune, CaseHandler, Normalizer
#from basedom import Node, Document, Element, Attr

NS_ANY = RWord.NS_ANY
EL_ANY = RWord.EL_ANY

class AttributeChoice:
    """A choice of which attributes should be treated as an ID.
    More generally, this could be specified by a full XPath. But this is
    simpler/faster, and so much more powerful than just a localname....

    ("", "", RWord.XML_PREFIX_URI, "id") should always be recognized....
    To just get all "id"s use addAttrChoice(
        elemNS=RWord.NS_ANY, elemName=RWord.EL_ANY, attrNS=RWord.NS_ANY, attrName="id")
    """
    def __init__(self, elemNS:str=NS_ANY, elemName:str=EL_ANY,
        attrNS:str=NS_ANY, attrName:str=None,
        valgen:Callable=None, caseH:Union[CaseHandler, Normalizer]=None):

        if not Rune.isXmlName(attrName): raise KeyError(
            f"Bad/no attribute name specified ('{attrName}').")
        if valgen is not None and not callable(valgen): raise KeyError(
            f"valgen is {type(valgen)}, not a Callable or None")

        self.elemNS    = elemNS     # Element's namespace URI
        self.elemName  = elemName   # An element type name
        self.attrNS    = attrNS     # Attribute's namespace URI
        self.attrName  = attrName   # An attribute name
        self.valgen = valgen  # A callback to calculate an ID string for a node
        self.caseH  = caseH   # CaseHandler -- TODO

    def __eq__(self, other:'AttributeChoice') -> bool:
        if self.elemNS    != other.elemNS:    return False
        if self.elemName  != other.elemName:  return False
        if self.attrNS    != other.attrNS:    return False
        if self.attrName  != other.attrName:  return False
        if self.valgen != other.valgen: return False
        if self.caseH  != other.caseH:  return False
        return True

    def tostring(self) -> str:
        return f"[{self.elemNS}]:{self.elemName} / [{self.attrNS}]:{self.attrName}"

    def isOkNsChoice(self, ns:str) -> bool:
        """TODO Should we allow "" or None?
        """
        if ns == RWord.NS_ANY: return True
        if re.match(r"\w+://\S+$", ns): return True
        return False

class IdHandler:
    """Manage an index of ID values, and the nodes to which they attack.

    TODO Support the special ID subtypes
    TODO Hook up to DocumentType for stuff it knows are IDs
    """
    def __init__(self, ownerDocument:'Document',
        caseHandler:Union[CaseHandler, Normalizer]=None,
        valgen:Callable=None):
        """Set up the ID handler.
        Specify a CaseHandler if you want case-ignoring of some kind.
        """
        self.ownerDocument = ownerDocument
        self.caseHandler = caseHandler
        self.valgen = valgen
        self.attributeChoices:List[AttributeChoice] = []

        # xml:id is reserved...
        self.addAttrChoice(NS_ANY, EL_ANY, RWord.XML_PREFIX_URI, "id")
        self.lockedChoices = False

        self.theIndex = {}

    def lockChoices(self) -> None:
        self.lockedChoices = True

    def addIdsFromDoctype(self) -> int:
        """Run through the Doctype (if any) and add any attrs that are IDs
        (does not add xml:id).
        Return the number of attribute choices added.
        """
        try:
            ad = self.ownerDocument.doctype.attrDefs
        except AttributeError:
            return 0
        nAdded = 0
        for attrName, attrDef in ad.items():
            if attrDef.attrType != "ID": continue
            self.addAttrChoice(elemNS=NS_ANY, elemName=attrDef.name,
                attrNS=attrDef.attrNS, attrName=attrName)
            nAdded += 1
        return nAdded

    def addAttrChoice(self, elemNS:str=None, elemName:NMTOKEN_t=None,
        attrNS:str=None, attrName:NMTOKEN_t=None) -> None:
        """Specify a place to find ID attrs, as (elemName, attrName).
        Set via schema, or directly via API. For just "id", use:
            idh.addAttrChoice("##any", "*", "##any", "id")
        Supports "##any" and "*".

        If valgen is set, the Node will be passed to it, and a non-None return
        is treated as the ID value for that node. This enables extensions
        such as accumulated IDs, foreign-key-like IDs, XPaths, XPointers, etc.
        """
        ac = AttributeChoice(elemNS, elemName, attrNS, attrName, None)
        self.attributeChoices.append(ac)

    def delAttributeChoice(self, elemNS:str, elemName:NMTOKEN_t, attrNS:str, attrName:NMTOKEN_t) -> None:
        ac = AttributeChoice(elemNS, elemName, attrNS, attrName, None)
        for i, curAC in enumerate(self.attributeChoices):
            if ac != curAC: continue
            del self.attributeChoices[i]
            return
        buf = f"AttributeChoice not found:\n--> {ac.tostring()}" + self.choicestostring()
        raise ValueError(buf)

    def choicestostring(self) -> str:
        if not self.attributeChoices: return " [none found]"
        buf = ""
        for curAC in self.attributeChoices: buf += "\n    " + curAC.tostring()
        return buf

    def clearIndex(self) -> None:
        self.theIndex = {}

    def buildIdIndex(self) -> Dict:
        """Build an index of all IDs.
        TODO: Update on changing an ID attribute.
        """
        self.theIndex = {}
        nNodes = nElements = nIds = 0
        for node in self.ownerDocument.documentElement.descendants(
            test=lambda x: x.isElement):
            #print(f"Node: {node.nodeName}")
            nNodes += 1
            if not node.isElement: continue
            nElements += 1
            #print(node.startTag)
            idVal = self.getIdVal(node)
            if idVal is not None:
                if self.caseHandler: idVal = self.caseHandler.normalize(idVal)
                nIds += 1
                self.theIndex[idVal] = node

        #print(f"\nFound {nNodes} nodes, {nElements} elements, {nIds} Ids.")
        #print("Choices:\n" + self.choicestostring())
        return self.theIndex

    def removeElementFromIndex(self, node:'Element') -> None:
        idVal = self.getIdVal(node)
        if self.caseHandler: idVal = self.caseHandler.normalize(idVal)
        if idVal and idVal in self.theIndex: del self.theIndex[idVal]

    def getIdVal(self, node:'Element') -> Any:
        attrNode = self.getIdAttrNode(node)
        if attrNode is None: return None
        if self.valgen: val = self.valgen(attrNode)
        else: val = attrNode.nodeValue.strip()
        if (self.caseHandler): val = self.caseHandler.normalize(val)
        return val

    def getIdAttrNode(self, node:'Element') -> 'Attr':
        """Check all the attributes ofan element, against their type (if any)
        and against all the active AttributeChoices,
        to find if any of them is actually an ID.
        Returns the first ID found.
        TODO: In theory, we needn't stop at just one match....
        """
        if not node.isElement:
            raise HReqE("Looking for ID on non-Element.")
        if not node.hasAttributes():
            return None
        dtr.msg(f"\nStart-tag (ns: {node.namespaceURI}): {node.startTag}.")
        if node.hasAttribute("xml:id"):
            dtr.msg("    Got xml:id")
            return node.getAttributeNode("xml:id")
        for _attrName in node.attributes:
            attrNode = node.getAttributeNode(_attrName)
            dtr.msg(f"  Trying attribute {attrNode}.")
            if attrNode.attrType == "ID":
                return attrNode
            for acTup in self.attributeChoices:
                dtr.msg(f"  Trying attribute choice {acTup.tostring()}.")
                if acTup.attrName != attrNode.nodeName:
                    continue
                if acTup.attrNS not in [ NS_ANY, None, "" ]:
                    attrNodeNS = attrNode.namespaceURI
                    if (attrNodeNS is None): raise NSE(
                        "Cannot map attribute {attrNode.nodeName}'s ns prefix.")
                    if acTup.attrNS != attrNodeNS: continue
                if acTup.elemName not in [ EL_ANY, None, "" ]:
                    if acTup.elemName != node.nodeName: continue
                if acTup.elemNS not in [ NS_ANY, None, "" ]:
                    elemNS = attrNode.ownerElement.namespaceURI
                    if (elemNS is None): raise NSE(
                        "Cannot map element {attrNode.ownerElement.nodeName}'s ns prefix.")
                    if acTup.elemNS != elemNS: continue
                dtr.msg(f"    AttributeChoice {acTup.tostring()} matches attribute '{attrNode.name}'.")
                return attrNode
        return None

    def getIndexedId(self, idVal:str) -> 'Element':
        if self.caseHandler: idVal = self.caseHandler.normalize(idVal)
        if idVal in self.theIndex: return self.theIndex[idVal]
        return None
