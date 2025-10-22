# ADR-014: Single Source of Truth — .repoq/ for all RDF artifacts

**Status**: Statusaccepted  
**Date**: 2025-01-15  

> **Generated from RDF**: This document is auto-generated from `.repoq/adr/{adr_id}.ttl`.
> Single Source of Truth: Edit RDF, regenerate Markdown.

## Проблема

В проекте существует несколько источников истины:
- docs/vdad/*.md — человеко-читаемая документация
- .repoq/ontologies/*.ttl — онтологии (meta)
- .repoq/vdad/*.ttl — извлечённые данные VDAD
- Возможное дублирование: docs/vdad/phase2-values.md + docs/vdad/phase2-values.ttl (sidecar)

Вопрос: Где хранить единственный источник истины (Single Source of Truth, SSoT)?

**Ограничения**:
- Разработчики привыкли к Markdown
- RDF сложнее редактировать вручную
- Риск рассинхронизации Markdown ↔ RDF

## Решение

.repoq/ — единственный источник истины для всех RDF-артефактов.

Workflow:
1. EDIT: .repoq/**/*.ttl (hand-edit RDF)
2. GENERATE: python scripts/generate_*.py
3. OUTPUT: docs/**/*.md (generated)
4. COMMIT: Both .ttl (source) and .md (generated)

Направление: RDF → Markdown (только одно направление!)

