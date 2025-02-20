#!/usr/bin/env python3
#
#pylint: disable=W0201, C2801
#
import unittest
import re
import datetime

from xmlstrings import CaseHandler
from xsdtypes import facetCheck, XsdFacet, DateTimeFrag, Duration
from documenttype import (
    SimpleType, ComplexType, SeqType,
    ElementDef, RepType, ModelGroup, ModelItem, Model,
    AttributeDef, DftType, EntityDef, EntitySpace, EntityParsing)
import xsparser
#from basedomtypes import HierarchyRequestError
#from basedomtypes import NotFoundError

from makeTestDoc import DBG  #makeTestDoc0, makeTestDoc2, DAT
from test4 import K, makeTestDocEachMethod


###############################################################################
#
ElementSamples = [
    "<!ELEMENT itemizedlist (listitem*)>",
    "<!ELEMENT orderedlist (listitem*) >",
    "<!ELEMENT\tlistitem (para*)>",
    "<!ELEMENT para (#PCDATA)>",
    "<!ELEMENT front (div1+)>",
    "<!ELEMENT body (div1+)>",
    "<!ELEMENT back ((div1+, inform-div1*) | inform-div1+)*>",
]

GoodPESamples = [
"""<!ENTITY % foo "<!ELEMENT q ANY>">
%foo;
<!ENTITY % bar "
    <!ATTLIST q ID #IMPLIED>
    <!ATTLIST i ID #IMPLIED>">
%bar;
""",
]

BadPESamples = [
"""
<!ENTITY % foo "para">
<!ELEMENT %foo; ANY>""",

"""<!ENTITY % foo "para">
<!ATTLIST %foo; ID #IMPLIED>""",

"""<!ENTITY % foo "ID">
<!ATTLIST para %foo; #IMPLIED>""",

"""<!ENTITY % foo "   ">
<!ATTLIST para %foo; ID #IMPLIED>""",

"""<!ENTITY % foo "#IMPLIED">
<!ATTLIST para ID %foo;>""",

"""
<!ENTITY % foo "'text'">
<!ENTITY zark "hello, %foo; world.">""",
]

AttlistSamples = [
    """<!ATTLIST  p  id ID #IMPLIED  class NMTOKENS "big">""",
    """<!ATTLIST td
    id              ID              #IMPLIED
    tgt             IDREF           #IMPLIED
    tgts            IDREFS          "foo bar1.a"
    direction       NMTOKEN         FIXED "up"
    bgcolor         NMTOKENS        "foo bar baz"
    rowspan         NUTOKEN         "1"
    colspan         NUMBER          "1"
    alt             CDATA           #REQUIRED
    compass         (n | s | e | w) 'w'
    thePic          ENTITY          "fig1"
    >
    """,
]


EntitySamples = [
    """<!ENTITY mdash  "--">""",
    """<!ENTITY nbsp   "&#160;">""",
    """<!ENTITY ldquo  "#x201C;"   >""",
    """<!ENTITY rdquo  "#x201D;">""",
    """<!ENTITY % local.p.class        "p">""",
    """<!ENTITY % p.class              "%local.p.class;""",
    """<!ENTITY NASA    "National Aeronautics and Space Administration">""",
    """<!ENTITY chap1   PUBLIC "-//foo" "c:\\docs\\chap1.xml">""",
    """<!ENTITY chap2   SYSTEM "c:\\docs\\chap2.xml">""",
    """<!ENTITY fig1    SYSTEM "/Users/abc/Pictures/img12.jpg" NDATA jpg>""",
]

NotationSamples = [
    """<!NOTATION jpg PUBLIC "+//ISO99999/Data Formats/JPEG//" "">""",
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
        self.assertEqual(facetCheck("foo:xy:zzy", "QName"), XsdFacet.pattern)
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
        self.assertEqual(len(ct.attributeDefs), 0)


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


class testAttributeDef(unittest.TestCase):
    def setup(self):
        #pylint: disable=W0612
        # First the usual SGML-based ones
        #
        a1 = AttributeDef(ens=None, ename=None, ans=None, aname="id",
            atype="ID", adfttype=DftType.IMPLIED)
        a2 = AttributeDef(ens=None, ename=None, ans=None, aname="class",
            atype="NMTOKENS", adfttype=DftType.IMPLIED)
        a3 = AttributeDef(ens=None, ename=None, ans=None, aname="font-family",
            atype="NMTOKEN", adfttype=DftType.IMPLIED)
        a4 = AttributeDef(ens=None, ename=None, ans=None, aname="alt",
            atype="CDATA", adfttype="#REQUIRED")

        a5 = AttributeDef(ens=None, ename=None, ans=None, aname="version",
            atype="NUTOKEN", adfttype="#FIXED", literal="THE_FIXED_VALUE")
        a6 = AttributeDef(ens=None, ename=None, ans=None, aname="Author.Of-it",
            atype="NUTOKEN", adfttype="#FIXED")

        a7 = AttributeDef(ens=None, ename=None, ans=None, aname="target",
            atype="IDREF", adfttype=DftType.IMPLIED)
        a8 = AttributeDef(ens=None, ename=None, ans=None, aname="targets",
            atype="IDREFS", adfttype=DftType.IMPLIED)
        a9 = AttributeDef(ens=None, ename=None, ans=None, aname="format",
            atype="NOTATION", adfttype=DftType.IMPLIED)
        a10 = AttributeDef(ens=None, ename=None, ans=None, aname="object",
            atype="ENTITY", adfttype=DftType.IMPLIED)
        a11 = AttributeDef(ens=None, ename=None, ans=None, aname="objects",
            atype="ENTITIES", adfttype=DftType.IMPLIED)

        a12 = AttributeDef(ens=None, ename=None, ans=None, aname="orth",
            atype="( LAT GRK ENG )", adfttype=DftType.IMPLIED)

        # Now with namespaces and element assigments
        svgNS = "http://www.w3.org/2000/svg"
        b1 = AttributeDef(ens=None, ename=None, ans="svg", aname="path",
            atype="CDATA", adfttype=DftType.IMPLIED)
        b1 = AttributeDef(ens=svgNS, ename="g", ans=svgNS, aname="x",
            atype="NUTOKEN", adfttype=DftType.IMPLIED)


class testElementDefs(unittest.TestCase):
    def setup(self):
        m = Model(contentType="X_MODEL",
            tokens = [ "(", "#PCDATA", "|", "i", "|", "b", ")", "*" ])
        el = ElementDef("para", m)
        self.assertIsInstance(el, ElementDef)

        a1 = AttributeDef(ens=None, ename=None, ans=None, aname="id",
            atype="ID", adfttype=DftType.IMPLIED)
        el.attachAttr(a1)


###############################################################################
#
@unittest.skip
class testEntityDef(unittest.TestCase):
    def setUp(self):
        lit1 = "<warn>Do not fold, spindle, or mutilate.</warn>"
        sys1 = "/home/jsmith/docs/foo.xml"
        pub1 = "-//foo//bar//EN"
        sys2 = "/home/jsmith/docs/foo.xml"

        # Some kinds of identifiers
        ds1 = EntityDef("ds1", entSpace=EntitySpace.GENERAL, data=lit1)
        self.assertEqual(ds1.tostring(), "")
        ds2 = EntityDef("ds2", entSpace=EntitySpace.GENERAL, systemId=sys1)
        self.assertEqual(ds2.tostring(), "")
        ds3 = EntityDef("ds3", entSpace=EntitySpace.GENERAL, publicId=pub1, systemId=sys2)
        self.assertEqual(ds3.tostring(), "")
        ds4 = EntityDef("ds4", entSpace=EntitySpace.GENERAL, systemId=[ sys1, sys2 ])
        self.assertEqual(ds4.tostring(), "")

        # By space/type
        e1 = EntityDef("ent1", entSpace=EntitySpace.GENERAL, data=lit1,
            entParsing=EntityParsing.PCDATA, notationName=None, ownerSchema=None)
        self.assertEqual(e1.tostring(), "")
        e2 = EntityDef("ent1", entSpace=EntitySpace.PARAMETER, systemId=sys1,
            entParsing=EntityParsing.PCDATA, notationName=None, ownerSchema=None)
        self.assertEqual(e2.tostring(), "")
        e3 = EntityDef("ent1", entSpace=EntitySpace.NOTATION, publicId=pub1,
            entParsing=EntityParsing.PCDATA, notationName=None, ownerSchema=None)
        self.assertEqual(e3.tostring(), "")
        #e4 = EntityDef("ent1", EntityType.SDATA, systemID=sys1, publicId=pub1,
        #    entParsing=EntityParsing.PCDATA, notationName=None, ownerSchema=None)
        #self.assertEqual(e4.tostring(), "")
        #e5 = EntityDef("ent1", EntityType.NAMESET, data=lit1,
        #    entParsing=EntityParsing.PCDATA, notationName=None, ownerSchema=None)
        #self.assertEqual(e5.tostring(), "")

        # By parseType
        p1 = EntityDef("ent1", entSpace=EntitySpace.GENERAL, data=lit1,
            entParsing=EntityParsing.PCDATA, notationName=None, ownerSchema=None)
        self.assertEqual(p1.tostring(), "")
        p2 = EntityDef("ent1", entSpace=EntitySpace.GENERAL, data=lit1,
            entParsing=EntityParsing.NDATA, notationName=None, ownerSchema=None)
        self.assertEqual(p2.tostring(), "")
        p3 = EntityDef("ent1", entSpace=EntitySpace.GENERAL, data=lit1,
            entParsing=EntityParsing.CDATA, notationName=None, ownerSchema=None)
        self.assertEqual(p3.tostring(), "")
        p4 = EntityDef("ent1", entSpace=EntitySpace.GENERAL, data=lit1,
            entParsing=EntityParsing.RCDATA, notationName=None, ownerSchema=None)
        self.assertEqual(p4.tostring(), "")

        # TODO Extensions?

        # Add notation, ownerSchema, etc.

    def test_general(self):
        pass

    def test_parameter(self):
        pass


###############################################################################
#
@unittest.skip
class testNotationDef(unittest.TestCase):
    def setUp(self):
        madeDocObj = makeTestDocEachMethod(dc=K)
        self.dc = K
        self.n = madeDocObj.n

    def tests(self):
        nn = self.n.doc.theDoctype.defineNotation(
            "nname", publicId="-//foo", systemId="http://example.com/png")
        el = self.n.docEl.childNodes[5]
        el.setAttribute("notn", nn)
        return


###############################################################################
#
class testPEs(unittest.TestCase):

    def setUp(self):
        madeDocObj = makeTestDocEachMethod(dc=K)
        self.dc = K
        self.n = madeDocObj.n

    def testgoods(self):
        for s in GoodPESamples:
            p = xsparser.ParserCreate()
            p.Parse(s)                      # TODO Make a DOM?
            #self.assertTrue(theDom.doctype.entities("foo"))

    def testbads(self):
        for s in BadPESamples:
            with self.assertRaises(SyntaxError):
                p = xsparser.ParserCreate()
                p.Parse(s)


###############################################################################
#
@unittest.skip
class testWholeDoctype(unittest.TestCase):
    def setUp(self):
        DBG.msg("testWholeDoctype not yet written.")
        madeDocObj = makeTestDocEachMethod(dc=K)
        self.dc = K
        self.n = madeDocObj.n

    def tests(self):
        nn = self.n.doc.theDoctype.defineNotation(
            "nname", publicId="-//foo", systemId="http://example.com/png")
        el = self.n.docEl.childNodes[5]
        el.setAttribute("notn", nn)
        return


if __name__ == '__main__':
    unittest.main()
