from datetime import datetime, timezone
import math
import re
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from geoalchemy2.elements import WKTElement
from app.core.exceptions import (
    DuplicateResourceException,
    ResourceNotFoundException,
    ValidationException,
)
from app.models.donor import Donor
from app.repositories.donor_repository import DonorRepository
from app.repositories.hospital_repository import HospitalRepository
from app.schemas.common import PaginatedData
from app.schemas.donor import DonorCreate, DonorListQuery, DonorResponse, DonorUpdate


from app.core.phone_utils import normalize_phone_number
from app.core.location_service import validate_district_and_panchayat


class DonorService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.donor_repo = DonorRepository(session)
        self.hospital_repo = HospitalRepository(session)

    async def create_donor(self, data: DonorCreate) -> DonorResponse:
        # Validate district and local body
        canonical_dist, canonical_panchayat = validate_district_and_panchayat(
            data.district, data.panchayat
        )

        normalized_phone = normalize_phone_number(data.phone)

        # Check unique phone constraint
        existing = await self.donor_repo.get_by_phone(normalized_phone)
        if existing:
            raise DuplicateResourceException("Donor", "phone number", normalized_phone)

        if data.hospital_id:
            hospital = await self.hospital_repo.get_by_id(data.hospital_id)
            if not hospital:
                raise ResourceNotFoundException("Hospital", data.hospital_id)

        donor_code = data.donor_code
        if donor_code:
            existing_code = await self.donor_repo.get_by_code(donor_code)
            if existing_code:
                raise DuplicateResourceException("Donor", "donor_code", donor_code)
        else:
            donor_code = await self.donor_repo.generate_next_donor_code()

        location_geom = None
        consent_val = False
        consent_time = None
        if data.latitude is not None and data.longitude is not None:
            location_geom = WKTElement(f"POINT({data.longitude} {data.latitude})", srid=4326)
            consent_val = True
            consent_time = datetime.now(timezone.utc)

        new_donor = Donor(
            donor_code=donor_code,
            hospital_id=data.hospital_id,
            full_name=data.full_name.strip(),
            blood_group=data.blood_group,
            gender=data.gender.strip() if data.gender else None,
            phone=normalized_phone,
            email=str(data.email).lower().strip() if data.email else None,
            district=canonical_dist,
            panchayat=canonical_panchayat,
            address=data.address.strip() if data.address else None,
            location=location_geom,
            location_consent=consent_val,
            location_consent_recorded_at=consent_time,
            is_active=True,
            is_available=data.is_available,
        )

        await self.donor_repo.add(new_donor)
        await self.session.commit()
        await self.session.refresh(new_donor)

        return DonorResponse.model_validate(new_donor)

    async def get_donor_by_id(self, donor_id: int) -> DonorResponse:
        donor = await self.donor_repo.get_by_id(donor_id)
        if not donor:
            raise ResourceNotFoundException("Donor", donor_id)

        latest_donation = await self.donor_repo.get_latest_donation_date(donor_id)
        donor_resp = DonorResponse.model_validate(donor)
        donor_resp.last_donation_date = latest_donation
        return donor_resp

    async def update_donor(self, donor_id: int, data: DonorUpdate) -> DonorResponse:
        donor = await self.donor_repo.get_by_id(donor_id)
        if not donor:
            raise ResourceNotFoundException("Donor", donor_id)

        update_dict = data.model_dump(exclude_unset=True)

        if "phone" in update_dict and update_dict["phone"]:
            normalized = normalize_phone_number(update_dict["phone"])
            if normalized != donor.phone:
                existing = await self.donor_repo.get_by_phone(normalized)
                if existing and existing.id != donor.id:
                    raise DuplicateResourceException("Donor", "phone number", normalized)
                donor.phone = normalized
            del update_dict["phone"]

        if "hospital_id" in update_dict and update_dict["hospital_id"] is not None:
            hospital = await self.hospital_repo.get_by_id(update_dict["hospital_id"])
            if not hospital:
                raise ResourceNotFoundException("Hospital", update_dict["hospital_id"])

        # Validate district and local body if updated
        if "district" in update_dict or "panchayat" in update_dict:
            target_dist = update_dict.get("district", donor.district)
            target_panchayat = update_dict.get("panchayat", donor.panchayat)
            canonical_dist, canonical_panchayat = validate_district_and_panchayat(
                target_dist, target_panchayat
            )
            if "district" in update_dict:
                update_dict["district"] = canonical_dist
            if "panchayat" in update_dict:
                update_dict["panchayat"] = canonical_panchayat

        # Handle spatial location update/clearing
        if update_dict.get("remove_location"):
            donor.location = None
            donor.location_consent = False
            donor.location_consent_recorded_at = None
            del update_dict["remove_location"]
            if "latitude" in update_dict:
                del update_dict["latitude"]
            if "longitude" in update_dict:
                del update_dict["longitude"]
            if "location_consent" in update_dict:
                del update_dict["location_consent"]
        elif (
            "latitude" in update_dict
            and "longitude" in update_dict
            and update_dict["latitude"] is not None
            and update_dict["longitude"] is not None
        ):
            donor.location = WKTElement(
                f"POINT({update_dict['longitude']} {update_dict['latitude']})",
                srid=4326,
            )
            donor.location_consent = True
            donor.location_consent_recorded_at = datetime.now(timezone.utc)
            del update_dict["latitude"]
            del update_dict["longitude"]
            if "remove_location" in update_dict:
                del update_dict["remove_location"]
            if "location_consent" in update_dict:
                del update_dict["location_consent"]
        else:
            if "remove_location" in update_dict:
                del update_dict["remove_location"]
            if "latitude" in update_dict:
                del update_dict["latitude"]
            if "longitude" in update_dict:
                del update_dict["longitude"]
            if "location_consent" in update_dict:
                del update_dict["location_consent"]

        for key, value in update_dict.items():
            if value is not None and isinstance(value, str):
                setattr(donor, key, value.strip())
            else:
                setattr(donor, key, value)

        await self.session.commit()
        await self.session.refresh(donor)

        latest_donation = await self.donor_repo.get_latest_donation_date(donor.id)
        donor_resp = DonorResponse.model_validate(donor)
        donor_resp.last_donation_date = latest_donation
        return donor_resp

    async def update_donor_location(
        self, donor_id: int, latitude: float, longitude: float
    ) -> DonorResponse:
        donor = await self.donor_repo.get_by_id(donor_id)
        if not donor:
            raise ResourceNotFoundException("Donor", donor_id)

        donor.location = WKTElement(f"POINT({longitude} {latitude})", srid=4326)
        donor.location_consent = True
        donor.location_consent_recorded_at = datetime.now(timezone.utc)
        await self.session.commit()
        await self.session.refresh(donor)

        latest_donation = await self.donor_repo.get_latest_donation_date(donor.id)
        donor_resp = DonorResponse.model_validate(donor)
        donor_resp.last_donation_date = latest_donation
        return donor_resp

    async def remove_donor_location(self, donor_id: int) -> DonorResponse:
        donor = await self.donor_repo.get_by_id(donor_id)
        if not donor:
            raise ResourceNotFoundException("Donor", donor_id)

        donor.location = None
        donor.location_consent = False
        donor.location_consent_recorded_at = None
        await self.session.commit()
        await self.session.refresh(donor)

        latest_donation = await self.donor_repo.get_latest_donation_date(donor.id)
        donor_resp = DonorResponse.model_validate(donor)
        donor_resp.last_donation_date = latest_donation
        return donor_resp

    async def list_donors(self, query: DonorListQuery) -> PaginatedData[DonorResponse]:
        items, latest_dates, total = await self.donor_repo.list_donors(query)
        total_pages = math.ceil(total / query.page_size) if total > 0 else 1

        response_items = []
        for donor in items:
            resp = DonorResponse.model_validate(donor)
            resp.last_donation_date = latest_dates.get(donor.id)
            response_items.append(resp)

        return PaginatedData(
            items=response_items,
            page=query.page,
            page_size=query.page_size,
            total=total,
            total_pages=total_pages,
        )
