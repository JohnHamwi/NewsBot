#!/usr/bin/env python
"""
Test script for TelegramClient extension

This script tests the get_posts method added to the TelegramClient.
"""

import os
import sys
import asyncio
from pathlib import Path
import logging
from dotenv import load_dotenv
from telethon import TelegramClient

# Add the project root to the path so we can import modules
sys.path.append(str(Path(__file__).parent.parent))

from src.core.telegram_utils import extend_telegram_client

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s | [%(levelname)s] | %(message)s',
    datefmt='%Y-%m-%d | %I:%M:%S %p'
)
logger = logging.getLogger(__name__)

async def main():
    # Load environment variables
    load_dotenv()
    
    # Get Telegram API credentials
    api_id = os.getenv("TELEGRAM_API_ID")
    api_hash = os.getenv("TELEGRAM_API_HASH")
    
    if not api_id or not api_hash:
        logger.error("Telegram API credentials are missing. Check your .env file.")
        return
    
    logger.info(f"Starting Telegram client with API ID: {api_id}")
    
    # Create and start Telegram client
    client = TelegramClient("test_session", api_id, api_hash)
    await client.start()
    
    try:
        # Extend the client with our utility methods
        await extend_telegram_client(client)
        
        # Test channels (these should be configured in your bot)
        test_channels = [
            "moraselalthawrah",
            "shaamnetwork",
            "alktroone",
            "damascusv011",
            "almharar",
            "alarabytvsy",
            "bnn_syr"
        ]
        
        # Test get_posts for each channel
        for channel in test_channels:
            try:
                logger.info(f"Testing get_posts for channel: {channel}")
                
                # Get channel entity
                entity = await client.get_entity(channel)
                channel_title = getattr(entity, 'title', channel)
                logger.info(f"Found channel: {channel_title}")
                
                # Get posts - note that we're now calling a partial function 
                # (our get_posts wrapper), so we don't need to pass 'client' again
                posts = await client.get_posts(channel, limit=1)
                
                if posts:
                    post = posts[0]
                    logger.info(f"Successfully retrieved post from {channel_title} (ID: {post.id})")
                    
                    # Print post message (if available)
                    if hasattr(post, 'message') and post.message:
                        message_preview = post.message[:100] + "..." if len(post.message) > 100 else post.message
                        logger.info(f"Post message: {message_preview}")
                    else:
                        logger.info("Post has no text content")
                    
                    # Check for media
                    if hasattr(post, 'media') and post.media:
                        logger.info(f"Post has media: {type(post.media).__name__}")
                    else:
                        logger.info("Post has no media")
                else:
                    logger.warning(f"No posts found in channel: {channel}")
                
                # Sleep briefly to avoid rate limiting
                await asyncio.sleep(1)
                
            except Exception as e:
                logger.error(f"Error testing channel {channel}: {str(e)}")
        
    finally:
        # Disconnect the client
        await client.disconnect()
        logger.info("Telegram client disconnected")

if __name__ == "__main__":
    asyncio.run(main()) 