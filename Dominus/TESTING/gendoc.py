#!/usr/bin/env python3
#
# genDoc.py
# 2024-09-07: Written by Steven J. DeRose.
#
import sys
#import os
#import codecs
import math
import random
import string
from typing import Dict, List
import logging

#import xmlschema
#from xml.etree.ElementTree import Element, SubElement, tostring

#from xml.dom import minidom as theDOMmodule
import basedom as theDOMmodule

impl = theDOMmodule.getDOMImplementation()
Document = theDOMmodule.Document
Element = theDOMmodule.Element

lg = logging.getLogger("genDoc")

__metadata__ = {
    "title"        : "genDoc",
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

Generate somewhat random XML documents.

Eventually this should work directly from a chosen schema.

Parameters:

Maxima:
* Depth
* Fanout (nummber of children for each non-leaf node)
* XML NAME length
* Attributes value length
* Attributes value token count
* Attributes per node
* Text node length
* Range of code points to include

Frequencies
* Distribution of lengths -- uniform, poisson, normal,...
* % mixins for pi, comment, char ref, cdata
"""


###############################################################################
#
# English letter frequency (approx.)
#
LETTER_FREQ = {
    'a': 8.2, 'b': 1.5, 'c': 2.8, 'd': 4.3, 'e': 13, 'f': 2.2, 'g': 2, 'h': 6.1,
    'i': 7, 'j': 0.15, 'k': 0.77, 'l': 4, 'm': 2.4, 'n': 6.7, 'o': 7.5, 'p': 1.9,
    'q': 0.095, 'r': 6, 's': 6.3, 't': 9.1, 'u': 2.8, 'v': 0.98, 'w': 2.4,
    'x': 0.15, 'y': 2, 'z': 0.074
}

rootType = "html"
soup = ("i", "b", "#PCDATA", "tt", "em" )


###############################################################################
#
class dumSchema:
    fakeSchema = {  # Anything not listed is #PCDATA
        "html":   ["head", "body"],
        "head":   ["title", "meta*"],
        "body":   [ "div1*" ],
        "div1":   [ "h1", "div2*"],
        "div2":   ("p", "bq", "ol", "ul")
    }

    def genSeq(self, par:str="html") -> List[str]:
        if (par in dumSchema.fakeSchema):
            rule = dumSchema.fakeSchema
        else:
            rule = soup

        chList = []
        if (isinstance(rule, list)):
            for chType in rule:
                chList.extend(self.genByType(chType))
        if (isinstance(rule, set)):
            n = random.randrange(0, 3)
            for _ in range(n):
                chList.extend(self.genByType(random.randrange(0, len(rule))))
        return chList

    def genByType(self, typ:str):
        chList = []
        if (typ[-1] == "?"):
            if (random.random() < 0.5): chList.append(typ[0:-1])
        elif (typ[-1] == "+"):
            n = random.randrange(1, 7)
            for _ in range(n): chList.append(typ[0:-1])
        elif (typ[-1] == "*"):
            n = random.randrange(0, 3)
            for _ in range(n): chList.append(typ[0:-1])
        else:
            chList.append(typ)
        return chList


###############################################################################
#
class XmlGenerator:
    """Started with draft by Claude.
    Issues:
        * Uppercase -> starts
        * Rest of XSD types
        * PI/comment/char-ref add-ins
        * way to set high-prob elems/attrs
            ** p, list
            ** @id @class
        * doesn't generate forward idrefs, or use 1st idref if before 1st id.
    """

    def __init__(self, xsd_file:str=None):
        self.id_pool = set()

        self.maxInt = 99999

        self.attrProb = 0.2
        self.textProb = 0.5
        self.piProb = 0.02
        self.commentProb = 0.02

        self.ucProb = 0.1
        self.spaceProb = 0.15
        self.namechars = string.ascii_letters + string.digits + '_'
        self.idPrefix = "id_"

        self.theDom = None

    def generate_text(self, length):
        text = []
        for _ in range(length):
            char = random.choices(
                list(LETTER_FREQ.keys()),
                weights=list(LETTER_FREQ.values()))[0]
            if random.random() < self.ucProb: char = char.upper()
            text.append(char)
            if random.random() < self.spaceProb: text.append(' ')
        return ''.join(text)

    def generate_nmtoken(self, length:int=8) -> str:
        return ''.join(random.choice(self.namechars) for _ in range(length))

    def generate_id(self) -> str:
        cand = self.generate_nmtoken()
        while (self.idPrefix+cand in self.id_pool):
            cand = self.generate_nmtoken()
        self.id_pool.add(cand)
        return cand

    def generate_idref(self) -> str:
        if not self.id_pool: return self.generate_id()
        return random.choice(list(self.id_pool))

    def generate_nmtokens(self, min_count=1, max_count=5) -> str:
        count = random.randint(min_count, max_count)
        return ' '.join(self.generate_nmtoken() for _ in range(count))

    def generate_random_value(self, xsd_type) -> str:
        #if isinstance(xsd_type, xmlschema.XsdAtomicBuiltin):
        if (1 or 0):
            if xsd_type.name == 'string':
                return self.generate_text(random.randint(5, 20))
            elif xsd_type.name in ['integer', 'int']:
                return str(random.randint(0, self.maxInt))
            elif xsd_type.name == 'NMTOKEN':
                return self.generate_nmtoken()
            elif xsd_type.name == 'ID':
                return self.generate_id()
            elif xsd_type.name == 'IDREF':
                return self.generate_idref()
            # Add more type handlers as needed
        return ''

    def generate_random_element(self, element):
        new_element = self.theDom.createElement(element.name)

        if element.type.is_complex():
            content_type = element.type.content_type
            if content_type.is_element_only():
                #self.generate_element_only_content(new_element, content_type)
                pass
            elif content_type.is_mixed():
                self.generate_mixed_content(new_element, content_type)
            elif content_type.is_empty():
                pass  # No content for empty elements
        else:
            new_element.text = self.generate_random_value(element.type)

        # Generate attributes
        for attribute in element.attributes.values():
            if attribute.use == 'required' or random.random() < self.attrProb:
                if attribute.name == 'class':
                    value = self.generate_nmtokens()
                else:
                    value = self.generate_random_value(attribute.type)
                new_element.set(attribute.name, value)

        return new_element

    def generate_element_only_content(self, parent, content_type):
        for group in content_type.iter_model():
            min_occurs = group.min_occurs or 0
            max_occurs = group.max_occurs or 1 if group.max_occurs is None else group.max_occurs
            num_occurs = random.randint(min_occurs, max_occurs)

            for _ in range(num_occurs):
                child_elem = self.generate_random_element(group)
                parent.append(child_elem)


            #for _ in range(num_occurs):
            #    if isinstance(group, xmlschema.XsdGroup):
            #        self.generate_group_content(parent, group)
            #    elif isinstance(group, xmlschema.XsdElement):
            #        child_elem = self.generate_random_element(group)
            #x        parent.append(child_elem)


    def generate_mixed_content(self, parent, content_type):
        self.generate_element_only_content(parent, content_type)
        # Add some text nodes between elements
        children = list(parent)
        for i in range(len(children) + 1):
            if random.random() < self.textProb:  # % chance to add text
                text = self.generate_text(random.randint(3, 10))
                if i == 0:
                    if parent.text is None:
                        parent.text = text
                    else:
                        parent.text += text
                else:
                    if i == len(children):
                        if parent.tail is None:
                            parent.tail = text
                        else:
                            parent.tail += text
                    else:
                        if children[i-1].tail is None:
                            children[i-1].tail = text
                        else:
                            children[i-1].tail += text

    def generate_group_content(self, parent, group):
        if group.model == 'sequence':
            for child in group.iter_elements():
                child_elem = self.generate_random_element(child)
                parent.append(child_elem)
        elif group.model == 'choice':
            child = random.choice(list(group.iter_elements()))
            child_elem = self.generate_random_element(child)
            parent.append(child_elem)
        elif group.model == 'all':
            for child in group.iter_elements():
                if random.random() < 0.5:  # 50% chance to include each element
                    child_elem = self.generate_random_element(child)
                    parent.append(child_elem)

    def generate_PI(self):
        target = self.generate_nmtoken()
        data = self.generate_text(length=80)
        data = data.replace("?>", "__")
        pi = self.theDom.createProcessingInstruction(target, data)
        return pi

    def generate_comment(self):
        data = self.generate_text(length=80)
        data = data.replace("--", "==")
        com = self.theDom.createComment(data)
        return com

    def generate_random_xml(self):
        #root_element = self.schema.root_element
        root_element = rootType
        xml_root = self.generate_random_element(root_element)
        return xml_root


###############################################################################
###############################################################################
#
class NameGen:
    """Better to read an actual schema and use...
    """
    namechars = string.ascii_lowercase + string.ascii_uppercase + string.digits

    _root = [ "html" ]
    _div  = [ "div" ]
    _para = [ "p", "blcokquote" ]
    _soup = [ "i", "b", "tt", "strike" ]

    _attrPool = {
        "class":  str,
        "id":     str,
        "href":   str,
    }

    _maxLen = 10

    @staticmethod
    def makeNmToken() -> str:
        nameLen = random.randint(1, NameGen._maxLen)
        nam = ""
        for _ in range(nameLen):
            nam += NameGen.namechars[random.randint(0, len(NameGen.namechars))]
        return nam

    @staticmethod
    def makeAttr(typ:str) -> (str, str):
        nam = NameGen.makeNmToken()
        if (True or typ in [ "ID", "NMTOKEN", "IDREF" ]):
            val = NameGen.makeNmToken()
        return (nam, val)


###############################################################################
#
class TextGen:
    @staticmethod
    def randomText(n:int):
        buf = ""
        for _i in range(n):
            buf += chr(random.randint(32, 126))
        return buf

    @staticmethod
    def getSomeText(n:int):
        buf = """Lorem ipsum dolor sit amet, consectetur adipisicing elit, sed do
    eiusmod tempor incididunt ut labore et dolore magna aliqua. Ut
    enim ad minim veniam, quis nostrud exercitation ullamco laboris
    nisi ut aliquip ex ea commodo consequat. Duis aute irure dolor in
    reprehenderit in voluptate velit esse cillum dolore eu fugiat
    nulla pariatur. Excepteur sint occaecat cupidatat non proident,
    sunt in culpa qui officia deserunt mollit anim id est laborum. """
        ncopies = math.ceil(n/len(buf))
        return (buf * ncopies)[0:n]


###############################################################################
#
class XmlGen:
    def __init__(self, nonLatin:bool=False,
        depth:int=3, fanout:int=10, textLen:int=10, nAttrs:int=10):
        self.nonLatin = nonLatin
        self.depth = depth
        self.fanout = fanout
        self.textLen = textLen
        self.nAttrs = nAttrs
        self.nsURI = "http://example.com"
        self.rootName = "html"

        self.domDoc = None
        self.child1 = self.child2 = self.docEl = self.doc = None

    def buildDoc(self):
        """On my Mac: fanout 50 should take a few seconds.
        Total nodes created = 2 * fanout**3 + fanout**2 + fanout
        """
        #x = randomText(self.textLen)
        x = TextGen.getSomeText(self.textLen)

        attrs = { "id":"id0001", "class":"important" }

        doc = impl.createDocument(namespaceURI=self.nsURI, qualifiedName=self.rootName,
            doctype=None)
        docEl = doc.documentElement
        self.addNChildren(docEl, name="div1", n=self.fanout, attrs=attrs)
        for i1, ch1 in enumerate(docEl.childNodes):
            self.addNChildren(ch1, name="div2", n=self.fanout, attrs=attrs)
            for i2, ch2 in enumerate(ch1.childNodes):
                self.addNChildren(ch2, name="div3", n=self.fanout, attrs=attrs)
                for i3, ch3 in enumerate(ch2.childNodes):
                    tn = doc.createTextNode("%s.%d.%d.%d" % (x, i1, i2, i3))
                    ch3.appendChild(tn)
        return doc

    def addNChildren(self, node, name:str="div", n:int=100, attrs:Dict=None, rev:bool=False):
        doc = node.ownerDocument
        for _i in range(n):
            ch = doc.createElement(name)
            if (attrs):
                for k, v in attrs.items(): ch.setAttribute(k, v)
            if (not node.childNodes): node.appendChild(ch)
            elif (rev): node.insertBefore(ch, node.childNodes[0])
            else: node.appendChild(ch)

    def buildDoc2(self):
        #print("Starting setup, using %s", DOMImplementation.__file__)

        DOCELTYPE = "html"
        self.doc:Document = impl.createDocument("http://example.com/ns", DOCELTYPE, None)
        assert isinstance(self.doc, Document)
        assert self.doc.ownerDocument is None

        self.docEl:Element = self.doc.documentElement
        assert isinstance(self.docEl, Element)
        assert (self.docEl.nodeName == DOCELTYPE)
        assert len(self.docEl.childNodes) == 0

        # Add some more nodes

        self.child1 = self.doc.createElement('child1')
        self.child1.setAttribute('attr1', 'value1')
        self.docEl.appendChild(self.child1)

        self.child2 = self.doc.createElement('child2')
        self.docEl.appendChild(self.child2)
        assert len(self.docEl.childNodes) == 2
        assert self.docEl.childNodes[1] == self.child2

        grandchild = self.doc.createElement('grandchild')
        self.child2.appendChild(grandchild)

        text_node1 = self.doc.createTextNode('Some text content')
        self.child1.appendChild(text_node1)

        # Add empty node
        empty_node = self.doc.createElement('empty')
        self.docEl.appendChild(empty_node)

        # Add mixed content
        mixed = self.doc.createElement('mixed')
        mixed.appendChild(self.doc.createTextNode('Text before '))
        mixed.appendChild(self.doc.createElement('inline'))
        mixed.appendChild(self.doc.createTextNode(' and after'))
        self.docEl.appendChild(mixed)


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
        lg.critical("Point to an XSD.")
        sys.exit()

    # Usage
    generator = XmlGenerator(args.files[0])
    random_dom = generator.generate_random_xml()
    random_dom.writexml()
