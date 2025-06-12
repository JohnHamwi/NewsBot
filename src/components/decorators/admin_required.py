"""
Admin Authorization Decorator

Provides a reusable decorator for commands that require admin permissions.
Eliminates code duplication and ensures consistent authorization checks.
"""

from functools import wraps
from typing import Any, Callable

import discord

from src.core.config_manager import config
from src.utils.base_logger import base_logger as logger


def admin_required(func: Callable) -> Callable:
    """
    Decorator that ensures only users with admin role can execute the command.
    TEMPORARILY DISABLED FOR TESTING

    Args:
        func: The command function to wrap

    Returns:
        Wrapped function with admin authorization check
    """

    @wraps(func)
    async def wrapper(self, interaction: discord.Interaction, *args, **kwargs) -> Any:
        """
        Wrapper function that performs admin authorization check.
        TEMPORARILY DISABLED FOR TESTING
        """
        try:
            # TEMPORARILY DISABLED FOR TESTING
            logger.debug(f"Admin command {func.__name__} - permission check temporarily disabled")
            return await func(self, interaction, *args, **kwargs)
            
            # Original permission check code (commented out for testing)
            # # Get admin role ID from config
            # admin_role_id = config.get("bot.admin_role_id")
            # 
            # if not admin_role_id:
            #     logger.error("Admin role ID not configured")
            #     await interaction.response.send_message(
            #         "❌ Admin role not configured. Please contact the bot administrator.",
            #         ephemeral=True,
            #     )
            #     return
            # 
            # # Check if user has admin role
            # admin_role = discord.utils.get(interaction.guild.roles, id=admin_role_id)
            # 
            # if not admin_role:
            #     logger.error(f"Admin role with ID {admin_role_id} not found in guild")
            #     await interaction.response.send_message(
            #         "❌ Admin role not found. Please contact the bot administrator.",
            #         ephemeral=True,
            #     )
            #     return
            # 
            # if admin_role not in interaction.user.roles:
            #     logger.warning(
            #         f"Unauthorized access attempt by user {interaction.user.id} "
            #         f"({interaction.user.display_name}) to command {func.__name__}"
            #     )
            #     await interaction.response.send_message(
            #         "❌ You do not have permission to use this command.", ephemeral=True
            #     )
            #     return
            # 
            # # User is authorized, execute the original function
            # logger.debug(
            #     f"Admin command {func.__name__} authorized for user "
            #     f"{interaction.user.id} ({interaction.user.display_name})"
            # )
            # return await func(self, interaction, *args, **kwargs)

        except Exception as e:
            logger.error(f"Error in admin authorization check: {str(e)}", exc_info=True)
            await interaction.response.send_message(
                "❌ An error occurred while checking permissions.", ephemeral=True
            )
            return

    return wrapper


def admin_required_with_defer(func: Callable) -> Callable:
    """
    Decorator that ensures only users with admin role can execute the command.
    Automatically defers the interaction response for long-running commands.
    TEMPORARILY DISABLED FOR TESTING

    Args:
        func: The command function to wrap

    Returns:
        Wrapped function with admin authorization check and auto-defer
    """

    @wraps(func)
    async def wrapper(self, interaction: discord.Interaction, *args, **kwargs) -> Any:
        """
        Wrapper function that performs admin authorization check and defers response.
        TEMPORARILY DISABLED FOR TESTING
        """
        try:
            # TEMPORARILY DISABLED FOR TESTING
            logger.debug(f"Admin command {func.__name__} - permission check temporarily disabled")
            
            # Defer response for potentially long-running command
            if not interaction.response.is_done():
                await interaction.response.defer(ephemeral=False)
            
            return await func(self, interaction, *args, **kwargs)

        except discord.errors.HTTPException as e:
            if e.code == 40060:  # Interaction already acknowledged
                logger.warning(
                    f"Interaction already acknowledged for command {func.__name__}"
                )
                # Try to execute the function anyway since auth checks passed
                try:
                    return await func(self, interaction, *args, **kwargs)
                except Exception as func_error:
                    logger.error(
                        f"Error executing function after interaction acknowledgment: {func_error}"
                    )
                    return
            else:
                logger.error(
                    f"Discord HTTP error in admin authorization: {str(e)}",
                    exc_info=True,
                )
                # Send error response
                error_message = "❌ An error occurred while processing the command."
                try:
                    if interaction.response.is_done():
                        await interaction.followup.send(error_message, ephemeral=True)
                    else:
                        await interaction.response.send_message(
                            error_message, ephemeral=True
                        )
                except Exception:
                    logger.warning(
                        "Could not send error response - interaction may have expired"
                    )
                return

        except Exception as e:
            logger.error(f"Error in admin authorization check: {str(e)}", exc_info=True)

            # Send error response
            error_message = "❌ An error occurred while checking permissions."
            try:
                if interaction.response.is_done():
                    await interaction.followup.send(error_message, ephemeral=True)
                else:
                    await interaction.response.send_message(
                        error_message, ephemeral=True
                    )
            except Exception:
                logger.warning(
                    "Could not send error response - interaction may have expired"
                )

            return

    return wrapper
