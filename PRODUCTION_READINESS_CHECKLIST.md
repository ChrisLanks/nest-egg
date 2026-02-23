# Production Readiness Checklist

## Overview

This document tracks production readiness for Nest Egg.

**Current Status: 97/100**
**Last updated: February 2026**

---

## ✅ COMPLETED

### 1. Authentication & MFA
- [x] JWT access tokens (15-min expiry) + httpOnly refresh tokens (30-day)
- [x] Account lockout after 5 failed login attempts (30-min lock)
- [x] Rate limiting on login (5/min), MFA verify (3/min), refresh (10/min)
- [x] MFA: TOTP setup (`/api/v1/mfa/setup`, `/api/v1/mfa/verify`, `/api/v1/mfa/disable`)
- [x] MFA enforcement at login (non-dev mode) — returns `MFAChallengeResponse`
- [x] `POST /auth/mfa/verify` — completes 2-step login with TOTP or backup code
- [x] Frontend MFA step in login page (PinInput TOTP flow)
- [x] Backup codes (10 single-use codes, hashed + encrypted)
- [x] Email verification flow + banner

### 2. GDPR & Compliance
- [x] `DELETE /settings/account` — right to erasure (Article 17)
  - Requires password confirmation
  - Sole member: deletes entire organization (FK CASCADE)
  - Household member: deletes only user
  - Clears httpOnly refresh cookie on response
  - Logs deletion event for audit trail
- [x] `UserConsent` model — captures ToS + Privacy Policy acceptance at registration
- [x] `TERMS_VERSION` config variable for consent versioning
- [x] Data export endpoint (`GET /settings/export` → ZIP)

### 3. Security Hardening
- [x] HTTPS redirect (production only)
- [x] Security headers middleware (HSTS, X-Frame-Options, X-Content-Type-Options, CSP)
- [x] CSRF protection middleware
- [x] Trusted host middleware (production only)
- [x] Request size limit middleware
- [x] CORS locked to configured origins
- [x] Swagger/ReDoc disabled in production (`docs_url=None`, `redoc_url=None`)
- [x] `/security-status` gated behind org-admin auth
- [x] Health check sanitized (never reveals stack traces)
- [x] Plaid item_id uses random UUID (never exposes token content)
- [x] Sensitive fields encrypted at rest: `annual_salary`, `property_address`, `vehicle_vin`, `property_zip`, Plaid/Teller access tokens

### 4. Secrets Validation
- [x] Startup check rejects weak `SECRET_KEY`, `ENCRYPTION_KEY`, `DATABASE_URL` passwords
- [x] Checks for default `METRICS_PASSWORD`
- [x] Generates security checklist at `/security-status` (admin only)

### 5. Background Jobs (Celery)
- [x] `RetryableTask` base class: exponential backoff (60→120→240s), jitter, cap 10min
- [x] `task_acks_late=True`, `task_reject_on_worker_lost=True`
- [x] Task time limit: 5 minutes (soft: 4.5 min) — prevents runaway tasks
- [x] Beat schedule: snapshot capture, budget alerts, recurring detection, cash flow forecast, holdings price update, interest accrual, token cleanup

### 6. Testing
- [x] 1284 tests passing, 20 skipped (PostgreSQL-specific)
- [x] Test infrastructure: SQLite in-memory + StaticPool
- [x] Tests cover: auth, MFA, GDPR deletion, consent capture, budgets, transactions, accounts, holdings, savings goals, rate limiting, CSRF, audit logging, security headers

### 7. CI/CD & Developer Experience
- [x] GitHub Actions (ci.yml, pr-checks.yml)
- [x] Pre-commit hooks (Black, isort, Flake8)
- [x] Makefile
- [x] CONTRIBUTING.md

### 8. Monitoring & Logging
- [x] Sentry integration (error tracking, PII filtering, rate limiting events)
- [x] Structured logging (`RequestLoggingMiddleware`, `AuditLogMiddleware`)
- [x] Prometheus metrics (separate admin port)
- [x] `/api/v1/monitoring/health` — DB + Redis health check

---

## 🚀 Deployment Checklist

**Environment Variables (required in production):**
- [ ] `SECRET_KEY` — 64+ random chars (`openssl rand -hex 32`)
- [ ] `ENCRYPTION_KEY` — 32+ base64 chars (`openssl rand -base64 32`)
- [ ] `DATABASE_URL` — PostgreSQL with strong password
- [ ] `REDIS_URL` — Redis connection
- [ ] `SENTRY_DSN` — Sentry project DSN
- [ ] `CORS_ORIGINS` — production frontend domain only
- [ ] `ALLOWED_HOSTS` — production API domains only
- [ ] `DEBUG=false`
- [ ] `ENVIRONMENT=production`
- [ ] `PLAID_CLIENT_ID`, `PLAID_SECRET`, `PLAID_WEBHOOK_SECRET`
- [ ] `TELLER_CERT_PATH`, `TELLER_KEY_PATH`, `TELLER_WEBHOOK_SECRET`
- [ ] `METRICS_PASSWORD` — non-default value
- [ ] `TERMS_VERSION` — bump when ToS/Privacy Policy changes

**Database:**
- [ ] `alembic upgrade head`
- [ ] Backup schedule configured
- [ ] Not publicly accessible

**Security:**
- [ ] HTTPS certificate
- [ ] Firewall rules
- [ ] Redis not publicly accessible

**Final checks:**
- [ ] `GET /security-status` (as org admin) — all green
- [ ] All tests passing in CI
- [ ] Manual QA on staging

---

## 📊 Score History

| Round | Focus | Score |
|-------|-------|-------|
| Baseline | Initial setup | 70/100 |
| Round 1 | Auth, rate limiting, account lockout | 85/100 |
| Round 2 | Celery, metrics, composite indexes | 90/100 |
| Round 3 | MFA enforcement, GDPR deletion, consent, encryption, swagger | 95/100 |
| Round 4 | Auth state clearing, cookie cleanup, audit fixes, ESLint | 97/100 |
