# API Reference

!!! info "Comprehensive API"
    RepoQ provides both Python API for programmatic access and REST API for service integration. This reference covers all available interfaces.

## 🐍 Python API

### Core Analysis Classes

#### `StructureAnalyzer`

Main class for structural analysis with ontological intelligence.

```python
from repoq.analyzers.structure import StructureAnalyzer
from repoq.core.model import AnalysisResult

class StructureAnalyzer:
    """Advanced structure analyzer with ontological intelligence."""
    
    def __init__(self, 
                 ontology_enabled: bool = True,
                 pattern_detection: bool = True,
                 cross_inference: bool = True):
        """
        Initialize analyzer with ontological capabilities.
        
        Args:
            ontology_enabled: Enable semantic ontological analysis
            pattern_detection: Detect architectural patterns automatically
            cross_inference: Enable cross-ontology semantic inference
        """
    
    def analyze(self, 
                repo_path: str,
                include_patterns: List[str] = None,
                exclude_patterns: List[str] = None,
                max_depth: int = None) -> AnalysisResult:
        """
        Perform comprehensive structural analysis.
        
        Args:
            repo_path: Path to repository root
            include_patterns: Glob patterns for files to include
            exclude_patterns: Glob patterns for files to exclude  
            max_depth: Maximum directory depth to analyze
            
        Returns:
            AnalysisResult with structural and ontological insights
            
        Example:
            >>> analyzer = StructureAnalyzer(ontology_enabled=True)
            >>> result = analyzer.analyze("/path/to/repo")
            >>> print(f"Detected patterns: {result.detected_patterns}")
            >>> print(f"Architecture score: {result.quality_metrics.architecture_score}")
        """
    
    def analyze_file(self, file_path: str) -> FileAnalysis:
        """Analyze single file with full semantic understanding."""
    
    def detect_patterns(self, analysis_result: AnalysisResult) -> List[ArchitecturalPattern]:
        """Detect architectural patterns in analyzed code."""
```

**Usage Example:**
```python
from repoq.analyzers.structure import StructureAnalyzer

# Initialize with full ontological analysis
analyzer = StructureAnalyzer(
    ontology_enabled=True,
    pattern_detection=True,
    cross_inference=True
)

# Analyze repository
result = analyzer.analyze("/path/to/my-project")

# Access ontological insights
for pattern in result.detected_patterns:
    print(f"Pattern: {pattern.name}")
    print(f"Location: {pattern.location}")
    print(f"Confidence: {pattern.confidence}")
    print(f"Benefits: {pattern.benefits}")

# Access domain model analysis
domain_model = result.ontological_analysis.domain_model
for context in domain_model.bounded_contexts:
    print(f"Context: {context.name}")
    print(f"Entities: {context.entities}")
    print(f"Services: {context.services}")
```

#### `ComplexityAnalyzer`

Advanced complexity analysis with multiple metrics.

```python
from repoq.analyzers.complexity import ComplexityAnalyzer

class ComplexityAnalyzer:
    """Multi-dimensional complexity analysis."""
    
    def analyze(self, repo_path: str) -> ComplexityResult:
        """
        Comprehensive complexity analysis.
        
        Returns:
            ComplexityResult with multiple complexity metrics
        """
    
    def analyze_function(self, func_node: ast.FunctionDef) -> FunctionComplexity:
        """
        Analyze individual function complexity.
        
        Args:
            func_node: AST node representing function
            
        Returns:
            FunctionComplexity with detailed metrics
        """
```

**Usage Example:**
```python
from repoq.analyzers.complexity import ComplexityAnalyzer

analyzer = ComplexityAnalyzer()
result = analyzer.analyze("/path/to/project")

# Access complexity metrics
print(f"Average cyclomatic complexity: {result.avg_cyclomatic}")
print(f"Average cognitive complexity: {result.avg_cognitive}")

# High complexity functions
for func in result.high_complexity_functions:
    print(f"Function: {func.name}")
    print(f"  Cyclomatic: {func.cyclomatic_complexity}")
    print(f"  Cognitive: {func.cognitive_complexity}")
    print(f"  Maintainability: {func.maintainability_index}")
```

### Ontological Intelligence API

#### `OntologyManager`

Central manager for all ontological analysis.

```python
from repoq.ontologies.manager import OntologyManager

class OntologyManager:
    """Manages semantic ontologies and cross-domain inference."""
    
    def __init__(self):
        """Initialize with Code, C4, and DDD ontologies."""
    
    def analyze_project_structure(self, 
                                 structure_result: AnalysisResult) -> OntologicalAnalysis:
        """
        Apply ontological intelligence to structure analysis.
        
        Args:
            structure_result: Basic structural analysis result
            
        Returns:
            OntologicalAnalysis with semantic insights
        """
    
    def detect_architectural_patterns(self, 
                                    structure: ProjectStructure) -> List[ArchitecturalPattern]:
        """Detect patterns using ontological knowledge."""
    
    def analyze_domain_model(self, 
                           structure: ProjectStructure) -> DomainModel:
        """Extract domain-driven design concepts."""
    
    def cross_ontology_inference(self, 
                                concepts: List[Concept]) -> List[SemanticMapping]:
        """Create mappings between different ontological layers."""
```

**Usage Example:**
```python
from repoq.ontologies.manager import OntologyManager
from repoq.analyzers.structure import StructureAnalyzer

# Analyze structure
structure_analyzer = StructureAnalyzer(ontology_enabled=False)
structure_result = structure_analyzer.analyze("/path/to/project")

# Apply ontological intelligence
ontology_manager = OntologyManager()
ontological_analysis = ontology_manager.analyze_project_structure(structure_result)

# Access semantic insights
for mapping in ontological_analysis.semantic_mappings:
    print(f"Mapping: {mapping.source_concept} → {mapping.target_concept}")
    print(f"Relationship: {mapping.relationship_type}")
    print(f"Confidence: {mapping.confidence}")

# Domain-driven design analysis
domain_model = ontological_analysis.domain_model
for context in domain_model.bounded_contexts:
    print(f"\nBounded Context: {context.name}")
    print(f"Entities: {[e.name for e in context.entities]}")
    print(f"Value Objects: {[v.name for v in context.value_objects]}")
    print(f"Services: {[s.name for s in context.services]}")
```

### Data Models

#### `AnalysisResult`

Primary result object containing all analysis data.

```python
@dataclass
class AnalysisResult:
    """Comprehensive analysis result with ontological insights."""
    
    # Basic project information
    project: Project
    timestamp: datetime
    analyzer_version: str
    
    # Structural analysis
    file_structure: List[FileNode]
    dependencies: List[Dependency]
    metrics: ProjectMetrics
    
    # Ontological analysis
    ontological_analysis: Optional[OntologicalAnalysis]
    detected_patterns: List[ArchitecturalPattern]
    
    # Quality assessment
    quality_metrics: QualityMetrics
    recommendations: List[Recommendation]
    
    def to_json(self) -> str:
        """Export as JSON."""
    
    def to_jsonld(self) -> str:
        """Export as JSON-LD with semantic annotations."""
    
    def to_rdf(self) -> str:
        """Export as RDF/Turtle."""
    
    def to_markdown(self) -> str:
        """Generate human-readable report."""
```

#### `ArchitecturalPattern`

Represents detected design patterns with semantic context.

```python
@dataclass
class ArchitecturalPattern:
    """Detected architectural pattern with semantic context."""
    
    name: str                           # Pattern name (e.g., "Strategy", "Repository")
    pattern_type: PatternType           # CREATIONAL, STRUCTURAL, BEHAVIORAL
    location: str                       # File/module location
    confidence: float                   # Detection confidence (0.0-1.0)
    
    # Pattern participants
    participants: List[PatternParticipant]
    relationships: List[PatternRelationship]
    
    # Semantic annotations
    ontological_mapping: str            # Mapping to formal ontology
    business_context: str               # Business/domain context
    
    # Pattern benefits and trade-offs
    benefits: List[str]
    drawbacks: List[str]
    improvement_suggestions: List[str]
```

#### `DomainModel`

Domain-driven design model extracted from code.

```python
@dataclass 
class DomainModel:
    """Domain-driven design model with semantic annotations."""
    
    bounded_contexts: List[BoundedContext]
    entities: List[Entity]
    value_objects: List[ValueObject]
    services: List[DomainService]
    repositories: List[Repository]
    
    # Cross-context relationships
    context_relationships: List[ContextRelationship]
    
    # Quality assessment
    context_cohesion: float             # How well-defined contexts are
    entity_design_quality: float        # Appropriateness of entity design
    service_boundaries: float           # Clarity of service boundaries

@dataclass
class BoundedContext:
    """Bounded context with clear domain boundaries."""
    
    name: str
    description: str
    modules: List[str]                  # Associated code modules
    
    # Domain vocabulary
    vocabulary: List[str]               # Key domain terms
    ubiquitous_language: Dict[str, str] # Term definitions
    
    # Context contents
    entities: List[Entity]
    value_objects: List[ValueObject]  
    services: List[DomainService]
    
    # Boundaries and interfaces
    external_interfaces: List[ContextInterface]
    internal_concepts: List[str]
```

### TRS Framework API

#### `TRSVerifier`

Mathematical verification of term rewriting systems.

```python
from repoq.normalize.trs_verifier import TRSVerifier

class TRSVerifier:
    """Verifies TRS properties: soundness, confluence, termination."""
    
    def __init__(self, rules: List[RewriteRule]):
        """Initialize with rule set."""
    
    def verify_confluence(self) -> ConfluenceResult:
        """
        Verify confluence using critical pair analysis.
        
        Returns:
            ConfluenceResult with critical pairs and joinability status
        """
    
    def verify_termination(self) -> TerminationResult:
        """
        Verify termination using well-founded ordering.
        
        Returns:
            TerminationResult with ordering proof
        """
    
    def compute_normal_form(self, term: Term) -> Term:
        """
        Compute unique normal form.
        
        Args:
            term: Input term to normalize
            
        Returns:
            Normalized term in canonical form
        """
```

**Usage Example:**
```python
from repoq.normalize.trs_verifier import TRSVerifier
from repoq.normalize.spdx_trs import SPDX_RULES

# Create TRS verifier
verifier = TRSVerifier(SPDX_RULES)

# Verify mathematical properties
confluence_result = verifier.verify_confluence()
print(f"Confluent: {confluence_result.is_confluent}")
print(f"Critical pairs: {len(confluence_result.critical_pairs)}")

termination_result = verifier.verify_termination()
print(f"Terminating: {termination_result.is_terminating}")

# Normalize license expression
normalized = verifier.compute_normal_form("MIT AND (MIT OR Apache-2.0)")
print(f"Normalized: {normalized}")  # Output: "MIT"
```

## 🌐 REST API

RepoQ provides a REST API for service integration and web applications.

### Starting the API Server

```bash
# Start development server
repoq serve --host localhost --port 8080

# Production server with gunicorn
gunicorn -w 4 -b 0.0.0.0:8080 repoq.api:app
```

### Authentication

```python
# API key authentication
headers = {
    'Authorization': 'Bearer YOUR_API_KEY',
    'Content-Type': 'application/json'
}
```

### Endpoints

#### `POST /api/v1/analyze`

Submit repository for analysis.

**Request:**
```json
{
  "repository_url": "https://github.com/user/repo.git",
  "analysis_type": "full",
  "options": {
    "ontology_enabled": true,
    "pattern_detection": true,
    "include_history": true,
    "output_format": "jsonld"
  }
}
```

**Response:**
```json
{
  "analysis_id": "uuid-string",
  "status": "submitted",
  "estimated_duration": 120,
  "webhook_url": "https://your-app.com/webhook"
}
```

#### `GET /api/v1/analyze/{analysis_id}`

Get analysis status and results.

**Response:**
```json
{
  "analysis_id": "uuid-string", 
  "status": "completed",
  "progress": 100,
  "result": {
    "@context": "https://field33.com/ontologies/analysis/",
    "@type": "AnalysisResult",
    "project": { ... },
    "ontological_analysis": { ... },
    "quality_metrics": { ... }
  }
}
```

#### `POST /api/v1/analyze/file`

Analyze single file upload.

**Request:**
```bash
curl -X POST \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -F "file=@example.py" \
  -F "options={\"language\":\"python\",\"complexity_analysis\":true}" \
  http://localhost:8080/api/v1/analyze/file
```

**Response:**
```json
{
  "file_analysis": {
    "filename": "example.py",
    "language": "python",
    "lines_of_code": 150,
    "complexity": {
      "cyclomatic": 8,
      "cognitive": 12
    },
    "detected_patterns": [
      {
        "pattern": "Decorator",
        "location": "line 23",
        "confidence": 0.9
      }
    ]
  }
}
```

#### `GET /api/v1/patterns`

Get supported architectural patterns.

**Response:**
```json
{
  "patterns": [
    {
      "name": "Strategy Pattern",
      "category": "behavioral",
      "description": "Define family of algorithms, encapsulate each one",
      "detection_criteria": [
        "Common interface or base class",
        "Multiple concrete implementations",
        "Polymorphic usage"
      ]
    },
    {
      "name": "Repository Pattern", 
      "category": "architectural",
      "description": "Encapsulate data access logic",
      "detection_criteria": [
        "Data access abstraction",
        "Interface segregation",
        "Implementation independence"
      ]
    }
  ]
}
```

#### `GET /api/v1/ontologies`

Get available ontologies and their schemas.

**Response:**
```json
{
  "ontologies": [
    {
      "name": "Code Ontology",
      "prefix": "code",
      "namespace": "https://field33.com/ontologies/code/",
      "concepts": ["Module", "Function", "Class", "Dependency"],
      "relationships": ["imports", "calls", "inherits", "implements"]
    },
    {
      "name": "C4 Model Ontology",
      "prefix": "c4", 
      "namespace": "https://field33.com/ontologies/c4/",
      "concepts": ["System", "Container", "Component", "Code"],
      "relationships": ["contains", "uses", "dependsOn"]
    }
  ]
}
```

### Webhooks

Configure webhooks for async analysis completion:

**Webhook Payload:**
```json
{
  "event": "analysis.completed",
  "analysis_id": "uuid-string",
  "timestamp": "2024-01-15T10:30:00Z",
  "result_url": "https://api.repoq.com/api/v1/analyze/uuid-string",
  "summary": {
    "quality_score": 8.5,
    "patterns_detected": 12,
    "issues_found": 3
  }
}
```

## 🔧 Configuration API

### `ConfigManager`

Manage RepoQ configuration programmatically.

```python
from repoq.config import ConfigManager

class ConfigManager:
    """Manage RepoQ configuration."""
    
    @classmethod
    def load_config(cls, config_path: str = None) -> Config:
        """Load configuration from file or defaults."""
    
    @classmethod  
    def create_default_config(cls) -> Config:
        """Create default configuration."""
    
    def validate_config(self, config: Config) -> ValidationResult:
        """Validate configuration parameters."""
    
    def update_config(self, updates: Dict[str, Any]) -> Config:
        """Update configuration with new values."""
```

**Usage Example:**
```python
from repoq.config import ConfigManager

# Load configuration
config = ConfigManager.load_config(".repoq.yaml")

# Update analysis settings
config_manager = ConfigManager(config)
updated_config = config_manager.update_config({
    "ontology.pattern_detection": True,
    "quality.complexity.cyclomatic_max": 20,
    "output.default_format": "jsonld"
})

# Validate configuration
validation = config_manager.validate_config(updated_config)
if not validation.is_valid:
    print(f"Configuration errors: {validation.errors}")
```

## 📊 Metrics API

### `MetricsCollector`

Collect and analyze quality metrics.

```python
from repoq.metrics import MetricsCollector

class MetricsCollector:
    """Collect comprehensive quality metrics."""
    
    def collect_project_metrics(self, 
                               repo_path: str) -> ProjectMetrics:
        """Collect all project-level metrics."""
    
    def collect_file_metrics(self, 
                           file_path: str) -> FileMetrics:
        """Collect file-level metrics."""
    
    def collect_function_metrics(self, 
                               func_node: ast.FunctionDef) -> FunctionMetrics:
        """Collect function-level metrics."""
    
    def calculate_quality_score(self, 
                              metrics: ProjectMetrics) -> QualityScore:
        """Calculate overall quality score."""
```

**Quality Score Calculation:**
```python
def calculate_quality_score(metrics: ProjectMetrics) -> QualityScore:
    """
    Calculate quality score using weighted formula:
    
    Quality = (0.3 × Code Quality) + 
              (0.25 × Architecture Quality) + 
              (0.2 × Domain Modeling) +
              (0.15 × Test Coverage) +
              (0.1 × Documentation)
    """
    
    code_quality = calculate_code_quality(metrics.complexity, metrics.maintainability)
    arch_quality = calculate_architecture_quality(metrics.coupling, metrics.cohesion)  
    domain_quality = calculate_domain_quality(metrics.domain_model)
    test_quality = calculate_test_quality(metrics.test_coverage)
    doc_quality = calculate_documentation_quality(metrics.documentation)
    
    overall_score = (
        0.30 * code_quality +
        0.25 * arch_quality + 
        0.20 * domain_quality +
        0.15 * test_quality +
        0.10 * doc_quality
    )
    
    return QualityScore(
        overall=overall_score,
        code=code_quality,
        architecture=arch_quality,
        domain=domain_quality,
        testing=test_quality,
        documentation=doc_quality
    )
```

## 🧪 Testing Utilities

### `AnalysisTestCase`

Base class for testing analysis components.

```python
from repoq.testing import AnalysisTestCase

class TestMyAnalyzer(AnalysisTestCase):
    """Test custom analyzer with RepoQ testing utilities."""
    
    def setUp(self):
        """Set up test environment."""
        self.temp_repo = self.create_temp_repo({
            "src/main.py": """
            class Calculator:
                def add(self, a, b):
                    return a + b
            """,
            "tests/test_main.py": """
            def test_add():
                calc = Calculator()
                assert calc.add(2, 3) == 5
            """
        })
    
    def test_structure_analysis(self):
        """Test structural analysis."""
        analyzer = StructureAnalyzer()
        result = analyzer.analyze(self.temp_repo)
        
        self.assertGreater(len(result.file_structure), 0)
        self.assertIn("Calculator", [cls.name for cls in result.classes])
    
    def test_pattern_detection(self):
        """Test pattern detection."""
        # Create code with Strategy pattern
        strategy_code = self.create_strategy_pattern_code()
        
        analyzer = StructureAnalyzer(pattern_detection=True)
        result = analyzer.analyze(strategy_code)
        
        patterns = [p.name for p in result.detected_patterns]
        self.assertIn("Strategy", patterns)
```

### Mock Objects

```python
from repoq.testing.mocks import MockRepository

# Create mock repository for testing
mock_repo = MockRepository()
mock_repo.add_file("src/main.py", python_code)
mock_repo.add_file("tests/test_main.py", test_code)

# Simulate git history
mock_repo.add_commit("Initial commit", ["src/main.py"])
mock_repo.add_commit("Add tests", ["tests/test_main.py"])

# Use in tests
analyzer = StructureAnalyzer()
result = analyzer.analyze(mock_repo.path)
```

## 🔌 Plugin Development

### Creating Custom Analyzers

```python
from repoq.analyzers.base import BaseAnalyzer

class CustomSecurityAnalyzer(BaseAnalyzer):
    """Custom analyzer for security patterns."""
    
    def analyze(self, repo_path: str) -> AnalysisResult:
        """Implement custom analysis logic."""
        
        # Scan for security patterns
        security_issues = self.scan_for_security_issues(repo_path)
        
        # Create analysis result
        return AnalysisResult(
            analyzer_name="security",
            issues=security_issues,
            recommendations=self.generate_recommendations(security_issues)
        )
    
    def scan_for_security_issues(self, repo_path: str) -> List[SecurityIssue]:
        """Scan for security vulnerabilities."""
        issues = []
        
        for file_path in self.get_python_files(repo_path):
            with open(file_path) as f:
                content = f.read()
                
            # Check for SQL injection patterns
            if "execute(" in content and "%" in content:
                issues.append(SecurityIssue(
                    type="sql_injection",
                    file=file_path,
                    severity="high",
                    description="Potential SQL injection vulnerability"
                ))
        
        return issues

# Register custom analyzer
from repoq.analyzers import registry
registry.register("security", CustomSecurityAnalyzer)
```

### Creating Custom Ontologies

```python
from repoq.ontologies.base import OntologyPlugin

class SecurityOntologyPlugin(OntologyPlugin):
    """Security-focused ontology plugin."""
    
    def __init__(self):
        super().__init__(
            name="security",
            namespace="https://field33.com/ontologies/security/"
        )
    
    def get_concepts(self) -> List[Concept]:
        """Define security concepts."""
        return [
            Concept("Vulnerability", "Security weakness in code"),
            Concept("ThreatVector", "Potential attack mechanism"),
            Concept("SecurityControl", "Protective measure implementation"),
            Concept("AuthenticationMechanism", "User identity verification"),
            Concept("AuthorizationRule", "Access control specification")
        ]
    
    def get_relationships(self) -> List[Relationship]:
        """Define security relationships.""" 
        return [
            Relationship("exploits", "ThreatVector", "Vulnerability"),
            Relationship("mitigates", "SecurityControl", "Vulnerability"),
            Relationship("requires", "AuthorizationRule", "AuthenticationMechanism")
        ]
    
    def analyze_code_for_concepts(self, 
                                 code_structure: ProjectStructure) -> List[ConceptInstance]:
        """Extract security concepts from code."""
        concepts = []
        
        for file_node in code_structure.files:
            if "auth" in file_node.path.lower():
                concepts.append(ConceptInstance(
                    concept="AuthenticationMechanism",
                    location=file_node.path,
                    confidence=0.8
                ))
        
        return concepts

# Register custom ontology
from repoq.ontologies import registry
registry.register("security", SecurityOntologyPlugin)
```

---

This API reference provides comprehensive coverage of RepoQ's programmatic interfaces, enabling developers to integrate semantic analysis capabilities into their own tools and workflows. 🚀