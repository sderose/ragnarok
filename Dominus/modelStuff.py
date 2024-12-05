#!/usr/bin/env python3
#
from dataclasses import dataclass
from typing import List, Dict
import regex

#from domenums import
from basedomtypes import NMTOKEN_t, FlexibleEnum

class MNodeType(FlexibleEnum):
    """Kinds of model (sub)-groups
    """
    NONE = 0
    NAME = 1
    PCDATA = 2
    ORGROUP = 3
    SEQGROUP = 4
    ANDGROUP = 5

@dataclass
class MGroup:
    """An actual Model group, with connector type, repetition limites, and token list.
    """
    conn: str = None
    minO: int = -1
    maxO: int = -1
    items: List = []

class ModelStuff:
    """Support content models, primarily by converting a list of tokens to an AST.
    """
    def __init__(self, doctype:str):
        self.doctype = doctype

    def tokensToTree(self, tokens:List) -> List:
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
        return stack

class Validator:
    """Sneaky way to validate:
        * Assign a Unicode character to each element type name
        * Convert element type names in a model to those characters
        * Ditch commas but leave OR-bars, reps, and parentheses. No "&" for now.
        * Convert a sequence of child-nodeNames to a Unicode character string.
        * Match.
    """
    def __init__(self, doctype:str):
        self.doctype = doctype
        self.theMap = {}        # element name -> character
        self.modelTokens = {}   # tokenized content model
        self.modelRegex = {}    # model as regex

    def makeElementMap(self) -> Dict:
        """Assign a (private-use) character to each distinct element type name.
        TODO Deal with #PCDATA, EMPTY, ANY.
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
        But drop commas and whitespace.
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

    def checkSequence(self, ename:NMTOKEN_t, seq:List) -> int:
        """See if a sequence of element types is ok so far (it may require more).
        regex.match(r"a+b+c+", "aaaaabbc", partial=True)
        Returns:
            0 -- match failed (sequence invalid
            1 -- match is an ok beginning but needs more to complete
            30 -- match is ok and complete (but might permit more)
            (do we need a separate case for complete and cannot have more?)
        """
        mappedSeq = self.modelTokensToRegex(seq)
        mat = regex.match(f"^{self.modelRegex[ename]}", mappedSeq, partial=True)
        if mat is None: return 0
        if mat.partial: return 1
        return 30

    def successors(self, ename:NMTOKEN_t, seq:List) -> List:
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
