"""
Reload Cog

Provides an admin-only /reload command to hot-reload all loaded cogs/extensions
without restarting the bot.
"""

from typing import List, Tuple

import discord
from discord import app_commands
from discord.ext import commands

from src.utils.base_logger import base_logger as logger
from src.utils.config import Config
from src.utils.error_handler import error_handler

# Configuration constants
GUILD_ID = Config.GUILD_ID or 0
ADMIN_USER_ID = Config.ADMIN_USER_ID or 0


class ReloadCog(commands.Cog):
    """
    Cog for hot-reloading all loaded cogs/extensions via /reload command.

    Provides admin-only functionality to reload extensions without restarting
    the bot, useful for development and quick fixes.
    """

    def __init__(self, bot: commands.Bot) -> None:
        """Initialize the ReloadCog with bot reference."""
        self.bot = bot
        logger.info("🔧 ReloadCog initialized")

    @app_commands.command(
        name="reload", description="Reload all cogs and sync commands (admin only)"
    )
    async def reload_command(self, interaction: discord.Interaction) -> None:
        """
        Reload all loaded cogs/extensions.

        Args:
            interaction: The Discord interaction object
        """
        logger.info(
            f"[RELOAD][CMD] Reload command invoked by user {interaction.user.id}"
        )

        try:
            # Check authorization
            if interaction.user.id != ADMIN_USER_ID:
                logger.warning(
                    f"[RELOAD][CMD] Unauthorized access attempt by user {interaction.user.id}"
                )

                await interaction.response.send_message(
                    "❌ You are not authorized to use this command."
                )

                await error_handler.send_error_embed(
                    "Unauthorized Access",
                    Exception("User is not authorized."),
                    context=f"User: {interaction.user} ({interaction.user.id}) | Command: reload",
                    bot=self.bot,
                    channel=getattr(self.bot, "log_channel", None),
                )
                return

            # Defer response for potentially long operation
            await interaction.response.defer()

            # Perform reload operation
            reloaded, failed = await self._reload_all_extensions()

            # Create response embed
            embed = await self._create_reload_embed(reloaded, failed)

            # Send response
            await interaction.followup.send(embed=embed)

            logger.info(
                f"[RELOAD][CMD] Reload completed by user {interaction.user.id}: "
                f"{len(reloaded)} successful, {len(failed)} failed"
            )

        except Exception as e:
            logger.error(f"[RELOAD][CMD] Error during reload: {str(e)}", exc_info=True)

            error_embed = discord.Embed(
                title="❌ Reload Error",
                description=f"An error occurred during reload: {str(e)}",
                color=discord.Color.red(),
            )

            try:
                if interaction.response.is_done():
                    await interaction.followup.send(embed=error_embed)
                else:
                    await interaction.response.send_message(embed=error_embed)
            except discord.errors.NotFound:
                logger.warning(
                    "[RELOAD][CMD] Could not send error response, interaction expired"
                )

    async def _reload_all_extensions(self) -> Tuple[List[str], List[Tuple[str, str]]]:
        """
        Reload all loaded extensions.

        Returns:
            Tuple of (successfully_reloaded, failed_with_errors)
        """
        reloaded = []
        failed = []

        # Get list of extensions to reload
        extensions_to_reload = list(self.bot.extensions.keys())
        logger.debug(
            f"[RELOAD] Attempting to reload {len(extensions_to_reload)} extensions"
        )

        for ext_name in extensions_to_reload:
            try:
                await self.bot.reload_extension(ext_name)
                reloaded.append(ext_name)
                logger.debug(f"[RELOAD] Successfully reloaded: {ext_name}")

            except Exception as e:
                error_msg = str(e)
                failed.append((ext_name, error_msg))
                logger.error(f"[RELOAD] Failed to reload {ext_name}: {error_msg}")

        # Force command sync after reloading to refresh Discord's cache
        try:
            logger.debug("[RELOAD] Forcing command sync to refresh Discord cache")
            synced = await self.bot.tree.sync()
            logger.info(f"[RELOAD] ✅ Synced {len(synced)} slash commands after reload")
        except Exception as e:
            logger.error(f"[RELOAD] ❌ Failed to sync commands after reload: {str(e)}")
            failed.append(("command_sync", str(e)))

        return reloaded, failed

    async def _create_reload_embed(
        self, reloaded: List[str], failed: List[Tuple[str, str]]
    ) -> discord.Embed:
        """
        Create embed showing reload and sync results.

        Args:
            reloaded: List of successfully reloaded extensions
            failed: List of tuples (extension_name, error_message)

        Returns:
            Discord embed with reload and sync results
        """
        # Determine embed color based on results
        if not failed:
            color = discord.Color.green()
            title = "✅ Reload & Sync Completed Successfully"
        elif not reloaded:
            color = discord.Color.red()
            title = "❌ Reload & Sync Failed"
        else:
            color = discord.Color.orange()
            title = "⚠️ Reload & Sync Completed with Errors"

        embed = discord.Embed(
            title=title, color=color, timestamp=discord.utils.utcnow()
        )

        # Add successfully reloaded extensions
        if reloaded:
            # Truncate list if too long for Discord embed
            reloaded_display = reloaded[:10]  # Show max 10
            reloaded_text = "\n".join(f"✅ {ext}" for ext in reloaded_display)

            if len(reloaded) > 10:
                reloaded_text += f"\n... and {len(reloaded) - 10} more"

            embed.add_field(
                name=f"Reloaded ({len(reloaded)})",
                value=f"```{reloaded_text}```",
                inline=False,
            )
        else:
            embed.add_field(name="Reloaded (0)", value="```None```", inline=False)

        # Add failed extensions
        if failed:
            # Truncate list if too long for Discord embed
            failed_display = failed[:5]  # Show max 5 failures
            failed_text = "\n".join(
                f"❌ {ext}: {err[:50]}..." if len(err) > 50 else f"❌ {ext}: {err}"
                for ext, err in failed_display
            )

            if len(failed) > 5:
                failed_text += f"\n... and {len(failed) - 5} more failures"

            embed.add_field(
                name=f"Failed ({len(failed)})",
                value=f"```{failed_text}```",
                inline=False,
            )

        embed.set_footer(
            text=f"Total extensions processed: {len(reloaded) + len(failed)}"
        )

        return embed


async def setup(bot: commands.Bot) -> None:
    """Add the ReloadCog to the bot."""
    await bot.add_cog(ReloadCog(bot))
    logger.debug("📥 ReloadCog loaded successfully")
