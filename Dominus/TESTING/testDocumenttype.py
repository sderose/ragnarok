#!/usr/bin/env python3
#
#pylint: disable=W0201, C2801
#
import unittest
#import math
#import random
#from collections import defaultdict
#from typing import List

from xmlstrings import CaseHandler

#from basedomtypes import HierarchyRequestError
#from basedomtypes import NotFoundError

from documenttype import (
    facetCheck, XsdFacet, SimpleType, ComplexType,
    DateTimeFrag, SeqType, RepType, ModelGroup, ModelItem, Model)

from makeTestDoc import DBG  #makeTestDoc0, makeTestDoc2, DAT,
from test4EachMethod import K, makeTestDocEachMethod


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
        DBG.msg("testAttrDef not yet written.")

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

        self.assertFalse(facetCheck("31", "gDay"))
        self.assertFalse(facetCheck("12", "gMonth"))
        self.assertFalse(facetCheck("12-31", "gMonthDay"))
        self.assertFalse(facetCheck("2024", "gYear"))
        self.assertFalse(facetCheck("2024-01", "gYearMonth"))
        self.assertFalse(facetCheck("2024-02-29", "date"))
        self.assertFalse(facetCheck("2024-02-29T11:59:59.214Z", "dateTime"))
        self.assertFalse(facetCheck("11:59:59.214Z", "time"))
        self.assertFalse(facetCheck("11:59:60.2", "time"))  # Leap seconds
        self.assertFalse(facetCheck("", "duration"))

        self.assertFalse(facetCheck("EN:UK", "language"))
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
        self.assertFalse(facetCheck("thing1 thing2", "IDREFS"))
        self.assertFalse(facetCheck("ul ol dl", "NMTOKENS"))
        self.assertFalse(facetCheck("chap1 chap2 chap3 chap4", "ENTITIES"))


    def testxsdTypesFail(self):
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

        self.assertEqual(facetCheck("abc", "byte"), XsdFacet.pattern)
        self.assertEqual(facetCheck("128", "byte"), XsdFacet.maxInclusive)
        self.assertEqual(facetCheck("-129", "byte"), XsdFacet.minInclusive)
        self.assertEqual(facetCheck("32768", "short"), XsdFacet.maxInclusive)
        self.assertEqual(facetCheck("-32769", "short"), XsdFacet.minInclusive)
        self.assertEqual(facetCheck("9999999999999", "int"), XsdFacet.maxInclusive)
        self.assertEqual(facetCheck("True", "long"), XsdFacet.pattern)

        self.assertEqual(facetCheck("abcdef", "integer"), XsdFacet.pattern)
        self.assertEqual(facetCheck("99", "nonPositiveInteger"), XsdFacet.pattern)
        self.assertEqual(facetCheck("999999", "negativeInteger"), XsdFacet.pattern)
        self.assertEqual(facetCheck("-999999", "nonNegativeInteger"), XsdFacet.pattern)
        self.assertEqual(facetCheck("0", "positiveInteger"), XsdFacet.pattern)
        self.assertEqual(facetCheck("-99", "unsignedByte"), XsdFacet.pattern)
        self.assertEqual(facetCheck("-000000000000999999999", "unsignedShort"),
            XsdFacet.pattern)
        self.assertEqual(facetCheck("-1", "unsignedInt"), XsdFacet.pattern)
        self.assertEqual(facetCheck("-12", "unsignedLong"), XsdFacet.pattern)

        self.assertEqual(facetCheck("-3.14159xyz", "decimal"), XsdFacet.pattern)
        self.assertEqual(facetCheck(1.2+3.1j, "double"), XsdFacet.pattern)
        self.assertEqual(facetCheck("0xBEEF", "float"), XsdFacet.pattern)

        self.assertEqual(facetCheck("32", "gDay"), XsdFacet.pattern)
        self.assertEqual(facetCheck("-1", "gMonth"), XsdFacet.pattern)
        self.assertEqual(facetCheck("12-41", "gMonthDay"), XsdFacet.pattern)
        self.assertEqual(facetCheck("024", "gYear"), XsdFacet.pattern)
        self.assertEqual(facetCheck("2024-00", "gYearMonth"), XsdFacet.pattern)
        self.assertEqual(facetCheck("2024-02-57", "date"), XsdFacet.pattern)
        self.assertEqual(facetCheck("2024-02-29Q11:59:59.214Z", "dateTime"),
            XsdFacet.pattern)
        self.assertEqual(facetCheck("11:59:59.214*2", "time"), XsdFacet.pattern)
        self.assertEqual(facetCheck("11:59:61", "time"), XsdFacet.pattern)
        self.assertEqual(facetCheck("", "duration"), XsdFacet.pattern)

        self.assertEqual(facetCheck("12", "language"), XsdFacet.pattern)
        #self.assertEqual(facetCheck("", "normalizedString"), XsdFacet.pattern)
        #self.assertEqual(facetCheck("", "string"), XsdFacet.pattern)
        self.assertEqual(facetCheck("a b c", "token"), XsdFacet.pattern)
        self.assertEqual(facetCheck("example.com/docs/foo.xml#chap1", "anyURI"),
            XsdFacet.pattern)
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
        self.assertTrue(dtf.includesDate())
        self.assertFalse(dtf.includesTime())
        self.assertEqual(dtf.year, 2024)
        self.assertEqual(dtf.month, 11)
        self.assertEqual(dtf.day, 13)
        self.assertEqual(dtf.hour, 0)
        self.assertEqual(dtf.minute, 0)
        self.assertEqual(int(dtf.second), 0)
        self.assertEqual(int(dtf.microsecond), 0)
        self.assertEqual(int(dtf.zone), 0)

        dtf = DateTimeFrag(tim)
        self.assertIsInstance(DateTimeFrag(tim), DateTimeFrag)
        self.assertTrue(dtf.check())
        self.assertFalse(dtf.includesDate())
        self.assertTrue(dtf.includesTime())
        self.assertEqual(dtf.year, 0)
        self.assertEqual(dtf.month, 0)
        self.assertEqual(dtf.day, 0)
        self.assertEqual(dtf.hour, 18)
        self.assertEqual(dtf.minute, 5)
        self.assertEqual(int(dtf.second), 59)
        self.assertEqual(int(dtf.microsecond), 312000)
        self.assertEqual(int(dtf.zone), 0)

        dtf = DateTimeFrag(dat+"T"+tim)
        self.assertIsInstance(DateTimeFrag(), DateTimeFrag)
        self.assertTrue(dtf.check())
        self.assertTrue(dtf.includesDate())
        self.assertTrue(dtf.includesTime())
        self.assertEqual(dtf.year, 2024)
        self.assertEqual(dtf.month, 11)
        self.assertEqual(dtf.day, 13)
        self.assertEqual(dtf.day, 0)
        self.assertEqual(dtf.hour, 18)
        self.assertEqual(dtf.minute, 5)
        self.assertEqual(int(dtf.second), 59)
        self.assertEqual(int(dtf.microsecond), 312000)
        self.assertEqual(int(dtf.zone), 0)

        dtf2 = DateTimeFrag()  # TODO Check values w/ get
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


###############################################################################
#
class testSimpleType(unittest.TestCase):
    def test_simpletype(self):
        st = SimpleType(name="p", baseType=None)
        self.assertEqual(st.caseTx, CaseHandler.NONE)

        ct = ComplexType(name="p", baseType=None, model=Model("ANY"))
        self.assertEqual(len(ct.attributeDefs), 0)


###############################################################################
#
class testModel(unittest.TestCase):
    """ModelGroup takes raw tokens, including operators, unlike ModelGroup.
    Also unlike ModelGroup, it handles declared content types.
    """
    def test_model(self):
        self.assertTrue(Model(contentType="ANY"))
        self.assertTrue(Model(contentType="EMPTY", tokens=[]))
        self.assertTrue(Model(contentType="X_MODEL",
            tokens = [ "(", "#PCDATA", ")" ]))
        self.assertTrue(Model(contentType="X_MODEL",
            tokens = [ "(", "title", "p", "*", ")" ]))
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
        mg.rep.setBounds(self, minOccurs=5, maxOccurs=9)
        self.assertIsInstance(mg, ModelGroup)


class testModelItem(unittest.TestCase):
    def test_model_group(self):
        self.assertIsInstance(ModelItem(name="i", rep=RepType.PLUS), ModelItem)
        self.assertIsInstance(ModelItem(name="#PCDATA", rep=RepType.QUEST), ModelItem)
        self.assertIsInstance(ModelItem(name="_b.12", rep=RepType.STAR), ModelItem)
        self.assertIsInstance(ModelItem(name="hr", rep=RepType.NOREP), ModelItem)


class testElementDef(unittest.TestCase):
    def setup(self):
        DBG.msg("testElementDef not yet written.")


###############################################################################
#
@unittest.skip
class testEntityDef(unittest.TestCase):
    def setUp(self):
        DBG.msg("testEntityDef not yet written.")

    def test_general(self):
        pass

    def test_parameter(self):
        pass


###############################################################################
#
@unittest.skip
class testNotationDef(unittest.TestCase):
    def setUp(self):
        DBG.msg("testNotationDef not yet written.")
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
