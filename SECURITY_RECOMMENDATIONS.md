# Security Recommendations

This document outlines security improvements for Nest Egg production deployment.

## 🔴 Critical (Implement Before Production)

### 1. Fix Content Security Policy (CSP)

**Current Issue:** CSP allows `unsafe-eval` which enables arbitrary code execution

**Location:** `/backend/app/middleware/security_headers.py` line 18

**Current Code:**
```python
"script-src 'self' 'unsafe-inline' 'unsafe-eval'; "
```

**Recommended Fix:**
```python
# In security_headers.py
from app.core.config import settings

def get_script_src_policy() -> str:
    """Get script-src policy based on environment."""
    if settings.DEBUG:
        # Development: Allow unsafe-inline and unsafe-eval for HMR
        return "'self' 'unsafe-inline' 'unsafe-eval'"
    else:
        # Production: Use nonces or strict CSP
        # Option 1: Nonce-based (recommended)
        return "'self' 'nonce-{NONCE}'"
        # Option 2: Hash-based
        # return "'self' 'sha256-{HASH}'"
        # Option 3: Strict (no inline scripts)
        # return "'self'"

# In middleware
csp_header = (
    "default-src 'self'; "
    f"script-src {get_script_src_policy()}; "
    "style-src 'self' 'unsafe-inline'; "
    "img-src 'self' data: https:; "
    "font-src 'self' data:; "
    "connect-src 'self' https://api.plaid.com; "
    "frame-ancestors 'none'; "
    "base-uri 'self'; "
    "form-action 'self'"
)
```

**Impact:** Prevents XSS attacks via injected scripts
**Effort:** 2 hours (testing required)
**Priority:** HIGH

---

### 2. Move Refresh Tokens to HttpOnly Cookies

**Current Issue:** Refresh tokens stored in localStorage are vulnerable to XSS

**Current Implementation:**
- Access token: Memory (good!)
- Refresh token: localStorage (vulnerable!)

**Recommended Approach:**

**Backend Changes** (`/backend/app/api/v1/auth.py`):
```python
from fastapi import Response

@router.post("/login")
async def login(
    credentials: LoginRequest,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    # ... authentication logic ...

    # Set refresh token in httpOnly cookie
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,  # Prevents JavaScript access
        secure=True,    # HTTPS only
        samesite="strict",  # CSRF protection
        max_age=7 * 24 * 60 * 60,  # 7 days
        path="/api/v1/auth/refresh",  # Limit scope
    )

    # Return only access token in response
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": user_data,
    }

@router.post("/refresh")
async def refresh_token(
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    # Read refresh token from cookie
    refresh_token = request.cookies.get("refresh_token")
    if not refresh_token:
        raise HTTPException(status_code=401, detail="No refresh token")

    # ... token validation ...

    # Rotate refresh token (security best practice)
    new_refresh_token = create_refresh_token(user)
    response.set_cookie(
        key="refresh_token",
        value=new_refresh_token,
        httponly=True,
        secure=True,
        samesite="strict",
        max_age=7 * 24 * 60 * 60,
    )

    return {"access_token": new_access_token, "token_type": "bearer"}

@router.post("/logout")
async def logout(response: Response):
    # Clear cookie
    response.delete_cookie(key="refresh_token", path="/api/v1/auth/refresh")
    return {"message": "Logged out"}
```

**Frontend Changes** (`/frontend/src/features/auth/stores/authStore.ts`):
```typescript
// Remove localStorage for refresh token
// Tokens now handled entirely via cookies

// Update refresh logic
async refreshAccessToken() {
  try {
    // No need to send refresh token - it's in cookie
    const response = await api.post('/auth/refresh');
    this.setAccessToken(response.data.access_token);
    return true;
  } catch (error) {
    this.logout();
    return false;
  }
}
```

**Benefits:**
- Immune to XSS attacks
- Automatic rotation
- Scoped to specific endpoints
- CSRF protection with SameSite

**Impact:** Significantly improves token security
**Effort:** 8 hours (backend + frontend + testing)
**Priority:** HIGH

---

## 🟡 Important (Implement Soon)

### 3. Enhance Rate Limiting

**Current Status:** Rate limiting middleware exists but may need tuning

**Verify Configuration:**
```python
# Check /backend/app/middleware/rate_limit.py
# Recommended limits:
- Login: 5 requests / 15 minutes (prevent brute force)
- API calls: 100 requests / minute (prevent abuse)
- CSV import: 5 requests / hour (resource intensive)
```

**Add Endpoint-Specific Limits:**
```python
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

# In main.py
from app.core.config import settings

if not settings.DEBUG:
    # Strict limits in production
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)

# In auth.py
@router.post("/login")
@limiter.limit("5/15minutes")  # Strict for auth
async def login(...):
    ...

# In csv_import.py
@router.post("/import")
@limiter.limit("5/hour")  # Resource intensive
async def import_csv(...):
    ...
```

**Impact:** Prevents brute force and DoS attacks
**Effort:** 3 hours
**Priority:** MEDIUM

---

### 4. Add Security Headers

**Verify headers are set** (`/backend/app/middleware/security_headers.py`):

```python
# Required headers:
response.headers["X-Content-Type-Options"] = "nosniff"
response.headers["X-Frame-Options"] = "DENY"
response.headers["X-XSS-Protection"] = "1; mode=block"
response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"

# HSTS (HTTPS enforcement)
if not settings.DEBUG:
    response.headers["Strict-Transport-Security"] = (
        "max-age=31536000; includeSubDomains; preload"
    )
```

**Impact:** Defense in depth against various attacks
**Effort:** 1 hour
**Priority:** MEDIUM

---

### 5. Implement Account Lockout Protection

**Current Status:** Failed login tracking exists in User model
**Enhancement Needed:** Automatic lockout and unlock

**Implementation:**
```python
# In /backend/app/services/auth_service.py

from datetime import datetime, timedelta

async def check_account_lockout(user: User) -> None:
    """Check if account is locked and raise exception if so."""
    if user.locked_until and user.locked_until > datetime.utcnow():
        remaining = (user.locked_until - datetime.utcnow()).total_seconds() / 60
        raise HTTPException(
            status_code=423,  # Locked
            detail=f"Account locked. Try again in {int(remaining)} minutes."
        )

async def handle_failed_login(db: AsyncSession, user: User) -> None:
    """Increment failed attempts and lock if threshold reached."""
    user.failed_login_attempts += 1

    # Lock after 5 failed attempts
    if user.failed_login_attempts >= 5:
        # Lock for 30 minutes
        user.locked_until = datetime.utcnow() + timedelta(minutes=30)

    await db.commit()

async def handle_successful_login(db: AsyncSession, user: User) -> None:
    """Reset failed attempts on successful login."""
    user.failed_login_attempts = 0
    user.locked_until = None
    user.last_login_at = datetime.utcnow()
    await db.commit()
```

**Impact:** Prevents brute force attacks
**Effort:** 2 hours
**Priority:** MEDIUM

---

## 🟢 Nice to Have (Future Improvements)

### 6. Add Two-Factor Authentication (2FA)

**Options:**
1. TOTP (Time-based One-Time Password) - Google Authenticator
2. SMS-based (requires Twilio or similar)
3. Email-based (easiest to implement)

**Implementation Outline:**
```python
# New table: two_factor_settings
# Columns: user_id, method (totp/sms/email), secret, enabled

# New endpoints:
POST /auth/2fa/enable
POST /auth/2fa/verify
POST /auth/2fa/disable
```

**Effort:** 16 hours
**Priority:** LOW (but valuable for sensitive accounts)

---

### 7. Security Audit Checklist

Before production deployment, verify:

#### Authentication & Authorization
- [ ] Passwords hashed with Argon2 ✅ (already implemented)
- [ ] JWT tokens with short expiration (15 min access, 7 day refresh) ✅
- [ ] Refresh token rotation on use
- [ ] Account lockout after failed attempts
- [ ] Session invalidation on logout
- [ ] Multi-tenancy isolation (organization_id filters) ✅

#### Data Protection
- [ ] HTTPS enforced (HSTS header)
- [ ] Database credentials in environment variables ✅
- [ ] Sensitive data encrypted at rest
- [ ] PII (email, names) handled with care
- [ ] Financial data (transactions) properly secured

#### Input Validation
- [ ] All API inputs validated with Pydantic ✅
- [ ] SQL injection protection (SQLAlchemy ORM) ✅
- [ ] CSV upload validation and sanitization ✅
- [ ] File upload size limits (10MB) ✅
- [ ] Filename sanitization ✅

#### API Security
- [ ] CORS properly configured ✅
- [ ] Rate limiting enabled
- [ ] Request logging for audit trail
- [ ] Error messages don't leak sensitive info
- [ ] API versioning (/api/v1/) ✅

#### Frontend Security
- [ ] XSS protection (React auto-escapes) ✅
- [ ] CSRF tokens for state-changing operations
- [ ] No sensitive data in localStorage
- [ ] Tokens cleared on logout
- [ ] Content Security Policy enforced

#### Infrastructure
- [ ] Security headers configured
- [ ] Database backups automated
- [ ] Monitoring and alerting setup
- [ ] Incident response plan documented
- [ ] Regular dependency updates

---

## Implementation Priority

### Phase 1: Critical (Before Production)
1. Fix CSP to remove unsafe-eval (2 hours)
2. Move refresh tokens to httpOnly cookies (8 hours)

**Total:** 10 hours

### Phase 2: Important (First Month)
3. Verify/enhance rate limiting (3 hours)
4. Verify security headers (1 hour)
5. Implement account lockout (2 hours)

**Total:** 6 hours

### Phase 3: Nice to Have (Future)
6. Add 2FA support (16 hours)
7. Regular security audits (ongoing)

---

## Testing Security Changes

### 1. CSP Testing
```bash
# Test with browser DevTools
# Look for CSP violations in console
# Ensure Vite still works in development
# Verify no inline scripts in production build
```

### 2. Cookie Testing
```bash
# Verify cookies are httpOnly
document.cookie  # Should not show refresh_token

# Test token rotation
# Login -> Refresh -> Check new cookie value

# Test logout
# Verify cookie is cleared
```

### 3. Rate Limiting Testing
```bash
# Automated testing
for i in {1..10}; do
  curl -X POST http://localhost:8000/api/v1/auth/login
done
# Should see 429 Too Many Requests after 5 attempts
```

---

## Monitoring Security

### 1. Set Up Alerts
- Failed login attempts spike
- Rate limit hits increasing
- 500 errors (potential attacks)
- Unusual traffic patterns

### 2. Regular Reviews
- Weekly: Review failed login logs
- Monthly: Dependency vulnerability scan (`npm audit`, `pip-audit`)
- Quarterly: Security audit
- Yearly: Penetration testing

### 3. Incident Response
1. Detect: Monitoring alerts
2. Analyze: Check logs for attack pattern
3. Contain: Block IPs, disable accounts
4. Recover: Reset compromised accounts
5. Learn: Document and improve

---

## Resources

- **OWASP Top 10:** https://owasp.org/www-project-top-ten/
- **CSP Guide:** https://content-security-policy.com/
- **FastAPI Security:** https://fastapi.tiangolo.com/tutorial/security/
- **React Security:** https://reactjs.org/docs/dom-elements.html#dangerouslysetinnerhtml

---

## Questions?

Security is an ongoing process, not a one-time task. Regularly review and update these measures as new threats emerge.

For specific implementation help, consult:
- OWASP Cheat Sheets
- FastAPI documentation
- Your security team or consultant
