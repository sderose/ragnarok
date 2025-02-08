#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
from typing import Callable, Dict, List, Any, Union
import re

from basedomtypes import NMTOKEN_t, dtr
from basedomtypes import HReqE, NSE
from domenums import RWord
from xmlstrings import XmlStrings as XStr, CaseHandler, Normalizer
#from basedom import Node, Document, Element, Attr

NS_ANY = RWord.NS_ANY
EL_ANY = RWord.EL_ANY

class AttrChoice:
    """A choice of which attributes should be treated as an ID.
    More generally, this could be specified by a full XPath. But this is
    simpler/faster, and so much more powerful than just a localname....

    ("", "", RWord.XML_PREFIX_URI, "id") should always be recognized....
    To just get all "id"s use addAttrChoice(
        ens=RWord.NS_ANY, ename=RWord.EL_ANY, ans=RWord.NS_ANY, aname="id")
    """
    def __init__(self, ens:str=NS_ANY, ename:str=EL_ANY,
        ans:str=NS_ANY, aname:str=None,
        valgen:Callable=None, caseH:Union[CaseHandler, Normalizer]=None):

        if not XStr.isXmlName(aname): raise KeyError(
            f"Bad/no attribute name specified ('{aname}').")
        if valgen is not None and not callable(valgen): raise KeyError(
            f"valgen is {type(valgen)}, not a Callable or None")

        self.ens    = ens     # Element's namespace URI
        self.ename  = ename   # An element type name
        self.ans    = ans     # Attribute's namespace URI
        self.aname  = aname   # An attribute name
        self.valgen = valgen  # A callback to calculate an ID string for a node
        self.caseH  = caseH   # CaseHandler -- TODO

    def __eq__(self, other:'AttrChoice') -> bool:
        if self.ens    != other.ens:    return False
        if self.ename  != other.ename:  return False
        if self.ans    != other.ans:    return False
        if self.aname  != other.aname:  return False
        if self.valgen != other.valgen: return False
        if self.caseH  != other.caseH:  return False
        return True

    def tostring(self) -> str:
        return f"[{self.ens}]:{self.ename} / [{self.ans}]:{self.aname}"

    def isOkNsChoice(self, ns:str) -> bool:
        """TODO Should we allow "" or None?
        """
        if ns == RWord.NS_ANY: return True
        if re.match(r"\w+://\S+$", ns): return True
        return False

class IdHandler:
    """Manage an index of ID values, and the nodes to which they attack.

    TODO Maybe make a pass to add an isId bit to attrs, or myIdAttr to elems?
    TODO Add id-space, stacked id, co-id support
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
        self.attrChoices:List[AttrChoice] = []

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
            ad = self.ownerDocument.doctype.attributeDefs
        except AttributeError:
            return 0
        nAdded = 0
        for aname, adef in ad.items():
            if adef.atype != "ID": continue
            self.addAttrChoice(ens=NS_ANY, ename=adef.name,
                ans=adef.ans, aname=aname)
            nAdded += 1
        return nAdded

    def addAttrChoice(self, ens:str=None, ename:NMTOKEN_t=None,
        ans:str=None, aname:NMTOKEN_t=None) -> None:
        """Specify a place to find ID attrs, as (elementName, attributeName).
        Set via schema, or directly via API. For just "id", use:
            idh.addAttrChoice("##any", "*", "##any", "id")
        Supports "##any" and "*".

        If valgen is set, the Node will be passed to it, and a non-None return
        is treated as the ID value for that node. This enables extensions
        such as accumulated IDs, foreign-key-like IDs, XPaths, XPointers, etc.
        """
        ac = AttrChoice(ens, ename, ans, aname, None)
        self.attrChoices.append(ac)

    def delAttrChoice(self, ens:str, ename:NMTOKEN_t, ans:str, aname:NMTOKEN_t) -> None:
        ac = AttrChoice(ens, ename, ans, aname, None)
        for i, curAC in enumerate(self.attrChoices):
            if ac != curAC: continue
            del self.attrChoices[i]
            return
        buf = f"AttrChoice not found:\n--> {ac.tostring()}" + self.choicestostring()
        raise ValueError(buf)

    def choicestostring(self) -> str:
        if not self.attrChoices: return " [none found]"
        buf = ""
        for curAC in self.attrChoices: buf += "\n    " + curAC.tostring()
        return buf

    def clearIndex(self) -> None:
        self.theIndex = {}

    def buildIdIndex(self) -> Dict:
        """Build an index of all IDs.
        TODO: Update on changing an ID attribute.
        """
        self.theIndex = {}
        nNodes = nElements = nIds = 0
        for node in self.ownerDocument.documentElement.eachNode(excludeNames="#"):
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
        anode = self.getIdAttrNode(node)
        if anode is None: return None
        if self.valgen: val = self.valgen(anode)
        else: val = anode.nodeValue.strip()
        if (self.caseHandler): val = self.caseHandler.normalize(val)
        return val

    def getIdAttrNode(self, node:'Element') -> 'Attr':
        """Check all the attributes ofan element, against their type (if any)
        and against all the active AttrChoices,
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
        for _aname in node.attributes:
            anode = node.getAttributeNode(_aname)
            dtr.msg(f"  Trying attr {anode}.")
            if anode.attrType == "ID":
                return anode
            for acTup in self.attrChoices:
                dtr.msg(f"  Trying attrChoice {acTup.tostring()}.")
                if acTup.aname != anode.nodeName:
                    continue
                if acTup.ans not in [ NS_ANY, None, "" ]:
                    anodeNS = anode.namespaceURI
                    if (anodeNS is None): raise NSE(
                        "Cannot map attribute {anode.nodeName}'s ns prefix.")
                    if acTup.ans != anodeNS: continue
                if acTup.ename not in [ EL_ANY, None, "" ]:
                    if acTup.ename != node.nodeName: continue
                if acTup.ens not in [ NS_ANY, None, "" ]:
                    elemNS = anode.ownerElement.namespaceURI
                    if (elemNS is None): raise NSE(
                        "Cannot map element {anode.ownerElement.nodeName}'s ns prefix.")
                    if acTup.ens != elemNS: continue
                dtr.msg(f"    AttrChoice {acTup.tostring()} matches attr '{anode.name}'.")
                return anode
        return None

    def getIndexedId(self, idVal:str) -> 'Element':
        if self.caseHandler: idVal = self.caseHandler.normalize(idVal)
        if idVal in self.theIndex: return self.theIndex[idVal]
        return None
