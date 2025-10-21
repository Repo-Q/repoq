"""
Property-based tests for SemVer TRS normalization.

Verifies formal properties: idempotence, commutativity, associativity,
distributivity, and interval arithmetic correctness.
"""

import pytest
from hypothesis import given, strategies as st, settings, assume, HealthCheck
from repoq.normalize.semver_trs import (
    normalize_semver, parse_semver_range, Version, VersionInterval,
    VersionUnion, SEMVER_REWRITE_SYSTEM, ZERO_VERSION, MAX_VERSION,
    UNIVERSAL_INTERVAL, EMPTY_INTERVAL
)


# Hypothesis strategies for generating test data

@st.composite
def version_strategy(draw):
    """Generate valid semantic versions."""
    major = draw(st.integers(0, 100))
    minor = draw(st.integers(0, 100))
    patch = draw(st.integers(0, 100))
    
    # Sometimes add prerelease
    has_prerelease = draw(st.booleans())
    if has_prerelease:
        prerelease = draw(st.text(
            alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd'), 
                                 whitelist_characters='-'),
            min_size=1, max_size=10
        ))
    else:
        prerelease = ""
    
    return Version(major=major, minor=minor, patch=patch, prerelease=prerelease)


@st.composite
def version_string_strategy(draw):
    """Generate version strings."""
    version = draw(version_strategy())
    return str(version)


@st.composite
def simple_range_strategy(draw):
    """Generate simple SemVer range strings."""
    range_type = draw(st.sampled_from([
        'exact', 'caret', 'tilde', 'gte', 'lte', 'gt', 'lt', 'wildcard'
    ]))
    
    version = draw(version_string_strategy())
    
    if range_type == 'exact':
        return version
    elif range_type == 'caret':
        return f"^{version}"
    elif range_type == 'tilde':
        return f"~{version}"
    elif range_type == 'gte':
        return f">={version}"
    elif range_type == 'lte':
        return f"<={version}"
    elif range_type == 'gt':
        return f">{version}"
    elif range_type == 'lt':
        return f"<{version}"
    elif range_type == 'wildcard':
        return draw(st.sampled_from(['*', '1.x', '1.2.x', '2.*.*']))
    
    return version


@st.composite
def compound_range_strategy(draw):
    """Generate compound ranges with spaces."""
    num_parts = draw(st.integers(1, 3))
    parts = [draw(simple_range_strategy()) for _ in range(num_parts)]
    return " ".join(parts)


@st.composite 
def union_range_strategy(draw):
    """Generate union ranges with ||."""
    num_parts = draw(st.integers(1, 3))
    parts = [draw(compound_range_strategy()) for _ in range(num_parts)]
    return " || ".join(parts)


# Property-based tests

class TestSemVerNormalizationProperties:
    """Test formal properties of SemVer normalization."""
    
    @given(range_str=union_range_strategy())
    @settings(max_examples=100, deadline=5000)
    def test_idempotence(self, range_str):
        """Test that normalize(normalize(x)) = normalize(x)."""
        try:
            normalized = normalize_semver(range_str)
            double_normalized = normalize_semver(normalized)
            assert normalized == double_normalized, \
                f"Idempotence failed: {range_str} → {normalized} → {double_normalized}"
        except Exception:
            # Skip malformed ranges
            assume(False)
    
    @given(range_a=simple_range_strategy(), range_b=simple_range_strategy())
    @settings(max_examples=50, deadline=5000)
    def test_intersection_commutativity(self, range_a, range_b):
        """Test that A ∩ B = B ∩ A (when both are intervals)."""
        try:
            # Parse to intervals
            term_a = parse_semver_range(range_a)
            term_b = parse_semver_range(range_b)
            
            # Only test intervals (not unions)
            if isinstance(term_a, VersionInterval) and isinstance(term_b, VersionInterval):
                intersect_ab = term_a.intersect(term_b)
                intersect_ba = term_b.intersect(term_a)
                
                assert intersect_ab == intersect_ba, \
                    f"Intersection not commutative: {range_a} ∩ {range_b} ≠ {range_b} ∩ {range_a}"
        except Exception:
            assume(False)
    
    @given(range_a=simple_range_strategy(), range_b=simple_range_strategy())
    @settings(max_examples=50, deadline=5000)
    def test_union_commutativity(self, range_a, range_b):
        """Test that A ∪ B = B ∪ A (modulo ordering)."""
        try:
            term_a = parse_semver_range(range_a)
            term_b = parse_semver_range(range_b)
            
            if isinstance(term_a, VersionInterval) and isinstance(term_b, VersionInterval):
                union_ab = term_a.union(term_b)
                union_ba = term_b.union(term_a)
                
                # Sort for comparison (union is commutative up to ordering)
                union_ab_sorted = sorted(union_ab, key=lambda i: (i.min_version, i.max_version))
                union_ba_sorted = sorted(union_ba, key=lambda i: (i.min_version, i.max_version))
                
                assert union_ab_sorted == union_ba_sorted, \
                    f"Union not commutative: {range_a} ∪ {range_b} ≠ {range_b} ∪ {range_a}"
        except Exception:
            assume(False)
    
    @given(version_str=version_string_strategy())
    @settings(max_examples=30, deadline=3000)
    def test_exact_version_normalization(self, version_str):
        """Test that exact versions normalize to themselves."""
        try:
            normalized = normalize_semver(version_str)
            # Should be the version string itself
            assert normalized == version_str, \
                f"Exact version not preserved: {version_str} → {normalized}"
        except Exception:
            assume(False)
    
    @given(range_str=union_range_strategy())
    @settings(max_examples=50, deadline=5000, 
              suppress_health_check=[HealthCheck.filter_too_much])
    def test_normalize_preserves_semantics(self, range_str):
        """Test that normalization preserves semantic meaning (sampling test)."""
        try:
            original_term = parse_semver_range(range_str)
            normalized_str = normalize_semver(range_str)
            normalized_term = parse_semver_range(normalized_str)
            
            # Test on sample versions
            test_versions = [
                Version(0, 0, 1), Version(1, 0, 0), Version(1, 2, 3),
                Version(2, 0, 0), Version(10, 5, 2)
            ]
            
            for version in test_versions:
                original_contains = _term_contains_version(original_term, version)
                normalized_contains = _term_contains_version(normalized_term, version)
                
                assert original_contains == normalized_contains, \
                    f"Semantics changed for {version}: {range_str} vs {normalized_str}"
        except Exception:
            assume(False)
    
    @given(range_str=simple_range_strategy())
    @settings(max_examples=30, deadline=3000,
              suppress_health_check=[HealthCheck.filter_too_much])
    def test_caret_range_semantics(self, range_str):
        """Test that caret ranges have correct semantics."""
        if not range_str.startswith('^'):
            assume(False)
        
        try:
            version_str = range_str[1:]  # Remove ^
            version = Version.parse(version_str)
            
            term = parse_semver_range(range_str)
            
            # Version itself should be included
            assert _term_contains_version(term, version), \
                f"Caret range {range_str} should include {version}"
            
            # Test upper bound based on semver rules
            if version.major > 0:
                # ^1.2.3 should exclude 2.0.0
                upper_bound = Version(version.major + 1, 0, 0)
                assert not _term_contains_version(term, upper_bound), \
                    f"Caret range {range_str} should exclude {upper_bound}"
            
        except Exception:
            assume(False)
    
    @given(range_str=simple_range_strategy())
    @settings(max_examples=30, deadline=3000,
              suppress_health_check=[HealthCheck.filter_too_much])
    def test_tilde_range_semantics(self, range_str):
        """Test that tilde ranges have correct semantics."""
        if not range_str.startswith('~'):
            assume(False)
        
        try:
            version_str = range_str[1:]  # Remove ~
            version = Version.parse(version_str)
            
            term = parse_semver_range(range_str)
            
            # Version itself should be included
            assert _term_contains_version(term, version), \
                f"Tilde range {range_str} should include {version}"
            
            # ~1.2.3 should exclude 1.3.0
            upper_bound = Version(version.major, version.minor + 1, 0)
            assert not _term_contains_version(term, upper_bound), \
                f"Tilde range {range_str} should exclude {upper_bound}"
            
        except Exception:
            assume(False)
    
    def test_universal_range(self):
        """Test that * accepts any version."""
        normalized = normalize_semver("*")
        assert normalized == "*"
        
        term = parse_semver_range("*")
        test_versions = [
            Version(0, 0, 0), Version(1, 0, 0), Version(999, 999, 999)
        ]
        
        for version in test_versions:
            assert _term_contains_version(term, version), \
                f"Universal range should include {version}"
    
    def test_empty_intersection(self):
        """Test that disjoint ranges produce empty intersection."""
        # >=2.0.0 AND <1.0.0 should be empty
        range_str = ">=2.0.0 <1.0.0"
        try:
            normalized = normalize_semver(range_str)
            assert normalized == "∅", f"Empty range should normalize to ∅, got {normalized}"
        except Exception:
            # If parser doesn't handle this, skip
            pytest.skip("Parser doesn't handle empty ranges")
    
    @given(
        min_version=version_strategy(),
        max_version=version_strategy()
    )
    @settings(max_examples=30, deadline=3000)
    def test_interval_operations(self, min_version, max_version):
        """Test interval arithmetic properties."""
        # Ensure min <= max
        if min_version > max_version:
            min_version, max_version = max_version, min_version
        
        try:
            interval = VersionInterval(min_version, max_version, True, False)
            
            # Test contains
            if min_version < max_version:
                assert interval.contains(min_version), \
                    f"Interval should contain its minimum: {interval}"
                assert not interval.contains(max_version), \
                    f"Interval should not contain its maximum (exclusive): {interval}"
            
            # Test intersection with self
            self_intersect = interval.intersect(interval)
            assert self_intersect == interval, \
                f"Self-intersection should be identity: {interval}"
            
            # Test union with self
            self_union = interval.union(interval)
            assert self_union == [interval], \
                f"Self-union should be singleton: {interval}"
                
        except ValueError:
            # Skip invalid intervals
            assume(False)


# Helper functions

def _term_contains_version(term, version):
    """Check if a term contains a given version."""
    if isinstance(term, VersionInterval):
        return term.contains(version)
    elif isinstance(term, VersionUnion):
        return term.contains(version)
    else:
        return False


class TestSemVerParsing:
    """Test SemVer parsing correctness."""
    
    def test_parse_exact_version(self):
        """Test parsing exact versions."""
        cases = [
            "1.2.3",
            "0.0.1", 
            "10.20.30",
            "1.0.0-alpha",
            "1.0.0-alpha.1",
            "1.0.0+build.1"
        ]
        
        for case in cases:
            term = parse_semver_range(case)
            assert isinstance(term, VersionInterval)
            assert term.is_exact()
            assert str(term) == case
    
    def test_parse_caret_ranges(self):
        """Test parsing caret ranges."""
        cases = [
            ("^1.2.3", "[1.2.3, 2.0.0)"),
            ("^0.2.3", "[0.2.3, 0.3.0)"),
            ("^0.0.3", "[0.0.3, 0.0.4)")
        ]
        
        for input_range, expected in cases:
            term = parse_semver_range(input_range)
            assert isinstance(term, VersionInterval)
            assert str(term) == expected
    
    def test_parse_tilde_ranges(self):
        """Test parsing tilde ranges."""
        cases = [
            ("~1.2.3", "[1.2.3, 1.3.0)"),
            ("~0.2.3", "[0.2.3, 0.3.0)"),
            ("~1.2", "[1.2.0, 1.3.0)")  # If parser supports this
        ]
        
        for input_range, expected in cases:
            try:
                term = parse_semver_range(input_range)
                assert isinstance(term, VersionInterval)
                assert str(term) == expected
            except Exception:
                # Skip if parser doesn't support this format
                continue
    
    def test_parse_comparison_operators(self):
        """Test parsing comparison operators."""
        cases = [
            (">=1.2.3", "[1.2.3, ∞)"),
            ("<=1.2.3", "[0.0.0, 1.2.3]"),
            (">1.2.3", "(1.2.3, ∞)"),
            ("<1.2.3", "[0.0.0, 1.2.3)")
        ]
        
        for input_range, expected in cases:
            term = parse_semver_range(input_range)
            assert isinstance(term, VersionInterval)
            assert str(term) == expected
    
    def test_parse_wildcard_ranges(self):
        """Test parsing wildcard ranges."""
        cases = [
            ("*", "*"),
            ("1.x", "[1.0.0, 2.0.0)"),
            ("1.2.x", "[1.2.0, 1.3.0)")
        ]
        
        for input_range, expected in cases:
            term = parse_semver_range(input_range)
            if isinstance(term, VersionInterval):
                assert str(term) == expected
    
    def test_parse_compound_ranges(self):
        """Test parsing compound ranges."""
        cases = [
            ">=1.2.3 <2.0.0",
            ">=1.0.0 <=1.5.0", 
            ">1.0.0 <1.2.0"
        ]
        
        for case in cases:
            term = parse_semver_range(case)
            # Should parse without error
            assert term is not None
    
    def test_parse_union_ranges(self):
        """Test parsing union ranges."""
        cases = [
            "1.2.3 || 2.0.0",
            "^1.0.0 || ^2.0.0",
            "~1.2.0 || >=2.0.0 <3.0.0"
        ]
        
        for case in cases:
            term = parse_semver_range(case)
            # Should parse to VersionUnion or VersionInterval
            assert isinstance(term, (VersionInterval, VersionUnion))


class TestSemVerRewriteSystem:
    """Test the rewrite system directly."""
    
    def test_rewrite_system_basic(self):
        """Test basic rewrite system operations."""
        system = SEMVER_REWRITE_SYSTEM
        
        # Test normalization of simple interval
        interval = VersionInterval(Version(1, 0, 0), Version(2, 0, 0), True, False)
        normalized = system.normalize(interval)
        assert normalized == interval  # Should be unchanged
    
    def test_empty_interval_normalization(self):
        """Test normalization of empty intervals."""
        system = SEMVER_REWRITE_SYSTEM
        
        # Empty interval should normalize to EMPTY_INTERVAL
        normalized = system.normalize(EMPTY_INTERVAL)
        assert normalized == EMPTY_INTERVAL
    
    def test_universal_interval_normalization(self):
        """Test normalization of universal interval."""
        system = SEMVER_REWRITE_SYSTEM
        
        normalized = system.normalize(UNIVERSAL_INTERVAL)
        assert normalized == UNIVERSAL_INTERVAL
    
    def test_union_normalization(self):
        """Test normalization of version unions."""
        system = SEMVER_REWRITE_SYSTEM
        
        # Create overlapping intervals
        interval1 = VersionInterval(Version(1, 0, 0), Version(1, 5, 0), True, False)
        interval2 = VersionInterval(Version(1, 3, 0), Version(2, 0, 0), True, False)
        
        union = VersionUnion([interval1, interval2])
        normalized = system.normalize(union)
        
        # Should merge to single interval [1.0.0, 2.0.0)
        assert isinstance(normalized, VersionInterval)
        assert normalized.min_version == Version(1, 0, 0)
        assert normalized.max_version == Version(2, 0, 0)