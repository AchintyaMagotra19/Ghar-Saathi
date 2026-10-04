import os
import tempfile
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

os.environ["DATABASE_URL"] = "sqlite:///" + os.path.join(tempfile.mkdtemp(), "test.db")
os.environ["SECRET_KEY"] = "test-secret"

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


def tomorrow():
    return (datetime.now(ZoneInfo("Asia/Kolkata")).date() + timedelta(days=1)).isoformat()


def register(client, role, email, phone, **extra):
    body = {"role": role, "name": "Test Person", "phone": phone, "email": email, "password": "secret1"}
    body.update(extra)
    return client.post("/auth/register", json=body)


def auth(token):
    return {"Authorization": f"Bearer {token}"}


ORDER = {
    "size": 2, "services": ["sweep", "utensils"], "plan": "weekly", "days": ["Fri", "Mon", "Wed"],
    "start_minute": 420, "address": "B-12, Sector 10, Dwarka, Delhi", "notes": "Gate code 1234",
}


def test_full_flow(client):
    u = register(client, "user", "asha@example.com", "9810000001")
    assert u.status_code == 201
    user_token = u.json()["token"]

    h = register(client, "househelp", "sunita@example.com", "9810000002",
                 services=["sweep", "utensils", "cook"], experience="5+ years", area="Dwarka")
    assert h.status_code == 201
    helper_token = h.json()["token"]

    # duplicate email or phone
    assert register(client, "user", "ASHA@example.com", "9810000099").status_code == 409

    # login by email and by phone, wrong password
    assert client.post("/auth/login", json={"identifier": "asha@example.com", "password": "secret1"}).status_code == 200
    assert client.post("/auth/login", json={"identifier": "9810000001", "password": "secret1"}).status_code == 200
    assert client.post("/auth/login", json={"identifier": "asha@example.com", "password": "nope"}).status_code == 401

    # create order: server computes the price (2 BHK, 450/visit, 3 days, weekly -5%)
    r = client.post("/orders", json={**ORDER, "start_date": tomorrow()}, headers=auth(user_token))
    assert r.status_code == 201, r.text
    order = r.json()
    assert order["amount_inr"] == 1283 and order["price_unit"] == "per week"
    assert order["days"] == ["Mon", "Wed", "Fri"]
    assert order["duration_minutes"] == 90

    # roles are enforced
    assert client.post("/orders", json={**ORDER, "start_date": tomorrow()}, headers=auth(helper_token)).status_code == 403
    assert client.get("/jobs/open", headers=auth(user_token)).status_code == 403
    assert client.get("/orders").status_code == 401

    # open jobs hide address, notes and customer
    jobs = client.get("/jobs/open", headers=auth(helper_token)).json()
    assert len(jobs) == 1
    assert "address" not in jobs[0] and "notes" not in jobs[0] and "customer" not in jobs[0]

    # a househelp who does not cover every chore cannot see or take it
    other = register(client, "househelp", "meena@example.com", "9810000003",
                     services=["laundry"], area="Dwarka").json()["token"]
    assert client.get("/jobs/open", headers=auth(other)).json() == []
    assert client.post(f"/jobs/{order['id']}/accept", headers=auth(other)).status_code == 403

    # accept, then a second househelp is refused
    acc = client.post(f"/jobs/{order['id']}/accept", headers=auth(helper_token))
    assert acc.status_code == 200
    assert acc.json()["address"].startswith("B-12") and acc.json()["customer"]["name"] == "Test Person"
    second = register(client, "househelp", "geeta@example.com", "9810000004",
                      services=["sweep", "utensils"], area="Dwarka").json()["token"]
    assert client.post(f"/jobs/{order['id']}/accept", headers=auth(second)).status_code == 409

    # the user sees who accepted
    mine = client.get("/orders", headers=auth(user_token)).json()
    assert mine[0]["status"] == "accepted" and mine[0]["helper"]["name"] == "Test Person"

    # drop reopens it, cancel closes it, and strangers cannot cancel
    assert client.post(f"/jobs/{order['id']}/drop", headers=auth(helper_token)).status_code == 200
    stranger = register(client, "user", "ravi@example.com", "9810000005").json()["token"]
    assert client.delete(f"/orders/{order['id']}", headers=auth(stranger)).status_code == 404
    assert client.delete(f"/orders/{order['id']}", headers=auth(user_token)).json()["status"] == "cancelled"
    assert client.get("/jobs/open", headers=auth(helper_token)).json() == []


def test_validation(client):
    assert register(client, "user", "bad", "9810000010").status_code == 422
    assert register(client, "user", "x@example.com", "12345").status_code == 422
    assert register(client, "househelp", "y@example.com", "9810000011").status_code == 422  # no chores or area
    token = register(client, "user", "z@example.com", "9810000012").json()["token"]
    bad_time = {**ORDER, "start_date": tomorrow(), "start_minute": 425}
    assert client.post("/orders", json=bad_time, headers=auth(token)).status_code == 422
    past = {**ORDER, "start_date": "2020-01-01"}
    assert client.post("/orders", json=past, headers=auth(token)).status_code == 422
    no_days = {**ORDER, "start_date": tomorrow(), "days": []}
    assert client.post("/orders", json=no_days, headers=auth(token)).status_code == 422
    once = {**ORDER, "start_date": tomorrow(), "plan": "once", "days": []}
    r = client.post("/orders", json=once, headers=auth(token))
    assert r.status_code == 201 and r.json()["amount_inr"] == 450
