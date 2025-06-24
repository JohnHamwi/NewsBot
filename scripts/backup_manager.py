#!/usr/bin/env python3
"""
=============================================================================
NewsBot Backup Manager
=============================================================================
Command-line tool for managing automated backups.

Usage:
    python scripts/backup_manager.py create [type]     # Create a backup
    python scripts/backup_manager.py list             # List all backups
    python scripts/backup_manager.py status           # Show backup status
    python scripts/backup_manager.py restore <name>   # Restore from backup
    python scripts/backup_manager.py cleanup          # Clean old backups
    python scripts/backup_manager.py config           # Show backup configuration
"""

import argparse
import asyncio
import sys
import json
from pathlib import Path
from datetime import datetime
from typing import List, Dict

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.monitoring.backup_scheduler import BackupScheduler, BackupConfig


def format_size(bytes_size: int) -> str:
    """Format file size in human readable format."""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if bytes_size < 1024.0:
            return f"{bytes_size:.1f}{unit}"
        bytes_size /= 1024.0
    return f"{bytes_size:.1f}TB"


def format_timestamp(timestamp_str: str) -> str:
    """Format ISO timestamp for display."""
    try:
        dt = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    except:
        return timestamp_str


def print_colored(text: str, color: str = None) -> None:
    """Print colored text to console."""
    colors = {
        'red': '\033[91m',
        'green': '\033[92m',
        'yellow': '\033[93m',
        'blue': '\033[94m',
        'purple': '\033[95m',
        'cyan': '\033[96m',
        'white': '\033[97m',
        'bold': '\033[1m',
        'reset': '\033[0m'
    }
    
    if color and color in colors:
        print(f"{colors[color]}{text}{colors['reset']}")
    else:
        print(text)


def create_backup(backup_type: str = "manual") -> bool:
    """Create a new backup."""
    print_colored(f"🗄️ Creating {backup_type} backup...", "blue")
    
    try:
        scheduler = BackupScheduler()
        metadata = scheduler.create_backup(backup_type)
        
        if metadata.success:
            print_colored("✅ Backup created successfully!", "green")
            print(f"📁 Files: {', '.join(metadata.files_included)}")
            print(f"📊 Size: {format_size(metadata.total_size_bytes)}")
            print(f"🗜️ Compression: {metadata.compression_ratio:.2f}x")
            return True
        else:
            print_colored(f"❌ Backup failed: {metadata.error_message}", "red")
            return False
            
    except Exception as e:
        print_colored(f"❌ Error creating backup: {e}", "red")
        return False


def list_backups() -> None:
    """List all available backups."""
    try:
        scheduler = BackupScheduler()
        backup_dir = scheduler.backup_dir
        
        # Get all backup files
        backup_files = list(backup_dir.glob("newsbot_backup_*.tar.gz"))
        
        if not backup_files:
            print_colored("📭 No backups found", "yellow")
            return
        
        # Sort by modification time (newest first)
        backup_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
        
        print_colored(f"🗄️ Found {len(backup_files)} backups:", "blue")
        print()
        
        # Table header
        print(f"{'Name':<35} {'Type':<12} {'Date':<20} {'Size':<10}")
        print("-" * 77)
        
        for backup_file in backup_files:
            try:
                # Parse backup name
                name_parts = backup_file.stem.split('_')
                backup_type = name_parts[2] if len(name_parts) > 2 else "unknown"
                timestamp_str = '_'.join(name_parts[-2:]) if len(name_parts) >= 4 else "unknown"
                
                # Format timestamp
                try:
                    timestamp = datetime.strptime(timestamp_str, "%Y%m%d_%H%M%S")
                    date_str = timestamp.strftime("%Y-%m-%d %H:%M:%S")
                except:
                    date_str = timestamp_str
                
                # Get file size
                size_str = format_size(backup_file.stat().st_size)
                
                print(f"{backup_file.stem:<35} {backup_type:<12} {date_str:<20} {size_str:<10}")
                
            except Exception as e:
                print(f"{backup_file.name:<35} {'error':<12} {'unknown':<20} {'unknown':<10}")
        
        print()
        
    except Exception as e:
        print_colored(f"❌ Error listing backups: {e}", "red")


def show_backup_status() -> None:
    """Show backup system status and statistics."""
    try:
        scheduler = BackupScheduler()
        status = scheduler.get_backup_status()
        
        if "error" in status:
            print_colored(f"❌ Error getting status: {status['error']}", "red")
            return
        
        print_colored("🗄️ Backup System Status", "bold")
        print()
        
        # Basic info
        print(f"📁 Backup Directory: {status['backup_directory']}")
        print(f"📊 Total Backups: {status['total_backups']}")
        print(f"💾 Total Size: {format_size(status['total_size_mb'] * 1024 * 1024)}")
        print(f"✅ Enabled: {'Yes' if status['enabled'] else 'No'}")
        
        if status['last_backup']:
            print(f"🕐 Last Backup: {format_timestamp(status['last_backup'])}")
        else:
            print("🕐 Last Backup: Never")
        
        print()
        
        # Recent backups
        if status['recent_backups']:
            print_colored("📋 Recent Backups:", "blue")
            for backup in status['recent_backups']:
                date_str = format_timestamp(backup['timestamp'])
                size_str = format_size(backup['size_mb'] * 1024 * 1024)
                print(f"  • {backup['type']} - {date_str} - {size_str} ({backup['compression']})")
        else:
            print_colored("📭 No recent backups", "yellow")
        
        print()
        
        # Configuration
        config = scheduler.config
        print_colored("⚙️ Configuration:", "blue")
        print(f"  • Interval: Every {config.backup_interval_hours} hours")
        print(f"  • Daily: {config.daily_backup_time}")
        print(f"  • Weekly: {config.weekly_backup_day}")
        print(f"  • Retention: {config.retention_days} days")
        print(f"  • Include Logs: {'Yes' if config.include_logs else 'No'}")
        print(f"  • Include Cache: {'Yes' if config.include_cache else 'No'}")
        print(f"  • Compression: {'Yes' if config.compress_backups else 'No'}")
        
    except Exception as e:
        print_colored(f"❌ Error getting backup status: {e}", "red")


def restore_backup(backup_name: str) -> bool:
    """Restore from a backup."""
    print_colored(f"🔄 Restoring from backup: {backup_name}", "blue")
    
    try:
        scheduler = BackupScheduler()
        
        # Check if backup exists
        backup_file = scheduler.backup_dir / f"{backup_name}.tar.gz"
        if not backup_file.exists():
            print_colored(f"❌ Backup not found: {backup_name}", "red")
            print("Available backups:")
            list_backups()
            return False
        
        # Confirm restoration
        print_colored("⚠️ WARNING: This will overwrite current files!", "yellow")
        confirm = input("Are you sure you want to restore? (yes/no): ").lower().strip()
        
        if confirm not in ['yes', 'y']:
            print_colored("ℹ️ Restoration cancelled", "blue")
            return False
        
        # Perform restoration
        success = scheduler.restore_backup(backup_name)
        
        if success:
            print_colored("✅ Backup restored successfully!", "green")
            print_colored("🔄 You may need to restart the bot", "yellow")
            return True
        else:
            print_colored("❌ Backup restoration failed", "red")
            return False
            
    except Exception as e:
        print_colored(f"❌ Error restoring backup: {e}", "red")
        return False


def cleanup_backups() -> None:
    """Clean up old backups based on retention policy."""
    print_colored("🧹 Cleaning up old backups...", "blue")
    
    try:
        scheduler = BackupScheduler()
        
        # Count backups before cleanup
        backup_files_before = list(scheduler.backup_dir.glob("newsbot_backup_*.tar.gz"))
        
        # Perform cleanup
        scheduler.cleanup_old_backups()
        
        # Count backups after cleanup
        backup_files_after = list(scheduler.backup_dir.glob("newsbot_backup_*.tar.gz"))
        
        removed_count = len(backup_files_before) - len(backup_files_after)
        
        if removed_count > 0:
            print_colored(f"✅ Cleaned up {removed_count} old backups", "green")
        else:
            print_colored("ℹ️ No old backups to clean up", "blue")
        
        print(f"📊 Backups remaining: {len(backup_files_after)}")
        
    except Exception as e:
        print_colored(f"❌ Error during cleanup: {e}", "red")


def show_config() -> None:
    """Show current backup configuration."""
    try:
        scheduler = BackupScheduler()
        config = scheduler.config
        
        print_colored("⚙️ Backup Configuration", "bold")
        print()
        
        print(f"Enabled: {'Yes' if config.enabled else 'No'}")
        print(f"Backup Interval: Every {config.backup_interval_hours} hours")
        print(f"Daily Backup Time: {config.daily_backup_time}")
        print(f"Weekly Backup Day: {config.weekly_backup_day}")
        print(f"Retention Period: {config.retention_days} days")
        print(f"Backup Directory: {config.backup_directory}")
        print(f"Include Logs: {'Yes' if config.include_logs else 'No'}")
        print(f"Include Cache: {'Yes' if config.include_cache else 'No'}")
        print(f"Compress Backups: {'Yes' if config.compress_backups else 'No'}")
        print(f"Max Backup Size: {config.max_backup_size_mb} MB")
        print()
        
        # Show backup paths
        paths = scheduler.get_backup_paths()
        print_colored("📁 Paths to Backup:", "blue")
        for name, path in paths.items():
            status = "✅" if path.exists() else "❌"
            print(f"  {status} {name}: {path}")
        
    except Exception as e:
        print_colored(f"❌ Error getting configuration: {e}", "red")


def main():
    """Main entry point for the backup manager."""
    parser = argparse.ArgumentParser(
        description="NewsBot Backup Manager",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    %(prog)s create                 # Create manual backup
    %(prog)s create pre_deployment  # Create pre-deployment backup
    %(prog)s list                   # List all backups
    %(prog)s status                 # Show backup system status
    %(prog)s restore backup_name    # Restore from backup
    %(prog)s cleanup                # Clean old backups
    %(prog)s config                 # Show configuration
        """
    )
    
    parser.add_argument(
        'command',
        choices=['create', 'list', 'status', 'restore', 'cleanup', 'config'],
        help='Command to execute'
    )
    
    parser.add_argument(
        'arg',
        nargs='?',
        help='Additional argument (backup type for create, backup name for restore)'
    )
    
    args = parser.parse_args()
    
    try:
        if args.command == 'create':
            backup_type = args.arg or "manual"
            success = create_backup(backup_type)
            sys.exit(0 if success else 1)
            
        elif args.command == 'list':
            list_backups()
            
        elif args.command == 'status':
            show_backup_status()
            
        elif args.command == 'restore':
            if not args.arg:
                print_colored("❌ Backup name required for restore command", "red")
                sys.exit(1)
            success = restore_backup(args.arg)
            sys.exit(0 if success else 1)
            
        elif args.command == 'cleanup':
            cleanup_backups()
            
        elif args.command == 'config':
            show_config()
            
    except KeyboardInterrupt:
        print_colored("\n⚠️ Operation cancelled by user", "yellow")
        sys.exit(1)
    except Exception as e:
        print_colored(f"❌ Unexpected error: {e}", "red")
        sys.exit(1)


if __name__ == "__main__":
    main() 