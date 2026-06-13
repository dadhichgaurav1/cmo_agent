-- =====================================================================
-- 0003_action_cards.sql  —  Action Board: stateful marketing-action cards
-- Run AFTER 0001_init.sql and 0002_rls.sql.
--
-- Promotes the agent's drafts (today buried in runs.summary JSONB) to
-- first-class, stateful cards the founder works through on a Trello-like
-- board: one swimlane per platform, each card a specific place to post.
--
-- Same conventions as the rest of the schema: uuid PK, org_id scoping,
-- set_updated_at() trigger, RLS as defense-in-depth (backend still scopes
-- every query by org_id itself — it uses the service role, which bypasses RLS).
-- =====================================================================

create table public.action_cards (
  id            uuid primary key default gen_random_uuid(),
  org_id        uuid not null references public.organizations(id) on delete cascade,
  run_id        uuid references public.runs(id) on delete set null,  -- provenance (nullable: CLI/manual cards)
  company_slug  text,                          -- which company this board belongs to
  source        text not null default 'agent', -- agent | cli | manual
  platform      text not null,                 -- reddit | hackernews | x | linkedin | indiehackers | other
  kind          text not null default 'reply', -- post (prefill deep-link) | reply (copy + open thread)
  target_url    text,                          -- thread to reply to (null for kind=post)
  target_title  text,                          -- thread/source title, for the card face
  title         text not null default '',
  body          text not null default '',      -- the draft (already humanized)
  voice         text,                          -- voice profile applied (P2)
  state         text not null default 'suggested',
                -- suggested | drafted | approved | posted | engaged | dismissed
  posted_url    text,                          -- where they posted (loop-back signal, P4)
  posted_at     timestamptz,
  position      int not null default 0,        -- ordering within a (platform,state) cell
  metadata      jsonb not null default '{}',   -- platform extras (e.g. subreddit, tweet_id)
  created_at    timestamptz not null default now(),
  updated_at    timestamptz not null default now()
);
create index action_cards_org_state   on public.action_cards (org_id, state);
create index action_cards_org_company on public.action_cards (org_id, company_slug, created_at desc);

create trigger trg_action_cards_updated before update on public.action_cards
  for each row execute function public.set_updated_at();

-- RLS: any org member can read/write their org's cards (defense-in-depth).
alter table public.action_cards enable row level security;
create policy action_cards_member_rw on public.action_cards
  for all using (public.is_org_member(org_id)) with check (public.is_org_member(org_id));
