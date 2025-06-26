"""
Enhanced Security Management System for NewsBot
Provides comprehensive security features, input validation, and threat protection.
"""
import hashlib
import hmac
import secrets
import time
import re
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Set
from dataclasses import dataclass
from enum import Enum
from functools import wraps
import asyncio

import discord
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import base64

from src.utils.base_logger import base_logger as logger
from src.cache.json_cache import JSONCache


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
    metadata: Dict[str, Any]


class InputValidator:
    """Advanced input validation and sanitization."""
    
    # Dangerous patterns to detect
    DANGEROUS_PATTERNS = [
        r'<script.*?>.*?</script>',  # XSS attempts
        r'javascript:',              # JavaScript injection
        r'data:text/html',          # Data URI attacks
        r'vbscript:',               # VBScript injection
        r'onload\s*=',              # Event handler injection
        r'onerror\s*=',             # Error handler injection
        r'eval\s*\(',               # Eval injection
        r'document\.cookie',        # Cookie theft
        r'window\.location',        # Redirect attacks
        r'\.\./',                   # Path traversal
        r'\x00',                    # Null byte injection
    ]
    
    # SQL injection patterns
    SQL_INJECTION_PATTERNS = [
        r'union\s+select',
        r'drop\s+table',
        r'delete\s+from',
        r'insert\s+into',
        r'update\s+.*\s+set',
        r'exec\s*\(',
        r'sp_executesql',
        r'xp_cmdshell',
    ]
    
    # Command injection patterns
    COMMAND_INJECTION_PATTERNS = [
        r';\s*rm\s+-rf',
        r';\s*cat\s+/etc/passwd',
        r';\s*wget\s+',
        r';\s*curl\s+',
        r'`.*`',                    # Backtick execution
        r'\$\(.*\)',               # Command substitution
        r'>\s*/dev/null',          # Output redirection
    ]
    
    @classmethod
    def validate_input(cls, input_text: str, input_type: str = "general") -> tuple[bool, str]:
        """
        Validate and sanitize input text.
        
        Args:
            input_text: Text to validate
            input_type: Type of input (general, url, filename, etc.)
            
        Returns:
            Tuple of (is_safe, sanitized_text)
        """
        if not input_text:
            return True, ""
            
        # Check for dangerous patterns
        for pattern in cls.DANGEROUS_PATTERNS:
            if re.search(pattern, input_text, re.IGNORECASE):
                logger.warning(f"🚨 Dangerous pattern detected: {pattern}")
                return False, ""
                
        # Check for SQL injection
        for pattern in cls.SQL_INJECTION_PATTERNS:
            if re.search(pattern, input_text, re.IGNORECASE):
                logger.warning(f"🚨 SQL injection attempt detected: {pattern}")
                return False, ""
                
        # Check for command injection
        for pattern in cls.COMMAND_INJECTION_PATTERNS:
            if re.search(pattern, input_text, re.IGNORECASE):
                logger.warning(f"🚨 Command injection attempt detected: {pattern}")
                return False, ""
                
        # Type-specific validation
        if input_type == "url":
            return cls._validate_url(input_text)
        elif input_type == "filename":
            return cls._validate_filename(input_text)
        elif input_type == "discord_content":
            return cls._validate_discord_content(input_text)
            
        # Basic sanitization
        sanitized = cls._sanitize_general_input(input_text)
        return True, sanitized
        
    @classmethod
    def _validate_url(cls, url: str) -> tuple[bool, str]:
        """Validate URL input."""
        # Check for allowed protocols
        allowed_protocols = ['http://', 'https://']
        if not any(url.startswith(proto) for proto in allowed_protocols):
            return False, ""
            
        # Check for suspicious domains
        suspicious_domains = [
            'bit.ly', 'tinyurl.com', 'goo.gl',  # URL shorteners
            'localhost', '127.0.0.1', '0.0.0.0'  # Local addresses
        ]
        
        for domain in suspicious_domains:
            if domain in url:
                logger.warning(f"🚨 Suspicious domain in URL: {domain}")
                return False, ""
                
        return True, url
        
    @classmethod
    def _validate_filename(cls, filename: str) -> tuple[bool, str]:
        """Validate filename input."""
        # Remove dangerous characters
        dangerous_chars = ['..', '/', '\\', ':', '*', '?', '"', '<', '>', '|']
        for char in dangerous_chars:
            if char in filename:
                return False, ""
                
        # Limit length
        if len(filename) > 255:
            return False, ""
            
        # Check for reserved names (Windows)
        reserved_names = ['CON', 'PRN', 'AUX', 'NUL', 'COM1', 'COM2', 'LPT1', 'LPT2']
        if filename.upper() in reserved_names:
            return False, ""
            
        return True, filename
        
    @classmethod
    def _validate_discord_content(cls, content: str) -> tuple[bool, str]:
        """Validate Discord message content."""
        # Check length limits
        if len(content) > 2000:  # Discord message limit
            content = content[:1997] + "..."
            
        # Remove potential Discord formatting exploits
        content = content.replace('@everyone', '@\u200beveryone')
        content = content.replace('@here', '@\u200bhere')
        
        # Remove excessive newlines
        content = re.sub(r'\n{4,}', '\n\n\n', content)
        
        return True, content
        
    @classmethod
    def _sanitize_general_input(cls, text: str) -> str:
        """General input sanitization."""
        # Remove null bytes
        text = text.replace('\x00', '')
        
        # Limit excessive whitespace
        text = re.sub(r'\s{10,}', ' ', text)
        
        # Remove control characters (except newlines and tabs)
        text = ''.join(char for char in text if ord(char) >= 32 or char in '\n\t')
        
        return text.strip()


class RateLimiter:
    """Advanced rate limiting with multiple strategies."""
    
    def __init__(self):
        self.user_requests: Dict[int, List[float]] = {}
        self.ip_requests: Dict[str, List[float]] = {}
        self.global_requests: List[float] = []
        
        # Rate limit configurations
        self.limits = {
            'user_per_minute': 30,
            'user_per_hour': 200,
            'ip_per_minute': 100,
            'global_per_second': 50,
        }
        
    def is_rate_limited(self, user_id: int, ip_address: str = None) -> tuple[bool, str]:
        """
        Check if request should be rate limited.
        
        Args:
            user_id: Discord user ID
            ip_address: IP address (if available)
            
        Returns:
            Tuple of (is_limited, reason)
        """
        now = time.time()
        
        # Clean old requests
        self._cleanup_old_requests(now)
        
        # Check user limits
        user_requests = self.user_requests.get(user_id, [])
        
        # User per minute limit
        recent_user_requests = [req for req in user_requests if now - req < 60]
        if len(recent_user_requests) >= self.limits['user_per_minute']:
            return True, "User rate limit exceeded (per minute)"
            
        # User per hour limit
        hourly_user_requests = [req for req in user_requests if now - req < 3600]
        if len(hourly_user_requests) >= self.limits['user_per_hour']:
            return True, "User rate limit exceeded (per hour)"
            
        # IP limits (if available)
        if ip_address:
            ip_requests = self.ip_requests.get(ip_address, [])
            recent_ip_requests = [req for req in ip_requests if now - req < 60]
            if len(recent_ip_requests) >= self.limits['ip_per_minute']:
                return True, "IP rate limit exceeded"
                
        # Global limits
        recent_global_requests = [req for req in self.global_requests if now - req < 1]
        if len(recent_global_requests) >= self.limits['global_per_second']:
            return True, "Global rate limit exceeded"
            
        # Record request
        self._record_request(user_id, ip_address, now)
        
        return False, ""
        
    def _record_request(self, user_id: int, ip_address: str, timestamp: float):
        """Record a new request."""
        # Record user request
        if user_id not in self.user_requests:
            self.user_requests[user_id] = []
        self.user_requests[user_id].append(timestamp)
        
        # Record IP request
        if ip_address:
            if ip_address not in self.ip_requests:
                self.ip_requests[ip_address] = []
            self.ip_requests[ip_address].append(timestamp)
            
        # Record global request
        self.global_requests.append(timestamp)
        
    def _cleanup_old_requests(self, now: float):
        """Clean up old request records."""
        # Clean user requests (keep last hour)
        for user_id in list(self.user_requests.keys()):
            self.user_requests[user_id] = [
                req for req in self.user_requests[user_id] 
                if now - req < 3600
            ]
            if not self.user_requests[user_id]:
                del self.user_requests[user_id]
                
        # Clean IP requests (keep last hour)
        for ip in list(self.ip_requests.keys()):
            self.ip_requests[ip] = [
                req for req in self.ip_requests[ip] 
                if now - req < 3600
            ]
            if not self.ip_requests[ip]:
                del self.ip_requests[ip]
                
        # Clean global requests (keep last minute)
        self.global_requests = [
            req for req in self.global_requests 
            if now - req < 60
        ]


class EncryptionManager:
    """Secure encryption for sensitive data."""
    
    def __init__(self, password: str):
        """Initialize with password-derived key."""
        self.password = password.encode()
        self.salt = b'newsbot_salt_2025'  # Use a proper random salt in production
        
        # Derive key from password
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=self.salt,
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(self.password))
        self.cipher = Fernet(key)
        
    def encrypt(self, data: str) -> str:
        """Encrypt string data."""
        encrypted = self.cipher.encrypt(data.encode())
        return base64.urlsafe_b64encode(encrypted).decode()
        
    def decrypt(self, encrypted_data: str) -> str:
        """Decrypt string data."""
        try:
            decoded = base64.urlsafe_b64decode(encrypted_data.encode())
            decrypted = self.cipher.decrypt(decoded)
            return decrypted.decode()
        except Exception as e:
            logger.error(f"Decryption failed: {e}")
            return ""


class SecurityManager:
    """Comprehensive security management system."""
    
    def __init__(self, cache: Optional[JSONCache] = None):
        self.cache = cache
        self.validator = InputValidator()
        self.rate_limiter = RateLimiter()
        self.security_events: List[SecurityEvent] = []
        self.blocked_users: Set[int] = set()
        self.blocked_ips: Set[str] = set()
        
        # Security configuration
        self.config = {
            'max_security_events_per_hour': 10,
            'auto_block_threshold': 5,
            'block_duration_hours': 24,
            'enable_content_scanning': True,
            'enable_rate_limiting': True,
        }
        
    async def validate_command_input(self, interaction: discord.Interaction, **kwargs) -> bool:
        """
        Validate command input for security issues.
        
        Args:
            interaction: Discord interaction
            **kwargs: Command parameters to validate
            
        Returns:
            bool: True if input is safe
        """
        user_id = interaction.user.id
        
        # Check if user is blocked
        if user_id in self.blocked_users:
            await interaction.response.send_message(
                "❌ Access denied. Your account has been temporarily restricted.",
                ephemeral=True
            )
            return False
            
        # Rate limiting
        if self.config['enable_rate_limiting']:
            is_limited, reason = self.rate_limiter.is_rate_limited(user_id)
            if is_limited:
                await interaction.response.send_message(
                    f"⏱️ Rate limit exceeded: {reason}. Please try again later.",
                    ephemeral=True
                )
                self._record_security_event(
                    "rate_limit_exceeded",
                    ThreatLevel.MEDIUM,
                    user_id,
                    f"Rate limit exceeded: {reason}"
                )
                return False
                
        # Validate all input parameters
        for param_name, param_value in kwargs.items():
            if isinstance(param_value, str):
                is_safe, sanitized = self.validator.validate_input(param_value, "discord_content")
                if not is_safe:
                    await interaction.response.send_message(
                        "❌ Invalid input detected. Please check your input and try again.",
                        ephemeral=True
                    )
                    self._record_security_event(
                        "malicious_input",
                        ThreatLevel.HIGH,
                        user_id,
                        f"Malicious input in parameter '{param_name}': {param_value[:100]}"
                    )
                    return False
                    
        return True
        
    def _record_security_event(self, event_type: str, threat_level: ThreatLevel, 
                              user_id: Optional[int], description: str, 
                              metadata: Dict[str, Any] = None):
        """Record a security event."""
        event = SecurityEvent(
            event_type=event_type,
            threat_level=threat_level,
            user_id=user_id,
            description=description,
            timestamp=datetime.now(),
            metadata=metadata or {}
        )
        
        self.security_events.append(event)
        
        # Log security event
        logger.warning(
            f"🚨 Security Event: {event_type} | "
            f"Threat: {threat_level.value} | "
            f"User: {user_id} | "
            f"Description: {description}"
        )
        
        # Check for auto-block conditions
        if user_id and threat_level in [ThreatLevel.HIGH, ThreatLevel.CRITICAL]:
            self._check_auto_block(user_id)
            
    def _check_auto_block(self, user_id: int):
        """Check if user should be auto-blocked based on security events."""
        recent_events = [
            event for event in self.security_events
            if event.user_id == user_id and 
            event.timestamp > datetime.now() - timedelta(hours=1) and
            event.threat_level in [ThreatLevel.HIGH, ThreatLevel.CRITICAL]
        ]
        
        if len(recent_events) >= self.config['auto_block_threshold']:
            self.blocked_users.add(user_id)
            logger.critical(
                f"🚨 Auto-blocked user {user_id} due to {len(recent_events)} "
                f"high-threat security events in the last hour"
            )
            
            # Schedule unblock
            asyncio.create_task(self._schedule_unblock(user_id))
            
    async def _schedule_unblock(self, user_id: int):
        """Schedule automatic unblock after configured duration."""
        await asyncio.sleep(self.config['block_duration_hours'] * 3600)
        if user_id in self.blocked_users:
            self.blocked_users.remove(user_id)
            logger.info(f"🔓 Auto-unblocked user {user_id} after {self.config['block_duration_hours']} hours")
            
    async def get_security_summary(self) -> Dict[str, Any]:
        """Get comprehensive security summary."""
        now = datetime.now()
        
        # Count events by time period
        last_hour_events = [
            e for e in self.security_events 
            if e.timestamp > now - timedelta(hours=1)
        ]
        last_day_events = [
            e for e in self.security_events 
            if e.timestamp > now - timedelta(days=1)
        ]
        
        # Count by threat level
        threat_counts = {}
        for level in ThreatLevel:
            threat_counts[level.value] = len([
                e for e in last_day_events 
                if e.threat_level == level
            ])
            
        # Count by event type
        event_type_counts = {}
        for event in last_day_events:
            event_type_counts[event.event_type] = event_type_counts.get(event.event_type, 0) + 1
            
        return {
            'timestamp': now.isoformat(),
            'total_events_last_hour': len(last_hour_events),
            'total_events_last_day': len(last_day_events),
            'threat_level_counts': threat_counts,
            'event_type_counts': event_type_counts,
            'blocked_users_count': len(self.blocked_users),
            'blocked_ips_count': len(self.blocked_ips),
            'rate_limiter_stats': {
                'active_users': len(self.rate_limiter.user_requests),
                'active_ips': len(self.rate_limiter.ip_requests),
                'global_requests_last_minute': len([
                    req for req in self.rate_limiter.global_requests 
                    if time.time() - req < 60
                ])
            }
        }


def security_check(require_admin: bool = False):
    """Decorator for security validation on commands."""
    def decorator(func):
        @wraps(func)
        async def wrapper(self, interaction: discord.Interaction, *args, **kwargs):
            # Get security manager from bot
            security_manager = getattr(self.bot, 'security_manager', None)
            if not security_manager:
                logger.warning("Security manager not available for command validation")
                return await func(self, interaction, *args, **kwargs)
                
            # Validate input
            if not await security_manager.validate_command_input(interaction, **kwargs):
                return  # Security validation failed
                
            # Admin check
            if require_admin:
                if not hasattr(self, '_is_admin') or not self._is_admin(interaction.user):
                    await interaction.response.send_message(
                        "❌ Admin access required.",
                        ephemeral=True
                    )
                    security_manager._record_security_event(
                        "unauthorized_admin_access",
                        ThreatLevel.MEDIUM,
                        interaction.user.id,
                        f"Unauthorized admin command attempt: {func.__name__}"
                    )
                    return
                    
            return await func(self, interaction, *args, **kwargs)
        return wrapper
    return decorator 