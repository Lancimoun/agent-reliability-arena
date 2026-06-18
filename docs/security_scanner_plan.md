# FORGE Security Scanner Plan

Goal: evolve the account-security checklist into a defensive scanner for people who want to harden their own accounts, domains, and AI-agent infrastructure.

Hard boundary: only scan accounts, domains, and systems the user owns or has explicit permission to assess. Do not collect passwords. Do not bypass login. Do not read email bodies. Do not store private evidence by default.

## Phase 1 - Public Email Domain Scanner

Status: shipped in `security.html`.

This phase requires no login and no API keys. It checks public DNS posture for an email domain:

- MX records
- SPF TXT record
- DMARC TXT record and enforcement policy
- DMARC reporting (`rua=`)
- common DKIM selector records
- MTA-STS TXT record
- TLS reporting TXT record

The scanner accepts either `person@example.com` or `example.com`. If an email address is entered, only the domain is queried.

Limitations:

- DKIM selector discovery is incomplete by nature. Mail providers choose selectors, so the scanner checks common selectors and explains that a miss is not definitive.
- Public DNS posture does not prove inbox safety. It only catches domain-authentication gaps.
- DNS-over-HTTPS calls go to public resolvers; private account data is not sent.

## Phase 2 - Gmail Settings Scanner

Status: partially shipped as a guided cross-device deep scan; OAuth automation is planned.

Current shipped layer:

- Google/Gmail persistence checklist
- PC/browser hygiene checklist
- mobile/SIM path checklist
- financial recovery checklist
- developer/cloud secrets checklist
- evidence and aftercare checklist
- downloadable cross-device incident-readiness report

This layer works on desktop and mobile browsers without account access.

Future OAuth layer:

Use explicit Google OAuth and least-privilege scopes to inspect Gmail settings that public DNS cannot see:

- suspicious filters that delete, archive, mark-read, or hide security alerts
- forwarding addresses
- send-as aliases
- POP/IMAP settings
- delegated account settings where available

Rules:

- No email body access.
- No broad Gmail read scope unless absolutely necessary.
- No token storage in the browser.
- Server-side token storage, if ever added, must be encrypted, revocable, and scoped.
- The app must clearly explain what it reads before consent.

Important implementation note: Gmail settings scopes are sensitive/restricted and may require Google app verification before a public release.

## Phase 3 - Google Security Checkup Companion

Status: planned.

Some security-critical account surfaces are not cleanly exposed through public APIs, especially:

- passkeys and security keys
- active sessions and trusted devices
- third-party connected apps
- recovery email and recovery phone
- Advanced Protection enrollment

The safe public implementation is a guided checklist with deep links to Google Security Checkup and copy that explains what to look for.

## Phase 4 - Breach Exposure

Status: planned.

Use Have I Been Pwned carefully:

- password checks should use k-anonymity range lookup and never send a full password
- email breach lookup requires an API key
- domain breach search requires domain verification

Free public mode should link users to the official HIBP site or support local k-anonymity password checks only if implemented carefully.

## Phase 5 - Report And Lead Magnet

Status: planned.

Generate a polished report:

- JSON download
- copyable fix plan
- optional PDF
- optional email-to-Lance audit request via `mailto:`

Do not add automated outbound email until the backend can enforce rate limits, abuse prevention, consent, and privacy logging.

## Research Anchors

- DMARC: RFC 7489
- SPF: RFC 7208
- DKIM: RFC 6376
- MTA-STS: RFC 8461
- SMTP TLS Reporting: RFC 8460
- DNS-over-HTTPS: RFC 8484
- Gmail settings API: Gmail filters and forwarding-address endpoints
- Google Account Security Checkup: official Google Account help
- Have I Been Pwned API: official HIBP v3 documentation

## Product Positioning

This belongs inside Agent Reliability Arena because security and AI reliability share the same mental model:

1. Assume hidden failure modes exist.
2. Make invisible state visible.
3. Score the risk.
4. Prioritize the fix.
5. Verify that the fix holds.
