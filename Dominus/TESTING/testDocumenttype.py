#!/usr/bin/env python3
#
#pylint: disable=W0201, C2801
#
import unittest
import re
import datetime

from runeheim import CaseHandler
from xsdtypes import facetCheck, XsdFacet, DateTimeFrag, Duration
from documenttype import (
    DocumentType, SimpleType, ComplexType, SeqType,
    ElementDef, RepType, ModelGroup, ModelItem, Model,
    AttrDef, DftType, EntityDef, EntitySpace, EntityParsing)
import xsparser
#from ragnaroktypes import HierarchyRequestError
#from ragnaroktypes import NotFoundError

from makeTestDoc import makeTestDocEachMethod, DBG
import test4


###############################################################################
# Parameter entity cases
#     (Have to put DOCTYPE around all these)
#
GoodPESamples = [
"""<!-- hello? -->
<!ENTITY % foo "<!ELEMENT q ANY>">
%foo;
<!ENTITY % bar "
    <!ATTLIST q ID #IMPLIED>
    <!ATTLIST i ID #IMPLIED>">
%bar;
]>
""",
]

BadPESamples = [

### Broken comment close
"""
<!-- bad place to stop --
>""",

### No PE for element name in XML
"""
<!ENTITY % foo "para">
<!ELEMENT %foo; ANY>
""",

### No PE for attr name in XML
"""<!ENTITY % foo "id">
<!ELEMENT para ANY>
<!ATTLIST para %foo; ID #IMPLIED>
""",

### No PE for attr type in XML
"""<!ENTITY % foo "ID">
<!ELEMENT para ANY>
<!ATTLIST para id %foo; #IMPLIED>
""",

### No PE for attr default in XML
"""<!ENTITY % foo "#IMPLIED">
<!ELEMENT para ANY>
<!ATTLIST para id ID %foo;>
""",

### No empty PE either (?)
"""<!ENTITY % foo "">
<!ELEMENT para ANY>
<!ATTLIST para id ID %foo; #IMPLIED>
""",

"""<!ENTITY % foo "   ">
<!ATTLIST para id %foo; ID #IMPLIED>
""",

### How about inside a qlit?
"""
<!ENTITY % foo "'text'">
<!ENTITY zark "hello, %foo; world.">
""",
]


###############################################################################
# Element declaration cases
#     (Have to put DOCTYPE around all these)
#
GoodElementSamples = [
    "<!ELEMENT itemizedlist (listitem*)>",
    "<!ELEMENT orderedlist (listitem*) >",
    "<!ELEMENT\tlistitem (para*)>",
    "<!ELEMENT para  (#PCDATA)>",
    "<!ELEMENT li    (#PCDATA | i | hr|para)*>",
    "<!ELEMENT front (div1+)>",
    "<!ELEMENT body  (div1+)>",
    "<!ELEMENT back  ((div1?, (x | inform-div1)*) | inform-div1+)*>",
    "<!ELEMENT hr    EMPTY    >",
    "<!ELEMENT xy_.z ANY>",
]

BadElementSamples = [
    "<!ELEMENT>",
    "<!ELEMENT -- foo -- p (#PCDATA)>",
    "<!ELEMENT spam >",
    "<!ELEMENT 12    (listitem*)>",
    "<!ELEMENT ol@1  (listitem*) >",
    "<!ELEMENT item  RCDATA>",
    "<!ELEMENT list  (#PCDATA | item)+  +(footnote)>",
    "<!ELEMENT b     #PCDATA>",
    "<!ELEMENT front (ti, 1div*)>",
    "<!ELEMENT body  (ti, div | i | b)*>",
    "<!ELEMENT back  (ti, (div)>",
    "<!ELEMENT spam  (ti, (div) ) ) >",
]


###############################################################################
# Attlist declaration cases
#
GoodAttlistSamples = [
    """<!ATTLIST  p  id ID #IMPLIED  class NMTOKENS "big">""",
    """<!ATTLIST td
    id
    ID
    #IMPLIED
    tgt             IDREF           #IMPLIED
    tgts            IDREFS          "foo bar1.a"
    direction       NMTOKEN         FIXED "up"
    bgcolor         NMTOKENS        "foo
        bar baz"
    rowspan         NUTOKEN         "1"
    colspan         NUMBER          "1"
    alt             CDATA           #REQUIRED
    compass         (n | s | e | w) 'w'
    thePic          ENTITY          "fig1"
    >
    """,
]

BaddAttlistSamples = [
    """<!ATTLIST>""",
    """<!ATTLIST p  >""",
    """<!ATTLIST p id >""",
    """<!ATTLIST p id ID>""",
    """<!ATTLIST 12 id ID #REQUIRED>""",
    """<!ATTLIST p %% ID #REQUIRED>""",
    """<!ATTLIST p vev COMPLEX #REQUIRED>""",
    """<!ATTLIST p id ID #PROHIBITED>""",
    """<!ATTLIST p class NMTOKENS  notQuoted>""",
    """<!ATTLIST p class NMTOKENS  "a""b">""",
    """<!ATTLIST td direction NMTOKEN FIXED up>""",
    """<!ATTLIST loc_ compass (n | s | $12 | w) 'w'>""",
]


###############################################################################
# Entity declaration cases
#
GoodEntitySamples = [
    """<!ENTITY mdash   "--">""",
    """<!ENTITY nbsp    "&#160;">""",
    """<!ENTITY unused  "&#FFF;">""",
    """<!ENTITY ldquo   "#x201C;"   >""",
    """<!ENTITY rdquo   "#x201D;">""",
    """<!ENTITY nested  "'scare quotes'">""",
    """<!ENTITY whee    "'scare">""",
    """<!ENTITY whee2   "&quo;scare&#x22;">""",
    """<!ENTITY % local.p.class        "p">""",
    """<!ENTITY % p.class              "%local.p.class;""",
    """<!ENTITY NASA    "National Aeronautics and Space Administration">""",
    """<!ENTITY chap1   PUBLIC "-//foo" "c:\\docs\\chap1.xml">""",
    """<!ENTITY chap2   SYSTEM "c:\\docs\\chap2.xml">""",
    """<!ENTITY fig1    SYSTEM "/Users/abc/Pictures/img12.jpg" NDATA jpg>""",
]

BadEntitySamples = [
    """<!ENTITY""",
    """<!ENTITY
        """,
    """<!ENTITY
    >""",
    """<!ENTITY mdash  """,
    """<!ENTITY mdash>""",
    """<!ENTITY mdash --foo-->""",
    """<!ENTITY nbsp   "unclosed>""",
    """<!ENTITY nbsp   "unclosed'>""",
    """<!ENTITY ldquo  "&>""",
    """<!ENTITY ldquo  "&#>""",
    """<!ENTITY ldquo  "&#x>""",
    """<!ENTITY ldquo  "&#xFFFFFFFFFFFFFFFFFF;">""",
    """<!ENTITY chap1  PRIVATE "">""",
    """<!ENTITY chap1  PUBLIC>""",
    """<!ENTITY chap1  PUBLIC "-//foo">""",
    """<!ENTITY chap1  PUBLIC "-//foo" ">""",
    """<!ENTITY chap1  PUBLIC "-//foo" "nil.xml" NDATA >""",
    """<!ENTITY chap2  SYSTEM >""",
    """<!ENTITY chap2  SYSTEM "xxx>""",
    """<!ENTITY fig1   SYSTEM "/Users/abc/Pictures/img12.jpg" NDATA 12>""",
]


###############################################################################
# Notation declaration cases
#
GoodNotationSamples = [
    """<!NOTATION jpg PUBLIC "+//ISO99999/Data Formats/JPEG//" "">""",
]

BadNotationSamples = [
    """<!NOTATION""",
    """<!NOTATION>""",
    """<!NOTATION jpg >""",
    """<!NOTATION jpg SYSTEM>""",
    """<!NOTATION jpg SYSTEM '>""",
    """<!NOTATION jpg CDATA "nope">""",
    """<!NOTATION #foo SYSTEM 'somewhere'>""",
    """<!NOTATION jpg SYSTEM '>""",
    """<!NOTATION jpg PUBLIC>""",
    """<!NOTATION jpg PUBLIC "+//ISO99999/Data Formats/JPEG//" >""",
    """<!NOTATION jpg PUBLIC "+//ISO99999/Data Formats/JPEG//" ">""",
    """<!NOTATION jpg PUBLIC "+//ISO99999/Data Formats/JPEG//" "">""",
]


###############################################################################
# Extended declaration cases
#
GoodExtensionSample = [
    """<!ELEMENT (i|b |tt| mono )  (#PCDATA)>""",
    """<!ELEMENT - O para ANY>""",
    """<!ELEMENT para ANY  +(footnote) -(para)>""",
    """<!ELEMENT para ANYELEMENT>""",
    """<!ELEMENT para (head, leader{1,99})>""",
    """<!ELEMENT para CDATA>""",
    """<!ELEMENT para RCDATA>""",
    """<!ATTLIST para
        a1      COID    #IMPLIED
        a2      STACKID #IMPLIED
        a3      float   #IMPLIED
        a4      gMonthDay   "---03-15"
        a5      curls   “foo”
        a6      floats  "1.608 3.14"
        a7      float   "NaN"

        >""",
    """<!ATTLIST ?troff width NUTOKEN "12">""",
    """<!— emComment? —>""",
    """<!ATTLIST para  #ANY CDATA #IMPLIED>""",
    """<!ATTLIST * id ID #IMPLIED>""",
    """<!SDATA nbsp "&#160;">""",
    """<!SDATA nbsp 160 z 0x9D...>""",
]


###############################################################################
#
class testAttrDef(unittest.TestCase):
    def setup(self):
        pass

    def testxsdTypes(self):
        #self.assertFalse(facetCheck("", "base64Binary"))
        #self.assertFalse(facetCheck("", "hexBinary"))

        self.assertFalse(facetCheck("true", "boolean"))
        self.assertFalse(facetCheck("false", "boolean"))
        self.assertFalse(facetCheck("1", "boolean"))
        self.assertFalse(facetCheck("0", "boolean"))

        self.assertFalse(facetCheck("127", "byte"))
        self.assertFalse(facetCheck("-128", "byte"))
        self.assertFalse(facetCheck("32767", "short"))
        self.assertFalse(facetCheck("-32768", "short"))
        self.assertFalse(facetCheck("999999", "int"))
        self.assertFalse(facetCheck("-999999", "long"))

        self.assertFalse(facetCheck("-999999", "integer"))
        self.assertFalse(facetCheck("-999999", "nonPositiveInteger"))
        self.assertFalse(facetCheck("-999999", "negativeInteger"))
        self.assertFalse(facetCheck("999999", "nonNegativeInteger"))
        self.assertFalse(facetCheck("999999", "positiveInteger"))
        self.assertFalse(facetCheck("99", "unsignedByte"))
        self.assertFalse(facetCheck("+000000000000000009999", "unsignedShort"))
        self.assertFalse(facetCheck("999999", "unsignedInt"))
        self.assertFalse(facetCheck("999999", "unsignedLong"))

        self.assertFalse(facetCheck("-3.141592653589793238462643383", "decimal"))
        self.assertFalse(facetCheck("9876.54321", "double"))
        self.assertFalse(facetCheck("9876.54321", "float"))

        self.assertFalse(facetCheck("---31", "gDay"))
        self.assertFalse(facetCheck("--01Z", "gMonth"))
        self.assertFalse(facetCheck("--12", "gMonth"))
        self.assertFalse(facetCheck("--12-31", "gMonthDay"))
        self.assertFalse(facetCheck("2024", "gYear"))
        self.assertFalse(facetCheck("9999", "gYear"))
        # TODO self.assertFalse(facetCheck("-999999", "gYear"))  # Yes, this is valid
        self.assertFalse(facetCheck("2024-01", "gYearMonth"))
        self.assertFalse(facetCheck("2024-02-29", "date"))
        self.assertFalse(facetCheck("2024-02-20T11:12:59", "dateTime"))
        self.assertFalse(facetCheck("2024-02-29T11:59:59.214Z", "dateTime"))
        self.assertFalse(facetCheck("11:59:59.214Z", "time"))
        # Leap second test seems to fail on casting...
        self.assertFalse(facetCheck("11:59:60", "time"))  # Leap seconds

        durString = "P1Y2M3DT4H3.1415S"
        self.assertFalse(facetCheck(durString, "duration"))
        dur = Duration(durString)
        self.assertEqual(re.sub(r"(\.\d*?)0+S$", "\\1S", dur.tostring()), durString)

        self.assertFalse(facetCheck("EN-UK", "language"))
        self.assertFalse(facetCheck("a   b   c", "normalizedString"))
        self.assertFalse(facetCheck("aard%VARK", "string"))
        self.assertFalse(facetCheck("noSpaces", "token"))
        self.assertFalse(facetCheck("https://example.com/docs/foo.xml#chap1", "anyURI"))
        self.assertFalse(facetCheck("Sub-Para_3", "Name"))
        self.assertFalse(facetCheck("xyzzy", "NCName"))
        self.assertFalse(facetCheck("foo:xyzzy", "QName"))
        self.assertFalse(facetCheck("an_ID_VALUE", "ID"))
        self.assertFalse(facetCheck("an_ID_VALUE", "IDREF"))
        self.assertFalse(facetCheck("blockquote", "NMTOKEN"))
        self.assertFalse(facetCheck("bull", "ENTITY"))

        #TODO Special facet checks:
        #self.assertFalse(facetCheck("thing1 thing2", "IDREFS"))
        #self.assertFalse(facetCheck("ul ol dl", "NMTOKENS"))
        #self.assertFalse(facetCheck("chap1 chap2 chap3 chap4", "ENTITIES"))


    def testxsdTypesFail(self):
        """facetCheck() returns *which* facet was violated. Of course, a value
        could violate several at once, so the expected result could change
        if the order of checking changes (or could change it to return a
        set of all violated facets).

        TODO: Add more checks for violations other than XsdFacet.pattern
        """
        with self.assertRaises(TypeError):
            facetCheck("99", int)
            facetCheck("Q", "notAnXSDType")
            facetCheck("Q", "  int  sxs")
            facetCheck(None, "boolean")
            facetCheck(12.4+1.1j, "short")

        #self.assertTrue(facetCheck("xyzzy", "base64Binary"))
        #self.assertTrue(facetCheck("xyzzy", "hexBinary"))

        self.assertEqual(facetCheck("Q", "boolean"), XsdFacet.pattern)
        self.assertEqual(facetCheck("True", "boolean"), XsdFacet.pattern)
        self.assertEqual(facetCheck("False", "boolean"), XsdFacet.pattern)
        self.assertEqual(facetCheck("#T", "boolean"), XsdFacet.pattern)

        self.assertEqual(facetCheck("abc", "byte"), XsdFacet.pybase)  # etc?
        self.assertEqual(facetCheck("128", "byte"), XsdFacet.maxInclusive)
        self.assertEqual(facetCheck("-129", "byte"), XsdFacet.minInclusive)
        self.assertEqual(facetCheck("32768", "short"), XsdFacet.maxInclusive)
        self.assertEqual(facetCheck("-32769", "short"), XsdFacet.minInclusive)
        self.assertEqual(facetCheck("9999999999999", "int"), XsdFacet.maxInclusive)
        self.assertEqual(facetCheck("True", "long"), XsdFacet.pybase)

        self.assertEqual(facetCheck("abcdef", "integer"), XsdFacet.pybase)
        self.assertEqual(facetCheck("99", "nonPositiveInteger"), XsdFacet.pattern)
        self.assertEqual(facetCheck("999999", "negativeInteger"), XsdFacet.pattern)
        self.assertEqual(facetCheck("-999999", "nonNegativeInteger"), XsdFacet.pattern)
        self.assertEqual(facetCheck("0", "positiveInteger"), XsdFacet.pattern)
        self.assertEqual(facetCheck("-99", "unsignedByte"), XsdFacet.pattern)
        self.assertEqual(facetCheck("-000000000000999999999", "unsignedShort"),
            XsdFacet.pattern)
        self.assertEqual(facetCheck("-1", "unsignedInt"), XsdFacet.pattern)
        self.assertEqual(facetCheck("-12", "unsignedLong"), XsdFacet.pattern)

        self.assertEqual(facetCheck("-3.14159xyz", "decimal"), XsdFacet.pybase)
        self.assertEqual(facetCheck("1.2+3.1j", "double"), XsdFacet.pybase)
        with self.assertRaises(TypeError):
            facetCheck(1.2+3.1j, "double")
        self.assertEqual(facetCheck("0xBEEF", "float"), XsdFacet.pybase)

        # Many of the data cases fail on pybase, b/c the DateTimeFrag
        # constructor does a lot of checking on its own.
        self.assertEqual(facetCheck("31", "gDay"), XsdFacet.pattern)
        self.assertEqual(facetCheck("---32", "gDay"), XsdFacet.pattern)
        self.assertEqual(facetCheck("1", "gMonth"), XsdFacet.pattern)
        self.assertEqual(facetCheck("-1", "gMonth"), XsdFacet.pybase)
        self.assertEqual(facetCheck("--20000", "gMonth"), XsdFacet.pybase)
        self.assertEqual(facetCheck("12-41", "gMonthDay"), XsdFacet.pybase)
        self.assertEqual(facetCheck("--12-41", "gMonthDay"), XsdFacet.pybase)
        self.assertEqual(facetCheck("024", "gYear"), XsdFacet.pattern)
        self.assertEqual(facetCheck("0x07E8", "gYear"), XsdFacet.pybase)
        self.assertEqual(facetCheck("2024-00", "gYearMonth"), XsdFacet.pybase)
        self.assertEqual(facetCheck("2024-02-57", "date"), XsdFacet.pattern)
        self.assertEqual(facetCheck("2024-02-29Q11:59:59.214Z", "dateTime"),
            XsdFacet.pybase)
        self.assertEqual(facetCheck("11:59:59.214*2", "time"), XsdFacet.pybase)
        self.assertEqual(facetCheck("11:59:61", "time"), XsdFacet.pybase)
        self.assertEqual(facetCheck("", "duration"), XsdFacet.pybase)

        self.assertEqual(facetCheck("12", "language"), XsdFacet.pattern)
        #self.assertEqual(facetCheck("", "normalizedString"), XsdFacet.pattern)
        #self.assertEqual(facetCheck("", "string"), XsdFacet.pattern)
        # TODO self.assertEqual(facetCheck("a b c", "token"), XsdFacet.pattern)

        # For now, the pattern for anyURI accepts anything...
        #self.assertEqual(facetCheck("example.com/docs/foo.xml#chap1", "anyURI"),
        #    XsdFacet.pattern)

        self.assertEqual(facetCheck("-Sub-Para_3", "Name"), XsdFacet.pattern)
        self.assertEqual(facetCheck("xy:zzy", "NCName"), XsdFacet.pattern)
        #TODO self.assertEqual(facetCheck("foo:xy:zzy", "QName"), XsdFacet.pattern)
        self.assertEqual(facetCheck("-an_ID_VALUE", "ID"), XsdFacet.pattern)
        self.assertEqual(facetCheck("12-a", "IDREF"), XsdFacet.pattern)
        self.assertEqual(facetCheck("blockquote is not", "NMTOKEN"), XsdFacet.pattern)
        self.assertEqual(facetCheck("-12.2", "ENTITY"), XsdFacet.pattern)
        self.assertEqual(facetCheck("thing1 thing2 %", "IDREFS"), XsdFacet.pattern)
        self.assertEqual(facetCheck("ul, ol, dl", "NMTOKENS"), XsdFacet.pattern)
        self.assertEqual(facetCheck("chap1 chap2 @chap4", "ENTITIES"), XsdFacet.pattern)

    def testConversions(self):
        dateStr = "1990-02-22"
        timeStr = "15:02:59Z"
        dtStr = dateStr + "T" + timeStr

        dt1 = DateTimeFrag(dateStr)
        dt2 = dt1.copy()
        self.assertEqual(dt1, dt2)

        pyDate = datetime.date.fromisoformat(dateStr)
        dtfDate = DateTimeFrag(dateStr)
        dtfDate2 = DateTimeFrag()
        dtfDate2.setFromPythonDatetime(pyDate)
        self.assertEqual(dtfDate.tostring(), dtfDate2.tostring())

        pyTime = datetime.time.fromisoformat(timeStr)
        dtfTime = DateTimeFrag(timeStr)
        dtfTime2 = DateTimeFrag()
        dtfTime2.setFromPythonDatetime(timeStr)
        self.assertEqual(dtfTime, dtfTime2)

        pyDT = datetime.datetime.fromisoformat(dtStr)
        dtfDT = DateTimeFrag(dtStr)
        dtfDT2 = DateTimeFrag()
        dtfDT2.setFromPythonDatetime(dtStr)
        self.assertEqual(dtfDT, dtfDT2)

        self.assertEqual(dtfDT.getPythonDate(), pyDate)
        self.assertEqual(dtfDT.getPythonTime(), pyTime)
        self.assertEqual(dtfDT.getPythonDatetime(), pyDT)

        self.assertEqual(dtfDT.getXsdDate(), dateStr)
        self.assertEqual(dtfDT.getXsdTime(), timeStr)
        self.assertEqual(dtfDT.getXsdTzinfo(), dtStr)


###############################################################################
#
class testDateTimeFrag(unittest.TestCase):
    def setUp(self):
        pass

    def testDTF(self):
        dat = "2024-11-13"
        tim = "18:05:59.312Z"

        dtf = DateTimeFrag(dat)
        self.assertIsInstance(dtf, DateTimeFrag)
        self.assertTrue(dtf.check())
        self.assertTrue(dtf.includesDate)
        self.assertFalse(dtf.includesTime)
        self.assertEqual(dtf.year, 2024)
        self.assertEqual(dtf.month, 11)
        # TODO self.assertEqual(dtf.day, 13)
        self.assertIs(dtf.hour, None)
        self.assertIs(dtf.minute, None)
        self.assertIs(dtf.second, None)
        self.assertEqual(dtf.microsecond, None)
        self.assertIs(dtf.zone, None)

        dtf = DateTimeFrag(tim)
        self.assertIsInstance(DateTimeFrag(tim), DateTimeFrag)
        self.assertTrue(dtf.check())
        self.assertFalse(dtf.includesDate)
        self.assertTrue(dtf.includesTime)
        self.assertIs(dtf.year, None)
        self.assertIs(dtf.month, None)
        self.assertIs(dtf.day, None)
        self.assertEqual(dtf.hour, 18)
        self.assertEqual(dtf.minute, 5)
        self.assertEqual(int(dtf.second), 59)
        self.assertTrue(abs(dtf.microsecond - 312000) < 2)
        self.assertEqual(int(dtf.zone), 0)

        dtf = DateTimeFrag(dat+"T"+tim)
        self.assertIsInstance(DateTimeFrag(), DateTimeFrag)
        self.assertTrue(dtf.check())
        self.assertTrue(dtf.includesDate)
        self.assertTrue(dtf.includesTime)
        self.assertEqual(dtf.year, 2024)
        self.assertEqual(dtf.month, 11)
        # TODO self.assertEqual(dtf.day, 13)
        #self.assertEqual(dtf.day, 0)
        self.assertEqual(dtf.hour, 18)
        self.assertEqual(dtf.minute, 5)
        self.assertEqual(int(dtf.second), 59)
        self.assertTrue(abs(dtf.microsecond - 312000) < 2)
        self.assertEqual(int(dtf.zone), 0)

        dtf2 = DateTimeFrag()
        #TODO self.assertFalse(dtf.includesDate)
        #self.assertFalse(dtf.includesTime)
        self.assertTrue(dtf.check())

        self.assertTrue(dtf2.set_datetime(dat+"T"+tim))
        self.assertTrue(dtf2.set_date(dat))
        self.assertTrue(dtf2.set_time(tim))
        self.assertTrue(dtf2.set_gYear("1999"))
        self.assertTrue(dtf2.set_gYearMonth("1999-10"))
        self.assertTrue(dtf2.set_gMonthDay("--08-31"))
        self.assertTrue(dtf2.set_gMonth("--08"))
        self.assertTrue(dtf2.set_gDay("---01"))
        self.assertTrue(dtf2.set_zone("+05:30"))

        # TODO Check values w/ get
        #self.assertEqual(dtf2.get_date(), "1999-08-31")
        #self.assertEqual(dtf2.get_gYear(), "1999")
        #self.assertEqual(dtf2.get_gYearMonth(), "1999-10")
        #self.assertEqual(dtf2.get_gMonthDay(), "--08-31")
        #self.assertEqual(dtf2.get_gMonth(), "--08")
        #self.assertEqual(dtf2.get_gDay(), "---01")
        #self.assertEqual(dtf2.get_zone(), "+05:30")  # ???
        #self.assertEqual(dtf2.get_datetime(), "1999-08-31T00:00:00")

        #self.assertEqual(dtf2.get_time(tim), "18:05:59.312Z")


###############################################################################
#
class testSCType(unittest.TestCase):
    def test_simpletype(self):
        st = SimpleType(name="p", baseType=None)
        self.assertEqual(st.caseTx, CaseHandler.NONE)

        ct = ComplexType(name="p", baseType=None, model=Model(contentType="ANY"))
        self.assertEqual(len(ct.attrDefs), 0)


###############################################################################
#
class testModel(unittest.TestCase):
    """ModelGroup takes raw tokens, including operators, unlike ModelGroup.
    Also unlike ModelGroup, it handles declared content types.
    """
    def test_model(self):
        self.assertTrue(Model(contentType="ANY"))
        self.assertTrue(Model(contentType="EMPTY", tokens=None))
        self.assertTrue(Model(contentType="X_MODEL",
            tokens = [ "(", "#PCDATA", ")" ]))
        self.assertTrue(Model(contentType="X_MODEL",
            tokens = [ "(", "title", ",", "p", "*", ")" ]))
        self.assertTrue(Model(contentType="X_MODEL",
            tokens = [ "(", "#PCDATA", "|", "i", "|", "b", ")", "*" ]))

class testModelGroup(unittest.TestCase):
    """ModelGroup takes children+seq+rep, unlike (top-level) Model
    (children can be ModelGroups and/or ModelItems)
    """
    def test_model_group(self):
        self.assertIsInstance(ModelGroup(
            childItems=[ "i", "b", "tt" ], seq=SeqType.CHOICE, rep=RepType.PLUS),
            ModelGroup)
        self.assertIsInstance(ModelGroup(
            childItems=[ "i", "b", "tt" ], seq=",", rep="*"),
            ModelGroup)
        self.assertIsInstance(ModelGroup(
            childItems=[ "i", "b", "tt" ], seq="&", rep=""),
            ModelGroup)
        self.assertIsInstance(ModelGroup(
            childItems=[ "#PCDATA", "i", "b", "tt" ], seq="|", rep="?"),
            ModelGroup)
        mg = ModelGroup(
            childItems=[ "i", "b", "tt" ], seq=",", rep=RepType.X_BOUNDS)
        mg.rep.setBounds(minOccurs=5, maxOccurs=9)
        self.assertIsInstance(mg, ModelGroup)


class testModelItem(unittest.TestCase):
    def test_model_group(self):
        self.assertIsInstance(ModelItem(name="i", rep=RepType.PLUS), ModelItem)
        self.assertIsInstance(ModelItem(name="#PCDATA", rep=RepType.QUEST), ModelItem)
        self.assertIsInstance(ModelItem(name="_b.12", rep=RepType.STAR), ModelItem)
        self.assertIsInstance(ModelItem(name="hr", rep=RepType.NOREP), ModelItem)


class testAttrDef2(unittest.TestCase):
    def setup(self):
        pass

    def testAtDef(self):
        #pylint: disable=W0612
        # First the usual SGML-based ones
        #
        a1 = AttrDef(elemNS=None, elemName=None, attrNS=None, attrName="id",
            attrType="ID", attrDft=DftType.IMPLIED)
        a2 = AttrDef(elemNS=None, elemName=None, attrNS=None, attrName="class",
            attrType="NMTOKENS", attrDft=DftType.IMPLIED)
        a3 = AttrDef(elemNS=None, elemName=None, attrNS=None, attrName="font-family",
            attrType="NMTOKEN", attrDft=DftType.IMPLIED)
        a4 = AttrDef(elemNS=None, elemName=None, attrNS=None, attrName="alt",
            attrType="CDATA", attrDft="#REQUIRED")

        a5 = AttrDef(elemNS=None, elemName=None, attrNS=None, attrName="version",
            attrType="NUTOKEN", attrDft="#FIXED", literal="THE_FIXED_VALUE")
        a6 = AttrDef(elemNS=None, elemName=None, attrNS=None, attrName="Author.Of-it",
            attrType="NUTOKEN", attrDft="#FIXED")

        a7 = AttrDef(elemNS=None, elemName=None, attrNS=None, attrName="target",
            attrType="IDREF", attrDft=DftType.IMPLIED)
        a8 = AttrDef(elemNS=None, elemName=None, attrNS=None, attrName="targets",
            attrType="IDREFS", attrDft=DftType.IMPLIED)
        a9 = AttrDef(elemNS=None, elemName=None, attrNS=None, attrName="format",
            attrType="NOTATION", attrDft=DftType.IMPLIED)
        a10 = AttrDef(elemNS=None, elemName=None, attrNS=None, attrName="object",
            attrType="ENTITY", attrDft=DftType.IMPLIED)
        a11 = AttrDef(elemNS=None, elemName=None, attrNS=None, attrName="objects",
            attrType="ENTITIES", attrDft=DftType.IMPLIED)

        a12 = AttrDef(elemNS=None, elemName=None, attrNS=None, attrName="orth",
            attrType="( LAT GRK ENG )", attrDft=DftType.IMPLIED)

        # Now with namespaces and element assigments
        svgNS = "http://www.w3.org/2000/svg"
        b1 = AttrDef(elemNS=None, elemName=None, attrNS="svg", attrName="path",
            attrType="CDATA", attrDft=DftType.IMPLIED)
        b1 = AttrDef(elemNS=svgNS, elemName="g", attrNS=svgNS, attrName="x",
            attrType="NUTOKEN", attrDft=DftType.IMPLIED)


class testElementDefs(unittest.TestCase):
    def setup(self):
        pass

    def testElDef(self):
        m = Model(contentType="X_MODEL",
            tokens = [ "(", "#PCDATA", "|", "i", "|", "b", ")", "*" ])
        el = ElementDef("para", m)
        self.assertIsInstance(el, ElementDef)

        a1 = AttrDef(elemNS=None, elemName=None, attrNS=None, attrName="id",
            attrType="ID", attrDft=DftType.IMPLIED)
        el.attachAttr(a1)


###############################################################################
#
class testEntityDef(unittest.TestCase):
    def setUp(self):
        pass

    def aEQ(self, x, y):
        if x != y:
            print("Fail: Not equal:\n    //%s//\n    //%s//" % (x, y))
        self.assertEqual(x, y)

    def testEnDef(self):
        lit1 = "<warn>Do not fold, spindle, or mutilate.</warn>"
        sys1 = "/home/jsmith/docs/foo.xml"
        pub1 = "-//foo//bar//EN"
        sys2 = "/foo.xml"

        # Some kinds of identifiers
        ds1 = EntityDef("ds1", entSpace=EntitySpace.GENERAL, data=lit1)
        self.aEQ(ds1.tostring(),
            """<!ENTITY ds1 "<warn>Do not fold, spindle, or mutilate.</warn>">\n""")

        ds2 = EntityDef("ds2", entSpace=EntitySpace.GENERAL, systemId=sys1)
        self.aEQ(ds2.tostring(),
            """<!ENTITY ds2 SYSTEM "/home/jsmith/docs/foo.xml">\n""")

        ds3 = EntityDef("ds3", entSpace=EntitySpace.GENERAL, publicId=pub1, systemId=sys2)
        self.aEQ(ds3.tostring(),
            """<!ENTITY ds3 PUBLIC "-//foo//bar//EN" "/foo.xml">\n""")

        ds4 = EntityDef("ds4", entSpace=EntitySpace.GENERAL, systemId=[ sys1, sys2 ])
        self.aEQ(ds4.tostring(),
            """<!ENTITY ds4 SYSTEM "/home/jsmith/docs/foo.xml" "/foo.xml">\n""")

        # By space/type
        e1 = EntityDef("ent0", entSpace=EntitySpace.GENERAL, data=lit1,
            entParsing=EntityParsing.PCDATA, notationName=None, ownerSchema=None)
        self.aEQ(e1.tostring(),
            """<!ENTITY ent0 "<warn>Do not fold, spindle, or mutilate.</warn>">\n""")

        e2 = EntityDef("ent1", entSpace=EntitySpace.PARAMETER, systemId=sys1,
            entParsing=EntityParsing.PCDATA, notationName=None, ownerSchema=None)
        self.aEQ(e2.tostring(),
            """<!ENTITY % ent1 SYSTEM "/home/jsmith/docs/foo.xml">\n""")

        e3 = EntityDef("ent2", entSpace=EntitySpace.NOTATION, publicId=pub1,
            entParsing=EntityParsing.PCDATA, notationName=None, ownerSchema=None)
        self.aEQ(e3.tostring(),
            """<!ENTITY ent2 PUBLIC "-//foo//bar//EN" "">""")

        #e4 = EntityDef("ent3", EntityType.SDATA, systemID=sys1, publicId=pub1,
        #    entParsing=EntityParsing.PCDATA, notationName=None, ownerSchema=None)
        #self.aEQ(e4.tostring(), "")

        #e5 = EntityDef("ent4", EntityType.NAMESET, data=lit1,
        #    entParsing=EntityParsing.PCDATA, notationName=None, ownerSchema=None)
        #self.aEQ(e5.tostring(), "")

        # By parseType
        p1 = EntityDef("ent5", entSpace=EntitySpace.GENERAL, data=lit1,
            entParsing=EntityParsing.PCDATA, notationName=None, ownerSchema=None)
        self.aEQ(p1.tostring(), "")
        p2 = EntityDef("ent1", entSpace=EntitySpace.GENERAL, data=lit1,
            entParsing=EntityParsing.NDATA, notationName=None, ownerSchema=None)
        self.aEQ(p2.tostring(), "")
        p3 = EntityDef("ent1", entSpace=EntitySpace.GENERAL, data=lit1,
            entParsing=EntityParsing.CDATA, notationName=None, ownerSchema=None)
        self.aEQ(p3.tostring(), "")
        p4 = EntityDef("ent1", entSpace=EntitySpace.GENERAL, data=lit1,
            entParsing=EntityParsing.RCDATA, notationName=None, ownerSchema=None)
        self.aEQ(p4.tostring(), "")

        # TODO Extensions?

        # Add notation, ownerSchema, etc.

    def test_general(self):
        pass

    def test_parameter(self):
        pass


###############################################################################
#
class testNotationDef(unittest.TestCase):
    def setUp(self):
        madeDocObj = makeTestDocEachMethod(dc=test4.DAT_K)
        self.dc = test4.DAT_K
        self.n = madeDocObj.n

    def tests(self):
        doctype = DocumentType(qualifiedName=None,
            publicId=None, systemId=None, htmlEntities=True)
        self.n.doc.doctype = doctype
        self.assertIsInstance(self.n.doc.doctype, DocumentType)
        nn = self.n.doc.doctype.defineNotation(
            "nname", publicId="-//foo", systemId="http://example.com/png")
        el = self.n.docEl.childNodes[5]
        el.setAttribute("notn", nn)
        return


###############################################################################
#
class testPEs(unittest.TestCase):

    def setUp(self):
        madeDocObj = makeTestDocEachMethod(dc=test4.DAT_K)
        self.dc = test4.DAT_K
        self.n = madeDocObj.n

    def testgoods(self):
        for i, s in enumerate(GoodPESamples):
            print("Starting GoodPESamples[%s]" % (i))
            p = xsparser.ParserCreate()
            p.Parse(s)  # TODO Make a DOM?
            #self.assertTrue(theDom.doctype.entities("foo"))

    def testbads(self):
        for i, s in enumerate(BadPESamples):
            print("Starting BadPESamples[%s]" % (i))
            with self.assertRaises(SyntaxError):
                p = xsparser.ParserCreate()
                p.Parse(s)


###############################################################################
#
@unittest.skip
class testDcls(unittest.TestCase):
    def setUp(self):
        DBG.msg("testWholeDoctype not yet written.")
        madeDocObj = makeTestDocEachMethod(dc=test4.DAT_K)
        self.dc = test4.DAT_K
        self.n = madeDocObj.n

    def testElementDcls(self):
        for dcl in GoodElementSamples:
            xml = """<!DOCTYPE foo [\n%s\n]>""" % (dcl)
            p = xsparser.ParserCreate()
            p.Parse(xml)

    def testAttlistDcls(self):
        for dcl in GoodAttlistSamples:
            xml = """<!DOCTYPE foo [\n%s\n]>""" % (dcl)
            p = xsparser.ParserCreate()
            p.Parse(xml)

    def testEntityDcls(self):
        for dcl in GoodEntitySamples:
            xml = """<!DOCTYPE foo [\n%s\n]>""" % (dcl)
            p = xsparser.ParserCreate()
            p.Parse(xml)

    def testNotationDcls(self):
        for dcl in GoodNotationSamples:
            xml = """<!DOCTYPE foo [\n%s\n]>""" % (dcl)
            p = xsparser.ParserCreate()
            p.Parse(xml)


###############################################################################
#
@unittest.skip
class testWholeDoctype(unittest.TestCase):
    def setUp(self):
        DBG.msg("testWholeDoctype not yet written.")
        madeDocObj = makeTestDocEachMethod(dc=test4.DAT_K)
        self.dc = test4.DAT_K
        self.n = madeDocObj.n

    def tests(self):
        nn = self.n.doc.doctype.defineNotation(
            "nname", publicId="-//foo", systemId="http://example.com/png")
        el = self.n.docEl.childNodes[5]
        el.setAttribute("notn", nn)
        return

if __name__ == '__main__':
    unittest.main()
