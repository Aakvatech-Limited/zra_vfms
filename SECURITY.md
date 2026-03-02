# Security Policy

## Reporting a Vulnerability

The ZRA VFMS team takes security issues seriously. We appreciate your efforts to responsibly disclose your findings.

### How to Report

**Please do NOT report security vulnerabilities through public GitHub issues.**

Instead, please report them via email to: **emgani@aakvatech.com**

Include the following information in your report:

- Type of issue (e.g., SQL injection, XSS, authentication bypass, etc.)
- Full paths of source file(s) related to the issue
- Location of the affected source code (tag/branch/commit or direct URL)
- Step-by-step instructions to reproduce the issue
- Proof-of-concept or exploit code (if possible)
- Impact of the issue and potential attack scenarios

### Response Timeline

- **Initial Response**: Within 48 hours
- **Status Update**: Within 7 days
- **Resolution Target**: Within 30 days (depending on complexity)

## Supported Versions

| Version | Supported |
| ------- | --------- |
| 15.x.x  | Yes       |

## Security Best Practices

When developing with ZRA VFMS:

1. **Always use Frappe's ORM** - Avoid raw SQL queries
2. **Validate user input** - Use Frappe's built-in validation
3. **Check permissions** - Use `frappe.has_permission()`
4. **Sanitize output** - Use `frappe.utils.escape_html()` when needed
5. **Avoid `eval()` and `exec()`** - Use safer alternatives
6. **Protect API credentials** - Use Frappe's Password field type for tokens
