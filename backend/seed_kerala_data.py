"""
Rakthasethu - Kerala Sample & Dummy Seed Data Script
Populates realistic Kerala hospitals, staff users, blood donors across multiple districts,
clinical blood requests, and historical/scheduled donations for end-to-end testing.
"""

import asyncio
from datetime import date, timedelta
from sqlalchemy import delete
from app.core.database import AsyncSessionLocal
from app.core.security import hash_password
from app.models.enums import BloodGroup, DonationStatus, RequestStatus, RequestUrgency, UserRole
from app.models.hospital import Hospital
from app.models.user import User
from app.models.donor import Donor
from app.models.blood_request import BloodRequest
from app.models.donation import Donation


async def seed_data():
    async with AsyncSessionLocal() as session:
        print("[*] Starting Rakthasethu Kerala Database Seeding...")

        # 1. Clear existing operational records cleanly (in correct foreign-key order)
        print("[*] Cleaning existing operational data...")
        await session.execute(delete(Donation))
        await session.execute(delete(BloodRequest))
        await session.execute(delete(Donor))
        await session.execute(delete(User))
        await session.execute(delete(Hospital))
        await session.commit()

        # 2. Seed Hospitals across Kerala
        print("[*] Seeding Kerala Hospitals...")
        hospitals_data = [
            Hospital(
                hospital_code="HOSP001",
                name="Government Medical College Kottayam",
                hospital_type="Government Medical College",
                district="Kottayam",
                panchayat="Gandhinagar",
                address="Medical College PO, Gandhinagar, Kottayam, Kerala 686008",
                phone="+914812597284",
                email="gmckottayam@kerala.gov.in",
                emergency_number="108",
                latitude=9.6234,
                longitude=76.5387,
                is_active=True,
            ),
            Hospital(
                hospital_code="HOSP002",
                name="General Hospital Ernakulam",
                hospital_type="Government General Hospital",
                district="Ernakulam",
                panchayat="Kochi Corporation",
                address="Hospital Road, Marine Drive, Kochi, Ernakulam, Kerala 682011",
                phone="+914842361251",
                email="ghosp.ekm@kerala.gov.in",
                emergency_number="108",
                latitude=9.9723,
                longitude=76.2812,
                is_active=True,
            ),
            Hospital(
                hospital_code="HOSP003",
                name="Government Medical College Kozhikode",
                hospital_type="Government Medical College",
                district="Kozhikode",
                panchayat="Kozhikode Corporation",
                address="17 Medical College Road, Kozhikode, Kerala 673008",
                phone="+914952350216",
                email="gmckozhikode@kerala.gov.in",
                emergency_number="108",
                latitude=11.2721,
                longitude=75.8344,
                is_active=True,
            ),
            Hospital(
                hospital_code="HOSP004",
                name="Government Medical College Thiruvananthapuram",
                hospital_type="Government Medical College",
                district="Thiruvananthapuram",
                panchayat="Medical College",
                address="Medical College Junction, Thiruvananthapuram, Kerala 695011",
                phone="+914712528300",
                email="gmctvm@kerala.gov.in",
                emergency_number="108",
                latitude=8.5241,
                longitude=76.9298,
                is_active=True,
            ),
            Hospital(
                hospital_code="HOSP005",
                name="District Hospital Palakkad",
                hospital_type="District Hospital",
                district="Palakkad",
                panchayat="Palakkad Municipality",
                address="Near Fort Maidan, Palakkad, Kerala 678001",
                phone="+914912534522",
                email="dhpalakkad@kerala.gov.in",
                emergency_number="108",
                latitude=10.7753,
                longitude=76.6542,
                is_active=True,
            ),
            Hospital(
                hospital_code="HOSP006",
                name="General Hospital Alappuzha",
                hospital_type="General Hospital",
                district="Alappuzha",
                panchayat="Alappuzha Municipality",
                address="Iron Bridge Road, Alappuzha, Kerala 688001",
                phone="+914772253324",
                email="ghalappuzha@kerala.gov.in",
                emergency_number="108",
                latitude=9.4981,
                longitude=76.3388,
                is_active=True,
            ),
            Hospital(
                hospital_code="HOSP007",
                name="Government Medical College Thrissur",
                hospital_type="Government Medical College",
                district="Thrissur",
                panchayat="Mulamkunnathukavu",
                address="Mulamkunnathukavu, Thrissur, Kerala 680596",
                phone="+914872200310",
                email="gmcthrissur@kerala.gov.in",
                emergency_number="108",
                latitude=10.6092,
                longitude=76.2081,
                is_active=True,
            ),
            Hospital(
                hospital_code="HOSP008",
                name="District Hospital Mananthavady",
                hospital_type="District Hospital",
                district="Wayanad",
                panchayat="Mananthavady Municipality",
                address="Mananthavady, Wayanad, Kerala 670645",
                phone="+914935240223",
                email="dhmananthavady@kerala.gov.in",
                emergency_number="108",
                latitude=11.8021,
                longitude=76.0034,
                is_active=True,
            ),
        ]
        session.add_all(hospitals_data)
        await session.flush()
        print(f"[+] Added {len(hospitals_data)} Kerala hospitals.")

        # 3. Seed Users & RBAC
        print("[*] Seeding RBAC Users...")
        users_data = [
            User(
                user_code="USR001",
                email="admin@rakthasethu.org",
                hashed_password=hash_password("admin123"),
                full_name="State Super Admin",
                phone_number="+919447000001",
                role=UserRole.SUPER_ADMIN,
                district="Thiruvananthapuram",
                panchayat="Secretariat",
                is_active=True,
            ),
            User(
                user_code="USR002",
                hospital_id=hospitals_data[0].id,  # Kottayam
                email="kottayam.admin@rakthasethu.org",
                hashed_password=hash_password("hospital123"),
                full_name="Dr. Suresh Kumar (Blood Bank In-charge)",
                phone_number="+919447000002",
                role=UserRole.HOSPITAL_ADMIN,
                district="Kottayam",
                panchayat="Gandhinagar",
                is_active=True,
            ),
            User(
                user_code="USR003",
                hospital_id=hospitals_data[0].id,  # Kottayam
                email="kottayam.staff@rakthasethu.org",
                hashed_password=hash_password("staff123"),
                full_name="Rincy Varghese (Staff Nurse)",
                phone_number="+919447000003",
                role=UserRole.STAFF,
                district="Kottayam",
                panchayat="Gandhinagar",
                is_active=True,
            ),
            User(
                user_code="USR004",
                hospital_id=hospitals_data[1].id,  # Ernakulam
                email="ekm.admin@rakthasethu.org",
                hashed_password=hash_password("hospital123"),
                full_name="Dr. Lakshmi N (Medical Officer)",
                phone_number="+919447000004",
                role=UserRole.HOSPITAL_ADMIN,
                district="Ernakulam",
                panchayat="Kochi",
                is_active=True,
            ),
            User(
                user_code="USR005",
                hospital_id=hospitals_data[2].id,  # Kozhikode
                email="calicut.admin@rakthasethu.org",
                hashed_password=hash_password("hospital123"),
                full_name="Dr. Abdul Rasheed (Blood Bank Head)",
                phone_number="+919447000005",
                role=UserRole.HOSPITAL_ADMIN,
                district="Kozhikode",
                panchayat="Kozhikode",
                is_active=True,
            ),
            User(
                user_code="USR006",
                hospital_id=hospitals_data[3].id,  # TVM
                email="tvm.admin@rakthasethu.org",
                hashed_password=hash_password("hospital123"),
                full_name="Dr. Ananthakrishnan G",
                phone_number="+919447000006",
                role=UserRole.HOSPITAL_ADMIN,
                district="Thiruvananthapuram",
                panchayat="Medical College",
                is_active=True,
            ),
        ]
        session.add_all(users_data)
        await session.flush()
        print(f"[+] Added {len(users_data)} RBAC test users.")

        # 4. Seed Donors across Kerala Districts
        print("[*] Seeding Kerala Blood Donors...")
        donors_data = [
            # --- KOTTAYAM DONORS ---
            Donor(
                donor_code="DNR001",
                hospital_id=hospitals_data[0].id,
                full_name="Rahul Nair",
                blood_group=BloodGroup.O_POSITIVE,
                phone="+919847012345",
                gender="Male",
                email="rahul.nair@example.com",
                district="Kottayam",
                panchayat="Kumarakom",
                address="Nalukettu House, Kumarakom PO, Kottayam",
                is_available=True,
                is_active=True,
            ),
            Donor(
                donor_code="DNR002",
                hospital_id=hospitals_data[0].id,
                full_name="Anjali Menon",
                blood_group=BloodGroup.A_POSITIVE,
                phone="+919847123456",
                gender="Female",
                email="anjali.menon@example.com",
                district="Kottayam",
                panchayat="Pala",
                address="Menon Villa, Pala Town, Kottayam",
                is_available=True,
                is_active=True,
            ),
            Donor(
                donor_code="DNR003",
                hospital_id=hospitals_data[0].id,
                full_name="Mathew Joseph",
                blood_group=BloodGroup.B_POSITIVE,
                phone="+919847234567",
                gender="Male",
                email="mathew.joseph@example.com",
                district="Kottayam",
                panchayat="Changanassery",
                address="Kavalam House, Changanassery",
                is_available=True,
                is_active=True,
            ),
            Donor(
                donor_code="DNR004",
                hospital_id=hospitals_data[0].id,
                full_name="Sneha Thomas",
                blood_group=BloodGroup.AB_POSITIVE,
                phone="+919847345678",
                gender="Female",
                email="sneha.thomas@example.com",
                district="Kottayam",
                panchayat="Ettumanoor",
                address="Rose Garden, Ettumanoor, Kottayam",
                is_available=True,
                is_active=True,
            ),
            Donor(
                donor_code="DNR005",
                hospital_id=hospitals_data[0].id,
                full_name="Arun Kumar S",
                blood_group=BloodGroup.O_NEGATIVE,  # Rare Universal Donor
                phone="+919847456789",
                gender="Male",
                email="arun.ks@example.com",
                district="Kottayam",
                panchayat="Kanjirappally",
                address="Thamarassery House, Kanjirappally",
                is_available=True,
                is_active=True,
            ),
            Donor(
                donor_code="DNR006",
                hospital_id=hospitals_data[0].id,
                full_name="Reshma Varghese",
                blood_group=BloodGroup.A_NEGATIVE,
                phone="+919847567890",
                gender="Female",
                email="reshma.v@example.com",
                district="Kottayam",
                panchayat="Vaikom",
                address="Lake View, Vaikom West",
                is_available=True,
                is_active=True,
            ),
            Donor(
                donor_code="DNR007",
                hospital_id=hospitals_data[0].id,
                full_name="George Kurian",
                blood_group=BloodGroup.O_POSITIVE,
                phone="+919847678901",
                gender="Male",
                email="george.k@example.com",
                district="Kottayam",
                panchayat="Pala",
                address="Kurian Villa, Lalam, Pala",
                is_available=True,
                is_active=True,
            ),

            # --- ERNAKULAM DONORS ---
            Donor(
                donor_code="DNR008",
                hospital_id=hospitals_data[1].id,
                full_name="Muhammed Bilal",
                blood_group=BloodGroup.O_POSITIVE,
                phone="+919846012345",
                gender="Male",
                email="bilal.m@example.com",
                district="Ernakulam",
                panchayat="Aluva",
                address="Periyar Nagar, Aluva, Ernakulam",
                is_available=True,
                is_active=True,
            ),
            Donor(
                donor_code="DNR009",
                hospital_id=hospitals_data[1].id,
                full_name="Divya Pillai",
                blood_group=BloodGroup.B_POSITIVE,
                phone="+919846123456",
                gender="Female",
                email="divya.pillai@example.com",
                district="Ernakulam",
                panchayat="Kakkanad",
                address="Infopark Express Way, Kakkanad",
                is_available=True,
                is_active=True,
            ),
            Donor(
                donor_code="DNR010",
                hospital_id=hospitals_data[1].id,
                full_name="Akhil George",
                blood_group=BloodGroup.A_POSITIVE,
                phone="+919846234567",
                gender="Male",
                email="akhil.george@example.com",
                district="Ernakulam",
                panchayat="Angamaly",
                address="St. George Avenue, Angamaly",
                is_available=True,
                is_active=True,
            ),
            Donor(
                donor_code="DNR011",
                hospital_id=hospitals_data[1].id,
                full_name="Neha Nambiar",
                blood_group=BloodGroup.O_NEGATIVE,
                phone="+919846345678",
                gender="Female",
                email="neha.nambiar@example.com",
                district="Ernakulam",
                panchayat="Tripunithura",
                address="Statue Junction, Tripunithura",
                is_available=True,
                is_active=True,
            ),
            Donor(
                donor_code="DNR012",
                hospital_id=hospitals_data[1].id,
                full_name="Vishnu Das",
                blood_group=BloodGroup.AB_NEGATIVE,
                phone="+919846456789",
                gender="Male",
                email="vishnu.das@example.com",
                district="Ernakulam",
                panchayat="Perumbavoor",
                address="AM Road, Perumbavoor",
                is_available=True,
                is_active=True,
            ),
            Donor(
                donor_code="DNR013",
                hospital_id=hospitals_data[1].id,
                full_name="Fatima Zahra",
                blood_group=BloodGroup.B_NEGATIVE,
                phone="+919846567890",
                gender="Female",
                email="fatima.z@example.com",
                district="Ernakulam",
                panchayat="Muvattupuzha",
                address="Market Road, Muvattupuzha",
                is_available=True,
                is_active=True,
            ),

            # --- KOZHIKODE DONORS ---
            Donor(
                donor_code="DNR014",
                hospital_id=hospitals_data[2].id,
                full_name="Jamsheer K",
                blood_group=BloodGroup.O_POSITIVE,
                phone="+919895012345",
                gender="Male",
                email="jamsheer.k@example.com",
                district="Kozhikode",
                panchayat="Feroke",
                address="Chungam, Feroke, Kozhikode",
                is_available=True,
                is_active=True,
            ),
            Donor(
                donor_code="DNR015",
                hospital_id=hospitals_data[2].id,
                full_name="Aparna Ramesh",
                blood_group=BloodGroup.B_POSITIVE,
                phone="+919895123456",
                gender="Female",
                email="aparna.r@example.com",
                district="Kozhikode",
                panchayat="Vadakara",
                address="Temple Road, Vadakara",
                is_available=True,
                is_active=True,
            ),
            Donor(
                donor_code="DNR016",
                hospital_id=hospitals_data[2].id,
                full_name="Sreejith K P",
                blood_group=BloodGroup.A_POSITIVE,
                phone="+919895234567",
                gender="Male",
                email="sreejith.kp@example.com",
                district="Kozhikode",
                panchayat="Koyilandy",
                address="Beach Road, Koyilandy",
                is_available=True,
                is_active=True,
            ),
            Donor(
                donor_code="DNR017",
                hospital_id=hospitals_data[2].id,
                full_name="Nandana S",
                blood_group=BloodGroup.O_NEGATIVE,
                phone="+919895345678",
                gender="Female",
                email="nandana.s@example.com",
                district="Kozhikode",
                panchayat="Balussery",
                address="Balussery Mukku, Kozhikode",
                is_available=True,
                is_active=True,
            ),
            Donor(
                donor_code="DNR018",
                hospital_id=hospitals_data[2].id,
                full_name="Fayis Ahmed",
                blood_group=BloodGroup.AB_POSITIVE,
                phone="+919895456789",
                gender="Male",
                email="fayis.a@example.com",
                district="Kozhikode",
                panchayat="Ramanattukara",
                address="Airport Road, Ramanattukara",
                is_available=True,
                is_active=True,
            ),

            # --- THIRUVANANTHAPURAM DONORS ---
            Donor(
                donor_code="DNR019",
                hospital_id=hospitals_data[3].id,
                full_name="Gokul Krishna",
                blood_group=BloodGroup.O_POSITIVE,
                phone="+919447012345",
                gender="Male",
                email="gokul.k@example.com",
                district="Thiruvananthapuram",
                panchayat="Kazhakkoottam",
                address="Technopark Phase 1, Kazhakkoottam",
                is_available=True,
                is_active=True,
            ),
            Donor(
                donor_code="DNR020",
                hospital_id=hospitals_data[3].id,
                full_name="Lekshmi B",
                blood_group=BloodGroup.A_POSITIVE,
                phone="+919447123456",
                gender="Female",
                email="lekshmi.b@example.com",
                district="Thiruvananthapuram",
                panchayat="Attingal",
                address="Palace Road, Attingal",
                is_available=True,
                is_active=True,
            ),
            Donor(
                donor_code="DNR021",
                hospital_id=hospitals_data[3].id,
                full_name="Sarath Chandran",
                blood_group=BloodGroup.B_POSITIVE,
                phone="+919447234567",
                gender="Male",
                email="sarath.c@example.com",
                district="Thiruvananthapuram",
                panchayat="Neyyattinkara",
                address="TB Junction, Neyyattinkara",
                is_available=True,
                is_active=True,
            ),
            Donor(
                donor_code="DNR022",
                hospital_id=hospitals_data[3].id,
                full_name="Keerthi Mohan",
                blood_group=BloodGroup.O_NEGATIVE,
                phone="+919447345678",
                gender="Female",
                email="keerthi.m@example.com",
                district="Thiruvananthapuram",
                panchayat="Nedumangad",
                address="Koyikkal, Nedumangad",
                is_available=True,
                is_active=True,
            ),

            # --- THRISSUR, MALAPPURAM, PALAKKAD, ALAPPUZHA & WAYANAD ---
            Donor(
                donor_code="DNR023",
                hospital_id=hospitals_data[6].id,
                full_name="Harikrishnan P",
                blood_group=BloodGroup.O_POSITIVE,
                phone="+919496012345",
                gender="Male",
                email="hari.kp@example.com",
                district="Thrissur",
                panchayat="Guruvayur",
                address="East Nada, Guruvayur, Thrissur",
                is_available=True,
                is_active=True,
            ),
            Donor(
                donor_code="DNR024",
                hospital_id=hospitals_data[6].id,
                full_name="Meera Warrier",
                blood_group=BloodGroup.B_POSITIVE,
                phone="+919496123456",
                gender="Female",
                email="meera.w@example.com",
                district="Thrissur",
                panchayat="Irinjalakuda",
                address="Koodalmanikyam Road, Irinjalakuda",
                is_available=True,
                is_active=True,
            ),
            Donor(
                donor_code="DNR025",
                hospital_id=hospitals_data[4].id,
                full_name="Manikandan R",
                blood_group=BloodGroup.O_POSITIVE,
                phone="+919446012345",
                gender="Male",
                email="mani.r@example.com",
                district="Palakkad",
                panchayat="Ottapalam",
                address="Main Road, Ottapalam, Palakkad",
                is_available=True,
                is_active=True,
            ),
            Donor(
                donor_code="DNR026",
                hospital_id=hospitals_data[5].id,
                full_name="Vipin V",
                blood_group=BloodGroup.A_POSITIVE,
                phone="+919567012345",
                gender="Male",
                email="vipin.v@example.com",
                district="Alappuzha",
                panchayat="Cherthala",
                address="Court Road, Cherthala, Alappuzha",
                is_available=True,
                is_active=True,
            ),
            Donor(
                donor_code="DNR027",
                hospital_id=hospitals_data[7].id,
                full_name="Abhiram M",
                blood_group=BloodGroup.O_POSITIVE,
                phone="+919400123456",
                gender="Male",
                email="abhiram.m@example.com",
                district="Wayanad",
                panchayat="Kalpetta",
                address="Pinangode Road, Kalpetta, Wayanad",
                is_available=True,
                is_active=True,
            ),
        ]
        session.add_all(donors_data)
        await session.flush()
        print(f"[+] Added {len(donors_data)} Kerala blood donors across 8 districts.")

        # 5. Seed Historical and Scheduled Donations
        print("[*] Seeding Donations & Cooldown Ledgers...")
        today = date.today()
        donations_data = [
            # Donor 1 (Rahul Nair) donated 120 days ago -> Eligible now!
            Donation(
                donation_code="DN001",
                donor_id=donors_data[0].id,
                hospital_id=hospitals_data[0].id,
                donation_date=today - timedelta(days=120),
                donation_type="Whole Blood",
                units_donated=1,
                status=DonationStatus.COMPLETED,
                notes="Voluntary donation at Kottayam Medical College Blood Bank. Normal vitals.",
            ),
            # Donor 2 (Anjali Menon) donated 100 days ago -> Eligible now!
            Donation(
                donation_code="DN002",
                donor_id=donors_data[1].id,
                hospital_id=hospitals_data[0].id,
                donation_date=today - timedelta(days=100),
                donation_type="Whole Blood",
                units_donated=1,
                status=DonationStatus.COMPLETED,
                notes="Camp donation at Pala St. Thomas College.",
            ),
            # Donor 7 (George Kurian) donated 20 days ago -> In 90-day Cooldown (Resting until +70 days)
            Donation(
                donation_code="DN003",
                donor_id=donors_data[6].id,
                hospital_id=hospitals_data[0].id,
                donation_date=today - timedelta(days=20),
                donation_type="Whole Blood",
                units_donated=1,
                status=DonationStatus.COMPLETED,
                notes="Replacement donation for cardiac patient.",
            ),
            # Donor 8 (Muhammed Bilal) donated 150 days ago -> Eligible!
            Donation(
                donation_code="DN004",
                donor_id=donors_data[7].id,
                hospital_id=hospitals_data[1].id,
                donation_date=today - timedelta(days=150),
                donation_type="Whole Blood",
                units_donated=1,
                status=DonationStatus.COMPLETED,
                notes="Voluntary donation at Ernakulam General Hospital.",
            ),
            # Donor 14 (Jamsheer K) Scheduled donation next week
            Donation(
                donation_code="DN005",
                donor_id=donors_data[13].id,
                hospital_id=hospitals_data[2].id,
                donation_date=today + timedelta(days=3),
                donation_type="Whole Blood",
                units_donated=1,
                status=DonationStatus.SCHEDULED,
                notes="Scheduled appointment at Kozhikode Medical College Blood Bank.",
            ),
        ]
        session.add_all(donations_data)
        await session.flush()
        print(f"[+] Added {len(donations_data)} historical/scheduled donation records.")

        # 6. Seed Clinical Blood Requests
        print("[*] Seeding Clinical Blood Requests...")
        requests_data = [
            BloodRequest(
                request_code="BR001",
                hospital_id=hospitals_data[0].id,  # Kottayam
                patient_name="Baby of Soumya (NICU Bed 3)",
                blood_group=BloodGroup.O_POSITIVE,
                units_requested=2,
                district="Kottayam",
                location="Kottayam Medical College NICU",
                contact_phone="+919447111222",
                emergency_contact="+919447333444",
                required_date=today,
                urgency=RequestUrgency.CRITICAL,
                status=RequestStatus.PENDING,
                notes="Emergency neonatal exchange transfusion required immediately. Crossmatching ready.",
            ),
            BloodRequest(
                request_code="BR002",
                hospital_id=hospitals_data[0].id,  # Kottayam
                patient_name="Sreedharan Pillai (Orthopedic Surgery)",
                blood_group=BloodGroup.A_POSITIVE,
                units_requested=1,
                district="Kottayam",
                location="Kottayam Medical College OT 4",
                contact_phone="+919447222333",
                emergency_contact="+919447444555",
                required_date=today + timedelta(days=1),
                urgency=RequestUrgency.URGENT,
                status=RequestStatus.IN_PROGRESS,
                notes="Elective hip replacement surgery planned for tomorrow morning.",
            ),
            BloodRequest(
                request_code="BR003",
                hospital_id=hospitals_data[1].id,  # Ernakulam
                patient_name="Anitha Paul (Postpartum Hemorrhage)",
                blood_group=BloodGroup.B_POSITIVE,
                units_requested=3,
                district="Ernakulam",
                location="General Hospital Ernakulam Labour Room",
                contact_phone="+919447555666",
                emergency_contact="+919447777888",
                required_date=today,
                urgency=RequestUrgency.CRITICAL,
                status=RequestStatus.PENDING,
                notes="High priority emergency request for labor room hemorrhage.",
            ),
            BloodRequest(
                request_code="BR004",
                hospital_id=hospitals_data[1].id,  # Ernakulam
                patient_name="Master Devansh (Thalassemia Support)",
                blood_group=BloodGroup.O_NEGATIVE,  # Rare Group
                units_requested=1,
                district="Ernakulam",
                location="General Hospital Ernakulam Day Care",
                contact_phone="+919447888999",
                emergency_contact="+919447999000",
                required_date=today + timedelta(days=2),
                urgency=RequestUrgency.URGENT,
                status=RequestStatus.IN_PROGRESS,
                notes="Routine monthly transfusion for thalassemia major patient. Needs filtered blood.",
            ),
            BloodRequest(
                request_code="BR005",
                hospital_id=hospitals_data[2].id,  # Kozhikode
                patient_name="Kunjali Marakkar (Cardiothoracic ICU)",
                blood_group=BloodGroup.A_NEGATIVE,
                units_requested=2,
                district="Kozhikode",
                location="GMC Kozhikode CTVS ICU",
                contact_phone="+919895111222",
                emergency_contact="+919895333444",
                required_date=today + timedelta(days=1),
                urgency=RequestUrgency.CRITICAL,
                status=RequestStatus.PENDING,
                notes="Coronary artery bypass grafting surgery scheduled.",
            ),
            BloodRequest(
                request_code="BR006",
                hospital_id=hospitals_data[3].id,  # TVM
                patient_name="Radha Madhavan (Oncology Support)",
                blood_group=BloodGroup.AB_POSITIVE,
                units_requested=2,
                district="Thiruvananthapuram",
                location="Regional Cancer Centre Ward 3",
                contact_phone="+919447666777",
                emergency_contact="+919447888111",
                required_date=today + timedelta(days=2),
                urgency=RequestUrgency.NORMAL,
                status=RequestStatus.PENDING,
                notes="Chemotherapy induced thrombocytopenia support.",
            ),
            BloodRequest(
                request_code="BR007",
                hospital_id=hospitals_data[3].id,  # TVM
                patient_name="Venu Gopal (Accident Trauma)",
                blood_group=BloodGroup.O_POSITIVE,
                units_requested=1,
                district="Thiruvananthapuram",
                location="GMC Thiruvananthapuram Emergency Wing",
                contact_phone="+919447999111",
                emergency_contact="+919447222888",
                required_date=today - timedelta(days=2),
                urgency=RequestUrgency.NORMAL,
                status=RequestStatus.FULFILLED,
                notes="Patient successfully received 1 unit whole blood from voluntary replacement.",
            ),
        ]
        session.add_all(requests_data)
        await session.flush()
        print(f"[+] Added {len(requests_data)} clinical blood requests.")

        # Commit all transactions
        await session.commit()
        print("[*] Database successfully populated with realistic Kerala test dataset!")
        print("\n=======================================================")
        print("TEST LOGIN CREDENTIALS:")
        print("=======================================================")
        print("1. Super Admin:")
        print("   Email:    admin@rakthasethu.org")
        print("   Password: admin123")
        print("   Role:     SUPER_ADMIN (System-wide access)")
        print("\n2. Hospital Admin (Kottayam Medical College):")
        print("   Email:    kottayam.admin@rakthasethu.org")
        print("   Password: hospital123")
        print("   Role:     HOSPITAL_ADMIN (Kottayam scope)")
        print("\n3. Hospital Staff (Kottayam Medical College):")
        print("   Email:    kottayam.staff@rakthasethu.org")
        print("   Password: staff123")
        print("   Role:     STAFF (Kottayam operational)")
        print("\n4. Hospital Admin (Ernakulam General Hospital):")
        print("   Email:    ekm.admin@rakthasethu.org")
        print("   Password: hospital123")
        print("   Role:     HOSPITAL_ADMIN (Ernakulam scope)")
        print("\n5. Hospital Admin (Kozhikode Medical College):")
        print("   Email:    calicut.admin@rakthasethu.org")
        print("   Password: hospital123")
        print("   Role:     HOSPITAL_ADMIN (Kozhikode scope)")
        print("=======================================================\n")


if __name__ == "__main__":
    asyncio.run(seed_data())
