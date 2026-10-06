from datetime import date
from typing import List, Optional
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import settings
from app.models.donor import Donor
from app.models.donation import Donation
from app.models.enums import BloodGroup, DonationStatus
from app.schemas.matching import (
    MatchDonorsRequest,
    MatchDonorsResponse,
    MatchedDonorItem,
)
from app.services.blood_compatibility import (
    get_compatible_donor_groups,
    is_blood_compatible,
)
from app.services.cooldown_service import calculate_cooldown_eligibility


class MatchingService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def find_matching_donors(
        self,
        request: MatchDonorsRequest,
        hospital_id: Optional[int] = None,
    ) -> MatchDonorsResponse:
        """
        Finds and ranks eligible blood donors based on biological blood compatibility,
        geographic location (district/panchayat), availability status, and donation cooldowns.
        """
        ref_date = request.required_date or date.today()
        compatible_groups = get_compatible_donor_groups(request.blood_group)
        district_clean = request.district.strip().lower()
        panchayat_clean = request.panchayat.strip().lower() if request.panchayat else None

        # 1. Optimized SQL query: Get active, available donors with compatible blood in the district
        # along with their latest completed donation date in a SINGLE query using an aggregation subquery.
        latest_donation_subq = (
            select(
                Donation.donor_id,
                func.max(Donation.donation_date).label("last_completed_date"),
            )
            .where(Donation.status == DonationStatus.COMPLETED)
            .group_by(Donation.donor_id)
            .subquery()
        )

        stmt = (
            select(Donor, latest_donation_subq.c.last_completed_date)
            .outerjoin(latest_donation_subq, Donor.id == latest_donation_subq.c.donor_id)
            .where(
                Donor.is_active.is_(True),
                Donor.is_available.is_(True),
                Donor.blood_group.in_(compatible_groups),
                func.lower(Donor.district) == district_clean,
            )
        )

        # Optional hospital scope filter if requested
        if hospital_id is not None:
            stmt = stmt.where(Donor.hospital_id == hospital_id)

        result = await self.session.execute(stmt)
        candidates = result.all()

        # 2. Evaluate cooldown eligibility and construct match explanation
        eligible_items: List[MatchedDonorItem] = []

        for donor, last_donation_date in candidates:
            cooldown = calculate_cooldown_eligibility(
                last_donation_date=last_donation_date,
                donation_type=request.donation_type,
                reference_date=ref_date,
            )

            # Skip ineligible donors
            if not cooldown.is_eligible:
                continue

            # Build human-readable match explanation
            reasons = []
            if donor.blood_group == request.blood_group:
                reasons.append(f"Identical blood group ({donor.blood_group.value})")
            else:
                reasons.append(f"Compatible blood group ({donor.blood_group.value} -> {request.blood_group.value})")

            reasons.append(f"District match ({donor.district})")

            if panchayat_clean and donor.panchayat and donor.panchayat.strip().lower() == panchayat_clean:
                reasons.append(f"Panchayat proximity ({donor.panchayat})")

            if last_donation_date is None:
                reasons.append("First-time donor (eligible)")
            else:
                reasons.append(f"{cooldown.days_since_last_donation} days since last donation (eligible)")

            match_reason = "; ".join(reasons)

            eligible_items.append(
                MatchedDonorItem(
                    donor_id=donor.id,
                    donor_code=donor.donor_code,
                    full_name=donor.full_name,
                    blood_group=donor.blood_group,
                    phone=donor.phone,
                    district=donor.district,
                    panchayat=donor.panchayat,
                    is_available=donor.is_available,
                    last_donation_date=cooldown.last_donation_date,
                    eligible_from=cooldown.eligible_from,
                    days_since_last_donation=cooldown.days_since_last_donation,
                    match_reason=match_reason,
                )
            )

        # 3. Deterministic Ranking:
        # Priority 1: Exact panchayat match if requested (0 = match, 1 = other)
        # Priority 2: Identical blood group over universal/compatible alternative (0 = identical, 1 = compatible)
        # Priority 3: Longest rest period since last donation (never-donated first, then largest days_since_last_donation)
        # Priority 4: Stable tie-breaker: donor_id ascending
        def ranking_key(item: MatchedDonorItem):
            # Proximity rank
            panchayat_rank = 0 if (
                panchayat_clean
                and item.panchayat
                and item.panchayat.strip().lower() == panchayat_clean
            ) else 1

            # Blood group exactness rank
            bg_exact_rank = 0 if item.blood_group == request.blood_group else 1

            # Rest period rank (negative so larger days_since sorts earlier)
            # Never-donated receives highest rest priority (-999999)
            rest_rank = -(item.days_since_last_donation if item.days_since_last_donation is not None else 999999)

            return (panchayat_rank, bg_exact_rank, rest_rank, item.donor_id)

        eligible_items.sort(key=ranking_key)

        # 4. Limit results
        effective_limit = min(request.limit or settings.DEFAULT_MATCH_LIMIT, settings.MAX_MATCH_LIMIT)
        top_items = eligible_items[:effective_limit]

        return MatchDonorsResponse(
            recipient_blood_group=request.blood_group,
            compatible_blood_groups=compatible_groups,
            district=request.district,
            panchayat=request.panchayat,
            required_units=request.required_units,
            required_date=ref_date,
            total_eligible_found=len(eligible_items),
            items=top_items,
        )
