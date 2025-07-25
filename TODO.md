# TODO

## Next Priority Features
- **Rate Limiting Enforcement**: Implement MAX_CONCURRENT_SCANS_PER_IP and MAX_SCANS_PER_HOUR at application level
- **STARTTLS Protocol Support**: Add support for testing TLS on SMTP, IMAP, POP3, FTP, PostgreSQL, MySQL ports
- **Export Functionality**: Generate PDF/CSV reports of scan results
- **API Authentication**: Add optional OAuth2/API key authentication for programmatic access

## Performance Enhancements
- **Optimize testssl.sh Speed**: 
  - Investigate --fast and --sneaky options
  - Consider parallel cipher testing
  - Cache DNS lookups
- **Nginx Rate Limiting**: Implement at proxy level for better performance
  - 2 scans/minute per IP for POST /api/scans
  - 60 requests/minute for status polling
  - 120 requests/minute general API
- **WebSocket Support**: Replace polling with real-time updates
- **Smart Polling**: Implement exponential backoff for frontend status checks

## Enterprise Features
- **Authentication Providers**: 
  - LDAP/Active Directory integration
  - SAML 2.0 support
  - OAuth2 providers (Google, GitHub, Azure AD)
- **Scheduled Scans**: Cron-like syntax for recurring scans
- **Notifications**: 
  - Email alerts on scan completion
  - Webhook support for integrations
  - Slack/Teams notifications
- **Scan Comparison**: Side-by-side diff view of scan results
- **Access Control**:
  - IP allowlist/blocklist
  - User roles and permissions
  - Scan quotas per user/group
- **Audit Logging**: 
  - Track all API access with client IPs
  - Scan history with user attribution
  - Export audit logs

## UI/UX Improvements
- **Dark Mode**: Theme toggle with system preference detection
- **Scan Templates**: Save and reuse common scan configurations
- **Bulk Operations**: 
  - Import CSV/JSON list of hosts to scan
  - Batch operations UI
  - Queue management interface
- **Enhanced Results View**:
  - Printable reports
  - Shareable result links (with expiration)
  - Result history graphs

## Advanced Features
- **Configurable Grading**: 
  - Custom rules (e.g., TLS 1.0 = auto-fail)
  - Organization-specific compliance profiles
  - Industry standard templates (PCI-DSS, HIPAA)
- **Integration APIs**:
  - Prometheus metrics endpoint
  - Grafana dashboard templates
  - CI/CD pipeline integration
- **Change Control Integrations**:
  - ServiceNow integration for change requests
  - Ivanti/Cherwell ticket creation
  - BMC Remedy connector
  - Auto-create change tickets for critical findings
- **Issue Tracking Integrations**:
  - Jira integration for security findings
  - Auto-create issues for non-compliant configurations
  - GitHub/GitLab issue creation
  - Azure DevOps work items
  - Bulk issue creation with finding details
- **Multi-tenancy**: 
  - Separate data per organization
  - Custom branding options
  - Usage analytics per tenant

## Code Quality & DevOps
- **Testing Suite**:
  - Unit tests for validators and parsers
  - Integration tests for API endpoints
  - End-to-end tests with Playwright/Selenium
- **Structured Logging**:
  - JSON log format
  - Log levels (DEBUG, INFO, WARN, ERROR)
  - Log aggregation ready (ELK stack compatible)
- **Documentation**:
  - OpenAPI schema improvements
  - Architecture decision records (ADRs)
  - Deployment guides for K8s, AWS, Azure
- **Performance**:
  - Benchmark suite for load testing
  - Database query optimization
  - Redis caching strategy

## Technical Debt
- **Database Migrations**: Implement Alembic for schema version control
- **Configuration Management**: Move all hardcoded values to environment variables
- **Error Handling**: Consistent error response format across all endpoints
- **Code Organization**: Split large files into modules (app.py → routes/, models/, services/)

---

## Completed ✓
See [CHANGELOG.md](CHANGELOG.md) for completed features and fixes.