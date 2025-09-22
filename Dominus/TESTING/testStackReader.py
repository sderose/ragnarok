#!/usr/bin/env python3
#
#pylint: disable=W0201, C2801, W0401, W0614, W0212
#
import unittest
from math import isnan

from ragnaroktypes import *

from stackreader import InputFrame, StackReader

xmlDcl = """<?xml version="1.0" encoding="utf-8"?>"""
docType = """<!DOCTYPE srTest []>"""
docData = """<srTest><p id="foo" class=""   \t\n\n  >Hello</p></srTest>"""


###############################################################################
#
class TestInputFrame(unittest.TestCase):
    def setUp(self):
        return

    def testBasics(self):
        fr = InputFrame()
        fr.addData(docData)
        self.assertEqual(fr.bufLeft, len(docData))
        fr.clear()
        self.assertEqual(fr.bufLeft, 0)

        fr.addData(docData)
        self.assertEqual(fr.bufLeft, len(docData))
        self.assertEqual(fr.buf, docData)
        self.assertEqual(fr.fullOffset, 0)
        self.assertEqual(fr.fullLineNum, 1)
        self.assertEqual(fr.__str__(), docData)
        self.assertEqual(fr.__bool__(), True)
        self.assertEqual(fr.__getitem__(13), "=")
        self.assertEqual(fr.__getitem__(slice(14,19)), '"foo"')
        self.assertEqual(fr.__getitem__(-5), "T")
        with self.assertRaises(IndexError):
            _x = fr[1:10:4]
            _x = fr[99]

        fr.topOff()
        self.assertEqual(fr.bufLeft, len(docData))
        fr.dropUsedPart()
        self.assertEqual(fr.bufLeft, len(docData))
        fr.skipSpaces()
        self.assertEqual(fr.bufLeft, len(docData))

        self.assertEqual(fr.peek(), "<")
        self.assertEqual(fr.peek(8), "<srTest>")
        self.assertEqual(fr.consume(8), "<srTest>")
        self.assertEqual(fr.peek(5), "<p id")
        fr.dropUsedPart()
        self.assertEqual(fr.peek(5), "<p id")

        fr.pushBack("<srTest>")
        self.assertEqual(fr.bufLeft, len(docData))
        self.assertEqual(fr.buf, docData)

        fr.discard(8)
        self.assertEqual(fr.buf, docData)

    def testLocationCounting(self):
        fr = InputFrame()
        fr.addData(docData)
        fr.consume(40)
        self.assertEqual(fr.bufLeft, len(docData)-40)
        self.assertEqual(fr.buf[fr.bufPos:], docData[40:])
        self.assertEqual(fr.fullOffset, 40)
        self.assertEqual(fr.fullLineNum, 3)

        pb = "    \nxyz"
        fr.pushBack(pb)
        self.assertEqual(fr.fullOffset, 40-len(pb))
        self.assertEqual(fr.fullLineNum, 2)

    def testReaders1(self):
        """Try all kinds of things that should *fail* on this input.
        """
        fr = InputFrame()
        fr.addData(docData)

        self.assertEqual(fr.readConst("hello"), None)

        # Following should all fail at this location
        #
        #print("testReaders1: Before reading stuff: '%s'." % (str(fr)))
        self.assertEqual(fr.readBackslashChar(), None)
        self.assertEqual(fr.readNumericChar(ss=True), None)
        self.assertEqual(fr.readInt(), None)
        self.assertEqual(fr.readBaseInt(), None)
        self.assertEqual(fr.readFloat(signed=False), None)
        self.assertEqual(fr.readFloat(signed=True), None)
        self.assertEqual(fr.readName(), None)
        self.assertEqual(fr.readEnumName([ "foo", "BAR" ]), None)
        self.assertEqual(fr.readRegex(r"\w+\d+"), None)

        # Make sure none of them used up any data in failing
        #
        self.assertEqual(str(fr), docData)
        self.assertEqual(fr.readAll(), docData)
        self.assertEqual(fr.readAll(), "")

    def testReaders2(self):
        fr = InputFrame()
        fr.addData(docData)

        self.assertEqual(fr.readToString("EOF", consumeEnder=True), None)

        fr.pushBack("\\n")
        self.assertEqual(fr.readBackslashChar(), "\n")
        fr.pushBack("\\x41")
        self.assertEqual(fr.readBackslashChar(), "A")
        fr.pushBack("\\u263a")
        self.assertEqual(fr.readBackslashChar(), chr(0x263a))
        fr.pushBack("\\U0000263B")
        self.assertEqual(fr.readBackslashChar(), chr(0x263b))
        fr.pushBack("\\U0001f92d")
        self.assertEqual(fr.readBackslashChar(), chr(0x1f92d))

        numRefs = "&#65;&#000000000066;&#x4d;&#X04E;&#x4e;"
        fr.pushBack(numRefs)
        self.assertEqual(fr.peek(len(numRefs)), numRefs)

        self.assertEqual(fr.readNumericChar(ss=True), "A")
        self.assertEqual(fr.readNumericChar(ss=True), "B")
        self.assertEqual(fr.readNumericChar(ss=True), "M")
        self.assertEqual(fr.readNumericChar(ss=True), "N")
        self.assertEqual(fr.readNumericChar(ss=True), "N")

        fr.pushBack("     256    -257   +258  ")
        self.assertEqual(fr.readInt(ss=True),  256)
        self.assertEqual(fr.readInt(ss=True), -257)
        self.assertEqual(fr.readInt(ss=True),  258)
        fr.skipSpaces()

        fr.pushBack("     0x100    ")
        self.assertEqual(fr.readBaseInt(ss=True), 256)
        fr.skipSpaces()

        fr.pushBack(" \t\r -3.14156  NaN NaN")
        self.assertEqual(fr.readFloat(ss=True, signed=True,specialFloats=True), -3.14156)
        self.assertTrue(isnan(fr.readFloat(ss=True, specialFloats=True)))
        self.assertIsNone(fr.readFloat(ss=True, specialFloats=False))
        fr.skipSpaces()

        fr.pushBack(" para   P_1.3_  svg:g <>")
        self.assertEqual(fr.readName(ss=True), "para")
        self.assertEqual(fr.readName(ss=True), "P_1.3_")
        self.assertEqual(fr.readName(ss=True), "svg:g")
        self.assertEqual(fr.readName(ss=True), None)
        self.assertEqual(fr.peek(2), "<>")

        #self.assertEqual(fr.readEnumName(names, ss=True), "")

        #self.assertEqual(fr.readRegex(regex[str, re.Pattern], ss=True,fold=True), "")

    def testReaders3(self):
        fr = InputFrame()
        fr.addData(docData)

        # TODOself.assertEqual(fr.peekDelimPlus(ss=True), "")

    # TODO Same but with file and Entity instead of string.


###############################################################################
#
class TestSR(unittest.TestCase):
    def setUp(self):
        return

    def testBasics(self):
        fr1 = InputFrame()
        fr1.addData(xmlDcl)
        fr2 = InputFrame()
        fr2.addData(docType)
        fr3 = InputFrame()
        fr3.addData(docData)

        # Basic frame pushing and popping
        #
        sr = StackReader()  # TODO Which options apply?
        self.assertEqual(sr.depth, 0)
        sr.open(fr3)
        sr.open(fr2)
        sr.open(fr1)
        self.assertEqual(sr.depth, 3)
        self.assertEqual(sr.curFrame, fr1)
        sr.close()
        self.assertEqual(sr.depth, 2)
        self.assertEqual(sr.curFrame, fr2)

        # TODO Should we be able to stack the same frame twice?

        #self.assertEqual(EntE(msg))
        #self.assertEqual(isEntityOpen(space, name))
        #self.assertEqual(closeAll())
        #self.assertEqual(wholeLoc())
        #self.assertEqual(buf())
        #self.assertEqual(bufPos())
        #self.assertEqual(bufPos(n))
        #self.assertEqual(bufLeft())
        #self.assertEqual(bufSample())
        #self.assertEqual(peek(n=1))
        #self.assertEqual(consume(n=1))
        #self.assertEqual(discard(n=1))
        #self.assertEqual(pushBack(s))
        #self.assertEqual(topOff(n=None))
        #self.assertEqual(skipSpaces(allowComments=False, entOpener=None))None:

if __name__ == '__main__':
    unittest.main()
