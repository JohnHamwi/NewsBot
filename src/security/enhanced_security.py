"""
Enhanced Security System for NewsBot
Provides comprehensive security features and input validation.
"""
import re
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set
from dataclasses import dataclass
from enum import Enum
import asyncio

import discord
from src.utils.base_logger import base_logger as logger


class ThreatLevel(Enum):
    """Security threat levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class SecurityEvent:
    """Security event data structure."""
    event_type: str
    threat_level: ThreatLevel
    user_id: Optional[int]
    description: str
    timestamp: datetime


class InputValidator:
    """Advanced input validation and sanitization."""
    
    DANGEROUS_PATTERNS = [
        r'<script.*?>.*?</script>',
        r'javascript:',
        r'data:text/html',
        r'eval\s*\(',
        r'document\.cookie',
        r'\.\./',
        r'\x00',
    ]
    
    @classmethod
    def validate_input(cls, input_text: str) -> tuple[bool, str]:
        """Validate and sanitize input text."""
        if not input_text:
            return True, ""
            
        # Check for dangerous patterns
        for pattern in cls.DANGEROUS_PATTERNS:
            if re.search(pattern, input_text, re.IGNORECASE):
                logger.warning(f"🚨 Dangerous pattern detected: {pattern}")
                return False, ""
                
        # Basic sanitization
        sanitized = cls._sanitize_input(input_text)
        return True, sanitized
        
    @classmethod
    def _sanitize_input(cls, text: str) -> str:
        """Basic input sanitization."""
        # Remove null bytes
        text = text.replace('\x00', '')
        
        # Limit excessive whitespace
        text = re.sub(r'\s{10,}', ' ', text)
        
        # Remove control characters
        text = ''.join(char for char in text if ord(char) >= 32 or char in '\n\t')
        
        return text.strip()


class SecurityManager:
    """Enhanced security management system."""
    
    def __init__(self):
        self.validator = InputValidator()
        self.security_events: List[SecurityEvent] = []
        self.blocked_users: Set[int] = set()
        self.user_requests: Dict[int, List[float]] = {}
        
        # Security configuration
        self.config = {
            'auto_block_threshold': 5,
            'block_duration_hours': 24,
            'rate_limit_per_minute': 30,
        }
        
    async def validate_command_input(self, interaction: discord.Interaction, **kwargs) -> bool:
        """Validate command input for security issues."""
        user_id = interaction.user.id
        
        # Check if user is blocked
        if user_id in self.blocked_users:
            await interaction.response.send_message(
                "❌ Access denied. Your account has been temporarily restricted.",
                ephemeral=True
            )
            return False
            
        # Rate limiting
        if self._is_rate_limited(user_id):
            await interaction.response.send_message(
                "⏱️ Rate limit exceeded. Please try again later.",
                ephemeral=True
            )
            return False
            
        # Validate input parameters
        for param_name, param_value in kwargs.items():
            if isinstance(param_value, str):
                is_safe, sanitized = self.validator.validate_input(param_value)
                if not is_safe:
                    await interaction.response.send_message(
                        "❌ Invalid input detected. Please check your input.",
                        ephemeral=True
                    )
                    self._record_security_event(
                        "malicious_input",
                        ThreatLevel.HIGH,
                        user_id,
                        f"Malicious input in {param_name}"
                    )
                    return False
                    
        return True
        
    def _is_rate_limited(self, user_id: int) -> bool:
        """Check if user is rate limited."""
        now = time.time()
        
        # Clean old requests
        if user_id in self.user_requests:
            self.user_requests[user_id] = [
                req for req in self.user_requests[user_id] 
                if now - req < 60
            ]
        else:
            self.user_requests[user_id] = []
            
        # Check rate limit
        if len(self.user_requests[user_id]) >= self.config['rate_limit_per_minute']:
            return True
            
        # Record request
        self.user_requests[user_id].append(now)
        return False
        
    def _record_security_event(self, event_type: str, threat_level: ThreatLevel, 
                              user_id: Optional[int], description: str):
        """Record a security event."""
        event = SecurityEvent(
            event_type=event_type,
            threat_level=threat_level,
            user_id=user_id,
            description=description,
            timestamp=datetime.now()
        )
        
        self.security_events.append(event)
        logger.warning(f"🚨 Security Event: {event_type} - {description}")
        
        # Check for auto-block
        if user_id and threat_level in [ThreatLevel.HIGH, ThreatLevel.CRITICAL]:
            self._check_auto_block(user_id)
            
    def _check_auto_block(self, user_id: int):
        """Check if user should be auto-blocked."""
        recent_events = [
            event for event in self.security_events
            if event.user_id == user_id and 
            event.timestamp > datetime.now() - timedelta(hours=1) and
            event.threat_level in [ThreatLevel.HIGH, ThreatLevel.CRITICAL]
        ]
        
        if len(recent_events) >= self.config['auto_block_threshold']:
            self.blocked_users.add(user_id)
            logger.critical(f"🚨 Auto-blocked user {user_id}")
            
            # Schedule unblock
            asyncio.create_task(self._schedule_unblock(user_id))
            
    async def _schedule_unblock(self, user_id: int):
        """Schedule automatic unblock."""
        await asyncio.sleep(self.config['block_duration_hours'] * 3600)
        if user_id in self.blocked_users:
            self.blocked_users.remove(user_id)
            logger.info(f"🔓 Auto-unblocked user {user_id}")
            
    def get_security_summary(self) -> Dict:
        """Get security summary."""
        now = datetime.now()
        recent_events = [
            e for e in self.security_events 
            if e.timestamp > now - timedelta(hours=24)
        ]
        
        return {
            'total_events_24h': len(recent_events),
            'blocked_users': len(self.blocked_users),
            'active_rate_limits': len(self.user_requests)
        } 