import sys
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
from sqlalchemy.orm import Session

from app.database import engine, Base, SessionLocal
from app import models, auth
from app.config import settings

def ensure_database_exists():
    """
    Connect to default postgres DB and create database 'rakthasethu' if it does not exist.
    """
    db_name = "rakthasethu"
    if not settings.DATABASE_URL.startswith("postgresql"):
        return
    try:
        # Parse connection params to connect to default postgres db
        conn_str = settings.DATABASE_URL
        if f"/{db_name}" in conn_str:
            base_conn_str = conn_str.replace(f"/{db_name}", "/postgres")
        else:
            base_conn_str = conn_str

        # Connect to default postgres DB
        conn = psycopg2.connect(base_conn_str)
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cursor = conn.cursor()

        cursor.execute(f"SELECT 1 FROM pg_catalog.pg_database WHERE datname = '{db_name}';")
        exists = cursor.fetchone()
        if not exists:
            print(f"Database '{db_name}' does not exist. Creating database '{db_name}'...")
            cursor.execute(f'CREATE DATABASE "{db_name}";')
            print(f"Database '{db_name}' created successfully.")
        else:
            print(f"Database '{db_name}' already exists.")
        
        cursor.close()
        conn.close()
    except Exception as e:
        print(f"Note on DB auto-creation (Ensure PostgreSQL is running): {e}")

def seed_data():
    ensure_database_exists()
    print("Creating tables in PostgreSQL database 'rakthasethu'...")
    Base.metadata.create_all(bind=engine)
    
    db: Session = SessionLocal()
    try:
        # Check if test user exists
        test_email = "donor@rakthasethu.org"
        user = db.query(models.User).filter(models.User.email == test_email).first()
        if not user:
            print(f"Seeding default test user: {test_email}")
            test_user = models.User(
                email=test_email,
                hashed_password=auth.get_password_hash("password123"),
                full_name="Rajesh Kumar",
                phone_number="+91 9876543210",
                is_active=True,
                is_admin=True
            )
            db.add(test_user)
            db.commit()
            print("Default user seeded successfully!")
            print("Credentials: Email = donor@rakthasethu.org | Password = password123")
        else:
            print(f"Test user {test_email} already exists.")
    except Exception as e:
        print(f"Error during seeding: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    seed_data()
