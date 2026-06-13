# StratCMO — Backlog (deferred / later)

Persistent list of things intentionally deferred during the launch-readiness build (Phases 1–5).
Nothing here blocks launch; each item notes *why it can wait* and *what triggers doing it*.
The core launch work and its status live in [LAUNCH_PLAN.md](LAUNCH_PLAN.md).

---

## Integrations
- [ ] **Composio OAuth connect flow** — let each org connect its own accounts (Gmail, Slack, etc.).
  - Why later: only needed for "doing" tools (send/post/write), not searching/reading. The agent
    currently drafts but doesn't send. Per-org entity (`org-<id>`), the `integrations` table, and
    `/api/integrations` endpoints are already wired — only the connect UI + live OAuth handshake
    remain.
  - Trigger: the first time we want the agent to act inside a customer's own SaaS account.
  - Needs: live `COMPOSIO_API_KEY` to build/test the SDK-specific connect flow.

## Observability
- [ ] **LLM tracing (Langfuse or LangSmith)** — step-level traces + token cost for the agent graph.
  - Why later: Sentry already covers errors; tracing is a debugging/cost-visibility nice-to-have.
  - Needs: callback wiring into `models.py` + provider keys.
- [ ] **Per-run token-cost capture** into `usage_events.metadata` (real COGS, not just counts).
  - Trigger: before moving from flat pricing to usage-based/credits.

## Billing
- [ ] **Usage-based / credit pricing** (Stripe meter events).
  - Why later: flat free/pro subscription is live and simpler for v1.
  - Trigger: once per-run cost is measured and flat pricing shows margin risk.

## Rate limiting / cost caps
- [ ] **Redis-backed distributed rate limiting** (current limiter is in-memory, per-instance).
  - Trigger: when running more than one web instance.

## Background work
- [ ] **Offload long `/api/analyze` runs to the worker** with a Redis pub/sub → SSE bridge.
  - Why later: monitors are already off the web process; analyze runs inline but stream fine.
  - Trigger: when analyze runs get long enough to strain the web dyno or hit timeouts.

## Frontend
- [ ] **Org switcher UI** — backend resolves the oldest membership; no multi-org switch yet.
- [ ] **Settings UI** for delete-account / delete-workspace / manage-integrations (endpoints exist).
- [ ] **Usage + upgrade prompt on 429** — surface quota state and nudge to upgrade.

## Security / ops
- [ ] **Lock `ALLOWED_ORIGINS`** to the real domain in prod (env is wired; just set it).
- [ ] **Audit RLS** can't be bypassed from the frontend-direct path; review service-role usage.
- [ ] **Adopt Supabase CLI** (`supabase db push`) for repeatable staging/prod migrations.

## Legal / process (not code)
- [ ] **Execute DPAs** with subprocessors that handle customer data (esp. Maximem Synap).
- [ ] **Legal review** of `TERMS.md` / `PRIVACY.md` templates before launch.
- [ ] **Confirm Synap ownership model** (brains are org-scoped `org_id:slug`) before customer onboarding.

## Action Board (added during P1/P2 build)
- [ ] **HN reply cards link to the story's external URL, not the HN item page** when the
  Composio HN provider is used (native `tools.hn_search` already returns `item?id=` URLs).
  Affects the engagement radar too — it shares the research layer. Fix: prefer the HN item
  URL for `reply` cards, or normalize Composio HN results to the discussion page.
  - Trigger: when HN becomes a primary engagement channel for customers.
- [ ] **Daily card feeder in Redis/Arq mode** — `feed_all_cards` is wired into the in-process
  APScheduler only; the Arq worker path (when `REDIS_URL` set) doesn't feed yet. On-demand
  `POST /api/cards/generate` and the per-company "Auto-refill daily" toggle work in all modes;
  only the *automatic firing* needs the Arq path. The feeder is controlled per company (a toggle
  on the Action Board, stored as `monitors.feed_enabled`), not a global env flag.
- [ ] **Auto-detect replies/karma on posted cards** (the "engaged" state today is set manually
  by the founder). Real auto-detection needs per-platform read APIs (HN Algolia by item id,
  Reddit API by permalink); deep-link posting doesn't give us the new comment id. Wire when
  those read paths exist. The learning loop (posted/engaged -> Synap -> next batch bias) is live.
