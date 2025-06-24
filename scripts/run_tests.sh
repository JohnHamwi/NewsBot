#!/bin/bash
# =============================================================================
# NewsBot Test Runner Script
# =============================================================================
# Comprehensive test runner for the NewsBot project with coverage reporting
# and various test execution options.

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_color() {
    printf "${2}${1}${NC}\n"
}

# Function to check if pytest is installed
check_pytest() {
    if ! command -v pytest &> /dev/null; then
        print_color "❌ pytest not found. Installing test dependencies..." "$RED"
        pip install -r test_requirements.txt
    fi
}

# Function to run all tests
run_all_tests() {
    print_color "🧪 Running all tests..." "$BLUE"
    pytest tests/ \
        --cov=src \
        --cov-report=html \
        --cov-report=term \
        --cov-report=xml \
        --html=test_reports/report.html \
        --self-contained-html \
        --json-report --json-report-file=test_reports/report.json
}

# Function to run specific test categories
run_unit_tests() {
    print_color "🔬 Running unit tests..." "$BLUE"
    pytest tests/ -m "not integration" -v
}

run_integration_tests() {
    print_color "🔗 Running integration tests..." "$BLUE"
    pytest tests/test_integration.py -m "integration" -v --tb=short
}

# Function to run tests for specific components
run_core_tests() {
    print_color "⚙️ Running core bot tests..." "$BLUE"
    pytest tests/test_bot_core.py -v
}

run_background_task_tests() {
    print_color "🔄 Running background task tests..." "$BLUE"
    pytest tests/test_background_tasks.py -v
}

run_fetch_tests() {
    print_color "📡 Running fetch cog tests..." "$BLUE"
    pytest tests/test_fetch_cog.py -v
}

run_utils_tests() {
    print_color "🛠️ Running utility tests..." "$BLUE"
    pytest tests/test_utils.py -v
}

# Function to run tests with coverage only
run_coverage() {
    print_color "📊 Running tests with coverage..." "$BLUE"
    pytest tests/ \
        --cov=src \
        --cov-report=term \
        --cov-report=html \
        --cov-fail-under=80
}

# Function to run quick tests (no coverage)
run_quick() {
    print_color "⚡ Running quick tests..." "$BLUE"
    pytest tests/ -x -v --tb=short
}

# Function to run tests in watch mode
run_watch() {
    print_color "👀 Running tests in watch mode..." "$BLUE"
    print_color "Press Ctrl+C to stop watching..." "$YELLOW"
    
    if command -v ptw &> /dev/null; then
        ptw tests/ src/ --runner "pytest tests/ -x -v --tb=short"
    else
        print_color "⚠️ pytest-watch not installed. Install with: pip install pytest-watch" "$YELLOW"
        print_color "Running tests once instead..." "$YELLOW"
        run_quick
    fi
}

# Function to clean test artifacts
clean_test_artifacts() {
    print_color "🧹 Cleaning test artifacts..." "$YELLOW"
    rm -rf .pytest_cache/
    rm -rf htmlcov/
    rm -rf test_reports/
    rm -rf .coverage
    rm -rf **/__pycache__/
    print_color "✅ Test artifacts cleaned!" "$GREEN"
}

# Function to setup test environment
setup_test_env() {
    print_color "🚀 Setting up test environment..." "$BLUE"
    
    # Create test reports directory
    mkdir -p test_reports
    
    # Install test dependencies if needed
    if [ ! -f "test_requirements.txt" ]; then
        print_color "❌ test_requirements.txt not found!" "$RED"
        exit 1
    fi
    
    print_color "📦 Installing test dependencies..." "$YELLOW"
    pip install -r test_requirements.txt
    
    print_color "✅ Test environment ready!" "$GREEN"
}

# Function to run critical tests (for CI/CD)
run_critical() {
    print_color "🎯 Running critical tests..." "$BLUE"
    pytest tests/test_bot_core.py::TestPostingIntervalLogic \
           tests/test_background_tasks.py::TestAutoPostTask \
           tests/test_fetch_cog.py::TestDelayedPosting \
           -v --tb=short
}

# Function to show test statistics
show_stats() {
    print_color "📈 Test Statistics:" "$BLUE"
    echo "Total test files: $(find tests/ -name 'test_*.py' | wc -l)"
    echo "Total test functions: $(grep -r "def test_" tests/ | wc -l)"
    echo "Total test classes: $(grep -r "class Test" tests/ | wc -l)"
    
    if [ -f ".coverage" ]; then
        print_color "📊 Coverage Summary:" "$BLUE"
        python -m coverage report --show-missing
    fi
}

# Function to show help
show_help() {
    print_color "NewsBot Test Runner" "$GREEN"
    echo ""
    print_color "Usage: $0 [command]" "$BLUE"
    echo ""
    print_color "Commands:" "$YELLOW"
    echo "  all          Run all tests with coverage (default)"
    echo "  unit         Run unit tests only"
    echo "  integration  Run integration tests only"
    echo "  core         Run core bot tests"
    echo "  background   Run background task tests"
    echo "  fetch        Run fetch cog tests"
    echo "  utils        Run utility tests"
    echo "  coverage     Run tests with coverage reporting"
    echo "  quick        Run tests quickly (no coverage)"
    echo "  watch        Run tests in watch mode"
    echo "  critical     Run critical tests only"
    echo "  stats        Show test statistics"
    echo "  setup        Setup test environment"
    echo "  clean        Clean test artifacts"
    echo "  health       Run simple health check"
    echo "  deploy       Run pre-deployment check"
    echo "  backup       Create manual backup"
    echo "  backup-status Show backup system status"
    echo "  help         Show this help message"
    echo ""
    print_color "Examples:" "$BLUE"
    echo "  $0                # Run all tests"
    echo "  $0 quick          # Quick test run"
    echo "  $0 core           # Test core functionality"
    echo "  $0 coverage       # Run with coverage"
    echo "  $0 health         # Simple health check"
    echo "  $0 deploy         # Pre-deployment validation"
    echo ""
}

# Main script logic
main() {
    # Ensure we're in the project root
    if [ ! -f "src/bot/newsbot.py" ]; then
        print_color "❌ Please run this script from the NewsBot project root directory!" "$RED"
        exit 1
    fi
    
    # Check for pytest
    check_pytest
    
    # Handle command line arguments
    case "${1:-all}" in
        "all")
            run_all_tests
            ;;
        "unit")
            run_unit_tests
            ;;
        "integration")
            run_integration_tests
            ;;
        "core")
            run_core_tests
            ;;
        "background")
            run_background_task_tests
            ;;
        "fetch")
            run_fetch_tests
            ;;
        "utils")
            run_utils_tests
            ;;
        "coverage")
            run_coverage
            ;;
        "quick")
            run_quick
            ;;
        "watch")
            run_watch
            ;;
        "critical")
            run_critical
            ;;
        "stats")
            show_stats
            ;;
        "setup")
            setup_test_env
            ;;
        "clean")
            clean_test_artifacts
            ;;
        "health")
            print_color "🏥 Running simple health check..." "$BLUE"
            python3 scripts/simple_health_check.py
            ;;
        "deploy")
            print_color "🚀 Running pre-deployment check..." "$BLUE"
            bash scripts/pre_deployment_check.sh
            ;;
        "backup")
            print_color "🗄️ Creating manual backup..." "$BLUE"
            python3 scripts/backup_manager.py create manual
            ;;
        "backup-status")
            print_color "🗄️ Checking backup status..." "$BLUE"
            python3 scripts/backup_manager.py status
            ;;
        "help"|"-h"|"--help")
            show_help
            ;;
        *)
            print_color "❌ Unknown command: $1" "$RED"
            echo ""
            show_help
            exit 1
            ;;
    esac
}

# Run main function
main "$@" 