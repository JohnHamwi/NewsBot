# =============================================================================
# NewsBot Admin Authorization Decorator Module
# =============================================================================
# Provides reusable decorators for commands that require admin permissions,
# eliminating code duplication and ensuring consistent authorization checks
# with comprehensive error handling and interaction management.
# Last updated: 2025-01-16

# =============================================================================
# Standard Library Imports
# =============================================================================
from functools import wraps
from typing import Any, Callable

# =============================================================================
# Third-Party Library Imports
# =============================================================================
import discord

# =============================================================================
# Local Application Imports
# =============================================================================
from src.core.config_manager import config
from src.utils.base_logger import base_logger as logger


# =============================================================================
# Admin Authorization Decorators
# =============================================================================
def admin_required(func: Callable) -> Callable:
    """
    Decorator that ensures only users with admin role can execute the command.

    Args:
        func: The command function to wrap

    Returns:
        Wrapped function with admin authorization check
    """

    @wraps(func)
    async def wrapper(self, interaction: discord.Interaction, *args, **kwargs) -> Any:
        """
        Wrapper function that performs admin authorization check.
        """
        try:
            # Get admin role ID from config
            admin_role_id = config.get("bot.admin_role_id")
            admin_user_id = config.get("bot.admin_user_id")
            
            # Check if admin user ID is configured and matches
            if admin_user_id and interaction.user.id == int(admin_user_id):
                logger.debug(
                    f"Admin command {func.__name__} authorized for admin user "
                    f"{interaction.user.id} ({interaction.user.display_name})"
                )
                return await func(self, interaction, *args, **kwargs)
            
            # Check admin role if configured
            if admin_role_id:
                # Check if user has admin role
                admin_role = discord.utils.get(interaction.guild.roles, id=int(admin_role_id))
                
                if not admin_role:
                    logger.error(f"Admin role with ID {admin_role_id} not found in guild")
                    await interaction.response.send_message(
                        "❌ Admin role not found. Please contact the bot administrator.",
                        ephemeral=True,
                    )
                    return
                
                if admin_role in interaction.user.roles:
                    logger.debug(
                        f"Admin command {func.__name__} authorized for user "
                        f"{interaction.user.id} ({interaction.user.display_name})"
                    )
                    return await func(self, interaction, *args, **kwargs)
            
            # User is not authorized
            logger.warning(
                f"Unauthorized access attempt by user {interaction.user.id} "
                f"({interaction.user.display_name}) to command {func.__name__}"
            )
            await interaction.response.send_message(
                "❌ You do not have permission to use this command. Admin access required.",
                ephemeral=True,
            )
            return

        except Exception as e:
            logger.error(f"Error in admin authorization check: {str(e)}", exc_info=True)
            await interaction.response.send_message(
                "❌ An error occurred while checking permissions.", ephemeral=True
            )
            return

    return wrapper


# =============================================================================
# Admin Authorization with Auto-Defer
# =============================================================================
def admin_required_with_defer(func: Callable) -> Callable:
    """
    Decorator that ensures only users with admin role can execute the command.
    Automatically defers the interaction response for long-running commands.

    Args:
        func: The command function to wrap

    Returns:
        Wrapped function with admin authorization check and auto-defer
    """

    @wraps(func)
    async def wrapper(self, interaction: discord.Interaction, *args, **kwargs) -> Any:
        """
        Wrapper function that performs admin authorization check and defers response.
        """
        try:
            # Get admin role ID from config
            admin_role_id = config.get("bot.admin_role_id")
            admin_user_id = config.get("bot.admin_user_id")
            
            # Check if admin user ID is configured and matches
            if admin_user_id and interaction.user.id == int(admin_user_id):
                logger.debug(
                    f"Admin command {func.__name__} authorized for admin user "
                    f"{interaction.user.id} ({interaction.user.display_name})"
                )
                # Defer response for potentially long-running command
                if not interaction.response.is_done():
                    await interaction.response.defer(ephemeral=False)
                return await func(self, interaction, *args, **kwargs)
            
            # Check admin role if configured
            if admin_role_id:
                # Check if user has admin role
                admin_role = discord.utils.get(interaction.guild.roles, id=int(admin_role_id))
                
                if not admin_role:
                    logger.error(f"Admin role with ID {admin_role_id} not found in guild")
                    await interaction.response.send_message(
                        "❌ Admin role not found. Please contact the bot administrator.",
                        ephemeral=True,
                    )
                    return
                
                if admin_role in interaction.user.roles:
                    logger.debug(
                        f"Admin command {func.__name__} authorized for user "
                        f"{interaction.user.id} ({interaction.user.display_name})"
                    )
                    # Defer response for potentially long-running command
                    if not interaction.response.is_done():
                        await interaction.response.defer(ephemeral=False)
                    return await func(self, interaction, *args, **kwargs)
            
            # User is not authorized
            logger.warning(
                f"Unauthorized access attempt by user {interaction.user.id} "
                f"({interaction.user.display_name}) to command {func.__name__}"
            )
            await interaction.response.send_message(
                "❌ You do not have permission to use this command. Admin access required.",
                ephemeral=True,
            )
            return

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
