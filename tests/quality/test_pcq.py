"""Tests for Per-Component Quality (PCQ) with min-aggregation.

Phase 2.4: ZAG PCQ Anti-Gaming Aggregator
References: FR-04, ADR-007, V02 (Anti-gaming)

Test Coverage:
    - TestPCQCalculation: Basic min-aggregation logic
    - TestAntiGaming: Gaming resistance scenarios
    - TestModuleTypes: directory, layer, bounded_context
    - TestEdgeCases: Empty modules, single module, no files
    - TestIntegration: Realistic multi-module projects

Theoretical Foundation:
    PCQ(S) = min_{m∈modules} Q(m)

    Theorem (Gaming Resistance):
        ∀ modules M, improving Q(m_i) for m_i ≠ min-module
        does NOT increase PCQ(M).

        Proof: PCQ depends only on min Q(m), so Q(m_i) > min
               has no effect on final score.
"""

# Note: calculate_pcq is in legacy repoq.quality module (not repoq/quality/)
import repoq.quality as quality_module
from repoq.core.model import File, Module, Project


def calculate_pcq(project: Project, module_type: str = "directory") -> float:
    """Wrapper for legacy calculate_pcq in repoq.quality module."""
    return quality_module.calculate_pcq(project, module_type)


def compute_quality_score(project: Project):
    """Wrapper for legacy compute_quality_score in repoq.quality module."""
    return quality_module.compute_quality_score(project)


class TestPCQCalculation:
    """Test basic PCQ min-aggregation calculation."""

    def test_pcq_single_module(self):
        """PCQ with single module should equal module quality."""
        project = Project(id="test", name="Test")

        # Create module with 1 file
        module = Module(
            id="module1",
            name="Module1",
            path="src/module1",
        )
        file1 = File(
            id="file1",
            path="src/module1/main.py",
            language="Python",
            lines_of_code=100,
            complexity=5.0,  # Low complexity = good quality
            hotness=0.2,  # Low hotness = good quality
        )

        project.modules = {"module1": module}
        project.files = {"file1": file1}

        pcq = calculate_pcq(project, module_type="directory")

        # PCQ should equal quality of the only module
        module_quality = compute_quality_score(project)
        assert 0 <= pcq <= 100
        assert pcq == module_quality.score

    def test_pcq_min_aggregation(self):
        """PCQ should return MINIMUM quality across modules."""
        project = Project(id="test", name="Test")

        # Module 1: High quality (low complexity, low hotness)
        module1 = Module(id="mod1", name="Module1", path="src/mod1")
        file1 = File(
            id="f1",
            path="src/mod1/good.py",
            language="Python",
            lines_of_code=50,
            complexity=2.0,  # Low complexity = good
            hotness=0.1,  # Low hotness = good
        )

        # Module 2: Low quality (high complexity, high hotness)
        module2 = Module(id="mod2", name="Module2", path="src/mod2")
        file2 = File(
            id="f2",
            path="src/mod2/bad.py",
            language="Python",
            lines_of_code=200,
            complexity=25.0,  # High complexity = bad
            hotness=0.9,  # High hotness = bad
        )

        project.modules = {"mod1": module1, "mod2": module2}
        project.files = {"f1": file1, "f2": file2}

        pcq = calculate_pcq(project)

        # PCQ should reflect the WORSE module (mod2)
        # Compute quality for each module separately
        project_mod1 = Project(id="test/mod1", name="Module1")
        project_mod1.files = {"f1": file1}
        q1 = compute_quality_score(project_mod1).score

        project_mod2 = Project(id="test/mod2", name="Module2")
        project_mod2.files = {"f2": file2}
        q2 = compute_quality_score(project_mod2).score

        # PCQ = min(q1, q2)
        assert pcq == min(q1, q2)
        assert pcq < max(q1, q2)  # PCQ should be less than the best module

    def test_pcq_three_modules(self):
        """PCQ with 3 modules: min(Q1, Q2, Q3)."""
        project = Project(id="test", name="Test")

        # Module 1: Medium quality
        mod1 = Module(id="m1", name="M1", path="src/m1")
        f1 = File(
            id="f1",
            path="src/m1/a.py",
            language="Python",
            lines_of_code=100,
            complexity=10.0,
            hotness=0.5,
        )

        # Module 2: High quality
        mod2 = Module(id="m2", name="M2", path="src/m2")
        f2 = File(
            id="f2",
            path="src/m2/b.py",
            language="Python",
            lines_of_code=50,
            complexity=3.0,
            hotness=0.1,
        )

        # Module 3: Low quality (should be PCQ)
        mod3 = Module(id="m3", name="M3", path="src/m3")
        f3 = File(
            id="f3",
            path="src/m3/c.py",
            language="Python",
            lines_of_code=300,
            complexity=30.0,
            hotness=0.95,
        )

        project.modules = {"m1": mod1, "m2": mod2, "m3": mod3}
        project.files = {"f1": f1, "f2": f2, "f3": f3}

        pcq = calculate_pcq(project)

        # Compute individual module scores
        scores = []
        for mid, files in [("m1", {"f1": f1}), ("m2", {"f2": f2}), ("m3", {"f3": f3})]:
            p = Project(id=f"test/{mid}", name=mid)
            p.files = files
            scores.append(compute_quality_score(p).score)

        # PCQ = min(scores)
        assert pcq == min(scores)


class TestAntiGaming:
    """Test anti-gaming properties of PCQ min-aggregator."""

    def test_gaming_resistance_compensation(self):
        """Improving high-quality module CANNOT compensate for low-quality module.

        Gaming scenario: Developer improves Module A (already good)
        to hide poor quality of Module B.

        Expected: PCQ remains unchanged (depends only on min).
        """
        project = Project(id="test", name="Test")

        # Module A: Already good quality
        modA = Module(id="modA", name="ModuleA", path="src/modA")
        fileA = File(
            id="fA",
            path="src/modA/good.py",
            language="Python",
            lines_of_code=100,
            cyclomatic_complexity=5,
            test_coverage=0.85,
        )

        # Module B: Poor quality (the weak link)
        modB = Module(id="modB", name="ModuleB", path="src/modB")
        fileB = File(
            id="fB",
            path="src/modB/bad.py",
            language="Python",
            lines_of_code=200,
            cyclomatic_complexity=25,
            test_coverage=0.3,
        )

        project.modules = {"modA": modA, "modB": modB}
        project.files = {"fA": fileA, "fB": fileB}

        pcq_before = calculate_pcq(project)

        # GAMING ATTEMPT: Improve Module A (increase coverage 85% → 100%)
        fileA.test_coverage = 1.0
        fileA.cyclomatic_complexity = 2  # Also reduce complexity

        pcq_after = calculate_pcq(project)

        # PCQ should NOT change (Module B is still the bottleneck)
        assert pcq_after == pcq_before, "Gaming detected! Improving non-min module changed PCQ."

    def test_gaming_resistance_all_modules_required(self):
        """PCQ forces improvement of ALL modules, not just average.

        Gaming scenario: 9 modules with 100% quality, 1 module with 10% quality.
        Average would be 91%, but PCQ should be 10%.

        Expected: PCQ = 10% (min), not 91% (mean).
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
                cyclomatic_complexity=2,
                test_coverage=1.0,
            )
            project.modules[f"mod{i}"] = mod
            project.files[f"f{i}"] = file

        # Create 1 terrible module (the weak link)
        bad_mod = Module(id="bad", name="BadModule", path="src/bad")
        bad_file = File(
            id="fbad",
            path="src/bad/terrible.py",
            language="Python",
            lines_of_code=500,
            cyclomatic_complexity=50,
            test_coverage=0.1,
        )
        project.modules["bad"] = bad_mod
        project.files["fbad"] = bad_file

        pcq = calculate_pcq(project)

        # Compute bad module quality
        bad_project = Project(id="test/bad", name="BadModule")
        bad_project.files = {"fbad": bad_file}
        bad_quality = compute_quality_score(bad_project).score

        # PCQ should equal the bad module (min), NOT the average
        assert pcq == bad_quality
        assert pcq < 50, "PCQ should reflect the worst module, not average"

    def test_no_gaming_via_module_split(self):
        """Splitting a bad module doesn't improve PCQ unless quality improves.

        Gaming scenario: Developer splits 1 bad module into 2 bad modules,
        hoping to dilute the impact.

        Expected: PCQ still reflects the worst module.
        """
        # Original: 1 bad module
        project1 = Project(id="test1", name="Test1")
        mod1 = Module(id="mod1", name="Module1", path="src/mod1")
        file1 = File(
            id="f1",
            path="src/mod1/bad.py",
            language="Python",
            lines_of_code=400,
            cyclomatic_complexity=40,
            test_coverage=0.2,
        )
        project1.modules = {"mod1": mod1}
        project1.files = {"f1": file1}
        pcq1 = calculate_pcq(project1)

        # After split: 2 modules, same total complexity
        project2 = Project(id="test2", name="Test2")
        modA = Module(id="modA", name="ModuleA", path="src/modA")
        fileA = File(
            id="fA",
            path="src/modA/bad_part1.py",
            language="Python",
            lines_of_code=200,
            cyclomatic_complexity=20,
            test_coverage=0.2,
        )
        modB = Module(id="modB", name="ModuleB", path="src/modB")
        fileB = File(
            id="fB",
            path="src/modB/bad_part2.py",
            language="Python",
            lines_of_code=200,
            cyclomatic_complexity=20,
            test_coverage=0.2,
        )
        project2.modules = {"modA": modA, "modB": modB}
        project2.files = {"fA": fileA, "fB": fileB}
        pcq2 = calculate_pcq(project2)

        # PCQ should be similar (both modules still have same CC/LOC ratio)
        # Splitting doesn't magically improve quality
        assert (
            abs(pcq1 - pcq2) < 10
        ), "Module split gaming detected: PCQ changed without real improvement"


class TestModuleTypes:
    """Test PCQ with different module types (directory, layer, bounded_context)."""

    def test_pcq_directory_modules(self):
        """PCQ with module_type='directory'."""
        project = Project(id="test", name="Test")

        # Directory-based modules
        mod1 = Module(id="src", name="Source", path="src")
        mod2 = Module(id="tests", name="Tests", path="tests")

        file1 = File(
            id="f1",
            path="src/main.py",
            language="Python",
            lines_of_code=100,
            cyclomatic_complexity=5,
            test_coverage=0.8,
        )
        file2 = File(
            id="f2",
            path="tests/test_main.py",
            language="Python",
            lines_of_code=50,
            cyclomatic_complexity=2,
            test_coverage=1.0,
        )

        project.modules = {"src": mod1, "tests": mod2}
        project.files = {"f1": file1, "f2": file2}

        pcq = calculate_pcq(project, module_type="directory")
        assert 0 <= pcq <= 100

    def test_pcq_bounded_context_modules(self):
        """PCQ with module_type='bounded_context' (DDD).

        Note: BoundedContext is a conceptual DDD entity, but calculate_pcq
        uses generic Module objects. This test demonstrates usage pattern.
        """
        project = Project(id="test", name="Test")

        # Modules representing bounded contexts (DDD pattern)
        auth_module = Module(
            id="auth",
            name="Authentication",
            path="src/auth",
        )
        billing_module = Module(
            id="billing",
            name="Billing",
            path="src/billing",
        )

        file1 = File(
            id="f1",
            path="src/auth/login.py",
            language="Python",
            lines_of_code=100,
            cyclomatic_complexity=8,
            test_coverage=0.9,
        )
        file2 = File(
            id="f2",
            path="src/billing/invoice.py",
            language="Python",
            lines_of_code=150,
            cyclomatic_complexity=12,
            test_coverage=0.7,
        )

        # calculate_pcq uses project.modules (generic Module objects)
        project.modules = {
            "auth": auth_module,
            "billing": billing_module,
        }
        project.files = {"f1": file1, "f2": file2}

        pcq = calculate_pcq(project, module_type="bounded_context")
        assert 0 <= pcq <= 100


class TestEdgeCases:
    """Test edge cases for PCQ calculation."""

    def test_pcq_no_modules(self):
        """PCQ with no modules should use global quality."""
        project = Project(id="test", name="Test")

        # No modules, but has files
        file1 = File(
            id="f1",
            path="main.py",
            language="Python",
            lines_of_code=100,
            cyclomatic_complexity=5,
            test_coverage=0.8,
        )
        project.files = {"f1": file1}

        pcq = calculate_pcq(project)

        # Should equal global quality
        global_quality = compute_quality_score(project).score
        assert pcq == global_quality

    def test_pcq_empty_modules(self):
        """PCQ with modules but no files should return 100.0 (perfect)."""
        project = Project(id="test", name="Test")

        # Modules exist but have no files
        mod1 = Module(id="mod1", name="Module1", path="src/mod1")
        mod2 = Module(id="mod2", name="Module2", path="src/mod2")

        project.modules = {"mod1": mod1, "mod2": mod2}
        project.files = {}  # No files!

        pcq = calculate_pcq(project)

        # No files = no violations = perfect score
        assert pcq == 100.0

    def test_pcq_module_with_no_matching_files(self):
        """PCQ when module exists but files don't match module path."""
        project = Project(id="test", name="Test")

        mod1 = Module(id="mod1", name="Module1", path="src/module1")

        # File doesn't match module path
        file1 = File(
            id="f1",
            path="other/unrelated.py",
            language="Python",
            lines_of_code=100,
            cyclomatic_complexity=5,
            test_coverage=0.8,
        )

        project.modules = {"mod1": mod1}
        project.files = {"f1": file1}

        pcq = calculate_pcq(project)

        # No matching files for module = 100.0
        assert pcq == 100.0


class TestIntegration:
    """Integration tests with realistic multi-module projects."""

    def test_realistic_multi_module_project(self):
        """Realistic project with 4 modules of varying quality."""
        project = Project(id="ecommerce", name="E-Commerce Platform")

        # Module 1: Auth (high quality)
        auth_mod = Module(id="auth", name="Authentication", path="src/auth")
        auth_file = File(
            id="auth_py",
            path="src/auth/login.py",
            language="Python",
            lines_of_code=80,
            cyclomatic_complexity=4,
            test_coverage=0.95,
        )

        # Module 2: Payment (medium quality)
        payment_mod = Module(id="payment", name="Payment", path="src/payment")
        payment_file = File(
            id="payment_py",
            path="src/payment/stripe.py",
            language="Python",
            lines_of_code=150,
            cyclomatic_complexity=10,
            test_coverage=0.75,
        )

        # Module 3: Inventory (low quality - the bottleneck)
        inventory_mod = Module(id="inventory", name="Inventory", path="src/inventory")
        inventory_file = File(
            id="inventory_py",
            path="src/inventory/warehouse.py",
            language="Python",
            lines_of_code=300,
            cyclomatic_complexity=28,
            test_coverage=0.4,
        )

        # Module 4: Analytics (high quality)
        analytics_mod = Module(id="analytics", name="Analytics", path="src/analytics")
        analytics_file = File(
            id="analytics_py",
            path="src/analytics/dashboard.py",
            language="Python",
            lines_of_code=120,
            cyclomatic_complexity=6,
            test_coverage=0.88,
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
        inventory_project = Project(id="ecommerce/inventory", name="Inventory")
        inventory_project.files = {"inventory_py": inventory_file}
        inventory_quality = compute_quality_score(inventory_project).score

        # PCQ should equal inventory quality (the worst module)
        assert pcq == inventory_quality
        assert pcq < 70, "PCQ should reflect the low-quality inventory module"

    def test_pcq_improvement_scenario(self):
        """Test PCQ improvement by fixing the worst module."""
        project = Project(id="test", name="Test")

        # Module A: Good
        modA = Module(id="modA", name="ModuleA", path="src/modA")
        fileA = File(
            id="fA",
            path="src/modA/good.py",
            language="Python",
            lines_of_code=100,
            cyclomatic_complexity=5,
            test_coverage=0.9,
        )

        # Module B: Bad (bottleneck)
        modB = Module(id="modB", name="ModuleB", path="src/modB")
        fileB = File(
            id="fB",
            path="src/modB/bad.py",
            language="Python",
            lines_of_code=200,
            cyclomatic_complexity=25,
            test_coverage=0.3,
        )

        project.modules = {"modA": modA, "modB": modB}
        project.files = {"fA": fileA, "fB": fileB}

        pcq_before = calculate_pcq(project)

        # Fix Module B (reduce complexity, increase coverage)
        fileB.cyclomatic_complexity = 8
        fileB.test_coverage = 0.85

        pcq_after = calculate_pcq(project)

        # PCQ should improve (Module B was the bottleneck)
        assert pcq_after > pcq_before, "Fixing the worst module should improve PCQ"
        assert pcq_after >= pcq_before + 10, "PCQ improvement should be significant"


class TestPCQProperties:
    """Test mathematical properties of PCQ aggregator."""

    def test_pcq_monotonicity(self):
        """Improving any module should NOT decrease PCQ (monotonicity).

        Property: ∀ m ∈ modules, Q'(m) ≥ Q(m) ⟹ PCQ'(S) ≥ PCQ(S)
        """
        project = Project(id="test", name="Test")

        modA = Module(id="modA", name="ModuleA", path="src/modA")
        fileA = File(
            id="fA",
            path="src/modA/a.py",
            language="Python",
            lines_of_code=100,
            cyclomatic_complexity=10,
            test_coverage=0.7,
        )

        modB = Module(id="modB", name="ModuleB", path="src/modB")
        fileB = File(
            id="fB",
            path="src/modB/b.py",
            language="Python",
            lines_of_code=150,
            cyclomatic_complexity=15,
            test_coverage=0.6,
        )

        project.modules = {"modA": modA, "modB": modB}
        project.files = {"fA": fileA, "fB": fileB}

        pcq_before = calculate_pcq(project)

        # Improve Module A (any improvement)
        fileA.cyclomatic_complexity = 5  # Reduce complexity
        fileA.test_coverage = 0.85  # Increase coverage

        pcq_after = calculate_pcq(project)

        # PCQ should NOT decrease (monotonicity)
        assert pcq_after >= pcq_before, "Monotonicity violated: improving module decreased PCQ"

    def test_pcq_idempotence(self):
        """PCQ(PCQ(S)) = PCQ(S) (idempotence property).

        Note: This tests that re-calculating PCQ gives same result.
        """
        project = Project(id="test", name="Test")

        mod1 = Module(id="mod1", name="Module1", path="src/mod1")
        file1 = File(
            id="f1",
            path="src/mod1/a.py",
            language="Python",
            lines_of_code=100,
            cyclomatic_complexity=8,
            test_coverage=0.75,
        )

        project.modules = {"mod1": mod1}
        project.files = {"f1": file1}

        pcq1 = calculate_pcq(project)
        pcq2 = calculate_pcq(project)

        # Should be identical (deterministic)
        assert pcq1 == pcq2, "PCQ calculation is not deterministic"

    def test_pcq_bounds(self):
        """PCQ ∈ [0, 100] for all projects."""
        project = Project(id="test", name="Test")

        # Extreme case: terrible quality
        mod_bad = Module(id="bad", name="Bad", path="src/bad")
        file_bad = File(
            id="fbad",
            path="src/bad/terrible.py",
            language="Python",
            lines_of_code=1000,
            cyclomatic_complexity=100,
            test_coverage=0.0,
        )

        # Extreme case: perfect quality
        mod_good = Module(id="good", name="Good", path="src/good")
        file_good = File(
            id="fgood",
            path="src/good/perfect.py",
            language="Python",
            lines_of_code=10,
            cyclomatic_complexity=1,
            test_coverage=1.0,
        )

        project.modules = {"bad": mod_bad, "good": mod_good}
        project.files = {"fbad": file_bad, "fgood": file_good}

        pcq = calculate_pcq(project)

        # PCQ must be in valid range
        assert 0 <= pcq <= 100, f"PCQ out of bounds: {pcq}"
