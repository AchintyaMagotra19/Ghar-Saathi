from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base


def _now() -> datetime:
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    role: Mapped[str] = mapped_column(String(16), index=True)  # "user" or "househelp"
    name: Mapped[str] = mapped_column(String(120))
    phone: Mapped[str] = mapped_column(String(10), unique=True)
    email: Mapped[str] = mapped_column(String(254), unique=True)
    password_hash: Mapped[str] = mapped_column(String(256))
    # househelp-only profile
    services: Mapped[str] = mapped_column(String(200), default="")  # comma separated service ids
    experience: Mapped[str | None] = mapped_column(String(40), nullable=True)
    area: Mapped[str | None] = mapped_column(String(120), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class Order(Base):
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(primary_key=True)
    ref: Mapped[str] = mapped_column(String(12), unique=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    helper_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    size: Mapped[int] = mapped_column(Integer)
    services: Mapped[str] = mapped_column(String(200))  # comma separated service ids
    plan: Mapped[str] = mapped_column(String(16))
    days: Mapped[str] = mapped_column(String(40), default="")  # comma separated, empty for one-time
    start_date: Mapped[str] = mapped_column(String(10))  # YYYY-MM-DD
    start_minute: Mapped[int] = mapped_column(Integer)  # minutes from midnight
    address: Mapped[str] = mapped_column(Text)
    notes: Mapped[str] = mapped_column(Text, default="")
    amount_inr: Mapped[int] = mapped_column(Integer)
    price_unit: Mapped[str] = mapped_column(String(20))
    status: Mapped[str] = mapped_column(String(16), default="open", index=True)  # open, accepted, cancelled
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    customer: Mapped[User] = relationship(foreign_keys=[customer_id])
    helper: Mapped[User | None] = relationship(foreign_keys=[helper_id])
