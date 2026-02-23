# Self-Hosting Guide

This guide covers deploying Nest Egg in production for enterprise or personal self-hosted use.

## Prerequisites

- Docker & Docker Compose (recommended) or a Linux server with Python 3.11+, Node.js 18+, PostgreSQL 15+, and Redis 7+
- A domain name with HTTPS (via reverse proxy like Nginx, Caddy, or a cloud load balancer)

## Quick Start (Docker Compose)

```bash
# 1. Clone and configure
cp backend/.env.example backend/.env
# Edit backend/.env — see "Required Environment Variables" below

# 2. Start services
docker compose up -d

# 3. Run database migrations
docker compose exec backend alembic upgrade head

# 4. Verify
curl http://localhost:8000/health
# → {"status": "healthy", "checks": {"database": "ok"}}
```

## Required Environment Variables

These **must** be set before starting the app in production:

| Variable | How to generate |
|---|---|
| `SECRET_KEY` | `openssl rand -hex 32` |
| `MASTER_ENCRYPTION_KEY` | `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"` |
| `DATABASE_URL` | `postgresql+asyncpg://user:pass@host:5432/nestegg` |
| `REDIS_URL` | `redis://host:6379/0` |
| `ENVIRONMENT` | `production` |
| `ALLOWED_HOSTS` | `app.yourdomain.com,api.yourdomain.com` |
| `CORS_ORIGINS` | `https://app.yourdomain.com` |
| `APP_BASE_URL` | `https://app.yourdomain.com` |
| `METRICS_PASSWORD` | Any strong password (not the default) |

See `backend/.env.example` for the full list with descriptions.

## Production Checklist

- [ ] `ENVIRONMENT=production` — enables security validators (rejects insecure defaults)
- [ ] `SECRET_KEY` — at least 32 characters, randomly generated
- [ ] `MASTER_ENCRYPTION_KEY` — Fernet key for PII encryption at rest
- [ ] `ALLOWED_HOSTS` — specific domain(s), not `*`
- [ ] `CORS_ORIGINS` — specific origin(s), not `*`
- [ ] `APP_BASE_URL` — public HTTPS URL (not localhost)
- [ ] `METRICS_PASSWORD` — changed from default
- [ ] HTTPS termination — configured at reverse proxy / load balancer
- [ ] Database — PostgreSQL with SSL, not SQLite
- [ ] Redis — password-protected in production
- [ ] Backups — automated (see below)

## Database Backup & Restore

### Backup (Docker)

```bash
# Full backup
docker compose exec db pg_dump -U nestegg nestegg_prod > backup_$(date +%Y%m%d).sql

# Compressed backup
docker compose exec db pg_dump -U nestegg -Fc nestegg_prod > backup_$(date +%Y%m%d).dump
```

### Restore (Docker)

```bash
# From SQL file
docker compose exec -T db psql -U nestegg nestegg_prod < backup_20260101.sql

# From compressed dump
docker compose exec -T db pg_restore -U nestegg -d nestegg_prod --clean backup_20260101.dump
```

### Automated Backups

Add to your crontab (`crontab -e`):

```
0 2 * * * docker compose -f /path/to/docker-compose.yml exec -T db pg_dump -U nestegg -Fc nestegg_prod > /backups/nestegg_$(date +\%Y\%m\%d).dump
```

## Scaling

### Database Connection Pool

For high-traffic deployments, increase the connection pool:

```env
DB_POOL_SIZE=50        # Default: 20
DB_MAX_OVERFLOW=20     # Default: 10
```

Rule of thumb: `DB_POOL_SIZE` should be roughly `(number of uvicorn workers) * 2`.

### Celery Workers

Scale background job processing:

```bash
# Start multiple workers
celery -A app.workers.celery_app worker --concurrency=4 --loglevel=info

# Separate worker for heavy tasks
celery -A app.workers.celery_app worker -Q heavy --concurrency=2
```

### Redis

If Redis becomes a bottleneck:

```env
# Use separate Redis instances for cache vs. Celery broker
REDIS_URL=redis://redis-cache:6379/0
CELERY_BROKER_URL=redis://redis-broker:6379/0
```

## Data Retention

For compliance (e.g., GDPR, SOX), configure automatic purging of old transactions:

```env
# Keep 7 years of transaction history (~2555 days)
DATA_RETENTION_DAYS=2555

# IMPORTANT: Start with dry-run mode to verify what would be deleted
DATA_RETENTION_DRY_RUN=true
```

The retention task runs daily at 3:30 AM UTC. Check logs for:

```
Data retention DRY RUN: org=... would delete 1234 transactions older than 2019-02-23
```

Once satisfied, set `DATA_RETENTION_DRY_RUN=false` to enable actual deletion.

## Encryption Key Management

### Initial Setup

```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
# → set this as MASTER_ENCRYPTION_KEY
```

### Key Rotation

1. Copy the current `MASTER_ENCRYPTION_KEY` to `ENCRYPTION_KEY_V1`
2. Generate a new `MASTER_ENCRYPTION_KEY`
3. Increment `ENCRYPTION_CURRENT_VERSION` (e.g., 1 → 2)
4. Deploy — new writes use the new key; old data still decrypts via V1

```env
MASTER_ENCRYPTION_KEY=<new-key>
ENCRYPTION_KEY_V1=<old-key>
ENCRYPTION_CURRENT_VERSION=2
```

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

## Health Checks

The `/health` endpoint checks database connectivity and returns:

- **200** `{"status": "healthy", "checks": {"database": "ok"}}` — all good
- **503** `{"status": "unhealthy", "checks": {"database": "unreachable"}}` — restart needed

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

## Monitoring

### Prometheus Metrics

Metrics are served on a separate port (default 9090) with basic auth:

```bash
curl -u admin:$METRICS_PASSWORD http://localhost:9090/metrics
```

### Structured Logging

Set `LOG_FORMAT=json` in production for structured log aggregation (ELK, Datadog, etc.):

```env
LOG_FORMAT=json
LOG_LEVEL=INFO
```

### Sentry Error Tracking

```env
SENTRY_DSN=https://your-sentry-dsn@sentry.io/123
```
