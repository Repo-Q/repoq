# ADR-014: Single Source of Truth — `.repoq/` для всех RDF артефактов

**Status**: Accepted  
**Date**: 2025-01-15  
**Context**: Phase 5.6 (VDAD as RDF POC)

## Проблема

В проекте существует несколько источников истины:

- `docs/vdad/*.md` — человеко-читаемая документация
- `.repoq/ontologies/*.ttl` — онтологии (meta)
- `.repoq/vdad/*.ttl` — извлечённые данные VDAD
- Возможное дублирование: `docs/vdad/phase2-values.md` + `docs/vdad/phase2-values.ttl` (sidecar)

**Вопрос**: Где хранить единственный источник истины (Single Source of Truth, SSoT)?

## Решение

**Принцип**: `.repoq/` — единственный источник истины для всех RDF-артефактов.

### Структура

```text
.repoq/
  ontologies/
    vdad.ttl           # VDAD meta-ontology (SSoT)
    story.ttl          # Story ontology (SSoT)
  shapes/
    vdad-shapes.ttl    # SHACL shapes (SSoT)
  vdad/
    phase2-values.ttl  # Phase 2 Values RDF (SSoT)
    phase3-requirements.ttl
  story/
    phase1.ttl         # Phase 1 provenance (SSoT)
  raw/                 # Raw analysis data
  validated/           # SHACL-validated RDF
  reports/             # Generated reports
  certificates/        # Validation certificates
  cache/               # Incremental cache
  manifest.json        # Checksums + metadata

docs/
  vdad/
    phase2-values.md   # GENERATED from .repoq/vdad/phase2-values.ttl
    phase3-requirements.md  # GENERATED
```

### Правила

1. **Editing**: Изменения вносятся только в `.repoq/**/*.ttl`
2. **Generation**: `docs/**/*.md` генерируются из `.repoq/**/*.ttl`
3. **Versioning**: `.repoq/**/*.ttl` коммитятся в git (SSoT)
4. **Documentation**: `docs/**/*.md` могут быть в `.gitignore` (generated) или коммититься для удобства review
5. **Validation**: `scripts/validate_vdad.py` проверяет консистентность RDF ↔ Markdown (если Markdown коммитится)

## Последствия

### ✅ Pros

1. **Single Source of Truth**: Один источник истины для всех данных
2. **Reproducibility**: `manifest.json` содержит checksums всех `.repoq/**/*.ttl`
3. **Versioning**: RDF эволюционирует вместе с кодом
4. **Traceability**: Все артефакты трассируются через RDF
5. **SPARQL Queries**: Единая база данных для запросов
6. **Multi-format Export**: RDF → Markdown, HTML, PDF, LaTeX, диаграммы

### ⚠️ Cons

1. **Обучение**: Разработчики должны работать с RDF (но есть генераторы Markdown)
2. **Tooling**: Нужны скрипты для генерации Markdown из RDF
3. **Review**: Сложнее review RDF changes (но можно ревьюить generated Markdown)

### Миграция

**Phase 5.6 (POC)**: Phase 2 Values RDF → Markdown

- Extractor: `scripts/extract_vdad_rdf.py` (Markdown → RDF, временно)
- Generator: `scripts/generate_vdad_markdown.py` (RDF → Markdown)

**Phase 5.7 (Full VDAD)**: Все 5 фаз VDAD

- Phase 1: Domain → `.repoq/vdad/phase1-domain.ttl`
- Phase 2: Values → `.repoq/vdad/phase2-values.ttl` ✅
- Phase 3: Requirements → `.repoq/vdad/phase3-requirements.ttl`
- Phase 4: Architecture → `.repoq/vdad/phase4-architecture.ttl`
- Phase 5: Migration → `.repoq/vdad/phase5-migration.ttl`

**Phase 6 (Automation)**: CI/CD интеграция

- Pre-commit hook: Validate RDF, regenerate Markdown
- CI: Check RDF ↔ Markdown consistency
- Documentation site: Auto-generated from `.repoq/`

## Трассировка

- **FR-10**: Reproducible analysis (RDF checksums в manifest)
- **V07**: Observability (RDF как queryable база данных)
- **Theorem A**: Reproducibility (SSoT в `.repoq/`)
- **NFR-01**: Performance (генерация Markdown быстрая, <1s)

## Альтернативы

### Option A: Markdown as SSoT (отклонено)

- **Pros**: Привычно для разработчиков
- **Cons**: Сложно делать SPARQL queries, трассировку, валидацию

### Option B: Dual SSoT (Markdown + RDF sidecars) (отклонено)

- **Pros**: Удобно для review
- **Cons**: Риск рассинхронизации, дублирование

### Option C: RDF as SSoT (выбрано) ✅

- **Pros**: Single source, queries, validation, multi-format export
- **Cons**: Нужны генераторы Markdown

## Статус

**Accepted** — 2025-01-15

**Реализация**:

- Commit: `49d6909` (VDAD ontology + extractor)
- Tag: `v2.0.0-alpha.3`
- Скрипты:
  - `scripts/extract_vdad_rdf.py` (Markdown → RDF, временно для миграции)
  - `scripts/generate_vdad_markdown.py` (RDF → Markdown, основной workflow)

## Связанные ADR

- ADR-008: `.repoq/` workspace structure
- ADR-010: Ontology-driven validation
- ADR-013: Incremental migration strategy
