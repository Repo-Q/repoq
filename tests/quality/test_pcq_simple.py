"""Tests for Per-Component Quality (PCQ) with min-aggregation.

Phase 2.4: ZAG PCQ Anti-Gaming Aggregator
References: FR-04, ADR-007, V02 (Anti-gaming)

Simplified test suite focusing on core PCQ min-aggregation behavior.
Uses real File/Module/Project models from repoq.core.model.

Theoretical Foundation:
    PCQ(S) = min_{m∈modules} Q(m)

    Theorem (Gaming Resistance):
        ∀ modules M, improving Q(m_i) for m_i ≠ min-module
        does NOT increase PCQ(M).
"""

from repoq.core.model import File, Module, Project
from repoq.quality.pcq import calculate_pcq, compute_quality_score


class TestPCQMinAggregation:
    """Test core min-aggregation behavior."""

    def test_pcq_returns_minimum_module_quality(self):
        """PCQ should return the MINIMUM quality across all modules."""
        project = Project(id="test", name="Test Project")

        # Module A: Good quality (low complexity/hotness)
        modA = Module(id="modA", name="ModuleA", path="src/modA")
        fileA = File(
            id="fA",
            path="src/modA/good.py",
            language="Python",
            lines_of_code=100,
            complexity=3.0,  # Low complexity
            hotness=0.1,  # Low hotness
        )

        # Module B: Poor quality (high complexity/hotness) - THE BOTTLENECK
        modB = Module(id="modB", name="ModuleB", path="src/modB")
        fileB = File(
            id="fB",
            path="src/modB/bad.py",
            language="Python",
            lines_of_code=200,
            complexity=25.0,  # High complexity
            hotness=0.9,  # High hotness
        )

        project.modules = {"modA": modA, "modB": modB}
        project.files = {"fA": fileA, "fB": fileB}

        # Compute PCQ
        pcq = calculate_pcq(project)

        # Compute individual module scores
        proj_a = Project(id="a", name="A")
        proj_a.files = {"fA": fileA}
        score_a = compute_quality_score(proj_a).score

        proj_b = Project(id="b", name="B")
        proj_b.files = {"fB": fileB}
        score_b = compute_quality_score(proj_b).score

        # PCQ must equal min(score_a, score_b)
        expected_min = min(score_a, score_b)
        assert (
            pcq == expected_min
        ), f"PCQ={pcq} should equal min({score_a}, {score_b})={expected_min}"

    def test_pcq_single_module_equals_module_quality(self):
        """PCQ with only 1 module should equal that module's quality."""
        project = Project(id="test", name="Test")

        mod = Module(id="mod1", name="Module1", path="src/mod1")
        file1 = File(
            id="f1",
            path="src/mod1/main.py",
            language="Python",
            lines_of_code=100,
            complexity=8.0,
            hotness=0.4,
        )

        project.modules = {"mod1": mod}
        project.files = {"f1": file1}

        pcq = calculate_pcq(project)
        module_quality = compute_quality_score(project).score

        assert pcq == module_quality

    def test_pcq_no_modules_uses_global_quality(self):
        """PCQ with no modules should return global project quality."""
        project = Project(id="test", name="Test")

        # No modules, just files
        file1 = File(
            id="f1",
            path="main.py",
            language="Python",
            lines_of_code=100,
            complexity=5.0,
        )

        project.files = {"f1": file1}

        pcq = calculate_pcq(project)
        global_quality = compute_quality_score(project).score

        assert pcq == global_quality

    def test_pcq_empty_modules_returns_perfect_score(self):
        """PCQ with modules but no files should return 100.0."""
        project = Project(id="test", name="Test")

        mod1 = Module(id="mod1", name="Module1", path="src/mod1")
        mod2 = Module(id="mod2", name="Module2", path="src/mod2")

        project.modules = {"mod1": mod1, "mod2": mod2}
        project.files = {}  # No files

        pcq = calculate_pcq(project)

        assert pcq == 100.0, "No files should result in perfect score"


class TestAntiGamingResistance:
    """Test gaming resistance properties of min-aggregator."""

    def test_improving_good_module_does_not_increase_pcq(self):
        """GAMING SCENARIO: Improving non-min module should NOT change PCQ.

        Developer tries to game the system by improving Module A (already good)
        to hide poor quality of Module B.

        Expected: PCQ unchanged (depends only on min).
        """
        project = Project(id="test", name="Test")

        # Module A: Already good
        modA = Module(id="modA", name="ModuleA", path="src/modA")
        fileA = File(
            id="fA",
            path="src/modA/good.py",
            language="Python",
            lines_of_code=100,
            complexity=5.0,
            hotness=0.2,
        )

        # Module B: Poor (the bottleneck)
        modB = Module(id="modB", name="ModuleB", path="src/modB")
        fileB = File(
            id="fB",
            path="src/modB/bad.py",
            language="Python",
            lines_of_code=200,
            complexity=25.0,
            hotness=0.8,
        )

        project.modules = {"modA": modA, "modB": modB}
        project.files = {"fA": fileA, "fB": fileB}

        pcq_before = calculate_pcq(project)

        # GAMING ATTEMPT: Dramatically improve Module A
        fileA.complexity = 1.0  # Perfect complexity
        fileA.hotness = 0.0  # No hotness

        pcq_after = calculate_pcq(project)

        # PCQ should remain UNCHANGED (Module B is still the bottleneck)
        assert pcq_after == pcq_before, (
            f"Gaming detected! Improving non-min module changed PCQ: " f"{pcq_before} → {pcq_after}"
        )

    def test_improving_worst_module_increases_pcq(self):
        """Improving the WORST module SHOULD increase PCQ (legitimate improvement)."""
        project = Project(id="test", name="Test")

        modA = Module(id="modA", name="ModuleA", path="src/modA")
        fileA = File(
            id="fA",
            path="src/modA/good.py",
            language="Python",
            lines_of_code=100,
            complexity=5.0,
            hotness=0.2,
        )

        modB = Module(id="modB", name="ModuleB", path="src/modB")
        fileB = File(
            id="fB",
            path="src/modB/bad.py",
            language="Python",
            lines_of_code=200,
            complexity=25.0,
            hotness=0.9,
        )

        project.modules = {"modA": modA, "modB": modB}
        project.files = {"fA": fileA, "fB": fileB}

        pcq_before = calculate_pcq(project)

        # LEGITIMATE FIX: Improve Module B (the bottleneck)
        fileB.complexity = 8.0  # Reduce complexity
        fileB.hotness = 0.3  # Reduce hotness

        pcq_after = calculate_pcq(project)

        # PCQ SHOULD improve
        assert (
            pcq_after > pcq_before
        ), f"Fixing worst module should improve PCQ: {pcq_before} → {pcq_after}"

    def test_average_gaming_blocked(self):
        """9 perfect modules + 1 terrible module = PCQ reflects terrible module.

        Average would be ~91%, but min-aggregator returns ~low% (the weak link).
        """
        project = Project(id="test", name="Test")

        # Create 9 perfect modules
        for i in range(9):
            mod = Module(id=f"mod{i}", name=f"Module{i}", path=f"src/mod{i}")
            file = File(
                id=f"f{i}",
                path=f"src/mod{i}/perfect.py",
                language="Python",
                lines_of_code=50,
                complexity=1.0,  # Perfect
                hotness=0.0,  # Perfect
            )
            project.modules[f"mod{i}"] = mod
            project.files[f"f{i}"] = file

        # Create 1 terrible module
        bad_mod = Module(id="bad", name="BadModule", path="src/bad")
        bad_file = File(
            id="fbad",
            path="src/bad/terrible.py",
            language="Python",
            lines_of_code=500,
            complexity=50.0,  # Terrible
            hotness=0.99,  # Terrible
        )
        project.modules["bad"] = bad_mod
        project.files["fbad"] = bad_file

        pcq = calculate_pcq(project)

        # Compute bad module quality
        bad_proj = Project(id="bad", name="BadModule")
        bad_proj.files = {"fbad": bad_file}
        bad_quality = compute_quality_score(bad_proj).score

        # PCQ should equal the bad module (NOT the average of 9 perfect + 1 bad)
        assert pcq == bad_quality, f"PCQ={pcq} should equal worst module quality={bad_quality}"

        # PCQ should be significantly lower than average (91% if averaged)
        # With 9 perfect (100) + 1 bad (78.5), average would be ~97.8
        # But PCQ = min = 78.5 (reflects worst module)
        assert pcq < 90, "PCQ should reflect worst module, not average"


class TestPCQProperties:
    """Test mathematical properties of PCQ."""

    def test_pcq_monotonicity(self):
        """Improving any module should NOT decrease PCQ (monotonicity property).

        Property: Q'(m) ≥ Q(m) ⟹ PCQ'(S) ≥ PCQ(S)
        """
        project = Project(id="test", name="Test")

        modA = Module(id="modA", name="ModuleA", path="src/modA")
        fileA = File(
            id="fA",
            path="src/modA/a.py",
            language="Python",
            lines_of_code=100,
            complexity=10.0,
            hotness=0.5,
        )

        modB = Module(id="modB", name="ModuleB", path="src/modB")
        fileB = File(
            id="fB",
            path="src/modB/b.py",
            language="Python",
            lines_of_code=150,
            complexity=15.0,
            hotness=0.6,
        )

        project.modules = {"modA": modA, "modB": modB}
        project.files = {"fA": fileA, "fB": fileB}

        pcq_before = calculate_pcq(project)

        # Improve Module A
        fileA.complexity = 5.0
        fileA.hotness = 0.3

        pcq_after = calculate_pcq(project)

        # PCQ should NOT decrease
        assert pcq_after >= pcq_before, (
            f"Monotonicity violated: improving module decreased PCQ " f"{pcq_before} → {pcq_after}"
        )

    def test_pcq_deterministic(self):
        """PCQ calculation should be deterministic (same input → same output)."""
        project = Project(id="test", name="Test")

        mod = Module(id="mod1", name="Module1", path="src/mod1")
        file1 = File(
            id="f1",
            path="src/mod1/a.py",
            language="Python",
            lines_of_code=100,
            complexity=8.0,
            hotness=0.4,
        )

        project.modules = {"mod1": mod}
        project.files = {"f1": file1}

        pcq1 = calculate_pcq(project)
        pcq2 = calculate_pcq(project)

        assert pcq1 == pcq2, "PCQ should be deterministic"

    def test_pcq_bounds(self):
        """PCQ ∈ [0, 100] for all valid projects."""
        project = Project(id="test", name="Test")

        # Extreme case: terrible quality
        mod_bad = Module(id="bad", name="Bad", path="src/bad")
        file_bad = File(
            id="fbad",
            path="src/bad/terrible.py",
            language="Python",
            lines_of_code=1000,
            complexity=100.0,
            hotness=1.0,
        )

        # Extreme case: perfect quality
        mod_good = Module(id="good", name="Good", path="src/good")
        file_good = File(
            id="fgood",
            path="src/good/perfect.py",
            language="Python",
            lines_of_code=10,
            complexity=1.0,
            hotness=0.0,
        )

        project.modules = {"bad": mod_bad, "good": mod_good}
        project.files = {"fbad": file_bad, "fgood": file_good}

        pcq = calculate_pcq(project)

        assert 0 <= pcq <= 100, f"PCQ out of bounds: {pcq}"


class TestPCQIntegration:
    """Integration tests with realistic scenarios."""

    def test_realistic_ecommerce_project(self):
        """Realistic e-commerce project with 4 modules of varying quality."""
        project = Project(id="ecommerce", name="E-Commerce Platform")

        # Auth: High quality
        auth_mod = Module(id="auth", name="Authentication", path="src/auth")
        auth_file = File(
            id="auth_py",
            path="src/auth/login.py",
            language="Python",
            lines_of_code=80,
            complexity=4.0,
            hotness=0.1,
        )

        # Payment: Medium quality
        payment_mod = Module(id="payment", name="Payment", path="src/payment")
        payment_file = File(
            id="payment_py",
            path="src/payment/stripe.py",
            language="Python",
            lines_of_code=150,
            complexity=10.0,
            hotness=0.4,
        )

        # Inventory: Low quality (THE BOTTLENECK)
        inventory_mod = Module(id="inventory", name="Inventory", path="src/inventory")
        inventory_file = File(
            id="inventory_py",
            path="src/inventory/warehouse.py",
            language="Python",
            lines_of_code=300,
            complexity=28.0,
            hotness=0.85,
        )

        # Analytics: High quality
        analytics_mod = Module(id="analytics", name="Analytics", path="src/analytics")
        analytics_file = File(
            id="analytics_py",
            path="src/analytics/dashboard.py",
            language="Python",
            lines_of_code=120,
            complexity=6.0,
            hotness=0.2,
        )

        project.modules = {
            "auth": auth_mod,
            "payment": payment_mod,
            "inventory": inventory_mod,
            "analytics": analytics_mod,
        }
        project.files = {
            "auth_py": auth_file,
            "payment_py": payment_file,
            "inventory_py": inventory_file,
            "analytics_py": analytics_file,
        }

        pcq = calculate_pcq(project)

        # Compute inventory quality (should be the minimum)
        inventory_proj = Project(id="inv", name="Inventory")
        inventory_proj.files = {"inventory_py": inventory_file}
        inventory_quality = compute_quality_score(inventory_proj).score

        # PCQ should equal inventory (the worst module)
        assert (
            pcq == inventory_quality
        ), f"PCQ={pcq} should equal inventory quality={inventory_quality}"

        # PCQ should be lower than other high-quality modules
        # (auth, payment, analytics all have better quality)
        # Test that PCQ reflects the bottleneck, not the average
        assert pcq < 85, "PCQ should reflect low-quality inventory module (bottleneck)"
