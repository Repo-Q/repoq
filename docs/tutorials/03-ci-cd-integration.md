# Tutorial 3: CI/CD Integration

!!! tip "Learning Objectives"
    - Integrate RepoQ into GitHub Actions
    - Configure quality gates
    - Set up automated reporting
    - Fail builds on quality regressions

## Prerequisites

- GitHub repository with code
- Basic understanding of CI/CD concepts
- Completed [Tutorial 1: First Analysis](01-first-analysis.md)

## Why CI/CD Integration?

Automated quality checks ensure:
- **Early detection**: Catch issues before merge
- **Consistent standards**: Enforce quality thresholds
- **Trend tracking**: Monitor quality over time
- **Team awareness**: Share quality metrics

## GitHub Actions Integration

### Step 1: Basic Workflow

Create `.github/workflows/repoq.yml`:

```yaml
name: RepoQ Quality Check

on:
  pull_request:
    branches: [main, develop]
  push:
    branches: [main]

jobs:
  quality-check:
    runs-on: ubuntu-latest
    
    steps:
      - name: Checkout code
        uses: actions/checkout@v4
        with:
          fetch-depth: 0  # Full history for history analyzer
      
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      
      - name: Install uv
        uses: astral-sh/setup-uv@v3
      
      - name: Install RepoQ
        run: uv pip install repoq
      
      - name: Run RepoQ Analysis
        run: |
          uv run repoq analyze . \
            --format markdown \
            --format json \
            --output repoq-results/
      
      - name: Upload Results
        uses: actions/upload-artifact@v4
        with:
          name: repoq-analysis
          path: repoq-results/
      
      - name: Comment on PR
        if: github.event_name == 'pull_request'
        uses: actions/github-script@v7
        with:
          script: |
            const fs = require('fs');
            const report = fs.readFileSync('repoq-results/analysis.md', 'utf8');
            
            github.rest.issues.createComment({
              issue_number: context.issue.number,
              owner: context.repo.owner,
              repo: context.repo.name,
              body: `## RepoQ Quality Report\n\n${report}`
            });
```

### Step 2: Quality Gate

Fail the build if quality drops below threshold:

```yaml
      - name: Check Quality Threshold
        run: |
          SCORE=$(uv run repoq analyze . --format json | jq '.quality_score')
          THRESHOLD=7.0
          
          echo "Quality Score: $SCORE"
          echo "Threshold: $THRESHOLD"
          
          if (( $(echo "$SCORE < $THRESHOLD" | bc -l) )); then
            echo "❌ Quality score $SCORE below threshold $THRESHOLD"
            exit 1
          else
            echo "✅ Quality score $SCORE meets threshold"
          fi
```

### Step 3: Compare with Main Branch

Detect quality regressions:

```yaml
      - name: Analyze Main Branch
        run: |
          git checkout main
          uv run repoq analyze . \
            --format json \
            --output baseline/ \
            --save-baseline baseline.json
      
      - name: Analyze PR Branch
        run: |
          git checkout ${{ github.head_ref }}
          uv run repoq analyze . \
            --format json \
            --output current/ \
            --compare-baseline baseline/baseline.json
      
      - name: Check for Regressions
        run: |
          python scripts/check_regression.py \
            baseline/analysis.json \
            current/analysis.json
```

**check_regression.py**:
```python
#!/usr/bin/env python3
import json
import sys

def main():
    with open(sys.argv[1]) as f:
        baseline = json.load(f)
    
    with open(sys.argv[2]) as f:
        current = json.load(f)
    
    baseline_score = baseline['quality_score']
    current_score = current['quality_score']
    
    delta = current_score - baseline_score
    
    print(f"Baseline: {baseline_score:.2f}")
    print(f"Current:  {current_score:.2f}")
    print(f"Delta:    {delta:+.2f}")
    
    if delta < -0.5:  # Regression threshold
        print("❌ Quality regression detected!")
        sys.exit(1)
    elif delta > 0.5:
        print("✅ Quality improvement!")
    else:
        print("➖ No significant change")
    
    sys.exit(0)

if __name__ == '__main__':
    main()
```

## GitLab CI Integration

### .gitlab-ci.yml

```yaml
repoq-analysis:
  image: python:3.11
  stage: test
  
  before_script:
    - pip install uv
    - uv pip install repoq
  
  script:
    - uv run repoq analyze . --format json --format markdown --output results/
    - |
      SCORE=$(jq '.quality_score' results/analysis.json)
      echo "Quality Score: $SCORE"
      
      if (( $(echo "$SCORE < 7.0" | bc -l) )); then
        echo "Quality check failed"
        exit 1
      fi
  
  artifacts:
    paths:
      - results/
    reports:
      junit: results/junit.xml  # If you generate JUnit format
    expire_in: 1 week
  
  rules:
    - if: '$CI_PIPELINE_SOURCE == "merge_request_event"'
    - if: '$CI_COMMIT_BRANCH == "main"'
```

## Jenkins Integration

### Jenkinsfile

```groovy
pipeline {
    agent any
    
    stages {
        stage('Setup') {
            steps {
                sh 'pip install uv'
                sh 'uv pip install repoq'
            }
        }
        
        stage('Quality Analysis') {
            steps {
                sh '''
                    uv run repoq analyze . \
                        --format json \
                        --format markdown \
                        --format junit \
                        --output repoq-results/
                '''
            }
        }
        
        stage('Quality Gate') {
            steps {
                script {
                    def analysis = readJSON file: 'repoq-results/analysis.json'
                    def score = analysis.quality_score
                    
                    echo "Quality Score: ${score}"
                    
                    if (score < 7.0) {
                        error("Quality score ${score} below threshold 7.0")
                    }
                }
            }
        }
    }
    
    post {
        always {
            archiveArtifacts artifacts: 'repoq-results/**', allowEmptyArchive: true
            
            publishHTML([
                reportDir: 'repoq-results',
                reportFiles: 'analysis.html',
                reportName: 'RepoQ Quality Report'
            ])
        }
    }
}
```

## Advanced Configurations

### Conditional Analysis

Only analyze changed files:

```yaml
      - name: Get Changed Files
        id: changed-files
        uses: tj-actions/changed-files@v42
        with:
          files: |
            **/*.py
            **/*.js
      
      - name: Analyze Changed Files Only
        if: steps.changed-files.outputs.any_changed == 'true'
        run: |
          FILES="${{ steps.changed-files.outputs.all_changed_files }}"
          uv run repoq analyze . --files $FILES
```

### Matrix Testing

Test against multiple Python versions:

```yaml
jobs:
  quality-check:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: ['3.9', '3.10', '3.11', '3.12']
    
    steps:
      - uses: actions/checkout@v4
      
      - name: Set up Python ${{ matrix.python-version }}
        uses: actions/setup-python@v5
        with:
          python-version: ${{ matrix.python-version }}
      
      - name: Run RepoQ
        run: |
          uv pip install repoq
          uv run repoq analyze .
```

### Caching for Speed

Cache dependencies and analysis results:

```yaml
      - name: Cache RepoQ Results
        uses: actions/cache@v4
        with:
          path: |
            ~/.cache/repoq
            .repoq_cache/
          key: repoq-${{ hashFiles('**/*.py') }}
          restore-keys: |
            repoq-
      
      - name: Run RepoQ with Cache
        run: uv run repoq analyze . --cache
```

### Custom Quality Policy

Use repository-specific thresholds:

```yaml
# quality_policy.yaml
quality_thresholds:
  overall_score: 7.0
  complexity:
    max_cyclomatic: 15
    max_cognitive: 20
  maintainability:
    min_index: 65
  coverage:
    min_test_ratio: 0.7

analyzers:
  structure:
    enabled: true
  complexity:
    enabled: true
    max_complexity: 15
  hotspots:
    enabled: true
    threshold: 100
```

**Workflow:**
```yaml
      - name: Run with Custom Policy
        run: |
          uv run repoq analyze . \
            --config quality_policy.yaml \
            --output results/
```

## Notifications

### Slack Integration

```yaml
      - name: Notify Slack on Failure
        if: failure()
        uses: slackapi/slack-github-action@v1
        with:
          payload: |
            {
              "text": "❌ RepoQ Quality Check Failed",
              "blocks": [
                {
                  "type": "section",
                  "text": {
                    "type": "mrkdwn",
                    "text": "*Quality Check Failed* for <${{ github.event.pull_request.html_url }}|PR #${{ github.event.pull_request.number }}>"
                  }
                }
              ]
            }
        env:
          SLACK_WEBHOOK_URL: ${{ secrets.SLACK_WEBHOOK }}
```

### Email Reports

```yaml
      - name: Send Email Report
        if: always()
        uses: dawidd6/action-send-mail@v3
        with:
          server_address: smtp.gmail.com
          server_port: 587
          username: ${{ secrets.EMAIL_USERNAME }}
          password: ${{ secrets.EMAIL_PASSWORD }}
          subject: RepoQ Quality Report - ${{ github.repository }}
          body: file://repoq-results/analysis.md
          to: team@example.com
          from: ci@example.com
          attachments: repoq-results/analysis.json
```

## Pre-commit Hooks

Run RepoQ before commits:

### .pre-commit-config.yaml

```yaml
repos:
  - repo: local
    hooks:
      - id: repoq-check
        name: RepoQ Quality Check
        entry: repoq analyze . --quick
        language: system
        pass_filenames: false
        stages: [commit]
```

**Install:**
```bash
pip install pre-commit
pre-commit install
```

## Status Badges

### GitHub Actions Badge

Add to `README.md`:

```markdown
[![RepoQ Quality](https://github.com/your-org/your-repo/actions/workflows/repoq.yml/badge.svg)](https://github.com/your-org/your-repo/actions/workflows/repoq.yml)
```

### Custom Quality Badge

Generate dynamic badge with quality score:

```yaml
      - name: Generate Badge
        run: |
          SCORE=$(jq '.quality_score' results/analysis.json)
          COLOR="red"
          
          if (( $(echo "$SCORE >= 8.0" | bc -l) )); then
            COLOR="brightgreen"
          elif (( $(echo "$SCORE >= 6.0" | bc -l) )); then
            COLOR="yellow"
          fi
          
          curl "https://img.shields.io/badge/quality-${SCORE}-${COLOR}" \
            -o results/quality-badge.svg
      
      - name: Upload Badge
        uses: actions/upload-artifact@v4
        with:
          name: quality-badge
          path: results/quality-badge.svg
```

## Troubleshooting

### Issue: "Git history not found"

**Solution**: Fetch full history
```yaml
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0  # Not fetch-depth: 1
```

### Issue: "Out of memory"

**Solution**: Limit analysis scope
```yaml
      - name: Run RepoQ
        run: |
          uv run repoq analyze . \
            --max-depth 3 \
            --exclude "tests/**" \
            --exclude "vendor/**"
```

### Issue: "Analysis too slow"

**Solution**: Use caching and parallelism
```yaml
      - name: Run RepoQ
        run: |
          uv run repoq analyze . \
            --cache \
            --max-workers 4
```

## Best Practices

### 1. Run on Pull Requests

```yaml
on:
  pull_request:
    types: [opened, synchronize, reopened]
```

### 2. Use Quality Gates

```yaml
- name: Quality Gate
  run: |
    if [ $(jq '.quality_score' analysis.json) -lt 7 ]; then
      exit 1
    fi
```

### 3. Track Trends

Store historical data:

```yaml
      - name: Store History
        run: |
          mkdir -p quality-history
          cp results/analysis.json \
            quality-history/$(date +%Y%m%d-%H%M%S).json
          
          git add quality-history/
          git commit -m "Update quality history"
          git push
```

### 4. Make Reports Visible

```yaml
      - name: Create PR Comment
        uses: actions/github-script@v7
        with:
          script: |
            const report = require('./results/analysis.json');
            const comment = `
            ## 📊 Quality Report
            
            **Score**: ${report.quality_score}/10
            **Status**: ${report.quality_score >= 7 ? '✅ PASS' : '❌ FAIL'}
            
            ### Metrics
            - Complexity: ${report.metrics.avg_complexity}
            - Maintainability: ${report.metrics.maintainability_index}
            - Hotspots: ${report.hotspots.length}
            `;
            
            github.rest.issues.createComment({
              issue_number: context.issue.number,
              owner: context.repo.owner,
              repo: context.repo.name,
              body: comment
            });
```

## Next Steps

- **[Tutorial 4: Advanced Filtering](04-advanced-filtering.md)** - Target specific code
- **[Tutorial 5: RDF Queries](05-rdf-queries.md)** - Query analysis data
- **[User Guide: Configuration](../user-guide/configuration.md)** - Customize policies

## Summary

You learned how to:

- ✅ Integrate RepoQ with GitHub Actions, GitLab CI, Jenkins
- ✅ Configure quality gates and thresholds
- ✅ Detect quality regressions
- ✅ Set up notifications (Slack, email)
- ✅ Use pre-commit hooks
- ✅ Generate status badges

**Key Takeaways:**

1. **Automate**: Run on every PR
2. **Enforce**: Use quality gates
3. **Track**: Monitor trends over time
4. **Communicate**: Share results with team
5. **Optimize**: Cache and parallelize

---

!!! success "CI/CD Ready"
    Your repository now has automated quality checks! Every PR will be analyzed and gated on quality standards.
