# Docker Quick Reference - Nest Egg

Quick commands for Docker development and deployment.

## Quick Start

### Development Mode

```bash
# Start all services with hot-reload
docker-compose -f docker-compose.dev.yml up

# Run in background
docker-compose -f docker-compose.dev.yml up -d

# View logs
docker-compose -f docker-compose.dev.yml logs -f

# Stop services
docker-compose -f docker-compose.dev.yml down
```

Access:
- Frontend: http://localhost:3000 (Vite dev server with HMR)
- Backend: http://localhost:8000
- API Docs: http://localhost:8000/docs
- Flower: http://localhost:5555

### Production Mode

```bash
# Configure environment
cp .env.docker.example .env.docker
nano .env.docker  # Update all CHANGE_ME values

# Build and start
docker-compose --env-file .env.docker up -d

# Run migrations
docker-compose exec backend alembic upgrade head

# Check status
docker-compose ps
```

Access:
- Frontend: http://localhost (port 80)
- Backend: http://localhost:8000
- Flower: http://localhost:5555

---

## Common Commands

### Service Management

```bash
# Start all services
docker-compose up -d

# Stop all services (keeps data)
docker-compose down

# Stop and remove volumes (DESTROYS DATA)
docker-compose down -v

# Restart a service
docker-compose restart backend

# Rebuild after code changes
docker-compose build
docker-compose up -d
```

### Logs

```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f backend
docker-compose logs -f celery-worker

# Last 100 lines
docker-compose logs --tail=100 backend

# Logs since timestamp
docker-compose logs --since 2024-01-15T10:00:00 backend
```

### Database Operations

```bash
# Run migrations
docker-compose exec backend alembic upgrade head

# Create new migration
docker-compose exec backend alembic revision --autogenerate -m "description"

# Access PostgreSQL shell
docker-compose exec postgres psql -U nestegg

# Backup database
docker-compose exec postgres pg_dump -U nestegg nestegg > backup.sql

# Restore database
cat backup.sql | docker-compose exec -T postgres psql -U nestegg nestegg

# Reset database (DESTROYS DATA)
docker-compose down -v
docker-compose up -d postgres
docker-compose exec backend alembic upgrade head
```

### Shell Access

```bash
# Backend Python shell
docker-compose exec backend bash
docker-compose exec backend python

# Access Redis CLI
docker-compose exec redis redis-cli

# Access PostgreSQL
docker-compose exec postgres psql -U nestegg nestegg

# Frontend shell (dev mode only)
docker-compose exec frontend sh
```

### Debugging

```bash
# Check container status
docker-compose ps

# Inspect service logs
docker-compose logs --tail=50 backend

# Check resource usage
docker stats

# Inspect container
docker inspect nestegg-backend

# Test backend health
curl http://localhost:8000/health

# Test Redis connection
docker-compose exec redis redis-cli ping
```

---

## Development Workflow

### Initial Setup

```bash
# 1. Start infrastructure
docker-compose -f docker-compose.dev.yml up -d postgres redis

# 2. Run migrations
docker-compose -f docker-compose.dev.yml exec backend alembic upgrade head

# 3. Create test user (optional)
docker-compose -f docker-compose.dev.yml exec backend python -m app.scripts.create_user

# 4. Start all services
docker-compose -f docker-compose.dev.yml up -d
```

### Code Changes

**Backend changes** (auto-reload enabled):
- Edit Python files in `./backend`
- Uvicorn automatically reloads
- Watch logs: `docker-compose logs -f backend`

**Frontend changes** (HMR enabled):
- Edit React files in `./frontend`
- Vite hot-reloads in browser
- Watch logs: `docker-compose logs -f frontend`

**Database changes**:
```bash
# Create migration
docker-compose exec backend alembic revision --autogenerate -m "add new field"

# Apply migration
docker-compose exec backend alembic upgrade head
```

### Testing

```bash
# Run backend tests
docker-compose exec backend pytest

# Run with coverage
docker-compose exec backend pytest --cov=app --cov-report=html

# Run specific test
docker-compose exec backend pytest tests/unit/test_budget_service.py

# Frontend tests
docker-compose exec frontend npm test
```

### Celery Tasks

```bash
# View active workers
docker-compose exec celery-worker celery -A app.workers.celery_app inspect active

# View scheduled tasks
docker-compose exec celery-beat celery -A app.workers.celery_app inspect scheduled

# Manually trigger a task
docker-compose exec backend celery -A app.workers.celery_app call check_budget_alerts

# Monitor in Flower
open http://localhost:5555
```

---

## Production Deployment

### Pre-deployment Checklist

```bash
# ✅ Update .env.docker
# ✅ Generate secure keys: openssl rand -hex 32
# ✅ Set ENVIRONMENT=production
# ✅ Set DEBUG=false
# ✅ Configure ALLOWED_HOSTS
# ✅ Configure CORS_ORIGINS
# ✅ Update Plaid to production credentials
# ✅ Review security settings
```

### Deploy Commands

```bash
# Build production images
docker-compose --env-file .env.docker build

# Start services
docker-compose --env-file .env.docker up -d

# Run migrations
docker-compose exec backend alembic upgrade head

# Verify health
docker-compose ps
curl http://localhost:8000/health
curl http://localhost/health

# Monitor logs
docker-compose logs -f
```

### Updates

```bash
# Pull latest code
git pull origin main

# Rebuild images
docker-compose --env-file .env.docker build

# Restart services (zero-downtime with health checks)
docker-compose --env-file .env.docker up -d

# Run new migrations
docker-compose exec backend alembic upgrade head

# Verify
docker-compose ps
```

---

## Troubleshooting

### Containers won't start

```bash
# Check status
docker-compose ps

# Check logs
docker-compose logs

# Check ports
netstat -tuln | grep -E '80|8000|5432|6379|5555'

# Remove and recreate
docker-compose down
docker-compose up -d
```

### Database connection errors

```bash
# Check PostgreSQL is running
docker-compose ps postgres

# Check PostgreSQL logs
docker-compose logs postgres

# Test connection
docker-compose exec backend python -c "from app.core.database import engine; print('Connected!')"

# Restart database
docker-compose restart postgres
```

### Frontend not loading

```bash
# Check if frontend is running
docker-compose ps frontend

# Check frontend logs
docker-compose logs frontend

# Rebuild frontend
docker-compose build frontend
docker-compose up -d frontend

# Check API connection
curl http://localhost:8000/health
```

### Celery tasks not running

```bash
# Check worker status
docker-compose ps celery-worker celery-beat

# Check worker logs
docker-compose logs celery-worker
docker-compose logs celery-beat

# Check Redis
docker-compose exec redis redis-cli ping

# Check Flower
open http://localhost:5555

# Manually trigger task
docker-compose exec backend celery -A app.workers.celery_app call check_budget_alerts
```

### Out of disk space

```bash
# Check disk usage
docker system df

# Remove unused images
docker image prune -a

# Remove stopped containers
docker container prune

# Remove unused volumes (BE CAREFUL)
docker volume prune

# Complete cleanup (DESTROYS ALL DOCKER DATA)
docker system prune -a --volumes
```

### Port already in use

```bash
# Find process using port
lsof -i :8000
lsof -i :5432

# Kill process
kill -9 <PID>

# Or change port in docker-compose.yml
# ports:
#   - "8001:8000"  # Map to different host port
```

---

## Environment Variables

### Development (.env or inline)

```bash
PLAID_CLIENT_ID=your_sandbox_client_id
PLAID_SECRET=your_sandbox_secret
```

### Production (.env.docker)

See `.env.docker.example` for complete list. Critical variables:

- `SECRET_KEY` - JWT signing (generate with openssl)
- `MASTER_ENCRYPTION_KEY` - Data encryption (generate with openssl)
- `POSTGRES_PASSWORD` - Database password
- `ALLOWED_HOSTS` - Allowed domain names
- `CORS_ORIGINS` - Frontend origins
- `PLAID_CLIENT_ID`, `PLAID_SECRET` - Plaid API credentials
- `ENVIRONMENT=production` - Production mode
- `DEBUG=false` - Disable debug mode

---

## Best Practices

### Development

1. **Use dev compose file**: `docker-compose -f docker-compose.dev.yml`
2. **Enable hot-reload**: Source code is mounted as volumes
3. **Check logs frequently**: `docker-compose logs -f`
4. **Reset when needed**: `docker-compose down -v` to start fresh

### Production

1. **Use .env.docker**: Never hardcode secrets
2. **Enable health checks**: All services have healthcheck configured
3. **Monitor logs**: Set up log aggregation (ELK, Datadog, etc.)
4. **Backup regularly**: Automated daily backups of PostgreSQL
5. **Update frequently**: Security patches and bug fixes
6. **Use SSL/TLS**: Reverse proxy with Let's Encrypt
7. **Limit resources**: Set memory/CPU limits in docker-compose.yml

---

## Architecture

### Services

| Service | Purpose | Port | Dependencies |
|---------|---------|------|--------------|
| **frontend** | React/Vite UI | 80/3000 | backend |
| **backend** | FastAPI API | 8000 | postgres, redis |
| **postgres** | Database | 5432 | - |
| **redis** | Cache/Broker | 6379 | - |
| **celery-worker** | Background tasks | - | postgres, redis, backend |
| **celery-beat** | Task scheduler | - | postgres, redis, backend |
| **celery-flower** | Task monitor | 5555 | redis |

### Data Flow

```
User → Frontend → Backend → PostgreSQL
                    ↓
                  Redis
                    ↓
              Celery Workers
```

### Volumes

- `postgres_data` - PostgreSQL database files
- `redis_data` - Redis persistence files

**⚠️ WARNING**: Running `docker-compose down -v` will delete all data!

---

## Additional Resources

- **Full Deployment Guide**: See [DEPLOYMENT.md](./DEPLOYMENT.md)
- **Application Documentation**: See [README.md](./README.md)
- **Docker Compose Reference**: https://docs.docker.com/compose/
- **Docker Documentation**: https://docs.docker.com/
