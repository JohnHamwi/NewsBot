# 🇸🇾 NewsBot - Private Syrian Discord News Aggregator

**PROPRIETARY SOFTWARE - PRIVATE USE ONLY**

> Advanced news aggregation bot specifically designed for Syrian Discord communities. This is a private, closed-source project.

## 🔒 **CONFIDENTIAL PROJECT**

This NewsBot is a **proprietary system** developed exclusively for a private Syrian Discord server with 2,000+ members. 

**⚠️ IMPORTANT NOTICE:**
- This software is **NOT open source**
- **NO public distribution** is permitted
- **NO copying, modification, or redistribution** allowed
- For **AUTHORIZED USE ONLY** on designated Discord servers

---

## 🎯 **Project Overview**

NewsBot is a sophisticated Discord bot that aggregates news from multiple Telegram channels, translates Arabic content to English using AI, and posts formatted news updates to Discord servers.

### 🌟 **Key Features**

#### 📰 **News Intelligence**
- **Multi-channel aggregation** from 7+ Syrian news sources
- **AI-powered translation** (Arabic ↔ English)
- **Smart content filtering** with safety analysis
- **Duplicate detection** and quality assessment
- **Location detection** for Syrian cities and governorates

#### 🤖 **Advanced AI Integration**
- **Content safety analysis** with graphic content filtering
- **Sentiment analysis** and news categorization
- **Quality scoring** and posting priority calculation
- **Interactive filtering** with admin override buttons

#### ⚡ **Automation Features**
- **Intelligent auto-posting** with configurable intervals
- **Channel rotation** for balanced content distribution
- **Scheduled fetching** with advanced timing controls
- **Background processing** with health monitoring

#### 🛡️ **Security & Safety**
- **Content filtering** for graphic violence and disturbing material
- **Admin-only controls** with role-based access
- **Blacklist management** for channels and content
- **Interactive moderation** with Discord button controls

#### 📊 **Monitoring & Analytics**
- **Real-time health checks** with HTTP status endpoint
- **Performance metrics** and detailed logging
- **Command usage tracking** and error reporting
- **Comprehensive admin dashboard**

---

## 🏗️ **Technical Architecture**

### **Core Technologies**
- **Discord.py 2.5+** with slash commands
- **Telethon** for Telegram integration
- **OpenAI GPT** for translation and analysis
- **aiohttp** for web services
- **JSON-based caching** with Redis fallback

### **Modular Design**
```
📁 NewsBot/
├── 🤖 src/bot/          # Core bot functionality
├── ⚙️ src/cogs/         # Discord command modules
├── 🧠 src/services/     # AI and intelligence services
├── 💾 src/cache/        # Caching and data management
├── 📊 src/monitoring/   # Health checks and metrics
├── 🔧 src/utils/        # Utilities and helpers
└── 🛡️ src/security/    # Access control and safety
```

---

## ⚙️ **Configuration**

### **Required Environment Variables**
```bash
# Discord Configuration
DISCORD_TOKEN=your_discord_bot_token
DISCORD_GUILD_ID=your_server_id
DISCORD_NEWS_CHANNEL_ID=news_channel_id
DISCORD_LOG_CHANNEL_ID=log_channel_id

# Telegram Configuration  
TELEGRAM_API_ID=your_api_id
TELEGRAM_API_HASH=your_api_hash
TELEGRAM_BOT_TOKEN=your_telegram_bot_token

# AI Services
OPENAI_API_KEY=your_openai_key

# Admin Configuration
ADMIN_USER_ID=your_discord_user_id
```

### **News Sources**
The bot aggregates from multiple verified Syrian news channels:
- 📡 alekhbariahsy (الإخبارية السورية)
- 📡 alhourya_news (الحرية نيوز)
- 📡 alktroone (الكترونية)
- 📡 syrianews24 (سوريا نيوز 24)
- 📡 damascusnow (دمشق الآن)
- 📡 And additional verified sources...

---

## 🚀 **Deployment**

### **Docker Deployment** (Recommended)
```bash
# Build and run with Docker Compose
docker-compose up -d

# View logs
docker-compose logs -f newsbot
```

### **Manual Deployment**
```bash
# Install dependencies
pip install -r requirements.txt

# Run the bot
python run.py
```

---

## 📋 **Admin Commands**

### **News Management**
- `/admin post` - Manual posting controls
- `/admin channels` - Manage Telegram channels  
- `/admin autopost` - Configure automatic posting

### **System Operations**
- `/admin logs` - View system logs
- `/admin system` - System operations and health checks
- `/admin sync` - Sync Discord commands

### **Content Filtering**
- `/admin test_filter` - Test content safety filtering
- Interactive buttons for filtered content management

---

## 📊 **Monitoring & Health**

### **Health Check Endpoint**
```
GET http://localhost:8080/health
```

### **Performance Metrics**
- Real-time command execution tracking
- Memory and CPU usage monitoring
- Error rate and success metrics
- Channel activity statistics

---

## 🔧 **Maintenance**

### **Log Management**
- Automatic daily log rotation
- 30-day log retention
- Structured JSON logging
- Error aggregation and reporting

### **Cache Management**
- Automatic cache optimization
- Blacklist management
- Channel rotation state
- Performance data persistence

---

## 🛡️ **Security Notice**

This NewsBot system includes advanced security features:

- **Content Safety Filtering**: Automatically detects and filters graphic content
- **Admin-Only Access**: All management commands require admin privileges  
- **Secure Token Management**: All API keys and tokens are environment-based
- **Rate Limiting**: Built-in protection against API abuse
- **Audit Logging**: Comprehensive logging of all admin actions

---

## 📞 **Support & Contact**

This is a **private, proprietary system**. 

**For authorized users only:**
- Internal Discord support channel
- Direct admin contact: **Trippixn** (Discord)
- Emergency contact for critical problems

**⚠️ NO PUBLIC SUPPORT** - This software is not publicly distributed.

---

## 📄 **Legal Notice**

```
PROPRIETARY SOFTWARE - ALL RIGHTS RESERVED

This NewsBot system is proprietary software developed for 
private use. Unauthorized copying, distribution, or use 
is strictly prohibited and may result in legal action.

Copyright (c) 2025 NewsBot Project
```

---

**🇸🇾 Proudly serving the Syrian Discord community with reliable, intelligent news aggregation.** 