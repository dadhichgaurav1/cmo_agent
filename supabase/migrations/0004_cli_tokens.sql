-- =====================================================================
-- 0004_cli_tokens.sql  —  long-lived personal access tokens for the CLI
-- Run AFTER 0001_init.sql.
--
-- Supabase JWTs expire, which is wrong for a local CLI (the build-in-public
-- skill). These are hashed, org-scoped personal access tokens: the raw token
-- (prefix "scmo_") is shown once at mint time; only its sha256 hash is stored.
-- The token authorizes exactly one thing in practice — pushing cards — and the
-- founder's code never leaves their machine; only the post text does.
-- =====================================================================

create table public.cli_tokens (
  id           uuid primary key default gen_random_uuid(),
  org_id       uuid not null references public.organizations(id) on delete cascade,
  user_id      uuid references auth.users(id) on delete set null,
  token_hash   text not null unique,        -- sha256 of the raw token
  prefix       text not null default '',    -- first chars, for display only (e.g. scmo_ab12)
  label        text not null default '',
  last_used_at timestamptz,
  created_at   timestamptz not null default now()
);
create index cli_tokens_hash_idx on public.cli_tokens(token_hash);
create index cli_tokens_org_idx  on public.cli_tokens(org_id, created_at desc);

alter table public.cli_tokens enable row level security;
create policy cli_tokens_member_rw on public.cli_tokens
  for all using (public.is_org_member(org_id)) with check (public.is_org_member(org_id));
