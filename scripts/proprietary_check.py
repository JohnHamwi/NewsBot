#!/usr/bin/env python3
"""
🔒 PROPRIETARY SOFTWARE - Proprietary Notice Verification Script

This script verifies that all required proprietary software notices
are present in the NewsBot project files.

Copyright (c) 2025 NewsBot Project. All rights reserved.
CONFIDENTIAL - For authorized use only.
"""

import os
import sys
from pathlib import Path

def check_proprietary_notices():
    """Check that all key files have proprietary notices."""
    
    project_root = Path(__file__).parent.parent
    
    # Key files that should have proprietary notices
    key_files = [
        "LICENSE",
        "README.md", 
        "CONTRIBUTING.md",
        "SECURITY.md",
        "run.py",
        "src/bot/main.py",
        "src/bot/newsbot.py",
        "docker-compose.yml",
        "Dockerfile"
    ]
    
    # Required notice indicators
    required_notices = [
        "PROPRIETARY SOFTWARE",
        "Copyright (c) 2025 NewsBot Project",
        "private use only",
        "CONFIDENTIAL"
    ]
    
    print("🔒 PROPRIETARY SOFTWARE VERIFICATION")
    print("=" * 50)
    
    all_good = True
    
    for file_path in key_files:
        full_path = project_root / file_path
        
        if not full_path.exists():
            print(f"❌ MISSING: {file_path}")
            all_good = False
            continue
            
        try:
            content = full_path.read_text(encoding='utf-8')
            
            has_notices = []
            for notice in required_notices:
                if notice.lower() in content.lower():
                    has_notices.append(True)
                else:
                    has_notices.append(False)
            
            if all(has_notices):
                print(f"✅ PROTECTED: {file_path}")
            else:
                print(f"⚠️  INCOMPLETE: {file_path}")
                missing = [notice for notice, present in zip(required_notices, has_notices) if not present]
                print(f"   Missing: {', '.join(missing)}")
                all_good = False
                
        except Exception as e:
            print(f"❌ ERROR reading {file_path}: {e}")
            all_good = False
    
    print("\n" + "=" * 50)
    
    if all_good:
        print("✅ ALL FILES PROPERLY PROTECTED")
        print("🔒 Project is properly marked as proprietary software")
    else:
        print("❌ SOME FILES NEED ATTENTION")
        print("⚠️  Please add missing proprietary notices")
        
    return all_good

def check_git_status():
    """Check if this is still a git repository."""
    project_root = Path(__file__).parent.parent
    git_dir = project_root / ".git"
    
    if git_dir.exists():
        print("\n🔧 RECOMMENDATION:")
        print("Consider removing .git directory to fully disconnect from any public repository:")
        print("  rm -rf .git")
        print("  # This will remove all git history and make it a standalone project")

if __name__ == "__main__":
    print("🇸🇾 Syrian NewsBot - Proprietary Software Verification")
    print("For private Syrian Discord server use only\n")
    
    success = check_proprietary_notices()
    check_git_status()
    
    sys.exit(0 if success else 1) 