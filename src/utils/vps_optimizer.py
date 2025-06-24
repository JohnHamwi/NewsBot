"""
VPS Optimization Utilities
Reduces memory usage and optimizes performance for VPS deployment
"""
# =============================================================================
# NewsBot Vps Optimizer Utility Module
# =============================================================================
# Part of the NewsBot system for aggregating Syrian news from Telegram channels
# and posting them to Discord with AI-powered translation and formatting.
#
# Last updated: 2025-01-16

import gc
import asyncio
import logging
import psutil
import os
from typing import Optional

logger = logging.getLogger(__name__)


class VPSOptimizer:
    """Optimizes bot performance for VPS deployment."""
    
    def __init__(self, bot=None):
        self.bot = bot
        self.memory_cleanup_interval = 3600  # 1 hour
        self.cache_cleanup_interval = 7200   # 2 hours
        self.process = psutil.Process()
        
    async def start_optimization_tasks(self):
        """Start background optimization tasks."""
        logger.info("🔧 Starting VPS optimization tasks")
        
        # Start memory cleanup task
        asyncio.create_task(self._memory_cleanup_task())
        
        # Start cache cleanup task  
        asyncio.create_task(self._cache_cleanup_task())
        
    async def _memory_cleanup_task(self):
        """Periodic memory cleanup to prevent memory leaks."""
        while True:
            try:
                await asyncio.sleep(self.memory_cleanup_interval)
                await self.cleanup_memory()
            except Exception as e:
                logger.error(f"❌ Memory cleanup task error: {e}")
                await asyncio.sleep(300)  # Wait 5 minutes on error
                
    async def _cache_cleanup_task(self):
        """Periodic cache cleanup to free disk space."""
        while True:
            try:
                await asyncio.sleep(self.cache_cleanup_interval)
                await self.cleanup_caches()
            except Exception as e:
                logger.error(f"❌ Cache cleanup task error: {e}")
                await asyncio.sleep(300)  # Wait 5 minutes on error
                
    async def cleanup_memory(self):
        """Force garbage collection and memory cleanup."""
        try:
            # Get memory usage before cleanup
            memory_before = self.process.memory_info().rss / 1024 / 1024  # MB
            
            # Force garbage collection
            collected = gc.collect()
            
            # Get memory usage after cleanup
            memory_after = self.process.memory_info().rss / 1024 / 1024  # MB
            memory_freed = memory_before - memory_after
            
            if memory_freed > 1:  # Only log if we freed more than 1MB
                logger.info(f"🧹 Memory cleanup: freed {memory_freed:.1f}MB (collected {collected} objects)")
            else:
                logger.debug(f"🧹 Memory cleanup: {memory_after:.1f}MB used, {collected} objects collected")
                
        except Exception as e:
            logger.error(f"❌ Memory cleanup failed: {e}")
            
    async def cleanup_caches(self):
        """Clean up temporary files and caches."""
        try:
            cleaned_files = 0
            freed_space = 0
            
            # Clean up temporary media files older than 24 hours
            temp_dirs = ['data/cache']
            
            for temp_dir in temp_dirs:
                if os.path.exists(temp_dir):
                    for root, dirs, files in os.walk(temp_dir):
                        for file in files:
                            file_path = os.path.join(root, file)
                            try:
                                # Check if file is older than 24 hours
                                if os.path.getmtime(file_path) < (asyncio.get_event_loop().time() - 86400):
                                    # Skip important files
                                    if file.endswith(('.log', '.json', '.yaml')):
                                        continue
                                        
                                    file_size = os.path.getsize(file_path)
                                    os.remove(file_path)
                                    cleaned_files += 1
                                    freed_space += file_size
                                    
                            except (OSError, PermissionError):
                                continue  # Skip files we can't access
                                
            if cleaned_files > 0:
                freed_mb = freed_space / 1024 / 1024
                logger.info(f"🧹 Cache cleanup: removed {cleaned_files} files, freed {freed_mb:.1f}MB")
            else:
                logger.debug("🧹 Cache cleanup: no old files to remove")
                
        except Exception as e:
            logger.error(f"❌ Cache cleanup failed: {e}")
            
    async def optimize_for_vps(self):
        """Apply VPS-specific optimizations."""
        try:
            # Optimize garbage collection
            gc.set_threshold(700, 10, 10)  # More aggressive GC
            logger.info("🔧 Optimized garbage collection thresholds for VPS")
                          
        except Exception as e:
            logger.error(f"❌ VPS optimization failed: {e}")


# Global optimizer instance
vps_optimizer: Optional[VPSOptimizer] = None


def get_vps_optimizer(bot=None) -> VPSOptimizer:
    """Get or create the global VPS optimizer instance."""
    global vps_optimizer
    if vps_optimizer is None:
        vps_optimizer = VPSOptimizer(bot)
    return vps_optimizer


async def start_vps_optimizations(bot):
    """Start VPS optimization tasks."""
    optimizer = get_vps_optimizer(bot)
    await optimizer.optimize_for_vps()
    await optimizer.start_optimization_tasks()
