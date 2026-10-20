from datetime import date
from typing import List, Optional
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import settings
from app.core.exceptions import ValidationException
from app.models.donor import Donor
from app.models.donation import Donation
from app.models.hospital import Hospital
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
        Finds and ranks eligible blood donors.
        Origin selection order:
        1. Explicit GPS coordinates from request (latitude, longitude)
        2. Associated hospital's spatial location (if hospital_id is provided and has coordinates)
        3. Legacy district/panchayat matching behavior (if no spatial origin is available)
        """
        ref_date = request.required_date or date.today()
        compatible_groups = get_compatible_donor_groups(request.blood_group)

        effective_hospital_id = hospital_id or request.hospital_id
        target_hospital: Optional[Hospital] = None
        origin_type = "DISTRICT_DEFAULT"
        origin_lat: Optional[float] = None
        origin_lon: Optional[float] = None

        # 1. Origin Resolution
        if request.latitude is not None and request.longitude is not None:
            origin_type = "EXPLICIT_GPS"
            origin_lat = request.latitude
            origin_lon = request.longitude
        elif effective_hospital_id is not None:
            hosp_stmt = select(Hospital).where(Hospital.id == effective_hospital_id)
            hosp_res = await self.session.execute(hosp_stmt)
            target_hospital = hosp_res.scalar_one_or_none()
            if target_hospital and target_hospital.latitude is not None and target_hospital.longitude is not None:
                origin_type = "HOSPITAL_LOCATION"
                origin_lat = target_hospital.latitude
                origin_lon = target_hospital.longitude

        effective_district = request.district or (target_hospital.district if target_hospital else None)
        district_clean = effective_district.strip().lower() if effective_district else None
        panchayat_clean = request.panchayat.strip().lower() if request.panchayat else None

        # Single subquery to fetch the latest completed donation date per donor
        latest_donation_subq = (
            select(
                Donation.donor_id,
                func.max(Donation.donation_date).label("last_completed_date"),
            )
            .where(Donation.status == DonationStatus.COMPLETED)
            .group_by(Donation.donor_id)
            .subquery()
        )

        # -------------------------------------------------------------
        # Branch A: Spatial Proximity Matching (GPS origin available)
        # -------------------------------------------------------------
        if origin_type in ("EXPLICIT_GPS", "HOSPITAL_LOCATION") and origin_lat is not None and origin_lon is not None:
            radius_km = request.radius_km or settings.DEFAULT_PROXIMITY_RADIUS_KM
            if radius_km <= 0 or radius_km > settings.MAX_PROXIMITY_RADIUS_KM:
                raise ValidationException(
                    f"Search radius ({radius_km} km) must be greater than 0 and cannot exceed {settings.MAX_PROXIMITY_RADIUS_KM} km."
                )
            radius_meters = radius_km * 1000.0
            origin_point = func.ST_SetSRID(func.ST_MakePoint(origin_lon, origin_lat), 4326)

            # Query 1: Coordinate-enabled donors with explicit consent within radius (uses GiST spatial index)
            stmt_proximity = (
                select(
                    Donor,
                    latest_donation_subq.c.last_completed_date,
                    func.ST_Distance(Donor.location, origin_point).label("distance_meters"),
                )
                .outerjoin(latest_donation_subq, Donor.id == latest_donation_subq.c.donor_id)
                .where(
                    Donor.is_active.is_(True),
                    Donor.is_available.is_(True),
                    Donor.blood_group.in_(compatible_groups),
                    Donor.location.is_not(None),
                    Donor.location_consent.is_(True),
                    func.ST_DWithin(Donor.location, origin_point, radius_meters),
                )
            )
            if hospital_id is not None:
                stmt_proximity = stmt_proximity.where(Donor.hospital_id == hospital_id)

            prox_res = await self.session.execute(stmt_proximity)
            proximity_rows = prox_res.all()

            proximity_items: List[MatchedDonorItem] = []
            for donor, last_donation_date, dist_meters in proximity_rows:
                cooldown = calculate_cooldown_eligibility(
                    last_donation_date=last_donation_date,
                    donation_type=request.donation_type,
                    reference_date=ref_date,
                )
                if not cooldown.is_eligible:
                    continue

                dist_km = round(dist_meters / 1000.0, 1)
                reasons = [f"Proximity match ({dist_km} km away)"]
                if donor.blood_group == request.blood_group:
                    reasons.append(f"Identical blood group ({donor.blood_group.value})")
                else:
                    reasons.append(f"Compatible blood group ({donor.blood_group.value} -> {request.blood_group.value})")

                if last_donation_date is None:
                    reasons.append("First-time donor (eligible)")
                else:
                    reasons.append(f"{cooldown.days_since_last_donation} days since last donation (eligible)")

                proximity_items.append(
                    MatchedDonorItem(
                        donor_id=donor.id,
                        donor_code=donor.donor_code,
                        full_name=donor.full_name,
                        blood_group=donor.blood_group,
                        phone=donor.phone,
                        district=donor.district,
                        panchayat=donor.panchayat,
                        is_available=donor.is_available,
                        distance_km=dist_km,
                        match_category="PROXIMITY",
                        last_donation_date=cooldown.last_donation_date,
                        eligible_from=cooldown.eligible_from,
                        days_since_last_donation=cooldown.days_since_last_donation,
                        match_reason="; ".join(reasons),
                    )
                )

            # Sort proximity candidates:
            # 1. Distance ascending (closest first)
            # 2. Exact blood group over compatible alternative
            # 3. Longest rest period since last donation
            # 4. Stable tie-breaker: donor_id
            proximity_items.sort(
                key=lambda item: (
                    item.distance_km if item.distance_km is not None else 999999.0,
                    0 if item.blood_group == request.blood_group else 1,
                    -(item.days_since_last_donation if item.days_since_last_donation is not None else 999999),
                    item.donor_id,
                )
            )

            # Query 2: Coordinate-less fallback donors in the target district (if fallback enabled)
            fallback_items: List[MatchedDonorItem] = []
            if request.include_fallback and district_clean:
                stmt_fallback = (
                    select(Donor, latest_donation_subq.c.last_completed_date)
                    .outerjoin(latest_donation_subq, Donor.id == latest_donation_subq.c.donor_id)
                    .where(
                        Donor.is_active.is_(True),
                        Donor.is_available.is_(True),
                        Donor.blood_group.in_(compatible_groups),
                        Donor.location.is_(None),
                        func.lower(Donor.district) == district_clean,
                    )
                )
                if hospital_id is not None:
                    stmt_fallback = stmt_fallback.where(Donor.hospital_id == hospital_id)

                fb_res = await self.session.execute(stmt_fallback)
                fallback_rows = fb_res.all()

                for donor, last_donation_date in fallback_rows:
                    cooldown = calculate_cooldown_eligibility(
                        last_donation_date=last_donation_date,
                        donation_type=request.donation_type,
                        reference_date=ref_date,
                    )
                    if not cooldown.is_eligible:
                        continue

                    reasons = ["District fallback (No GPS coordinates registered)"]
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

                    fallback_items.append(
                        MatchedDonorItem(
                            donor_id=donor.id,
                            donor_code=donor.donor_code,
                            full_name=donor.full_name,
                            blood_group=donor.blood_group,
                            phone=donor.phone,
                            district=donor.district,
                            panchayat=donor.panchayat,
                            is_available=donor.is_available,
                            distance_km=None,
                            match_category="FALLBACK_DISTRICT",
                            last_donation_date=cooldown.last_donation_date,
                            eligible_from=cooldown.eligible_from,
                            days_since_last_donation=cooldown.days_since_last_donation,
                            match_reason="; ".join(reasons),
                        )
                    )

                # Sort fallback candidates within fallback group:
                fallback_items.sort(
                    key=lambda item: (
                        0 if (panchayat_clean and item.panchayat and item.panchayat.strip().lower() == panchayat_clean) else 1,
                        0 if item.blood_group == request.blood_group else 1,
                        -(item.days_since_last_donation if item.days_since_last_donation is not None else 999999),
                        item.donor_id,
                    )
                )

            # Stable ranking policy:
            # Tier 1 (Proximity candidates with verified distance) ALWAYS precedes Tier 2 (District fallback candidates)
            eligible_items = proximity_items + fallback_items

        # -------------------------------------------------------------
        # Branch B: Legacy District/Panchayat Matching (No GPS origin)
        # -------------------------------------------------------------
        else:
            radius_km = None
            stmt_legacy = (
                select(Donor, latest_donation_subq.c.last_completed_date)
                .outerjoin(latest_donation_subq, Donor.id == latest_donation_subq.c.donor_id)
                .where(
                    Donor.is_active.is_(True),
                    Donor.is_available.is_(True),
                    Donor.blood_group.in_(compatible_groups),
                    func.lower(Donor.district) == (district_clean or ""),
                )
            )
            if hospital_id is not None:
                stmt_legacy = stmt_legacy.where(Donor.hospital_id == hospital_id)

            legacy_res = await self.session.execute(stmt_legacy)
            candidates = legacy_res.all()

            eligible_items = []
            for donor, last_donation_date in candidates:
                cooldown = calculate_cooldown_eligibility(
                    last_donation_date=last_donation_date,
                    donation_type=request.donation_type,
                    reference_date=ref_date,
                )
                if not cooldown.is_eligible:
                    continue

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
                        distance_km=None,
                        match_category="DISTRICT_DEFAULT",
                        last_donation_date=cooldown.last_donation_date,
                        eligible_from=cooldown.eligible_from,
                        days_since_last_donation=cooldown.days_since_last_donation,
                        match_reason="; ".join(reasons),
                    )
                )

            # Legacy ranking key
            eligible_items.sort(
                key=lambda item: (
                    0 if (panchayat_clean and item.panchayat and item.panchayat.strip().lower() == panchayat_clean) else 1,
                    0 if item.blood_group == request.blood_group else 1,
                    -(item.days_since_last_donation if item.days_since_last_donation is not None else 999999),
                    item.donor_id,
                )
            )

        # Apply result limit
        effective_limit = min(request.limit or settings.DEFAULT_MATCH_LIMIT, settings.MAX_MATCH_LIMIT)
        top_items = eligible_items[:effective_limit]

        return MatchDonorsResponse(
            recipient_blood_group=request.blood_group,
            compatible_blood_groups=compatible_groups,
            district=effective_district,
            panchayat=request.panchayat,
            origin_type=origin_type,
            origin_latitude=origin_lat,
            origin_longitude=origin_lon,
            radius_km=radius_km,
            required_units=request.required_units,
            required_date=ref_date,
            total_eligible_found=len(eligible_items),
            items=top_items,
        )
