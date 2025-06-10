#!/usr/bin/env python3
"""
NewsBot Entry Point

Simple entry point script that runs the bot from its new organized location.
"""

import sys
import os

# Add the src directory to the Python path so imports work correctly
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# Import and run the main function from the bot module
if __name__ == "__main__":
    from bot.main import main
    import asyncio
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n🛑 Bot stopped by user")
    except Exception as e:
        print(f"❌ Error starting bot: {e}")
        sys.exit(1) 