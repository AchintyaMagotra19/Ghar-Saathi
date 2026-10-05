# Ghar Saathi

A househelp booking app. Customers book chores (sweeping, utensils, cooking, laundry, bathroom cleaning, child or elder care) for a 1, 2 or 3 BHK home, as a one-time visit or on a weekly, monthly or yearly plan. Househelps sign up with the chores they do, see open requests that match, and accept jobs.

The project has two parts:

| Part | Path | Stack |
|---|---|---|
| Front end | `Ghar Saathi.html` | One HTML file with inline CSS and plain JavaScript, no build step |
| Back end | `ghar-saathi-api/` | Python, FastAPI, SQLAlchemy, JWT sign-in, SQLite by default |

> **Note:** The front end does not call the API yet. It keeps accounts, bookings and the session in the browser's `localStorage`, so everything it shows lives only in that one browser. The API is complete on its own and has tests, but the two have not been connected.

## Project structure

```
Ghar-Saathi/
├── Ghar Saathi.html          # The whole front end (markup, styles, script)
├── .vscode/launch.json       # Launches the HTML page in Chrome from VS Code
└── ghar-saathi-api/
    ├── README.md             # API reference: settings, endpoints, design notes
    ├── requirements.txt
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

## Running the front end

Open `Ghar Saathi.html` in a browser. There is nothing to install.

Two demo accounts are built in, and the sign-in screen has a "Fill it in" button for each:

| Role | Email | Password |
|---|---|---|
| Customer | `demo@gharsaathi.in` | `demo123` |
| Househelp | `helper@gharsaathi.in` | `demo123` |

Because data is stored in `localStorage`, a househelp sees only requests placed from the same browser.

## Running the back end

```bash
cd ghar-saathi-api
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
SECRET_KEY="$(python -c 'import secrets; print(secrets.token_urlsafe(32))')" \
  uvicorn app.main:app --reload
```

Interactive API docs are at http://localhost:8000/docs.

Run the tests from inside `ghar-saathi-api`:

```bash
pytest tests
```

Pass `tests` explicitly. A bare `pytest` also collects the duplicate `ghar-saathi-api/ghar-saathi-api/tests/test_api.py` and stops with an import error.

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
