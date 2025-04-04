#!/usr/bin/env python3
#
# testSuperLong.py: Generate XML with long names, attlists, etc.
# 2025-03-22: Written by Steven J. DeRose.
#
import sys

__metadata__ = {
    "title"        : "testSuperLong.py",
    "description"  : "Generate XML with long names, attlists, etc.",
    "rightsHolder" : "Steven J. DeRose",
    "creator"      : "http://viaf.org/viaf/50334488",
    "type"         : "http://purl.org/dc/dcmitype/Software",
    "language"     : "Python 3.9",
    "created"      : "2025-03-22",
    "modified"     : "2025-03-22",
    "publisher"    : "http://github.com/sderose",
    "license"      : "https://creativecommons.org/licenses/by-sa/3.0/"
}
__version__ = __metadata__["modified"]

descr = """
=Name=

testSuperLong.py

=Description=

Make really big XML constructs and see if they fail.
Direct the output to a file or something that takes XML on stdin.

Note re. checking output with xmllint:
* depth seems to be max 256 unless you set --huge
* name length seems to be max 65535.
* to suppress it's echo of the document, use --noout.

=Some cases=

* element/attr/notation name
* pi target
* pi data
* comment
* cdata ms
* numeric char ref w/ leading 0s
* many attributes
* very deep
* very wide/bushy

==To add==

* ns prefix
* ns url
* qlits for public, system, attr defaults, attr values
* model and other stuff in DTD
* whitespace

=History=

* 2025-03-22: Written by Steven J. DeRose.


=Rights=

Copyright 2025-03-22 by Steven J. DeRose. This work is licensed under a
Creative Commons Attribution-Share-alike 3.0 unported license.
See [http://creativecommons.org/licenses/by-sa/3.0/] for more information.

For the most recent version, see [http://www.derose.net/steve/utilities]
or [https://github.com/sderose].


=Options=
"""

def deep(depth:int) -> str:
    if not args.deep: return ""
    return f"""<p> {'<q>' * depth} T {'</q>' * depth} </q>\n"""


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
            "--deep", action="store_true",
            help="Include deep nesting.")
        parser.add_argument(
            "--power", type=int, default=10,
            help="n for 2**n length.")
        parser.add_argument(
            "--verbose", "-v", action="count", default=0,
            help="Add more messages (repeatable).")
        parser.add_argument(
            "--version", action="version", version=__version__,
            help="Display version information, then exit.")

        args0 = parser.parse_args()

        return(args0)


    ###########################################################################
    #
    args = processOptions()

    for i in range(args.power, args.power+1):
        n = 2**i
        sys.stderr.write("\n\n******* Starting n = %d.\n" % (n))
        ename = "ename_" + "e" * n
        aname = "aname_" + "a" * n
        avalue = "avalue_" + "v" * n
        leadzero = "0" * n
        buf = f"""<?xml version="1.0" encoding="utf-8"?>
<doc>
    <!-- Long element name -->
    <{ename}></{ename}>

    <!-- Long attribute name and value -->
    <e {aname}="{avalue}">
        <!-- Long text node -->
        {ename} {aname} {avalue}
    </e>

    <!-- Long comment -->
    <!-- {avalue} -->

    <!-- Long PI target -->
    <?{avalue} VALUE?>

    <!-- Long PI data -->
    <?TARGET {avalue}?>

    <!-- Long CDATA MS -->
    <![CDATA[ {avalue} ]]>

    <!-- Long numeric char (a comma)-->
    <p>hello&#x{leadzero}2C; world.</p>

    <!-- Many attrs -->
    <p {' '.join('a_%d="v"' % (anum) for anum in range(n))} />

    <!-- Very wide -->
    <p> {''.join('<q/>' for anum in range(n))} </p>

    {deep(n)}
</doc>
"""

    sys.stderr.write(f"Total XML length: {len(buf)}.\n")
    print(buf)
