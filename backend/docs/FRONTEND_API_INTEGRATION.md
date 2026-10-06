# Rakthasethu Frontend API Integration & Architecture Guide

## Overview
This document specifies the integration architecture connecting the React (Vite) frontend to the FastAPI + PostgreSQL backend for Rakthasethu.

---

## 1. Environment Configuration

The frontend uses Vite environment variables:
- `VITE_API_BASE_URL`: Defines the root versioned backend endpoint (e.g. `http://127.0.0.1:8000/api/v1`).
- `.env` and `.env.example` files are maintained at the project root.
- No secrets or private tokens are stored in `VITE_*` variables.

---

## 2. Central API Client (`src/api.js`)

### Response Envelope Handling
The backend returns a unified `ApiResponse[T]` payload:
```json
{
  "success": true,
  "message": "...",
  "data": { ... },
  "requestId": "req_...",
  "error": null
}
```
The frontend API client automatically:
1. Validates HTTP status code.
2. Checks `success: true`.
3. Unwraps and returns `data` directly to callers.
4. On error (`success: false` or HTTP status >= 400), constructs and throws a custom `ApiError(message, status, code, details)`.
5. On HTTP 401 (`UNAUTHORIZED`), automatically clears the access token and stored user session.

---

## 3. Authentication & RBAC

### Flow
1. User enters email and password on `/login`.
2. Client calls `POST /api/v1/auth/login`.
3. On success:
   - `access_token` is stored in `localStorage` under `access_token`.
   - `Authorization: Bearer <token>` is injected on all subsequent API requests.
   - User profile with role (`SUPER_ADMIN`, `HOSPITAL_ADMIN`, `STAFF`, `CITIZEN`) is saved to context.
4. Protected routes verify user role and redirect unauthenticated access.
5. On mount, `fetchCurrentUser()` (`GET /api/v1/auth/me`) validates active session.

---

## 4. Key Workflows

### 4.1. Donor Management
- **List/Search:** `GET /api/v1/donors?search=...&blood_group=...&district=...&is_available=...&page=...&page_size=...`
- **Creation:** `POST /api/v1/donors`
- **Edit / Deactivate:** `PATCH /api/v1/donors/{id}`

### 4.2. Hospital Donor Bulk Import (CSV / XLSX)
- **Preview & Validation:** `POST /api/v1/donors/import/preview` (multipart form).
  - Displays validation counts (total, valid, invalid, new, update).
  - Shows row-level preview table and error markers before committing.
- **Execution:** `POST /api/v1/donors/import` (multipart form).
  - Performs canonical deduplication and inserts/updates registry records.
  - Returns final counts: `new_donors_created`, `existing_donors_updated`, `failed_records`.

### 4.3. Blood Requests & Matching Engine
- **List/Filter:** `GET /api/v1/blood-requests`
- **Create:** `POST /api/v1/blood-requests`
- **Update/Cancel:** `PATCH /api/v1/blood-requests/{id}`
- **Matching:** `GET /api/v1/blood-requests/{id}/matches?limit=20`
  - Evaluates ABO/Rh blood compatibility matrix.
  - Filters by geographic district/panchayat.
  - Applies 90-day cooldown calculation.
  - Clearly displays clinical disclaimer: *"Matching an eligible donor indicates compatibility and cooldown compliance; it does not constitute consent or a confirmed donation appointment."*

### 4.4. Blood Donations & Cooldown Rules
- **List:** `GET /api/v1/donations`
- **Record Donation:** `POST /api/v1/donations`
  - Validates date (`donation_date <= today` for completed donations).
  - Enforces 90-day whole-blood cooldown against prior completed donations.
- **Status Updates:** `PATCH /api/v1/donations/{id}` (`SCHEDULED` $\to$ `COMPLETED`, `CANCELLED`, `REJECTED`).

---

## 5. Local Development Setup

1. **Backend:**
   ```bash
   cd backend
   uvicorn app.main:app --reload --port 8000
   ```
2. **Frontend:**
   ```bash
   npm install
   npm run dev
   ```
3. Open `http://localhost:5173`.
