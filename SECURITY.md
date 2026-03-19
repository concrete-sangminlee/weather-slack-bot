# Security Policy

## Supported Versions

| Version | Supported |
|---------|-----------|
| 2.x     | ✅        |
| 1.x     | ❌        |

## Reporting a Vulnerability

If you discover a security vulnerability, please report it responsibly:

1. **Do not** open a public GitHub issue
2. Email: concrete.sangminlee@gmail.com
3. Include:
   - Description of the vulnerability
   - Steps to reproduce
   - Potential impact

## Security Considerations

- **Slack Bot Token**: Stored as GitHub Secret, never committed to code
- **API Keys**: No API keys required (Open-Meteo is keyless)
- **No User Data**: This bot does not collect, store, or process any user data
- **Dependencies**: Monitored by Dependabot for known vulnerabilities
- **CI/CD**: All changes require passing tests before deployment

## Response Timeline

- Acknowledgment: within 48 hours
- Assessment: within 1 week
- Fix (if applicable): within 2 weeks
