-- =====================================================================
-- 0001_init.sql  —  StratCMO core schema (users / orgs / runs / monitors / billing)
-- Run in: Supabase Dashboard -> SQL Editor -> New query -> paste -> Run
-- Safe to run once on a fresh project.
-- =====================================================================

create extension if not exists "pgcrypto";

-- ---------- profiles: 1:1 with auth.users ----------
create table public.profiles (
  id          uuid primary key references auth.users(id) on delete cascade,
  email       text,
  full_name   text,
  avatar_url  text,
  created_at  timestamptz not null default now(),
  updated_at  timestamptz not null default now()
);

-- ---------- organizations (workspaces = tenants) ----------
create table public.organizations (
  id                     uuid primary key default gen_random_uuid(),
  name                   text not null,
  slug                   text unique not null,
  created_by             uuid references auth.users(id) on delete set null,
  -- Stripe billing state (source of truth = Stripe webhooks)
  stripe_customer_id     text unique,
  stripe_subscription_id text,
  plan                   text not null default 'free',       -- free | pro | ...
  subscription_status    text not null default 'inactive',   -- active | trialing | past_due | canceled | inactive
  current_period_end     timestamptz,
  created_at             timestamptz not null default now(),
  updated_at             timestamptz not null default now()
);

-- ---------- membership ----------
create type public.org_role as enum ('owner','admin','member');

create table public.org_members (
  org_id     uuid not null references public.organizations(id) on delete cascade,
  user_id    uuid not null references auth.users(id) on delete cascade,
  role       public.org_role not null default 'member',
  created_at timestamptz not null default now(),
  primary key (org_id, user_id)
);
create index org_members_user_idx on public.org_members(user_id);

-- ---------- runs: historical agent analyses (replaces /tmp + cache) ----------
create table public.runs (
  id                uuid primary key default gen_random_uuid(),
  org_id            uuid not null references public.organizations(id) on delete cascade,
  created_by        uuid references auth.users(id) on delete set null,
  company_url       text not null,
  company_slug      text not null,
  synap_customer_id text,                                   -- org-scoped Synap brain key (org_id:slug)
  mode              text not null default 'live',
  status            text not null default 'running',        -- running | done | error
  summary           jsonb,                                  -- final structured result
  events            jsonb,                                  -- optional: streamed events for replay
  error             text,
  started_at        timestamptz not null default now(),
  finished_at       timestamptz
);
create index runs_org_created_idx on public.runs(org_id, started_at desc);
create index runs_org_slug_idx    on public.runs(org_id, company_slug);

-- ---------- monitors: durable scheduler state (was in-process) ----------
create table public.monitors (
  id           uuid primary key default gen_random_uuid(),
  org_id       uuid not null references public.organizations(id) on delete cascade,
  company_slug text not null,
  jobs         jsonb not null default '[]',
  enabled      boolean not null default true,
  updated_at   timestamptz not null default now(),
  unique (org_id, company_slug)
);

-- ---------- monitor changelog / deltas ----------
create table public.monitor_events (
  id           uuid primary key default gen_random_uuid(),
  org_id       uuid not null references public.organizations(id) on delete cascade,
  company_slug text not null,
  entry        jsonb not null,
  created_at   timestamptz not null default now()
);
create index monitor_events_idx on public.monitor_events(org_id, company_slug, created_at desc);

-- ---------- per-org settings ----------
create table public.org_settings (
  org_id     uuid primary key references public.organizations(id) on delete cascade,
  settings   jsonb not null default '{}',
  updated_at timestamptz not null default now()
);

-- ---------- per-org integration connections (Composio etc.) ----------
create table public.integrations (
  id            uuid primary key default gen_random_uuid(),
  org_id        uuid not null references public.organizations(id) on delete cascade,
  provider      text not null,                              -- gmail | slack | ...
  connection_id text,                                       -- Composio connection id
  status        text not null default 'pending',
  metadata      jsonb not null default '{}',
  created_at    timestamptz not null default now(),
  unique (org_id, provider)
);

-- ---------- usage metering (billing + cost caps) ----------
create table public.usage_events (
  id         uuid primary key default gen_random_uuid(),
  org_id     uuid not null references public.organizations(id) on delete cascade,
  kind       text not null,                                 -- run | chat | research | monitor
  quantity   numeric not null default 1,
  metadata   jsonb not null default '{}',
  created_at timestamptz not null default now()
);
create index usage_events_idx on public.usage_events(org_id, created_at desc);

-- =====================================================================
-- updated_at maintenance
-- =====================================================================
create or replace function public.set_updated_at()
returns trigger language plpgsql as $$
begin new.updated_at = now(); return new; end; $$;

create trigger trg_profiles_updated     before update on public.profiles      for each row execute function public.set_updated_at();
create trigger trg_orgs_updated         before update on public.organizations for each row execute function public.set_updated_at();
create trigger trg_monitors_updated     before update on public.monitors      for each row execute function public.set_updated_at();
create trigger trg_org_settings_updated before update on public.org_settings  for each row execute function public.set_updated_at();

-- =====================================================================
-- Auto-provision profile + personal workspace on signup
-- =====================================================================
create or replace function public.handle_new_user()
returns trigger
language plpgsql
security definer set search_path = public as $$
declare
  new_org uuid;
  display text;
begin
  display := coalesce(new.raw_user_meta_data->>'full_name', new.raw_user_meta_data->>'name', split_part(new.email,'@',1));

  insert into public.profiles (id, email, full_name)
  values (new.id, new.email, display);

  insert into public.organizations (name, slug, created_by)
  values (display || '''s Workspace', 'org-' || substr(replace(new.id::text,'-',''),1,12), new.id)
  returning id into new_org;

  insert into public.org_members (org_id, user_id, role) values (new_org, new.id, 'owner');
  insert into public.org_settings (org_id) values (new_org);

  return new;
end; $$;

create trigger on_auth_user_created
after insert on auth.users
for each row execute function public.handle_new_user();
