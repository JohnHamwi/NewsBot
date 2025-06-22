#!/usr/bin/env python3
"""
🔒 PROPRIETARY SOFTWARE - NEWSBOT PROJECT

This is proprietary software developed for private use only.
Unauthorized copying, distribution, or use is strictly prohibited.

Copyright (c) 2025 NewsBot Project. All rights reserved.

Syrian Discord News Aggregation Bot - CONFIDENTIAL
For authorized use on designated Discord servers only.

Modern Discord bot for aggregating Syrian news from Telegram channels
and posting them to Discord with AI-powered translation and formatting.

Usage:
    python run.py

Requirements:
    - Python 3.11+
    - Discord.py 2.5+
    - Valid Discord bot token
    - Telegram API credentials (optional)

Author: Trippixn (Discord)
Version: 4.5.0
"""

from __future__ import annotations

import asyncio
import logging
import sys
import os
from pathlib import Path

# Add src directory to Python path
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

try:
    from bot.main import main
except ImportError as e:
    print(f"❌ Failed to import main module: {e}")
    print("Make sure all dependencies are installed: pip install -r requirements.txt")
    sys.exit(1)


if __name__ == "__main__":
    """
    Main entry point for the Syrian NewsBot.
    
    This script initializes logging, handles graceful shutdown,
    and starts the bot with proper error handling.
    """
    try:
        # Run the bot
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n🛑 Bot stopped by user")
    except Exception as e:
        print(f"❌ Fatal error: {e}")
        logging.exception("Fatal error occurred")
        sys.exit(1) 