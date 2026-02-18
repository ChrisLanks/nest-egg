# Deployment Guide

This guide covers deploying Nest Egg in production using Docker (recommended) or manual deployment.

## Table of Contents
- [Docker Deployment (Recommended)](#docker-deployment-recommended)
- [Manual Deployment](#manual-deployment---celery-workers)
- [Monitoring](#monitoring)
- [Troubleshooting](#troubleshooting)

---

# Docker Deployment (Recommended)

Deploy Nest Egg as a multi-container application using Docker Compose.

## Architecture

```
┌─────────────────────────────────────────────────────┐
│                  Docker Network                      │
├─────────────────────────────────────────────────────┤
│                                                       │
│  ┌──────────┐   ┌──────────┐   ┌──────────┐        │
│  │ Frontend │   │ Backend  │   │PostgreSQL│        │
│  │  (nginx) │◄──┤ (FastAPI)│◄──┤    DB    │        │
│  │   :80    │   │  :8000   │   │  :5432   │        │
│  └──────────┘   └──────────┘   └──────────┘        │
│                       ▲                              │
│                       │                              │
│  ┌──────────┐   ┌────┴─────┐   ┌──────────┐        │
│  │  Celery  │   │  Redis   │   │  Flower  │        │
│  │  Worker  │◄──┤  Broker  │──►│(Monitor) │        │
│  │          │   │  :6379   │   │  :5555   │        │
│  └──────────┘   └──────────┘   └──────────┘        │
│       ▲                                              │
│       │                                              │
│  ┌────┴─────┐                                       │
│  │  Celery  │                                       │
│  │   Beat   │                                       │
│  │(Scheduler)│                                       │
│  └──────────┘                                       │
└─────────────────────────────────────────────────────┘
```

## Quick Start

```bash
# 1. Copy and configure environment file
cp .env.docker.example .env.docker
nano .env.docker  # Update all CHANGE_ME values

# 2. Generate secure keys
openssl rand -hex 32  # For SECRET_KEY
openssl rand -hex 32  # For MASTER_ENCRYPTION_KEY

# 3. Build and start all services
docker-compose --env-file .env.docker up -d

# 4. Run database migrations
docker-compose exec backend alembic upgrade head

# 5. Create first user (optional)
docker-compose exec backend python -m app.scripts.create_user

# 6. Verify all services are healthy
docker-compose ps
```

Access the application:
- Frontend: http://localhost (or configured port)
- Backend API: http://localhost:8000
- Flower (task monitor): http://localhost:5555
- API Docs: http://localhost:8000/docs

## Configuration

### Critical Environment Variables

Edit `.env.docker` and update these **REQUIRED** values:

```bash
# Security (MUST CHANGE)
SECRET_KEY=<generate-with-openssl-rand-hex-32>
MASTER_ENCRYPTION_KEY=<generate-with-openssl-rand-hex-32>
POSTGRES_PASSWORD=<strong-password>
ALLOWED_HOSTS=app.yourdomain.com,api.yourdomain.com

# Plaid API (Required for bank connections)
PLAID_CLIENT_ID=your_plaid_client_id
PLAID_SECRET=your_plaid_secret
PLAID_ENV=production  # or sandbox for testing

# Teller API (Optional alternative)
TELLER_APP_ID=your_teller_app_id
TELLER_API_KEY=your_teller_api_key
```

See `.env.docker.example` for complete configuration options.

## Production Deployment Steps

### 1. Prepare Server

```bash
# Install Docker and Docker Compose
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo apt-get install docker-compose-plugin

# Create deployment directory
sudo mkdir -p /opt/nest-egg
cd /opt/nest-egg

# Clone repository
git clone https://github.com/yourusername/nest-egg.git .
```

### 2. Configure Environment

```bash
# Copy and edit environment file
cp .env.docker.example .env.docker

# Generate secure keys
openssl rand -hex 32  # Use for SECRET_KEY
openssl rand -hex 32  # Use for MASTER_ENCRYPTION_KEY

# Edit configuration
nano .env.docker
```

**Production Checklist** (.env.docker):
- ✅ `ENVIRONMENT=production`
- ✅ `DEBUG=false`
- ✅ `SECRET_KEY` - Generated with openssl
- ✅ `MASTER_ENCRYPTION_KEY` - Generated with openssl
- ✅ `POSTGRES_PASSWORD` - Strong password (16+ characters)
- ✅ `ALLOWED_HOSTS` - Specific domains (NOT "*")
- ✅ `CORS_ORIGINS` - Specific domains (NOT localhost)
- ✅ `VITE_API_URL` - Production backend URL
- ✅ `PLAID_ENV=production` - Production Plaid credentials
- ✅ `LOG_FORMAT=json` - Structured logging

### 3. Build and Deploy

```bash
# Build images (first time or after code changes)
docker-compose --env-file .env.docker build

# Start all services in background
docker-compose --env-file .env.docker up -d

# Run database migrations
docker-compose exec backend alembic upgrade head

# Verify all services are healthy
docker-compose ps
```

### 4. SSL/TLS Configuration (Recommended)

Use a reverse proxy like nginx or Traefik for SSL/TLS termination.

**Example nginx reverse proxy:**

```nginx
# /etc/nginx/sites-available/nest-egg
server {
    listen 443 ssl http2;
    server_name app.yourdomain.com;

    ssl_certificate /etc/letsencrypt/live/yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/yourdomain.com/privkey.pem;

    # Frontend
    location / {
        proxy_pass http://localhost:80;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}

server {
    listen 443 ssl http2;
    server_name api.yourdomain.com;

    ssl_certificate /etc/letsencrypt/live/yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/yourdomain.com/privkey.pem;

    # Backend API
    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

## Docker Commands

### Service Management

```bash
# Start all services
docker-compose --env-file .env.docker up -d

# Stop all services
docker-compose down

# Restart specific service
docker-compose restart backend

# View logs
docker-compose logs -f backend
docker-compose logs -f celery-worker

# Check service status
docker-compose ps

# View resource usage
docker stats
```

### Updates and Maintenance

```bash
# Pull latest code
git pull origin main

# Rebuild and restart
docker-compose --env-file .env.docker build
docker-compose --env-file .env.docker up -d

# Run new migrations
docker-compose exec backend alembic upgrade head

# Prune old images (save disk space)
docker system prune -a
```

### Database Management

```bash
# Backup database
docker-compose exec postgres pg_dump -U nestegg nestegg > backup_$(date +%Y%m%d).sql

# Restore database
cat backup_20240115.sql | docker-compose exec -T postgres psql -U nestegg nestegg

# Access PostgreSQL shell
docker-compose exec postgres psql -U nestegg

# View database logs
docker-compose logs -f postgres
```

### Debugging

```bash
# Access backend shell
docker-compose exec backend bash

# Run Python commands
docker-compose exec backend python

# Access logs
docker-compose logs -f backend
docker-compose logs -f celery-worker
docker-compose logs -f celery-beat

# Inspect network
docker network inspect nest-egg_nestegg-network

# Check volumes
docker volume ls
docker volume inspect nest-egg_postgres_data
```

## Monitoring

### Health Checks

All services have built-in health checks:

```bash
# Check all service health
docker-compose ps

# Backend health endpoint
curl http://localhost:8000/health

# Frontend health endpoint
curl http://localhost/health

# Redis health
docker-compose exec redis redis-cli ping
```

### Celery Monitoring (Flower)

Access Flower at http://localhost:5555 (or configured port)

Default credentials (from .env.docker):
- Username: admin
- Password: (set in FLOWER_PASSWORD)

### Logs and Metrics

```bash
# View all logs
docker-compose logs -f

# View specific service logs
docker-compose logs -f backend
docker-compose logs -f celery-worker
docker-compose logs -f postgres

# Export logs to file
docker-compose logs > deployment_logs_$(date +%Y%m%d).txt
```

## Scaling

### Horizontal Scaling

Scale Celery workers:

```bash
# Run 4 worker instances
docker-compose --env-file .env.docker up -d --scale celery-worker=4

# Check worker status in Flower
open http://localhost:5555
```

### Vertical Scaling

Edit `docker-compose.yml` to adjust resource limits:

```yaml
services:
  backend:
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 4G
        reservations:
          cpus: '1'
          memory: 2G
```

## Security Best Practices

1. **Never commit `.env.docker`** - Contains secrets
2. **Use strong passwords** - 16+ characters for database
3. **Rotate keys regularly** - SECRET_KEY, API keys
4. **Enable SSL/TLS** - Use reverse proxy with Let's Encrypt
5. **Restrict network access** - Firewall rules for PostgreSQL/Redis
6. **Keep images updated** - Rebuild regularly for security patches
7. **Monitor logs** - Set up alerts for errors

## Backup Strategy

### Automated Backups

Add to crontab:

```bash
# Daily database backup at 2 AM
0 2 * * * cd /opt/nest-egg && docker-compose exec -T postgres pg_dump -U nestegg nestegg | gzip > /backups/nest-egg_$(date +\%Y\%m\%d).sql.gz

# Keep only last 7 days
0 3 * * * find /backups/nest-egg_*.sql.gz -mtime +7 -delete
```

### Volume Backups

```bash
# Backup PostgreSQL volume
docker run --rm \
  -v nest-egg_postgres_data:/data \
  -v $(pwd):/backup \
  alpine tar czf /backup/postgres_backup.tar.gz /data

# Backup Redis volume
docker run --rm \
  -v nest-egg_redis_data:/data \
  -v $(pwd):/backup \
  alpine tar czf /backup/redis_backup.tar.gz /data
```

## Troubleshooting Docker

### Services won't start

```bash
# Check logs
docker-compose logs

# Check specific service
docker-compose logs backend

# Verify environment file
cat .env.docker

# Check port conflicts
netstat -tuln | grep -E '80|8000|5432|6379|5555'
```

### Database connection errors

```bash
# Check PostgreSQL is running
docker-compose ps postgres

# Check PostgreSQL logs
docker-compose logs postgres

# Test connection
docker-compose exec backend python -c "from app.core.database import engine; print(engine)"
```

### Build failures

```bash
# Clean build
docker-compose down -v
docker system prune -a
docker-compose --env-file .env.docker build --no-cache

# Check disk space
df -h
```

---

# Manual Deployment - Celery Workers

For non-Docker deployments, follow these instructions.

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
