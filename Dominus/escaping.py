#!/usr/bin/env python3
#
# Support escaping of many kinds, both in terms of how to escape,
# and which characters *to* escape.
#
# 2024-11-20: Written by Steven J. DeRose.
#
from typing import Dict
from enum import Enum
from html.entities import codepoint2name
#
_orthography_blocks = {
    # ISO 15924 code, name, [ codepoint-ranges ]
    'adlm': ("Adlam",                 [(0x1E900, 0x1E95F)]),
    'arab': ("Arabic",                [(0x00600, 0x006FF), (0x00750, 0x0077F),
        (0x008A0, 0x008FF), (0x0FB50, 0x0FDFF), (0x0FE70, 0x0FEFF)]),
    'armn': ("Armenian",              [(0x00530, 0x0058F), (0x0FB13, 0x0FB17)]),
    'avst': ("Avestan",               [(0x10B00, 0x10B3F)]),
    'bali': ("Balinese",              [(0x01B00, 0x01B7F)]),
    'bamu': ("Bamum",                 [(0x0A6A0, 0x0A6FF), (0x16800, 0x16A3F)]),
    'bass': ("Bassa Vah",             [(0x16AD0, 0x16AFF)]),
    'batk': ("Batak",                 [(0x01BC0, 0x01BFF)]),
    'beng': ("Bengali",               [(0x00980, 0x009FF)]),
    'bhks': ("Bhaiksuki",             [(0x11C00, 0x11C6F)]),
    'bopo': ("Bopomofo",              [(0x02E80, 0x02EFF), (0x03100, 0x0312F)]),
    'brah': ("Brahmi",                [(0x11000, 0x1107F)]),
    'bugi': ("Buginese",              [(0x01A00, 0x01A1F)]),
    'buhd': ("Buhid",                 [(0x01740, 0x0175F)]),
    'cakm': ("Chakma",                [(0x11100, 0x1114F)]),
    'cans': ("Canadian Aboriginal",   [(0x01400, 0x0167F)]),
    'cari': ("Carian",                [(0x102A0, 0x102DF)]),
    'cham': ("Cham",                  [(0x0AA00, 0x0AA5F)]),
    'cher': ("Cherokee",              [(0x013A0, 0x013FF), (0x0AB70, 0x0ABBF)]),
    'chrs': ("Old Turkic",            [(0x10C00, 0x10C4F)]),
    'copt': ("Coptic",                [(0x02C80, 0x02CFF)]),
    'cprt': ("Cypriot",               [(0x10800, 0x1083F)]),
    'cyrl': ("Cyrillic",              [(0x00400, 0x004FF), (0x00500, 0x0052F),
        (0x02DE0, 0x02DFF), (0x0A640, 0x0A69F)]),
    'deva': ("Devanagari",            [(0x00900, 0x0097F)]),
    'dogr': ("Dogra",                 [(0x11800, 0x1184F)]),
    'dsrt': ("Deseret",               [(0x10400, 0x1044F)]),
    'dupl': ("Duployan",              [(0x1BC00, 0x1BC9F)]),
    'egyp': ("Egyptian Hieroglyphs",  [(0x13000, 0x1342F)]),
    'elba': ("Elbasan",               [(0x10500, 0x1052F)]),
    'ethi': ("Ethiopic",              [(0x01200, 0x0137F), (0x01380, 0x0139F),
        (0x02D80, 0x02DDF)]),
    'geor': ("Georgian",              [(0x010A0, 0x010FF), (0x02D00, 0x02D2F)]),
    'glag': ("Glagolitic",            [(0x02C00, 0x02C5F)]),
    'gong': ("Gunjala Gondi",         [(0x11D60, 0x11DAF)]),
    'gonm': ("Masaram Gondi",         [(0x11D00, 0x11D5F)]),
    'goth': ("Gothic",                [(0x10330, 0x1034F)]),
    'gran': ("Grantha",               [(0x11300, 0x1137F)]),
    'grek': ("Greek",                 [(0x00370, 0x003FF), (0x01F00, 0x01FFF)]),
    'gujr': ("Gujarati",              [(0x00A80, 0x00AFF)]),
    'guru': ("Gurmukhi",              [(0x00A00, 0x00A7F)]),
    'hang': ("Hangul",                [(0x01100, 0x011FF), (0x0A960, 0x0A97F),
        (0x0D7B0, 0x0D7FF)]),
    'hani': ("Han",                   [(0x02E80, 0x02FFF), (0x03000, 0x03FFF),
        (0x04E00, 0x09FFF), (0x0F900, 0x0FAFF)]),
    'hano': ("Hanunoo",               [(0x01720, 0x0173F)]),
    'hans': ("Han (Simplified)",      [(0x04E00, 0x09FFF), (0x03400, 0x04DBF),
        (0x20000, 0x2A6DF), (0x2A700, 0x2B73F)]),
    'hant': ("Han (Traditional)",     [(0x04E00, 0x09FFF), (0x03400, 0x04DBF),
        (0x20000, 0x2A6DF), (0x2A700, 0x2B73F)]),
    'hatr': ("Hatran",                [(0x108E0, 0x108FF)]),
    'hebr': ("Hebrew",                [(0x00590, 0x005FF), (0x0FB1D, 0x0FB4F)]),
    'hira': ("Hiragana",              [(0x03040, 0x0309F)]),
    'hluw': ("Anatolian Hieroglyphs", [(0x14400, 0x1467F)]),
    'hmng': ("Pahawh Hmong",          [(0x16B00, 0x16B8F)]),
    'hmnp': ("Nyiakeng Puachue Hmong",[(0x1E100, 0x1E14F)]),
    'hrkt': ("Japanese Syllabaries",  [(0x03040, 0x0309F), (0x030A0, 0x030FF)]),
    'hung': ("Old Hungarian",         [(0x10C80, 0x10CFF)]),
    'ital': ("Old Italic",            [(0x10300, 0x1032F)]),
    'java': ("Javanese",              [(0x0A980, 0x0A9DF)]),
    'jpan': ("Japanese",              [(0x03040, 0x0309F), (0x030A0, 0x030FF),
        (0x04E00, 0x09FFF), (0x03400, 0x04DBF)]),
    'kali': ("Kayah Li",              [(0x0A900, 0xA92F)]),
    'kana': ("Katakana",              [(0x030A0, 0x030FF), (0x031F0, 0x031FF),
        (0x032D0, 0x032FE)]),
    'khar': ("Kharoshthi",            [(0x10A00, 0x10A5F)]),
    'khmr': ("Khmer",                 [(0x01780, 0x017FF), (0x019E0, 0x019FF)]),
    'khoj': ("Khojki",                [(0x11200, 0x1124F)]),
    'knda': ("Kannada",               [(0x00C80, 0x00CFF)]),
    'kore': ("Korean",                [(0x0AC00, 0x0D7AF), (0x1100, 0x11FF),
        (0x3130, 0x318F), (0x03200, 0x032FF)]),
    'kthi': ("Kaithi",                [(0x11080, 0x110CF)]),
    'lana': ("Tai Tham",              [(0x01A20, 0x01AAF)]),
    'laoo': ("Lao",                   [(0x00E80, 0x00EFF)]),
    'latn': ("Latin",                 [(0x00000, 0x0024F), (0x02B0, 0x002FF),
        (0x01E00, 0x01EFF), (0x02C60, 0x02C7F)]),
    'lepc': ("Lepcha",                [(0x01C00, 0x01C4F)]),
    'limb': ("Limbu",                 [(0x01900, 0x0194F)]),
    'lina': ("Linear A",              [(0x10640, 0x1067F)]),
    'linb': ("Linear B",              [(0x10000, 0x1007F)]),
    'lisu': ("Lisu",                  [(0x0A4D0, 0x0A4FF)]),
    'lyci': ("Lycian",                [(0x10280, 0x1029F)]),
    'lydi': ("Lydian",                [(0x10920, 0x1093F)]),
    'mahj': ("Mahajani",              [(0x11150, 0x1117F)]),
    'maka': ("Makasar",               [(0x11EE0, 0x11EFF)]),
    'mand': ("Mandaic",               [(0x00840, 0x0085F)]),
    'mani': ("Manichaean",            [(0x10AC0, 0x10AFF)]),
    'marc': ("Marchen",               [(0x11C70, 0x11CBF)]),
    'medf': ("Medefaidrin",           [(0x16E40, 0x16E9F)]),
    'mend': ("Mende Kikakui",         [(0x1E800, 0x1E8DF)]),
    'merc': ("Meroitic Cursive",      [(0x109A0, 0x109FF)]),
    'mero': ("Meroitic Hieroglyphs",  [(0x10980, 0x1099F)]),
    'mlym': ("Malayalam",             [(0x00D00, 0x00D7F)]),
    'modi': ("Modi",                  [(0x11600, 0x1165F)]),
    'mong': ("Mongolian",             [(0x01800, 0x018AF)]),
    'mroo': ("Mro",                   [(0x16A40, 0x16A6F)]),
    'mtei': ("Meetei Mayek",          [(0x0ABC0, 0x0ABFF)]),
    'mult': ("Multani",               [(0x11280, 0x112AF)]),
    'mymr': ("Myanmar",               [(0x01000, 0x0109F)]),
    'nand': ("Nandinagari",           [(0x119A0, 0x119FF)]),
    'narb': ("Old North Arabian",     [(0x10A80, 0x10A9F)]),
    'nbat': ("Nabataean",             [(0x10880, 0x108AF)]),
    'newa': ("Newa",                  [(0x11400, 0x1147F)]),
    'nkoo': ("N'Ko",                  [(0x007C0, 0x007FF)]),
    'nshu': ("Nüshu",                 [(0x1B170, 0x1B2FF)]),
    'ogam': ("Ogham",                 [(0x01680, 0x0169F)]),
    'olck': ("Ol Chiki",              [(0x01C50, 0x01C7F)]),
    'orkh': ("Old Turkic",            [(0x10C00, 0x10C4F)]),
    'orya': ("Oriya",                 [(0x00B00, 0x00B7F)]),
    'osge': ("Osage",                 [(0x104B0, 0x104FF)]),
    'osma': ("Osmanya",               [(0x10480, 0x104AF)]),
    'palm': ("Palmyrene",             [(0x10860, 0x1087F)]),
    'pauc': ("Pau Cin Hau",           [(0x11AC0, 0x11AFF)]),
    'perm': ("Old Permic",            [(0x10350, 0x1037F)]),
    'phag': ("Phags-pa",              [(0x0A840, 0x0A87F)]),
    'phli': ("Inscriptional Pahlavi", [(0x10B60, 0x10B7F)]),
    'phlp': ("Psalter Pahlavi",       [(0x10B80, 0x10BAF)]),
    'phnx': ("Phoenician",            [(0x10900, 0x1091F)]),
    'plrd': ("Miao",                  [(0x16F00, 0x16F9F)]),
    'prti': ("Inscriptional Parthian",[(0x10B40, 0x10B5F)]),
    'rjng': ("Rejang",                [(0x0A930, 0x0A95F)]),
    'rohg': ("Hanifi Rohingya",       [(0x10D00, 0x10D3F)]),
    'runr': ("Runic",                 [(0x16A0, 0x016FF)]),
    'samr': ("Samaritan",             [(0x00800, 0x0083F)]),
    'sarb': ("Old South Arabian",     [(0x10A60, 0x10A7F)]),
    'saur': ("Saurashtra",            [(0x0A880, 0x0A8DF)]),
    'sgnw': ("SignWriting",           [(0x1D800, 0x1DAAF)]),
    'shaw': ("Shavian",               [(0x10450, 0x1047F)]),
    'shrd': ("Sharada",               [(0x11180, 0x111DF)]),
    'sidd': ("Siddham",               [(0x11580, 0x115FF)]),
    'sind': ("Khudawadi",             [(0x112B0, 0x112FF)]),
    'sinh': ("Sinhala",               [(0x00D80, 0x00DFF)]),
    'sogd': ("Sogdian",               [(0x10F30, 0x10F6F)]),
    'sogo': ("Old Sogdian",           [(0x10F00, 0x10F2F)]),
    'sora': ("Sora Sompeng",          [(0x110D0, 0x110FF)]),
    'soyo': ("Soyombo",               [(0x11A50, 0x11AAF)]),
    'sund': ("Sundanese",             [(0x01B80, 0x01BBF)]),
    'sylo': ("Syloti Nagri",          [(0x0A800, 0x0A82F)]),
    'syrc': ("Syriac",                [(0x00700, 0x0074F)]),
    'tagb': ("Tagbanwa",              [(0x01760, 0x0177F)]),
    'takr': ("Takri",                 [(0x11680, 0x116CF)]),
    'tale': ("Tai Le",                [(0x01950, 0x0197F)]),
    'talu': ("New Tai Lue",           [(0x01980, 0x019DF)]),
    'taml': ("Tamil",                 [(0x00B80, 0x00BFF)]),
    'tang': ("Tangut",                [(0x17000, 0x187FF)]),
    'tavt': ("Tai Viet",              [(0x0AA80, 0x0AADF)]),
    'telu': ("Telugu",                [(0x00C00, 0x00C7F)]),
    'tfng': ("Tifinagh",              [(0x02D30, 0x02D7F)]),
    'tglg': ("Tagalog",               [(0x01700, 0x0171F)]),
    'thaa': ("Thaana",                [(0x00780, 0x007BF)]),
    'thai': ("Thai",                  [(0x00E00, 0x00E7F)]),
    'tibt': ("Tibetan",               [(0x00F00, 0x00FFF)]),
    'tirh': ("Tirhuta",               [(0x11480, 0x114DF)]),
    'ugar': ("Ugaritic",              [(0x10380, 0x1039F)]),
    'vaii': ("Vai",                   [(0x0A500, 0x0A63F)]),
    'wara': ("Warang Citi",           [(0x118A0, 0x118FF)]),
    'wcho': ("Wancho",                [(0x1E2C0, 0x1E2FF)]),
    'xpeo': ("Old Persian",           [(0x103A0, 0x103DF)]),
    'xsux': ("Cuneiform",             [(0x12000, 0x123FF), (0x12400, 0x1247F)]),
    'yiii': ("Yi",                    [(0x0A000, 0x0A48F)]),
    'zanb': ("Zanabazar Square",      [(0x11A00, 0x11A4F)]),
}

def is_in_script(char: str, script: str) -> bool:
    if script not in _orthography_blocks:
        return False
    code_point = ord(char)
    return any(start <= code_point <= end for start, end in _orthography_blocks[script])


###############################################################################
#
class SlashType(Enum):
    """Support ways to do backslashing to use (normally NONE).
    Does not support URL-style %XX, or escaping UTF-8 bytes.
    """
    NONE    = 0
    LETTER  = 1     # Use \\n \\r \\t \\f
    HEX2    = 2     # Use \\xFF when char fits
    HEX4    = 4     # Use \\uFFFF when char fits
    HEX8    = 8     # Use \\UFFFFFFFF
    HEXBRACE= 16    # Use \\x{FFF}

    _slashLetters = { "\n": "\\n", "\r": "\\r", "\t": "\\t", "\f": "\\f" }

    @staticmethod
    def slashify(c:str, how:int=0) -> str:
        """Return a backslash-code for the given character.
        Pass any combination of the named kinds of escaping as 'how'.
        """
        if isinstance(c, int): c = chr(c)
        if not how: return c
        if (how & SlashType.LETTER) and c in SlashType._slashLetters:
            return SlashType._slashLetters[c]
        n = ord(c)
        if (how & SlashType.HEX2) and n <= 0xFF: return f"\\x{n:02x}"
        if (how & SlashType.HEX4) and n <= 0xFFFF: return f"\\u{n:04x}"
        if (how & SlashType.HEX8): return f"\\U{n:08x}"
        if (how & SlashType.HEXBRACE): return "\\x{%x}" % (n)
        return c


###############################################################################
#
class EscapeHandler:
    """Do optional escaping (not the required kind for delimiters).
    This lets you choose HOW to escape (names, hex, decimal, even backslashing),
    and which characters to escape.
    """
    def __init__(self,
        custom:Dict=None,   # A custom dictionary like html.codepoint2name
        html:bool=True,     # Use html.codepoint2name
        slash:SlashType=0,  # Use backslashing of specified type(s)
        base:int=16,        # If not in the dict(s), use base 10 or 16 char refs
        xcap:bool=True,     # If base==16, should the "x" be upper case?
        width:int=4,        # 0-pad numeric char refs to this minium width
        maxNoEscape:int=65535 # Escape anything over this.
        ):
        self.custom = custom
        self.html = html
        self.slash = slash
        self.base = base
        self.xcap = xcap
        self.width = width

        self.maxNoEscape = maxNoEscape
        self.orthographies = {}     # Orth codes NOT to escape
        self.allRanges = []         # And the corresponding codepoint ranges

    def addOrthography(self, orth:str):
        """Pass an ISO 15924 4-letter orthography code or the equivalent
        English name. The corresponding Unicode ranges will be considered
        ok to NOT escape.
        """
        code = None
        if orth in _orthography_blocks:
            code = orth
        else:
            for k, v in _orthography_blocks.items():
                if orth == v[0]:
                    code = k
                    break
        if not code:
            raise KeyError(f"Orthography code or name '{orth}' not recognized.")

        self.orthographies[code] = True
        for rg in _orthography_blocks[code][1]:
            self.allRanges.append(rg)

    def escapeString(self, s:str) -> str:
        return ''.join([self.escapeIfNeeded(c) for c in s])

    def escapeIfNeeded(self, c:str) -> str:
        """Return the escaped form of this character if needed. If the character
        doesn't need to be escaped, just return it unchanged.
        """
        n = ord(c)
        if self.orthographies:
            if any(start <= n <= end for start, end in self.allRanges):
                return c
        if n <= self.maxNoEscape:
            return c
        return self.escapeChar(n)

    def escapeChar(self, n:int) -> str:
        if self.custom and n in self.custom: return f"&{self.custom[n]};"
        if self.html and n in codepoint2name: return codepoint2name[n]
        if self.slash: return SlashType.slashify(n, how=self.slash)
        if self.base == 10: return f"&#{n:0{self.width}d};"
        if self.xcap: return f"&#X{n:0{self.width}x};"
        return f"&#x{n:0{self.width}x};"
