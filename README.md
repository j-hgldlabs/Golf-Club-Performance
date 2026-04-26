# Golf Performance Dashboard

A full-stack golf analytics application built on **Garmin R10 launch monitor data**. Upload session CSVs, store them in Supabase, compute analytics, and explore results in an interactive Streamlit dashboard.

---

## Architecture overview

```
┌─────────────────────────────┐     HTTP/JWT      ┌───────────────────────────┐
│   Streamlit frontend        │ ◄────────────────► │  FastAPI backend          │
│   app/streamlit_app.py      │                    │  api/main.py              │
└─────────────────────────────┘                    └───────────┬───────────────┘
                                                               │
                                                   ┌───────────▼───────────────┐
                                                   │  Supabase                 │
                                                   │  • Auth (JWT)             │
                                                   │  • Postgres DB            │
                                                   │  • Storage (raw CSVs)     │
                                                   └───────────────────────────┘
```

The analytics engine (`src/golf_analytics/`) is a pure-Python library shared by both the API and the Streamlit frontend.

---

## Features

### Authentication
- Email/password login via Supabase Auth (JWT-secured)
- Role-based access: `user` and `admin`
- Session state managed in Streamlit; token passed to every API call

### Session management
- Upload one or more Garmin R10 CSV files from the sidebar
- Raw CSVs are stored in Supabase Storage (`raw-sessions` bucket)
- Shot rows are parsed and inserted into the `shots` Postgres table
- Sessions can be listed and deleted per user

### Analytics generation
- Click **Generate analytics** to recompute all deliverables from your stored shots
- Results are cached in the `club_summaries` Postgres table
- Computations use the `golf_analytics` engine — no raw data leaves the backend

### Dashboard tabs

| Tab | Contents |
|-----|----------|
| **Distance dashboard** | Avg carry per club, longest/shortest club metrics, Altair comparison chart, Pygwalker drag-and-drop explorer |
| **Notebook deliverables** | Club summary table, face-to-path variance table, carry averages (p10/p50/p90) — each downloadable as CSV |
| **Notebook visualizations** | Finish dispersion scatter, start-vs-curve scatter, per-club dispersion selector, shot-shape summary table |
| **Performance metrics** | Club speed, ball speed, apex height, carry, total distance, spin rate, and smash factor — all by club |

### Admin controls (admin role only)
- Invite new users by email (Supabase magic-link)
- View all registered users with email, role, created date, and last sign-in
- Update a user's role (`user` ↔ `admin`)
- Delete a user and all their associated data

---

## Project layout

```
golf_project_refactored_plus_viz/
├── api/                          # FastAPI backend
│   ├── main.py                   # App entrypoint, CORS, router registration
│   ├── auth.py                   # JWT dependency (get_current_user, require_admin)
│   ├── db.py                     # Supabase client dependency
│   ├── schema.sql                # Postgres schema (sessions, shots, club_summaries)
│   └── routers/
│       ├── auth.py               # POST /auth/login
│       ├── sessions.py           # POST /sessions/upload, GET /, DELETE /{id}
│       ├── analytics.py          # POST /generate, GET /summary, /carry-averages,
│       │                         #   /face-variance, /shot-shapes, /avg-carry, /shots
│       └── admin.py              # GET/POST/PATCH/DELETE /admin/users
│
├── src/golf_analytics/           # Reusable analytics engine
│   ├── api_client.py             # HTTP client wrapper (login, upload, generate, fetch)
│   ├── cleaning/
│   │   └── normalize.py          # Normalize avg-carry DataFrame
│   ├── io/
│   │   ├── loaders.py            # Load avg_carry_yds.csv from file/upload
│   │   └── raw_sessions.py       # Parse raw Garmin R10 session CSVs
│   ├── metrics/
│   │   ├── deliverables.py       # compute_club_summary, face_variance, carry_averages
│   │   ├── notebook_metrics.py   # start/curve/finish, shape labels, shape summary
│   │   └── summary.py            # CarrySummary (longest/shortest club)
│   ├── viz/
│   │   ├── charts.py             # carry_comparison_chart (Altair)
│   │   └── notebook_charts.py    # finish_dispersion, start_vs_curve,
│   │                             #   club_dispersion, performance_metrics
│   └── app/
│       └── streamlit_app.py      # Streamlit UI (mirrors app/streamlit_app.py)
│
├── app/
│   ├── streamlit_app.py          # Streamlit entrypoint (thin wrapper around src/)
│   └── _legacy_club_performance_dashboard_streamlit.py  # Original prototype (reference)
│
├── tests/
│   └── test_loaders.py
│
├── .env.example                  # Required environment variables
├── pyproject.toml                # Package metadata and dependencies
└── requirements.txt
```

---

## Quick start

### 1. Install dependencies

```bash
python -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install -e ".[dev,api]"
```

### 2. Configure environment

```bash
cp .env.example .env
# Fill in SUPABASE_URL, SUPABASE_KEY, SUPABASE_SERVICE_KEY
```

Credentials are in the Supabase dashboard under **Project Settings → API**.

### 3. Set up the database

Open the Supabase SQL Editor and run the contents of `api/schema.sql`. It is idempotent — safe to re-run.

This creates three tables with Row Level Security enabled:
- `sessions` — one row per uploaded CSV file
- `shots` — one row per individual shot
- `club_summaries` — cached computed analytics

### 4. Run the API

```bash
uvicorn api.main:app --reload
# Runs on http://localhost:8000
# Interactive docs at http://localhost:8000/docs
```

### 5. Run the Streamlit app

```bash
streamlit run app/streamlit_app.py
# Runs on http://localhost:8501
```

---

## API reference

All routes (except `/auth/login` and `/health`) require a `Bearer <token>` header.

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/health` | Health check |
| `POST` | `/auth/login` | Exchange email/password for a JWT |
| `POST` | `/auth/refresh` | Exchange a refresh token for a new access token |
| `POST` | `/sessions/upload` | Upload a Garmin R10 CSV; stores raw file + imports shots |
| `GET` | `/sessions/` | List all sessions for the authenticated user |
| `DELETE` | `/sessions/{id}` | Delete a session and its shots |
| `POST` | `/analytics/generate` | Recompute deliverables from stored shots |
| `GET` | `/analytics/summary` | Cached club summary |
| `GET` | `/analytics/carry-averages` | Carry distance percentiles (p10/p50/p90) per club |
| `GET` | `/analytics/face-variance` | Face-to-path variance and shape bias per club |
| `GET` | `/analytics/shot-shapes` | Draw/fade/straight classification per club |
| `GET` | `/analytics/avg-carry` | Base carry + wind-adjusted distances per club |
| `GET` | `/analytics/shots` | All raw shots in analytics-engine column format |
| `GET` | `/admin/users` | List all users *(admin only)* |
| `POST` | `/admin/invite` | Invite a new user by email *(admin only — requires a public Site URL; use Supabase dashboard to set passwords on localhost)* |
| `PATCH` | `/admin/users/role` | Update a user's role *(admin only)* |
| `DELETE` | `/admin/users/{id}` | Delete a user and all their data *(admin only)* |

---

## Wind adjustment model

The `/analytics/avg-carry` endpoint (and Distance dashboard tab) applies the following wind model on top of each club's mean carry:

**Headwind** — ball plays longer; effective yardage increases ~1% per mph

| Wind range | Adjustment |
|------------|-----------|
| 0–5 mph | −5% |
| 5–10 mph | −10% |
| 10–20 mph | −20% |
| 20–30 mph | −30% |

**Tailwind** — ball plays shorter; carry bonus is roughly half the headwind penalty

| Wind range | Adjustment |
|------------|-----------|
| 0–5 mph | +2% |
| 5–10 mph | +4% |
| 10–20 mph | +8% |
| 20–30 mph | +12% |

---

## Input data format

Each Garmin R10 session CSV must include the following columns (extra columns are ignored):

| Column | Description |
|--------|-------------|
| `Club Type` | Short club name (e.g. `D`, `3W`, `7i`, `SW`, `LW`) |
| `Club Speed` | Club head speed (mph) |
| `Ball Speed` | Ball speed (mph) |
| `Smash Factor` | Ball speed ÷ club speed |
| `Launch Angle` | Vertical launch angle (°) |
| `Launch Direction` | Horizontal launch direction (°) |
| `Club Path` | Club path (°, negative = in-to-out) |
| `Club Face` | Club face angle at impact (°) |
| `Face to Path` | Club face minus club path (°) |
| `Attack Angle` | Angle of attack (°) |
| `Backspin` | Backspin (rpm) |
| `Sidespin` | Sidespin (rpm) |
| `Spin Rate` | Total spin rate (rpm) |
| `Spin Axis` | Spin axis tilt (°) |
| `Apex Height` | Peak ball height (ft) |
| `Carry Distance` | Carry distance (yds) |
| `Carry Deviation Angle` | Carry offline angle (°) |
| `Carry Deviation Distance` | Carry offline distance (yds) |
| `Total Distance` | Total distance including roll (yds) |
| `Total Deviation Angle` | Total offline angle (°) |
| `Total Deviation Distance` | Total offline distance (yds) |

---

## Development

### Run tests

```bash
pytest -q
```

### Lint

```bash
ruff check src/ api/ app/ tests/
```

### Dependencies

| Extra | Installs |
|-------|---------|
| *(none)* | `pandas`, `streamlit`, `altair`, `pygwalker`, `requests`, `python-dotenv` |
| `[dev]` | `pytest`, `ruff` |
| `[api]` | `fastapi`, `uvicorn`, `supabase`, `python-multipart`, `pydantic[email]` |
