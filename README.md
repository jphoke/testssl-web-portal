# TestSSL Web Portal

A modern web-based SSL/TLS testing portal built with FastAPI, PostgreSQL, Redis, and Celery. Provides comprehensive SSL/TLS security assessment using [testssl.sh](https://github.com/testssl/testssl.sh).

## Features

- 🔒 **Comprehensive Testing**: Protocols, ciphers, vulnerabilities, and certificates
- 📊 **Security Grading**: Automatic A+ to F ratings
- 🚀 **Scalable Architecture**: Async processing with configurable workers
- 📝 **Scan Comments**: Add notes to identify scans
- 🔄 **Real-time Updates**: Live progress tracking
- 📚 **REST API**: Full OpenAPI documentation
- 🐳 **Docker Ready**: Complete containerization

## Screenshots

<img width="512" height="352" alt="Main Interface" src="https://github.com/user-attachments/assets/76c3e84c-50fe-4a2e-99de-e3ff491e6928" />
<img width="512" height="551" alt="Scan Results" src="https://github.com/user-attachments/assets/ebd88b8f-d4ad-4816-8abe-d570282829ba" />
<img width="512" height="542" alt="Detailed Results" src="https://github.com/user-attachments/assets/7e409274-b183-40f5-8d4f-e3f29e17954a" />

## Quick Start

```bash
# Clone the repository
git clone https://github.com/jphoke/testssl-web-portal
cd testssl-web-portal

# Deploy (prompts for secure database password)
./clean-deploy.sh
```

**Access the portal:**
- Web UI: http://localhost:3000
- API Docs: http://localhost:8000/docs

For detailed setup instructions, see [SETUP.md](SETUP.md).

## Configuration

Key settings in `.env` (created during deployment):

```bash
WORKER_CONCURRENCY=2        # Number of concurrent scans
SCAN_TIMEOUT=600           # Timeout per scan (seconds)
MAX_CONCURRENT_SCANS_PER_IP=2    # Per-IP limits (not yet enforced)
```

See [SETUP.md](SETUP.md#configuration-options) for all options.

## Usage

1. **Run a scan**: Enter hostname/IP and port → Start Scan
2. **Add context**: Optional comment field (100 chars)
3. **View results**: Real-time progress and detailed security analysis
4. **Check history**: Recent scans in sidebar

## Architecture

```
Frontend (Nginx:3000) → API (FastAPI:8000) → Database (PostgreSQL)
                              ↓
                        Redis Queue → Celery Workers → testssl.sh
```

## Utility Scripts

| Script | Purpose | When to Use |
|--------|---------|-------------|
| `./deploy.sh` | Standard deployment | Updates, restarts |
| `./clean-deploy.sh` | Fresh installation | First setup, full reset |
| `./debug.sh` | System diagnostics | Troubleshooting |
| `./cleanup-data.sh` | Data management | Disk space cleanup |

See script details in [SETUP.md](SETUP.md#common-tasks).

## API Reference

Core endpoints:
- `POST /api/scans` - Create scan
- `GET /api/scans/{id}/status` - Check progress
- `GET /api/scans/{id}/results` - Get results

Full documentation at http://localhost:8000/docs

## Security

- ✅ Input validation and sanitization
- ✅ XSS prevention
- ✅ Security headers (X-Frame-Options, etc.)
- ✅ Containerized isolation
- ✅ No direct command execution
- ✅ Enforced secure passwords

For production deployment, see [SETUP.md](SETUP.md#production-deployment).

## Development

**Project structure:**
- `app.py` - FastAPI backend
- `worker.py` - Celery scan processor  
- `frontend/` - Web UI (HTML/JS/CSS)
- `docker-compose.yml` - Service orchestration

**Making changes:**
```bash
# Modify code
# Rebuild service
docker compose build <service>
docker compose up -d <service>
```

For detailed development info, see [CLAUDE.md](CLAUDE.md).

## Troubleshooting

Common issues:
- **Scans fail quickly**: Check `docker compose logs worker`
- **Can't access UI**: Verify ports 3000/8000 are free
- **Database errors**: Check credentials in `.env`

Run `./debug.sh` for comprehensive diagnostics.

## Contributing

1. Fork the repository
2. Create feature branch
3. Make changes with tests
4. Submit pull request

See [TODO.md](TODO.md) for planned features.

## License

GPL v3 (inherited from testssl.sh)

## Acknowledgments

Built with:
- [testssl.sh](https://github.com/testssl/testssl.sh) - Core SSL/TLS testing
- [FastAPI](https://fastapi.tiangolo.com/) - Modern Python framework
- [Claude Code](https://github.com/anthropics/claude-code) - AI development assistance

---

**Links:** [Issues](https://github.com/jphoke/testssl-web-portal/issues) | [Changelog](CHANGELOG.md) | [Security](SECURITY.md)