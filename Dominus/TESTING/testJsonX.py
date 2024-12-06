#!/usr/bin/env python3
#
#pylint: disable=E1120,E1121, W0718
#
import unittest
import basedom
#from basedom import Document, Element, Attr
#from basedomtypes import HReqE

import jsonx

from makeTestDoc import isEqualNode  # makeTestDoc0, makeTestDoc2, DAT, DBG
from test4 import makeTestDocEachMethod, K

sampleData = """
[ { "#name":"#document", "#format":"JSONX",
    "#version":"1.0", "#encoding":"utf-8", "#standalone":"yes",
    "#doctype":"html", "#systemId":"http://w3.org/html" },
  [ { "#name": "html", "xmlns:html":"http://www.w3.org/1999/xhtml" },
    [ { "#name": "head" },
      [ { "#name": "title" },
        "My document" ]
    ],
    [ { "#name": "body" },
      [ { "#name": "p", "id":"stuff", "class":"lead" },
        "This is a ",
        [ { "#name": "i" }, "very" ],
        " short document.",
      ],
      [ { "#name": "#cdata" }, "This is some <real> & <legit/> cdata." ],
      [ { "#name": "#pi", "#target"="troff" }, ".ss;.b" ],
      [ { "#name": "#comment" }, "This is some <real> & <legit/> cdata." ],
    ],
    [ { "#name": "hr" } ]
  ]
]
"""

#         [ { "#name": "#text" }, "Another way to do text." ]


class TestJsonX(unittest.TestCase):
    def setUp(self):
        madeDocObj = makeTestDocEachMethod(dc=K)
        self.n = madeDocObj.n

    def testJSON(self):
        jsaver = jsonx.Saver(self.n.doc)
        jsonData = jsaver.tostring()

        impl = basedom.getDOMImplementation()
        jloader = jsonx.Loader(domImpl=impl, jdata=jsonData)
        theDoc = jloader.domDoc

        self.assertTrue(isEqualNode(theDoc, self.n.doc))


if __name__ == '__main__':
    unittest.main()
