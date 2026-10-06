# Rakthasethu Database Schema Review (Final Approved Specification)

This document summarizes the final reviewed PostgreSQL schema for **Rakthasethu** prior to applying the initial Alembic migration.

---

## 1. Custom PostgreSQL Enumerations

```sql
CREATE TYPE blood_group_enum AS ENUM (
    'A+', 'A-', 'B+', 'B-', 'AB+', 'AB-', 'O+', 'O-'
);

CREATE TYPE user_role_enum AS ENUM (
    'SUPER_ADMIN', 'HOSPITAL_ADMIN', 'STAFF'
);

CREATE TYPE donation_status_enum AS ENUM (
    'SCHEDULED', 'COMPLETED', 'CANCELLED', 'REJECTED'
);

CREATE TYPE request_status_enum AS ENUM (
    'PENDING', 'IN_PROGRESS', 'FULFILLED', 'CANCELLED', 'REJECTED'
);

CREATE TYPE request_urgency_enum AS ENUM (
    'NORMAL', 'URGENT', 'CRITICAL'
);

CREATE TYPE import_status_enum AS ENUM (
    'PENDING', 'PROCESSING', 'COMPLETED', 'FAILED'
);
```

---

## 2. Table Specifications

### 2.1 Table: `hospitals`
| Column | Type | Nullable | Default | Key / Constraint | Description |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `id` | `INTEGER` | `NO` | `nextval()` | `PRIMARY KEY` | Auto-increment primary key |
| `hospital_code` | `VARCHAR(32)` | `NO` | None | `UNIQUE`, `NOT NULL` | External reference code (e.g. HOSP001) |
| `name` | `VARCHAR(255)` | `NO` | None | `NOT NULL` | Facility name |
| `hospital_type` | `VARCHAR(50)` | `NO` | `'Government'` | `NOT NULL` | Government / Private |
| `district` | `VARCHAR(100)` | `NO` | None | `NOT NULL` | District location |
| `panchayat` | `VARCHAR(100)` | `YES` | `NULL` | None | Local panchayat/body |
| `address` | `TEXT` | `NO` | None | `NOT NULL` | Physical address |
| `phone` | `VARCHAR(20)` | `YES` | `NULL` | None | Contact telephone |
| `email` | `VARCHAR(120)` | `YES` | `NULL` | None | Contact email |
| `emergency_number` | `VARCHAR(20)` | `YES` | `NULL` | None | 24/7 Helpline |
| `latitude` | `DOUBLE PRECISION`| `YES` | `NULL` | None | GPS Latitude |
| `longitude` | `DOUBLE PRECISION`| `YES` | `NULL` | None | GPS Longitude |
| `is_active` | `BOOLEAN` | `NO` | `TRUE` | `NOT NULL` | Active status |
| `created_at` | `TIMESTAMPTZ` | `NO` | `CURRENT_TIMESTAMP` | `NOT NULL` | Creation timestamp |
| `updated_at` | `TIMESTAMPTZ` | `NO` | `CURRENT_TIMESTAMP` | `NOT NULL` | Last updated timestamp |

---

### 2.2 Table: `users`
| Column | Type | Nullable | Default | Key / Constraint | Description |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `id` | `INTEGER` | `NO` | `nextval()` | `PRIMARY KEY` | Auto-increment primary key |
| `user_code` | `VARCHAR(32)` | `NO` | None | `UNIQUE`, `NOT NULL` | User identifier code |
| `hospital_id` | `INTEGER` | `YES` | `NULL` | `FK -> hospitals(id) ON DELETE SET NULL` | Linked hospital (NULL for Super Admin) |
| `email` | `VARCHAR(120)` | `NO` | None | `UNIQUE`, `NOT NULL` | Authentication login email |
| `hashed_password` | `VARCHAR(255)` | `NO` | None | `NOT NULL` | Securely hashed password |
| `full_name` | `VARCHAR(150)` | `NO` | None | `NOT NULL` | User full name |
| `phone_number` | `VARCHAR(20)` | `YES` | `NULL` | None | Contact number |
| `role` | `user_role_enum` | `NO` | `'STAFF'` | `NOT NULL` | RBAC Role |
| `district` | `VARCHAR(100)` | `YES` | `NULL` | None | Assigned jurisdiction district |
| `panchayat` | `VARCHAR(100)` | `YES` | `NULL` | None | Assigned jurisdiction panchayat |
| `is_active` | `BOOLEAN` | `NO` | `TRUE` | `NOT NULL` | Account active flag |
| `last_login_at` | `TIMESTAMPTZ` | `YES` | `NULL` | None | Last authentication timestamp |
| `created_at` | `TIMESTAMPTZ` | `NO` | `CURRENT_TIMESTAMP` | `NOT NULL` | Creation timestamp |
| `updated_at` | `TIMESTAMPTZ` | `NO` | `CURRENT_TIMESTAMP` | `NOT NULL` | Last update timestamp |

---

### 2.3 Table: `donors`
| Column | Type | Nullable | Default | Key / Constraint | Description |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `id` | `INTEGER` | `NO` | `nextval()` | `PRIMARY KEY` | Auto-increment primary key |
| `donor_code` | `VARCHAR(32)` | `NO` | None | `UNIQUE`, `NOT NULL` | Public donor code (e.g. DON001) |
| `hospital_id` | `INTEGER` | `YES` | `NULL` | `FK -> hospitals(id) ON DELETE SET NULL` | Sourcing/Onboarding hospital |
| `full_name` | `VARCHAR(150)` | `NO` | None | `NOT NULL` | Legal full name |
| `blood_group` | `blood_group_enum`| `NO` | None | `NOT NULL` | Controlled ABO/Rh group |
| `gender` | `VARCHAR(20)` | `YES` | `NULL` | None | Gender metadata |
| `phone` | `VARCHAR(20)` | `NO` | None | `UNIQUE`, `NOT NULL` | Normalized canonical phone |
| `email` | `VARCHAR(120)` | `YES` | `NULL` | None | Contact email |
| `district` | `VARCHAR(100)` | `NO` | None | `NOT NULL` | Residence district |
| `panchayat` | `VARCHAR(100)` | `YES` | `NULL` | None | Local village / municipality |
| `address` | `TEXT` | `YES` | `NULL` | None | Full residential address |
| `is_active` | `BOOLEAN` | `NO` | `TRUE` | `NOT NULL` | Soft-delete / record validity |
| `is_available` | `BOOLEAN` | `NO` | `TRUE` | `NOT NULL` | Opt-in contact availability |
| `created_at` | `TIMESTAMPTZ` | `NO` | `CURRENT_TIMESTAMP` | `NOT NULL` | Registration timestamp |
| `updated_at` | `TIMESTAMPTZ` | `NO` | `CURRENT_TIMESTAMP` | `NOT NULL` | Last update timestamp |

---

### 2.4 Table: `donations`
| Column | Type | Nullable | Default | Key / Constraint | Description |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `id` | `INTEGER` | `NO` | `nextval()` | `PRIMARY KEY` | Auto-increment primary key |
| `donation_code` | `VARCHAR(32)` | `NO` | None | `UNIQUE`, `NOT NULL` | Ledger transaction code |
| `donor_id` | `INTEGER` | `NO` | None | `FK -> donors(id) ON DELETE RESTRICT` | Linked donor (**RESTRICT** protects history) |
| `hospital_id` | `INTEGER` | `YES` | `NULL` | `FK -> hospitals(id) ON DELETE SET NULL` | Collecting facility |
| `donation_date` | `DATE` | `NO` | None | `NOT NULL` | Date of donation event |
| `donation_type` | `VARCHAR(50)` | `NO` | `'Voluntary'` | `NOT NULL` | Voluntary, Replacement, Camp |
| `units_donated` | `INTEGER` | `NO` | `1` | `CHECK (units_donated > 0)` | Whole blood units count |
| `status` | `donation_status_enum`| `NO`| `'COMPLETED'`| `NOT NULL` | Status of donation event |
| `notes` | `TEXT` | `YES` | `NULL` | None | Clinical notes |
| `created_at` | `TIMESTAMPTZ` | `NO` | `CURRENT_TIMESTAMP` | `NOT NULL` | Entry timestamp |

---

### 2.5 Table: `blood_requests`
| Column | Type | Nullable | Default | Key / Constraint | Description |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `id` | `INTEGER` | `NO` | `nextval()` | `PRIMARY KEY` | Auto-increment primary key |
| `request_code` | `VARCHAR(32)` | `NO` | None | `UNIQUE`, `NOT NULL` | Request identifier code |
| `hospital_id` | `INTEGER` | `NO` | None | `FK -> hospitals(id) ON DELETE RESTRICT` | Requesting hospital |
| `patient_name` | `VARCHAR(150)` | `NO` | None | `NOT NULL` | Patient name or hospital clinical case ref |
| `blood_group` | `blood_group_enum`| `NO` | None | `NOT NULL` | Required blood type |
| `units_requested`| `INTEGER` | `NO` | `1` | `CHECK (units_requested > 0)` | Units needed |
| `district` | `VARCHAR(100)` | `NO` | None | `NOT NULL` | Target delivery district |
| `location` | `VARCHAR(255)` | `YES` | `NULL` | None | Ward / Room / Location |
| `contact_phone` | `VARCHAR(20)` | `NO` | None | `NOT NULL` | Primary emergency contact |
| `emergency_contact`| `VARCHAR(20)`| `YES` | `NULL` | None | Secondary contact |
| `required_date` | `DATE` | `NO` | None | `NOT NULL` | Deadline requirement date |
| `urgency` | `request_urgency_enum`| `NO`| `'NORMAL'` | `NOT NULL` | Urgency level |
| `status` | `request_status_enum`| `NO` | `'PENDING'` | `NOT NULL` | Request status pipeline |
| `notes` | `TEXT` | `YES` | `NULL` | None | Additional notes |
| `created_at` | `TIMESTAMPTZ` | `NO` | `CURRENT_TIMESTAMP` | `NOT NULL` | Creation timestamp |
| `updated_at` | `TIMESTAMPTZ` | `NO` | `CURRENT_TIMESTAMP` | `NOT NULL` | Last update timestamp |

---

### 2.6 Table: `donor_import_batches`
| Column | Type | Nullable | Default | Key / Constraint | Description |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `id` | `INTEGER` | `NO` | `nextval()` | `PRIMARY KEY` | Batch ID |
| `batch_code` | `VARCHAR(32)` | `NO` | None | `UNIQUE`, `NOT NULL` | Batch tracking code (e.g. IMP001) |
| `hospital_id` | `INTEGER` | `YES` | `NULL` | `FK -> hospitals(id) ON DELETE SET NULL` | Uploading hospital |
| `uploaded_by_user_id`| `INTEGER` | `YES` | `NULL` | `FK -> users(id) ON DELETE SET NULL` | Uploading staff user |
| `filename` | `VARCHAR(255)` | `NO` | None | `NOT NULL` | Uploaded file name |
| `file_format` | `VARCHAR(10)` | `NO` | `'csv'` | `NOT NULL` | 'csv', 'xlsx', 'xls' |
| `total_records` | `INTEGER` | `NO` | `0` | `NOT NULL` | Total parsed rows |
| `successful_records`| `INTEGER` | `NO` | `0` | `NOT NULL` | Successfully processed records |
| `failed_records` | `INTEGER` | `NO` | `0` | `NOT NULL` | Errored/rejected records |
| `status` | `import_status_enum` | `NO` | `'PENDING'` | `NOT NULL` | Batch execution status |
| `error_summary` | `TEXT` | `YES` | `NULL` | None | Detailed error log |
| `created_at` | `TIMESTAMPTZ` | `NO` | `CURRENT_TIMESTAMP` | `NOT NULL` | Creation timestamp |
| `completed_at` | `TIMESTAMPTZ` | `YES` | `NULL` | None | Batch completion timestamp |

---

## 3. Foreign Key References & Cascades

| Child Table | Foreign Key | Parent Table | Parent Key | ON DELETE |
| :--- | :--- | :--- | :--- | :--- |
| `users` | `hospital_id` | `hospitals` | `id` | `SET NULL` |
| `donors` | `hospital_id` | `hospitals` | `id` | `SET NULL` |
| `donations` | `donor_id` | `donors` | `id` | `RESTRICT` |
| `donations` | `hospital_id` | `hospitals` | `id` | `SET NULL` |
| `blood_requests` | `hospital_id` | `hospitals` | `id` | `RESTRICT` |
| `donor_import_batches`| `hospital_id` | `hospitals` | `id` | `SET NULL` |
| `donor_import_batches`| `uploaded_by_user_id` | `users` | `id` | `SET NULL` |

---

## 4. Final Indexes

```sql
-- Donors Matching Indexes
CREATE INDEX idx_donors_blood_group ON donors(blood_group);
CREATE INDEX idx_donors_district ON donors(district);
CREATE INDEX idx_donors_active_available ON donors(is_active, is_available);
CREATE INDEX idx_donors_matching_composite ON donors(blood_group, district, is_active, is_available);

-- Donations Ledger Indexes
CREATE INDEX idx_donations_donor_id ON donations(donor_id);
CREATE INDEX idx_donations_hospital_id ON donations(hospital_id);
CREATE INDEX idx_donations_date_status ON donations(donation_date, status);

-- Blood Requests Pipeline Indexes
CREATE INDEX idx_requests_status ON blood_requests(status);
CREATE INDEX idx_requests_urgency ON blood_requests(urgency);
CREATE INDEX idx_requests_district ON blood_requests(district);
CREATE INDEX idx_requests_blood_group ON blood_requests(blood_group);
CREATE INDEX idx_requests_hospital_id ON blood_requests(hospital_id);

-- Hospitals & Users Indexes
CREATE INDEX idx_hospitals_district ON hospitals(district);
CREATE INDEX idx_hospitals_is_active ON hospitals(is_active);
CREATE INDEX idx_users_hospital_id ON users(hospital_id);
CREATE INDEX idx_users_email ON users(email);

-- Import Batch Indexes
CREATE INDEX idx_import_batches_hospital_id ON donor_import_batches(hospital_id);
CREATE INDEX idx_import_batches_status ON donor_import_batches(status);
```
