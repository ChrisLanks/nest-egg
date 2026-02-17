# Production Monitoring & Observability Guide

This guide covers setting up comprehensive monitoring for Nest Egg in production.

## 📊 Overview

Nest Egg includes production-grade monitoring with:
- **Structured Logging** - JSON logs for log aggregation
- **Prometheus Metrics** - Performance and business metrics
- **Sentry Integration** - Error tracking and performance monitoring
- **Rate Limiting Dashboard** - Real-time rate limit status
- **Health Checks** - Readiness and liveness probes

---

## 🚀 Quick Start

### 1. Enable Monitoring (Already Enabled by Default)

```bash
# In .env
METRICS_ENABLED=true
LOG_LEVEL=INFO
LOG_FORMAT=text  # Use 'json' in production
ENVIRONMENT=production
```

### 2. Access Monitoring Endpoints

```bash
# Health check
curl http://localhost:8000/api/v1/monitoring/health

# Prometheus metrics
curl http://localhost:8000/metrics

# Rate limiting dashboard (admin only)
curl -H "Authorization: Bearer <token>" \
  http://localhost:8000/api/v1/monitoring/rate-limits

# System statistics (admin only)
curl -H "Authorization: Bearer <token>" \
  http://localhost:8000/api/v1/monitoring/system-stats
```

---

## 📝 Structured Logging

### Configuration

Logs automatically switch to JSON format in production:

```python
# Development logs (human-readable)
2024-02-17 10:30:15 app.api.v1.auth INFO user_login user_id=123 email=user@example.com

# Production logs (JSON)
{"timestamp": "2024-02-17T10:30:15.123Z", "level": "info", "event": "user_login", "user_id": 123, "email": "user@example.com", "filename": "auth.py", "lineno": 45}
```

### Usage in Code

```python
from app.core.logging_config import get_logger

logger = get_logger(__name__)

# Log with context
logger.info("user_login", user_id=user.id, email=user.email, ip=client_ip)
logger.error("database_error", exc_info=True, query="SELECT ...", duration_ms=1234)
logger.warning("rate_limit_exceeded", endpoint="/api/transactions", ip=client_ip)
```

### Log Aggregation

Forward JSON logs to your logging service:

#### Datadog
```yaml
# docker-compose.yml
logging:
  driver: "json-file"
  options:
    max-size: "10m"
    max-file: "3"
    labels: "service,environment"
```

#### ELK Stack
```bash
# Filebeat configuration
filebeat.inputs:
  - type: log
    enabled: true
    paths:
      - /app/logs/*.log
    json.keys_under_root: true
    json.add_error_key: true
```

#### CloudWatch
```bash
# AWS CloudWatch agent
{
  "logs": {
    "logs_collected": {
      "files": {
        "collect_list": [
          {
            "file_path": "/app/logs/*.log",
            "log_group_name": "/nestegg/api",
            "log_stream_name": "{instance_id}"
          }
        ]
      }
    }
  }
}
```

---

## 📈 Prometheus Metrics

### Available Metrics

#### HTTP Metrics
- `http_requests_total` - Total HTTP requests (by method, endpoint, status)
- `http_request_duration_seconds` - Request latency histogram
- `http_requests_inprogress` - Current in-flight requests
- `http_request_size_bytes` - Request body size
- `http_response_size_bytes` - Response body size

#### Database Metrics
- `db_query_duration_seconds` - Query execution time
- `db_connection_pool_size` - Connection pool size
- `db_connection_pool_available` - Available connections

#### Celery Metrics
- `celery_tasks_total` - Total tasks executed (by task name, status)
- `celery_task_duration_seconds` - Task execution time

#### Rate Limiting Metrics
- `rate_limit_hits_total` - Requests blocked by rate limiting
- `rate_limit_requests_total` - Requests subject to rate limiting

#### Business Metrics
- `users_total` - Total registered users
- `transactions_total` - Total transactions
- `accounts_total` - Total linked accounts
- `plaid_syncs_total` - Plaid sync operations (by status)
- `budget_alerts_total` - Budget alerts triggered (by priority)

### Prometheus Configuration

```yaml
# prometheus.yml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

scrape_configs:
  - job_name: 'nestegg-api'
    static_configs:
      - targets: ['api:8000']
    metrics_path: '/metrics'
    scrape_interval: 30s
```

### Grafana Dashboard

Import the included Grafana dashboard:

```bash
# Located at: docs/grafana-dashboard.json
# Or create custom dashboards with these queries:
```

#### Example PromQL Queries

```promql
# Request rate (requests/second)
rate(http_requests_total[5m])

# 95th percentile latency
histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))

# Error rate
rate(http_requests_total{status=~"5.."}[5m]) / rate(http_requests_total[5m])

# Active users (last hour)
increase(users_total[1h])

# Database connection pool utilization
(db_connection_pool_size - db_connection_pool_available) / db_connection_pool_size

# Celery task success rate
rate(celery_tasks_total{status="success"}[5m]) / rate(celery_tasks_total[5m])
```

---

## 🐛 Sentry Integration

### Setup

1. **Create Sentry Project**
   - Go to https://sentry.io
   - Create new project (Python/FastAPI)
   - Copy DSN

2. **Configure Environment**
```bash
# .env
SENTRY_DSN=https://abc123@o123456.ingest.sentry.io/7890123
ENVIRONMENT=production
```

3. **Verify Integration**
```bash
# Test Sentry capture
curl -X POST http://localhost:8000/api/v1/dev/test-sentry
```

### Features

- **Error Tracking** - Automatic exception capture
- **Performance Monitoring** - Slow transaction detection
- **Release Tracking** - Group errors by release version
- **Breadcrumbs** - Trace events leading to errors
- **PII Filtering** - Sensitive data automatically filtered

### Custom Error Tracking

```python
from sentry_sdk import capture_exception, capture_message

try:
    # Risky operation
    process_transaction()
except Exception as e:
    # Automatically captured by Sentry
    capture_exception(e)
    raise
```

---

## 🚦 Rate Limiting Dashboard

### Access Dashboard

```bash
# Requires admin user
GET /api/v1/monitoring/rate-limits
Authorization: Bearer <admin-token>
```

### Response Format

```json
{
  "current_active_limits": [
    {
      "endpoint": "/api/v1/transactions",
      "client_id": "192.168.1.100",
      "requests": 45,
      "limit": 100,
      "window_seconds": 60,
      "resets_at": "2024-02-17T10:35:00Z",
      "blocked": false
    }
  ],
  "total_requests_last_hour": 1234,
  "blocked_requests_last_hour": 12,
  "top_clients": [
    {"client_id": "192.168.1.100", "requests": 450},
    {"client_id": "192.168.1.101", "requests": 320}
  ],
  "top_endpoints": [
    {"endpoint": "/api/v1/transactions", "requests": 890},
    {"endpoint": "/api/v1/accounts", "requests": 345}
  ]
}
```

### Monitoring Alerts

Set up alerts for rate limiting abuse:

```promql
# Alert if blocked requests exceed 10% of total
rate(rate_limit_hits_total[5m]) / rate(rate_limit_requests_total[5m]) > 0.1
```

---

## ❤️ Health Checks

### Endpoints

```bash
# Simple health check
GET /health
→ {"status": "healthy"}

# Detailed health check with dependencies
GET /api/v1/monitoring/health
→ {
  "status": "healthy",
  "version": "1.0.0",
  "timestamp": "2024-02-17T10:30:15Z",
  "database": "ok",
  "redis": "ok"
}
```

### Kubernetes Probes

```yaml
# deployment.yaml
livenessProbe:
  httpGet:
    path: /health
    port: 8000
  initialDelaySeconds: 30
  periodSeconds: 10
  timeoutSeconds: 5
  failureThreshold: 3

readinessProbe:
  httpGet:
    path: /api/v1/monitoring/health
    port: 8000
  initialDelaySeconds: 10
  periodSeconds: 5
  timeoutSeconds: 3
  successThreshold: 1
```

### Docker Health Check

```dockerfile
# Dockerfile
HEALTHCHECK --interval=30s --timeout=3s --start-period=40s --retries=3 \
  CMD curl -f http://localhost:8000/health || exit 1
```

---

## 🔔 Alerting

### Recommended Alerts

#### Critical Alerts (PagerDuty)

```yaml
# Prometheus alerting rules
groups:
  - name: nestegg_critical
    rules:
      - alert: HighErrorRate
        expr: rate(http_requests_total{status=~"5.."}[5m]) > 0.05
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "High error rate detected"

      - alert: DatabaseDown
        expr: up{job="nestegg-api"} == 0
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "API is down"

      - alert: SlowResponses
        expr: histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m])) > 2
        for: 10m
        labels:
          severity: warning
        annotations:
          summary: "95th percentile latency > 2 seconds"
```

#### Warning Alerts (Slack)

```yaml
  - name: nestegg_warnings
    rules:
      - alert: HighRateLimitHits
        expr: rate(rate_limit_hits_total[5m]) > 10
        for: 5m
        labels:
          severity: warning

      - alert: CeleryTaskBacklog
        expr: celery_tasks_inprogress > 100
        for: 15m
        labels:
          severity: warning
```

---

## 📊 Monitoring Stack Setup

### Option 1: Docker Compose (Simple)

```yaml
# docker-compose.monitoring.yml
version: '3.8'

services:
  prometheus:
    image: prom/prometheus:latest
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml
      - prometheus_data:/prometheus
    ports:
      - "9090:9090"
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.path=/prometheus'

  grafana:
    image: grafana/grafana:latest
    volumes:
      - grafana_data:/var/lib/grafana
    ports:
      - "3000:3000"
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin
      - GF_USERS_ALLOW_SIGN_UP=false

volumes:
  prometheus_data:
  grafana_data:
```

### Option 2: Hosted Services (Production)

#### Datadog
```bash
# docker-compose.yml
environment:
  - DD_AGENT_HOST=datadog-agent
  - DD_ENV=production
  - DD_SERVICE=nestegg-api
  - DD_VERSION=1.0.0
```

#### New Relic
```bash
# Install New Relic agent
pip install newrelic

# newrelic.ini
[newrelic]
license_key = YOUR_LICENSE_KEY
app_name = Nest Egg API
```

---

## 🎯 Best Practices

1. **Set Up Alerts Early** - Don't wait for incidents
2. **Use SLOs** - Define service level objectives (e.g., 99.9% uptime, p95 latency < 500ms)
3. **Monitor Business Metrics** - Track user signups, transactions, revenue
4. **Set Up Dashboards** - Make metrics visible to the team
5. **Test Alerts** - Regularly test alert firing and escalation
6. **Log Retention** - Keep logs for at least 30 days
7. **Metric Cardinality** - Avoid high-cardinality labels (e.g., user IDs)

---

## 🔍 Troubleshooting

### Metrics Not Appearing

```bash
# Check if metrics endpoint is accessible
curl http://localhost:8000/metrics

# Verify METRICS_ENABLED in .env
grep METRICS_ENABLED .env

# Check Prometheus targets
curl http://prometheus:9090/api/v1/targets
```

### Logs Not in JSON Format

```bash
# Verify LOG_FORMAT setting
grep LOG_FORMAT .env

# Should be 'json' for production
LOG_FORMAT=json
```

### Sentry Not Capturing Errors

```bash
# Verify SENTRY_DSN is set
grep SENTRY_DSN .env

# Test Sentry integration
curl -X POST http://localhost:8000/api/v1/dev/test-sentry
```

---

## 📚 Additional Resources

- [Prometheus Documentation](https://prometheus.io/docs/)
- [Grafana Dashboards](https://grafana.com/grafana/dashboards/)
- [Sentry FastAPI Integration](https://docs.sentry.io/platforms/python/guides/fastapi/)
- [Structlog Documentation](https://www.structlog.org/)
- [OpenTelemetry Python](https://opentelemetry.io/docs/instrumentation/python/)

---

**Last Updated:** February 2024
