# Production Readiness Analyzer

A comprehensive CLI tool that audits codebases for production readiness across 13 categories with 70+ checks.

## What It Checks

| Category | Checks | Inspired By |
|---|---|---|
| **Security** | Hardcoded secrets, dependency lockfiles, `.env` exposure | security review |
| **Reliability** | Health endpoints, graceful shutdown, retry logic, error handling | SRE best practices |
| **Observability** | Structured logging, metrics, distributed tracing, alerting | monitoring & ops |
| **Testing** | Test files, CI pipelines, coverage config, e2e tests | QA |
| **Documentation** | README quality, API docs, ADRs, changelog, contributing guide | technical writing |
| **Operations** | Dockerfiles, K8s manifests, IaC, dockerignore | DevOps |
| **Code Quality** | File size, function length, TODO debt, SQL injection, duplication, nesting depth | code review & simplification |
| **Release** | Versioning, changelog, release automation, lockfiles, CODEOWNERS | shipping workflows |
| **Architecture** | ADRs, layered structure, circular imports, config management, DB migrations, API versioning, DI | engineering planning |
| **Accessibility** | Alt text, form labels, ARIA landmarks, focus styles, responsive design, a11y testing tools | browser QA & WCAG |
| **API Design** | OpenAPI specs, rate limiting, auth, error formats, input validation, CORS, pagination | API development |
| **Developer Experience** | Linting, formatting, pre-commit hooks, editor config, task runners, contributing guide, dev containers | DX & onboarding |
| **Process** | CI completeness (test/lint/security/deploy steps), PR templates, issue templates, Dependabot, CODEOWNERS, scheduled jobs | engineering process & retros |

## Quick Start

```bash
# Install
pip install -e .

# Analyze current directory (all 13 categories)
production-readiness-analyzer .

# JSON output for CI pipelines
production-readiness-analyzer ./my-project --format json

# Only run specific categories
production-readiness-analyzer . --categories security,testing,api_design

# List all available categories
production-readiness-analyzer . --list-categories

# Set a minimum score threshold (exit code 1 if below)
production-readiness-analyzer . --threshold 80
```

## Example Output

```
╭──────────── Production Readiness Report: my-project ─────────────╮
│ Overall Score: 68/100  [█████████████░░░░░░░]  NEEDS WORK        │
╰──────────────────────────────────────────────────────────────────╯

Security              85/100  █████████████████░░░
Reliability           60/100  ████████████░░░░░░░░
Observability         55/100  ███████████░░░░░░░░░
Testing               90/100  ██████████████████░░
Documentation         70/100  ██████████████░░░░░░
Operations            72/100  ██████████████░░░░░░
Code Quality          78/100  ████████████████░░░░
Release               65/100  █████████████░░░░░░░
Architecture          60/100  ████████████░░░░░░░░
Accessibility        100/100  ████████████████████
API Design            45/100  █████████░░░░░░░░░░░
Developer Experience  72/100  ██████████████░░░░░░
Process               55/100  ███████████░░░░░░░░░

Critical Issues (3):
  [SEC-001] Possible hardcoded API key in src/config.py:23
  [API-003] No authentication/authorization patterns detected
  [PRC-003] No CI/CD pipeline

Warnings (8):
  [OBS-002] No metrics library or endpoint detected
  [CQ-001]  src/monolith.py has 847 lines — consider splitting
  [DX-001]  No linting configuration found
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
  - OPS-004   # skip k8s manifest check
  - A11Y-000  # skip accessibility (no frontend)
  - API-000   # skip API design (not an API)
```

## All Check IDs

<details>
<summary>Click to expand full check reference</summary>

### Security (SEC)
- `SEC-001` Hardcoded secrets (API keys, passwords, tokens)
- `SEC-002` Missing dependency lockfile
- `SEC-003` `.env` not in `.gitignore`
- `SEC-004` `.env` file committed to repo

### Reliability (REL)
- `REL-001` No health check endpoint
- `REL-002` No graceful shutdown handling
- `REL-003` No retry / circuit breaker logic
- `REL-004` No error handling patterns

### Observability (OBS)
- `OBS-001` No structured logging
- `OBS-002` No metrics endpoint/library
- `OBS-003` No distributed tracing
- `OBS-004` No alerting configuration

### Testing (TST)
- `TST-001` Missing or insufficient test files
- `TST-002` No CI/CD pipeline
- `TST-003` No coverage configuration
- `TST-004` No e2e/integration tests

### Documentation (DOC)
- `DOC-001` Missing or sparse README
- `DOC-002` No CHANGELOG
- `DOC-003` No API documentation
- `DOC-004` No ADRs
- `DOC-005` No CONTRIBUTING guide

### Operations (OPS)
- `OPS-001` No container configuration
- `OPS-002` No K8s/Helm manifests
- `OPS-003` No Infrastructure as Code
- `OPS-004` Missing .dockerignore
- `OPS-005` No environment-specific configs

### Code Quality (CQ)
- `CQ-001` Oversized files (>500 lines)
- `CQ-002` Long functions (>80 lines)
- `CQ-003` TODO/FIXME/HACK markers
- `CQ-004` SQL injection risk (string concatenation)
- `CQ-005` Debug print statements left in code
- `CQ-006` Deeply nested code (4+ levels)
- `CQ-007` Duplicated code patterns

### Release (SHP)
- `SHP-001` No version declaration
- `SHP-002` No/sparse CHANGELOG
- `SHP-003` No release automation
- `SHP-004` No release/tag configuration
- `SHP-005` Manifest without lockfile
- `SHP-006` No CODEOWNERS

### Architecture (ARC)
- `ARC-001` No ADRs
- `ARC-002` No layered architecture
- `ARC-003` Circular imports
- `ARC-004` No config management / missing .env.example
- `ARC-005` Database without migrations
- `ARC-006` API without versioning
- `ARC-007` No dependency injection (large codebases)

### Accessibility (A11Y)
- `A11Y-001` Images without alt text
- `A11Y-002` Form inputs without labels
- `A11Y-003` No ARIA landmarks
- `A11Y-004` No focus styles
- `A11Y-005` No responsive design
- `A11Y-006` No a11y testing tools
- `A11Y-007` No skip-to-content link
- `A11Y-008` Missing lang attribute on HTML

### API Design (API)
- `API-001` No OpenAPI/Swagger spec
- `API-002` No rate limiting
- `API-003` No authentication/authorization
- `API-004` No standardized error responses
- `API-005` No input validation
- `API-006` No CORS configuration
- `API-007` No pagination

### Developer Experience (DX)
- `DX-001` No linting configuration
- `DX-002` No code formatter
- `DX-003` No pre-commit hooks
- `DX-004` No editor/IDE settings
- `DX-005` No task runner
- `DX-006` No CONTRIBUTING guide
- `DX-007` No dev container
- `DX-008` README lacks setup instructions

### Process (PRC)
- `PRC-001` No PR template
- `PRC-002` No issue templates
- `PRC-003` No CI pipeline / missing test step
- `PRC-004` CI missing lint step
- `PRC-005` CI missing security scanning
- `PRC-006` CI missing deploy step
- `PRC-007` No Dependabot/Renovate
- `PRC-008` No scheduled CI jobs
- `PRC-009` No CODEOWNERS

</details>

## Development

```bash
git clone https://github.com/Pcecil21/production-readiness-analyzer.git
cd production-readiness-analyzer
pip install -e ".[dev]"
pytest
```

## License

MIT
