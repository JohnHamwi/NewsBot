[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Discord.py 2.5+](https://img.shields.io/badge/discord.py-2.5+-blue.svg)](https://discordpy.readthedocs.io/)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Version](https://img.shields.io/badge/version-3.0.0-green.svg)](https://github.com/your-org/syrian-newsbot/releases)

# Syrian NewsBot v3.0 🤖📰

## Overview
A sophisticated Discord bot that aggregates Syrian news from Telegram channels, translates Arabic content to English using AI, and posts formatted news to Discord servers with intelligent categorization and location detection.

**Version 3.0** brings major stability improvements, comprehensive error handling, enhanced monitoring capabilities, and a completely refined codebase with zero known issues.

## ✨ What's New in v3.0

### 🛡️ **Enhanced Stability & Error Handling**
- **Zero Known Errors**: Complete elimination of attribute errors and null pointer exceptions
- **Robust Bot Readiness**: Comprehensive checks for all Discord operations
- **Error Recovery**: Advanced error recovery and graceful degradation
- **Fixed Timing Issues**: Resolved duplicate posting with proper interval timing
- **Clean Codebase**: Removed all TODO comments and deprecated code

### 📊 **Advanced Monitoring & Health Checks**
- **Real-time Metrics**: Performance metrics with health scoring system
- **Resource Monitoring**: CPU, memory, and system resource tracking
- **Background Task Health**: Comprehensive task lifecycle monitoring
- **Rich Presence**: Dynamic status with countdown timers and activity updates
- **Health Check API**: HTTP endpoint for external monitoring

### 🔧 **Improved Architecture**
- **Modern Discord.py 2.5+**: Full slash command implementation
- **Enhanced Task Management**: Proper background task lifecycle handling
- **Configuration Profiles**: Environment-based configuration management
- **Service Layer**: Clean separation of concerns with dedicated services
- **Defensive Programming**: Extensive use of hasattr() checks and null safety

### 🚀 **Performance Optimizations**
- **Media Download Progress**: Real-time progress tracking for large files
- **Enhanced Caching**: Improved JSON-based caching mechanisms
- **Memory Management**: Better resource utilization and cleanup
- **Rate Limiting**: Advanced rate limiting and flood protection
- **Circuit Breakers**: Fault tolerance for external service calls

## ✨ Features

### 🔄 **Real-time News Aggregation**
- Monitors multiple Telegram news channels simultaneously
- Intelligent content filtering and deduplication
- Round-robin posting for balanced channel coverage
- Configurable posting intervals (5 minutes to 24 hours)

### 🌐 **AI-Powered Translation**
- Arabic to English translation using OpenAI GPT
- Context-aware translation preserving news meaning
- Automatic Arabic title generation (3-6 words)
- Fallback vocabulary-based translation system

### 📍 **Syrian Location Intelligence**
- Detects 50+ Syrian cities, governorates, and regions
- Supports both Arabic and English location names
- Regional grouping and categorization
- Location-based content tagging

### 🏷️ **Smart Content Categorization**
- AI-powered news categorization system
- Categories: Breaking News, Military, Politics, Economy, Health, International, Social, Security
- Automatic forum tag assignment for Discord forums
- Content filtering and cleaning

### 🎨 **Rich Discord Integration**
- Modern Discord.py 2.5+ slash commands
- Forum channel support with automatic threading
- Rich embeds with media attachments
- Role-based access control (RBAC)
- Dynamic bot presence with countdown timers

### 🛡️ **Advanced Monitoring & Security**
- Comprehensive error handling and recovery
- Circuit breaker patterns for external services
- Rate limiting and flood protection
- Structured JSON logging with rotation
- Performance metrics and health monitoring

## 🚀 Quick Start

### Prerequisites

- **Python 3.11+** (recommended: 3.13)
- **Discord Bot Token** with necessary permissions
- **Telegram API Credentials** (optional, for news fetching)
- **OpenAI API Key** (optional, for AI translation)

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/your-org/syrian-newsbot.git
   cd syrian-newsbot
   ```

2. **Create virtual environment**
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment variables**
   ```bash
   cp .env.example .env
   # Edit .env with your credentials
   ```

5. **Run the bot**
   ```bash
   python run.py
   ```

## 📁 Project Architecture

```
NewsBot/
├── run.py                     # 🚀 Main entry point (13 lines)
├── requirements.txt           # 📦 Dependencies
├── pyproject.toml            # 🔧 Project configuration
├── README.md                 # 📖 This file
│
├── config/                   # ⚙️ Configuration
│   ├── config.yaml          # Main bot configuration
│   ├── config_profiles.yaml # Environment profiles
│   └── .env                 # Environment variables (secrets)
│
├── data/                    # 💾 Runtime data
│   ├── sessions/            # Telegram session files
│   ├── cache/               # Cache files
│   ├── botdata.json         # Bot data storage
│   └── last_uptime.txt      # Uptime tracking
│
├── src/                     # 📁 Source code
│   ├── bot/                 # 🤖 Main bot code
│   │   ├── main.py          # Bot entry point (13 lines)
│   │   ├── newsbot.py       # Core NewsBot class (441 lines)
│   │   └── background_tasks.py # Background tasks (416 lines)
│   │
│   ├── services/            # 🔧 Service layer
│   │   ├── media_service.py     # Media downloading (259 lines)
│   │   ├── ai_service.py        # AI translation (247 lines)
│   │   └── posting_service.py   # Discord posting (286 lines)
│   │
│   ├── cogs/                # 🔌 Discord command modules
│   │   ├── news.py          # News management (488 lines)
│   │   ├── info.py          # Bot information (381 lines)
│   │   ├── status.py        # System status (354 lines)
│   │   ├── fetch_cog.py     # News fetching (402 lines)
│   │   ├── fetch_view.py    # News posting UI (371 lines)
│   │   ├── reload.py        # Command reloading (203 lines)
│   │   ├── admin.py         # Admin commands (130 lines)
│   │   └── ai_utils.py      # AI utilities (205 lines)
│   │
│   ├── commands/            # 💬 Command implementations
│   │   └── config_commands.py # Configuration commands (340 lines)
│   │
│   ├── components/          # 🎨 UI components
│   │   ├── embeds/          # Discord embeds
│   │   │   └── base_embed.py    # Base embed class (357 lines)
│   │   └── decorators/      # Function decorators
│   │       └── admin_required.py # Admin authorization (176 lines)
│   │
│   ├── core/                # 🏗️ Core functionality
│   │   ├── config_manager.py    # Configuration management (244 lines)
│   │   ├── config_validator.py  # Configuration validation (273 lines)
│   │   ├── simple_config.py     # Simple config handling (373 lines)
│   │   ├── circuit_breaker.py   # Circuit breaker pattern (225 lines)
│   │   ├── telegram_utils.py    # Telegram utilities (50 lines)
│   │   └── rich_presence.py     # Discord presence (64 lines)
│   │
│   ├── utils/               # 🛠️ Utility functions
│   │   ├── config.py            # Config utilities (199 lines)
│   │   ├── logger.py            # Logging system (183 lines)
│   │   ├── structured_logger.py # Structured logging (102 lines)
│   │   ├── base_logger.py       # Base logging (88 lines)
│   │   ├── error_handler.py     # Error handling (241 lines)
│   │   ├── task_manager.py      # Task management (258 lines)
│   │   ├── rate_limiter.py      # Rate limiting (222 lines)
│   │   ├── telegram_client.py   # Telegram client (288 lines)
│   │   ├── logging_decorators.py # Logging decorators (256 lines)
│   │   └── text_utils.py        # Text processing (78 lines)
│   │
│   ├── cache/               # 💾 Caching implementations
│   │   └── redis_cache.py       # JSON-based cache (193 lines)
│   │
│   ├── monitoring/          # 📊 Monitoring and metrics
│   │   ├── metrics.py           # Metrics collection (166 lines)
│   │   ├── log_aggregator.py    # Log aggregation (389 lines)
│   │   └── log_api.py           # Log API endpoints (374 lines)
│   │
│   └── security/            # 🔒 Security features
│       └── rbac.py              # Role-based access control (287 lines)
│
├── tools/                   # 🔧 Development tools
│   ├── fix_telegram_auth.py     # Telegram authentication fixes
│   ├── check_env.py             # Environment validation
│   ├── check_fetch.py           # Fetch functionality testing
│   └── check_style.sh           # Code style checking
│
├── scripts/                 # 📜 Utility scripts
│   ├── check_dependencies.py    # Dependency checking
│   ├── test_telegram.py         # Telegram testing
│   ├── log_report.py            # Log reporting
│   ├── view_logs.py             # Log viewing
│   └── demo_logging.py          # Logging demonstration
│
├── docs/                    # 📚 Documentation
│   ├── phases/              # Project phase documentation
│   ├── api/                 # API documentation
│   ├── integration_guide.md # Integration guide
│   ├── configuration.md     # Configuration guide
│   └── *.md                 # Various documentation files
│
├── tests/                   # 🧪 Test files
└── logs/                    # 📝 Log files
```

## 🎮 Commands

### 📋 **Public Commands**
- `/info` - Show comprehensive bot information with sections
- `/help` - Display available commands and usage

### 👑 **Admin Commands**
- `/fetch` - Manually fetch posts from Telegram channels
- `/channel` - Manage Telegram channels (list/add/activate/deactivate)
- `/start` - Trigger immediate news post
- `/set_interval` - Configure auto-posting interval
- `/log` - View recent bot logs
- `/status` - Display comprehensive system status

## ⚙️ Configuration

### Environment Variables

Create a `.env` file in the project root:

```env
# Discord Configuration
DISCORD_TOKEN=your_discord_bot_token
GUILD_ID=your_discord_server_id
NEWS_CHANNEL_ID=your_news_channel_id
ERRORS_CHANNEL_ID=your_errors_channel_id
LOG_CHANNEL_ID=your_log_channel_id

# Admin Configuration
ADMIN_USER_ID=your_discord_user_id
ADMIN_ROLE_ID=your_admin_role_id
NEWS_ROLE_ID=your_news_role_id

# Telegram Configuration (Optional)
TELEGRAM_API_ID=your_telegram_api_id
TELEGRAM_API_HASH=your_telegram_api_hash
TELEGRAM_TOKEN=your_telegram_bot_token

# OpenAI Configuration (Optional)
OPENAI_API_KEY=your_openai_api_key

# Redis Configuration (Optional)
REDIS_URL=redis://localhost:6379
```

### Discord Permissions

Your bot needs the following permissions:
- `Send Messages`
- `Use Slash Commands`
- `Embed Links`
- `Attach Files`
- `Read Message History`
- `Create Public Threads` (for forum channels)
- `Manage Threads` (for forum channels)

## 🏗️ Architecture

### Modern Discord.py 2.5+ Design
```
NewsBot (discord.Client)
├── Command Tree (slash commands only)
├── Background Tasks (auto-posting, monitoring)
├── Core Systems
│   ├── JSON Cache (persistent data)
│   ├── RBAC Manager (security)
│   ├── Task Manager (background jobs)
│   └── Error Handler (recovery)
└── Services
    ├── Telegram Client (news fetching)
    ├── AI Service (translation)
    ├── Media Service (file handling)
    └── Posting Service (Discord output)
```

### Key Components

- **`src/bot/newsbot.py`** - Main bot class with modern Discord.py patterns
- **`src/cogs/`** - Command modules with setup functions
- **`src/services/`** - Core business logic services
- **`src/utils/`** - Utility modules and helpers
- **`src/core/`** - Configuration and system management
- **`src/cache/`** - Data persistence layer

## 🔧 Development

### Code Quality

This project uses modern Python development practices:

```bash
# Format code with Black
black src/ tests/ --line-length 88

# Sort imports with isort
isort src/ tests/ --profile black

# Type checking with mypy
mypy src/

# Run tests
pytest tests/ -v

# Lint with ruff
ruff check src/ tests/
```

### Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src tests/

# Run specific test file
pytest tests/test_syrian_features.py -v
```

### Project Structure

```
NewsBot/
├── src/                    # Source code
│   ├── bot/               # Bot core and main class
│   ├── cogs/              # Command modules
│   ├── services/          # Business logic services
│   ├── utils/             # Utility modules
│   ├── core/              # Configuration and system
│   ├── cache/             # Data persistence
│   ├── components/        # Reusable components
│   ├── monitoring/        # Metrics and logging
│   └── security/          # RBAC and security
├── tests/                 # Test suite
├── logs/                  # Log files
├── data/                  # Data storage
├── config/                # Configuration files
└── docs/                  # Documentation
```

## 📊 Monitoring

### Logging

The bot provides comprehensive logging:

- **Console Output** - Real-time status and errors
- **File Logging** - Rotating daily logs in `logs/`
- **Structured Logging** - JSON format for analysis
- **Error Tracking** - Detailed error context and recovery

### Metrics

Built-in monitoring includes:

- System resource usage (CPU, RAM)
- Command execution statistics
- Error rates and types
- Auto-posting success rates
- Telegram connection status

### Health Checks

- `/status` command provides comprehensive health information
- Background task monitoring
- Circuit breaker status
- Cache and database connectivity

## 🌍 Localization

### Syrian Location Support

The bot recognizes 50+ Syrian locations:

**Major Cities**: Damascus, Aleppo, Homs, Latakia, Tartus, Daraa, Deir ez-Zor, Raqqa, Idlib, Hasakah

**Governorates**: All 14 Syrian governorates with Arabic/English names

**Regional Grouping**: Capital, Northern, Northwestern, Northeastern, Eastern, Central, Coastal, Southern Syria

### Time Zone Support

- **Syrian Time (Asia/Damascus)** - All timestamps in local time
- **Daylight Saving Time** - Automatic DST handling
- **Relative Time** - "2 hours ago", "just now" formatting

## 🔒 Security

### Role-Based Access Control (RBAC)

- **Admin Role** - Full bot management access
- **News Role** - Mentioned in news posts
- **Permission System** - Granular command permissions

### Rate Limiting

- **Command Cooldowns** - Prevents spam and abuse
- **API Rate Limiting** - Respects Discord and Telegram limits
- **Error Rate Limiting** - Prevents error spam

### Data Protection

- **Environment Variables** - Sensitive data not in code
- **Secure Sessions** - Encrypted Telegram sessions
- **Input Validation** - All user inputs validated

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes following the code style
4. Add tests for new functionality
5. Run the test suite (`pytest`)
6. Format code (`black src/ tests/`)
7. Commit changes (`git commit -m 'Add amazing feature'`)
8. Push to branch (`git push origin feature/amazing-feature`)
9. Open a Pull Request

### Code Style

- **Black** formatting (88 character line length)
- **isort** import sorting
- **Type hints** for all functions
- **Comprehensive docstrings** (Google style)
- **Error handling** for all external calls

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- **Discord.py** - Modern Discord API wrapper
- **Telethon** - Telegram client library
- **OpenAI** - AI translation services
- **Syrian Community** - Feedback and testing

## 📞 Support

- **Issues** - [GitHub Issues](https://github.com/your-org/syrian-newsbot/issues)
- **Discussions** - [GitHub Discussions](https://github.com/your-org/syrian-newsbot/discussions)
- **Discord** - Join our support server

---

**Made with ❤️ by حَـــــنَّـــــا for the Syrian community** 