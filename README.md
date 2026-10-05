# Ghar Saathi

A househelp booking app. Customers book chores (sweeping, utensils, cooking, laundry, bathroom cleaning, child or elder care) for a 1, 2 or 3 BHK home, as a one-time visit or on a weekly, monthly or yearly plan. Househelps sign up with the chores they do, see open requests that match, and accept jobs.

The project has two parts:

| Part | Path | Stack |
|---|---|---|
| Front end | `Ghar Saathi.html` | One HTML file with inline CSS and plain JavaScript, no build step |
| Back end | `ghar-saathi-api/` | Python, FastAPI, SQLAlchemy, JWT sign-in, SQLite by default |

The API also serves the front end at `/`, so the page and the API share one address. Accounts and bookings live in the API's database. The browser keeps only the sign-in token.

## Project structure

```
Ghar-Saathi/
├── Ghar Saathi.html          # The whole front end (markup, styles, script)
├── .vscode/launch.json       # Launches the HTML page in Chrome from VS Code
└── ghar-saathi-api/
    ├── README.md             # API reference: settings, endpoints, design notes
    ├── requirements.txt
    ├── pytest.ini            # Lets a bare `pytest` find `app` and only run `tests/`
    ├── app/
    │   ├── main.py           # FastAPI app, routes, auth and role checks
    │   ├── models.py         # SQLAlchemy tables: User, Order
    │   ├── schemas.py        # Pydantic request and response models, validation
    │   ├── pricing.py        # Chores, prices, visit lengths, plan discounts
    │   ├── security.py       # scrypt password hashing, JWT tokens
    │   └── db.py             # Engine and session setup
    ├── tests/test_api.py     # End-to-end flow and validation tests
    └── ghar-saathi-api/      # An accidental copy of the folder above (see below)
```

## Running the app

```bash
cd ghar-saathi-api
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
SECRET_KEY="$(python -c 'import secrets; print(secrets.token_urlsafe(32))')" \
  uvicorn app.main:app --reload
```

Then open http://localhost:8000. The first start creates the database file `ghar-saathi-api/gharsaathi.db`, which git ignores.

On startup the API creates two demo accounts if they are missing (set `SEED_DEMO=0` to skip this). The sign-in screen has a "Fill it in" button for each:

| Role | Email | Password |
|---|---|---|
| Customer | `demo@gharsaathi.in` | `demo123` |
| Househelp | `helper@gharsaathi.in` | `demo123` |

A new `SECRET_KEY` on each start signs everyone out. Keep the same value between restarts to stay signed in.

Interactive API docs are at http://localhost:8000/docs.

Run the tests from inside `ghar-saathi-api`:

```bash
pytest
```

See [`ghar-saathi-api/README.md`](ghar-saathi-api/README.md) for environment variables, the endpoint list and design notes.

## How pricing works

Each chore has a per-visit price and length that depend on home size. Prices are defined in `ghar-saathi-api/app/pricing.py` (and copied into the front end's script).

| Plan | Charged | Discount |
|---|---|---|
| One-Time | Per visit | None |
| Weekly | Per visit × days per week | 5% |
| Monthly | Weekly total × 52 ÷ 12 | 12% |
| Yearly | Weekly total × 52 | 20% |

Visits can start every half hour from 6:00 am to 8:00 pm.
