---
name: production-readiness-analyzer
description: >
  Analyzes any codebase and generates a prioritized roadmap with time and cost estimates for taking it from hobby/personal-use to production (paying customers or app store). Use when I say 'analyze this repo', 'production readiness', 'what would it take to ship this', 'time and cost estimate', 'ready for production', 'how far from shippable', 'audit this codebase', 'ship this app', or when I point at a repo and want to understand the gap between where it is and where it needs to be. Also triggers on 'app store ready', 'production gaps', 'technical debt audit', 'what's missing', or 'prioritize my work'. Always use this skill when evaluating whether a hobby project can become a product — even if the user doesn't use these exact words.
---

# Production Readiness Analyzer

## Goal
Analyze a codebase and produce a **prioritized, repo-specific roadmap** with **concrete time and cost estimates** for taking it to production. Production means either: paying customers (SaaS/API) or app store distribution (iOS/Android).

Every finding must point to specific files, explain why it matters for THIS project's goals, and include an effort estimate. Generic advice ("add tests", "improve error handling") without file references and context is a failure mode — avoid it.

## Inputs
- A codebase (the current working directory, or a path provided by the user)
- Developer context (gathered interactively in Step 2)

## Output
All output is written to `.production-ready/` in the project root:
- `manifest.json` — codebase inventory and detection results
- `context.json` — developer goals, constraints, distribution target
- `findings.json` — all analyzer findings with severity, effort, file refs
- `roadmap.md` — the final deliverable: phased plan with time/cost estimates

## Workflow

Execute these steps in order. Do not skip steps. Write intermediate outputs to `.production-ready/` as you go — if the session is interrupted, partial results are preserved.

---

### Step 1: Codebase Ingestion

Run these commands and reads to build the manifest. Adapt commands to what's actually present (not every project has package.json).

**1a. Directory structure**
```bash
find . -type f -not -path '*/node_modules/*' -not -path '*/.git/*' -not -path '*/.next/*' -not -path '*/dist/*' -not -path '*/__pycache__/*' -not -path '*/venv/*' -not -path '*/.production-ready/*' | head -500
```
```bash
find . -type f -not -path '*/node_modules/*' -not -path '*/.git/*' -not -path '*/.next/*' -not -path '*/dist/*' | wc -l
```

**1b. Framework and language detection**
Check for these files and parse what's found:
- `package.json` → framework, dependencies, scripts
- `requirements.txt` / `pyproject.toml` / `Pipfile` → Python stack
- `Cargo.toml` → Rust
- `go.mod` → Go
- `tsconfig.json` → TypeScript config and strictness
- `next.config.*` / `nuxt.config.*` / `vite.config.*` → meta-framework
- `app.json` / `app.config.js` → Expo/React Native
- `Dockerfile` / `docker-compose.yml` → containerization
- `.github/workflows/` → CI/CD
- `vercel.json` / `netlify.toml` / `fly.toml` → deployment target
- `.env*` files → environment variable patterns (DO NOT log values)

**1c. Dependency health**
```bash
# JS/TS projects
npm audit --json 2>/dev/null || true
npm outdated --json 2>/dev/null || true

# Python projects
pip audit --format json 2>/dev/null || true
```

**1d. Code metrics**
```bash
# Total lines by file type
find . -type f \( -name '*.ts' -o -name '*.tsx' -o -name '*.js' -o -name '*.jsx' -o -name '*.py' -o -name '*.rs' -o -name '*.go' \) -not -path '*/node_modules/*' -not -path '*/.git/*' | xargs wc -l 2>/dev/null | tail -1

# Test file count
find . -type f \( -name '*.test.*' -o -name '*.spec.*' -o -name '*_test.*' -o -path '*/tests/*' -o -path '*/__tests__/*' \) -not -path '*/node_modules/*' | wc -l

# TODO/FIXME/HACK inventory
grep -rn 'TODO\|FIXME\|HACK\|XXX' --include='*.ts' --include='*.tsx' --include='*.js' --include='*.jsx' --include='*.py' --include='*.rs' --include='*.go' . 2>/dev/null | grep -v node_modules | head -30
```

**1e. Security surface scan**
```bash
# Hardcoded secrets (patterns only — flag for human review)
grep -rn 'sk_live\|sk_test\|AKIA\|password\s*=\s*["\x27]\|api_key\s*=\s*["\x27]\|secret\s*=\s*["\x27]' --include='*.ts' --include='*.tsx' --include='*.js' --include='*.jsx' --include='*.py' --include='*.env' . 2>/dev/null | grep -v node_modules | head -20

# .gitignore check for env files
cat .gitignore 2>/dev/null | grep -i 'env'
```

**1f. API route inventory** (for web frameworks)
```bash
# Next.js API routes
find . -path '*/api/*' -name '*.ts' -o -path '*/api/*' -name '*.js' | grep -v node_modules | head -30

# Express/Fastify route patterns
grep -rn 'app\.\(get\|post\|put\|delete\|patch\)\|router\.\(get\|post\|put\|delete\|patch\)' --include='*.ts' --include='*.js' . 2>/dev/null | grep -v node_modules | head -30
```

**1g. Auth detection**
```bash
grep -rn 'supabase\|firebase\|auth0\|clerk\|nextauth\|passport\|jwt\|bcrypt\|session' --include='*.ts' --include='*.tsx' --include='*.js' --include='*.jsx' . 2>/dev/null | grep -v node_modules | head -20
```

Write `manifest.json` to `.production-ready/`. Include:
- `framework`, `language`, `package_manager`
- `total_files`, `total_loc`, `test_files`
- `dependencies` (count, outdated count, vulnerable count)
- `api_routes` (count and list)
- `auth_provider` (detected or "none")
- `database` (detected or "none")
- `deployment_target` (detected or "none")
- `ci_cd` (detected or "none")
- `docker` (detected or "none")
- `env_vars_referenced` (count)
- `secrets_flagged` (count — patterns only, no values)
- `todos_fixmes` (count)

Present the manifest summary to the user and ask them to confirm or correct any misdetections before proceeding.

---

### Step 2: Context Gathering

Ask the user these questions interactively. Pre-populate answers from manifest detections where possible (e.g., "I detected this is a Next.js app on Vercel — correct?").

**Required context (must ask all):**

1. **What does this app do?** (One sentence — pre-populate from README if found)
2. **Distribution target:** App Store (iOS) / App Store (Android) / Web SaaS / API product / Internal tool / CLI tool / Other
3. **Current state:** Personal use only / Shared with friends / Alpha/beta users / Already has some users
4. **Target monetization:** Subscription / One-time purchase / Freemium / Usage-based / Free (growth play) / Not decided
5. **Target audience:** Who specifically would pay? (If they say "everyone" — push back)
6. **Timeline pressure:** Ship in weeks / Ship in 1–3 months / Ship in 3–6 months / No deadline, doing it right
7. **Biggest worry:** What keeps you up at night about taking this to production? (Open-ended)

**Conditional context (ask only if relevant):**

- If distribution target is App Store: "Does this need HealthKit, camera, location, or other device APIs? Which ones?"
- If distribution target is App Store AND current stack is web: "This is a web app — are you planning to rebuild in React Native/Swift, or wrap it? This is a critical fork in the road."
- If database detected: "Is your data model stable, or are you still changing the schema regularly?"
- If no auth detected: "Is there any authentication at all right now, or is it fully open?"
- If health/financial data involved: "Are you aware of HIPAA/PCI/SOC2 requirements for your data type? Do you know if they apply?"

Write `context.json` to `.production-ready/`.

---

### Step 3: Run Analyzers

Read `references/analyzers.md` for detailed instructions per analyzer. Run all five, adapting depth to the codebase size. Each analyzer reads specific files and runs targeted commands — do not try to feed the entire codebase to each one.

**Analyzers to run (in order):**

1. **Security Analyzer** — secrets, auth, input validation, CORS, data handling
2. **Infrastructure Analyzer** — deployment, CI/CD, environments, monitoring, backups
3. **Code Quality Analyzer** — architecture, type safety, error handling, dead code, deps
4. **Testing Analyzer** — coverage, framework, which layers are tested
5. **Platform Compliance Analyzer** — app store requirements, privacy policy, permissions, accessibility (skip if distribution target is not app store)

Each analyzer outputs findings in this structure (append all to a single findings array):

```json
{
  "id": "SEC-001",
  "analyzer": "security",
  "severity": "critical | high | medium | low | info",
  "title": "Short title",
  "file": "path/to/file.ts",
  "line": 23,
  "description": "What's wrong — reference the actual code.",
  "why_it_matters": "Why this matters given the context.json goals. Be specific.",
  "recommendation": "Exactly what to do, referencing their actual files/patterns.",
  "effort_hours_low": 1,
  "effort_hours_high": 4,
  "effort_cost_low_usd": 0,
  "effort_cost_high_usd": 400,
  "depends_on": [],
  "phase": "stop_the_bleeding | foundation | infrastructure | quality | growth | parking_lot"
}
```

**Severity calibration rules** (reference context.json):
- `critical` = will cause rejection, data loss, security breach, or legal liability
- `high` = users will hit this in the first session; blocks charging money
- `medium` = matters for retention and quality; should fix before scale
- `low` = best practice; fix when you have time
- `info` = awareness item; may not need action

**Phase assignment rules:**
- `stop_the_bleeding` = exposed secrets, broken auth, data loss risk — fix before anything else
- `foundation` = auth, core error handling, permission flows — required for any production use
- `infrastructure` = CI/CD, monitoring, deployment pipeline — required to operate in production
- `quality` = tests, performance, accessibility, code cleanup — determines if users stay
- `growth` = analytics, feature flags, scalability — needed when product works and you're growing
- `parking_lot` = real issues that don't matter for this developer's stated goals/timeline

**Cost estimation rules:**
- `effort_cost_*_usd`: $0 if DIY is the obvious path; estimate contractor cost if the work is commonly hired out (design: $80–150/hr, backend specialist: $100–200/hr, security audit: $150–300/hr, QA: $40–80/hr)
- Always include both low and high bounds — never a single number
- For "rebuild" items (e.g., web-to-native port), estimate the full scope, not just the gap

Write `findings.json` to `.production-ready/`.

---

### Step 4: Generate Roadmap

Read `references/roadmap-template.md` for the output format. Generate `roadmap.md` using findings.json and context.json.

**Roadmap generation rules:**

1. **Group findings by phase** (stop_the_bleeding → foundation → infrastructure → quality → growth → parking_lot)
2. **Within each phase, sort by: severity DESC, then effort ASC** (highest impact, lowest effort first)
3. **Respect dependencies** — if SEC-003 depends on SEC-001, SEC-001 must appear first regardless of effort
4. **Calculate phase totals:**
   - Sum effort_hours_low and effort_hours_high for each phase
   - Convert to calendar time using the developer's stated availability (from context)
   - Sum effort_cost ranges for each phase
5. **Calculate grand totals** at the bottom
6. **Include the Parking Lot explicitly** — items that are real but not worth addressing now, with a one-line explanation of why each is deferred
7. **Add a "Key Decisions" section** — forks where the developer needs to make a choice that affects downstream work (e.g., "rebuild in React Native vs. wrap in Capacitor" or "Supabase RLS vs. custom auth middleware")

**Anti-generic checks before writing roadmap.md:**
- Every item references a specific file? If not, make it specific or cut it.
- Every "why it matters" connects to their stated goals? If not, rewrite it.
- Any item that could appear in any repo without modification? Rewrite to be repo-specific or move to parking lot.
- Does the parking lot exist and contain items? If the parking lot is empty, you're not being honest about prioritization.

Present `roadmap.md` to the user. Summarize the key numbers: total effort range, total cost range, estimated calendar time, and the single most important decision they need to make first.

---

## Critical Rules

- **Never log, display, or write secret values.** Flag the pattern and file location only.
- **Never guess about compliance requirements** (HIPAA, PCI, GDPR, SOC2). Flag when they might apply and recommend professional review.
- **Effort estimates are ranges, never single numbers.** Always low–high.
- **If you can't determine something from the code, say so.** Don't fabricate findings.
- **Confirm the manifest with the user before running analyzers.** Misdetection cascades into wrong recommendations.
- **The parking lot is mandatory.** Every analysis must defer at least some items. If you're not deferring anything, you're not prioritizing.
