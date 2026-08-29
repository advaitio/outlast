# Contributing to Repair Quest

## Suggested hackathon ownership

- **Rescue flow + AI:** `repair_quest/ai.py`, quest creation and completion in `app.py`.
- **Social / Discover:** Rescue Board cards and Claim, Join, Offer Part interactions in `app.py`.
- **Impact + integration:** `repair_quest/scoring.py`, `supabase/schema.sql`, leaderboard, deployment, and visual consistency.

All three teammates should help test the end-to-end demo and pitch.

## Fast team workflow

1. Pull `main` before starting.
2. Create a small branch such as `feature/rescue-flow`.
3. Keep each pull request focused on one feature.
4. Run `ruff check .` and `pytest` before requesting review.
5. Merge often so the demo branch never drifts far from working code.

Do not commit `.streamlit/secrets.toml`, `.env`, API keys, or Supabase service-role keys.

