import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# In production (Vercel), set DATABASE_URL to your Neon/Postgres connection string.
# Falls back to local SQLite so nothing breaks for local dev if it's unset.
# NOTE: Vercel's serverless filesystem is read-only/ephemeral, so SQLite must
# never be used in production — this fallback is for local dev only.
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./tracker.db")

# Some providers (Neon included) hand out "postgres://" URLs — SQLAlchemy 2.x
# requires the "postgresql://" scheme, so normalize it here.
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()