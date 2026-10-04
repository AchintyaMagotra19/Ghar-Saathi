# Ghar Saathi API

Backend for the Ghar Saathi househelp booking app. FastAPI, SQLAlchemy, JWT sign-in.

## Run it

```bash
cd ghar-saathi-api
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
SECRET_KEY="$(python -c 'import secrets; print(secrets.token_urlsafe(32))')" \
  uvicorn app.main:app --reload
```

Open http://localhost:8000/docs for interactive API docs. Run the tests with `pytest`.

## Settings

| Variable | Default | Purpose |
|---|---|---|
| `SECRET_KEY` | dev value (warns) | Signs login tokens. Always set it in production. |
| `DATABASE_URL` | `sqlite:///./gharsaathi.db` | Use `postgresql+psycopg://user:pass@host/db` for PostgreSQL (also `pip install "psycopg[binary]"`). |
| `CORS_ORIGINS` | `http://localhost:3000` | Comma-separated sites allowed to call the API. |

## Endpoints

| Method | Path | Who | What |
|---|---|---|---|
| GET | `/catalog` | anyone | Chores, prices by BHK, visit minutes, plans, days, start times |
| POST | `/auth/register` | anyone | Create a `user` or `househelp` account |
| POST | `/auth/login` | anyone | Sign in with email or mobile number |
| GET | `/me` | signed in | Current account |
| POST | `/orders` | user | Place an order. The server calculates the price |
| GET | `/orders` | user | Your orders, with the househelp once one accepts |
| DELETE | `/orders/{id}` | user | Cancel your order |
| GET | `/jobs/open` | househelp | Open orders whose chores are all on your profile |
| POST | `/jobs/{id}/accept` | househelp | Take a job. Returns the address and customer |
| POST | `/jobs/{id}/drop` | househelp | Give a job back |
| GET | `/jobs/mine` | househelp | Jobs you accepted |

Send the token from login as `Authorization: Bearer <token>`.

## Design notes

- Prices and visit lengths live in `app/pricing.py`. The page never sends a price.
- A househelp sees an open job without its address, notes or customer. Those appear only after accepting.
- Accepting is one atomic database update, so two househelps cannot take the same job.
- Passwords are hashed with scrypt. Login gives the same error for an unknown account and a wrong password.

## Not built yet

Rate limiting on login, phone number verification by OTP, payments, ID checks for househelps, and ratings. Add rate limiting and HTTPS before real users sign up.
