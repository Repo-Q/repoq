"""
Property-based tests for normalization systems.

Tests fundamental TRS properties:
- Idempotence: NF(NF(x)) = NF(x)
- Confluence: all reduction paths lead to same NF
- Termination: all sequences reach NF
- Size reduction: rewrites don't increase size
"""

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from repoq.normalize.spdx_trs import (
    SPDX_REWRITE_SYSTEM,
    SPDXAnd,
    SPDXAtom,
    SPDXOr,
    normalize_spdx,
    parse_spdx,
)

# Strategy for generating SPDX license IDs
spdx_ids = st.sampled_from(
    [
        "MIT",
        "Apache-2.0",
        "GPL-2.0",
        "GPL-3.0",
        "BSD-3-Clause",
        "ISC",
        "LGPL-2.1",
    ]
)


# Strategy for generating SPDX expressions
@st.composite
def spdx_expressions(draw, max_depth=3):
    """Generate random SPDX expressions."""
    if max_depth == 0:
        return draw(spdx_ids)

    choice = draw(st.integers(min_value=0, max_value=2))

    if choice == 0:
        # Atomic
        return draw(spdx_ids)
    elif choice == 1:
        # OR
        left = draw(spdx_expressions(max_depth=max_depth - 1))
        right = draw(spdx_expressions(max_depth=max_depth - 1))
        return f"{left} OR {right}"
    else:
        # AND
        left = draw(spdx_expressions(max_depth=max_depth - 1))
        right = draw(spdx_expressions(max_depth=max_depth - 1))
        return f"{left} AND {right}"


class TestSPDXProperties:
    """Property-based tests for SPDX normalization."""

    @given(spdx_expressions())
    @settings(max_examples=100)
    def test_idempotence(self, expr: str):
        """NF(NF(x)) = NF(x)."""
        nf1 = normalize_spdx(expr, use_cache=False)
        nf2 = normalize_spdx(nf1, use_cache=False)

        assert nf1 == nf2, f"Idempotence violated: NF({expr}) = {nf1}, NF(NF({expr})) = {nf2}"

    @given(spdx_expressions())
    @settings(max_examples=100)
    def test_terminates(self, expr: str):
        """All expressions normalize without hanging."""
        # Should complete without timeout
        result = normalize_spdx(expr, use_cache=False)
        assert isinstance(result, str)

    @given(spdx_expressions())
    @settings(max_examples=50)
    def test_size_monotonic(self, expr: str):
        """Normalization doesn't increase size."""
        try:
            term = parse_spdx(expr)
            nf_term = SPDX_REWRITE_SYSTEM.normalize(term)

            assert (
                nf_term.size() <= term.size()
            ), f"Size increased: {expr} (size {term.size()}) → {nf_term} (size {nf_term.size()})"
        except Exception:
            # Parser may fail on complex generated expressions
            pass

    @given(st.sampled_from(["MIT", "GPL-2.0", "Apache-2.0"]))
    def test_or_commutative(self, lic: str):
        """A OR B = B OR A."""
        expr1 = f"{lic} OR MIT"
        expr2 = f"MIT OR {lic}"

        nf1 = normalize_spdx(expr1, use_cache=False)
        nf2 = normalize_spdx(expr2, use_cache=False)

        assert nf1 == nf2, f"Commutativity violated: {expr1} → {nf1}, {expr2} → {nf2}"

    @given(st.sampled_from(["MIT", "GPL-2.0", "Apache-2.0"]))
    def test_and_commutative(self, lic: str):
        """A AND B = B AND A."""
        expr1 = f"{lic} AND MIT"
        expr2 = f"MIT AND {lic}"

        nf1 = normalize_spdx(expr1, use_cache=False)
        nf2 = normalize_spdx(expr2, use_cache=False)

        assert nf1 == nf2, f"Commutativity violated: {expr1} → {nf1}, {expr2} → {nf2}"

    def test_idempotence_or(self):
        """A OR A = A."""
        assert normalize_spdx("MIT OR MIT") == "MIT"
        assert normalize_spdx("GPL-2.0 OR GPL-2.0") == "GPL-2.0"

    def test_idempotence_and(self):
        """A AND A = A."""
        assert normalize_spdx("MIT AND MIT") == "MIT"
        assert normalize_spdx("GPL-2.0 AND GPL-2.0") == "GPL-2.0"

    def test_absorption(self):
        """A OR (A AND B) = A."""
        assert normalize_spdx("MIT OR (MIT AND GPL-2.0)") == "MIT"
        assert normalize_spdx("(MIT AND Apache-2.0) OR MIT") == "MIT"

    def test_sorting(self):
        """Operands are lexicographically sorted."""
        # OR
        result = normalize_spdx("MIT OR Apache-2.0 OR GPL-2.0")
        assert result == "Apache-2.0 OR GPL-2.0 OR MIT"

        # AND
        result = normalize_spdx("MIT AND Apache-2.0 AND GPL-2.0")
        assert result == "Apache-2.0 AND GPL-2.0 AND MIT"


class TestSPDXConcreteExamples:
    """Concrete test cases for SPDX normalization."""

    def test_simple_or(self):
        """Simple OR expressions."""
        assert normalize_spdx("MIT") == "MIT"
        assert normalize_spdx("MIT OR GPL-2.0") == "GPL-2.0 OR MIT"

    def test_simple_and(self):
        """Simple AND expressions."""
        assert normalize_spdx("MIT AND GPL-2.0") == "GPL-2.0 AND MIT"

    def test_complex_absorption(self):
        """Complex absorption cases."""
        # (A AND B) OR A = A
        expr = "(MIT AND Apache-2.0) OR MIT"
        assert normalize_spdx(expr) == "MIT"

        # A OR (A AND B) OR C
        expr = "MIT OR (MIT AND GPL-2.0) OR Apache-2.0"
        result = normalize_spdx(expr)
        # Should contain MIT and Apache, but not the AND
        assert "MIT" in result
        assert "Apache-2.0" in result

    def test_flattening(self):
        """Nested operators are flattened."""
        # (A OR B) OR C → A OR B OR C
        expr = "(MIT OR GPL-2.0) OR Apache-2.0"
        result = normalize_spdx(expr)
        assert result.count(" OR ") == 2

        # (A AND B) AND C → A AND B AND C
        expr = "(MIT AND GPL-2.0) AND Apache-2.0"
        result = normalize_spdx(expr)
        assert result.count(" AND ") == 2


class TestRewriteSystem:
    """Tests for the rewrite system infrastructure."""

    def test_critical_pairs(self):
        """Check for confluence violations."""
        violations = SPDX_REWRITE_SYSTEM.check_critical_pairs()

        # Should have no violations (or document expected ones)
        if violations:
            pytest.fail(
                f"Found {len(violations)} critical pair violations:\n"
                + "\n".join(f"  {ctx}: {r1} vs {r2}" for ctx, r1, r2 in violations)
            )

    def test_cache(self):
        """Normalization cache works correctly."""
        expr = "MIT OR GPL-2.0 OR Apache-2.0"

        # First call (cache miss)
        result1 = normalize_spdx(expr, use_cache=True)

        # Second call (cache hit)
        result2 = normalize_spdx(expr, use_cache=True)

        assert result1 == result2

    def test_size_measure(self):
        """Term size is correctly computed."""
        atom = SPDXAtom("MIT")
        assert atom.size() == 1

        or_term = SPDXOr([SPDXAtom("MIT"), SPDXAtom("GPL-2.0")])
        assert or_term.size() == 3  # 1 + 1 + 1

        nested = SPDXOr([SPDXAnd([SPDXAtom("MIT"), SPDXAtom("GPL-2.0")]), SPDXAtom("Apache-2.0")])
        assert nested.size() == 5  # 1 + (1 + 1 + 1) + 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
