# Deployment & Self-Hosting

This guide covers deploying Nest Egg in production using Docker Compose (recommended) or manual deployment.

## Architecture

```
┌─────────────────────────────────────────────────────┐
│                  Docker Network                      │
├─────────────────────────────────────────────────────┤
│                                                      │
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
│  ┌────┴─────┐                                       │
│  │  Celery  │                                       │
│  │   Beat   │                                       │
│  └──────────┘                                       │
└─────────────────────────────────────────────────────┘
```

| Service | Purpose | Port |
|---------|---------|------|
| **frontend** | React/Vite UI | 80 (prod) / 3000 (dev) |
| **backend** | FastAPI API | 8000 |
| **postgres** | Database | 5432 |
| **redis** | Cache & Celery broker | 6379 |
| **celery-worker** | Background tasks | -- |
| **celery-beat** | Task scheduler | -- |
| **celery-flower** | Task monitor UI | 5555 |

---

## Quick Start (Docker Compose)

```bash
# 1. Copy and configure environment
cp .env.docker.example .env.docker
nano .env.docker   # Update all CHANGE_ME values

# 2. Generate secure keys
openssl rand -hex 32   # For SECRET_KEY
openssl rand -hex 32   # For MASTER_ENCRYPTION_KEY

# 3. Build and start all services
docker-compose --env-file .env.docker up -d

# 4. Run database migrations
docker-compose exec backend alembic upgrade head

# 5. Create first user (optional)
docker-compose exec backend python -m app.scripts.create_user

# 6. Verify
docker-compose ps
curl http://localhost:8000/health
# -> {"status": "healthy", "checks": {"database": "ok"}}
```

Access points: Frontend http://localhost, API http://localhost:8000, Swagger http://localhost:8000/docs, Flower http://localhost:5555.

> **Production helper scripts:** `./scripts/prod/setup.sh` handles initial configuration; `./scripts/prod/run.sh` starts services with production defaults.

---

## Production Checklist

Before going live, verify every item:

- [ ] `ENVIRONMENT=production` and `DEBUG=false`
- [ ] `SECRET_KEY` -- randomly generated, at least 32 characters
- [ ] `MASTER_ENCRYPTION_KEY` -- Fernet key for PII encryption at rest
- [ ] `POSTGRES_PASSWORD` -- strong password (16+ characters)
- [ ] `ALLOWED_HOSTS` -- specific domain(s), **not** `*`
- [ ] `CORS_ORIGINS` -- specific origin(s), **not** `*` or localhost
- [ ] `APP_BASE_URL` -- public HTTPS URL (not localhost)
- [ ] `VITE_API_URL` -- production backend URL
- [ ] `METRICS_PASSWORD` -- changed from default
- [ ] `PLAID_ENV=production` with production Plaid credentials
- [ ] `LOG_FORMAT=json` -- structured logging enabled
- [ ] HTTPS termination configured at reverse proxy / load balancer
- [ ] PostgreSQL with SSL (not SQLite)
- [ ] Redis password-protected
- [ ] Automated backups configured (see [Database](#database))

### SSL/TLS

Use a reverse proxy (Nginx, Caddy, Traefik) for TLS termination with Let's Encrypt. Point `app.yourdomain.com` to the frontend (port 80) and `api.yourdomain.com` to the backend (port 8000). Set `proxy_set_header` for `Host`, `X-Real-IP`, `X-Forwarded-For`, and `X-Forwarded-Proto`.

### Security Best Practices

1. **Never commit `.env.docker`** -- it contains secrets.
2. **Rotate keys regularly** -- SECRET_KEY, MASTER_ENCRYPTION_KEY, API keys.
3. **Restrict network access** -- firewall rules for PostgreSQL (5432) and Redis (6379).
4. **Keep images updated** -- rebuild regularly for security patches.
5. **Limit container resources** -- set CPU/memory limits in `docker-compose.yml`.

---

## Environment Configuration

For the full environment variable reference, see [docs/configuration.md](./configuration.md).

### Workflow

1. Copy the example file: `cp .env.docker.example .env.docker`
2. Generate secrets:
   ```bash
   openssl rand -hex 32                  # SECRET_KEY
   python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"  # MASTER_ENCRYPTION_KEY
   ```
3. Edit `.env.docker` and replace every `CHANGE_ME` value.
4. For **staging**, set `ENVIRONMENT=staging` and use sandbox API credentials.
5. For **production**, complete the [Production Checklist](#production-checklist).

### Critical Variables (Quick Reference)

| Variable | How to generate |
|---|---|
| `SECRET_KEY` | `openssl rand -hex 32` |
| `MASTER_ENCRYPTION_KEY` | Fernet key (see above) |
| `DATABASE_URL` | `postgresql+asyncpg://user:pass@host:5432/nestegg` |
| `REDIS_URL` | `redis://host:6379/0` |
| `ALLOWED_HOSTS` | `app.yourdomain.com,api.yourdomain.com` |
| `CORS_ORIGINS` | `https://app.yourdomain.com` |

---

## Docker Commands Reference

### Service Management

```bash
docker-compose --env-file .env.docker up -d          # Start all services
docker-compose down                                   # Stop (keeps data)
docker-compose down -v                                # Stop + remove volumes (DESTROYS DATA)
docker-compose restart backend                        # Restart one service
docker-compose ps                                     # Check status
docker stats                                          # Resource usage
```

### Logs

```bash
docker-compose logs -f                                # All services
docker-compose logs -f backend                        # Specific service
docker-compose logs --tail=100 backend                # Last N lines
docker-compose logs --since 2025-01-15T10:00:00 backend
docker-compose logs > logs_$(date +%Y%m%d).txt        # Export
```

### Shell Access

```bash
docker-compose exec backend bash                      # Backend shell
docker-compose exec backend python                    # Python REPL
docker-compose exec postgres psql -U nestegg          # PostgreSQL shell
docker-compose exec redis redis-cli                   # Redis CLI
```

### Updates

```bash
git pull origin main
docker-compose --env-file .env.docker build
docker-compose --env-file .env.docker up -d
docker-compose exec backend alembic upgrade head
docker system prune -a                                # Reclaim disk space
```

---

## Database

### Migrations

```bash
docker-compose exec backend alembic upgrade head
docker-compose exec backend alembic revision --autogenerate -m "description"
```

### Backup & Restore

```bash
# SQL backup
docker-compose exec postgres pg_dump -U nestegg nestegg > backup_$(date +%Y%m%d).sql

# Compressed backup
docker-compose exec postgres pg_dump -U nestegg -Fc nestegg > backup_$(date +%Y%m%d).dump

# Restore from SQL
cat backup.sql | docker-compose exec -T postgres psql -U nestegg nestegg

# Restore from compressed dump
docker-compose exec -T postgres pg_restore -U nestegg -d nestegg --clean backup.dump
```

### Automated Backups

Add to crontab (`crontab -e`):

```cron
# Daily database backup at 2 AM, retain 7 days
0 2 * * * cd /opt/nest-egg && docker-compose exec -T postgres pg_dump -U nestegg nestegg | gzip > /backups/nestegg_$(date +\%Y\%m\%d).sql.gz
0 3 * * * find /backups/nestegg_*.sql.gz -mtime +7 -delete
```

### Data Retention

For compliance (GDPR, SOX), configure automatic purging:

```env
DATA_RETENTION_DAYS=2555          # ~7 years
DATA_RETENTION_DRY_RUN=true       # Start with dry-run to verify
```

The retention task runs daily at 3:30 AM UTC. Once satisfied with dry-run output, set `DATA_RETENTION_DRY_RUN=false`.

---

## Scaling

### Database Connection Pool

```env
DB_POOL_SIZE=50        # Default: 20
DB_MAX_OVERFLOW=20     # Default: 10
```

Rule of thumb: `DB_POOL_SIZE` ~ `(number of uvicorn workers) * 2`.

### Celery Workers

```bash
# Scale workers horizontally (Docker)
docker-compose --env-file .env.docker up -d --scale celery-worker=4

# Increase concurrency within a single worker
celery -A app.workers.celery_app worker --concurrency=4 --loglevel=info

# Dedicated queue for heavy tasks
celery -A app.workers.celery_app worker -Q heavy --concurrency=2
```

### Redis

Split cache and broker onto separate instances if Redis becomes a bottleneck:

```env
REDIS_URL=redis://redis-cache:6379/0
CELERY_BROKER_URL=redis://redis-broker:6379/0
```

### Vertical Scaling

Set resource limits in `docker-compose.yml`:

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

---

## Encryption Key Rotation

Generate the initial key:

```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

To rotate:

1. Copy current `MASTER_ENCRYPTION_KEY` to `ENCRYPTION_KEY_V1`.
2. Generate a new `MASTER_ENCRYPTION_KEY`.
3. Increment `ENCRYPTION_CURRENT_VERSION` (e.g., 1 to 2).
4. Deploy -- new writes use the new key; old data still decrypts via V1.

```env
MASTER_ENCRYPTION_KEY=<new-key>
ENCRYPTION_KEY_V1=<old-key>
ENCRYPTION_CURRENT_VERSION=2
```

---

## Identity Provider Setup

Nest Egg supports pluggable identity providers. The default is the built-in JWT system.

### AWS Cognito

```env
IDENTITY_PROVIDER_CHAIN=cognito,builtin
IDP_COGNITO_ISSUER=https://cognito-idp.us-east-1.amazonaws.com/us-east-1_XXXXXXX
IDP_COGNITO_CLIENT_ID=your-client-id
IDP_COGNITO_ADMIN_GROUP=nest-egg-admins
```

### Keycloak

```env
IDENTITY_PROVIDER_CHAIN=keycloak,builtin
IDP_KEYCLOAK_ISSUER=https://keycloak.example.com/realms/nest-egg
IDP_KEYCLOAK_CLIENT_ID=your-client-id
```

### Okta

```env
IDENTITY_PROVIDER_CHAIN=okta,builtin
IDP_OKTA_ISSUER=https://company.okta.com/oauth2/default
IDP_OKTA_CLIENT_ID=your-client-id
```

### Google

```env
IDENTITY_PROVIDER_CHAIN=google,builtin
IDP_GOOGLE_CLIENT_ID=your-google-oauth-client-id
```

---

## Monitoring & Health Checks

For the full monitoring guide (Prometheus dashboards, alerting rules, Grafana setup), see [docs/MONITORING.md](./MONITORING.md).

### Health Endpoints

```bash
curl http://localhost:8000/health          # Backend: 200 healthy / 503 unhealthy
curl http://localhost/health               # Frontend
docker-compose exec redis redis-cli ping   # Redis
```

### Docker HEALTHCHECK

```dockerfile
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
  CMD curl -f http://localhost:8000/health || exit 1
```

### Kubernetes Liveness Probe

```yaml
livenessProbe:
  httpGet:
    path: /health
    port: 8000
  initialDelaySeconds: 10
  periodSeconds: 30
```

### Prometheus Metrics

Metrics are served on a separate port (default 9090) with basic auth:

```bash
curl -u admin:$METRICS_PASSWORD http://localhost:9090/metrics
```

### Structured Logging & Sentry

```env
LOG_FORMAT=json                            # For ELK, Datadog, etc.
LOG_LEVEL=INFO
SENTRY_DSN=https://your-sentry-dsn@sentry.io/123
```

### Celery Monitoring (Flower)

Access Flower at http://localhost:5555. Credentials are set via `FLOWER_PASSWORD` in `.env.docker`.

---

## Scheduled Tasks

| Task | Schedule | Purpose |
|------|----------|---------|
| `check_budget_alerts` | Daily 00:00 | Notify users of budget overruns |
| `detect_recurring_patterns` | Monday 02:00 | Find subscription patterns |
| `check_cash_flow_forecast` | Daily 06:30 | Alert on negative balance projections |
| `update_holdings_prices` | Daily 18:00 | Refresh market prices |
| `capture_daily_holdings_snapshot` | Daily 23:59 | Portfolio history tracking |

---

## Manual Deployment (Non-Docker)

Requirements: Python 3.11+, Node.js 18+, PostgreSQL 15+, Redis 7+.

### Celery Workers

```bash
cd backend
celery -A app.workers.celery_app worker --loglevel=info   # Terminal 1
celery -A app.workers.celery_app beat --loglevel=info      # Terminal 2
celery -A app.workers.celery_app flower                    # Terminal 3 (optional)
```

### Systemd Services (Production)

Create `/etc/systemd/system/nest-egg-worker.service`:

```ini
[Unit]
Description=Nest Egg Celery Worker
After=network.target redis.service

[Service]
Type=forking
User=nest-egg
WorkingDirectory=/var/www/nest-egg/backend
Environment="PATH=/var/www/nest-egg/backend/venv/bin"
ExecStart=/var/www/nest-egg/backend/venv/bin/celery -A app.workers.celery_app worker \
    --detach --pidfile=/var/run/celery/worker.pid \
    --logfile=/var/log/celery/worker.log --loglevel=info

[Install]
WantedBy=multi-user.target
```

Create a matching `nest-egg-beat.service` for the scheduler, then:

```bash
sudo systemctl daemon-reload
sudo systemctl enable nest-egg-worker nest-egg-beat
sudo systemctl start nest-egg-worker nest-egg-beat
```

---

## Troubleshooting

### Services Won't Start

```bash
docker-compose logs                           # Check all logs
docker-compose logs backend                   # Check specific service
netstat -tuln | grep -E '80|8000|5432|6379'   # Port conflicts
lsof -i :8000                                 # Find process on port
```

### Database Connection Errors

```bash
docker-compose ps postgres                    # Is it running?
docker-compose logs postgres                  # Check logs
docker-compose restart postgres               # Restart
```

### Frontend Not Loading

```bash
docker-compose logs frontend
docker-compose build frontend && docker-compose up -d frontend
curl http://localhost:8000/health              # Verify backend is reachable
```

### Celery Tasks Not Running

```bash
docker-compose ps celery-worker celery-beat
docker-compose logs celery-worker
docker-compose exec redis redis-cli ping
docker-compose exec backend celery -A app.workers.celery_app call check_budget_alerts
```

### Build Failures / Disk Space

```bash
docker-compose down -v
docker system prune -a
docker-compose --env-file .env.docker build --no-cache
df -h
```

### High Worker Memory

Restart workers periodically via crontab:

```cron
0 3 * * * cd /opt/nest-egg && docker-compose restart celery-worker
```
