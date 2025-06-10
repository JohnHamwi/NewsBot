#!/usr/bin/env python
"""
Dependency Checker

This script checks if all required dependencies are installed and reports any missing packages.
It also verifies that installed versions meet minimum requirements.
"""

import os
import sys
import importlib.util
import pkg_resources
from pathlib import Path
import subprocess
import re

# Colors for terminal output
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
RESET = "\033[0m"
BOLD = "\033[1m"

def print_status(message, status, details=None):
    """Print a formatted status message."""
    if status == "OK":
        status_color = f"{GREEN}[OK]{RESET}"
    elif status == "WARNING":
        status_color = f"{YELLOW}[WARNING]{RESET}"
    else:
        status_color = f"{RED}[ERROR]{RESET}"
    
    print(f"{status_color} {message}")
    if details:
        print(f"     {details}")


def check_python_version():
    """Check if the Python version is adequate."""
    import platform
    version = platform.python_version()
    version_tuple = tuple(map(int, version.split('.')))
    
    if version_tuple < (3, 9):
        print_status(
            f"Python version: {version}",
            "WARNING",
            "NewsBot recommends Python 3.9 or higher for best compatibility."
        )
    else:
        print_status(f"Python version: {version}", "OK")


def parse_requirements(req_path):
    """Parse requirements.txt into a dictionary of package names and versions."""
    requirements = {}
    comment_pattern = re.compile(r"\s*#.*$")
    
    with open(req_path, 'r') as f:
        for line in f:
            # Skip empty lines and comments
            line = line.strip()
            line = comment_pattern.sub("", line)
            if not line or line.startswith('#'):
                continue
                
            # Handle environment markers
            if ";" in line:
                req, marker = line.split(";", 1)
                # Skip if the environment marker doesn't apply to this system
                try:
                    if not pkg_resources.evaluate_marker(marker.strip()):
                        continue
                except:
                    # If there's an error evaluating the marker, include the package anyway
                    req = line
            else:
                req = line
                
            # Handle version specifiers
            try:
                pkg_req = pkg_resources.Requirement.parse(req)
                package_name = pkg_req.project_name
                specs = pkg_req.specs
                requirements[package_name] = specs
            except:
                # For lines that can't be parsed (like -r other_requirements.txt)
                pass
                
    return requirements


def check_installed_packages(requirements):
    """Check if required packages are installed with correct versions."""
    installed_packages = {pkg.project_name: pkg.version for pkg in pkg_resources.working_set}
    missing = []
    outdated = []
    
    for package, specs in requirements.items():
        if package not in installed_packages:
            missing.append(package)
            continue
            
        installed_version = installed_packages[package]
        
        # Check version constraints
        for operator, version in specs:
            if operator == '>=':
                if pkg_resources.parse_version(installed_version) < pkg_resources.parse_version(version):
                    outdated.append((package, installed_version, operator, version))
            elif operator == '==':
                if pkg_resources.parse_version(installed_version) != pkg_resources.parse_version(version):
                    outdated.append((package, installed_version, operator, version))
            elif operator == '>':
                if pkg_resources.parse_version(installed_version) <= pkg_resources.parse_version(version):
                    outdated.append((package, installed_version, operator, version))
    
    return missing, outdated


def check_optional_dependencies():
    """Check if recommended optional dependencies are installed."""
    optional_deps = {
        "matplotlib": "For log visualization and reporting",
        "fpdf": "For PDF report generation",
        "cryptg": "For faster Telegram encryption/decryption",
        "aiohttp": "For more efficient HTTP requests",
        "redis": "For caching support"
    }
    
    missing_optional = []
    
    for package, description in optional_deps.items():
        if importlib.util.find_spec(package) is None:
            missing_optional.append((package, description))
    
    return missing_optional


def print_pip_command(missing, outdated):
    """Generate and print pip command to install missing/outdated packages."""
    if not missing and not outdated:
        return
        
    cmd = [sys.executable, "-m", "pip", "install"]
    
    for package in missing:
        cmd.append(package)
        
    for package, _, operator, version in outdated:
        cmd.append(f"{package}{operator}{version}")
    
    print("\nYou can install missing/outdated packages with:")
    print(f"{BOLD}{' '.join(cmd)}{RESET}")


def main():
    """Main function."""
    print(f"{BOLD}NewsBot Dependency Checker{RESET}")
    print("===============================")
    
    # Get the project root directory
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    req_path = project_root / "requirements.txt"
    
    # Check Python version
    check_python_version()
    
    # Check if requirements.txt exists
    if not req_path.exists():
        print_status("requirements.txt file", "ERROR", f"Could not find {req_path}")
        return
        
    print_status("requirements.txt file", "OK")
    
    # Parse requirements
    try:
        requirements = parse_requirements(req_path)
        print_status(f"Parsed {len(requirements)} requirements", "OK")
    except Exception as e:
        print_status("Parsing requirements.txt", "ERROR", str(e))
        return
    
    # Check installed packages
    missing, outdated = check_installed_packages(requirements)
    
    if missing:
        print_status(
            f"Missing packages: {', '.join(missing)}",
            "ERROR",
            "These packages are required but not installed."
        )
    else:
        print_status("All required packages are installed", "OK")
    
    if outdated:
        for package, installed, operator, required in outdated:
            print_status(
                f"Package {package} version {installed} does not meet requirement {operator}{required}",
                "WARNING"
            )
    else:
        print_status("All package versions meet requirements", "OK")
    
    # Check optional dependencies
    missing_optional = check_optional_dependencies()
    
    if missing_optional:
        print("\n{BOLD}Optional Dependencies:{RESET}")
        for package, description in missing_optional:
            print_status(
                f"Optional package {package} is not installed",
                "WARNING",
                description
            )
    
    # Print pip command if needed
    print_pip_command(missing, outdated)


if __name__ == "__main__":
    main() 