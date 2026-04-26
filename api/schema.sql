-- ============================================================
-- Golf Analytics — Supabase schema
-- Paste this entire file into the Supabase SQL Editor and run it.
-- Safe to re-run: uses IF NOT EXISTS / OR REPLACE throughout.
-- ============================================================


-- -------------------------------------------------------
-- 1. sessions
--    One row per uploaded Garmin R10 CSV file.
-- -------------------------------------------------------
create table if not exists sessions (
  id           uuid primary key default gen_random_uuid(),
  user_id      uuid references auth.users (id) on delete cascade not null,
  filename     text not null,
  storage_path text not null,
  uploaded_at  timestamptz default now()
);

alter table sessions enable row level security;

drop policy if exists "users see own sessions" on sessions;
create policy "users see own sessions"
  on sessions for all
  using  (user_id = auth.uid())
  with check (user_id = auth.uid());


-- -------------------------------------------------------
-- 2. shots
--    One row per shot within a session (your raw CSV rows).
-- -------------------------------------------------------
create table if not exists shots (
  id                        uuid primary key default gen_random_uuid(),
  session_id                uuid references sessions (id) on delete cascade not null,
  user_id                   uuid references auth.users (id) on delete cascade not null,
  club_type                 text,
  club_speed                float,
  attack_angle              float,
  club_path                 float,
  club_face                 float,
  face_to_path              float,
  ball_speed                float,
  smash_factor              float,
  launch_angle              float,
  launch_direction          float,
  backspin                  float,
  sidespin                  float,
  spin_rate                 float,
  spin_axis                 float,
  apex_height               float,
  carry_distance            float,
  carry_deviation_angle     float,
  carry_deviation_distance  float,
  total_distance            float,
  total_deviation_angle     float,
  total_deviation_distance  float
);

alter table shots enable row level security;

drop policy if exists "users see own shots" on shots;
create policy "users see own shots"
  on shots for all
  using  (user_id = auth.uid())
  with check (user_id = auth.uid());

-- Index to speed up "all shots for user" queries
create index if not exists shots_user_id_idx on shots (user_id);
create index if not exists shots_session_id_idx on shots (session_id);


-- -------------------------------------------------------
-- 3. club_summaries
--    Cached computed analytics, regenerated on demand.
-- -------------------------------------------------------
create table if not exists club_summaries (
  id             uuid primary key default gen_random_uuid(),
  user_id        uuid references auth.users (id) on delete cascade not null,
  computed_at    timestamptz default now(),
  club_type      text,
  shots          int,
  avg_carry_yd   float,
  std_carry_yd   float,
  avg_ball_speed float,
  avg_smash      float,
  avg_club_speed float,
  avg_launch_deg float,
  avg_backspin   float,
  shape_bias     text
);

alter table club_summaries enable row level security;

drop policy if exists "users see own summaries" on club_summaries;
create policy "users see own summaries"
  on club_summaries for all
  using  (user_id = auth.uid())
  with check (user_id = auth.uid());

create index if not exists club_summaries_user_id_idx on club_summaries (user_id);
