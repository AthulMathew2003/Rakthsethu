import sys
import os
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
        # 1. Seed Users (Admin, Staff, Panchayat Admin, Citizens)
        drishya_email = "drishya@gmail.com"
        drishya_user = db.query(models.User).filter(models.User.email == drishya_email).first()
        if not drishya_user:
            print("Seeding Admin user (Drishya)...")
            db.add(models.User(
                user_code="ADM001",
                email=drishya_email,
                hashed_password=auth.get_password_hash("Drishya@"),
                full_name="Drishya",
                phone_number="+91 98765 43210",
                role="Super Admin",
                district="Kottayam",
                panchayat="Kanjirappally",
                registered_date="2026-08-29",
                last_active="2026-08-29",
                status="Active",
                is_active=True,
                is_admin=True
            ))

        admin_email = "sruthy.admin@rakthasethu.org"
        admin_user = db.query(models.User).filter(models.User.email == admin_email).first()
        if not admin_user:
            print("Seeding Admin user (Sruthy M S)...")
            db.add(models.User(
                user_code="USR001",
                email=admin_email,
                hashed_password=auth.get_password_hash("password123"),
                full_name="Sruthy M S",
                phone_number="+91 98456 78901",
                role="Admin",
                district="Kottayam",
                panchayat="Kanjirappally",
                registered_date="2026-08-01",
                last_active="2026-08-22",
                status="Active",
                is_active=True,
                is_admin=True
            ))
            
        users_seed_data = [
            {
                "user_code": "USR002",
                "email": "anu@example.com",
                "hashed_password": auth.get_password_hash("password123"),
                "full_name": "Anu Thomas",
                "phone_number": "9845678901",
                "role": "Citizen",
                "district": "Kottayam",
                "panchayat": "Kanjirappally",
                "registered_date": "2026-08-10",
                "last_active": "2026-08-21",
                "status": "Active",
                "is_active": True,
                "is_admin": False
            },
            {
                "user_code": "USR003",
                "email": "faisal@example.com",
                "hashed_password": auth.get_password_hash("password123"),
                "full_name": "Faisal Rahman",
                "phone_number": "9445123456",
                "role": "Panchayat Admin",
                "district": "Ernakulam",
                "panchayat": "Cheranallur",
                "registered_date": "2026-08-16",
                "last_active": "2026-08-22",
                "status": "Active",
                "is_active": True,
                "is_admin": False
            },
            {
                "user_code": "USR004",
                "email": "meera@example.com",
                "hashed_password": auth.get_password_hash("password123"),
                "full_name": "Meera Krishnan",
                "phone_number": "9895012345",
                "role": "Department Admin",
                "district": "Kottayam",
                "panchayat": "Thellakom",
                "registered_date": "2026-08-18",
                "last_active": "2026-08-20",
                "status": "Inactive",
                "is_active": False,
                "is_admin": False
            },
            {
                "user_code": "USR005",
                "email": "joseph@example.com",
                "hashed_password": auth.get_password_hash("password123"),
                "full_name": "Joseph Antony",
                "phone_number": "9747123458",
                "role": "Staff",
                "district": "Kozhikode",
                "panchayat": "Karanthur",
                "registered_date": "2026-08-05",
                "last_active": "2026-08-19",
                "status": "Suspended",
                "is_active": False,
                "is_admin": False
            }
        ]
        for u in users_seed_data:
            if not db.query(models.User).filter(models.User.email == u["email"]).first():
                db.add(models.User(**u))
        db.commit()
        print("Users initialized.")

        # 2. Seed Hospitals
        existing_hospitals_count = db.query(models.Hospital).count()
        if existing_hospitals_count == 0:
            print("Seeding hospitals...")
            hospitals_data = [
                {
                    "hospital_code": "HOSP001",
                    "name": "Government Medical College Hospital",
                    "type": "Government",
                    "district": "Kottayam",
                    "panchayat": "Kumarakom",
                    "address": "Gandhinagar, Kottayam, Kerala 686008",
                    "phone": "04812597311",
                    "email": "gmc.ktm@kerala.gov.in",
                    "emergency_number": "108",
                    "latitude": 9.5916,
                    "longitude": 76.5222,
                    "services": "Emergency, Cardiology, Orthopaedics, Neurology, Blood Bank",
                    "status": "Active"
                },
                {
                    "hospital_code": "HOSP002",
                    "name": "Aster Medcity",
                    "type": "Private",
                    "district": "Ernakulam",
                    "panchayat": "Cheranallur",
                    "address": "Kuttisahib Road, Cheranallur, Kochi, Kerala 682027",
                    "phone": "04846627000",
                    "email": "info@astermedcity.com",
                    "emergency_number": "04846627500",
                    "latitude": 10.0264,
                    "longitude": 76.2694,
                    "services": "Emergency, Cardiology, Oncology, Pediatrics, Blood Bank",
                    "status": "Active"
                },
                {
                    "hospital_code": "HOSP003",
                    "name": "Government Medical College Calicut",
                    "type": "Government",
                    "district": "Kozhikode",
                    "panchayat": "Karanthur",
                    "address": "Medical College Junction, Kozhikode, Kerala 673008",
                    "phone": "04952350216",
                    "email": "principalmcc@gmail.com",
                    "emergency_number": "108",
                    "latitude": 11.2728,
                    "longitude": 75.8369,
                    "services": "Emergency, Cardiology, General Surgery, Nephrology, Blood Bank",
                    "status": "Active"
                },
                {
                    "hospital_code": "HOSP004",
                    "name": "Caritas Hospital",
                    "type": "Private",
                    "district": "Kottayam",
                    "panchayat": "Thellakom",
                    "address": "Thellakom P.O., Kottayam, Kerala 686630",
                    "phone": "04812790025",
                    "email": "caritas@caritashospital.org",
                    "emergency_number": "04812790000",
                    "latitude": 9.6267,
                    "longitude": 76.5278,
                    "services": "Emergency, Gastroenterology, Urology, Cardiology, Blood Bank",
                    "status": "Inactive"
                }
            ]
            for h in hospitals_data:
                db.add(models.Hospital(**h))
            db.commit()
            print("Hospitals seeded successfully.")

        # 3. Seed Blood Inventory Batches & Aggregates
        existing_batches_count = db.query(models.BloodInventoryBatch).count()
        if existing_batches_count == 0:
            print("Seeding inventory batches...")
            batches_data = [
                {
                    "batch_code": "INV001",
                    "blood_group": "O+",
                    "component": "Whole Blood",
                    "available_units": 18,
                    "reserved_units": 4,
                    "collection_date": "2026-08-15",
                    "expiry_date": "2026-09-20",
                    "storage_location": "Blood Bank A - Rack 03",
                    "status": "Available",
                    "notes": "Standard whole blood batch, tested and cleared."
                },
                {
                    "batch_code": "INV002",
                    "blood_group": "O-",
                    "component": "Packed RBC",
                    "available_units": 3,
                    "reserved_units": 0,
                    "collection_date": "2026-08-10",
                    "expiry_date": "2026-09-14",
                    "storage_location": "Blood Bank B - Freezer 01",
                    "status": "Critical",
                    "notes": "Rare blood group, low stock alert triggered."
                },
                {
                    "batch_code": "INV003",
                    "blood_group": "A+",
                    "component": "Plasma",
                    "available_units": 25,
                    "reserved_units": 5,
                    "collection_date": "2026-08-01",
                    "expiry_date": "2026-09-01",
                    "storage_location": "Blood Bank A - Plasma Freezer",
                    "status": "Available",
                    "notes": "Expiring soon batch, monitor closely."
                },
                {
                    "batch_code": "INV004",
                    "blood_group": "B+",
                    "component": "Platelets",
                    "available_units": 8,
                    "reserved_units": 2,
                    "collection_date": "2026-08-19",
                    "expiry_date": "2026-08-24",
                    "storage_location": "Blood Bank B - Incubator 02",
                    "status": "Low Stock",
                    "notes": "Platelets have a short 5-day lifespan."
                },
                {
                    "batch_code": "INV005",
                    "blood_group": "AB-",
                    "component": "Cryoprecipitate",
                    "available_units": 0,
                    "reserved_units": 0,
                    "collection_date": "2026-07-20",
                    "expiry_date": "2026-08-20",
                    "storage_location": "Blood Bank A - Rack 04",
                    "status": "Expired",
                    "notes": "Batch expired, marked for safe disposal."
                },
                {
                    "batch_code": "INV006",
                    "blood_group": "A-",
                    "component": "Packed RBC",
                    "available_units": 12,
                    "reserved_units": 2,
                    "collection_date": "2026-08-12",
                    "expiry_date": "2026-09-18",
                    "storage_location": "Blood Bank A - Rack 02",
                    "status": "Available",
                    "notes": "Tested negative for all pathogens."
                },
                {
                    "batch_code": "INV007",
                    "blood_group": "B-",
                    "component": "Whole Blood",
                    "available_units": 6,
                    "reserved_units": 1,
                    "collection_date": "2026-08-14",
                    "expiry_date": "2026-09-19",
                    "storage_location": "Blood Bank B - Rack 01",
                    "status": "Low Stock",
                    "notes": "Routine collection from campus drive."
                },
                {
                    "batch_code": "INV008",
                    "blood_group": "AB+",
                    "component": "Plasma",
                    "available_units": 15,
                    "reserved_units": 3,
                    "collection_date": "2026-08-08",
                    "expiry_date": "2026-09-10",
                    "storage_location": "Blood Bank A - Plasma Freezer 2",
                    "status": "Available",
                    "notes": "Universal plasma donor batch."
                }
            ]
            for b in batches_data:
                db.add(models.BloodInventoryBatch(**b))
            db.commit()
            print("Blood inventory batches seeded.")

        # Seed Summary table
        inventory_defaults = [
            {"blood_group": "A+", "units_available": 25, "units_reserved": 5, "min_threshold": 20, "status": "Sufficient"},
            {"blood_group": "A−", "units_available": 12, "units_reserved": 2, "min_threshold": 15, "status": "Sufficient"},
            {"blood_group": "B+", "units_available": 8, "units_reserved": 2, "min_threshold": 15, "status": "Low"},
            {"blood_group": "B−", "units_available": 6, "units_reserved": 1, "min_threshold": 10, "status": "Low"},
            {"blood_group": "O+", "units_available": 18, "units_reserved": 4, "min_threshold": 25, "status": "Low"},
            {"blood_group": "O−", "units_available": 3, "units_reserved": 0, "min_threshold": 15, "status": "Critical"},
            {"blood_group": "AB+", "units_available": 15, "units_reserved": 3, "min_threshold": 10, "status": "Sufficient"},
            {"blood_group": "AB−", "units_available": 0, "units_reserved": 0, "min_threshold": 10, "status": "Critical"},
        ]
        for inv_data in inventory_defaults:
            existing_inv = db.query(models.BloodInventory).filter(
                models.BloodInventory.blood_group == inv_data["blood_group"]
            ).first()
            if not existing_inv:
                db.add(models.BloodInventory(**inv_data))
            else:
                existing_inv.units_available = inv_data["units_available"]
                existing_inv.units_reserved = inv_data["units_reserved"]
                existing_inv.status = inv_data["status"]
        db.commit()

        # 4. Seed Donors
        existing_donors_count = db.query(models.Donor).count()
        if existing_donors_count == 0:
            print("Seeding initial donors...")
            donors_data = [
                {"donor_code": "DON001", "name": "Arun Kumar", "blood_group": "O+", "phone": "+91 98456 12345", "email": "arun.kumar@gmail.com", "location": "Kottayam", "last_donation": "20 Aug 2026", "status": "Active", "total_donations": 4, "age": 29, "gender": "Male"},
                {"donor_code": "DON002", "name": "Saritha Varma", "blood_group": "A-", "phone": "+91 94472 56789", "email": "saritha.varma@gmail.com", "location": "Ernakulam", "last_donation": "22 Aug 2026", "status": "Active", "total_donations": 3, "age": 26, "gender": "Female"},
                {"donor_code": "DON003", "name": "Rahul Bose", "blood_group": "B+", "phone": "+91 97441 23456", "email": "rahul.bose@gmail.com", "location": "Kozhikode", "last_donation": "28 Aug 2026", "status": "Active", "total_donations": 5, "age": 34, "gender": "Male"},
                {"donor_code": "DON004", "name": "Anjali Menon", "blood_group": "AB+", "phone": "+91 96543 98765", "email": "anjali.menon@gmail.com", "location": "Thiruvananthapuram", "last_donation": "15 Aug 2026", "status": "Active", "total_donations": 2, "age": 31, "gender": "Female"},
                {"donor_code": "DON005", "name": "Ramesh Babu", "blood_group": "O-", "phone": "+91 98950 45612", "email": "ramesh.babu@gmail.com", "location": "Kottayam", "last_donation": "30 May 2026", "status": "Active", "total_donations": 6, "age": 42, "gender": "Male"},
                {"donor_code": "DON006", "name": "Divya Tom", "blood_group": "B-", "phone": "+91 97472 34567", "email": "divya.tom@gmail.com", "location": "Kottayam", "last_donation": "18 Jun 2026", "status": "Active", "total_donations": 3, "age": 28, "gender": "Female"}
            ]
            for donor in donors_data:
                db.add(models.Donor(**donor))
            db.commit()
            print("Donors seeded.")

        # 5. Seed Blood Requests
        existing_requests_count = db.query(models.BloodRequest).count()
        if existing_requests_count == 0:
            print("Seeding blood requests...")
            requests_data = [
                {
                    "request_code": "BR001",
                    "patient_name": "Anu Thomas",
                    "blood_group": "O+",
                    "units_requested": 2,
                    "hospital_name": "Government Medical College Hospital",
                    "district": "Kottayam",
                    "location": "Kottayam",
                    "contact_phone": "9845678902",
                    "emergency_contact": "9744123457",
                    "required_date": "2026-08-25",
                    "urgency": "Critical",
                    "status": "Pending",
                    "notes": "Urgently required for heart surgery.",
                    "time_ago": "2 hours ago"
                },
                {
                    "request_code": "BR002",
                    "patient_name": "Faisal Rahman",
                    "blood_group": "B-",
                    "units_requested": 3,
                    "hospital_name": "Aster Medcity",
                    "district": "Ernakulam",
                    "location": "Ernakulam",
                    "contact_phone": "9876543211",
                    "emergency_contact": "9895045613",
                    "required_date": "2026-08-27",
                    "urgency": "Urgent",
                    "status": "Approved",
                    "notes": "Post-accident trauma, required by tomorrow morning.",
                    "time_ago": "5 hours ago"
                },
                {
                    "request_code": "BR003",
                    "patient_name": "Meera Krishnan",
                    "blood_group": "A+",
                    "units_requested": 1,
                    "hospital_name": "Caritas Hospital",
                    "district": "Kottayam",
                    "location": "Kottayam",
                    "contact_phone": "9447256780",
                    "emergency_contact": "9654398766",
                    "required_date": "2026-08-30",
                    "urgency": "Normal",
                    "status": "Fulfilled",
                    "notes": "Scheduled knee replacement surgery.",
                    "time_ago": "1 day ago"
                },
                {
                    "request_code": "BR004",
                    "patient_name": "Joseph Antony",
                    "blood_group": "AB-",
                    "units_requested": 2,
                    "hospital_name": "Government Medical College Calicut",
                    "district": "Kozhikode",
                    "location": "Kozhikode",
                    "contact_phone": "9495178902",
                    "emergency_contact": "9747234568",
                    "urgency": "Critical",
                    "status": "In Progress",
                    "notes": "Patient in ICU, emergency blood required.",
                    "time_ago": "1 day ago"
                }
            ]
            for req in requests_data:
                db.add(models.BloodRequest(**req))
            db.commit()
            print("Blood requests seeded.")

        # 6. Seed Campus Events
        existing_camps_count = db.query(models.CampEvent).count()
        if existing_camps_count == 0:
            print("Seeding campus events...")
            camps_data = [
                {
                    "camp_code": "EV001",
                    "title": "Blood Donation Camp",
                    "type": "Blood Donation",
                    "location": "CMS College Kottayam",
                    "venue": "College Auditorium",
                    "event_date": "2026-09-05",
                    "start_time": "09:00 AM",
                    "end_time": "03:00 PM",
                    "time_slot": "09:00 AM – 03:00 PM",
                    "organizer": "Rakthasethu & NSS",
                    "participants": 120,
                    "max_participants": 200,
                    "target_units": 100,
                    "collected_units": 0,
                    "description": "Campus blood donation awareness and collection camp.",
                    "contact_number": "9845678902",
                    "registration_required": True,
                    "registration_deadline": "2026-09-03",
                    "image_banner": "https://images.unsplash.com/photo-1615461066841-6116e61058f4?q=80&w=600&auto=format&fit=crop",
                    "status": "Upcoming"
                },
                {
                    "camp_code": "EV002",
                    "title": "Health & Hygiene Camp",
                    "type": "Health Camp",
                    "location": "St. Teresa's College Ernakulam",
                    "venue": "Seminar Hall",
                    "event_date": "2026-09-12",
                    "start_time": "10:00 AM",
                    "end_time": "04:00 PM",
                    "time_slot": "10:00 AM – 04:00 PM",
                    "organizer": "NSS & Rakthasethu",
                    "participants": 85,
                    "max_participants": 100,
                    "target_units": 50,
                    "collected_units": 0,
                    "description": "Free medical checkups, health advisory, and awareness programs.",
                    "contact_number": "9744123457",
                    "registration_required": True,
                    "registration_deadline": "2026-09-10",
                    "image_banner": "",
                    "status": "Upcoming"
                },
                {
                    "camp_code": "EV003",
                    "title": "Volunteer Training Activity",
                    "type": "Volunteer Activity",
                    "location": "Rakthasethu Regional Office Kottayam",
                    "venue": "Conference Room B",
                    "event_date": "2026-08-22",
                    "start_time": "02:00 PM",
                    "end_time": "05:00 PM",
                    "time_slot": "02:00 PM – 05:00 PM",
                    "organizer": "Rakthasethu HQ",
                    "participants": 30,
                    "max_participants": 50,
                    "target_units": 0,
                    "collected_units": 0,
                    "description": "Orientation program for newly registered campus blood ambassadors.",
                    "contact_number": "9876543211",
                    "registration_required": False,
                    "image_banner": "",
                    "status": "Ongoing"
                },
                {
                    "camp_code": "EV004",
                    "title": "Awareness & Rally Session",
                    "type": "Awareness Program",
                    "location": "Government Medical College Calicut",
                    "venue": "Campus Grounds",
                    "event_date": "2026-08-15",
                    "start_time": "09:00 AM",
                    "end_time": "12:00 PM",
                    "time_slot": "09:00 AM – 12:00 PM",
                    "organizer": "Red Ribbon Club",
                    "participants": 250,
                    "max_participants": 300,
                    "target_units": 150,
                    "collected_units": 162,
                    "description": "Independence Day blood donation awareness rally and talk.",
                    "contact_number": "9495178902",
                    "registration_required": False,
                    "image_banner": "",
                    "status": "Completed"
                }
            ]
            for camp in camps_data:
                db.add(models.CampEvent(**camp))
            db.commit()
            print("Campus events seeded.")

        # 7. Seed Donations History
        existing_donations_count = db.query(models.Donation).count()
        if existing_donations_count == 0:
            print("Seeding donations history...")
            donations_data = [
                {
                    "donation_code": "DN001",
                    "donor_id": 1,
                    "donor_name": "Arun Kumar",
                    "blood_group": "O+",
                    "phone": "9845678901",
                    "email": "arun@example.com",
                    "district": "Kottayam",
                    "address": "Arun Villa, Kottayam, Kerala",
                    "donation_date": "2026-08-20",
                    "donation_type": "Voluntary",
                    "units": 1,
                    "hospital": "Government Medical College Hospital",
                    "venue": "Government Medical College Hospital",
                    "status": "Completed",
                    "notes": "Regular blood donor, overall health good."
                },
                {
                    "donation_code": "DN002",
                    "donor_id": 2,
                    "donor_name": "Saritha Varma",
                    "blood_group": "A-",
                    "phone": "9445123456",
                    "email": "saritha@example.com",
                    "district": "Ernakulam",
                    "address": "Flat 4B, Skyview, Ernakulam, Kerala",
                    "donation_date": "2026-08-22",
                    "donation_type": "Replacement",
                    "units": 1,
                    "hospital": "Aster Medcity",
                    "venue": "Aster Medcity",
                    "status": "Completed",
                    "notes": "Donated for relative's surgery."
                },
                {
                    "donation_code": "DN003",
                    "donor_id": 3,
                    "donor_name": "Rahul Bose",
                    "blood_group": "B+",
                    "phone": "9895012345",
                    "email": "rahul@example.com",
                    "district": "Kozhikode",
                    "address": "Bose House, Kozhikode, Kerala",
                    "donation_date": "2026-08-28",
                    "donation_type": "Camp Donation",
                    "units": 2,
                    "hospital": "Kozhikode Town Hall Camp",
                    "venue": "Kozhikode Town Hall Camp",
                    "status": "Scheduled",
                    "notes": "Registered for upcoming donation drive."
                },
                {
                    "donation_code": "DN004",
                    "donor_id": 4,
                    "donor_name": "Anjali Menon",
                    "blood_group": "AB+",
                    "phone": "9747123458",
                    "email": "anjali@example.com",
                    "district": "Thiruvananthapuram",
                    "address": "Anjali Nivas, TVM, Kerala",
                    "donation_date": "2026-08-15",
                    "donation_type": "Directed Donation",
                    "units": 1,
                    "hospital": "Sree Chitra Tirunal Hospital",
                    "venue": "Sree Chitra Tirunal Hospital",
                    "status": "Completed",
                    "notes": "Directed donation for patient."
                }
            ]
            for don in donations_data:
                db.add(models.Donation(**don))
            db.commit()
            print("Donations seeded.")

        # 8. Seed System Settings
        from app.routers.settings_router import DEFAULT_SETTINGS
        for section_name, sec_data in DEFAULT_SETTINGS.items():
            existing_setting = db.query(models.SystemSetting).filter(models.SystemSetting.section == section_name).first()
            if not existing_setting:
                db.add(models.SystemSetting(section=section_name, settings_data=sec_data))
        db.commit()
        print("System settings seeded.")

        # 9. Seed Activity Logs
        existing_logs = db.query(models.ActivityLog).count()
        if existing_logs == 0:
            print("Seeding activity logs...")
            activity_data = [
                {"category": "Blood Requests", "activity": "New request for O+ Whole Blood submitted by Aster Medcity", "count": 4, "status": "Pending", "log_date": "2026-08-22"},
                {"category": "Blood Inventory", "activity": "Stock level adjustment: batch INV002 packed RBC reduced", "count": 1, "status": "Completed", "log_date": "2026-08-22"},
                {"category": "Users", "activity": "New Volunteer User registered: Faisal Rahman", "count": 1, "status": "Active", "log_date": "2026-08-22"},
                {"category": "Campus Events", "activity": "Volunteer Training Session updated to Ongoing", "count": 30, "status": "Ongoing", "log_date": "2026-08-21"},
                {"category": "Blood Donations", "activity": "Scheduled Blood Donation Camp successfully completed", "count": 18, "status": "Completed", "log_date": "2026-08-20"},
                {"category": "Blood Requests", "activity": "Critical blood request fulfilled for AB- Cryoprecipitate", "count": 2, "status": "Fulfilled", "log_date": "2026-08-19"},
                {"category": "Users", "activity": "Department Admin account created for Meera Krishnan", "count": 1, "status": "Active", "log_date": "2026-08-18"},
                {"category": "Campus Events", "activity": "Awareness Rally event marked Completed", "count": 250, "status": "Completed", "log_date": "2026-08-15"},
                {"category": "Hospitals", "activity": "Hospital profile updated: Government Medical College Hospital", "count": 1, "status": "Active", "log_date": "2026-08-14"},
                {"category": "Users", "activity": "Citizen account created for Anu Thomas", "count": 1, "status": "Active", "log_date": "2026-08-10"}
            ]
            for act in activity_data:
                db.add(models.ActivityLog(**act))
            db.commit()
            print("Activity logs seeded.")

        # 10. Seed Notifications
        existing_notif_count = db.query(models.Notification).count()
        if existing_notif_count == 0:
            print("Seeding notifications...")
            notifs = [
                {"title": "Critical Blood Request", "message": "Urgent O- blood required at Medical College Hospital, Kottayam.", "type": "urgent", "is_read": False},
                {"title": "Upcoming Camp Tomorrow", "message": "Blood Donation Camp at College Auditorium starts at 9:00 AM.", "type": "alert", "is_read": False},
                {"title": "Low Inventory Alert", "message": "AB- and O- blood groups are below recommended safety threshold.", "type": "alert", "is_read": False}
            ]
            for n in notifs:
                db.add(models.Notification(**n))
            db.commit()
            print("Notifications seeded.")

        print("\nAll database tables and seed data created successfully!")
    except Exception as e:
        print(f"Error during database seeding: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    seed_data()
