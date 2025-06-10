"""
FetchCog Diagnostic Tool

This script tests if the FetchCog is working properly by:
1. Checking OpenAI API connection
2. Testing Telegram API connection
3. Trying a simple fetch operation with a timeout

This helps diagnose issues when the bot gets stuck on '/start' or other fetch operations.
"""

import asyncio
import os
from dotenv import load_dotenv
import sys
import traceback
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s',
    datefmt='%Y-%m-%d | %I:%M:%S %p'
)
logger = logging.getLogger("FetchDiagnostic")

# Load environment variables
load_dotenv()

async def test_openai_connection():
    """Test if the OpenAI API is working correctly."""
    try:
        import openai
        client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        
        logger.info("Testing OpenAI API connection...")
        
        # Set a timeout for the API call
        response = await asyncio.wait_for(
            asyncio.to_thread(
                client.chat.completions.create,
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": "Say hello"}],
                max_tokens=10
            ),
            timeout=10.0
        )
        
        logger.info(f"✅ OpenAI API test successful: {response.choices[0].message.content}")
        return True
    except ImportError:
        logger.error("❌ OpenAI package not installed. Run: pip install openai")
        return False
    except openai.APIError as e:
        logger.error(f"❌ OpenAI API error: {str(e)}")
        return False
    except asyncio.TimeoutError:
        logger.error("❌ OpenAI API call timed out after 10 seconds")
        return False
    except Exception as e:
        logger.error(f"❌ OpenAI API test failed: {str(e)}")
        return False

async def test_telegram_connection():
    """Test if the Telegram API is working correctly."""
    try:
        from telethon import TelegramClient
        
        api_id = os.getenv("TELEGRAM_API_ID")
        api_hash = os.getenv("TELEGRAM_API_HASH")
        
        if not api_id or not api_hash:
            logger.error("❌ Telegram API ID or Hash is missing in environment variables")
            return False
        
        logger.info("Testing Telegram API connection...")
        
        # Create a temporary client
        client = TelegramClient("diagnostic_session", api_id, api_hash)
        
        # Set a timeout for connecting
        try:
            await asyncio.wait_for(client.connect(), timeout=15.0)
            is_connected = await client.is_user_authorized()
            
            if is_connected:
                logger.info("✅ Telegram API test successful - User is authorized")
            else:
                logger.warning("⚠️ Telegram API connected but user is not authorized")
                
            await client.disconnect()
            return True
        except asyncio.TimeoutError:
            logger.error("❌ Telegram API connection timed out after 15 seconds")
            try:
                await client.disconnect()
            except:
                pass
            return False
    except ImportError:
        logger.error("❌ Telethon package not installed. Run: pip install telethon")
        return False
    except Exception as e:
        logger.error(f"❌ Telegram API test failed: {str(e)}")
        return False

async def test_fetch_operation():
    """Test if the fetch operation works with a timeout."""
    try:
        from telethon import TelegramClient
        
        api_id = os.getenv("TELEGRAM_API_ID")
        api_hash = os.getenv("TELEGRAM_API_HASH")
        
        if not api_id or not api_hash:
            logger.error("❌ Telegram API ID or Hash is missing in environment variables")
            return False
        
        # Test channel name - use one from your auto_post_channels_config
        test_channel = "shaamnetwork"  # Updated to a different channel from the config
        
        logger.info(f"Testing fetch operation from channel: {test_channel}")
        
        # Create a temporary client
        client = TelegramClient("diagnostic_session", api_id, api_hash)
        
        try:
            await asyncio.wait_for(client.connect(), timeout=15.0)
            
            # Try to get the channel entity
            try:
                entity = await asyncio.wait_for(
                    client.get_entity(test_channel),
                    timeout=10.0
                )
                
                logger.info(f"✅ Successfully found channel: {getattr(entity, 'title', test_channel)}")
                
                # Try to get the latest post
                try:
                    posts = await asyncio.wait_for(
                        client.get_messages(entity, limit=1),
                        timeout=10.0
                    )
                    
                    if posts and len(posts) > 0:
                        post = posts[0]
                        logger.info(f"✅ Successfully fetched post (ID: {post.id})")
                        logger.info(f"✅ Post has text: {bool(post.message)}")
                        logger.info(f"✅ Post has media: {hasattr(post, 'media') and post.media is not None}")
                    else:
                        logger.warning("⚠️ No posts found in the channel")
                        
                except asyncio.TimeoutError:
                    logger.error("❌ Fetching post timed out after 10 seconds")
                    return False
                    
            except asyncio.TimeoutError:
                logger.error("❌ Getting channel entity timed out after 10 seconds")
                return False
            except Exception as e:
                logger.error(f"❌ Error getting channel entity: {str(e)}")
                return False
                
            await client.disconnect()
            return True
            
        except asyncio.TimeoutError:
            logger.error("❌ Telegram API connection timed out after 15 seconds")
            try:
                await client.disconnect()
            except:
                pass
            return False
    except Exception as e:
        logger.error(f"❌ Fetch operation test failed: {str(e)}")
        return False

async def run_diagnostics():
    """Run all diagnostic tests."""
    logger.info("Starting FetchCog diagnostics...")
    
    openai_success = await test_openai_connection()
    telegram_success = await test_telegram_connection()
    fetch_success = await test_fetch_operation()
    
    logger.info("\n=== Diagnostics Summary ===")
    logger.info(f"OpenAI API: {'✅ PASSED' if openai_success else '❌ FAILED'}")
    logger.info(f"Telegram API: {'✅ PASSED' if telegram_success else '❌ FAILED'}")
    logger.info(f"Fetch Operation: {'✅ PASSED' if fetch_success else '❌ FAILED'}")
    
    if openai_success and telegram_success and fetch_success:
        logger.info("✅ All tests passed! The issue might be elsewhere in the bot.")
    else:
        logger.info("❌ Some tests failed. Fix the issues before running the bot.")

if __name__ == "__main__":
    try:
        asyncio.run(run_diagnostics())
    except KeyboardInterrupt:
        logger.info("Diagnostics interrupted by user")
    except Exception as e:
        logger.error(f"Error running diagnostics: {str(e)}")
        traceback.print_exc() 