#!/usr/bin/env python3
#
# domConsole.py
# 2024-09-07: Written by Steven J. DeRose.
#
import sys
import codecs
import logging

import gendoc
import dombuilder

lg = logging.getLogger("domConsole.py")

__metadata__ = {
    "title"        : "domConsole.py",
    "description"  : "",
    "rightsHolder" : "Steven J. DeRose",
    "creator"      : "http://viaf.org/viaf/50334488",
    "type"         : "http://purl.org/dc/dcmitype/Software",
    "language"     : "Python 3.9",
    "created"      : "2024-09-07",
    "modified"     : "2024-09-07",
    "publisher"    : "http://github.com/sderose",
    "license"      : "https://creativecommons.org/licenses/by-sa/3.0/"
}
__version__ = __metadata__["modified"]

descr = """
=Name=

domConsole.py

=Description=

Make or load an XML document, create a DOM, then run lines from the user to test.


==Usage==

    domConsole.py [options] [files]


=See also=


=Known bugs and Limitations=


=To do=


=History=

* 2024-09-07: Written by Steven J. DeRose.


=Rights=

Copyright 2024-09-07 by Steven J. DeRose. This work is licensed under a
Creative Commons Attribution-Share-alike 3.0 unported license.
See [http://creativecommons.org/licenses/by-sa/3.0/] for more information.

For the most recent version, see [http://www.derose.net/steve/utilities]
or [https://github.com/sderose].


=Options=
"""

def showHelp():
    print("""
    """)


###############################################################################
#
def makeDocument(path:str) -> int:
    """Read and deal with one individual file.
    """
    if (not path):
        XG = gendoc.XMLGenerator("")
        XG.generate_random_xml()
    else:
        try:
            fh = codecs.open(path, "rb", encoding=args.iencoding)
        except IOError as e:
            lg.info("Cannot open '%s':\n    %s", path, e)
            return 0

    recnum = 0
    for rec in fh.readlines():
        recnum += 1
        if (args.tickInterval and (recnum % args.tickInterval == 0)):
            lg.info("Processing record %s.", recnum)
        if (rec == ""): continue  # Blank record
        rec = rec.rstrip()
        print(rec)
    if  (fh != sys.stdin): fh.close()
    return recnum

def loadXmlFile(path:str):
    """Parse and load
    """
    db = dombuilder.DOMBuilder()
    impl = basedom.getDOMImplementation()
    aDom = db.parse(path)
    return aDom


###############################################################################
# Main
#
if __name__ == "__main__":
    import argparse

    def processOptions() -> argparse.Namespace:
        try:
            from BlockFormatter import BlockFormatter
            parser = argparse.ArgumentParser(
                description=descr, formatter_class=BlockFormatter)
        except ImportError:
            parser = argparse.ArgumentParser(description=descr)

        parser.add_argument(
            "--quiet", "-q", action="store_true",
            help="Suppress most messages.")
        parser.add_argument(
            "--verbose", "-v", action="count", default=0,
            help="Add more messages (repeatable).")
        parser.add_argument(
            "--version", action="version", version=__version__,
            help="Display version information, then exit.")

        parser.add_argument(
            "files", type=str, nargs=argparse.REMAINDER,
            help="Path(s) to input file(s)")

        args0 = parser.parse_args()
        if (lg and args0.verbose):
            logging.basicConfig(level=logging.INFO - args0.verbose)

        return(args0)


    ###########################################################################
    #
    args = processOptions()

    if (not args.files):
        theDom = makeDocument("")
    else:
        theDom = loadXmlFile(args.files[0])

    while (True):
        print(">", end="")
        cmd = sys.stdin.read()
        if (cmd == "q"): break
        elif (cmd == "h"): showHelp()
        else:
            try:
                eval(cmd)
            except Exception as ex:
                print("Failed: %s" % (ex))
