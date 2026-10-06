# Blood Request & Donation Workflow Hardening Specification

> [!IMPORTANT]
> **Operational Disclaimer:**
> **Matching a donor does not mean that the donor has agreed to donate.**
> Automated matching identifies biologically compatible, geographically proximate, and cooldown-eligible candidate donors. Volunteer donor confirmation, clinical pre-donation screening, and blood-bank cross-matching must be performed by hospital staff before transfusion.

---

## 1. End-to-End Core Workflow Lifecycle

```
[ Hospital Staff / Super Admin ]
               │
               ▼
   1. Create Blood Request (POST /api/v1/blood-requests)
               │ (Status: PENDING)
               ▼
   2. Fetch Eligible Donors (GET /api/v1/blood-requests/{id}/matches)
               │ (Invokes decoupled MatchingService)
               ▼
   3. Contact / Schedule Donor (POST /api/v1/donations)
               │ (Status: SCHEDULED, can have future date)
               ▼
   4. Transition Request to IN_PROGRESS (PATCH /api/v1/blood-requests/{id})
               │
               ▼
   5. Donation Occurs & Verified (PATCH /api/v1/donations/{id})
               │ (Status: COMPLETED, triggers 90/14/28-day cooldown)
               ▼
   6. Request Fulfilled (PATCH /api/v1/blood-requests/{id})
               │ (Status: FULFILLED, terminal state)
```

---

## 2. Blood Request State Machine Transitions

| From Status | Allowed Next Statuses | Terminal? | Notes |
| :--- | :--- | :--- | :--- |
| **`PENDING`** | `IN_PROGRESS`, `CANCELLED`, `REJECTED`, `PENDING` | No | Initial active state. Eligible for donor matching. |
| **`IN_PROGRESS`** | `FULFILLED`, `CANCELLED`, `REJECTED`, `IN_PROGRESS` | No | Donor contacted/scheduled. Eligible for donor matching. |
| **`FULFILLED`** | `FULFILLED` | **Yes** | Demand satisfied. Cannot transition back to active/pending. |
| **`CANCELLED`** | `CANCELLED` | **Yes** | Cancelled by patient/hospital. Cannot be matched or fulfilled. |
| **`REJECTED`** | `REJECTED` | **Yes** | Rejected by clinical staff. Cannot be matched or fulfilled. |

### Forbidden Transitions
- `FULFILLED` $\to$ `PENDING` / `IN_PROGRESS` (Rejected with `422 VALIDATION_ERROR`)
- `CANCELLED` $\to$ `FULFILLED` / `PENDING` (Rejected with `422 VALIDATION_ERROR`)
- `REJECTED` $\to$ `FULFILLED` / `PENDING` (Rejected with `422 VALIDATION_ERROR`)

---

## 3. Donation State Machine Transitions

| From Status | Allowed Next Statuses | Terminal? | Notes |
| :--- | :--- | :--- | :--- |
| **`SCHEDULED`** | `COMPLETED`, `CANCELLED`, `REJECTED`, `SCHEDULED` | No | Appointment planned. May have a future `donation_date`. |
| **`COMPLETED`** | `COMPLETED` | **Yes** | Donation performed and logged. Triggers cooldown. Cannot have future date. |
| **`CANCELLED`** | `CANCELLED` | **Yes** | Donor missed appointment. Does NOT trigger cooldown. |
| **`REJECTED`** | `REJECTED` | **Yes** | Donor failed pre-donation vitals/Hb test. Does NOT trigger cooldown. |

### Cooldown & Date Enforcement
1. **No Future Completed Donations**: Attempting to record `status = 'COMPLETED'` with `donation_date > today` is rejected with `422 VALIDATION_ERROR`.
2. **Cooldown Protection**: Attempting to record `status = 'COMPLETED'` for a donor who completed a whole blood donation $< 90$ days prior is rejected with `422 VALIDATION_ERROR`.

---

## 4. Matching Service Integration

- The blood request workflow reuses `MatchingService` without duplicating any compatibility or cooldown logic.
- Route: `GET /api/v1/blood-requests/{id}/matches?limit=20`
- **State Guard**: Only `PENDING` and `IN_PROGRESS` blood requests are matchable. Matching against `FULFILLED`, `CANCELLED`, or `REJECTED` requests raises `422 VALIDATION_ERROR`.
- **Hospital Scope Guard**: Hospital users attempting to match blood requests belonging to another hospital receive `403 HOSPITAL_ACCESS_DENIED`.

---

## 5. Required Units & Fulfillment Separation

- The system intentionally does **NOT** assume $1\text{ donor} = 1\text{ unit}$ or automatically mark requests fulfilled upon donor discovery.
- Required units represent demand quantity; fulfillment is a distinct clinical lifecycle transition performed when blood collection and verification are confirmed.

---

## 6. RBAC & IDOR Prevention Matrix

| Role | Blood Request Permissions | Donation Ledger Permissions | Matching Scope |
| :--- | :--- | :--- | :--- |
| **`SUPER_ADMIN`** | Create, view, update, and match across all hospitals system-wide. | Create, view, update donations across all hospitals. | System-wide search across all districts. |
| **`HOSPITAL_ADMIN`** | Scoped strictly to `hospital_id`. Cannot mutate or match other hospitals' requests. | Scoped strictly to `hospital_id`. Cannot mutate other hospitals' donations. | Hospital and district donor search. |
| **`STAFF`** | Operational access scoped to `hospital_id`. | Operational access scoped to `hospital_id`. | Hospital and district donor search. |

---

## 7. Deferred Components (Future Phases)
- WhatsApp Cloud API messaging and automated SMS dispatch.
- NLP conversational intake for patient blood requests.
- Multi-party transfusion inventory allocation models.
