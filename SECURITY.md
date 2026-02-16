# Security Documentation

## Secrets Management

### Required Secrets

#### Critical Secrets (Must be set in production)
1. **SECRET_KEY** - JWT token signing key
   - Minimum length: 32 characters
   - Generate: `openssl rand -hex 32`
   - Used for: JWT token generation and validation

2. **ENCRYPTION_KEY** - Data encryption key
   - Minimum length: 32 characters
   - Generate: `openssl rand -base64 32`
   - Used for: Encrypting Plaid access tokens in database

3. **DATABASE_URL** - PostgreSQL connection string
   - Format: `postgresql://user:password@host:port/database`
   - Password minimum length: 16 characters
   - Use strong password with mixed characters

#### Important Secrets
4. **PLAID_CLIENT_ID** - Plaid API client ID
   - Obtain from: Plaid Dashboard
   - Required for: Plaid integration

5. **PLAID_SECRET** - Plaid API secret
   - Obtain from: Plaid Dashboard
   - Keep secure, never commit to git

6. **PLAID_WEBHOOK_SECRET** - Plaid webhook verification key
   - Obtain from: Plaid Dashboard webhook settings
   - Used for: Verifying webhook authenticity

#### Optional Secrets
7. **ALPHA_VANTAGE_API_KEY** - Stock market data API
8. **FINNHUB_API_KEY** - Alternative stock market data API

---

## Secrets Rotation Procedures

### JWT Secret Key Rotation

**When to rotate:**
- Every 90 days (recommended)
- Immediately after suspected compromise
- When team member with access leaves

**Steps:**
1. Generate new secret: `openssl rand -hex 32`
2. Update `SECRET_KEY` in production environment
3. Restart application
4. All existing JWT tokens will be invalidated
5. Users will need to log in again

**Impact:** All users logged out

### Encryption Key Rotation

**When to rotate:**
- Every 6 months (recommended)
- Immediately after suspected compromise

**Steps:**
1. **DO NOT rotate without data migration plan**
2. Generate new key: `openssl rand -base64 32`
3. Create migration script to re-encrypt all Plaid tokens
4. Update `ENCRYPTION_KEY`
5. Run migration
6. Restart application

**Impact:** High - requires data migration

### Database Password Rotation

**When to rotate:**
- Every 90 days (recommended)
- Immediately after suspected compromise
- When DBA with access leaves

**Steps:**
1. Create new database password
2. Update password in PostgreSQL: `ALTER USER username WITH PASSWORD 'new_password';`
3. Update `DATABASE_URL` in production environment
4. Restart application with minimal downtime

**Impact:** Brief downtime during restart

### Plaid Secret Rotation

**When to rotate:**
- When Plaid recommends
- Immediately after suspected compromise

**Steps:**
1. Generate new secret in Plaid Dashboard
2. Update `PLAID_SECRET` in production environment
3. Restart application
4. Old secret continues working for 24 hours (Plaid grace period)

**Impact:** None if done during grace period

---

## Environment-Specific Configuration

### Production Requirements

```bash
# Critical - Must be set
SECRET_KEY=<64-char-hex-string>
ENCRYPTION_KEY=<base64-encoded-32-bytes>
DATABASE_URL=postgresql://user:strong_password@prod-db:5432/nestegg
DEBUG=false

# Network Security
CORS_ORIGINS=["https://app.nestegg.com"]
ALLOWED_HOSTS=["app.nestegg.com", "api.nestegg.com"]

# Plaid Integration
PLAID_ENV=production
PLAID_CLIENT_ID=<from-plaid-dashboard>
PLAID_SECRET=<from-plaid-dashboard>
PLAID_WEBHOOK_SECRET=<from-plaid-dashboard>
```

### Development Configuration

```bash
# Development - Can use test values
SECRET_KEY=dev-secret-key-at-least-32-characters-long
ENCRYPTION_KEY=dev-encryption-key-base64-encoded
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/nestegg_dev
DEBUG=true

# Network (allow localhost)
CORS_ORIGINS=["http://localhost:3000", "http://localhost:5173"]
ALLOWED_HOSTS=["*"]

# Plaid Sandbox
PLAID_ENV=sandbox
PLAID_CLIENT_ID=<sandbox-client-id>
PLAID_SECRET=<sandbox-secret>
```

---

## Security Checklist for Production Deployment

- [ ] DEBUG mode disabled (`DEBUG=false`)
- [ ] Strong SECRET_KEY (32+ chars, random)
- [ ] Strong ENCRYPTION_KEY (32+ bytes, random)
- [ ] Strong database password (16+ chars)
- [ ] CORS_ORIGINS set to specific domain(s)
- [ ] ALLOWED_HOSTS set to specific domain(s)
- [ ] Database not on localhost
- [ ] HTTPS enabled (certificates configured)
- [ ] Plaid production credentials configured
- [ ] Plaid webhook secret configured
- [ ] No secrets in git history
- [ ] Environment variables stored securely (AWS Secrets Manager, etc.)

---

## Incident Response

### If Secrets are Compromised

1. **Immediate Actions:**
   - Rotate compromised secret immediately
   - Review access logs for suspicious activity
   - Notify security team

2. **Investigation:**
   - Determine scope of compromise
   - Identify how secret was exposed
   - Check for unauthorized access

3. **Remediation:**
   - Rotate all related secrets
   - Update security procedures
   - Document incident for future prevention

### Reporting Security Issues

- Email: security@nestegg.com (if production)
- For development: Create GitHub issue with `security` label
- For critical issues: Rotate secrets first, report second

---

## Best Practices

1. **Never commit secrets to git**
   - Use `.env` files (gitignored)
   - Use environment variable injection in CI/CD

2. **Use secret management tools**
   - AWS Secrets Manager
   - HashiCorp Vault
   - Google Cloud Secret Manager

3. **Principle of least privilege**
   - Only give access to secrets when needed
   - Revoke access when no longer needed

4. **Audit secret access**
   - Log who accessed secrets and when
   - Review logs regularly

5. **Automate rotation where possible**
   - Set up automated rotation for compatible secrets
   - Use managed services that handle rotation

---

## Security Monitoring

### What to Monitor

1. **Failed login attempts**
   - 5+ failures = account lockout
   - Pattern of failures across accounts = potential attack

2. **API rate limit hits**
   - Frequent 429 errors = potential abuse
   - Review source IPs

3. **Database connection errors**
   - Could indicate password/connection issues
   - Check credentials haven't expired

4. **Webhook verification failures**
   - Invalid Plaid webhooks = potential attack
   - Review webhook source

### Alerts to Set Up

- Failed secrets validation on startup
- Database connection failures
- Multiple account lockouts
- Rate limit breaches
- Webhook verification failures

---

## Additional Resources

- [OWASP Secrets Management Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Secrets_Management_Cheat_Sheet.html)
- [Plaid Security Documentation](https://plaid.com/docs/api/webhooks/#webhook-verification)
- [FastAPI Security Best Practices](https://fastapi.tiangolo.com/tutorial/security/)
