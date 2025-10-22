# GitStatusAnalyzer

**Module:** `repoq/analyzers/git_status.py`  
**Purpose:** Детектирует состояние git-репозитория для обеспечения воспроизводимости анализа  
**Phase:** Structure (запускается после StructureAnalyzer)

---

## Обзор

`GitStatusAnalyzer` проверяет чистоту git-репозитория перед анализом, выявляя:

- Незакоммиченные изменения (staged/unstaged)
- Неотслеживаемые файлы (untracked)
- Merge-конфликты
- Detached HEAD состояние
- Расхождение с remote-веткой (ahead/behind)

**Цель:** Гарантировать, что анализ проводится на фиксированном состоянии кода, предупредить о временных изменениях, которые могут повлиять на результаты.

---

## Архитектура

### Формальная модель

```text
Σ (Signature):
  - Input: Project(root_path: Path)
  - Output: GitStatusReport + List[Issue]
  - Git commands: status --porcelain=v2, symbolic-ref, rev-parse, rev-list

Γ (Gates):
  ✓ Soundness: все git-команды детерминированы, не изменяют состояние
  ✓ Termination: все команды имеют timeout (subprocess default)
  ✓ Orthogonality: независим от других анализаторов
  ✓ Idempotence: повторный запуск даёт тот же результат

𝒫 (Options):
  1. git status --porcelain=v2 (machine-readable, structured output)
  2. Альтернатива: git diff-index + ls-files (более низкоуровневый)
  → Выбор: porcelain=v2 (стабильный API, полная информация)

Λ (Aggregation):
  - Soundness: 1.0 (git — доверенный источник)
  - Performance: 0.9 (быстрые команды)
  - Maintainability: 0.8 (зависимость от git CLI)
  → Total score: 0.9

R (Result): Реализация GitStatusAnalyzer с 6 типами Issue
```

---

## Типы Issue

| Type                       | Severity | Условие                          |
|----------------------------|----------|----------------------------------|
| `GitUncommittedChanges`    | Major    | staged_count + unstaged_count > 0 |
| `GitUntrackedFiles`        | Minor    | untracked_count > 0              |
| `GitMergeConflicts`        | Critical | conflicted_count > 0             |
| `GitDetachedHead`          | Major    | HEAD не указывает на ветку       |
| `GitBranchAhead`           | Minor    | локальная ветка опережает remote |
| `GitBranchBehind`          | Minor    | remote опережает локальную ветку |

---

## Реализация

### Ключевые методы

#### `_parse_git_status(repo_dir: Path) -> GitStatusReport`

Парсинг `git status --porcelain=v2`:

```python
# Format: <XY> <sub> <mH> <mI> <mW> <hH> <hI> <path>
# XY: staged/unstaged status
#   1 = ordinary changed entries
#   2 = renamed/copied entries
#   u = unmerged entries
#   ? = untracked entries
```

**Примеры:**

- `1 .M N... 100644 100644 100644 abc123 def456 file.py` → unstaged modification
- `1 A. N... 000000 100644 100644 000000 abc123 new.py` → staged addition
- `? file.txt` → untracked file
- `u UU N... 100644 100644 100644 abc123 def456 conflict.py` → merge conflict

#### `_check_head_state(repo_dir: Path) -> Optional[str]`

Проверка detached HEAD:

```bash
git symbolic-ref --short HEAD
# Если returncode != 0 → detached HEAD
```

#### `_check_tracking_status(repo_dir: Path, branch: str) -> tuple[int, int]`

Расчёт ahead/behind:

```bash
# 1. Получить upstream branch
git rev-parse --abbrev-ref {branch}@{upstream}

# 2. Подсчитать коммиты
git rev-list --left-right --count {branch}...{upstream}
# Output: "3\t5" → 3 ahead, 5 behind
```

---

## Интеграция в pipeline

```python
# repoq/pipeline.py
def run_structure_analysis(project: Project, config: Config):
    # 1. StructureAnalyzer (сканирует файлы)
    structure_analyzer = StructureAnalyzer()
    structure_analyzer.run(project, config)
    
    # 2. GitStatusAnalyzer (проверяет состояние репо)
    git_status_analyzer = GitStatusAnalyzer()
    git_status_analyzer.run(project, config)
    
    # 3. ComplexityAnalyzer (анализирует сложность)
    # ...
```

**Обоснование порядка:** GitStatusAnalyzer запускается **после** StructureAnalyzer, так как не зависит от списка файлов, но логически входит в фазу структурного анализа.

---

## Тестирование

**Файл:** `tests/unit/test_git_status.py`  
**Покрытие:** 8 тестов

### Тест-кейсы

1. **test_clean_repository**: Проверка чистого репозитория

   ```python
   report = analyzer._analyze_git_status(project.root)
   assert report.is_clean
   assert len(report.staged_files) == 0
   ```

2. **test_uncommitted_changes_staged**: Staged изменения

   ```python
   # git add file.txt
   report = analyzer._analyze_git_status(repo_path)
   assert not report.is_clean
   assert len(report.staged_files) == 1
   ```

3. **test_uncommitted_changes_unstaged**: Unstaged изменения

   ```python
   # echo "change" >> file.txt
   report = analyzer._analyze_git_status(repo_path)
   assert len(report.unstaged_files) == 1
   ```

4. **test_untracked_files**: Неотслеживаемые файлы

   ```python
   (repo_path / "untracked.txt").write_text("content")
   report = analyzer._analyze_git_status(repo_path)
   assert len(report.untracked_files) == 1
   ```

5. **test_detached_head**: Detached HEAD

   ```python
   # git checkout <commit-sha>
   detached_msg = analyzer._check_head_state(repo_path)
   assert detached_msg and "detached" in detached_msg.lower()
   ```

6. **test_branch_tracking**: Ahead/Behind расчёт

   ```python
   # git checkout -b branch && git commit
   ahead, behind = analyzer._check_tracking_status(repo_path, "branch")
   assert ahead > 0
   ```

---

## Конфигурация

GitStatusAnalyzer не требует дополнительных настроек в `repoq.toml`, но учитывает:

```toml
[general]
root = "."  # Корень репозитория для git-команд
```

---

## Ограничения и будущие улучшения

### Текущие ограничения

1. **Git CLI dependency**: Требует установленный git в PATH
2. **No stash detection**: Не проверяет наличие stashed changes
3. **No submodule tracking**: Игнорирует состояние submodules

### Roadmap

- [ ] Детектирование git stash (непримененные изменения)
- [ ] Проверка submodules dirty state
- [ ] Интеграция с git hooks (pre-commit, pre-push)
- [ ] Опциональная блокировка анализа при dirty state
- [ ] Автоматическое создание snapshot commit перед анализом

---

## Рефлексивность

GitStatusAnalyzer **демонстрирует рефлексивную способность** системы:

```python
# Self-analysis результаты:
{
  "issues": [
    {
      "@type": "repo:GitUncommittedChanges",
      "description": "Repository has 2 uncommitted changes (0 staged, 2 unstaged)",
      "severity": "Major"
    },
    {
      "@type": "repo:GitUntrackedFiles", 
      "description": "Repository has 4 untracked files. Examples: repoq/analyzers/git_status.py, ...",
      "severity": "Minor"
    }
  ]
}
```

**Вывод:** RepoQ успешно обнаружил собственные новые файлы (git_status.py, doc_code_sync.py) и незакоммиченные изменения в pipeline.py/cli.py во время self-analysis.

---

## Связь с TRS Framework

GitStatusAnalyzer НЕ использует TRS напрямую, но следует архитектурным принципам:

- **Детерминированность**: Git-команды не изменяют состояние (read-only)
- **Терминация**: Все команды завершаются за O(files) времени
- **Звуковость**: Git-статус является ground truth для состояния репозитория
- **Конфлюэнтность**: Порядок проверок не влияет на результат

---

## Примеры использования

### CLI

```bash
# Анализ с проверкой git status
repoq analyze . --mode structure

# Если обнаружены uncommitted changes:
# ⚠️  WARNING: Repository has uncommitted changes
# ⚠️  Commit changes before analysis for reproducible results
```

### Programmatic

```python
from repoq.analyzers.git_status import GitStatusAnalyzer
from repoq.core.model import Project

project = Project(id="myproject", root=Path("."))
analyzer = GitStatusAnalyzer()
analyzer.run(project, config)

# Проверка результатов
git_issues = [i for i in project.issues.values() 
              if i.type.startswith("repo:Git")]
for issue in git_issues:
    print(f"{issue.type}: {issue.description}")
```

---

## Ссылки

- **Код:** [`repoq/analyzers/git_status.py`](../../repoq/analyzers/git_status.py)
- **Тесты:** [`tests/unit/test_git_status.py`](../../tests/unit/test_git_status.py)
- **Git Porcelain Format:** [git-status documentation](https://git-scm.com/docs/git-status#_porcelain_format_version_2)
- **Related:** [ArchitectureAnalyzer](architecture-analyzer.md), [Analyzer Pipeline](analyzer-pipeline.md)
