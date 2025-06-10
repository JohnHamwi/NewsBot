#!/bin/bash
# check_style.sh - Script to check code style and quality for NewsBot

# Color definitions
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}=== NewsBot Code Quality Check ===${NC}"

# Make sure all required packages are installed
echo -e "${YELLOW}Installing required packages...${NC}"
pip install -q flake8 pylint black isort mypy 2>/dev/null

# Function to run a command and handle its output
run_check() {
    local tool=$1
    local cmd=$2
    local args=$3
    
    echo -e "\n${BLUE}Running $tool...${NC}"
    eval "$cmd $args"
    
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✓ $tool check passed!${NC}"
        return 0
    else
        echo -e "${RED}✗ $tool check found issues.${NC}"
        return 1
    fi
}

# Run flake8 syntax check (lighter weight than pylint)
run_check "flake8" "flake8" "--count --select=E9,F63,F7,F82 --exclude=.venv,__pycache__,tests --show-source --statistics src/"

# Run more comprehensive flake8 check
run_check "flake8 (full)" "flake8" "--count --exclude=.venv,__pycache__,tests --max-complexity=10 --max-line-length=100 --statistics src/"

# Run black code formatter in check mode
run_check "black (check)" "black" "--check --line-length=100 src/"

# Run isort import sorter in check mode
run_check "isort (check)" "isort" "--check-only --profile black src/"

# Run pylint on core modules (more intensive)
run_check "pylint (core)" "pylint" "--disable=C0111,C0103 src/core/"

# Run pylint on utility modules
run_check "pylint (utils)" "pylint" "--disable=C0111,C0103 src/utils/"

# Run pylint on cog modules
run_check "pylint (cogs)" "pylint" "--disable=C0111,C0103 src/cogs/"

# Run mypy type check
run_check "mypy" "mypy" "--ignore-missing-imports src/"

echo -e "\n${BLUE}=== Summary ===${NC}"
echo -e "${YELLOW}The code has been checked for style and quality issues.${NC}"
echo -e "${YELLOW}To automatically fix some issues:${NC}"
echo -e "  ${GREEN}black --line-length=100 src/${NC} - Fix code formatting"
echo -e "  ${GREEN}isort --profile black src/${NC} - Fix import sorting"
echo -e "  ${GREEN}autopep8 --in-place --aggressive --aggressive --max-line-length=100 src/**/*.py${NC} - Fix PEP8 issues"
echo -e "\n${YELLOW}Review the output above for issues that need manual fixing.${NC}" 