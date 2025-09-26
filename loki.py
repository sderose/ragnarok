#!/usr/bin/env python3
#
# Loki: Parser extensions beyond XML.
#
#pylint: disable=W1201
#
from typing import Dict
import logging

from runeheim import CaseHandler, WSHandler, Normalizer  #, UNormHandler
from thor import XSParser, XSPOptions
from xsdtypes import XSDDatatypes

lg = logging.getLogger("loki")

__metadata__ = {
    "title"        : "Loki",
    "description"  : "An XML-like with extended syntax.",
    "rightsHolder" : "Steven J. DeRose",
    "creator"      : "http://viaf.org/viaf/50334488",
    "type"         : "http://purl.org/dc/dcmitype/Software",
    "language"     : "Python 3.11",
    "created"      : "2011-03-11",
    "modified"     : "2025-05-26",
    "publisher"    : "http://github.com/sderose",
    "license"      : "https://creativecommons.org/licenses/by-sa/3.0/"
}
__version__ = __metadata__['modified']


###############################################################################
# NOTE: These defaults must all be falsish (False, "", 0, None),
# because thor.XSPOptions returns None if it tries to dereference
# an option it hasn't heard of.
#
CASE = CaseHandler
NORM = Normalizer
WS = WSHandler

lokiDefaultOptions = {
    #NM = Union[ CaseHandler, UNormHandler, WSHandler, Normalizer ]
    ### Case and Unicode
    "elementFold"   : ( CASE, None  ),  # element names
    "entityFold"    : ( CASE, None  ),  # entity names
    "notationFold"  : ( CASE, None  ),  # notation names                    TODO
    "attributeFold" : ( CASE, None  ),  # attribute NAMEs
    "keywordFold"   : ( CASE, None  ),  # ATTLIST, SYSTEM, CDATA, etc.      TODO
    "idFold"        : ( CASE, None  ),  # ID, IDREFS, COID, etc.
    "xsdFold"       : ( CASE, None  ),  # true, false, inf, nan, etc.       TODO
    "uNormHandler"  : ( NORM, None  ),  # ??? Unicode normalization         TODO
    "wsDef"         : ( WS,   None  ),  # (XML default)                     TODO


    ### Schema-related stuff ##################################################

    # Element dcls
    "groupDcl"      : ( bool, False ),  # <!ELEMENT (x|y|z)...>
    "oflag"         : ( bool, False ),  # <!ELEMENT - O para...>
    "sgmlWord"      : ( bool, False ),  # CDATA RCDATA #CURRENT etc.
    "mixel"         : ( bool, False ),  # Declared content ANYELEMENT       TODO
    "mixin"         : ( bool, False ),  # cf incl exceptions
    "repBrace"      : ( bool, False ),  # {min,max} for repetition

    # Attributes and attribute dcls
    "globalAttribute" : ( bool, False ),  # <!ATTLIST * ...>
    "anyAttribute"  : ( bool, False ),  # <!ATTLIST foo #ANY CDATA #IMPLIED>
    "xsdType"       : ( bool, False ),  # XSD builtins for attribute types
    "xsdPlural"     : ( bool, False ),  # XSD types + plurals               TODO

    # Comments
    "fragComment"   : ( bool, False ),  # In-dcl like SGML

    # Entities
    "htmlNames"     : ( bool, False ),  # Enable HtML/Annex D named char refs
    "unicodeNames"  : ( bool, False ),  # Unicode name references
    "multiSDATA"    : ( bool, False ),  # <!SDATA nbsp 160 z 0x9D>          TODO
    "schemaType"    : ( bool, False ),  # <!DOCTYPE foo SYSTEM "" NDATA XSD>

    # May also affect Yggdrasil
    "multiPath"     : ( bool, False ),  # Multiple SYSTEM IDs
    "setDcl"        : ( bool, False ),  # <!ENTITY % x SET (i b tt)>        TODO
    "entEncoding"   : ( bool, False ),  # <!ENTITY c SYSTEM "c" ENCODING e> TODO


    ### Yggdrasil/Dominus stuff ###############################################

    # PIs
    "piAttribute"   : ( bool, False ),  # PI parsed like attributes.
    "piAttlist"     : ( bool, False ),  # <!ATTLIST ?target ...>            TODO

    # Beyond hierarchy
    "multiTag"      : ( bool, False ),  # <div/title>...</title/div>        TODO
    "simultaneous"  : ( bool, False ),  # <b|i> </i|/b>
    "suspend"       : ( bool, False ),  # <x>...<-x>...<+x>...</x>
    "olist"         : ( bool, False ),  # olist not stack
    "suspendDcl"    : ( bool, False ),  # <!ELEMENT ... SUSPENDABLE>        TODO
    "olistDcl"      : ( bool, False ),  # <!ELEMENT ... OLISTABLE>          TODO
    "trojanDcl"     : ( bool, False ),  # <!ATTLIST q s TROJAN_START...     TODO
    # TODO Drop trojanDcl and infer from attribute type? Finer-grained types?
    "unordered"     : ( bool, False ),  # <{bibentry}>...</{bibentry>       TODO


    ### Loki stuff ############################################################

    # Shorttag-ish stuff
    "emptyEnd"      : ( bool, False ),  # </>
    "omitEnd"       : ( bool, False ),  # May omit end-tags before another
    "omitAtEOF"     : ( bool, False ),  # May omit end-tags at EOF
    "restart"       : ( bool, False ),  # <|> to close & reopen current element
    "restartName"   : ( bool, False ),  # <|name>
    "endTagId"      : ( bool, False ),  # Permit ID on end-tag              TODO
    "levelCount"    : ( bool, False ),  # Enable Schemera nest/rank         TODO ???
    "qgi"           : ( bool, False ),  # Ancestor types in tags            TODO
    "elementAbbr"   : ( bool, False ),  # Abbreviate element names          TODO
    "lineTag"       : ( bool, False ),  # Way to auto-tag lines (poetry, code,...) TODO

    # Attributes
    "unQuotedAttribute" : ( bool, False ),  # <p x=foo>
    "curlyQuote"        : ( bool, False ),
    "noAttributeNorm"   : ( bool, False ),  # Suppress ws norm for undcl attrs TODO
    "booleanAttribute"  : ( bool, False ),  # <x +border -foo>
    "booleanIsName"     : ( bool, False ),  # +x attr -->  x="x", not x="1"
    "attributeAbbr"     : ( bool, False ),  # Abbreviate attr names         TODO

    # Attribute defaulting (also affect Schemera)
    "bangAttribute"     : ( bool, False ),  # != on first use to set dft
    "bangAttributeType" : ( bool, False ),  # !typ= to set datatype         TODO

    # Content, escaping, breaking
    "backslash"     : ( bool, False ),  # \n \xff \uffff (not yet \\x{}
    "piEscape"      : ( bool, False ),  # Recognize char refs in PIs    TODO
    "expatBreaks"   : ( bool, False ),  # Break at \n and entities like expat

    # Marked Sections
    "MSType"        : ( bool, False ),  # Allow other than CDATA? Case?

    # Comments
    "emComment"     : ( bool, False ),  # emdash as -- for comments
    "poundComment"  : ( bool, False ),  # "#" as "--"                       TODO
    "nestComment"   : ( bool, False ),  # <!-- foo <!-- bar --> baz -->     TODO

    # XML dcl
    "extraDcl"      : ( bool, False ),  # Allow entity ref to complete docs TODO


    ### ID subtypes (all caps b/c they're essentially entity types ############
    "IDSuffix"      : ( bool, False ),  # <p#someId>                        TODO
    "NAMESPACEID"   : ( bool, False ),  # NS prefixes on ID values          TODO
    "STACKID"       : ( bool, False ),  # value is '/'.join(anc:@id)        TODO
    "TYPEID"        : ( bool, False ),  # value unique for element type     TODO
    "COMPOUNDID"    : ( bool, False ),  # value from evaluating an XPath    TODO
    "COID"          : ( bool, False ),  # co-index start and end milestones TODO
    "STARTID"       : ( bool, False ),  # Only on starts (like Trojan sId)  TODO
    "SUSPENDID"     : ( bool, False ),  # Only on suspends                  TODO
    "RESUMEID"      : ( bool, False ),  # Only on resumes                   TODO
    "ENDID"         : ( bool, False ),  # Only on ends (like Trojan eId)    TODO
    "BOUNDARYID"    : ( bool, False ),  # e.g., empty page-breaks           TODO


    ### Uhhhh...
    "specialFloat"  : ( bool, False ),  # Nan Inf etc. (needed?)
}

class LokiOptions(XSPOptions):
    """Keep track of parser extensions in use (if any).
    By default, this just adds options that do not touch XML syntax at all.
    For example, constraints on entity security, extra charset restrictions,
    tweaks to how SAX events are generated, etc.

    To get Loki extensions, explicitly call addLokiOptions().

    Shunt the deuterium from the main cryo-pump to the auxiliary tank.
    Er, the tank can't withstand that kind of pressure.
    Where'd you... where'd you get that idea?
    ...It's in the impulse engine specifications.
    Regulation 42/15 -- Pressure Variances on the IRC Tank Storage?
    Yeah.
    Forget it. I wrote it. Just... boost the flow. It'll work.
            -- ST:TNG "Relics"
    """
    for k, v in lokiDefaultOptions.items():
        if v[1]: raise SyntaxError(f"Non-falsish Loki default for option {k}={v}.")

    def __init__(self, options:Dict=None):
        super().__init__()
        self.utgard = True
        for k, v in LokiOptions.lokiDefaultOptions.items():
            if v[1] is not None and not isinstance(v[1], v[0]):
                raise SyntaxError(
                    f"Value '{v[1]}' for option '{k}' was type '{type(v[1])}',"
                    f"but should be None or type '{v[0]}'.")
            setattr(self, k, v)
        if options:
            for k, v in options.items():
                self.setOption(k, v)

    def asDict(self) -> Dict:
        theDict = {}
        for k in LokiOptions.lokiDefaultOptions.keys():
            theDict[k] = getattr(self, k)
        return theDict


###############################################################################
#
def ParserCreate(
    encoding="utf-8",
    namespace_separator=None  # Leaves xmlns as attributes, and prefixes as-is.
    ) -> 'XSParser':
    return Loki(encoding=encoding, namespace_separator=namespace_separator)


class Loki(XSParser):
    def __init__(self,
        encoding:str="utf-8",
        namespace_separator:str=None,
        options:Dict=None
        ):
        super().__init__(encoding, namespace_separator)
        #assert isinstance(self.options, (dict, None))
        self.utgard = True
        self.options = LokiOptions()
        if self.options.xsdType: self.attrTypes = XSDDatatypes
        self.bangAttributes:dict = {}

        lg.warning("utgard/Loki set up. Options (type %s):", type(self.options))
        for x in dir(self.options):
            if x.startswith("_"): continue
            val = getattr(self.options, x)
            lg.warning("    %-16s  %-12s  %s" % (x, type(val), val))
