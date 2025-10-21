# Workflows

!!! success "Best Practices"
    Common workflows and best practices for using RepoQ effectively in different scenarios.

## Daily Development Workflows

### 1. Pre-Commit Quality Check

Check code quality before committing:

```bash
#!/bin/bash
# .git/hooks/pre-commit

# Run quick analysis on staged files
STAGED_FILES=$(git diff --cached --name-only --diff-filter=ACM | grep "\.py$")

if [ -n "$STAGED_FILES" ]; then
    echo "🔍 Running RepoQ quality check..."
    
    # Analyze staged files
    repoq complexity . --include "$STAGED_FILES" --cyclomatic-max 15
    
    if [ $? -ne 0 ]; then
        echo "❌ Quality check failed. Please fix issues before committing."
        exit 1
    fi
    
    echo "✅ Quality check passed!"
fi
```

### 2. Feature Branch Analysis

Compare feature branch against main:

```bash
# Analyze current branch
repoq analyze . --output feature-analysis/

# Checkout main and analyze
git checkout main
repoq analyze . --output main-analysis/

# Compare results
repoq diff main-analysis/analysis.json feature-analysis/analysis.json

# Return to feature branch
git checkout -
```

### 3. Refactoring Workflow

Before refactoring, establish baseline:

```bash
# 1. Analyze before refactoring
repoq analyze . --output baseline/

# 2. Refactor code
# ... make changes ...

# 3. Analyze after refactoring
repoq analyze . --output refactored/

# 4. Compare
repoq diff baseline/analysis.json refactored/analysis.json

# 5. Verify improvements
# Check that complexity decreased, quality increased
```

---

## CI/CD Workflows

### 1. Pull Request Quality Gate

GitHub Actions workflow:

```yaml
# .github/workflows/pr-quality.yml
name: PR Quality Gate

on:
  pull_request:
    branches: [main, develop]

jobs:
  quality-check:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0  # Full history
      
      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      
      - name: Install RepoQ
        run: |
          pip install uv
          uv pip install repoq[full]
      
      - name: Run Quality Analysis
        run: |
          repoq analyze . \
            --output pr-analysis \
            --format json \
            --fail-below 7.0
      
      - name: Comment on PR
        if: always()
        uses: actions/github-script@v7
        with:
          script: |
            const fs = require('fs');
            const analysis = JSON.parse(fs.readFileSync('pr-analysis/analysis.json'));
            const score = analysis.quality_score;
            const message = `## 📊 RepoQ Quality Report\n\n` +
                          `**Quality Score:** ${score}/10\n\n` +
                          `**Metrics:**\n` +
                          `- Complexity: ${analysis.metrics.complexity}\n` +
                          `- Maintainability: ${analysis.metrics.maintainability}\n` +
                          `- Test Coverage: ${analysis.metrics.coverage}\n\n` +
                          `[View Full Report](${process.env.GITHUB_SERVER_URL}/${process.env.GITHUB_REPOSITORY}/actions/runs/${process.env.GITHUB_RUN_ID})`;
            
            github.rest.issues.createComment({
              issue_number: context.issue.number,
              owner: context.repo.owner,
              repo: context.repo.repo,
              body: message
            });
      
      - name: Upload Reports
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: quality-reports
          path: pr-analysis/
```

### 2. Nightly Quality Monitoring

Track quality trends over time:

```yaml
# .github/workflows/nightly-quality.yml
name: Nightly Quality Monitoring

on:
  schedule:
    - cron: '0 2 * * *'  # 2 AM daily

jobs:
  monitor:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0
      
      - name: Install RepoQ
        run: pip install repoq[full]
      
      - name: Run Full Analysis
        run: |
          repoq analyze . \
            --output nightly-$(date +%Y%m%d) \
            --format json,jsonld
      
      - name: Store Metrics
        run: |
          # Extract metrics
          SCORE=$(jq -r '.quality_score' nightly-*/analysis.json)
          DATE=$(date +%Y-%m-%d)
          
          # Append to metrics file
          echo "$DATE,$SCORE" >> quality-history.csv
          
          # Commit updated history
          git config user.name "Quality Bot"
          git config user.email "bot@example.com"
          git add quality-history.csv
          git commit -m "chore: update quality metrics [$DATE]"
          git push
      
      - name: Alert on Degradation
        run: |
          CURRENT=$(jq -r '.quality_score' nightly-*/analysis.json)
          THRESHOLD=7.0
          
          if (( $(echo "$CURRENT < $THRESHOLD" | bc -l) )); then
            curl -X POST ${{ secrets.SLACK_WEBHOOK }} \
              -H 'Content-Type: application/json' \
              -d "{\"text\": \"⚠️ Quality score dropped below $THRESHOLD: $CURRENT\"}"
          fi
```

### 3. Release Quality Verification

Ensure quality before releases:

```yaml
# .github/workflows/release.yml
name: Release

on:
  push:
    tags:
      - 'v*'

jobs:
  verify-quality:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0
      
      - name: Install RepoQ
        run: pip install repoq[full]
      
      - name: Verify Release Quality
        run: |
          repoq analyze . \
            --output release-analysis \
            --config .repoq/release-policy.yaml \
            --fail-below 8.0  # Strict for releases
      
      - name: Generate Release Notes
        run: |
          # Extract quality metrics for release notes
          SCORE=$(jq -r '.quality_score' release-analysis/analysis.json)
          COMPLEXITY=$(jq -r '.metrics.avg_complexity' release-analysis/analysis.json)
          
          cat >> release-notes.md <<EOF
          ## Quality Metrics
          
          - Quality Score: $SCORE/10
          - Average Complexity: $COMPLEXITY
          - Test Coverage: $(jq -r '.metrics.coverage' release-analysis/analysis.json)%
          EOF
      
      - name: Create Release
        uses: actions/create-release@v1
        with:
          tag_name: ${{ github.ref }}
          release_name: Release ${{ github.ref }}
          body_path: release-notes.md
```

---

## Code Review Workflows

### 1. Reviewer Checklist

Use RepoQ to assist code reviews:

```bash
# Before reviewing PR
PR_BRANCH="feature/new-feature"

# Checkout PR branch
git checkout $PR_BRANCH

# Run focused analysis on changed files
CHANGED_FILES=$(git diff --name-only main...HEAD | grep "\.py$")

# Analyze changed files
repoq complexity . --include "$CHANGED_FILES"
repoq hotspots . --include "$CHANGED_FILES"

# Generate review notes
repoq analyze . --output pr-review/ --format markdown

# Use output/pr-review/full_report.md in review comments
```

### 2. Automated Review Comments

Bot that comments on high complexity:

```python
# review_bot.py
import json
import subprocess
import sys

def analyze_pr_diff():
    # Get changed files
    result = subprocess.run(
        ["git", "diff", "--name-only", "main...HEAD"],
        capture_output=True,
        text=True
    )
    changed_files = result.stdout.strip().split('\n')
    
    # Run complexity analysis
    subprocess.run([
        "repoq", "complexity", ".",
        "--include", ",".join(changed_files),
        "--format", "json",
        "--output", "pr-analysis"
    ])
    
    # Parse results
    with open("pr-analysis/complexity.json") as f:
        data = json.load(f)
    
    # Find high complexity functions
    issues = []
    for func in data["functions"]:
        if func["cyclomatic"] > 15:
            issues.append(
                f"⚠️ `{func['name']}` in `{func['file']}` has high complexity: {func['cyclomatic']}"
            )
    
    return issues

if __name__ == "__main__":
    issues = analyze_pr_diff()
    
    if issues:
        print("## 🔍 RepoQ Review\n")
        print("\n".join(issues))
        print("\nConsider refactoring these functions to reduce complexity.")
        sys.exit(1)
    else:
        print("✅ No complexity issues found!")
        sys.exit(0)
```

---

## Maintenance Workflows

### 1. Technical Debt Tracking

Track and prioritize technical debt:

```bash
# Monthly technical debt report
repoq weakness . --output debt-report/

# Extract TODOs and FIXMEs
jq -r '.weaknesses[] | select(.type=="TODO" or .type=="FIXME") | "\(.file):\(.line) - \(.message)"' \
  debt-report/weaknesses.json > debt-backlog.txt

# Prioritize by hotspot score
repoq hotspots . --output hotspots-report/

# Combine for prioritization
python prioritize_debt.py debt-backlog.txt hotspots-report/hotspots.json
```

### 2. Dependency Update Impact

Assess impact of dependency updates:

```bash
# Before update
repoq analyze . --output before-update/

# Update dependencies
uv sync --upgrade

# After update
repoq analyze . --output after-update/

# Compare
repoq diff before-update/analysis.json after-update/analysis.json

# If quality degraded, investigate or rollback
```

### 3. Legacy Code Modernization

Track progress on legacy code modernization:

```bash
# Baseline of legacy code
repoq analyze legacy/ --output legacy-baseline/

# After modernization sprint
repoq analyze legacy/ --output legacy-sprint-1/

# Measure improvements
repoq diff legacy-baseline/analysis.json legacy-sprint-1/analysis.json

# Extract metrics
BEFORE=$(jq -r '.quality_score' legacy-baseline/analysis.json)
AFTER=$(jq -r '.quality_score' legacy-sprint-1/analysis.json)
IMPROVEMENT=$(echo "$AFTER - $BEFORE" | bc)

echo "Quality improved by $IMPROVEMENT points!"
```

---

## Team Workflows

### 1. Team Quality Dashboard

Aggregate quality metrics across team:

```bash
# Each developer runs analysis
repoq analyze ~/projects/project-a --output ~/quality-reports/project-a/
repoq analyze ~/projects/project-b --output ~/quality-reports/project-b/

# Aggregate script
python aggregate_metrics.py ~/quality-reports/ > team-dashboard.html

# Serve dashboard
python -m http.server 8000 --directory ~/quality-reports/
```

### 2. Knowledge Sharing Workflow

Use analysis to identify knowledge silos:

```bash
# Find files with single contributor (knowledge silo risk)
repoq history . --output history-report/

# Extract single-author files
jq -r '.files[] | select(.authors | length == 1) | .path' \
  history-report/history.json > knowledge-silos.txt

# Prioritize complex single-author files
repoq complexity . --include $(cat knowledge-silos.txt | tr '\n' ',')
```

### 3. Onboarding New Developers

Help new developers understand codebase:

```bash
# Generate comprehensive overview
repoq analyze . --output onboarding-docs/

# Create onboarding guide
cat > onboarding/code-overview.md <<EOF
# Code Overview

## Project Structure
$(cat onboarding-docs/structure_report.md)

## Key Areas to Understand
$(jq -r '.hotspots[:5] | .[] | "- \(.file): \(.reason)"' onboarding-docs/hotspots.json)

## Recommended Reading Order
1. Start with core modules (lowest complexity)
2. Read tests to understand behavior
3. Review high-level architecture
EOF
```

---

## Research & Analysis Workflows

### 1. Architectural Pattern Study

Study patterns across multiple projects:

```bash
# Analyze multiple projects
for repo in ~/projects/*; do
    echo "Analyzing $repo..."
    repoq structure "$repo" \
      --output "pattern-study/$(basename $repo)" \
      --format json
done

# Extract patterns
for file in pattern-study/*/structure.json; do
    jq -r '.patterns[] | "\(.name),\(.confidence)"' "$file"
done > patterns.csv

# Analyze with R/Python
python analyze_patterns.py patterns.csv
```

### 2. Quality Trend Analysis

Long-term quality trend analysis:

```bash
# Historical analysis across commits
for commit in $(git log --format=%H --reverse); do
    git checkout $commit
    DATE=$(git show -s --format=%ci $commit | cut -d' ' -f1)
    
    repoq analyze . --output "history/$commit/" --format json
    
    # Extract score
    SCORE=$(jq -r '.quality_score' "history/$commit/analysis.json")
    echo "$DATE,$commit,$SCORE" >> quality-timeline.csv
done

# Visualize timeline
python plot_quality_timeline.py quality-timeline.csv
```

---

## Integration Workflows

### 1. Jira/GitHub Issues Integration

Create issues from RepoQ findings:

```python
# create_issues.py
import json
from github import Github

# Load RepoQ results
with open("output/hotspots.json") as f:
    hotspots = json.load(f)

# GitHub API
g = Github("your-token")
repo = g.get_repo("owner/repo")

# Create issues for hotspots
for hotspot in hotspots["hotspots"][:5]:  # Top 5
    title = f"Refactor {hotspot['file']} (complexity: {hotspot['complexity']})"
    body = f"""
    ## 🔥 Code Hotspot Detected
    
    **File:** `{hotspot['file']}`
    **Complexity:** {hotspot['complexity']}
    **Changes:** {hotspot['changes']} commits
    **Hotspot Score:** {hotspot['score']}/10
    
    ### Recommendations
    {hotspot['recommendations']}
    
    ### Generated by RepoQ
    """
    
    repo.create_issue(
        title=title,
        body=body,
        labels=["technical-debt", "refactoring"]
    )
```

### 2. Slack Notifications

Post quality updates to Slack:

```bash
# slack_notify.sh
#!/bin/bash

SCORE=$(jq -r '.quality_score' output/analysis.json)
WEBHOOK_URL="your-slack-webhook-url"

curl -X POST "$WEBHOOK_URL" \
  -H 'Content-Type: application/json' \
  -d "{
    \"text\": \"📊 Code Quality Report\",
    \"attachments\": [{
      \"color\": \"good\",
      \"fields\": [
        {\"title\": \"Quality Score\", \"value\": \"$SCORE/10\", \"short\": true},
        {\"title\": \"Project\", \"value\": \"MyProject\", \"short\": true}
      ]
    }]
  }"
```

---

## Next Steps

- **[Configuration](configuration.md)**: Customize for your workflows
- **[CLI Commands](commands.md)**: Complete command reference
- **[Tutorials](../tutorials/)**: Detailed step-by-step guides
- **[API Reference](../api/reference.md)**: Programmatic integration

!!! tip "Automation"
    Automate these workflows with cron jobs, CI/CD pipelines, or git hooks to make quality checks seamless and consistent.
