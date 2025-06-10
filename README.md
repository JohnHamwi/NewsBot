[![CI](https://github.com/JohnHamwi/NewsBot/actions/workflows/ci.yml/badge.svg)](https://github.com/JohnHamwi/NewsBot/actions/workflows/ci.yml)
[![Coverage Status](https://img.shields.io/badge/coverage-80%25-brightgreen)](https://github.com/JohnHamwi/NewsBot/actions)

# NewsBot 🤖📰

## Overview
NewsBot is a specialized Discord bot for aggregating, translating, and posting news from Telegram channels to a designated Discord server. It features automatic content curation, media handling, Arabic-to-English translation through AI integration, comprehensive system monitoring, and modern Discord UI components.

## ✨ Key Features
- 🔄 **Automatic News Aggregation** - Fetches news from configured Telegram channels
- 🌐 **AI-Powered Translation** - Arabic to English translation with OpenAI
- 📱 **Modern Discord UI** - Interactive dropdowns and embeds for better UX
- 📊 **Comprehensive Monitoring** - Real-time metrics and system health tracking
- 🎯 **Smart Content Filtering** - Avoids duplicate posts and filters content
- 🔒 **Role-Based Security** - Admin-only commands with proper authorization
- ⚡ **Service-Oriented Architecture** - Clean, maintainable codebase

## 🚀 Quick Start

### Prerequisites
- Python 3.9+
- Discord bot token
- Telegram API credentials
- OpenAI API key

### Installation
```bash
# Clone the repository
git clone https://github.com/YOUR_USERNAME/NewsBot.git
cd NewsBot

# Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment (see Configuration section)
cp config/.env.example config/.env  # Edit with your credentials

# Run the bot
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

### Public Commands
- `/info` - Show bot information and features

### Admin-Only Commands
- `/status [view] [details] [compact]` - Comprehensive bot status and metrics
- `/config <action>` - Configuration management with dropdown interface
- `/channel <action>` - **NEW!** Channel management with interactive dropdowns
  - **Activate**: Select from deactivated channels to enable
  - **Deactivate**: Select from active channels to disable
  - **List**: View all channels with their status
- `/reload` - Reload bot cogs and sync commands automatically
- `/fetch <channel>` - Fetch posts from specific Telegram channel
- `/set_debug_mode <on|off>` - Toggle debug mode
- `/set_rich_presence <mode>` - Set Discord presence mode
- `/set_interval <hours>` - Configure auto-posting interval
- `/start` - Trigger immediate news post
- `/log [lines] [level]` - View recent logs

## ⚙️ Configuration

### Environment Variables (config/.env)
```env
# Discord Configuration
DISCORD_TOKEN=your_discord_token
APPLICATION_ID=your_application_id
GUILD_ID=your_guild_id

# Channel IDs
NEWS_CHANNEL_ID=your_news_channel_id
ERRORS_CHANNEL_ID=your_errors_channel_id
LOG_CHANNEL_ID=your_log_channel_id
NEWS_ROLE_ID=your_news_role_id

# Admin Configuration
ADMIN_ROLE_ID=your_admin_role_id

# Telegram Configuration
TELEGRAM_API_ID=your_telegram_api_id
TELEGRAM_API_HASH=your_telegram_api_hash
TELEGRAM_BOT_TOKEN=your_telegram_bot_token

# OpenAI Configuration
OPENAI_API_KEY=your_openai_api_key

# Optional Configuration
DEBUG_MODE=false
LOG_LEVEL=INFO
```

## 🏗️ Architecture Highlights

### Service-Oriented Design
The bot follows a clean service-oriented architecture with proper separation of concerns:

- **MediaService**: Handles media downloading with timeouts and error handling
- **AIService**: Manages AI translation and title generation
- **PostingService**: Centralizes Discord posting logic with consistent formatting

### Modern Discord UI
- **Interactive Dropdowns**: Channel management uses dynamic dropdowns
- **Context-Aware Options**: Only shows relevant channels (active/inactive)
- **Multi-Selection Support**: Bulk operations for efficiency
- **Rich Embeds**: Beautiful, informative message formatting

### Robust Error Handling
- **Timeout Management**: Prevents hanging operations
- **Circuit Breaker Pattern**: Automatic failure recovery
- **Comprehensive Logging**: Structured logging with multiple levels
- **Graceful Degradation**: Partial success reporting

## 🔧 Development

### Code Quality
- **No files exceed 600 lines** - Excellent maintainability
- **Comprehensive error handling** throughout
- **Type hints** and documentation
- **Consistent code style** with pre-commit hooks

### Testing
```bash
# Run tests
pytest

# Run with coverage
pytest --cov=src

# Style checking
./tools/check_style.sh
```

### Project Phases
The project has undergone comprehensive refactoring:
- **Phase 1**: Eliminated 1,986-line monolithic system.py
- **Phase 2**: Split large files and created service layer
- **Current**: Clean, maintainable architecture with modern UI

## 📊 Monitoring

The bot includes comprehensive monitoring:
- **Real-time Metrics**: System performance and health
- **Log Aggregation**: Centralized logging with API access
- **Error Tracking**: Automatic error reporting and recovery
- **Uptime Monitoring**: Track bot availability and performance

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests and style checks
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- Discord.py community for excellent documentation
- OpenAI for AI translation capabilities
- Telegram API for news source integration 