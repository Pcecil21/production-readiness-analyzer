# Production Readiness Analyzer

A CLI tool that audits codebases for production readiness across security, reliability, observability, and operational maturity.

## What It Checks

| Category | Checks |
|---|---|
| **Security** | Hardcoded secrets, dependency lockfiles, `.env` in `.gitignore`, HTTPS enforcement |
| **Reliability** | Error handling patterns, health check endpoints, graceful shutdown, retry logic |
| **Observability** | Structured logging, metrics endpoints, distributed tracing, alerting configs |
| **Testing** | Test file presence, CI pipeline config, coverage config, e2e tests |
| **Documentation** | README, API docs, runbooks, architecture decision records |
| **Operations** | Dockerfiles, K8s manifests, IaC templates, backup configs |

## Quick Start

```bash
# Install
pip install -e .

# Analyze current directory
production-readiness-analyzer .

# Analyze with specific output format
production-readiness-analyzer ./my-project --format json

# Only run specific categories
production-readiness-analyzer . --categories security,testing
```

## Example Output

```
Production Readiness Report: my-project
========================================

Overall Score: 72/100  [██████████████░░░░░░]  NEEDS WORK

Security .............. 85/100  ██████████████████░░
Reliability ........... 60/100  ████████████░░░░░░░░
Observability ......... 55/100  ███████████░░░░░░░░░
Testing ............... 90/100  ██████████████████░░
Documentation ......... 70/100  ██████████████░░░░░░
Operations ............ 72/100  ██████████████░░░░░░

Critical Issues (2):
  [SEC-001] Possible hardcoded API key in src/config.py:23
  [REL-003] No health check endpoint detected

Warnings (5):
  [OBS-002] No structured logging library detected
  [DOC-001] Missing CHANGELOG.md
  ...
```

## Configuration

Create a `.readiness.yml` in your project root to customize:

```yaml
# Exclude paths from scanning
exclude:
  - vendor/
  - node_modules/
  - "*.test.*"

# Adjust severity thresholds
thresholds:
  overall: 80
  security: 90
  testing: 75

# Disable specific checks
disabled_checks:
  - OPS-004  # skip k8s manifest check
```

## Development

```bash
git clone https://github.com/Pcecil21/production-readiness-analyzer.git
cd production-readiness-analyzer
pip install -e ".[dev]"
pytest
```

## License

MIT
