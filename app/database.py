from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool
from pydantic_settings import BaseSettings, SettingsConfigDict
import os
from dotenv import load_dotenv

load_dotenv()


def _get_engine_url() -> str:
    """Return DATABASE_URL, normalizing PostgreSQL for Supabase (use psycopg2 driver)."""
    url = os.getenv("DATABASE_URL", "mysql+pymysql://root:password@localhost:3306/factory_management")
    # Supabase (and plain postgresql://) work with psycopg2; make driver explicit
    if url.startswith("postgresql://") and "+" not in url.split("://")[0]:
        url = url.replace("postgresql://", "postgresql+psycopg2://", 1)
    return url


def _use_null_pool() -> bool:
    """Use NullPool for Supabase pooler (serverless) to avoid connection issues."""
    url = os.getenv("DATABASE_URL", "")
    if os.getenv("USE_SUPABASE_POOLER", "").lower() in ("1", "true", "yes"):
        return True
    return "pooler.supabase.com" in url


class Settings(BaseSettings):
    database_url: str = os.getenv("DATABASE_URL", "mysql+pymysql://root:password@localhost:3306/factory_management")

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore"  # Ignore extra fields from .env file
    )


settings = Settings()
engine_url = _get_engine_url()

engine = create_engine(
    engine_url,
    pool_pre_ping=True,
    pool_recycle=300,
    echo=False,
    poolclass=NullPool if _use_null_pool() else None,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

