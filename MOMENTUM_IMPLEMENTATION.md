# StratCMO — Momentum: Implementation Plan

Engineering plan to build the feature specified in `MOMENTUM_SPEC.md`. Maps every piece to
real files and existing conventions. **No code is written here — this is the build order.**

> Read `MOMENTUM_SPEC.md` first for the *why*. This doc is the *how*.

---

## 0. Guiding implementation principles (decisions already made)

1. **One scoring hook, server-side.** All points are awarded inside the existing
   `PATCH /api/cards/{id}` handler ([main.py:210](backend/app/main.py#L210)) — it already
   detects `state == "posted"` and stamps `posted_at` ([main.py:214](backend/app/main.py#L214)).
   We add one call after `db.update_card` succeeds. No new posting plumbing, no UI-side scoring.
2. **Edge is lazy-on-read, not scheduler-dependent (v1).** `GET /api/edge` generates today's
   lesson on demand if it doesn't exist (`get_or_create_lesson`). This sidesteps the
   single-instance scheduler caveat called out in [monitors.py:12](backend/app/monitors.py#L12)
   and the redis double-fire guard. Scheduler pre-warm is an optional M3 fast-follow that reuses
   the **exact** `set_feeder` pattern at [main.py:103](backend/app/main.py#L103).
3. **Reuse `db.py` conventions verbatim** — service-role client via `_sb()`, every query
   `.eq("org_id", org_id)`, timestamps via `db._now()` ([db.py:36](backend/app/db.py#L36)).
   Migrations follow `0003_action_cards.sql` exactly (uuid PK, org cascade, `set_updated_at`
   trigger, RLS via `is_org_member`).
4. **Everything behind a flag.** Add `MOMENTUM_ENABLED` to `config.py`
   ([config.py:64](backend/app/config.py#L64) pattern: `_get("MOMENTUM_ENABLED") == "1"`).
   Backend awards are no-ops when off; frontend hides the chip/tab. Ship dark, enable per-cohort.
5. **The PATCH response carries the award** so the frontend can fire the toast without a second
   round-trip: `{ card, momentum?: { awarded, breakdown, total_points, current_streak,
   streak_safe, leveled_up?: {from,to} } }`. `momentum` is present only when points were awarded.

---

## 1. Architecture at a glance

```
 FRONTEND                          BACKEND                         DB
 ─────────                         ────────                        ────
 MomentumChip ──GET /api/momentum──▶ main.py ──▶ db.get_momentum ─▶ momentum_state
 Momentum tab ──GET /api/momentum/events─▶         db.list_events ─▶ momentum_events
 EdgeCard     ──GET /api/edge──────▶ main.py ─▶ lessons.get_or_create ─▶ lessons
              ──POST /api/edge/{id}/read─▶       momentum.award(lesson_read)
 ActionCard   ──PATCH /api/cards/{id}{state:posted}─▶ main.py
                                       └─▶ db.update_card
                                       └─▶ momentum.award(transition)  ◀── THE HOOK
                                              ├─ resolve points (rule table)
                                              ├─ write momentum_events row
                                              ├─ recompute momentum_state (incremental)
                                              └─ maybe persona level-up
                ◀── {card, momentum:{...}} ──┘
 Toast ◀────────────────────────────┘
```

New backend module **`backend/app/momentum.py`** is the brain (rules, multipliers, streak,
persona). New **`backend/app/lessons.py`** + **`backend/app/lessons/*.json`** is the Edge engine.

---

## 2. Backend — phase by phase

### M1 — Score core

#### 2.1 Migration — `supabase/migrations/0005_momentum.sql`
Create `momentum_events` + `momentum_state` exactly as specified in `MOMENTUM_SPEC.md` §4.1–4.2.
Copy the trailing RLS + trigger block from `0003_action_cards.sql` (swap the table name). Add the
two indexes per table. **Acceptance:** `supabase db reset` applies clean; RLS policies present;
`is_org_member` referenced.

#### 2.2 `backend/app/momentum.py` (new) — the rule engine
Pure-ish module, no FastAPI imports. Public surface:

```
BASE_PTS: dict          # kind -> base points (SPEC §4.1)
PERSONA_LADDER: list    # (key, title, ship_threshold, platform_breadth, streak_req, blurb) — SPEC §6.1
FREEZE_MAX = 2
GRACE_HOURS = 4

def award(org_id, user_id, card, transition, *, tz) -> dict | None
    # transition: which kind fired ('card_posted', 'card_reviewed', ...) derived by caller
    # 1. if not config.MOMENTUM_ENABLED or not db.enabled(): return None
    # 2. base = BASE_PTS[transition]; bonus = _courage_bonuses(card, state)
    # 3. mult = _streak_mult(state) * _variety_mult(state, card.platform, today)
    # 4. pts = round((base + bonus) * mult); if pts <= 0: return None
    # 5. db.record_event(...); state2 = _recompute_state(...)   # streak, persona, totals
    # 6. return {awarded, breakdown[], total_points, current_streak, streak_safe, leveled_up?}

def classify_transition(prev_state, patch) -> str | None
    # maps a card state change to an event kind; None if not scoreable
    # 'suggested'->'drafted' w/ body diff => 'card_reviewed'
    # *->'approved' => 'card_approved'
    # *->'posted' => 'card_posted' (+ original/first_on_platform bonuses computed in award)
    # 'posted'->'engaged' => 'card_engaged'

def _recompute_state(org_id, slug, day_key, tz) -> dict
    # incremental: read momentum_state row; update totals, streak (SPEC §5.3 freeze logic),
    # ships counters, platforms_shipped, persona check; upsert; return the row
```

Streak math (SPEC §5.3) lives entirely here: `day_key` in founder tz, freeze auto-spend, grace
window, comeback detection. **Keep it unit-testable** — pass `today`/`tz` in, no `datetime.now()`
buried inside (mirrors how `monitors.now_iso` is centralized).

**Acceptance:** pure functions for streak/multiplier covered by unit tests (§5); `award` returns
`None` cleanly when flag off or `db` disabled (CI has no Supabase).

#### 2.3 `backend/app/db.py` additions (follow existing helper shape)
```
def record_event(org_id, event: dict) -> Optional[dict]      # insert momentum_events
def get_momentum(org_id, slug) -> dict                       # select momentum_state (or zero-row default)
def upsert_momentum_state(org_id, slug, fields) -> dict      # upsert momentum_state
def list_events(org_id, slug, since: str | None, limit=200) -> List[dict]
```
All `.eq("org_id", org_id)`, all guarded by `if not enabled(): return ...` like existing helpers.

#### 2.4 `backend/app/schemas.py` additions
`MomentumState`, `MomentumEvent`, `MomentumAward` (the PATCH-response sub-object). Place near
`ActionCard*` models. These are response models — keep them permissive (mirror existing style).

#### 2.5 `backend/app/main.py` edits
- **Hook the award into the existing PATCH** ([main.py:210-219](backend/app/main.py#L210-L219)).
  Read the card's `prev_state` *before* `db.update_card` (one extra `db.list_cards`-style read, or
  return prev from `update_card`), then:
  ```
  updated = db.update_card(org_id, card_id, patch)
  ...
  kind = momentum.classify_transition(prev_state, patch)
  award = momentum.award(org_id, ctx.get("user_id"), updated, kind, tz=_org_tz(org_id)) if kind else None
  return {"card": updated, **({"momentum": award} if award else {})}
  ```
- **New read endpoints** (all `Depends(current_context)`, mirror `cards_list`):
  - `GET /api/momentum?slug=` → `{ "momentum": db.get_momentum(org_id, slug) }`
  - `GET /api/momentum/events?slug=&since=` → `{ "events": db.list_events(...) }`
- `_org_tz(org_id)` helper: read tz from `organizations`/`org_settings`
  ([db.get_org_settings](backend/app/db.py#L285)); default `UTC`. (Timezone column added in 2.6.)

#### 2.6 Timezone storage (small, do it in M1 — streaks depend on it)
Add `timezone text default 'UTC'` to `organizations` in `0005_momentum.sql`; set it from the
browser (`Intl.DateTimeFormat().resolvedOptions().timeZone`) on first authed load via a tiny
`PATCH /api/org/timezone` (or fold into an existing settings write). Cheap, but the core mechanic
is wrong without it.

---

### M2 — Persona + streak polish (mostly frontend + tuning)
- Persona ladder thresholds already in `momentum.py` (2.2). M2 = the **level-up payload**:
  `_recompute_state` already returns `leveled_up`; ensure `award` surfaces it so the frontend can
  fire the interstitial. No new endpoints.
- Freezes, calendar data, weekly rollup all derive from `momentum_events` via the existing
  `/api/momentum/events` — no backend changes beyond ensuring `day_key` + `freezes_left` are in
  the state payload.

---

### M3 — The Daily Edge ⭐

#### 2.7 Migration `supabase/migrations/0006_lessons.sql`
`lessons` table per SPEC §4.3. Same conventions + RLS.

#### 2.8 Principle library — `backend/app/lessons/*.json` (mirrors `backend/app/skills/*.json`)
~30–40 small JSON objects (SPEC §7.2 schema: `key, bucket, one_liner, applies_when[],
teach_prompt, fix_pattern`). Loaded by a registry loader mirroring `skills.py`. **Author content
incrementally** — ship M3 with ~12 high-value principles (Cialdini 7 + Field-of-Dreams,
curse-of-knowledge, fewer-problems, channel-trust, build-in-public), expand later.

#### 2.9 `backend/app/lessons.py` (new) — selection + generation
```
def load_principles() -> list                              # read lessons/*.json once, cache
def get_or_create_lesson(org_id, slug, day_key, tz) -> dict
    # 1. if a lessons row exists for (org,slug,day_key) -> return it
    # 2. recent_activity = db.list_events(org, slug, since=3d) + cards touched
    # 3. principle = _select(recent_activity, profile, recently_taught)   # SPEC §7.3 scoring
    #    - require a real tie-back (specific card + what they did); else positioning-tied;
    #      else return None (SKIP THE DAY — no filler)
    # 4. lesson = _generate(principle, tie_back_card, profile)  # LLM via models.py + humanize.scrub
    # 5. cta_card_id = best on-board draft the principle applies to
    # 6. db row (state=unread); return it
```
Generation reuses the existing model call path + `humanize.scrub()`
([models.py:74](backend/app/models.py#L74)) and pulls the company profile from Synap memory via
the same `recall` path `generate_cards` uses ([graph.py:399](backend/app/graph.py#L399)).
New prompt(s) in `prompts.py` (one per `teach_prompt`, or a shared template parameterized by
principle). `db.py`: `get_lesson`, `create_lesson`, `mark_lesson`, `latest_lessons`.

#### 2.10 `main.py` Edge endpoints
- `GET /api/edge?slug=` → `lessons.get_or_create_lesson(...)` (may return `null` = skip day).
- `POST /api/edge/{id}/read` → `db.mark_lesson(state='read')` + `momentum.award(... 'lesson_read')`
  (capped once/day inside `award`).
- `lesson_applied` (+10): when a card whose id == some lesson's `cta_card_id` hits `posted`, the
  PATCH hook also fires this. Implement as a lookup in `award` (cheap: `db` query
  `lessons where cta_card_id=card_id and state!='applied'`), then `mark_lesson('applied')`.

#### 2.11 Scheduler pre-warm (optional, after lazy works)
Register an edge feeder alongside the card feeder: add `set_edge_feeder` in `monitors.py` mirroring
`set_feeder`/`_fire_feeder` ([monitors.py:113](backend/app/monitors.py#L113)), wire in
`main.py` startup next to [main.py:103](backend/app/main.py#L103), gated by a config flag and the
same redis double-fire guard. Lazy-on-read remains the fallback so correctness never depends on it.

---

### M4 — Loop-back bonus
- `card_engaged` (+10) is already classifiable by `classify_transition` (`posted->engaged`). It
  fires automatically once `ACTION_BOARD_PLAN.md` P4 flips cards to `engaged`. No new code beyond
  confirming the transition is reachable and excluded from streak/persona gating (SPEC §5.4).

---

## 3. Frontend — phase by phase

### M1
- **`frontend/src/api.ts`** — add (mirror `patchCard`/`listCards` at
  [api.ts:109-122](frontend/src/api.ts#L109-L122)):
  `getMomentum(url)`, `getMomentumEvents(url, since?)`. **Modify `patchCard`** callers to read the
  optional `momentum` field from the response (the function already returns parsed JSON).
- **`frontend/src/components/MomentumChip.tsx`** (new) — compact header chip (SPEC §8.1).
  Props: momentum state. Renders streak flame + points + persona; hollow flame + hover nudge when
  no ship today; unread-Edge dot. Click → `setTab('momentum')`.
- **`frontend/src/App.tsx`**:
  - Add `{ id: 'momentum', label: 'Momentum', tier: 'primary' }` to `TABS`
    ([App.tsx:185](frontend/src/App.tsx#L185)).
  - Render `<MomentumChip>` inside `<header className="top">`
    ([App.tsx:247](frontend/src/App.tsx#L247)).
  - Add `momentum` state + hydrate from `getMomentum` on load and after any `patchCard`.
  - `{tab === 'momentum' && <Momentum .../>}` near [App.tsx:296](frontend/src/App.tsx#L296).
- **Toast on send (SPEC §8.3)** — the highest-value pixels. Wherever a card is marked posted
  (the `patchCard(id,{state:'posted'})` call in the Action Board), if the response has
  `momentum`, show a toast with the breakdown. Add a lightweight toast util (no dep) +
  `.toast` CSS. Also update `momentum` state from the response so the chip animates instantly.
- **`frontend/src/types.ts`** — add `Momentum`, `MomentumEvent`, `MomentumAward` types
  (mirror existing exported types).
- **`frontend/src/styles.css`** — `.streak`, `.persona`, `.toast`, `.chip-momentum` reusing the
  existing CSS vars / `.card` / `.chip` styles.

### M2
- **`frontend/src/components/Momentum.tsx`** (new) — the full page (SPEC §8.2): persona card +
  progress bar, streak calendar (from `/api/momentum/events`), week breakdown, history.
- **Level-up interstitial** — full-width dismissible overlay fired when a `patchCard` response
  has `momentum.leveled_up` (SPEC §8.4).
- **Tone skin** (Ops vs Hype) — a class toggle on the Momentum container; default inferred from
  company category, overridable. Pure CSS/string differences.
- **Empty/day-one state** (SPEC §8.5) inside `Momentum.tsx`.

### M3
- **`frontend/src/components/EdgeCard.tsx`** (new) — renders today's lesson; "mark read" →
  `POST /api/edge/{id}/read`; CTA button deep-links to the `cta_card_id` on the Action Board.
  Lives at the top of `Momentum.tsx` and optionally as a dismissible banner elsewhere.
- **`api.ts`** — `getEdge(url)`, `readEdge(id)`.
- Handle the **skip-day** case (`getEdge` returns null) gracefully — show nothing, no error.

---

## 4. Config & flags
- `backend/app/config.py`: `MOMENTUM_ENABLED = _get("MOMENTUM_ENABLED") == "1"`;
  `EDGE_FEEDER_ENABLED` (M3 scheduler, default off).
- `render.yaml`: add the env vars (default `0`).
- Frontend: chip/tab render only when `getMomentum` returns a non-null state **and** a build-time
  or runtime flag is on (simplest: backend returns `{momentum: null}` when disabled → frontend
  hides). Single source of truth = backend flag.

---

## 5. Testing plan
- **Unit (backend, no Supabase needed)** — `momentum.py` pure functions:
  - points resolution per transition incl. courage bonuses,
  - multiplier math (streak/variety/comeback/cold-start) with known inputs,
  - streak transitions: consecutive days, gap+freeze, freeze exhaustion+reset, grace window,
    tz boundaries (the bug-prone part),
  - persona level-up thresholds (volume + breadth + streak gates).
- **Unit — `lessons._select`**: given fabricated events/cards, picks the right principle, enforces
  21-day no-repeat, returns None when no tie-back clears the bar (the skip rule).
- **Integration** — PATCH a card `→posted` end to end: event row written, state recomputed,
  response carries `momentum`, idempotent on re-PATCH of an already-posted card (no double award).
- **Anti-gaming** (SPEC §5.5): no points for no-op `suggested→drafted` (no body diff), un-URL'd
  ship daily cap, lesson_read once/day, no points for dismiss.
- **Frontend** — toast fires from a mocked `momentum` response; chip hides when `momentum` null.
- **Manual smoke** — flag on in a dev org, run through: review → approve → post (see toast) →
  next-day ship (streak +1) → first-on-new-platform (bravery toast) → level-up interstitial.

---

## 6. Idempotency & correctness watch-list
1. **Double-award on re-PATCH.** `classify_transition` must return `None` when `prev_state ==`
   new state (e.g. PATCHing a `posted` card again). Award only on an actual forward transition.
2. **Concurrent PATCHes** to two cards in the same day → `_recompute_state` must be a read-modify-
   write that tolerates races (recompute from `momentum_events` truth rather than blind increment
   where feasible; the cached `momentum_state` is an optimization, the events table is truth).
3. **Timezone** — all streak math on `day_key` computed from the org tz; never compare raw
   `created_at`. Default UTC if unknown but capture browser tz early (2.6).
4. **`db` disabled / flag off** — every new helper and `award` returns a safe default; the app
   must run identically with Momentum off (CI runs without Supabase).
5. **Edge skip is normal, not an error** — `GET /api/edge` returning null is a valid daily state.

---

## 7. Build order checklist (dependency-ordered)

**M1 — Score core (the bet's foundation)**
1. `0005_momentum.sql` (tables + RLS + org `timezone` column)
2. `momentum.py`: `BASE_PTS`, `PERSONA_LADDER`, `classify_transition`, multipliers, streak,
   `_recompute_state`, `award` (+ unit tests)
3. `db.py`: `record_event`, `get_momentum`, `upsert_momentum_state`, `list_events`
4. `schemas.py`: momentum response models
5. `config.py` + `render.yaml`: `MOMENTUM_ENABLED`
6. `main.py`: hook `award` into PATCH; `GET /api/momentum`; `GET /api/momentum/events`;
   `_org_tz`; tz capture endpoint
7. `api.ts` + `types.ts`: getters + read `momentum` from `patchCard`
8. `MomentumChip.tsx` + header wire-in + `momentum` state in `App.tsx`
9. Toast on send + `styles.css`
10. Integration + anti-gaming tests

**M2 — Persona + streak polish**
11. `Momentum.tsx` page (persona, calendar, week, history)
12. Level-up interstitial
13. Tone skins + empty/day-one state

**M3 — The Daily Edge** ⭐
14. `0006_lessons.sql`
15. `lessons/*.json` (~12 principles to start) + loader
16. `lessons.py`: select + generate; `prompts.py` teach prompt; `db.py` lesson helpers
17. `main.py`: `GET /api/edge`, `POST /api/edge/{id}/read`, `lesson_applied` in PATCH hook
18. `EdgeCard.tsx` + `api.ts` getters + Momentum page integration
19. (optional) scheduler pre-warm via `set_edge_feeder`

**M4 — Loop-back bonus**
20. Confirm `posted→engaged` award path once Action Board P4 lands

---

## 8. Effort estimate

| Phase | Backend | Frontend | Total |
|---|---|---|---|
| M1 Score core | 3–4 d | 2 d | **~1 wk** |
| M2 Persona/polish | 0.5 d | 2–3 d | **~3 d** |
| M3 Daily Edge ⭐ | 4–5 d (content + selection is the cost) | 1–2 d | **~1 wk** |
| M4 Loop-back | 0.5 d | 0.5 d | **~1 d** |

M1 is a self-contained, shippable activation/retention win on top of the existing Action Board
with **no new AI**. M3 is the bet and the moat — staff the principle library + selection quality,
not the UI. Ship M1→M2 behind the flag, validate ship-rate lift (SPEC §10 north star) before
investing in M3.

---

## 9. Open decisions to lock before coding (from SPEC §12)
1. Ops-vs-Hype skin: infer from category, or ask once in onboarding? (affects M2 onboarding)
2. Un-URL'd self-reported ship cap value (default 10/day in `momentum.py`)
3. Tie-back confidence bar for skipping the Edge (default: require a specific `card_id` match)
4. Secondary "engagement streak" alongside the ship-only flame? (affects state payload + chip)

These don't block M1 — they're M2/M3 knobs. M1 can start immediately on the checklist above.
