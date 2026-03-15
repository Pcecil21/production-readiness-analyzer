# App-Type Profiles

Use these profiles to calibrate finding severity in Step 3. The same code issue has different severity depending on where the app ships.

---

## iOS App Store

**Hard rejection triggers (always Critical):**
- Missing privacy policy
- Missing or vague permission usage descriptions
- App crashes during review
- App is primarily a web wrapper with no native functionality
- HealthKit data leaving device without explicit consent
- Missing entitlements for declared capabilities
- Inaccurate App Privacy nutrition labels

**Elevated severity (bump one level):**
- Offline handling (reviewers test in airplane mode)
- Permission denial handling (reviewers deny permissions)
- Accessibility labels (Apple features accessible apps)
- Onboarding flow quality (affects first-impression review)

**Reduced severity (can defer):**
- Scalability (App Store apps rarely see explosive day-1 traffic)
- CI/CD (nice to have but not required for first submission)
- Comprehensive test coverage (manual testing on devices is acceptable for v1)

**Unique requirements:**
- Monetization via in-app purchases only (no external payment links for digital goods — Apple's rules)
- Must support current and (current - 1) iOS versions
- Must support all current iPhone screen sizes
- TestFlight beta testing recommended before submission
- Budget 2–3 review cycles for first-time submissions

---

## Android Play Store

**Hard rejection triggers (always Critical):**
- Missing privacy policy
- Target SDK too old (must target recent API level)
- Missing permission declarations in manifest
- Crashes on launch

**Elevated severity:**
- Performance on low-end devices (Android has wider device range than iOS)
- Permissions — Android 13+ requires granular permissions

**Reduced severity:**
- Accessibility (less enforced than iOS, but still important)
- UI polish (Android users are somewhat more tolerant of rougher UI)

---

## Web SaaS (Paying Customers)

**Hard requirements (always Critical):**
- Authentication is working and secure
- Payment/billing integration functional
- User data is isolated (no tenant bleed)
- HTTPS everywhere
- Data backup exists

**Elevated severity:**
- Rate limiting (public-facing APIs get abused quickly)
- Input validation (SQL injection, XSS are real attack vectors)
- Error handling on payment flows (failed charge = lost customer + potential billing dispute)
- Monitoring and alerting (you must know when it's down)

**Reduced severity:**
- Offline support (web apps can assume connectivity)
- Platform-specific permissions (not applicable)
- App Store compliance (not applicable)

**Unique requirements:**
- Legal: Terms of Service, Privacy Policy, Cookie consent (if EU users)
- Billing: Stripe/Paddle/Lemon Squeezy integration, invoice generation, refund handling
- Support: need a support channel from day 1 (even if it's just an email address)

---

## API Product

**Hard requirements (always Critical):**
- Authentication (API keys, OAuth, or JWT)
- Rate limiting
- Input validation on every endpoint
- Consistent error response format
- HTTPS only

**Elevated severity:**
- API documentation (OpenAPI/Swagger — developers won't adopt without docs)
- Versioning strategy (breaking changes kill developer trust)
- Uptime and reliability (API consumers build on top of you)

**Reduced severity:**
- UI/UX (there is no UI)
- Onboarding flows (docs serve this purpose)
- Accessibility (not applicable)

---

## Internal Tool / Self-Hosted

**Elevated severity:**
- Basic auth (even internal tools get exposed accidentally)
- Data handling (internal tools often have the weakest data hygiene)

**Reduced severity:**
- Almost everything else can be lower severity
- Focus findings on: does it work reliably, is data safe, can someone else run it

---

## Profile Application Rules

1. Read the distribution target from `context.json`
2. Before assigning severity to any finding, check the relevant profile
3. If a finding's default severity should be bumped up or down per the profile, adjust it and note in the finding: `"severity_note": "Elevated from medium to high — App Store reviewers test permission denial flows"`
4. If a finding is marked "reduced severity" by the profile AND has effort > 20 hours, consider moving it to parking_lot phase
5. If a distribution target isn't listed here (e.g., "CLI tool", "Discord bot"), use Web SaaS as the baseline and remove irrelevant categories (UI/UX, onboarding, etc.)
