import asyncio
from .newsbot import NewsBot
from src.core.config_manager import config
from src.utils.base_logger import base_logger as logger

async def main():
    bot = NewsBot()
    async with bot:
        await bot.start(config.get("tokens.discord"))

if __name__ == "__main__":
    asyncio.run(main())
