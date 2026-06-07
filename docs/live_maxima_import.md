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

## What Does Not Get Imported

- Raw private memory
- `.env` values
- token query strings in saved source metadata
- Obsidian vault contents
