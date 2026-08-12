from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from app.config import settings

db_url = settings.DATABASE_URL
connect_args = {"check_same_thread": False} if db_url.startswith("sqlite") else {}

try:
    engine = create_engine(db_url, pool_pre_ping=True, connect_args=connect_args)
    # Quick connectivity test
    with engine.connect() as conn:
        pass
except Exception as e:
    print(f"Warning: Could not connect to target database ({db_url}): {e}")
    print("Falling back to local SQLite database: sqlite:///./rakthasethu.db")
    db_url = "sqlite:///./rakthasethu.db"
    engine = create_engine(db_url, connect_args={"check_same_thread": False})

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

