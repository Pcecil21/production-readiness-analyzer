# Roadmap Template

Use this template when generating `roadmap.md` in Step 4. Replace all `{placeholders}` with actual values from findings.json and context.json.

---

## Template Start

```markdown
# Production Readiness Roadmap: {app_name}

**Generated:** {date}
**Distribution target:** {distribution_target}
**Monetization model:** {monetization_model}
**Developer availability:** {timeline_and_hours}

---

## Executive Summary

**Overall assessment:** {one sentence — e.g., "Solid prototype with significant security and infrastructure gaps before it's ready for paying customers."}

| Metric | Value |
|---|---|
| Total effort (DIY) | {hours_low}–{hours_high} hours |
| Calendar estimate | {weeks_low}–{weeks_high} weeks at {hours_per_week} hrs/week |
| Estimated cost if hiring out | ${cost_low}–${cost_high} |
| Critical findings | {count} |
| High findings | {count} |
| Medium findings | {count} |
| Low/Info findings | {count} |
| Items deferred (parking lot) | {count} |

**The single most important thing to do first:** {one sentence — the highest-severity, lowest-effort item, or the key decision that unblocks everything else}

---

## Key Decisions

Before starting work, you need to resolve these forks. Each one affects downstream effort estimates.

### Decision 1: {title}
{description of the fork — e.g., "Rebuild in React Native vs. wrap in Capacitor"}

- **Option A:** {option} → adds ~{hours}hrs, enables {benefit}
- **Option B:** {option} → adds ~{hours}hrs, enables {benefit}
- **Recommendation:** {if one is clearly better given context, say so; if genuinely 50/50, say that}

{Repeat for each key decision. Typically 1–3 decisions.}

---

## Phase 0: Stop the Bleeding
*Issues that are actively dangerous. Do these before any other work.*
*Estimated effort: {hours_low}–{hours_high} hours | Cost if hired: ${cost_low}–${cost_high}*

{If no Phase 0 items: "No critical safety issues found. Proceed to Phase 1."}

### {finding_id}: {title}
**File:** `{file_path}` (line {line})
**Severity:** Critical | **Effort:** {hours_low}–{hours_high} hrs
**What's wrong:** {description — reference the actual code}
**Why it matters for you:** {why_it_matters — tied to their goals}
**What to do:** {recommendation — specific to their codebase}

{Repeat for each finding in this phase}

---

## Phase 1: Foundation
*Required for any version that has real users. The minimum bar for charging money or submitting to an app store.*
*Estimated effort: {hours_low}–{hours_high} hours | Cost if hired: ${cost_low}–${cost_high}*

{Findings sorted by severity DESC, then effort ASC}

### {finding_id}: {title}
**File:** `{file_path}` (line {line})
**Severity:** {severity} | **Effort:** {hours_low}–{hours_high} hrs
{If depends_on is not empty: **Blocked by:** {dependency_ids}}
**What's wrong:** {description}
**Why it matters for you:** {why_it_matters}
**What to do:** {recommendation}

---

## Phase 2: Production Infrastructure
*What you need to operate the app in production — deploy, monitor, recover.*
*Estimated effort: {hours_low}–{hours_high} hours | Cost if hired: ${cost_low}–${cost_high}*

{Same format as Phase 1}

---

## Phase 3: Quality & Polish
*What determines whether users stay. Not required for launch, but required for retention.*
*Estimated effort: {hours_low}–{hours_high} hours | Cost if hired: ${cost_low}–${cost_high}*

{Same format as Phase 1}

---

## Phase 4: Growth Readiness
*Infrastructure for scaling. Don't build this until the product works and people want it.*
*Estimated effort: {hours_low}–{hours_high} hours | Cost if hired: ${cost_low}–${cost_high}*

{Same format as Phase 1}

---

## Parking Lot
*Real issues that don't need attention given your current goals and timeline. Revisit when circumstances change.*

| ID | Title | Why Deferred |
|---|---|---|
| {id} | {title} | {one sentence — e.g., "Scalability optimization — not relevant until 1000+ users"} |

---

## Cost Breakdown by Category

| Category | DIY Hours | Hire-Out Cost | Notes |
|---|---|---|---|
| Security fixes | {hrs} | ${cost} | {note} |
| Infrastructure setup | {hrs} | ${cost} | {note} |
| Code quality / refactoring | {hrs} | ${cost} | {note} |
| Testing | {hrs} | ${cost} | {note} |
| Platform compliance | {hrs} | ${cost} | {note} |
| UI/UX polish | {hrs} | ${cost} | {note} |
| Ongoing monthly cost | — | ${monthly} | {breakdown: hosting, monitoring, etc.} |
| **Total** | **{total_hrs}** | **${total_cost}** | |

---

## Ongoing Costs Once Live

| Item | Estimated Monthly | Notes |
|---|---|---|
| {item} | ${cost} | {note} |
| **Total ongoing** | **${total_monthly}** | |

---

## Timeline Visualization

{Render a simple text-based timeline:}

Week 1–2:   ████ Phase 0 (Stop the Bleeding)
Week 3–6:   ████████████ Phase 1 (Foundation)
Week 7–9:   ████████ Phase 2 (Infrastructure)
Week 10–14: ████████████████ Phase 3 (Quality)
Week 15+:   ░░░░░░░░ Phase 4 (Growth — as needed)

{Adjust week ranges based on actual estimates and developer availability}

---

*This roadmap was generated by analyzing the codebase at {repo_path}. Estimates assume {stated_availability}. Actual effort may vary — treat ranges as planning guidance, not commitments. Security and compliance recommendations are based on code analysis, not legal review — consult a professional for HIPAA, PCI, GDPR, or other regulatory requirements.*
```

## Template Rules

1. **Never output the template with unfilled placeholders.** Every `{placeholder}` must be replaced with actual data from findings.json and context.json. If data is missing, write "Unknown — requires further analysis" rather than leaving a placeholder.

2. **Phase sections with zero findings should still appear** with a note: "No issues found in this category." This signals thoroughness.

3. **The Executive Summary is the most important section.** Many developers will read only this. Make the total effort range, calendar estimate, and "most important thing to do first" crystal clear.

4. **Ongoing costs section is required even if estimated at $0.** A hobby app with no backend has ~$99/year (Apple dev program) and that should be stated.

5. **The timeline visualization should be realistic, not aspirational.** Use the developer's stated availability, not full-time assumptions.
