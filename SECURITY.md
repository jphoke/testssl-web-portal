# Security Policy

## Supported Versions

We support security updates for the following versions of testssl-web-portal:

| Version | Supported          |
| ------- | ------------------ |
| latest  | :white_check_mark: |
| < 1.0   | :x:                |

## Reporting a Vulnerability

If you discover a security vulnerability in testssl-web-portal, please report it responsibly:

### Private Disclosure Process

1. **DO NOT** create a public GitHub issue for security vulnerabilities
2. Create a GitHub issue using the "Security Vulnerability" template or email directly
3. Include the following information:
  - Description of the vulnerability
  - Steps to reproduce the issue
  - Potential impact assessment
  - Suggested mitigation (if any)


### Response Timeline

- **Initial Response**: Within 7 days (this is a side project maintained by one person)
- **Status Updates**: As available, typically every 2-4 weeks
- **Resolution Target**: Critical issues addressed as soon as possible, typically within 60-90 days depending on complexity and maintainer availability

## Security Considerations

### Architecture Security

This application processes user-provided hostnames and performs external SSL/TLS scans. Key security measures:

- **Input Validation**: All user inputs are validated and sanitized
- **Network Isolation**: Containerized environment prevents direct system access
- **Private IP Protection**: Scans against private IP ranges are blocked
- **Command Injection Prevention**: No direct shell command execution with user input

### Known Security Limitations

1. **testssl.sh Dependency**: This project relies on [testssl.sh](https://github.com/testssl/testssl.sh), which has the following security notice:
  > "testssl.sh is intended to be used as a standalone CLI tool. While we tried to apply best practice security measures and sanitize external input, we can't guarantee that the program is without any vulnerabilities. Running as a web service may pose security risks."

2. **External Network Access**: The application makes outbound connections to user-specified hosts for SSL/TLS testing

3. **Resource Consumption**: SSL/TLS scans can be resource-intensive and may be subject to abuse

### Production Security Recommendations

Before deploying to production, implement these additional security measures:

#### Authentication & Authorization
- Implement user authentication (not included in base application)
- Add role-based access controls
- Consider IP-based access restrictions

#### Rate Limiting & DoS Protection
- Implement rate limiting on scan requests
- Set maximum concurrent scans per user/IP
- Configure request timeouts and resource limits

#### Network Security
- Deploy behind a reverse proxy (nginx/Apache)
- Use HTTPS with proper TLS certificates
- Configure firewall rules to restrict outbound connections
- Consider using a DMZ for scan operations

#### Configuration Security
- Change all default passwords in `.env`
- Use strong, unique database passwords
- Implement secret management (HashiCorp Vault, AWS Secrets Manager)
- Regular security updates for all dependencies

#### Monitoring & Logging
- Enable comprehensive logging
- Monitor for suspicious scan patterns
- Set up alerting for failed authentication attempts
- Log all administrative actions

### Environment Variables Security

The following environment variables contain sensitive information:
- `SECRET_KEY`: JWT signing key - must be cryptographically secure (See SETUP.md for additional guidance)
- `POSTGRES_PASSWORD`: Database password
- `DATABASE_URL`: Contains database credentials

Ensure these are:
- Generated using cryptographically secure methods
- Stored securely (not in version control)
- Rotated regularly
- Accessible only to necessary services

### Container Security

When deploying with Docker:
- Run containers as non-root users where possible
- Use official, regularly updated base images
- Scan container images for vulnerabilities
- Implement container runtime security monitoring

### Data Protection

- Scan results may contain sensitive SSL/TLS configuration information
- Implement data retention policies
- Consider encryption at rest for sensitive scan data
- Ensure secure deletion of expired scan results

## Security Updates

- Monitor the [testssl.sh security advisories](https://github.com/testssl/testssl.sh/security/advisories)
- Security updates are provided on a best-effort basis as maintainer time allows
- Consider subscribing to notifications for this repository to stay informed
- For production deployments, implement your own monitoring of dependencies

## Disclaimer

**USE AT YOUR OWN RISK AND DISCRETION**

This project makes no warranty for the security, reliability, or fitness for purpose of the code. By using this software, you acknowledge that:

- SSL/TLS scanning can consume significant system resources
- Network scanning may trigger security alerts or protections on target systems
- Improper use could potentially disrupt services or cause unintended consequences
- The software may contain bugs, vulnerabilities, or other issues
- You are solely responsible for any outcomes resulting from use of this tool
- The authors, maintainers or other contributors make no promises that this wont break things, nor be secure in your environment. 

This is experimental software provided "as-is" without any guarantees. It could theoretically cause resource exhaustion, network issues, trigger security responses, immanentize the eschaton, or other unforeseen consequences.
- FNORD 

## Responsible Use

This tool is designed for:
- Security assessment of systems you own or have explicit permission to test
- Internal security audits and compliance checking
- Educational purposes in controlled environments

**DO NOT** use this tool for:
- Unauthorized scanning of third-party systems
- Malicious reconnaissance or exploitation
- Violating any applicable laws or regulations

## Security Contact

For security-related questions or concerns:
- Security issues: Create a private GitHub issue or discussion
- General questions: Create a GitHub issue (for non-security matters only)

## Acknowledgments

We appreciate the security research community and encourage responsible disclosure. This is a personal open-source project maintained in spare time, so please be patient with response times.

---

*This security policy is reviewed periodically and updated as needed. Last updated: **24-July-2025**
