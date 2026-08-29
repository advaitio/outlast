-- Atomic persistence for Repair Quest. Run this after schema.sql.
-- It prevents partial writes across rescues, XP, and activity days.

create or replace function public.add_rescue_suggestion(
  p_rescue_id uuid, p_player_id uuid, p_message text, p_xp_awarded integer,
  p_streak_multiplier numeric, p_activity_date date
)
returns void language plpgsql security definer set search_path = public as $$
declare v_status text;
begin
  select status into v_status from public.rescues where id = p_rescue_id for update;
  if v_status is distinct from 'Open' then raise exception 'Rescue is not open'; end if;
  insert into public.rescue_contributions
    (rescue_id, player_id, contribution_type, message, xp_awarded, streak_multiplier)
  values (p_rescue_id, p_player_id, 'Suggestion', p_message, p_xp_awarded, p_streak_multiplier);
  update public.players set xp = xp + p_xp_awarded where id = p_player_id;
  if not found then raise exception 'Player not found'; end if;
  insert into public.player_activity_days (player_id, activity_date)
  values (p_player_id, p_activity_date) on conflict (player_id, activity_date) do nothing;
end;
$$;

create or replace function public.complete_rescue_with_awards(
  p_rescue_id uuid, p_completed_by_id uuid, p_outcome text,
  p_completion_xp_awarded integer, p_completion_streak_multiplier numeric,
  p_solvers jsonb, p_activity_date date, p_after_image_path text default null
)
returns void language plpgsql security definer set search_path = public as $$
declare
  v_owner_id uuid; v_status text; v_solver jsonb; v_solver_id uuid;
  v_solver_xp integer; v_solver_multiplier numeric;
begin
  select owner_id, status into v_owner_id, v_status
  from public.rescues where id = p_rescue_id for update;
  if v_status is distinct from 'Open' then raise exception 'Rescue is not open'; end if;
  if v_owner_id is distinct from p_completed_by_id then
    raise exception 'Only the rescue owner can complete it';
  end if;
  update public.rescues set status = 'Completed', outcome = p_outcome,
    completed_by_id = p_completed_by_id, completion_xp_awarded = p_completion_xp_awarded,
    completion_streak_multiplier = p_completion_streak_multiplier,
    after_image_path = p_after_image_path, completed_at = now()
  where id = p_rescue_id;
  update public.players set xp = xp + p_completion_xp_awarded where id = p_completed_by_id;
  if not found then raise exception 'Completing player not found'; end if;
  insert into public.player_activity_days (player_id, activity_date)
  values (p_completed_by_id, p_activity_date) on conflict (player_id, activity_date) do nothing;
  for v_solver in select value from jsonb_array_elements(p_solvers) loop
    v_solver_id := (v_solver ->> 'player_id')::uuid;
    v_solver_xp := (v_solver ->> 'xp_awarded')::integer;
    v_solver_multiplier := (v_solver ->> 'streak_multiplier')::numeric;
    insert into public.rescue_solvers (rescue_id, player_id, xp_awarded, streak_multiplier)
    values (p_rescue_id, v_solver_id, v_solver_xp, v_solver_multiplier)
    on conflict (rescue_id, player_id) do update set xp_awarded = excluded.xp_awarded,
      streak_multiplier = excluded.streak_multiplier;
    update public.players set xp = xp + v_solver_xp where id = v_solver_id;
    if not found then raise exception 'Solver not found'; end if;
    insert into public.player_activity_days (player_id, activity_date)
    values (v_solver_id, p_activity_date) on conflict (player_id, activity_date) do nothing;
  end loop;
end;
$$;

grant execute on function public.add_rescue_suggestion(uuid, uuid, text, integer, numeric, date)
  to anon, authenticated;
grant execute on function public.complete_rescue_with_awards(uuid, uuid, text, integer, numeric, jsonb, date, text)
  to anon, authenticated;

drop policy if exists "Prototype upload rescue images" on storage.objects;
create policy "Prototype upload rescue images" on storage.objects for insert
with check (bucket_id = 'rescue-images');
