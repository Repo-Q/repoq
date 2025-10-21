from __future__ import annotations
import json, re, os
from dataclasses import dataclass
from typing import List, Tuple

@dataclass
class Rule:
    lhs: str
    rhs: str

class TRSEngine:
    """Naive string-pattern TRS engine (educational).
    - Patterns are simplified; variables like A,B,C,X,Y,Z represent wildcards.
    - Not a general-purpose theorem prover — intended for demo/experiments.
    """
    VARS = ("A","B","C","X","Y","Z")

    def __init__(self, rules: List[Rule]):
        self.rules = rules

    @staticmethod
    def load(path: str) -> "TRSEngine":
        data = json.load(open(path, "r", encoding="utf-8"))
        rules = [Rule(lhs=r[0], rhs=r[1]) for r in data.get("rules", [])]
        return TRSEngine(rules)

    def _compile(self, pattern: str) -> re.Pattern:
        # Very coarse: replace VAR names with regex groups that don't cross whitespace/quotes
        p = re.escape(pattern)
        for v in self.VARS:
            p = p.replace(re.escape(v), r"(?P<%s>[^\s\)\(\}\{]+)" % v)
        return re.compile(p)

    def rewrite_once(self, term: str) -> Tuple[str, bool]:
        for r in self.rules:
            regex = self._compile(r.lhs)
            m = regex.search(term)
            if m:
                repl = r.rhs
                for v in self.VARS:
                    if v in m.groupdict():
                        repl = repl.replace(v, m.group(v))
                new_term = term[:m.start()] + repl + term[m.end():]
                return new_term, True
        return term, False

    def normal_form(self, term: str, max_steps: int = 256) -> str:
        cur = term
        for _ in range(max_steps):
            nxt, changed = self.rewrite_once(cur)
            if not changed:
                return cur
            cur = nxt
        raise RuntimeError("Potential non-termination (max steps exceeded)")
