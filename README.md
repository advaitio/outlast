# Outlast

Outlast is a community repair app built for the LifeHack hackathon. Before replacing or
discarding a broken household item, a user can assess it with AI, post a repair request, collect
suggestions, recognise successful helpers, and track the waste avoided.

The prototype focuses on one behaviour:

> Give a broken item one informed community repair attempt before replacing it.

## Features

- Photo-and-description item reports with structured OpenAI assessment.
- Safe offline fallback when no OpenAI key is configured.
- Community listings, suggestions, owner-managed outcomes, and before/after photos.
- Responsible-disposal guidance and searchable Singapore NEA e-waste collection points.
- Individual XP, streaks, solver recognition, and a community leaderboard.
- Optional Supabase persistence for listings, images, contributions, XP, and activity history.
- Seeded demo users and data for credential-free local testing.

## Requirements

- Python 3.11 or newer
- Git
- An OpenAI API key for real AI and image assessment (optional)
- A Supabase project for shared persistence (optional)

## Quick start

Clone the repository and enter its directory:

```bash
git clone https://github.com/advaitio/outlast.git
cd outlast
```

Create a virtual environment and install the development dependencies:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements-dev.txt
```

On Windows PowerShell, activate the environment with:

```powershell
.venv\Scripts\Activate.ps1
```

Start the application:

```bash
streamlit run app.py
```

Open the URL printed by Streamlit, normally [http://localhost:8501](http://localhost:8501).
The app starts in demo mode if no API credentials are configured.

## Configure API keys

Copy the included secrets template:

```bash
cp .streamlit/secrets.toml.example .streamlit/secrets.toml
```

Add the services you want to enable:

```toml
OPENAI_API_KEY = "your-openai-api-key"
OPENAI_MODEL = "gpt-5.6-luna"

SUPABASE_URL = "https://your-project.supabase.co"
SUPABASE_KEY = "your-supabase-anon-key"
```

- `OPENAI_API_KEY` enables real text-and-image assessment and disposal guidance.
- `OPENAI_MODEL` is optional; the template contains the default model.
- `SUPABASE_URL` and `SUPABASE_KEY` must both be present to enable remote persistence.
- OpenAI can be enabled without Supabase, and Supabase can be enabled without OpenAI.

Restart Streamlit after changing the secrets file. Never commit `.streamlit/secrets.toml`, an
`.env` file, API keys, or a Supabase service-role key.

## Optional Supabase setup

The application uses local Streamlit session state when Supabase is not configured. To enable
shared data:

1. Create a Supabase project.
2. Open its SQL Editor.
3. Run [`supabase/schema.sql`](supabase/schema.sql).
4. Run [`supabase/atomic_persistence.sql`](supabase/atomic_persistence.sql) afterward.
5. Add the project URL and anon key to `.streamlit/secrets.toml`.
6. Restart the application.

The first script creates players, listings, contributions, solver records, activity history, and
the `rescue-images` Storage bucket. The second adds transactional functions for XP-sensitive
writes and the prototype image-upload policy.

The included policies are suitable only for this hackathon prototype. Replace the fake identity
selector and prototype policies with Supabase Auth and production RLS rules before using real
user data.

## Run automated tests

Activate the virtual environment, then run:

```bash
source .venv/bin/activate
python -m pytest -q
python -m ruff check .
```

Optional syntax check:

```bash
python -m py_compile app.py outlast/*.py
```

The same pytest and Ruff checks run in GitHub Actions for pushes to `main` and pull requests.

## Test the application manually

### 1. Report an item

1. Start the app and select **Report** in the header.
2. Confirm the page says **AI analysis is ready** when testing with an OpenAI key. If it says
   demo mode, check `.streamlit/secrets.toml` and restart Streamlit.
3. Upload a JPG, PNG, or WebP photo.
4. Enter a specific symptom, for example:

   ```text
   My desk fan hums, but the blades no longer turn.
   ```

5. Select **Assess item**.
6. Verify the private pre-post assessment includes a varied title, reason, recommended next step,
   difficulty, and estimated waste.
7. Select **Post repair request**.

### 2. Verify the listing and contribution flow

1. Open **Listings → My listings** and confirm the new item and photo appear.
2. Open the profile control in the header and switch to a different demo player.
3. Open **Listings → Community listings** and select **View item** on the new listing.
4. Enter a useful suggestion and select **Post contribution**.
5. Confirm that the contributor receives XP.
6. Switch back to the original poster and confirm the contribution appears on the item.

### 3. Resolve a successful repair

1. As the original poster, open **Listings → My listings → View item**.
2. Under **Manage your listing**, choose **Repair** as the outcome.
3. Select one or more helpers under **Who helped solve it?**
4. Optionally upload an after photo.
5. Select **Resolve item**.
6. Open **Dashboard** and verify the completed repair, XP awards, activity, waste impact, and
   leaderboard changes.

### 4. Test responsible disposal

1. Open an unresolved item owned by the current player.
2. Generate the owner guidance under the responsible-disposal section.
3. Choose **Recycle / dispose responsibly** as the outcome.
4. Search for and select an exact NEA collection point.
5. Optionally upload a collection-point evidence photo for the evidence XP bonus.
6. Resolve the item and verify that it is recorded as a responsible exit rather than a repaired
   item.

If Supabase is not configured, restart Streamlit to begin with fresh session data. If Supabase is
configured, use **Refresh community data** in the profile control to reload shared data.

## XP rules

| Activity | Base XP |
| --- | ---: |
| Post a contribution | 20 |
| Resolve an owned item | 50 |
| Be selected as a solver | 100 |
| Add disposal evidence | 30 |

Awards use the recipient's active calendar-day streak multiplier:

| Active streak | Multiplier |
| --- | ---: |
| 1–2 days | 1.0× |
| 3–6 days | 1.1× |
| 7–13 days | 1.25× |
| 14+ days | 1.5× |

Environmental impact values are prototype estimates, not audited measurements.

## Project structure

```text
app.py                              Streamlit interface and navigation
outlast/ai.py                       OpenAI prompts and offline fallbacks
outlast/db.py                       Optional Supabase repository
outlast/ewaste.py                   Singapore e-waste collection-point search
outlast/images.py                   Image normalisation for display
outlast/models.py                   Structured application models
outlast/scoring.py                  XP, streak, and impact calculations
outlast/seed.py                     Demo users, listings, and scores
outlast/state.py                    Application actions and session state
supabase/schema.sql                 Database, storage, and prototype policies
supabase/atomic_persistence.sql     Transactional XP and completion functions
tests/                              Unit and regression tests
.github/workflows/ci.yml            Continuous integration checks
```

## Troubleshooting

### The app says demo mode

Confirm `.streamlit/secrets.toml` exists, contains a valid `OPENAI_API_KEY`, and uses valid TOML
quotes. Restart Streamlit after editing it.

### OpenAI assessment fails

Check the terminal for the API error, confirm the configured model is available to the project,
and verify that the API key has active quota. The app falls back automatically only when no key
is configured; a configured but invalid key surfaces an error for correction.

### Supabase data does not load

Confirm both Supabase secrets are set and that the SQL scripts were run in the documented order.
Use the header refresh action after fixing the connection.

### Uploaded images do not appear

In local demo mode, images live only in the current Streamlit session. With Supabase enabled,
confirm that the `rescue-images` bucket and its upload policy were created by the SQL setup.
