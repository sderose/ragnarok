#!/usr/bin/env python3
#
import unittest
#import logging
from xml.parsers import expat
from xml.dom import minidom

#from xml.dom.minidom import getDOMImplementation, DOMImplementation,Element

#from basedom import Node


WFTestCases = [
    # Invalid XML declaration format [§2.8]
    """<?xml version="1.0" encoding="utf-8" standalone="yes" id="spam"?>""",
    """<?xml version="1.0" encoding="utf-8" standalone="yes" id="spam"?>""",
    """<?xml version="1.0" encoding="utf-8"? >""",
    """<?XML version="1.0"?>""",  # wrong case
    """<?xml version="1.0"?><root><?xml version="1.0"?></root>""",

    # Invalid XML version number [§2.8]
    """<?xml version="0.999999999999999"?>""",
    """<?xml version="1.100000000000001"?>""",
    """<?xml version="xyzzy"?>""",
    """<?xml version\uff1d"1.0"?>""",  # fullwidth equals

    # Multiple root elements [§2.1]
    """<doc>foo</doc><doc>bar</doc>""",

    # Missing encoding declaration when using non-UTF-8/16 encodings [§4.3.3]
    # \\x9e is cp1252 LATIN SMALL LETTER Z WITH CARON (-> U+017e)
    """<?xml version="1.0"?><p\x9e>Hello</p\x9e>""",

    # Missing paired tags or improper nesting [§2.1]
    "<p>hello <i>there</i>.</q></p>"

    # Invalid element names [§2.3]
    """<-p>Hello</-p>""",
    """<.p>Hello</.p>""",
    """<:p>Hello</:p>""",
    """<foo:-p>Hello</foo:-p>""",
    """<foo:>Hello</foo:>""",

    # Invalid attribute names [§2.3]
    """<p:id="foo">Hello</p>""",
    """<p foo:="foo">Hello</p>""",
    """<p foo:bar:baz="foo">Hello</p>""",
    """<p -foo="bar">Hello</p>""",
    """<p .foo="bar">Hello</p>""",
    """<p :foo="bar">Hello</p>""",
    """<p foo "bar">Hello</p>""",
    """<p "bar">Hello</p>""",
    """<p ="bar">Hello</p>""",

    # Missing quotes around attribute values [§3.1]
    """<p border=border></p>""",
    """<p border></p>""",

    # Non-unique attributes within an element [§3.1]
    """<p class="foo" id="A12" class="foo">""",
    """<p xml:id="foo" id="A12" xml:id="foo">""",

    # Undefined entities [§4.1]
    "<p>&chap1;<p>"
    "<p>%soup;<p>"

    # Invalid character references [§4.1]
    """<p>&#bull;</p>""",
    """<p>&-bull;</p>""",
    """<p>&-bull;</p>""",
    """<p>&html:bull;</p>""",
    """<p>&#bull ;</p>""",
    """<p>&#bull&#x3b;</p>""",
    """<p>&#bull in a china closet</p>""",
    """<p>&#bull:bull;</p>""",
    """<p>&#BEEF;</p>""",
    """<p>&#xBEEG;</p>""",
    """<p>&#Xbull;</p>""",

    """<p>&#0;</p>""",
    """<p>&#x00;</p>""",
    """<p>&#1;</p>""",
    """<p>&#x1;</p>""",
    """<p>&#-12;</p>""",
    """<p>&#65.2;</p>""",

    # These are ok in doc instance:
    #"""<p>%#65;</p>""",
    #"""<p>%#x2022;</p>""",
    #"""<p>%#x2022;</p>""",
    #"""<p>%#x2022;</p>""",

    # Improper use of reserved characters (< > & ' ") without escaping [§2.4]
    """<p> Really? < </p>""",
    """<p> Really? & </p>""",
    """<p class="foo"far"> Really? </p>""",
    """<p class="foo""far"> Really? </p>""",
    """<p class="foo\\"far"> Really? </p>""",
    """<p class='foo'far'> Really? </p>""",

    # CDATA sections with improper termination [§2.7]
    """<p>Hello <![CDATA[ huh? ]] >.</p>""",
    """<p>Hello <![CDATA[ huh? ]]> and again ]]>.</p>""",
    """<p>Hello <![CDATA[ huh? <![CDATA[ ]]> and again ]]>.</p>""",
    """<p>Hello <![CDATA [ huh? ]]></p>""",

    # Processing instructions without proper syntax [§2.6]
    """<p><?-tgt Hello ?><p>""",
    """<p><? Hello??? ? ><p>""",
    """<p><? Hello ?><p>""",
    """<p><?tgt Hello ? ><p>""",

    # Comments containing "--" or ending in "-" [§2.5]
    """<p><!-- this -- is not -- ok --></p>""",
    """<p><!-- this is not ok ---></p>""",

    # Namespaces [§3]
    """<undef:p>Hello</undef:p>""",
    """<p xmlns:foo="">Hello</p>""",
    """<p xmlns:xml="http://www.w3.org/XML/1998/namespace">Hello</p>""",

    # DTD
    """<!DOCTYPE root [<!NOPE foo "bar"> ]>""",
    """<!DOCTYPE root [<!ENTITY foo "bar">&foo; ]>""",
    """<!DOCTYPE root SYSTEM "foo.dtd" PUBLIC "bar.dtd">""",  # both SYSTEM and PUBLIC
    """<!DOCTYPE root [<!ELEMENT root (#PCDATA)> ]><root/>""",  # DTD after root element

    # What about?
    # different prefix w/ same URL
    # prefix inherited vs. set conflict
    # """<p><!- this is not ok --></p>""",
    # """<p><!-- this is not ok""",
    # """<p></p><!-- this is not ok""",
    # """<p [\d!@#$$%^^&*)>Hello</p>""",
]


class TestDOMNode(unittest.TestCase):
    def setUp(self):
        #self.makeDocObj = makeTestDoc0(dc=DAT_DocBook)
        #self.n = self.makeDocObj.n
        return

    def test_errs_expat(self):
        p = expat.ParserCreate()
        for x in WFTestCases:
            with self.assertRaises(expat.ExpatError):
                p.Parse(x)

    def test_errs_minidom(self):
        for x in WFTestCases:
            try:
                _domDoc = minidom.parseString(x)
                self.assertFalse(f"For test '{x}', did not raise exception.")
            except expat.ExpatError:
                return
            #pylint: disable=W0718
            except Exception as e:
                self.assertFalse(f"For test '{x}', "
                    f"raised wrong exception (expected ExpatError):\n    {e}")


if __name__ == '__main__':
    unittest.main()
