# Deployment Guide - Celery Workers

## Overview

Nest Egg uses Celery for background tasks:
- Budget alerts (daily at midnight)
- Recurring transaction detection (weekly)
- Cash flow forecasting (daily at 6:30am)
- Holdings price updates (daily at 6pm)
- Portfolio snapshots (daily at 11:59pm)

## Prerequisites

1. **Redis** (message broker)
```bash
# macOS
brew install redis
brew services start redis

# Ubuntu/Debian
sudo apt-get install redis-server
sudo systemctl start redis
```

2. **Environment Variables**
```bash
# Add to backend/.env
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0
```

## Running Celery Workers

### Development

```bash
cd backend

# Terminal 1: Start Celery worker
celery -A app.workers.celery_app worker --loglevel=info

# Terminal 2: Start Celery beat (scheduler)
celery -A app.workers.celery_app beat --loglevel=info

# Terminal 3: (Optional) Flower monitoring
celery -A app.workers.celery_app flower
# Then visit http://localhost:5555
```

### Production (Systemd)

Create `/etc/systemd/system/nest-egg-worker.service`:
```ini
[Unit]
Description=Nest Egg Celery Worker
After=network.target redis.service

[Service]
Type=forking
User=nest-egg
Group=nest-egg
WorkingDirectory=/var/www/nest-egg/backend
Environment="PATH=/var/www/nest-egg/backend/venv/bin"
ExecStart=/var/www/nest-egg/backend/venv/bin/celery -A app.workers.celery_app worker \
    --detach \
    --pidfile=/var/run/celery/worker.pid \
    --logfile=/var/log/celery/worker.log \
    --loglevel=info

[Install]
WantedBy=multi-user.target
```

Create `/etc/systemd/system/nest-egg-beat.service`:
```ini
[Unit]
Description=Nest Egg Celery Beat
After=network.target redis.service

[Service]
Type=simple
User=nest-egg
Group=nest-egg
WorkingDirectory=/var/www/nest-egg/backend
Environment="PATH=/var/www/nest-egg/backend/venv/bin"
ExecStart=/var/www/nest-egg/backend/venv/bin/celery -A app.workers.celery_app beat \
    --loglevel=info \
    --pidfile=/var/run/celery/beat.pid \
    --logfile=/var/log/celery/beat.log

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl daemon-reload
sudo systemctl enable nest-egg-worker nest-egg-beat
sudo systemctl start nest-egg-worker nest-egg-beat
```

## Monitoring

### Check Status
```bash
# Systemd
sudo systemctl status nest-egg-worker
sudo systemctl status nest-egg-beat

# Logs
sudo tail -f /var/log/celery/worker.log
sudo tail -f /var/log/celery/beat.log
```

### Flower Dashboard
```bash
celery -A app.workers.celery_app flower
# Visit http://localhost:5555
```

## Task Schedule

| Task | Schedule | Purpose |
|------|----------|---------|
| check_budget_alerts | Daily 00:00 | Notify users of budget overruns |
| detect_recurring_patterns | Mon 02:00 | Find subscription patterns |
| check_cash_flow_forecast | Daily 06:30 | Alert negative balance projections |
| update_holdings_prices | Daily 18:00 | Refresh market prices |
| capture_daily_holdings_snapshot | Daily 23:59 | Portfolio history tracking |

## Troubleshooting

### Worker not starting
```bash
# Check Redis
redis-cli ping  # Should return PONG

# Check logs
tail -f /var/log/celery/worker.log

# Test task manually
python
>>> from app.workers.tasks.budget_tasks import check_budget_alerts_task
>>> check_budget_alerts_task.delay()
```

### Tasks not running on schedule
```bash
# Verify beat is running
ps aux | grep celery

# Check beat schedule
celery -A app.workers.celery_app inspect scheduled

# Force run a task
celery -A app.workers.celery_app call check_budget_alerts
```

### High memory usage
```bash
# Restart workers periodically (every 24h)
# Add to crontab:
0 3 * * * systemctl restart nest-egg-worker
```

## Scaling

### Multiple Workers
```bash
# Start 4 worker processes
celery -A app.workers.celery_app worker --concurrency=4

# Or multiple instances
celery -A app.workers.celery_app worker -n worker1@%h
celery -A app.workers.celery_app worker -n worker2@%h
```

### Task Priorities
```python
# High priority tasks
celery_app.send_task(
    'check_budget_alerts',
    priority=9  # 0-9, 9 is highest
)
```

## Security

1. **Secure Redis**
```bash
# /etc/redis/redis.conf
bind 127.0.0.1
requirepass your-strong-password
```

2. **Update .env**
```bash
CELERY_BROKER_URL=redis://:your-strong-password@localhost:6379/0
```

## Verification Checklist

- [ ] Redis running and accessible
- [ ] Celery worker started
- [ ] Celery beat started
- [ ] Flower dashboard accessible (optional)
- [ ] Test task executes successfully
- [ ] Budget alerts working (check notifications)
- [ ] Logs show no errors

## Quick Start

```bash
# 1. Install Redis
brew install redis && brew services start redis

# 2. Start workers
cd backend
celery -A app.workers.celery_app worker -l info &
celery -A app.workers.celery_app beat -l info &

# 3. Verify
curl http://localhost:5555  # Flower (if running)

# 4. Test a task
celery -A app.workers.celery_app call check_budget_alerts
```

Done! Workers are now running. Check notifications in the UI.
