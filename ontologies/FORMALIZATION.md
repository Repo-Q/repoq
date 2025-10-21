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

## TODO Phase 2

- [ ] Формализовать все концепты в OML
- [ ] Создать Rosetta CLI проект
- [ ] Генерировать OWL2 из OML
- [ ] Синхронизировать с SHACL shapes
- [ ] Доказать soundness в Lean4
- [ ] Добавить property tests для axioms
