# Agent Reliability Arena Roadmap

This project is moving from a transcript analyzer into a public reliability benchmark for AI agents.

## North Star

Make agent reliability visible, repeatable, and useful for real builders.

The long-term product loop:

1. Run the same reliability probes across agents or model providers.
2. Score memory drift, stale facts, tool honesty, answer completion, and decision transparency.
3. Publish a clean leaderboard and scorecard.
4. Turn the results into portfolio proof, client audits, and CI regression tests.

## Phase 1 - Leaderboard V1

Status: in progress.

Ship a public comparison board on the GitHub Pages demo.

Scope:

- Seed the board with real deterministic Arena results.
- Show Maxima's live score when `maxima-trend.json` is available.
- Add pending provider slots for Claude, GPT, Gemini, and Groq through Axiom.
- Make the page clearly state what is real now versus queued next.

Done when:

- The live page has a leaderboard section.
- The board can update from static JSON.
- No provider score is invented before a real run.

## Phase 2 - Axiom Multi-Provider Runner

Status: planned.

Use Axiom as the multi-provider gateway.

Scope:

- Create 15-20 probe prompts for known failure modes.
- Run the same prompts through each provider.
- Capture transcripts and raw responses.
- Normalize results into the Arena report shape.
- Render a public HTML/PDF scorecard.

Target providers:

- Claude
- GPT
- Gemini
- Groq
- Maxima

## Phase 3 - Cost And Latency View

Status: planned.

Reliability alone is not enough for business decisions.

Scope:

- Track estimated cost per run.
- Track latency per provider.
- Add a decision-grade view: reliability score x cost x speed.
- Turn this into buying guidance for founders and teams.

## Phase 4 - Developer Distribution

Status: planned.

Make the Arena useful inside real engineering workflows.

Scope:

- GitHub Action that runs reliability checks on pull requests.
- Optional failure threshold for regressions.
- README badge that links back to the Arena.
- Sample CI config for agent repos.

## Phase 5 - Deeper Reliability Science

Status: planned.

Add stronger evaluation layers after the deterministic foundation is stable.

Scope:

- Optional LLM-as-judge scoring behind API keys.
- Adversarial prompt-injection and jailbreak probes.
- Statistical rigor: run each case multiple times and report variance.
- Named framework: Arena Reliability Spec.

## Productized Offer

The paid offer should stay simple while the tool matures:

- Starter Audit: transcript review, score, and fix checklist.
- Deep Audit: multi-case eval pack and reliability hardening plan.
- Implementation: prompts, memory rules, evals, tool honesty, dashboards, and CI.

The best next move is still shipping one visible improvement at a time.
