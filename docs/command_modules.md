# Command Modules Documentation

This document provides detailed information about the command modules (cogs) that implement the bot's functionality.

## Table of Contents
1. [FetchCog](#fetchcog)
2. [SystemCog](#systemcog)
3. [NewsCog](#newscog)
4. [ReloadCog](#reloadcog)

---

## FetchCog

**File**: `src/cogs/fetch_cog.py`

The FetchCog is the primary module responsible for fetching, processing, and posting news from Telegram channels to Discord.

### Key Features

- **Telegram Integration**: Fetches posts from configured Telegram channels
- **Media Handling**: Downloads and processes photos and videos
- **Content Filtering**: Identifies and filters advertisements and off-topic content
- **Arabic-to-English Translation**: Uses AI to translate Arabic content to English
- **Post Formatting**: Creates rich Discord embeds with original and translated content
- **Blacklist Management**: Prevents reposting of previously posted content
- **Auto-Posting**: Supports scheduled automatic posting
- **Post Reviewing**: Allows admins to review posts before sending to news channel

### Commands

#### `/fetch`
Fetches and processes posts from a specified Telegram channel.

**Usage**: `/fetch channel:@channel_name number:5`

**Parameters**:
- `channel`: The Telegram channel username (with autocompletion support)
- `number`: Number of posts to fetch (1-10, default: 1)

**Permissions**:
- Requires "fetch" permission

#### `/clear_blacklist`
Clears all IDs from the blacklist, allowing previously posted content to be posted again.

**Usage**: `/clear_blacklist`

**Permissions**:
- Requires admin permission

### Helper Functions

#### `handle_fetch_error(error: Exception, context: str) -> None`
Handles errors in fetch operations, sending error embeds.

#### `should_skip_post(content: str) -> bool`
Checks if a post should be skipped based on blacklist.

#### `fetch_and_post_auto(channelname: str) -> bool`
Fetches and posts a single post from a channel for auto-posting. Returns True if posted successfully.

### Message Processing

The module processes Telegram messages with these steps:
1. Fetch messages from channel
2. Filter out messages without media or text
3. Check against blacklist
4. Download media
5. Clean and process text (remove hashtags, emojis, etc.)
6. Generate English translation using AI
7. Create Discord embed with original and translated content
8. Send embed with action buttons for posting/skipping

### Usage Example

```python
# Fetch command handler
@app_commands.command(name="fetch", description="Fetch latest posts from a Telegram channel")
async def fetch(self, interaction: discord.Interaction, channel: str, number: Optional[int] = None) -> None:
    # Command implementation...

# Auto-posting usage
async def auto_post_task(self):
    while not self.is_closed():
        for channel in channels:
            posted = await self.fetch_cog.fetch_and_post_auto(channel)
            if posted:
                break
        await asyncio.sleep(self.auto_post_interval)
```

---

## SystemCog

**File**: `src/cogs/system.py`

The SystemCog provides system administration and monitoring commands for managing the bot's operation.

### Key Features

- **Status Reporting**: Shows detailed bot and system status
- **Log Viewing**: Displays recent log entries
- **Rich Presence Control**: Changes bot's Discord presence mode
- **Auto-Post Interval**: Configures auto-posting schedule
- **Manual Posting**: Triggers immediate post
- **Debug Mode**: Toggles debug logging level

### Commands

#### `/status`
Shows detailed bot status including system metrics, bot metrics, and service statuses.

**Usage**: `/status`

**Permissions**:
- Requires "system.view" permission

#### `/info`
Shows basic bot information including version and uptime.

**Usage**: `/info`

**Permissions**:
- No special permissions required

#### `/log`
Shows the most recent log entries.

**Usage**: `/log lines:20`

**Parameters**:
- `lines`: Number of log lines to show (5-50, default: 15)

**Permissions**:
- Requires "admin.access" permission

#### `/set_rich_presence`
Sets the bot's rich presence mode (automatic or maintenance).

**Usage**: `/set_rich_presence mode:automatic`

**Parameters**:
- `mode`: "automatic" or "maintenance"

**Permissions**:
- Requires "admin.access" permission

#### `/set_interval`
Sets the auto-post interval in hours.

**Usage**: `/set_interval hours:6`

**Parameters**:
- `hours`: Hours between posts (0-24, 0 to disable)

**Permissions**:
- Requires "admin.access" permission

#### `/start`
Triggers an immediate auto-post.

**Usage**: `/start`

**Permissions**:
- Requires "admin.access" permission

#### `/set_debug_mode`
Sets debug mode on or off.

**Usage**: `/set_debug_mode mode:on`

**Parameters**:
- `mode`: "on" or "off"

**Permissions**:
- Requires admin user ID

### Helper Functions

#### `_gather_system_metrics()`
Gathers system metrics including CPU, RAM, and disk usage.

#### `_gather_bot_metrics()`
Gathers bot metrics including uptime, guilds, and users.

#### `_gather_cache_metrics()`
Gathers cache metrics including channels and post history.

#### `_gather_circuit_breaker_metrics()`
Gathers circuit breaker statuses for external services.

#### `_gather_presence_metrics()`
Gathers rich presence mode and status.

#### `_gather_error_metrics()`
Gathers error statistics and recent error history.

#### `_gather_telegram_metrics()`
Gathers Telegram connection status.

### Usage Example

```python
# Status command handler
@app_commands.command(name="status", description="Show detailed bot status")
async def status_command(self, interaction: discord.Interaction) -> None:
    # Command implementation...

# Set interval command handler
@app_commands.command(name="set_interval", description="Set the auto-post interval in hours")
async def set_interval_command(self, interaction: discord.Interaction, hours: int) -> None:
    # Validate input
    if hours < 0 or hours > 24:
        await interaction.followup.send("Interval must be between 0 (disabled) and 24 hours.")
        return
    
    # Set interval
    self.bot.set_auto_post_interval(hours)
    
    # Send confirmation
    embed = discord.Embed(
        title="Auto-Post Interval Updated",
        description=f"Automatic posting interval set to **{hours} hour{'s' if hours != 1 else ''}**.",
        color=discord.Color.green()
    )
    await interaction.followup.send(embed=embed)
```

---

## NewsCog

**File**: `src/cogs/news.py`

The NewsCog manages Telegram channels for news aggregation, including activation and deactivation of channels.

### Key Features

- **Channel Management**: Activates and deactivates Telegram channels
- **Channel Listing**: Lists all configured channels by status
- **Cache Integration**: Stores channel configuration in persistent cache
- **Validation**: Verifies channel existence before activation

### Commands

#### `/channel_activate`
Activates a Telegram channel for news aggregation.

**Usage**: `/channel_activate username:channelname`

**Parameters**:
- `username`: Telegram channel username (without @)

**Permissions**:
- Requires "admin.access" permission

#### `/channel_deactivate`
Deactivates a Telegram channel to stop receiving news from it.

**Usage**: `/channel_deactivate username:channelname`

**Parameters**:
- `username`: Telegram channel username (without @)

**Permissions**:
- Requires "admin.access" permission

#### `/channel_list`
Lists all configured Telegram channels by status.

**Usage**: `/channel_list status:all`

**Parameters**:
- `status`: Filter by status ("all", "activated", or "deactivated")

**Permissions**:
- Requires "admin.access" permission

### Helper Functions

#### `_validate_channel(username: str) -> bool`
Validates that a channel exists on Telegram.

#### `_update_channel_cache(username: str, status: str) -> bool`
Updates the channel cache with a new status.

#### `_list_channels(status: str) -> List[str]`
Lists channels by status from the cache.

### Usage Example

```python
# Activate channel command handler
@app_commands.command(name="channel_activate", description="Activate a Telegram channel by username")
async def channel_activate(self, interaction: discord.Interaction, username: str) -> None:
    # Remove @ if provided
    username = username.lstrip('@')
    
    # Validate channel exists
    valid = await self._validate_channel(username)
    if not valid:
        await interaction.followup.send(f"Channel @{username} not found on Telegram.")
        return
    
    # Activate channel
    success = await self._update_channel_cache(username, "activated")
    if success:
        embed = discord.Embed(
            title="Channel Activated",
            description=f"Channel @{username} has been activated for news aggregation.",
            color=discord.Color.green()
        )
        await interaction.followup.send(embed=embed)
    else:
        await interaction.followup.send(f"Failed to activate channel @{username}.")
```

---

## ReloadCog

**File**: `src/cogs/reload.py`

The ReloadCog provides runtime code reloading without requiring a bot restart, useful for development and maintenance.

### Key Features

- **Extension Reloading**: Reloads cogs/extensions at runtime
- **Error Handling**: Provides detailed error messages if reloading fails
- **Safety Checks**: Ensures critical modules aren't unloaded

### Commands

#### `/reload`
Reloads all cogs/extensions.

**Usage**: `/reload`

**Permissions**:
- Requires "admin.access" permission

### Internal Methods

#### `_reload_extensions()`
Reloads all extensions and handles errors.

#### `_get_extension_list()`
Gets a list of all currently loaded extensions.

### Usage Example

```python
# Reload command handler
@app_commands.command(name="reload", description="Reload all cogs/extensions")
async def reload_command(self, interaction: discord.Interaction) -> None:
    await interaction.response.defer()
    
    # Check permissions
    if not self.bot.rbac.has_permission(interaction.user.id, "admin.access"):
        await interaction.followup.send("You don't have permission to use this command.")
        return
    
    # Reload extensions
    success, failed = await self._reload_extensions()
    
    # Build response
    if not failed:
        embed = discord.Embed(
            title="Reload Complete",
            description=f"Successfully reloaded {len(success)} extensions.",
            color=discord.Color.green()
        )
    else:
        embed = discord.Embed(
            title="Reload Partially Complete",
            description=f"Reloaded {len(success)} extensions. {len(failed)} failed.",
            color=discord.Color.orange()
        )
        embed.add_field(name="Failed Extensions", value="\n".join(failed), inline=False)
    
    await interaction.followup.send(embed=embed)
``` 