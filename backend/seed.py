import sys
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
from sqlalchemy.orm import Session
from datetime import datetime

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
        conn_str = settings.DATABASE_URL
        if f"/{db_name}" in conn_str:
            base_conn_str = conn_str.replace(f"/{db_name}", "/postgres")
        else:
            base_conn_str = conn_str

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
    print("Creating all tables in PostgreSQL database 'rakthasethu'...")
    Base.metadata.create_all(bind=engine)
    
    db: Session = SessionLocal()
    try:
        # 1. Seed Users (Admin & Staff)
        admin_email = "sruthy.admin@rakthasethu.org"
        admin_user = db.query(models.User).filter(models.User.email == admin_email).first()
        if not admin_user:
            print("Seeding Admin user (Sruthy M S)...")
            db.add(models.User(
                email=admin_email,
                hashed_password=auth.get_password_hash("password123"),
                full_name="Sruthy M S",
                phone_number="+91 98456 78901",
                role="Admin",
                is_active=True,
                is_admin=True
            ))
            
        test_email = "donor@rakthasethu.org"
        test_user = db.query(models.User).filter(models.User.email == test_email).first()
        if not test_user:
            print("Seeding test user...")
            db.add(models.User(
                email=test_email,
                hashed_password=auth.get_password_hash("password123"),
                full_name="Rajesh Kumar",
                phone_number="+91 9876543210",
                role="Staff",
                is_active=True,
                is_admin=False
            ))
        db.commit()

        # 2. Seed Blood Inventory (All 8 blood groups)
        inventory_defaults = [
            {"blood_group": "A+", "units_available": 80, "units_reserved": 12, "min_threshold": 30, "status": "Sufficient"},
            {"blood_group": "A−", "units_available": 28, "units_reserved": 4, "min_threshold": 20, "status": "Sufficient"},
            {"blood_group": "B+", "units_available": 60, "units_reserved": 8, "min_threshold": 25, "status": "Sufficient"},
            {"blood_group": "B−", "units_available": 20, "units_reserved": 2, "min_threshold": 15, "status": "Low"},
            {"blood_group": "O+", "units_available": 90, "units_reserved": 15, "min_threshold": 35, "status": "Sufficient"},
            {"blood_group": "O−", "units_available": 25, "units_reserved": 5, "min_threshold": 20, "status": "Low"},
            {"blood_group": "AB+", "units_available": 12, "units_reserved": 2, "min_threshold": 15, "status": "Critical"},
            {"blood_group": "AB−", "units_available": 5, "units_reserved": 1, "min_threshold": 10, "status": "Critical"},
        ]
        
        for inv_data in inventory_defaults:
            existing_inv = db.query(models.BloodInventory).filter(
                models.BloodInventory.blood_group == inv_data["blood_group"]
            ).first()
            if not existing_inv:
                db.add(models.BloodInventory(**inv_data))
        db.commit()
        print("Blood inventory initialized.")

        # 3. Seed Donors
        existing_donors_count = db.query(models.Donor).count()
        if existing_donors_count == 0:
            print("Seeding initial donors...")
            donors_data = [
                {"donor_code": "DON001", "name": "Anil Kumar", "blood_group": "O+", "phone": "+91 98456 12345", "email": "anil.kumar@gmail.com", "location": "Kottayam", "last_donation": "12 May 2025", "status": "Active", "total_donations": 4, "age": 29, "gender": "Male"},
                {"donor_code": "DON002", "name": "Neha Nair", "blood_group": "B+", "phone": "+91 94472 56789", "email": "neha.nair@gmail.com", "location": "Changanassery", "last_donation": "20 Jun 2025", "status": "Active", "total_donations": 3, "age": 26, "gender": "Female"},
                {"donor_code": "DON003", "name": "Vishnu Prasad", "blood_group": "A+", "phone": "+91 97441 23456", "email": "vishnu.prasad@gmail.com", "location": "Erumely", "last_donation": "05 Apr 2025", "status": "Active", "total_donations": 5, "age": 34, "gender": "Male"},
                {"donor_code": "DON004", "name": "Sreelekha S", "blood_group": "AB+", "phone": "+91 96543 98765", "email": "sreelekha.s@gmail.com", "location": "Punalur", "last_donation": "14 Jul 2025", "status": "Active", "total_donations": 2, "age": 31, "gender": "Female"},
                {"donor_code": "DON005", "name": "Ramesh Babu", "blood_group": "O−", "phone": "+91 98950 45612", "email": "ramesh.babu@gmail.com", "location": "Kottayam", "last_donation": "30 May 2025", "status": "Active", "total_donations": 6, "age": 42, "gender": "Male"},
                {"donor_code": "DON006", "name": "Arun M", "blood_group": "A−", "phone": "+91 94951 78901", "email": "arun.m@gmail.com", "location": "Kanjirappally", "last_donation": "10 Feb 2025", "status": "Inactive", "total_donations": 1, "age": 24, "gender": "Male"},
                {"donor_code": "DON007", "name": "Divya Tom", "blood_group": "B−", "phone": "+91 97472 34567", "email": "divya.tom@gmail.com", "location": "Kottayam", "last_donation": "18 Jun 2025", "status": "Active", "total_donations": 3, "age": 28, "gender": "Female"},
                {"donor_code": "DON008", "name": "Mathew Varghese", "blood_group": "O+", "phone": "+91 94460 11223", "email": "mathew.v@gmail.com", "location": "Changanassery", "last_donation": "02 Jul 2025", "status": "Active", "total_donations": 7, "age": 38, "gender": "Male"},
                {"donor_code": "DON009", "name": "Ananya Pillai", "blood_group": "AB−", "phone": "+91 98471 99887", "email": "ananya.p@gmail.com", "location": "Punalur", "last_donation": "19 May 2025", "status": "Active", "total_donations": 2, "age": 25, "gender": "Female"},
                {"donor_code": "DON010", "name": "Karthik R", "blood_group": "A+", "phone": "+91 94963 44556", "email": "karthik.r@gmail.com", "location": "Erumely", "last_donation": "28 Jun 2025", "status": "Active", "total_donations": 4, "age": 30, "gender": "Male"}
            ]
            for donor in donors_data:
                db.add(models.Donor(**donor))
            db.commit()
            print("Donors seeded successfully.")

        # 4. Seed Blood Requests
        existing_requests_count = db.query(models.BloodRequest).count()
        if existing_requests_count == 0:
            print("Seeding blood requests...")
            requests_data = [
                {"request_code": "REQ001", "patient_name": "Anil Kumar", "blood_group": "O+", "units_requested": 2, "hospital_name": "General Hospital Kottayam", "location": "Kottayam", "contact_phone": "+91 98456 12345", "urgency": "Urgent", "status": "Pending", "time_ago": "2 hours ago"},
                {"request_code": "REQ002", "patient_name": "Neha Nair", "blood_group": "B+", "units_requested": 1, "hospital_name": "St. Thomas Hospital", "location": "Changanassery", "contact_phone": "+91 94472 56789", "urgency": "Normal", "status": "In Progress", "time_ago": "4 hours ago"},
                {"request_code": "REQ003", "patient_name": "Vishnu Prasad", "blood_group": "A+", "units_requested": 3, "hospital_name": "Community Health Centre", "location": "Erumely", "contact_phone": "+91 97441 23456", "urgency": "Critical", "status": "Pending", "time_ago": "6 hours ago"},
                {"request_code": "REQ004", "patient_name": "Sreelekha S", "blood_group": "AB+", "units_requested": 1, "hospital_name": "Taluk Hospital Punalur", "location": "Punalur", "contact_phone": "+91 96543 98765", "urgency": "Normal", "status": "Completed", "time_ago": "1 day ago"},
                {"request_code": "REQ005", "patient_name": "Ramesh Babu", "blood_group": "O−", "units_requested": 2, "hospital_name": "Medical College Hospital", "location": "Kottayam", "contact_phone": "+91 98950 45612", "urgency": "Critical", "status": "In Progress", "time_ago": "1 day ago"}
            ]
            for req in requests_data:
                db.add(models.BloodRequest(**req))
            db.commit()
            print("Blood requests seeded successfully.")

        # 5. Seed Camps & Events
        existing_camps_count = db.query(models.CampEvent).count()
        if existing_camps_count == 0:
            print("Seeding camp events...")
            camps_data = [
                {"camp_code": "CAMP001", "title": "Kanjirappally Blood Donation Camp", "location": "Kanjirappally Town Hall", "event_date": "15 Aug 2025", "time_slot": "9:00 AM – 2:00 PM", "organizer": "Red Cross & Rakthasethu", "target_units": 100, "collected_units": 0, "status": "Upcoming"},
                {"camp_code": "CAMP002", "title": "Kottayam Youth Voluntary Camp", "location": "CMS College Kottayam", "event_date": "22 Aug 2025", "time_slot": "10:00 AM – 4:00 PM", "organizer": "CMS NSS Unit", "target_units": 150, "collected_units": 0, "status": "Upcoming"},
                {"camp_code": "CAMP003", "title": "Changanassery Community Drive", "location": "Rotary Club Hall", "event_date": "01 Aug 2025", "time_slot": "9:00 AM – 1:00 PM", "organizer": "Rotary Club Changanassery", "target_units": 80, "collected_units": 86, "status": "Completed"}
            ]
            for camp in camps_data:
                db.add(models.CampEvent(**camp))
            db.commit()
            print("Camps seeded successfully.")

        # 6. Seed Donation History
        existing_donations_count = db.query(models.Donation).count()
        if existing_donations_count == 0:
            print("Seeding donation history logs...")
            donations_data = [
                {"donation_code": "DONAT-001", "donor_id": 1, "donor_name": "Anil Kumar", "blood_group": "O+", "units": 1, "donation_date": "12 May 2025", "venue": "Kottayam Blood Bank", "status": "Completed"},
                {"donation_code": "DONAT-002", "donor_id": 2, "donor_name": "Neha Nair", "blood_group": "B+", "units": 1, "donation_date": "20 Jun 2025", "venue": "Changanassery Drive", "status": "Completed"},
                {"donation_code": "DONAT-003", "donor_id": 3, "donor_name": "Vishnu Prasad", "blood_group": "A+", "units": 1, "donation_date": "05 Apr 2025", "venue": "General Hospital", "status": "Completed"},
                {"donation_code": "DONAT-004", "donor_id": 5, "donor_name": "Ramesh Babu", "blood_group": "O−", "units": 1, "donation_date": "30 May 2025", "venue": "Mobile Blood Van", "status": "Completed"}
            ]
            for don in donations_data:
                db.add(models.Donation(**don))
            db.commit()
            print("Donations history seeded.")

        # 7. Seed Notifications
        existing_notif_count = db.query(models.Notification).count()
        if existing_notif_count == 0:
            print("Seeding notifications...")
            notifs = [
                {"title": "Critical Blood Request", "message": "Urgent O− blood required at Medical College Hospital, Kottayam.", "type": "urgent", "is_read": False},
                {"title": "Upcoming Camp Tomorrow", "message": "Kanjirappally Blood Donation Camp starts at 9:00 AM.", "type": "alert", "is_read": False},
                {"title": "Low Inventory Alert", "message": "AB− and B− blood groups are below recommended safety threshold.", "type": "alert", "is_read": False}
            ]
            for n in notifs:
                db.add(models.Notification(**n))
            db.commit()
            print("Notifications seeded.")

        print("\nAll PostgreSQL tables in 'rakthasethu' seeded and up-to-date successfully!")
    except Exception as e:
        print(f"Error during database seeding: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    seed_data()
