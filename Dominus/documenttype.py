#!/usr/bin/env python3
# DocementType class: split from basedom 2024-06-28 sjd.
#
#
import re
from datetime import datetime, timedelta  # date, time,
from collections import defaultdict, namedtuple
from enum import Enum
from typing import List, Set, Dict, Any, Union, Iterable
import base64

from basedomtypes import (NMTOKEN_t, QName_t, NodeType, FlexibleEnum,
    NSuppE, DOMException, ICharE)
from domenums import RWord
from xmlstrings import XmlStrings as XStr, CaseHandler, WSHandler
from basedom import Node

descr = """
This library provides a basic interface to schema information, whether created
via the API, an XML (or perhaps SGML) DTD, an XML Schems, or (eventually) a Relax-NG schema (I'm less
familiar with those, so that may be a while). The idea here is to get any
schema into a common API that parsers and validators can talk to.

There are a lot of classes, but most are quite small and correspond closely
to SGML/HTML/XML/XSD notions. Enums in here generally include the union
of possibilities (for example, #CURRENT has a defined name even though
it is only used in SGML).
Unnamed options such as having NO repetition or no seq operator (as for
singleton model groups) have corresponding enum values for expliciteness.


* SimpleType/attribute stuff (perhaps split to separate file?)

    ** DerivationLimits(FlexibleEnum): Ways to derive types
    (extension, etc)

    ** SimpleType(dict): Basicallly like XSD, a name, base type
    (plus corresponding Python type if any), and selected facets

    ** XsdType(dict): The set of built-in XSD datatypes, with their facets

    ** DateTimeFrag: Support for fragmentary dates/times per XSD

    ** XsdFacet(Enum): The set of known XSD facets

    ** AttributeDef: A single attribute with name/type/default

    ** AttlistDef(dict): A bundle of attributes. These must be attached to
the Doctype, and to their element(s)


* ComplexType(SimpleType): Basically like XSD or SGML Element

    ** ContentType(FlexibleEnum): ANY, EMPTY, etc., or X_MODEL

    ** DclType(FlexibleEnum):  Attribute declared types (cf XsdType)

    ** DftType(FlexibleEnum):  Attribute defaults (#IMPLIED etc., or X_LITERAL)

    ** SeqType(FlexibleEnum):  OR vs. SEQ vs. the late AND

    ** RepType(FlexibleEnum):  *?+ or {} like XSD min/maxOccurs

    ** ModelItem: A token + RepType in a content model

    ** ModelGroup: A group in a content model

    ** Model(ModelGroup): An *entire* content model or declared content value

    ** ElementDef(ComplexType): An element declaration (name(s?) plus Model)
    Cf ComplexType


* Entity stuff

    ** EntityType(FlexibleEnum): What kinds of entities we got?
    parameter, general, ndata, maybe sdata

    ** EntityParseType(FlexibleEnum): Parsing constraint on entity

    ** DataSource: A QLit or PUBLIC/SYSTEM ID(s)

    ** EntityDef: An entity declaration (name plus
    EntityType, ParseType, and DataSource)


* Notation stuff (treated as a quasi-entity)

    ** Notation: A notation declaration: name, plus
    a DataSource (which should always be a PUBLIC/SYSTEM ID(s), not QLit)

* Document stuff

    ** DocumentType(Node):
"""


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

class SimpleType(dict):
    def __init__(self, name:NMTOKEN_t, baseType:NMTOKEN_t):
        self.name = name
        self.baseType = baseType
        self.restrictions = {}
        self.memberTypes = None  # For list and union types
        self.caseTx = CaseHandler.NONE
        self.unormTx = CaseHandler.NONE
        self.wsTx = WSHandler.XML


###########################################################################
#
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


class DclType(FlexibleEnum):  # For attributes
    CDATA     = "CDATA"
    NDATA     = "NDATA"
    RCDATA    = "RCDATA"      # In case of SGML
    SDATA     = "SDATA"       # In case of SGML


class DftType(FlexibleEnum):  # For attributes
    REQUIRED  = "#REQUIRED"
    IMPLIED   = "#IMPLIED"
    FIXED     = "#FIXED"
    X_VALUE   = "X_VALUE"     # Set when there's a literal default value
    CONREF    = "#CONREF"     # In case of SGML
    CURRENT   = "#CURRENT"    # In case of SGML

# An AttrKey is what attributes are index by in a Doctype. Elements also
# have their own list of attributes, which should probably point via one of
# these, though one of these could apply to many elements. Is an attribute
# identified by
#   * the attribute name, in a given namespace
#   * the attribute name and a single element (q)name (on which it occurs)
#   * the attribute name and the element (q)name(s) from the same ATTLIST dcl
#   * the attribute name, regardless
#   ...
#
AttrKey = namedtuple("AttrKey", [ "ens", "ename", "ans", "aname" ])

class AttributeDef:
    """Define an Attribute. This can be handed information from parsing
    a schema, or just be called on the fly. There does not have to be
    an element of the given name defined (either now or later).

    This does NOT save/attach the definition anywhere. Caller must do that.
    """
    def __init__(self, ens:NMTOKEN_t, ename:NMTOKEN_t, ans:NMTOKEN_t, aname:NMTOKEN_t,
        atype:NMTOKEN_t, adefault:Any, readOrder:int=0):
        self.ens = ens
        self.ename = ename  # TODO Provide for element name lists? What about NS?
        self.ans = ans
        self.aname = aname
        self.atype = atype   # TODO string or a type object?
        self.adefault = adefault
        self.readOrder = readOrder

        self.caseTx = "NONE"
        self.wsTx = "NONE"
        self.enumValues:dict = None

        if not XStr.isXmlQName(aname): raise ICharE(
             "Bad name '{aname}' for attribute.")
        if atype not in AttrTypes and not isinstance(atype, type): raise TypeError(
            "Unrecognized type for attribute {aname} for {self.name}.")
        if adefault is not None:
            pass  # TODO

    def enumSpec(self) -> str:
        if self.enumValues: return " (%s)" % (" | ".join(self.enumValues))
        return None

    def getKey(self):
        """Return a hashable key for this attribute.
        """
        return AttrKey(self.ens, self.ename, self.ans, self.aname)

class AttlistDef(dict):
    """Represent an entire ATTLIST declaration.
    But how are attributes attached? A copy to each element? Or one object
    per ATTLIST and pointers from elements? And do the attributes identify
    their owner element(s), or just via their ATTLIST?
    Who creates/attaches the element if it's not already there?  TODO
    """
    def __init__(self, enames:Union[str, List[str]], readOrder:int=0):
        """Add the individual attrs with __setitem__. The AttlistDef crosses
        a set of elements, with a set of attributes. We actually *need* readOrder
        because in case of duplicates attr names for a single elements, 1st applies.
        Eventually
        """
        self.enames = enames if isinstance(enames, Iterable) else [ enames ]
        bads = []
        for ename in self.enames:
            if not XStr.isXmlQName(ename): bads.append(ename)
        if bads: raise ICharE(
            "Bad element name(s) {bads} in ATTLIST.")
        self.readOrder = readOrder
        self.attributes = {}

    def __setitem__(self, aname:NMTOKEN_t, atype:str, adefault:Any=None) -> AttributeDef:
        """Just makes an attribute; caller must attach to element, doctype.
        """
        if aname in self.attributes:
            raise KeyError("Attribute {aname} already defined for {self.name}.")
        adef = AttributeDef(ens=None, ename=None, ans=RWord.NS_ANY, aname=aname,
            atype=atype, adefault=adefault, readOrder=len(self.attributes))
        self.attributes[(RWord.NS_ANY, aname)] = adef
        return adef

    def tostring(self) -> str:
        buf = "<!ATTLIST (%s) " % (", ".join(self.enames))
        for aname, aobj in self.items():
            buf += "\n    %16s %16s %s" % (aname, aobj.enumSpec(), aobj.adefault)
        buf += ">\n"
        return buf


###############################################################################
# ELEMENT / ComplexType Stuff
#
class ComplexType(SimpleType):
    def __init__(self, name:NMTOKEN_t, baseType=None, model:'Model'=None):
        super().__init__(name=name, baseType=baseType)
        self.abstract = False
        self.final = None
        self.block = None
        self.attributeDefs:Dict[AttrKey, 'AttributeDef'] = {}
        self.contentType = None
        self.model = model

class ContentType(FlexibleEnum):  # For elements
    ANY       = "ANY"
    EMPTY     = "EMPTY"
    PCDATA    = "#PCDATA"
    X_MODEL   = "X_MODEL"     # Has content model, not one of the above
    X_ELEMENT = "X_ELEMENT"   # HERE -- for element-only content

class SeqType(FlexibleEnum):  # For ModelGroups
    NOSEQ     = ""            # Only for singleton groups
    SEQUENCE  = ","
    CHOICE    = "|"
    ALL       = "&"

UNLIMITED = -1  # (or None?)

class RepType(FlexibleEnum):  # For ModelItems and ModelGroups
    # TODO Figure out best way to deal with {} case
    # Why shouldn't this be available for List attributes too?
    NOREP   = ""
    STAR    = "*"
    PLUS    = "+"
    QUEST   = "?"
    X_BOUNDS= "{}"            # Like regex and xsd

    def __init__(self, minOccurs:int=1, maxOccurs:int=1):
        try:
            self.minOccurs = int(minOccurs)
        except (TypeError, ValueError):
            self.minOccurs = 0
        try:
            self.maxOccurs = int(maxOccurs)
        except (TypeError, ValueError):
            self.maxOccurs = 0

    def setBounds(self, minOccurs:int=None, maxOccurs:int=None) -> None:
        """Mainly meant for X_BOUNDS case and XSD-based usage.
        """
        if self.value == "*":
            self.minOccurs = 0; self.maxOccurs = UNLIMITED
        elif self.value == "+":
            self.minOccurs = 1; self.maxOccurs = UNLIMITED
        elif self.value == "?":
            self.minOccurs = 0; self.maxOccurs = 1
        elif self.value == "":
            self.minOccurs = 1; self.maxOccurs = 1
        else:
            self.minOccurs = 0
            if self.minOccurs is not None: self.minOccurs = minOccurs
            self.maxOccurs = UNLIMITED
            if self.maxOccurs is not None: self.maxOccurs = maxOccurs
        if (self.minOccurs >= 0 and self.maxOccurs >= 0
            and self.minOccurs > self.maxOccurs): raise SyntaxError(
                "Occurrence bounds out of order: min %d, max %d."
                % (self.minOccurs, self.maxOccurs))

    def tostring(self) -> str:
        if self.minOccurs == 0:
            if self.maxOccurs == 1: return "?"
            if self.maxOccurs == UNLIMITED: return "*"
        elif self.minOccurs == 1:
            if self.maxOccurs == 1: return ""
            if self.maxOccurs == UNLIMITED: return "+"
        return "{%d,%d}" % (self.minOccurs, self.maxOccurs)


###############################################################################
#
class ModelItem:
    """One item (an element name with a rep, or just #PCDATA).
    BS integration?
    """
    def __init__(self, name:NMTOKEN_t, rep:RepType=RepType.NOREP):
        assert name == ContentType.PCDATA.value or XStr.isXmlNMTOKEN(name)
        self.name = name
        self.rep = rep

    def tostring(self, indent:str=None) -> str:
        return self.name + self.rep.tostring()

class ModelGroup:
    """Any parenthesized group, with ModelItem and/or ModelGroup members,
    plus sequence and rep settings.
    Maybe keep the original string, or a list of PEs in it?
    """
    def __init__(self, childItems:List[Union['ModelGroup', ModelItem]]=None,
        seq:SeqType=None, rep:RepType=None):
        self.seq = SeqType(seq) or SeqType.NOSEQ
        self.rep = RepType(rep) or RepType.NOREP
        self.childItems = childItems or []

    def getNames(self) -> Set:
        """Recursively extract the set of all names used anywhere within.
        """
        names = set()
        for childItem in self.childItems:
            if isinstance(childItem, ModelItem):
                names = names.union([childItem.name])
            elif isinstance(childItem, ModelGroup):
                names = names.union(childItem.getNames())
        return names

    def tostring(self, indent:str=None) -> str:
        """TODO Maybe re-introduce PEs or complex types?
        """
        if not self.childItems: return "()"
        buf = ""
        connector = self.seq.value
        for ch in self.childItems:
            if not buf: buf = f"\n{indent}({ch.tostring()}"
            else: buf +=  f" {connector} {ch.tostring()}"
        return buf + ")"

class Model(ModelGroup):
    """The whole/top model, which can be a declared content keyword OR
     a model group (passed here as a List of string tokens.
     Tokens are converted to an AST of ModelGroups and ModelItems.

    childItems comes in as List[str], for example:
        [ "(", "i", "|", "b", "*", "|", "tt", ")", "+" ]
    """
    def __init__(self, tokens:List[str]=None, seq:SeqType=None, rep:RepType=None,
        contentType:ContentType=None):
        super(). __init__(None, None, None)
        self.contentType = None if not contentType else ContentType(contentType)
        if not tokens: return

        # Model, not declared content
        #
        if seq or rep: raise DOMException(
            "Don't pass seq or rep to Model, only to ModelGroup or ModelItem.")
        if contentType != ContentType.X_MODEL: raise SyntaxError(
            f"Expected contentType X_MODEL (not {contentType}) with tokens = {tokens}")
        if not isinstance(tokens, Iterable): raise SyntaxError(
            f"Model tokens arg is not Iterable, but {type(tokens)}.")

        # Make a proper AST from the model tokens
        #   (super() already set .childItems = [])
        #
        MGStack = [ self.childItems ]
        for i in range(len(tokens)):
            t = tokens[i]
            if t == "(":
                newMG = ModelGroup()
                if MGStack: MGStack[-1].childItems.append(newMG)
                MGStack.append(newMG)
            elif t == ")":
                if len(MGStack) == 0: raise SyntaxError(
                    "Extra ')' at token {i} in model: %s." % (tokens))
                if i+1 < len(tokens) and isinstance(tokens[i+1], RepType):
                    MGStack[-1].rep = tokens[i+1]
                    MGStack.pop()
                    i += 1
            elif t in "|&,":  # Sequence type
                if MGStack[-1].seq is SeqType.NOSEQ:
                    MGStack[-1].seq = SeqType(t)
                elif MGStack[-1].seq != SeqType(t): raise SyntaxError(
                    f"Inconsistent connector (token {i} '{t}' vs. {MGStack[-1].seq}.")
            elif t == ContentType.PCDATA.value or XStr.isXmlName(t):
                newMI = ModelItem(t)
                MGStack[-1].childItems.append(newMI)
                if i+1 < len(tokens) and isinstance(tokens[i+1], RepType):
                    newMI.rep = RepType(tokens[i+1])  # TODO Map to enum
                    i += 1
            else:
                raise SyntaxError(f"Unexpected model token #{i}: '{t}'.")
        if len(MGStack) != 0:
            raise SyntaxError(f"Unclosed () group in model: {tokens}.")

    def tostring(self, indent:str=None) -> str:
        if self.contentType != ContentType.X_MODEL:
            return self.contentType.tostring()
        else:
            return super().tostring(indent=indent)

class ElementDef(ComplexType):
    def __init__(self, name:NMTOKEN_t, model:Model,
        ownerSchema:'DocumentType'=None, readOrder:int=0):
        super().__init__(name, model)
        self.ownerSchema = ownerSchema
        self.readOrder = readOrder
        self.attributeDefs:Dict[AttrKey, 'AttributeDef'] = None
        self.allowText:bool = True
        self.inclusions = None
        self.exclusions = None

    def attachAttr(self, attrDef:AttributeDef):
        akey = attrDef.getKey()
        if akey not in self.attributeDefs:
            self.attributeDefs[akey] = attrDef

    def tostring(self) -> str:
        buf = "<!ELEMEMT %-12s %s" % (self.name, self.model.tostring())
        if self.inclusions: buf += "\n    +(%s)" % " | ".join(self.inclusions)
        if self.exclusions: buf += "\n    -(%s)" % " | ".join(self.exclusions)
        buf += ">\n"
        # TODO Issue attlist alongside element dcl?
        return buf

    # Integrate the validator


###############################################################################
#
class EntityType(FlexibleEnum):
    GENERAL = 1
    PARAMETER = 2
    NOTATION = 4  # Treat as special entity, or not?

    # Names for possible extensions
    SDATA = 8
    NAMESET = 16

class EntityParseType(FlexibleEnum):  # Includes extras...
    NDATA   = 0
    CDATA   = 1
    RCDATA  = 2
    PCDATA  = 3

    # Names for possible additions
    XINCLUDE = 100
    SUBDOC   = 101
    STARTTAG = 102
    ENDTAG   = 103
    PI       = 104
    XMSKEY   = 105

class DataSource:
    """PUBLIC and/or SYSTEM identifier or (for ENTITY but not NOTATION) QLit.
    """
    def __init__(self,
        literal:str=None,
        publicId:str=None,
        systemId:Union[str, List]=None):
        self.literal = literal
        self.publicId = publicId
        if not isinstance(systemId, List): systemId = [ systemId ]
        self.systemId = systemId

    def tostring(self) -> str:
        if self.literal:
            return '"%s"' % (XStr.escapeAttribute(self.literal))
        if self.publicId:
            src = 'PUBLIC "%s"' % (XStr.escapeAttribute(self.literal))
        else:
            src = 'SYSTEM'
        if not self.systemId:
            src += ' ""'
        else:
            for s in self.systemId:
                src += ' "%s"' % (XStr.escapeAttribute(s.literal))
        return src

class EntityDef:
    """Any of several subtypes.
    """
    def __init__(self, name:NMTOKEN_t,
        etype:EntityType,
        dataSource:DataSource,
        parseType:EntityParseType=EntityParseType.PCDATA,
        notation:NMTOKEN_t=None,
        ownerSchema:'DocumentType'=None,
        readOrder:int=0
        ):
        self.name = name
        self.etype = etype
        self.dataSource = dataSource
        self.parseType = parseType
        self.notation = notation
        self.localPath = None
        self.ownerSchema = ownerSchema
        self.readOrder = readOrder

    def tostring(self) -> str:
        src = self.dataSource.tostring()
        pct = "% " if self.etype == EntityType.PARAMETER else ""
        return "<!ENTITY %s%s %s>\n" % (pct, self.name, src)

class Notation:
    """This is for data notation/format applicable to entities. They are normally
    embedded by declaring an external file or object as an ENTITY, and then
    mentioning that entity name (not actually referencing the entity) as
    the value of an attribute that was declared as being of type ENTITY.
    """
    def __init__(self, name:NMTOKEN_t, dataSource:DataSource,
        ownerSchema:'DocumentType'=None, readOrder:int=0):
        if dataSource.literal is not None:
            raise SyntaxError("NOTATION {nname} has QLit, not PUBLIC or SYSTEM.")
        self.name = name
        self.dataSource = dataSource
        self.ownerSchema = ownerSchema
        self.readOrder = readOrder

    def tostring(self) -> str:
        return "<!NOTATION %-12s %s>\n" % (self.name, self.dataSource.tostring())


###############################################################################
#
class DocumentType(Node):
    """Just a stub for the moment.
    See also Schemas.py and https://docs.python.org/3.8/library/xml.dom.html
    TODO Also keep track of who was defined by which ATTLISTs.
    """
    def __init__(self, qualifiedName:QName_t=None,
        publicId:str='', systemId:str='', htmlEntities:bool=True):
        super().__init__(nodeName="#doctype")
        self.nodeType = NodeType.DOCUMENT_TYPE_NODE

        self.name = self.nodeName = qualifiedName  # TODO Get from DOCTYPE
        self.publicId = publicId  # TODO Switch to DataSource
        self.systemId = systemId
        self.htmlEntities = htmlEntities

        self.elementDefs:dict[NMTOKEN_t, 'ElementDef'] = {}
        self.attributeDefs:dict[NMTOKEN_t, AttributeDef] = {}  # NamedNodeMap() later if needed
        self.attlistDefs:list[AttlistDef] = []

        # These are all considered subtypes of entity here:
        self.entityDefs:Dict[NMTOKEN_t, 'EntityDef'] = {}
        self.pentityDefs:Dict[NMTOKEN_t, 'EntityDef'] = {}
        self.notationDefs:Dict[NMTOKEN_t, 'EntityDef'] = {}
        self.nameSetDefs:Dict[NMTOKEN_t, set] = {}  # Accommodation for schema maintenance

    def connectAttributes(self):
        """Ensure that each attribute is listed under all available elements.
        AttlistDef objects know their attributes, but not vice versa.
        TODO Should we create dummy element defs?
        TODO What about * and ##any?
        """
        for attributeDef in self.attributeDefs.items():
            if attributeDef.ename not in self.elementDefs: continue
            edef = self.elementDefs[attributeDef.ename]
            if attributeDef.aname not in edef.attributeDefs:
                edef.attributeDefs[attributeDef.aname] = attributeDef

    @property
    def nodeValue(self) -> str:
        return None

    def after(self, stuff:List) -> None:
        """Inserts a set of Node or string objects in the child list of the
        parent, just after this node.
        """
        par = self.parentNode
        rsib = self.nextSibling
        if rsib:
            rsib.before(stuff)
        else:
            for thing in stuff:
                par.appendChild(thing)

    def before(self, stuff:List) -> None:
        """Inserts a set of Node or string objects in the child list of the
        parent, just before this node.
        """
        par = self.parentNode
        for thing in stuff:
            par.insertBefore(self, thing)

    def removeNode(self) -> None:
        """Removes this object from its parent child list.
        """
        par = self.parentNode
        par.removeChild(self)

    def replaceWith(self, stuff:List) -> None:
        """Replaces the document type with a set of given nodes.
        """
        raise NSuppE

    ####### EXTENSIONS

    def reindex(self) -> None:
        self.elementDefs = {}
        self.attlistDefs = []
        self.attributeDefs = {}
        self.entityDefs = {}
        self.pentityDefs = {}
        self.notationDefs = {}
        self.nameSetDefs = {}

        for ch in self.childNodes:
            if isinstance(ch, ElementDef): self.elementDefs[ch.name] = ch
            elif isinstance(ch, AttributeDef): self.attributeDefs[ch.name] = ch
            elif isinstance(ch, EntityDef):
                self.entityDefs[ch.etype][ch.name] = ch
            else:
                assert False, "Unknown declaration type %s." % (type(ch))
        return

    # ELEMENT
    def getElementDef(self, name:NMTOKEN_t) -> ElementDef:
        return self.elementDefs[name] if name in self.elementDefs else None

    def defineElement(self, name:NMTOKEN_t, modelInfo):
        assert name not in self.elementDefs
        self.elementDefs[name] = modelInfo

    # Attribute
    def getAttributeDef(self, ename:NMTOKEN_t, aname:NMTOKEN_t) -> AttributeDef:
        if ename not in self.elementDefs: return None
        edef = self.elementDefs[ename]
        if aname in edef.attributeDefs: return edef.attributeDefs[aname]
        return None

    def defineAttribute(self, ename:NMTOKEN_t, aname:NMTOKEN_t,
        atype:NMTOKEN_t="CDATA", adefault:NMTOKEN_t="IMPLIED") -> None:
        assert aname not in self.attributeDefs
        self.elementDefs[(ename)].attributeDefs[aname] = [ atype, adefault ]

    # Entity (subtypes for General, Parameter, Notation, and NameSet)
    def getEntityDef(self, name:NMTOKEN_t) -> EntityDef:
        return self.entityDefs[name] if name in self.entityDefs else None

    def defineEntity(self, name:NMTOKEN_t,
        literal:str=None, publicId:str=None, systemId:str=None,
        parseType:EntityParseType=EntityParseType.PCDATA, notation:NMTOKEN_t=None) -> None:
        assert name not in self.entityDefs
        assert isinstance(parseType, EntityParseType)
        ds = DataSource(literal, publicId, systemId)
        self.entityDefs[name] = EntityDef(name, EntityType.GENERAL,
            dataSource=ds, parseType=parseType, notation=notation)

    def getPEntityDef(self, name:NMTOKEN_t) -> EntityDef:
        return self.pentityDefs[name] if name in self.pentityDefs else None

    def definePEntity(self, name:NMTOKEN_t,
        literal:str=None, publicId:str=None, systemId:str=None) -> None:
        assert name not in self.pentityDefs
        self.entityDefs[name] = EntityDef(name,
            EntityType.PARAMETER, literal, publicId, systemId)

    def getNotationDef(self, name:NMTOKEN_t) -> EntityDef:
        return self.notationDefs[name] if name in self.notationDefs else None

    def defineNotation(self, name:NMTOKEN_t,
        literal:str=None, publicId:str=None, systemId:str=None) -> None:
        assert name not in self.notationDefs
        self.notationDefs[name] = EntityDef(name,
            EntityType.NOTATION, literal, publicId, systemId)

    # Basic operations
    #
    def cloneNode(self, deep:bool=False) -> 'Node':
        newNode = DocumentType(
            qualifiedName=self.name,
            publicId = self.publicId,
            systemId = self.systemId
        )
        if deep: newNode.elementDefs = self.elementDefs.deepcopy()
        else: newNode.elementDefs = self.elementDefs.copy()
        return newNode

    def isEqualNode(self, n2) -> bool:  # DocumentType
        if self.nodeType != n2.nodeType: return False
        #if (self.nodeName != n2.nodeName or
        #    self.publicId != n2.publicId or
        #    self.systemId != n2.systemId): return False
        docel1 = self.ownerDocument.documentElement
        docel2 = n2.ownerDocument.documentElement
        if not docel1.isEqualNode(docel2): return False
        return True

    ####### EXTENSIONS

    @property
    def outerXML(self) -> str:
        """TODO: Preserve input order
        """
        return self.toprettyxml()

    def tostring(self) -> str:
        buf = ('<!DOCTYPE %s PUBLIC "%s" "%s" [\n') % (
            self.nodeName, self.publicId, self.systemId)

        for pent in sorted(self.pentityDefs):
            buf += pent.toprettyxml()

        for notn in sorted(self.notationDefs):
            buf += notn.toprettyxml()

        for ent in sorted(self.entityDefs):
            buf += ent.toprettyxml()

        attrsDone = defaultdict(int)
        for elem in sorted(self.elementDefs):
            buf += elem.toprettyxml()
            if elem.name in self.attributeDefs:
                buf += self.attributeDefs[elem.name].toprettyxml()
                attrsDone[elem.name] = True

        for attr in self.attributeDefs:
            if attr.name in attrsDone: continue
            buf += self.attributeDefs[attr.name].toprettyxml()

        buf += "]>\n"
        return buf

    # end class DocumentType

DocType = Doctype = DocumentType
