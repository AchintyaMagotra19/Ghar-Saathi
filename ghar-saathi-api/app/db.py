import os

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

# SQLite by default so the API runs with no setup.
# For PostgreSQL set DATABASE_URL, e.g. postgresql+psycopg://user:pass@host/gharsaathi
DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///./gharsaathi.db")

connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
