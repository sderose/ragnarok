#!/usr/bin/env python3
#
#pylint: disable=E1120,E1121, W0718
#
import unittest
import codecs
import json
from collections import defaultdict
import logging

import basedom
from basedom import Document  #, Element, Attr
#from basedomtypes import HReqE

from bifrost import Loader, Saver

from makeTestDoc import makeTestDocEachMethod
from test4 import DAT_K

lg = logging.getLogger("testBifrost.py")

sampleJ = "../DATA/jsample.jsonx"
sampleX = "../DATA/jsample.xml"

nodeCounts = defaultdict(int)

def countJsonNodes(root):
    if isinstance(root, list):
        nodeCounts[root[0]["~"]] += 1
        for ch in root[1:]: countJsonNodes(ch)
    else:
        nodeCounts["#"+type(root).__name__] += 1

class TestBifrost(unittest.TestCase):
    def setUp(self):
        madeDocObj = makeTestDocEachMethod(dc=DAT_K)
        self.n = madeDocObj.n

    def testJSONload(self):
        with codecs.open(sampleJ, "rb", encoding="utf-8") as ifh:
            jsonString = ifh.read()
        j = json.loads(jsonString)

        nodeCounts.clear()
        countJsonNodes(j)
        self.assertEqual(nodeCounts, {
            "#cdata":   1,
            "#comment": 1,
            "#pi":      1,
            "body":     1,
            "head":     1,
            "hr":       1,
            "html":     1,
            "i":        1,
            "JSONX":    1,
            "p":        1,
            "title":    1,
        })

        # Now make a DOM from that literal json
        #
        impl = basedom.getDOMImplementation()
        jloader = Loader(domImpl=impl, jdata=jsonString)
        theDoc = jloader.domDoc
        self.assertIsInstance(theDoc, Document)
        theDoc.documentElement.checkNode(deep=True)

    def testXMLload(self):
        impl = basedom.getDOMImplementation()
        theDoc = impl.parse(sampleX)
        self.assertIsInstance(theDoc, Document)

        #lg.info("From XML:\n%s", theDoc.toprettyxml())

        jsaver = Saver(theDoc)
        jsonData = jsaver.tostring()
        x = json.loads(jsonData)
        self.assertIsInstance(x, list)
        lg.info("\n******* JSON created from XML DOM:\n%s",jsonData)

    def testOther(self):
        pass
        #impl = basedom.getDOMImplementation()
        #jloader = Loader(domImpl=impl, jdata=jsonData)
        #theDoc = jloader.domDoc
        #self.assertIsInstance(theDoc, Document)
        #self.assertTrue(theDoc.isEqualNode(self.n.doc))


if __name__ == '__main__':
    unittest.main()
