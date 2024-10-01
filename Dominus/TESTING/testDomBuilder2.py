#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
#pylint: disable=W0613, W0603, W0212
#
import os
#from typing import IO, Union, Dict
import logging
import argparse

#from xml.parsers import expat

import basedom
from dombuilder import DomBuilder

lg = logging.getLogger("testDomBuilder")

descr = """
Test driver for dombuilder.
"""

def processOptions():
    try:
        from BlockFormatter import BlockFormatter
        parser = argparse.ArgumentParser(
            description=descr, formatter_class=BlockFormatter)
    except ImportError:
        parser = argparse.ArgumentParser(description=descr)

    parser.add_argument(
        "--baseDom", action="store_true",
        help="Try building using BaseDOM.")
    parser.add_argument(
        "--echo", action="store_true",
        help="Reconstruct and print the XML.")
    parser.add_argument(
        "--iencoding", type=str, default="UTF-8",
        choices=[ "UTF-8", "UTF-16", "ISO-8859-1", "ASCII" ],
        help="Encoding to assume for the input. Default: UTF-8.")
    parser.add_argument(
        "--istring", type=str, default="    ",
        help="String to repeat to make indentation.")
    parser.add_argument(
        "--ns", action="store_true",
        help="Activate expat namespace handling.")
    parser.add_argument(
        "--quiet", "-q", action="store_true",
        help="Suppress most messages.")
    parser.add_argument(
        "--verbose", "-v", action="count", default=0,
        help="Add more messages (repeatable).")
    parser.add_argument(
        "--version", action="version", version="1.0",
        help="Display version information, then exit.")

    parser.add_argument(
        "files", nargs=argparse.REMAINDER,
        help="Path(s) to input file(s).")

    args0 = parser.parse_args()
    return args0

if (os.environ["PYTHONIOENCODING"] != "utf_8"):
    lg.error("Warning: PYTHONIOENCODING is not utf_8.\n")

args = processOptions()

if (len(args.files) == 0):
    tfileName = "testDoc.xml"
    print("No files specified, trying %s." % (tfileName))
    args.files.append(tfileName)

for thePath in args.files:
    if (not os.path.isfile(thePath)):
        lg.error("No file at '%s'.", thePath)
        continue
    print("Building the DOM for '%s'." % (thePath))

    impl = basedom.getDOMImplementation()

    theDomB = DomBuilder(domImpl=impl, verbose=args.verbose)
    theDom = theDomB.parse(thePath)
    print("\nResults:")
    print(theDom.tostring())
