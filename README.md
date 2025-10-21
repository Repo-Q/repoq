# repoq — Repository Quality CLI (Final)

[![Production Readiness](https://img.shields.io/badge/production--ready-70%25-yellow)](INDEX.md)
[![Test Coverage](https://img.shields.io/badge/coverage-5%25-red)](https://github.com/yourorg/repoq-pro-final/actions)
[![URPKS Gates](https://img.shields.io/badge/gates-3%2F8%20passing-orange)](ROADMAP.md#phase-0-текущее-состояние-baseline)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

> 📚 **[См. INDEX.md для полной навигации по роадмапу](INDEX.md)** — executive summary, спринт-планы, формализация, визуализация

**repoq 2.0** — производственный CLI для реверс‑инжиниринга качества Git‑репозитория
с расширенной семантической онтологией (**PROV‑O, OSLC Core/CM/QM/Config, SPDX, FOAF, OKN/SDO**),
TTL‑экспортом, SHACL/ResourceShape‑валидацией, JUnit‑парсингом тестов и графами.

> ⚠️ **Status**: Phase 0 (70% ready) → [см. ROADMAP для production v3.0](ROADMAP.md)

## Установка

```bash
pip install -e .               # минимально
pip install -e ".[full]"       # все фичи (PyDriller/Lizard/Radon/Graphviz/RDF/SHACL)
```

## Примеры

```bash
# Полный анализ + графы + TTL + SHACL‑валидация
repoq full . -o quality.jsonld --md quality.md --graphs graphs/ --ttl quality.ttl --validate-shapes

# Только структура с checksums SHA-256
repoq structure https://github.com/org/repo -o quality.jsonld --hash sha256

# История за 6 месяцев, OSLC CM дефекты: fail при high
repoq full . --since "6 months ago" --fail-on-issues high -o quality.jsonld
```

### Флаги (избранное)
- `--since` | `--extensions` | `--exclude` | `--max-files`
- `--graphs DIR` — DOT (+SVG при наличии Graphviz)
- `--ttl FILE` — экспорт Turtle (RDF)
- `--validate-shapes` `--shapes-dir SHAPES` — валидация через pySHACL (и OSLC ResourceShapes)
- `--hash sha1|sha256` — вычислять SPDX контрольные суммы по файлам
- `--context-file` — добавить/переопределить JSON‑LD контекст
- `--field33-context` — подключить контекст Field33 (при наличии локально)
- `--fail-on-issues` — CI‑сигнал при high/medium/low

## Что генерируется
- **JSON‑LD**: проект, модули, файлы (`spdx:File`), авторы (`foaf:Person`), коммиты (`prov:Activity`),
  версии (`oslc_config:VersionResource`), ишью/горячие точки (`oslc_cm:ChangeRequest`/`Defect`),
  тесты (`oslc_qm:TestCase`/`TestResult`), зависимости и coupling‑ребра.
- **Markdown**: сводка (языки/авторы/hotspots/TODO).
- **Graphviz**: `dependencies.dot/svg`, `coupling.dot/svg`.
- **TTL**: результат в Turtle (для triple‑store).
- **SHACL отчёт** (если включена валидация).

## 📋 Documentation & Roadmap

### For Decision Makers
- **[� Executive Summary](EXECUTIVE_SUMMARY.md)** — production readiness assessment, ROI, approval request

### For Engineers
- **[🚀 Full Roadmap](ROADMAP.md)** — 4 phases, 7 months to v3.0 GA (with formal verification)
- **[✅ Phase 1 Checklist](PHASE1_CHECKLIST.md)** — actionable sprint plan (weeks 1-4)
- **[🧬 Ontology Formalization](ontologies/FORMALIZATION.md)** — OML/Lean4 specification

### Quick Start (Phase 1)
```bash
# Week 1: Setup testing infrastructure
pip install -e ".[full,dev]"
pytest --cov=repoq --cov-report=html
ruff check . --fix
mypy repoq/

# Self-hosting check
repoq full . -o artifacts/self.jsonld --validate-shapes
```

**Critical gaps** (blocking production):
1. 🔴 Test coverage <10% → need 80% (4 weeks)
2. 🔴 No formal ontology spec → need OML+Lean4 (6 weeks)
3. 🔴 No self-hosting CI → need GitHub Action (1 week)

**Timeline**: 7 months to production v3.0 | **Investment**: ~$150K | **ROI**: break-even in 3 years (SaaS)

**Contribute**: Pick a task from [PHASE1_CHECKLIST.md](PHASE1_CHECKLIST.md) and open a PR!

## Лицензия
MIT
