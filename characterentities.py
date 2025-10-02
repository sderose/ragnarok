#!/usr/bin/env python3
#
# characterentities.py: Loadable character-name mappings for Ragnarok.
# 2024-09-09: Written by Steven J. DeRose.
#
import sys
import codecs
import logging
import re

from runeheim import XmlStrings as Rune

lg = logging.getLogger("addCharacterEntities.py")

__metadata__ = {
    "title"        : "characterentities",
    "description"  : "Loadable character-name mappings for Ragnarok.",
    "rightsHolder" : "Steven J. DeRose",
    "creator"      : "http://viaf.org/viaf/50334488",
    "type"         : "http://purl.org/dc/dcmitype/Software",
    "language"     : "Python 3.11",
    "created"      : "2024-09-09",
    "modified"     : "2024-09-09",
    "publisher"    : "http://github.com/sderose",
    "license"      : "https://creativecommons.org/licenses/by-sa/3.0/"
}
__version__ = __metadata__["modified"]

descr = """See docs/characterentities.md
"""

class CharacterEntities:
    """Maintain a union list of special character/name mappings.
    Note: It is ok to map multiple names to the same code point, but only
    the first such will be chosen for codepoint2name.
    """
    def __init__(self, includeHTML:bool=True):
        self.codepoint2name = {}
        self.name2codepoint = {}
        if includeHTML: self.addHTML()

    def add(self, name:str, cp:int, force:bool=False) -> bool:
        assert isinstance(name, str) and isinstance(cp, int)
        if not Rune.isXmlName(name):
            raise KeyError("Char name is not an XML NAME: '%s'." % (name))
        if cp < 1 or cp > sys.maxunicode:
            raise ValueError("Code point for '%s' is out of range: %06x." % (name, cp))

        # codepoint2name can only have one entry per codepoint
        if force or cp not in self.codepoint2name:
            self.codepoint2name[cp] = name
        else:
            lg.warning("codepoint %04x already covered ('%s' vs. new '%s').",
                cp, self.codepoint2name[cp], name)

        # But name2codepoint allows multiple names to map to the same codepoint
        if force or name not in self.name2codepoint:
            self.name2codepoint[name] = cp
        elif cp == self.name2codepoint[name]:
            pass
        else:
            raise KeyError("Name '%s' already defined, points to %04x not new %04x."
                % (name, self.name2codepoint[name], cp))
        return True

    def delete(self, name:str, cp:int) -> None:
        """Remember there can be multiple names for the same code point.
        So if we delete one of them, codepoint2name may need to change to another.
        """
        if name in self.name2codepoint:
            del self.name2codepoint[name]
        if cp in self.codepoint2name and self.codepoint2name[cp] == name:
            # Check if there's at least some other name to fall back to.
            for candCp, candName in self.codepoint2name.items():
                if candCp == cp:
                    self.codepoint2name[cp] = candName
                    return
            del self.codepoint2name[cp]

    def addHTML(self) -> None:
        from html.entities import codepoint2name as HTMLc2n
        for cp, name in HTMLc2n.items():
            self.add(name, cp)

    def addFromPairFile(self, path:str) -> int:
        """File format:
            * Initial "#" (optional spaces before) is a comment.
            * Blank lines ignored.
            * Data lines are like: entName sep number
                * sep can be any non-word characters (comma, space, etc.)
                * number can be anything that int(s, 0) takes.
        """
        ifh = codecs.open(path, "rb", encoding="utf-8")
        nAdded = 0
        for recnum, rec in enumerate(ifh.readlines()):
            rec = rec.strip()
            if rec.startswith("#") or rec=="": continue
            mat = re.match(r"^([\w.-]+)\W+(0?x?[a-f\d]+)$", rec)
            if mat is None:
                raise ValueError("Cannot parse record %d: %s" % (recnum, rec))
            cp = int(mat.group(2), 0)
            self.add(mat.group(1), cp)
            nAdded += 1
        ifh.close()
        return nAdded

    def addFromDclFile(self, path:str) -> int:
        """File format (not full XML, just lines like these):
            * <!ENTITY name "&#xFFFF;">
            * <!-- comment -->
        """
        ifh = codecs.open(path, "rb", encoding="utf-8")
        nAdded = 0
        for recnum, rec in enumerate(ifh.readlines()):
            rec = rec.strip()
            if rec.match("<!--([^-]|-[^-])*-->") or rec=="": continue
            mat = re.match(r"""^<!ENTITY\s+(\w+)\s+(SDATA\s+)?("[^"]"|'[^']+')\s*>$""", rec)
            if mat is None:
                raise ValueError("Cannot parse ENTITY dcl at record %d: %s" % (recnum, rec))
            cpString = mat.group(2)[1:-1].strip()
            if cpString[0] == "&":
                cpString = Rune.unescapeXml(cpString)
            if len(cpString) != 1:
                raise ValueError("Couldn't resolve to char in ENTITY dcl "
                    "at record %d: %s" % (recnum, rec))
            self.add(mat.group(1), ord(cpString))
            nAdded += 1
        ifh.close()
        return nAdded

    def saveToFile(self, path:str, includeHTML:bool=False,
        sep:str=", ", base:int=16) -> None:
        from html.entities import codepoint2name as HTMLc2n
        ofh = codecs.open(path, "wb", encoding="utf-8")
        nAdded = 0
        names = sorted(list(self.name2codepoint.keys()))
        fmt = "%s%s" + ("0x%04x\n" if base==16 else "%d")
        for name in names:
            if not includeHTML and name in HTMLc2n: continue
            ofh.write(fmt % (name, sep, self.name2codepoint[name]))
            nAdded += 1
        ofh.close()
        return nAdded
