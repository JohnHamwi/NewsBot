#!/usr/bin/env python3

# =============================================================================
# NewsBot Main Entry Point
# =============================================================================
# Modern Discord bot for aggregating Syrian news from Telegram channels
# and posting them to Discord with AI-powered translation and formatting.
#
# Usage:
#     python run.py
#
# Requirements:
#     - Python 3.11+
#     - Discord.py 2.5+
#     - Valid Discord bot token
#     - Telegram API credentials (optional)
#
# Author: Trippixn (Discord)
# Version: 4.5.0
# Last updated: 2025-01-16

# =============================================================================
# Future Imports
# =============================================================================
from __future__ import annotations

# =============================================================================
# Standard Library Imports
# =============================================================================
import asyncio
import logging
import sys
import os
import signal
import psutil
from pathlib import Path

# =============================================================================
# Path Configuration
# =============================================================================
# Add src directory to Python path
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

# =============================================================================
# Local Application Imports
# =============================================================================
try:
    from bot.main import main
except ImportError as e:
    print(f"❌ Failed to import main module: {e}")
    print("Make sure all dependencies are installed: pip install -r requirements.txt")
    sys.exit(1)

from src.utils.logger import get_logger

logger = get_logger("NewsBot")


def check_existing_instances():
    """Check for existing bot instances and kill them."""
    current_pid = os.getpid()
    current_script = os.path.abspath(__file__)
    killed_processes = []
    
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            # Skip current process
            if proc.info['pid'] == current_pid:
                continue
                
            # Check if it's a Python process running this script
            if (proc.info['name'] and 'python' in proc.info['name'].lower() and 
                proc.info['cmdline'] and len(proc.info['cmdline']) > 1):
                
                # Check if it's running run.py
                for arg in proc.info['cmdline']:
                    if 'run.py' in arg or current_script in arg:
                        logger.info(f"🔄 Found existing bot instance (PID: {proc.info['pid']}), terminating...")
                        proc.terminate()
                        killed_processes.append(proc.info['pid'])
                        break
                        
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            continue
    
    # Wait for processes to terminate
    if killed_processes:
        import time
        time.sleep(2)
        logger.info(f"✅ Terminated {len(killed_processes)} existing bot instance(s)")
    
    return len(killed_processes)


async def main():
    """Main application entry point."""
    try:
        # Check and kill existing instances
        killed_count = check_existing_instances()
        
        if killed_count > 0:
            logger.info("🔄 Starting fresh bot instance after cleanup...")
        else:
            logger.info("🚀 Starting NewsBot...")
            
        # Import and start the bot
        from src.bot.main import main as bot_main
        await bot_main()
        
    except KeyboardInterrupt:
        logger.info("🛑 Received keyboard interrupt, shutting down...")
    except Exception as e:
        logger.error(f"❌ Fatal error in main: {e}")
        raise


# =============================================================================
# Main Entry Point
# =============================================================================
if __name__ == "__main__":
    """
    Main entry point for the Syrian NewsBot.
    
    This script initializes logging, handles graceful shutdown,
    and starts the bot with proper error handling.
    """
    # Set up signal handlers for graceful shutdown
    def signal_handler(signum, frame):
        logger.info(f"🛑 Received signal {signum}, initiating graceful shutdown...")
        # The actual shutdown will be handled by the bot's signal handlers
        
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)
    
    # Run the bot
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("🛑 Bot stopped by user")
    except Exception as e:
        logger.error(f"❌ Bot crashed: {e}")
        sys.exit(1) 