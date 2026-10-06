# Blood Donor Matching & Medical Policy Specification

> [!NOTE]
> **Medical / Clinical Disclaimer:**
> The policies documented herein represent the automated computational rules adopted by the Rakthasethu platform for preliminary donor filtering and volunteer matching. In clinical practice, all blood transfusions must undergo rigorous ABO/Rh cross-matching, antibody screening, and donor pre-donation screening under the direct supervision of licensed blood-bank officers and medical professionals.

---

## 1. Blood Component Matching Policy

The matching engine defaults to standard **Red Blood Cell (RBC) and Whole Blood ABO & Rh D-antigen compatibility**.

### Biological Compatibility Matrix (Recipient $\to$ Eligible Donors)

| Recipient Blood Group | Identical Group (Priority 1) | Compatible Subtype / Universal Donors (Priority 2) |
| :--- | :--- | :--- |
| **O-** | `O-` | *None (O- can only receive O-)* |
| **O+** | `O+` | `O-` |
| **A-** | `A-` | `O-` |
| **A+** | `A+` | `A-`, `O+`, `O-` |
| **B-** | `B-` | `O-` |
| **B+** | `B+` | `B-`, `O+`, `O-` |
| **AB-** | `AB-` | `A-`, `B-`, `O-` |
| **AB+** (Universal Recipient) | `AB+` | `AB-`, `A+`, `A-`, `B+`, `B-`, `O+`, `O-` |

*Note: O Negative is the Universal RBC donor, and AB Positive is the Universal RBC recipient.*

---

## 2. Donation Cooldown & Rest Interval Policy

To safeguard voluntary donor health and ensure adequate red blood cell/iron replenishment, mandatory cooldown windows are enforced between donations.

### Configurable Cooldown Durations (Environment Settings)
* **Whole Blood (`WHOLE_BLOOD_COOLDOWN_DAYS`)**: Default **90 days** (approx. 3 months).
* **Platelets / Apheresis (`PLATELET_COOLDOWN_DAYS`)**: Default **14 days** (2 weeks).
* **Plasma (`PLASMA_COOLDOWN_DAYS`)**: Default **28 days** (4 weeks).

### Cooldown Computation Rules
1. **Donation Status Considered**: Only donations marked with `status = 'COMPLETED'` trigger the cooldown period.
2. **Ignored Records**: `CANCELLED`, `REJECTED`, or `SCHEDULED` donations do **NOT** penalize the donor.
3. **First-Time Donors**: If a donor has zero completed donations recorded in the database, their `days_remaining = 0` and they are immediately eligible.
4. **Latest Donation Anchor**: Eligibility is calculated as:
   $$\text{Eligible From} = \text{Latest Completed Donation Date} + \text{Cooldown Days}$$
   $$\text{Days Remaining} = \max(0, \text{Eligible From} - \text{Reference Date})$$

---

## 3. Geographic & Location Matching

1. **Primary Boundary (District Level)**:
   - Matching is strictly bounded by the patient's target `district` (case-insensitive match, e.g. `Kottayam`).
2. **Proximity Refinement (Panchayat / Taluk Level)**:
   - When a `panchayat` is provided in the request, eligible donors residing in the exact matching panchayat are given priority ranking over donors from other areas in the same district.
3. **Cross-District Search**:
   - Cross-district searching is disabled by default to minimize donor transit delay during critical emergencies.

---

## 4. Donor Eligibility Filter Hierarchy

A donor record must satisfy **ALL** of the following conditions simultaneously to be returned as an eligible candidate:

```
[ All Centralized Donors ]
           │
           ▼
[ is_active = TRUE ] ──── (Filters out archived or soft-deleted donors)
           │
           ▼
[ is_available = TRUE ] ── (Filters out temporarily unavailable donors)
           │
           ▼
[ Blood Group ∈ Compatible List ] ── (Biological compatibility)
           │
           ▼
[ District == Target District ] ── (Geographic boundary)
           │
           ▼
[ Cooldown Satisfied (Days Remaining == 0) ] ── (Health rest interval)
           │
           ▼
[ Ordered & Ranked Candidate List ]
```

---

## 5. Deterministic Ranking & Tie-Breaking

To avoid subjective, arbitrary scoring algorithms, the matching engine uses a transparent, deterministic sorting hierarchy:

1. **Priority 1: Geographic Proximity**
   - Donors residing in the requested `panchayat` rank before general district donors.
2. **Priority 2: Identical Blood Match**
   - Donors with the identical blood group (e.g. `B+` for `B+`) rank before compatible universal alternatives (e.g. `O-` for `B+`) to preserve scarce O- reserves.
3. **Priority 3: Rest Period / Donor Readiness**
   - First-time donors and donors with the longest elapsed time since their previous donation are prioritized first to distribute the donation load evenly.
4. **Priority 4: Stable Tie-Breaker**
   - Stable sorting by `donor.id ASC`.

---

## 6. Required Units Handling

- In the current phase, `required_units` specifies the clinical demand for the blood request.
- The matching service returns all eligible candidates up to the requested `limit` (default: 20, max: 100).
- Requesters can evaluate the ordered candidate pool to fulfill the target quantity.

---

## 7. Security, Privacy & Scoping

- **Authentication**: The matching endpoint `POST /api/v1/matching/donors` requires a valid JWT access token.
- **Scoping**:
  - `SUPER_ADMIN`: Can execute regional and system-wide donor searches.
  - `HOSPITAL_ADMIN` / `STAFF`: Scoped appropriately to operational workflows.
- **WhatsApp Bot Decoupling**:
  - The matching engine operates independently of external messaging protocols. Future WhatsApp bot workflows will invoke `MatchingService` internally and sanitize/mask donor contact details before presenting response summaries to public end users.
