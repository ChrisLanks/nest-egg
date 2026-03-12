# Troubleshooting & Common Tasks

## Common Issues

### Notification Bell Not Updating

**Symptoms**: No unread count, notifications not appearing

```bash
# Check backend logs
docker compose logs backend | grep notification

# Test notification endpoint
curl -X POST http://localhost:8000/api/v1/notifications/test \
  -H "Authorization: Bearer <your-token>"

# Check Redis connection
docker compose exec redis redis-cli ping
# Should return: PONG
```

### Celery Tasks Not Running

**Symptoms**: Budget alerts not firing, snapshots not captured

```bash
# Check Celery worker status
docker compose logs celery-worker

# Check Celery beat (scheduler)
docker compose logs celery-beat

# View task queue in Flower
open http://localhost:5555

# Manually trigger task
celery -A app.workers.celery_app call check_budget_alerts
```

Without Celery running:
- Budget alerts won't fire
- Recurring transactions won't be detected
- Portfolio snapshots won't be captured
- Cash flow forecasts won't generate alerts

### Duplicate Transactions After CSV Import

**Diagnosis**:
```sql
-- Check transaction hashes
SELECT id, merchant_name, amount, transaction_hash
FROM transactions
WHERE merchant_name = 'Starbucks'
ORDER BY date DESC
LIMIT 10;

-- Check for NULL hashes (should not exist)
SELECT COUNT(*) FROM transactions WHERE transaction_hash IS NULL;
```

**Solution**:
```bash
# Backfill missing hashes (if needed)
cd backend
python app/scripts/backfill_transaction_hashes.py
```

### Teller Sync Failing

**Symptoms**: "Sync failed" error, old transactions

```bash
# Check Teller logs
docker compose logs backend | grep -i teller

# Test Teller connection
curl -X GET http://localhost:8000/api/v1/teller/test-connection \
  -H "Authorization: Bearer <your-token>"

# Re-link account
# Dashboard -> Account -> "Re-link Account" button
```

### Yahoo Finance Price Fetch Failing

**Symptoms**: "Failed to fetch quote" errors, stale prices

```bash
# Test Yahoo Finance manually
curl -X GET "http://localhost:8000/api/v1/market-data/quote/AAPL" \
  -H "Authorization: Bearer <your-token>"

# Yahoo Finance uses standard symbols: AAPL, GOOGL, SPY, etc.
```

### Database Migration Issues

**Symptoms**: "relation does not exist" errors

```bash
cd backend

# Check current migration
alembic current

# Check pending migrations
alembic history

# Run migrations
alembic upgrade head

# Rollback if needed
alembic downgrade -1
```

### Frontend Not Loading

**Symptoms**: Blank page, API connection errors

```bash
# Check API is running
curl http://localhost:8000/health

# Check frontend environment
cat frontend/.env
# VITE_API_URL should be http://localhost:8000

# Clear browser cache: Ctrl+Shift+R (hard refresh)

# Reinstall dependencies
cd frontend && rm -rf node_modules && npm install && npm run dev
```

## Debugging Tips

### Enable Debug Logging

Set `DB_ECHO=true` in `backend/.env` to log all SQL queries (very verbose).

Set `LOG_LEVEL=DEBUG` for detailed application logging.

### Check Celery Task Status

```bash
# List registered tasks
celery -A app.workers.celery_app inspect registered

# Check active tasks
celery -A app.workers.celery_app inspect active

# Check scheduled tasks (beat schedule)
celery -A app.workers.celery_app inspect scheduled
```

## Common Tasks

### Add New User to Household

```bash
# Via UI (recommended):
# 1. Login as admin user
# 2. Navigate to Household Settings
# 3. Click "Invite Member"
# 4. Enter email address
# 5. New user registers and accepts invitation

# Via API:
curl -X POST http://localhost:8000/api/v1/household/invite \
  -H "Authorization: Bearer <admin-token>" \
  -H "Content-Type: application/json" \
  -d '{"email":"newuser@example.com"}'
```

### Grant Data Access to a Household Member

```bash
# Via UI (recommended):
# 1. Login as the data owner
# 2. Navigate to /permissions
# 3. Click "Grant Access"
# 4. Pick member, resource type, and actions

# Via API:
curl -X POST http://localhost:8000/api/v1/permissions/grants \
  -H "Authorization: Bearer <owner-token>" \
  -H "Content-Type: application/json" \
  -d '{
    "grantee_id": "<member-uuid>",
    "resource_type": "transaction",
    "actions": ["read", "update"]
  }'
```

### Refresh Investment Prices

```bash
# Single quote
curl -X GET "http://localhost:8000/api/v1/market-data/quote/AAPL" \
  -H "Authorization: Bearer <token>"

# Batch quotes
curl -X POST "http://localhost:8000/api/v1/market-data/quote/batch" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '["AAPL", "GOOGL", "MSFT"]'
```

### Export Transactions to CSV

```bash
# Via UI: Transactions -> Export CSV button

# Via API:
curl -X GET "http://localhost:8000/api/v1/transactions/export?start_date=2024-01-01&end_date=2024-12-31" \
  -H "Authorization: Bearer <token>" \
  -o transactions.csv
```

### Create Database Backup

```bash
# PostgreSQL dump
docker compose exec postgres pg_dump -U nestegg nestegg > backup_$(date +%Y%m%d).sql

# Restore from backup
docker compose exec -T postgres psql -U nestegg nestegg < backup_20240115.sql
```

### Reset a Test User's Password

```bash
cd backend && python scripts/reset_test_password.py   # resets test@test.com to test1234
```

## Known Issues

### First Portfolio Snapshot Takes 24 Hours

The smart snapshot scheduler distributes organizations across 24 hours. Your first snapshot may not appear immediately. Manual override: `POST /api/v1/holdings/capture-snapshot`.

### Teller Sandbox Limitations

When using Teller Sandbox: test institutions only, limited transaction history, no real-time updates. Switch to Production for real banks (100 free accounts/month).

### Transaction Dedupe Only Within Organization

Deduplication is organization-scoped. Same transaction across different organizations is kept (correct behavior).

### Category Mapping Persistence

When you map a provider category to a custom category, the mapping applies to **all future transactions**. Existing transactions are not updated — run manual recategorization if needed.

### CSV Import Format Requirements

```csv
Date,Merchant,Amount,Category,Description
2024-01-15,Starbucks,-5.50,Dining,Morning coffee
```

- **Date**: YYYY-MM-DD format
- **Amount**: Negative for expenses, positive for income
- **Category**: Must match existing category name
