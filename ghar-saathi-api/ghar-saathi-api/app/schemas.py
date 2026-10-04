from datetime import date, datetime
from typing import Literal, Optional
from zoneinfo import ZoneInfo

from pydantic import BaseModel, Field, field_validator, model_validator

from .pricing import DAYS, SERVICES, START_MAX, START_MIN, START_STEP

IST = ZoneInfo("Asia/Kolkata")
EXPERIENCE = Literal["Less than 1 year", "1 to 3 years", "3 to 5 years", "5+ years"]


# ---------- requests ----------
class RegisterIn(BaseModel):
    role: Literal["user", "househelp"]
    name: str = Field(min_length=2, max_length=120)
    phone: str
    email: str = Field(max_length=254, pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
    password: str = Field(min_length=6, max_length=128)
    # househelp only
    services: Optional[list[str]] = None
    experience: Optional[EXPERIENCE] = None
    area: Optional[str] = Field(default=None, max_length=120)

    @field_validator("phone", mode="before")
    @classmethod
    def clean_phone(cls, v):
        v = "".join(str(v).split())
        import re
        if not re.fullmatch(r"[6-9]\d{9}", v):
            raise ValueError("Enter a 10-digit Indian mobile number.")
        return v

    @model_validator(mode="after")
    def check_househelp(self):
        if self.role == "househelp":
            chores = self.services or []
            if not chores:
                raise ValueError("Pick at least one chore you do.")
            if any(s not in SERVICES for s in chores):
                raise ValueError("Unknown chore in your list.")
            if not self.area or len(self.area.strip()) < 2:
                raise ValueError("Enter the area you can work in.")
        return self


class LoginIn(BaseModel):
    identifier: str = Field(min_length=3, max_length=254)  # email or mobile number
    password: str = Field(min_length=1, max_length=128)


class OrderIn(BaseModel):
    size: Literal[1, 2, 3]
    services: list[str] = Field(min_length=1)
    plan: Literal["once", "weekly", "monthly", "yearly"]
    days: list[str] = []
    start_date: date
    start_minute: int
    address: str = Field(min_length=5, max_length=500)
    notes: str = Field(default="", max_length=300)

    @model_validator(mode="after")
    def check_order(self):
        if len(set(self.services)) != len(self.services) or any(s not in SERVICES for s in self.services):
            raise ValueError("Choose each chore at most once, from the chore list.")
        if any(d not in DAYS for d in self.days) or len(set(self.days)) != len(self.days):
            raise ValueError("Days must be Mon to Sun, each at most once.")
        if self.plan != "once" and not self.days:
            raise ValueError("Pick at least one day for a recurring plan.")
        if self.plan == "once":
            self.days = []
        if self.start_date < datetime.now(IST).date():
            raise ValueError("Choose a date from today onward.")
        if not (START_MIN <= self.start_minute <= START_MAX and self.start_minute % START_STEP == 0):
            raise ValueError("Start time must be on the hour or half hour, from 6:00 am to 8:00 pm.")
        self.days = sorted(self.days, key=DAYS.index)
        return self


# ---------- responses ----------
class UserOut(BaseModel):
    id: int
    role: str
    name: str
    phone: str
    email: str
    services: list[str] = []
    experience: Optional[str] = None
    area: Optional[str] = None


class AuthOut(BaseModel):
    token: str
    user: UserOut


class PersonOut(BaseModel):
    name: str
    phone: str


class OrderOut(BaseModel):
    id: int
    ref: str
    size: int
    services: list[str]
    plan: str
    days: list[str]
    start_date: str
    start_minute: int
    duration_minutes: int
    address: str
    notes: str
    amount_inr: int
    price_unit: str
    status: str
    helper: Optional[PersonOut] = None
    created_at: datetime


class OpenJobOut(BaseModel):
    """What a househelp sees before accepting. No address, notes or customer details."""
    id: int
    ref: str
    size: int
    services: list[str]
    plan: str
    days: list[str]
    start_date: str
    start_minute: int
    duration_minutes: int
    amount_inr: int
    price_unit: str


class MyJobOut(OrderOut):
    customer: PersonOut
