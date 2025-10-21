# ROADMAP — repoq 2.0 → Production-Ready

**Цель**: Довести платформу до уровня формально верифицированной системы с URPKS-гарантиями (soundness, confluence, completeness, termination).

**Методология**: Σ→Γ→𝒫→Λ→R (сигнатура → гейты → опции → агрегация → результат)

---

## Фазы развития

```
Phase 0: CURRENT (v2.0)     ━━━━━━━━━━━━━━━━━━━━━━━━ 70% готовности
Phase 1: FOUNDATIONS        ━━━━━━━━━━━━━━━ (80% → milestone M1)
Phase 2: FORMALIZATION      ━━━━━━━━━━ (90% → milestone M2)
Phase 3: VERIFICATION       ━━━━━━ (95% → milestone M3)
Phase 4: PRODUCTION         ━━━ (100% → v3.0 GA)
```

---

## Phase 0: ТЕКУЩЕЕ СОСТОЯНИЕ (baseline)

### ✅ Реализовано
- [x] CLI с 3 режимами (structure/history/full)
- [x] 6 анализаторов (Structure, History, Complexity, Weakness, Hotspots, CI/QM)
- [x] JSON-LD экспорт с онтологиями (PROV-O, OSLC, SPDX, FOAF, SDO)
- [x] TTL экспорт (RDF/Turtle)
- [x] SHACL валидация (опционально)
- [x] Graphviz графы (dependencies, coupling)
- [x] Markdown отчёты
- [x] Базовый интеграционный тест

### ❌ Критические пробелы
- [ ] Формальная спецификация онтологии (OML/OWL2)
- [ ] Доказательство звуковости маппинга (Python→RDF)
- [ ] Self-hosting (анализ самого проекта)
- [ ] Unit-тесты анализаторов (coverage <10%)
- [ ] SPARQL-примеры и документация запросов
- [ ] Property-based тесты (идемпотентность, детерминизм)
- [ ] Стратификация уровней рефлексии
- [ ] Deep merge контекстов (сейчас shallow)

---

## Phase 1: FOUNDATIONS (4 недели) → **Milestone M1**

**Цель**: Базовая инфраструктура качества и тестирования

### Week 1-2: Testing Infrastructure
**Гейт**: `tests_min_cov: 0.8` ✅

#### Task 1.1: Unit-тесты для анализаторов
```bash
tests/
  analyzers/
    test_structure.py         # StructureAnalyzer
    test_history.py           # HistoryAnalyzer
    test_complexity.py        # ComplexityAnalyzer
    test_weakness.py          # WeaknessAnalyzer
    test_hotspots.py          # HotspotsAnalyzer
    test_ci_qm.py             # CIQualityAnalyzer
  core/
    test_model.py             # dataclass invariants
    test_jsonld.py            # маппинг корректности
    test_rdf_export.py        # TTL serialization
    test_repo_loader.py       # Git operations
  integration/
    test_pipelines.py         # end-to-end scenarios
    test_cli_modes.py         # CLI команды
```

**Критерии приёмки**:
- [ ] Coverage ≥ 80% (pytest-cov)
- [ ] Все анализаторы имеют ≥5 unit-тестов
- [ ] Тесты детерминированы (фиксированные моки для Git)

#### Task 1.2: Property-based тесты
```python
# tests/properties/test_analyzers_properties.py
from hypothesis import given, strategies as st

@given(st.text(), st.integers(min_value=0))
def test_structure_analyzer_idempotent(repo_path, seed):
    """Двойной запуск → идентичный результат"""
    result1 = run_structure_twice(repo_path, seed)
    result2 = run_structure_twice(repo_path, seed)
    assert result1 == result2

@given(st.lists(st.text()))
def test_analyzers_commutative(analyzer_order):
    """Порядок анализаторов не влияет на финальный граф (коммутативность)"""
    # ... проверка, что coupling/dependencies инвариантны
```

**Критерии приёмки**:
- [ ] ≥10 property-тестов (Hypothesis)
- [ ] Проверка идемпотентности всех анализаторов
- [ ] Проверка коммутативности (где применимо)

### Week 3: Self-hosting
**Гейт**: `reflexive_completeness: true` ✅

#### Task 1.3: Bootstrap pipeline
```bash
# .github/workflows/self_analyze.yml
name: Self-Hosting Quality Check
on: [push, pull_request]
jobs:
  analyze-self:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: pip install -e ".[full]"
      - run: repoq full . -o artifacts/repoq_self.jsonld --ttl artifacts/repoq_self.ttl --validate-shapes
      - run: python scripts/assert_quality_gates.py artifacts/repoq_self.jsonld
      - uses: actions/upload-artifact@v3
        with:
          name: self-analysis
          path: artifacts/
```

```python
# scripts/assert_quality_gates.py
import json, sys

data = json.load(open("artifacts/repoq_self.jsonld"))
issues_high = [i for i in data.get("issues", []) if i.get("severity", {}).get("@id", "").endswith("Critical")]

if len(issues_high) > 0:
    print(f"FAIL: {len(issues_high)} high-severity issues in repoq itself!")
    sys.exit(1)

# Проверка минимальных метрик
assert data.get("modules"), "No modules found"
assert len(data.get("contributors", [])) > 0, "No contributors"
print("✅ Self-analysis passed")
```

**Критерии приёмки**:
- [ ] CI автоматически запускает `repoq full .`
- [ ] Артефакты сохраняются (repoq_self.jsonld/ttl)
- [ ] Fail при high-severity issues
- [ ] Badge в README с результатами

#### Task 1.4: Deep merge контекстов
```python
# repoq/core/jsonld.py
def _deep_merge_contexts(base: dict, override: dict, path: str = "") -> dict:
    """Рекурсивный merge с conflict detection"""
    conflicts = []
    result = base.copy()
    
    for key, value in override.items():
        if key in result:
            if isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = _deep_merge_contexts(result[key], value, f"{path}.{key}")
            elif result[key] != value:
                conflicts.append(f"{path}.{key}: {result[key]} vs {value}")
                result[key] = value  # override wins
        else:
            result[key] = value
    
    if conflicts:
        logger.warning(f"Context merge conflicts: {conflicts}")
    
    return result
```

**Критерии приёмки**:
- [ ] Реализован `_deep_merge_contexts`
- [ ] Логирование конфликтов
- [ ] Тесты для corner cases (циклические ссылки)

### Week 4: Documentation
**Гейт**: `quality: linters + docs` ✅

#### Task 1.5: SPARQL примеры
```bash
examples/
  queries/
    01_project_overview.rq
    02_top_hotspots.rq
    03_authors_by_commits.rq
    04_coupling_matrix.rq
    05_issues_by_severity.rq
    06_test_coverage.rq
    07_dependencies_graph.rq
    08_prov_lineage.rq
    09_oslc_compliance.rq
    10_spdx_checksums.rq
  notebooks/
    analyze_with_sparql.ipynb
  data/
    sample_repoq_output.ttl
```

**Пример запроса**:
```sparql
# examples/queries/02_top_hotspots.rq
PREFIX repo: <http://example.org/repo#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

SELECT ?file ?hotness ?complexity ?churn
WHERE {
  ?file a repo:File ;
        repo:hotness ?hotness ;
        repo:complexity ?complexity ;
        repo:codeChurn ?churn .
}
ORDER BY DESC(?hotness)
LIMIT 10
```

**Критерии приёмки**:
- [ ] ≥10 SPARQL запросов с комментариями
- [ ] Jupyter notebook с примерами
- [ ] README секция "Querying RDF Graph"

#### Task 1.6: Линтеры и CI checks
```toml
# pyproject.toml
[tool.ruff]
line-length = 120
target-version = "py39"
select = ["E", "F", "I", "N", "UP", "YTT", "S", "BLE", "FBT", "B", "A", "COM", "C4", "DTZ", "T10", "DJ", "EM", "EXE", "ISC", "ICN", "G", "INP", "PIE", "T20", "PYI", "PT", "Q", "RSE", "RET", "SLF", "SIM", "TID", "TCH", "INT", "ARG", "PTH", "ERA", "PD", "PGH", "PL", "TRY", "NPY", "RUF"]

[tool.mypy]
strict = true
warn_unused_ignores = true
disallow_untyped_defs = true
```

```yaml
# .github/workflows/ci.yml
name: CI
on: [push, pull_request]
jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: {python-version: "3.11"}
      - run: pip install -e ".[dev]"
      - run: ruff check .
      - run: black --check .
      - run: mypy repoq/
  
  test:
    strategy:
      matrix:
        python-version: ["3.9", "3.10", "3.11", "3.12"]
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: {python-version: "${{ matrix.python-version }}"}
      - run: pip install -e ".[full,dev]"
      - run: pytest --cov=repoq --cov-report=xml
      - uses: codecov/codecov-action@v3
```

**Критерии приёмки**:
- [ ] CI проходит (lint + test + coverage)
- [ ] Codecov badge ≥80%
- [ ] mypy strict mode без ошибок

---

## Phase 2: FORMALIZATION (6 недель) → **Milestone M2**

**Цель**: Формальная спецификация онтологии и доказательство звуковости

### Week 5-6: OML/OWL2 Ontology
**Гейт**: `soundness: formal_spec` ✅

#### Task 2.1: OML спецификация
```bash
ontologies/
  repoq_core.oml            # Базовые концепты (Project, Module, File, Person)
  repoq_prov.oml            # PROV-O extension
  repoq_oslc.oml            # OSLC CM/QM/Config alignment
  repoq_spdx.oml            # SPDX File/Checksum
  repoq_metrics.oml         # Метрики (complexity, hotness, coupling)
  mappings/
    python_to_rdf.oml       # Маппинг Python dataclasses → RDF
```

**Пример OML**:
```oml
@dc:title "repoq Core Ontology"
vocabulary <http://example.org/repoq/core#> as repoq {
  
  extends <http://www.w3.org/ns/prov#> as prov
  extends <http://spdx.org/rdf/terms#> as spdx
  
  concept Project :> prov:Entity [
    restricts all relation containsModule to Module
    restricts all relation containsFile to File
  ]
  
  concept File :> spdx:File, prov:Entity [
    restricts some scalar property linesOfCode to xsd:nonNegativeInteger
    restricts some scalar property complexity to xsd:decimal
    restricts all relation contributedBy to Person
  ]
  
  concept Person :> prov:Agent
  
  scalar property hotness :> [
    domain File
    range xsd:decimal
    functional
  ]
  
  // Аксиомы
  rule HotnessNonNegative [
    hotness(?f, ?h) -> greaterThanOrEqual(?h, 0.0)
  ]
}
```

**Критерии приёмки**:
- [ ] ≥5 OML модулей
- [ ] Аксиомы для всех метрик
- [ ] Валидация OML через Rosetta CLI

#### Task 2.2: SHACL by default + расширенные shapes
```turtle
# shapes/repoq_advanced.ttl
@prefix sh: <http://www.w3.org/ns/shacl#> .
@prefix repo: <http://example.org/repo#> .

repo:FileShape a sh:NodeShape ;
  sh:targetClass repo:File ;
  sh:property [
    sh:path repo:linesOfCode ;
    sh:minInclusive 0 ;
    sh:datatype xsd:nonNegativeInteger ;
  ] ;
  sh:property [
    sh:path repo:hotness ;
    sh:minInclusive 0.0 ;
    sh:maxInclusive 1.0 ;
  ] ;
  sh:property [
    sh:path repo:complexity ;
    sh:minInclusive 0.0 ;
  ] .

repo:PersonShape a sh:NodeShape ;
  sh:targetClass foaf:Person ;
  sh:property [
    sh:path foaf:name ;
    sh:minCount 1 ;
    sh:datatype xsd:string ;
  ] ;
  sh:property [
    sh:path repo:commits ;
    sh:minInclusive 0 ;
  ] .
```

```python
# repoq/config.py
@dataclass
class AnalyzeConfig:
    validate_shapes: bool = True  # ← по умолчанию включено
```

**Критерии приёмки**:
- [ ] SHACL валидация включена by default
- [ ] ≥20 shapes (покрытие всех концептов)
- [ ] CI fail при SHACL violations

### Week 7-8: Lean4 Proofs
**Гейт**: `soundness: verified_mapping` ✅

#### Task 2.3: Lean4 спецификация маппинга
```bash
proofs/
  RepoqCore.lean            # Базовые определения
  Mapping.lean              # Доказательство корректности Python→RDF
  Soundness.lean            # Soundness теорема
  Completeness.lean         # Completeness (относительная)
  Tests.lean                # QuickCheck-like property tests
```

**Пример Lean4 кода**:
```lean
-- proofs/RepoqCore.lean
import Mathlib.Data.Finset.Basic
import Mathlib.Data.Real.Basic

structure File where
  path : String
  loc : Nat
  complexity : Option Real
  hotness : Option Real
  deriving Repr

-- Инвариант: hotness в [0, 1]
def File.valid (f : File) : Prop :=
  match f.hotness with
  | none => True
  | some h => 0 ≤ h ∧ h ≤ 1

-- proofs/Mapping.lean
def pythonFileToRDF (f : File) : RDFGraph :=
  { triples := [
      (f.path, "rdf:type", "repo:File"),
      (f.path, "repo:linesOfCode", toString f.loc),
      -- ...
    ]
  }

-- Soundness: валидный Python File → валидный RDF граф
theorem mapping_preserves_validity (f : File) (h : f.valid) :
  (pythonFileToRDF f).satisfies repo_shapes := by
  unfold pythonFileToRDF
  unfold File.valid at h
  cases f.hotness with
  | none => simp; sorry  -- trivial case
  | some hval =>
    cases h with
    | intro h1 h2 =>
      -- доказываем, что RDF triple (f.path, "repo:hotness", hval) удовлетворяет SHACL
      sorry
```

**Критерии приёмки**:
- [ ] Формализованы все основные dataclasses (Project, File, Module, Person)
- [ ] Доказана теорема `mapping_preserves_validity`
- [ ] CI проверяет Lean4 проекты (`lake build`)

### Week 9: Стратификация рефлексии
**Гейт**: `reflexive_completeness: stratified_reflection` ✅

#### Task 2.4: Уровни вселенных для метаанализа
```python
# repoq/meta/levels.py
from enum import IntEnum

class AnalysisLevel(IntEnum):
    """Стратификация уровней анализа (предотвращает парадоксы self-reference)"""
    L0_CODE = 0          # Анализируемый код (user projects)
    L1_ANALYZER = 1      # Код анализаторов (repoq itself)
    L2_META_ANALYZER = 2 # Анализ анализаторов (будущее расширение)

@dataclass
class Project:
    # ...
    analysis_level: AnalysisLevel = AnalysisLevel.L0_CODE
    
    def analyze_self(self) -> "Project":
        """Self-hosting: анализировать сам проект на уровне L1"""
        if self.analysis_level >= AnalysisLevel.L1_ANALYZER:
            raise ValueError("Cannot self-analyze beyond L1 (prevents infinite regress)")
        
        # ... запуск анализа с level=L1
```

**Критерии приёмки**:
- [ ] Введены уровни 0/1/2
- [ ] Запрет на анализ уровня ≥L2 (защита от парадоксов)
- [ ] Тесты для cross-level analysis

### Week 10: Confluence check
**Гейт**: `confluence: orthogonality` ✅

#### Task 2.5: Проверка ортогональности анализаторов
```python
# tests/confluence/test_analyzer_independence.py
import pytest
from itertools import permutations

def test_analyzers_orthogonal():
    """Анализаторы не конфликтуют (локальная confluence)"""
    repo = create_test_repo()
    project = Project(...)
    
    # Все перестановки порядка анализаторов
    analyzers = [StructureAnalyzer(), HistoryAnalyzer(), ComplexityAnalyzer()]
    
    results = []
    for order in permutations(analyzers):
        p = deepcopy(project)
        for analyzer in order:
            analyzer.run(p, repo, cfg)
        results.append(p.to_dict())
    
    # Все результаты должны быть идентичны (модуло ordering)
    canonical = normalize(results[0])
    for r in results[1:]:
        assert normalize(r) == canonical, "Analyzers not orthogonal!"

def normalize(data: dict) -> dict:
    """Нормализация для сравнения (sorting списков и т.п.)"""
    # ...
```

**Критерии приёмки**:
- [ ] Тест на все перестановки анализаторов
- [ ] Доказательство ортогональности (нет взаимных зависимостей)
- [ ] Если неортогональны → рефакторинг или документирование порядка

---

## Phase 3: VERIFICATION (4 недели) → **Milestone M3**

**Цель**: Полная формальная верификация и производственная готовность

### Week 11-12: Formal Verification Suite
**Гейт**: `all_gates: green` ✅

#### Task 3.1: TLA+ спецификация пайплайна
```tla
---- MODULE RepoqPipeline ----
EXTENDS Naturals, Sequences, FiniteSets

CONSTANTS Analyzers, MaxFiles
VARIABLES project, currentAnalyzer, filesProcessed

Init ==
  /\ project = [files |-> {}, modules |-> {}, issues |-> {}]
  /\ currentAnalyzer = 1
  /\ filesProcessed = 0

RunAnalyzer(a) ==
  /\ currentAnalyzer = a
  /\ filesProcessed < MaxFiles
  /\ project' = [project EXCEPT 
       !.files = @ \union AnalyzeFiles(a),
       !.issues = @ \union DetectIssues(a)]
  /\ filesProcessed' = filesProcessed + 1
  /\ currentAnalyzer' = IF a < Len(Analyzers) THEN a + 1 ELSE a

Termination == filesProcessed >= MaxFiles \/ currentAnalyzer > Len(Analyzers)

Invariant ==
  /\ filesProcessed <= MaxFiles  \* всегда терминируем
  /\ Cardinality(project.issues) < 10000  \* не взрыв памяти

Spec == Init /\ [][RunAnalyzer(currentAnalyzer)]_<<project, currentAnalyzer, filesProcessed>> /\ WF_<<...>>(Termination)
====
```

**Критерии приёмки**:
- [ ] TLA+ spec для пайплайна
- [ ] Model checking через TLC (proof of termination)
- [ ] Invariants проверены (no deadlocks, bounded memory)

#### Task 3.2: Coq/Isabelle формализация (optional, high-value)
```coq
(* proofs/repoq_soundness.v *)
Require Import Coq.Strings.String.
Require Import Coq.Lists.List.
Import ListNotations.

Inductive RDFTriple : Type :=
  | triple : string -> string -> string -> RDFTriple.

Definition RDFGraph := list RDFTriple.

Inductive File : Type :=
  | mkFile : string -> nat -> option Q -> File.  (* path, LOC, complexity *)

Definition fileToRDF (f : File) : RDFGraph :=
  match f with
  | mkFile p loc cplx =>
      [ triple p "rdf:type" "repo:File" ;
        triple p "repo:linesOfCode" (natToString loc) ]
  end.

(* Soundness: всегда генерируем хотя бы rdf:type *)
Theorem fileToRDF_has_type : forall f,
  exists g, In (triple (filePath f) "rdf:type" "repo:File") (fileToRDF f).
Proof.
  intros. destruct f as [p loc cplx]. simpl.
  exists (triple p "rdf:type" "repo:File"). left. reflexivity.
Qed.
```

**Критерии приёмки**:
- [ ] Базовая Coq формализация (маппинг + soundness)
- [ ] Proof-carrying code (экспорт сертификатов)

### Week 13: Performance & Scalability
**Гейт**: `performance: production_ready` ✅

#### Task 3.3: Benchmarks
```python
# benchmarks/bench_analyzers.py
import pytest
from repoq.pipeline import run_pipeline

@pytest.mark.benchmark(group="analyzers")
def test_structure_10k_files(benchmark, large_repo):
    """Структурный анализ 10K файлов < 60 сек"""
    result = benchmark(run_pipeline, mode="structure", repo=large_repo, max_files=10000)
    assert result.duration < 60.0

@pytest.mark.benchmark(group="history")
def test_history_100k_commits(benchmark, huge_repo):
    """История 100K коммитов < 300 сек"""
    result = benchmark(run_pipeline, mode="history", repo=huge_repo)
    assert result.duration < 300.0
```

```bash
# CI benchmark regression tracking
pytest benchmarks/ --benchmark-autosave --benchmark-compare=last
```

**Критерии приёмки**:
- [ ] Benchmarks для всех анализаторов
- [ ] Regression tracking в CI
- [ ] Оптимизация узких мест (profiling → pypy/cython для hotspots)

#### Task 3.4: Масштабирование (parallel execution)
```python
# repoq/pipeline.py
from concurrent.futures import ProcessPoolExecutor

def run_pipeline_parallel(project: Project, repo_dir: str, cfg: AnalyzeConfig) -> None:
    """Параллельный запуск ортогональных анализаторов"""
    
    # Group 1: независимые (можно параллельно)
    independent = [StructureAnalyzer(), ComplexityAnalyzer(), WeaknessAnalyzer()]
    
    with ProcessPoolExecutor(max_workers=cfg.max_workers) as executor:
        futures = [executor.submit(a.run, project, repo_dir, cfg) for a in independent]
        for f in futures:
            f.result()  # ждём завершения
    
    # Group 2: зависимые от Group 1 (последовательно)
    HistoryAnalyzer().run(project, repo_dir, cfg)
    HotspotsAnalyzer().run(project, repo_dir, cfg)
```

**Критерии приёмки**:
- [ ] Параллельный режим (--parallel флаг)
- [ ] Speedup ≥2x на 4-core машине
- [ ] Thread-safety всех анализаторов

### Week 14: Security & Hardening
**Гейт**: `security: production_hardened` ✅

#### Task 3.5: Security audit
```bash
# CI security checks
pip install bandit safety semgrep
bandit -r repoq/ -f json -o security_report.json
safety check --json
semgrep --config=auto repoq/
```

**Checklist**:
- [ ] Нет eval/exec/pickle десериализации
- [ ] Валидация всех пользовательских входов (paths, URLs, globs)
- [ ] Rate limiting для Git clone (защита от DoS)
- [ ] Sandboxing для анализа недоверенных репозиториев

#### Task 3.6: Error handling & resilience
```python
# repoq/core/resilience.py
from tenacity import retry, stop_after_attempt, wait_exponential

class AnalyzerError(Exception):
    """Базовое исключение анализатора"""
    pass

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
def safe_git_clone(url: str, dest: str) -> str:
    """Retry-логика для Git операций"""
    try:
        return git.Repo.clone_from(url, dest)
    except git.GitCommandError as e:
        logger.warning(f"Git clone failed: {e}, retrying...")
        raise

def run_analyzer_safe(analyzer: Analyzer, project: Project, repo_dir: str, cfg: AnalyzeConfig) -> None:
    """Обёртка с graceful degradation"""
    try:
        analyzer.run(project, repo_dir, cfg)
    except Exception as e:
        logger.error(f"{analyzer.__class__.__name__} failed: {e}")
        project.issues[f"analyzer_failure_{analyzer.__class__.__name__}"] = Issue(
            id=f"error:{analyzer.__class__.__name__}",
            type="oslc_cm:Defect",
            description=f"Analyzer crashed: {e}",
            severity="high"
        )
        if cfg.fail_fast:
            raise
```

**Критерии приёмки**:
- [ ] Retry для всех сетевых операций
- [ ] Graceful degradation (продолжаем при падении 1 анализатора)
- [ ] Structured logging (JSON logs для production)

---

## Phase 4: PRODUCTION (2 недели) → **v3.0 GA**

**Цель**: Релиз production-ready версии с полной документацией

### Week 15: Production Deployment
**Гейт**: `deployment: automated` ✅

#### Task 4.1: Docker + Helm
```dockerfile
# Dockerfile
FROM python:3.11-slim
WORKDIR /app
RUN apt-get update && apt-get install -y git graphviz && rm -rf /var/lib/apt/lists/*
COPY . /app
RUN pip install --no-cache-dir -e ".[full]"
ENTRYPOINT ["repoq"]
```

```yaml
# helm/repoq/values.yaml
image:
  repository: ghcr.io/yourorg/repoq
  tag: "3.0.0"
  pullPolicy: IfNotPresent

resources:
  limits:
    cpu: 4
    memory: 8Gi
  requests:
    cpu: 2
    memory: 4Gi

persistence:
  enabled: true
  size: 50Gi
```

**Критерии приёмки**:
- [ ] Docker image < 500MB
- [ ] Helm chart для Kubernetes
- [ ] CI публикует образы в GHCR

#### Task 4.2: SaaS API (optional)
```python
# repoq/api/server.py
from fastapi import FastAPI, BackgroundTasks
from pydantic import BaseModel

app = FastAPI(title="repoq API", version="3.0.0")

class AnalysisRequest(BaseModel):
    repository_url: str
    mode: str = "full"
    options: dict = {}

@app.post("/analyze")
async def analyze(req: AnalysisRequest, background_tasks: BackgroundTasks):
    """Асинхронный анализ репозитория"""
    task_id = uuid4()
    background_tasks.add_task(run_analysis_task, task_id, req)
    return {"task_id": task_id, "status": "queued"}

@app.get("/results/{task_id}")
async def get_results(task_id: str):
    """Получить результаты анализа"""
    # ... retrieve from storage
```

**Критерии приёмки**:
- [ ] REST API (FastAPI)
- [ ] Async queue (Celery/RQ)
- [ ] S3 storage для результатов

### Week 16: Documentation & Release
**Гейт**: `documentation: complete` ✅

#### Task 4.3: Полная документация
```bash
docs/
  index.md                  # Главная
  getting-started.md        # Quick start
  architecture/
    overview.md
    analyzers.md
    ontology.md
    pipeline.md
  api/
    cli-reference.md
    python-api.md
    rest-api.md
  guides/
    ci-integration.md
    sparql-queries.md
    custom-analyzers.md
    performance-tuning.md
  verification/
    formal-proofs.md        # Lean4/Coq доказательства
    shacl-shapes.md
    testing-strategy.md
  deployment/
    docker.md
    kubernetes.md
    production-checklist.md
```

**Критерии приёмки**:
- [ ] MkDocs site (readthedocs theme)
- [ ] API reference автогенерация (sphinx-apidoc)
- [ ] Video tutorial (5 мин)
- [ ] Case studies (≥3 примера на реальных проектах)

#### Task 4.4: Release процесс
```yaml
# .github/workflows/release.yml
name: Release
on:
  push:
    tags: ['v*']
jobs:
  release:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: python -m build
      - run: twine upload dist/*
        env:
          TWINE_USERNAME: __token__
          TWINE_PASSWORD: ${{ secrets.PYPI_TOKEN }}
      - uses: docker/build-push-action@v5
        with:
          push: true
          tags: ghcr.io/yourorg/repoq:${{ github.ref_name }}
      - uses: ncipollo/release-action@v1
        with:
          artifacts: "dist/*"
          generateReleaseNotes: true
```

**Критерии приёмки**:
- [ ] Автоматическая публикация в PyPI
- [ ] GitHub Release с changelog
- [ ] Docker image tagged
- [ ] Announcement (blog post, Twitter, HN)

---

## Метрики успеха (Gate Criteria)

| Гейт | Phase 0 | M1 | M2 | M3 | v3.0 |
|------|---------|----|----|----|----|
| **Soundness** | ⚠️ 40% | 60% | ✅ 90% | ✅ 95% | ✅ 100% |
| **Completeness** | ⚠️ 50% | 70% | ✅ 85% | ✅ 90% | ✅ 95% |
| **Confluence** | ⚠️ 60% | ✅ 80% | ✅ 90% | ✅ 95% | ✅ 100% |
| **Termination** | ✅ 80% | ✅ 90% | ✅ 95% | ✅ 100% | ✅ 100% |
| **Test Coverage** | ❌ 5% | ✅ 80% | ✅ 85% | ✅ 90% | ✅ 95% |
| **Documentation** | ⚠️ 30% | 50% | 70% | ✅ 90% | ✅ 100% |
| **Performance** | ⚠️ 60% | 70% | ✅ 80% | ✅ 95% | ✅ 100% |
| **Security** | ⚠️ 50% | 60% | 70% | ✅ 95% | ✅ 100% |

---

## Ресурсы и команда

### Требуемые роли
- **Lead Engineer** (1 FTE) — архитектура, код-ревью
- **Formal Methods Expert** (0.5 FTE) — Lean4/Coq/TLA+
- **DevOps Engineer** (0.3 FTE) — CI/CD, Kubernetes
- **Technical Writer** (0.2 FTE) — документация

### Бюджет времени
- Phase 1: 4 недели × 1.5 FTE = 6 person-weeks
- Phase 2: 6 недель × 2 FTE = 12 person-weeks
- Phase 3: 4 недели × 2 FTE = 8 person-weeks
- Phase 4: 2 недели × 1.5 FTE = 3 person-weeks
- **ИТОГО**: ~29 person-weeks ≈ 7 calendar months

---

## Риски и митигации

| Риск | Вероятность | Влияние | Митигация |
|------|-------------|---------|-----------|
| Lean4 доказательства слишком сложны | HIGH | MEDIUM | Упростить до Coq/QuickCheck; фокус на key properties |
| OML спецификация не покрывает edge cases | MEDIUM | HIGH | Итеративная разработка + тесты на реальных данных |
| Performance деградация при больших репо | MEDIUM | MEDIUM | Раннее профилирование + incremental analysis |
| SHACL shapes конфликтуют с legacy данными | LOW | HIGH | Versioning онтологии (v2 vs v3 contexts) |
| Команда недооценивает объём формализации | HIGH | HIGH | Weekly checkpoints, MVP-подход к доказательствам |

---

## Критерии завершения (Definition of Done)

✅ **v3.0 GA считается готовой, если**:

1. **Верификация**:
   - [ ] Все гейты зелёные (soundness/confluence/completeness/termination)
   - [ ] Lean4 теорема `mapping_preserves_validity` доказана
   - [ ] TLA+ model checking проходит без violations
   - [ ] Coverage ≥90%

2. **Производительность**:
   - [ ] 10K файлов < 60 сек
   - [ ] 100K коммитов < 5 мин
   - [ ] Memory < 8GB для крупных репозиториев

3. **Документация**:
   - [ ] Полная docs site (MkDocs)
   - [ ] ≥10 SPARQL примеров
   - [ ] Video tutorial
   - [ ] ≥3 case studies

4. **Deployment**:
   - [ ] Docker image опубликован
   - [ ] PyPI package released
   - [ ] Helm chart готов
   - [ ] Production checklist пройден

5. **Community**:
   - [ ] ≥100 GitHub stars
   - [ ] ≥10 contributors
   - [ ] ≥5 issues closed
   - [ ] Mention в ≥2 статьях/блогах

---

## Next Steps (немедленные действия)

```bash
# Week 1 Sprint Plan
git checkout -b phase1/testing-infra

# Day 1-2: Setup pytest infrastructure
mkdir -p tests/{analyzers,core,integration,properties,confluence}
touch tests/analyzers/test_{structure,history,complexity,weakness,hotspots,ci_qm}.py

# Day 3-4: Implement first 20 unit tests
# ... (focus on StructureAnalyzer + ComplexityAnalyzer)

# Day 5: Setup CI
cp examples/ci.yml.template .github/workflows/ci.yml
# Add codecov, pytest, ruff, mypy

# End of Week 1: PR with ≥50% coverage increase
```

**Запустить немедленно**:
```bash
pip install -e ".[dev]"
pytest --cov=repoq --cov-report=term-missing  # baseline coverage
ruff check . --fix
mypy repoq/ --install-types
```

---

**Статус**: ROADMAP утверждён. Начало Phase 1 — немедленно.  
**Owner**: Lead Engineer  
**Review cadence**: еженедельные sync-up по пятницам  
**Success metric**: v3.0 GA в production к Q2 2026
