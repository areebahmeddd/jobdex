# Security Policy

## Supported Versions

Only the latest release is supported. Fixes are applied to `main` and go out in the next release.

## Reporting a Vulnerability

Report privately through [GitHub Security Advisories](https://github.com/areebahmeddd/jobdex/security/advisories/new), or by email to <hi@areeb.dev>. Please do not open a public issue for a security report.

Include the affected endpoint or file, the steps to reproduce, and the impact you observed. Expect an acknowledgement within 72 hours and an assessment within a week.

## Scope

JobDex reads public, zero-auth ATS job boards and serves them through a public read-only API. There are no user accounts, and no personal data is collected or stored.

In scope:

- The API at `jobdex-api.1mindlabs.org` and the site at `jobdex.1mindlabs.org`
- Injection, authentication bypass on the payment endpoints, and data exposure through the API
- Dependency vulnerabilities that are reachable in this codebase

Out of scope:

- Volumetric denial of service
- Findings against the upstream ATS providers listed in the README
- Missing hardening headers with no demonstrated impact
