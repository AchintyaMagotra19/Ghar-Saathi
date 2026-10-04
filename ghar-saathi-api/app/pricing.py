"""Prices and visit lengths live here, on the server, so a client can never set its own price."""

SIZES = (1, 2, 3)  # BHK

SERVICES = {
    "sweep":    {"name": "Sweeping and mopping",  "prices": {1: 200, 2: 300, 3: 400}, "mins": {1: 45, 2: 60, 3: 90}},
    "utensils": {"name": "Utensils",              "prices": {1: 120, 2: 150, 3: 180}, "mins": {1: 20, 2: 30, 3: 40}},
    "cook":     {"name": "Cooking",               "prices": {1: 300, 2: 350, 3: 400}, "mins": {1: 60, 2: 75, 3: 90}},
    "laundry":  {"name": "Laundry",               "prices": {1: 180, 2: 200, 3: 250}, "mins": {1: 30, 2: 40, 3: 50}},
    "bath":     {"name": "Bathroom cleaning",     "prices": {1: 200, 2: 350, 3: 450}, "mins": {1: 30, 2: 45, 3: 60}},
    "care":     {"name": "Child or elder care",   "prices": {1: 500, 2: 500, 3: 500}, "mins": {1: 240, 2: 240, 3: 240}},
}

PLANS = {
    "once":    {"name": "One-Time", "discount_pct": 0,  "unit": "one visit"},
    "weekly":  {"name": "Weekly",   "discount_pct": 5,  "unit": "per week"},
    "monthly": {"name": "Monthly",  "discount_pct": 12, "unit": "per month"},
    "yearly":  {"name": "Yearly",   "discount_pct": 20, "unit": "per year"},
}

DAYS = ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")

START_MIN = 6 * 60    # 6:00 am, in minutes from midnight
START_MAX = 20 * 60   # 8:00 pm
START_STEP = 30


def _round(x: float) -> int:
    return int(x + 0.5)  # round half up, same as the front end


def per_visit(size: int, services: list[str]) -> int:
    return sum(SERVICES[s]["prices"][size] for s in services)


def duration_minutes(size: int, services: list[str]) -> int:
    return sum(SERVICES[s]["mins"][size] for s in services)


def quote(size: int, services: list[str], plan: str, days: list[str]) -> tuple[int, str]:
    """Return (amount in rupees, unit) for what the customer pays per billing period."""
    visit = per_visit(size, services)
    gross = visit * max(len(days), 1)
    if plan == "once":
        return visit, PLANS["once"]["unit"]
    if plan == "weekly":
        return _round(gross * 0.95), PLANS["weekly"]["unit"]
    if plan == "monthly":
        return _round(gross * 52 / 12 * 0.88), PLANS["monthly"]["unit"]
    return _round(gross * 52 * 0.80), PLANS["yearly"]["unit"]
