# Outlast

Outlast is a small social repair game built for the LifeHack hackathon. Before replacing or throwing away a broken item, a user gives it one informed repair attempt with help from their community.

The MVP is intentionally focused on one measurable behaviour:

> Give a broken item one informed community repair attempt before replacing it.

## What is already working

- **Discover:** an eight-request repair board where community members share useful suggestions.
- **Items:** photo and description input, private AI pre-post guidance, repair-request posting, and owner-led resolution.
- **Alternative guidance:** AI may privately suggest passing on an already-working item or responsibly handling one that appears unsafe or impractical to repair.
- **Responsible exit:** private, item-specific recycle/dispose guidance when an owner has to let an item go.
- **Impact:** shared waste impact, responsible-exit tracking, and an individual XP leaderboard.
- **Demo mode:** fake users and a deterministic AI fallback, so the full flow works without credentials.
- **Cloud-ready setup:** OpenAI secrets template, Supabase schema, Streamlit theme, tests, linting, and GitHub Actions.

## Run locally

Python 3.11 or newer is required.

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-dev.txt
streamlit run app.py
```

The app works immediately in demo mode. To enable real photo analysis:

```bash
cp .streamlit/secrets.toml.example .streamlit/secrets.toml
```

Then add an `OPENAI_API_KEY` to `.streamlit/secrets.toml`. The default model is `gpt-5.6-luna`; it accepts image input and supports structured outputs through the Responses API, which keeps item data predictable. See the [official model page](https://developers.openai.com/api/docs/models/gpt-5.6-luna) and [Responses API reference](https://developers.openai.com/api/reference/resources/responses/methods/create).

Never commit `.streamlit/secrets.toml` or `.env`.

## Recommended demo story

1. On **Items**, describe a desk fan that stopped spinning and assess the item.
2. Post the item to the shared board.
3. Change the demo player in the sidebar and post a useful suggestion on **Discover**.
4. Switch to the original poster, resolve the item as Repaired, and select one or more solvers.
5. Alternatively, open **My items**, select **I have to let this item go**, and get owner-only disposal guidance.
6. Open **Impact** to show community impact, individual XP, and streaks.

## Scoring

| Activity | Base XP |
| --- | ---: |
| Post a useful suggestion | 20 |
| Resolve an item as its original poster | 50 |
| Selected as a solver | 100 |

Each award is multiplied by the recipient's active calendar-day streak: 1–2 days is **1.0×**, 3–6 is **1.1×**, 7–13 is **1.25×**, and 14+ is **1.5×**. Missing a full day resets the active multiplier to 1.0×.

Impact values are deliberately presented as estimates. They are suitable for a prototype and should not be marketed as audited environmental measurements.

## Architecture

```text
Streamlit app
├── OpenAI Responses API (optional photo + text analysis)
├── Streamlit session state (temporary UI cache)
├── Supabase PostgreSQL + Storage (prepared next integration)
└── Python scoring rules
```

When Supabase credentials are configured, items, images, suggestions, solver awards, activity days, and player XP are persisted remotely. Run `supabase/schema.sql` followed by `supabase/atomic_persistence.sql`; the second script makes suggestion and completion awards atomic. If the configured database cannot be loaded, the app shows the connection error instead of silently replacing remote data with the demo.

## Project map

```text
app.py                       Three-screen Streamlit application
repair_quest/ai.py           OpenAI analysis and offline fallback
repair_quest/models.py       Structured item and contribution models
repair_quest/scoring.py      XP streak and community impact rules
repair_quest/seed.py         Fake users, items, and individual XP data
repair_quest/state.py        Prototype session-state actions
supabase/schema.sql          Shared database and image-store setup
supabase/atomic_persistence.sql  Transactional write functions and Storage upload policy
tests/                       Fast unit tests
.github/workflows/ci.yml     Automated lint and test checks
```

## Highest-priority next steps

1. Add the OpenAI project key and test with 5–10 real item photos; tune only the prompt if results are unclear.
2. Create a Supabase project and run `supabase/schema.sql`, then `supabase/atomic_persistence.sql`.
3. Polish the single fan item demo, deploy to Streamlit Community Cloud, and rehearse a 2–3 minute pitch.

Do not add real authentication, payments, geolocation, chat, or a repair-guide database until the core demo is polished.
