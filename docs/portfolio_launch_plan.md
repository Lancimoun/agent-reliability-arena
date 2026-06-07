# Portfolio Launch Plan

Agent Reliability Arena is strongest as a public proof-of-skill repo.

## Positioning

One-line pitch:

> A dependency-light eval harness for testing AI agents against memory drift, stale facts, tool hallucinations, incomplete replies, and transcript health.

## Launch Checklist

- Create a dedicated GitHub repo named `agent-reliability-arena`.
- Copy this folder into the new repo root.
- Run the CI workflow.
- Add a screenshot of `runs/dashboard.html` generated from the foundation suite.
- Add a screenshot of `runs/drift-dashboard.html` showing the arena catching failures.
- Pin the repo on GitHub.
- Post a short LinkedIn/Discord writeup.

## Suggested Post

I built Agent Reliability Arena because agent demos are easy, but agent reliability is hard.

It checks:

- stale memory leaks
- current-truth override
- tool honesty
- incomplete replies
- missing reasoning frameworks
- transcript health

It is dependency-light, runs locally, and generates JSON plus a static dashboard.

This came from hardening my own AI partner system, Project Maxima.

## Next Technical Upgrades

- Add regression thresholds in CI.
- Add OpenTelemetry-style trace export.
- Add optional model-graded rubric checks.
- Add live Maxima import examples with redacted reports.
- Add a small FastAPI dashboard service.
