# repoq Core Ontology (OML Specification)

## Vocabulary: repoq Core

**IRI**: `http://example.org/repoq/core#`  
**Prefix**: `repoq`

**Description**: Формальная спецификация базовых концептов платформы анализа качества репозиториев.

---

## Imports

```oml
vocabulary <http://example.org/repoq/core#> as repoq {
  
  extends <http://www.w3.org/ns/prov#> as prov
  extends <http://spdx.org/rdf/terms#> as spdx
  extends <http://xmlns.com/foaf/0.1/> as foaf
  extends <http://open-services.net/ns/core#> as oslc
  extends <http://www.w3.org/2000/01/rdf-schema#> as rdfs
  extends <http://www.w3.org/2001/XMLSchema#> as xsd
}
```

---

## Concepts (Classes)

### Project

```oml
concept Project :> prov:Entity, oslc:Resource [
  restricts all relation containsModule to Module
  restricts all relation containsFile to File
  restricts all relation hasContributor to Person
  restricts all relation hasIssue to Issue
]
```

**Invariants**:

- Каждый проект имеет уникальный IRI
- `name` обязателен (min cardinality 1)
- `programmingLanguages` может быть пустым, но если задан, то LOC > 0

### Module

```oml
concept Module :> oslc:Resource [
  restricts all relation containsFile to File
  restricts all relation containsModule to Module
  restricts some relation owner to Person
]
```

**Axiom**: Иерархия модулей ациклична

```lean
-- Формальное доказательство в Lean4:
theorem module_hierarchy_acyclic (m : Module) :
  ¬(m ∈ transitive_closure m.containsModule m) := by
  -- доказательство через well-founded recursion
  sorry
```

### File

```oml
concept File :> spdx:File, prov:Entity [
  restricts some scalar property path to xsd:string
  restricts some scalar property linesOfCode to xsd:nonNegativeInteger
  restricts some scalar property complexity to xsd:decimal [
    restricts min inclusive to 0.0
  ]
  restricts some scalar property maintainability to xsd:decimal
  restricts some scalar property hotness to xsd:decimal [
    restricts min inclusive to 0.0
    restricts max inclusive to 1.0
  ]
  restricts all relation contributedBy to Person
]
```

**Invariants**:

- `linesOfCode >= 0` (enforced by type)
- `complexity >= 0.0` (if present)
- `hotness ∈ [0, 1]` (normalized score)
- `path` is unique within project

### Person

```oml
concept Person :> foaf:Person, prov:Agent, prov:Person [
  restricts some scalar property name to xsd:string
  restricts some scalar property email to xsd:string
  restricts some scalar property commits to xsd:nonNegativeInteger
  restricts some scalar property linesAdded to xsd:nonNegativeInteger
  restricts some scalar property linesDeleted to xsd:nonNegativeInteger
]
```

**Invariants**:

- `name` обязателен
- `commits >= 0`
- `linesAdded >= 0`, `linesDeleted >= 0`
- `email` может быть пустым, но если задан, то должен быть валидным email
- `mbox_sha1sum` вычисляется детерминированно из `email`

### Issue

```oml
concept Issue :> oslc:ChangeRequest [
  restricts some scalar property description to xsd:string
  restricts some scalar property severity to IssueSeverity
  restricts some scalar property priority to IssuePriority
  restricts some scalar property status to IssueStatus
  restricts some relation affectsFile to File
]
```

**Enumerations**:

```oml
scalar IssueSeverity :> xsd:string [
  oneOf "low" "medium" "high"
]

scalar IssuePriority :> xsd:string [
  oneOf "low" "medium" "high"
]

scalar IssueStatus :> xsd:string [
  oneOf "Open" "InProgress" "Closed"
]
```

### Commit

```oml
concept Commit :> prov:Activity [
  restricts some scalar property message to xsd:string
  restricts some relation wasAssociatedWith to Person
  restricts some scalar property endedAtTime to xsd:dateTime
]
```

### DependencyEdge

```oml
concept DependencyEdge :> oslc:Resource [
  restricts some relation source to (Module | File)
  restricts some relation target to (Module | File)
  restricts some scalar property weight to xsd:positiveInteger
  restricts some scalar property type to DependencyType
]

scalar DependencyType :> xsd:string [
  oneOf "import" "runtime" "build" "test"
]
```

**Axiom**: Dependency graph может иметь циклы (разрешены для циклических импортов)

### CouplingEdge

```oml
concept CouplingEdge :> oslc:Resource [
  restricts some relation fileA to File
  restricts some relation fileB to File
  restricts some scalar property weight to xsd:positiveInteger
]
```

**Axiom**: Coupling is symmetric

```lean
theorem coupling_symmetric (c : CouplingEdge) :
  ∃ c', c'.fileA = c.fileB ∧ c'.fileB = c.fileA ∧ c'.weight = c.weight := by
  sorry
```

---

## Relations (Object Properties)

```oml
relation containsModule [
  from Project | Module
  to Module
  inverse isModuleOf
]

relation containsFile [
  from Project | Module
  to File
  inverse isFileOf
]

relation hasContributor [
  from Project
  to Person
  inverse contributesTo
]

relation contributedBy [
  from File
  to Person
  inverse contributed
]

relation owner [
  from Module
  to Person
  functional  // one owner per module
]

relation affectsFile [
  from Issue
  to File
  inverse hasIssue
]
```

---

## Scalar Properties (Data Properties)

```oml
scalar property name [
  domain Project | Module | Person
  range xsd:string
  functional
]

scalar property path [
  domain File
  range xsd:string
  functional
]

scalar property linesOfCode [
  domain File
  range xsd:nonNegativeInteger
  functional
]

scalar property complexity [
  domain File
  range xsd:decimal
  functional
]

scalar property maintainability [
  domain File
  range xsd:decimal
  functional
]

scalar property hotness [
  domain File
  range xsd:decimal
  functional
]

scalar property commits [
  domain Person
  range xsd:nonNegativeInteger
  functional
]

scalar property description [
  domain Project | Issue
  range xsd:string
]

scalar property severity [
  domain Issue
  range IssueSeverity
  functional
]
```

---

## Axioms & Rules

### Rule 1: Hotness Range Constraint

```oml
rule HotnessInRange [
  hotness(?f, ?h) -> greaterThanOrEqual(?h, 0.0) ^ lessThanOrEqual(?h, 1.0)
]
```

### Rule 2: Module Owner Must Be Contributor

```oml
rule OwnerIsContributor [
  owner(?m, ?p) ^ isModuleOf(?m, ?proj) -> hasContributor(?proj, ?p)
]
```

### Rule 3: File Contributors Must Be Project Contributors

```oml
rule FileContributorInProject [
  contributedBy(?f, ?p) ^ isFileOf(?f, ?proj) -> hasContributor(?proj, ?p)
]
```

### Rule 4: Complexity Non-Negative

```oml
rule ComplexityNonNegative [
  complexity(?f, ?c) -> greaterThanOrEqual(?c, 0.0)
]
```

### Rule 5: Issue Affects File in Same Project

```oml
rule IssueInSameProject [
  affectsFile(?i, ?f) ^ isFileOf(?f, ?proj) -> hasIssue(?proj, ?i)
]
```

---

## Soundness Guarantees (для Lean4)

**Theorem 1: Valid Python File → Valid RDF Graph**

```lean
theorem mapping_preserves_validity (f : PythonFile) (h : f.valid) :
  (pythonFileToRDF f).satisfies repoq_core_shapes := by
  unfold pythonFileToRDF
  unfold PythonFile.valid at h
  
  -- Случай 1: hotness в [0, 1]
  cases f.hotness with
  | none => simp
  | some hval =>
    have h_range : 0 ≤ hval ∧ hval ≤ 1 := h.hotness_range
    -- доказываем, что RDF triple удовлетворяет SHACL constraint
    apply satisfies_hotness_range
    exact h_range
  
  -- Случай 2: LOC >= 0 (тривиально из типа Nat)
  apply satisfies_loc_nonneg
  
  -- Случай 3: complexity >= 0 (если задано)
  cases f.complexity with
  | none => simp
  | some cval =>
    have h_cplx : 0 ≤ cval := h.complexity_nonneg
    apply satisfies_complexity_nonneg
    exact h_cplx
```

**Theorem 2: Confluence of Analyzers**

```lean
-- Если анализаторы ортогональны, то порядок не важен
theorem analyzers_confluent (a1 a2 : Analyzer) (p : Project) 
  (h : orthogonal a1 a2) :
  (a1.run >> a2.run) p = (a2.run >> a1.run) p := by
  unfold orthogonal at h
  -- доказываем через коммутативность независимых операций
  sorry
```

**Theorem 3: Termination**

```lean
-- Pipeline всегда терминирует при ограниченных ресурсах
theorem pipeline_terminates (cfg : AnalyzeConfig) (repo : Repository) 
  (h : cfg.max_files.isSome ∨ repo.files.length < ∞) :
  ∃ (n : Nat), (pipeline cfg repo).steps ≤ n := by
  cases h with
  | inl max_set =>
    -- ограничено max_files
    use cfg.max_files.get * number_of_analyzers
    sorry
  | inr finite_repo =>
    -- ограничено размером репо
    use repo.files.length * number_of_analyzers
    sorry
```

---

## Связь с SHACL Shapes

Каждая OML аксиома должна иметь соответствующий SHACL constraint:

| OML Rule | SHACL Shape |
|----------|-------------|
| `HotnessInRange` | `sh:minInclusive 0.0; sh:maxInclusive 1.0` |
| `ComplexityNonNegative` | `sh:minInclusive 0.0` |
| `OwnerIsContributor` | `sh:node :ContributorShape` |
| `FileContributorInProject` | Custom SPARQL constraint |

**Proof obligation**: Доказать, что SHACL shapes полностью покрывают OML axioms.

---

## Метаданные

- **Version**: 1.0 (Phase 2)
- **Status**: Draft
- **Authors**: repoq team
- **License**: MIT
- **Related**:
  - `shapes/repoq_core.ttl` (SHACL implementation)
  - `proofs/RepoqCore.lean` (Formal verification)
  - `repoq/core/model.py` (Python implementation)

---

## Extension Vocabularies (Phase 0.5)

### Vocabulary: test (Testing & Coverage)

**IRI**: `http://example.org/vocab/test#`  
**Prefix**: `test`  
**Ontology File**: `repoq/ontologies/test.ttl`

**Description**: Формализация тестирования, покрытия кода, property-based testing, контрактов.

#### Concepts

```oml
vocabulary <http://example.org/vocab/test#> as test {
  extends <http://example.org/repoq/core#> as repoq
  extends <http://www.w3.org/ns/prov#> as prov
  
  concept TestCase :> prov:Activity [
    restricts some scalar property testName to xsd:string
    restricts some scalar property testStatus to TestStatus
    restricts some relation testedConcept to repoq:Concept
  ]
  
  concept UnitTest :> TestCase
  concept IntegrationTest :> TestCase
  concept PropertyTest :> TestCase [
    restricts some scalar property propertyDescription to xsd:string
    restricts some scalar property shrinkingStrategy to xsd:string
  ]
  concept ContractTest :> TestCase [
    restricts some scalar property precondition to xsd:string
    restricts some scalar property postcondition to xsd:string
    restricts some scalar property invariant to xsd:string
  ]
  
  concept Coverage :> repoq:Metric [
    restricts some scalar property coveragePercentage to xsd:decimal [
      restricts min inclusive to 0.0
      restricts max inclusive to 100.0
    ]
  ]
  
  concept ConceptCoverage :> Coverage [
    restricts some relation coveredConcept to repoq:Concept
  ]
  
  // Issue types (for CoverageAnalyzer, TestEffectivenessAnalyzer)
  concept UncoveredFunction :> repoq:Issue
  concept LowCoverage :> repoq:Issue
  concept FlakyTest :> repoq:Issue
  concept WeakTest :> repoq:Issue
  concept SlowTest :> repoq:Issue
  
  scalar TestStatus :> xsd:string [
    oneOf "passed" "failed" "skipped" "flaky"
  ]
}
```

#### Axioms

```oml
// Coverage must be in [0, 100]
rule CoverageRange [
  coveragePercentage(?c, ?pct) -> 
    greaterThanOrEqual(?pct, 0.0) ^ lessThanOrEqual(?pct, 100.0)
]

// Property test must have description
rule PropertyTestHasDescription [
  PropertyTest(?t) -> propertyDescription(?t, ?desc)
]

// Contract test must have at least one condition
rule ContractTestHasCondition [
  ContractTest(?t) -> 
    precondition(?t, ?pre) | postcondition(?t, ?post) | invariant(?t, ?inv)
]
```

#### Lean4 Invariants

```lean
-- Coverage percentage valid
theorem coverage_in_range (c : Coverage) :
  0 ≤ c.percentage ∧ c.percentage ≤ 100 := by
  cases c.percentage_valid
  constructor <;> assumption

-- Test execution is deterministic (modulo flakiness)
theorem test_deterministic (t : TestCase) (h : ¬t.isFlaky) :
  ∀ (run1 run2 : TestRun), run1.test = t → run2.test = t → 
    run1.status = run2.status := by
  intro run1 run2 h1 h2
  unfold TestCase.isFlaky at h
  -- доказываем через отсутствие недетерминированных операций
  sorry
```

---

### Vocabulary: security (Vulnerabilities & Secrets)

**IRI**: `http://example.org/vocab/security#`  
**Prefix**: `security`  
**Ontology File**: `repoq/ontologies/security.ttl`

**Description**: Формализация уязвимостей, CVE, утечек секретов, зависимостей.

#### Concepts

```oml
vocabulary <http://example.org/vocab/security#> as security {
  extends <http://example.org/repoq/core#> as repoq
  extends <http://spdx.org/rdf/terms#> as spdx
  
  concept Vulnerability :> repoq:Issue [
    restricts some scalar property hasSeverity to Severity
    restricts some scalar property hasCVSSScore to xsd:decimal [
      restricts min inclusive to 0.0
      restricts max inclusive to 10.0
    ]
    restricts some scalar property exploitabilityScore to xsd:decimal
  ]
  
  concept CVE :> Vulnerability [
    restricts some scalar property hasCVEID to xsd:string  // pattern: CVE-YYYY-NNNNN
  ]
  
  concept SecretLeak :> Vulnerability [
    restricts some scalar property entropyScore to xsd:decimal [
      restricts min inclusive to 0.0
    ]
  ]
  
  // Secret types
  concept Secret
  concept APIKey :> Secret
  concept Password :> Secret
  concept PrivateKey :> Secret
  concept Token :> Secret
  concept DatabaseCredential :> Secret
  
  concept DependencyVulnerability :> Vulnerability [
    restricts some scalar property affectsPackage to xsd:string
    restricts some scalar property fixedInVersion to xsd:string
  ]
  
  concept Remediation [
    restricts some scalar property remediationDescription to xsd:string
  ]
  concept Upgrade :> Remediation
  concept Patch :> Remediation
  concept Workaround :> Remediation
  concept ConfigurationChange :> Remediation
  
  // Issue types (for SecretLeakAnalyzer, DependencyHealthAnalyzer)
  concept ExposedAPIKey :> SecretLeak
  concept ExposedPassword :> SecretLeak
  concept ExposedPrivateKey :> SecretLeak
  concept HighEntropyString :> SecretLeak
  concept VulnerableDependency :> DependencyVulnerability
  concept OutdatedDependency :> DependencyVulnerability
  concept UnmaintainedDependency :> DependencyVulnerability
  
  scalar Severity :> xsd:string [
    oneOf "Critical" "High" "Medium" "Low"
  ]
}
```

#### Axioms

```oml
// CVSS score must be in [0, 10]
rule CVSSRange [
  hasCVSSScore(?v, ?score) -> 
    greaterThanOrEqual(?score, 0.0) ^ lessThanOrEqual(?score, 10.0)
]

// Severity aligned with CVSS
rule SeverityAlignedWithCVSS [
  hasCVSSScore(?v, ?score) ^ greaterThanOrEqual(?score, 9.0) -> 
    hasSeverity(?v, "Critical")
]

rule SeverityHighRange [
  hasCVSSScore(?v, ?score) ^ greaterThanOrEqual(?score, 7.0) ^ 
    lessThan(?score, 9.0) -> hasSeverity(?v, "High")
]

// CVE ID format validation
rule CVEIDFormat [
  CVE(?cve) ^ hasCVEID(?cve, ?id) -> 
    matches(?id, "^CVE-[0-9]{4}-[0-9]{4,}$")
]

// DependencyVulnerability must specify package
rule DependencyVulnHasPackage [
  DependencyVulnerability(?v) -> affectsPackage(?v, ?pkg)
]
```

#### Lean4 Invariants

```lean
-- CVSS score validity
theorem cvss_valid (v : Vulnerability) (h : v.hasCVSSScore) :
  0 ≤ v.cvssScore ∧ v.cvssScore ≤ 10 := by
  cases v.cvss_constraint
  constructor <;> assumption

-- Severity monotonic with CVSS
theorem severity_monotonic (v1 v2 : Vulnerability) 
  (h1 : v1.hasCVSSScore) (h2 : v2.hasCVSSScore)
  (hcmp : v1.cvssScore < v2.cvssScore) :
  severity_rank v1.severity ≤ severity_rank v2.severity := by
  unfold severity_rank
  -- доказываем через CVSS ranges
  cases v1.severity <;> cases v2.severity <;> linarith

-- CVE ID uniqueness (global invariant)
theorem cve_id_unique (cve1 cve2 : CVE) 
  (h : cve1.cveID = cve2.cveID) :
  cve1 = cve2 := by
  -- доказываем через глобальный CVE registry
  sorry
```

---

### Vocabulary: arch (Architecture & Design)

**IRI**: `http://example.org/vocab/arch#`  
**Prefix**: `arch`  
**Ontology File**: `repoq/ontologies/arch.ttl`

**Description**: Формализация архитектурных слоёв, паттернов, нарушений границ.

#### Concepts

```oml
vocabulary <http://example.org/vocab/arch#> as arch {
  extends <http://example.org/repoq/core#> as repoq
  
  concept ArchitectureModel [
    restricts some relation hasLayer to Layer
    restricts some relation hasPattern to ArchitecturePattern
  ]
  
  concept Layer [
    restricts some scalar property layerName to xsd:string
    restricts some relation dependsOn to Layer  // allowed dependencies
    restricts some relation contains to repoq:Module
  ]
  
  concept PresentationLayer :> Layer
  concept ApplicationLayer :> Layer
  concept DomainLayer :> Layer
  concept InfrastructureLayer :> Layer
  
  concept Component :> repoq:Module [
    restricts some relation belongsToLayer to Layer
    restricts some scalar property couplingScore to xsd:decimal [
      restricts min inclusive to 0.0
    ]
    restricts some scalar property cohesionScore to xsd:decimal [
      restricts min inclusive to 0.0
      restricts max inclusive to 1.0
    ]
    restricts some scalar property instability to xsd:decimal [
      restricts min inclusive to 0.0
      restricts max inclusive to 1.0
    ]
    restricts some scalar property abstractness to xsd:decimal [
      restricts min inclusive to 0.0
      restricts max inclusive to 1.0
    ]
  ]
  
  concept Boundary [
    restricts some relation separates to Layer
    restricts some relation allowedDependency to Layer
    restricts some relation forbiddenDependency to Layer
  ]
  
  concept ArchitecturePattern
  concept HexagonalArchitecture :> ArchitecturePattern
  concept CleanArchitecture :> ArchitecturePattern
  concept LayeredArchitecture :> ArchitecturePattern
  
  concept ArchitectureRule [
    restricts some scalar property ruleDescription to xsd:string
  ]
  concept LayerDependencyRule :> ArchitectureRule
  concept ForbiddenImportRule :> ArchitectureRule
  concept CyclicDependencyRule :> ArchitectureRule
  concept InterfaceSegregationRule :> ArchitectureRule
  
  // Issue types (for ArchitectureDriftAnalyzer)
  concept LayerViolation :> repoq:Issue [
    restricts some relation violatesRule to LayerDependencyRule
  ]
  concept ForbiddenImport :> repoq:Issue [
    restricts some relation violatesRule to ForbiddenImportRule
  ]
  concept CyclicDependency :> repoq:Issue
  concept BoundaryViolation :> repoq:Issue
  concept GodClass :> repoq:Issue
  concept StrayModule :> repoq:Issue
}
```

#### Axioms

```oml
// Layer hierarchy must be acyclic
rule LayerHierarchyAcyclic [
  dependsOn(?l1, ?l2) -> ¬transitiveClosure(dependsOn)(?l2, ?l1)
]

// Clean Architecture: Domain layer has no dependencies
rule DomainLayerIndependent [
  DomainLayer(?dl) -> ¬dependsOn(?dl, ?other)
]

// Coupling/Cohesion trade-off
rule CouplingCohesionTradeoff [
  couplingScore(?c, ?coup) ^ cohesionScore(?c, ?coh) ->
    lessThanOrEqual(?coup + ?coh, 2.0)  // heuristic bound
]

// Instability formula: I = Ce / (Ca + Ce)
rule InstabilityDefinition [
  instability(?c, ?i) ^ efferentCoupling(?c, ?ce) ^ afferentCoupling(?c, ?ca) ->
    equal(?i, divide(?ce, plus(?ca, ?ce)))
]

// Distance from main sequence: D = |A + I - 1|
rule DistanceFromMainSequence [
  abstractness(?c, ?a) ^ instability(?c, ?i) ^ 
    distanceFromMainSequence(?c, ?d) ->
    equal(?d, abs(plus(?a, ?i) - 1))
]
```

#### Lean4 Invariants

```lean
-- Layer hierarchy acyclicity (CRITICAL)
theorem layer_hierarchy_acyclic (l : Layer) :
  ¬(l ∈ transitive_closure l.dependsOn l) := by
  -- доказываем через well-founded recursion на DAG
  apply Relation.TransGen.trans_induction_on
  intro x y hz
  -- base case: l ≠ l.dependsOn
  { intro heq
    cases l.no_self_dependency heq }
  -- inductive case: если x→y и y→*l, то x→*l
  { intro _ ih heq
    exact l.no_cycles (hz ▸ ih) }

-- Cohesion bounded
theorem cohesion_normalized (c : Component) :
  0 ≤ c.cohesionScore ∧ c.cohesionScore ≤ 1 := by
  cases c.cohesion_valid
  constructor <;> assumption

-- Instability bounded
theorem instability_normalized (c : Component) :
  0 ≤ c.instability ∧ c.instability ≤ 1 := by
  unfold Component.instability
  -- доказываем через Ce / (Ca + Ce) ∈ [0, 1]
  have h1 : 0 ≤ c.efferentCoupling := Nat.zero_le _
  have h2 : c.efferentCoupling ≤ c.efferentCoupling + c.afferentCoupling := 
    Nat.le_add_right _ _
  constructor
  · exact div_nonneg h1 (Nat.add_pos_left _ _)
  · exact div_le_one_of_le h2 (Nat.add_pos_left _ _)

-- Main sequence theorem: components close to D=0 are balanced
theorem main_sequence_balance (c : Component) 
  (h : c.distanceFromMainSequence < 0.1) :
  balanced c.abstractness c.instability := by
  unfold distanceFromMainSequence at h
  unfold balanced
  -- доказываем, что |A + I - 1| < 0.1 ⟹ A + I ≈ 1
  linarith
```

---

### Vocabulary: license (License Compliance)

**IRI**: `http://example.org/vocab/license#`  
**Prefix**: `license`  
**Ontology File**: `repoq/ontologies/license.ttl`

**Description**: Формализация лицензий, совместимости, политик SPDX.

#### Concepts

```oml
vocabulary <http://example.org/vocab/license#> as license {
  extends <http://example.org/repoq/core#> as repoq
  extends <http://spdx.org/rdf/terms#> as spdx
  
  concept License :> spdx:License [
    restricts some scalar property hasSPDXIdentifier to xsd:string
    restricts some scalar property hasOSIApproval to xsd:boolean
    restricts some scalar property isCopyleft to xsd:boolean
    restricts some scalar property requiresAttribution to xsd:boolean
    restricts some scalar property allowsCommercialUse to xsd:boolean
    restricts some scalar property allowsModification to xsd:boolean
    restricts some scalar property allowsDistribution to xsd:boolean
    restricts some scalar property requiresSourceDisclosure to xsd:boolean
  ]
  
  concept PermissiveLicense :> License [
    restricts scalar property isCopyleft to false
  ]
  concept CopyleftLicense :> License [
    restricts scalar property isCopyleft to true
    restricts scalar property requiresSourceDisclosure to true
  ]
  concept ProprietaryLicense :> License [
    restricts scalar property allowsModification to false
  ]
  concept PublicDomain :> License
  
  concept Policy [
    restricts some relation appliesToLicense to License
  ]
  concept AllowedLicense :> Policy
  concept RestrictedLicense :> Policy
  concept ForbiddenLicense :> Policy
  
  concept Compatibility [
    restricts some relation sourceLicense to License
    restricts some relation targetLicense to License
  ]
  concept Compatible :> Compatibility
  concept Incompatible :> Compatibility
  concept ConditionallyCompatible :> Compatibility [
    restricts some scalar property condition to xsd:string
  ]
  
  // Issue types (for LicenseComplianceAnalyzer)
  concept IncompatibleLicense :> repoq:Issue [
    restricts some relation conflictingLicense to License
  ]
  concept UnknownLicense :> repoq:Issue
  concept ForbiddenLicenseViolation :> repoq:Issue [
    restricts some relation violatedPolicy to ForbiddenLicense
  ]
  concept RestrictedLicenseWarning :> repoq:Issue [
    restricts some relation triggeredPolicy to RestrictedLicense
  ]
  concept MissingLicenseNotice :> repoq:Issue
  concept LicenseMismatch :> repoq:Issue
}
```

#### Axioms

```oml
// Copyleft requires source disclosure
rule CopyleftRequiresSource [
  CopyleftLicense(?l) -> requiresSourceDisclosure(?l, true)
]

// Permissive licenses allow commercial use
rule PermissiveAllowsCommercial [
  PermissiveLicense(?l) -> allowsCommercialUse(?l, true)
]

// Compatibility is directional (not symmetric!)
rule CompatibilityDirectional [
  Compatible(?c) ^ sourceLicense(?c, ?s) ^ targetLicense(?c, ?t) ->
    ¬necessarily(Compatible(?c2) ^ sourceLicense(?c2, ?t) ^ targetLicense(?c2, ?s))
]

// GPL-3.0 incompatible with permissive (one-way)
rule GPLIncompatibleWithPermissive [
  CopyleftLicense(?gpl) ^ hasSPDXIdentifier(?gpl, "GPL-3.0") ^
  PermissiveLicense(?perm) ->
    Incompatible(?inc) ^ sourceLicense(?inc, ?gpl) ^ targetLicense(?inc, ?perm)
]

// MIT → GPL-3.0 compatible (permissive can be relicensed as copyleft)
rule MITtoGPLCompatible [
  PermissiveLicense(?mit) ^ hasSPDXIdentifier(?mit, "MIT") ^
  CopyleftLicense(?gpl) ^ hasSPDXIdentifier(?gpl, "GPL-3.0") ->
    Compatible(?c) ^ sourceLicense(?c, ?mit) ^ targetLicense(?c, ?gpl)
]

// Transitivity (conditional)
rule CompatibilityTransitive [
  Compatible(?c1) ^ sourceLicense(?c1, ?a) ^ targetLicense(?c1, ?b) ^
  Compatible(?c2) ^ sourceLicense(?c2, ?b) ^ targetLicense(?c2, ?c) ^
  ¬CopyleftLicense(?b) ->  // transitivity breaks at copyleft boundary
    Compatible(?c3) ^ sourceLicense(?c3, ?a) ^ targetLicense(?c3, ?c)
]
```

#### Lean4 Invariants

```lean
-- Copyleft implies source disclosure
theorem copyleft_requires_source (l : License) (h : l.isCopyleft = true) :
  l.requiresSourceDisclosure = true := by
  cases l with
  | PermissiveLicense => contradiction  -- isCopyleft = false
  | CopyleftLicense => simp [CopyleftLicense.requiresSourceDisclosure]
  | ProprietaryLicense => cases h  -- proprietary can't be copyleft
  | PublicDomain => cases h

-- Compatibility is NOT symmetric
theorem compatibility_not_symmetric :
  ∃ (c1 c2 : Compatibility) (l1 l2 : License),
    c1.source = l1 ∧ c1.target = l2 ∧ c1.isCompatible ∧
    c2.source = l2 ∧ c2.target = l1 ∧ ¬c2.isCompatible := by
  -- пример: MIT → GPL compatible, но GPL → MIT incompatible
  use (compat MIT GPL_3_0 true)
  use (compat GPL_3_0 MIT false)
  use MIT, GPL_3_0
  simp [MIT.spdx_id, GPL_3_0.spdx_id]
  constructor <;> rfl

-- Transitivity breaks at copyleft boundary
theorem compatibility_not_fully_transitive :
  ∃ (c1 c2 : Compatibility) (l1 l2 l3 : License),
    c1.source = l1 ∧ c1.target = l2 ∧ c1.isCompatible ∧
    c2.source = l2 ∧ c2.target = l3 ∧ c2.isCompatible ∧
    ¬compatible l1 l3 := by
  -- контрпример: MIT → Apache-2.0 → GPL-3.0 (но MIT ⊥ GPL прямо)
  use (compat MIT Apache_2_0 true)
  use (compat Apache_2_0 GPL_3_0 true)
  use MIT, Apache_2_0, GPL_3_0
  -- доказываем, что MIT напрямую несовместима с GPL (требуется доп. условие)
  sorry

-- SPDX identifier uniqueness
theorem spdx_id_unique (l1 l2 : License) 
  (h : l1.spdxIdentifier = l2.spdxIdentifier) :
  l1 = l2 := by
  -- доказываем через SPDX registry (каждый ID → уникальная лицензия)
  sorry
```

---

### Vocabulary: api (API Contracts & Breaking Changes)

**IRI**: `http://example.org/vocab/api#`  
**Prefix**: `api`  
**Ontology File**: `repoq/ontologies/api.ttl`

**Description**: Формализация API-контрактов, версионирования (semver), breaking changes.

#### Concepts

```oml
vocabulary <http://example.org/vocab/api#> as api {
  extends <http://example.org/repoq/core#> as repoq
  
  concept API [
    restricts some scalar property hasVersion to xsd:string  // semver format
    restricts some scalar property isPublic to xsd:boolean
    restricts some scalar property isDeprecated to xsd:boolean
  ]
  
  concept PublicAPI :> API [
    restricts scalar property isPublic to true
  ]
  concept InternalAPI :> API [
    restricts scalar property isPublic to false
  ]
  concept ExperimentalAPI :> API
  
  concept Contract [
    restricts some relation definesFunction to Function
    restricts some scalar property precondition to xsd:string
    restricts some scalar property postcondition to xsd:string
    restricts some scalar property invariant to xsd:string
  ]
  
  concept Function [
    restricts some relation hasParameter to Parameter
    restricts some relation hasReturnValue to ReturnValue
    restricts some relation raisesException to Exception
  ]
  
  concept Parameter [
    restricts some scalar property parameterName to xsd:string
    restricts some scalar property parameterType to xsd:string
    restricts some scalar property isRequired to xsd:boolean
  ]
  
  concept ReturnValue [
    restricts some scalar property returnType to xsd:string
  ]
  
  concept Exception [
    restricts some scalar property exceptionType to xsd:string
  ]
  
  concept Version [
    restricts some scalar property majorVersion to xsd:nonNegativeInteger
    restricts some scalar property minorVersion to xsd:nonNegativeInteger
    restricts some scalar property patchVersion to xsd:nonNegativeInteger
  ]
  
  concept Change [
    restricts some relation changedFrom to Version
    restricts some relation changedTo to Version
    restricts some scalar property changeDescription to xsd:string
  ]
  
  concept BreakingChange :> Change [
    restricts some relation affectsFunction to Function
    restricts some scalar property mitigationStrategy to xsd:string
  ]
  
  concept NonBreakingChange :> Change
  
  concept Deprecation :> Change [
    restricts some scalar property deprecationMessage to xsd:string
    restricts some scalar property deprecatedSince to xsd:string  // version
    restricts some scalar property removedIn to xsd:string  // future version
  ]
  
  // Breaking change subtypes
  concept FunctionRemoved :> BreakingChange
  concept FunctionRenamed :> BreakingChange
  concept SignatureChanged :> BreakingChange [
    restricts some scalar property oldSignature to xsd:string
    restricts some scalar property newSignature to xsd:string
  ]
  concept ReturnTypeChanged :> BreakingChange
  concept ParameterRemoved :> BreakingChange
  concept ParameterTypeChanged :> BreakingChange
  concept ClassRemoved :> BreakingChange
  concept MethodRemoved :> BreakingChange
  concept AttributeRemoved :> BreakingChange
  concept ExceptionAdded :> BreakingChange
  
  // Issue types (for APIBreakingChangeAnalyzer)
  concept BreakingChangeDetected :> repoq:Issue [
    restricts some relation detectedChange to BreakingChange
  ]
  concept DeprecatedAPI :> repoq:Issue [
    restricts some relation deprecatedElement to Function
  ]
  concept MissingAPIDocumentation :> repoq:Issue
  concept VersionMismatch :> repoq:Issue [
    restricts some scalar property expectedVersion to xsd:string
    restricts some scalar property actualVersion to xsd:string
  ]
  concept UndocumentedBreakingChange :> repoq:Issue [
    restricts some relation undocumentedChange to BreakingChange
  ]
}
```

#### Axioms

```oml
// Semantic versioning: breaking change requires major bump
rule BreakingChangeRequiresMajorBump [
  BreakingChange(?bc) ^ changedFrom(?bc, ?v1) ^ changedTo(?bc, ?v2) ^
  majorVersion(?v1, ?maj1) ^ majorVersion(?v2, ?maj2) ->
    greaterThan(?maj2, ?maj1)
]

// Non-breaking change allows minor/patch bump
rule NonBreakingChangeAllowsMinorBump [
  NonBreakingChange(?nbc) ^ changedFrom(?nbc, ?v1) ^ changedTo(?nbc, ?v2) ^
  majorVersion(?v1, ?maj1) ^ majorVersion(?v2, ?maj2) ->
    greaterThanOrEqual(?maj2, ?maj1)
]

// Deprecation must specify removal version
rule DeprecationHasRemovalVersion [
  Deprecation(?d) -> removedIn(?d, ?futureVer)
]

// Public API breaking changes are forbidden without major bump
rule PublicAPIProtection [
  BreakingChange(?bc) ^ affectsFunction(?bc, ?f) ^ 
  belongsTo(?f, ?api) ^ PublicAPI(?api) ^
  changedFrom(?bc, ?v1) ^ changedTo(?bc, ?v2) ^
  majorVersion(?v1, ?maj1) ^ majorVersion(?v2, ?maj2) ^
  equal(?maj1, ?maj2) ->
    VersionMismatch(?issue) ^ reportsChange(?issue, ?bc)
]

// Version ordering: semver lexicographic
rule VersionOrdering [
  Version(?v1) ^ Version(?v2) ^
  majorVersion(?v1, ?maj1) ^ majorVersion(?v2, ?maj2) ^
  lessThan(?maj1, ?maj2) ->
    versionLessThan(?v1, ?v2)
]
```

#### Lean4 Invariants

```lean
-- Semantic versioning constraint
theorem breaking_change_requires_major_bump (bc : BreakingChange) 
  (v1 v2 : Version) 
  (h1 : bc.changedFrom = v1) (h2 : bc.changedTo = v2) :
  v2.major > v1.major := by
  cases bc.semver_compliance
  assumption

-- Version components non-negative
theorem version_components_nonneg (v : Version) :
  v.major ≥ 0 ∧ v.minor ≥ 0 ∧ v.patch ≥ 0 := by
  constructor
  · exact Nat.zero_le v.major
  constructor
  · exact Nat.zero_le v.minor
  · exact Nat.zero_le v.patch

-- Version ordering total
theorem version_ordering_total (v1 v2 : Version) :
  v1 < v2 ∨ v1 = v2 ∨ v2 < v1 := by
  unfold Version.lt
  -- лексикографическое сравнение (major, minor, patch)
  cases Nat.lt_trichotomy v1.major v2.major with
  | inl h => left; constructor; exact h
  | inr h => cases h with
    | inl heq => 
      cases Nat.lt_trichotomy v1.minor v2.minor with
      | inl h2 => left; constructor; exact ⟨heq, h2⟩
      | inr h2 => cases h2 with
        | inl heq2 =>
          cases Nat.lt_trichotomy v1.patch v2.patch with
          | inl h3 => left; exact ⟨heq, heq2, h3⟩
          | inr h3 => cases h3 with
            | inl heq3 => right; left; ext <;> assumption
            | inr h3 => right; right; exact ⟨heq, heq2, h3⟩
        | inr h2 => right; right; constructor; exact ⟨heq, h2⟩
    | inr h => right; right; constructor; exact h

-- Deprecation timeline consistency
theorem deprecation_timeline_consistent (d : Deprecation) 
  (vDep vRem : Version)
  (h1 : d.deprecatedSince = vDep) (h2 : d.removedIn = vRem) :
  vDep < vRem := by
  cases d.timeline_valid
  assumption
```

---

## TODO Phase 2

- [ ] Формализовать все концепты в OML
- [ ] Создать Rosetta CLI проект
- [ ] Генерировать OWL2 из OML
- [ ] Синхронизировать с SHACL shapes
- [ ] Доказать soundness в Lean4
- [ ] Добавить property tests для axioms
