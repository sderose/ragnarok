#!/usr/bin/env python3
# DocementType class: split from basedom 2024-06-28 sjd.
#
#
import re
from datetime import datetime, timedelta  # date, time,
from collections import namedtuple
from enum import Enum
from typing import List, Any, Union
import base64

from basedomtypes import FlexibleEnum, DOMException
#from domenums import RWord
from xmlstrings import XmlStrings as XStr, WSHandler
#from basedom import Node


###############################################################################
# ATTRIBUTE / SimpleType stuff
#
# These are the signed, positive maxima (rest calculated from them)
MAXLONG = 9223372036854775807
MAXINT = 2147483647
MAXSHORT = 32767
MAXBYTE = 127

ALPHA_re = "[a-zA-Z]"
ALNUM_re = "[a-zA-Z0-9]"
HEX_re = "[0-9a-fA-F]"
DIGIT_re = r"\d"
EXPNAN_re = r"([eE][-+]?\d+)?|INF|NaN"

TZONE_re = r"(Z|(\+|-)((0\d|1[0-3]):[0-5]\d|14:00))?"
GYEAR_re = r"-?([1-9]\d{3,}|0\d{3})"
GMONTH_re = r"-?([1-9]\d{3,}|0\d{3})"
GDAY_re = r"\(0\[1-9\]\|\[12\]\\d\|3\[01\]\)"
TIME_re = (r"\(\(\[01\]\\d\|2\[0-3\]\):\[0-5\]\\d:\[0-5\]\\d\(\\\.\\d\+\)\?\|" +
    r"\(24:00:00\(\\\.0\+\)\?\)\)")


MinMax = namedtuple('MinMax',
    ['minInclusive', 'minExclusive', 'maxExclusive', 'maxInclusive'])


class DerivationLimits(FlexibleEnum):
    """for XSD .block and .final
    """
    NONE = "NONE"
    EXTENSION = "EXTENSION"
    RESTRICTION = "RESTRICTION"
    ALL = "ALL"


class DatePrecision(Enum):
    """EDTF (Extended Date/Time Format) extends ISO 8601,
    now standardized as ISO 8601-2:2019.
    season, range, choices
    """
    BEFORE  = "b"
    AFTER   = "a"
    CERCA   = "~"
    UNCERTAIN = "?"
    UC      = "%"
    CENTURY = "c"


class DateTimeFrag:
    """Support XSD date and time types. This structure can handle any
    subset of the usual time fields, and convert to/from XSD types as well
    as Python types. Note:
        * I may not have covered all edge cases, like leap-second (second 61?),
          or the negative leap seconds I hear are being considered.
        * This doesn't do anything for pre-Gregorian dates, so they'll be off
          by 11 days.
        * There is no provision for approximate or uncertain dates yet.
    """
    def __init__(self, timestring:str=None):
        self._year:int      = None
        self._month:int     = None
        self._day:int       = None
        self._hour:int      = None
        self._minute:int    = None
        self._second:float  = None
        self._zone:int      = None
        self.precision:DatePrecision = None
        self.annotation:Any = None
        if timestring: self.set_any(timestring)

    def check(self):
        """Check by self-assigning, since the property-setters check.
        """
        if self.year is not None: self.year = self.year
        if self.month is not None: self.month = self.month
        if self.day is not None: self.day = self.day
        if self.hour is not None: self.hour = self.hour
        if self.minute is not None: self.minute = self.minute
        if self.second is not None: self.second = self.second
        if self.zone is not None: self.zone = self.zone
        return True

    @property
    def includesDate(self):
        return self.year is not None

    @property
    def includesTime(self):
        return self.hour is not None

    # Items setters and getters
    #
    @property
    def year(self):
        return self._year
    @year.setter
    def year(self, y:int):
        y = int(y)
        if y < 0 or y > 9999: raise ValueError(f"Bad year {y}.")
        self._year = y

    @property
    def month(self):
        return self._month
    @month.setter
    def month(self, m:int):
        m = int(m)
        if m < 1 or m > 12: raise ValueError(f"Bad month {m}.")
        self._month = m

    @property
    def day(self):
        return self._day
    @day.setter
    def day(self, d:int):
        d = int(d)
        if d < 1 or d > 31: raise ValueError(f"Bad day {d}.")
        if d == 31 and self.month in (2, 4, 6, 9, 11): return False
        if (self.month == 2 and d > 28
            and datetime(self.year, 2, self.month).month != 2): return False
        self._day = d

    @property
    def hour(self):
        return self._hour
    @hour.setter
    def hour(self, h:int):
        h = int(h)
        if h < 0 or h > 24: raise ValueError(f"Bad hour {h}.")
        self._hour = h

    @property
    def minute(self):
        return self._minute
    @minute.setter
    def minute(self, m:int):
        m = int(m)
        if m < 0 or m > 59: raise ValueError(f"Bad minute {m}.")
        self._minute = m

    @property
    def second(self):
        return self._second
    @second.setter
    def second(self, s:int):
        """Don't forget leap seconds.
        """
        s = int(s)
        if s < 0 or s > 60: raise ValueError(f"Bad second {s}.")
        self._second = s

    @property
    def zone(self):
        return self._zone
    @zone.setter
    def zone(self, z:int):
        z = int(z)
        if z < -(12*60) or z > (12*60): raise ValueError(f"Bad time zone {z}.")
        self._zone = z

    @property
    def microsecond(self):
        if not self.second: return 0
        return (self.second - int(self.second)) * 1000000

    # Convert to the usual Python objects.
    #
    def get_datetime(self):
        """Incomplete data just gets passed along to the constructor.
        What it *means* is not entirely clear, e.g. if there's no year.
        """
        return datetime.datetime(self.year, self.month, self.day,
            self.hour, self.minute, int(self.second),
            int(self.microsecond), self.get_tzinfo())

    def get_date(self):
        return datetime.date(self.year, self.month, self.day)

    def get_time(self):
        return datetime.time(self.hour, self.minute, self.second,
            int(self.microsecond), self.get_tzinfo())

    def get_tzinfo(self):
        zinfo = None
        if self.zone:
            tdelta = datetime.timdelta(minutes=self.zone)
            zinfo = datetime.tzinfo.utcoffset(tdelta)
        return zinfo

    # Setters for the XSD types, coming in as strings
    #
    def set_any(self, s:str) -> bool:           # y-m-dTh:m:s[-+]m
        """Take a full-fledged ISO 8601 string, and do what we can with it.
        """
        datePart, _T, timePart = s.partition("T")
        if not _T:
            if ":" in s:
                datePart = None; timePart = s
            if "-" in s:
                datePart = s; timePart = None

        if datePart:
            if datePart.startswith("---"):
                self.day = int(datePart[4:])
            elif datePart.startswith("--"):
                m, _d, d = datePart[2:].partition("-")
                self.month = int(m)
                if d: self.day = int(d)
            else:
                parts = datePart.split("-")
                self.year = int(parts[0])
                if len(parts) > 1:
                    self.month = int(parts[1])
                    if len(parts) > 2:
                        self.dat = int(parts[2])

        if timePart:
            mat = re.match(r"(Z|[-+]\d+(:\d+)?)$", timePart)
            if not mat:
                basetimePart = timePart
            else:
                basetimePart = timePart[0:mat.start(1)]
                self.set_zone(mat.group(1))
            parts = basetimePart.split(":")
            self.hour = int(parts[0])
            if len(parts) > 1:
                self.minute = int(parts[1])
                if len(parts) > 2:
                    self.second = float(parts[2])

    def set_datetime(self, s:str) -> bool:      # 2024-01-31T11:59:59.12-05:00
        self.set_any(s)

    def set_time(self, s:str) -> bool:          # 11:59:59.12-05:00
        self.set_any(s)

    def set_date(self, s:str) -> bool:          # 2024-01-31
        self.set_any(s)

    def set_gYearMonth(self, s:str) -> bool:    # 2024-01
        y, _dash, m = s[2:].partition("-")
        try:
            y = int(y)
            m = int(m)
            if y < 0 or y > 9999 or m < 1 or m > 12: return False
        except ValueError:
            return False
        self.year = y
        self.month = m
        return True

    def set_gYear(self, s:str) -> bool:         # 2024
        try:
            y = int(s)
            if y < 0 or y > 9999: return False
        except ValueError:
            return False
        self.year = y
        return True

    def set_gMonthDay(self, s:str) -> bool:     # --01-31
        if not s.startswith("--"): return False
        m, _dash, d = s[2:].partition("-")
        try:
            m = int(m)
            d = int(d)
            if m < 1 or m > 12 or d < 1 or d > 31: return False
        except ValueError:
            return False
        self.month = m
        self.day = d
        return True

    def set_gMonth(self, s:str) -> bool:        # --01
        if not s.startswith("--"): return False
        try:
            m = int(s[2:])
            if m < 1 or m > 12: return False
        except ValueError:
            return False
        self.month = m
        return True

    def set_gDay(self, s:str) -> bool:          # ---31
        if not s.startswith("--3"): return False
        try:
            d = int(s[3:])
            if d < 1 or d > 31: return False
        except ValueError:
            return False
        self.day = d
        return True

    def set_zone(self, s:str) -> bool:          # "", "Z", or -+05:30
        s = s.strip()
        if s in [ "Z", "" ]:
            self.zone = 0
            return True
        mat = re.match(r"([-+]?)(\d+)(:\d+)?$", s.strip())
        if not mat: return False
        z = 0
        if mat.group(2): z += 60 * int(mat.group(2))
        if mat.group(3): z += int(mat.group(3)[1:])
        if z > 12*60: return False
        if mat.group(1) == "-": z = -z
        self.zone = z
        return True


###########################################################################
# See [https://www.w3.org/TR/xml/]
# iscastable; iscanonical; ispybaseof;
# tocanonical; lists/unions? inheritable fetch?
# TODO: Integrate w/ NewType items in basedomtypes?
#
class XsdFacet(Enum):
    """Cf https://www.w3.org/TR/xmlschema11-1/
    """
    minExclusive = 1
    minInclusive = 2
    maxExclusive = 3
    maxInclusive = 4
    totalDigits = 5
    fractionDigits = 6
    length = 7
    minLength = 8
    maxLength = 9
    enumeration = 10
    whiteSpace = 11     # "collapse", "preserve", or "replace"
    pattern = 12        # We use PCRE, so don't have \\i or \\c
    assertion = 13      # Let user add callables?
    # {any with namespace: ##other}

    # These aren't technically facets, but it's a handy place for them
    range = 100         # Cover for min/max incl/excl
    pybase = 101        # Python cover type if any
    base = 102          # XSD supertype
    variety = 103       # "atomic", "list", or "union"

# (ENTITY ones are defined later)


class XsdType(dict):
    """A type for the bundle of info that defines an the XSD datatype
    (e.g. for attributes).
    TODO: What else belongs in here?
    """
    def __getitem__(self, key) -> Union[List, 'Node']:
        # TODO fetch up the inheritance chain?
        return super().get(key, None)

    def isOkValue(self, val:Any) -> bool:
        if isinstance(val, self["pybase"]): return True
        problem = facetCheck(val, self)
        return (problem is None)

AttrTypes = {
    "string": XsdType({
        "pybase": str,
        "base": None,
        "pattern": r".*",
        "length": None,
        "minLength": None,
        "maxLength": None,
        "whiteSpace": "preserve"
    }),
    "normalizedString": XsdType({
        "pybase": str,
        "base": "string",
        "pattern": r".*",
        "whiteSpace": "replace"
    }),
    "token": XsdType({
        "pybase": str,
        "base": "normalizedString",
        "pattern": r".*",
    }),
    "language": XsdType({
        "pybase": str,
        "base": "token",
        "pattern": r"[a-zA-Z]{1,8}(-[a-zA-Z0-9]{1,8})*", # TODO
    }),
    "NMTOKEN": XsdType({
        "pybase": str,
        "base": "token",
        "pattern": XStr.NMTOKEN_re,
    }),
    "NMTOKENS": XsdType({
        "pybase": str,
        "base": "NMTOKEN",
        "pattern": r"%s(\s+%s)*" % (XStr.NMTOKEN_re, XStr.NMTOKEN_re),
        "variety": "list",
    }),
    "Name": XsdType({
        "pybase": str,
        "base": "token",
        "pattern": XStr.QQName_re,
    }),
    "NCName": XsdType({
        "pybase": str,
        "base": "Name",
        "pattern": XStr.NCName_re,
    }),
    "ID": XsdType({
        "pybase": str,
        "base": "NCName",
        "pattern": XStr.NCName_re,
    }),
    "IDREF": XsdType({
        "pybase": str,
        "base": "NCName",
        "pattern": XStr.NCName_re,
    }),
    "IDREFS": XsdType({
        "pybase": str,
        "base": "IDREF",
        "pattern": r"%s(\s+%s)*" % (XStr.QName_re, XStr.QName_re),
        "variety": "list",
    }),
    "ENTITY": XsdType({
        "pybase": str,
        "base": "NCName",
        "pattern": XStr.NCName_re,
    }),
    "ENTITIES": XsdType({
        "pybase": str,
        "base": "ENTITY",
        "pattern": r"%s(\s+%s)*" % (XStr.NCName_re, XStr.NCName_re),
        "variety": "list",
    }),
    "QName": XsdType({
        "pybase": str,
        "base": "string",
        "pattern": XStr.QName_re,
    }),
    "NOTATION": XsdType({
        "pybase": str,
        "base": "string",
        "pattern": XStr.QName_re,
    }),

    ###########################################################################
    "boolean": XsdType({
        "pybase": bool,
        "base": None,
        "pattern": r"true|false|1|0",
    }),

    ###########################################################################
    "decimal": XsdType({
        "pybase": int,
        "base": None,
        "pattern": r"(\+|-)?((\d+(\.\d*)?)|(\.\d+))",
    }),
    "integer": XsdType({  # Unbounded
        "pybase": int,
        "base": "decimal",
        "pattern": r"[\-+]?\d+",
        "fractionDigits": 0,
    }),
    "nonPositiveInteger": XsdType({
        "pybase": int,
        "base": "integer",
        "pattern": r"(-\d+)|0",
        "range": MinMax(None, None, None, 0),
        "fractionDigits": 0,
    }),
    "negativeInteger": XsdType({
        "pybase": int,
        "base": "nonPositiveInteger",
        "pattern": r"-\d+",
        "range": MinMax(None, None, None, -1),
        "fractionDigits": 0,
    }),
    "nonNegativeInteger": XsdType({
        "pybase": int,
        "base": "integer",
        "pattern": r"[+]?\d+",
        "range": MinMax(0, None, None, None),
        "fractionDigits": 0,
    }),
    "positiveInteger": XsdType({
        "pybase": int,
        "base": "nonNegativeInteger",
        "pattern": r"[+]?\d*[1-9]\d*",
        "range": MinMax(1, None, None, None),
        "fractionDigits": 0,
    }),
    "long": XsdType({
        "pybase": int,
        "base": "integer",
        "pattern": r"[-+]?\d+",
        "range": MinMax(-MAXLONG-1, None, None, MAXLONG),
        "fractionDigits": 0,
    }),
    "int": XsdType({
        "pybase": int,
        "base": "long",
        "pattern": r"[-+]?\d+",
        "range": MinMax(-MAXINT-1, None, None, MAXINT),
        "fractionDigits": 0,
    }),
    "short": XsdType({
        "pybase": int,
        "base": "int",
        "pattern": r"[-+]?\d+",
        "range": MinMax(-MAXSHORT-1, None, None, MAXSHORT),
        "fractionDigits": 0,
    }),
    "byte": XsdType({
        "pybase": int,
        "base": "short",
        "pattern": r"[-+]?\d+",
        "range": MinMax(-MAXBYTE-1, None, None, MAXBYTE),
        "fractionDigits": 0,
    }),
    "unsignedLong": XsdType({
        "pybase": int,
        "base": "nonNegativeInteger",
        "pattern": r"[+]?\d+",
        "range": MinMax(0, None, None, MAXLONG<<1 + 1),
        "fractionDigits": 0,
    }),
    "unsignedInt": XsdType({
        "pybase": int,
        "base": "unsignedLong",
        "pattern": r"[+]?\d+",
        "range": MinMax(0, None, None, MAXINT<<1 + 1),
        "fractionDigits": 0,
    }),
    "unsignedShort": XsdType({
        "pybase": int,
        "base": "unsignedInt",
        "pattern": r"[+]?\d+",
        "range": MinMax(0, None, None, MAXSHORT<<1 + 1),
        "fractionDigits": 0,
    }),
    "unsignedByte": XsdType({
        "pybase": int,
        "base": "unsignedShort",
        "pattern": r"[+]?\d+",
        "range": MinMax(0, None, None, MAXBYTE<<1 + 1),
        "fractionDigits": 0,
    }),

    ###########################################################################
    "float": XsdType({
        "pybase": float,
        "base": "decimal",
        "pattern": r"(\+|-)?(\d+(\.\d*)?|\.\d+)" + EXPNAN_re,
    }),
    "double": XsdType({
        "pybase": float,
        "base": "decimal",
        "pattern": r"(\+|-)?(\d+(\.\d*)?|\.\d+)" + EXPNAN_re,
    }),

    ###########################################################################
    "duration": XsdType({
        "pybase": timedelta,
        "base": None,
        "pattern": r"-?P(\d+Y)?(\d+M)?(\d+D)?(T(\d+H)?(\d+M)?(\d+(\.\d+)?S)?)?",
    }),

    "dateTime": XsdType({
        "pybase": DateTimeFrag,
        "base": None,
        "pattern": GYEAR_re + r"-" + GMONTH_re + r"-" + GDAY_re + r"T" + TIME_re + TZONE_re,
    }),
    "time": XsdType({
        "pybase": DateTimeFrag,
        "base": None,
        "pattern": TIME_re + TZONE_re,
    }),
    "date": XsdType({
        "pybase": DateTimeFrag,
        "base": None,
        "pattern": GYEAR_re + r"-" + GMONTH_re + r"-" + GDAY_re + TZONE_re,
    }),
    "gYearMonth": XsdType({
        "pybase": DateTimeFrag,
        "base": None,
        "pattern": GYEAR_re + r"-" + GMONTH_re + TZONE_re,
    }),
    "gYear": XsdType({
        "pybase": DateTimeFrag,
        "base": None,
        "pattern": GYEAR_re + TZONE_re,
    }),
    "gMonthDay": XsdType({
        "pybase": DateTimeFrag,
        "base": None,
        "pattern": r"--" + GMONTH_re + r"-" + GDAY_re + TZONE_re,
    }),
    "gDay": XsdType({
        "pybase": DateTimeFrag,
        "base": None,
        "pattern": r"---" + GDAY_re + TZONE_re,
    }),
    "gMonth": XsdType({
        "pybase": DateTimeFrag,
        "base": None,
        "pattern": r"--" + GMONTH_re + TZONE_re,
    }),

    ###########################################################################
    "hexBinary": XsdType({
        "pybase": lambda x: bytes.fromhex(x),  # TODO Is this good enough?
        "base": "string",
        "pattern": r"([0-9a-fA-F]{2})*",
    }),
    "base64Binary": XsdType({
        "pybase": lambda x: base64.b64decode(x),
        "base": "string",
        "pattern": (
            r"((([A-Za-z0-9+/] ?){4})*(([A-Za-z0-9+/] ?){3}" +
            r"[A-Za-z0-9+/]|([A-Za-z0-9+/] ?){2}" +
            r"[AEIMQUYcgkosw048] ?=|[A-Za-z0-9+/] ?[AQgw] ?= ?=))?"),
    }),

    ###########################################################################
    "anyURI": XsdType({
        "pybase": str,
        "base": "string",
        "pattern": r".*",  # Too lenient, at least rule out spaces? Keep ##any.
    }),
}  # AttrTypes

requiredFacets = [ "pybase", "base", "pattern" ]

# Check and add defaults
for _atype, _ainfo in AttrTypes.items():
    for rf in requiredFacets:
        if rf not in _ainfo: raise DOMException(
            f"Missing required facet '{rf}' for XSD type '{_atype}'.")
    if "variety" not in _ainfo: _ainfo["variety"] = "atom"
    if "whiteSpace" not in _ainfo: _ainfo["whiteSpace"] = "collapse"

    for prop in _ainfo.keys():
        if prop not in XsdFacet.__members__: raise DOMException(
            f"Unrecognized facet '{prop}' for XSD type '{_atype}'.")
        if prop == "range" and not isinstance(_ainfo[prop], MinMax): raise DOMException(
            f"Range constraint is not a MinMax object for XSD type '{_atype}'.")


def facetCheck(val:str, typ:Union[str, XsdType]) -> XsdFacet:
    """Returns the first XsdFacet that the value violates (if any),
    or None if all its facet constraints are satisfied.
    TODO: Issues:
        *be* of the type, or just castable?
        Does normalizedstring mean it is noramlizable, or already normed?
        What about case and unorm?
        What about None and ""?
        Should there be a configurable bool normalizer?
            (yes/no, 1/0, T/F, True/False, true/false, on/off,...)
        Almost anything can cast to bool or string, and float casts to int.
        Should int 31 (vs. "31") count as GDay (etc.)
        Must the value *directly* cast to its pybase?
    """
    if not isinstance(typ, XsdType):
        try:
            typ = AttrTypes[typ]
        except KeyError as e:
            raise TypeError(
                f"Unrecognized XSD type name '{typ}' for value '{val}'.") from e

    if not isinstance(val, str): raise TypeError(
        "Value to check against XSD datatype '%s' is a Python '%s', not str."
        % (typ, type(val).__name__))

    typeSpec = typ
    sval = str(val)

    if "pybase" in typeSpec and typeSpec["pybase"] is not None:
        try:
            # TODO Figure out what to do with base64 types
            _castVal = typeSpec["pybase"](sval)
        except (TypeError, ValueError):
            return XsdFacet.pybase
    if "variety" in typeSpec:
        if typeSpec["variety"] == "list":
            return None  # TODO Finish variety=list
        elif typeSpec["variety"] == "union":
            return None  # TODO Finish variety=union
    if "whiteSpace" in typeSpec:
        if typeSpec["whiteSpace"] == "collapse":
            sval = WSHandler.xcollapseSpace(sval)
        elif typeSpec["whiteSpace"] == "replace":
            sval = WSHandler.xreplaceSpace(sval)
    if "minLength" in typeSpec:
        if len(sval) < typeSpec["minLength"]: return XsdFacet.minLength
    if "maxLength" in typeSpec:
        if len(sval) > typeSpec["minLength"]: return XsdFacet.maxLength
    if "pattern" in typeSpec:
        if not re.match(typeSpec["pattern"], sval): return XsdFacet.pattern
    if "range" in typeSpec:
        mm = typeSpec["range"]
        tval = int(val)
        if mm[0] is not None and tval < mm[0]: return XsdFacet.minInclusive
        if mm[1] is not None and tval <= mm[1]: return XsdFacet.minExclusive
        if mm[2] is not None and tval >= mm[2]: return XsdFacet.maxExclusive
        if mm[3] is not None and tval > mm[3]: return XsdFacet.maxInclusive
    if "enumeration" in typeSpec and typeSpec["enumeration"]:
        if sval not in typeSpec["enumeration"]: return XsdFacet.enumeration
    if "totalDigits" in typeSpec or "fractionDigits" in typeSpec:
        pre, _dot, post = sval.partition(".")
        if "totalDigits" in typeSpec and len(pre) > typeSpec["totalDigits"]:
            return XsdFacet.totalDigits
        if "fractionDigits" in typeSpec and len(post) > typeSpec["fractionDigits"]:
            return XsdFacet.fractionDigits
    return None  # Passes all facet checks
