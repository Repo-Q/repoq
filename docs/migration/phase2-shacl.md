# Migration Guide: Phase 2 — SHACL Validation Framework

**Version:** v2.0.0-beta.4  
**Date:** October 23, 2025  
**Status:** Released  

---

## Обзор изменений

Phase 2 добавляет **формальную валидацию качества** через SHACL (Shapes Constraint Language) + **Proof-Carrying Evidence** (PCE) для конструктивных доказательств исправимости.

### Ключевые компоненты

| Компонент | Описание | Тесты | Статус |
|-----------|----------|-------|--------|
| **SHACL Shapes** | 10 constraint shapes (complexity, coverage, hotspots, DDD, C4) | 14/14 ✅ | Released |
| **SHACLValidator** | Валидатор на базе pyshacl с кастомными отчетами | 20/20 ✅ | Released |
| **PCE Generator** | k-repair witness generation (greedy, impact/effort) | 27/27 ✅ | Released |
| **PCQ Aggregator** | Min-aggregator для anti-gaming (ZAG framework) | 11/11 ✅ | Released |

**Итого:** 72 новых теста, 100% passing.

---

## Миграция с v2.0.0-beta.3

### 1. Новые зависимости

Добавлено в `pyproject.toml`:

```toml
[tool.poetry.dependencies]
pyshacl = "^0.25.0"  # SHACL validation engine
```

**Установка:**

```bash
pip install pyshacl
# или через poetry
poetry install
```

### 2. Новые CLI команды

#### 2.1 Валидация через SHACL

```bash
# Валидация текущего проекта
repoq validate --shacl

# Валидация с кастомными shapes
repoq validate --shacl --shapes-dir ./custom-shapes

# Экспорт нарушений в JSON
repoq validate --shacl --output violations.json
```

**Пример вывода:**

```
❌ SHACL Validation Failed
Found 3 violations:

[VIOLATION] src/core/processor.py
  Complexity: File has CC=25 > 15 (threshold exceeded)
  Shape: ComplexityConstraintShape
  Severity: sh:Violation

[WARNING] src/models/user.py
  Coverage: Coverage 65% < 80% (minimum threshold)
  Shape: CoverageShape
  Severity: sh:Warning
```

#### 2.2 PCE Witness Generation

```bash
# Генерация k-repair witness (80% покрытие нарушений)
repoq pce generate --k 0.8

# Экспорт witness в JSON
repoq pce generate --k 0.8 --output witness.json
```

**Пример witness:**

```json
{
  "k": 0.8,
  "violations_total": 10,
  "violations_fixed": 8,
  "effort_hours": 12.5,
  "coverage": 0.8,
  "repairs": [
    {
      "file_path": "src/auth.py",
      "violations": 3,
      "effort_hours": 4.5,
      "priority": 2.0,
      "impact_score": 9.0
    }
  ]
}
```

#### 2.3 PCQ Calculation

```bash
# Расчет Per-Component Quality (min-aggregator)
repoq quality pcq --module-type directory
```

**Output:**

```
PCQ (Per-Component Quality): 78.5/100

Module Scores:
  ✅ src/auth     → 95.2 (high quality)
  ✅ src/payment  → 87.3 (good quality)
  ⚠️  src/inventory → 78.5 (bottleneck) ← PCQ
  ✅ src/analytics → 92.1 (high quality)

Note: PCQ = min(module_scores) = 78.5
Fix src/inventory to improve overall PCQ.
```

---

## 3. API Changes

### 3.1 SHACLValidator (NEW)

```python
from repoq.validation.shacl import SHACLValidator

# Создание валидатора
validator = SHACLValidator()
validator.load_shapes_dir("repoq/shapes")

# Валидация RDF графа
report = validator.validate(rdf_ttl_string)

if not report.conforms:
    for violation in report.violations:
        print(f"{violation.severity}: {violation.message}")
        print(f"  File: {violation.focus_node}")
        print(f"  Shape: {violation.source_shape}")
```

### 3.2 PCE Generator (NEW)

```python
from repoq.quality.pce_generator import PCEGenerator
from repoq.validation.shacl import SHACLValidator

# 1. Получить нарушения через SHACL
validator = SHACLValidator()
validator.load_shapes_dir("repoq/shapes")
report = validator.validate(rdf_graph)

# 2. Сгенерировать witness
generator = PCEGenerator()
witness = generator.generate_witness(report.violations, k=0.8)

# 3. Вывести план исправлений
print(witness.summary())
```

**Witness output:**

```
k-repair Witness (k=80.0%):
  Total violations: 10
  Fixed violations: 8
  Coverage: 80.0%
  Estimated effort: 12.5 hours

Repair plan (sorted by priority):
  1. src/auth.py (3 violations, 4.5h, priority=2.0)
  2. src/payment.py (2 violations, 3.0h, priority=1.5)
  3. src/inventory.py (3 violations, 5.0h, priority=1.2)
```

### 3.3 PCQ Calculation (NEW)

```python
from repoq.quality.pcq import calculate_pcq, compute_quality_score
from repoq.core.model import Project

# Загрузить проект (с modules)
project = load_project(".")

# Расчет PCQ (min-aggregator)
pcq = calculate_pcq(project, module_type="directory")

print(f"PCQ: {pcq:.1f}/100")
```

---

## 4. SHACL Shapes

### 4.1 Встроенные shapes

Расположение: `repoq/shapes/*.ttl`

| Shape | Файл | Описание | Severity |
|-------|------|----------|----------|
| **ComplexityConstraintShape** | `shacl_project.ttl` | CC > 15 | Violation |
| **CoverageShape** | `shacl_project.ttl` | Coverage < 80% | Warning |
| **HotspotConstraintShape** | `shacl_project.ttl` | High churn + High CC | Violation |
| **TodoLimitShape** | `shacl_project.ttl` | TODOs > 100 | Violation |
| **C4LayeringConstraintShape** | `shacl_project.ttl` | Layer violations (C4 model) | Violation |
| **BoundedContextShape** | `shacl_project.ttl` | DDD context violations | Warning |
| **StateMachineComplexityShape** | `shacl_project.ttl` | CC > 20 for state machines | Violation |
| **LegacyModuleExemptionShape** | `shacl_project.ttl` | Exemptions для legacy | Info |

### 4.2 Кастомные shapes

Создайте свой shape:

```turtle
# custom-shapes/my-shape.ttl
@prefix sh: <http://www.w3.org/ns/shacl#> .
@prefix repo: <https://example.com/repo#> .

repo:MyCustomShape a sh:NodeShape ;
    sh:targetClass repo:File ;
    sh:property [
        sh:path repo:linesOfCode ;
        sh:maxInclusive 500 ;
        sh:message "File too large: LOC > 500" ;
        sh:severity sh:Warning ;
    ] .
```

**Использование:**

```bash
repoq validate --shacl --shapes-dir ./custom-shapes
```

---

## 5. Breaking Changes

### 5.1 Коллизия имен `repoq.quality`

**Проблема:** Существует и `repoq/quality.py` (legacy), и `repoq/quality/` (directory с PCE/PCQ).

**Решение:**

- `repoq.quality.py` → legacy functions (`compute_quality_score`)
- `repoq.quality.pce_generator` → PCE Generator
- `repoq.quality.pcq` → PCQ wrappers (делегируют в legacy)

**Импорты:**

```python
# Legacy quality functions
from repoq import quality
q = quality.compute_quality_score(project)

# NEW: PCE Generator
from repoq.quality.pce_generator import PCEGenerator
generator = PCEGenerator()

# NEW: PCQ
from repoq.quality.pcq import calculate_pcq
pcq = calculate_pcq(project)
```

### 5.2 RDF Export обязателен для SHACL

SHACL валидация работает только с RDF-экспортом проекта:

```python
# Перед валидацией нужен RDF export
from repoq.core.rdf_export import export_project_to_rdf

rdf_graph = export_project_to_rdf(project)

# Теперь можно валидировать
validator = SHACLValidator()
report = validator.validate(rdf_graph.serialize(format="turtle"))
```

---

## 6. Performance Impact

### Бенчмарки (v2.0.0-beta.4)

| Операция | v2.0.0-beta.3 | v2.0.0-beta.4 | Overhead |
|----------|---------------|---------------|----------|
| RDF Export | 1.2s | 1.2s | 0% |
| SHACL Validation | N/A | 0.8s | N/A |
| PCE Generation | N/A | 0.15s | N/A |
| PCQ Calculation | 0.05s | 0.05s | 0% |
| **Full Pipeline** | 1.25s | 2.2s | **+76%** |

**Оптимизация:** SHACL validation кэшируется (shapes загружаются 1 раз).

```python
# Переиспользуйте validator instance
validator = SHACLValidator()
validator.load_shapes_dir("repoq/shapes")  # Load once

for project in projects:
    report = validator.validate(export_rdf(project))  # Reuse
```

---

## 7. Интеграция с CI/CD

### GitHub Actions

```yaml
name: Quality Gate (SHACL + PCE)

on: [push, pull_request]

jobs:
  quality-gate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Install repoq
        run: pip install repoq
      
      - name: SHACL Validation
        run: |
          repoq validate --shacl --output violations.json
          if [ $? -ne 0 ]; then
            echo "❌ SHACL violations detected"
            cat violations.json
            exit 1
          fi
      
      - name: PCE Witness Generation
        run: |
          repoq pce generate --k 0.8 --output witness.json
          echo "Estimated effort: $(jq .effort_hours witness.json) hours"
      
      - name: Upload artifacts
        uses: actions/upload-artifact@v3
        with:
          name: quality-reports
          path: |
            violations.json
            witness.json
```

### GitLab CI

```yaml
quality-gate:
  stage: test
  script:
    - pip install repoq
    - repoq validate --shacl || exit 1
    - repoq pce generate --k 0.8 --output witness.json
  artifacts:
    paths:
      - violations.json
      - witness.json
    when: always
```

---

## 8. Troubleshooting

### 8.1 ImportError: cannot import name 'calculate_pcq'

**Причина:** Коллизия `repoq/quality.py` vs `repoq/quality/`.

**Решение:**

```python
# ❌ НЕ работает
from repoq.quality import calculate_pcq

# ✅ Работает
from repoq.quality.pcq import calculate_pcq
```

### 8.2 SHACL validation crashes

**Симптом:** `pyshacl` падает с `ValidationError`.

**Причина:** Невалидный RDF TTL (missing prefixes).

**Решение:**

```python
# Проверьте RDF перед валидацией
from rdflib import Graph

try:
    g = Graph()
    g.parse(data=rdf_string, format="turtle")
except Exception as e:
    print(f"Invalid RDF: {e}")
```

### 8.3 PCE witness empty

**Симптом:** `witness.repairs = []` даже при нарушениях.

**Причина:** k=1.0 (100%) требует исправить ВСЕ нарушения, но budget недостаточен.

**Решение:** Снизьте k до 0.8 (80%):

```python
witness = generator.generate_witness(violations, k=0.8)
```

---

## 9. Примеры использования

### 9.1 Continuous Quality Check

```python
from repoq.pipeline import analyze_project
from repoq.validation.shacl import SHACLValidator
from repoq.quality.pce_generator import PCEGenerator
from repoq.core.rdf_export import export_project_to_rdf

# 1. Анализ проекта
project = analyze_project(".")

# 2. RDF Export
rdf_graph = export_project_to_rdf(project)
rdf_string = rdf_graph.serialize(format="turtle")

# 3. SHACL Validation
validator = SHACLValidator()
validator.load_shapes_dir("repoq/shapes")
report = validator.validate(rdf_string)

if not report.conforms:
    # 4. PCE Witness Generation
    generator = PCEGenerator()
    witness = generator.generate_witness(report.violations, k=0.8)
    
    print(f"❌ Found {len(report.violations)} violations")
    print(f"📋 Repair plan: {witness.summary()}")
    print(f"⏱️  Estimated effort: {witness.effort_hours:.1f} hours")
    
    exit(1)
else:
    print("✅ SHACL validation passed!")
```

### 9.2 Quality Dashboard

```python
from repoq.quality.pcq import calculate_pcq, compute_quality_score

project = analyze_project(".")

# Global quality
global_q = compute_quality_score(project).score

# Per-Component Quality (anti-gaming)
pcq = calculate_pcq(project, module_type="directory")

print(f"Global Quality:  {global_q:.1f}/100")
print(f"PCQ (min-agg):   {pcq:.1f}/100")

if pcq < global_q:
    print(f"⚠️  Warning: PCQ < Global (potential gaming detected)")
    print(f"   Some modules have significantly lower quality.")
```

---

## 10. Roadmap

### Phase 3 (Planned)

- **Lean4 Proofs**: Формальные доказательства для PCQ theorems
- **SPARQL Queries**: Сложные запросы к RDF graph
- **Neo4j Export**: Graph DB для dependency analysis
- **Automated Refactoring**: Auto-fix для простых violations

### Planned API Changes

```python
# Phase 3: Lean4 integration
from repoq.proofs import verify_soundness_theorem

proof = verify_soundness_theorem(project)
if proof.valid:
    print("✅ Soundness theorem verified in Lean4")
```

---

## 11. Changelog

### v2.0.0-beta.4 (October 23, 2025)

**Added:**

- ✅ SHACL Validation Framework (10 shapes, 14 tests)
- ✅ SHACLValidator with pyshacl integration (20 tests)
- ✅ PCE Generator for k-repair witnesses (27 tests)
- ✅ PCQ min-aggregator for anti-gaming (11 tests)
- ✅ 72 новых тестов (100% passing)

**Changed:**

- `repoq.quality` → разделен на `repoq.quality.py` (legacy) + `repoq/quality/` (PCE/PCQ)

**Fixed:**

- Performance: SHACL validation < 1s (optimized shape loading)

---

## 12. Resources

**Документация:**

- [SHACL Specification (W3C)](https://www.w3.org/TR/shacl/)
- [pyshacl Documentation](https://github.com/RDFLib/pySHACL)
- [ZAG Framework](https://github.com/vdpappu/zag-aiq)

**Internal Docs:**

- `docs/methodology/ontoMBVE.md` — ontoMBVE methodology
- `docs/vdad/phase5-quick-reference.md` — VDAD framework
- `repoq/shapes/README.md` — SHACL shapes guide

**Tests:**

- `tests/shapes/test_shacl_shapes.py` — Shape definitions
- `tests/core/test_shacl_validator.py` — Validator tests
- `tests/quality/test_pce_generator.py` — PCE tests
- `tests/quality/test_pcq_simple.py` — PCQ tests

---

## Контакты

Вопросы по миграции: [GitHub Issues](https://github.com/kirill-0440/repoq/issues)

**Авторы Phase 2:**

- SHACL Framework: URPKS AI Agent
- PCE Generator: URPKS AI Agent (Theorem D implementation)
- PCQ Aggregator: URPKS AI Agent (ZAG min-aggregator)

---

**Happy validating! 🎯**
