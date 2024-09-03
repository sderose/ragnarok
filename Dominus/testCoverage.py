#!/usr/bin/env python3
#
# Doesn't check instance variables
# What of stuff inherited from list/dict?
#
import xml.dom.minidom
import BaseDOM

descr = """
Compare the dir() items in minidom vs. BaseDOM.

"""

fmt = "  %-24s %26s %26s"
nope = "----"

def compareDir(cl1, cl2):
    dir1 = dir(cl1)
    dir2 = dir(cl2)

    dirUnion = set(dir1).union(set(dir2))

    print("\n" + fmt % ("="*24, "minidom "+cl1.__name__, "BaseDOM "+cl2.__name__))
    for x in sorted(list(dirUnion)):
        if (x.startswith("_")): continue
        msg1 = type(getattr(cl1, x)).__name__ if x in dir1 else nope
        msg2 = type(getattr(cl2, x)).__name__ if x in dir2 else nope

        if (args.omitInherited):
            if (in_superclass(cl1, x) and in_superclass(cl2, x)): continue
        if (args.omitExtensions and msg1 == nope): continue
        if (args.omitBothHave and (msg1 != nope and msg2 != nope)): continue
        if (args.omitMatches and
            (msg1 == msg2 or (msg1=="int" and msg2=="NodeTypes"))): continue
        print(fmt % (x, msg1, msg2))

def in_superclass(cls, member):
    return member in set(dir(cls.__base__)) & set(dir(cls))


##############################################################################
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
            "--omitBothHave", action="store_true",
            help="Don't display items both versions have.")
        parser.add_argument(
            "--omitExtensions", action="store_true",
            help="Don't display BaseDOM extensions.")
        parser.add_argument(
            "--omitInherited", action="store_true",
            help="Don't display items in both superclasses.")
        parser.add_argument(
            "--omitMatches", action="store_true",
            help="Don't display items where both have same type.")
        parser.add_argument(
            "--quiet", "-q", action="store_true",
            help="Suppress most messages.")
        parser.add_argument(
            "--verbose", "-v", action="count", default=0,
            help="Add more messages (repeatable).")
        parser.add_argument(
            "--version", action="version", version="0.9",
            help="Display version information, then exit.")

        args0 = parser.parse_args()
        return(args0)


    ###########################################################################
    #
    args = processOptions()

    compareDir(xml.dom.minidom.Node,             BaseDOM.Node)
    compareDir(xml.dom.minidom.Element,          BaseDOM.Element)
    compareDir(xml.dom.minidom.Text,             BaseDOM.Text)
    compareDir(xml.dom.minidom.Document,         BaseDOM.Document)
    compareDir(xml.dom.minidom.CDATASection,     BaseDOM.CDATASection)
    compareDir(xml.dom.minidom.ProcessingInstruction, BaseDOM.ProcessingInstruction)
    compareDir(xml.dom.minidom.Comment,          BaseDOM.Comment)
    compareDir(xml.dom.minidom.Notation,         BaseDOM.Notation)
    compareDir(xml.dom.minidom.Attr,             BaseDOM.Attr)
    compareDir(xml.dom.minidom.NodeList,         BaseDOM.NodeList)
    compareDir(xml.dom.minidom.NamedNodeMap,     BaseDOM.NamedNodeMap)
    #compareDir(xml.dom.minidom.EntityReference,  BaseDOM.EntityReference)

