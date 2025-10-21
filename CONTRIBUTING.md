# Contributing to RepoQ

Welcome! RepoQ is a technical project requiring mathematical precision in Term Rewriting Systems (TRS) and semantic web technologies.

## Quick Start for Contributors

### 1. Development Setup

#### Local Python Environment
```bash
# Clone and setup
git clone https://github.com/kirill-0440/repoq.git
cd repoq
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
pip install -e ".[full,dev]"

# Run tests
pytest --cov=repoq --cov-report=html
```

#### Docker Environment (Recommended)
```bash
# Clone repository
git clone https://github.com/kirill-0440/repoq.git
cd repoq

# Build and run development container
docker-compose up repoq-dev

# Run tests in container
docker-compose up repoq-test

# Serve documentation locally
docker-compose up repoq-docs
# Open http://localhost:8000 in browser

# Run analysis on current directory
docker-compose run --rm repoq-prod analyze /repo --format json
```

**Docker Benefits**:
- ✅ Reproducible builds across platforms
- ✅ Isolated dependencies (no system pollution)
- ✅ Same environment as CI/CD
- ✅ Multi-stage builds (optimized images)
- ✅ Hot-reload for development

### 2. Project Architecture
```
repoq/
├── analyzers/     # Git repository analysis modules
├── core/          # Data models and utilities  
├── normalize/     # TRS systems for data canonicalization
├── ontologies/    # Semantic web schemas and managers
└── reporting/     # Output formatters (MD, GraphViz, etc.)
```

## Priority Contribution Areas

### 🔥 Critical (Help Needed)
1. **Test Coverage** - Currently <10%, need 80%+
   - Golden snapshot tests for analyzers
   - Property-based tests for TRS systems
   - Integration tests for CLI workflows

2. **TRS Mathematical Correctness** - Production blockers
   - Fix Metrics TRS idempotence violations
   - Resolve SPDX/SemVer/RDF confluence issues  
   - Ensure termination guarantees

3. **Performance Optimization**
   - Implement caching for expensive operations
   - Memory usage optimization for large repositories
   - Parallel processing for multi-repository analysis

### 📊 High Impact
4. **Docker & CI/CD**
   - Multi-stage Docker build optimization
   - GitHub Actions workflow enhancement
   - Cross-platform testing (Windows/Mac/Linux)

5. **SHACL Validation**
   - Semantic export validation rules
   - W3C compliance verification
   - Error reporting improvements

### 🌍 Community
6. **Documentation & Examples**
   - Integration guides for popular CI systems
   - Real-world case studies
   - API reference improvements

## Contribution Guidelines

### Code Quality Standards
- **Test Coverage**: All new code requires ≥90% test coverage
- **Type Hints**: Full type annotations required  
- **Documentation**: Docstrings for all public APIs
- **TRS Soundness**: Mathematical proofs for new TRS rules

### Pull Request Process
1. **Create Issue First**: Discuss approach before coding
2. **Branch Naming**: `feature/description` or `fix/issue-number`
3. **Commit Messages**: Follow conventional commits
4. **Tests Required**: No PR merged without tests
5. **Review Process**: At least one maintainer approval

### Testing Requirements
```bash
# Local testing
pytest --cov=repoq --cov-report=term-missing
ruff check repoq/ tests/
mypy repoq/

# Docker testing (recommended for CI parity)
docker-compose up repoq-test

# Golden snapshot updates (when needed)
pytest --snapshot-update tests/
```

### Docker Development Workflow
```bash
# Start development container with hot-reload
docker-compose up repoq-dev

# Attach to running container for interactive work
docker-compose exec repoq-dev bash

# Run specific tests inside container
docker-compose exec repoq-dev pytest tests/test_ontology_manager.py -v

# Rebuild after dependency changes
docker-compose build repoq-dev

# Clean up containers and images
docker-compose down
docker system prune -f
```

## Technical Deep Dives

### Understanding TRS Systems
RepoQ uses Term Rewriting Systems for data normalization:
- **Confluence**: Critical pairs must be resolvable
- **Termination**: Well-founded measures required
- **Soundness**: Preserve semantic meaning

See `docs/ontology/trs-framework.md` for details.

### Semantic Web Integration
- JSON-LD context management in `core/jsonld.py`
- RDF export with W3C ontologies in `core/rdf_export.py`  
- SHACL shapes for validation in `shapes/`

## Getting Help

### Communication Channels
- **GitHub Issues**: Bug reports and feature requests
- **GitHub Discussions**: Architecture questions and ideas
- **Code Review**: Direct feedback on PRs

### Mentorship Available
Maintainers provide guidance for:
- First-time contributors to semantic web technologies
- TRS system design and implementation
- Academic collaboration opportunities

## Recognition

Contributors will be:
- Listed in `CONTRIBUTORS.md`
- Credited in academic papers (if applicable)
- Invited to co-present at conferences
- Considered for maintainer status

## Code of Conduct

We follow the [Contributor Covenant](https://www.contributor-covenant.org/):
- Be respectful and inclusive
- Focus on technical merit
- Welcome newcomers and questions
- Maintain professional discourse

## Roadmap Alignment

Current phase: **Technical Excellence** (T+0-30 days)
- Primary focus: Test coverage and TRS correctness
- Secondary: Performance and Docker optimization
- Future: Community growth and ecosystem integration

Thank you for contributing to advancing semantic software analysis! 🚀