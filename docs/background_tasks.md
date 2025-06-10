# Background Tasks Documentation

This document provides detailed information about the background tasks that run continuously in the NewsBot application.

## Table of Contents
1. [Auto-Posting Task](#auto-posting-task)
2. [Resource Monitoring Task](#resource-monitoring-task)
3. [Metrics Collection Task](#metrics-collection-task)
4. [Log Tail Task](#log-tail-task)
5. [Rich Presence Task](#rich-presence-task)

---

## Auto-Posting Task

**File**: `main.py (NewsBot.auto_post_task)`

The Auto-Posting Task automatically fetches and posts news from configured Telegram channels at scheduled intervals.

### Key Features

- **Scheduled Posting**: Posts news at configured time intervals
- **Channel Rotation**: Uses round-robin selection of channels to ensure variety
- **Error Resilience**: Continues operation even if some channels fail
- **Configurable Interval**: Adjustable posting frequency (1-24 hours)
- **Force Post**: Supports manual triggering of immediate posts
- **Persistent Configuration**: Saves settings and last post time to cache

### Implementation Details

#### State Variables
- `auto_post_interval`: Seconds between posts (0 = disabled)
- `last_post_time`: Timestamp of the last successful post
- `force_auto_post`: Flag to trigger immediate posting
- `next_post_time`: Calculated next post time

#### Algorithm
1. Check if auto-posting is enabled (interval > 0)
2. Check for force post flag or if enough time has passed since last post
3. Load channel configuration from cache
4. Attempt to post from each channel in rotation until successful
5. Update last post time and next post time
6. Save configuration to cache
7. Sleep until next check

### Configuration

The auto-posting task can be configured via:
- `/set_interval` command: Sets hours between posts
- `/start` command: Forces an immediate post
- `auto_post_channels_config` cache: Stores channel rotation state

### Error Handling

- Failed posts from a channel don't stop the task
- The task advances to the next channel if the current one fails
- All errors are logged and reported through the error handler
- Task continues running even after errors

### Example Operation

```python
# Main auto-post task loop
async def auto_post_task(self):
    await self.wait_until_ready()
    while not self.is_closed():
        try:
            if self.auto_post_interval <= 0:
                # Auto-posting disabled
                await asyncio.sleep(60)
                continue
                
            now = datetime.datetime.utcnow()
            
            # Check for force post or interval elapsed
            if self.force_auto_post or (
                self.last_post_time and 
                (now - self.last_post_time).total_seconds() >= self.auto_post_interval
            ):
                self.force_auto_post = False
                
                # Get channels and current index
                config = await self.json_cache.get("auto_post_channels_config") or {}
                channels = config.get("channels", [])
                index = config.get("index", 0)
                
                # Try posting from each channel
                for i in range(len(channels)):
                    channel_idx = (index + i) % len(channels)
                    channel = channels[channel_idx]
                    
                    # Try to post
                    fetch_cog = self.get_cog("FetchCog")
                    if fetch_cog:
                        post_made = await fetch_cog.fetch_and_post_auto(channel)
                        if post_made:
                            # Update state
                            self.last_post_time = now
                            self.set_next_post_time(now + datetime.timedelta(seconds=self.auto_post_interval))
                            self.mark_just_posted()
                            
                            # Update index for next time
                            config["index"] = (channel_idx + 1) % len(channels)
                            await self.json_cache.set("auto_post_channels_config", config)
                            break
                
                # No valid post found
                if not post_made:
                    config["index"] = (index + 1) % len(channels)
                    await self.json_cache.set("auto_post_channels_config", config)
            
            # Sleep for a bit before checking again
            await asyncio.sleep(60)
            
        except Exception as e:
            logger.error(f"Error in auto_post_task: {str(e)}")
            await asyncio.sleep(60)
```

---

## Resource Monitoring Task

**File**: `main.py (NewsBot.resource_monitor)`

The Resource Monitoring Task tracks CPU and RAM usage and alerts when thresholds are exceeded.

### Key Features

- **CPU Monitoring**: Tracks CPU usage percentage
- **RAM Monitoring**: Tracks memory usage of the bot process
- **Threshold Alerts**: Sends alerts when resources exceed thresholds
- **Admin Notification**: Pings the admin when critical resource usage occurs
- **Continuous Monitoring**: Runs at regular intervals

### Implementation Details

#### Monitored Metrics
- CPU usage percentage
- Process memory usage (RAM)
- Process ID

#### Thresholds
- CPU: 80% by default
- RAM: 70% by default

#### Algorithm
1. Measure current CPU and RAM usage
2. Compare against configured thresholds
3. If thresholds exceeded, send alert to errors channel
4. Sleep for configured interval
5. Repeat

### Configuration

Resource monitoring thresholds are configured in `config.yaml`:
```yaml
monitoring:
  resource_alerts:
    cpu_threshold: 80.0  # percentage
    ram_threshold: 70.0  # percentage
    check_interval: 30  # seconds
```

### Error Handling

- The task catches and logs its own exceptions
- Errors in the monitoring task itself are reported via the error handler
- The task continues running even after internal errors

### Example Operation

```python
# Resource monitoring task
async def resource_monitor(self):
    from src.utils.error_handler import error_handler
    admin_user_id = int(os.getenv("ADMIN_USER_ID", "0"))
    cpu_threshold = 80.0
    ram_threshold = 70.0
    process = psutil.Process()
    
    while True:
        try:
            cpu = psutil.cpu_percent()
            ram = process.memory_percent()
            
            if cpu > cpu_threshold or ram > ram_threshold:
                msg = f"⚠️ High resource usage detected! CPU: {cpu:.1f}%, RAM: {ram:.1f}%"
                logger.warning(msg)
                
                if self.errors_channel:
                    alert = discord.Embed(
                        title="⚠️ High Resource Usage",
                        description=msg,
                        color=discord.Color.red(),
                        timestamp=discord.utils.utcnow(),
                    )
                    alert.add_field(name="CPU Usage", value=f"{cpu:.1f}%", inline=True)
                    alert.add_field(name="RAM Usage", value=f"{ram:.1f}%", inline=True)
                    alert.add_field(name="Process ID", value=f"{process.pid}", inline=True)
                    
                    content = f"<@{admin_user_id}>"
                    await self.errors_channel.send(content=content, embed=alert)
                    
            await asyncio.sleep(30)
            
        except Exception as e:
            logger.error(f"Error in resource monitor: {str(e)}")
            await error_handler.send_error_embed(
                error_title="Resource Monitor Error",
                error=e,
                context="resource_monitor",
                bot=self
            )
            await asyncio.sleep(30)
```

---

## Metrics Collection Task

**File**: `main.py (NewsBot.update_metrics)`

The Metrics Collection Task periodically updates system metrics for monitoring purposes.

### Key Features

- **System Metrics**: Collects and updates system resource metrics
- **Prometheus Integration**: Works with Prometheus metrics format
- **Configurable Interval**: Customizable collection frequency
- **Error Resilience**: Continues operation even after collection errors

### Implementation Details

#### Collected Metrics
- Memory usage
- Command execution metrics
- Error counts
- Message processing metrics

#### Algorithm
1. Call metrics manager's `update_system_metrics()` method
2. Handle any exceptions that occur
3. Sleep for configured interval
4. Repeat

### Configuration

Metrics collection is configured in `config.yaml`:
```yaml
monitoring:
  metrics:
    port: 8000
    collection_interval: 60  # seconds
```

### Error Handling

- The task catches and logs its own exceptions
- Errors in metrics collection are reported via the error handler
- The task continues running even after collection errors

### Example Operation

```python
# Metrics collection task
async def update_metrics(self):
    from src.utils.error_handler import error_handler
    try:
        while True:
            try:
                self.metrics.update_system_metrics()
            except Exception as e:
                logger.error(f"Error updating metrics: {str(e)}")
                await error_handler.send_error_embed(
                    error_title="Metrics Update Error",
                    error=e,
                    context="update_metrics",
                    bot=self
                )
            await asyncio.sleep(METRICS_COLLECTION_INTERVAL)
    except Exception as e:
        logger.error(f"Error in update_metrics loop: {str(e)}")
        await error_handler.send_error_embed(
            error_title="Metrics Task Loop Error",
            error=e,
            context="update_metrics main loop",
            bot=self
        )
```

---

## Log Tail Task

**File**: `main.py (NewsBot.log_tail_task)`

The Log Tail Task periodically posts recent log entries and system status to the log channel.

### Key Features

- **Log Aggregation**: Collects recent log entries
- **Heartbeat Monitoring**: Shows bot is alive and functioning
- **System Statistics**: Includes CPU, memory, and uptime information
- **Error Summary**: Shows count of errors in the last 24 hours
- **Configurable Interval**: Customizable reporting frequency

### Implementation Details

#### Reported Information
- Recent log lines (last 15)
- CPU and memory usage
- Bot uptime
- Error count (last 24 hours)

#### Algorithm
1. Read the last N lines from the log file
2. Gather system metrics (CPU, RAM)
3. Calculate uptime
4. Count recent errors
5. Format and send an embed to the log channel
6. Sleep for configured interval
7. Repeat

### Configuration

Log tailing is configured in `config.yaml`:
```yaml
logging:
  file: "logs/NewsBot.log"
  max_lines_tail: 15
  heartbeat_interval: 3600  # seconds
```

### Error Handling

- The task catches and logs its own exceptions
- Errors in log tailing are reported via the error handler
- The task continues running even after internal errors

### Example Operation

```python
# Log tail task
async def log_tail_task(self):
    import aiofiles
    import datetime
    from src.utils.error_handler import error_handler
    
    await self.wait_until_ready()
    log_path = "logs/NewsBot.log"
    
    try:
        while not self.is_closed():
            try:
                if self.log_channel:
                    # Read last 15 lines
                    lines = []
                    try:
                        async with aiofiles.open(log_path, mode="r") as f:
                            all_lines = await f.readlines()
                            lines = all_lines[-15:]
                    except Exception as e:
                        lines = [f"Could not read log file: {e}\n"]
                    
                    # Gather system metrics
                    process = psutil.Process()
                    cpu_usage = psutil.cpu_percent()
                    memory_usage = process.memory_info().rss / 1024 / 1024
                    uptime = discord.utils.utcnow() - self.startup_time
                    hours, remainder = divmod(int(uptime.total_seconds()), 3600)
                    minutes, seconds = divmod(remainder, 60)
                    days, hours = divmod(hours, 24)
                    uptime_str = f"{days} days, {hours}:{minutes:02}:{seconds:02}"
                    
                    # Count recent errors
                    from datetime import datetime, timedelta
                    now = datetime.utcnow()
                    error_count_24h = 0
                    if hasattr(error_handler, "error_history"):
                        error_count_24h = sum(
                            1 for err in error_handler.error_history
                            if (now - err.timestamp).total_seconds() < 86400
                        )
                    
                    # Create and send embed
                    summary = (
                        f"❤️ **HEARTBEAT**\n\n"
                        f"⏰ **Uptime:** {uptime_str}   "
                        f"🖥️ **CPU:** {cpu_usage:.1f}%   "
                        f"🗄️ **Memory:** {memory_usage:.1f} MB\n\n"
                    )
                    joined_lines = "\n\n".join(line.strip() for line in lines)
                    content = summary + f"```python\n{joined_lines}\n```" + f"\n🛑 **Errors (24h):** {error_count_24h}\n"
                    
                    embed = discord.Embed(
                        title=None,
                        description=content,
                        color=discord.Color.green(),
                        timestamp=discord.utils.utcnow(),
                    )
                    await self.log_channel.send(embed=embed)
                    
            except Exception as e:
                logger.error(f"Error in log_tail_task: {str(e)}")
                await error_handler.send_error_embed(
                    error_title="Log Tail Task Error",
                    error=e,
                    context="log_tail_task",
                    bot=self
                )
                
            await asyncio.sleep(3600)  # 1 hour interval
            
    except Exception as e:
        logger.error(f"Error in log_tail_task main loop: {str(e)}")
        await error_handler.send_error_embed(
            error_title="Log Tail Task Loop Error",
            error=e,
            context="log_tail_task main loop",
            bot=self
        )
```

---

## Rich Presence Task

**File**: `main.py (NewsBot.rich_presence_task)`

The Rich Presence Task manages the bot's Discord status/presence based on its current mode and state.

### Key Features

- **Multiple Modes**: Supports different operational modes (automatic, maintenance)
- **Dynamic Status**: Shows countdown to next post in automatic mode
- **Post Indicators**: Shows when posts have just been made
- **Visual Feedback**: Provides clear visual indication of bot state
- **Continuous Updates**: Regularly updates to reflect current state

### Implementation Details

#### Presence Modes
- **Automatic**: Shows countdown to next post
- **Maintenance**: Shows maintenance status
- **Posted**: Shows that a post was just made

#### State Variables
- `rich_presence_mode`: Current mode (automatic or maintenance)
- `_just_posted`: Flag indicating a post was just made
- `next_post_time`: When the next automatic post is scheduled

#### Algorithm
1. Check current rich presence mode
2. For maintenance mode, set maintenance presence
3. For automatic mode:
   a. If just posted, set posted presence for 10 minutes
   b. Otherwise, calculate seconds until next post and set automatic presence
4. Sleep for configured interval
5. Repeat

### Configuration

Rich presence is configured in `config.yaml`:
```yaml
rich_presence:
  update_interval: 60  # seconds
  posted_duration: 600  # seconds
```

### Error Handling

- The task catches and logs its own exceptions
- Errors in presence updates are reported via the error handler
- The task continues running even after internal errors

### Example Operation

```python
# Rich presence task
async def rich_presence_task(self):
    import datetime
    import asyncio
    from src.utils.error_handler import error_handler
    
    await self.wait_until_ready()
    
    try:
        while not self.is_closed():
            try:
                if self.rich_presence_mode == "maintenance":
                    await set_maintenance_presence(self)
                    await asyncio.sleep(60)
                elif self.rich_presence_mode == "automatic":
                    if self._just_posted:
                        await set_posted_presence(self)
                        await asyncio.sleep(600)  # 10 minutes
                        self._just_posted = False
                    else:
                        # Calculate seconds until next post
                        now = datetime.datetime.utcnow()
                        if self.next_post_time and self.next_post_time > now:
                            seconds = int((self.next_post_time - now).total_seconds())
                        else:
                            seconds = 0
                        await set_automatic_presence(self, max(seconds, 0))
                        await asyncio.sleep(60)
                else:
                    await set_maintenance_presence(self)
                    await asyncio.sleep(60)
                    
            except Exception as e:
                logger.error(f"Error in rich_presence_task: {str(e)}")
                await error_handler.send_error_embed(
                    error_title="Rich Presence Task Error",
                    error=e,
                    context="rich_presence_task",
                    bot=self
                )
                await asyncio.sleep(60)
                
        except Exception as e:
            logger.error(f"Error in rich_presence_task main loop: {str(e)}")
            await error_handler.send_error_embed(
                error_title="Rich Presence Task Loop Error",
                error=e,
                context="rich_presence_task main loop",
                bot=self
            )
``` 