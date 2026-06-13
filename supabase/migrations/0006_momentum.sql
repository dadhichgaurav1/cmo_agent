-- =====================================================================
-- 0006_momentum.sql  —  Momentum: founder activation score + streak
-- Run AFTER 0001_init.sql, 0002_rls.sql, 0003_action_cards.sql.
--
-- Two tables + one column:
--  * momentum_events  — append-only log of scoreable acts (the substrate).
--  * momentum_state   — denormalized per-company rollup (the header chip reads this).
--  * organizations.timezone — streak day-bucketing is timezone-correct.
--
-- Same conventions as the rest of the schema: uuid PK, org_id scoping,
-- set_updated_at() trigger, RLS as defense-in-depth (backend uses the service
-- role and still scopes every query by org_id itself).
-- =====================================================================

-- Founder-local timezone, for streak day_key math (default UTC; set from browser).
alter table public.organizations
  add column if not exists timezone text not null default 'UTC';

-- --- the activity log (append-only) ----------------------------------------
create table if not exists public.momentum_events (
  id            uuid primary key default gen_random_uuid(),
  org_id        uuid not null references public.organizations(id) on delete cascade,
  user_id       uuid,                              -- who did it (for per-founder views)
  company_slug  text,                              -- which company
  kind          text not null,                     -- lesson_read | card_reviewed | card_approved
                                                   -- | card_posted | card_engaged | lesson_applied
  card_id       uuid references public.action_cards(id) on delete set null,  -- provenance
  platform      text,                              -- reddit | hackernews | x | linkedin | indiehackers
  points        int not null default 0,            -- resolved at write time
  multiplier    numeric not null default 1.0,      -- streak/variety/courage multiplier applied
  day_key       date not null,                     -- founder-local day bucket for streak math
  metadata      jsonb not null default '{}',       -- {original:true, first_on_platform:true, breakdown:[]}
  created_at    timestamptz not null default now()
);
create index if not exists momentum_events_org_day
  on public.momentum_events (org_id, company_slug, day_key);
create index if not exists momentum_events_org_user
  on public.momentum_events (org_id, user_id, created_at desc);

alter table public.momentum_events enable row level security;
create policy momentum_events_member_rw on public.momentum_events
  for all using (public.is_org_member(org_id)) with check (public.is_org_member(org_id));

-- --- the cached rollup (one row per org/company) ---------------------------
create table if not exists public.momentum_state (
  org_id            uuid not null references public.organizations(id) on delete cascade,
  company_slug      text not null default '',
  total_points      int not null default 0,
  current_streak    int not null default 0,         -- consecutive active (=shipped) days
  longest_streak    int not null default 0,
  freezes_left      int not null default 2,          -- streak-saver budget
  last_active_day   date,                            -- last day with a ship
  persona_key       text not null default 'lurker',
  persona_progress  int not null default 0,          -- ships toward the next persona tier
  ships_total       int not null default 0,          -- count of card_posted (the headline number)
  ships_this_week   int not null default 0,
  platforms_shipped text[] not null default '{}',    -- distinct platforms ever shipped on
  updated_at        timestamptz not null default now(),
  primary key (org_id, company_slug)
);

create trigger trg_momentum_state_updated before update on public.momentum_state
  for each row execute function public.set_updated_at();

alter table public.momentum_state enable row level security;
create policy momentum_state_member_rw on public.momentum_state
  for all using (public.is_org_member(org_id)) with check (public.is_org_member(org_id));
