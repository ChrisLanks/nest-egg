# Logging and Monitoring Setup

This document describes the logging and monitoring infrastructure for Nest Egg.

## Backend Logging

### Configuration

Logging is configured in `/backend/app/core/logging_config.py`

**Features:**
- Console logging for development
- File logging for production (logs/app.log, logs/error.log)
- Structured log format with timestamps, function names, and line numbers
- Different log levels per environment (DEBUG in dev, INFO in prod)
- Reduced noise from third-party libraries (uvicorn, SQLAlchemy, asyncio)

### Request Logging Middleware

Located at `/backend/app/middleware/logging_middleware.py`

**Logs include:**
- HTTP method and path
- Response status code
- Request duration in milliseconds
- User ID (if authenticated)
- Client IP address (including X-Forwarded-For)

**Log Levels:**
- `ERROR` (red): 5xx status codes
- `WARNING` (yellow): 4xx status codes or requests >1000ms
- `INFO` (white): Successful requests

### Usage

To enable request logging, add to `main.py`:

```python
from app.middleware.logging_middleware import RequestLoggingMiddleware
from app.core.logging_config import setup_logging

# Initialize logging
setup_logging()

# Add request logging middleware
app.add_middleware(RequestLoggingMiddleware)
```

### Log Files (Production)

```
backend/
  logs/
    app.log     # All logs (INFO and above)
    error.log   # Errors only (ERROR and above)
```

**Rotation:** Implement log rotation using `logging.handlers.RotatingFileHandler` or external tools like `logrotate`.

---

## Frontend Monitoring

### Configuration

Monitoring service is located at `/frontend/src/services/monitoring.ts`

**Features:**
- Sentry integration (commented out, ready to enable)
- Error tracking with automatic reporting
- Performance monitoring (Browser Tracing)
- Session replay for debugging
- User context tracking
- Custom event logging
- Breadcrumb trail for debugging

### Enabling Sentry

**Step 1: Install Sentry**
```bash
cd frontend
npm install @sentry/react
```

**Step 2: Get Sentry DSN**
1. Sign up at https://sentry.io
2. Create a new React project
3. Copy the DSN (Data Source Name)

**Step 3: Configure Environment**

Add to `.env.production`:
```env
VITE_SENTRY_DSN=https://your-sentry-dsn@sentry.io/your-project-id
VITE_APP_VERSION=1.0.0
```

**Step 4: Uncomment Sentry Code**

In `/frontend/src/services/monitoring.ts`, uncomment:
- Import statement: `import * as Sentry from '@sentry/react'`
- `Sentry.init()` configuration
- All helper functions (logEvent, logError, setUserContext, etc.)

### Usage Examples

**Error Logging:**
```typescript
import { logError } from './services/monitoring';

try {
  await api.post('/transactions', data);
} catch (error) {
  logError(error as Error, { context: 'Creating transaction', data });
}
```

**User Context:**
```typescript
import { setUserContext, clearUserContext } from './services/monitoring';

// On login
setUserContext({
  id: user.id,
  email: user.email,
  name: user.first_name,
});

// On logout
clearUserContext();
```

**Custom Events:**
```typescript
import { logEvent } from './services/monitoring';

logEvent('CSV Import Started', {
  filename: file.name,
  rowCount: rows.length,
});
```

**Breadcrumbs:**
```typescript
import { addBreadcrumb } from './services/monitoring';

addBreadcrumb('User selected account', {
  accountId: selectedAccount.id,
  accountType: selectedAccount.type,
});
```

---

## Monitoring Best Practices

### 1. Sensitive Data Protection

The configuration automatically:
- Removes `authorization`, `password`, `token` from breadcrumbs
- Removes auth headers from error reports
- Masks all text in session replays
- Blocks all media in session replays

### 2. Sample Rates

**Recommended settings:**
- Performance monitoring: 10% (0.1)
- Session replay: 10% normal, 100% on errors
- Adjust based on traffic volume and budget

### 3. Ignored Errors

Already configured to ignore:
- Browser extension errors
- Network errors (Failed to fetch)
- User-cancelled actions (AbortError)

Add more as needed in the `ignoreErrors` array.

### 4. Environment Tracking

Automatically tracks:
- Environment (production, staging, development)
- Release version (from VITE_APP_VERSION)
- User information (on login)

---

## Production Checklist

### Backend
- [ ] Ensure `DEBUG=False` in production `.env`
- [ ] Set up log rotation (logrotate or similar)
- [ ] Monitor disk space for log files
- [ ] Set up log aggregation (optional: ELK stack, CloudWatch)
- [ ] Add RequestLoggingMiddleware to main.py
- [ ] Call setup_logging() on startup

### Frontend
- [ ] Install @sentry/react: `npm install @sentry/react`
- [ ] Get Sentry DSN from sentry.io
- [ ] Set VITE_SENTRY_DSN in .env.production
- [ ] Set VITE_APP_VERSION for release tracking
- [ ] Uncomment Sentry code in monitoring.ts
- [ ] Test error reporting in staging
- [ ] Verify sensitive data is filtered
- [ ] Set appropriate sample rates

---

## Debugging in Development

### Backend
- SQL queries logged when DEBUG=True
- All logs output to console
- No file logging in development

### Frontend
- Global error handler logs to console
- Unhandled promise rejections logged
- Custom events logged to console
- No data sent to Sentry

---

## Performance Impact

### Backend Logging
- **Minimal**: Async logging, non-blocking
- **File I/O**: Buffered writes
- **Overhead**: <1ms per request

### Frontend Monitoring
- **Sentry SDK**: ~50KB gzipped
- **Performance**: Lazy-loaded, non-blocking
- **Session Replay**: 10% sample rate minimizes impact
- **Overhead**: <5ms on page load

---

## Troubleshooting

### Backend: No logs appearing
1. Check `DEBUG` setting in .env
2. Ensure `setup_logging()` is called
3. Check file permissions for logs/ directory
4. Verify log level configuration

### Backend: Too many logs
1. Increase log level to WARNING
2. Disable SQLAlchemy query logging
3. Reduce third-party library verbosity

### Frontend: Sentry not reporting
1. Verify VITE_SENTRY_DSN is set
2. Check Sentry code is uncommented
3. Ensure running in production mode
4. Check browser console for errors
5. Verify Sentry project is active

### Frontend: Too many error reports
1. Adjust sample rates
2. Add errors to ignoreErrors list
3. Implement error boundaries
4. Filter out known issues

---

## Next Steps

1. **Backend**: Integrate with centralized logging (optional)
   - ELK Stack (Elasticsearch, Logstash, Kibana)
   - CloudWatch Logs (AWS)
   - Datadog, Splunk, etc.

2. **Frontend**: Advanced Sentry features
   - Source maps for production debugging
   - Custom tags and contexts
   - Release health monitoring
   - User feedback widgets

3. **Alerting**: Set up alerts for critical errors
   - Sentry alerts for high error rates
   - Log monitoring alerts for 500 errors
   - Performance degradation alerts

4. **Analytics**: Add product analytics (optional)
   - Google Analytics
   - Mixpanel
   - Amplitude
   - PostHog

---

## Cost Considerations

### Sentry (Free Tier)
- 5,000 errors/month
- 10,000 performance transactions/month
- 50 session replays/month
- Sufficient for small-medium applications

### Paid Tier ($29-$99/month)
- Needed for higher traffic
- More session replays
- Longer data retention
- Team features

### Self-Hosted Alternative
- Open-source Sentry
- Requires infrastructure management
- No cost per event
- Higher operational overhead
