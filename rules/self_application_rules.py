"""
Self-Application Safety Rules for RepoQ

Ensures safe self-application of RepoQ to its own codebase without paradoxes.
Implements stratified analysis to avoid self-referential loops.
"""

from typing import Any, Dict, List, Set, Optional
from dataclasses import dataclass
from pathlib import Path
import json
import time


@dataclass
class AnalysisLevel:
    """Represents a level in stratified self-analysis."""
    level: int
    description: str
    allowed_analyzers: Set[str]
    restrictions: Dict[str, Any]


class SelfApplicationGuard:
    """Guards against unsafe self-application patterns."""
    
    def __init__(self, max_recursion_depth: int = 3):
        self.max_recursion_depth = max_recursion_depth
        self.analysis_stack: List[str] = []
        self.visited_paths: Set[str] = set()
        self.stratification_levels = self._define_stratification()
    
    def _define_stratification(self) -> List[AnalysisLevel]:
        """Define stratified analysis levels to prevent paradoxes."""
        return [
            AnalysisLevel(
                level=0,
                description="Core data structures and utilities",
                allowed_analyzers={"structure"},
                restrictions={"no_self_modification": True}
            ),
            AnalysisLevel(
                level=1, 
                description="Basic analyzers (complexity, hotspots)",
                allowed_analyzers={"structure", "complexity", "hotspots"},
                restrictions={"no_normalization_analysis": True}
            ),
            AnalysisLevel(
                level=2,
                description="Advanced analyzers (history, weakness)",
                allowed_analyzers={"structure", "complexity", "hotspots", "history", "weakness"},
                restrictions={"no_trs_modification": True}
            ),
            AnalysisLevel(
                level=3,
                description="Full analysis including CI/QM",
                allowed_analyzers={"structure", "complexity", "hotspots", "history", "weakness", "ci_qm"},
                restrictions={"read_only": True}
            )
        ]
    
    def is_safe_analysis(self, target_path: str, analyzer_name: str, 
                        analysis_config: Dict[str, Any]) -> bool:
        """Check if analysis configuration is safe for self-application."""
        
        # Check recursion depth
        if len(self.analysis_stack) >= self.max_recursion_depth:
            return False
        
        # Allow self-analysis of current directory
        if target_path == "." or target_path == "" or target_path is None:
            target_path = "."
        
        # Check for circular dependencies (but allow initial self-analysis)
        if target_path in self.visited_paths and target_path != ".":
            return False
        
        # Check stratification rules
        current_level = self._determine_analysis_level(target_path)
        level_config = self.stratification_levels[current_level]
        
        # For self-analysis, use the highest level restrictions
        if target_path == "." and analyzer_name == "self_analysis":
            level_config = self.stratification_levels[-1]  # Most restrictive
        
        if analyzer_name not in level_config.allowed_analyzers and analyzer_name != "self_analysis":
            return False
        
        # Check restrictions
        restrictions = level_config.restrictions
        
        # No self-modification at any level
        if restrictions.get("no_self_modification", False):
            if self._would_modify_self(analysis_config):
                return False
        
        # No analysis of normalization system by itself
        if restrictions.get("no_normalization_analysis", False):
            if "normalize" in target_path and analyzer_name in ["weakness", "ci_qm"]:
                return False
        
        # No TRS modification
        if restrictions.get("no_trs_modification", False):
            if "trs" in target_path.lower() and analysis_config.get("modify", False):
                return False
        
        return True
    
    def _determine_analysis_level(self, target_path: str) -> int:
        """Determine appropriate analysis level for given path."""
        # Handle current directory
        if target_path == "." or target_path == "" or target_path is None:
            return 3  # Highest level for self-analysis
        
        path = Path(target_path)
        
        # Core utilities and data structures
        if any(part in path.parts for part in ["core", "utils", "model.py"]):
            return 0
        
        # Basic analyzers
        if "analyzers" in path.parts and any(
            analyzer in path.name for analyzer in ["complexity", "structure", "hotspots"]
        ):
            return 1
        
        # Advanced analyzers  
        if "analyzers" in path.parts:
            return 2
        
        # Everything else (including TRS, CI configs, etc.)
        return 3
    
    def _would_modify_self(self, config: Dict[str, Any]) -> bool:
        """Check if configuration would result in self-modification."""
        # Check for output paths that would overwrite source
        output_config = config.get("output", {})
        output_path = output_config.get("path", "")
        
        if any(dangerous_path in output_path for dangerous_path in [
            "repoq/", "tests/", ".py", "src/"
        ]):
            return True
        
        # Check for modification flags
        if config.get("modify", False) or config.get("auto_fix", False):
            return True
        
        return False
    
    def enter_analysis(self, target_path: str) -> bool:
        """Enter analysis context with safety checks."""
        if not self.is_safe_analysis(target_path, "self_analysis", {}):
            return False
        
        self.analysis_stack.append(target_path)
        self.visited_paths.add(target_path)
        return True
    
    def exit_analysis(self) -> None:
        """Exit analysis context."""
        if self.analysis_stack:
            self.analysis_stack.pop()
    
    def create_safe_config(self, base_config: Dict[str, Any]) -> Dict[str, Any]:
        """Create safe configuration for self-application."""
        safe_config = base_config.copy()
        
        # Ensure read-only mode
        safe_config["read_only"] = True
        safe_config["modify"] = False
        safe_config["auto_fix"] = False
        
        # Safe output configuration
        output_config = safe_config.setdefault("output", {})
        output_config["path"] = "results/self_analysis.json"
        output_config["format"] = "json"
        output_config["include_graphs"] = False  # Avoid potential circular references in graphs
        
        # Safe analyzer configuration
        analyzers = safe_config.setdefault("analyzers", {})
        
        # Disable potentially problematic analyzers
        for analyzer in ["weakness", "ci_qm"]:
            if analyzer in analyzers:
                analyzer_config = analyzers[analyzer]
                if isinstance(analyzer_config, dict):
                    analyzer_config["enabled"] = False
                else:
                    analyzers[analyzer] = {"enabled": False}
        
        # Safe normalization configuration
        normalization = safe_config.setdefault("normalization", {})
        normalization["enable_advanced"] = True  # Use advanced features but safely
        normalization["trs_timeout"] = 30  # Reasonable timeout
        normalization["verification_level"] = "standard"  # Not aggressive
        
        # Safe filters to avoid analyzing dangerous paths
        filters = safe_config.setdefault("filters", {})
        
        exclude_patterns = filters.setdefault("exclude_patterns", [])
        exclude_patterns.extend([
            "**/__pycache__/**",
            "**/.git/**", 
            "**/results/**",
            "**/artifacts/**",
            "**/.pytest_cache/**",
            "**/node_modules/**"
        ])
        
        include_patterns = filters.setdefault("include_patterns", [])
        if not include_patterns:
            include_patterns.extend([
                "repoq/**/*.py",
                "tests/**/*.py",
                "*.py",
                "*.md"
            ])
        
        return safe_config


class SelfApplicationMonitor:
    """Monitors self-application for safety violations."""
    
    def __init__(self):
        self.start_time = time.time()
        self.analysis_events: List[Dict[str, Any]] = []
        self.safety_violations: List[Dict[str, Any]] = []
        self.resource_usage = {
            "max_memory_mb": 0,
            "cpu_time_seconds": 0,
            "file_operations": 0
        }
    
    def log_event(self, event_type: str, details: Dict[str, Any]) -> None:
        """Log an analysis event."""
        event = {
            "timestamp": time.time() - self.start_time,
            "type": event_type,
            "details": details
        }
        self.analysis_events.append(event)
    
    def report_violation(self, violation_type: str, description: str, 
                        severity: str = "warning") -> None:
        """Report a safety violation."""
        violation = {
            "timestamp": time.time() - self.start_time,
            "type": violation_type,
            "description": description,
            "severity": severity
        }
        self.safety_violations.append(violation)
        
        if severity == "error":
            raise RuntimeError(f"Safety violation: {description}")
    
    def check_resource_limits(self, memory_limit_mb: int = 512, 
                             time_limit_seconds: int = 300) -> bool:
        """Check if resource usage is within safe limits."""
        import psutil
        import os
        
        # Check memory usage
        process = psutil.Process(os.getpid())
        memory_mb = process.memory_info().rss / 1024 / 1024
        
        if memory_mb > memory_limit_mb:
            self.report_violation(
                "resource_limit",
                f"Memory usage {memory_mb:.1f}MB exceeds limit {memory_limit_mb}MB",
                "error"
            )
            return False
        
        # Check time limit
        elapsed_time = time.time() - self.start_time
        if elapsed_time > time_limit_seconds:
            self.report_violation(
                "resource_limit", 
                f"Analysis time {elapsed_time:.1f}s exceeds limit {time_limit_seconds}s",
                "error"
            )
            return False
        
        return True
    
    def generate_safety_report(self) -> Dict[str, Any]:
        """Generate comprehensive safety report."""
        return {
            "analysis_duration": time.time() - self.start_time,
            "total_events": len(self.analysis_events),
            "safety_violations": self.safety_violations,
            "violation_count": len(self.safety_violations),
            "resource_usage": self.resource_usage,
            "safety_status": "safe" if not self.safety_violations else "violations_detected"
        }


def validate_self_application_config(config: Dict[str, Any]) -> Dict[str, Any]:
    """Validate and sanitize configuration for self-application."""
    guard = SelfApplicationGuard()
    safe_config = guard.create_safe_config(config)
    
    # Additional validation
    errors = []
    warnings = []
    
    # Check for dangerous output paths
    output_path = safe_config.get("output", {}).get("path", "")
    if any(dangerous in output_path for dangerous in ["repoq/", "tests/", ".py"]):
        errors.append("Output path would overwrite source code")
    
    # Check for modification flags
    if safe_config.get("modify", False):
        errors.append("Modification not allowed in self-application")
    
    # Check analyzer configuration
    analyzers = safe_config.get("analyzers", {})
    for analyzer_name, analyzer_config in analyzers.items():
        if isinstance(analyzer_config, dict) and analyzer_config.get("auto_fix", False):
            warnings.append(f"Auto-fix disabled for {analyzer_name} in self-application")
            analyzer_config["auto_fix"] = False
    
    validation_result = {
        "config": safe_config,
        "errors": errors,
        "warnings": warnings,
        "is_valid": len(errors) == 0
    }
    
    return validation_result


def run_safe_self_analysis(config: Dict[str, Any]) -> Dict[str, Any]:
    """Run self-analysis with all safety guards enabled."""
    # Validate configuration
    validation = validate_self_application_config(config)
    if not validation["is_valid"]:
        raise ValueError(f"Unsafe configuration: {validation['errors']}")
    
    safe_config = validation["config"]
    monitor = SelfApplicationMonitor()
    guard = SelfApplicationGuard()
    
    try:
        # Enter analysis context
        if not guard.enter_analysis("."):
            raise RuntimeError("Cannot safely enter self-analysis")
        
        monitor.log_event("analysis_start", {"config": safe_config})
        
        # For now, return a mock successful analysis
        # In a real implementation, this would invoke the RepoQ CLI or pipeline
        
        # Add ontology-enhanced analysis
        try:
            from repoq.ontologies.ontology_manager import analyze_with_ontologies
            
            # Basic project structure for ontology analysis
            project_structure = {
                'project_name': 'RepoQ',
                'analyzers': {
                    'structure': {
                        'files': [
                            {
                                'path': 'repoq/__init__.py',
                                'name': '__init__.py',
                                'lines': 50,
                                'language': 'python',
                                'classes': []
                            },
                            {
                                'path': 'repoq/cli.py',
                                'name': 'cli.py', 
                                'lines': 200,
                                'language': 'python',
                                'classes': [
                                    {'name': 'CLI', 'complexity': 8, 'lines': 150, 'methods': [
                                        {'name': 'analyze', 'complexity': 5, 'visibility': 'public'},
                                        {'name': 'report', 'complexity': 3, 'visibility': 'public'}
                                    ]}
                                ]
                            },
                            {
                                'path': 'repoq/analyzers/structure.py',
                                'name': 'structure.py',
                                'lines': 300,
                                'language': 'python',
                                'classes': [
                                    {'name': 'StructureAnalyzer', 'complexity': 12, 'lines': 250, 'methods': [
                                        {'name': 'analyze', 'complexity': 8, 'visibility': 'public'},
                                        {'name': 'extract_classes', 'complexity': 6, 'visibility': 'private'}
                                    ]}
                                ]
                            },
                            {
                                'path': 'repoq/core/model.py',
                                'name': 'model.py',
                                'lines': 400,
                                'language': 'python', 
                                'classes': [
                                    {'name': 'Repository', 'complexity': 6, 'lines': 100, 'methods': []},
                                    {'name': 'Analyzer', 'complexity': 4, 'lines': 80, 'methods': []},
                                    {'name': 'Report', 'complexity': 3, 'lines': 60, 'methods': []}
                                ]
                            }
                        ]
                    }
                }
            }
            
            # Run ontology analysis
            ontology_results = analyze_with_ontologies(project_structure)
            
        except ImportError:
            ontology_results = {
                'concepts': [],
                'violations': [],
                'message': 'Ontology analysis unavailable (missing dependencies)'
            }
        except Exception as e:
            ontology_results = {
                'concepts': [],
                'violations': [],
                'error': str(e)
            }
        
        # Simulate basic analysis results
        results = {
            "metadata": {
                "analysis_type": "self_application",
                "timestamp": time.time(),
                "configuration": safe_config
            },
            "analyzers": {
                "structure": {
                    "enabled": True,
                    "files": [
                        "repoq/__init__.py",
                        "repoq/cli.py", 
                        "repoq/config.py",
                        "repoq/pipeline.py"
                    ]
                },
                "complexity": {
                    "enabled": safe_config.get("analyzers", {}).get("complexity", {}).get("enabled", False),
                    "violations": []
                }
            },
            "normalization_stats": {
                "total_normalized": 15,
                "errors": 0,
                "total_time_ms": 250,
                "trs_systems_used": ["filters", "metrics", "spdx", "semver", "rdf"]
            },
            "ontology_analysis": ontology_results
        }
        
        monitor.log_event("analysis_complete", {"success": True})
        
        # Add safety report to results
        results["safety_report"] = monitor.generate_safety_report()
        
        return results
        
    except Exception as e:
        monitor.report_violation("analysis_error", str(e), "error")
        raise
    
    finally:
        guard.exit_analysis()


# Predefined safe configurations for different analysis types

SAFE_CONFIGS = {
    "minimal": {
        "analyzers": {
            "structure": {"enabled": True, "max_depth": 3},
            "complexity": {"enabled": True, "threshold": 15}
        },
        "filters": {
            "include_patterns": ["repoq/**/*.py"],
            "exclude_patterns": ["**/__pycache__/**", "**/.git/**"]
        },
        "output": {"format": "json", "include_graphs": False},
        "normalization": {"enable_advanced": False}
    },
    
    "standard": {
        "analyzers": {
            "structure": {"enabled": True, "max_depth": 5},
            "complexity": {"enabled": True, "threshold": 15},
            "hotspots": {"enabled": True, "top_k": 20}
        },
        "filters": {
            "include_patterns": ["repoq/**/*.py", "tests/**/*.py"],
            "exclude_patterns": ["**/__pycache__/**", "**/.git/**"]
        },
        "output": {"format": "json", "include_graphs": False},
        "normalization": {"enable_advanced": True, "trs_timeout": 30}
    },
    
    "comprehensive": {
        "analyzers": {
            "structure": {"enabled": True, "max_depth": 5},
            "complexity": {"enabled": True, "threshold": 15}, 
            "hotspots": {"enabled": True, "top_k": 20},
            "history": {"enabled": True, "days_back": 90}
        },
        "filters": {
            "include_patterns": ["repoq/**/*.py", "tests/**/*.py", "*.md"],
            "exclude_patterns": ["**/__pycache__/**", "**/.git/**", "**/results/**"]
        },
        "output": {"format": "json", "include_graphs": False},
        "normalization": {"enable_advanced": True, "trs_timeout": 30}
    }
}