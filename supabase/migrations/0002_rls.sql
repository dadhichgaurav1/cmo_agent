-- =====================================================================
-- 0002_rls.sql  —  Row Level Security: tenant isolation by org membership
-- Run AFTER 0001_init.sql.
--
-- NOTE: your FastAPI backend uses the SERVICE ROLE key, which BYPASSES RLS.
-- These policies protect any direct frontend -> Supabase access and act as
-- defense-in-depth. The backend must still scope every query by org_id itself.
-- =====================================================================

-- Membership check. SECURITY DEFINER so it does not recurse through
-- org_members' own RLS policy.
create or replace function public.is_org_member(target uuid)
returns boolean
language sql stable security definer set search_path = public as $$
  select exists(
    select 1 from public.org_members m
    where m.org_id = target and m.user_id = auth.uid()
  );
$$;

create or replace function public.is_org_admin(target uuid)
returns boolean
language sql stable security definer set search_path = public as $$
  select exists(
    select 1 from public.org_members m
    where m.org_id = target and m.user_id = auth.uid() and m.role in ('owner','admin')
  );
$$;

-- ---------- enable RLS everywhere ----------
alter table public.profiles       enable row level security;
alter table public.organizations  enable row level security;
alter table public.org_members    enable row level security;
alter table public.runs           enable row level security;
alter table public.monitors       enable row level security;
alter table public.monitor_events enable row level security;
alter table public.org_settings   enable row level security;
alter table public.integrations   enable row level security;
alter table public.usage_events   enable row level security;

-- ---------- profiles: each user sees/edits only their own ----------
create policy profiles_self on public.profiles
  for all using (id = auth.uid()) with check (id = auth.uid());

-- ---------- organizations ----------
create policy orgs_member_read on public.organizations
  for select using (public.is_org_member(id));
create policy orgs_admin_update on public.organizations
  for update using (public.is_org_admin(id)) with check (public.is_org_admin(id));

-- ---------- org_members ----------
create policy members_read on public.org_members
  for select using (public.is_org_member(org_id));
create policy members_admin_write on public.org_members
  for all using (public.is_org_admin(org_id)) with check (public.is_org_admin(org_id));

-- ---------- org-scoped tables: any member can read/write rows in their org ----------
create policy runs_member_rw on public.runs
  for all using (public.is_org_member(org_id)) with check (public.is_org_member(org_id));

create policy monitors_member_rw on public.monitors
  for all using (public.is_org_member(org_id)) with check (public.is_org_member(org_id));

create policy monitor_events_member_rw on public.monitor_events
  for all using (public.is_org_member(org_id)) with check (public.is_org_member(org_id));

create policy org_settings_member_read on public.org_settings
  for select using (public.is_org_member(org_id));
create policy org_settings_admin_write on public.org_settings
  for all using (public.is_org_admin(org_id)) with check (public.is_org_admin(org_id));

create policy integrations_member_rw on public.integrations
  for all using (public.is_org_member(org_id)) with check (public.is_org_member(org_id));

-- usage_events: members read; writes happen via service role (backend) only
create policy usage_member_read on public.usage_events
  for select using (public.is_org_member(org_id));
