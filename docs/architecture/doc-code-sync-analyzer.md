# DocCodeSyncAnalyzer

**Module:** `repoq/analyzers/doc_code_sync.py`  
**Purpose:** Валидация синхронизации документации с реализацией кода  
**Phase:** Full (запускается последним после всех других анализаторов)

---

## Обзор

`DocCodeSyncAnalyzer` проверяет соответствие документации коду, выявляя:

- Отсутствующие docstring (функции/классы без документации)
- Несовпадение сигнатур (параметры в docstring ≠ реальные параметры)
- Устаревшая документация (TODO/FIXME маркеры в docstring)
- Неактуальные примеры в README.md

**Цель:** Обеспечить, что документация не отстаёт от кода, предотвращая misleading documentation.

---

## Архитектура

### Формальная модель

```text
Σ (Signature):
  - Input: Project(files: List[File])
  - Output: List[Issue]
  - Analysis: AST parsing (Python), regex (README), optional docstring_parser

Γ (Gates):
  ✓ Soundness: AST parsing детерминирован (Python grammar)
  ✓ Completeness: покрывает функции, классы, методы
  ✓ Termination: O(files × functions) — линейная сложность
  ✓ False positives: минимизированы (skip private functions, __init__)

𝒫 (Options):
  1. AST-only (без docstring_parser): только missing docstrings + TODO detection
  2. AST + docstring_parser: полная валидация сигнатур
  3. AST + LLM: семантическая проверка outdated docs
  → Выбор: AST + optional docstring_parser (баланс точности/зависимостей)

Λ (Aggregation):
  - Completeness: 0.9 (покрывает Python, не JS/TS)
  - False positives: 0.8 (могут быть false alarms для auto-generated code)
  - Maintainability: 0.9 (стабильный Python AST API)
  → Total score: 0.87

R (Result): Реализация DocCodeSyncAnalyzer с 4 типами Issue
```

---

## Типы Issue

| Type                           | Severity | Условие                                  |
|--------------------------------|----------|------------------------------------------|
| `MissingDocstring`             | Major    | Функция/класс без docstring (не private) |
| `DocstringSignatureMismatch`   | Major    | Параметры в docstring ≠ actual params    |
| `OutdatedDocstring`            | Minor    | TODO/FIXME маркеры в docstring           |
| `OutdatedREADMEExample`        | Minor    | Импорты в README не найдены в проекте    |

---

## Реализация

### Ключевые методы

#### `_analyze_python_file(project_id: str, file_path: str, abs_path: Path) -> List[Issue]`

AST-анализ одного Python файла:

```python
tree = ast.parse(source_code, filename=str(abs_path))
for node in ast.walk(tree):
    if isinstance(node, ast.FunctionDef):
        issues.extend(self._check_function(node, ...))
    elif isinstance(node, ast.ClassDef):
        issues.extend(self._check_class(node, ...))
```

**Пропускаемые функции:**

- `_private_functions()` (начинаются с `_`)
- `__dunder_methods__()` (кроме `__init__`)
- Вложенные функции внутри других функций

#### `_check_function(node: ast.FunctionDef, ...) -> List[Issue]`

Проверка функции:

```python
# 1. Missing docstring
if not ast.get_docstring(node):
    return [Issue(type="repo:MissingDocstring", ...)]

# 2. TODO/FIXME detection
docstring = ast.get_docstring(node)
if re.search(r'\b(TODO|FIXME|XXX|HACK)\b', docstring, re.IGNORECASE):
    return [Issue(type="repo:OutdatedDocstring", ...)]

# 3. Signature mismatch (requires docstring_parser)
issues.extend(self._check_signature_mismatch(node, docstring, ...))
```

#### `_check_signature_mismatch(node: ast.FunctionDef, docstring: str, ...) -> List[Issue]`

Валидация параметров (опционально, требует `docstring_parser`):

```python
try:
    from docstring_parser import parse
    
    parsed = parse(docstring)
    doc_params = {p.arg_name for p in parsed.params}
    
    # Реальные параметры из AST
    actual_params = {arg.arg for arg in node.args.args if arg.arg != 'self'}
    
    # Расхождение
    if doc_params != actual_params:
        missing = actual_params - doc_params
        extra = doc_params - actual_params
        return [Issue(type="repo:DocstringSignatureMismatch", ...)]
except ImportError:
    # Gracefully degrade if docstring_parser not installed
    return []
```

**Пример расхождения:**

```python
def process_data(config: dict, verbose: bool = False):
    """
    Process data.
    
    Args:
        options: Configuration dictionary  # ← Несовпадение!
        verbose: Verbosity flag
    """
```

→ Issue: `Missing params: config, Extra params: options`

#### `_check_readme_examples() -> List[Issue]`

Проверка примеров в README.md:

```python
# 1. Извлечь Python code blocks из README
code_blocks = re.findall(r'```python\n(.*?)\n```', readme_content, re.DOTALL)

# 2. Найти импорты
for block in code_blocks:
    imports = re.findall(r'from (\S+) import|import (\S+)', block)
    
    # 3. Проверить, что импорты существуют в проекте
    for module in imports:
        if not self._module_exists(module, project_files):
            return [Issue(type="repo:OutdatedREADMEExample", ...)]
```

**Пример проблемы:**

```markdown
# README.md
```python
from repoq.old_api import analyze  # ← Модуль не существует!
```

```text
→ Issue: `README example imports non-existent module: repoq.old_api`
```

---

## Интеграция в pipeline

```python
# repoq/pipeline.py
def run_full_analysis(project: Project, config: Config):
    # ... (все другие анализаторы)
    
    # DocCodeSyncAnalyzer запускается ПОСЛЕДНИМ
    # (нуждается в полном списке файлов из StructureAnalyzer)
    doc_sync_analyzer = DocCodeSyncAnalyzer()
    doc_sync_analyzer.run(project, config)
```

**Обоснование порядка:** DocCodeSyncAnalyzer зависит от `project.files` (заполняется StructureAnalyzer), поэтому запускается в конце pipeline.

---

## Тестирование

**Файл:** `tests/unit/test_doc_code_sync.py`  
**Покрытие:** 6 тестов

### Тест-кейсы

1. **test_missing_docstring_detection**: Функция без docstring

   ```python
   # module.py
   def undocumented_function():
       pass
   
   issues = analyzer._analyze_python_file(...)
   assert any(i.type == "repo:MissingDocstring" for i in issues)
   ```

2. **test_signature_mismatch_detection**: Несовпадение параметров

   ```python
   # module.py
   def process(config: dict):
       """Args: options (dict): Config"""
       pass
   
   issues = analyzer._analyze_python_file(...)
   mismatch = [i for i in issues if "DocstringSignatureMismatch" in i.type]
   assert len(mismatch) == 1
   assert "config" in mismatch[0].description  # Missing param
   ```

3. **test_todo_in_docstring_detection**: TODO маркеры

   ```python
   def broken():
       """TODO: fix this"""
       pass
   
   issues = analyzer._analyze_python_file(...)
   assert any("OutdatedDocstring" in i.type for i in issues)
   ```

4. **test_class_missing_docstring**: Класс без docstring

   ```python
   class UndocumentedClass:
       pass
   
   issues = analyzer._analyze_python_file(...)
   assert any("MissingDocstring" in i.type and "UndocumentedClass" in i.description for i in issues)
   ```

5. **test_readme_example_validation**: Неверные импорты в README

   ```python
   # README.md
   ```python
   from nonexistent_module import func
   ```python
   from nonexistent_module import func
   ```

   issues = analyzer._check_readme_examples(...)
   assert any("OutdatedREADMEExample" in i.type for i in issues)
   ```

6. **test_skips_private_functions**: Игнорирование private функций

   ```python
   def _private():  # Без docstring
       pass
   
   issues = analyzer._analyze_python_file(...)
   assert not any("_private" in i.description for i in issues)
   ```

---

## Конфигурация

```toml
# repoq.toml (будущее расширение)
[doc_code_sync]
check_private_functions = false  # По умолчанию: false
check_test_files = false         # По умолчанию: false
require_return_docs = true       # Требовать документацию Returns
readme_files = ["README.md", "docs/index.md"]  # Какие README проверять
```

---

## Зависимости

### Обязательные

- `ast` (stdlib) — парсинг Python AST
- `re` (stdlib) — regex для TODO/FIXME

### Опциональные

- `docstring_parser` — полная валидация сигнатур

  ```bash
  uv add docstring_parser  # Если нужна signature validation
  ```

**Graceful degradation:** Если `docstring_parser` не установлен, анализатор пропускает проверку signature mismatch, но остальные проверки работают.

---

## Ограничения и будущие улучшения

### Текущие ограничения

1. **Python-only**: Не проверяет docstrings в JS/TS/Java
2. **No semantic validation**: Не проверяет корректность *содержания* документации
3. **README parsing simplistic**: Regex-based, может пропустить сложные случаи
4. **No type hint validation**: Не сравнивает типы в docstring vs type hints

### Roadmap

- [ ] Поддержка JSDoc/TSDoc для JavaScript/TypeScript
- [ ] LLM-based semantic validation (outdated descriptions)
- [ ] Type hint vs docstring type consistency check
- [ ] Mkdocs integration (проверка docs/ structure)
- [ ] Auto-fix capability (генерация skeleton docstrings)

---

## Рефлексивность

DocCodeSyncAnalyzer **обнаружил 208 проблем в самом RepoQ**:

```json
{
  "issues": [
    {
      "@type": "repo:MissingDocstring",
      "title": "Missing docstring: mock_import()",
      "file": "repoq/analyzers/weakness.py"
    },
    {
      "@type": "repo:MissingDocstring",
      "title": "Missing docstring: dfs()",
      "file": "repoq/analyzers/structure.py"
    },
    {
      "@type": "repo:OutdatedDocstring",
      "title": "TODO in docstring: _generate_cytoscape_json()",
      "file": "repoq/reporting/graphviz.py"
    }
  ]
}
```

**Выводы:**

1. **208 функций без docstring** — большая часть кодовой базы недокументирована
2. **2 устаревших docstring** с TODO — требуют обновления
3. **Self-analysis работает:** система успешно обнаружила собственные недостатки

---

## Связь с TRS Framework

DocCodeSyncAnalyzer следует TRS принципам на метауровне:

- **Звуковость (Soundness):** AST parsing гарантирует корректное извлечение сигнатур
- **Терминация (Termination):** O(n) по количеству функций
- **Идемпотентность:** Повторный запуск даёт тот же результат
- **Консервативность:** Пропускает private functions (false negatives > false positives)

**Рефлексивный аспект:**

```python
# DocCodeSyncAnalyzer сам имеет docstrings!
class DocCodeSyncAnalyzer(BaseAnalyzer):
    """
    Analyzer that detects documentation-code synchronization issues.
    
    Checks:
    - Missing docstrings in functions/classes
    - Signature mismatches between docstrings and actual parameters
    - TODO/FIXME markers in docstrings
    - Outdated README examples
    """
```

→ Система описывает саму себя через те же механизмы, которые она проверяет.

---

## Примеры использования

### CLI

```bash
# Полный анализ (включает doc-code sync)
repoq analyze . --mode full

# Проверка результатов
jq '.issues[] | select(.["@type"][] | contains("MissingDocstring"))' self-analysis.json
```

### Programmatic

```python
from repoq.analyzers.doc_code_sync import DocCodeSyncAnalyzer
from repoq.core.model import Project, File

project = Project(id="myproject", root=Path("."))
project.files["main.py"] = File(path="main.py", language="Python")

analyzer = DocCodeSyncAnalyzer()
analyzer.run(project, config)

# Фильтрация по типу Issue
missing_docs = [i for i in project.issues.values() 
                if i.type == "repo:MissingDocstring"]
print(f"Found {len(missing_docs)} undocumented functions")
```

### CI Integration

```yaml
# .github/workflows/doc-check.yml
- name: Check documentation sync
  run: |
    repoq analyze . --mode full
    jq '.issues[] | select(.["@type"][] | contains("DocstringSignatureMismatch"))' \
      self-analysis.json > doc-issues.json
    if [ -s doc-issues.json ]; then
      echo "❌ Found documentation-code mismatches!"
      cat doc-issues.json
      exit 1
    fi
```

---

## Связь с другими анализаторами

| Analyzer              | Связь                                                    |
|-----------------------|----------------------------------------------------------|
| **StructureAnalyzer** | Предоставляет список Python файлов для анализа          |
| **ComplexityAnalyzer**| Высокая сложность + missing docstring = critical issue  |
| **WeaknessAnalyzer**  | TODO в коде → может коррелировать с TODO в docstrings   |
| **GitStatusAnalyzer** | Uncommitted docs → может быть причиной outdated docs    |

**Будущее:** Composite issues (например, "Complex function without docstring" = MissingDocstring + HighCyclomaticComplexity).

---

## Метрики качества

Self-analysis показал:

```text
Q-score: 98.97 (Grade A)
Total issues: 628
MissingDocstring: 208 (33% от всех issues)
```

**Интерпретация:**

- 208/628 = 33% проблем — это недокументированные функции
- Q-score всё ещё высокий (98.97) → система считает missing docstrings minor issue
- **Рекомендация:** Повысить severity для MissingDocstring в публичных API

---

## Ссылки

- **Код:** [`repoq/analyzers/doc_code_sync.py`](../../repoq/analyzers/doc_code_sync.py)
- **Тесты:** [`tests/unit/test_doc_code_sync.py`](../../tests/unit/test_doc_code_sync.py)
- **Python AST:** [ast module documentation](https://docs.python.org/3/library/ast.html)
- **docstring_parser:** [GitHub repo](https://github.com/rr-/docstring_parser)
- **Related:** [GitStatusAnalyzer](git-status-analyzer.md), [Analyzer Pipeline](analyzer-pipeline.md)
