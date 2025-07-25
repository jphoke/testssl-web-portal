# SSL Test Portal - CLAUDE Documentation

This file contains important information for Claude AI to understand and work with this codebase effectively.

## Project Overview

This is a modern web-based SSL/TLS testing portal that uses testssl.sh to perform comprehensive security scans on HTTPS endpoints. Built with FastAPI, PostgreSQL, Redis, and Docker, it provides a secure, scalable solution for SSL/TLS security assessment.

## Architecture

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Frontend  │────▶│   FastAPI   │────▶│ PostgreSQL  │
│  (Nginx)    │     │   Backend   │     │  Database   │
└─────────────┘     └─────────────┘     └─────────────┘
                           │
                           ▼
                    ┌─────────────┐     ┌─────────────┐
                    │    Redis    │◀────│   Celery    │
                    │   Queue     │     │   Worker    │
                    └─────────────┘     └─────────────┘
                                               │
                                               ▼
                                        ┌─────────────┐
                                        │ testssl.sh  │
                                        └─────────────┘
```

## Key Files and Their Purposes

### Core Application
- `app.py` - FastAPI backend with REST API endpoints, database models, and request validation
- `worker.py` - Celery worker that executes testssl.sh scans and parses results
- `requirements.txt` - Python dependencies (FastAPI, SQLAlchemy, Celery, etc.)
- `Dockerfile` - Container image with testssl.sh and dependencies
- `docker-compose.yml` - Multi-service orchestration

### Frontend
- `frontend/index.html` - Main UI with testssl.sh attribution
- `frontend/app.js` - JavaScript for API interaction, real-time updates, expandable cipher details
- `frontend/style.css` - Modern, responsive styling

### Utilities
- `clean-deploy.sh` - Fresh deployment (removes all data)
- `debug.sh` - System diagnostics and troubleshooting
- `cleanup-data.sh` - Data retention management
- `deploy.sh` - Standard deployment

### Configuration
- `.env.example` - Environment template with secure defaults
- `.gitignore` - Comprehensive ignore patterns
- `nginx.conf` - Frontend server configuration

## Key Commands

```bash
# Fresh deployment (removes all data, prompts for secure password)
./clean-deploy.sh

# Standard deployment (checks for secure password)
./deploy.sh

# System diagnostics
./debug.sh

# Data management
./cleanup-data.sh --days 30  # Keep last 30 days
./cleanup-data.sh --all       # Remove all data

# Service logs
docker compose logs -f worker
docker compose logs --tail 100

# Rebuild after changes
docker compose build worker
docker compose up -d worker

# Rebuild frontend after permission fixes
docker compose build frontend
docker compose up -d frontend

# Manual testssl.sh test
docker compose exec worker /opt/testssl.sh/testssl.sh --help
```

## Implementation Details

### SSL/TLS Scanning (worker.py)
```python
# testssl.sh command structure
cmd = [
    testssl_path,
    "--jsonfile", json_output,
    "--severity", "LOW",
    "--color", "0",        # Disable colors for parsing
    "-p",                  # Protocols
    "-P",                  # Server preference
    "-S",                  # Server defaults
    "-h",                  # Headers
    "-U",                  # Vulnerabilities
    "-s",                  # Standard ciphers
    "-f",                  # Forward secrecy
    "-4",                  # RC4
    "-W",                  # SWEET32
    f"{host}:{port}"
]
```

### Grade Extraction
- Primary source: testssl.sh's native rating
- Pattern: `r'Overall\s+Grade\s+([A-FM][+-]?)'`
- Supports: A+, A, A-, B+, B, B-, ..., F+, F, F-, M
- Fallback: Custom calculation if not found

### API Endpoints (app.py)
- `GET /api/health` - Health check with service status
- `POST /api/scans` - Create new scan (validates host/port/comment)
- `GET /api/scans` - List recent scans with pagination
- `GET /api/scans/{id}/status` - Real-time progress
- `GET /api/scans/{id}/results` - Full scan results

### Database Schema
```sql
CREATE TABLE scans (
    id UUID PRIMARY KEY,
    host VARCHAR(255) NOT NULL,
    port INTEGER NOT NULL,
    status VARCHAR(50),  -- queued, running, completed, error
    grade VARCHAR(3),    -- A+, A, B, etc.
    results JSONB,       -- Full testssl.sh output
    created_at TIMESTAMP,
    completed_at TIMESTAMP,
    error TEXT,
    comment VARCHAR(100) -- Optional user comment
);
```

### Security Features
1. **Input Validation**: 
   - Host: DNS/IP validation, no private IPs
   - Port: 1-65535 range
   - Comment: 0-100 chars, sanitized (printable chars only)
2. **No Command Injection**: Uses subprocess list args
3. **Rate Limiting**: Prevents scan abuse (TODO)
4. **Containerization**: Isolated environment
5. **Secrets Management**: Environment variables
6. **Password Security**: 
   - Deployment scripts enforce secure passwords (12+ chars)
   - No default passwords allowed
   - Password confirmation required
7. **Process Security**:
   - Limited Celery concurrency (2 workers)
   - Docker init system prevents zombie processes
   - Proper file permissions in containers
8. **XSS Prevention**:
   - HTML escaping for user comments in frontend
   - Server-side sanitization of comment input

## Common Issues and Solutions

### 1. Scans Failing Quickly
**Symptom**: Scan completes in < 1 second
**Cause**: Missing testssl.sh dependencies
**Solution**: Ensure Dockerfile includes `bsdmainutils` for hexdump

### 2. Incorrect Grade
**Symptom**: Shows B when testssl.sh says A+
**Cause**: Not capturing testssl.sh's output
**Solution**: Use `--color 0` flag, check regex patterns

### 3. Duplicate Ciphers
**Symptom**: Same cipher appears multiple times
**Solution**: Use `processed_ciphers` set in parser

### 4. Missing GCM Ciphers
**Symptom**: Only showing CBC ciphers
**Solution**: Check cipher parsing logic includes all types

### 5. Nginx Permission Denied
**Symptom**: 403 errors when accessing frontend
**Cause**: Incorrect file permissions in container
**Solution**: Frontend Dockerfile includes chmod/chown commands

### 6. Too Many Worker Processes
**Symptom**: 30+ Celery processes on high-CPU systems
**Cause**: Default concurrency = CPU count
**Solution**: Limited to 2 workers in docker-compose.yml

### 7. Zombie Bash Processes
**Symptom**: Defunct bash processes accumulating
**Cause**: testssl.sh child processes not reaped
**Solution**: Added `init: true` to worker in docker-compose.yml

## Testing Checklist

1. **Deployment Test**
   ```bash
   ./clean-deploy.sh
   # Wait for "deployment complete"
   ```

2. **Functional Tests**
   - Scan google.com:443
   - Verify grade matches testssl.sh CLI
   - Click cipher details to expand
   - Check recent scans list

3. **Error Handling**
   - Try private IP (should reject)
   - Try invalid hostname
   - Try closed port

4. **Performance**
   - Run concurrent scans
   - Check memory usage
   - Verify cleanup works

## Adding Features

### New API Endpoint
```python
# In app.py
@app.get("/api/feature")
async def new_feature(db: Session = Depends(get_db)):
    # Implementation
    return {"status": "ok"}
```

### New Background Task
```python
# In worker.py
@celery_app.task
def new_task(param: str):
    # Implementation
    pass
```

### Frontend Feature
```javascript
// In frontend/app.js
async function newFeature() {
    const response = await fetch('/api/feature');
    const data = await response.json();
    // Update UI
}
```

## Performance Tuning

### Worker Concurrency
```yaml
# docker-compose.yml
command: celery -A worker worker --concurrency=4
```

### Database Pool
```python
# app.py
engine = create_engine(
    DATABASE_URL,
    pool_size=20,
    max_overflow=40
)
```

### Redis Memory
```yaml
# docker-compose.yml
command: redis-server --maxmemory 256mb --maxmemory-policy allkeys-lru
```

## Production Considerations

1. **HTTPS**: Use reverse proxy with SSL certificates
2. **Authentication**: Add auth middleware
3. **Monitoring**: Integrate Prometheus/Grafana
4. **Backups**: Automate PostgreSQL backups
5. **Updates**: Regular security patches
6. **Scaling**: Add more workers as needed

## Debugging Tips

### Check Worker Processing
```bash
docker compose exec redis redis-cli
> KEYS *
> LLEN celery
```

### Database Queries
```bash
docker compose exec postgres psql -U ssluser -d ssltestportal
\dt  # List tables
SELECT * FROM scans ORDER BY created_at DESC LIMIT 5;
```

### testssl.sh Direct Test
```bash
docker compose exec worker bash
cd /opt/testssl.sh
./testssl.sh --color 0 google.com:443
```

## Future Enhancements

1. **Real-time Updates**: WebSocket for live progress
2. **User Management**: Authentication/authorization
3. **Scheduling**: Cron-like recurring scans
4. **Notifications**: Email/webhook alerts
5. **Export Formats**: PDF, CSV reports
6. **API Keys**: For programmatic access
7. **Scan Templates**: Predefined scan configurations
8. **Comparison**: Side-by-side scan results

## Themes

- Web frontend theme supporting light and dark mode