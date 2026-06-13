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

## Engineering Lessons

1. Keep telemetry out of memory.

   Eval history belongs in a flight recorder, not in the user's long-term memory store.

2. Current truth must outrank old recall.

   Old tactical facts should never beat fresh runtime truth.

3. Public demos need both happy-path and failure-path examples.

   A reliability tool is more credible when it shows what it catches.

4. Private agent telemetry needs token-safe import rules.

   Reports should store source paths without query tokens.

## Next Steps

- Add shareable report pages.
- Add regression thresholds for CI.
- Add OpenTelemetry-style trace export.
- Add optional model-graded rubrics.
- Add adapters for more agent telemetry formats.
- Turn Maxima's Eval Lab into a recurring benchmark source.
