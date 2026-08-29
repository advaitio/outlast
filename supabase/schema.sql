-- Repair Quest MVP schema
-- Run in Supabase SQL Editor when the project is ready to replace Streamlit session state.

create extension if not exists "pgcrypto";

create table if not exists public.players (
  id uuid primary key default gen_random_uuid(),
  display_name text not null,
  created_at timestamptz not null default now()
);

create table if not exists public.quests (
  id uuid primary key default gen_random_uuid(),
  owner_id uuid not null references public.players(id) on delete cascade,
  title text not null,
  item_name text not null,
  description text not null,
  recommended_action text not null check (recommended_action in ('Repair', 'Rehome', 'Salvage')),
  difficulty text not null check (difficulty in ('Easy', 'Medium', 'Hard')),
  estimated_waste_kg numeric(8,2) not null default 0,
  suggested_next_step text not null,
  image_path text,
  after_image_path text,
  status text not null default 'Open' check (status in ('Open', 'Claimed', 'Completed')),
  outcome text check (outcome in ('Repair', 'Rehome', 'Salvage')),
  points_awarded integer not null default 0,
  created_at timestamptz not null default now(),
  completed_at timestamptz
);

create table if not exists public.quest_helpers (
  quest_id uuid not null references public.quests(id) on delete cascade,
  player_id uuid not null references public.players(id) on delete cascade,
  role text not null check (role in ('Claim', 'Join', 'Offer Part')),
  message text,
  created_at timestamptz not null default now(),
  primary key (quest_id, player_id, role)
);

create table if not exists public.quest_suggestions (
  id uuid primary key default gen_random_uuid(),
  quest_id uuid not null references public.quests(id) on delete cascade,
  player_id uuid not null references public.players(id) on delete cascade,
  message text not null check (char_length(message) between 1 and 280),
  created_at timestamptz not null default now()
);

insert into storage.buckets (id, name, public)
values ('quest-images', 'quest-images', true)
on conflict (id) do nothing;

-- The hackathon build uses fake users. Before production, enable RLS and replace
-- these prototype policies with rules tied to Supabase Auth identities.
alter table public.players enable row level security;
alter table public.quests enable row level security;
alter table public.quest_helpers enable row level security;
alter table public.quest_suggestions enable row level security;

create policy "Prototype read players" on public.players for select using (true);
create policy "Prototype read quests" on public.quests for select using (true);
create policy "Prototype read helpers" on public.quest_helpers for select using (true);
create policy "Prototype read suggestions" on public.quest_suggestions for select using (true);

