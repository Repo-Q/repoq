# Phase 1: Workspace Foundation (Complete ✅)

**Status**: Completed (Commit: bed0ea5)  
**Duration**: 3 days (planned), 1 day (actual)  
**Tests**: 18/18 passing  

## Overview

Phase 1 establishes the `.repoq/` workspace structure for reproducible analysis runs. Every analysis creates a manifest with checksums and metadata for full traceability.

## What Changed

### 1. New Module: `repoq/core/workspace.py`

**Purpose**: Manage `.repoq/` directory structure and manifest generation.

**Key Classes**:
- `RepoQWorkspace`: Directory manager with 6 subdirectories
- `ManifestEntry`: Dataclass for manifest.json structure

**Key Functions**:
- `initialize()`: Creates `.repoq/` structure + `.gitignore`
- `save_manifest()`: Generates manifest.json with checksums
- `load_manifest()`: Loads and validates manifest
- `compute_ontology_checksums()`: SHA256 checksums for ontologies

**Directory Structure**:
```
.repoq/
├── raw/           # Raw analysis artifacts (JSON-LD, RDF/XML)
├── validated/     # SHACL-validated RDF (Phase 2)
├── reports/       # Human-readable reports (MD, HTML)
├── certificates/  # Quality gate certificates (signed)
├── cache/         # Incremental analysis cache
└── manifest.json  # Reproducibility metadata
```

### 2. Pipeline Integration: `repoq/pipeline.py`

**Changes**:
- **Start**: `workspace.initialize()` creates `.repoq/`
- **End**: `workspace.save_manifest()` generates manifest with:
  - Commit SHA (from git)
  - Policy version (2.0.0-alpha)
  - Ontology checksums (SHA256 of all `.ttl` files)
  - Timestamp (ISO 8601)

**Code**:
```python
from repoq.core.workspace import RepoQWorkspace, compute_ontology_checksums

def run_pipeline(project: Project, repo_dir: str, cfg: AnalyzeConfig) -> None:
    # Initialize workspace
    repo_path = Path(repo_dir)
    workspace = RepoQWorkspace(repo_path)
    workspace.initialize()
    
    # ... run analyzers ...
    
    # Generate manifest
    commit_sha = subprocess.run(["git", "rev-parse", "HEAD"], ...).stdout.strip()
    checksums = compute_ontology_checksums(Path("repoq/ontologies"))
    workspace.save_manifest(commit_sha, "2.0.0-alpha", checksums)
```

### 3. Tests: 18 Total

**Unit Tests** (`tests/core/test_workspace.py`):
- 15 tests for `RepoQWorkspace` class
- Test classes:
  - `TestRepoQWorkspaceInitialization` (4 tests)
  - `TestManifestGeneration` (6 tests)
  - `TestOntologyChecksums` (3 tests)
  - `TestWorkspaceIntegration` (2 tests)

**Integration Tests** (`tests/integration/test_gate_workspace.py`):
- 3 tests for pipeline integration
- Test workspace initialization on `run_pipeline()`
- Test manifest generation with valid checksums
- Test performance <50ms (NFR-01)

## Manifest Example

```json
{
  "commit_sha": "bed0ea5c8f6a1234567890abcdef",
  "policy_version": "2.0.0-alpha",
  "ontology_checksums": {
    "context_ext.jsonld": "sha256:abc123...",
    "field33.context.jsonld": "sha256:def456..."
  },
  "created_at": "2025-01-15T10:30:45.123456Z"
}
```

## Usage

### For Users

No changes required! Workspace is created automatically on every analysis:

```bash
repoq analyze --mode full
# .repoq/ created automatically
# manifest.json generated at end
```

### For Developers

```python
from repoq.core.workspace import RepoQWorkspace

# Create workspace
workspace = RepoQWorkspace(Path("/path/to/repo"))
workspace.initialize()

# Save manifest
workspace.save_manifest(
    commit_sha="abc123",
    policy_version="2.0.0-alpha",
    ontology_checksums={"test.ttl": "sha256:..."}
)

# Load manifest
manifest = workspace.load_manifest()
print(manifest.commit_sha)  # "abc123"
```

## Traceability

| ID | Requirement | Implementation |
|----|-------------|----------------|
| FR-10 | Reproducible analysis results | Manifest with commit SHA + checksums |
| V07 | Observability and transparency | `.repoq/` visible structure |
| Theorem A | Reproducibility | SHA256 checksums for ontologies |
| NFR-01 | Performance | <50ms workspace overhead |
| ADR-008 | Git as source of truth | Commit SHA in manifest |
| ADR-010 | Incremental analysis | `.repoq/cache/` for future use |
| ADR-013 | Incremental migration | Phase 1 = zero breaking changes |

## Performance

**Workspace Overhead**: <50ms (measured in tests)  
**Breakdown**:
- `initialize()`: ~10ms (mkdir operations)
- `compute_ontology_checksums()`: ~20ms (SHA256 of 2 files)
- `save_manifest()`: ~5ms (JSON serialization)
- `load_manifest()`: ~5ms (JSON deserialization)

**Impact**: <5% overhead on typical analysis run (NFR-01 satisfied).

## Testing

```bash
# Run all workspace tests
pytest tests/core/test_workspace.py tests/integration/test_gate_workspace.py -v

# Run unit tests only
pytest tests/core/test_workspace.py -v

# Run integration tests only
pytest tests/integration/test_gate_workspace.py -v
```

## Next Steps

**Phase 2: SHACL Validation** (Week 2-3)
- Integrate SHACL validation into pipeline
- Save validated RDF to `.repoq/validated/`
- Certificate generation on validation success

**Phase 3: Reasoner Integration** (Week 4-6)
- Add OWL reasoning to pipeline
- Infer implicit facts (e.g., hotspot propagation)
- Save inferred triples to `.repoq/validated/`

**Phase 4: Unified Pipeline** (Week 7-10)
- Feature flag for v2 pipeline
- Parallel execution (v1 + v2)
- Gradual cutover based on metrics

## Migration Notes

### Zero Breaking Changes ✅

Phase 1 is **fully backward compatible**:
- No CLI changes
- No config changes
- No API changes
- Only addition: `.repoq/` directory created

### Rollback Plan

If issues arise:
1. Delete `.repoq/` directory (safe - all data is in git)
2. Revert commit: `git revert bed0ea5`
3. Tests will still pass (workspace is optional in this phase)

### Known Limitations

1. **Manifest not used yet**: Future phases will validate against manifest
2. **Cache not populated**: Incremental analysis comes in Phase 2+
3. **Certificates not generated**: Comes in Phase 2 (SHACL validation)

## Questions?

See:
- `docs/vdad/phase5-migration-roadmap.md` (full roadmap)
- `docs/vdad/phase5-quick-reference.md` (quick navigation)
- `docs/vdad/phase4-adr-013-incremental-migration.md` (formal decision)
