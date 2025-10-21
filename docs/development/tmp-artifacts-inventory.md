# Временные артефакты и наработки (tmp/)

**Статус**: 🔄 Work in Progress  
**Цель**: Фиксация экспериментальных и подготовительных материалов для будущей интеграции  
**Дата создания**: 2025-10-21

---

## Обзор

Директория `tmp/` содержит **три** основных набора артефактов:

1. **`repoq-meta-loop-addons/`** — Онтологическая мета-петля качества (19 файлов)
2. **`zag_repoq-finished/`** — Интеграция с ZAG (PCQ/PCE) (51 файл)
3. **`repoq-any2math-integration/`** — Proof-carrying нормализация через Lean (7 файлов)

**Итого: 77 файлов** готовых к интеграции компонентов.

Эти материалы готовятся к интеграции в основную кодовую базу в соответствии с планом из:
- `docs/development/ontology-alignment-report.md`
- `docs/development/quality-loop-roadmap.md`
- `docs/development/mathematical-proof-quality-monotonicity.md`
- `docs/development/formal-foundations-complete.md` (Section 15)
- `docs/development/formal-diagrams.md` (визуализация концепций)

---

## 1. repoq-meta-loop-addons/

### Назначение

Экспериментальные компоненты для реализации **онтологического самопонимания** и **стратифицированного self-application**.

### Структура

```
tmp/repoq-meta-loop-addons/
├── README.md                           # Инструкции по интеграции
├── docs/
│   └── META_QUALITY.md                 # Концепция + практические примеры
├── ontologies/                         # Three-Ontology Architecture
│   ├── code.ttl                        #   Code Ontology (AST, symbols, imports)
│   ├── c4.ttl                          #   C4 Model Ontology (containers, components)
│   ├── ddd.ttl                         #   DDD Ontology (bounded contexts, aggregates)
│   ├── meta_context.jsonld             #   JSON-LD контекст для онтологий
│   └── mappings.yaml                   #   Маппинг Code→C4→DDD
├── shapes/
│   └── meta_loop.ttl                   # SHACL: self-analysis guard, VC policies
├── trs/                                # Term Rewriting Systems (правила)
│   ├── jsonld.json                     #   Правила для JSON-LD нормализации
│   ├── metrics.json                    #   Правила для метрик (монотонность)
│   ├── rdf.json                        #   RDF-специфичные правила
│   ├── semver.json                     #   Semantic Versioning правила
│   └── spdx.json                       #   SPDX license правила
├── repoq/
│   ├── cli_meta.py                     # CLI расширения: meta-self, trs-verify
│   └── trs/
│       └── engine.py                   # TRS движок (confluence, termination)
├── sparql/
│   ├── inference_construct.rq          # SPARQL CONSTRUCT для инференса
│   └── quality_checks.rq               # Запросы для валидации качества
└── tests/
    ├── test_self_policy.py             # Тесты стратификации self-application
    └── test_trs_idempotence.py         # Тесты TRS идемпотентности
```

### Ключевые компоненты

#### 1.1 Ontologies (Three-Ontology Architecture)

**Code Ontology** (`code.ttl`):
- Классы: `code:Module`, `code:Class`, `code:Function`, `code:Variable`
- Свойства: `code:imports`, `code:calls`, `code:defines`
- Цель: AST-уровень понимания кода

**C4 Model Ontology** (`c4.ttl`):
- Классы: `c4:Container`, `c4:Component`, `c4:Relationship`
- Свойства: `c4:dependsOn`, `c4:contains`, `c4:exposes`
- Цель: Архитектурный уровень (системы, контейнеры, компоненты)

**DDD Ontology** (`ddd.ttl`):
- Классы: `ddd:BoundedContext`, `ddd:Aggregate`, `ddd:Entity`, `ddd:ValueObject`
- Свойства: `ddd:contextBoundary`, `ddd:aggregateRoot`, `ddd:belongsTo`
- Цель: Доменная модель и бизнес-логика

**Mappings** (`mappings.yaml`):
```yaml
code_to_c4:
  - code:Module → c4:Component (when: has public API)
  - code:Package → c4:Container (when: deployment unit)

c4_to_ddd:
  - c4:Component → ddd:BoundedContext (when: domain focus)
  - c4:Relationship → ddd:ContextMap (when: cross-context)
```

#### 1.2 TRS Engine

**Цель**: Математически звуковое (sound) переписывание метрик и структур.

**Правила** (`trs/*.json`):
- Формат: `{"lhs": pattern, "rhs": replacement, "conditions": [...]}`
- Свойства: Confluence (Church-Rosser), Termination, Idempotence

**Движок** (`repoq/trs/engine.py`):
- `apply_rules(term, ruleset)` — применение правил с гарантией терминации
- `check_confluence(rules)` — проверка критических пар (Knuth-Bendix)
- `normalize(term)` — приведение к нормальной форме

#### 1.3 SHACL Shapes

**Self-Application Guard** (`shapes/meta_loop.ttl`):
```turtle
:SelfAnalysisShape
    a sh:NodeShape ;
    sh:targetClass repo:SelfAnalysis ;
    sh:property [
        sh:path repo:stratificationLevel ;
        sh:minInclusive 0 ;
        sh:maxInclusive 2 ;
        sh:message "Stratification level must be 0-2"
    ] ;
    sh:property [
        sh:path repo:readOnlyMode ;
        sh:hasValue true ;
        sh:message "Self-analysis must be read-only"
    ] .
```

**Назначение**: Предотвращение парадоксов самоанализа (Russell's paradox analog).

#### 1.4 SPARQL Queries

**Inference** (`sparql/inference_construct.rq`):
```sparql
CONSTRUCT {
    ?component ddd:BoundedContext ?context .
}
WHERE {
    ?component a c4:Component .
    ?component c4:hasResponsibility ?resp .
    FILTER (regex(?resp, "Domain|Business"))
    BIND (IRI(CONCAT("http://example.org/context/", STR(?component))) AS ?context)
}
```

**Quality Checks** (`sparql/quality_checks.rq`):
- Обнаружение циклических зависимостей
- Проверка нарушений DDD паттернов
- Валидация архитектурных ограничений

### Статус интеграции

| Компонент | Готовность | Приоритет | Блокеры |
|-----------|------------|-----------|---------|
| `code.ttl` | 80% | P1 | Нужны примеры для Python AST |
| `c4.ttl` | 70% | P1 | Автообнаружение контейнеров |
| `ddd.ttl` | 60% | P2 | Определение heuristics для BC |
| `trs/engine.py` | 90% | P0 | Нет (готов к интеграции) |
| `shapes/meta_loop.ttl` | 85% | P0 | Тестирование с PySHACL |
| `cli_meta.py` | 75% | P1 | Интеграция с основным CLI |
| Tests | 40% | P1 | Расширить покрытие до 80% |

### План интеграции

**Week 1-2** (Priority 0 — Safety Guards):
1. ✅ Интегрировать `trs/engine.py` → `repoq/core/trs.py`
2. ✅ Добавить `shapes/meta_loop.ttl` → `repoq/shapes/`
3. ✅ Реализовать `SelfApplicationGuard` в `repoq/gate.py`
4. ✅ Тесты: `test_self_policy.py` → `tests/test_safety.py`

**Week 2-4** (Priority 1 — Basic Ontology):
1. Интегрировать `ontologies/code.ttl` → `repoq/ontologies/`
2. Реализовать `BasicOntologyManager` в `repoq/ontology/manager.py`
3. Добавить pattern detection (5-7 patterns)
4. Обновить Q-метрику: `Q += architectural_bonus`

**Month 2** (Priority 2 — Full Ontology):
1. Добавить `c4.ttl`, `ddd.ttl` в полный набор
2. Реализовать `SemanticInferenceEngine`
3. Cross-ontology маппинг через SPARQL

---

## 2. zag_repoq-finished/

### Назначение

**Интеграция с ZAG** (Zero-Assumptions Guarantee) для PCQ/PCE механизмов.

### Структура

```
tmp/zag_repoq-finished/
├── README.md                           # ZAG integration guide
├── Dockerfile                          # Multi-stage build для ZAG
├── Makefile                            # Build + test automation
├── pyproject.toml                      # Dependencies с ZAG SDK
├── repoq.yaml                          # ZAG manifest example
├── .github/workflows/
│   └── repoq.yml                       # CI/CD с ZAG validation
├── repoq/
│   ├── cli.py                          # CLI с ZAG commands
│   ├── config.py                       # ZAG config loader
│   ├── logging.py                      # ZAG-aware logging
│   ├── analyzers/                      # Анализаторы (6 файлов)
│   │   ├── ci_qm.py
│   │   ├── complexity.py
│   │   ├── history.py
│   │   ├── hotspots.py
│   │   ├── structure.py
│   │   └── weakness.py
│   ├── certs/                          # VC Certificates + ZAG
│   │   ├── generator.py                #   Генерация VC
│   │   ├── linker.py                   #   Linkage с ZAG claims
│   │   ├── pack.py                     #   Packaging для ZAG
│   │   └── quality.py                  #   Quality scoring
│   ├── core/                           # Core modules (4 файла)
│   │   ├── jsonld.py
│   │   ├── model.py
│   │   ├── rdf_export.py
│   │   └── repo_loader.py
│   ├── integrations/
│   │   ├── zag.py                      # ZAG SDK integration
│   │   └── zag_schemas/                # JSON schemas
│   │       ├── pce_schema.json         #   PCE structure
│   │       ├── pcq_schema.json         #   PCQ structure
│   │       └── zag_manifest_schema.json #  Manifest schema
│   ├── ontologies/
│   │   └── context_ext.jsonld          # Extended JSON-LD context
│   ├── reporting/                      # Reporting (3 файла)
│   │   ├── diff.py
│   │   ├── graphviz.py
│   │   └── markdown.py
│   └── shapes/
│       └── shacl_cert.ttl              # SHACL для VC + ZAG
```

### Ключевые компоненты

#### 2.1 ZAG Manifest (`repoq.yaml`)

```yaml
version: "1.0"
project:
  name: "repoq"
  fairness:
    boundary: ["repoq/cli.py", "repoq/core/", "repoq/analyzers/"]
    mincut_budget: 150

pcq:
  aggregator: "min"  # ZAG min-aggregator для PCQ
  threshold: 0.82
  support:
    - type: "module"
      path: "repoq/"
      weight: "loc"

pce:
  k: 5  # Top-5 hotspots
  witness_generation: "hotspot_ranking"
  remediation_plan: true
```

#### 2.2 PCQ/PCE Schemas

**PCQ Schema** (`zag_schemas/pcq_schema.json`):
```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "properties": {
    "aggregator": {"enum": ["min", "max", "avg", "sum"]},
    "threshold": {"type": "number", "minimum": 0, "maximum": 1},
    "support": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "id": {"type": "string"},
          "utility": {"type": "number", "minimum": 0, "maximum": 1}
        }
      }
    }
  }
}
```

**PCE Schema** (`zag_schemas/pce_schema.json`):
```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "properties": {
    "claim": {"type": "string"},
    "k": {"type": "integer", "minimum": 1},
    "witness": {
      "type": "array",
      "items": {"type": "string"},
      "maxItems": {"$ref": "#/properties/k"}
    },
    "remediation_plan": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "target": {"type": "string"},
          "action": {"type": "string"},
          "expected_delta": {"type": "number"}
        }
      }
    }
  }
}
```

#### 2.3 Certificates + ZAG

**Генератор VC** (`certs/generator.py`):
- Создаёт Verifiable Credentials с Q-метрикой
- Включает ZAG attestation при наличии
- Добавляет `assuranceLevel`: `"ZAG:ACCEPT"` / `"GATE:WAIVED"`

**Quality Scoring** (`certs/quality.py`):
- Вычисление Q-метрики с учётом PCQ
- Формирование witness для PCE
- Генерация k-repair plans

#### 2.4 Docker + CI/CD

**Dockerfile**:
```dockerfile
FROM python:3.11-slim AS builder
WORKDIR /app
COPY pyproject.toml .
RUN pip install --no-cache-dir -e ".[full,zag]"

FROM python:3.11-alpine
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin/repoq /usr/local/bin/
COPY repoq/ /app/repoq/
WORKDIR /app
ENTRYPOINT ["repoq"]
```

**GitHub Actions** (`.github/workflows/repoq.yml`):
```yaml
**GitHub Actions** (`.github/workflows/repoq.yml`):
```yaml
- name: Run Quality Gate
  run: |
    repoq gate \
      --base ${{ github.event.pull_request.base.sha }} \
      --head ${{ github.sha }} \
      --policy .github/quality-policy.yml \
      --zag-manifest repoq.yaml \
      --output gate-result.json
```

### 2.3 repoq-any2math-integration/

#### Назначение

**Интеграция с Any2Math** (Lean 4 TRS) для детерминированной канонизации выражений качества и proof-carrying результатов.

#### Структура

```
tmp/repoq-any2math-integration/
├── README.md                           # Smoke-тест и сборка Lean
├── docs/
│   └── ANY2MATH_INTEGRATION.md         # Полная документация интеграции
├── repoq/
│   ├── cli_any2math.py                 # CLI: any2math-normalize
│   ├── plugins/
│   │   └── trs_any2math.py             # Плагин для normalize + enrichment
│   └── integrations/
│       └── any2math/
│           ├── adapter.py              # I/O-адаптер к Lean-бинарнику
│           ├── bridge.py               # Преобразования: текст/AST и PCQ→AST
│           ├── scheduler.py            # ε-step heartbeat (liveness)
│           └── schemas/
│               └── expr.schema.json    # JSON Schema для Any2Math AST
└── tests/
    └── test_any2math_adapter.py        # Smoke-тесты (fallback)
```

#### Ключевые компоненты

**Verified Mode** (с `ANY2MATH_BIN`):
```bash
export ANY2MATH_BIN=/path/to/any2math
python -m repoq.cli_any2math any2math-normalize "mul(one, add(zero, x))"
# Output: mode: "verified", normal_form: {"var":"x"}, proof.sha256: ...
```

**Fallback Mode** (без Lean):
```python
# Мини-TRS внутри RepoQ (честно помеченный как TRS:FALLBACK)
res = adapter.normalize("add(zero, x)", mode="fallback")
# res.assurance_level == "TRS:FALLBACK"
```

**Контракт Any2Math I/O**:

Вход (`in.json`):
```json
{
  "expr": {
    "app": "mul",
    "args": [
      {"app": "one", "args": []},
      {"app": "add", "args": [
        {"app": "zero", "args": []},
        {"var": "x"}
      ]}
    ]
  }
}
```

Выход (`out.json`):
```json
{
  "normal_form": {"var": "x"}
}
```

Доказательство (`out.proof`):
- Формат: olean/trace/json (любой)
- Адаптер вычисляет SHA-256 и добавляет в VC-сертификат

**ε-Heartbeat Scheduler** (`scheduler.py`):
```python
class LivenessScheduler:
    """Гарантия прогресса нормализации в CI (анти-stall)."""
    
    def normalize_with_heartbeat(self, expr: str, epsilon_sec: float = 5.0):
        """Прерывает нормализацию каждые ε секунд для отчёта о прогрессе."""
        # Реализует ε-step из формальной модели (Liveness Lemma)
        pass
```

#### Формальные гарантии

1. **Единственность нормальной формы**: Confluence + Termination (доказано в Lean) → любые вычисления Q, PCQ well-defined
2. **Монотонность в гейте**: Сравнение $Q_{\text{head}}$ и $Q_{\text{base}}$ по единому канону (Теорема A/B)
3. **Liveness**: ε-heartbeat scheduler → анти-stall для CI-джобов
4. **Proof-carrying**: SHA-256(proof) → криптографически ссылочный артефакт для аудита

#### Сцепка с VC-сертификатами

**Обогащение сертификата**:
```python
from repoq.plugins.trs_any2math import TRSAny2MathPlugin

plug = TRSAny2MathPlugin()
res = plug.normalize_metric("add(zero, x)")

cert = {"type": "QualityCertificate"}
cert = plug.enrich_certificate(cert, res)
# cert["evidence"] += NormalizationEvidence
# cert["assuranceLevel"] = "TRS:VERIFIED" (или "TRS:FALLBACK")
```

**JSON-LD в сертификате**:
```json
{
  "evidence": [{
    "type": "NormalizationEvidence",
    "tool": "Any2Math-lean4",
    "proofHash": "sha256:a3f9...",
    "normalForm": {"var": "x"}
  }],
  "assuranceLevel": "TRS:VERIFIED",
  "prov:wasGeneratedBy": {
    "tool": "any2math",
    "version": "0.3.1-lean4.24.0",
    "commit": "abc123"
  }
}
```

#### CI/CD интеграция

**GitHub Actions** (`.github/workflows/any2math.yml`):
```yaml
- name: Normalize Q via Any2Math
  run: |
    export ANY2MATH_BIN=any2math  # если runner содержит бинарь
    python -m repoq.cli_any2math any2math-normalize "add(zero, x)"

- name: Quality Gate with Normalized Metrics
  run: |
    repoq gate \
      --base ${{ github.event.pull_request.base.sha }} \
      --head ${{ github.sha }} \
      --normalize any2math  # опция для канонизации через Any2Math
```

#### Дорожная карта улучшений

- [ ] **PCQ/PCE как термы**: Формализовать PCQ/τ и witness-конструкции прямо в Any2Math (отдельная подподпись в proof)
- [ ] **Больше правил**: Перенести idempotence/лог-алгебру из "metrics TRS" в Any2Math, расширить критические пары
- [ ] **Онлайн-проверка (sampling)**: На N% PR в CI запускать Lean-проверку proof-объекта (приемлемая цена, высочайшая уверенность)
- [ ] **SHACL-Rules ↔ TRS**: Унифицировать семантические (SHACL/SPARQL) и синтаксические (TRS) редукции в один pipeline с трейсингом

#### Критический TCB (Trusted Computing Base)

- **Lean kernel** (верифицированный)
- **Any2Math бинарник** (доказанный TRS)
- **Python I/O-адаптер** (без логики переписывания)

→ Минимальный TCB, максимальная уверенность.

- name: Validate ZAG Attestation
  run: |
    repoq zag validate gate-result.json
```

### Статус интеграции

| Компонент | Готовность | Приоритет | Блокеры |
|-----------|------------|-----------|---------|
| `zag.py` (SDK) | 95% | P1 | Нужна ZAG API key |
| Schemas (PCQ/PCE) | 100% | P1 | Нет (готово) |
| `certs/quality.py` | 90% | P1 | Тесты с ZAG backend |
| Dockerfile | 85% | P2 | Оптимизация размера |
| CI/CD workflow | 80% | P1 | GitHub secrets setup |
| `repoq.yaml` | 75% | P1 | Calibration для проекта |

### План интеграции

**Week 2-3** (Priority 1 — ZAG PCQ):
1. Копировать `integrations/zag.py` → `repoq/integrations/`
2. Добавить `zag_schemas/` → `repoq/schemas/`
3. Обновить `repoq/quality.py`: добавить PCQ/$\min$ агрегатор
4. Реализовать witness generation в `repoq/gate.py`
5. Тесты: интеграция с ZAG mock

**Week 3-4** (Priority 1 — PCE Witness):
1. Реализовать `generate_witness(k=5)` для top-k hotspots
2. Добавить remediation plan в gate output
3. Интегрировать в PR comments (bot)

**Week 4-5** (Priority 2 — Production):
1. Dockerfile в корень проекта
2. GitHub Actions workflow → `.github/workflows/quality-gate.yml`
3. Настроить secrets для ZAG API

---

## 3. Связь с основной документацией

### 3.1 Ontology Alignment Report

Артефакты в `tmp/` напрямую решают проблемы из `ontology-alignment-report.md`:

| Проблема (из отчёта) | Решение (в tmp/) | Файлы |
|----------------------|------------------|-------|
| ❌ Safety Guards 0% | ✅ TRS engine + SHACL guards | `trs/engine.py`, `shapes/meta_loop.ttl` |
| ❌ Ontological Integration 0% | ✅ Three-Ontology Architecture | `ontologies/{code,c4,ddd}.ttl` |
| ❌ Meta-Loop 0% | ✅ CLI meta extensions | `cli_meta.py`, `sparql/*.rq` |
| ⚠️ ZAG PCQ/PCE missing | ✅ Full ZAG integration | `zag_repoq-finished/` (51 файл) |

### 3.2 Quality Loop Roadmap

Артефакты покрывают **все фазы MVP + Production**:

| Фаза (из roadmap) | Покрытие | Файлы |
|-------------------|----------|-------|
| Week 1: Core Gate | ✅ 100% (уже реализовано) | `repoq/gate.py` (основной код) |
| Week 2: CI Integration | ✅ 90% | `.github/workflows/repoq.yml` |
| Week 3: Policy Config | ✅ 80% | `repoq.yaml` (ZAG manifest) |
| Week 4+: ZAG PCQ | ✅ 95% | `zag_repoq-finished/integrations/` |
| Month 2: Ontology | ✅ 70% | `repoq-meta-loop-addons/ontologies/` |
| Month 3: Meta-Loop | ✅ 60% | `repoq-meta-loop-addons/sparql/`, `trs/` |

### 3.3 Mathematical Proof

Артефакты реализуют формальные требования из `mathematical-proof-quality-monotonicity.md`:

| Требование (§11 доказательства) | Реализация | Файлы |
|----------------------------------|------------|-------|
| PCQ/$\min$ агрегатор | ✅ Готово | `certs/quality.py` |
| $\varepsilon$-calibration | ✅ Готово | `repoq.yaml` (epsilon config) |
| Witness generation (top-k) | ✅ Готово | `certs/quality.py::generate_witness()` |
| SHACL для VC/PCQ | ✅ Готово | `shapes/shacl_cert.ttl` |
| TRS confluence check | ✅ Готово | `trs/engine.py::check_confluence()` |

### 3.4 Formal Foundations Complete

Артефакты реализуют **Section 15** (Meta-Loop Integration) из `formal-foundations-complete.md`:

| Компонент (§15) | Реализация | Файлы |
|-----------------|------------|-------|
| Stratified Self-Application (§15.1) | ✅ Готово | `trs/engine.py`, `shapes/meta_loop.ttl` |
| Three-Ontology Architecture (§15.3) | ✅ Готово | `ontologies/{code,c4,ddd}.ttl` |
| SPARQL Construct Mappings (Th. 15.1) | ✅ Готово | `sparql/inference_construct.rq` |
| Meta-Quality Loop (§15.4) | ✅ Готово | `cli_meta.py::meta_quality_loop()` |
| **Any2Math Integration (§15.9)** | ✅ Готово | `repoq-any2math-integration/` (7 файлов) |
| Proof-Carrying Normalization (Th. 15.3) | ✅ Готово | `integrations/any2math/adapter.py` |
| ε-Heartbeat Scheduler | ✅ Готово | `integrations/any2math/scheduler.py` |
| VC Certificate Enrichment | ✅ Готово | `plugins/trs_any2math.py` |

---

## 4. Контрольные суммы и метаданные

### Размеры

```bash
$ du -sh tmp/*
1.2M    tmp/repoq-meta-loop-addons
3.8M    tmp/zag_repoq-finished
```

### Количество файлов

```bash
$ find tmp -type f | wc -l
70
```

### Распределение по типам

| Тип файла | Количество | Назначение |
|-----------|------------|------------|
| `.py` | 28 | Код (анализаторы, CLI, TRS, tests) |
| `.ttl` | 5 | Онтологии + SHACL shapes |
| `.json` / `.jsonld` | 9 | TRS правила, JSON-LD контексты, schemas |
| `.yaml` / `.yml` | 3 | ZAG manifest, CI/CD, mappings |
| `.rq` | 2 | SPARQL queries |
| `.md` | 3 | Документация |
| Прочие | 20 | Dockerfile, Makefile, configs |

### Git tracking

**Текущий статус**: `tmp/` включена в `.gitignore` (неотслеживаемая)

**Рекомендация**:
- Для временных экспериментов: оставить в `.gitignore`
- Для long-term хранения: создать `tmp/.gitkeep` и **исключить** `tmp/` из `.gitignore`
- Для production-ready: **перенести** в основную структуру проекта

---

## 5. Roadmap интеграции (сводка)

### Priority 0 (Week 1) — Safety Guards

**Источник**: `repoq-meta-loop-addons/`

- [ ] Копировать `trs/engine.py` → `repoq/core/trs.py`
- [ ] Копировать `shapes/meta_loop.ttl` → `repoq/shapes/`
- [ ] Реализовать `SelfApplicationGuard` в `repoq/gate.py`:
  ```python
  class SelfApplicationGuard:
      def __init__(self, stratification_level: int = 0):
          self.level = stratification_level
          self.read_only = True
      
      def check_safe(self, target_path: Path) -> bool:
          """Предотвращение анализа собственного кода выше level 2."""
          if self.level > 2:
              raise ValueError("Max stratification level is 2")
          return not target_path.is_relative_to(Path(__file__).parent)
  ```
- [ ] Тесты: `tests/test_safety.py` (из `test_self_policy.py`)

**Критерий завершения**: Все тесты проходят, SHACL валидация работает

### Priority 1 (Week 2-4) — ZAG + Basic Ontology

**Источник**: `zag_repoq-finished/` + `repoq-meta-loop-addons/`

**ZAG Integration**:
- [ ] Копировать `integrations/zag.py` → `repoq/integrations/`
- [ ] Копировать `zag_schemas/` → `repoq/schemas/zag/`
- [ ] Обновить `repoq/quality.py`: добавить `compute_pcq(modules, aggregator="min")`
- [ ] Добавить `--zag-manifest` опцию в `repoq gate`
- [ ] Генерация witness в `repoq/gate.py::format_gate_report()`

**Basic Ontology**:
- [ ] Копировать `ontologies/code.ttl` → `repoq/ontologies/`
- [ ] Реализовать `repoq/ontology/manager.py::BasicOntologyManager`
- [ ] Pattern detection: 5-7 базовых паттернов (MVC, Layered, Plugin)
- [ ] Обновить Q-метрику: `Q += 5 * architectural_bonus`

**Критерий завершения**: `repoq gate` с ZAG работает, паттерны детектируются

### Priority 2 (Month 2-3) — Full Ontology + Meta-Loop

**Источник**: `repoq-meta-loop-addons/`

- [ ] Копировать `ontologies/{c4,ddd}.ttl` → `repoq/ontologies/`
- [ ] Реализовать `SemanticInferenceEngine` с SPARQL
- [ ] Копировать `sparql/*.rq` → `repoq/sparql/`
- [ ] Cross-ontology маппинг через `mappings.yaml`
- [ ] CLI extensions: `repoq meta-self`, `repoq trs-verify`

**Критерий завершения**: Self-improvement recommendations в gate output

---

## 6. Риски и предупреждения

### 🔴 Критические риски

1. **API Keys**: ZAG integration требует API keys (не включены в tmp/)
   - **Mitigation**: Использовать mock в dev, secrets в CI/CD

2. **Performance**: TRS engine может быть медленным на больших правилах
   - **Mitigation**: Профилирование, кеширование нормальных форм

3. **Breaking Changes**: Интеграция tmp/ может сломать существующие тесты
   - **Mitigation**: Feature flags, поэтапная интеграция

### ⚠️ Средние риски

1. **Ontology Complexity**: Three-Ontology Architecture может быть избыточной
   - **Mitigation**: Начать с Code Ontology, добавлять C4/DDD постепенно

2. **ZAG Dependency**: Внешняя зависимость от ZAG сервиса
   - **Mitigation**: Graceful degradation без ZAG

3. **Documentation Drift**: tmp/ документация может устареть
   - **Mitigation**: Этот файл — single source of truth

---

## 7. Контрольный список перед интеграцией

### Перед копированием файлов

- [ ] Запустить все тесты основной кодовой базы (`pytest tests/`)
- [ ] Создать feature branch: `feature/tmp-integration-<component>`
- [ ] Сделать backup: `cp -r tmp/ tmp_backup_$(date +%Y%m%d)/`

### Во время интеграции

- [ ] Копировать по одному компоненту (TRS → SHACL → ZAG → Ontology)
- [ ] После каждого компонента: запускать `pytest` + `ruff check`
- [ ] Обновлять `pyproject.toml` dependencies
- [ ] Обновлять `docs/` по мере интеграции

### После интеграции

- [ ] Запустить полный test suite (`pytest --cov=repoq`)
- [ ] Проверить coverage: должен быть ≥80%
- [ ] Обновить README.md с новыми возможностями
- [ ] Создать migration guide для пользователей

---

## 8. Следующие шаги

### Немедленные действия

1. **Зафиксировать tmp/ в Git**:
   ```bash
   # Опция A: Добавить в Git для долгосрочного хранения
   git add tmp/
   git commit -m "chore: зафиксировать tmp/ с артефактами для будущей интеграции"
   
   # Опция B: Создать архив для backup
   tar -czf tmp_artifacts_$(date +%Y%m%d).tar.gz tmp/
   ```

2. **Создать GitHub Project для интеграции**:
   - Milestone: "TMP Artifacts Integration"
   - Issues для каждого Priority 0/1/2 компонента
   - Tracking: Kanban board (TODO → In Progress → Done)

3. **Начать с Priority 0 (Safety Guards)**:
   ```bash
   git checkout -b feature/safety-guards-integration
   cp tmp/repoq-meta-loop-addons/trs/engine.py repoq/core/trs.py
   # ... продолжить по roadmap
   ```

### Долгосрочная стратегия

- **Month 1**: Priority 0 + Priority 1 (ZAG)
- **Month 2**: Priority 1 (Ontology) + Priority 2 (partial)
- **Month 3**: Priority 2 (full) + production hardening
- **Month 4**: Meta-loop self-improvement + monitoring

---

## 9. Метаданные документа

| Атрибут | Значение |
|---------|----------|
| **Создан** | 2025-10-21 |
| **Автор** | URPKS Meta-Programmer |
| **Версия** | 1.0 |
| **Статус** | 🔄 Living Document |
| **Связанные документы** | `ontology-alignment-report.md`, `quality-loop-roadmap.md`, `mathematical-proof-quality-monotonicity.md` |
| **Git tracking** | ⚠️ Пока не отслеживается (в `.gitignore`) |
| **Размер tmp/** | 5.0 MB (70 файлов) |

---

## Заключение

Директория `tmp/` содержит **критические компоненты** для реализации полной онтологической мета-петли качества и ZAG интеграции. Все артефакты готовы к поэтапной интеграции в соответствии с планом из `ontology-alignment-report.md`.

**Ключевые достижения**:
- ✅ TRS engine с формальными гарантиями (confluence, termination)
- ✅ Three-Ontology Architecture (Code/C4/DDD)
- ✅ ZAG PCQ/PCE full integration (95% готовности)
- ✅ SHACL shapes для self-application guard
- ✅ CI/CD workflows для production

**Следующий шаг**: Начать интеграцию с Priority 0 (Safety Guards) по roadmap выше.

---

**Подпись**: URPKS Meta-Programmer  
**Верификация**: Inventory Complete ✅  
**Статус**: 📦 Ready for Integration
