# Current Limitations & Roadmap

!!! warning "Honest Assessment"
    RepoQ is in active development. This page provides a transparent view of current limitations and planned improvements.

## 🚨 Current Limitations

### **Test Coverage** 
- **Current**: <10% test coverage
- **Target**: 80%+ with golden snapshots
- **Impact**: Limited confidence in edge cases
- **Timeline**: Priority #1 for Phase 1 (T+30)

### **Performance & Scalability**
- **Issue**: No incremental caching or analysis optimization
- **Impact**: Slow on large repositories (>10k files)
- **Workaround**: Use `--since` and file filters
- **Timeline**: Performance improvements in Phase 1

### **Container & CI/CD Integration**
- **Missing**: Docker container and GitHub Actions
- **Impact**: Manual setup required for CI/CD
- **Timeline**: Phase 1 priority

### **Semantic Validation**
- **Missing**: SHACL shapes for data validation  
- **Impact**: No formal validation of JSON-LD/RDF exports
- **Timeline**: Phase 1 deliverable

### **Statistical Rigor**
- **Issue**: Temporal coupling uses simple co-occurrence
- **Missing**: Statistical significance testing (PMI, χ²-p-value)
- **Timeline**: Phase 3 advanced analytics

## 🎯 30-60-90 Day Roadmap

### **T+30: Production Ready**
**Goal**: Stable, tested, containerized tool ready for daily use

**Critical Deliverables**:
- [ ] **80%+ Test Coverage**: Unit tests, golden snapshots, property-based testing
- [ ] **Docker Container**: `repoq:latest` with all dependencies
- [ ] **GitHub Action**: `.github/workflows/repoq.yml` template
- [ ] **SHACL Validation**: Core shapes for Project/Module/File validation
- [ ] **Performance**: Caching with `--cache-dir`, `--since` filters
- [ ] **Reference Examples**: 2-3 OSS analyses (small/medium/large repos)

**Acceptance Criteria**:
- ✅ Green CI with 80%+ coverage
- ✅ Valid JSON-LD/RDF exports pass SHACL validation
- ✅ Docker runs on clean system
- ✅ GitHub Action produces artifacts

### **T+60: Semantic Certification**
**Goal**: Verifiable quality certificates and enterprise integration

**Key Features**:
- [ ] **Quality Certificates**: W3C Verifiable Credentials with Ed25519 signatures
- [ ] **Canonical Context**: Stable JSON-LD `@context` with versioned ontologies
- [ ] **SHACL Rules**: Derived properties and quality inference rules
- [ ] **PR Bot Integration**: Quality insights in PR comments
- [ ] **SPARQL Endpoint**: Query interface for quality data
- [ ] **OSLC Compatibility**: Enterprise QM/CM interoperability testing

**Acceptance Criteria**:
- ✅ Certificates validate with standard VC tools
- ✅ PR bot comments with quality insights
- ✅ SPARQL queries return expected results
- ✅ OSLC compatibility tests pass

### **T+90: Advanced Analytics**
**Goal**: Statistical rigor and optimization guidance

**Advanced Features**:
- [ ] **Statistical Coupling**: PMI, φ-coefficient, χ²-p-value with FDR correction
- [ ] **ZAG Framework**: PCQ/PCE/Manifest with fairness curves and AHR
- [ ] **SBOM Security**: SPDX SBOM with CVE/OSV vulnerability mapping
- [ ] **k-Repair Engine**: Measurable optimization suggestions
- [ ] **ML Pattern Recognition**: Automated architectural pattern detection
- [ ] **Interactive Dashboards**: Web UI for trend analysis and exploration

**Acceptance Criteria**:
- ✅ ZAG manifests validate with official tools
- ✅ k-repair suggestions proven effective on test repos
- ✅ Statistical coupling filters false positives
- ✅ Security vulnerabilities correctly mapped to dependencies

## 🔧 Known Issues

### **Language Support**
**Current**: Python (full), JavaScript/TypeScript (basic), others (structure only)  
**Planned**: Tree-sitter integration for 40+ languages

### **Complexity Analyzers**
**Graceful Degradation**: RepoQ continues with available analyzers
- Missing `lizard`: No complexity metrics, basic structure only
- Missing `radon`: No maintainability index for Python
- Missing `pydriller`: Current state only, no history analysis

### **Memory Usage**
**Large Repos**: Can exceed 2GB RAM on repositories with >50k files
**Workaround**: Use `--max-files` and exclusion patterns
**Fix**: Streaming analysis planned for Phase 1

### **Git History**
**Performance**: Full history analysis can be slow on old repositories
**Workaround**: Use `--since "2024-01-01"` for recent history only
**Fix**: Incremental analysis with commit caching

## 📊 Quality Gates

We apply the same quality standards to RepoQ that we expect from analyzed projects:

### **Current Quality Metrics**
- **Test Coverage**: <10% ❌ (Target: 80%+)
- **Code Complexity**: Average 8.2 ✅ (Target: <15)
- **Documentation**: 100% ✅ (All APIs documented)
- **Linting**: 100% ✅ (Ruff + type hints)
- **Dependency Management**: ✅ (Pinned versions, security scanning)

### **Blocking Issues for v1.0**
1. **Test Coverage**: Must reach 80%+ before stable release
2. **SHACL Validation**: JSON-LD exports must validate against shapes
3. **Container Security**: Docker image must pass security scans
4. **Performance**: Must handle 10k+ file repositories within reasonable time
5. **API Stability**: No breaking changes to core interfaces

## 🚀 How to Help

### **High-Impact Contributions**
1. **Test Coverage**: Unit tests for parsers and exporters
2. **Golden Snapshots**: Reference outputs for regression testing  
3. **Performance**: Caching and incremental analysis
4. **Documentation**: Real-world examples and tutorials
5. **Language Support**: Tree-sitter parsers for additional languages

### **Getting Started**
```bash
# Set up development environment
git clone https://github.com/kirill-0440/repoq.git
cd repoq
pip install -e ".[full,dev]"

# Run tests and see current coverage
python -m pytest --cov=repoq --cov-report=html tests/
open htmlcov/index.html

# Identify areas needing tests
python -m pytest --cov=repoq --cov-report=term-missing tests/
```

### **Current Priority Areas**
- [ ] `tests/test_structure_analyzer.py` - Structure analysis test suite
- [ ] `tests/test_complexity_analyzer.py` - Complexity metrics validation
- [ ] `tests/test_jsonld_export.py` - Semantic export validation
- [ ] `tests/data/golden/` - Reference outputs for regression testing
- [ ] `docker/Dockerfile` - Multi-stage container build
- [ ] `.github/workflows/test.yml` - Comprehensive CI pipeline

## 📈 Success Metrics

We track these metrics to measure progress toward production readiness:

### **Technical Metrics**
- **Test Coverage**: Current <10% → Target 80%+
- **Performance**: Current 45s on RepoQ → Target <10s
- **Memory Usage**: Current 1.2GB → Target <512MB
- **Container Size**: Target <500MB compressed
- **Startup Time**: Target <2s cold start

### **Quality Metrics**  
- **Bug Reports**: Track and resolve within 48h
- **Documentation Coverage**: Maintain 100% API coverage
- **Security Scans**: Zero high/critical vulnerabilities
- **Dependency Updates**: Automated security updates
- **Breaking Changes**: Zero breaking API changes after v1.0

### **Community Metrics**
- **Contributors**: Current 1 → Target 5+ active contributors
- **Issues Closed**: Track resolution rate and time
- **Feature Requests**: Community-driven roadmap input
- **Documentation Feedback**: User experience improvements

---

**We believe in transparent development.** This honest assessment helps set proper expectations while we work toward a production-ready tool that delivers real value to development teams.

**Want to help accelerate progress?** Check our [Contributing Guide](../development/contributing.md) and join the effort! 🚀