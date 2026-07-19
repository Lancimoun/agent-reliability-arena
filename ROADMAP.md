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

Status: shipped (2026-07).

Ship a public comparison board on the GitHub Pages demo.

Scope:

- Seed the board with real deterministic Arena results.
- Show Maxima's live score when `maxima-trend.json` is available.
- Add pending provider slots for Claude, GPT, Gemini, and Groq through Axiom.
- Make the page clearly state what is real now versus queued next.

Done when:

- The live page has a leaderboard section. ✅
- The board can update from static JSON. ✅ (`docs/leaderboard.json`)
- No provider score is invented before a real run. ✅ (GPT and Maxima-via-Axiom stay unscored)

## Phase 2 - Axiom Multi-Provider Runner

Status: shipped, with the probe suite still short of target.

Uses Axiom as the multi-provider gateway. `scripts/build_leaderboard.py` runs the suite through Axiom's `/benchmark/reliability`, normalizes results into the Arena report shape, and commits `docs/leaderboard.json` for the public page to render.

Scope:

- Create 15-20 probe prompts for known failure modes. ⏳ **5 today** — the main open gap in this phase.
- Run the same prompts through each provider. ✅
- Capture transcripts and raw responses. ✅
- Normalize results into the Arena report shape. ✅
- Render a public HTML/PDF scorecard. ✅ HTML on the live page; PDF export not built.

Target providers:

- Claude ✅ scored
- GPT ⏳ blocked on OpenAI quota/rate limit
- Gemini ✅ scored
- Groq ✅ scored
- Maxima ⏳ `MAXIMA_BENCHMARK_URL` unset; reports via live trend import instead

## Phase 3 - Cost And Latency View

Status: shipped.

Reliability alone is not enough for business decisions. The board now carries cost and latency columns beside every score, which is what makes the spread legible: the fastest provider (Groq, 769 ms) and the slowest (Gemini, 16247 ms) sit within one point of each other on reliability.

Scope:

- Track estimated cost per run. ✅ (run count per provider)
- Track latency per provider. ✅
- Add a decision-grade view: reliability score x cost x speed. ✅ on the live board
- Turn this into buying guidance for founders and teams. ⏳ the numbers are published; the written guidance is not

## Phase 4 - Developer Distribution

Status: partially shipped.

Scope:

- GitHub Action that runs reliability checks on pull requests. ✅ (`ci.yml` runs the foundation suite, drift demo, dashboards, and unit tests on push + PR)
- Optional failure threshold for regressions. ✅ `gate` enforces foundation quality ≥90, zero hard failures, and at most one warning. CI also requires the intentional drift canary to stay ≤50 with at least one hard failure, so a permissive evaluator cannot earn a false green build.
- README badge that links back to the Arena. ✅
- Sample CI config for agent repos. ⏳

## Phase 5 - Deeper Reliability Science

Status: partially shipped.

Scope:

- Optional LLM-as-judge scoring behind API keys. ⏳
- Adversarial prompt-injection and jailbreak probes. ⏳
- Statistical rigor: run each case multiple times and report variance. ✅ every provider runs 3×; the board publishes mean and range.
- Named framework: Arena Reliability Spec. ⏳

## Productized Offer

The paid offer should stay simple while the tool matures:

- Starter Audit: transcript review, score, and fix checklist.
- Deep Audit: multi-case eval pack and reliability hardening plan.
- Implementation: prompts, memory rules, evals, tool honesty, dashboards, and CI.

The best next move is still shipping one visible improvement at a time.
