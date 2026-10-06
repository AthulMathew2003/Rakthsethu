# Frontend API Migration Guide (Phase 3 Documentation)

> **Important:** The React frontend codebase has been preserved in its original state and was NOT modified during this phase. This document serves as the roadmap for upgrading the frontend API client (`src/api.js`) to the `/api/v1` architecture.

---

## 1. Route Comparison Table

| Feature / Domain | Legacy Frontend Path (`src/api.js`) | Standardized Backend Path (`app/api/v1/*`) | Notes |
| :--- | :--- | :--- | :--- |
| **Authentication** | `POST /api/auth/login` | `POST /api/v1/auth/login` | Payload `{ email, password }` matching; returns JWT & UserResponse in standard envelope |
| **User Profile** | `GET /api/auth/me` | `GET /api/v1/auth/me` | Validates `Bearer <token>` |
| **Hospitals List** | `GET /api/hospitals` | `GET /api/v1/hospitals` | Supports `search`, `district`, `is_active`, `page`, `page_size` |
| **Create Hospital**| `POST /api/hospitals` | `POST /api/v1/hospitals` | Requires `SUPER_ADMIN` token |
| **Update Hospital**| `PUT /api/hospitals/{id}` | `PATCH /api/v1/hospitals/{id}` | Standard HTTP PATCH for partial updates |
| **Donors List** | `GET /api/donors` | `GET /api/v1/donors` | Paginated output; includes `last_donation_date` computed dynamically |
| **Create Donor** | `POST /api/donors` | `POST /api/v1/donors` | Enforces E.164 phone normalization and unique phone validation |
| **Update Donor** | `PUT /api/donors/{id}` | `PATCH /api/v1/donors/{id}` | Partial update for availability/contact information |
| **Donations List** | `GET /api/donations` | `GET /api/v1/donations` | Paginated output with donor name and blood group joined |
| **Create Donation**| `POST /api/donations` | `POST /api/v1/donations` | Requires integer `donor_id` (foreign key) rather than raw donor name |
| **Requests List** | `GET /api/requests` | `GET /api/v1/blood-requests` | Standardized resource pluralization (`blood-requests`) |
| **Create Request** | `POST /api/requests` | `POST /api/v1/blood-requests` | Validates integer `hospital_id` and positive units |
| **Update Request** | `PUT /api/requests/{id}` | `PATCH /api/v1/blood-requests/{id}` | Updates status or details |

---

## 2. Response Envelope Integration

The React frontend currently reads raw arrays or objects from API calls. The new backend returns data wrapped in the standard envelope:
```javascript
// Example: Extracting data from response
const response = await apiFetch('/api/v1/donors');
const donors = response.data.items; // Paginated list
const totalCount = response.data.total;
```
