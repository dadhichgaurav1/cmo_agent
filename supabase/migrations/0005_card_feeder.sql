-- =====================================================================
-- 0005_card_feeder.sql  —  per-company Action Board daily feeder toggle
-- Run AFTER 0001_init.sql (and 0003_action_cards.sql).
--
-- The daily "refill the board" job is a recurring per-company job, so it lives
-- on the monitors row (the per-company recurring-jobs table) rather than a
-- global env flag. The on/off control is surfaced on the Action Board; the
-- monitor scheduler fires it. Default off: the founder opts each company in.
-- =====================================================================

alter table public.monitors
  add column if not exists feed_enabled boolean not null default false;
