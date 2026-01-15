# Security Guidelines

This document outlines security best practices for the Books API project.

## Table of Contents

- [Security Decisions](#security-decisions)
- [Secret Management](#secret-management)
- [Environment Configuration](#environment-configuration)
- [Database Security](#database-security)
- [API Security](#api-security)
- [Deployment Checklist](#deployment-checklist)
- [Incident Response](#incident-response)

## Security Decisions

### Why Custom Ports?

We use non-default ports (8001 for API, 5433 for PostgreSQL) because:

1. **Reduced Attack Surface**: Automated scanners target default ports (8000, 5432, 6379)
2. **Avoid Conflicts**: Won't interfere with local development services
3. **Defense in Depth**: One layer of many security measures

| Service    | Default Port | Our Port | Why? |
|------------|--------------|----------|------|
| API        | 8000         | 8001     | Avoid automated scanning |
| PostgreSQL | 5432         | 5433     | Common attack target |
| Redis      | 6379         | 6380     | Phase 2 |

### Why Custom Credentials?

Default credentials are dangerous because:

1. **Well-Known**: `postgres:postgres` is the first thing attackers try
2. **Documented**: Default credentials are in every tutorial
3. **Automated**: Bots scan for default credentials 24/7

**Never use these in production:**
- Username: `postgres`, `admin`, `root`
- Password: `postgres`, `password`, `admin`, `123456`

## Secret Management

### Generating Secure Secrets

#### SECRET_KEY (64 characters hex)

```bash
# Option 1: OpenSSL (recommended)
openssl rand -hex 32

# Option 2: Python
python -c "import secrets; print(secrets.token_hex(32))"
```

#### Database Password (32+ characters)

```bash
# Option 1: OpenSSL (recommended)
openssl rand -base64 24

# Option 2: Python
python -c "import secrets; print(secrets.token_urlsafe(24))"
```

### Secret Requirements

| Secret | Min Length | Allowed Characters | Rotation |
|--------|------------|-------------------|----------|
| SECRET_KEY | 64 chars | Hex (0-9, a-f) | Every 90 days |
| POSTGRES_PASSWORD | 24 chars | Base64 | Every 90 days |
| API Keys | 32 chars | Alphanumeric | Per user |

### How to Rotate Secrets

#### Rotating SECRET_KEY

1. Generate new key: `openssl rand -hex 32`
2. Update `.env` with new value
3. Restart the application
4. Note: Active sessions will be invalidated

#### Rotating Database Password

1. Generate new password: `openssl rand -base64 24`
2. Update PostgreSQL user password:
   ```sql
   ALTER USER books_admin WITH PASSWORD 'new_password';
   ```
3. Update `.env` with new password
4. Update `DATABASE_URL` in `.env`
5. Restart the application

## Environment Configuration

### .env File Security

The `.env` file contains secrets and should NEVER be committed to Git.

#### DO:
- ✅ Add `.env` to `.gitignore` (already done)
- ✅ Use `.env.example` as a template (no real secrets)
- ✅ Set restrictive file permissions: `chmod 600 .env`
- ✅ Keep backups in a secure password manager

#### DON'T:
- ❌ Commit `.env` to Git
- ❌ Share `.env` via email or chat
- ❌ Use the same secrets in dev and production
- ❌ Store secrets in code or comments

### Environment-Specific Settings

| Setting | Development | Production |
|---------|-------------|------------|
| DEBUG | `True` | `False` |
| LOG_LEVEL | `DEBUG` | `WARNING` |
| ALLOWED_ORIGINS | `localhost:*` | Your domain only |
| SECRET_KEY | Dev key | Production key |

## Database Security

### Connection Security

1. **Use SSL in Production**: Add `?sslmode=require` to DATABASE_URL
2. **Limit Connections**: Set reasonable pool sizes
3. **Network Isolation**: Use Docker networks or VPCs

### User Permissions

For production, create a limited database user:

```sql
-- Create application user with limited permissions
CREATE USER books_app WITH PASSWORD 'secure_password';

-- Grant only necessary permissions
GRANT CONNECT ON DATABASE books_production TO books_app;
GRANT USAGE ON SCHEMA public TO books_app;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO books_app;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO books_app;

-- Don't grant: CREATE, DROP, TRUNCATE, etc.
```

### Backup Security

- Encrypt database backups at rest
- Store backups in a different location than the database
- Test backup restoration regularly
- Rotate backup encryption keys

## API Security

### CORS Configuration

```python
# Development
ALLOWED_ORIGINS=http://localhost:3000,http://localhost:8080

# Production
ALLOWED_ORIGINS=https://yourdomain.com,https://app.yourdomain.com
```

### Rate Limiting (Phase 2)

When implemented:
- 100 requests per minute for anonymous users
- Higher limits for authenticated users
- Exponential backoff for repeated violations

### Input Validation

All input is validated using Pydantic schemas:
- String lengths are limited
- Numbers have min/max constraints
- Emails are validated
- URLs are validated

### Error Handling

- Debug mode shows detailed errors (development only)
- Production mode hides internal details
- All errors are logged for investigation

## Deployment Checklist

### Before Going Live

#### Configuration
- [ ] DEBUG is set to `False`
- [ ] SECRET_KEY is a unique, generated value
- [ ] POSTGRES_PASSWORD is a strong, generated value
- [ ] ALLOWED_ORIGINS contains only your domains
- [ ] LOG_LEVEL is set to `WARNING` or `ERROR`

#### Infrastructure
- [ ] Database is not publicly accessible
- [ ] API is behind HTTPS (SSL/TLS)
- [ ] Firewall rules are configured
- [ ] Container images are from trusted sources

#### Secrets
- [ ] No secrets in code or comments
- [ ] No secrets in Git history
- [ ] `.env` file is not in the repository
- [ ] Secrets are rotated from development values

#### Monitoring
- [ ] Error logging is configured
- [ ] Health checks are working
- [ ] Alerts are set up for failures

### Regular Security Tasks

| Task | Frequency |
|------|-----------|
| Rotate secrets | Every 90 days |
| Update dependencies | Monthly |
| Review access logs | Weekly |
| Test backups | Monthly |
| Security scan | Before each release |

## What to Never Commit to Git

### Files
- `.env` - Contains secrets
- `*.pem`, `*.key` - Private keys
- `*.log` - May contain sensitive data
- Database dumps - Contains user data

### Data in Code
- API keys
- Passwords
- Private keys
- Access tokens
- Connection strings with credentials

### How to Check for Secrets

```bash
# Search for common secret patterns
grep -r "password" --include="*.py" .
grep -r "secret" --include="*.py" .
grep -r "api_key" --include="*.py" .

# Use git-secrets or similar tools
git secrets --scan
```

## Incident Response

### If Secrets Are Exposed

1. **Rotate Immediately**: Generate and deploy new secrets
2. **Revoke Old Secrets**: Ensure old values no longer work
3. **Audit Logs**: Check for unauthorized access
4. **Notify**: Inform stakeholders if data was accessed

### If You Committed Secrets to Git

1. **Don't panic** - but act quickly
2. **Rotate the secrets immediately**
3. **Remove from Git history**:
   ```bash
   # Use git-filter-repo or BFG Repo-Cleaner
   git filter-repo --invert-paths --path .env
   ```
4. **Force push** (coordinate with team)
5. **GitHub**: Check for forks that may have the secret

### Security Contact

For security concerns or to report vulnerabilities:
- Open a private security advisory on GitHub
- Email: security@yourdomain.com

---

## Summary

Security is not a one-time setup but an ongoing practice:

1. **Use strong, random secrets** - Never use defaults
2. **Keep secrets out of Git** - Use `.env` files
3. **Use non-default ports** - Avoid automated scans
4. **Rotate regularly** - Don't let secrets get stale
5. **Monitor and audit** - Know what's happening in your system

Remember: Security is only as strong as its weakest link.
