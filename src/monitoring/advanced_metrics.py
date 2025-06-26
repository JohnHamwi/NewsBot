"""
Advanced Performance Metrics and Optimization System for NewsBot
Provides detailed performance tracking, optimization suggestions, and resource management.
"""
import asyncio
import time
import psutil
import gc
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from collections import defaultdict, deque
from functools import wraps

from src.utils.base_logger import base_logger as logger
from src.cache.json_cache import JSONCache


@dataclass
class PerformanceMetric:
    """Individual performance metric data point."""
    name: str
    value: float
    unit: str
    timestamp: datetime
    context: Dict[str, Any] = field(default_factory=dict)


@dataclass
class OptimizationSuggestion:
    """Performance optimization suggestion."""
    category: str
    priority: str  # high, medium, low
    description: str
    impact: str
    implementation: str


class AdvancedMetricsCollector:
    """Advanced performance metrics collection and analysis."""
    
    def __init__(self, cache: Optional[JSONCache] = None):
        self.cache = cache
        self.metrics_history: Dict[str, deque] = defaultdict(lambda: deque(maxlen=1000))
        self.start_time = time.time()
        
        # Performance thresholds
        self.thresholds = {
            'api_response_time_ms': 2000,  # 2 seconds
            'memory_usage_percent': 80,    # 80%
            'cpu_usage_percent': 70,       # 70%
            'disk_usage_percent': 85,      # 85%
            'error_rate_percent': 5,       # 5%
            'translation_time_ms': 3000,   # 3 seconds
            'posting_time_ms': 5000,       # 5 seconds
        }
        
        # Optimization tracking
        self.optimization_suggestions: List[OptimizationSuggestion] = []
        self.last_optimization_check = time.time()
        
    def record_metric(self, name: str, value: float, unit: str, context: Dict[str, Any] = None):
        """Record a performance metric."""
        metric = PerformanceMetric(
            name=name,
            value=value,
            unit=unit,
            timestamp=datetime.now(),
            context=context or {}
        )
        
        self.metrics_history[name].append(metric)
        
        # Check for threshold violations
        self._check_threshold_violation(metric)
        
    def _check_threshold_violation(self, metric: PerformanceMetric):
        """Check if metric violates performance thresholds."""
        threshold = self.thresholds.get(metric.name)
        if threshold and metric.value > threshold:
            logger.warning(
                f"⚠️ Performance threshold exceeded: {metric.name} = {metric.value}{metric.unit} "
                f"(threshold: {threshold}{metric.unit})"
            )
            
    async def collect_system_metrics(self) -> Dict[str, float]:
        """Collect comprehensive system performance metrics."""
        metrics = {}
        
        # CPU metrics
        cpu_percent = psutil.cpu_percent(interval=0.1)
        cpu_count = psutil.cpu_count()
        load_avg = psutil.getloadavg() if hasattr(psutil, 'getloadavg') else (0, 0, 0)
        
        metrics.update({
            'cpu_usage_percent': cpu_percent,
            'cpu_count': cpu_count,
            'load_avg_1min': load_avg[0],
            'load_avg_5min': load_avg[1],
            'load_avg_15min': load_avg[2],
        })
        
        # Memory metrics
        memory = psutil.virtual_memory()
        swap = psutil.swap_memory()
        
        metrics.update({
            'memory_usage_percent': memory.percent,
            'memory_available_mb': memory.available / (1024 * 1024),
            'memory_used_mb': memory.used / (1024 * 1024),
            'swap_usage_percent': swap.percent,
        })
        
        # Disk metrics
        disk = psutil.disk_usage('/')
        
        metrics.update({
            'disk_usage_percent': (disk.used / disk.total) * 100,
            'disk_free_gb': disk.free / (1024 * 1024 * 1024),
            'disk_used_gb': disk.used / (1024 * 1024 * 1024),
        })
        
        # Network metrics (if available)
        try:
            net_io = psutil.net_io_counters()
            metrics.update({
                'network_bytes_sent': net_io.bytes_sent,
                'network_bytes_recv': net_io.bytes_recv,
                'network_packets_sent': net_io.packets_sent,
                'network_packets_recv': net_io.packets_recv,
            })
        except Exception:
            pass
            
        # Record all metrics
        for name, value in metrics.items():
            self.record_metric(name, value, self._get_unit_for_metric(name))
            
        return metrics
        
    def _get_unit_for_metric(self, metric_name: str) -> str:
        """Get appropriate unit for metric."""
        unit_map = {
            'percent': '%',
            'mb': 'MB',
            'gb': 'GB',
            'ms': 'ms',
            'count': '',
            'bytes': 'B',
            'packets': '',
        }
        
        for key, unit in unit_map.items():
            if key in metric_name:
                return unit
        return ''
        
    async def analyze_performance_trends(self) -> Dict[str, Any]:
        """Analyze performance trends and identify issues."""
        analysis = {
            'trends': {},
            'anomalies': [],
            'recommendations': []
        }
        
        for metric_name, history in self.metrics_history.items():
            if len(history) < 10:  # Need enough data points
                continue
                
            values = [m.value for m in list(history)[-50:]]  # Last 50 data points
            
            # Calculate trend
            if len(values) >= 2:
                trend = self._calculate_trend(values)
                analysis['trends'][metric_name] = {
                    'direction': 'increasing' if trend > 0.1 else 'decreasing' if trend < -0.1 else 'stable',
                    'slope': trend,
                    'current_value': values[-1],
                    'avg_value': sum(values) / len(values)
                }
                
                # Detect anomalies
                anomalies = self._detect_anomalies(values)
                if anomalies:
                    analysis['anomalies'].extend([
                        {
                            'metric': metric_name,
                            'type': 'spike' if anomaly > 0 else 'drop',
                            'severity': abs(anomaly),
                            'timestamp': datetime.now().isoformat()
                        }
                        for anomaly in anomalies
                    ])
        
        # Generate recommendations
        analysis['recommendations'] = await self._generate_recommendations(analysis)
        
        return analysis
        
    def _calculate_trend(self, values: List[float]) -> float:
        """Calculate trend slope using simple linear regression."""
        n = len(values)
        if n < 2:
            return 0
            
        x_sum = sum(range(n))
        y_sum = sum(values)
        xy_sum = sum(i * values[i] for i in range(n))
        x_sq_sum = sum(i * i for i in range(n))
        
        slope = (n * xy_sum - x_sum * y_sum) / (n * x_sq_sum - x_sum * x_sum)
        return slope
        
    def _detect_anomalies(self, values: List[float]) -> List[float]:
        """Detect anomalies using simple statistical methods."""
        if len(values) < 10:
            return []
            
        mean = sum(values) / len(values)
        variance = sum((x - mean) ** 2 for x in values) / len(values)
        std_dev = variance ** 0.5
        
        threshold = 2 * std_dev  # 2 standard deviations
        
        anomalies = []
        for value in values[-10:]:  # Check last 10 values
            deviation = abs(value - mean)
            if deviation > threshold:
                anomalies.append(value - mean)
                
        return anomalies
        
    async def _generate_recommendations(self, analysis: Dict[str, Any]) -> List[OptimizationSuggestion]:
        """Generate optimization recommendations based on analysis."""
        recommendations = []
        
        trends = analysis.get('trends', {})
        anomalies = analysis.get('anomalies', [])
        
        # Memory optimization recommendations
        if 'memory_usage_percent' in trends:
            memory_trend = trends['memory_usage_percent']
            if memory_trend['current_value'] > 75:
                recommendations.append(OptimizationSuggestion(
                    category="Memory",
                    priority="high",
                    description="High memory usage detected",
                    impact="May cause performance degradation and potential crashes",
                    implementation="Consider implementing memory pooling, reducing cache sizes, or adding garbage collection optimization"
                ))
                
        # CPU optimization recommendations  
        if 'cpu_usage_percent' in trends:
            cpu_trend = trends['cpu_usage_percent']
            if cpu_trend['direction'] == 'increasing' and cpu_trend['current_value'] > 60:
                recommendations.append(OptimizationSuggestion(
                    category="CPU",
                    priority="medium",
                    description="Increasing CPU usage trend detected",
                    impact="May lead to slower response times and reduced throughput",
                    implementation="Profile CPU-intensive operations, optimize algorithms, or implement request queuing"
                ))
                
        # API performance recommendations
        api_metrics = [name for name in trends.keys() if 'api' in name or 'response_time' in name]
        for metric in api_metrics:
            if trends[metric]['current_value'] > 2000:  # 2 seconds
                recommendations.append(OptimizationSuggestion(
                    category="API Performance",
                    priority="high",
                    description=f"Slow API response times detected in {metric}",
                    impact="Poor user experience and potential timeouts",
                    implementation="Implement response caching, connection pooling, or async request optimization"
                ))
                
        return recommendations
        
    async def get_performance_summary(self) -> Dict[str, Any]:
        """Get comprehensive performance summary."""
        current_metrics = await self.collect_system_metrics()
        analysis = await self.analyze_performance_trends()
        
        # Calculate uptime
        uptime_seconds = time.time() - self.start_time
        uptime_hours = uptime_seconds / 3600
        
        # Performance score (0-100)
        performance_score = self._calculate_performance_score(current_metrics, analysis)
        
        return {
            'timestamp': datetime.now().isoformat(),
            'uptime_hours': round(uptime_hours, 2),
            'performance_score': performance_score,
            'current_metrics': current_metrics,
            'trends': analysis['trends'],
            'anomalies': analysis['anomalies'],
            'recommendations': analysis['recommendations'],
            'health_status': 'excellent' if performance_score > 90 else 
                           'good' if performance_score > 75 else
                           'fair' if performance_score > 60 else 'poor'
        }
        
    def _calculate_performance_score(self, metrics: Dict[str, float], analysis: Dict[str, Any]) -> int:
        """Calculate overall performance score (0-100)."""
        score = 100
        
        # Deduct points for high resource usage
        if metrics.get('cpu_usage_percent', 0) > 70:
            score -= 20
        elif metrics.get('cpu_usage_percent', 0) > 50:
            score -= 10
            
        if metrics.get('memory_usage_percent', 0) > 80:
            score -= 20
        elif metrics.get('memory_usage_percent', 0) > 60:
            score -= 10
            
        if metrics.get('disk_usage_percent', 0) > 85:
            score -= 15
            
        # Deduct points for anomalies
        anomaly_count = len(analysis.get('anomalies', []))
        score -= min(anomaly_count * 5, 25)  # Max 25 points deduction
        
        # Deduct points for high-priority recommendations
        high_priority_recs = len([r for r in analysis.get('recommendations', []) if r.priority == 'high'])
        score -= high_priority_recs * 10
        
        return max(0, min(100, score))


def performance_tracker(metric_name: str):
    """Decorator to track function performance."""
    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = await func(*args, **kwargs)
                duration_ms = (time.time() - start_time) * 1000
                
                # Record metric if collector is available
                if hasattr(args[0], 'metrics_collector'):
                    args[0].metrics_collector.record_metric(
                        f"{metric_name}_duration_ms",
                        duration_ms,
                        "ms",
                        {'function': func.__name__, 'success': True}
                    )
                    
                return result
            except Exception as e:
                duration_ms = (time.time() - start_time) * 1000
                
                # Record failed metric
                if hasattr(args[0], 'metrics_collector'):
                    args[0].metrics_collector.record_metric(
                        f"{metric_name}_duration_ms",
                        duration_ms,
                        "ms", 
                        {'function': func.__name__, 'success': False, 'error': str(e)}
                    )
                    
                raise
                
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                duration_ms = (time.time() - start_time) * 1000
                
                # Record metric if collector is available
                if hasattr(args[0], 'metrics_collector'):
                    args[0].metrics_collector.record_metric(
                        f"{metric_name}_duration_ms",
                        duration_ms,
                        "ms",
                        {'function': func.__name__, 'success': True}
                    )
                    
                return result
            except Exception as e:
                duration_ms = (time.time() - start_time) * 1000
                
                # Record failed metric
                if hasattr(args[0], 'metrics_collector'):
                    args[0].metrics_collector.record_metric(
                        f"{metric_name}_duration_ms",
                        duration_ms,
                        "ms",
                        {'function': func.__name__, 'success': False, 'error': str(e)}
                    )
                    
                raise
                
        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
    return decorator 