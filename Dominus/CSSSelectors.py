#!/usr/bin/env python3
#
import re
from typing import Any

from xml.dom import minidom
from xml.dom.minidom import Node

class CSSSelectors:
    """
    name
    *
    [name?]#id
    [name?].class
    name[attrname]
    name[attrname="value"]  (and *= $= ~= |= ^=)  (and " [is]" at end) (and unquoted vale as ident

    name desc
    name + nextSib
    name > child
    name ~ follSib

    :first-child
    :first-of-type
    :has(...) ??
    :is(selector*)  (any) :where
    :lang()
    :lang-child
    :last-of-type

    :not()
    :nth-child()
    :nth-of-type()
    :nth-last-child()
    :nth-last-of-type()
    :only-child
    :only-of-type
    :root

    Grammar (backslashing, colon)
        top     ::= atom ( topOp atom )*
        topOp   ::= s* ("+" | ">" | "~" | " " | "!") s*
        atom    ::= star | namePlus | id | class | virtual
        star    ::= "*"
        nameP   ::= name | name "[" atname (op atval)? "]"
        name    ::= \\w[-\\w]*
        id      ::= "#" name
        class   ::= "." name
        virtual ::= ":" name ( "(" arg ")" )?
        arg     ::= [^()]*
    """
    nameX = r"\w[-\w]*"
    topExpr = r"(\w+|\*)?(\.\w+)"


class CSSSelector(Node):
    """Drafted by Claude 3.5.
    """
    def __init__(self, selector):
        self.selector = selector
        self.parsed_selector = self.parse_selector(selector)

    def parse_selector(self, selector):
        """Just divide at the top level, to a list of parts and
        operators. Manage escaping and nested [].
        Top-level operators:
            > child
            + next-sibling
            ~ any later siblings
            space descendant
            | namespace separate ???
            || column combinator ???
        """
        parts = []
        current = ''
        in_bracket = 0
        escaped = False
        for char in selector:
            if (escaped):
                current += char
                escaped = False
            if (char == "\\"):
                escaped = True
            elif char in '>[]+~' and not in_bracket:
                if current:
                    parts.append(current.strip())
                parts.append(char)
                current = ''
            elif char == '[':
                in_bracket += 1
                current += char
            elif char == ']':
                in_bracket -= 1
                current += char
            elif char.isspace() and not in_bracket:
                if current:
                    parts.append(current.strip())
                    current = ''
            else:
                current += char
        if current:
            parts.append(current.strip())
        return parts

    def match(self, node):
        return self._match_parts(node, self.parsed_selector)

    def _match_parts(self, node, parts):
        if not parts:
            return [node]

        part = parts[0]
        remaining = parts[1:]

        if part == '>':
            return self._match_child(node, remaining)
        elif part == '+':
            return self._match_adjacent_sibling(node, remaining)
        elif part == '~':
            return self._match_general_sibling(node, remaining)
        else:
            return self._match_descendant(node, part, remaining)

    def _match_child(self, node, parts):
        matches = []
        for child in node.childNodes:
            if child.nodeType == child.ELEMENT_NODE:
                matches.extend(self._match_parts(child, parts))
        return matches

    def _match_adjacent_sibling(self, node, parts):
        matches = []
        sibling = node.nextSibling
        while sibling and sibling.nodeType != sibling.ELEMENT_NODE:
            sibling = sibling.nextSibling
        if sibling:
            matches.extend(self._match_parts(sibling, parts))
        return matches

    def _match_general_sibling(self, node, parts):
        matches = []
        sibling = node.nextSibling
        while sibling:
            if sibling.nodeType == sibling.ELEMENT_NODE:
                matches.extend(self._match_parts(sibling, parts))
            sibling = sibling.nextSibling
        return matches

    def _match_descendant(self, node, part, remaining):
        matches = []
        if self._match_element(node, part):
            if not remaining:
                matches.append(node)
            else:
                matches.extend(self._match_parts(node, remaining))
        for child in node.childNodes:
            if child.nodeType == child.ELEMENT_NODE:
                matches.extend(self._match_descendant(child, part, remaining))
        return matches

    def _match_element(self, node, selector):
        if selector == '*':
            return True
        if selector.startswith('#'):
            return node.getAttribute('id') == selector[1:]  # TODO ID
        elif selector.startswith('.'):
            return selector[1:] in node.getAttribute('class').split()
        elif '[' in selector:
            tag, attr = selector.split('[', 1)
            attr = attr.rstrip(']')
            if tag and tag != '*' and tag != node.tagName:
                return False
            mat = re.split(r"\s*([$*^~|]?=)\s*([is])?\s*$", attr)
            if (not mat): raise ValueError("Bad [] syntax in '%s'." % (attr))
            return self.testAttr(
                node, mat.group(1), mat.group(2), mat.group(3), mat.group(4))
        elif ':' in selector:  # TODO Handle multiple pseudos
            tag, pseudo = selector.split(':')
            if tag and tag != '*' and tag != node.tagName: return False
            pseudo, _lpar, arg = pseudo.partition("(")
            if (arg): theArg = arg.strip(" )")
            return self.testPseudo(node, pseudo, theArg)
        else:
            return node.tagName == selector

    def testAttr(self, node, aname:str, op:str, tgtValue:str, caseFlag:str) -> bool:
        """Test whether the node's @aname satisfies the [] condition.
        """
        if (not op and not tgtValue):
            return node.hasAttribute(aname)
        tgtValue = tgtValue.strip(" \t\n\r\"'")
        docValue = node.getAttribute(aname).strip()
        if (caseFlag in "iI"):
            tgtValue = tgtValue.lower()
            docValue = docValue.lower()

        if (op == '='):                                 # equal
            return docValue == tgtValue
        elif (op == '~='):                              # has token
            return " " + tgtValue + " " in " " + docValue + " "
        elif (op == '|='):                              # eq or starts w/ val+"-"
            return docValue.startswith(tgtValue+"-")
        elif (op == "^="):                              # starts w/
            return docValue.startswith(tgtValue)
        elif (op == "$="):                              # endswith
            return docValue.endswith(tgtValue)
        elif (op == "*="):                              # contains
            return tgtValue in docValue
        else:
            raise ValueError("Unexpected operator '%s'." % (op))

    def testPseudo(self, node, pseudo:str, n:Any) -> bool:
        """This does not include ones relating to form or UI status;
        just things about structure per se.
        Maybe add: dir (bidi)
        Presumably the CSS "nth" items count from 1.
        """
        if (pseudo == "only-child"):
            return len(node.parentNode.childNodes) == 1
        elif (pseudo == "only-of-type"):
            return (node.getChildIndex(ofType=True) == 0
                and node.getRChildIndex(ofType=True) == -1)
        elif (pseudo == "first-child"):
            return node.parentNode.firstChild == node
        elif (pseudo == "first-of-type"):
            return node.getChildIndex(ofType=True) == 0
        elif (pseudo == "nth-child"):
            return node.getChildIndex() == int(n)-1
        elif (pseudo == "nth-of-type"):
            return node.getChildIndex(ofType=True) == int(n)-1
        elif (pseudo == "nth-last-child"):
            return node.getRChildIndex() == -int(n)
        elif (pseudo == "nth-last-of-type"):
            return node.getRChildIndex(ofType=True) == -int(n)
        elif (pseudo == "last-child"):
            return node.parentNode.lastChild == node
        elif (pseudo == "last-of-type"):
            return node.getRChildIndex(ofType=True) == -1

        elif (pseudo == "root"):
            return node == node.ownerDocument
        elif (pseudo == "empty"):
            return not node.childNodes
        elif (pseudo == "has"):
            raise KeyError("Unsupported")
        elif (pseudo == "is (aka matches) (cf where)"):
            raise KeyError("Unsupported")
        elif (pseudo == "lang"):
            curLang = node.getInheritedAttribute("xml:lang")
            return curLang == n  # TODO: ignore case? Strip subcode?
        else:
            raise KeyError("Pseudo-CSS word '%s' not supported." % (pseudo))

    def select(self, root):
        return self._match_parts(root, self.parsed_selector)

    @staticmethod
    def looseEqual(s1:str, s2:str, caseFlag:str):
        """Seemingly CSS only does ASCII case-folding. srsly?
        """
        if (caseFlag in "iI"):
            return s1.strip().lower() == s2.strip().lower()
        else:
            return s1.strip() == s2.strip()


# Example usage
def create_sample_dom():
    doc = minidom.parseString("""
    <html>
        <body>
            <div class="container">
                <p id="first-paragraph">Hello</p>
                <p class="text">World <span class="highlight">!</span></p>
                <div class="blue">Blue div</div>
            </div>
        </body>
    </html>
    """)
    return doc.documentElement

# Test the implementation
dom = create_sample_dom()
selectors = [
    'div.container p',
    'p#first-paragraph',
    'div > p.text',
    'p + p',
    'div p:first-child',
    'p[class]',
    '*',
    '*.blue',
    '.container',
    '#first-paragraph',
    'div *'
]

for s in selectors:
    sel = CSSSelector(s)
    results = sel.select(dom)
    print(f"Selector '{s}' matched {len(results)} elements:")
    for result in results:
        print(f"  {result.tagName} (id: {result.getAttribute('id')}, class: " +
            result.getAttribute('class'))
    print()
