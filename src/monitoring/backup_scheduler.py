#!/usr/bin/env python3
"""
=============================================================================
NewsBot Automated Backup Scheduler
=============================================================================
Handles automated backup scheduling for bot data, configuration, and logs.
Supports multiple backup strategies and retention policies.
"""

import asyncio
import os
import shutil
import tarfile
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
import schedule
import time
from threading import Thread

# Configure logging
logger = logging.getLogger('NewsBot.BackupScheduler')


@dataclass
class BackupConfig:
    """Configuration for backup operations."""
    enabled: bool = True
    backup_interval_hours: int = 6  # Backup every 6 hours
    daily_backup_time: str = "02:00"  # Daily backup at 2 AM
    weekly_backup_day: str = "sunday"  # Weekly backup on Sunday
    retention_days: int = 30  # Keep backups for 30 days
    backup_directory: str = "backups"
    include_logs: bool = True
    include_cache: bool = False  # Cache can be large, exclude by default
    compress_backups: bool = True
    max_backup_size_mb: int = 500  # Alert if backup exceeds this size


@dataclass
class BackupMetadata:
    """Metadata for backup operations."""
    timestamp: str
    backup_type: str  # "scheduled", "manual", "pre_deployment"
    files_included: List[str]
    total_size_bytes: int
    compression_ratio: float
    success: bool
    error_message: Optional[str] = None


class BackupScheduler:
    """
    Automated backup scheduler for NewsBot.
    
    Handles multiple backup types:
    - Hourly incremental backups
    - Daily full backups
    - Weekly archive backups
    - Pre-deployment backups
    """
    
    def __init__(self, config: Optional[BackupConfig] = None):
        """Initialize the backup scheduler."""
        self.config = config or BackupConfig()
        self.backup_dir = Path(self.config.backup_directory)
        self.backup_dir.mkdir(exist_ok=True)
        
        self.is_running = False
        self.scheduler_thread: Optional[Thread] = None
        
        # Track backup history
        self.backup_history: List[BackupMetadata] = []
        self.load_backup_history()
        
        logger.info(f"🗄️ Backup scheduler initialized - backups every {self.config.backup_interval_hours}h")
    
    def load_backup_history(self) -> None:
        """Load backup history from metadata file."""
        history_file = self.backup_dir / "backup_history.json"
        if history_file.exists():
            try:
                with open(history_file, 'r') as f:
                    data = json.load(f)
                    self.backup_history = [BackupMetadata(**item) for item in data]
                logger.debug(f"📚 Loaded {len(self.backup_history)} backup records")
            except Exception as e:
                logger.error(f"❌ Failed to load backup history: {e}")
                self.backup_history = []
    
    def save_backup_history(self) -> None:
        """Save backup history to metadata file."""
        history_file = self.backup_dir / "backup_history.json"
        try:
            with open(history_file, 'w') as f:
                json.dump([asdict(backup) for backup in self.backup_history], f, indent=2)
        except Exception as e:
            logger.error(f"❌ Failed to save backup history: {e}")
    
    def get_backup_paths(self) -> Dict[str, Path]:
        """Get paths to include in backup."""
        base_path = Path.cwd()
        
        paths = {
            "config": base_path / "config",
            "data": base_path / "data", 
            "src": base_path / "src",
            "requirements": base_path / "requirements.txt",
            "test_requirements": base_path / "test_requirements.txt",
            "pytest_ini": base_path / "pytest.ini",
            "run_py": base_path / "run.py",
        }
        
        if self.config.include_logs:
            paths["logs"] = base_path / "logs"
        
        if self.config.include_cache:
            paths["cache"] = base_path / "data" / "cache"
        
        # Filter to only existing paths
        return {name: path for name, path in paths.items() if path.exists()}
    
    def create_backup_name(self, backup_type: str = "scheduled") -> str:
        """Generate a unique backup name."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"newsbot_backup_{backup_type}_{timestamp}"
    
    def calculate_directory_size(self, path: Path) -> int:
        """Calculate total size of directory in bytes."""
        total_size = 0
        try:
            for file_path in path.rglob('*'):
                if file_path.is_file():
                    total_size += file_path.stat().st_size
        except Exception as e:
            logger.warning(f"⚠️ Error calculating size for {path}: {e}")
        return total_size
    
    def create_backup(self, backup_type: str = "scheduled") -> BackupMetadata:
        """
        Create a backup of the bot's data and configuration.
        
        Args:
            backup_type: Type of backup ("scheduled", "manual", "pre_deployment")
            
        Returns:
            BackupMetadata: Information about the created backup
        """
        backup_name = self.create_backup_name(backup_type)
        backup_path = self.backup_dir / f"{backup_name}.tar.gz"
        
        logger.info(f"🗄️ Creating {backup_type} backup: {backup_name}")
        
        try:
            paths_to_backup = self.get_backup_paths()
            files_included = list(paths_to_backup.keys())
            
            # Calculate total size before compression
            total_size = 0
            for path in paths_to_backup.values():
                if path.is_file():
                    total_size += path.stat().st_size
                elif path.is_dir():
                    total_size += self.calculate_directory_size(path)
            
            # Create compressed backup
            with tarfile.open(backup_path, "w:gz" if self.config.compress_backups else "w") as tar:
                for name, path in paths_to_backup.items():
                    try:
                        tar.add(path, arcname=name)
                        logger.debug(f"✅ Added {name} to backup")
                    except Exception as e:
                        logger.warning(f"⚠️ Failed to add {name} to backup: {e}")
            
            # Calculate compression ratio
            backup_size = backup_path.stat().st_size
            compression_ratio = backup_size / total_size if total_size > 0 else 0
            
            # Check backup size warning
            backup_size_mb = backup_size / (1024 * 1024)
            if backup_size_mb > self.config.max_backup_size_mb:
                logger.warning(f"⚠️ Backup size ({backup_size_mb:.1f}MB) exceeds threshold ({self.config.max_backup_size_mb}MB)")
            
            metadata = BackupMetadata(
                timestamp=datetime.now().isoformat(),
                backup_type=backup_type,
                files_included=files_included,
                total_size_bytes=backup_size,
                compression_ratio=compression_ratio,
                success=True
            )
            
            logger.info(f"✅ Backup created successfully: {backup_path.name}")
            logger.info(f"📊 Size: {backup_size_mb:.1f}MB | Compression: {compression_ratio:.2f}x")
            
            return metadata
            
        except Exception as e:
            logger.error(f"❌ Backup creation failed: {e}")
            return BackupMetadata(
                timestamp=datetime.now().isoformat(),
                backup_type=backup_type,
                files_included=[],
                total_size_bytes=0,
                compression_ratio=0,
                success=False,
                error_message=str(e)
            )
    
    def cleanup_old_backups(self) -> None:
        """Remove backups older than the retention period."""
        try:
            cutoff_date = datetime.now() - timedelta(days=self.config.retention_days)
            removed_count = 0
            
            for backup_file in self.backup_dir.glob("newsbot_backup_*.tar.gz"):
                try:
                    # Extract timestamp from filename
                    timestamp_str = backup_file.stem.split('_')[-2] + '_' + backup_file.stem.split('_')[-1]
                    backup_date = datetime.strptime(timestamp_str, "%Y%m%d_%H%M%S")
                    
                    if backup_date < cutoff_date:
                        backup_file.unlink()
                        removed_count += 1
                        logger.debug(f"🗑️ Removed old backup: {backup_file.name}")
                        
                except Exception as e:
                    logger.warning(f"⚠️ Error processing backup file {backup_file}: {e}")
            
            if removed_count > 0:
                logger.info(f"🧹 Cleaned up {removed_count} old backups (older than {self.config.retention_days} days)")
            
            # Also clean up backup history
            cutoff_timestamp = cutoff_date.isoformat()
            original_count = len(self.backup_history)
            self.backup_history = [
                backup for backup in self.backup_history 
                if backup.timestamp > cutoff_timestamp
            ]
            
            if len(self.backup_history) < original_count:
                self.save_backup_history()
                logger.debug(f"📚 Cleaned up backup history: {original_count} -> {len(self.backup_history)} records")
                
        except Exception as e:
            logger.error(f"❌ Error during backup cleanup: {e}")
    
    def perform_scheduled_backup(self) -> None:
        """Perform a scheduled backup operation."""
        if not self.config.enabled:
            logger.debug("⏸️ Backup scheduler disabled, skipping backup")
            return
        
        try:
            # Create backup
            metadata = self.create_backup("scheduled")
            self.backup_history.append(metadata)
            
            # Cleanup old backups
            self.cleanup_old_backups()
            
            # Save updated history
            self.save_backup_history()
            
            if metadata.success:
                logger.info("✅ Scheduled backup completed successfully")
            else:
                logger.error(f"❌ Scheduled backup failed: {metadata.error_message}")
                
        except Exception as e:
            logger.error(f"❌ Error during scheduled backup: {e}")
    
    def create_pre_deployment_backup(self) -> bool:
        """
        Create a backup before deployment.
        
        Returns:
            bool: True if backup was successful
        """
        logger.info("🚀 Creating pre-deployment backup...")
        metadata = self.create_backup("pre_deployment")
        self.backup_history.append(metadata)
        self.save_backup_history()
        
        if metadata.success:
            logger.info("✅ Pre-deployment backup completed")
        else:
            logger.error(f"❌ Pre-deployment backup failed: {metadata.error_message}")
        
        return metadata.success
    
    def get_backup_status(self) -> Dict:
        """Get current backup status and statistics."""
        try:
            recent_backups = sorted(
                [b for b in self.backup_history if b.success],
                key=lambda x: x.timestamp,
                reverse=True
            )[:5]
            
            total_backup_size = sum(
                backup_file.stat().st_size 
                for backup_file in self.backup_dir.glob("newsbot_backup_*.tar.gz")
            )
            
            last_successful = recent_backups[0] if recent_backups else None
            
            status = {
                "enabled": self.config.enabled,
                "backup_directory": str(self.backup_dir),
                "total_backups": len(list(self.backup_dir.glob("newsbot_backup_*.tar.gz"))),
                "total_size_mb": total_backup_size / (1024 * 1024),
                "last_backup": last_successful.timestamp if last_successful else None,
                "next_cleanup": (datetime.now() + timedelta(days=self.config.retention_days)).isoformat(),
                "recent_backups": [
                    {
                        "timestamp": b.timestamp,
                        "type": b.backup_type,
                        "size_mb": b.total_size_bytes / (1024 * 1024),
                        "compression": f"{b.compression_ratio:.2f}x"
                    }
                    for b in recent_backups
                ]
            }
            
            return status
            
        except Exception as e:
            logger.error(f"❌ Error getting backup status: {e}")
            return {"error": str(e)}
    
    def setup_schedule(self) -> None:
        """Set up the backup schedule."""
        # Clear any existing schedules
        schedule.clear()
        
        if not self.config.enabled:
            logger.info("⏸️ Backup scheduling disabled")
            return
        
        # Schedule periodic backups
        schedule.every(self.config.backup_interval_hours).hours.do(self.perform_scheduled_backup)
        
        # Schedule daily backup at specific time
        schedule.every().day.at(self.config.daily_backup_time).do(
            lambda: self.create_backup("daily")
        )
        
        # Schedule weekly backup
        getattr(schedule.every(), self.config.weekly_backup_day.lower()).at(self.config.daily_backup_time).do(
            lambda: self.create_backup("weekly")
        )
        
        logger.info(f"📅 Backup schedule configured:")
        logger.info(f"   • Every {self.config.backup_interval_hours} hours")
        logger.info(f"   • Daily at {self.config.daily_backup_time}")
        logger.info(f"   • Weekly on {self.config.weekly_backup_day} at {self.config.daily_backup_time}")
    
    def start_scheduler(self) -> None:
        """Start the backup scheduler in a background thread."""
        if self.is_running:
            logger.warning("⚠️ Backup scheduler already running")
            return
        
        self.setup_schedule()
        self.is_running = True
        
        def run_scheduler():
            logger.info("🗄️ Backup scheduler started")
            while self.is_running:
                try:
                    schedule.run_pending()
                    time.sleep(60)  # Check every minute
                except Exception as e:
                    logger.error(f"❌ Error in backup scheduler: {e}")
                    time.sleep(300)  # Wait 5 minutes on error
        
        self.scheduler_thread = Thread(target=run_scheduler, daemon=True)
        self.scheduler_thread.start()
        
        logger.info("✅ Backup scheduler started successfully")
    
    def stop_scheduler(self) -> None:
        """Stop the backup scheduler."""
        if not self.is_running:
            return
        
        self.is_running = False
        schedule.clear()
        
        if self.scheduler_thread and self.scheduler_thread.is_alive():
            self.scheduler_thread.join(timeout=5)
        
        logger.info("🛑 Backup scheduler stopped")
    
    def restore_backup(self, backup_name: str, restore_path: Optional[Path] = None) -> bool:
        """
        Restore from a backup file.
        
        Args:
            backup_name: Name of the backup file (without extension)
            restore_path: Path to restore to (defaults to current directory)
            
        Returns:
            bool: True if restore was successful
        """
        backup_file = self.backup_dir / f"{backup_name}.tar.gz"
        
        if not backup_file.exists():
            logger.error(f"❌ Backup file not found: {backup_file}")
            return False
        
        restore_path = restore_path or Path.cwd()
        
        try:
            logger.info(f"🔄 Restoring backup: {backup_name}")
            
            with tarfile.open(backup_file, "r:gz") as tar:
                tar.extractall(restore_path)
            
            logger.info(f"✅ Backup restored successfully to {restore_path}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Backup restore failed: {e}")
            return False


# Integration with bot
async def integrate_backup_scheduler(bot) -> BackupScheduler:
    """
    Integrate backup scheduler with the bot instance.
    
    Args:
        bot: NewsBot instance
        
    Returns:
        BackupScheduler: Configured scheduler instance
    """
    try:
        # Load configuration from bot config if available
        backup_config = BackupConfig()
        
        if hasattr(bot, 'automation_config') and bot.automation_config:
            backup_settings = bot.automation_config.get('backup', {})
            
            backup_config.enabled = backup_settings.get('enabled', True)
            backup_config.backup_interval_hours = backup_settings.get('interval_hours', 6)
            backup_config.retention_days = backup_settings.get('retention_days', 30)
            backup_config.include_logs = backup_settings.get('include_logs', True)
            backup_config.include_cache = backup_settings.get('include_cache', False)
        
        scheduler = BackupScheduler(backup_config)
        
        # Add backup scheduler to bot
        bot.backup_scheduler = scheduler
        
        # Start the scheduler
        scheduler.start_scheduler()
        
        logger.info("🗄️ Backup scheduler integrated with bot")
        return scheduler
        
    except Exception as e:
        logger.error(f"❌ Failed to integrate backup scheduler: {e}")
        # Return a disabled scheduler as fallback
        return BackupScheduler(BackupConfig(enabled=False))


if __name__ == "__main__":
    # Example usage
    scheduler = BackupScheduler()
    
    # Create a manual backup
    metadata = scheduler.create_backup("manual")
    print(f"Backup created: {metadata.success}")
    
    # Get status
    status = scheduler.get_backup_status()
    print(f"Backup status: {status}") 