# StratCMO — Launch Plan

From hackathon prototype → launch-ready multi-tenant SaaS. Phases follow the dependency order:
each phase unblocks the next. Status legend: ✅ done · 🟡 in progress · ⬜ not started.

**Stack decisions (locked):** Supabase (Postgres + Auth), supabase-py on the backend (service
role, REST), Stripe for billing, Render for deploy (single Docker container today).

---

## Phase 0 — Foundation: Supabase DB + migrations  ✅ DONE

- [x] Supabase project created; SQL schema applied
- [x] Tables: `profiles`, `organizations`, `org_members`, `runs`, `monitors`, `monitor_events`,
      `org_settings`, `integrations`, `usage_events`
- [x] Auto-provision trigger: signup → profile + personal workspace + owner membership
- [x] RLS enabled on all tables, isolation by org membership (`is_org_member`/`is_org_admin`)
- [x] Migrations version-controlled: [supabase/migrations/0001_init.sql](supabase/migrations/0001_init.sql),
      [0002_rls.sql](supabase/migrations/0002_rls.sql)

**Files:** `supabase/migrations/*`

---

## Phase 1 — Auth + orgs + tenant-scoping retrofit  ✅ DONE (org switcher + CORS lock deferred)

Frontend auth shipped: `frontend/src/supabase.ts` (client gated on `VITE_SUPABASE_*`),
`Auth.tsx` (AuthGate + email/password Login + SignOut), `api.ts` attaches the bearer token to
every call and `?access_token=` to the SSE stream, `main.tsx` wraps the app. Builds clean.
Still open: org-switcher UI and CORS lockdown (tracked in Phase 5 / below).

### Done
- [x] `config.py` reads `SUPABASE_*` (accepts dashboard alias names)
- [x] `app/db.py` — supabase-py service-role client + run/monitor/usage helpers + `primary_org_for`
      (safe no-op when unconfigured)
- [x] `app/auth.py` — JWT verify dep; handles **both** HS256 (legacy secret) and asymmetric
      (JWKS) tokens; accepts header or `?access_token=` query param (for SSE)
- [x] `app/tenancy.py` — `customer_scope(org_id, slug)` single source of truth
- [x] `memory.py` — dropped hardcoded `USER_ID="founder"`; `user_id` threaded in
- [x] `graph.py` — `org_id`/`user_id`/`scope` flow through state; Synap + monitors org-scoped
- [x] `monitors.py` — keyed by `(org_id, slug)`, DB-backed with JSON fallback
- [x] `main.py` — endpoints resolve caller org via auth; runs persisted; usage metered;
      `GET /api/runs` added
- [x] Verified: live Supabase connectivity, `primary_org_for` resolves test user's workspace

### Remaining
- [ ] **Frontend auth (BLOCKER for live use).** Backend now requires a bearer token; frontend
      sends none yet → all calls 401.
  - [ ] `npm i @supabase/supabase-js`; create `frontend/src/supabase.js` client (URL + anon/publishable key)
  - [ ] Sign-up / sign-in / sign-out UI; session persistence
  - [ ] Attach `Authorization: Bearer <access_token>` to all `fetch` calls
  - [ ] **SSE gotcha:** `EventSource` can't set headers → pass `?access_token=` on
        `/api/analyze/stream` (backend already accepts it). Research: EventSource vs fetch-based
        streaming (`@microsoft/fetch-event-source`) — decide which.
  - [ ] Frontend env: `VITE_SUPABASE_URL`, `VITE_SUPABASE_ANON_KEY`
- [ ] **Org switcher UI** (later) — `primary_org_for` returns oldest membership today; multi-org
      switching needs a UI + active-org passed to the backend.
- [ ] **Lock CORS** — `main.py` is `allow_origins=["*"]`; restrict to real frontend origin(s).
- [ ] Research: confirm which signing key the project actually issues (HS256 legacy vs ES256
      asymmetric) so we know which verification path is live; both are coded.

**Files:** `frontend/src/*`, `backend/app/main.py`

---

## Phase 2 — Background worker (move monitors off the web process)  ✅ DONE (monitors); analyze-run offload deferred

Shipped: `app/worker.py` (Arq) with `run_monitor_task` + a `sweep_monitors` cron (every 15 min)
that enqueues due monitors using Redis last-fire stamps. Gated on `REDIS_URL`: when set, the
in-process APScheduler is disabled (`monitors.redis_enabled()`) so the worker owns scheduling and
nothing double-fires; when unset, the in-process scheduler still runs (local/demo). `render.yaml`
gains a `cmo-worker` service (`arq app.worker.WorkerSettings`) + `REDIS_URL` on web + worker.
Chosen Arq over Celery (async-native, lighter). Provision Render Key Value / Upstash + set
`REDIS_URL` to activate.

Still deferred (the original "research" items):
- Offload long `/api/analyze` runs to the worker with a Redis pub/sub → SSE bridge.

The in-process APScheduler won't survive restarts and double-fires on >1 instance. Monitor state
is already DB-backed (`monitors`/`monitor_events`), so the store is migration-ready.

- [ ] Choose: **Arq + Redis** (lightweight, async-native, fits FastAPI) vs **Celery + Redis**
      (heavier, more ecosystem) vs **Render Cron Jobs** (no Redis, but coarse scheduling).
  - Research: Arq vs Celery for async FastAPI; Render's worker + cron primitives + pricing.
- [ ] Add Redis (Render Redis add-on or Upstash).
- [ ] Move `monitors._fire` / `run_monitor` into worker tasks; web process only enqueues.
- [ ] Scheduler reads all monitors from DB (across orgs) and enqueues on cadence.
- [ ] Long agent runs (`/api/analyze`) → consider moving to worker too; web streams progress
      from a job channel instead of running the graph inline. (Research: SSE/websocket bridging
      from a worker — Redis pub/sub.)
- [ ] Idempotency / dedupe so a monitor doesn't run twice per window.

**Files:** new `backend/app/worker.py`, `monitors.py`, `render.yaml` (add worker service)

---

## Phase 3 — Rate limits + cost caps  ✅ DONE (Redis-backed rate limit + token-cost capture deferred)

Shipped: `app/usage.py` (per-plan monthly quotas via `PLAN_LIMITS`; free=10 runs/200 chats/etc,
pro=unlimited; kill-switch via `org_settings.settings.disabled`), `app/ratelimit.py` (in-memory
fixed-window burst caps), and a shared `_enforce(ctx, request, kind)` in main.py applied to
run/chat/research/ui — kill-switch → rate limit → monthly quota, returning 403/429 with an
upgrade message. Demo mode (no org) skips quotas. Closed a security gap: `/api/research` and
`/api/ui/render` now require auth. New `GET /api/usage` surfaces current usage vs limits.

Still deferred (the original "research" items):
- Redis-backed distributed rate limiting (in-memory is per-instance only).
- Capturing real per-run token spend into `usage_events.metadata` (needs threading model usage
  out of `models.py`).
- Frontend: show usage + upgrade prompt on 429.

We proxy paid APIs (Anthropic, Browserbase, Exa, Composio) per user. Without caps, one user can
run up the bill. `usage_events` already records run/chat/research/monitor events.

- [ ] Per-org quotas by plan (e.g. free = N runs/month) enforced before starting a run.
- [ ] Per-org + per-IP rate limiting (research: `slowapi` for FastAPI, or Redis token bucket).
- [ ] Aggregate `usage_events` → current-period counters (view or scheduled rollup).
- [ ] Surface usage to the user (dashboard) and return 429 / upgrade prompt when over.
- [ ] Hard kill-switch per org (abuse).
- [ ] Research: capturing real token spend per run (LLM response usage) into `usage_events.metadata`
      so cost, not just count, is tracked.

**Files:** `backend/app/usage.py` (new), `main.py`, `db.py`

---

## Phase 4 — Stripe billing  ✅ DONE (free/pro subscription); metered/credits deferred

Shipped: `app/billing.py` (Checkout, Customer Portal, webhook handler) + routes
`/api/billing/{checkout,portal,webhook}`. Webhooks are the source of truth — `checkout.session
.completed`, `customer.subscription.*`, `invoice.payment_failed` write `plan`/`subscription_status`
/`current_period_end`/`stripe_*` onto the org (verified via `STRIPE_WEBHOOK_SECRET`). Phase 3
quotas read `plan`, so entitlement is automatic. Gated on `STRIPE_SECRET_KEY` (503 when unset).
Frontend: `AccountBar` footer shows plan + Upgrade (Checkout) / Manage billing (Portal) + Sign out.

To activate: create a Pro recurring price in Stripe → set `STRIPE_PRICE_PRO`, `STRIPE_SECRET_KEY`,
`STRIPE_WEBHOOK_SECRET`, `APP_BASE_URL`. Test webhooks with `stripe listen --forward-to
localhost:8080/api/billing/webhook`.

Still deferred (the original "research" items):
- Usage-based / credit pricing (Stripe meter events) — current model is flat free/pro.
- Chosen flat subscription for v1 simplicity; revisit once real COGS per run is measured (Phase 3 deferred item).

Depends on orgs + entitlement storage (Phase 1) and ideally usage tracking (Phase 3).
`organizations` already has `stripe_customer_id`, `stripe_subscription_id`, `plan`,
`subscription_status`, `current_period_end`.

- [ ] Decide pricing model: seat-based vs usage-based vs credits. (AI COGS are real — flat
      unlimited will be arbitraged. Lean: base plan + metered overage, or credits.)
- [ ] Stripe products/prices created.
- [ ] Checkout: create Stripe customer on first upgrade, map `stripe_customer_id` → org.
- [ ] **Webhooks are the source of truth** — endpoint handling `checkout.session.completed`,
      `customer.subscription.{created,updated,deleted}`, `invoice.payment_failed`; write
      plan/status/`current_period_end` into `organizations`. Verify webhook signatures.
- [ ] Customer portal (Stripe-hosted) for plan changes / cancellation.
- [ ] Entitlement checks: gate features/quotas by `organizations.plan`.
- [ ] Research: Stripe usage-based / meter events API if going metered; idempotency keys;
      test-mode webhook flow with Stripe CLI.

**Files:** `backend/app/billing.py` (new), `main.py` (webhook route), frontend billing page

---

## Phase 5 — Observability + launch polish  ⬜ NOT STARTED (run in parallel)

### Observability
- [ ] Error tracking: **Sentry** (backend + frontend).
- [ ] LLM tracing: **Langfuse** or **LangSmith** (we run a LangGraph agent — need step-level
      traces + cost). Research: Langfuse self-host vs cloud; LangGraph integration.
- [ ] Structured logging + request IDs; per-org cost dashboard (from `usage_events`).
- [ ] Uptime/health alerting on `/api/health`.

### Per-org integrations (Composio)
- [ ] `composio_tools.py` uses one shared `USER_ID="cmo-cofounder"` — make connections
      per-org via the `integrations` table. Research: Composio per-end-user connected accounts
      / OAuth-per-workspace flow.
- [ ] Onboarding: connect-integrations step.

### Security
- [ ] Lock CORS (also in Phase 1), security headers, secrets in Render env (not committed `.env`).
- [ ] Verify RLS can't be bypassed from the frontend-direct path; audit service-role usage.
- [ ] Dependency/secret scanning.

### Legal / launch table-stakes
- [ ] Terms of Service + Privacy Policy.
- [ ] **DPA with Maximem/Synap** — we store customer company data in a third party.
- [ ] Data-deletion / export path (account + workspace deletion cascades).
- [ ] Transactional email (Resend — already cached in repo) for auth/billing/monitor alerts.

### Onboarding
- [ ] First-run flow: create/confirm workspace → connect integrations → first analysis.

**Files:** cross-cutting

---

## Cross-cutting notes / open questions

- **Single container caveat:** DB is managed Supabase (good), but app + scheduler share one
  Render web container. Phase 2 splits the worker out; revisit horizontal scaling then.
- **Demo mode preserved:** with `SUPABASE_*` unset, backend runs single-tenant with JSON/-tmp
  fallbacks and no auth — keep this path working for local dev.
- **Migration tooling:** SQL files are hand-applied today. Consider adopting the Supabase CLI
  (`supabase db push`) for repeatable staging/prod migrations.
- **Synap scoping:** brains are org-scoped (`org_id:slug`). Confirm this is the desired ownership
  model vs user-scoped before customers onboard.
