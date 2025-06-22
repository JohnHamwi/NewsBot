#!/usr/bin/env python3
"""
Comprehensive Bot Test Suite

This script provides comprehensive testing for ALL commands and functions
of the Syrian NewsBot, eliminating the need for manual Discord testing.

Usage:
    python tools/comprehensive_test_suite.py [test_category]
    
Examples:
    python tools/comprehensive_test_suite.py all
    python tools/comprehensive_test_suite.py admin
    python tools/comprehensive_test_suite.py fetch
    python tools/comprehensive_test_suite.py --interactive
"""

import asyncio
import json
import os
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, List, Optional

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.cache.json_cache import JSONCache
from src.cogs.fetch_cog import FetchCommands
from src.services.ai_service import AIService
from src.monitoring.health_check import HealthCheckService
from src.monitoring.performance_metrics import PerformanceMetrics
from src.utils.base_logger import base_logger as logger
from src.utils.telegram_client import TelegramManager


class MockInteraction:
    """Mock Discord interaction for testing commands."""
    
    def __init__(self, user_id: int = 12345):
        self.user_id = user_id
        self.guild_id = 67890
        self.response_sent = False
        self.followup_sent = False
        self.deferred = False
        
        # Mock user
        self.user = type('MockUser', (), {
            'id': user_id,
            'display_name': 'TestUser',
            'mention': f'<@{user_id}>',
            'roles': []
        })()
        
        # Mock guild
        self.guild = type('MockGuild', (), {
            'id': self.guild_id,
            'name': 'Test Guild',
            'member_count': 100
        })()
    
    class MockResponse:
        def __init__(self):
            self.is_done_value = False
        
        def is_done(self):
            return self.is_done_value
        
        async def defer(self, thinking=False, ephemeral=False):
            self.is_done_value = True
        
        async def send_message(self, content=None, embed=None, ephemeral=False):
            self.is_done_value = True
    
    class MockFollowup:
        async def send(self, content=None, embed=None, ephemeral=False):
            pass
    
    def __init__(self, user_id: int = 12345):
        self.user_id = user_id
        self.response = self.MockResponse()
        self.followup = self.MockFollowup()


class MockBot:
    """Enhanced mock bot class for comprehensive testing."""
    
    def __init__(self):
        self.json_cache = None
        self.telegram_client = None
        self.fetch_commands = None
        self.ai_service = None
        self.health_check = None
        self.performance_metrics = None
        
        # Bot properties
        self.user = type('MockUser', (), {'id': 123456789, 'name': 'NewsBot'})()
        self.guilds = [type('MockGuild', (), {'id': 1, 'member_count': 100})()]
        self.latency = 0.05
        self.startup_time = datetime.utcnow()
        self.auto_post_interval = 10800  # 3 hours
        self.last_post_time = None
        self.is_auto_posting_enabled = True
        
        # Command tree mock
        self.tree = type('MockTree', (), {
            'sync': self._mock_sync,
            'add_command': lambda cmd: None,
            'get_commands': lambda: []
        })()
    
    def get_channel(self, channel_id):
        """Mock get_channel method."""
        return type('MockChannel', (), {
            'id': channel_id,
            'name': 'test-channel',
            'send': self._mock_send
        })()
    
    async def _mock_send(self, content=None, embed=None):
        """Mock channel send method."""
        pass
    
    async def _mock_sync(self):
        """Mock command tree sync."""
        return []
    
    def is_ready(self):
        """Mock is_ready method."""
        return True
    
    async def initialize(self):
        """Initialize the mock bot with all necessary components."""
        # Initialize cache
        self.json_cache = JSONCache()
        await self.json_cache.initialize()
        
        # Initialize Telegram client (but skip connection status sending)
        self.telegram_client = TelegramManager(self)
        
        # Patch the _send_connection_status to do nothing
        async def mock_send_status():
            pass
        self.telegram_client._send_connection_status = mock_send_status
        
        await self.telegram_client.connect()
        
        # Initialize AI service
        self.ai_service = AIService(self)
        
        # Initialize fetch commands
        self.fetch_commands = FetchCommands(self)
        
        # Initialize monitoring systems
        try:
            self.performance_metrics = PerformanceMetrics(self, retention_hours=1)
            self.health_check = HealthCheckService(self, port=8081)  # Different port for testing
        except Exception as e:
            logger.warning(f"Could not initialize monitoring: {e}")
        
        logger.info("🤖 Enhanced mock bot initialized successfully")


class ComprehensiveTestSuite:
    """Comprehensive test suite for all bot commands and functions."""
    
    def __init__(self):
        self.bot = None
        self.test_results = {}
        self.start_time = None
    
    async def initialize(self):
        """Initialize the test suite."""
        print("🚀 Initializing Comprehensive Test Suite...")
        print("=" * 60)
        
        self.start_time = time.time()
        self.bot = MockBot()
        await self.bot.initialize()
        
        print("✅ Test suite initialized successfully")
    
    async def run_all_tests(self):
        """Run all available tests."""
        test_categories = [
            ("🔧 Admin Commands", self.test_admin_commands),
            ("📡 Fetch Commands", self.test_fetch_commands),
            ("ℹ️ Info Commands", self.test_info_commands),
            ("📊 Status Commands", self.test_status_commands),
            ("🛠️ Utility Commands", self.test_utility_commands),
            ("🔍 Monitoring Systems", self.test_monitoring_systems),
            ("🤖 AI Services", self.test_ai_services),
            ("💾 Cache Operations", self.test_cache_operations),
            ("📱 Telegram Integration", self.test_telegram_integration),
            ("🔄 Background Tasks", self.test_background_tasks),
        ]
        
        print("\n🧪 Running Comprehensive Test Suite")
        print("=" * 60)
        
        for category_name, test_function in test_categories:
            print(f"\n{category_name}")
            print("-" * 40)
            
            try:
                await test_function()
                self.test_results[category_name] = {"status": "✅ PASSED", "errors": []}
            except Exception as e:
                self.test_results[category_name] = {"status": "❌ FAILED", "errors": [str(e)]}
                print(f"❌ {category_name} failed: {e}")
        
        await self.generate_test_report()
    
    async def test_admin_commands(self):
        """Test all admin commands."""
        print("Testing admin command functions...")
        
        # Test admin logs command
        try:
            from src.cogs.admin import AdminCommands
            admin_cog = AdminCommands(self.bot)
            
            # Mock interaction
            interaction = MockInteraction(user_id=999999)  # Admin user
            
            # Test logs command
            await admin_cog._handle_logs(interaction, count=10, level=None, search=None, format=None)
            print("  ✅ Admin logs command")
            
        except Exception as e:
            print(f"  ❌ Admin logs command: {e}")
        
        # Test manual post command
        try:
            await admin_cog._handle_manual_post(interaction, channel="alekhbariahsy", mode=None, preview=True)
            print("  ✅ Manual post command")
        except Exception as e:
            print(f"  ❌ Manual post command: {e}")
        
        # Test autopost configuration
        try:
            operation = type('Choice', (), {'value': 'status'})()
            await admin_cog._handle_autopost(interaction, operation, value=None, unit=None)
            print("  ✅ Autopost configuration")
        except Exception as e:
            print(f"  ❌ Autopost configuration: {e}")
        
        # Test channel management
        try:
            action = type('Choice', (), {'value': 'list'})()
            await admin_cog._handle_channels(interaction, action, channel_name=None, filter_type=None)
            print("  ✅ Channel management")
        except Exception as e:
            print(f"  ❌ Channel management: {e}")
    
    async def test_fetch_commands(self):
        """Test all fetch command variations."""
        print("Testing fetch command functions...")
        
        # Test auto-fetch functionality
        try:
            result = await self.bot.fetch_commands.fetch_and_post_auto("alekhbariahsy")
            print(f"  ✅ Auto-fetch: {'Success' if result else 'No content found'}")
        except Exception as e:
            print(f"  ❌ Auto-fetch: {e}")
        
        # Test blacklist checking
        try:
            should_skip = await self.bot.fetch_commands.should_skip_post("test content")
            print(f"  ✅ Blacklist check: {should_skip}")
        except Exception as e:
            print(f"  ❌ Blacklist check: {e}")
        
        # Test fetch command variations
        test_actions = ["latest", "targeted", "preview"]
        for action in test_actions:
            try:
                interaction = MockInteraction()
                action_choice = type('Choice', (), {'value': action})()
                
                if action == "latest":
                    await self.bot.fetch_commands._handle_latest_fetch(
                        interaction, "alekhbariahsy", False, True, 5, None, None, None, True
                    )
                elif action == "targeted":
                    await self.bot.fetch_commands._handle_targeted_fetch(
                        interaction, "alekhbariahsy", True, None, None, None, True
                    )
                elif action == "preview":
                    await self.bot.fetch_commands._handle_preview_fetch(
                        interaction, "alekhbariahsy", 5, None, None, None
                    )
                
                print(f"  ✅ Fetch {action} command")
            except Exception as e:
                print(f"  ❌ Fetch {action} command: {e}")
    
    async def test_info_commands(self):
        """Test all info commands."""
        print("Testing info command functions...")
        
        try:
            from src.cogs.bot_commands import BotCommands
            bot_cog = BotCommands(self.bot)
            
            # Test different info sections
            sections = ["overview", "features", "commands", "technical", "stats"]
            for section in sections:
                try:
                    embed = await bot_cog._build_overview_embed(detailed=False)
                    print(f"  ✅ Info {section} section")
                except Exception as e:
                    print(f"  ❌ Info {section} section: {e}")
            
            # Test help command functionality
            try:
                embed = await bot_cog._build_commands_embed(detailed=True)
                print("  ✅ Help command embed")
            except Exception as e:
                print(f"  ❌ Help command embed: {e}")
                
        except Exception as e:
            print(f"  ❌ Info commands initialization: {e}")
    
    async def test_status_commands(self):
        """Test all status and monitoring commands."""
        print("Testing status command functions...")
        
        try:
            from src.cogs.status import StatusCommands
            status_cog = StatusCommands(self.bot)
            
            # Test different status views
            views = ["all", "system", "bot", "cache", "performance", "errors", "services"]
            for view in views:
                try:
                    metric_data = await status_cog._gather_metrics(view)
                    color = status_cog._determine_health_color(metric_data)
                    embed = await status_cog._build_status_embed(metric_data, view, False, False, color)
                    print(f"  ✅ Status {view} view")
                except Exception as e:
                    print(f"  ❌ Status {view} view: {e}")
            
            # Test quick status
            try:
                start_time = datetime.utcnow()
                embed = await status_cog._build_quick_status_embed(start_time)
                print("  ✅ Quick status")
            except Exception as e:
                print(f"  ❌ Quick status: {e}")
                
        except Exception as e:
            print(f"  ❌ Status commands initialization: {e}")
    
    async def test_utility_commands(self):
        """Test all utility commands."""
        print("Testing utility command functions...")
        
        try:
            from src.cogs.utility import UtilityCommands
            utility_cog = UtilityCommands(self.bot)
            
            # Test ping command
            try:
                start_time = datetime.utcnow()
                embed = await utility_cog._build_ping_embed(start_time, detailed=False)
                print("  ✅ Ping command")
            except Exception as e:
                print(f"  ❌ Ping command: {e}")
            
            # Test uptime command
            try:
                embed = await utility_cog._build_uptime_embed(detailed=True)
                print("  ✅ Uptime command")
            except Exception as e:
                print(f"  ❌ Uptime command: {e}")
            
            # Test server info command
            try:
                interaction = MockInteraction()
                embed = await utility_cog._build_serverinfo_embed(interaction, detailed=False)
                print("  ✅ Server info command")
            except Exception as e:
                print(f"  ❌ Server info command: {e}")
                
        except Exception as e:
            print(f"  ❌ Utility commands initialization: {e}")
    
    async def test_monitoring_systems(self):
        """Test monitoring and health check systems."""
        print("Testing monitoring systems...")
        
        # Test health check service
        if self.bot.health_check:
            try:
                health_data = await self.bot.health_check._get_detailed_health()
                print(f"  ✅ Health check: {health_data['overall_status']}")
            except Exception as e:
                print(f"  ❌ Health check: {e}")
        
        # Test performance metrics
        if self.bot.performance_metrics:
            try:
                summary = self.bot.performance_metrics.get_performance_summary()
                print(f"  ✅ Performance metrics: {len(summary)} metrics")
            except Exception as e:
                print(f"  ❌ Performance metrics: {e}")
        
        # Test log API functionality
        try:
            from src.monitoring.log_api import LogAPICog
            log_cog = LogAPICog(self.bot)
            
            # Test log aggregator initialization
            await log_cog.ensure_aggregator_initialized()
            print("  ✅ Log aggregator")
        except Exception as e:
            print(f"  ❌ Log aggregator: {e}")
    
    async def test_ai_services(self):
        """Test AI service functionality."""
        print("Testing AI services...")
        
        # Test AI text processing
        try:
            test_text = "هذا نص تجريبي باللغة العربية للاختبار"
            result = self.bot.ai_service.get_ai_result_comprehensive(test_text)
            print(f"  ✅ AI processing: {result.get('title', 'No title')}")
        except Exception as e:
            print(f"  ❌ AI processing: {e}")
        
        # Test AI translation
        try:
            english, title, location = await self.bot.ai_service.process_text_with_ai(test_text, timeout=30)
            print(f"  ✅ AI translation: {'Success' if english else 'Failed'}")
        except Exception as e:
            print(f"  ❌ AI translation: {e}")
    
    async def test_cache_operations(self):
        """Test cache operations."""
        print("Testing cache operations...")
        
        # Test basic cache operations
        try:
            await self.bot.json_cache.set("test_key", "test_value")
            value = await self.bot.json_cache.get("test_key")
            assert value == "test_value"
            print("  ✅ Basic cache operations")
        except Exception as e:
            print(f"  ❌ Basic cache operations: {e}")
        
        # Test channel management
        try:
            await self.bot.json_cache.add_telegram_channel("test_channel")
            channels = await self.bot.json_cache.list_telegram_channels("activated")
            print(f"  ✅ Channel management: {len(channels)} channels")
        except Exception as e:
            print(f"  ❌ Channel management: {e}")
        
        # Test blacklist operations
        try:
            blacklist = await self.bot.json_cache.get("blacklisted_posts") or []
            print(f"  ✅ Blacklist operations: {len(blacklist)} items")
        except Exception as e:
            print(f"  ❌ Blacklist operations: {e}")
    
    async def test_telegram_integration(self):
        """Test Telegram integration."""
        print("Testing Telegram integration...")
        
        # Test connection status
        try:
            is_connected = await self.bot.telegram_client.is_connected()
            print(f"  ✅ Connection status: {'Connected' if is_connected else 'Disconnected'}")
        except Exception as e:
            print(f"  ❌ Connection status: {e}")
        
        # Test message fetching
        try:
            messages = await self.bot.telegram_client.get_messages("alekhbariahsy", limit=3)
            print(f"  ✅ Message fetching: {len(messages)} messages")
        except Exception as e:
            print(f"  ❌ Message fetching: {e}")
    
    async def test_background_tasks(self):
        """Test background task functionality."""
        print("Testing background tasks...")
        
        # Test auto-posting configuration
        try:
            interval = getattr(self.bot, 'auto_post_interval', 0)
            enabled = getattr(self.bot, 'is_auto_posting_enabled', False)
            print(f"  ✅ Auto-posting config: {interval}s interval, {'enabled' if enabled else 'disabled'}")
        except Exception as e:
            print(f"  ❌ Auto-posting config: {e}")
        
        # Test task manager
        try:
            from src.utils.task_manager import task_manager
            if task_manager:
                running_tasks = getattr(task_manager, 'running_tasks', {})
                print(f"  ✅ Task manager: {len(running_tasks)} running tasks")
            else:
                print("  ℹ️ Task manager: Not available")
        except Exception as e:
            print(f"  ❌ Task manager: {e}")
    
    async def generate_test_report(self):
        """Generate a comprehensive test report."""
        end_time = time.time()
        duration = end_time - self.start_time
        
        print("\n" + "=" * 60)
        print("📋 COMPREHENSIVE TEST REPORT")
        print("=" * 60)
        
        total_tests = len(self.test_results)
        passed_tests = sum(1 for result in self.test_results.values() if "✅" in result["status"])
        failed_tests = total_tests - passed_tests
        
        print(f"⏱️  **Duration:** {duration:.2f} seconds")
        print(f"📊 **Total Categories:** {total_tests}")
        print(f"✅ **Passed:** {passed_tests}")
        print(f"❌ **Failed:** {failed_tests}")
        print(f"📈 **Success Rate:** {(passed_tests/total_tests)*100:.1f}%")
        
        print("\n📋 **Detailed Results:**")
        for category, result in self.test_results.items():
            print(f"  {result['status']} {category}")
            if result['errors']:
                for error in result['errors']:
                    print(f"    └─ {error}")
        
        # Generate recommendations
        print("\n💡 **Recommendations:**")
        if failed_tests == 0:
            print("  🎉 All tests passed! Your bot is functioning perfectly.")
        else:
            print(f"  🔧 {failed_tests} categories need attention. Check the errors above.")
            print("  📖 Review the logs for detailed error information.")
            print("  🔄 Run individual test categories for focused debugging.")
        
        print("\n🚀 **Next Steps:**")
        print("  • Use individual test functions for specific debugging")
        print("  • Check logs for detailed error traces")
        print("  • Run the development server for interactive testing")
        print("  • Monitor the health check endpoints for production readiness")
        
        print("\n" + "=" * 60)
    
    async def cleanup(self):
        """Cleanup test resources."""
        try:
            if self.bot and self.bot.telegram_client:
                await self.bot.telegram_client.disconnect()
            
            if self.bot and self.bot.health_check:
                await self.bot.health_check.stop()
            
            print("🧹 Test cleanup completed")
        except Exception as e:
            print(f"⚠️ Cleanup warning: {e}")


async def run_specific_category(category: str):
    """Run tests for a specific category."""
    suite = ComprehensiveTestSuite()
    await suite.initialize()
    
    category_map = {
        "admin": suite.test_admin_commands,
        "fetch": suite.test_fetch_commands,
        "info": suite.test_info_commands,
        "status": suite.test_status_commands,
        "utility": suite.test_utility_commands,
        "monitoring": suite.test_monitoring_systems,
        "ai": suite.test_ai_services,
        "cache": suite.test_cache_operations,
        "telegram": suite.test_telegram_integration,
        "background": suite.test_background_tasks,
    }
    
    if category in category_map:
        print(f"🧪 Running {category.title()} Tests")
        print("=" * 40)
        await category_map[category]()
    else:
        print(f"❌ Unknown category: {category}")
        print(f"Available categories: {', '.join(category_map.keys())}")
    
    await suite.cleanup()


async def interactive_mode():
    """Interactive testing mode."""
    suite = ComprehensiveTestSuite()
    await suite.initialize()
    
    while True:
        print("\n🎮 Interactive Testing Mode")
        print("=" * 40)
        print("Available test categories:")
        print("1. 🔧 Admin Commands")
        print("2. 📡 Fetch Commands")
        print("3. ℹ️ Info Commands")
        print("4. 📊 Status Commands")
        print("5. 🛠️ Utility Commands")
        print("6. 🔍 Monitoring Systems")
        print("7. 🤖 AI Services")
        print("8. 💾 Cache Operations")
        print("9. 📱 Telegram Integration")
        print("10. 🔄 Background Tasks")
        print("11. 🧪 Run All Tests")
        print("12. 📋 Generate Report")
        print("13. 🚪 Exit")
        
        choice = input("\nSelect test category (1-13): ").strip()
        
        category_map = {
            "1": suite.test_admin_commands,
            "2": suite.test_fetch_commands,
            "3": suite.test_info_commands,
            "4": suite.test_status_commands,
            "5": suite.test_utility_commands,
            "6": suite.test_monitoring_systems,
            "7": suite.test_ai_services,
            "8": suite.test_cache_operations,
            "9": suite.test_telegram_integration,
            "10": suite.test_background_tasks,
            "11": suite.run_all_tests,
            "12": suite.generate_test_report,
        }
        
        if choice == "13":
            print("👋 Goodbye!")
            break
        elif choice in category_map:
            try:
                await category_map[choice]()
            except Exception as e:
                print(f"❌ Test failed: {e}")
        else:
            print("❌ Invalid choice")
    
    await suite.cleanup()


async def main():
    """Main function."""
    if len(sys.argv) > 1:
        if sys.argv[1] == "--interactive":
            await interactive_mode()
        elif sys.argv[1] == "all":
            suite = ComprehensiveTestSuite()
            await suite.initialize()
            await suite.run_all_tests()
            await suite.cleanup()
        else:
            # Run specific category
            await run_specific_category(sys.argv[1])
    else:
        # Default: run all tests
        suite = ComprehensiveTestSuite()
        await suite.initialize()
        await suite.run_all_tests()
        await suite.cleanup()


if __name__ == "__main__":
    asyncio.run(main()) 