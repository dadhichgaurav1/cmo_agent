# StratCMO — Action Board + Handoff Features: Build Plan

Build plan for three features that close the **send-gap** identified in
`StratCMO_GTM_Problem_Map.md` (§7, §9) — without falling into integrations-hell.

Unifying tenet: **handoff, don't integrate.** StratCMO produces the portable artifact;
the human (or the human's own agent) executes it locally. This dodges OAuth-hell *and*
repo-trust-hell, and it preserves the "the human ships" rule the research says we can't
violate (the #7 mindset block).

Three features, in priority order:
1. **Action Board** (#1–#3) — RHS tab, Trello board, swimlanes per platform, deep-link + clipboard.
2. **Landing-page → Claude Code prompt** (#4) — stack-agnostic spec the founder pastes into their own agent.
3. **Build-in-public CLI skill** (#5) — on-device git→post, only text leaves the machine.

---

## Grounding: what already exists (so we reuse, not rebuild)

| Need | Already in codebase | File |
|---|---|---|
| Find threads worth replying to | `synthesize` node emits `Opportunity.thread_url` | `backend/app/graph.py:171` |
| Draft a platform-specific reply | `draft` node emits `Artifact{channel, body}` | `backend/app/graph.py:196` |
| Per-platform voice | `skills.py` resolves humanizer + channel skill into `DRAFT_SYS` | `backend/app/skills.py`, `graph.py:200` |
| Humanize output | `humanize.scrub()` applied to every model result | `backend/app/models.py:74` |
| Search Reddit / HN / X | `capabilities.research()` + Composio runtime binding | `backend/app/capabilities.py:75` |
| Copy + open-in-tab a draft | `RadarCard` copy/open buttons | `frontend/src/App.tsx:50` |
| Recurring background runs | APScheduler + optional arq/redis worker | `backend/app/monitors.py`, `worker.py` |
| Multi-tenant scoping | `org_id` everywhere + RLS; backend scopes manually | `supabase/migrations/0002_rls.sql` |

**The gap is not generation — it's persistence + a board UI + a feeder loop.** Today the
`draft` node generates artifacts then buries them in `runs.summary` JSONB. We promote them
to first-class, stateful **cards**.

> ⚠️ The board UI is a weekend. The suggestion engine (which *specific* thread, what to say,
> in the community's voice — especially Reddit) is the product. Staff accordingly. Phase 2 is
> where the real work and the moat live.

---

# Feature 1 — The Action Board (#1, #2, #3)

A right-hand tab with a Trello-like board. Swimlanes = platforms (Reddit, Hacker News, X,
LinkedIn, Indie Hackers). Cards = specific marketing actions. Two card shapes (see below).
1-click copy, 1-click open-platform, mark-posted. Becomes the **daily-grind feeder**.

## 1.1 The two card shapes (the key correctness detail)

There is no uniform "1-click post." Design around card `kind`:

| `kind` | When | Deep-link behavior | Platforms |
|---|---|---|---|
| **`post`** (new) | Founder publishes a fresh post | True prefill — open compose URL with body pre-filled | X tweet, Reddit self-post, LinkedIn (best-effort) |
| **`reply`** (to existing thread) | Respond to a *specific* thread (highest-value per research) | **No prefill exists** → 1-click copy + 1-click open thread; founder pastes | Reddit comment, HN comment, X reply\*, IH comment |

\* X is the exception: `intent/tweet?in_reply_to=<id>&text=` *does* prefill a reply. Everything
else with `kind=reply` is copy+open only. Do **not** promise "1-click post" globally — promise
**"1-click copy · 1-click open · mark posted."** Underselling here keeps trust; overselling
breaks on the first Reddit reply.

### Deep-link recipes (per platform)
- **X new post**: `https://twitter.com/intent/tweet?text={enc(body)}`
- **X reply**: `https://twitter.com/intent/tweet?in_reply_to={tweet_id}&text={enc(body)}`
- **Reddit self-post**: `https://www.reddit.com/r/{sub}/submit?title={enc(title)}&text={enc(body)}`
- **Reddit comment**: open `target_url`; body to clipboard (no prefill API)
- **Hacker News**: open `target_url` (item page); body to clipboard (no prefill)
- **LinkedIn**: body to clipboard; open `https://www.linkedin.com/feed/?shareActive=true` (prefill unreliable — treat as copy-only)
- **Indie Hackers**: open `target_url`; body to clipboard

Recipes live in one place so the UI stays dumb: `frontend/src/deeplinks.ts` (new).

## 1.2 Data model — new `action_cards` table

New migration `supabase/migrations/0003_action_cards.sql`. Follows the existing
uuid-PK / org_id-scoped / `set_updated_at` trigger / RLS conventions exactly.

```sql
create table public.action_cards (
  id            uuid primary key default gen_random_uuid(),
  org_id        uuid not null references public.organizations(id) on delete cascade,
  run_id        uuid references public.runs(id) on delete set null,  -- provenance
  company_slug  text,                          -- which company this is for
  source        text not null default 'agent', -- agent | cli | manual
  platform      text not null,                 -- reddit | hackernews | x | linkedin | indiehackers
  kind          text not null,                 -- post | reply
  target_url    text,                          -- thread to reply to (null for kind=post)
  target_title  text,                          -- thread title, for the card face
  title         text not null default '',
  body          text not null default '',      -- the draft (already humanized)
  voice         text,                          -- voice profile applied
  state         text not null default 'suggested',
                -- suggested -> drafted -> approved -> posted -> engaged | dismissed
  posted_url    text,                          -- where they posted (loop-back signal)
  posted_at     timestamptz,
  position      int not null default 0,        -- ordering within a swimlane
  metadata      jsonb not null default '{}',
  created_at    timestamptz not null default now(),
  updated_at    timestamptz not null default now()
);
create index action_cards_org_state    on public.action_cards (org_id, state);
create index action_cards_org_company  on public.action_cards (org_id, company_slug, created_at desc);
create trigger trg_action_cards_updated before update on public.action_cards
  for each row execute function public.set_updated_at();

-- RLS (defense-in-depth; backend still scopes by org_id manually)
alter table public.action_cards enable row level security;
create policy action_cards_member_rw on public.action_cards
  for all using (public.is_org_member(org_id)) with check (public.is_org_member(org_id));
```

`db.py` helpers (mirror `list_runs`/`save_monitor` patterns, always `.eq("org_id", org_id)`):
`list_cards(org_id, slug=None)`, `create_card(org_id, card)`, `update_card(org_id, id, patch)`,
`delete_card(org_id, id)`, `bulk_create_cards(org_id, cards)`.

## 1.3 Backend endpoints (`backend/app/main.py`)

All behind `current_context` (resolves `org_id` from the JWT, like every other route).

| Method | Route | Purpose |
|---|---|---|
| `GET`  | `/api/cards?slug=` | List board cards for the org (optionally one company) |
| `POST` | `/api/cards` | Create a card — used by manual add **and** the CLI skill (#5) |
| `PATCH`| `/api/cards/{id}` | Move/edit: state, body, position, posted_url/posted_at |
| `DELETE`| `/api/cards/{id}` | Dismiss a card |
| `POST` | `/api/cards/generate` | **Feeder** — run the suggestion engine now; return a fresh batch (see §1.5) |

Pydantic models in `schemas.py`: `ActionCard`, `ActionCardCreate`, `ActionCardPatch`
(reuse the existing `Artifact` fields; add `platform`, `kind`, `target_url`, `state`).

## 1.4 Frontend (`frontend/src/`)

No drag-drop dependency exists; add **`@dnd-kit/core` + `@dnd-kit/sortable`** (modern, React-18,
light) — only place a new dep is justified. New files:

- `components/ActionBoard.tsx` — the board: columns = platforms, vertical card stacks,
  drag between/within columns (updates `position`/`state` via PATCH).
- `components/ActionCard.tsx` — generalization of `RadarCard` (`App.tsx:50`). Shows
  target-thread title, drafted body, and a button row that **branches on `kind`**:
  - `kind=post` → **[Post on {platform} ↗]** (prefill deep-link) + **[Copy]**
  - `kind=reply` → **[Copy draft]** + **[Open thread ↗]** + **[Mark posted]**
- `deeplinks.ts` — the per-platform recipes from §1.1.
- `api.ts` — add `listCards`, `createCard`, `patchCard`, `deleteCard`, `generateCards`
  (follow the existing bearer-token fetch helpers).

Wire-in: add `{ id: 'actions', label: 'Action Board', tier: 'primary' }` to the `TABS`
array (`App.tsx:184`) and render `{tab === 'actions' && <ActionBoard .../>}` (~`App.tsx:298`).
State: a `cards` array in `App.tsx` hydrated from `GET /api/cards` on load and after `generate`.
Styling: reuse `.card` / `.chip` CSS vars; add `.board`, `.swimlane`, `.swimcard` to `styles.css`.

**Card states** drive the column-internal visual: `suggested` (muted), `drafted` (normal),
`approved` (accent border), `posted` (check + faded), `engaged` (got a reply — highlight).

## 1.5 The suggestion engine + feeder loop (THE PRODUCT — Phase 2)

A new lightweight graph entrypoint `generate_cards(org_id, slug, emit)` in `graph.py`, modeled
on `run_monitor` (`graph.py:317`). For a company it:
1. **Recalls** Synap memory (ICP, positioning, channels) — already available via `recall`.
2. **Searches** each active platform for *fresh* threads matching the ICP via
   `capabilities.research()` (Reddit/HN/X already supported; Composio binds others).
3. **Drafts** a platform-voiced `reply` (or a `post`) per thread using the existing `draft`
   path — `skills.py` voice + `humanize.scrub()`.
4. **Writes** them as `action_cards` (state=`suggested`).

Triggers:
- **On-demand**: `POST /api/cards/generate` (button on the board).
- **Daily feeder**: register `generate_cards` with the existing scheduler
  (`monitors.py:116` / `worker.py` arq cron) at a daily cadence per active company. This is
  the "daily-grind feeder" — the board refills overnight so the founder wakes to a queue.

### Voice profiles (replaces the "no-contractions" rule)
**Do not hardcode a no-contractions ban** — it reads as *more* AI, not less. Instead extend
`skills.py` with per-platform voice packs the research already pointed to:
- **Reddit**: story-first, genuinely helpful, product as "a natural example, not a pitch."
- **Hacker News**: terse, technical, no marketing affect.
- **X**: punchy, one idea.
- **LinkedIn**: build-in-public narrative.

Humanization stays a tunable, applied via the existing `humanize.scrub()` + a voice skill,
not a global rule.

### Loop-back (Phase 4)
When a card → `posted` with a `posted_url`, register a tiny monitor on that URL (reuse
`monitors` infra) to detect replies/karma. On movement, flip the card to `engaged` and feed
the signal into the next `generate_cards` batch ("this kind of thread worked"). Without this,
the board is a prettier todo list; with it, it's the retention engine.

---

# Feature 2 — Landing-page → Claude Code prompt (#4)

The single best-evidenced tactic in the research ("dedicated landing pages for each specific
use case, not a generic homepage"). We supply the PM+marketer judgment; the founder's own
coding agent supplies stack-specific code.

## 2.1 Flow
1. From a strategic opportunity (or a "Generate landing page" action), call
   `POST /api/export/landing-spec` → returns a structured spec:
   `{ use_case, headline, subhead, sections[], proof[], cta, layout_notes, positioning_oneliner }`.
   Generated by a new prompt in `prompts.py` off the company's Synap profile/objective/positioning.
   Render the spec in the UI (reuse the existing `OpenUIPanel` / card patterns).
2. **On a button click only** (lazy, not by default), `POST /api/export/claude-prompt` turns
   that spec into a **single copyable, stack-agnostic Claude Code prompt** with one Copy button.

## 2.2 The prompt contract (what makes it work)
The generated prompt must be **self-contained and adaptive** — it carries the copy, layout
intent, positioning, and acceptance criteria, and opens with:

> "Build a single-use-case landing page in **this repo**. First inspect the repo and adapt to
> whatever stack, framework, routing, and styling conventions you find — make no assumptions
> about React/Next/Tailwind/etc. Here is the page to build and why each section exists: …"

This is the "handoff, don't integrate" tenet in action — no stack assumptions, no code from us.
Behaves like a PM+Marketer, not a template.

## 2.3 Surface
- Backend: 2 endpoints in `main.py`; 2 prompts in `prompts.py`. No new table (stateless;
  optionally cache the latest spec in `runs.summary` or `org_settings`).
- Frontend: a "Landing pages" section/action (reuse opportunity card UI) with a **[Generate
  Claude Code prompt]** button → modal with the prompt + Copy.

---

# Feature 3 — Build-in-public CLI skill (#5)

The web version (connect GitHub, upload repo) is a heavy trust ask. The on-device version falls
straight out of the handoff tenet: **the code never leaves the laptop; only the post you were
going to publish anyway does.**

## 3.1 Shape — a Claude Code skill the founder installs locally
Ship a distributable skill (`stratcmo-buildinpublic/SKILL.md` + a small script) that:
1. Runs `git log` / `git diff` **on the founder's machine** (their own Claude Code drafts it,
   or the script calls our draft endpoint with only a commit *summary* — never code).
2. Produces a build-in-public post (developer-diary voice — the tactic that put `phlsa`
   top-paid on the App Store, per the research notes).
3. `POST /api/cards` with `source='cli'`, `platform` (x/linkedin), `kind='post'`,
   `state='drafted'` → the post lands as a card on the web Action Board for approval.

The only payload over the wire is the marketing text. Safety story in one sentence:
*"Your repo never leaves your laptop; only the post lands in StratCMO."*

Bonus: this makes StratCMO **distribute through the tool the ICP already lives in** — a Claude
Code skill that feeds the web board. We practice the "distribution is the moat" thesis on ourselves.

## 3.2 Auth for the CLI (the one new primitive)
Supabase JWTs expire — bad for a long-lived CLI. Add a minimal personal-access-token concept:
- New table `cli_tokens (id, org_id, user_id, token_hash, label, last_used_at, created_at)`
  (migration `0004_cli_tokens.sql`).
- `POST /api/cli-tokens` (mint, returns the raw token once) + `GET`/`DELETE` (manage) — gated
  by `current_context`. Surface a "Generate CLI token" button in the (deferred) Settings UI;
  for v1 a single endpoint + curl is fine.
- `auth.py`: accept `Authorization: Bearer scmo_<token>` by hashing and looking up `cli_tokens`,
  resolving `org_id`/`user_id` — alongside the existing JWT path. `POST /api/cards` then works
  unchanged for the CLI.

---

# Sequencing & estimates

| Phase | Scope | Rough effort |
|---|---|---|
| **P1 — Board skeleton** | `action_cards` table + `db.py` helpers + CRUD endpoints + `ActionBoard`/`ActionCard` UI + `deeplinks.ts` + dnd-kit. Hydrate from existing `runs.summary` artifacts so the board has content day one. | ~3–4 days |
| **P2 — Suggestion engine** ⭐ | `generate_cards` entrypoint + `/api/cards/generate` + per-platform voice packs + daily scheduler feeder. **The real product.** | ~5–8 days |
| **P3 — Landing → Claude prompt (#4)** | 2 endpoints + 2 prompts + generate-prompt modal. Self-contained; ships independently. | ~2–3 days |
| **P4 — Loop-back** | posted→monitor→`engaged` signal feeding next batch. | ~2–3 days |
| **P5 — CLI skill (#5)** | `cli_tokens` table + mint/auth + the distributable skill + `source='cli'` cards. | ~3–4 days |

Ship order rationale: **P1 then P3 are the quick, independent wins** (board with seeded content;
landing-prompt as a standalone feature). **P2 is the bet** — it's what converts the most-acute
pains (#2 "launched → nothing", #3 "manual grind") from 🟡 to 🟢 and what makes someone keep
paying for "a CMO you don't give equity to." **P4/P5 deepen retention and distribution.**

## What we are deliberately NOT building
- **No full autopost / OAuth posting.** The #7 mindset block means a real slice of the ICP
  *won't* hand over send. Human-in-the-loop approval is a feature, not a v1 limitation. (This
  is why the Action Board ends at deep-link + clipboard and the CLI ends at "lands as a card.")
- **No server-side repo access** for #5. On-device only.
- **No Composio dependency for v1** of any of these — the handoff tenet routes around it.
  (Composio remains the path for a *later* opt-in "let StratCMO actually send" tier.)

## Resolved decisions
1. **Platforms at launch — all five day one**: Reddit, Hacker News, X, LinkedIn, Indie Hackers.
   → P1 ships five swimlanes; P2 must land all five voice packs (Reddit story-first, HN terse/technical,
   X punchy, LinkedIn build-in-public narrative, IH founder-peer). Budget voice-tuning time accordingly —
   this is the larger surface, and getting each voice right is what keeps the drafts from reading as spam.
2. **Board scope — one board per tracked company** (scoped by `company_slug`). The board defaults to the
   active company; `GET /api/cards?slug=` always passes a slug. Matches how `analyze` already works.
   (Schema still supports a global view later via omitting the slug filter.)
3. **#4 — just the prompt** (no live preview for v1). Generate the spec + the copyable, stack-agnostic
   Claude Code prompt. Skip the `OpenUIPanel` preview — it can be a fast-follow if founders ask for it.
