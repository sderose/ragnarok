#!/usr/bin/env python3
#
from enum import Enum
from dataclasses import dataclass
from typing import List
import regex

class MNodeType(Enum):
    NONE = 0
    NAME = 1
    PCDATA = 2
    ORGROUP = 3
    SEQGROUP = 4
    ANDGROUP = 5

@dataclass
class MGroup:
    conn: str = None
    minO: int = -1
    maxO: int = -1
    items: List = []

class ModelStuff:
    def __init__(self, doctype):
        pass

    def tokensToTree(self, tokens:List):
        """Take a list of tokens such as produced by readModelGroup,
        and return a nested list representing the correct tree. E.g.:
            ( a , b ? , ( c | d ) * ) becomes

        This involves:
          *  Factoring out sequence operators ,|&. Yes, I'm supporting &,
             'cuz at this level it's no extra work. Filter it out later.
          *  Factoring out groups
        """
        stack = [ ]
        for t in tokens:
            if t == "(":
                curGroup = MGroup()
                stack.append(curGroup)
            elif t == ")":
                stack.pop()
            elif t in "|,&":
                if not curGroup.conn: curGroup.conn = t
                elif curGroup.conn != t:
                    raise SyntaxError("Inconsistent connectors.")
            elif t in "+?*":
                pass
            else:
                raise SyntaxError(f"Bad token '{t}' found.")
        return

class Validator:
    def __init__(self, doctype):
        self.doctype = doctype
        self.theMap = {}        # element name -> character
        self.modelTokens = {}   # tokenized content model
        self.modelRegex = {}    # model as regex

    def makeElementMap(self):
        """TODO Deal with #PCDATA, EMPTY, ANY.
        """
        nextCodePoint = 0xE000
        self.theMap = {}
        for x in self.doctype.elements:
            self.theMap[x.ename] = nextCodePoint
            nextCodePoint += 1
            if nextCodePoint >= 0xF8FF: raise IndexError(
                "A schema that big? It might be very useful. But now it is gone.")
        return self.theMap

    def modelTokensToRegex(self, modelTokens:List) -> str:
        """Copy operators verbatim, and map element names to single chars.
        TODO Mixins?
        """
        expr = ""
        for t in modelTokens:
            if t in self.theMap: expr += self.theMap[t]
            else: expr += t
            try:
                regex.compile(expr)
            except Exception as e:
                raise SyntaxError from e
        return expr

    def checkSequence(self, ename, seq) -> int:
        """The sequence is so far, but may require more.
        regex.match(r"a+b+c+", "aaaaabbc", partial=True)
        """
        mappedSeq = self.modelTokensToRegex(seq)
        mat = regex.match(f"^{self.modelRegex[ename]}", mappedSeq, partial=True)
        if mat is None: return 0
        if mat.partial: return 1
        return 30

    def successors(self, ename, seq) -> List:
        """Find what elements could happen next.
        The list should include a "None" entry if it's ok as-is.
        I don't see a way to do this with typical regex engines.
        But it might not be bad to just try all the elements
        that are even mentioned in the rule.
        """
        allowed = []
        for cand in self.modelTokens[ename]:
            if len(cand) == 1 and cand in "()+*?,&|": continue
            seq.append(self.theMap[cand])
            if regex.match(self.modelRegex[ename], seq, partial=True):
                allowed.append(cand)
            seq.pop()
        return allowed
