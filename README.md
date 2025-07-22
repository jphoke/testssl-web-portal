# SSL Test Portal

A modern, secure SSL/TLS testing portal built with FastAPI, PostgreSQL, Redis, and Celery. This application provides comprehensive SSL/TLS security assessment using testssl.sh.

## Features

- ✅ **Comprehensive SSL/TLS Testing**: Tests protocols, ciphers, vulnerabilities, and certificate details
- ✅ **Modern Architecture**: FastAPI backend with PostgreSQL database and Redis caching
- ✅ **Background Processing**: Celery workers for asynchronous scan execution
- ✅ **Real-time Updates**: Progress tracking during scans
- ✅ **Security Grading**: Automatic calculation of security grades (A+ to F)
- ✅ **Interactive UI**: Expandable cipher details and comprehensive result display
- ✅ **RESTful API**: Full API with OpenAPI documentation
- ✅ **Docker Deployment**: Fully containerized with Docker Compose

## Prerequisites

- Docker Engine 20.10+
- Docker Compose v2.0+
- 2GB+ RAM available
- 5GB+ disk space

## Quick Start

1. **Clone the repository and navigate to the project**:
   ```bash
   git clone <repository-url>
   cd testssl-new-web
   ```

2. **Run the clean deployment script**:
   ```bash
   chmod +x clean-deploy.sh
   ./clean-deploy.sh
   ```

   This will:
   - Build all Docker images
   - Initialize the database
   - Start all services
   - Perform health checks

3. **Access the application**:
   - Web UI: http://localhost:3000
   - API Documentation: http://localhost:8000/docs
   - API Health Check: http://localhost:8000/api/health

## Manual Deployment

If you prefer manual deployment or need to customize the process:

1. **Create environment file**:
   ```bash
   cp .env.example .env
   # Generate a secure secret key
   SECRET_KEY=$(openssl rand -hex 32)
   # Update .env with the secret key (macOS)
   sed -i '' "s/your-secret-key-here-use-openssl-rand-hex-32/$SECRET_KEY/" .env
   # Or for Linux:
   # sed -i "s/your-secret-key-here-use-openssl-rand-hex-32/$SECRET_KEY/" .env
   ```

2. **Create required directories**:
   ```bash
   mkdir -p logs results
   ```

3. **Build and start services**:
   ```bash
   docker compose build
   docker compose up -d
   ```

4. **Verify deployment**:
   ```bash
   docker compose ps
   curl http://localhost:8000/api/health
   ```

## Usage

### Running SSL Scans

1. Open the web UI at http://localhost:3000
2. Enter a hostname (e.g., `example.com`) and port (default: 443)
3. Click "Start Scan"
4. Monitor progress in real-time
5. View comprehensive results including:
   - Security grade (A+ to F)
   - Protocol support (SSL 2/3, TLS 1.0-1.3)
   - Cipher suites (click to expand for full details)
   - Vulnerabilities (BEAST, CRIME, POODLE, SWEET32, etc.)
   - Certificate information
   - Security headers

### Viewing Previous Scans

Recent scans are displayed in the sidebar. Click any scan to view its results.

## Utility Scripts

### Deployment Scripts

#### Standard Deployment (`deploy.sh`)

Use this for regular deployments and updates:

```bash
./deploy.sh
```

This script:
- Preserves existing data and scan history
- Updates containers with latest code
- Maintains database content
- Good for: Updates, restart after shutdown, applying changes

**When to use**: When you want to update the application while keeping your scan history.

#### Clean Deployment (`clean-deploy.sh`) 

Use this for fresh installations or complete resets:

```bash
./clean-deploy.sh
```

This script:
- **Removes ALL existing data** (prompts for confirmation)
- Deletes volumes, databases, and scan results
- Rebuilds everything from scratch
- Creates fresh `.env` with new secret key
- Good for: First installation, major issues, clean slate

**When to use**: First time setup or when you need to completely reset everything.

### Debug Script (`debug.sh`)

Check system status and troubleshoot issues:

```bash
./debug.sh
```

This shows:
- Running services status
- Worker logs (last 50 lines)
- Recent scan results
- Database records
- API health status
- Container resource usage

### Data Cleanup Script (`cleanup-data.sh`)

Remove old scan data to manage disk space:

```bash
# Keep last 30 days of scans (default)
./cleanup-data.sh

# Keep only last 7 days
./cleanup-data.sh --days 7

# Delete all scan history (careful!)
./cleanup-data.sh --all

# Show help
./cleanup-data.sh --help
```

**Note**: This script is for administrative use only and requires typing "yes" for confirmation before deleting data.

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
                    │   Cache     │     │   Worker    │
                    └─────────────┘     └─────────────┘
                                               │
                                               ▼
                                        ┌─────────────┐
                                        │ testssl.sh  │
                                        └─────────────┘
```

## Services

- **Frontend (Nginx)**: Static file serving on port 3000
- **Backend (FastAPI)**: REST API on port 8000
- **Database (PostgreSQL)**: Data persistence
- **Cache (Redis)**: Job queue and temporary data
- **Worker (Celery)**: Background scan execution
- **Scanner (testssl.sh)**: SSL/TLS security testing from https://github.com/testssl/testssl.sh

## API Endpoints

- `GET /api/health` - Health check
- `POST /api/scans` - Create new scan
- `GET /api/scans` - List recent scans
- `GET /api/scans/{scan_id}` - Get scan details
- `GET /api/scans/{scan_id}/status` - Get scan status and progress
- `GET /api/scans/{scan_id}/results` - Get scan results

Full API documentation with interactive testing available at http://localhost:8000/docs

## Security Features

- Input validation for all user inputs
- Hostname/IP validation (no private IPs)
- No direct command execution
- Containerized environment isolation
- Secure default configuration

## Troubleshooting

### Scans failing quickly (< 1 second)
- Check worker logs: `docker compose logs worker`
- Verify testssl.sh dependencies: `docker compose exec worker /opt/testssl.sh/testssl.sh --version`
- Run debug script: `./debug.sh`

### Database connection errors
- Check PostgreSQL status: `docker compose ps postgres`
- Verify credentials in `.env` file
- Check database logs: `docker compose logs postgres`

### Frontend not loading
- Check Nginx logs: `docker compose logs frontend`
- Verify port 3000 is not in use: `lsof -i :3000`
- Clear browser cache

### General debugging
- Run the debug script: `./debug.sh`
- Check all logs: `docker compose logs -f`
- Check container health: `docker compose ps`

## Development

### Modifying the code

1. Make changes to source files
2. Rebuild affected services:
   ```bash
   docker compose build <service-name>
   docker compose up -d <service-name>
   ```

### Adding new dependencies

1. Update `requirements.txt` for Python packages
2. Update `Dockerfile` for system packages
3. Rebuild: `docker compose build --no-cache`

## Maintenance

### Backup database
```bash
docker compose exec postgres pg_dump -U ssluser ssltestportal > backup_$(date +%Y%m%d).sql
```

### Restore database
```bash
cat backup.sql | docker compose exec -T postgres psql -U ssluser ssltestportal
```

### View logs
```bash
# All services
docker compose logs -f

# Specific service
docker compose logs -f worker

# Save logs to file
docker compose logs > all_logs_$(date +%Y%m%d).txt
```

### Update testssl.sh
The application uses the official testssl.sh from https://github.com/testssl/testssl.sh.git
To update, rebuild the worker container:
```bash
docker compose build --no-cache worker
docker compose up -d worker
```

## Performance Tuning

### Adjust worker concurrency
Edit `docker-compose.yml` and modify the worker command:
```yaml
command: celery -A worker worker --loglevel=info --concurrency=4
```

### Database connection pooling
Adjust in `app.py`:
```python
engine = create_engine(DATABASE_URL, pool_size=20, max_overflow=40)
```

## Security Notes for Production

- Change all default passwords in `.env`
- Use HTTPS with proper certificates
- Implement authentication/authorization
- Add rate limiting to prevent abuse
- Configure firewall rules
- Regular security updates
- Monitor logs for suspicious activity

## License

This project inherits the GPL v3 license from testssl.sh

## Acknowledgments

- [testssl.sh](https://github.com/testssl/testssl.sh) for SSL/TLS testing functionality
- FastAPI for the modern Python web framework
- Docker for containerization
- PostgreSQL for reliable data storage
- Redis for high-performance caching
- Celery for distributed task processing