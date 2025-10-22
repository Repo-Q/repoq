# Plan улучшений RepoQ: Стратегический roadmap

**Дата**: 2025-10-22  
**Контекст**: Post Option C implementation (per-function metrics)  
**Методология**: Σ→Γ→𝒫→Λ→R для каждого направления

---

## [Σ] Signature: Текущее состояние системы

### ✅ Достигнуто (v0.4.0)

**Core Features**:

- ✅ Structure analysis (files, modules, dependencies)
- ✅ Complexity metrics (cyclomatic complexity, MI)
- ✅ Git history (authorship, churn, temporal coupling)
- ✅ Hotspots detection (high-churn + high-complexity)
- ✅ Semantic export (JSON-LD, RDF/Turtle, W3C ontologies)
- ✅ Refactoring plan generation (PCE algorithm)
- ✅ Quality gates (CI/CD integration)
- ✅ **Per-function metrics** (NEW! Functions with CCN, LOC, line ranges)

**Testing**:

- ✅ 295 tests collected
- ✅ Coverage: 63%
- ✅ CI: GitHub Actions

**Documentation**:

- ✅ README with quick start
- ✅ Dogfooding meta-level report
- ✅ Task #2 failure analysis (Σ→Γ→𝒫→Λ→R)

### 🔴 Критические проблемы

**Problem 1: High complexity в core модулях**

```
refactoring-plan-v2.md (Top-5 CRITICAL):
1. repoq/analyzers/history.py:     CCN=35 (_run_pydriller), CCN=30 (_run_git)
2. repoq/core/jsonld.py:           CCN=33 (to_jsonld)
3. repoq/cli.py:                   CCN=26 (_run_command), CCN=16 (_run_trs_verification)
4. repoq/gate.py:                  CCN=23 (format_gate_report)
5. repoq/refactoring.py:           CCN=21 (generate_plan)

Total Expected ΔQ: +589.0 points
```

**Problem 2: tmp/ pollution risk**

- ❌ `--exclude` не всегда работает корректно
- ❌ Нет автоочистки tmp/ директорий
- ❌ Нет предупреждения о stale data

**Problem 3: Отсутствие per-function ΔQ estimation**

- ❌ Plan показывает файловый ΔQ, не function-level
- ❌ Нет оценки "сколько даст рефакторинг функции X"
- ❌ Приоритизация основана на файлах, не на функциях

**Problem 4: Limited IDE integration**

- ❌ Нет quick-jump links для функций
- ❌ Нет inline recommendations в IDE
- ❌ Нет auto-fix suggestions

**Problem 5: Single-language support**

- ✅ Python (lizard)
- ❌ JavaScript/TypeScript (нужен ESLint/TSLint)
- ❌ Java (нужен PMD/Checkstyle)
- ❌ Go, Rust, C++, etc.

---

## [Γ] Gates: Критерии качества улучшений

Каждое улучшение должно пройти гейты:

### Gate 1: Soundness (корректность)

- ✅ Метрики соответствуют семантике кода
- ✅ Нет false positives/negatives
- ✅ Воспроизводимость результатов

### Gate 2: Performance (производительность)

- ✅ Analysis time: O(N) где N = LOC
- ✅ Memory usage: <512MB для проектов до 100K LOC
- ✅ No blocking operations без timeout

### Gate 3: Usability (удобство)

- ✅ Actionable recommendations (конкретные действия)
- ✅ Clear error messages
- ✅ Minimal configuration required

### Gate 4: Extensibility (расширяемость)

- ✅ Plugin architecture для новых анализаторов
- ✅ Custom metrics support
- ✅ API для интеграций

### Gate 5: Testability (тестируемость)

- ✅ Coverage ≥80% для новых модулей
- ✅ Property-based tests для критических алгоритмов
- ✅ E2E tests для пайплайнов

---

## [𝒫] Options: Направления улучшений

### Tier 1: КРИТИЧЕСКИЕ (выполнить первыми)

#### 🔴 T1.1: Refactor Top-5 Complex Modules

**Цель**: Снизить complexity в core модулях (ΔQ = +589.0)

**Задачи**:

1. **history.py** (CCN=35, ΔQ=+153):
   - Refactor `_run_pydriller()`: split into `_collect_commits()`, `_process_commit()`, `_aggregate_stats()`
   - Refactor `_run_git()`: extract `_parse_git_blame()`, `_compute_ownership()`
   - Target: CCN=35→<15 per function

2. **jsonld.py** (CCN=33, ΔQ=+146):
   - Refactor `to_jsonld()`: split into `_create_context()`, `_serialize_project()`, `_serialize_files()`, `_serialize_issues()`
   - Introduce builder pattern for JSON-LD nodes
   - Target: CCN=33→<15

3. **cli.py** (CCN=26, ΔQ=+108):
   - Refactor `_run_command()`: extract `_prepare_command()`, `_execute_process()`, `_handle_result()`
   - Refactor `_run_trs_verification()`: split verification logic
   - Split cli.py: commands/ module (analyze, gate, refactor-plan, etc.)
   - Target: CCN=26→<15, LOC=1535→<500 per file

4. **gate.py** (CCN=23, ΔQ=+93):
   - Refactor `format_gate_report()`: extract formatters (markdown, json, junit)
   - Refactor `run_quality_gate()`: split predicates, policy evaluation
   - Target: CCN=23→<15

5. **refactoring.py** (CCN=21, ΔQ=+89):
   - Refactor `generate_plan()`: extract PCE steps
   - Split priority calculation, ΔQ estimation, task generation
   - Target: CCN=21→<15

**Effort**: 20-40 hours (4-8h per module)  
**Priority**: 🔴 CRITICAL  
**ΔQ**: +589.0 points  
**Gates**: Soundness (maintain behavior), Performance (<10% slowdown), Testability (add tests for extracted functions)

#### 🔴 T1.2: Fix tmp/ Pollution & Stale Data Detection

**Цель**: Предотвратить анализ устаревших/временных файлов

**Задачи**:

1. **Улучшить --exclude logic**:

   ```python
   # repoq/analyzers/structure.py
   def _should_exclude(self, path: Path) -> bool:
       # FIX: Проверять ВСЕ exclude_globs, включая tmp/**
       for pattern in self.cfg.exclude_globs:
           if path.match(pattern):
               return True
       # Add: Автоматическое исключение типичных временных директорий
       auto_exclude = ["tmp", "temp", ".cache", "__pycache__", "node_modules"]
       if any(part in path.parts for part in auto_exclude):
           return True
       return False
   ```

2. **Stale data warning**:

   ```python
   # repoq/core/repo_loader.py
   def analyze_project(self, path: Path) -> Project:
       # Check if analyzing potentially stale files
       stale_paths = []
       for file_path in self.collected_files:
           mtime = file_path.stat().st_mtime
           if time.time() - mtime > 86400 * 7:  # >7 days old
               stale_paths.append(file_path)
       
       if stale_paths:
           logger.warning(
               f"⚠️  Analyzing {len(stale_paths)} potentially stale files "
               f"(not modified in 7+ days). Consider excluding old snapshots."
           )
   ```

3. **Auto-cleanup tmp/**:

   ```python
   # repoq/cli.py
   def _cleanup_temp_files(self, max_age_days: int = 7):
       """Remove tmp/ files older than max_age_days."""
       tmp_dirs = [Path("tmp"), Path(".repoq_cache"), Path(".repoq_tmp")]
       for tmp_dir in tmp_dirs:
           if tmp_dir.exists():
               # ... cleanup logic ...
   ```

**Effort**: 4-6 hours  
**Priority**: 🔴 CRITICAL  
**Impact**: Prevent metric pollution (как в Task #2)  
**Gates**: Soundness (don't exclude valid files), Performance (fast glob matching)

#### 🔴 T1.3: Per-Function ΔQ Estimation

**Цель**: Показывать ожидаемый прирост Q-score при рефакторинге конкретной функции

**Задачи**:

1. **Extend FunctionMetrics**:

   ```python
   @dataclass
   class FunctionMetrics:
       # ... existing fields ...
       expected_delta_q: Optional[float] = None  # ← NEW
       refactoring_priority: Optional[str] = None  # "critical", "high", "medium", "low"
   ```

2. **Compute per-function ΔQ**:

   ```python
   # repoq/refactoring.py
   def _estimate_function_delta_q(func: FunctionMetrics, file_loc: int) -> float:
       """
       Estimate ΔQ improvement from refactoring a function.
       
       Formula:
       ΔQ = (current_CCN - target_CCN) * weight_complexity
            + (current_LOC - target_LOC) * weight_loc
            + file_impact_factor
       """
       target_ccn = 10.0
       target_loc = func.lines_of_code * 0.7  # Aim for 30% reduction
       
       delta_ccn = max(0, func.cyclomatic_complexity - target_ccn)
       delta_loc = max(0, func.lines_of_code - target_loc)
       
       # Weights
       w_ccn = 5.0
       w_loc = 0.5
       
       # File impact (larger files benefit more from extraction)
       file_factor = 1.0 + (file_loc / 1000.0)
       
       delta_q = (delta_ccn * w_ccn + delta_loc * w_loc) * file_factor
       return round(delta_q, 1)
   ```

3. **Update refactor-plan output**:

   ```markdown
   ### Task #3: repoq/cli.py
   **Priority**: 🔴 CRITICAL
   **Expected ΔQ**: +108.0 points (file-level)
   
   **Recommendations**:
   1. 🎯 Refactor function `_run_command` (CCN=26, lines 593-772)
      → Expected ΔQ: +85.0 points (78% of file's potential)
      → Estimated effort: 3-4 hours
      
   2. 🎯 Refactor function `_run_trs_verification` (CCN=16, lines 775-843)
      → Expected ΔQ: +15.0 points (14% of file's potential)
      → Estimated effort: 1-2 hours
   ```

**Effort**: 6-8 hours  
**Priority**: 🔴 CRITICAL  
**Impact**: Better prioritization (refactor high-impact functions first)  
**Gates**: Soundness (ΔQ formula validated), Usability (clear metrics)

---

### Tier 2: ВАЖНЫЕ (выполнить после Tier 1)

#### 🟡 T2.1: IDE Integration (VSCode Extension)

**Цель**: Inline refactoring recommendations в редакторе

**Задачи**:

1. **VSCode extension skeleton**:

   ```typescript
   // extension.ts
   export function activate(context: vscode.ExtensionContext) {
       // Command: Run RepoQ analysis
       context.subscriptions.push(
           vscode.commands.registerCommand('repoq.analyze', async () => {
               const analysis = await runRepoQAnalysis();
               showRecommendations(analysis);
           })
       );
       
       // CodeLens: Show complexity inline
       context.subscriptions.push(
           vscode.languages.registerCodeLensProvider('python', new ComplexityCodeLensProvider())
       );
   }
   ```

2. **Features**:
   - ✅ Show CCN inline above functions (CodeLens)
   - ✅ Quick-jump to refactoring plan (click on recommendation)
   - ✅ Inline actions: "Extract function", "Split function"
   - ✅ Diff preview for suggested refactorings

3. **Protocol**:

   ```json
   // LSP extension для RepoQ
   {
       "method": "repoq/getRecommendations",
       "params": {
           "uri": "file:///path/to/file.py",
           "position": { "line": 593, "character": 0 }
       },
       "result": {
           "recommendations": [
               {
                   "type": "refactor.extract",
                   "title": "Extract subprocess logic",
                   "range": { "start": { "line": 600, "character": 4 }, "end": { ... } },
                   "expectedDeltaQ": 45.0
               }
           ]
       }
   }
   ```

**Effort**: 15-20 hours  
**Priority**: 🟡 HIGH  
**Impact**: Better developer experience (no context switching)  
**Gates**: Usability (non-intrusive), Performance (fast inline hints)

#### 🟡 T2.2: Multi-Language Support

**Цель**: Анализ JavaScript/TypeScript, Java, Go

**Задачи**:

1. **Abstract complexity analyzer**:

   ```python
   # repoq/analyzers/complexity_base.py
   from abc import ABC, abstractmethod
   
   class ComplexityAnalyzerBase(ABC):
       @abstractmethod
       def analyze_file(self, path: Path) -> List[FunctionMetrics]:
           pass
       
       @abstractmethod
       def supported_extensions(self) -> List[str]:
           pass
   ```

2. **Language-specific implementations**:

   ```python
   # repoq/analyzers/complexity_js.py
   class JavaScriptComplexityAnalyzer(ComplexityAnalyzerBase):
       def analyze_file(self, path: Path) -> List[FunctionMetrics]:
           # Use ESLint's complexity plugin
           result = subprocess.run(
               ["eslint", "--format=json", "--rule", "complexity:2", str(path)],
               capture_output=True
           )
           # Parse ESLint output...
   
   # repoq/analyzers/complexity_java.py
   class JavaComplexityAnalyzer(ComplexityAnalyzerBase):
       def analyze_file(self, path: Path) -> List[FunctionMetrics]:
           # Use PMD or Checkstyle
           # ...
   ```

3. **Auto-detect language**:

   ```python
   # repoq/analyzers/factory.py
   ANALYZERS = {
       "python": PythonComplexityAnalyzer,
       "javascript": JavaScriptComplexityAnalyzer,
       "typescript": TypeScriptComplexityAnalyzer,
       "java": JavaComplexityAnalyzer,
   }
   
   def get_analyzer(language: str) -> ComplexityAnalyzerBase:
       return ANALYZERS.get(language, PythonComplexityAnalyzer)()
   ```

**Effort**: 20-30 hours (10h per language)  
**Priority**: 🟡 HIGH  
**Impact**: Wider adoption (not Python-only)  
**Gates**: Soundness (metrics match language idioms), Extensibility (easy to add new languages)

#### 🟡 T2.3: Auto-Refactoring Suggestions

**Цель**: Предлагать конкретные трансформации кода

**Задачи**:

1. **Pattern detection**:

   ```python
   # repoq/refactoring/patterns.py
   
   @dataclass
   class RefactoringPattern:
       name: str
       condition: Callable[[FunctionMetrics, str], bool]  # (metrics, source_code) -> bool
       suggestion: str
       transformations: List[Transformation]
   
   PATTERNS = [
       RefactoringPattern(
           name="extract_subprocess_logic",
           condition=lambda m, src: m.cyclomatic_complexity >= 15 and "subprocess." in src,
           suggestion="Extract subprocess handling into helper function",
           transformations=[
               ExtractFunctionTransformation(
                   pattern=r"subprocess\.(run|Popen|check_output).*?\n",
                   new_function_name="_run_subprocess",
               )
           ]
       ),
       RefactoringPattern(
           name="split_nested_conditionals",
           condition=lambda m, src: m.max_nesting_depth >= 5,
           suggestion="Split deeply nested conditionals into separate functions",
           transformations=[...]
       ),
   ]
   ```

2. **AST-based transformations**:

   ```python
   # repoq/refactoring/transformations.py
   import ast
   
   class ExtractFunctionTransformation:
       def apply(self, tree: ast.AST, target: FunctionMetrics) -> ast.AST:
           # Find target function node
           # Extract complex block
           # Create new function definition
           # Replace original block with function call
           # ...
   ```

3. **Generate diff preview**:

   ```python
   # repoq/refactoring.py
   def generate_refactoring_diff(
       file_path: Path,
       func: FunctionMetrics,
       pattern: RefactoringPattern
   ) -> str:
       """Generate unified diff for suggested refactoring."""
       original = file_path.read_text()
       transformed = apply_transformations(original, func, pattern.transformations)
       return difflib.unified_diff(original, transformed, lineterm="")
   ```

**Effort**: 30-40 hours  
**Priority**: 🟡 HIGH  
**Impact**: From "what to refactor" to "how to refactor"  
**Gates**: Soundness (preserve behavior), Testability (property-based tests)

---

### Tier 3: ПОЛЕЗНЫЕ (выполнить после Tier 2)

#### 🟢 T3.1: Machine Learning for Smell Detection

**Цель**: Обучить модель находить code smells помимо метрик

**Задачи**:

1. **Dataset creation**:
   - Collect 1000+ Python repositories
   - Label code smells manually (God Class, Feature Envy, Long Method, etc.)
   - Extract features: AST patterns, metrics, naming conventions

2. **Model training**:

   ```python
   # repoq/ml/smell_detector.py
   from sklearn.ensemble import RandomForestClassifier
   
   class CodeSmellDetector:
       def __init__(self):
           self.model = RandomForestClassifier(n_estimators=100)
       
       def extract_features(self, func: FunctionMetrics, source: str) -> np.ndarray:
           # Features: CCN, LOC, params, nesting, token_count
           # + AST features: num_classes, num_loops, num_exceptions
           # + naming: function_name_length, camelCase vs snake_case
           # ...
       
       def predict_smells(self, func: FunctionMetrics, source: str) -> List[str]:
           features = self.extract_features(func, source)
           probas = self.model.predict_proba([features])[0]
           return [smell for smell, p in zip(SMELL_CLASSES, probas) if p > 0.7]
   ```

3. **Integration**:

   ```markdown
   ### Task #3: repoq/cli.py
   **Recommendations**:
   1. 🎯 Refactor function `_run_command` (CCN=26)
      🤖 Detected smells:
         - Long Method (LOC=122, threshold=50)
         - Feature Envy (high coupling with subprocess module)
         - Primitive Obsession (many string parameters)
   ```

**Effort**: 40-60 hours (dataset + training + integration)  
**Priority**: 🟢 MEDIUM  
**Impact**: Find issues beyond complexity metrics  
**Gates**: Soundness (low false positive rate <10%), Performance (fast inference)

#### 🟢 T3.2: Quality Certificates & Badges

**Цель**: Генерировать сертификаты качества для проектов

**Задачи**:

1. **Certificate schema**:

   ```json
   {
       "@context": "https://field33.com/ontologies/quality-cert/",
       "@type": "QualityCertificate",
       "project": "repoq-pro-final",
       "issuer": "RepoQ v0.5.0",
       "issuedAt": "2025-10-25T10:00:00Z",
       "validUntil": "2026-10-25T10:00:00Z",
       "grade": "A",
       "qScore": 85.5,
       "criteria": {
           "complexity": { "score": 90, "threshold": 80, "passed": true },
           "coverage": { "score": 63, "threshold": 80, "passed": false },
           "documentation": { "score": 95, "threshold": 70, "passed": true }
       },
       "badges": [
           "https://img.shields.io/badge/RepoQ-Grade_A-brightgreen",
           "https://img.shields.io/badge/Q--Score-85.5-green"
       ]
   }
   ```

2. **SVG badge generation**:

   ```python
   # repoq/reporting/badges.py
   def generate_badge(label: str, value: str, color: str) -> str:
       """Generate SVG badge."""
       # Use shields.io style
       # ...
   ```

3. **CLI command**:

   ```bash
   repoq certify . -o quality-certificate.json
   repoq badge . --metric q-score -o badge.svg
   ```

**Effort**: 10-15 hours  
**Priority**: 🟢 MEDIUM  
**Impact**: Showcase project quality (README badges)  
**Gates**: Usability (beautiful badges), Standards (W3C verifiable credentials)

#### 🟢 T3.3: SPARQL Query Interface

**Цель**: Запросы к RDF/Turtle экспорту

**Задачи**:

1. **Local SPARQL endpoint**:

   ```python
   # repoq/semantic/sparql_server.py
   from rdflib import Graph
   from flask import Flask, request, jsonify
   
   app = Flask(__name__)
   graph = Graph()
   
   @app.route('/sparql', methods=['GET', 'POST'])
   def sparql_query():
       query = request.args.get('query') or request.form.get('query')
       results = graph.query(query)
       return jsonify([dict(row.asdict()) for row in results])
   ```

2. **Example queries**:

   ```sparql
   # Find all files with complexity > 20
   PREFIX repo: <https://field33.com/ontologies/repoq/>
   SELECT ?file ?complexity WHERE {
       ?file a repo:File ;
             repo:complexity ?complexity .
       FILTER (?complexity > 20)
   }
   ORDER BY DESC(?complexity)
   
   # Find functions with CCN > 15 and LOC > 100
   PREFIX repo: <https://field33.com/ontologies/repoq/>
   SELECT ?file ?function ?ccn ?loc WHERE {
       ?file repo:hasFunction ?function .
       ?function repo:cyclomaticComplexity ?ccn ;
                 repo:linesOfCode ?loc .
       FILTER (?ccn > 15 && ?loc > 100)
   }
   ```

3. **CLI integration**:

   ```bash
   repoq sparql . --query "SELECT ?file WHERE { ?file repo:complexity ?c . FILTER(?c > 20) }"
   repoq sparql . --server --port 8080  # Start SPARQL endpoint
   ```

**Effort**: 12-15 hours  
**Priority**: 🟢 MEDIUM  
**Impact**: Advanced semantic queries (research, BI)  
**Gates**: Standards (SPARQL 1.1 compliance), Performance (fast queries)

---

### Tier 4: ЭКСПЕРИМЕНТАЛЬНЫЕ (исследовательские)

#### 🔵 T4.1: TRS-Based Self-Verification

**Цель**: Формальная верификация рефакторингов через TRS

**Задачи**:

1. **Define TRS for Python AST**:

   ```lean4
   -- repoq/verification/python_trs.lean
   inductive PyExpr where
     | Call (func : String) (args : List PyExpr)
     | Lambda (params : List String) (body : PyExpr)
     | If (cond : PyExpr) (then_ : PyExpr) (else_ : PyExpr)
     -- ...
   
   -- Rewrite rules
   def extract_function : PyExpr → PyExpr
     | If cond (Call f args) else_ => 
         let helper := Lambda ["x"] (Call f args)
         If cond (Call "helper" [cond]) else_
   ```

2. **Prove equivalence**:

   ```lean4
   theorem extract_function_preserves_semantics (e : PyExpr) :
     eval e = eval (extract_function e) := by
       -- Proof by structural induction
       -- ...
   ```

3. **Generate verified patches**:

   ```bash
   repoq verify-refactor --file cli.py --function _run_command --strategy extract_subprocess
   # Output: Verified patch with proof certificate
   ```

**Effort**: 60-80 hours (requires Lean4 expertise)  
**Priority**: 🔵 LOW (research)  
**Impact**: Provably correct refactorings  
**Gates**: Soundness (theorem prover validates), Completeness (covers common patterns)

#### 🔵 T4.2: Temporal Coupling Analysis

**Цель**: Найти файлы, которые часто меняются вместе (structural coupling)

**Задачи**:

1. **Git log mining**:

   ```python
   # repoq/analyzers/coupling.py
   def analyze_temporal_coupling(repo_path: Path) -> Dict[Tuple[str, str], float]:
       """
       Compute temporal coupling score for file pairs.
       
       Score = commits_together / min(commits_A, commits_B)
       """
       commits = git.log("--all", "--format=%H")
       
       coupling = defaultdict(int)
       for commit_hash in commits:
           files_changed = git.diff_tree("--no-commit-id", "--name-only", "-r", commit_hash)
           for f1, f2 in combinations(files_changed, 2):
               coupling[(f1, f2)] += 1
       
       # Normalize by individual file change frequency
       # ...
   ```

2. **Visualize as graph**:

   ```python
   # repoq/reporting/coupling_graph.py
   def generate_coupling_graph(coupling: Dict, threshold: float = 0.3) -> str:
       """Generate DOT graph of highly coupled files."""
       dot = ["digraph G {"]
       for (f1, f2), score in coupling.items():
           if score >= threshold:
               dot.append(f'  "{f1}" -> "{f2}" [label="{score:.2f}"];')
       dot.append("}")
       return "\n".join(dot)
   ```

3. **Recommendations**:

   ```markdown
   ### Warning: High Temporal Coupling Detected
   
   Files `repoq/core/model.py` and `repoq/analyzers/complexity.py` change together 85% of the time.
   
   **Recommendation**: Consider merging or creating a shared abstraction to reduce coupling.
   ```

**Effort**: 15-20 hours  
**Priority**: 🔵 LOW  
**Impact**: Find architectural issues  
**Gates**: Soundness (avoid false coupling from mass refactorings)

---

## [Λ] Aggregation: Приоритизация

### Scoring Matrix

| Task | Soundness | Performance | Usability | Extensibility | Testability | **Total** | **Priority** |
|------|-----------|-------------|-----------|---------------|-------------|-----------|--------------|
| **T1.1: Refactor Top-5** | 10 | 8 | 9 | 7 | 10 | **44** | 🔴 CRITICAL |
| **T1.2: Fix tmp/ pollution** | 10 | 9 | 10 | 6 | 8 | **43** | 🔴 CRITICAL |
| **T1.3: Per-function ΔQ** | 9 | 10 | 10 | 8 | 7 | **44** | 🔴 CRITICAL |
| T2.1: IDE Integration | 7 | 8 | 10 | 9 | 6 | **40** | 🟡 HIGH |
| T2.2: Multi-Language | 8 | 7 | 9 | 10 | 7 | **41** | 🟡 HIGH |
| T2.3: Auto-Refactoring | 7 | 6 | 10 | 8 | 6 | **37** | 🟡 HIGH |
| T3.1: ML Smell Detection | 6 | 5 | 7 | 7 | 5 | **30** | 🟢 MEDIUM |
| T3.2: Quality Certificates | 8 | 9 | 8 | 6 | 8 | **39** | 🟢 MEDIUM |
| T3.3: SPARQL Queries | 9 | 7 | 6 | 8 | 7 | **37** | 🟢 MEDIUM |
| T4.1: TRS Verification | 10 | 4 | 4 | 5 | 8 | **31** | 🔵 LOW |
| T4.2: Temporal Coupling | 7 | 8 | 6 | 7 | 7 | **35** | 🔵 LOW |

**Критерии** (каждый по шкале 1-10):

- **Soundness**: Корректность и надёжность
- **Performance**: Влияние на скорость работы
- **Usability**: Удобство для пользователя
- **Extensibility**: Расширяемость решения
- **Testability**: Покрытие тестами

### Рекомендуемый порядок выполнения

**Phase 1: Foundation** (Tier 1, 30-54 hours)

1. ✅ T1.2: Fix tmp/ pollution (4-6h) — блокирует корректные метрики
2. ✅ T1.3: Per-function ΔQ (6-8h) — улучшает приоритизацию
3. ✅ T1.1: Refactor Top-5 (20-40h) — снижает technical debt

**Phase 2: Usability** (Tier 2, 65-90 hours)
4. ✅ T2.1: IDE Integration (15-20h) — улучшает UX
5. ✅ T2.2: Multi-Language (20-30h) — расширяет аудиторию
6. ✅ T2.3: Auto-Refactoring (30-40h) — автоматизация

**Phase 3: Advanced** (Tier 3, 37-45 hours)
7. ✅ T3.2: Quality Certificates (10-15h) — маркетинг
8. ✅ T3.3: SPARQL Queries (12-15h) — advanced use cases
9. ✅ T3.1: ML Smell Detection (40-60h) — research

**Phase 4: Research** (Tier 4, 75-100 hours)
10. ✅ T4.2: Temporal Coupling (15-20h) — эксперимент
11. ✅ T4.1: TRS Verification (60-80h) — формальные методы

---

## [R] Result: Execution Plan

### Sprint 1: Fix Critical Issues (2 weeks)

**Goals**:

- ✅ Fix tmp/ pollution (T1.2)
- ✅ Add per-function ΔQ estimation (T1.3)
- ✅ Refactor history.py + jsonld.py (T1.1, partial)

**Deliverables**:

- ✅ No stale data warnings
- ✅ Per-function ΔQ in refactoring-plan
- ✅ history.py CCN: 35→<15
- ✅ jsonld.py CCN: 33→<15

**Success Criteria**:

- All Tier 1 tests pass
- Coverage ≥70%
- ΔQ improvement: +300 points

### Sprint 2: Complete Top-5 Refactoring (2 weeks)

**Goals**:

- ✅ Refactor cli.py, gate.py, refactoring.py (T1.1, complete)

**Deliverables**:

- ✅ cli.py split into commands/ module
- ✅ gate.py CCN: 23→<15
- ✅ refactoring.py CCN: 21→<15

**Success Criteria**:

- All Top-5 tasks completed
- Coverage ≥75%
- Total ΔQ improvement: +589 points

### Sprint 3: IDE Integration (2 weeks)

**Goals**:

- ✅ VSCode extension MVP (T2.1)

**Deliverables**:

- ✅ Inline CCN display (CodeLens)
- ✅ Quick-jump to recommendations
- ✅ Basic refactoring actions

**Success Criteria**:

- Extension published to VSCode Marketplace
- ≥50 installs in first week
- Positive user feedback

### Sprint 4: Multi-Language Support (3 weeks)

**Goals**:

- ✅ Add JavaScript/TypeScript support (T2.2)

**Deliverables**:

- ✅ ESLint integration
- ✅ Per-function metrics for JS/TS
- ✅ refactoring-plan support for JS/TS

**Success Criteria**:

- Analyze 5+ popular JS/TS repos
- Metrics match ESLint output
- Coverage ≥70% for new code

### Sprint 5+: Advanced Features (ongoing)

- T2.3: Auto-Refactoring (4 weeks)
- T3.1: ML Smell Detection (6 weeks)
- T3.2: Quality Certificates (2 weeks)
- T3.3: SPARQL Queries (2 weeks)

---

## Immediate Next Steps (Next 48 hours)

### Step 1: Fix tmp/ Pollution ✅ URGENT

```bash
# 1. Remove all tmp/ directories
rm -rf tmp/

# 2. Add .gitignore entry
echo "tmp/" >> .gitignore

# 3. Fix exclude logic in structure.py
# (см. T1.2 выше)

# 4. Run fresh analysis
repoq analyze . -o baseline-clean.jsonld --extensions py

# 5. Verify no tmp/ files
python3 -c "
import json
data = json.load(open('baseline-clean.jsonld'))
tmp_files = [f['path'] for f in data.get('files', []) if 'tmp/' in f['path']]
assert len(tmp_files) == 0, f'Found {len(tmp_files)} tmp/ files!'
print('✅ No tmp/ pollution!')
"
```

### Step 2: Start T1.1 - Refactor history.py ✅ HIGH PRIORITY

```bash
# 1. Create tracking document
touch docs/vdad/task-t1.1-history-refactoring.md

# 2. Baseline measurement
repoq analyze . -o baseline-history.jsonld
# Extract history.py metrics: _run_pydriller CCN=35, _run_git CCN=30

# 3. Apply refactoring plan
# - Extract _collect_commits() from _run_pydriller()
# - Extract _process_commit() from _run_pydriller()
# - Extract _parse_git_blame() from _run_git()

# 4. Measure after each step
repoq analyze . -o after-history-step1.jsonld
# Verify CCN reduction

# 5. Run tests
pytest tests/analyzers/test_history.py -v

# 6. Commit
git add repoq/analyzers/history.py tests/
git commit -m "refactor(history): extract functions (T1.1 Step 1)

- Extract _collect_commits() from _run_pydriller()
- Reduce CCN: 35→28
- Add tests for extracted function

Ref: docs/vdad/improvement-roadmap.md (T1.1)"
```

### Step 3: Implement T1.3 - Per-Function ΔQ ✅ HIGH PRIORITY

```bash
# 1. Extend FunctionMetrics dataclass
# (см. T1.3 выше)

# 2. Add _estimate_function_delta_q() to refactoring.py

# 3. Update generate_recommendations() to show per-function ΔQ

# 4. Test
repoq analyze . -o test.jsonld
repoq refactor-plan test.jsonld -o plan-with-delta-q.md
# Verify output shows per-function ΔQ

# 5. Commit
git add repoq/core/model.py repoq/refactoring.py
git commit -m "feat: Add per-function ΔQ estimation (T1.3)

- Extend FunctionMetrics with expected_delta_q field
- Compute ΔQ based on CCN reduction + LOC + file impact
- Show per-function ΔQ in refactor-plan

Example:
'Refactor function _run_command (CCN=26) → ΔQ: +85.0 (78% of file)'

Ref: docs/vdad/improvement-roadmap.md (T1.3)"
```

---

## Success Metrics (Q4 2025)

**Code Quality**:

- ✅ Average file CCN: <15 (current: ~25)
- ✅ Max function CCN: <20 (current: 35)
- ✅ Test coverage: ≥80% (current: 63%)

**Features**:

- ✅ Per-function ΔQ estimation
- ✅ IDE integration (VSCode)
- ✅ Multi-language support (Python + JS/TS)

**Adoption**:

- ✅ ≥100 VSCode extension installs
- ✅ ≥10 external projects using RepoQ
- ✅ ≥5 contributors

**Documentation**:

- ✅ Complete API docs
- ✅ Tutorial: "Refactoring with RepoQ"
- ✅ Case study: "Dogfooding meta-level"

---

## Заключение

**Roadmap summary**:

- **Tier 1** (CRITICAL): Fix technical debt + foundation (30-54h)
- **Tier 2** (HIGH): Usability + extensibility (65-90h)
- **Tier 3** (MEDIUM): Advanced features (37-45h)
- **Tier 4** (LOW): Research + experiments (75-100h)

**Total effort**: 207-289 hours (~5-7 months при 10h/week)

**Next immediate actions**:

1. ✅ Fix tmp/ pollution (4-6h) — URGENT
2. ✅ Refactor history.py (8-10h) — HIGH
3. ✅ Add per-function ΔQ (6-8h) — HIGH

**Philosophy**:
> "A system for synthesis should be able to synthesize improvements to itself."

Этот roadmap — демонстрация **рефлексивной полноты**: RepoQ анализирует себя → находит проблемы → генерирует план улучшений → реализует улучшения → снова анализирует себя.

**TRUE meta-level dogfooding!** 🚀

---

**Автор**: AI Senior Engineer (Σ→Γ→𝒫→Λ→R methodology)  
**Дата**: 2025-10-22  
**Версия**: 1.0  
**Статус**: READY FOR EXECUTION  
**Tracking**: docs/vdad/improvement-roadmap.md
