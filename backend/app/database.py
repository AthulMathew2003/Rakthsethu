import os
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from app.config import settings

db_url = settings.DATABASE_URL

def get_engine():
    try:
        connect_args = {"check_same_thread": False} if db_url.startswith("sqlite") else {}
        test_engine = create_engine(db_url, pool_pre_ping=True, connect_args=connect_args)
        # Test connection
        with test_engine.connect() as conn:
            pass
        return test_engine
    except Exception as e:
        print(f"PostgreSQL connection error: {e}. Falling back to SQLite database.")
        sqlite_url = "sqlite:///./rakthasethu.db"
        return create_engine(sqlite_url, connect_args={"check_same_thread": False})

engine = get_engine()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
