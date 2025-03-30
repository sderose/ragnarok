#!/usr/bin/env python3
#
# characterentities.py
# 2024-09-09: Written by Steven J. DeRose.
#
import sys
import codecs
import logging
import re

from xmlstrings import XmlStrings as Rune

lg = logging.getLogger("addCharacterEntities.py")

__metadata__ = {
    "title"        : "characterentities",
    "description"  : "",
    "rightsHolder" : "Steven J. DeRose",
    "creator"      : "http://viaf.org/viaf/50334488",
    "type"         : "http://purl.org/dc/dcmitype/Software",
    "language"     : "Python 3.9",
    "created"      : "2024-09-09",
    "modified"     : "2024-09-09",
    "publisher"    : "http://github.com/sderose",
    "license"      : "https://creativecommons.org/licenses/by-sa/3.0/"
}
__version__ = __metadata__["modified"]

descr = """
=Name=

characterentities


=Description=

Maintain mappings between Unicode code point values and XML/HTML NAMEs
for them. This is basically just like Python's html.entities, with
codepoint2name and name2codepoint. However:

* You can define multiple names for the same codepoint.
* You can add new items, either via add(name, codepoint) or by
specifying a file to load (see below)
* You can delete items (this allows you to trim the list down to what
you expect, thus making uses of unexpected references cause WF errors
so you immediately catch them.
* You can define multiple maps and switch between them (I can imagine wanting
this is you're importing files from TEX or other sources).
*

==Usage==

    from charentities import CharacterEntities
    CE = CharacterEntities(HTML=True)
    CE.addFile("myEntDefs.txt")
    addCharacterEntities.py [options] [files]


==File formats==

Two file formats for listing special character definitions are supported:

`addFromPairFile(path)` -- this loads from a simple 2-column file, like:

    # My own special characters
    bull 8226
    nbsp 0xA0
    logo 0xE100

The rules are:
    * Leading and trailing whitespace is removed.
    * LInes that are empty or start with "#" are discarded as comments.
    * The lines is parse as an XML local name; some non-name-character
separator character(s) such as space, command, etc); and a number. The
number can be in any format accepted by Python int(x, 0).

`addFromDclFile(path)` -- this loads lines that are simple SGML/XML/HTML
ENTITY declarations, like:

    <!-- My owm special characters -->
    <!ENTITY bull "*">
    <!ENTITY nbsp   "&#160;" >
    <!ENTITY   logo   "&#XE100;">

The rules are:
    * No interior comments (though entire comment lines are ok).
    * Only ENTITY declarations, one per line.
    * Extra whitespace (not including line-breaks) is ok.
    * The quoted part can use decimal, hex, XML predefined, and/or
    HTML 4 predefined references, or a literal character. But it must
resolve down to one character in the end. No external entities.


=See also=


=Known bugs and Limitations=

If you load from a file and then save back out, comments, blank lines,
and extra whitespace are lost.

It would be nice to allow multi-character values.

It would be nice to allow the right-hand side of declarations read by
`addFromDclFile(path)` to use references defined by a CharacterEntities
instance.


=To do=

This absolutely has to be hooked up Sebastian's list of AMS, AFII, TEX,
and other names! This could be done by code over his dataset, or by
making loadable files for each system.


=History=

* 2024-09-09: Written by Steven J. DeRose.


=Rights=

Copyright 2024-09-09 by Steven J. DeRose. This work is licensed under a
Creative Commons Attribution-Share-alike 3.0 unported license.
See [http://creativecommons.org/licenses/by-sa/3.0/] for more information.

For the most recent version, see [http://www.derose.net/steve/utilities]
or [https://github.com/sderose].


=Options=
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
            mat = re.match(r"""^<!ENTITY\s+(\w+)\s+("[^"]"|'[^']+')\s*>$""", rec)
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

    def saveToFile(self, path:str, includeHTML:bool=False, sep:str=", ") -> None:
        from html.entities import codepoint2name as HTMLc2n
        ofh = codecs.open(path, "wb", encoding="utf-8")
        nAdded = 0
        names = sorted(list(self.name2codepoint.keys()))
        for name in names:
            if not includeHTML and name in HTMLc2n: continue
            ofh.write("%s%s%04x\n" % (name, sep, self.name2codepoint[name]))
            nAdded += 1
        ofh.close()
        return nAdded
