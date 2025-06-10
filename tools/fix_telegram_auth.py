#!/usr/bin/env python3
"""
Telegram Authentication Fix Script

This script helps fix authentication issues with the Telegram client
by providing an interactive login flow. It will:

1. Connect to Telegram using the API credentials from .env
2. Request a phone number from the user
3. Send a verification code to that phone
4. Ask the user to input the verification code
5. Complete the authentication process
6. Create a valid session file that can be used by the bot

Usage:
python fix_telegram_auth.py

After running this script, the bot should be able to access Telegram
channels properly without the "key not registered" error.
"""

import os
import asyncio
from dotenv import load_dotenv
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s',
    datefmt='%Y-%m-%d | %I:%M:%S %p'
)
logger = logging.getLogger("TelegramAuth")

# Load environment variables
load_dotenv()

async def fix_telegram_auth():
    """Run the Telegram authentication fix process"""
    try:
        from telethon import TelegramClient
        from telethon.errors import SessionPasswordNeededError
        
        # Get API credentials from environment variables
        api_id = os.getenv("TELEGRAM_API_ID")
        api_hash = os.getenv("TELEGRAM_API_HASH")
        
        if not api_id or not api_hash:
            logger.error("❌ Telegram API ID or Hash is missing in environment variables")
            return False
        
        logger.info("Starting Telegram authentication process...")
        
        # Create client with the same session name as used in the bot
        client = TelegramClient("newsbot_session", api_id, api_hash)
        
        # Connect to Telegram
        await client.connect()
        
        # Check if already authorized
        if await client.is_user_authorized():
            logger.info("✅ Already authorized! Session file is valid.")
            logger.info("✅ The bot should now be able to access Telegram channels.")
            await client.disconnect()
            return True
        
        # Ask for phone number
        phone = input("Enter your phone number (international format with +): ")
        
        # Send code request
        logger.info(f"Sending code request to {phone}...")
        await client.send_code_request(phone)
        
        # Ask for the code
        code = input("Enter the verification code you received: ")
        
        try:
            # Sign in with code
            await client.sign_in(phone, code)
            logger.info("✅ Successfully signed in!")
        except SessionPasswordNeededError:
            # 2FA is enabled
            password = input("Two-factor authentication is enabled. Enter your password: ")
            await client.sign_in(password=password)
            logger.info("✅ Successfully signed in with 2FA!")
        
        # Test if the authentication worked
        me = await client.get_me()
        logger.info(f"✅ Authentication successful! Logged in as: {me.first_name}")
        
        # Try to access a channel from the auto-post config
        try:
            test_channel = "shaamnetwork"  # One of the channels from auto_post_channels_config
            logger.info(f"Testing access to channel: {test_channel}")
            
            entity = await client.get_entity(test_channel)
            logger.info(f"✅ Successfully accessed channel: {getattr(entity, 'title', test_channel)}")
            
            messages = await client.get_messages(entity, limit=1)
            if messages and len(messages) > 0:
                logger.info(f"✅ Successfully retrieved messages from channel")
            else:
                logger.warning("⚠️ No messages found in the channel")
        except Exception as e:
            logger.error(f"❌ Error accessing channel: {str(e)}")
        
        # Disconnect
        await client.disconnect()
        logger.info("✅ Authentication process complete!")
        logger.info("✅ The bot should now be able to access Telegram channels.")
        return True
        
    except ImportError:
        logger.error("❌ Telethon package not installed. Run: pip install telethon")
        return False
    except Exception as e:
        logger.error(f"❌ Authentication process failed: {str(e)}")
        return False

if __name__ == "__main__":
    try:
        asyncio.run(fix_telegram_auth())
    except KeyboardInterrupt:
        logger.info("Authentication process interrupted by user")
    except Exception as e:
        logger.error(f"Error in authentication process: {str(e)}") 