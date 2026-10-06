# Rakthasethu API Architecture Specification

## 1. Architectural Overview & Layers

The Rakthasethu FastAPI backend is designed around a strictly decoupled, 5-tier layered architecture:

```
[ HTTP Client (Web Dashboard / Future Chatbot) ]
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│ 1. API Route Layer (FastAPI Routers: app/api/v1/*)           │
│    - Handles HTTP verbs, route definitions, query parameters │
│    - Extracts dependencies (current_user, database session)  │
│    - Dispatches to business services                         │
└──────────────────────────────┬──────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│ 2. Schema Validation Layer (Pydantic v2: app/schemas/*)      │
│    - Validates request payloads and query constraints        │
│    - Serializes output into standard response envelopes      │
│    - Enforces enum types and data types                      │
└──────────────────────────────┬──────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│ 3. Service Layer (Business Logic: app/services/*)           │
│    - Coordinates domain operations & business validation     │
│    - Enforces security, phone normalization & RBAC scoping   │
│    - Controls database transaction commits and rollbacks     │
└──────────────────────────────┬──────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│ 4. Repository Layer (Data Access: app/repositories/*)        │
│    - Performs SQL queries via SQLAlchemy 2.0 select()        │
│    - Handles SQL-level pagination and filtering              │
│    - Abstracts database queries from business services       │
└──────────────────────────────┬──────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│ 5. Database & ORM Layer (SQLAlchemy 2.x / PostgreSQL 16)    │
│    - Declarative models (app/models/*)                       │
│    - AsyncPG asynchronous engine pool (app/core/database.py) │
│    - PostgreSQL 16 server (Docker container / Native)        │
└─────────────────────────────────────────────────────────────┘
```

---

## 2. API Versioning & Routing Conventions

All application endpoints are strictly versioned under the `/api/v1` namespace.

* **Base Prefix:** `/api/v1`
* **Root Health Check:** `GET /health` (Unversioned system status check)

### Complete v1 Route Map:
| Method | Path | Summary | Access Level |
| :--- | :--- | :--- | :--- |
| `POST` | `/api/v1/auth/login` | Authenticate user & issue JWT | Public |
| `GET` | `/api/v1/auth/me` | Fetch active authenticated profile | Authenticated (Any Role) |
| `POST` | `/api/v1/auth/users` | Register admin or staff user account | `SUPER_ADMIN` only |
| `POST` | `/api/v1/hospitals` | Create hospital profile | `SUPER_ADMIN` only |
| `GET` | `/api/v1/hospitals` | List and search hospitals (Paginated) | Authenticated (Any Role) |
| `GET` | `/api/v1/hospitals/{id}` | Get hospital details by ID | Authenticated (Any Role) |
| `PATCH` | `/api/v1/hospitals/{id}` | Update hospital profile | `SUPER_ADMIN` / `HOSPITAL_ADMIN` |
| `POST` | `/api/v1/donors` | Register a new voluntary blood donor | Staff / Hospital Admin / Super Admin |
| `POST` | `/api/v1/donors/import/preview` | Dry-run preview & validation of CSV/XLSX donor file | Staff / Hospital Admin / Super Admin |
| `POST` | `/api/v1/donors/import` | Bulk import donors from CSV/XLSX into registry | Staff / Hospital Admin / Super Admin |
| `GET` | `/api/v1/donors/imports` | List bulk import batches and status (Paginated) | Staff / Hospital Admin / Super Admin |
| `GET` | `/api/v1/donors/imports/{batch_id}` | Retrieve specific import batch audit details | Staff / Hospital Admin / Super Admin |
| `GET` | `/api/v1/donors` | List and search donors (Paginated) | Authenticated (Any Role) |
| `GET` | `/api/v1/donors/{id}` | Get donor profile + latest donation date | Authenticated (Any Role) |
| `PATCH` | `/api/v1/donors/{id}` | Update donor profile / availability | Staff / Hospital Admin / Super Admin |
| `POST` | `/api/v1/donations` | Record blood donation event | Staff / Hospital Admin / Super Admin |
| `GET` | `/api/v1/donations` | List donation ledger (Paginated) | Authenticated (Any Role) |
| `GET` | `/api/v1/donations/{id}` | Get donation transaction details | Authenticated (Any Role) |
| `PATCH` | `/api/v1/donations/{id}` | Update donation status (SCHEDULED -> COMPLETED/CANCELLED) | Staff / Hospital Admin / Super Admin |
| `POST` | `/api/v1/blood-requests` | Submit clinical patient blood request | Staff / Hospital Admin / Super Admin |
| `GET` | `/api/v1/blood-requests` | List clinical requests (Paginated) | Authenticated (Any Role) |
| `GET` | `/api/v1/blood-requests/{id}` | Get blood request details | Authenticated (Any Role) |
| `PATCH` | `/api/v1/blood-requests/{id}` | Update blood request status (PENDING -> IN_PROGRESS -> FULFILLED) | Staff / Hospital Admin / Super Admin |
| `GET` | `/api/v1/blood-requests/{id}/matches` | Find matching eligible donors for a blood request | Staff / Hospital Admin / Super Admin |
| `POST` | `/api/v1/matching/donors` | Standalone search & rank eligible blood donors | Authenticated (Any Role) |

---

## 3. Standard API Response Envelope

All API endpoints wrap their payload in a consistent, predictable JSON envelope.

### Successful Response Format (`HTTP 200 / 201`):
```json
{
  "success": true,
  "message": "Donor registered successfully.",
  "data": {
    "id": 1,
    "donor_code": "DON00001",
    "full_name": "Sruthy M S",
    "blood_group": "O+",
    "phone": "+919876543210",
    "district": "Kottayam",
    "is_active": true,
    "is_available": true,
    "last_donation_date": null,
    "created_at": "2026-09-24T22:00:00Z",
    "updated_at": "2026-09-24T22:00:00Z"
  },
  "requestId": "550e8400-e29b-41d4-a716-446655440000",
  "error": null
}
```

### Error Response Format (`HTTP 4xx / 5xx`):
```json
{
  "success": false,
  "message": "Donor with phone number '+919876543210' already exists.",
  "data": null,
  "requestId": "550e8400-e29b-41d4-a716-446655440000",
  "error": {
    "code": "DUPLICATE_RESOURCE",
    "details": null
  }
}
```

---

## 4. SQL-Level Pagination Schema

List endpoints utilize database `OFFSET` and `LIMIT` calculations, returning pagination metadata:

```json
{
  "items": [...],
  "page": 1,
  "page_size": 20,
  "total": 142,
  "total_pages": 8
}
```

---

## 5. Phone Normalization Strategy

To guarantee identity consistency across manual entries and future hospital imports:
* All phone inputs are stripped of whitespace, dashes, and brackets.
* Standard 10-digit Indian numbers (`9876543210`) are normalized to international E.164 format (`+919876543210`).
* Leading zeros (`09876543210`) are converted to `+919876543210`.
* Invalid string formats raise a `ValidationException` (HTTP 422).
