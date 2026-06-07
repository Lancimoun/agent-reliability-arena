# Live Maxima Import

Agent Reliability Arena can import Project Maxima's private Eval Lab telemetry and turn it into a normal Arena report.

This is useful when you want to compare canned eval cases against a real deployed agent.

## Privacy Rules

- Do not commit token URLs.
- Do not paste `SYNC_SECRET` into README files, screenshots, issues, or logs.
- Prefer environment variables over command-line tokens.
- Generated reports in `runs/` are ignored by git.

## Import From Railway

PowerShell:

```powershell
$env:SYNC_SECRET = "your-secret-here"
python -m agent_reliability_arena import-maxima --out runs/maxima-live.json
python -m agent_reliability_arena dashboard --report runs/maxima-live.json --out runs/maxima-live-dashboard.html
```

The stored report records only the source path, not the query token.

## Daily Trend

Use `--trend-out` when you want each live import to update a compact reliability history:

```powershell
$env:SYNC_SECRET = "your-secret-here"
python -m agent_reliability_arena import-maxima --out runs/maxima-live.json --trend-out runs/maxima-trend.json
python -m agent_reliability_arena trend-dashboard --trend runs/maxima-trend.json --out runs/maxima-trend.html
```

Trend rows are intentionally small: run id, generated time, Arena score, source score, verdict, pass/warn/fail counts, and token-stripped source URL. They do not store raw memory, query tokens, or the full private payload.

## GitHub Actions Automation

The repository includes a scheduled workflow named `Maxima Reliability Trend`.

To activate it:

1. Open the GitHub repo settings.
2. Go to `Secrets and variables` -> `Actions`.
3. Add a repository secret named `MAXIMA_SYNC_SECRET`.
4. Paste the same sync secret used by Maxima's private `/eval-lab.json` endpoint.
5. Run the workflow manually once from the `Actions` tab, or wait for the daily schedule.

The workflow runs at `09:00 IST` and updates:

- `docs/maxima-trend.json`
- `docs/maxima-trend.html`

If the secret is not configured, the workflow exits safely without importing live Maxima telemetry.

## Import From A Full URL

Use this only locally:

```powershell
python -m agent_reliability_arena import-maxima --url "https://maxima-v3-production.up.railway.app/eval-lab.json?token=REDACTED" --out runs/maxima-live.json
```

Do not commit or screenshot the full token URL.

## What Gets Imported

- Maxima core Eval Lab checks
- Maxima Canary checks
- Live transcript health checks
- Maxima quality score when available
- Maxima history summary when available
- Compact daily trend rows when `--trend-out` is used

## What Does Not Get Imported

- Raw private memory
- `.env` values
- token query strings in saved source metadata
- Obsidian vault contents
