import os
import secrets
from contextlib import asynccontextmanager
from pathlib import Path

import jwt
from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import or_, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from . import pricing
from .db import Base, SessionLocal, engine, get_db
from .models import Order, User
from .schemas import (AuthOut, LoginIn, MyJobOut, OpenJobOut, OrderIn, OrderOut,
                      PersonOut, RegisterIn, UserOut)
from .security import create_token, decode_token, hash_password, verify_password


FRONTEND = Path(__file__).resolve().parents[2] / "Ghar Saathi.html"

# Sign-in screen has "Fill it in" buttons for these. Set SEED_DEMO=0 to skip creating them.
DEMO_ACCOUNTS = [
    dict(role="user", name="Demo User", phone="9810012345", email="demo@gharsaathi.in"),
    dict(role="househelp", name="Sunita Devi", phone="9810055555", email="helper@gharsaathi.in",
         services="sweep,utensils,cook,laundry,bath", experience="5+ years", area="Dwarka, Delhi"),
]


def seed_demo_accounts():
    with SessionLocal() as db:
        for acct in DEMO_ACCOUNTS:
            exists = db.scalar(select(User).where(or_(User.email == acct["email"], User.phone == acct["phone"])))
            if not exists:
                db.add(User(**acct, password_hash=hash_password("demo123")))
        db.commit()


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(engine)
    if os.environ.get("SEED_DEMO", "1") != "0":
        seed_demo_accounts()
    yield


app = FastAPI(title="Ghar Saathi API", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in os.environ.get("CORS_ORIGINS", "http://localhost:3000").split(",")],
    allow_methods=["*"],
    allow_headers=["*"],
)

bearer = HTTPBearer(auto_error=False)
_DUMMY_HASH = hash_password("not-a-real-password")  # keeps login timing similar for unknown accounts


# ---------- helpers ----------
def split(csv: str) -> list[str]:
    return [x for x in csv.split(",") if x]


def user_out(u: User) -> UserOut:
    return UserOut(id=u.id, role=u.role, name=u.name, phone=u.phone, email=u.email,
                   services=split(u.services), experience=u.experience, area=u.area)


def order_fields(o: Order) -> dict:
    services = split(o.services)
    return dict(
        id=o.id, ref=o.ref, size=o.size, services=services, plan=o.plan, days=split(o.days),
        start_date=o.start_date, start_minute=o.start_minute,
        duration_minutes=pricing.duration_minutes(o.size, services),
        address=o.address, notes=o.notes, amount_inr=o.amount_inr, price_unit=o.price_unit,
        status=o.status, created_at=o.created_at,
        helper=PersonOut(name=o.helper.name, phone=o.helper.phone) if o.helper else None,
    )


def order_out(o: Order) -> OrderOut:
    return OrderOut(**order_fields(o))


def my_job_out(o: Order) -> MyJobOut:
    return MyJobOut(**order_fields(o), customer=PersonOut(name=o.customer.name, phone=o.customer.phone))


def open_job_out(o: Order) -> OpenJobOut:
    f = order_fields(o)
    keep = OpenJobOut.model_fields.keys()
    return OpenJobOut(**{k: v for k, v in f.items() if k in keep})


def current_user(creds: HTTPAuthorizationCredentials | None = Depends(bearer),
                 db: Session = Depends(get_db)) -> User:
    if creds is None:
        raise HTTPException(401, "Sign in first.")
    try:
        payload = decode_token(creds.credentials)
        user = db.get(User, int(payload["sub"]))
    except (jwt.PyJWTError, KeyError, ValueError):
        raise HTTPException(401, "Your session has expired. Sign in again.")
    if user is None:
        raise HTTPException(401, "Your session has expired. Sign in again.")
    return user


def require_role(role: str):
    def dep(user: User = Depends(current_user)) -> User:
        if user.role != role:
            raise HTTPException(403, "This action is not available for your account type.")
        return user
    return dep


# ---------- public ----------
@app.get("/", include_in_schema=False)
def frontend():
    return FileResponse(FRONTEND)


@app.get("/health")
def health():
    return {"ok": True}


@app.get("/catalog")
def catalog():
    return {
        "sizes": list(pricing.SIZES),
        "services": [
            {"id": sid, "name": s["name"], "prices": s["prices"], "minutes": s["mins"]}
            for sid, s in pricing.SERVICES.items()
        ],
        "plans": pricing.PLANS,
        "days": list(pricing.DAYS),
        "start_times": {"first": pricing.START_MIN, "last": pricing.START_MAX, "step": pricing.START_STEP},
    }


# ---------- auth ----------
@app.post("/auth/register", response_model=AuthOut, status_code=201)
def register(body: RegisterIn, db: Session = Depends(get_db)):
    email = body.email.strip().lower()
    taken = db.scalar(select(User).where(or_(User.email == email, User.phone == body.phone)))
    if taken:
        raise HTTPException(409, "An account with that email or number already exists. Sign in instead.")
    user = User(
        role=body.role, name=body.name.strip(), phone=body.phone, email=email,
        password_hash=hash_password(body.password),
        services=",".join(body.services or []) if body.role == "househelp" else "",
        experience=body.experience if body.role == "househelp" else None,
        area=body.area.strip() if body.role == "househelp" and body.area else None,
    )
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "An account with that email or number already exists. Sign in instead.")
    return AuthOut(token=create_token(user.id, user.role), user=user_out(user))


@app.post("/auth/login", response_model=AuthOut)
def login(body: LoginIn, db: Session = Depends(get_db)):
    ident = body.identifier.strip().lower()
    digits = "".join(ident.split())
    user = db.scalar(select(User).where(or_(User.email == ident, User.phone == digits)))
    ok = verify_password(body.password, user.password_hash if user else _DUMMY_HASH)
    if not user or not ok:
        raise HTTPException(401, "Wrong email, number or password.")
    return AuthOut(token=create_token(user.id, user.role), user=user_out(user))


@app.get("/me", response_model=UserOut)
def me(user: User = Depends(current_user)):
    return user_out(user)


# ---------- orders (users) ----------
@app.post("/orders", response_model=OrderOut, status_code=201)
def create_order(body: OrderIn, user: User = Depends(require_role("user")), db: Session = Depends(get_db)):
    amount, unit = pricing.quote(body.size, body.services, body.plan, body.days)
    order = Order(
        ref="GS" + "".join(secrets.choice("0123456789") for _ in range(8)),
        customer_id=user.id, size=body.size, services=",".join(body.services), plan=body.plan,
        days=",".join(body.days), start_date=body.start_date.isoformat(), start_minute=body.start_minute,
        address=body.address.strip(), notes=body.notes.strip(), amount_inr=amount, price_unit=unit,
    )
    db.add(order)
    db.commit()
    return order_out(order)


@app.get("/orders", response_model=list[OrderOut])
def my_orders(user: User = Depends(require_role("user")), db: Session = Depends(get_db)):
    rows = db.scalars(select(Order).where(Order.customer_id == user.id).order_by(Order.id.desc())).all()
    return [order_out(o) for o in rows]


@app.delete("/orders/{order_id}", response_model=OrderOut)
def cancel_order(order_id: int, user: User = Depends(require_role("user")), db: Session = Depends(get_db)):
    order = db.get(Order, order_id)
    if order is None or order.customer_id != user.id:
        raise HTTPException(404, "Order not found.")
    if order.status == "cancelled":
        raise HTTPException(409, "This order is already cancelled.")
    order.status = "cancelled"
    order.helper_id = None
    db.commit()
    return order_out(order)


# ---------- jobs (househelps) ----------
@app.get("/jobs/open", response_model=list[OpenJobOut])
def open_jobs(user: User = Depends(require_role("househelp")), db: Session = Depends(get_db)):
    mine = set(split(user.services))
    rows = db.scalars(
        select(Order).where(Order.status == "open", Order.helper_id.is_(None)).order_by(Order.id.desc())
    ).all()
    return [open_job_out(o) for o in rows if set(split(o.services)) <= mine]


@app.get("/jobs/mine", response_model=list[MyJobOut])
def my_jobs(user: User = Depends(require_role("househelp")), db: Session = Depends(get_db)):
    rows = db.scalars(select(Order).where(Order.helper_id == user.id).order_by(Order.id.desc())).all()
    return [my_job_out(o) for o in rows]


@app.post("/jobs/{order_id}/accept", response_model=MyJobOut)
def accept_job(order_id: int, user: User = Depends(require_role("househelp")), db: Session = Depends(get_db)):
    order = db.get(Order, order_id)
    if order is None or order.status == "cancelled":
        raise HTTPException(404, "This job is no longer available.")
    if not set(split(order.services)) <= set(split(user.services)):
        raise HTTPException(403, "This job includes chores that are not on your profile.")
    # One atomic update, so two househelps cannot both take the same job.
    result = db.execute(
        update(Order)
        .where(Order.id == order_id, Order.helper_id.is_(None), Order.status == "open")
        .values(helper_id=user.id, status="accepted")
    )
    db.commit()
    if result.rowcount == 0:
        raise HTTPException(409, "Another househelp already took this job.")
    db.refresh(order)
    return my_job_out(order)


@app.post("/jobs/{order_id}/drop", response_model=OpenJobOut)
def drop_job(order_id: int, user: User = Depends(require_role("househelp")), db: Session = Depends(get_db)):
    order = db.get(Order, order_id)
    if order is None or order.helper_id != user.id:
        raise HTTPException(404, "Job not found.")
    order.helper_id = None
    order.status = "open"
    db.commit()
    return open_job_out(order)
