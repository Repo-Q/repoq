# 📚 REPOQ DOCUMENTATION INDEX

Добро пожаловать в документацию RepoQ v3.0 — революционной системы анализа качества кода с семантической метапетлей качества.

## 🎯 Начинаем работу

- **[README.md](README.md)** — основная информация и быстрый старт
- **[SELF_APPLICATION_GUIDE.md](SELF_APPLICATION_GUIDE.md)** — руководство по самоприменению

## 🚀 Революционные достижения

- **[BREAKTHROUGH_ACHIEVEMENTS.md](BREAKTHROUGH_ACHIEVEMENTS.md)** — исторические достижения семантической метапетли качества
- **[ONTOLOGY_ROADMAP.md](ONTOLOGY_ROADMAP.md)** — план развития онтологической интеллектуальной системы
- **[ROADMAP.md](ROADMAP.md)** — общая дорожная карта развития проекта

## 🧠 Техническая документация

### Архитектура и компоненты
```
repoq/
├── analyzers/          # Анализаторы качества кода
├── core/               # Основные модели и утилиты  
├── normalize/          # TRS системы нормализации
├── ontologies/         # Онтологическая интеллектуальная система
├── reporting/          # Генерация отчетов (JSON-LD, Markdown, Graphviz)
└── shapes/             # SHACL валидация схем
```

### TRS Verification Framework
```
rules/
├── trs_properties.py   # Абстрактная верификация свойств
├── trs_verifiers.py    # Конкретные TRS верификаторы
└── self_application_rules.py  # Безопасность самоприменения
```

### Self-Application Infrastructure  
```
scripts/
├── verify_trs.py       # Верификация TRS систем
├── self_application.py # Безопасное самоприменение
└── deploy_hooks.py     # GitHub Actions интеграция
```

## 🔬 Онтологическая система

### Формальные спецификации
- **[repoq/ontologies/plugins/code_ontology.jsonld](repoq/ontologies/plugins/code_ontology.jsonld)** — 150+ концептов структуры кода
- **[repoq/ontologies/plugins/c4_model.jsonld](repoq/ontologies/plugins/c4_model.jsonld)** — 50+ архитектурных элементов
- **[repoq/ontologies/plugins/ddd_ontology.jsonld](repoq/ontologies/plugins/ddd_ontology.jsonld)** — 40+ концептов предметно-ориентированного дизайна

### Cross-Ontology Intelligence
```json
{
  "semantic_mappings": {
    "code:Class": "c4:Component",
    "ddd:BoundedContext": "c4:Container", 
    "code:Service": "ddd:DomainService"
  },
  "automatic_inference": [
    "architectural_consistency",
    "domain_model_validation", 
    "pattern_recognition"
  ]
}
```

## ⚙️ CI/CD и автоматизация

### GitHub Actions Workflows
- **[.github/workflows/trs-verification.yml](.github/workflows/trs-verification.yml)** — автоматическая TRS верификация
- **Pre-commit hooks** — блокировка некорректных изменений TRS

### Self-Application Security
- **4-уровневая стратификация** анализа (0-3)
- **Resource limits** (512MB, 300s timeout)
- **Read-only enforcement** для предотвращения парадоксов

## 📊 Семантическая метапетля качества

### Революционные возможности
- **Формальное понимание собственной архитектуры** через онтологии
- **Автоматическое извлечение концептов** из кода  
- **Cross-domain semantic analysis** (Code ↔ Architecture ↔ Domain)
- **Self-improving quality insights** через мета-анализ

### Примеры использования
```python
# Онтологический анализ структуры проекта
from repoq.analyzers.structure import StructureAnalyzer
analyzer = StructureAnalyzer() 
project = analyzer.run(...)

# Извлеченные семантические концепты
concepts = project.ontological_analysis['concepts']
relationships = project.ontological_analysis['relationships'] 
violations = project.ontological_analysis['violations']
```

## 🔧 Разработка и вклад

### Установка зависимостей
```bash
pip install -e ".[full,dev]"  # Полная установка с онтологиями
```

### Запуск тестов
```bash
pytest tests/                 # Unit тесты
python scripts/verify_trs.py  # TRS верификация
python scripts/self_application.py  # Мета-анализ
```

### Архитектурные принципы
- **TRS-based normalization** для детерминированности
- **Plugin-based ontologies** для расширяемости
- **Stratified self-application** для безопасности
- **Semantic web compliance** (JSON-LD, OWL, SHACL)

## 🌟 Статус проекта

### ✅ Операциональные возможности
- Семантическая метапетля качества
- Онтологическая интеллектуальная система  
- Безопасное самоприменение
- TRS верификация (4/5 систем стабильны)

### ⚠️ В разработке
- TRS confluence optimization (Metrics focus)
- ML-based pattern recognition
- Extended domain ontologies
- Automated improvement suggestions

### 🚀 Видение
RepoQ представляет первую в мире **самопонимающую систему анализа качества**, которая:
- Понимает собственную архитектуру через формальные онтологии
- Предоставляет семантические инсайты качества на беспрецедентном уровне
- Создает фундамент для AI-assisted software development

---

*Последнее обновление: October 21, 2025*  
*Версия документации: 3.0.0*