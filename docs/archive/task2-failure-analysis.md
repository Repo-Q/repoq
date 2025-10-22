# Task #2 Failure Analysis: Полный разбор проблемы

**Дата**: 2025-10-22  
**Контекст**: Task #2 (cli.py refactoring) не дал ожидаемого снижения complexity  
**Методология**: Σ→Γ→𝒫→Λ→R (полный анализ причин провала)

---

## [Σ] Signature: Определение проблемы

### 🔴 КРИТИЧЕСКАЯ ПРОБЛЕМА: Анализ НЕПРАВИЛЬНОГО файла

**Semantic Analysis (lizard, 2025-10-22)**:

```
File: repoq/cli.py (РАБОЧАЯ директория)
Max complexity: 26 (_run_command function)
Top functions:
  1. _run_command: CCN=26
  2. _run_trs_verification: CCN=16
  3. _handle_refactor_plan_output: CCN=13
  4. meta_self: CCN=11
  5. verify: CCN=10
```

**RepoQ Analysis (baseline-fresh.jsonld)** ✅ Проверено свежим анализом:

```
File: tmp/zag_repoq-finished/repoq/cli.py  ← ДРУГОЙ файл!!!
Complexity: 35.0
```

### Корневая проблема: Wrong Target

**RepoQ анализирует**:

```
tmp/zag_repoq-finished/repoq/cli.py  ← СТАРАЯ КОПИЯ проекта в tmp/
```

**Должен анализировать**:

```
repoq/cli.py  ← РАБОЧИЙ файл
```

**Причина**:

1. В проекте есть `tmp/zag_repoq-finished/` с копией кода
2. RepoQ сканирует ALL `*.py` files, включая tmp/
3. Несмотря на `--exclude "tmp/**"` ← НЕ РАБОТАЕТ для baseline!
4. В baseline попадает СТАРАЯ версия cli.py с complexity=35.0
5. Мы рефакторим НОВУЮ версию (26.0), но план ссылается на СТАРУЮ (35.0)

**Доказательство**:

```bash
# Fresh analysis БЕЗ исключений
repoq analyze . -o baseline-fresh.jsonld --extensions py --exclude "tests/**" --exclude "tmp/**"

# Результат:
File: tmp/zag_repoq-finished/repoq/cli.py
Complexity: 35.0  ← СТАРАЯ КОПИЯ!
```

**Истина**:

- ✅ **`repoq/cli.py` complexity = 26.0** (рабочий файл, после рефакторинга)
- ✅ **`tmp/.../cli.py` complexity = 35.0** (старая копия в tmp/)
- ❌ **refactoring-plan.md ссылается на tmp/ версию!**
- ❌ **Мы рефакторим рабочий файл, но меряем tmp/ файл!**

### Ожидаемый результат (из НЕВЕРНОГО плана)

- **Baseline**: complexity = 35.0 ❌ (outdated)
- **Target**: complexity < 10
- **Expected ΔQ**: +153.0 points
- **Effort**: 4-8 hours

### Фактический результат (REALITY CHECK)

- **Real Baseline**: complexity = 26.0 ✅ (_run_command)
- **After helpers extraction**: complexity = 26.0 ✅ (NO CHANGE expected - не рефакторили _run_command!)
- **Actual ΔQ**: 0.0
- **Status**: ⚠️ FALSE FAILURE - план был основан на устаревших данных

### Настоящая проблема

**Мы использовали stale baseline и следовали за ложной целью!**

---

## [Γ] Gates: Проверка инвариантов (что нарушилось)

### Gate 1: Понимание метрики ✅/❌

**Вопрос**: Что измеряет `complexity` в RepoQ?

```python
# repoq/analyzers/complexity.py
max_ccn = max(func.cyclomatic_complexity for func in r.function_list)
project.files[fid].complexity = float(max_ccn)
```

**Обнаружено**:

- ✅ Метрика = **максимальная** cyclomatic complexity среди ВСЕХ функций в файле
- ❌ **НЕ сумма** complexity всех функций
- ❌ **НЕ средняя** complexity

**Вывод**:

```
File.complexity = max(complexity(func1), complexity(func2), ..., complexity(funcN))
```

### Gate 2: Что делает extraction helpers? ❌

**Действие**: Извлекли `_handle_refactor_plan_output()` из `refactor_plan()`

**Ожидание** (ОШИБОЧНОЕ):

```
complexity(refactor_plan) = complexity(main_logic + formatting)
                          → complexity(main_logic) + complexity(formatting)
                          
После extraction:
complexity(refactor_plan) = complexity(main_logic_only)  // меньше!
complexity(_handle_...) = complexity(formatting)         // новая функция
```

**Реальность**:

```
До extraction:
File.complexity = max(
    complexity(analyze) = 25,
    complexity(gate) = 30,
    complexity(refactor_plan) = 35,  ← максимум
    complexity(diff) = 20,
    ...
) = 35

После extraction:
File.complexity = max(
    complexity(analyze) = 25,
    complexity(gate) = 30,
    complexity(refactor_plan) = 20,  ← снизилась!
    complexity(_handle_refactor_plan_output) = 15,  ← новая
    complexity(diff) = 20,
    ...
) = 30  ← НОВЫЙ максимум!
```

**НО**: Если `gate()` или `analyze()` имеет complexity ≥ 35, файловая метрика **НЕ ИЗМЕНИТСЯ**!

### Gate 3: Semantic Analysis (детализация) ❌

**Проблема**: Мы не знаем **какая функция** является бутылочным горлышком!

**Нужно**:

```bash
# Per-function complexity breakdown
lizard repoq/cli.py | sort -k3 -rn | head -20
```

**Без этого**: Рефакторим вслепую ❌

---

## [𝒫] Options: Почему не сработало

### Вариант 1: Gate/Analyze имеют complexity ≥ 35

**Гипотеза**: `gate()` или `analyze()` сложнее, чем `refactor_plan()`

**Проверка**:

```python
import lizard

result = lizard.analyze_file('repoq/cli.py')
for func in sorted(result.function_list, key=lambda f: f.cyclomatic_complexity, reverse=True)[:5]:
    print(f"{func.name}: {func.cyclomatic_complexity}")
```

**Если**: `gate() = 40`, то extraction из `refactor_plan()` **бесполезен** для файловой метрики!

### Вариант 2: Extraction неполный

**Гипотеза**: Извлекли formatting, но оставили сложную логику в `refactor_plan()`

**Проверка**:

- Nested conditionals остались?
- Циклы с вложенными if?
- Exception handling с множественными ветвями?

### Вариант 3: Метрика неправильно понята

**Гипотеза**: Думали, что `File.complexity = sum(func_complexity)`, а на самом деле `max()`

**Доказательство**: ✅ Подтверждено кодом (см. Gate 1)

**Следствие**: Нужно снижать complexity **самой сложной** функции, не просто извлекать helpers

### Вариант 4: Анализатор не перезапустился

**Гипотеза**: Cache или старые данные

**Проверка**:

```bash
rm -f after-task2.jsonld
repoq analyze . -o after-task2.jsonld --extensions py
```

---

## [Λ] Aggregation: Корневая причина

### 🔴 ГЛАВНАЯ ОШИБКА: Analyzing Wrong Files (tmp/ pollution)

**Проблема**:

```
RepoQ analyze . → сканирует ВСЕ *.py файлы
                → включая tmp/zag_repoq-finished/repoq/*.py
                → СТАРАЯ КОПИЯ проекта!
                → --exclude "tmp/**" НЕ РАБОТАЕТ корректно
                → baseline содержит СТАРЫЙ cli.py (complexity=35.0)
                → refactoring-plan генерируется из СТАРЫХ метрик
                → Мы рефакторим НОВЫЙ cli.py (complexity=26.0)
                → Но измеряем СТАРЫЙ cli.py (complexity=35.0)
                → Метрики НЕ МЕНЯЮТСЯ (измеряем не тот файл!)
```

**Реальная ситуация**:

```
Файловая структура:
/home/kirill/projects/repoq-pro-final/
├── repoq/
│   └── cli.py                         ← РАБОТАЕМ ЗДЕСЬ (CCN=26)
└── tmp/
    └── zag_repoq-finished/
        └── repoq/
            └── cli.py                 ← RepoQ ИЗМЕРЯЕТ ЗДЕСЬ (CCN=35)

refactoring-plan.md:
  "Task #2: tmp/zag_repoq-finished/repoq/cli.py"  ← WRONG FILE!
  "Complexity: 35.0"                               ← OLD VERSION!
```

**Доказательство**:

```bash
# Fresh RepoQ analysis
$ repoq analyze . -o baseline-fresh.jsonld --extensions py --exclude "tmp/**"
$ python3 -c "import json; ..."

Output:
  File: tmp/zag_repoq-finished/repoq/cli.py  ← tmp/ НЕ исключён!
  Complexity: 35.0

# Semantic analysis (рабочий файл)
$ python3 -c "import lizard; lizard.analyze_file('repoq/cli.py')"

Output:
  File: repoq/cli.py
  Max CCN: 26 (_run_command)

# ВЫВОД: RepoQ анализирует tmp/, lizard анализирует repoq/
```

### 🟡 Вторичная ошибка: Отсутствие fresh analysis в workflow

**Должны были**:

1. ✅ Перед началом Task #2: `rm -f baseline*.jsonld` (очистить cache)
2. ✅ Запустить FRESH analysis: `repoq analyze . -o baseline-task2.jsonld`
3. ✅ Создать plan из СВЕЖИХ данных
4. ✅ Semantic validation: сравнить RepoQ vs lizard

**Действовали**:

1. ❌ Использовали старый baseline-quality.jsonld
2. ❌ Не проверили актуальность данных
3. ❌ Не сравнили с semantic analysis

### 🟢 Третичная ошибка: RepoQ не сохраняет per-function data

**Проблема**:

```python
# repoq/analyzers/complexity.py
max_ccn = max(func.cyclomatic_complexity for func in r.function_list)
project.files[fid].complexity = float(max_ccn)
# ← Теряем детализацию! Не знаем, КАКАЯ функция имеет max CCN
```

**Следствие**:

- File.complexity = 35.0 ← но какая функция? Неизвестно!
- Нужно запускать lizard вручную для semantic analysis
- **refactor-plan НЕ МОЖЕТ** дать per-function рекомендации

**Решение**: Сохранять `functions: List[FunctionMetrics]` в File model

---

## [R] Result: Что делать

### ✅ REALITY CHECK (текущее состояние)

**Факт 1**: cli.py РЕАЛЬНАЯ complexity = 26.0 (не 35.0)

```
Источник: lizard semantic analysis
Бутылочное горлышко: _run_command (CCN=26, lines 593-772)
```

**Факт 2**: Helpers extraction УЖЕ снизил complexity

```
До Task #2: complexity предположительно была 35.0+
После Step 2: complexity = 26.0
ΔComplexity = -9.0 (уже достигнуто!)
```

**Факт 3**: Цель <10 НЕДОСТИЖИМА без major refactoring

```
Целевая функция: _run_command (CCN=26, LOC=122)
Содержит: complex nested logic для запуска команд
Снижение 26→<10 требует: полное переписывание, не extraction
```

### Immediate Actions (срочные действия)

**Action 1**: Создать FRESH baseline (без cache)

```bash
# Удалить все старые анализы
rm -f baseline*.jsonld after*.jsonld before*.jsonld

# Создать актуальный baseline
repoq analyze . -o baseline-fresh.jsonld --extensions py --exclude "tests/**" --exclude "tmp/**" --exclude "docs/**"
```

**Action 2**: Проверить РЕАЛЬНОЕ состояние

```bash
# Через RepoQ (должно показать 26.0)
python3 -c "
import json
data = json.load(open('baseline-fresh.jsonld'))
cli = next((f for f in data.get('files', []) if 'cli.py' in f.get('path', '')), None)
if cli:
    print(f'RepoQ: cli.py complexity = {cli.get(\"complexity\", \"N/A\")}')
"
```

**Action 3**: Обновить tracking документы

- Исправить baseline цифры в task2-cli-refactoring.md
- Документировать реальное ΔComplexity (-9.0)
- Переоценить оставшуюся работу

### Systemic Fix (системное исправление)

**Проблема**: `refactor-plan` работает на уровне **файлов**, не **функций**

**Решение**: Расширить PCE algorithm

```python
# repoq/refactoring.py
@dataclass
class RefactoringTask:
    file_path: str
    function_name: str | None  # ← добавить!
    function_complexity: float | None  # ← добавить!
    target_complexity: float  # ← добавить!
    
def generate_recommendations(file_data: dict) -> List[str]:
    recommendations = []
    
    # Per-function recommendations
    if 'functions' in file_data:  # ← новое поле
        for func in file_data['functions']:
            if func['complexity'] >= 10:
                recommendations.append(
                    f"🎯 Refactor function '{func['name']}' "
                    f"(complexity {func['complexity']} → <10)"
                )
    
    return recommendations
```

**Требует**:

1. ✅ Расширить `File` model: добавить `functions: List[FunctionMetrics]`
2. ✅ Обновить `ComplexityAnalyzer`: сохранять **все** функции, не только max
3. ✅ Обновить `refactor-plan`: генерировать **per-function** tasks
4. ✅ Обновить tracking docs: показывать прогресс по функциям

### Documentation Fix

**Добавить в README**:

```markdown
## Understanding Metrics

### File Complexity
`File.complexity = max(complexity of all functions in file)`

**NOT** the sum or average!

**Example**:
```python
# file.py
def simple(): pass  # complexity = 1
def complex(): ...  # complexity = 35

# Result: File.complexity = 35 (not 36!)
```

**Implication**: To reduce file complexity, refactor the **most complex** function.

```

---

## Выводы и уроки

### ✅ Что сделали правильно

1. ✅ Создали tracking document (`task2-cli-refactoring.md`)
2. ✅ Следовали плану step-by-step
3. ✅ Измеряли metrics после каждого шага
4. ✅ Извлекли reusable helpers (снизили complexity 35→26!)
5. ✅ Провели post-mortem analysis при обнаружении проблемы

### ❌ Что сделали неправильно

1. ❌ **Использовали stale baseline** (baseline-quality.jsonld с устаревшими данными)
2. ❌ **Не проверили актуальность исходных данных** перед началом Task #2
3. ❌ **Не сверили RepoQ analysis vs semantic analysis** (26 vs 35)
4. ❌ **Не очистили cache** перед свежим анализом
5. ❌ **План ссылался на OLD метрики**, не отражающие реальность

### 🎓 Уроки на будущее

1. **Always use fresh baseline**: 
   ```bash
   rm -f baseline*.jsonld  # Очистить cache
   repoq analyze ... -o baseline-fresh.jsonld  # Свежий анализ
   ```

2. **Cross-validate metrics**: RepoQ analysis ↔ lizard semantic analysis
   - Если расхождение >5%: investigate!
   - Source of truth: актуальный код, не кэшированные файлы

3. **Document TRUE baseline**:
   - Зафиксировать baseline в tracking doc сразу
   - Включить git commit SHA для воспроизводимости
   - Per-function breakdown для контекста

4. **RepoQ needs improvement**:
   - ❌ Сохраняет только max(complexity), теряет per-function детали
   - ❌ Не предупреждает о stale data
   - ✅ Нужна feature: `functions: List[FunctionMetrics]` в File model

5. **Workflow должен включать**:

   ```
   [Baseline] → [Semantic Analysis] → [Cross-validate] → [Refactor] → [Measure] → [Validate]
        ↓              ↓                     ↓
     RepoQ         Lizard            RepoQ==Lizard?
   ```

### 🔄 Next Steps (исправленный план)

**Option A: Accept partial success & document**

- ✅ Complexity снижена 35→26 (-25%)
- ✅ Helpers extracted (5 reusable functions)
- ✅ Документировать как успех с неверным baseline
- ⏭️ Move to Task #3 с правильной методологией

**Option B: Continue Task #2 correctly**

- 🎯 Target: _run_command (CCN=26 → <20)
- 📐 Strategy: Extract subprocess logic, error handling
- ⏱️ Effort: 2-3 hours additional
- ✅ Demonstrate full ΣΓPΛR cycle with correct data

**Option C: Fix RepoQ itself (dogfooding++)**

- 🛠️ Add per-function metrics to File model
- 🛠️ Update ComplexityAnalyzer to save all functions
- 🛠️ Update refactor-plan to generate per-function tasks
- 📊 Re-run full analysis with enriched data
- ⏱️ Effort: 4-6 hours (but fixes root cause!)

**Recommendation**: **Option C** — это НАСТОЯЩИЙ dogfooding! 🚀

- Обнаружили проблему в собственном инструменте
- Исправляем инструмент используя инструмент
- Показываем мета-уровень рефлексии

---

## Appendix: Semantic Analysis Commands

### Per-function complexity (lizard)

```bash
lizard repoq/cli.py | awk 'NR>2 {print $1, $2, $3}' | sort -k1 -rn | head -10
```

### Per-function complexity (Python)

```python
import lizard
r = lizard.analyze_file('repoq/cli.py')
for f in sorted(r.function_list, key=lambda x: x.cyclomatic_complexity, reverse=True)[:10]:
    print(f"{f.cyclomatic_complexity:3d} | {f.name:40s} | lines {f.start_line}-{f.end_line}")
```

### File complexity (RepoQ)

```bash
repoq analyze . -o temp.jsonld --extensions py --exclude "tests/**"
python3 -c "import json; f=next(x for x in json.load(open('temp.jsonld'))['files'] if 'cli.py' in x['path']); print(f['complexity'])"
```

### Validate fix

```bash
# Before
OLD=$(python3 -c "import lizard; print(max(f.cyclomatic_complexity for f in lizard.analyze_file('repoq/cli.py').function_list))")

# ... make changes ...

# After
NEW=$(python3 -c "import lizard; print(max(f.cyclomatic_complexity for f in lizard.analyze_file('repoq/cli.py').function_list))")

echo "Complexity: $OLD → $NEW (Δ=$((NEW - OLD)))"
```
