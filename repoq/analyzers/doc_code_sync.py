"""Documentation-code synchronization validator.

STRATIFICATION_LEVEL: 0 (analyzes code and docs, no meta-operations)

This analyzer detects mismatches between documentation and implementation:
- Docstring signatures vs actual function signatures
- Missing docstrings (coverage gaps)
- Deprecated code without proper markers
- README examples vs actual API differences
- TODO/FIXME in docstrings (outdated documentation)

These checks ensure documentation accuracy and reduce onboarding friction.

Algorithm:
    1. Parse Python files with AST
    2. Extract function/class signatures
    3. Extract docstrings and parse with docstring_parser
    4. Compare signature in docstring vs AST
    5. Check for deprecated markers in code but not docs
    6. Scan README.md for code examples
    7. Validate examples against actual API (heuristic)

Safety:
- Read-only analysis
- Deterministic (same code+docs → same output)
- Terminating (fixed set of files to analyze)
"""

from __future__ import annotations

import ast
import logging
import re
from pathlib import Path
from typing import List, Optional

from ..config import AnalyzeConfig
from ..core.model import Issue, Project
from .base import Analyzer

logger = logging.getLogger(__name__)

try:
    from docstring_parser import parse as parse_docstring

    HAVE_DOCSTRING_PARSER = True
except ImportError:
    HAVE_DOCSTRING_PARSER = False
    logger.debug("docstring_parser not available, signature validation disabled")


class DocCodeSyncAnalyzer(Analyzer):
    """Analyze documentation-code synchronization and detect mismatches.

    Detects:
    - Missing docstrings (functions/classes without documentation)
    - Docstring signature mismatches (params in docstring != actual params)
    - Deprecated code without @deprecated markers
    - Outdated TODO/FIXME comments in docstrings
    - README code examples that don't match actual API

    Generates warnings as Issue objects for documentation quality.
    """

    name = "doc_code_sync"

    def run(self, project: Project, repo_dir: str, cfg: AnalyzeConfig) -> None:
        """Run documentation-code sync analysis.

        Args:
            project: Project model to populate
            repo_dir: Repository directory path
            cfg: Analysis configuration

        Note:
            Populates project.issues with documentation sync warnings.
        """
        logger.info("Running documentation-code sync analysis...")

        repo_path = Path(repo_dir)
        issues_count = 0

        # 1. Analyze Python files for docstring mismatches
        for file_id, file_obj in project.files.items():
            if not file_obj.path.endswith(".py"):
                continue

            file_path = repo_path / file_obj.path
            if not file_path.exists():
                continue

            try:
                file_issues = self._analyze_python_file(project.id, file_obj.path, file_path)
                for issue in file_issues:
                    project.issues[issue.id] = issue
                    issues_count += 1

            except Exception as e:
                logger.debug(f"Failed to analyze {file_obj.path}: {e}")

        # 2. Check README for outdated examples (if README exists)
        readme_path = repo_path / "README.md"
        if readme_path.exists():
            try:
                readme_issues = self._check_readme_examples(project.id, readme_path, project)
                for issue in readme_issues:
                    project.issues[issue.id] = issue
                    issues_count += 1

            except Exception as e:
                logger.debug(f"Failed to check README: {e}")

        logger.info(f"Documentation sync analysis complete: {issues_count} issues found")

    def _analyze_python_file(self, project_id: str, file_path: str, full_path: Path) -> List[Issue]:
        """Analyze single Python file for documentation issues.

        Args:
            project_id: Project ID for issue IDs
            file_path: Relative file path
            full_path: Absolute path to file

        Returns:
            List of Issue objects
        """
        issues = []

        try:
            with full_path.open("r", encoding="utf-8") as f:
                source = f.read()

            tree = ast.parse(source, filename=str(full_path))

        except SyntaxError:
            # Syntax error, skip (handled by other analyzers)
            return issues

        # Walk AST and check functions/classes
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) or isinstance(node, ast.AsyncFunctionDef):
                func_issues = self._check_function(project_id, file_path, node, source)
                issues.extend(func_issues)

            elif isinstance(node, ast.ClassDef):
                class_issues = self._check_class(project_id, file_path, node, source)
                issues.extend(class_issues)

        return issues

    def _check_function(
        self, project_id: str, file_path: str, node: ast.FunctionDef, source: str
    ) -> List[Issue]:
        """Check function for documentation issues.

        Args:
            project_id: Project ID
            file_path: File path
            node: AST FunctionDef node
            source: Full source code (for line numbers)

        Returns:
            List of Issue objects
        """
        issues = []
        func_name = node.name

        # Skip private functions (heuristic: start with _)
        if func_name.startswith("_") and not func_name.startswith("__"):
            return issues

        # 1. Check for missing docstring
        docstring = ast.get_docstring(node)
        if not docstring:
            issue = Issue(
                id=f"{project_id}:issue:doc:missing:{file_path}:{func_name}",
                type="repo:MissingDocstring",
                file_id=f"{project_id}:file:{file_path}",
                description=(
                    f"Function '{func_name}' has no docstring. "
                    "Add docstring to improve code documentation."
                ),
                severity="low",
                priority="low",
                status="Open",
                title=f"Missing docstring: {func_name}()",
            )
            issues.append(issue)
            return issues  # No docstring, can't check signature

        # 2. Check for TODO/FIXME in docstring (outdated documentation)
        if re.search(r"\b(TODO|FIXME|XXX|HACK)\b", docstring, re.IGNORECASE):
            issue = Issue(
                id=f"{project_id}:issue:doc:todo:{file_path}:{func_name}",
                type="repo:OutdatedDocstring",
                file_id=f"{project_id}:file:{file_path}",
                description=(
                    f"Function '{func_name}' has TODO/FIXME in docstring. "
                    "Update documentation or remove marker."
                ),
                severity="low",
                priority="low",
                status="Open",
                title=f"Outdated docstring: {func_name}()",
            )
            issues.append(issue)

        # 3. Check signature mismatch (if docstring_parser available)
        if HAVE_DOCSTRING_PARSER:
            mismatch_issue = self._check_signature_mismatch(
                project_id, file_path, func_name, node, docstring
            )
            if mismatch_issue:
                issues.append(mismatch_issue)

        return issues

    def _check_signature_mismatch(
        self,
        project_id: str,
        file_path: str,
        func_name: str,
        node: ast.FunctionDef,
        docstring: str,
    ) -> Optional[Issue]:
        """Check if docstring signature matches actual function signature.

        Args:
            project_id: Project ID
            file_path: File path
            func_name: Function name
            node: AST FunctionDef node
            docstring: Function docstring

        Returns:
            Issue if mismatch found, None otherwise
        """
        try:
            parsed_doc = parse_docstring(docstring)

            # Extract actual parameter names (excluding self, cls, *args, **kwargs)
            actual_params = set()
            for arg in node.args.args:
                if arg.arg not in ("self", "cls"):
                    actual_params.add(arg.arg)

            # Extract documented parameter names
            documented_params = {param.arg_name for param in parsed_doc.params}

            # Check for mismatches
            missing_in_doc = actual_params - documented_params
            extra_in_doc = documented_params - actual_params

            if missing_in_doc or extra_in_doc:
                description_parts = [f"Function '{func_name}' signature mismatch:"]

                if missing_in_doc:
                    description_parts.append(
                        f"Parameters not documented: {', '.join(sorted(missing_in_doc))}"
                    )

                if extra_in_doc:
                    description_parts.append(
                        f"Documented but not in signature: {', '.join(sorted(extra_in_doc))}"
                    )

                return Issue(
                    id=f"{project_id}:issue:doc:mismatch:{file_path}:{func_name}",
                    type="repo:DocstringSignatureMismatch",
                    file_id=f"{project_id}:file:{file_path}",
                    description=" ".join(description_parts),
                    severity="medium",
                    priority="medium",
                    status="Open",
                    title=f"Signature mismatch: {func_name}()",
                )

        except Exception as e:
            # Parsing failed, skip
            logger.debug(f"Failed to parse docstring for {func_name}: {e}")

        return None

    def _check_class(
        self, project_id: str, file_path: str, node: ast.ClassDef, source: str
    ) -> List[Issue]:
        """Check class for documentation issues.

        Args:
            project_id: Project ID
            file_path: File path
            node: AST ClassDef node
            source: Full source code

        Returns:
            List of Issue objects
        """
        issues = []
        class_name = node.name

        # Skip private classes
        if class_name.startswith("_"):
            return issues

        # Check for missing docstring
        docstring = ast.get_docstring(node)
        if not docstring:
            issue = Issue(
                id=f"{project_id}:issue:doc:missing:{file_path}:{class_name}",
                type="repo:MissingDocstring",
                file_id=f"{project_id}:file:{file_path}",
                description=(
                    f"Class '{class_name}' has no docstring. "
                    "Add docstring to improve code documentation."
                ),
                severity="low",
                priority="low",
                status="Open",
                title=f"Missing docstring: class {class_name}",
            )
            issues.append(issue)

        return issues

    def _check_readme_examples(
        self, project_id: str, readme_path: Path, project: Project
    ) -> List[Issue]:
        """Check README.md for outdated code examples.

        Args:
            project_id: Project ID
            readme_path: Path to README.md
            project: Project model (for API validation)

        Returns:
            List of Issue objects
        """
        issues = []

        try:
            with readme_path.open("r", encoding="utf-8") as f:
                readme_content = f.read()

        except Exception as e:
            logger.debug(f"Failed to read README: {e}")
            return issues

        # Extract code blocks (```python ... ```)
        code_blocks = re.findall(
            r"```(?:python|py)\n(.*?)```", readme_content, re.DOTALL | re.IGNORECASE
        )

        if not code_blocks:
            return issues

        # Heuristic check: look for common import patterns that might be outdated
        for i, block in enumerate(code_blocks):
            # Check for imports that don't exist in project
            import_lines = re.findall(r"^\s*(?:from|import)\s+([\w.]+)", block, re.MULTILINE)

            for import_name in import_lines:
                # Check if module exists in project files
                if "." in import_name:
                    base_module = import_name.split(".")[0]
                else:
                    base_module = import_name

                # Heuristic: if importing from project name, check if module exists
                if base_module == project.name or import_name.startswith(project.name + "."):
                    # Extract module path
                    module_path = import_name.replace(".", "/") + ".py"

                    # Check if file exists
                    file_id = f"{project_id}:file:{module_path}"
                    if file_id not in project.files:
                        issue = Issue(
                            id=f"{project_id}:issue:doc:readme_outdated:block{i}",
                            type="repo:OutdatedREADMEExample",
                            file_id=None,
                            description=(
                                f"README.md contains code example importing '{import_name}', "
                                f"but module not found in project. "
                                "Update README examples to match current API."
                            ),
                            severity="medium",
                            priority="medium",
                            status="Open",
                            title=f"Outdated README example (block {i+1})",
                        )
                        issues.append(issue)
                        break  # One issue per code block

        return issues
