#!/usr/bin/env python3
#
import sys
import logging

#from xml.parsers import expat

#from schemera import EntityDef, EntitySpace, EntityParsing
#import thor
#from runeheim import CaseHandler
#from saxplayer import SaxEvent

from thor import StackReader  #, EntityFrame, XSParser
import dombuilder
import basedom

lg = logging.getLogger("parseStdin")
logging.basicConfig(level=logging.INFO)

options = {
    ### Size limits and security (these are XML compatible)
    "MAXEXPANSION"    : 1<<20,  # Limit expansion length of entities
    "MAXENTITYDEPTH"  : 1000,   # Limit nesting of entities
    "charEntities"    : True,   # Allow SDATA and CDATA entities
    "extEntities"     : True,   # External entity refs?
    "netEntities"     : True,   # Off-localhost entity refs?
    "entityDirs"      : [],     # Permitted dirs to get ents from

    ### Case and Unicode
    "elementFold"     : None,
    "attrFold"        : None,   # (attribute NAMEs)
    "entityFold"      : None,
    "keywordFold"     : None,
    "uNormHandler"    : None,   #                                 UNFIN
    "wsDef"           : None,   # (XML default)                   UNFIN
    "radix"           : ".",    # Decimal point choice            UNFIN
    "noC1"            : False,  # No C1 controls                  UNFIN

    ### Schemas
    "schemaType"      : "DTD",  # <!DOCTYPE foo SYSTEM "" NDATA XSD>
    "fragComments"    : False,  # In-dcl like SGML
    #"setDcls"        : False,  # <!ENTITY % x SET (i b tt)>      UNFIN

    ### Elements
    "groupDcl"        : False,  # <!ELEMENT (x|y|z)...>
    "oflag"           : False,  # <!ELEMENT - O para...>
    "sgmlWord"        : False,  # CDATA RCDATA #CURRENT etc.
    "mixel"           : False,  # Dcl content ANYELEMENT          UNFIN
    "mixins"          : False,  # cf incl exceptions
    "repBrace"        : False,  # {min max} for repetition
    "emptyEnd"        : False,  # </>
    "restart"         : False,  # <|> to close & reopen current element
    "simultaneous"    : False,  # <b|i> </i|/b>
    "multiTag"        : False,  # <div/title>...</title/div>      UNFIN
    "suspend"         : False,  # <x>...<-x>...<+x>...</x>
    "olist"           : False,  # olist not stack

    ### Attributes
    "globalAttr"      : False,  # <!ATTLIST * ...>
    "anyAttr"         : False,  # <!ATTLIST foo #ANY CDATA #IMPLIED>
    "undeclaredAttrs" : False,  #                                 UNFIN
    "xsdType"         : False,  # XSD builtins for attr types
    "xsdPlural"       : False,  # XSD types + plurals             UNFIN
    "specialFloat"    : False,  # Nan Inf etc. (needed?)
    "unQuotedAttr"    : False,  # <p x=foo>
    "curlyQuote"      : False,
    "booleanAttr"     : False,  # <x +border -foo>
    "bangAttr"        : False,  # != on first use to set dft
    "bangAttrType"    : False,  # !typ= to set datatype           UNFIN
    "coID"            : False,  # co-index Trojans                UNFIN
    "nsID"            : False,  # IDs can have ns prefix          UNFIN
    "stackID"         : False,  # ID is cat(anc:@id)              UNFIN

    ### Validation (beyond WF!)
    "valElementNames" : False,  # Must be declared
    "valModels"       : False,  # Child sequences                 UNFIN
    "valAttrNames"    : False,  # Must be declared
    "valAttrTypes"    : False,  # Must match datatype

    ### Entities and special characters
    "htmlNames"       : False,  # Enable HtML/Annex D named char refs
    "unicodeNames"    : False,  # Enable Raku-like unicode entities
    "multiPath"       : False,  # Multiple SYSTEM IDs
    "multiSDATA"      : False,  # <!SDATA nbsp 160 z 0x9D>        UNFIN
    "backslash"       : False,  # \n \xff \uffff (not yet \\x{}

    ### Other
    "expatBreaks"     : False,  # Break at \n and entities like expat
    "emComments"      : False,  # emdash as -- for comments       UNFIN
    "piAttr"          : False,  # PI parsed like attributes.      UNFIN
    "piAttrDcl"       : False,  # <!ATTLIST ?target ...>          UNFIN
    "nsSep"           : ":",    #                                 UNFIN
    "nsUsage"         : None,   # one/global/noredef/regular      UNFIN
    "MSTypes"         : False,  # Allow other than CDATA?
}

sr = StackReader(options=options)
di = basedom.getDOMImplementation()
db = dombuilder.DomBuilder(parserClass=sr, domImpl=di)

xml = sys.stdin.read()
doc1 = db.parse_string(xml)
assert isinstance(doc1, basedom.Document)

print(doc1.toprettyxml())
