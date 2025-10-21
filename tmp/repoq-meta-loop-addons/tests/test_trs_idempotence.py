from repoq.trs.engine import TRSEngine
import json, os

def test_idempotence_rules():
    eng = TRSEngine.load(os.path.join(os.path.dirname(__file__), '..', 'trs', 'metrics.json'))
    for expr in ["max(x, x)", "min(y, y)", "z ∧ z", "a ∨ a"]:
        nf = eng.normal_form(expr)
        assert nf in ("x", "y", "z", "a"), f"Unexpected NF: {expr} -> {nf}"
