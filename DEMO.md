# CMO Cofounder — Demo Runbook

An autonomous **CMO cofounder** for founders: point it at a company URL → it picks the stage-right
objective, maps where the customers actually are, hunts non-obvious wedges, and hands back a
prioritized board + an engagement radar (specific threads to act on) **with ready-to-send drafts**.
Runs in the cloud, remembers across runs, fully inspectable.

## Run locally
Backend:
```
cd backend && .venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8080
```
Frontend (dev, hot reload, proxies /api → :8080):
```
cd frontend && npm run dev      # http://localhost:5173
```
Production single container (what Render runs — UI + API on one port):
```
docker build -t cmo . && docker run -p 8080:8080 --env-file backend/.env cmo   # http://localhost:8080
```

## Demo flow (~90s — use CACHED mode: deterministic, instant, stage-safe)
1. App opens with `resend.com` pre-filled, mode = **cached**. Hit **Run agent**.
2. **Trace** (left) streams: recall → objective → source map → plan → research → reflect ×N → synthesize → drafts. Model badges show Sonnet / Haiku / EXA / HN per step. Click any step to open it in a tab.
3. **Objective banner**: "Lock in category ownership of 'email for developers'…" — explicitly **NOT** raw traffic. The stage-aware CMO brain.
4. **Where your customers actually are** — the company-type-aware source map.
5. **Engagement radar**: real HN threads (Wraps "AWS SES made usable", Sidemail) each with a **drafted founder-voice reply** → "open in tab" to inspect, "copy" to use.
6. **Prioritized moves**: P0/P1 plays (npm→API-key funnel, Supabase/Clerk integration slots, anti-SES-wrapper positioning).
7. **✨ Live view (OpenUI)**: click generate → a bespoke dashboard rendered by OpenUI.
8. **Chat**: "what's our #1 growth lever?" → answered by **GPT-4o** (multi-model). Flip **research mode** to trigger a fresh live web pull.
9. Switch to **live** + a judge's company for the "try yours" encore.

## Sponsor integrations
- **Composio** — HN/Reddit search routes through `composio.tools.execute` (needs valid `COMPOSIO_API_KEY`).
- **OpenUI** — `/api/ui/render` calls OpenUI's OpenAI-compatible API. To use genuine OpenUI:
  ```
  docker run --rm -p 7878:7878 -e OPENAI_API_KEY=$OPENAI_API_KEY ghcr.io/wandb/openui
  ```
  then set `OPENUI_URL=http://localhost:7878` in `backend/.env` (or Render env). Without it, a model fallback renders the view.
- **Render** — Docker web service via `render.yaml`; binds `$PORT`.
- **Maximem Synap** — compounding memory (`customer_id` = the analyzed company); needs valid `SYNAP_API_KEY`.
- **EXA** — neural web search. **Browserbase** — remote-headless freshness fallback (interface ready).

## ⚠️ Fix before the live demo
`COMPOSIO_API_KEY` and `SYNAP_API_KEY` currently return **auth errors** (401 / Invalid credentials).
The app runs on fallbacks (direct EXA/HN search; local-JSON memory), but to light up the real
Composio + Synap sponsor stories, set valid keys in `backend/.env` **and** the Render dashboard, then
re-seed the demo cache:
```
cd backend && .venv/bin/python seed_cache.py resend.com
```

## Integration test
```
cd backend && .venv/bin/python integration_test.py          # structural + free checks
RUN_LIVE=1 .venv/bin/python integration_test.py             # + live API checks
```

## Models (best model per task)
Sonnet 4.6 → objective / source-strategy / plan / reflect / synthesize · Haiku 4.5 → drafts · GPT-4o → chat.
