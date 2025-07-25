# Changelog

All notable changes to the TestSSL Web Portal will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [1.0.2] - 2025-07-26

### Added
- Comments feature for SSL scans
  - Optional comment field (0-100 characters) on scan submission form
  - Comments displayed in scan results and recent scans list
  - Server-side validation and sanitization for security
  - Client-side HTML escaping to prevent XSS
  - Database schema updated with new comment column
  - API endpoints updated to handle comments in all relevant operations
- Configurable resource limits via environment variables
  - WORKER_CONCURRENCY: Control number of concurrent testssl.sh scans (default: 2)
  - SCAN_TIMEOUT: Configurable timeout per scan in seconds (default: 300)
  - MAX_CONCURRENT_SCANS_PER_IP: Define per-IP limits (default: 2, not yet enforced)
  - MAX_SCANS_PER_HOUR: Rate limiting configuration (default: 0/unlimited, not yet enforced)
  - Additional options for disk usage and auto-cleanup defined in .env.example

### Changed
- Deployment scripts now display configuration options and instructions after completion

### Security
- Improved error handling to prevent information disclosure
  - Internal exceptions now show generic user-friendly messages with reference IDs
  - Detailed error information logged server-side only for debugging
  - Prevents exposure of file paths, stack traces, and system configuration details
- Added security headers to nginx configuration
  - X-Frame-Options: SAMEORIGIN
  - X-Content-Type-Options: nosniff
  - X-XSS-Protection: 1; mode=block
  - Referrer-Policy: no-referrer-when-downgrade
- Removed unnecessary CORS middleware
  - Eliminated potential CSRF attack vector
  - API is only accessed via nginx proxy (same origin)
  - No functionality impact since no cross-origin requests occur

## [1.0.1] - 2025-07-25 (Unreleased internal testing only)

### Fixed
- Fixed connection failure detection - scans against closed ports now properly show error status instead of incorrect "B" grade
- Fixed error message display in scan progress section to show actual connection failure reason
- Fixed error message display in recent scans list to show detailed error below status badge
- Fixed oversized heading text in error results display
- Added proper error information to API responses (/api/scans and /api/scans/{id}/status endpoints)

### Added
- Added cache prevention headers to nginx configuration to prevent browser caching of JS/CSS/HTML files
- Added comprehensive error messages for different connection failure scenarios:
  - "Connection refused" - when target port is not accepting connections
  - "Unable to connect" - when host/port is unreachable
  - "TCP connect problem" - when blocked by firewall or network issues

### Changed
- Updated worker to check testssl.sh exit codes and output for connection failures
- Enhanced frontend error handling to display connection errors with helpful suggestions

### Security
- Added defense-in-depth command injection prevention:
  - API validates hosts/IPs against dangerous shell characters
  - Only allows alphanumeric, dots, and hyphens in hostnames
  - Validates IP addresses using Python's ipaddress module
  - Worker performs additional validation before executing commands
  - Supports all valid hostnames and IP addresses including private/RFC1918 ranges

## [1.0.0] - First Public Release

### Added
- Initial release of TestSSL Web Portal
- Web-based interface for SSL/TLS security testing
- Integration with testssl.sh for comprehensive scanning
- Real-time progress tracking during scans
- Historical scan results storage
- Expandable cipher suite details
- Support for all testssl.sh grades including A-F, +/- modifiers, M, and T
- Scan ID display in recent scans list for easier tracking and sharing
- Certificate expiration warnings with color coding (red/yellow/green)
- Docker Compose deployment
- PostgreSQL database for persistence
- Redis for job queuing
- Celery workers for background processing
- RESTful API with OpenAPI documentation (Swagger UI at /docs)
- Responsive web UI
- Data cleanup utilities
- Debug utilities
- Secure database password prompting in deployment scripts
- Docker init system for automatic zombie process cleanup
- Password strength requirements (minimum 12 characters)

### Changed
- Improved cipher strength classification with proper color coding:
  - Green (✅) for strong/modern ciphers
  - Yellow (⚠️) for medium/questionable ciphers
  - Red (❌) for weak/obsolete ciphers
- Enhanced cipher detection to identify obsolete algorithms (3DES, RC4, MD5, etc.)
- Ciphers on deprecated protocols (TLS 1.0/1.1) now marked as weak
- Limited Celery worker concurrency to 2 (from default CPU count)
- Updated deployment scripts to prevent use of default passwords

### Fixed
- Fixed zombie process issue by implementing proper process tree management with psutil
- Fixed grade extraction to use testssl.sh native grades (A+, A, A-, B-F, M, T)
- Fixed subprocess handling to prevent lingering bash processes on Linux
- Added proper cleanup of temporary JSON files
- Improved timeout handling for stuck scans
- Fixed nginx permission issues in frontend container
- Resolved Celery process spawning too many workers on high-CPU systems

### Security
- Input validation for all user inputs
- Protection against private IP scanning
- No direct command execution
- Secure containerized environment
- Deployment scripts now enforce secure database passwords
- Removed ability to deploy with default "changeme" passwords
- Added password confirmation to prevent typos
- Frontend files properly secured with correct permissions

### Technical
- Added psutil dependency for process management
- Replaced subprocess.run() with Popen() for better process control
- Implemented process groups for reliable cleanup of child processes
- Added `init: true` to docker-compose.yml for proper PID 1 handling
- Fixed frontend Dockerfile permissions with chmod/chown

### Attribution
- Uses testssl.sh (https://github.com/testssl/testssl.sh) for SSL/TLS testing
