#!/usr/bin/env python3
#
from collections import namedtuple, defaultdict
from typing import Dict, List

#from xml.dom import minidom
import basedom

descr = """
Check all the (XML) DOM methods, and whether they're defined, inherited, or
absent on each Node (sub)class.

    "Node",
        "Document",
        "Element",
        "Attr",
        "CharacterData",
            "Text", "Comment", "ProcessingInstruction", "CDATASection",
    #
    # Additional classes included in basedom AND minidom:
    #   DocumentFragment, DocumentType, DOMImplementation,
    #   Entity, NamedNodeMap, NodeList, Notation
    #
    # Additional classes only included in basedom:
    #   EntityReference, DOMTokenList, NameSpaces, XmlStrings,
    #   Enums: UNormTx, CaseTx, WSDefs, NameTx,
    #     BaseTypes, AttrTypes, AttrDefaults, EntityType, EntitySource,
    #     EntityParseType, ModelTypes, NodeTypes, SaxEvents
    #
    # Additional classes included in minidom:
    #   AttributeList(NamedNodeMap)
    #   Childless -- seems to just be to kill some methods.
    #   DOMImplementationLS: createDomBuilder, createDOMInputSource, createDOMWriter
    #   DocumentLS: abort, async_, load, loadXML, saveXML
    #   ElementInfo: getAttributeType, getAttributeTypeNS,
    #     isElementContent, isEmpty, isId, isIdNS, tagName
    #   EmptyNodeList: count, index, item, length
    #   Identified :publicId, systemId
    #   ReadOnlySequentialNamedNodeMap
    #   StringTypes: count, index
    #   TypeInfo: name, namespace
"""

classNames = [
    "Node",
    "Element",
    "Attr",
    "CharacterData",
    "Text",
    "Comment",
    "ProcessingInstruction",
    "Document"
]
bcFields = [ "name", *classNames ]
byClass = namedtuple("byClass", bcFields)
BC = byClass

# Legend:
#    + : Property/method is available and meaningful for this class
#    ~ : Property/method exists but may not be meaningful or is abstract
#    - : Property/method is not available for this class
#    ! : Property/method is available but likely overrides or
#        significantly modifies behavior from its parent class
#
NIL = "NIL"
NEW = "NEW"
INH = "INHERIT"
OVR = "OVERRIDE"
HID = "HIDDEN"
ABS = "ABSTRACT"

statuses = [ NIL, NEW, INH, OVR, HID, ABS ]



itemIndex = [
    # Property/Method     Node   Element     Attr      Ch  Text Comment         PI   Doc

    # Instance Variables
    BC( "nodeType",            NEW, INH,       INH,    INH,  INH,    INH,       INH,  INH   ),
    BC( "nodeName",            NEW, OVR,       OVR,    OVR,  OVR,    OVR,       OVR,  OVR   ),
    BC( "nodeValue",           NIL, NIL,       OVR,    OVR,  OVR,    OVR,       OVR,  NIL   ),
    BC( "namespaceURI",        NIL, OVR,       OVR,    NIL,  NIL,    NIL,       NIL,  OVR   ),
    BC( "prefix",              NIL, OVR,       OVR,    NIL,  NIL,    NIL,       NIL,  OVR   ),
    BC( "localName",           NIL, OVR,       OVR,    NIL,  NIL,    NIL,       NIL,  NIL   ),
    BC( "ownerDocument",       NEW, INH,       INH,    INH,  INH,    INH,       INH,  OVR   ),
    BC( "parentNode",          NEW, INH,       OVR,    INH,  INH,    INH,       INH,  NIL   ),
    BC( "childNodes",          NEW, INH,       NIL,    INH,  NIL,    NIL,       NIL,  INH   ),
    BC( "firstChild",          NEW, INH,       NIL,    INH,  NIL,    NIL,       NIL,  INH   ),
    BC( "lastChild",           NEW, INH,       NIL,    INH,  NIL,    NIL,       NIL,  INH   ),
    BC( "previousSibling",     NEW, INH,       NIL,    INH,  INH,    INH,       INH,  NIL   ),
    BC( "nextSibling",         NEW, INH,       NIL,    INH,  INH,    INH,       INH,  NIL   ),
    BC( "attributes",          NIL, INH,       NIL,    NIL,  NIL,    NIL,       NIL,  NIL   ),
    BC( "textContent",         NEW, OVR,       OVR,    OVR,  OVR,    OVR,       OVR,  OVR   ),
    BC( "data",                NIL, NIL,       NIL,    INH,  OVR,    OVR,       INH,  NIL   ),
    BC( "length",              NIL, NIL,       NIL,    INH,  OVR,    OVR,       INH,  NIL   ),
    BC( "documentElement",     NIL, NIL,       NIL,    NIL,  NIL,    NIL,       NIL,  INH   ),
    BC( "doctype",             NIL, NIL,       NIL,    NIL,  NIL,    NIL,       NIL,  INH   ),
    BC( "implementation",      NIL, NIL,       NIL,    NIL,  NIL,    NIL,       NIL,  INH   ),
    BC( "URL",                 NIL, NIL,       NIL,    NIL,  NIL,    NIL,       NIL,  INH   ),
    BC( "documentURI",         NIL, NIL,       NIL,    NIL,  NIL,    NIL,       NIL,  INH   ),
    BC( "characterSet",        NIL, NIL,       NIL,    NIL,  NIL,    NIL,       NIL,  INH   ),
    BC( "wholeText",           NIL, NIL,       NIL,    NIL,  INH,    NIL,       NIL,  NIL   ),

    # Constructors
    BC( "createElement",       NIL, NIL,       NIL,    NIL,  NIL,    NIL,       NIL,  INH   ),
    BC( "createElementNS",     NIL, NIL,       NIL,    NIL,  NIL,    NIL,       NIL,  INH   ),
    BC( "createTextNode",      NIL, NIL,       NIL,    NIL,  NIL,    NIL,       NIL,  INH   ),
    BC( "createComment",       NIL, NIL,       NIL,    NIL,  NIL,    NIL,       NIL,  INH   ),
    BC( "createProcessingInstruction",
                               NIL, NIL,       NIL,    NIL,  NIL,    NIL,       NIL,  INH   ),
    BC( "createAttribute",     NIL, NIL,       NIL,    NIL,  NIL,    NIL,       NIL,  INH   ),
    BC( "createAttributeNS",   NIL, NIL,       NIL,    NIL,  NIL,    NIL,       NIL,  INH   ),
    BC( "createDocumentFragment",
                               NIL, NIL,       NIL,    NIL,  NIL,    NIL,       NIL,  INH   ),
    BC( "createCDATASection",  NIL, NIL,       NIL,    NIL,  NIL,    NIL,       NIL,  INH   ),

    # Predicates
    BC( "hasChildNodes",       NEW, INH,       NIL,    INH,  NIL,    NIL,       NIL,  INH   ),
    BC( "isEqualNode",         NEW, OVR,       OVR,    OVR,  OVR,    OVR,       OVR,  OVR   ),
    BC( "isSameNode",          NEW, INH,       INH,    INH,  INH,    INH,       INH,  INH   ),
    BC( "isConnected",         NEW, INH,       INH,    INH,  INH,    INH,       INH,  INH   ),
    BC( "contains",            NEW, INH,       NIL,    INH,  NIL,    NIL,       NIL,  INH   ),
    BC( "matches",             NIL, INH,       NIL,    NIL,  NIL,    NIL,       NIL,  NIL   ),

    # Tree Navigators/Searchers
    BC( "getElementsByClassName",
                               NIL, INH,       NIL,    NIL,  NIL,    NIL,       NIL,  INH   ),
    BC( "getElementsByTagName",
                               NIL, INH,       NIL,    NIL,  NIL,    NIL,       NIL,  INH   ),
    BC( "closest",             NIL, INH,       NIL,    NIL,  NIL,    NIL,       NIL,  NIL   ),
    BC( "getRootNode",         NEW, INH,       INH,    INH,  INH,    INH,       INH,  OVR   ),

    # Tree Mutators
    BC( "appendChild",         NEW, OVR,       NIL,    OVR,  NIL,    NIL,       NIL,  OVR   ),
    BC( "removeChild",         NEW, OVR,       NIL,    OVR,  NIL,    NIL,       NIL,  OVR   ),
    BC( "replaceChild",        NEW, OVR,       NIL,    OVR,  NIL,    NIL,       NIL,  OVR   ),
    BC( "insertBefore",        NEW, OVR,       NIL,    OVR,  NIL,    NIL,       NIL,  OVR   ),
    BC( "cloneNode",           NEW, OVR,       OVR,    OVR,  OVR,    OVR,       OVR,  OVR   ),
    BC( "normalize",           NEW, OVR,       NIL,    INH,  NIL,    NIL,       NIL,  OVR   ),
    BC( "prepend",             NIL, INH,       NIL,    NIL,  NIL,    NIL,       NIL,  INH   ),
    BC( "append",              NIL, INH,       NIL,    NIL,  NIL,    NIL,       NIL,  INH   ),
    BC( "before",              NIL, INH,       NIL,    INH,  INH,    INH,       INH,  NIL   ),
    BC( "after",               NIL, INH,       NIL,    INH,  INH,    INH,       INH,  NIL   ),
    BC( "replaceWith",         NIL, INH,       NIL,    INH,  INH,    INH,       INH,  NIL   ),
    BC( "remove",              NIL, INH,       NIL,    INH,  INH,    INH,       INH,  NIL   ),
    BC( "insertAdjacentElement",
                               NIL, INH,       NIL,    NIL,  NIL,    NIL,       NIL,  NIL   ),
    BC( "insertAdjacentText",  NIL, INH,       NIL,    NIL,  NIL,    NIL,       NIL,  NIL   ),
    BC( "insertAdjacentHTML",  NIL, INH,       NIL,    NIL,  NIL,    NIL,       NIL,  NIL   ),

    # Other Methods
    BC( "compareDocumentPosition",
                               NEW, INH,       INH,    INH,  INH,    INH,       INH,  INH   ),
    BC( "lookupPrefix",        NEW, OVR,       OVR,    INH,  INH,    INH,       INH,  OVR   ),
    BC( "lookupNamespaceURI",  NEW, OVR,       OVR,    INH,  INH,    INH,       INH,  OVR   ),
    BC( "isDefaultNamespace",  NEW, OVR,       OVR,    INH,  INH,    INH,       INH,  OVR   ),
    BC( "importNode",          NIL, NIL,       NIL,    NIL,  NIL,    NIL,       NIL,  INH   ),
    BC( "adoptNode",           NIL, NIL,       NIL,    NIL,  NIL,    NIL,       NIL,  INH   ),
    BC( "appendData",          NIL, NIL,       NIL,    INH,  INH,    INH,       INH,  NIL   ),
    BC( "insertData",          NIL, NIL,       NIL,    INH,  INH,    INH,       INH,  NIL   ),
    BC( "deleteData",          NIL, NIL,       NIL,    INH,  INH,    INH,       INH,  NIL   ),
    BC( "replaceData",         NIL, NIL,       NIL,    INH,  INH,    INH,       INH,  NIL   ),
    BC( "substringData",       NIL, NIL,       NIL,    INH,  INH,    INH,       INH,  NIL   ),
    BC( "splitText",           NIL, NIL,       NIL,    NIL,  INH,    NIL,       NIL,  NIL   ),
]

# HTML only
itemIndexHTML = [
    BC( "assignedSlot",        NIL, INH,       NIL,    INH,  INH,    INH,       NIL,  NIL   ),
    BC( "baseURI",             NEW, OVR,       INH,    INH,  INH,    INH,       INH,  OVR   ),
    BC( "compatMode",          NIL, NIL,       NIL,    NIL,  NIL,    NIL,       NIL,  INH   ),
    BC( "contentType",         NIL, NIL,       NIL,    NIL,  NIL,    NIL,       NIL,  INH   ),
    BC( "createEvent",         NIL, NIL,       NIL,    NIL,  NIL,    NIL,       NIL,  INH   ),
    BC( "createNodeIterator",  NIL, NIL,       NIL,    NIL,  NIL,    NIL,       NIL,  INH   ),
    BC( "createTreeWalker",    NIL, NIL,       NIL,    NIL,  NIL,    NIL,       NIL,  INH   ),
    BC( "innerHTML",           NIL, INH,       NIL,    NIL,  NIL,    NIL,       NIL,  NIL   ),
    BC( "outerHTML",           NIL, INH,       NIL,    NIL,  NIL,    NIL,       NIL,  NIL   ),
    BC( "innerText",           NIL, INH,       NIL,    NIL,  NIL,    NIL,       NIL,  NIL   ),  # ??
    BC( "origin",              NIL, NIL,       NIL,    NIL,  NIL,    NIL,       NIL,  INH   ),
    #BC( "style" ),
    #BC( "className" ),
    #BC( "addEventListener" ),
    #BC( "removeEventListener" ),
    BC( "querySelector",       NIL, INH,       NIL,    NIL,  NIL,    NIL,       NIL,  INH   ),
    BC( "querySelectorAll",    NIL, INH,       NIL,    NIL,  NIL,    NIL,       NIL,  INH   ),
    #BC( "dataset" ),
]

def is_hidden(method):
    #assert callable(method)
    return getattr(method, '__is_hidden__', False)

def categorize(classObj, itemName:str, miWarn:bool=False) -> (str, List[type]):
    """Figure out who defines the method, and return a flag for whether it is:
        NIL = "NIL"         -- not available at all
        NEW = "NEW"         -- new, not on superclass(es)
        INH = "INHERITED"   -- not local, just inherited
        OVR = "OVERRIDDEN"  -- local override of inherited method
        HID = "HIDDEN"      -- local overridden in order to remove (this
            required using the "@hidden" decorator on the definition).
        ABS = "ABSTRACT"    -- defined but abstract, signalled by Python's
            "@abstractmethod" decorator (not yet detected here)
    """
    definedHere = itemName in classObj.__dict__  # dir() would also get inherited ones
    hidBit = False
    if definedHere:
        theMethod = getattr(classObj, itemName)
        hidBit = is_hidden(theMethod)

    definedAnc = False
    whoDefined = []
    par = classObj.__bases__
    while (par):
        # All your base are belong to us.
        if (miWarn and len(par) > 1):
            print("        Multiple inheritance, from %s" % ([ x.__name__ for x in par ]))
        base = par[-1]
        if itemName in base.__dict__:
            definedAnc = True
            whoDefined.append(base)
        par = base.__bases__


    # No good way to test for HID, since you have to defined it to remove it.
    # Could define them all to forward to a reserved method that just raises exc?
    status = "???"
    if (hidBit):
        status = HID
    elif (definedAnc and not definedHere):
        status = INH
    elif (definedAnc and definedHere):
        status = OVR
    elif (not definedAnc and not definedHere):
        status = NIL
    elif (not definedAnc and definedHere):
        status = NEW
    return status, whoDefined

def getClassMap(module_name:str) -> Dict:
    cmap = []
    for cn in classNames:
        try:
            cmap.append( (cn, getattr(module_name, cn)) )
        except AttributeError:
            print(f"Can't find class {cn} in module {module_name}.")
    return cmap

def testAll():
    prob = ok = 1
    cmap = getClassMap(basedom)

    conflicts = defaultdict(int)
    for j, classInfo in enumerate(cmap):
        className = classInfo[0]
        classObj = classInfo[1]
        print(f"\n******* Class {className}")
        for _, row in enumerate(itemIndex):
            flag, _whence = categorize(classObj, row.name)
            expectedFlag = row[j+1]
            conflicts[(expectedFlag, flag)] += 1
            if (flag == expectedFlag):
                ok += 1
            else:
                print("    %-25s expected %-10s but got %s"
                    % (row.name+":", expectedFlag, flag))
                prob += 1

    print("\nCases %d, ok %d, problem %d (%5.2f%% ok).\n"
        % (ok+prob, ok, prob, 100.0*ok/(ok+prob)))

    print("\nExpected...got:")
    ss = sorted(statuses)
    head = " " * 15
    head += "".join([ ("%10s" % (x)) for x in ss ])
    print(head)
    for exp in ss:
        buf = "    %-10s " % (exp)
        for got in sorted(statuses):
            k = (exp, got)
            n = conflicts[k] if k in conflicts else 0
            buf += "%10s" % (n)
        print(buf)

testAll()
