# NewsBot API Reference

## Overview

NewsBot is a sophisticated Discord bot that bridges Telegram news channels with Discord servers, featuring AI-powered translation, content analysis, and automated posting capabilities.

## Core Components

### Bot Instance (`src/bot/newsbot.py`)

#### `class NewsBot(discord.Client)`

The main bot class handling Discord interactions and automation.

**Key Methods:**

```python
async def fetch_and_post_auto(channel_name: str = None) -> bool
```
- **Purpose**: Automatically fetch and post news from Telegram channels
- **Parameters**: 
  - `channel_name` (optional): Specific channel to fetch from
- **Returns**: `bool` - Success status
- **Usage**: Called by background tasks for automation

```python
def set_auto_post_interval(minutes: int) -> None
```
- **Purpose**: Configure automatic posting interval
- **Parameters**: 
  - `minutes`: Interval between posts in minutes
- **Usage**: Admin configuration

```python
async def get_automation_status() -> dict
```
- **Purpose**: Get current automation configuration and status
- **Returns**: Dictionary with automation settings
- **Usage**: Status monitoring and admin commands

### AI Services

#### `class AIService` (`src/services/ai_service.py`)

Handles OpenAI API interactions for translation and analysis.

**Key Methods:**

```python
async def translate_to_english(arabic_text: str) -> str
```
- **Purpose**: Translate Arabic text to English using GPT-4
- **Parameters**: 
  - `arabic_text`: Arabic text to translate
- **Returns**: English translation
- **Error Handling**: Returns original text on failure

```python
async def categorize_content(content: str) -> str
```
- **Purpose**: Categorize news content using AI
- **Parameters**: 
  - `content`: Text content to categorize
- **Returns**: Category string
- **Categories**: "breaking", "politics", "military", "economy", etc.

#### `class AIContentAnalyzer` (`src/services/ai_content_analyzer.py`)

Advanced content analysis and processing.

**Key Methods:**

```python
async def analyze_content(content: str) -> ContentAnalysis
```
- **Purpose**: Comprehensive content analysis including sentiment, urgency, and safety
- **Parameters**: 
  - `content`: Text content to analyze
- **Returns**: `ContentAnalysis` object with detailed results

### Posting Service

#### `class PostingService` (`src/services/posting_service.py`)

Handles Discord message posting with rich formatting.

**Key Methods:**

```python
async def post_news_content(content_data: dict, content_category: str = "general", is_manual: bool = False) -> bool
```
- **Purpose**: Post formatted news content to Discord
- **Parameters**: 
  - `content_data`: Dictionary containing news data
  - `content_category`: Content category for formatting
  - `is_manual`: Whether this is a manual or automated post
- **Returns**: Success status

**Content Data Structure:**
```python
{
    "arabic_text": str,           # Original Arabic text
    "english_translation": str,   # AI translation
    "ai_title": str,             # AI-generated title
    "location": str,             # Detected location
    "media_urls": List[str],     # Media file URLs
    "source_channel": str,       # Telegram channel name
    "urgency_level": str,        # "breaking", "important", "normal"
    "timestamp": datetime        # Message timestamp
}
```

### Media Service

#### `class MediaService` (`src/services/media_service.py`)

Handles media download and processing from Telegram.

**Key Methods:**

```python
async def download_media(message, timeout: int = 30) -> List[str]
```
- **Purpose**: Download media files from Telegram messages
- **Parameters**: 
  - `message`: Telegram message object
  - `timeout`: Download timeout in seconds
- **Returns**: List of local file paths

### Monitoring Systems

#### `class HealthMonitor` (`src/monitoring/health_monitor.py`)

Comprehensive system health monitoring.

**Key Methods:**

```python
async def run_full_health_check() -> SystemHealth
```
- **Purpose**: Perform comprehensive system health check
- **Returns**: `SystemHealth` object with detailed status
- **Checks**: Discord connection, Telegram connection, OpenAI API, system resources

#### `class AdvancedMetricsCollector` (`src/monitoring/advanced_metrics.py`)

Advanced performance metrics and optimization.

**Key Methods:**

```python
async def get_performance_summary() -> dict
```
- **Purpose**: Get comprehensive performance analysis
- **Returns**: Dictionary with metrics, trends, and recommendations
- **Features**: Anomaly detection, trend analysis, optimization suggestions

## Admin Commands

### `/admin status`
- **Purpose**: Display bot status and automation health
- **Permissions**: Admin only
- **Response**: Embed with system metrics and automation status

### `/admin emergency`
- **Purpose**: Emergency controls for bot operation
- **Options**: 
  - `pause`: Pause auto-posting
  - `resume`: Resume auto-posting
  - `restart`: Restart bot
  - `stop`: Emergency stop
- **Permissions**: Admin only

### `/admin maintenance`
- **Purpose**: Maintenance operations
- **Options**:
  - `clear_cache`: Clear system cache
  - `reload_config`: Reload configuration
  - `view_logs`: Display recent logs
  - `health_check`: Run health check
- **Permissions**: Admin only

### `/admin info`
- **Purpose**: Display bot information and statistics
- **Permissions**: Admin only
- **Response**: Bot version, uptime, post statistics

## Configuration

### Environment Variables

```bash
# Discord Configuration
DISCORD_TOKEN=your_discord_token
DISCORD_GUILD_ID=your_guild_id
DISCORD_NEWS_CHANNEL_ID=your_news_channel_id

# Telegram Configuration  
TELEGRAM_API_ID=your_api_id
TELEGRAM_API_HASH=your_api_hash
TELEGRAM_PHONE_NUMBER=your_phone_number

# OpenAI Configuration
OPENAI_API_KEY=your_openai_api_key
OPENAI_MODEL=gpt-4-turbo-preview

# Bot Configuration
AUTO_POST_INTERVAL=180  # Minutes between posts
STARTUP_GRACE_PERIOD=2  # Minutes to wait after startup
```

### Configuration File (`config/unified_config.yaml`)

```yaml
bot:
  debug_mode: false
  auto_post_interval: 180
  startup_grace_period_minutes: 2

discord:
  guild_id: 123456789
  channels:
    news: 123456789
    logs: 123456789
    errors: 123456789

telegram:
  channels:
    - "channel_name_1"
    - "channel_name_2"

openai:
  model: "gpt-4-turbo-preview"
  max_tokens: 4000
  temperature: 0.3

automation:
  enabled: true
  require_media: false
  ai_translation: true
  ai_categorization: true
```

## Error Handling

### Error Types

- **`TelegramAuthError`**: Telegram authentication failures
- **`OpenAIAPIError`**: OpenAI API errors and rate limits
- **`DiscordConnectionError`**: Discord connection issues
- **`MediaDownloadError`**: Media download failures
- **`ConfigurationError`**: Configuration validation errors

### Error Recovery

The bot implements comprehensive error recovery:

1. **Automatic Retry**: Failed operations are retried with exponential backoff
2. **Graceful Degradation**: Services continue operating with reduced functionality
3. **Circuit Breaker**: Prevents cascade failures by temporarily disabling failing services
4. **Error Reporting**: Detailed error logging and Discord notifications

## Performance Optimization

### Caching Strategy

- **Translation Cache**: AI translations cached to reduce API calls
- **Media Cache**: Downloaded media cached temporarily
- **Configuration Cache**: Config values cached in memory
- **Blacklist Cache**: Message blacklist cached for duplicate prevention

### Resource Management

- **Memory Optimization**: Automatic garbage collection and memory monitoring
- **Connection Pooling**: Efficient connection reuse for APIs
- **Rate Limiting**: Built-in rate limiting for all external APIs
- **Background Tasks**: Non-blocking background processing

## Security Features

### Access Control

- **Role-Based Access**: Admin commands restricted by Discord roles
- **Permission Validation**: All commands validate user permissions
- **Secure Token Storage**: Sensitive tokens stored securely

### Content Safety

- **AI Safety Filter**: Content filtered for safety and appropriateness
- **Spam Prevention**: Duplicate content detection and prevention
- **Rate Limiting**: Protection against abuse and spam

## Deployment

### VPS Deployment

```bash
# Deploy to VPS
./vps-deployment/deploy_to_vps.sh

# Monitor status
./vps-deployment/check_bot_status.sh

# View logs
./vps-deployment/monitor_bot.sh
```

### Systemd Service

```ini
[Unit]
Description=NewsBot Discord Bot
After=network.target

[Service]
Type=simple
User=newsbot
WorkingDirectory=/home/newsbot/NewsBot
ExecStart=/home/newsbot/venv/bin/python run.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

## API Rate Limits

### Discord API
- **Message Posting**: 5 requests per 5 seconds per channel
- **Command Responses**: 50 requests per second globally

### Telegram API  
- **Message Fetching**: 30 requests per second
- **Media Download**: 20 concurrent downloads

### OpenAI API
- **GPT-4 Requests**: 500 requests per minute
- **Token Limits**: 40,000 tokens per minute

## Troubleshooting

### Common Issues

1. **Bot Not Responding**
   - Check Discord token validity
   - Verify bot permissions in Discord server
   - Check network connectivity

2. **Telegram Connection Failed**
   - Verify API credentials
   - Check phone number authentication
   - Ensure Telegram account has access to channels

3. **OpenAI API Errors**
   - Verify API key validity
   - Check account billing and limits
   - Monitor rate limit usage

4. **High Memory Usage**
   - Clear media cache: `/admin maintenance clear_cache`
   - Restart bot: `/admin emergency restart`
   - Check for memory leaks in logs

### Log Analysis

```bash
# View recent errors
tail -f logs/$(date +%Y-%m-%d).log | grep ERROR

# Monitor performance
tail -f logs/$(date +%Y-%m-%d).log | grep PERFORMANCE

# Check automation status
tail -f logs/$(date +%Y-%m-%d).log | grep AUTOMATION
```

## Support and Maintenance

### Health Monitoring

The bot includes comprehensive health monitoring:

- **System Health**: CPU, memory, disk usage monitoring
- **Service Health**: API connectivity and response times
- **Application Health**: Error rates and performance metrics
- **Automated Alerts**: Proactive notifications for issues

### Backup and Recovery

- **Automatic Backups**: Daily backups of configuration and data
- **Configuration Versioning**: Git-based configuration management
- **Disaster Recovery**: Automated recovery procedures for common failures

---

*Last updated: 2025-01-16*
*Version: 2.0.0* 