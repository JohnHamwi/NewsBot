import asyncio
import sys
from pathlib import Path

# Add src directory to Python path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.config_manager import config

from .newsbot import NewsBot


async def main():
    bot = NewsBot()
    async with bot:
        await bot.start(config.get("tokens.discord"))


if __name__ == "__main__":
    asyncio.run(main())
