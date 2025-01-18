#!/usr/bin/env python3
#
#pylint: disable=E1120,E1121, W0718
#
import unittest
import codecs
import json
import logging

import basedom
from basedom import Document  #, Element, Attr
#from basedomtypes import HReqE

import jsonx

#from makeTestDoc import isEqualNode  # makeTestDoc0, makeTestDoc2, DAT, DBG
from test4 import makeTestDocEachMethod, K

lg = logging.getLogger("testJsonX.py")

sampleJ = "../DATA/jsample.jsonx"
sampleX = "../DATA/jsample.xml"


class TestJsonX(unittest.TestCase):
    def setUp(self):
        madeDocObj = makeTestDocEachMethod(dc=K)
        self.n = madeDocObj.n

    def testJSONload(self):
        with codecs.open(sampleJ, "rb", encoding="utf-8") as ifh:
            jsonString = ifh.read()

        j = json.loads(jsonString)
        jsonString2 = json.dumps(j, indent="  ")
        lg.warning(jsonString2)

        impl = basedom.getDOMImplementation()
        jloader = jsonx.Loader(domImpl=impl, jdata=jsonString)
        theDoc = jloader.domDoc
        self.assertIsInstance(theDoc, Document)

    def testXMLload(self):
        impl = basedom.getDOMImplementation()
        theDoc = impl.parse(sampleX)
        self.assertIsInstance(theDoc, Document)
        lg.info("From XML:\n%s", theDoc.toprettyxml())

        jsaver = jsonx.Saver(theDoc)
        jsonData = jsaver.tostring()
        x = json.loads(jsonData)
        self.assertIsInstance(x, list)
        lg.info("\n******* JSON created from XML DOM:\n%s",jsonData)

    def testOther(self):
        pass
        #impl = basedom.getDOMImplementation()
        #jloader = jsonx.Loader(domImpl=impl, jdata=jsonData)
        #theDoc = jloader.domDoc
        #self.assertIsInstance(theDoc, Document)
        #self.assertTrue(theDoc.isEqualNode(self.n.doc))


if __name__ == '__main__':
    unittest.main()
