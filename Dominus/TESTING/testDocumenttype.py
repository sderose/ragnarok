#!/usr/bin/env python3
#
#pylint: disable=W0201, C2801
#
import unittest
#import math
#import random
#from collections import defaultdict
#from typing import List

#from domexceptions import HierarchyRequestError
#from domexceptions import NotFoundError

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
class testElementDef(unittest.TestCase):
    def setup(self):
        DBG.msg("testElementDef not yet written.")


###############################################################################
#
class testAttrDef(unittest.TestCase):
    def setup(self):
        DBG.msg("testAttrDef not yet written.")


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
