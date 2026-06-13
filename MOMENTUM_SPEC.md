# StratCMO — Momentum: Spec

> A solo founder gets no dopamine and no witness. No one congratulates them, no one
> trusts them, and the one act that actually moves their company — *being seen, hitting
> send* — is the exact act they're most afraid of (`StratCMO_GTM_Problem_Map.md` §7, §9).
>
> **Momentum** is the part of StratCMO that watches the founder do the scary work, counts
> it, congratulates them, teaches them *why it worked*, and pulls them back to do it again
> tomorrow. It is two halves of one loop:
>
> 1. **The Score** — a streak + points + an evolving operator persona, in the header, that
>    rewards *shipping* above all else.
> 2. **The Daily Edge** — one psychological/persuasion principle a day, tailored to their
>    business and tied to something they actually did, that ends by pointing at the next
>    scary action.
>
> **Primary goal: activation.** Not "log in and feel good." *Hit send on the thing you've
> been avoiding.* Every design decision below is graded against that one verb.

---

## 0. The one-paragraph pitch (for the founder)

> "You did the hard, lonely thing — you put yourself out there. I counted it. Here's your
> streak, here's what you've shipped this week, and here's the one piece of marketing
> psychology that explains why your last post landed (or didn't). Now there's one more
> draft sitting on your board. Want to keep the streak alive?"

---

## 1. Why this is one feature, not two

Both ideas run on the **same substrate and the same loop**:

```
            ┌──────────────────────────────────────────────┐
            │                                              │
   you act  │   Action Board       The Score     The Edge  │
 (ship!) ───┼──▶ card → posted ──▶ +points,    ──▶ "here's │
            │                      streak,         why it   │
            │                      persona         worked"  │
            │         ▲                                │     │
            │         └──── "one more to keep ◀────────┘     │
            │               the streak" / "apply this        │
            │               to the draft on your board"      │
            └──────────────────────────────────────────────┘
```

- The **Score** needs an event log of what the founder did.
- The **Edge** needs the *same* log to find a teachable moment ("the cold email you sent
  Tuesday").
- The Edge's call-to-action drives the next **Score**-able act.

Build the event log once; both halves get cheap. The Edge without the Score is a newsletter
you mute. The Score without the Edge is a vanity bar a serious founder ignores. Together they
are an **identity-transformation engine**: *engineer who hates marketing → founder who's
learning to market and proud of the proof.* That identity shift is the §7 mindset block, which
the research says is 80% of the battle and currently 🟡 in our fit-scoring.

---

## 2. Goals & non-goals

**Goals**
1. **Activation** — increase the rate at which `action_cards` move to `posted` (the send), and
   the rate at which the *scariest* sends happen (original posts, first-time-on-a-platform).
2. **Retention via streak** — bring the founder back daily; a streak they don't want to break.
3. **Make the founder feel witnessed** — the cofounder-who-trusts-you emotional payload (§10).
4. **Teach marketing** — convert advice-fatigue (§9) into tailored, applied judgment (§1).

**Non-goals (v1)**
- ❌ Measuring marketing *outcomes* (revenue, true reach). We measure **inputs** — they're
  cheap, honest-enough, and under the founder's control. (One free outcome signal, `engaged`,
  is a *bonus*, §5.4 — never the core.)
- ❌ Leaderboards / social comparison. The ICP is a solo founder; comparison to strangers
  demotivates and invites gaming. The only person you compete with is past-you.
- ❌ Punishing inactivity with guilt. A broken streak is acknowledged gently, never shamed
  (anti-pattern for an already-discouraged founder). Streak **freezes**, not streak death.
- ❌ Cute infantilizing tone by default. Tone is persona-calibrated (§6.4); a B2B SaaS
  founder gets an ops dashboard, not a cartoon.

---

## 3. The activation thesis (read before the scoring)

The user's instinct is right: **measure inputs, not outcomes** — outcomes are slow, noisy, and
demoralizing to a pre-traction founder ("$0 revenue" is not a number you gamify). But "input"
is not flat. The whole spec hangs on one move:

> **Weight inputs by courage.** The point value of an action ∝ how much it *exposes the founder*.
> Reading a lesson is safe (1pt). Editing a draft is safe-ish (3pt). **Hitting send is the
> scary one we actually want (20–40pt).** Posting something *original* where your name is on it
> beats replying in someone else's thread.

So the Score is technically an input-counter (easy to build) but it is *tuned* to drag the
founder toward the single act the research says is the unlock and the fear: **being seen.**
That's the "spicier with your inputs" the user asked for — the spice is the weighting, the
multipliers, the persona gates, and the streak rule, all pointed at *send*.

---

## 4. Data model

Two new tables, following the exact conventions in `supabase/migrations/0003_action_cards.sql`
(uuid PK, `org_id` FK + cascade, `set_updated_at` trigger, RLS via `is_org_member`). New
migration `supabase/migrations/0005_momentum.sql`.

### 4.1 `momentum_events` — the substrate (the activity log)

Append-only log of scoreable acts. Written by the backend whenever a card changes state or a
lesson is read. This is the source of truth for *both* halves.

```sql
create table public.momentum_events (
  id            uuid primary key default gen_random_uuid(),
  org_id        uuid not null references public.organizations(id) on delete cascade,
  user_id       uuid,                              -- who did it (for persona/per-founder view)
  company_slug  text,                              -- which company
  kind          text not null,                     -- see EVENT TYPES below
  card_id       uuid references public.action_cards(id) on delete set null,  -- provenance
  platform      text,                              -- reddit | hackernews | x | linkedin | indiehackers
  points        int not null default 0,            -- resolved at write time (rules in §5)
  multiplier    numeric not null default 1.0,      -- streak/variety/courage multiplier applied
  day_key       date not null,                     -- local-day bucket for streak math (§5.3)
  metadata      jsonb not null default '{}',       -- {first_on_platform:true, kind:'post', ...}
  created_at    timestamptz not null default now()
);
create index momentum_events_org_day   on public.momentum_events (org_id, day_key);
create index momentum_events_org_user  on public.momentum_events (org_id, user_id, created_at desc);
```

**EVENT TYPES (`kind`)** — only these are scoreable:

| kind | Fired when | Base pts | Notes |
|---|---|---|---|
| `lesson_read` | Founder opens/finishes the Daily Edge | 1 | once/day, capped |
| `card_reviewed` | Card moves `suggested→drafted` *with an edit* | 3 | proves engagement, not autopilot |
| `card_approved` | Card moves `→approved` | 5 | committed but not yet brave |
| **`card_posted`** | **Card moves `→posted` (THE SEND)** | **20** | the activation target |
| `card_posted_original` | …and `kind='post'` (own voice, name on it) | **+15** | bravery bonus (total 35) |
| `first_on_platform` | First-ever `posted` on a platform | **+25** | conquering a new fear |
| `card_engaged` | `posted→engaged` (got a reply/karma, §5.4) | 10 | *bonus*, outcome-ish, optional |
| `lesson_applied` | Lesson CTA → a card it pointed at gets posted | +10 | closes the teach→ship loop |

> Design note: there is **no points for `dismissed`** and **no points for merely opening the
> app**. We pay for forward motion, and we pay the most for the send. Reviewing/approving earns
> a little so the funnel isn't all-or-nothing, but the math is lopsided toward `posted` on
> purpose — a week of "approved but never sent" should feel visibly worse than one real send.

### 4.2 `momentum_state` — the cached rollup (one row per org/company)

Denormalized read-model so the header chip is a single fast `SELECT` (no aggregation on every
page load). Recomputed on each event write (cheap; it's incremental).

```sql
create table public.momentum_state (
  org_id            uuid not null references public.organizations(id) on delete cascade,
  company_slug      text not null default '',
  total_points      int not null default 0,
  current_streak    int not null default 0,        -- consecutive active days (§5.3)
  longest_streak    int not null default 0,
  freezes_left      int not null default 2,         -- streak-saver budget (§5.3)
  last_active_day   date,
  persona_key       text not null default 'lurker', -- §6
  persona_progress  int not null default 0,         -- pts toward next persona tier
  ships_total       int not null default 0,         -- count of card_posted (the headline #)
  ships_this_week   int not null default 0,
  platforms_shipped text[] not null default '{}',   -- distinct platforms ever shipped on
  updated_at        timestamptz not null default now(),
  primary key (org_id, company_slug)
);
```

### 4.3 `lessons` — the Daily Edge content + delivery log

```sql
create table public.lessons (
  id            uuid primary key default gen_random_uuid(),
  org_id        uuid not null references public.organizations(id) on delete cascade,
  company_slug  text,
  day_key       date not null,
  principle_key text not null,                      -- curriculum id, e.g. 'social_proof' (§7.2)
  title         text not null,                      -- "Why your 12 likes actually hurt you"
  body          text not null,                      -- the tailored 60-sec read (markdown)
  tie_back      jsonb not null default '{}',        -- {card_id, what_you_did, quote}
  cta_card_id   uuid references public.action_cards(id) on delete set null,  -- "apply it here"
  cta_label     text,                               -- "Sharpen the draft waiting on your board →"
  state         text not null default 'unread',     -- unread | read | applied
  created_at    timestamptz not null default now(),
  updated_at    timestamptz not null default now()
);
create index lessons_org_day on public.lessons (org_id, day_key desc);
```

`db.py` helpers (mirror `list_cards`/`update_card`, always `.eq("org_id", org_id)`):
`record_event`, `get_momentum(org_id, slug)`, `list_events(org_id, slug, since)`,
`get_or_create_lesson(org_id, slug, day_key)`, `mark_lesson(org_id, id, state)`.

---

## 5. The Score — rules

### 5.1 Resolving points (where it happens)

Points are resolved **server-side at the moment of the triggering state change**, not in the
UI (UI can't be trusted, and we want one source of truth). Concretely: in the existing
`PATCH /api/cards/{id}` handler (`main.py`, §1.3 of `ACTION_BOARD_PLAN.md`), after a successful
state transition, call `momentum.award(org_id, user_id, card, transition)`. New module
`backend/app/momentum.py` owns the rule table, the multiplier math, the streak update, and the
persona check — one place, like `humanize.scrub()` is one place.

```
award(transition) =>
  base   = BASE_PTS[transition.kind]                 # §4.1 table
  bonus  = courage_bonuses(card)                     # original / first_on_platform
  mult   = streak_mult(state) * variety_mult(today)  # §5.2
  pts    = round((base + bonus) * mult)
  write momentum_events row; recompute momentum_state; maybe level_up persona
```

### 5.2 Multipliers (the spice)

| Multiplier | Rule | Cap | Why |
|---|---|---|---|
| **Streak** | +5% per current-streak day | ×2.0 (at 20-day streak) | compounds the habit; losing it hurts more the longer it is |
| **Variety** | ×1.5 if you ship on a platform you haven't shipped on *today* | per-day | pushes multi-channel, prevents one-platform grind |
| **Comeback** | ×1.5 on first ship after a freeze/gap | once per return | re-onboards the discouraged founder warmly |
| **Cold-start** | ×2.0 for the very first 3 ships ever | first 3 | front-loads the dopamine when it matters most |

All multipliers are **transparent** — the post-send toast spells out the math (§8.3). Hidden
scoring breeds distrust in a skeptical ICP; shown scoring teaches the founder what we value
(shipping, variety, consistency).

### 5.3 The streak (the retention engine) — define "active day" carefully

> **An "active day" = a day with at least one `card_posted`.** Reading a lesson or approving a
> card does **not** keep the streak — only *shipping* does.

This is deliberate and central to the activation goal. If reading the Edge kept the streak, the
founder would optimize for the safe act. The streak is a **ship streak.** (We *show* lesson-read
days on the calendar in a different color so it's not invisible, but they don't count for the
flame.)

- **Day boundary**: `day_key` is computed in the founder's local timezone (stored on the org;
  default from browser on first load). Streak math is all on `day_key`, never raw timestamps.
- **Freeze, don't break**: everyone gets **2 freezes**, auto-applied. Miss a day → a freeze is
  silently spent, streak preserved, founder told gently on next visit ("Used a freeze to keep
  your 9-day streak 🙏 — 1 left"). Freezes refill +1 per 7 active days (cap 2). Only when
  freezes hit 0 *and* a day is missed does the streak reset — and even then the copy is
  encouragement, never a tombstone (§2 non-goal).
- **Grace window**: a ship before, say, 4am local counts for the previous day (founders work
  late). Tunable constant.

### 5.4 The one outcome signal we allow (bonus only)

`ACTION_BOARD_PLAN.md` P4 loop-back already flips `posted→engaged` when a posted URL gets a
reply/karma. When that fires we award `card_engaged` (+10) and surface a *separate, quieter*
celebration ("Someone replied to your HN comment — that's real traction"). It is explicitly
**not** part of the streak or persona gating, because it's outside the founder's control and we
refuse to make the streak depend on luck. It's a gift when it lands, never a stick.

### 5.5 Anti-gaming (a skeptical ICP *will* test this)

- **Reviewed-with-edit requires a real diff** — `suggested→drafted` only scores if the body
  actually changed (cheap server check), else 0. No points for clicking through.
- **`card_posted` requires a `posted_url` OR an explicit "Mark posted" confirm** — and we
  *trust* the founder here (it's self-report; they're only cheating themselves, and the ICP
  hates being treated like a liar). But we cap **un-URL'd self-reported ships at N/day** (e.g.
  10) so a bored founder can't smash the button for points.
- **Lesson points are once/day**, period.
- **No points for dismiss/delete** — you can't farm by churning cards.
- We log enough in `momentum_events` to spot abuse later, but v1 stays trust-first; over-policing
  a solo founder's own dashboard is self-defeating.

---

## 6. The Persona (identity made visible)

The persona is the **emotional core** — the "we trust you / you're becoming someone" payload.
It's a single evolving archetype (not a stat sheet) that levels as `ships_total` and breadth
grow. It directly narrates the §7 identity shift.

### 6.1 The ladder

| Tier | Key | Unlock (ships / breadth) | The story it tells |
|---|---|---|---|
| 0 | `lurker` | start | "You've been reading. Time to be read." |
| 1 | `first_blood` | 1 ship | "You hit send. That's more than most ever do." |
| 2 | `poster` | 5 ships | "You're showing up. The grind has begun." |
| 3 | `regular` | 15 ships, 2+ platforms | "People are starting to see your name around." |
| 4 | `operator` | 40 ships, 3+ platforms, 10-day streak | "You market now. This is a muscle, and it's growing." |
| 5 | `distribution_machine` | 100 ships, 4+ platforms, 20-day streak | "Distribution is your moat — and you built it." (§8 thesis, verbatim) |

Thresholds are constants in `momentum.py`, easy to retune from early data. Each level-up is a
**moment** — full-card celebration (§8.4), new persona art/title in the header, and a one-line
note on *what changed in them*, not just a badge.

### 6.2 Persona ↔ activation

Persona gates require **breadth and streak, not just volume**, so the only way up is to keep
shipping *and* conquer new platforms (each `first_on_platform` is a fear faced). The ladder is
literally a map of the §7 mindset journey from "I'm an engineer, not a salesperson" → "I market
now."

### 6.3 Persona art

Lightweight (emoji/SVG glyph + color), no heavy illustration dependency for v1. The *words*
carry the weight; art is a fast-follow.

### 6.4 Tone calibration

One toggle (or inferred from the company category in the Synap profile): **"Ops" vs "Hype."**
- *Ops* (B2B/serious): "12 ships · 9-day streak · Operator." Dashboard energy.
- *Hype* (indie/consumer): "🔥 9 · LV4 Operator" + confetti. Game energy.
Same data, different skin. Default inferred, founder can flip in settings.

---

## 7. The Daily Edge — the lesson engine

### 7.1 The non-negotiable: it must be tied to *their own work*

A generic "Today's bias: social proof" is a newsletter they mute in a week. The entire
defensibility is:

> "Remember the cold email you drafted Tuesday? Its second line triggers the **curse of
> knowledge** — you wrote it for someone who already knows what you know. Here's the 60-second
> fix, and there's a draft on your board with the same problem. Want to sharpen it?"

No external newsletter can write that sentence — it needs the founder's `momentum_events`,
their drafts, their platforms, their positioning. **Ship only the tied version.** If on a given
day there's no real teachable moment in their work, fall back to a principle tied to their
*positioning/ICP* (still from their Synap profile), never to a context-free listicle entry.

### 7.2 The curriculum (so it doesn't repeat or feel like a listicle)

A finite, ordered well of ~30–40 **principles**, each a small content object in
`backend/app/lessons/` (mirrors how `skills/*.json` works today). Buckets:

- **Persuasion** (Cialdini): reciprocity, social proof, authority, scarcity, commitment,
  liking, unity.
- **Cognitive biases that wreck founder copy**: curse of knowledge, framing, anchoring,
  loss aversion, peak-end, von Restorff (distinctiveness), Zeigarnik (open loops).
- **Distribution/GTM psychology** (straight from the problem map): Field-of-Dreams fallacy
  (§2), "fewer problems not more features" (§5), build-in-public vulnerability (§7),
  channel-trust (§4), the Mom Test framing (§6).

Each principle object:
```json
{
  "key": "curse_of_knowledge",
  "bucket": "bias",
  "one_liner": "You write for people who already know what you know.",
  "applies_when": ["draft body uses jargon", "no concrete before/after", "kind=post"],
  "teach_prompt": "…LLM prompt that takes {their_card_body, their_profile} → tailored 60-sec lesson…",
  "fix_pattern": "Rewrite the first line as the reader's problem in their words."
}
```

### 7.3 Selection algorithm (event-driven, daily *ceiling* not daily *quota*)

Run once/day per active company (piggyback the existing daily `generate_cards` scheduler —
`monitors.py` / `worker.py` cron):

```
1. Look at the last 1–3 days of momentum_events + the cards touched.
2. Score each not-recently-taught principle by `applies_when` match against that activity.
3. Pick the highest-scoring principle with a real tie-back (a specific card + what they did).
   - If none clears the bar → pick a positioning-tied principle from the Synap profile.
   - If still nothing fresh (rare) → SKIP the day. No filler. (A skipped day is better than
     a generic day that trains the founder to ignore the panel.)
4. Generate the tailored lesson via `teach_prompt`, run through humanize.scrub().
5. Set cta_card_id = the best draft currently on the board the lesson applies to.
6. Write a `lessons` row (state=unread). Don't repeat a principle within ~21 days.
```

> **Cadence rule:** at most one Edge per day (the ceiling). Driven by real teachable moments,
> not a quota. Better to skip than to bore. This is the opposite of a content treadmill.

### 7.4 The Edge is a Trojan horse for the send

Every lesson ends with a CTA that points at a **real card on their board** (`cta_card_id`) and
uses send-language: *"There's a LinkedIn draft with exactly this problem — fix the first line
and ship it →."* Reading teaches; the CTA activates; posting that card fires `lesson_applied`
(+10) and `card_posted` (+20). The lesson literally closes its own loop into a ship.

---

## 8. UI surfaces

### 8.1 The header chip (the hook — `App.tsx` top bar)

Compact, always visible, pulls into the page. Sits in the header near the existing tab nav.

```
Hype skin:     🔥 9   ·  ⚡ 1,240  ·  LV4 Operator        ← click → Momentum page
Ops skin:      9-day streak · 12 ships · Operator
```

- The **flame + number** is the streak (the loss-aversion hook — they don't want to break it).
- On a day with no ship yet, the flame is **hollow/grey** with a quiet nudge on hover:
  *"Ship one thing to keep your streak."* (the daily pull, the §3 activation drag).
- A small dot on the chip when there's an unread Daily Edge.

### 8.2 The Momentum page (new primary tab, `TABS` in `App.tsx:184`)

`components/Momentum.tsx`. Sections, top to bottom:

```
┌─ MOMENTUM ───────────────────────────────────────────────┐
│  [Persona card]   Operator · LV4                          │
│   🜂 glyph        "You market now. This is a muscle."     │
│                   ▓▓▓▓▓▓▓░░░  28/40 ships to next level   │
│                                                           │
│  🔥 9-day streak   ·  2 freezes   ·  ⚡1,240 pts          │
│  ┌ Streak calendar (last 30 days) ───────────────────┐   │
│  │ ▢▣▣▣◍▣▣▣▣  ▣ = shipped  ◍ = freeze  · = lesson    │   │
│  └────────────────────────────────────────────────────┘  │
│                                                           │
│  ── TODAY'S EDGE ──────────────────────────────────────  │
│  "Why your 12 likes actually hurt you"                    │
│  [tied to: your X post from Tuesday]                      │
│  …60-sec read…                                            │
│  [ Sharpen the draft on your board and ship it → ]        │
│                                                           │
│  ── THIS WEEK ─────────────────────────────────────────  │
│  4 ships · 3 platforms · 2 lessons applied                │
│  Breakdown: Reddit ▣▣ · HN ▣ · LinkedIn ▣                 │
│                                                           │
│  ── HISTORY ───────────────────────────────────────────  │
│  past Edges (re-readable) + recent ships timeline         │
└───────────────────────────────────────────────────────────┘
```

The **proof-of-work framing** ("4 ships · 3 platforms this week") is deliberate — it's the
artifact a founder can screenshot for an investor/cofounder and the antidote to "no one trusts
me." (Optional v2: a shareable "30 days of momentum" card.)

### 8.3 The post-send toast (the dopamine hit — *this is the moment*)

The most important pixels in the feature. Fires the instant a card → `posted`. Must be
immediate, specific, and spell out the math (transparency, §5.2):

```
   ✦ Shipped to Reddit.  +30
   ─────────────────────────
   20 base · ×1.5 streak (9 days) — keep it going
   🔥 streak safe for today
```

For a bravery event, it escalates: *"First time on LinkedIn. That took guts. +45 🎉"*

### 8.4 The level-up moment

Full-width interstitial (dismissible), not a tiny badge. New persona art + title + the
one-line "what changed in you" note + the next goal. The rare, earned, *big* dopamine.

### 8.5 Empty / day-one state

A brand-new founder has 0 ships. The page is **invitational, not empty**: persona = Lurker with
"Time to be read," a single highlighted card from the Action Board, and "Your first ship is
worth double (×2 cold-start). Most founders never send one." Make the first send irresistible.

---

## 9. Backend surface

| Method | Route | Purpose |
|---|---|---|
| `GET` | `/api/momentum?slug=` | Header chip + page rollup (reads `momentum_state` + recent events) |
| `GET` | `/api/momentum/events?slug=&since=` | Streak calendar + history timeline |
| `GET` | `/api/edge?slug=` | Today's lesson (creates lazily if scheduler hasn't, §7.3) |
| `POST` | `/api/edge/{id}/read` | Mark lesson read → fires `lesson_read` (+1) |

No new *posting* endpoints — scoring hooks into the **existing** `PATCH /api/cards/{id}`
(`ACTION_BOARD_PLAN.md` §1.3). That's the integration point: every card state change already
flows through there; `momentum.award()` rides along. New module `backend/app/momentum.py`
(rules + multipliers + streak + persona). Lesson generation is a new prompt family in
`prompts.py` + the `lessons/` principle objects, run inside the daily scheduler next to
`generate_cards`.

**Frontend** (`frontend/src/`): `components/Momentum.tsx`, `components/MomentumChip.tsx`,
`components/EdgeCard.tsx`, toast util; `api.ts` adds `getMomentum`, `getEvents`, `getEdge`,
`readEdge`; add `{ id: 'momentum', label: 'Momentum', tier: 'primary' }` to `TABS`. Reuse
`.card`/`.chip` CSS; add `.streak`, `.persona`, `.toast`, `.calendar` to `styles.css`. No new
heavy dep (confetti optional, tiny).

---

## 10. Success metrics (does it actually activate?)

The feature exists to move one number. Instrument from day one:

**North star:** `card_posted` events per active founder per week (ship rate).

| Metric | What it tells us |
|---|---|
| Ship rate (posts/founder/week) — **the one that matters** | activation working? |
| % of weekly-active founders with a live streak ≥3 | habit forming? |
| First-ship conversion (signup → first `card_posted`) & time-to-first-ship | onboarding the fear |
| `first_on_platform` events / founder | breadth / fear-conquering |
| Daily Edge: open rate, applied rate (`lesson_applied`/delivered) | is the teaching landing? |
| Streak resurrection rate (ship after a freeze/break) | are we re-engaging the discouraged? |
| D7 / D30 retention vs. pre-Momentum cohort | the retention bet |

**Guardrail (anti-vanity):** points/streak going up while *ship rate is flat* = we built a
busywork toy. Watch the ratio of `card_posted` points to total points; if it drops, the
multipliers are rewarding the wrong thing — retune toward send.

---

## 11. Phasing

| Phase | Scope | Why this order |
|---|---|---|
| **M1 — Score core** | `momentum_events`+`momentum_state` tables, `momentum.py` rules, hook into `PATCH /api/cards`, header chip, post-send toast, basic Momentum page (streak + ships + persona text). | The dopamine loop is the bet; ship the *feeling of being counted* first. Streak + toast are the activation drivers. |
| **M2 — Persona + streak polish** | Full persona ladder + level-up moment, freezes, calendar, tone skins, empty/day-one state. | Deepens retention + the identity payload once the core loop is proven. |
| **M3 — The Daily Edge** ⭐ | `lessons` table, principle library, selection algorithm, generation prompt, EdgeCard UI, `lesson_applied` loop. | The teaching/moat half. Higher build cost, needs the event log (M1) to exist first to have anything to tie back to. **This is where the defensibility lives.** |
| **M4 — Loop-back bonus + proof-of-work share** | `card_engaged` award wired to P4 monitor; shareable momentum card. | Bonus outcome signal + the "show an investor" artifact. Depends on `ACTION_BOARD_PLAN.md` P4. |

Ship-order rationale: M1+M2 are a self-contained retention/activation win on top of the Action
Board with no new AI. **M3 is the bet** — it's what no newsletter can clone and what turns
advice-fatigue (§9) into applied learning (§1). M4 rides existing infra.

---

## 12. Risks & open questions

1. **Will a serious B2B founder feel patronized?** Mitigation: the Ops skin (§6.4), transparent
   math, proof-of-work framing. *Open: do we default-infer the skin from category, or ask once
   in onboarding?*
2. **Self-reported `posted` is gameable.** Accepted as trust-first with a soft daily cap (§5.5).
   *Open: is the un-URL'd ship cap (10/day) right, or lower?*
3. **The Edge's tie-back quality is the whole game** — a bad tie-back ("the post you made" when
   they made none) is worse than no lesson. The skip-the-day rule (§7.3) is the safety valve.
   *Open: how high do we set the tie-back confidence bar before we'd rather skip?*
4. **Streak = ship-only is aggressive.** It's the right call for activation but may frustrate a
   founder who engaged all week without sending. *Open: do we show a secondary "engagement
   streak" so effort isn't invisible, while keeping the flame ship-only?*
5. **Timezone correctness** is fiddly and streaks live or die on it. Lock the `day_key` + grace
   window logic early (§5.3) — it's the kind of bug that silently kills the core mechanic.
6. **Persona thresholds are guesses.** Ship as tunable constants; recalibrate from M1 data
   before M2 hardens the level-up moments.

---

## 13. The one-line summary

> Count the brave act, congratulate it the instant it happens, teach the founder why it worked
> using their own work, and pull them back tomorrow to do it again — until "I'm an engineer who
> hates marketing" quietly becomes "I market now."
