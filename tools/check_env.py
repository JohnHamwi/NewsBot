#!/usr/bin/env python3
"""
Simple script to check if environment variables are loading correctly.
"""

import os
from dotenv import load_dotenv
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger("env_check")

def main():
    """Check if environment variables are loaded correctly."""
    logger.info("Loading environment variables...")
    load_dotenv()
    
    # Check for Discord token
    discord_token = os.getenv("DISCORD_TOKEN")
    if discord_token and discord_token != "your_discord_token_here":
        logger.info("✅ DISCORD_TOKEN is set")
    else:
        logger.error("❌ DISCORD_TOKEN is missing or has placeholder value")
    
    # Check for Telegram API credentials
    telegram_api_id = os.getenv("TELEGRAM_API_ID")
    if telegram_api_id and telegram_api_id != "your_telegram_api_id_here":
        logger.info("✅ TELEGRAM_API_ID is set")
    else:
        logger.error("❌ TELEGRAM_API_ID is missing or has placeholder value")
    
    telegram_api_hash = os.getenv("TELEGRAM_API_HASH")
    if telegram_api_hash and telegram_api_hash != "your_telegram_api_hash_here":
        logger.info("✅ TELEGRAM_API_HASH is set")
    else:
        logger.error("❌ TELEGRAM_API_HASH is missing or has placeholder value")
    
    # Check for admin user ID
    admin_user_id = os.getenv("ADMIN_USER_ID")
    if admin_user_id and admin_user_id != "your_discord_user_id_here":
        logger.info("✅ ADMIN_USER_ID is set")
    else:
        logger.error("❌ ADMIN_USER_ID is missing or has placeholder value")

if __name__ == "__main__":
    main() 