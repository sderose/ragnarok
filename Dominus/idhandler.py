#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
from collections import namedtuple
from typing import Callable, Dict

from basedomtypes import NMTOKEN_t
from basedomtypes import HReqE
#from basedomtypes import ICharE
#from basedomtypes import NSuppE
#from basedomtypes import NamespaceError
#from basedomtypes import NotFoundError
#from basedomtypes import OperationError
from domenums import RWord
from xmlstrings import CaseHandler  # XmlStrings as XStr,
#from basedom import Node, Document, Element, Attr


# A choice of element@attr to be treated as an ID
#
AttrChoice = namedtuple("AttChoice", [
    "ens",     # Element's namespace URI, or "##any"
    "ename",   # An element type name, or "*"
    "ans",     # Attribute's namespace URI, or "##any"
    "aname",   # An attribute name (no "*")
    "valgen"   # A callback to calculate the ID string for a node.
])


class IdHandler:
    """Manage an index of ID values, and the nodes to which they attack.
    TODO Dang, it's the attr's ns that matters....
    TODO Maybe just make a pass to add an isId bit to attrs, or myIdAttr to elems?
        Prob. easier to do updates then.
    """
    def __init__(self, ownerDocument:'Document', caseHandler:CaseHandler=None,
        valgen:Callable=None):
        """Set up the ID handler.
        Specify a CaseHandler if you want case-ignoring of some kind.
        """
        self.ownerDocument = ownerDocument
        self.caseHandler = caseHandler
        self.valgen = valgen
        self.attrChoices = []

        self.addAttrChoice(RWord.NS_ANY, "*", RWord.XML_NS_URI, "id")
        self.lockedChoices = False

        self.theIndex = {}

    def lockChoices(self) -> None:
        self.lockedChoices = True

    def addAttrChoice(self, ens:str, ename:NMTOKEN_t, ans:str, aname:NMTOKEN_t) -> None:
        """Specify a place to find ID attrs, as (elementName, attributeName).
        Set via schema, or directly via API. For just "id", use:
            idh.addAttrChoice("##any", "*", "##any", "id")
        Supports "##any" and "*".

        If valgen is set, the Node will be passed to it, and a non-None return
        is treated as the ID value for that node. This enables extensions
        such as accumulated IDs, foreign-key-like IDs, XPaths, XPointers, etc.
        """
        if not ens: ens = RWord.NS_ANY
        if not ename: ename = RWord.EL_ANY
        if not ans: ans = RWord.NS_ANY
        if not aname: raise KeyError("No attribute name specified.")
        ac = AttrChoice(ens, ename, ans, aname, None)
        self.attrChoices.append(ac)

    def delAttrChoice(self, ens:str, ename:NMTOKEN_t, ans:str, aname:NMTOKEN_t) -> None:
        ac = AttrChoice(ens, ename, ans, aname, None)
        try:
            x = self.attrChoices.index(ac)
            del self.attrChoices[x]
        except KeyError as e:
            raise KeyError(f"AttrChoice not found: {ac}.") from e

    def getIdAttrNode(self, elem:'Node') -> 'Attr':
        """TODO: In theory, we needn't stop at just one match....
        """
        if not elem.isElement:
            raise HReqE("Looking for ID on non-Element.")
        if not elem.hasAttributes:
            return None
        for tup in self.attrChoices:
            if tup.ens != RWord.NS_ANY:
                if tup.ens != elem.namespaceURI: continue
            if tup.ename != RWord.EL_ANY:
                if tup.ename != elem.nodeName: continue
            anode = elem.getAttributeNodeNS(tup.ans, tup.aname)
            if anode: return anode
        return None

    def buildIdIndex(self) -> Dict:
        """Build an index of all IDs.
        TODO: Update on changing an ID attribute.
        """
        self.theIndex = {}
        print("\nScanning for ids")
        for node in self.ownerDocument.documentElement.eachNode(excludeNodeNames="#"):
            print(node.startTag)
            anode = self.getIdAttrNode(node)
            if not anode: continue
            print(f'    ID: {anode.name}="{anode.value}"')
            if self.valgen: val = self.valgen(anode)
            else: val = anode.value
            self.theIndex[val] = anode

        print("\n####### IDs found: %s." % (", ".join(self.theIndex.keys())))
        return self.theIndex

    def clearIndex(self) -> None:
        self.theIndex = {}


    def getIndexedId(self, idval:str) -> 'Element':
        if idval in self.theIndex: return self.theIndex[idval]
        return None
