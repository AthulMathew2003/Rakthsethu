# Rakthasethu Authorization & RBAC Specification

## 1. Role Definitions

The Rakthasethu administration and operational platform enforces Role-Based Access Control (RBAC) across three distinct tiers:

1. **`SUPER_ADMIN`:** System-wide superuser with unrestricted access to all facilities, hospital configurations, user management, and platform analytics.
2. **`HOSPITAL_ADMIN`:** Department or hospital lead responsible for their specific facility's blood requests, staff oversight, and hospital profile updates.
3. **`STAFF`:** Operational blood bank or healthcare worker assigned to a hospital, capable of registering donors, logging donations, and submitting blood requests.

---

## 2. Permission Matrix

| Operation | Target Resource | `SUPER_ADMIN` | `HOSPITAL_ADMIN` | `STAFF` | Public |
| :--- | :--- | :---: | :---: | :---: | :---: |
| **Login / Auth** | `/api/v1/auth/login` | ✅ | ✅ | ✅ | ✅ |
| **Get My Profile** | `/api/v1/auth/me` | ✅ | ✅ | ✅ | ❌ |
| **Create Users** | `/api/v1/auth/users` | ✅ | ❌ | ❌ | ❌ |
| **Create Hospital** | `/api/v1/hospitals` | ✅ | ❌ | ❌ | ❌ |
| **List Hospitals** | `/api/v1/hospitals` | ✅ | ✅ | ✅ | ❌ |
| **View Hospital** | `/api/v1/hospitals/{id}` | ✅ | ✅ | ✅ | ❌ |
| **Update Hospital**| `/api/v1/hospitals/{id}` | ✅ | ✅ (Own Facility Only) | ❌ | ❌ |
| **Register Donor** | `/api/v1/donors` | ✅ | ✅ (Own Facility Tagged) | ✅ (Own Facility Tagged) | ❌ |
| **List Donors** | `/api/v1/donors` | ✅ | ✅ | ✅ | ❌ |
| **View Donor** | `/api/v1/donors/{id}` | ✅ | ✅ | ✅ | ❌ |
| **Update Donor** | `/api/v1/donors/{id}` | ✅ | ✅ | ✅ | ❌ |
| **Record Donation**| `/api/v1/donations` | ✅ | ✅ | ✅ | ❌ |
| **List Donations** | `/api/v1/donations` | ✅ | ✅ | ✅ | ❌ |
| **Create Request** | `/api/v1/blood-requests` | ✅ | ✅ (Own Facility Only) | ✅ (Own Facility Only) | ❌ |
| **List Requests** | `/api/v1/blood-requests` | ✅ | ✅ | ✅ | ❌ |
| **Update Request** | `/api/v1/blood-requests/{id}` | ✅ | ✅ (Own Facility Only) | ✅ (Own Facility Only) | ❌ |

---

## 3. Hospital Scoping Enforcement

Hospital isolation is enforced strictly on the backend via dependency validation:

* When a `HOSPITAL_ADMIN` or `STAFF` user submits a blood request or updates a hospital entity, the backend verifies that `user.hospital_id == resource.hospital_id`.
* If a hospital staff user attempts to modify or create a resource for another hospital ID, the request is immediately rejected with `HTTP 403 Forbidden` (`HOSPITAL_ACCESS_DENIED`).
* `SUPER_ADMIN` users bypass hospital scoping checks (`user.hospital_id` is `NULL`).
