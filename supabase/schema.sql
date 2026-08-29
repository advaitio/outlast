-- Repair Quest schema: individual rescues, suggestion contributions, and XP.
-- Run in the Supabase SQL Editor when replacing prototype session state.

create extension if not exists "pgcrypto";

create table if not exists public.players (
  id uuid primary key default gen_random_uuid(),
  display_name text not null unique,
  xp integer not null default 0 check (xp >= 0),
  created_at timestamptz not null default now()
);

create table if not exists public.rescues (
  id uuid primary key default gen_random_uuid(),
  owner_id uuid not null references public.players(id) on delete cascade,
  title text not null,
  item_name text not null,
  description text not null,
  recommended_action text not null check (recommended_action in ('Repair', 'Rehome', 'Salvage')),
  difficulty text not null check (difficulty in ('Easy', 'Medium', 'Hard')),
  estimated_waste_kg numeric(8,2) not null default 0 check (estimated_waste_kg >= 0),
  suggested_next_step text not null,
  image_path text,
  after_image_path text,
  status text not null default 'Open' check (status in ('Open', 'Completed')),
  outcome text check (outcome in ('Repair', 'Rehome', 'Salvage')),
  created_at timestamptz not null default now(),
  completed_at timestamptz,
  check ((status = 'Completed') = (completed_at is not null))
);

-- Contribution type is intentionally restricted to suggestions for this release.
create table if not exists public.rescue_contributions (
  id uuid primary key default gen_random_uuid(),
  rescue_id uuid not null references public.rescues(id) on delete cascade,
  player_id uuid not null references public.players(id) on delete cascade,
  contribution_type text not null default 'Suggestion' check (contribution_type = 'Suggestion'),
  message text not null check (char_length(message) between 1 and 280),
  xp_awarded integer not null check (xp_awarded >= 0),
  streak_multiplier numeric(3,2) not null check (streak_multiplier in (1.00, 1.10, 1.25, 1.50)),
  created_at timestamptz not null default now()
);

-- The original poster can select more than one successful solver.
create table if not exists public.rescue_solvers (
  rescue_id uuid not null references public.rescues(id) on delete cascade,
  player_id uuid not null references public.players(id) on delete cascade,
  xp_awarded integer not null check (xp_awarded >= 0),
  streak_multiplier numeric(3,2) not null check (streak_multiplier in (1.00, 1.10, 1.25, 1.50)),
  selected_at timestamptz not null default now(),
  primary key (rescue_id, player_id)
);

-- Store every qualifying calendar day, so a streak can be calculated from durable data.
create table if not exists public.player_activity_days (
  player_id uuid not null references public.players(id) on delete cascade,
  activity_date date not null,
  primary key (player_id, activity_date)
);

create index if not exists rescue_contributions_rescue_created_idx
  on public.rescue_contributions (rescue_id, created_at);
create index if not exists player_activity_days_player_date_idx
  on public.player_activity_days (player_id, activity_date desc);

insert into storage.buckets (id, name, public)
values ('rescue-images', 'rescue-images', true)
on conflict (id) do nothing;

-- The hackathon build uses fake users. Before production, replace these read-only
-- prototype policies with policies tied to Supabase Auth and server-side XP writes.
alter table public.players enable row level security;
alter table public.rescues enable row level security;
alter table public.rescue_contributions enable row level security;
alter table public.rescue_solvers enable row level security;
alter table public.player_activity_days enable row level security;

create policy "Prototype read players" on public.players for select using (true);
create policy "Prototype read rescues" on public.rescues for select using (true);
create policy "Prototype read contributions" on public.rescue_contributions for select using (true);
create policy "Prototype read solvers" on public.rescue_solvers for select using (true);
create policy "Prototype read activity days" on public.player_activity_days for select using (true);
