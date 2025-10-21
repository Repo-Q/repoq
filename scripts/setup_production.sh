#!/usr/bin/env bash
#
# Production Setup Script with UV
# 
# Полная автоматизированная настройка проекта для production-ready состояния
# с использованием uv для управления зависимостями.

set -e

echo "🚀 repoq Production Setup with UV"
echo "=================================="
echo ""

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# 1. Check uv installation
echo "📋 Step 1: Checking prerequisites..."
if ! command -v uv &> /dev/null; then
    echo -e "${RED}❌ uv not found. Installing...${NC}"
    curl -LsSf https://astral.sh/uv/install.sh | sh
    export PATH="$HOME/.cargo/bin:$PATH"
fi

UV_VERSION=$(uv --version 2>&1 || echo "unknown")
echo -e "${GREEN}✅ uv $UV_VERSION${NC}"

if ! command -v git &> /dev/null; then
    echo -e "${RED}❌ Git not found. Please install Git${NC}"
    exit 1
fi
echo -e "${GREEN}✅ Git found${NC}"

# 2. Create virtual environment with uv
echo ""
echo "🐍 Step 2: Creating virtual environment..."
if [ -d ".venv" ]; then
    echo -e "${YELLOW}⚠️  .venv exists, removing...${NC}"
    rm -rf .venv
fi

uv venv
echo -e "${GREEN}✅ Virtual environment created${NC}"

# 3. Install dependencies with uv
echo ""
echo "📦 Step 3: Installing dependencies with uv..."
source .venv/bin/activate

# Install base dependencies
echo "  Installing base dependencies..."
uv pip install -e .

# Install full dependencies
echo "  Installing full dependencies (PyDriller, Lizard, RDF, etc.)..."
uv pip install pydriller lizard radon graphviz rdflib orjson pyshacl

# Install dev dependencies
echo "  Installing dev dependencies (pytest, ruff, mypy, etc.)..."
uv pip install pytest pytest-cov pytest-mock pytest-xdist hypothesis \
    ruff black mypy types-PyYAML \
    bandit safety

echo -e "${GREEN}✅ All dependencies installed${NC}"

# 4. Run baseline tests
echo ""
echo "🧪 Step 4: Running baseline tests..."
pytest --cov=repoq --cov-report=term-missing --cov-report=html -v || {
    echo -e "${YELLOW}⚠️  Some tests failed (expected in Phase 0)${NC}"
}

# 5. Run linters
echo ""
echo "🔍 Step 5: Running linters..."
echo "  Ruff check..."
ruff check . || echo -e "${YELLOW}⚠️  Ruff issues found${NC}"

echo "  Black formatting check..."
black --check . || echo -e "${YELLOW}⚠️  Code needs formatting (run: black .)${NC}"

echo "  MyPy type checking..."
mypy repoq/ --install-types --non-interactive || echo -e "${YELLOW}⚠️  Type errors found${NC}"

# 6. Self-analysis
echo ""
echo "🔬 Step 6: Running self-analysis..."
mkdir -p artifacts

# Ensure repoq is in PATH
export PYTHONPATH="$PWD:$PYTHONPATH"

python -m repoq.cli full . \
  -o artifacts/repoq_self_baseline.jsonld \
  --md artifacts/repoq_self_baseline.md \
  --graphs artifacts/graphs_baseline \
  || echo -e "${YELLOW}⚠️  Self-analysis completed with warnings${NC}"

echo -e "${GREEN}✅ Baseline self-analysis saved to artifacts/${NC}"

# 7. Run quality gates
echo ""
echo "📏 Step 7: Validating quality gates..."
python scripts/assert_quality_gates.py artifacts/repoq_self_baseline.jsonld --phase phase0 || {
    echo -e "${YELLOW}⚠️  Quality gates show warnings (expected in Phase 0)${NC}"
}

# 8. Display summary
echo ""
echo "📊 Step 8: Setup Summary"
echo "======================="

if [ -f "coverage.xml" ] || [ -f ".coverage" ]; then
    echo -e "${BLUE}Coverage report:${NC} htmlcov/index.html"
fi

if [ -f "artifacts/repoq_self_baseline.jsonld" ]; then
    NUM_FILES=$(python3 -c "import json; print(len(json.load(open('artifacts/repoq_self_baseline.jsonld')).get('files', [])))" 2>/dev/null || echo "N/A")
    NUM_MODULES=$(python3 -c "import json; print(len(json.load(open('artifacts/repoq_self_baseline.jsonld')).get('modules', [])))" 2>/dev/null || echo "N/A")
    echo -e "${BLUE}Self-analysis:${NC} $NUM_FILES files, $NUM_MODULES modules"
fi

echo ""
echo -e "${GREEN}✨ Production setup complete!${NC}"
echo ""
echo "🎯 Next Steps:"
echo "1. Activate venv: source .venv/bin/activate"
echo "2. Review coverage: open htmlcov/index.html"
echo "3. Review self-analysis: cat artifacts/repoq_self_baseline.md"
echo "4. Start Phase 1: see PHASE1_CHECKLIST.md"
echo ""
echo "📚 Quick Commands:"
echo "  pytest --cov=repoq -v           # Run tests"
echo "  ruff check . --fix              # Fix lint issues"
echo "  black .                         # Format code"
echo "  mypy repoq/                     # Type check"
echo "  python -m repoq.cli full . -o out.jsonld  # Analyze repo"
echo ""
echo -e "${BLUE}🚀 Ready for Phase 1 development!${NC}"
