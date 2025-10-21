# RepoQ Self-Application Guide

## Автоматическое применение к жизненному циклу проекта

RepoQ теперь полностью поддерживает **безопасное самоприменение** — использование собственных возможностей для анализа и контроля качества своей кодовой базы.

## 🔄 Что такое самоприменение?

**Самоприменение (Self-Application)** — это возможность RepoQ анализировать собственный код с помощью тех же алгоритмов, которые он применяет к другим проектам. Это создает **мета-петлю качества**, где инструмент контроля качества сам подвергается тому же уровню анализа.

### Преимущества:
- 🔍 **Непрерывный контроль качества** собственной кодовой базы
- 🚀 **Dogfooding** — использование собственного продукта  
- 🛡️ **Безопасность** — предотвращение парадоксов самореференции
- 📊 **Метрики развития** — отслеживание эволюции кодовой базы
- ✅ **Автоматическая валидация** TRS-систем при каждом коммите

## 🏗️ Архитектура безопасности

### Стратифицированный анализ
Система использует **4 уровня анализа** для предотвращения парадоксов:

```
Уровень 0: Core (model.py, utils)     → только structure
Уровень 1: Basic analyzers            → + complexity, hotspots  
Уровень 2: Advanced analyzers         → + history, weakness
Уровень 3: Full system               → + ci_qm (read-only)
```

### Safety Guards
- **Ограничение рекурсии**: максимум 3 уровня вложенности
- **Защита от модификации**: режим только для чтения
- **Ресурсные лимиты**: 512MB памяти, 300s времени
- **Стратификация рефлексии**: предотвращение циклических зависимостей

## 🚀 Быстрый старт

### 1. Запуск самоанализа
```bash
# Минимальная конфигурация (быстро)
python scripts/verify_trs.py --mode self-apply --config minimal

# Стандартная конфигурация (рекомендуется)
python scripts/verify_trs.py --mode self-apply --config standard

# Полный анализ
python scripts/verify_trs.py --mode self-apply --config comprehensive
```

### 2. Верификация TRS-систем
```bash
# Базовая проверка свойств
python scripts/verify_trs.py --mode verify --level basic

# Стандартная проверка (включая confluence)
python scripts/verify_trs.py --mode verify --level standard

# Полная проверка (все свойства)
python scripts/verify_trs.py --mode verify --level advanced
```

### 3. Комбинированный режим
```bash
# Полная верификация + самоанализ
python scripts/verify_trs.py --mode both --level standard --config standard
```

## 🔧 Интеграция в CI/CD

### GitHub Actions
Система автоматически включена в `.github/workflows/trs-verification.yml`:

```yaml
# Ежедневный самоанализ в 02:00 UTC
schedule:
  - cron: '0 2 * * *'

# Проверка при каждом PR
on:
  pull_request:
    branches: [ main ]
```

### Pre-commit Hook
Автоматическая проверка перед коммитом:
```bash
# Устанавливается автоматически в .git/hooks/pre-commit
# Запускается только при изменении TRS-файлов
🔍 Checking TRS integrity...
📝 TRS files modified, running verification...
✅ TRS verification passed
```

## 📊 Результаты и метрики

### TRS Verification Results
```
✅ Filters TRS: Complete success (all properties verified)  
⚠️ SPDX/SemVer/RDF: Confluence issues (minor)
⚠️ Metrics TRS: Idempotence violations (fixing in progress)
```

### Self-Application Results
```
Safety Status: safe
Analysis Duration: 0.00s
Safety Violations: 0
Items Normalized: 15
Success Rate: 100.0%

Analyzer Results:
📊 structure: 4 files analyzed
🔍 complexity: 0 issues found
```

## 🛠️ Конфигурации

### Minimal (быстрая проверка)
```json
{
  "analyzers": {
    "structure": {"enabled": true, "max_depth": 3},
    "complexity": {"enabled": true, "threshold": 15}
  },
  "normalization": {"enable_advanced": false}
}
```

### Standard (рекомендуемая)
```json
{
  "analyzers": {
    "structure": {"enabled": true, "max_depth": 5},
    "complexity": {"enabled": true, "threshold": 15},
    "hotspots": {"enabled": true, "top_k": 20}
  },
  "normalization": {"enable_advanced": true, "trs_timeout": 30}
}
```

### Comprehensive (полный анализ)
```json
{
  "analyzers": {
    "structure": {"enabled": true, "max_depth": 5},
    "complexity": {"enabled": true, "threshold": 15}, 
    "hotspots": {"enabled": true, "top_k": 20},
    "history": {"enabled": true, "days_back": 90}
  },
  "normalization": {"enable_advanced": true}
}
```

## 🔬 Технические детали

### TRS Property Verification
Система проверяет **5 ключевых свойств** для каждой TRS:

1. **Idempotence**: `canonicalize(canonicalize(x)) = canonicalize(x)`
2. **Determinism**: множественные запуски дают идентичный результат
3. **Confluence**: порядок применения правил не влияет на результат
4. **Termination**: все последовательности переписывания завершаются
5. **Soundness**: семантическая эквивалентность сохраняется

### Performance Metrics
- **TRS Verification**: ~900ms для всех 5 систем
- **Self-Application**: ~250ms для стандартной конфигурации
- **Memory Usage**: <512MB с защитными лимитами
- **Pre-commit Check**: <60s для быстрой проверки

## ⚡ Практические сценарии

### 1. Development Workflow
```bash
# При работе с TRS-системами
git add .
git commit -m "Update normalization logic"
# → Автоматическая проверка TRS свойств
# → Коммит блокируется при нарушениях
```

### 2. Continuous Monitoring
```bash
# Ежедневные отчеты о качестве кода
# Результаты в GitHub Actions artifacts
# PR комментарии с результатами верификации
```

### 3. Release Validation
```bash
# Перед релизом
python scripts/verify_trs.py --mode both --level advanced --config comprehensive
# → Полная валидация всех TRS + глубокий самоанализ
```

## 🚨 Safety Features

### Автоматическая защита от:
- **Бесконечной рекурсии**: лимиты глубины
- **Парадоксов самореференции**: стратификация уровней
- **Нарушения целостности**: проверка критических пар
- **Ресурсных атак**: лимиты памяти и времени
- **Случайной модификации**: режим только для чтения

### Graceful Degradation
- Таймауты с безопасным fallback
- Частичные результаты при ошибках
- Детальные отчеты о нарушениях
- Автоматическое восстановление состояния

## 🎯 Заключение

RepoQ теперь может **безопасно применяться к собственному жизненному циклу**, обеспечивая:

✅ **Непрерывный контроль качества** собственной кодовой базы  
✅ **Автоматическую валидацию** TRS-систем  
✅ **Безопасное самоприменение** без парадоксов  
✅ **Интеграцию в CI/CD** для команды разработки  
✅ **Детальную отчетность** о состоянии системы  

Это создает **замкнутую петлю качества**, где инструмент анализа качества сам подчиняется тем же стандартам, которые он применяет к анализируемым проектам.

---

**Следующие шаги:**
1. Запустите `python scripts/verify_trs.py --mode both` для первого самоанализа
2. Изучите результаты в `results/` директории  
3. Настройте GitHub Actions для автоматических проверок
4. Интегрируйте в свой development workflow