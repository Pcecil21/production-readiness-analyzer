"""Interactive context gatherer — collects developer goals and constraints."""

from __future__ import annotations
import json
import os


# Default questions with auto-detected suggestions
QUESTIONS = [
    {
        "key": "app_description",
        "prompt": "What does this app do?",
        "hint": "(Pre-populated from detection — confirm or correct)",
        "auto_detect": True,
    },
    {
        "key": "target_user",
        "prompt": "Who is the target user?",
        "hint": "e.g., fitness enthusiasts, small business owners, developers",
        "auto_detect": False,
    },
    {
        "key": "distribution_target",
        "prompt": "How will this be distributed?",
        "hint": "",
        "options": [
            ("1", "app-store", "App Store / Play Store"),
            ("2", "web-saas", "Web SaaS (paid product)"),
            ("3", "web", "Web app (free / portfolio)"),
            ("4", "api", "API / Developer tool"),
            ("5", "internal", "Internal tool"),
        ],
        "auto_detect": False,
    },
    {
        "key": "monetization",
        "prompt": "Monetization model?",
        "hint": "",
        "options": [
            ("1", "subscription", "Subscription"),
            ("2", "one-time", "One-time purchase"),
            ("3", "freemium", "Freemium"),
            ("4", "usage-based", "Usage-based"),
            ("5", "free", "Free"),
            ("6", "not-decided", "Not decided yet"),
        ],
        "auto_detect": False,
    },
    {
        "key": "timeline",
        "prompt": "When do you want to ship?",
        "hint": "",
        "options": [
            ("1", "weeks", "In weeks"),
            ("2", "months", "In 1-3 months"),
            ("3", "ongoing", "Ongoing iteration (already live or no deadline)"),
        ],
        "auto_detect": False,
    },
    {
        "key": "biggest_worry",
        "prompt": "What's your biggest worry about going to production?",
        "hint": "e.g., security, performance, scaling, UX, cost, legal",
        "auto_detect": False,
    },
    {
        "key": "compliance_requirements",
        "prompt": "Any specific compliance requirements? (comma-separated, or 'none')",
        "hint": "e.g., HIPAA, GDPR, PCI-DSS, SOC2, none",
        "auto_detect": False,
    },
]


def _auto_describe(manifest: dict) -> str:
    """Generate a description from the manifest."""
    parts = []
    frameworks = manifest.get("frameworks", [])
    if frameworks:
        parts.append(f"{', '.join(frameworks)} application")
    else:
        lang = manifest.get("primary_language", "unknown")
        parts.append(f"{lang} project")

    dbs = manifest.get("databases", [])
    if dbs:
        parts.append(f"using {', '.join(dbs)}")

    auth = manifest.get("auth", [])
    if auth:
        parts.append(f"with {', '.join(auth)} auth")

    deploy = manifest.get("deployment", [])
    if deploy:
        parts.append(f"deployed via {', '.join(deploy)}")

    return " ".join(parts)


def gather_context_interactive(manifest: dict) -> dict:
    """Run interactive questionnaire, return context dict."""
    context = {}
    auto_desc = _auto_describe(manifest)

    print("\n" + "=" * 60)
    print("  PRODUCTION READINESS — Context Gathering")
    print("=" * 60)
    print("\nI need a few details about your goals for this app.")
    print("This takes ~2 minutes and dramatically improves the analysis.\n")

    for q in QUESTIONS:
        if q.get("auto_detect") and q["key"] == "app_description":
            print(f"  Detected: {auto_desc}")
            answer = input(f"  {q['prompt']} [Enter to confirm, or type to correct]: ").strip()
            if not answer:
                answer = auto_desc
            context[q["key"]] = answer
        elif "options" in q:
            print(f"\n  {q['prompt']}")
            for num, _val, label in q["options"]:
                print(f"    {num}. {label}")
            while True:
                choice = input("  Choice: ").strip()
                matched = [o for o in q["options"] if o[0] == choice]
                if matched:
                    context[q["key"]] = matched[0][1]
                    break
                # Also accept the value directly
                val_matched = [o for o in q["options"] if o[1] == choice]
                if val_matched:
                    context[q["key"]] = val_matched[0][1]
                    break
                print("  Invalid choice, try again.")
        else:
            hint = f" ({q['hint']})" if q.get("hint") else ""
            answer = input(f"\n  {q['prompt']}{hint}: ").strip()
            if q["key"] == "compliance_requirements":
                if answer.lower() == "none" or not answer:
                    context[q["key"]] = []
                else:
                    context[q["key"]] = [r.strip() for r in answer.split(",")]
            else:
                context[q["key"]] = answer

    return context


def gather_context_from_file(path: str) -> dict:
    """Load context from a JSON file (for repeat runs)."""
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_context(context: dict, output_dir: str) -> str:
    """Save context to JSON."""
    os.makedirs(output_dir, exist_ok=True)
    path = os.path.join(output_dir, "context.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(context, f, indent=2)
    return path
