# 📊 Monitoring & Health Checks

Syrian NewsBot includes comprehensive monitoring and health check capabilities for production deployment.

## 🏥 Health Check Endpoints

The bot provides HTTP endpoints for external monitoring systems.

### Available Endpoints

| Endpoint | Description | Response Format |
|----------|-------------|-----------------|
| `/health` | Basic health status | JSON |
| `/health/detailed` | Comprehensive health information | JSON |
| `/metrics` | Performance metrics (Prometheus format) | Text |
| `/ready` | Kubernetes readiness probe | JSON |
| `/live` | Kubernetes liveness probe | JSON |

### Configuration

Health check server runs on port `8080` by default.

## 📈 Performance Metrics

Advanced performance monitoring system that tracks:

- **System Resources**: CPU, memory, disk usage
- **Command Performance**: Execution times, success rates, error tracking
- **Auto-posting Metrics**: Success rates, posting frequency
- **Error Analysis**: Error types, frequencies, recent occurrences

### Features

- **Real-time Monitoring**: Continuous system resource tracking
- **Command Tracking**: Automatic performance measurement for all commands
- **Error Tracking**: Comprehensive error logging and analysis
- **Health Scoring**: Overall bot health score (0-100)
- **Alerting**: Threshold-based warnings and critical alerts
- **Retention**: Configurable data retention (default: 24 hours)

### Performance Thresholds

| Metric | Warning | Critical |
|--------|---------|----------|
| CPU Usage | 80% | 95% |
| Memory Usage | 80% | 95% |
| Discord Latency | 500ms | 1000ms |

## 🤖 Discord Commands

### `/monitoring`

Comprehensive monitoring dashboard accessible via Discord.

**Usage:**
```
/monitoring [detail_level] [metric_type]
```

**Parameters:**
- `detail_level`: Summary, Detailed, Full Report
- `metric_type`: All Metrics, System Performance, Command Performance, Error Analysis, Auto-posting

## 🔧 Integration

### Kubernetes/Docker

Health check endpoints are designed for container orchestration with liveness and readiness probes.

### Prometheus Monitoring

The `/metrics` endpoint provides Prometheus-compatible metrics for monitoring dashboards.

## 🚨 Alerting

The system logs warnings and critical alerts for system resource usage and performance issues.

## 🛠️ Development

### Performance Tracking Decorator

Automatically track command performance:

```python
from src.components.decorators.performance_tracking import track_performance

@track_performance()
async def my_command(interaction: discord.Interaction):
    # Command implementation
    pass
```

---

**Author**: حَـــــنَّـــــا  
**Version**: 3.0.0
