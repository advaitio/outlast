-- Outlast schema: individual items, suggestion contributions, and XP.
-- Run in the Supabase SQL Editor when replacing prototype session state.

create extension if not exists "pgcrypto";

create table if not exists public.players (
  id uuid primary key default gen_random_uuid(),
  display_name text not null unique,
  xp integer not null default 0 check (xp >= 0),
  created_at timestamptz not null default now()
);

-- Existing prototype projects may already have players without the new XP column.
alter table public.players add column if not exists xp integer not null default 0;

create table if not exists public.rescues (
  id uuid primary key default gen_random_uuid(),
  owner_id uuid not null references public.players(id) on delete cascade,
  title text not null,
  item_name text not null,
  description text not null,
  recommended_action text not null check (recommended_action = 'Repair'),
  difficulty text not null check (difficulty in ('Easy', 'Medium', 'Hard')),
  estimated_waste_kg numeric(8,2) not null default 0 check (estimated_waste_kg >= 0),
  suggested_next_step text not null,
  image_path text,
  after_image_path text,
  disposal_location text,
  disposal_evidence_xp_awarded integer not null default 0 check (disposal_evidence_xp_awarded >= 0),
  status text not null default 'Open' check (status in ('Open', 'Completed')),
  outcome text check (outcome in ('Repair', 'Recycle / dispose responsibly')),
  completed_by_id uuid references public.players(id),
  completion_xp_awarded integer not null default 0 check (completion_xp_awarded >= 0),
  completion_streak_multiplier numeric(3,2) check (completion_streak_multiplier in (1.00, 1.10, 1.25, 1.50)),
  created_at timestamptz not null default now(),
  completed_at timestamptz,
  check ((status = 'Completed') = (completed_at is not null)),
  check (
    status <> 'Completed'
    or (
      completed_by_id is not null
      and completion_xp_awarded > 0
      and completion_streak_multiplier is not null
    )
  )
);

alter table public.rescues add column if not exists disposal_location text;
alter table public.rescues add column if not exists disposal_evidence_xp_awarded integer not null default 0;

-- Migrate prototype data from the former multi-path rescue flow.
update public.rescues
set recommended_action = 'Repair'
where recommended_action in ('Salvage', 'Rehome');
update public.rescues set outcome = null where outcome in ('Salvage', 'Rehome');
alter table public.rescues drop constraint if exists rescues_recommended_action_check;
alter table public.rescues add constraint rescues_recommended_action_check
  check (recommended_action = 'Repair');
alter table public.rescues drop constraint if exists rescues_outcome_check;
alter table public.rescues add constraint rescues_outcome_check
  check (outcome in ('Repair', 'Recycle / dispose responsibly'));

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

insert into public.players (display_name, xp)
select seeded.display_name, seeded.xp
from (values
  ('Alex', 120), ('Maya', 240), ('Noah', 210), ('Priya', 180), ('Sam', 130)
) as seeded(display_name, xp)
where not exists (
  select 1 from public.players existing
  where existing.display_name = seeded.display_name
);

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

drop policy if exists "Prototype read players" on public.players;
drop policy if exists "Prototype read rescues" on public.rescues;
drop policy if exists "Prototype read contributions" on public.rescue_contributions;
drop policy if exists "Prototype read solvers" on public.rescue_solvers;
drop policy if exists "Prototype read activity days" on public.player_activity_days;
drop policy if exists "Prototype insert players" on public.players;
drop policy if exists "Prototype update players" on public.players;
drop policy if exists "Prototype insert rescues" on public.rescues;
drop policy if exists "Prototype update rescues" on public.rescues;
drop policy if exists "Prototype insert contributions" on public.rescue_contributions;
drop policy if exists "Prototype insert solvers" on public.rescue_solvers;
drop policy if exists "Prototype update solvers" on public.rescue_solvers;
drop policy if exists "Prototype insert activity days" on public.player_activity_days;

create policy "Prototype read players" on public.players for select using (true);
create policy "Prototype read rescues" on public.rescues for select using (true);
create policy "Prototype read contributions" on public.rescue_contributions for select using (true);
create policy "Prototype read solvers" on public.rescue_solvers for select using (true);
create policy "Prototype read activity days" on public.player_activity_days for select using (true);
create policy "Prototype insert players" on public.players for insert with check (true);
create policy "Prototype update players" on public.players for update using (true) with check (true);
create policy "Prototype insert rescues" on public.rescues for insert with check (true);
create policy "Prototype update rescues" on public.rescues for update using (true) with check (true);
create policy "Prototype insert contributions" on public.rescue_contributions for insert with check (true);
create policy "Prototype insert solvers" on public.rescue_solvers for insert with check (true);
create policy "Prototype update solvers" on public.rescue_solvers for update using (true) with check (true);
create policy "Prototype insert activity days" on public.player_activity_days for insert with check (true);
