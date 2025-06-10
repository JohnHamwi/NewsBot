import asyncio
from .newsbot import NewsBot
from src.core.config_manager import config


async def main():
    bot = NewsBot()
    async with bot:
        await bot.start(config.get("tokens.discord"))

if __name__ == "__main__":
    asyncio.run(main())
