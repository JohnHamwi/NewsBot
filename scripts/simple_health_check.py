#!/usr/bin/env python3
"""
Simple NewsBot Health Check

A lightweight health check script that doesn't require external dependencies.
Validates basic functionality and runs critical tests.
"""

import os
import sys
import json
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path

def print_colored(text, color_code):
    """Print colored text."""
    print(f"\033[{color_code}m{text}\033[0m")

def print_section(title):
    """Print a section header."""
    print("\n" + "="*50)
    print_colored(f"  {title}", "36")  # Cyan
    print("="*50)

def run_critical_tests():
    """Run the critical logic tests."""
    print_section("🧪 CRITICAL TESTS")
    
    try:
        result = subprocess.run(
            ["python3", "-m", "pytest", "tests/test_critical_logic.py", "-v", "--tb=short"],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode == 0:
            print_colored("✅ Critical Logic Tests: PASSED", "32")  # Green
            print_colored("✅ Posting interval logic validated", "32")
            return True
        else:
            print_colored("❌ Critical Logic Tests: FAILED", "31")  # Red
            print("Error output:")
            print(result.stderr[-500:] if result.stderr else "No error details")
            return False
            
    except subprocess.TimeoutExpired:
        print_colored("❌ Critical Logic Tests: TIMEOUT", "31")
        return False
    except Exception as e:
        print_colored(f"❌ Critical Logic Tests: ERROR - {e}", "31")
        return False

def check_file_structure():
    """Check that required files and directories exist."""
    print_section("📁 FILE STRUCTURE")
    
    required_files = [
        "src/bot/newsbot.py",
        "tests/test_critical_logic.py",
        "scripts/run_tests.sh",
        "pytest.ini"
    ]
    
    required_dirs = [
        "src/",
        "tests/",
        "scripts/",
        "logs/",
        "data/"
    ]
    
    all_good = True
    
    # Check files
    for file_path in required_files:
        if Path(file_path).exists():
            print_colored(f"✅ {file_path}", "32")
        else:
            print_colored(f"❌ {file_path} - MISSING", "31")
            all_good = False
    
    # Check directories
    for dir_path in required_dirs:
        if Path(dir_path).exists():
            print_colored(f"✅ {dir_path}", "32")
        else:
            Path(dir_path).mkdir(parents=True, exist_ok=True)
            print_colored(f"📁 Created {dir_path}", "33")  # Yellow
    
    return all_good

def check_python_syntax():
    """Check Python syntax in source files."""
    print_section("🐍 SYNTAX CHECK")
    
    src_files = list(Path("src").rglob("*.py"))
    
    if not src_files:
        print_colored("❌ No Python files found in src/", "31")
        return False
    
    failed_files = []
    
    for py_file in src_files:
        try:
            with open(py_file, 'r') as f:
                compile(f.read(), str(py_file), 'exec')
            print_colored(f"✅ {py_file}", "32")
        except SyntaxError as e:
            print_colored(f"❌ {py_file} - Syntax Error: {e}", "31")
            failed_files.append(str(py_file))
        except Exception as e:
            print_colored(f"⚠️ {py_file} - Warning: {e}", "33")
    
    if failed_files:
        print_colored(f"\n❌ {len(failed_files)} files have syntax errors", "31")
        return False
    else:
        print_colored(f"\n✅ All {len(src_files)} Python files have valid syntax", "32")
        return True

def check_test_health():
    """Check test suite health."""
    print_section("🏥 TEST HEALTH")
    
    # Count test files
    test_files = list(Path("tests").glob("test_*.py"))
    print_colored(f"📊 Test files: {len(test_files)}", "37")
    
    # Count test functions
    total_tests = 0
    for test_file in test_files:
        try:
            with open(test_file, 'r') as f:
                content = f.read()
                test_count = content.count("def test_")
                total_tests += test_count
                print_colored(f"  {test_file.name}: {test_count} tests", "37")
        except Exception:
            pass
    
    print_colored(f"📊 Total test functions: {total_tests}", "36")
    
    if total_tests >= 100:
        print_colored("✅ Excellent test coverage!", "32")
        return True
    elif total_tests >= 50:
        print_colored("✅ Good test coverage", "32")
        return True
    else:
        print_colored("⚠️ Consider adding more tests", "33")
        return True

def check_configuration():
    """Check configuration validity."""
    print_section("⚙️ CONFIGURATION")
    
    config_files = [
        "config/config.yaml",
        "data/unified_config.json",
        "pytest.ini"
    ]
    
    found_configs = 0
    
    for config_file in config_files:
        if Path(config_file).exists():
            print_colored(f"✅ Found {config_file}", "32")
            found_configs += 1
            
            # Validate JSON files
            if config_file.endswith('.json'):
                try:
                    with open(config_file, 'r') as f:
                        json.load(f)
                    print_colored(f"  ✅ Valid JSON", "32")
                except json.JSONDecodeError as e:
                    print_colored(f"  ❌ Invalid JSON: {e}", "31")
                    return False
        else:
            print_colored(f"⚠️ {config_file} not found", "33")
    
    if found_configs > 0:
        print_colored("✅ Configuration files available", "32")
        return True
    else:
        print_colored("⚠️ No configuration files found - using defaults", "33")
        return True

def generate_health_report():
    """Generate overall health report."""
    print_section("📋 HEALTH REPORT")
    
    checks = [
        ("File Structure", check_file_structure()),
        ("Python Syntax", check_python_syntax()),
        ("Configuration", check_configuration()),
        ("Test Health", check_test_health()),
        ("Critical Tests", run_critical_tests())
    ]
    
    passed = sum(1 for _, result in checks if result)
    total = len(checks)
    score = (passed / total) * 100
    
    print(f"\nHealth Summary:")
    print_colored(f"  ✅ Passed: {passed}/{total}", "32")
    print_colored(f"  📊 Score: {score:.0f}/100", "36")
    
    if score >= 80:
        print_colored("\n🎉 SYSTEM HEALTHY", "32")
        status = "HEALTHY"
    elif score >= 60:
        print_colored("\n⚠️ SYSTEM WARNING", "33")
        status = "WARNING"
    else:
        print_colored("\n❌ SYSTEM CRITICAL", "31")
        status = "CRITICAL"
    
    # Save simple health report
    health_data = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "status": status,
        "score": score,
        "checks": {name: result for name, result in checks}
    }
    
    Path("data").mkdir(exist_ok=True)
    
    try:
        with open("data/health_report.json", "w") as f:
            json.dump(health_data, f, indent=2)
        print_colored(f"\n📄 Health report saved to data/health_report.json", "36")
    except Exception as e:
        print_colored(f"\n⚠️ Could not save health report: {e}", "33")
    
    return score >= 80

def main():
    """Main health check function."""
    print_colored("🏥 NewsBot Simple Health Check", "35")  # Purple
    print_colored(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", "37")
    
    # Ensure we're in the right directory
    if not Path("src/bot").exists():
        print_colored("❌ Please run from NewsBot project root directory", "31")
        sys.exit(1)
    
    # Run health check
    healthy = generate_health_report()
    
    print_colored("\n" + "="*50, "37")
    
    if healthy:
        print_colored("✅ Bot is ready for operation!", "32")
        print("\nQuick commands:")
        print("  Run critical tests: python -m pytest tests/test_critical_logic.py -v")
        print("  Run all tests: ./scripts/run_tests.sh")
        print("  Check logs: tail -f logs/newsbot.log")
        sys.exit(0)
    else:
        print_colored("❌ Issues detected - please fix before deployment", "31")
        sys.exit(1)

if __name__ == "__main__":
    main() 