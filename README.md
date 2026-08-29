# Repair Quest

Repair Quest is a small social rescue game built for the LifeHack hackathon. Before throwing away or replacing an item, a user posts it as a rescue opportunity and asks their community to help **repair, rehome, or salvage** it.

The MVP is intentionally focused on one measurable behaviour:

> Give an unwanted item one community rescue attempt before replacing it.

## What is already working

- **Discover:** an eight-quest Rescue Board with Claim, Join, Offer Part, and suggestions.
- **Rescue:** photo and description input, AI-assisted structured quest generation, posting, and completion.
- **Impact:** outcome scoring, collaboration bonuses, individual metrics, progress, and leaderboard.
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

Then add an `OPENAI_API_KEY` to `.streamlit/secrets.toml`. The default model is `gpt-5.6-luna`; it accepts image input and supports structured outputs through the Responses API, which keeps quest data predictable. See the [official model page](https://developers.openai.com/api/docs/models/gpt-5.6-luna) and [Responses API reference](https://developers.openai.com/api/reference/resources/responses/methods/create).

Never commit `.streamlit/secrets.toml` or `.env`.

## Recommended demo story

1. On **Rescue**, describe a desk fan that stopped spinning and generate a quest.
2. Post the generated quest to the shared board.
3. Change the demo player in the sidebar, then Claim or Join the fan quest on **Discover**.
4. Return to **Rescue**, complete it as Repaired, and show the point reward.
5. Open **Impact** to show updated community progress and individual leaderboard.

## Scoring

| Outcome | Base points |
| --- | ---: |
| Repair | 100 |
| Rehome | 80 |
| Salvage | 60 |
| Each teammate who helped | +30 |

Impact values are deliberately presented as estimates. They are suitable for a prototype and should not be marketed as audited environmental measurements.

## Architecture

```text
Streamlit app
├── OpenAI Responses API (optional photo + text analysis)
├── Streamlit session state (working hackathon data store)
├── Supabase PostgreSQL + Storage (prepared next integration)
└── Python scoring rules
```

The current build uses session state so the social loop is demoable now. `supabase/schema.sql` prepares the shared database and image bucket, but persistence is not yet connected to the UI.

## Project map

```text
app.py                       Three-screen Streamlit application
repair_quest/ai.py           OpenAI analysis and offline fallback
repair_quest/models.py       Structured quest data models
repair_quest/scoring.py      Transparent impact point rules
repair_quest/seed.py         Fake users, quests, and leaderboard
repair_quest/state.py        Prototype session-state actions
supabase/schema.sql          Shared database and image-store setup
tests/                       Fast unit tests
.github/workflows/ci.yml     Automated lint and test checks
```

## Highest-priority next steps

1. Give each teammate one feature area using the ownership guide in `CONTRIBUTING.md`.
2. Add the OpenAI project key and test with 5–10 real item photos; tune only the prompt if results are unclear.
3. Create a Supabase project, run `supabase/schema.sql`, and replace session-state writes with a small repository layer.
4. Add image upload to the `quest-images` bucket and save its returned path on each quest.
5. Polish the single fan rescue demo, deploy to Streamlit Community Cloud, and rehearse a 2–3 minute pitch.

Do not add real authentication, payments, geolocation, chat, or a repair-guide database until the core demo is polished.

