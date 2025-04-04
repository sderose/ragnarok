#!/usr/bin/env python3
#
# Loki: Parser extensions beyond XML.
#
#pylint: disable=W1201
#
from typing import Dict
#from types import SimpleNamespace
import logging

#from runeheim import CaseHandler, UNormHandler, WSHandler, Normalizer
from xsparser import XSParser, XSPOptions, XSDDatatypes

lg = logging.getLogger("loki")

__metadata__ = {
    "title"        : "Loki",
    "description"  : "An XML-like with extended syntax.",
    "rightsHolder" : "Steven J. DeRose",
    "creator"      : "http://viaf.org/viaf/50334488",
    "type"         : "http://purl.org/dc/dcmitype/Software",
    "language"     : "Python 3.11",
    "created"      : "2011-03-11",
    "modified"     : "2025-04-01",
    "publisher"    : "http://github.com/sderose",
    "license"      : "https://creativecommons.org/licenses/by-sa/3.0/"
}
__version__ = __metadata__['modified']


###############################################################################
#
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
    def __init__(self, options:Dict=None):
        super().__init__()
        for k, v in self.getLokiDefaults().items():
            assert not hasattr(self, k)
            setattr(self, k, v)
        self.utgard = True

        if options:
            for k, v in options.items():
                self.setOption(k, v)

    def getLokiDefaults(self) -> Dict:
        """NOTE: These defaults must all be falsish (False, "", 0, None),
        because xsparser.XSPOptions returns None if it tries to dereference
        an option it hasn't heard of.
        """
        #NM = Union[ CaseHandler, UNormHandler, WSHandler, Normalizer ]
        dfts = {
            ### Case and Unicode
            "elementFold"     : None,
            "attrFold"        : None,   # (attribute NAMEs)
            "entityFold"      : None,
            "idFold"          : None,   # (for ID, IDREF, coID, etc)
            "xsdFold"         : None,   # (for true, false, inf, nan, etc) TODO
            "keywordFold"     : None,   # (for ATTLIST, SYSTEM, CDATA, etc)

            "uNormHandler"    : None,   # ??? Unicode normalization       TODO
            "wsDef"           : None,   # (XML default)                   TODO

            ### Schemas
            "fragComments"    : False,  # In-dcl like SGML
            #"setDcls"        : False,  # <!ENTITY % x SET (i b tt)>      TODO
            "schemaType"      : False,  # <!DOCTYPE foo SYSTEM "" NDATA XSD>

            ### Elements
            "groupDcl"        : False,  # <!ELEMENT (x|y|z)...>
            "oflag"           : False,  # <!ELEMENT - O para...>
            "sgmlWord"        : False,  # CDATA RCDATA #CURRENT etc.
            "mixel"           : False,  # Dcl content ANYELEMENT          TODO
            "mixins"          : False,  # cf incl exceptions
            "repBrace"        : False,  # {min,max} for repetition

            "emptyEnd"        : False,  # </>
            "omitEnd"         : False,  # May omit end-tags before another
            "omitAtEOF"       : False,  # May omit end-tags at EOF
            "restart"         : False,  # <|> to close & reopen current element
            "endTagID"        : False,  # Permit ID on end-tag            TODO
            "levelCount"      : False,  # Enable Schemera nest/rank       TODO ???

            ### Beyond hierarchy
            "multiTag"        : False,  # <div/title>...</title/div>      TODO
            "simultaneous"    : False,  # <b|i> </i|/b>
            "suspend"         : False,  # <x>...<-x>...<+x>...</x>
            "olist"           : False,  # olist not stack
            "suspendDcl"      : False,  # <!ELEMENT ... SUSPENDABLE>      TODO
            "olistDcl"        : False,  # <!ELEMENT ... OLISTABLE>        TODO
            "trojanDcl"       : False,  # <!ATTLIST q s TROJAN_START etc. TODO,
            # BEG SUS RES END ?

            ### Attributes
            "globalAttr"      : False,  # <!ATTLIST * ...>
            "anyAttr"         : False,  # <!ATTLIST foo #ANY CDATA #IMPLIED>
            "xsdType"         : False,  # XSD builtins for attr types
            "xsdPlural"       : False,  # XSD types + plurals             TODO
            "specialFloat"    : False,  # Nan Inf etc. (needed?)
            "unQuotedAttr"    : False,  # <p x=foo>
            "curlyQuote"      : False,
            "booleanAttr"     : False,  # <x +border -foo>
            "bangAttr"        : False,  # != on first use to set dft
            "bangAttrType"    : False,  # !typ= to set datatype           TODO

            ### IDs
            "idNameSpaces"    : False,  # Allow ns prefixes on ID values, TODO
            "coID"            : False,  # co-index Trojans                TODO
            "nsID"            : False,  # IDs can have ns prefix          TODO
            "stackID"         : False,  # ID is cat(anc:@id)              TODO

            ### Entities and special characters
            "htmlNames"       : False,  # Enable HtML/Annex D named char refs
            "unicodeNames"    : False,  # Enable Raku-like unicode entities
            "multiPath"       : False,  # Multiple SYSTEM IDs
            "multiSDATA"      : False,  # <!SDATA nbsp 160 z 0x9D>        TODO
            "backslash"       : False,  # \n \xff \uffff (not yet \\x{}

            ### Other
            "expatBreaks"     : False,  # Break at \n and entities like expat
            "emComments"      : False,  # emdash as -- for comments
            "poundComments"   : False,  #
            "piEscapes"       : False,  # Recognize char refs in PIs      TODO
            "piAttr"          : False,  # PI parsed like attributes.
            "piAttrDcl"       : False,  # <!ATTLIST ?target ...>          TODO
            "MSTypes"         : False,  # Allow other than CDATA?
        }
        for k, v in dfts.items():
            if v: raise SyntaxError(f"Bad Loki default for option {k}={v}.")
        return dfts


###############################################################################
#
def ParserCreate(
    encoding="utf-8",
    namespace_separator=None  # Leaves xmlns as attrs, and prefixes as-is.
    ) -> 'XSParser':
    return Loki(encoding=encoding, namespace_separator=namespace_separator)


class Loki(XSParser):
    def __init__(self,
        encoding:str="utf-8",
        namespace_separator:str=None,
        options:Dict=None):
        super().__init__(encoding, namespace_separator)
        self.options.addLokiOptions(options)
        if self.options.xsdType: self.attrTypes = XSDDatatypes
        self.bangAttrs:dict = {}
        self.utgard = True
        lg.warning("utgard/Loki set up.")
