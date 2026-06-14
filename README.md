# StratCMO

**An AI CMO cofounder for founders.** Point it at your company URL and it researches your market,
finds the specific threads and communities where your customers already are, drafts platform-native
posts you can ship, and keeps a board full of fresh opportunities — then turns shipping into a habit
with streaks, personas, and a daily marketing lesson tailored to your own drafts.

Built by [Maximem](https://maximem.ai) as an open showcase for **Synap**, our durable-memory engine.

> **It drafts; you ship.** Every post is a draft for your review — you publish it under your own
> identity and accounts, and you're responsible for following each community's rules. Several
> platforms (Reddit, Hacker News, Indie Hackers) police self-promotion hard; the app flags the
> smells, but the judgment is yours.

---

## How it works

A LangGraph-style agent runs a research → synthesize → draft → monitor loop:

1. **Objective** — reads your site, infers your stage and a marketing objective.
2. **Source strategy** — maps where your customers actually hang out.
3. **Act / reflect** — runs real research (Exa, Hacker News, Reddit, your connected tools) until the
   intel is specific.
4. **Synthesize** — turns it into strategic moves + concrete engagement opportunities.
5. **Draft** — writes platform-voiced replies for each opportunity.
6. **Monitor** — self-identifies recurring signals to watch, so the board refills over time.
7. **Remember** — writes durable company memory to Synap so it gets sharper every run.

The **Action Board** is where drafts live as cards (suggested → drafted → approved → posted →
engaged). Shipping drives the **momentum** system — activation score, ship-streak, personas, and
**the Daily Edge** (one tailored marketing lesson a day, grounded in your actual drafts).

## Architecture

| Layer | Stack |
|-------|-------|
| Backend | FastAPI (Python 3.11), the agent graph, Stripe billing, plan entitlements |
| Frontend | React + Vite (no router dependency; served statically by the backend in prod) |
| Auth + DB | Supabase (Postgres + JWT). Single-tenant local mode when unset. |
| Memory | **Synap** (Maximem) — durable per-company memory |
| Models | Anthropic + OpenAI (via the Pioneer gateway when available, else native) |
| Research | Exa, Browserbase, Composio (connected tools) |
| Scheduling | In-process APScheduler, or Redis + Arq worker when `REDIS_URL` is set |
| Payments | Stripe (Checkout + Customer Portal + webhooks) |

## Quickstart (local)

```bash
# 1. Backend
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # fill in your keys (see below)
uvicorn app.main:app --reload --port 8080

# 2. Frontend (separate terminal)
cd frontend
npm install
cp .env.example .env          # optional: Supabase + Sentry
npm run dev                   # http://localhost:5173
```

With **no keys set**, the backend runs in single-tenant demo mode (no auth, no quotas, JSON
fallbacks) so you can see the cached demo run immediately. To exercise the real agent you bring your
own keys (below).

## Configuration

Every external dependency is optional except the model and memory keys needed to actually run the
agent. Set what you need in `backend/.env`:

| Variable | Needed for |
|----------|-----------|
| `ANTHROPIC_API_KEY` / `OPENAI_API_KEY` / `PIONEER_API_KEY` | Model inference (at least one) |
| `SYNAP_API_KEY`, `SYNAP_BASE_URL` | Durable memory (the compounding moat — see below) |
| `EXA_API_KEY`, `BROWSERBASE_API_KEY` / `_PROJECT_ID` | Web research + page reading |
| `COMPOSIO_API_KEY` | Connecting platforms/tools |
| `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY` | Auth + multi-tenant accounts (omit for local demo) |
| `STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET`, `STRIPE_PRICE_PRO` | Billing (omit to stay free-plan-only) |
| `REDIS_URL` | Dedicated monitor worker (omit for in-process scheduler) |
| `ALLOWED_ORIGINS`, `APP_BASE_URL`, `SENTRY_DSN`, `RESEND_API_KEY` | Production hardening |

See [`backend/.env.example`](backend/.env.example) and [`frontend/.env.example`](frontend/.env.example)
for the full list.

## Plans & entitlements

Plan logic is plain data in [`backend/app/usage.py`](backend/app/usage.py): **Free** is the cold
start and the manual loop (one weekly run, a daily chat allowance, create-but-don't-fire monitors,
one company); **Pro** unlocks firing monitors, unlimited re-runs, agentic chat, and multiple
companies. Tune the numbers freely. Self-hosting? It's Apache-2.0 — flip your own plan to `pro`; the
free/paid split exists for the hosted service.

## Self-hosting — read this first

This repo is genuinely open (Apache 2.0) and runs end-to-end. But "self-host" is not "free":

- **Bring your own keys.** Anthropic/OpenAI, Exa, Browserbase, Composio, Supabase and Stripe are
  third-party services you sign up and pay for directly. The agent's per-run cost is real (model +
  search + page-reads).
- **Synap is required for the full experience and is itself freemium.** The durable cross-run memory
  — the thing that makes the agent get smarter about *your* company over weeks — runs on Maximem
  Synap. The app degrades gracefully without it (you can evaluate the loop), but the compounding
  value lives there. Get a key at [maximem.ai](https://maximem.ai).
- **You run the ops.** Postgres, the scheduler/worker, key management, and updates are yours.

If you'd rather not run any of that, the hosted version is at [stratcmo.app](https://stratcmo.app).

## License & contributing

Licensed under the **Apache License 2.0** — see [LICENSE](LICENSE). Note that Apache 2.0 grants
copyright and patent rights but **not** trademark: "StratCMO" and the Maximem marks are reserved.

Issues and PRs welcome. For anything substantial, open an issue first so we can align on direction.

— Questions: **gaurav@maximem.ai**
