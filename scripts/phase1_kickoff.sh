#!/usr/bin/env bash
#
# Quick Start Script for Phase 1
# 
# Автоматизирует первые шаги для начала работы над доведением
# repoq до production-ready состояния.
#
# Usage: ./scripts/phase1_kickoff.sh

set -e

echo "🚀 repoq Phase 1 Kickoff — Testing Infrastructure"
echo "=================================================="
echo ""

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# 1. Check prerequisites
echo "📋 Step 1: Checking prerequisites..."
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}❌ Python 3 not found. Please install Python 3.9+${NC}"
    exit 1
fi

PYTHON_VERSION=$(python3 --version | cut -d' ' -f2)
echo -e "${GREEN}✅ Python $PYTHON_VERSION found${NC}"

if ! command -v git &> /dev/null; then
    echo -e "${RED}❌ Git not found. Please install Git${NC}"
    exit 1
fi
echo -e "${GREEN}✅ Git found${NC}"

# 2. Install dependencies
echo ""
echo "📦 Step 2: Installing dependencies..."
python3 -m pip install --upgrade pip setuptools wheel 2>/dev/null || {
    echo -e "${YELLOW}⚠️  pip not found, attempting to bootstrap...${NC}"
    curl -sS https://bootstrap.pypa.io/get-pip.py | python3
}
python3 -m pip install -e ".[full,dev]"
echo -e "${GREEN}✅ Dependencies installed${NC}"

# 3. Run baseline tests
echo ""
echo "🧪 Step 3: Running baseline tests..."
pytest --cov=repoq --cov-report=term-missing --cov-report=html || true
echo -e "${YELLOW}⚠️  Baseline coverage is low (expected in Phase 0)${NC}"
echo -e "${YELLOW}   Target: 80%+ by end of Phase 1${NC}"

# 4. Run linters
echo ""
echo "🔍 Step 4: Running linters..."
ruff check . --fix || echo -e "${YELLOW}⚠️  Some lint issues found (will fix in Phase 1)${NC}"
black --check . || echo -e "${YELLOW}⚠️  Code not formatted (run 'black .' to fix)${NC}"
mypy repoq/ || echo -e "${YELLOW}⚠️  Type errors found (will fix in Phase 1)${NC}"

# 5. Self-analysis
echo ""
echo "🔬 Step 5: Running self-analysis..."
mkdir -p artifacts
repoq full . \
  -o artifacts/repoq_self_baseline.jsonld \
  --md artifacts/repoq_self_baseline.md \
  --ttl artifacts/repoq_self_baseline.ttl \
  --graphs artifacts/graphs_baseline \
  || echo -e "${YELLOW}⚠️  Self-analysis completed with warnings (expected)${NC}"

echo -e "${GREEN}✅ Baseline self-analysis saved to artifacts/${NC}"

# 6. Display results
echo ""
echo "📊 Step 6: Summary"
echo "=================="

if [ -f "coverage.xml" ]; then
    COVERAGE=$(grep -oP 'line-rate="\K[0-9.]+' coverage.xml | head -1)
    COVERAGE_PCT=$(echo "$COVERAGE * 100" | bc)
    echo -e "Coverage: ${YELLOW}${COVERAGE_PCT}%${NC} (target: 80%)"
else
    echo -e "Coverage: ${RED}Not measured${NC}"
fi

if [ -f "artifacts/repoq_self_baseline.jsonld" ]; then
    NUM_FILES=$(jq '.files | length' artifacts/repoq_self_baseline.jsonld)
    NUM_MODULES=$(jq '.modules | length' artifacts/repoq_self_baseline.jsonld)
    NUM_ISSUES=$(jq '.issues | length' artifacts/repoq_self_baseline.jsonld)
    echo -e "Self-analysis: ${GREEN}${NUM_FILES} files, ${NUM_MODULES} modules, ${NUM_ISSUES} issues${NC}"
else
    echo -e "Self-analysis: ${RED}Failed${NC}"
fi

echo ""
echo "🎯 Next Steps:"
echo "1. Review coverage report: open htmlcov/index.html"
echo "2. Review self-analysis: cat artifacts/repoq_self_baseline.md"
echo "3. Start Phase 1 Sprint 1: see PHASE1_CHECKLIST.md"
echo "4. Write your first test: tests/analyzers/test_structure.py"
echo ""
echo "📚 Resources:"
echo "- Full roadmap: ROADMAP.md"
echo "- Sprint checklist: PHASE1_CHECKLIST.md"
echo "- Executive summary: EXECUTIVE_SUMMARY.md"
echo ""
echo -e "${GREEN}✨ Phase 1 kickoff complete! Ready to start development.${NC}"
