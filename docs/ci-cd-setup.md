# CI/CD Configuration Guide

This document describes the GitHub Actions workflows configured for RepoQ and how to set up your own CI/CD pipeline.

## Overview

RepoQ uses GitHub Actions for:
- ✅ **Continuous Testing** (Python 3.9-3.12)
- ✅ **Code Quality Gates** (coverage, lint, type checks)
- ✅ **Docker Build & Validation**
- ✅ **Automated Releases** (PyPI + Docker Hub)
- ✅ **PR Quality Validation**

## Workflows

### 1. CI Workflow (`.github/workflows/ci.yml`)

**Triggers:**
- Push to `main` or `develop` branches
- Pull requests to `main`

**Jobs:**
- **lint**: Ruff, Black, MyPy checks
- **test**: Run tests on Python 3.9-3.12 with coverage
- **docker-build**: Build and test Docker image
- **self-analyze**: Run RepoQ on itself (dogfooding)
- **security**: Bandit and Safety scans

**Coverage Threshold:**
```python
threshold = 60.0  # Phase 5.7 minimum
target = 80.0     # Long-term goal
```

**Usage:**
```bash
# Runs automatically on push/PR
# Manually trigger:
gh workflow run ci.yml
```

---

### 2. Release Workflow (`.github/workflows/release.yml`)

**Triggers:**
- Push tags matching `v*.*.*` (e.g., `v2.0.0`, `v2.1.0-beta.1`)

**Jobs:**
1. **validate-tag**: Check version format and match with `pyproject.toml`
2. **test**: Full test suite on all Python versions
3. **build-wheel**: Create wheel and sdist packages
4. **docker-build**: Multi-arch Docker images (amd64 + arm64)
5. **publish-pypi**: Upload to PyPI (trusted publishing)
6. **create-github-release**: Create GitHub release with changelog
7. **notify-success**: Post summary to GitHub

**Prerequisites:**

#### PyPI Trusted Publishing
1. Go to https://pypi.org/manage/account/publishing/
2. Add trusted publisher:
   - **Repository**: `kirill-0440/repoq`
   - **Workflow**: `release.yml`
   - **Environment**: `pypi`

#### Docker Hub
1. Create Docker Hub account
2. Generate access token at https://hub.docker.com/settings/security
3. Add GitHub secrets:
   - `DOCKERHUB_USERNAME`: Your Docker Hub username
   - `DOCKERHUB_TOKEN`: Access token

**Usage:**
```bash
# 1. Update version in pyproject.toml
sed -i 's/version = "2.0.0"/version = "2.1.0"/' pyproject.toml

# 2. Commit changes
git add pyproject.toml
git commit -m "chore: bump version to 2.1.0"

# 3. Create and push tag
git tag v2.1.0
git push origin v2.1.0

# 4. Workflow runs automatically
# Monitor at: https://github.com/kirill-0440/repoq/actions
```

---

### 3. PR Quality Gate (`.github/workflows/pr-quality-gate.yml`)

**Triggers:**
- Pull requests opened/updated on `main` or `develop`

**Jobs:**
- **quality-gate**: Run tests, check coverage, validate no regression
- **policy-validation**: Validate `.github/quality-policy.yml`
- **size-check**: Ensure Docker image ≤200MB

**Quality Checks:**
1. **Coverage**: Must be ≥60% (Phase 5.7 threshold)
2. **Regression**: Coverage drop ≤2% from baseline
3. **Code Quality**: ≤10 critical Ruff issues
4. **Tests**: All tests must pass
5. **Policy**: Valid quality-policy.yml

**PR Comment Example:**
```markdown
## 🚦 Quality Gate Report

### Coverage
- **Current:** 63.5%
- **Threshold:** 60% (minimum)
- **Target:** 80% (goal)

✅ Coverage 63.5% meets minimum threshold 60%

### Checks
- ✅ Tests passed
- ✅ No major regression
- ✅ Code quality acceptable
```

---

### 4. TRS Verification (`.github/workflows/trs-verification.yml`)

**Triggers:**
- Scheduled (weekly)
- Manual trigger

**Purpose:**
Validate mathematical correctness of Term Rewriting Systems:
- Confluence checks
- Termination proofs
- Idempotence validation

---

## Configuration Files

### Quality Policy (`.github/quality-policy.yml`)

Defines quality gates and thresholds:

```yaml
version: "1.0"
project:
  name: "repoq"
  language: "python"

gates:
  soundness: {enabled: true, fail_on_error: true}
  confluence: {enabled: true, check_critical_pairs: true, completion_strategy: "knuth-bendix"}
  termination: {enabled: true, max_iterations: 1000, timeout_seconds: 30}

stratification:
  max_level: 10
  allow_self_analysis: true
  self_analysis_max_level: 2

quality_thresholds:
  test_coverage_min: 0.80
  complexity_max: 15
  duplication_max: 0.10
```

---

## Local Testing

### Run tests with coverage
```bash
pytest --cov=repoq --cov-report=term-missing --cov-report=json
```

### Check coverage threshold
```python
python -c "
import json
with open('coverage.json') as f:
    coverage = json.load(f)['totals']['percent_covered']
assert coverage >= 60.0, f'Coverage {coverage}% below 60%'
print(f'✅ Coverage {coverage:.1f}% meets threshold')
"
```

### Lint checks
```bash
ruff check .
black --check .
mypy repoq/
```

### Docker build
```bash
docker build -t repoq:test --target runtime .
docker run --rm repoq:test --help
```

---

## GitHub Secrets

Required secrets for full CI/CD:

| Secret | Purpose | How to Generate |
|--------|---------|-----------------|
| `DOCKERHUB_USERNAME` | Docker Hub login | Docker Hub account username |
| `DOCKERHUB_TOKEN` | Docker Hub push | https://hub.docker.com/settings/security |
| `CODECOV_TOKEN` | Coverage upload | https://codecov.io (optional) |

PyPI publishing uses **OIDC trusted publishing** (no token needed).

---

## Troubleshooting

### Coverage threshold failure
```
❌ FAIL: Coverage 58.3% below threshold 60.0%
```

**Fix:** Add tests to increase coverage:
```bash
pytest --cov=repoq --cov-report=term-missing
# Focus on uncovered lines shown in report
```

### Docker image too large
```
⚠️ WARNING: Image size 220MB exceeds 200MB target
```

**Fix:** Check multi-stage build layers:
```bash
docker history repoq:latest --human
# Identify large layers and optimize
```

### PyPI publish failure
```
ERROR: 403 Forbidden (configure trusted publishing)
```

**Fix:** Configure trusted publisher at https://pypi.org/manage/account/publishing/

### Version mismatch
```
❌ Version mismatch: tag=2.1.0, pyproject.toml=2.0.0
```

**Fix:** Update `pyproject.toml` before tagging:
```bash
sed -i 's/version = "2.0.0"/version = "2.1.0"/' pyproject.toml
git add pyproject.toml
git commit -m "chore: bump version to 2.1.0"
git tag v2.1.0
```

---

## Integration with Other CI Systems

### GitLab CI

```yaml
# .gitlab-ci.yml
stages:
  - test
  - build
  - deploy

test:
  stage: test
  image: python:3.11-alpine
  before_script:
    - apk add --no-cache git graphviz
    - pip install -e ".[full,dev]"
  script:
    - pytest --cov=repoq --cov-report=term-missing
    - python -c "import json; assert json.load(open('coverage.json'))['totals']['percent_covered'] >= 60.0"
  coverage: '/TOTAL.*\s+(\d+%)$/'

docker:
  stage: build
  image: docker:latest
  services:
    - docker:dind
  script:
    - docker build -t $CI_REGISTRY_IMAGE:$CI_COMMIT_TAG .
    - docker push $CI_REGISTRY_IMAGE:$CI_COMMIT_TAG
  only:
    - tags
```

### Jenkins

```groovy
// Jenkinsfile
pipeline {
    agent { docker { image 'python:3.11-alpine' } }
    
    stages {
        stage('Test') {
            steps {
                sh 'apk add --no-cache git graphviz'
                sh 'pip install -e ".[full,dev]"'
                sh 'pytest --cov=repoq --cov-report=xml'
            }
            post {
                always {
                    junit 'test-results.xml'
                    cobertura coberturaReportFile: 'coverage.xml'
                }
            }
        }
        
        stage('Quality Gate') {
            steps {
                script {
                    def coverage = sh(
                        script: 'python -c "import json; print(json.load(open(\'coverage.json\'))[\'totals\'][\'percent_covered\'])"',
                        returnStdout: true
                    ).trim().toFloat()
                    
                    if (coverage < 60.0) {
                        error("Coverage ${coverage}% below threshold 60%")
                    }
                }
            }
        }
    }
}
```

---

## Best Practices

1. **Always run tests locally before pushing**
   ```bash
   pytest --cov=repoq --cov-report=term-missing
   ```

2. **Use pre-commit hooks**
   ```bash
   pip install pre-commit
   pre-commit install
   ```

3. **Monitor CI performance**
   - Test execution time should be <5 minutes
   - Docker build should be <2 minutes (with cache)

4. **Keep workflows DRY**
   - Reusable workflows for common tasks
   - Composite actions for complex steps

5. **Security**
   - Never commit secrets to repository
   - Use GitHub secrets for sensitive data
   - Enable Dependabot for dependency updates

---

## References

- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [PyPI Trusted Publishing](https://docs.pypi.org/trusted-publishers/)
- [Docker Multi-Arch Builds](https://docs.docker.com/build/building/multi-platform/)
- [Codecov Integration](https://docs.codecov.com/docs)
