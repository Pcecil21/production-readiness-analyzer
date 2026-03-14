"""Platform compatibility analyzer — App Store, web SaaS, API-specific requirements."""

from __future__ import annotations
import os
import re
from .base import BaseAnalyzer


class PlatformCompatAnalyzer(BaseAnalyzer):
    name = "platform_compat"
    description = "Platform-specific requirements: App Store, web SaaS, API, internal tool"

    def run(self) -> list:
        distribution = self.context.get("distribution_target", "web")

        # Always check these
        self._check_readme()
        self._check_license()

        if distribution == "app-store":
            self._check_app_store_requirements()
        elif distribution in ("web-saas", "web"):
            self._check_web_saas_requirements()
        elif distribution == "api":
            self._check_api_requirements()

        # Check monetization readiness if applicable
        monetization = self.context.get("monetization", "not-decided")
        if monetization not in ("free", "not-decided"):
            self._check_monetization_readiness()

        self._check_legal_compliance()
        return self.findings

    def _check_readme(self):
        has_readme = self.manifest.get("has_readme", False)
        if not has_readme:
            self._add(
                id=self._next_id("PLAT"),
                severity="medium",
                category="documentation",
                title="No README file found",
                description="Project has no README.md.",
                why_it_matters="A README is the entry point for anyone (including future you) trying to understand, set up, or contribute to the project.",
                recommendation="Add a README with: what the app does, how to set it up locally, how to deploy, and key architecture decisions.",
                effort_hours=2,
            )

    def _check_license(self):
        license_files = self._find_files("LICENSE", "LICENSE.*", "LICENCE", "LICENCE.*")
        distribution = self.context.get("distribution_target", "web")

        if not license_files and distribution not in ("internal",):
            self._add(
                id=self._next_id("PLAT"),
                severity="low",
                category="legal",
                title="No LICENSE file found",
                description="No license file detected. If this is a public/commercial project, you need one.",
                why_it_matters="Without a license, the code is technically all-rights-reserved. For open source: others can't legally use it. For commercial: you should have terms.",
                recommendation="For commercial products: consult a lawyer. For open source: choose MIT, Apache 2.0, or GPL depending on your goals.",
                effort_hours=1,
            )

    def _check_app_store_requirements(self):
        frameworks = self.manifest.get("frameworks", [])

        # Check for privacy policy
        code_files = self._find_files("*.ts", "*.tsx", "*.js", "*.jsx", "*.swift")
        has_privacy_link = False
        for fp in code_files[:30]:
            content = self._read_file(fp)
            if content and re.search(r'privacy[_\-\s]?policy', content, re.IGNORECASE):
                has_privacy_link = True
                break

        if not has_privacy_link:
            self._add(
                id=self._next_id("PLAT"),
                severity="critical",
                category="app_store",
                title="No privacy policy reference found",
                description="App Store requires a privacy policy URL. No reference to a privacy policy found in the code.",
                why_it_matters="Apple and Google will reject your app without a privacy policy. This is a hard requirement, not optional.",
                recommendation="Create a privacy policy (use a generator like Termly or iubenda) and link it in your app settings screen and store listing.",
                effort_hours=3,
            )

        # Check for app permissions
        if any(f in frameworks for f in ["react-native", "expo"]):
            app_json = self._read_file("app.json") or self._read_file("app.config.js")
            if app_json:
                missing_configs = []
                if "icon" not in (app_json or ""):
                    missing_configs.append("app icon")
                if "splash" not in (app_json or ""):
                    missing_configs.append("splash screen")
                if "version" not in (app_json or ""):
                    missing_configs.append("version number")

                if missing_configs:
                    self._add(
                        id=self._next_id("PLAT"),
                        severity="high",
                        category="app_store",
                        title=f"Missing app config: {', '.join(missing_configs)}",
                        file="app.json",
                        description=f"app.json is missing required fields for store submission: {', '.join(missing_configs)}.",
                        why_it_matters="These are required fields for App Store / Play Store submission. Your build will either fail or be rejected without them.",
                        recommendation="Add missing fields to app.json. See Expo docs for complete app store requirements.",
                        effort_hours=2,
                    )

        # Check for offline handling
        code_content = ""
        for fp in code_files[:20]:
            content = self._read_file(fp)
            if content:
                code_content += content

        if not re.search(r'(?:NetInfo|@react-native-community/netinfo|navigator\.onLine|offline)', code_content, re.IGNORECASE):
            self._add(
                id=self._next_id("PLAT"),
                severity="medium",
                category="app_store",
                title="No offline/network handling detected",
                description="No network state detection or offline handling found.",
                why_it_matters="Apple requires apps to handle network loss gracefully. Showing a crash or blank screen when offline can lead to rejection.",
                recommendation="Add network state detection and show appropriate offline messaging. Cache critical data for offline access.",
                effort_hours=4,
            )

    def _check_web_saas_requirements(self):
        code_files = self._find_files("*.ts", "*.tsx", "*.js", "*.jsx")

        # SEO basics for web apps
        frameworks = self.manifest.get("frameworks", [])
        if "next.js" in frameworks:
            # Check for metadata/head management
            has_metadata = False
            for fp in code_files[:30]:
                content = self._read_file(fp)
                if content and re.search(r'(?:metadata|Head|NextSeo|<title)', content):
                    has_metadata = True
                    break

            if not has_metadata:
                self._add(
                    id=self._next_id("PLAT"),
                    severity="medium",
                    category="web_seo",
                    title="No page metadata/SEO configuration detected",
                    description="No metadata export, Head component, or SEO library found.",
                    why_it_matters="Without proper meta tags, search engines can't index your pages and social sharing shows generic previews.",
                    recommendation="Add metadata export in layout.tsx (Next.js App Router) or use next-seo for Pages Router.",
                    effort_hours=2,
                )

        # Check for loading states
        has_loading = False
        has_error_ui = False
        for fp in code_files[:30]:
            content = self._read_file(fp)
            if not content:
                continue
            if re.search(r'(?:loading|isLoading|skeleton|spinner|Loader)', content):
                has_loading = True
            if re.search(r'(?:error\.tsx|ErrorBoundary|error\s*&&|isError)', content):
                has_error_ui = True

        if not has_loading:
            self._add(
                id=self._next_id("PLAT"),
                severity="medium",
                category="web_ux",
                title="No loading states detected",
                description="No loading indicators, skeletons, or spinner components found.",
                why_it_matters="Users perceive apps without loading states as broken or slow. Showing a blank screen during data fetches is a poor experience.",
                recommendation="Add loading states for async operations. Use Suspense (React), skeleton screens, or simple spinners.",
                effort_hours=3,
            )

    def _check_api_requirements(self):
        api_files = self._find_files("*/api/*", "*/routes/*", "*/endpoints/*")

        # Check for API documentation
        doc_files = self._find_files("*openapi*", "*swagger*", "api-docs*", "*.openapi.*")
        deps = self.manifest.get("dependencies", {})
        all_deps = deps.get("node", []) + deps.get("python", [])
        doc_libs = {"swagger-ui-express", "swagger-jsdoc", "fastify-swagger",
                    "drf-spectacular", "flasgger", "redoc"}
        has_api_docs = bool(doc_files) or any(lib in d for d in all_deps for lib in doc_libs)

        if api_files and not has_api_docs:
            self._add(
                id=self._next_id("PLAT"),
                severity="high",
                category="api_docs",
                title="No API documentation detected",
                description="API routes exist but no OpenAPI/Swagger documentation found.",
                why_it_matters="Without API docs, consumers (including your frontend team or third-party integrators) can't reliably use your API.",
                recommendation="Add OpenAPI/Swagger documentation. Use swagger-jsdoc (Express) or FastAPI's built-in docs (Python).",
                effort_hours=6,
            )

        # Check for rate limiting
        rate_limit_libs = {"express-rate-limit", "rate-limiter-flexible", "bottleneck",
                           "slowapi", "django-ratelimit", "flask-limiter"}
        has_rate_limit = any(lib in d for d in all_deps for lib in rate_limit_libs)

        code_content = ""
        for fp in api_files[:10]:
            content = self._read_file(fp)
            if content:
                code_content += content

        if not has_rate_limit and "rateLimit" not in code_content and "rate_limit" not in code_content:
            self._add(
                id=self._next_id("PLAT"),
                severity="high",
                category="api_security",
                title="No rate limiting detected on API",
                description="No rate limiting library or middleware found.",
                why_it_matters="Without rate limiting, a single client can overwhelm your API, exhaust your database, or run up your cloud bill.",
                recommendation="Add rate limiting middleware. express-rate-limit (Node) or slowapi (Python) are easy to set up.",
                effort_hours=2,
            )

        # Check for API versioning
        has_versioning = False
        for fp in api_files:
            if re.search(r'v[12]/|/api/v', fp):
                has_versioning = True
                break

        if api_files and not has_versioning:
            self._add(
                id=self._next_id("PLAT"),
                severity="low",
                category="api_design",
                title="No API versioning detected",
                description="API routes don't include version prefixes (e.g., /api/v1/).",
                why_it_matters="Without versioning, breaking changes affect all clients immediately. Versioning gives you room to evolve the API.",
                recommendation="Add version prefix to API routes (e.g., /api/v1/). Not urgent for v1, but plan for it.",
                effort_hours=2,
            )

    def _check_monetization_readiness(self):
        monetization = self.context.get("monetization", "")
        deps = self.manifest.get("dependencies", {})
        all_deps = deps.get("node", []) + deps.get("python", [])

        payment_libs = {"stripe", "@stripe/stripe-js", "@stripe/react-stripe-js",
                        "react-native-iap", "expo-in-app-purchases",
                        "paypal", "@paypal/react-paypal-js",
                        "lemonsqueezy", "@lemonsqueezy/wedges"}

        has_payment = any(lib in d for d in all_deps for lib in payment_libs)

        if monetization in ("subscription", "one-time", "freemium", "usage-based") and not has_payment:
            self._add(
                id=self._next_id("PLAT"),
                severity="high",
                category="monetization",
                title="No payment integration detected",
                description=f"Monetization model is '{monetization}' but no payment library (Stripe, PayPal, IAP) found.",
                why_it_matters="You can't charge users without payment infrastructure. This is a critical path item for any monetized product.",
                recommendation="Add Stripe (web SaaS) or RevenueCat/react-native-iap (mobile). Stripe is the default choice for most web products.",
                effort_hours=16,
            )

    def _check_legal_compliance(self):
        distribution = self.context.get("distribution_target", "web")
        compliance = self.context.get("compliance_requirements", [])

        # Basic GDPR check for any web product
        if distribution in ("web-saas", "web", "api"):
            code_files = self._find_files("*.ts", "*.tsx", "*.js", "*.jsx")
            has_cookie_consent = False
            has_privacy_reference = False
            for fp in code_files[:30]:
                content = self._read_file(fp)
                if not content:
                    continue
                if re.search(r'cookie[_\-\s]?(?:consent|banner|policy)', content, re.IGNORECASE):
                    has_cookie_consent = True
                if re.search(r'privacy[_\-\s]?policy|gdpr|data[_\-\s]?protection', content, re.IGNORECASE):
                    has_privacy_reference = True

            if not has_cookie_consent and not has_privacy_reference:
                self._add(
                    id=self._next_id("PLAT"),
                    severity="medium",
                    category="legal",
                    title="No cookie consent or privacy compliance detected",
                    description="No cookie consent banner, GDPR references, or privacy policy links found.",
                    why_it_matters="GDPR (EU) and similar laws require user consent for cookies/tracking. Non-compliance can result in fines.",
                    recommendation="Add a cookie consent banner if you use analytics/tracking. Add a privacy policy page. Consider using a service like CookieBot or Termly.",
                    effort_hours=4,
                )
