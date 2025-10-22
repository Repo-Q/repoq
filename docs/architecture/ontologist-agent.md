# OntologistAgent: Meta-Level Ontology Management

**Status:** ✅ Implemented  
**Location:** `repoq/ontologies/ontologist_agent.py`  
**Purpose:** Validate ontologies before analyzer registration (meta-level quality gate)

---

## Overview

**OntologistAgent** is a meta-level agent that ensures **ontological soundness** of analyzers:

- Every analyzer declares its ontology dependency (`ontology="test.ttl"`)
- OntologistAgent validates ontology **before** analyzer registration
- If validation fails, analyzer registration is blocked (fail-fast)
- Optional: AI-powered suggestions for fixing ontology issues

---

## Architecture

### Principle: "No Analyzer Without Ontology"

```python
@AnalyzerRegistry.register(AnalyzerMetadata(
    name="CoverageAnalyzer",
    ontology="test.ttl",  # ← OntologistAgent validates THIS
    rdf_namespace="http://example.org/vocab/test#",
    issue_types=["UncoveredFunction", "LowCoverage"],  # ← Must exist in test.ttl
))
class CoverageAnalyzer(BaseAnalyzer):
    ...
```

**At registration time:**
```python
# AnalyzerRegistry calls OntologistAgent
ontologist = OntologistAgent()
report = ontologist.validate_for_analyzer(metadata)

if not report.passed:
    raise AnalyzerRegistrationError(report.summary())
```

---

## Validation Gates

### Gate 1: Ontology Existence & Parseability
```python
def check_ontology_exists(metadata: AnalyzerMetadata) -> GateResult
```

**Checks:**
- File `repoq/ontologies/{metadata.ontology}` exists
- Parses successfully as Turtle/RDF (using `rdflib`)

**Failure:** `❌ Ontology file not found: test.ttl`

---

### Gate 2: Issue Types Coverage
```python
def check_issue_types_defined(metadata: AnalyzerMetadata, ontology: Graph) -> GateResult
```

**Checks:**
- All `metadata.issue_types` exist as OWL classes in ontology
- Example: `test:UncoveredFunction a owl:Class`

**Failure:** `❌ Missing OWL classes: ['UncoveredFunction', 'LowCoverage']`

**AI Suggestion (mode='ai_assist'):**
```turtle
# Suggested fixes:

test:UncoveredFunction a owl:Class ;
    rdfs:subClassOf quality:Issue ;
    rdfs:label "Uncovered Function" ;
    rdfs:comment "Issue type for CoverageAnalyzer" .
```

---

### Gate 3: No Cycles (DAG Hierarchy)
```python
def check_no_cycles(ontology: Graph) -> GateResult
```

**Checks:**
- Class hierarchy is acyclic (no `A rdfs:subClassOf B`, `B rdfs:subClassOf A`)
- Uses `networkx` to detect cycles

**Failure:** `❌ Circular inheritance detected: [test:A, test:B, test:A]`

---

### Gate 4: Namespace Isolation
```python
def check_namespace_isolation(metadata: AnalyzerMetadata, ontology: Graph) -> GateResult
```

**Checks:**
- All classes/properties use declared namespace (`metadata.rdf_namespace`)
- No leakage into other ontologies' namespaces

**Failure:** `❌ Class http://example.org/vocab/quality#Metric outside declared namespace test#`

---

### Gate 5: Property Consistency
```python
def check_property_consistency(ontology: Graph) -> GateResult
```

**Checks:**
- Property domains/ranges reference existing classes
- Example: `test:hasCoverage rdfs:domain repo:File` → `repo:File` must exist

**Warning:** `⚠️ Property test:hasCoverage has undefined domain: repo:File`

---

## Usage

### CLI (Manual Validation)

```bash
python repoq/ontologies/ontologist_agent.py test.ttl
```

**Output:**
```
✅ CoverageAnalyzer ontology validation PASSED (5 gates checked)
```

**On failure:**
```
❌ CoverageAnalyzer ontology validation FAILED
   Failed gates: issue_types_defined
   - issue_types_defined: Missing OWL classes: ['UncoveredFunction']

================================================================================
AI SUGGESTION:
================================================================================
# Suggested fixes:
...
```

---

### Programmatic (In AnalyzerRegistry)

```python
from repoq.ontologies.ontologist_agent import OntologistAgent, AnalyzerMetadata

ontologist = OntologistAgent()

metadata = AnalyzerMetadata(
    name="CoverageAnalyzer",
    ontology="test.ttl",
    rdf_namespace="http://example.org/vocab/test#",
    issue_types=["UncoveredFunction", "LowCoverage"],
    category="testing"
)

report = ontologist.validate_for_analyzer(metadata, mode="strict")

if not report.passed:
    raise AnalyzerRegistrationError(report.summary())
```

---

## Modes

### Mode: `strict` (Default)
- Fail-fast on first failed gate
- No AI suggestions
- For CI/CD validation

### Mode: `ai_assist`
- Run all gates (don't fail-fast)
- Generate AI suggestions for fixes
- For development workflow

**Example:**
```python
report = ontologist.validate_for_analyzer(metadata, mode="ai_assist")

if not report.passed:
    print(report.summary())
    if report.ai_suggestion:
        print(report.ai_suggestion)  # AI-generated fix
```

---

## Integration with AnalyzerRegistry

### Before OntologistAgent
```python
@AnalyzerRegistry.register(...)
class CoverageAnalyzer(BaseAnalyzer):
    ...
```

**Problem:** No validation that `test.ttl` exists or has required classes.

---

### After OntologistAgent
```python
class AnalyzerRegistry:
    @classmethod
    def register(cls, metadata: AnalyzerMetadata):
        def decorator(analyzer_cls):
            # [Γ] GATE: Validate ontology
            ontologist = OntologistAgent()
            report = ontologist.validate_for_analyzer(metadata)
            
            if not report.passed:
                raise AnalyzerRegistrationError(
                    f"Ontology validation failed for {metadata.name}:\n{report.summary()}"
                )
            
            cls._registry[metadata.name] = (analyzer_cls, metadata)
            return analyzer_cls
        return decorator
```

**Benefit:** Analyzers cannot be registered without valid ontology (fail-fast at startup).

---

## Reflexivity: OntologistAgent is Self-Described

**meta.ttl:**
```turtle
meta:OntologistAgent a owl:Class ;
    rdfs:subClassOf meta:MetaAgent ;
    rdfs:label "Ontologist Agent" ;
    rdfs:comment """
        Meta-level agent validating ontologies for analyzers.
        Ensures soundness, completeness, consistency of ontology-analyzer mappings.
    """ .

meta:validatesOntology a owl:ObjectProperty ;
    rdfs:domain meta:OntologistAgent ;
    rdfs:range meta:Ontology .

meta:hasValidationGate a owl:ObjectProperty ;
    rdfs:domain meta:OntologistAgent ;
    rdfs:range meta:ValidationGate .
```

---

## Dependencies

- **rdflib** (parse Turtle/RDF)
- **networkx** (cycle detection in class hierarchy)
- **Optional:** BAML client (for AI suggestions)

---

## Next Steps

1. ✅ Create remaining ontologies: `security.ttl`, `arch.ttl`, `license.ttl`, `api.ttl`
2. Integrate OntologistAgent into `AnalyzerRegistry.register()`
3. Add OntologistAgent validation to CI/CD (pre-commit hook)
4. Implement BAML function `GenerateOntologyFragment` for AI suggestions

---

## Related

- [Ontological Grounding (Roadmap)](../development/meta-loop-closure-roadmap.md#ontological-grounding)
- [Meta-Level Ontology](./meta-ontology.md)
- [Analyzer Pipeline](./analyzer-pipeline.md)
