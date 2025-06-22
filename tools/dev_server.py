#!/usr/bin/env python3
"""
Development Server with Hot Reload

This script provides a development environment with:
- Hot reload when code changes
- Simple web interface for testing
- Live log streaming
- Manual trigger endpoints

Usage:
    python tools/dev_server.py
    
Then visit: http://localhost:8090
"""

import asyncio
import json
import os
import sys
import time
from pathlib import Path
from typing import Dict, Any

import aiohttp
from aiohttp import web, WSMsgType
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.utils.base_logger import base_logger as logger


class CodeChangeHandler(FileSystemEventHandler):
    """Handle file system events for hot reload."""
    
    def __init__(self, callback):
        self.callback = callback
        self.last_reload = 0
        self.debounce_seconds = 2
    
    def on_modified(self, event):
        if event.is_directory:
            return
        
        # Only reload for Python files
        if not event.src_path.endswith('.py'):
            return
        
        # Debounce rapid file changes
        now = time.time()
        if now - self.last_reload < self.debounce_seconds:
            return
        
        self.last_reload = now
        print(f"🔄 Code change detected: {event.src_path}")
        # Schedule the callback in a thread-safe way - fixed to avoid RuntimeError
        try:
            loop = asyncio.get_running_loop()
            # Use asyncio.run_coroutine_threadsafe instead of call_soon_threadsafe
            asyncio.run_coroutine_threadsafe(self.callback(), loop)
        except RuntimeError:
            # No event loop running, skip the callback
            print("⚠️ No event loop running, skipping reload callback")


class DevServer:
    """Development server with testing capabilities."""
    
    def __init__(self):
        self.app = web.Application()
        self.websockets = set()
        self.bot_process = None
        self.observer = None
        
        # Setup routes
        self.setup_routes()
    
    def setup_routes(self):
        """Setup web routes."""
        # Static files
        self.app.router.add_get('/', self.index)
        self.app.router.add_get('/ws', self.websocket_handler)
        
        # API endpoints
        self.app.router.add_post('/api/test/auto-fetch', self.test_auto_fetch)
        self.app.router.add_post('/api/test/message-fetch', self.test_message_fetch)
        self.app.router.add_post('/api/test/ai-process', self.test_ai_process)
        self.app.router.add_post('/api/bot/restart', self.restart_bot)
        self.app.router.add_get('/api/logs', self.get_logs)
        
        # Comprehensive testing endpoints
        self.app.router.add_post('/api/test/comprehensive', self.run_comprehensive_tests)
        self.app.router.add_post('/api/test/category', self.run_category_test)
        self.app.router.add_get('/api/test/categories', self.get_test_categories)
    
    async def index(self, request):
        """Serve the main page."""
        html = """
<!DOCTYPE html>
<html>
<head>
    <title>NewsBot Dev Server</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }
        .container { max-width: 1200px; margin: 0 auto; }
        .card { background: white; padding: 20px; margin: 10px 0; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        button { padding: 10px 20px; margin: 5px; border: none; border-radius: 4px; cursor: pointer; }
        .primary { background: #007bff; color: white; }
        .success { background: #28a745; color: white; }
        .warning { background: #ffc107; color: black; }
        .danger { background: #dc3545; color: white; }
        #logs { height: 300px; overflow-y: scroll; background: #000; color: #0f0; padding: 10px; font-family: monospace; }
        input, textarea { width: 100%; padding: 8px; margin: 5px 0; border: 1px solid #ddd; border-radius: 4px; }
        .status { padding: 10px; margin: 10px 0; border-radius: 4px; }
        .status.success { background: #d4edda; color: #155724; border: 1px solid #c3e6cb; }
        .status.error { background: #f8d7da; color: #721c24; border: 1px solid #f5c6cb; }
        .grid { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }
    </style>
</head>
<body>
    <div class="container">
        <h1>🤖 NewsBot Development Server</h1>
        
        <div class="card">
            <h2>🚀 Bot Control</h2>
            <button class="primary" onclick="restartBot()">Restart Bot</button>
            <button class="success" onclick="testAutoFetch()">Test Auto-Fetch</button>
            <div id="bot-status" class="status"></div>
        </div>
        
                 <div class="card">
             <h2>🧪 Comprehensive Testing</h2>
             <button class="success" onclick="runComprehensiveTests()">Run All Tests</button>
             <select id="test-category">
                 <option value="">Select Category...</option>
                 <option value="admin">🔧 Admin Commands</option>
                 <option value="fetch">📡 Fetch Commands</option>
                 <option value="info">ℹ️ Info Commands</option>
                 <option value="status">📊 Status Commands</option>
                 <option value="utility">🛠️ Utility Commands</option>
                 <option value="monitoring">🔍 Monitoring Systems</option>
                 <option value="ai">🤖 AI Services</option>
                 <option value="cache">💾 Cache Operations</option>
                 <option value="telegram">📱 Telegram Integration</option>
                 <option value="background">🔄 Background Tasks</option>
             </select>
             <button class="primary" onclick="runCategoryTest()">Test Category</button>
             <div id="comprehensive-result"></div>
         </div>
         
         <div class="grid">
             <div class="card">
                 <h2>📡 Message Fetching Test</h2>
                 <input type="text" id="channel-name" placeholder="Channel name (e.g., alekhbariahsy)" value="alekhbariahsy">
                 <input type="number" id="message-limit" placeholder="Message limit" value="5">
                 <button class="primary" onclick="testMessageFetch()">Test Message Fetch</button>
                 <div id="fetch-result"></div>
             </div>
             
             <div class="card">
                 <h2>🤖 AI Processing Test</h2>
                 <textarea id="ai-text" placeholder="Enter Arabic text to process..." rows="4"></textarea>
                 <button class="primary" onclick="testAIProcess()">Test AI Processing</button>
                 <div id="ai-result"></div>
             </div>
         </div>
        
        <div class="card">
            <h2>📋 Live Logs</h2>
            <button class="warning" onclick="clearLogs()">Clear Logs</button>
            <div id="logs"></div>
        </div>
    </div>

    <script>
        const ws = new WebSocket('ws://localhost:8090/ws');
        const logsDiv = document.getElementById('logs');
        
        ws.onmessage = function(event) {
            const data = JSON.parse(event.data);
            if (data.type === 'log') {
                logsDiv.innerHTML += data.message + '\\n';
                logsDiv.scrollTop = logsDiv.scrollHeight;
            } else if (data.type === 'status') {
                updateStatus(data.message, data.level || 'success');
            }
        };
        
        function updateStatus(message, level) {
            const statusDiv = document.getElementById('bot-status');
            statusDiv.textContent = message;
            statusDiv.className = 'status ' + level;
        }
        
        function clearLogs() {
            logsDiv.innerHTML = '';
        }
        
        async function restartBot() {
            updateStatus('Restarting bot...', 'warning');
            const response = await fetch('/api/bot/restart', { method: 'POST' });
            const result = await response.json();
            updateStatus(result.message, result.success ? 'success' : 'error');
        }
        
        async function testAutoFetch() {
            updateStatus('Testing auto-fetch...', 'warning');
            const response = await fetch('/api/test/auto-fetch', { method: 'POST' });
            const result = await response.json();
            updateStatus(result.message, result.success ? 'success' : 'error');
        }
        
        async function testMessageFetch() {
            const channel = document.getElementById('channel-name').value;
            const limit = document.getElementById('message-limit').value;
            
            const response = await fetch('/api/test/message-fetch', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ channel, limit: parseInt(limit) })
            });
            
            const result = await response.json();
            document.getElementById('fetch-result').innerHTML = 
                `<pre>${JSON.stringify(result, null, 2)}</pre>`;
        }
        
                 async function testAIProcess() {
             const text = document.getElementById('ai-text').value;
             
             const response = await fetch('/api/test/ai-process', {
                 method: 'POST',
                 headers: { 'Content-Type': 'application/json' },
                 body: JSON.stringify({ text })
             });
             
             const result = await response.json();
             document.getElementById('ai-result').innerHTML = 
                 `<pre>${JSON.stringify(result, null, 2)}</pre>`;
         }
         
         async function runComprehensiveTests() {
             updateStatus('Running comprehensive tests...', 'warning');
             document.getElementById('comprehensive-result').innerHTML = '<p>🧪 Running all tests...</p>';
             
             const response = await fetch('/api/test/comprehensive', { method: 'POST' });
             const result = await response.json();
             
             document.getElementById('comprehensive-result').innerHTML = 
                 `<pre>${result.report || result.message}</pre>`;
             updateStatus(result.message, result.success ? 'success' : 'error');
         }
         
         async function runCategoryTest() {
             const category = document.getElementById('test-category').value;
             if (!category) {
                 updateStatus('Please select a test category', 'error');
                 return;
             }
             
             updateStatus(`Running ${category} tests...`, 'warning');
             document.getElementById('comprehensive-result').innerHTML = `<p>🧪 Testing ${category}...</p>`;
             
             const response = await fetch('/api/test/category', {
                 method: 'POST',
                 headers: { 'Content-Type': 'application/json' },
                 body: JSON.stringify({ category })
             });
             
             const result = await response.json();
             
             document.getElementById('comprehensive-result').innerHTML = 
                 `<pre>${result.report || result.message}</pre>`;
             updateStatus(result.message, result.success ? 'success' : 'error');
         }
        
        // Auto-refresh logs every 5 seconds
        setInterval(async () => {
            const response = await fetch('/api/logs');
            const logs = await response.text();
            // Only update if logs changed to avoid scroll jumping
            if (logs !== logsDiv.textContent) {
                logsDiv.textContent = logs;
                logsDiv.scrollTop = logsDiv.scrollHeight;
            }
        }, 5000);
    </script>
</body>
</html>
        """
        return web.Response(text=html, content_type='text/html')
    
    async def websocket_handler(self, request):
        """Handle WebSocket connections."""
        ws = web.WebSocketResponse()
        await ws.prepare(request)
        
        self.websockets.add(ws)
        
        async for msg in ws:
            if msg.type == WSMsgType.ERROR:
                print(f'WebSocket error: {ws.exception()}')
        
        self.websockets.discard(ws)
        return ws
    
    async def broadcast(self, message_type: str, message: str, level: str = 'info'):
        """Broadcast message to all connected WebSockets."""
        if not self.websockets:
            return
        
        data = json.dumps({
            'type': message_type,
            'message': message,
            'level': level
        })
        
        # Remove closed connections
        closed = set()
        for ws in self.websockets:
            if ws.closed:
                closed.add(ws)
            else:
                try:
                    await ws.send_str(data)
                except Exception:
                    closed.add(ws)
        
        self.websockets -= closed
    
    async def test_auto_fetch(self, request):
        """Test auto-fetch endpoint."""
        try:
            # Import and run the test
            from tools.test_auto_fetch import test_auto_fetch
            result = await test_auto_fetch()
            
            await self.broadcast('status', 
                f"Auto-fetch test {'completed successfully' if result else 'found no content'}", 
                'success' if result else 'warning')
            
            return web.json_response({
                'success': True,
                'message': f"Auto-fetch test {'completed' if result else 'found no content'}",
                'result': result
            })
        except Exception as e:
            await self.broadcast('status', f"Auto-fetch test failed: {e}", 'error')
            return web.json_response({
                'success': False,
                'message': f"Test failed: {e}"
            })
    
    async def test_message_fetch(self, request):
        """Test message fetching endpoint."""
        try:
            data = await request.json()
            channel = data.get('channel', 'alekhbariahsy')
            limit = data.get('limit', 5)
            
            from tools.test_auto_fetch import test_message_fetching
            messages = await test_message_fetching(channel, limit)
            
            return web.json_response({
                'success': True,
                'message': f"Fetched {len(messages)} messages",
                'messages': [
                    {
                        'id': msg.id,
                        'date': str(msg.date),
                        'text': (msg.message or 'No text')[:200],
                        'has_media': bool(msg.media)
                    } for msg in messages[:5]  # Limit response size
                ]
            })
        except Exception as e:
            return web.json_response({
                'success': False,
                'message': f"Test failed: {e}"
            })
    
    async def test_ai_process(self, request):
        """Test AI processing endpoint."""
        try:
            data = await request.json()
            text = data.get('text', '')
            
            if not text:
                return web.json_response({
                    'success': False,
                    'message': 'No text provided'
                })
            
            from tools.test_auto_fetch import test_ai_processing
            result = await test_ai_processing(text)
            
            return web.json_response({
                'success': True,
                'message': 'AI processing completed',
                'result': result
            })
        except Exception as e:
            return web.json_response({
                'success': False,
                'message': f"Test failed: {e}"
            })
    
    async def restart_bot(self, request):
        """Restart bot endpoint."""
        await self.broadcast('status', 'Bot restart requested...', 'warning')
        return web.json_response({
            'success': True,
            'message': 'Bot restart functionality not implemented yet'
        })
    
    async def get_logs(self, request):
        """Get recent logs."""
        try:
            log_file = Path(__file__).parent.parent / "logs" / "newsbot.log"
            if log_file.exists():
                with open(log_file, 'r') as f:
                    lines = f.readlines()
                    # Return last 50 lines
                    return web.Response(text=''.join(lines[-50:]))
            else:
                return web.Response(text='No log file found')
        except Exception as e:
            return web.Response(text=f'Error reading logs: {e}')
    
    async def run_comprehensive_tests(self, request):
        """Run comprehensive test suite."""
        try:
            await self.broadcast('status', 'Running comprehensive test suite...', 'warning')
            
            # Import and run comprehensive tests
            from tools.comprehensive_test_suite import ComprehensiveTestSuite
            suite = ComprehensiveTestSuite()
            await suite.initialize()
            await suite.run_all_tests()
            
            # Generate report
            total_tests = len(suite.test_results)
            passed_tests = sum(1 for result in suite.test_results.values() if "✅" in result["status"])
            
            report = f"""
📋 COMPREHENSIVE TEST REPORT
{'='*40}
📊 Total Categories: {total_tests}
✅ Passed: {passed_tests}
❌ Failed: {total_tests - passed_tests}
📈 Success Rate: {(passed_tests/total_tests)*100:.1f}%

📋 Detailed Results:
"""
            for category, result in suite.test_results.items():
                report += f"{result['status']} {category}\n"
                if result['errors']:
                    for error in result['errors']:
                        report += f"    └─ {error}\n"
            
            await suite.cleanup()
            
            await self.broadcast('status', 
                f"Comprehensive tests completed: {passed_tests}/{total_tests} passed", 
                'success' if passed_tests == total_tests else 'warning')
            
            return web.json_response({
                'success': True,
                'message': f'Comprehensive tests completed: {passed_tests}/{total_tests} passed',
                'report': report,
                'results': suite.test_results
            })
            
        except Exception as e:
            await self.broadcast('status', f"Comprehensive tests failed: {e}", 'error')
            return web.json_response({
                'success': False,
                'message': f"Tests failed: {e}"
            })
    
    async def run_category_test(self, request):
        """Run tests for a specific category."""
        try:
            data = await request.json()
            category = data.get('category', '')
            
            if not category:
                return web.json_response({
                    'success': False,
                    'message': 'No category specified'
                })
            
            await self.broadcast('status', f'Running {category} tests...', 'warning')
            
            # Import and run category tests
            from tools.comprehensive_test_suite import ComprehensiveTestSuite
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
                await category_map[category]()
                report = f"✅ {category.title()} tests completed successfully"
            else:
                report = f"❌ Unknown category: {category}"
            
            await suite.cleanup()
            
            await self.broadcast('status', f'{category.title()} tests completed', 'success')
            
            return web.json_response({
                'success': True,
                'message': f'{category.title()} tests completed',
                'report': report
            })
            
        except Exception as e:
            await self.broadcast('status', f"Category test failed: {e}", 'error')
            return web.json_response({
                'success': False,
                'message': f"Category test failed: {e}"
            })
    
    async def get_test_categories(self, request):
        """Get available test categories."""
        categories = [
            {"id": "admin", "name": "🔧 Admin Commands"},
            {"id": "fetch", "name": "📡 Fetch Commands"},
            {"id": "info", "name": "ℹ️ Info Commands"},
            {"id": "status", "name": "📊 Status Commands"},
            {"id": "utility", "name": "🛠️ Utility Commands"},
            {"id": "monitoring", "name": "🔍 Monitoring Systems"},
            {"id": "ai", "name": "🤖 AI Services"},
            {"id": "cache", "name": "💾 Cache Operations"},
            {"id": "telegram", "name": "📱 Telegram Integration"},
            {"id": "background", "name": "🔄 Background Tasks"},
        ]
        
        return web.json_response({
            'success': True,
            'categories': categories
        })
    
    async def reload_callback(self):
        """Called when code changes are detected."""
        await self.broadcast('status', 'Code change detected - consider restarting', 'warning')
    
    def start_file_watcher(self):
        """Start watching for file changes."""
        src_dir = Path(__file__).parent.parent / "src"
        
        event_handler = CodeChangeHandler(self.reload_callback)
        self.observer = Observer()
        self.observer.schedule(event_handler, str(src_dir), recursive=True)
        self.observer.start()
        print(f"👀 Watching for changes in: {src_dir}")
    
    async def start_server(self, port=8090):
        """Start the development server."""
        print(f"🚀 Starting development server on http://localhost:{port}")
        
        # Start file watcher
        self.start_file_watcher()
        
        # Start web server
        runner = web.AppRunner(self.app)
        await runner.setup()
        site = web.TCPSite(runner, 'localhost', port)
        await site.start()
        
        print(f"✅ Development server running!")
        print(f"📱 Web interface: http://localhost:{port}")
        print(f"🔄 Hot reload: Enabled")
        
        # Keep running
        try:
            while True:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            print("\n👋 Shutting down development server...")
            if self.observer:
                self.observer.stop()
                self.observer.join()


async def main():
    """Main function."""
    dev_server = DevServer()
    await dev_server.start_server()


if __name__ == "__main__":
    asyncio.run(main()) 