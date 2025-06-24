#!/usr/bin/env python3

# =============================================================================
# NewsBot Main Entry Point Module
# =============================================================================
# This module contains the main entry point and initialization logic for the
# Syrian NewsBot. It handles bot startup, configuration loading, signal
# handling, and graceful shutdown procedures.
#
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
import os
import signal
import sys
from pathlib import Path

# =============================================================================
# Path Configuration
# =============================================================================
# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

# =============================================================================
# Local Application Imports
# =============================================================================
from src.bot.newsbot import NewsBot
from src.core.unified_config import unified_config as config
from src.utils.base_logger import base_logger as logger

# =============================================================================
# Global Variables
# =============================================================================
# Global bot instance for signal handling
bot_instance = None


# =============================================================================
# Signal Handler Configuration
# =============================================================================
def setup_signal_handlers():
    """Set up signal handlers for graceful shutdown."""
    shutdown_initiated = False

    def signal_handler(signum, frame):
        """Handle shutdown signals gracefully."""
        nonlocal shutdown_initiated

        if shutdown_initiated:
            logger.warning("🛑 Shutdown already in progress, forcing exit...")
            os._exit(1)

        shutdown_initiated = True
        signal_name = signal.Signals(signum).name
        logger.info(f"🛑 Received {signal_name} signal, initiating graceful shutdown...")

        if bot_instance:
            # Create a new event loop if needed
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    # If loop is running, schedule shutdown
                    loop.create_task(graceful_shutdown())
                else:
                    # If loop is not running, run shutdown directly
                    asyncio.run(graceful_shutdown())
            except RuntimeError:
                # Create new loop for shutdown
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                loop.run_until_complete(graceful_shutdown())
        else:
            sys.exit(0)

    async def graceful_shutdown():
        """Perform graceful shutdown with timeout."""
        try:
            # Give bot time to shutdown properly
            await asyncio.wait_for(bot_instance.close(), timeout=10.0)
        except asyncio.TimeoutError:
            logger.warning("🛑 Shutdown timeout reached, forcing exit...")
        except Exception as e:
            logger.error(f"🛑 Error during shutdown: {e}")
        finally:
            # Force exit after cleanup attempt
            os._exit(0)

    # Handle common termination signals
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)   # Ctrl+C

    logger.info("✅ Signal handlers configured for graceful shutdown")


# =============================================================================
# Main Application Function
# =============================================================================
async def main() -> None:
    """
    Main entry point for the Syrian NewsBot.

    This function initializes the bot, loads configuration,
    and starts the Discord client with proper error handling.
    """
    global bot_instance

    try:
        # Set up signal handlers
        setup_signal_handlers()

        # Configuration is automatically validated on import
        # Check if we can get required values
        discord_token = config.get("discord.token")
        if not discord_token:
            logger.error("❌ Discord token not found in configuration")
            sys.exit(1)



        # Initialize and start the bot
        logger.info("🚀 Initializing Syrian NewsBot...")
        bot_instance = NewsBot()

        await bot_instance.start(discord_token)

    except KeyboardInterrupt:
        logger.info("🛑 Bot stopped by user (Ctrl+C)")
    except Exception as e:
        logger.error(f"❌ Fatal error in main: {e}")
        raise
    finally:
        # Ensure cleanup happens
        if bot_instance:
            try:
                await bot_instance.close()
            except Exception as e:
                logger.error(f"❌ Error during final cleanup: {e}")


# =============================================================================
# Module Entry Point
# =============================================================================
if __name__ == "__main__":
    """Entry point when running the module directly."""
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("🛑 Bot interrupted")
    except Exception as e:
        logger.error(f"❌ Unhandled exception: {e}")
        sys.exit(1)
