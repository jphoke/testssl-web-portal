# Contributing to TestSSL Web Portal

Thank you for your interest in contributing to the TestSSL Web Portal! This document provides guidelines for contributing to the project.

## Getting Started

1. Fork the repository
2. Clone your fork locally
3. Create a new branch for your feature or bugfix
4. Make your changes
5. Test thoroughly
6. Submit a pull request

## Development Setup

1. Ensure you have Docker and Docker Compose installed
2. Clone the repository
3. Copy `.env.example` to `.env` and configure
4. Run `./clean-deploy.sh` for a fresh start

## Code Standards

### Python Code (Backend)
- Follow PEP 8 style guidelines
- Use type hints where appropriate
- Add docstrings to functions and classes
- Keep functions focused and small
- Write tests for new functionality

### JavaScript Code (Frontend)
- Use modern ES6+ syntax
- Keep the code simple and readable
- Comment complex logic
- Maintain consistent indentation

### General Guidelines
- No hardcoded credentials or secrets
- Validate all user inputs
- Handle errors gracefully
- Log important events
- Keep security in mind

## Testing

Before submitting a PR:
1. Test the full deployment with `./clean-deploy.sh`
2. Run a few test scans
3. Check the logs for errors
4. Verify the UI works correctly
5. Test edge cases

## Pull Request Process

1. Update the README.md with details of changes if needed
2. Update the CHANGELOG.md with your changes
3. Ensure all tests pass
4. Request review from maintainers

## Reporting Issues

When reporting issues, please include:
- Description of the problem
- Steps to reproduce
- Expected behavior
- Actual behavior
- System information (OS, Docker version)
- Relevant logs

## Security Vulnerabilities

If you discover a security vulnerability, please email the maintainers directly rather than creating a public issue.

## Questions?

Feel free to open an issue for any questions about contributing.