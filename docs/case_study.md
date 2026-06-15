# Case Study: Hardening An AI Journal Partner

## Problem

AI agents can sound confident while quietly failing at the things users care about most:

- remembering stale facts as if they are current
- claiming tool access they do not actually have
- writing long replies that never complete the thought
- skipping reasoning on high-impact recommendations
- losing track of recent conversation context

Project Maxima exposed these issues in a real personal-agent workflow. The answer was not to add more tools first. The answer was to build a reliability lab.

## Approach

Agent Reliability Arena turns those failure modes into deterministic checks.

The first suite focuses on:

- current-truth override
- stale countdown suppression
- decision transparency
- tool honesty
- compact complete responses
- transcript health

The goal is simple: make agent quality visible before users need to complain.

In v0.2, the project also adds a public browser analyzer:

- paste any AI agent transcript
- run local deterministic checks
- get a reliability score and verdict
- download a JSON report
- see one concrete next action

This turns the repo from a static portfolio proof into a usable lead magnet for agent audit work.

## What The Arena Catches

The `drift_demo` suite intentionally includes bad agent behavior:

- stale countdown leak
- unsupported live-web claim
- missing reasoning framework
- incomplete answer ending

The Arena scores this as a patch-needed run instead of letting the failure hide inside a natural-language transcript.

## Result

Foundation suite:

```text
5 pass / 0 warn / 0 fail - quality 100/100
```

Drift demo:

```text
0 pass / 4 warn / 1 fail - quality 40/100
```

Live Maxima import:

```text
Arena quality: 67/100
Maxima source quality: 96/100
Token in saved report: false
```

The mismatch between Arena quality and source quality is useful: it shows that an external harness can be stricter than the agent's own internal score.

Public v0.2 analyzer:

```text
Paste transcript -> score -> failure modes -> report download -> audit CTA
```

This creates a simple commercial path: a founder can test a transcript themselves, then hire Lance for a deeper reliability audit or implementation fix.

## Cross-Model Reliability Leaderboard (v0.3, June 2026)

The Arena started by scoring one agent. v0.3 turns it into a comparative benchmark: the same probe suite, run across multiple frontier models, so reliability can be compared apples to apples.

**Architecture.** The heavy lifting lives in Axiom — a self-built multi-provider LLM gateway — which exposes `POST /benchmark/reliability`. It runs the probe suite through Claude, GPT, Gemini, Groq, and Maxima using one shared router and the same deterministic scoring. A GitHub Action calls that endpoint in CI (provider keys stay in repo Secrets), transforms the report, and commits a static `leaderboard.json` that the public page renders. The result: no per-visitor cost, no API key in the browser, and an auto-refreshing board.

**Multi-run averaging.** Agents are non-deterministic, so a single run is noisy. Each provider is run three times; the board reports the mean and the range. That is the difference between a number and a *trustworthy* number.

**Verified results (3 runs each):**

```text
Groq    90/100  (range 89-91)  - consistent
Claude  88/100  (range 87-89)  - consistent
```

**What the benchmark surfaced — honestly:**

- It caught two real provider-integration bugs in the gateway, not in the models: GPT-5-series models reject the legacy `max_tokens` parameter (they require `max_completion_tokens`), and the Gemini SDK throws when a response is truncated. Both were silently breaking every call to those providers — found only because the benchmark exercised them under pressure.
- It hit the limits of the *pipeline*, not just the models: a fresh OpenAI key with no billing returns quota errors, and Gemini's free tier exhausts quickly under repeated runs.

The meta-lesson is the whole point of the project: **reliability is not just model quality — it is the entire pipeline (parameters, quotas, rate limits, retries) holding up under real conditions.** A model you cannot call reliably is unreliable, full stop.

## Engineering Lessons

1. Keep telemetry out of memory.

   Eval history belongs in a flight recorder, not in the user's long-term memory store.

2. Current truth must outrank old recall.

   Old tactical facts should never beat fresh runtime truth.

3. Public demos need both happy-path and failure-path examples.

   A reliability tool is more credible when it shows what it catches.

4. Private agent telemetry needs token-safe import rules.

   Reports should store source paths without query tokens.

5. Single runs of non-deterministic models lie.

   Run each model several times and report the mean and the spread. Consistency is itself a reliability signal — a model that swings 30 points between identical runs is a different risk than one that holds steady.

6. A benchmark proves its worth by catching infrastructure bugs, not just model flaws.

   The cross-model run exposed parameter mismatches and SDK edge cases that no single happy-path demo would ever have revealed.

## Next Steps

- Score GPT and Gemini once provider billing/quota is provisioned (full five-model board).
- Add an adversarial / prompt-injection probe suite.
- Add a reliability x cost x latency view for model selection.
- Add an embeddable "reliability score" badge for any audited agent.
- Add a GitHub Action that reliability-tests any agent repo on each PR.
- Turn Maxima's Eval Lab into a recurring benchmark source.
