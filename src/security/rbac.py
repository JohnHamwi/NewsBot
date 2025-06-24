# =============================================================================
# NewsBot Role-Based Access Control Module
# =============================================================================
# This module provides RBAC functionality for command and resource access 
# control, including role management, permission management, access control 
# checks, role hierarchy, and permission inheritance.
# Last updated: 2025-01-16

# =============================================================================
# Standard Library Imports
# =============================================================================
import logging
import os
import traceback
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set

# =============================================================================
# Third-Party Library Imports
# =============================================================================
import discord

# =============================================================================
# Local Application Imports
# =============================================================================
# Use the same base logger as the rest of the bot for consistent formatting
from src.utils.base_logger import base_logger as rbac_logger
from src.core.unified_config import unified_config as config


# =============================================================================
# Permission Class
# =============================================================================
class Permission:
    """Represents a single permission."""

    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description


# =============================================================================
# Role Class
# =============================================================================
class Role:
    """
    Represents a role with associated permissions.

    Attributes:
        name (str): Role name
        permissions (Set[str]): Set of permission names
        discord_role_id (int): Associated Discord role ID
    """

    def __init__(self, name: str, discord_role_id: int):
        self.name = name
        self.permissions: Set[str] = set()
        self.discord_role_id = discord_role_id

    def add_permission(self, permission: str) -> None:
        """Add a permission to the role."""
        self.permissions.add(permission)

    def remove_permission(self, permission: str) -> None:
        """Remove a permission from the role."""
        self.permissions.discard(permission)

    def has_permission(self, permission: str) -> bool:
        """Check if role has a specific permission."""
        return permission in self.permissions


# =============================================================================
# RBAC Manager Main Class
# =============================================================================
class RBACManager:
    """
    Manages role-based access control for the bot.

    Features:
    - Role management with Discord integration
    - Permission management and assignment
    - Access control checks for commands and resources
    - Role hierarchy and permission inheritance
    - Comprehensive permission system
    """

    def __init__(self):
        """Initialize RBAC manager."""
        # Prevent multiple initialization of the same instance
        if hasattr(self, "_initialized"):
            return
        self._initialized = True

        self.roles: Dict[str, Role] = {}
        self.permissions: Dict[str, Permission] = {}

        # Initialize default permissions
        self._setup_default_permissions()

    # =========================================================================
    # Initialization Methods
    # =========================================================================
    async def initialize(self):
        """Initialize the RBAC system asynchronously."""
        try:
            # Load permissions and roles
            self.load_permissions()
            rbac_logger.info("✅ RBAC system initialized successfully")
        except Exception as e:
            rbac_logger.error(f"❌ Failed to initialize RBAC system: {e}")
            raise

    def _setup_default_permissions(self) -> None:
        """Set up default permissions."""
        default_permissions = {
            "commands.execute": "Execute basic commands",
            "commands.manage": "Manage bot commands",
            "news.read": "Read news updates",
            "news.post": "Post news updates",
            "news.manage": "Manage news settings",
            "admin.access": "Access admin features",
            "admin.manage": "Manage bot settings",
            "system.view": "View system metrics",
            "system.manage": "Manage system settings",
        }

        for name, description in default_permissions.items():
            self.add_permission(name, description)

    # =========================================================================
    # Permission Management Methods
    # =========================================================================
    def add_permission(self, name: str, description: str) -> None:
        """
        Add a new permission.

        Args:
            name (str): Permission name
            description (str): Permission description
        """
        if name not in self.permissions:
            self.permissions[name] = Permission(name, description)
            rbac_logger.info(f"Added permission: {name}")

    # =========================================================================
    # Role Management Methods
    # =========================================================================
    def add_role(self, name: str, discord_role_id: int) -> None:
        """
        Add a new role.

        Args:
            name (str): Role name
            discord_role_id (int): Associated Discord role ID
        """
        if name not in self.roles:
            self.roles[name] = Role(name, discord_role_id)
            rbac_logger.info(f"Added role: {name}")

    def assign_permission_to_role(self, role_name: str, permission_name: str) -> bool:
        """
        Assign a permission to a role.

        Args:
            role_name (str): Role name
            permission_name (str): Permission name

        Returns:
            bool: Success status
        """
        if role_name in self.roles and permission_name in self.permissions:
            self.roles[role_name].add_permission(permission_name)
            rbac_logger.info(
                f"Assigned permission {permission_name} to role {role_name}"
            )
            return True
        return False

    def remove_permission_from_role(self, role_name: str, permission_name: str) -> bool:
        """
        Remove a permission from a role.

        Args:
            role_name (str): Role name
            permission_name (str): Permission name

        Returns:
            bool: Success status
        """
        if role_name in self.roles:
            self.roles[role_name].remove_permission(permission_name)
            rbac_logger.info(
                f"Removed permission {permission_name} from role {role_name}"
            )
            return True
        return False

    # =========================================================================
    # Access Control Methods
    # =========================================================================
    def has_permission(self, member: discord.Member, permission: str) -> bool:
        """
        Check if a member has a specific permission through their roles.

        Args:
            member (discord.Member): Discord member to check
            permission (str): Permission to check

        Returns:
            bool: Whether member has permission
        """
        # Admin role always has all permissions
        admin_role_id = config.get("bot.admin_role_id")
        if admin_role_id and admin_role_id in [role.id for role in member.roles]:
            return True

        # Check each role the member has
        for role in member.roles:
            for bot_role in self.roles.values():
                if bot_role.discord_role_id == role.id and bot_role.has_permission(
                    permission
                ):
                    return True
        return False

    def get_member_permissions(self, member: discord.Member) -> Set[str]:
        """
        Get all permissions a member has through their roles.

        Args:
            member (discord.Member): Discord member

        Returns:
            Set[str]: Set of permission names
        """
        permissions = set()

        # Admin role gets all permissions
        admin_role_id = config.get("bot.admin_role_id")
        if admin_role_id and admin_role_id in [role.id for role in member.roles]:
            return set(self.permissions.keys())

        # Combine permissions from all roles
        for role in member.roles:
            for bot_role in self.roles.values():
                if bot_role.discord_role_id == role.id:
                    permissions.update(bot_role.permissions)

        return permissions

    def get_role_info(self, role_name: str) -> Optional[Dict]:
        """
        Get information about a role.

        Args:
            role_name (str): Role name

        Returns:
            Optional[Dict]: Role information or None if not found
        """
        if role_name not in self.roles:
            return None

        role = self.roles[role_name]
        return {
            "name": role.name,
            "discord_role_id": role.discord_role_id,
            "permissions": sorted(list(role.permissions)),
        }

    def get_permission_info(self, permission_name: str) -> Optional[Dict]:
        """
        Get information about a permission.

        Args:
            permission_name (str): Permission name

        Returns:
            Optional[Dict]: Permission information or None if not found
        """
        if permission_name not in self.permissions:
            return None

        permission = self.permissions[permission_name]
        return {
            "name": permission.name,
            "description": permission.description,
            "roles": [
                role.name
                for role in self.roles.values()
                if permission.name in role.permissions
            ],
        }

    def get_all_roles(self) -> List[Dict]:
        """
        Get information about all roles.

        Returns:
            List[Dict]: List of role information
        """
        return [self.get_role_info(role_name) for role_name in self.roles.keys()]

    def get_all_permissions(self) -> List[Dict]:
        """
        Get information about all permissions.

        Returns:
            List[Dict]: List of permission information
        """
        return [
            self.get_permission_info(permission_name)
            for permission_name in self.permissions.keys()
        ]

    def load_permissions(self) -> None:
        """Load and initialize all permissions and roles."""
        rbac_logger.debug("Loading RBAC permissions and roles")

        # Add default roles from config
        default_roles = {
            "admin": config.get("bot.admin_role_id", 0),
            "moderator": config.get("bot.moderator_role_id", 0),
            "user": config.get("bot.user_role_id", 0),
        }

        for role_name, role_id in default_roles.items():
            if role_id != 0:  # Only add roles that have valid IDs
                self.add_role(role_name, role_id)
                rbac_logger.debug(f"Added role {role_name} with ID {role_id}")

        rbac_logger.debug("RBAC permissions and roles loaded successfully")
