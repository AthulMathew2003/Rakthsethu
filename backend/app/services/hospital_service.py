import math
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from geoalchemy2.elements import WKTElement
from app.core.exceptions import DuplicateResourceException, ResourceNotFoundException
from app.models.hospital import Hospital
from app.repositories.hospital_repository import HospitalRepository
from app.schemas.common import PaginatedData
from app.schemas.hospital import HospitalCreate, HospitalListQuery, HospitalResponse, HospitalUpdate


class HospitalService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.hospital_repo = HospitalRepository(session)

    async def create_hospital(self, data: HospitalCreate) -> HospitalResponse:
        hospital_code = data.hospital_code
        if hospital_code:
            existing = await self.hospital_repo.get_by_code(hospital_code)
            if existing:
                raise DuplicateResourceException("Hospital", "hospital_code", hospital_code)
        else:
            hospital_code = await self.hospital_repo.generate_next_hospital_code()

        location_geom = None
        if data.latitude is not None and data.longitude is not None:
            location_geom = WKTElement(f"POINT({data.longitude} {data.latitude})", srid=4326)

        new_hospital = Hospital(
            hospital_code=hospital_code,
            name=data.name.strip(),
            hospital_type=data.hospital_type.strip(),
            district=data.district.strip(),
            panchayat=data.panchayat.strip() if data.panchayat else None,
            address=data.address.strip(),
            phone=data.phone.strip() if data.phone else None,
            email=str(data.email).lower().strip() if data.email else None,
            emergency_number=data.emergency_number.strip() if data.emergency_number else None,
            latitude=data.latitude,
            longitude=data.longitude,
            location=location_geom,
            is_active=True,
        )

        await self.hospital_repo.add(new_hospital)
        await self.session.commit()
        await self.session.refresh(new_hospital)

        return HospitalResponse.model_validate(new_hospital)

    async def get_hospital_by_id(self, hospital_id: int) -> HospitalResponse:
        hospital = await self.hospital_repo.get_by_id(hospital_id)
        if not hospital:
            raise ResourceNotFoundException("Hospital", hospital_id)
        return HospitalResponse.model_validate(hospital)

    async def update_hospital(self, hospital_id: int, data: HospitalUpdate) -> HospitalResponse:
        hospital = await self.hospital_repo.get_by_id(hospital_id)
        if not hospital:
            raise ResourceNotFoundException("Hospital", hospital_id)

        update_dict = data.model_dump(exclude_unset=True)
        for key, value in update_dict.items():
            if value is not None and isinstance(value, str):
                setattr(hospital, key, value.strip())
            else:
                setattr(hospital, key, value)

        # Synchronize spatial point if coordinates changed
        if hospital.latitude is not None and hospital.longitude is not None:
            hospital.location = WKTElement(f"POINT({hospital.longitude} {hospital.latitude})", srid=4326)
        else:
            hospital.location = None

        await self.session.commit()
        await self.session.refresh(hospital)

        return HospitalResponse.model_validate(hospital)

    async def list_hospitals(self, query: HospitalListQuery) -> PaginatedData[HospitalResponse]:
        items, total = await self.hospital_repo.list_hospitals(query)
        total_pages = math.ceil(total / query.page_size) if total > 0 else 1

        return PaginatedData(
            items=[HospitalResponse.model_validate(h) for h in items],
            page=query.page,
            page_size=query.page_size,
            total=total,
            total_pages=total_pages,
        )
