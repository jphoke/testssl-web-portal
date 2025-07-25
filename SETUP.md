# TestSSL Web Portal - Setup Guide

This guide provides instructions for setting up the TestSSL Web Portal.

## Prerequisites

- Docker Engine 20.10+
- Docker Compose v2.0+
- 2GB+ RAM available
- 5GB+ disk space
- Internet connection

## Quick Setup (Recommended)

```bash
# Clone the repository
git clone https://github.com/jphoke/testssl-web-portal
cd testssl-web-portal

# Run the clean deployment script
chmod +x clean-deploy.sh
./clean-deploy.sh
```

The script will:
- Build all Docker images
- Prompt for a secure database password (12+ characters required)
- Generate security keys automatically
- Start all services
- Display configuration options

**Access the portal:**
- Web UI: http://localhost:3000
- API Docs: http://localhost:8000/docs

## Configuration Options

After deployment, you can customize settings in the `.env` file:

### Worker Settings
```bash
WORKER_CONCURRENCY=2        # Number of concurrent scans (increase for internal use)
SCAN_TIMEOUT=300           # Timeout per scan in seconds (default: 5 minutes)
```

### Rate Limiting (defined but not yet enforced)
```bash
MAX_CONCURRENT_SCANS_PER_IP=2    # Limit concurrent scans per IP
MAX_SCANS_PER_HOUR=0             # Hourly scan limit (0 = unlimited)
```

### Resource Management
```bash
MAX_DISK_USAGE_MB=5000           # Max disk usage for results
AUTO_CLEANUP_DAYS=90             # Auto-delete old scans
TESTSSL_FAST_MODE=false          # Use testssl.sh --fast flag
```

**To apply changes:**
```bash
# Edit .env file
nano .env

# Restart services
docker compose restart
```

## Manual Setup

If you need custom configuration:

### 1. Create Environment File
```bash
cp .env.example .env

# Generate secret key
SECRET_KEY=$(openssl rand -hex 32)

# Update .env with the secret key
sed -i "s/your-secret-key-here-use-openssl-rand-hex-32/$SECRET_KEY/" .env

# IMPORTANT: Edit .env and change DB_PASSWORD to a secure password (12+ chars)
```

### 2. Build and Start
```bash
# Create directories
mkdir -p logs results

# Build images
docker compose build

# Start services
docker compose up -d

# Verify deployment
docker compose ps
curl http://localhost:8000/api/health
```

## Common Tasks

### View Logs
```bash
docker compose logs -f          # All services
docker compose logs -f worker   # Just worker logs
```

### Update Services
```bash
docker compose down
git pull
docker compose build
docker compose up -d
```

### Check Status
```bash
./debug.sh
```

### Stop Services
```bash
docker compose down
```

## Production Deployment

### 1. Security Checklist
- [ ] Change default database password (enforced by scripts)
- [ ] Use HTTPS with proper certificates
- [ ] Restrict CORS in app.py (currently allows all origins)
- [ ] Configure firewall rules
- [ ] Set up regular backups
- [ ] Enable monitoring

### 2. Performance Tuning
For high-traffic deployments:
```bash
# Edit .env
WORKER_CONCURRENCY=6    # Increase workers
SCAN_TIMEOUT=180       # Reduce timeout for faster turnover
```

### 3. HTTPS Configuration
Use a reverse proxy (nginx/traefik) with SSL certificates:
```nginx
server {
    listen 443 ssl http2;
    server_name your-domain.com;
    
    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;
    
    location / {
        proxy_pass http://localhost:3000;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
}
```

### 4. Backup Script
```bash
#!/bin/bash
# Save as backup.sh
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/backups/ssltestportal"

# Backup database
docker compose exec -T postgres pg_dump -U ssluser ssltestportal | \
    gzip > "$BACKUP_DIR/db_$DATE.sql.gz"

# Keep last 30 days only
find "$BACKUP_DIR" -name "db_*.sql.gz" -mtime +30 -delete
```

## Troubleshooting

### Services Won't Start
```bash
# Check logs for errors
docker compose logs --tail=50

# Rebuild if needed
docker compose down -v
./clean-deploy.sh
```

### Scans Not Processing
```bash
# Check worker status
docker compose logs worker --tail=50

# Check Redis queue
docker compose exec redis redis-cli LLEN celery
```

### Port Conflicts
Edit `docker-compose.yml` to change ports:
```yaml
services:
  frontend:
    ports:
      - "3001:80"   # Change from 3000
  app:
    ports:
      - "8001:8000" # Change from 8000
```

## Support

- Logs: Run `./debug.sh` for system diagnostics
- Documentation: See README.md and CHANGELOG.md
- Issues: https://github.com/jphoke/testssl-web-portal/issues