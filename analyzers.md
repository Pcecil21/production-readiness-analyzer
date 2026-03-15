# Analyzer Reference

Detailed instructions for each analyzer. Read the relevant section when executing that analyzer in Step 3.

---

## Security Analyzer

### What to check

**Hardcoded secrets** (Critical)
- Review the grep results from Step 1e
- Read any files flagged — determine if the match is a real secret, a placeholder, or a false positive
- Check if `.env.example` exists with placeholder values (good practice) vs. `.env` committed with real values (critical issue)
- Check `.gitignore` for env file exclusions
- For client-side code (React, Next.js `pages/`, `app/`, `components/`): any `process.env` reference that isn't `NEXT_PUBLIC_*` won't work client-side — but `NEXT_PUBLIC_*` values ARE exposed to browsers, so check what's behind those prefixes

**Authentication** (Critical if multi-user, High if single-user going multi)
- Identify the auth provider from Step 1g results
- If Supabase: check for Row Level Security (RLS) policies — read any migration files or SQL files for `CREATE POLICY` / `ALTER TABLE ... ENABLE ROW LEVEL SECURITY`
- If no auth detected: flag as critical if distribution target involves multiple users
- Check API routes for auth middleware / session verification — are there unprotected routes that should be protected?
- Check for auth on both read AND write operations (common to protect writes but not reads)
- Look for admin/privileged routes and verify they have elevated auth checks

**Input validation** (High)
- Read API route files identified in Step 1f
- Check for request body validation (zod, joi, yup, class-validator, or manual checks)
- Check for SQL/NoSQL injection patterns: string interpolation in queries vs. parameterized queries
- Check for file upload handling without size/type validation

**CORS configuration** (Medium)
- Search for CORS configuration: `cors`, `Access-Control`, `allowedOrigins`
- Wildcard `*` origin in production config is a finding
- Missing CORS config when API is consumed cross-origin is a finding

**Data sensitivity** (severity depends on data type)
- Identify what data types the app handles (from context + code analysis)
- Health data → flag HIPAA consideration
- Payment/financial data → flag PCI consideration
- EU user data → flag GDPR consideration
- User PII (names, emails, addresses) → flag basic privacy requirements
- Check if sensitive data is logged, cached, or stored in plaintext

**Rate limiting** (Medium for SaaS, Low for internal)
- Check for rate limiting middleware on API routes
- If absent and app will be public-facing, flag with effort estimate

### Files to read
- All files in API route directories
- Auth configuration files
- Database schema / migration files
- Middleware files
- Environment configuration

---

## Infrastructure Analyzer

### What to check

**Deployment** (High)
- Identify current deployment from manifest (Vercel, Railway, Fly, AWS, self-hosted, none)
- If none: flag as high — "no deployment pipeline means manual deploys, which means human error"
- If detected: assess whether it's production-appropriate (Vercel free tier has limits; self-hosted needs monitoring)
- Check for preview/staging environments vs. deploy-straight-to-prod

**CI/CD** (Medium)
- Check `.github/workflows/`, `.gitlab-ci.yml`, `Jenkinsfile`, etc.
- If absent: flag with note on what a minimal CI pipeline looks like for their stack
- If present: check what it does — lint only? build? test? deploy? Each missing step is a sub-finding

**Environment management** (High)
- How many environments exist? (dev/staging/prod or just "it runs on my machine and also Vercel")
- Are there environment-specific configs?
- Check for production database pointing to same instance as development (very common in hobby projects — very dangerous)

**Database** (High if present)
- Migration framework present? (Prisma, Drizzle, Alembic, diesel, knex, etc.)
- If no migrations: flag — "schema changes are manual and unreproducible"
- Backup strategy? (Usually: none. Flag it.)
- Connection pooling configured? (Matters at scale, not for v1 — phase as `growth`)

**Monitoring and alerting** (Medium)
- Crash reporting SDK? (Sentry, Bugsnag, Crashlytics)
- Uptime monitoring? (Usually: none)
- Application logging beyond console.log? (structured logging, log aggregation)
- Error tracking on API routes?
- If none of the above: single finding — "you will not know when things break in production"

**Backup and recovery** (Medium–High depending on data value)
- Database backups configured?
- Can you recover from a bad deploy? (rollback capability)
- Is user data recoverable if the database corrupts?

### Files to read
- CI/CD config files
- Deployment config files (vercel.json, Dockerfile, etc.)
- Database config and migration directories
- Logging/monitoring configuration
- Package.json scripts section

---

## Code Quality Analyzer

### What to check

**Architecture and separation of concerns** (Medium)
- Is there a clear separation between: UI components / business logic / data access / API layer?
- Or is everything in one directory / component files contain fetch calls, business logic, and UI?
- Check the largest 5 files by line count — are any over 500 lines? Over 1000?
- Identify "god files" that do too many things

**TypeScript strictness** (Medium for TS projects)
- Read `tsconfig.json` — check `strict`, `noImplicitAny`, `strictNullChecks`
- Count `any` usage: `grep -rn ': any\|as any\|<any>' --include='*.ts' --include='*.tsx' . | grep -v node_modules | wc -l`
- If strict mode is off: flag with effort to enable (usually medium — lots of type errors to fix)

**Error handling** (High)
- Search for empty catch blocks: `catch\s*(\w*)\s*\{\s*\}` or `catch { }`
- Search for error swallowing: catch blocks that log but don't rethrow or handle
- Check API routes: do they return proper error responses (status codes, messages) or crash?
- Check for unhandled promise rejections
- Check React components for Error Boundaries

**Dependency health** (Medium)
- Reference npm audit / pip audit results from Step 1c
- Count total dependencies — over 100 for a small app is a smell
- Identify dependencies that are unmaintained (check for clearly abandoned packages)
- Check for duplicate packages serving same purpose (e.g., both axios and fetch, both moment and date-fns)

**Dead code** (Low)
- Unused exports, commented-out blocks, files not imported anywhere
- TODO/FIXME/HACK inventory from Step 1d — categorize by severity (some TODOs are reminders; some are "this will break")

**Code duplication** (Low–Medium)
- Look for copy-pasted patterns, especially in API routes or components
- Common in hobby projects: same fetch/error/loading pattern duplicated across 10 components

### Files to read
- tsconfig.json
- Largest files by line count (top 5–10)
- All API route files
- Main application entry points
- Shared utility/helper directories

---

## Testing Analyzer

### What to check

**Test existence** (Medium–High)
- Reference test file count from Step 1d
- Zero tests is a finding, but severity depends on context:
  - Shipping to app store in 2 weeks with zero tests → High ("manual test on 3+ devices before submitting")
  - Building SaaS over 3 months → Medium ("add tests to critical paths as you build")

**Test framework** (Info if absent, Low if misconfigured)
- Is a test framework configured? (Jest, Vitest, pytest, etc.)
- Is it in devDependencies but with no test files? (Started, never followed through)
- Check package.json `test` script — does it run anything?

**What's covered** (Medium)
- Categorize existing tests: unit / integration / e2e
- Which layers are tested? (Usually: nothing, or only utility functions)
- Are API routes tested? (Usually: no)
- Are critical user flows tested? (Usually: no)

**Recommended testing strategy** (include in findings)
- Don't recommend "add comprehensive test coverage" generically
- Recommend specific tests based on the app's critical paths:
  - For SaaS: auth flow, payment flow, core value-delivery flow
  - For App Store: permission flows, offline behavior, data sync
  - For API: endpoint contracts, error responses, auth enforcement

### Files to read
- Test configuration files (jest.config, vitest.config, pytest.ini)
- Any existing test files (to assess quality and patterns)
- Package.json test scripts

---

## Platform Compliance Analyzer

**Only run this analyzer if distribution target is App Store (iOS or Android).** Skip entirely for web SaaS, API, internal tool, or CLI targets.

### What to check

**App Store hard requirements** (Critical)
- Privacy policy: does one exist? Is it hosted at a public URL? Check for `privacy` references in code/config.
- If React Native / Expo: check `app.json` / `app.config.js` for required fields (bundleIdentifier, version, permissions, entitlements)
- If web app targeting app store: **flag as critical decision point** — "This is a web app. Apple rejects apps that are essentially websites in a wrapper. You need either a native rebuild or substantial native functionality to pass review."

**Permission declarations** (Critical for app store)
- Identify all sensitive APIs used (HealthKit, Location, Camera, Contacts, Notifications, etc.)
- Check for usage description strings (NSCameraUsageDescription, etc.)
- Check for entitlement declarations
- For Expo: verify plugins are configured for each permission in app.json

**Permission denial handling** (High)
- Search for permission request code — is there handling for denial?
- Common gap: app requests permission, assumes grant, crashes or shows blank state on denial
- Each permission-dependent feature needs a denial path

**Offline behavior** (Medium for app store)
- What happens when network is unavailable?
- Check for network status detection (NetInfo, navigator.onLine)
- Check for offline data caching
- App store reviewers sometimes test in airplane mode

**Accessibility basics** (Medium)
- Check for accessibility labels on interactive elements
- Check for Dynamic Type / font scaling support
- For React Native: search for `accessible`, `accessibilityLabel`, `accessibilityRole` props

**Monetization infrastructure** (High if monetization is planned)
- If subscription planned: check for StoreKit / RevenueCat / in-app purchase integration
- If not present: estimate effort to add (typically 20–40 hours including paywall UI, restore, receipt validation)
- Check for any existing payment/billing code

### Files to read
- app.json / app.config.js (Expo/RN)
- Info.plist or equivalent
- Permission request code
- Any in-app purchase configuration
- Network/connectivity handling code

---

## Cross-Analyzer Calibration

After running all analyzers, review the full findings list for:

1. **Duplicates** — two analyzers flagging the same file/issue. Keep the more specific one.
2. **Conflicts** — one analyzer recommends X, another recommends Y. Resolve based on context.json priorities.
3. **Missing "so what"** — any finding where `why_it_matters` is generic. Rewrite it to reference the developer's stated goals.
4. **Empty parking lot** — if nothing is deferred, you're not prioritizing. Move the lowest-severity items to parking lot with a "defer because" note.
5. **Effort sanity check** — do the total hours make sense for the scope? A 500-LOC app shouldn't total 400 hours of fixes. A 20,000-LOC app with zero tests and no auth might.
