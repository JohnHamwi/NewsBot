"""
Feature Management System for NewsBot
Provides centralized feature flag management and easy feature toggling.
"""

from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from enum import Enum
import json
from pathlib import Path

from src.utils.debug_logger import debug_logger, debug_context
from src.core.unified_config import unified_config as config


class FeatureStatus(Enum):
    """Feature status levels."""
    ENABLED = "enabled"
    DISABLED = "disabled"
    EXPERIMENTAL = "experimental"
    DEPRECATED = "deprecated"


@dataclass
class Feature:
    """Individual feature definition."""
    name: str
    description: str
    status: FeatureStatus
    dependencies: List[str] = field(default_factory=list)
    config_requirements: List[str] = field(default_factory=list)
    version_added: str = "1.0.0"
    experimental_until: Optional[str] = None
    deprecated_in: Optional[str] = None
    removed_in: Optional[str] = None


class FeatureManager:
    """Centralized feature management system."""
    
    def __init__(self):
        self.features: Dict[str, Feature] = {}
        self.feature_overrides: Dict[str, FeatureStatus] = {}
        self.load_feature_definitions()
        self.load_feature_overrides()
    
    def load_feature_definitions(self):
        """Load all feature definitions."""
        # Core Features
        self.register_feature(Feature(
            name="auto_posting",
            description="Automatic content posting from Telegram channels",
            status=FeatureStatus.ENABLED,
            config_requirements=["channels.active", "automation.interval_minutes"]
        ))
        
        self.register_feature(Feature(
            name="ai_translation",
            description="AI-powered Arabic to English translation",
            status=FeatureStatus.ENABLED,
            dependencies=["openai_api"],
            config_requirements=["openai.api_key"]
        ))
        
        self.register_feature(Feature(
            name="ai_categorization",
            description="AI-powered content categorization",
            status=FeatureStatus.ENABLED,
            dependencies=["ai_translation"],
            config_requirements=["openai.api_key"]
        ))
        
        self.register_feature(Feature(
            name="ai_title_generation",
            description="AI-powered Arabic title generation",
            status=FeatureStatus.ENABLED,
            dependencies=["openai_api"],
            config_requirements=["openai.api_key"]
        ))
        
        self.register_feature(Feature(
            name="location_detection",
            description="Automatic Syrian location detection in content",
            status=FeatureStatus.ENABLED
        ))
        
        self.register_feature(Feature(
            name="media_processing",
            description="Media file processing and attachment",
            status=FeatureStatus.ENABLED
        ))
        
        self.register_feature(Feature(
            name="news_role_pinging",
            description="Automatic news role pinging for posts",
            status=FeatureStatus.ENABLED,
            config_requirements=["bot.news_role_id"]
        ))
        
        self.register_feature(Feature(
            name="forum_tags",
            description="Discord forum tag assignment based on content",
            status=FeatureStatus.ENABLED,
            dependencies=["ai_categorization"]
        ))
        
        self.register_feature(Feature(
            name="rich_presence",
            description="Discord rich presence status updates",
            status=FeatureStatus.ENABLED
        ))
        
        self.register_feature(Feature(
            name="health_monitoring",
            description="Comprehensive system health monitoring",
            status=FeatureStatus.ENABLED
        ))
        
        self.register_feature(Feature(
            name="performance_tracking",
            description="Performance metrics and monitoring",
            status=FeatureStatus.ENABLED
        ))
        
        # Experimental Features
        self.register_feature(Feature(
            name="content_filtering",
            description="Advanced content filtering and quality scoring",
            status=FeatureStatus.EXPERIMENTAL,
            dependencies=["ai_translation"],
            experimental_until="2.0.0"
        ))
        
        self.register_feature(Feature(
            name="sentiment_analysis",
            description="AI-powered sentiment analysis of news content",
            status=FeatureStatus.EXPERIMENTAL,
            dependencies=["ai_translation"],
            experimental_until="2.0.0"
        ))
        
        self.register_feature(Feature(
            name="priority_scoring",
            description="Intelligent priority scoring for content",
            status=FeatureStatus.EXPERIMENTAL,
            dependencies=["sentiment_analysis", "ai_categorization"],
            experimental_until="2.0.0"
        ))
        
        # Base Dependencies
        self.register_feature(Feature(
            name="openai_api",
            description="OpenAI API connectivity",
            status=FeatureStatus.ENABLED,
            config_requirements=["openai.api_key"]
        ))
        
        self.register_feature(Feature(
            name="discord_api",
            description="Discord bot API connectivity",
            status=FeatureStatus.ENABLED,
            config_requirements=["discord.token", "discord.guild_id"]
        ))
        
        self.register_feature(Feature(
            name="telegram_api",
            description="Telegram client API connectivity",
            status=FeatureStatus.ENABLED,
            config_requirements=["telegram.api_id", "telegram.api_hash", "telegram.phone_number"]
        ))
    
    def register_feature(self, feature: Feature):
        """Register a new feature."""
        self.features[feature.name] = feature
        debug_logger.debug(f"Registered feature: {feature.name} ({feature.status.value})")
    
    def load_feature_overrides(self):
        """Load feature overrides from file."""
        override_file = Path("data/feature_overrides.json")
        if override_file.exists():
            try:
                with open(override_file, 'r') as f:
                    overrides = json.load(f)
                    self.feature_overrides = {
                        name: FeatureStatus(status) 
                        for name, status in overrides.items()
                    }
                debug_logger.info(f"Loaded {len(self.feature_overrides)} feature overrides")
            except Exception as e:
                debug_logger.error("Failed to load feature overrides", error=e)
    
    def save_feature_overrides(self):
        """Save feature overrides to file."""
        override_file = Path("data/feature_overrides.json")
        override_file.parent.mkdir(exist_ok=True)
        
        try:
            with open(override_file, 'w') as f:
                json.dump({
                    name: status.value 
                    for name, status in self.feature_overrides.items()
                }, f, indent=2)
            debug_logger.info(f"Saved {len(self.feature_overrides)} feature overrides")
        except Exception as e:
            debug_logger.error("Failed to save feature overrides", error=e)
    
    @debug_context("Feature Check")
    def is_enabled(self, feature_name: str) -> bool:
        """Check if a feature is enabled."""
        # Check override first
        if feature_name in self.feature_overrides:
            status = self.feature_overrides[feature_name]
        else:
            feature = self.features.get(feature_name)
            if not feature:
                debug_logger.warning(f"Unknown feature: {feature_name}")
                return False
            status = feature.status
        
        # Only enabled features are considered enabled
        result = status == FeatureStatus.ENABLED
        debug_logger.debug(f"Feature {feature_name}: {status.value} -> {'enabled' if result else 'disabled'}")
        return result
    
    def is_experimental(self, feature_name: str) -> bool:
        """Check if a feature is experimental."""
        if feature_name in self.feature_overrides:
            return self.feature_overrides[feature_name] == FeatureStatus.EXPERIMENTAL
        
        feature = self.features.get(feature_name)
        return feature and feature.status == FeatureStatus.EXPERIMENTAL
    
    def enable_feature(self, feature_name: str) -> bool:
        """Enable a feature."""
        if feature_name not in self.features:
            debug_logger.error(f"Cannot enable unknown feature: {feature_name}")
            return False
        
        # Check dependencies
        feature = self.features[feature_name]
        for dep in feature.dependencies:
            if not self.is_enabled(dep):
                debug_logger.error(f"Cannot enable {feature_name}: dependency {dep} is not enabled")
                return False
        
        # Check config requirements
        for req in feature.config_requirements:
            if not config.get(req):
                debug_logger.error(f"Cannot enable {feature_name}: missing config {req}")
                return False
        
        self.feature_overrides[feature_name] = FeatureStatus.ENABLED
        self.save_feature_overrides()
        debug_logger.info(f"Enabled feature: {feature_name}")
        return True
    
    def disable_feature(self, feature_name: str) -> bool:
        """Disable a feature."""
        if feature_name not in self.features:
            debug_logger.error(f"Cannot disable unknown feature: {feature_name}")
            return False
        
        # Check for dependents
        dependents = self.get_dependents(feature_name)
        enabled_dependents = [dep for dep in dependents if self.is_enabled(dep)]
        
        if enabled_dependents:
            debug_logger.error(f"Cannot disable {feature_name}: enabled dependents: {enabled_dependents}")
            return False
        
        self.feature_overrides[feature_name] = FeatureStatus.DISABLED
        self.save_feature_overrides()
        debug_logger.info(f"Disabled feature: {feature_name}")
        return True
    
    def get_dependents(self, feature_name: str) -> List[str]:
        """Get all features that depend on the given feature."""
        dependents = []
        for name, feature in self.features.items():
            if feature_name in feature.dependencies:
                dependents.append(name)
        return dependents
    
    def get_feature_status(self, feature_name: str) -> Optional[FeatureStatus]:
        """Get the current status of a feature."""
        if feature_name in self.feature_overrides:
            return self.feature_overrides[feature_name]
        
        feature = self.features.get(feature_name)
        return feature.status if feature else None
    
    def get_all_features(self) -> Dict[str, Feature]:
        """Get all registered features."""
        return self.features.copy()
    
    def get_enabled_features(self) -> List[str]:
        """Get list of all enabled features."""
        return [name for name in self.features.keys() if self.is_enabled(name)]
    
    def get_disabled_features(self) -> List[str]:
        """Get list of all disabled features."""
        return [name for name in self.features.keys() if not self.is_enabled(name)]
    
    def get_experimental_features(self) -> List[str]:
        """Get list of all experimental features."""
        return [name for name in self.features.keys() if self.is_experimental(name)]
    
    def validate_feature_dependencies(self) -> List[str]:
        """Validate all feature dependencies and return any issues."""
        issues = []
        
        for name, feature in self.features.items():
            # Check if enabled feature has disabled dependencies
            if self.is_enabled(name):
                for dep in feature.dependencies:
                    if not self.is_enabled(dep):
                        issues.append(f"Enabled feature '{name}' has disabled dependency '{dep}'")
                
                # Check config requirements
                for req in feature.config_requirements:
                    if not config.get(req):
                        issues.append(f"Enabled feature '{name}' missing required config '{req}'")
        
        return issues
    
    def generate_feature_report(self) -> str:
        """Generate a comprehensive feature status report."""
        lines = []
        
        lines.append("📋 FEATURE STATUS REPORT")
        lines.append("=" * 50)
        
        # Summary
        enabled = self.get_enabled_features()
        disabled = self.get_disabled_features()
        experimental = self.get_experimental_features()
        
        lines.append(f"✅ Enabled: {len(enabled)}")
        lines.append(f"❌ Disabled: {len(disabled)}")
        lines.append(f"🧪 Experimental: {len(experimental)}")
        lines.append("")
        
        # Dependency issues
        issues = self.validate_feature_dependencies()
        if issues:
            lines.append("⚠️ DEPENDENCY ISSUES:")
            for issue in issues:
                lines.append(f"  • {issue}")
            lines.append("")
        
        # Feature details
        for category, feature_list in [
            ("ENABLED FEATURES", enabled),
            ("DISABLED FEATURES", disabled),
            ("EXPERIMENTAL FEATURES", experimental)
        ]:
            if feature_list:
                lines.append(f"{category}:")
                for feature_name in sorted(feature_list):
                    feature = self.features[feature_name]
                    lines.append(f"  • {feature_name}: {feature.description}")
                lines.append("")
        
        return "\n".join(lines)


# Decorator for feature-gated functions
def requires_feature(feature_name: str, fallback_return=None):
    """Decorator to gate functions behind feature flags."""
    def decorator(func: Callable):
        def wrapper(*args, **kwargs):
            if not feature_manager.is_enabled(feature_name):
                debug_logger.debug(f"Skipping {func.__name__}: feature {feature_name} disabled")
                return fallback_return
            return func(*args, **kwargs)
        
        async def async_wrapper(*args, **kwargs):
            if not feature_manager.is_enabled(feature_name):
                debug_logger.debug(f"Skipping {func.__name__}: feature {feature_name} disabled")
                return fallback_return
            return await func(*args, **kwargs)
        
        # Return appropriate wrapper
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return wrapper
    
    return decorator


# Global feature manager instance
feature_manager = FeatureManager() 