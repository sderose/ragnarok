#!/usr/bin/env python3
#
import re
from html.entities import name2codepoint  #, codepoint2name
from typing import Union, Dict
class XMLStrings:
    """Provides (mostly static) methods used for XML serialization.
    Note: There are escapeXXX() methods for most nodeTypes, but XML itself
    does not define how (for example) to escape "--" inside a comment.
    We do something simple that's guaranteed to make it not throw a WF error.
    """
    XMLEntities = {
         '&quo;'  : '"',
         '&apos;' : "'",
         '&lt;'   : '<',
         '&gt;'   : '>',
         '&amp;'  : '&',
    }

    escMap = {
        '"'       : '&quo;',
        "'"       : '&apos;',
        '<'       : '&lt;',
        '>'       : '&gt;',
        '?>'      : '?&gt;',
        '--'      : '- -',
        ']]>'     : '&rsqb;]>',
        '&'       : '&amp;',
    }

    @staticmethod
    def _escaper(mat):
        return XMLStrings.escMap[mat.group(1)]

    @staticmethod
    def escapeAttribute(s:str) -> str:
        return re.sub(r'(["<&])', XMLStrings._escaper, s)

    @staticmethod
    def escapeText(s:str) -> str:
        return re.sub(r'(<|&|]]>)', XMLStrings._escaper, s)

    @staticmethod
    def escapeCDATA(s:str) -> str:
        return re.sub(r'(]]>)', XMLStrings._escaper, s)

    @staticmethod
    def escapePI(s:str) -> str:
        return re.sub(r'(\?>)', XMLStrings._escaper, s)

    @staticmethod
    def escapeComment(s:str) -> str:
        return re.sub(r'(--)', XMLStrings._escaper, s)

    @staticmethod
    def normalizeSpace(s:str, unicode:bool=False) -> str:
        s = re.sub(r"\s+" ," ", s, flags=re.UNICODE if unicode else 0)
        s = re.sub(r"^ ", "", s)
        s = re.sub(r" $", "", s)
        return(s)

    @staticmethod
    def unescapeXml(s:str) -> str:
        return re.sub(r"&(#[xX])?(\w+);", XMLStrings.unescapeXmlFunction, s)

    @staticmethod
    def unescapeXmlFunction(mat) -> str:
        """
        Convert HTML entities, and numeric character references, to literal chars.
        """
        if (len(mat.group(1)) == 2):
            return chr(int(mat.group[2], 16))
        elif (mat.group(1)):
            return chr(int(mat.group[2], 10))
        elif (mat.group(2) in name2codepoint):
            return name2codepoint[mat.group(2)]
        else:
            raise ValueError("Unrecognized entity: '%s'." % (mat.group(0)))

    @staticmethod
    def makeStartTag(gi:str, attrs:Union[str, Dict]="", empty:bool=False) -> str:
        tag = "<" + gi
        if (attrs):
            if (isinstance(attrs, str)):
                tag += " " + attrs.strip()
            else:
                tag += XMLStrings.dictToAttrs(attrs, sortAttributes=True)
        tag += "/>" if empty else ">"
        return tag

    @staticmethod
    def dictToAttrs(dct, sortAttributes: bool=None, normValues: bool=False) -> str:
        """Turn a dict into a serialized attribute list (possibly sorted
        and/or space-normalized). Escape as needed.
        """
        sep = " "
        anames = dct.keys()
        if (sortAttributes): anames.sort()
        attrString = ""
        for a in (anames):
            v = dct[a]
            if (normValues): v = XMLStrings.normalizeSpace(v)
            attrString += "%s%s=\"%s\"" % (sep, a, XMLStrings.escapeAttribute(v))
        return attrString


    @staticmethod
    def makeEndTag(node:'Node') -> str:
        return "</%s>" % (node.nodeName)

    @staticmethod
    def getLocalPart(s:str) -> str:
        if (not s): return ""
        return re.sub(r'^.*:', '', s)

    @staticmethod
    def getNSPart(s:str) -> str:
        if (not s): return ""
        return re.sub(r':.*$', '', s)
