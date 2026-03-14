# Production Readiness Analyzer — Claude Code Project Instructions

## Purpose
Analyze hobby/side-project codebases and produce an actionable, prioritized roadmap
for taking them to production. Inspired by the Karpathy autoresearch loop pattern.

## Project Structure
```
production-readiness-analyzer/
├── CLAUDE.md                    # THIS FILE
├── src/
│   ├── cli.py                   # Entry point — run against a target repo
│   ├── context_gatherer.py      # Interactive questionnaire for developer context
│   ├── ingestion.py             # Codebase manifest builder
│   ├── aggregator.py            # Merge + deduplicate + severity-calibrate findings
│   ├── roadmap.py               # Generate phased markdown roadmap
│   └── analyzers/
│       ├── base.py              # Base analyzer interface
│       ├── security.py          # Secrets, auth, input validation, CORS
│       ├── infrastructure.py    # Deploy, CI/CD, monitoring, backups
│       ├── code_quality.py      # Structure, types, errors, deps, dead code
│       ├── testing.py           # Test presence, coverage, frameworks
│       └── platform_compat.py   # App Store, web, API platform requirements
├── .production-ready/           # Output directory (created per-target)
├── requirements.txt
└── config.example.yaml
```

## How It Works
```
1. INGEST    → Build codebase manifest (framework, deps, structure)
2. CONTEXT   → Gather developer goals, timeline, distribution target
3. ANALYZE   → Run 5 specialized analyzers against the code
4. AGGREGATE → Merge findings, deduplicate, calibrate severity
5. ROADMAP   → Generate phased action plan with effort estimates
```

## Anti-Generic Checklist (Every Finding Must Pass)
- **File reference:** Points to a specific file/line, not vague advice
- **So-what:** Explains why it matters for THIS app with THESE goals
- **Effort:** Includes realistic time estimate
- **Sequencing:** Indicates dependencies between fixes
- **Skip test:** Explicitly says what can be ignored given current goals

## Output
- `.production-ready/manifest.json` — codebase manifest
- `.production-ready/context.json` — developer context
- `.production-ready/findings/` — per-analyzer JSON findings
- `.production-ready/roadmap.md` — phased action plan
- `.production-ready/score.json` — overall readiness score

## Key Principles
- Output is ANALYSIS, not prescriptive advice
- Every finding must be repo-specific with file references
- The "Parking Lot" (things to ignore) is as important as the roadmap
- Prefer actionable over comprehensive
