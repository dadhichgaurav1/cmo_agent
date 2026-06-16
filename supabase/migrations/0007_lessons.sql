-- =====================================================================
-- 0007_lessons.sql  —  The Daily Edge: one tailored marketing lesson a day
-- Run AFTER 0006_momentum.sql.
--
-- One psychological/persuasion principle a day, tailored to the founder's own
-- work and tied to a specific card on their board. The tie-back is the moat —
-- no newsletter can write "remember the cold email you drafted Tuesday".
-- Same conventions: uuid PK, org_id scoping, set_updated_at() trigger, RLS.
-- =====================================================================

create table if not exists public.lessons (
  id            uuid primary key default gen_random_uuid(),
  org_id        uuid not null references public.organizations(id) on delete cascade,
  company_slug  text,
  day_key       date not null,                     -- one lesson per company per day
  principle_key text not null,                     -- curriculum id, e.g. 'curse_of_knowledge'
  title         text not null,
  body          text not null,                     -- the ~120-word tailored read
  tie_back      jsonb not null default '{}',       -- {card_id, what_you_did}
  cta_card_id   uuid references public.action_cards(id) on delete set null,  -- "apply it here"
  cta_label     text,
  state         text not null default 'unread',    -- unread | read | applied
  created_at    timestamptz not null default now(),
  updated_at    timestamptz not null default now()
);
create index if not exists lessons_org_day on public.lessons (org_id, company_slug, day_key desc);

create or replace trigger trg_lessons_updated before update on public.lessons
  for each row execute function public.set_updated_at();

alter table public.lessons enable row level security;
drop policy if exists lessons_member_rw on public.lessons;
create policy lessons_member_rw on public.lessons
  for all using (public.is_org_member(org_id)) with check (public.is_org_member(org_id));
