from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import or_
from app.database import get_db
from app import models, schemas
from typing import Optional, List
import json
from datetime import datetime

router = APIRouter(
    prefix="/api/hospitals",
    tags=["Hospitals"]
)

@router.get("", response_model=List[schemas.HospitalResponse])
def get_hospitals(
    search: Optional[str] = None,
    district: Optional[str] = None,
    type: Optional[str] = None,
    status: Optional[str] = None,
    db: Session = Depends(get_db)
):
    query = db.query(models.Hospital)

    if search:
        s = f"%{search}%"
        query = query.filter(
            or_(
                models.Hospital.name.ilike(s),
                models.Hospital.district.ilike(s),
                models.Hospital.panchayat.ilike(s),
                models.Hospital.address.ilike(s),
                models.Hospital.hospital_code.ilike(s)
            )
        )
    if district and district != "All":
        query = query.filter(models.Hospital.district.ilike(district))
    if type and type != "All":
        query = query.filter(models.Hospital.type.ilike(type))
    if status and status != "All":
        query = query.filter(models.Hospital.status.ilike(status))

    return query.order_by(models.Hospital.id.asc()).all()

@router.post("", response_model=schemas.HospitalResponse, status_code=status.HTTP_201_CREATED)
def create_hospital(hosp_in: schemas.HospitalCreate, db: Session = Depends(get_db)):
    last_hosp = db.query(models.Hospital).order_by(models.Hospital.id.desc()).first()
    next_num = (last_hosp.id + 1) if last_hosp else 1
    code = f"HOSP{str(next_num).zfill(3)}"

    new_hosp = models.Hospital(
        hospital_code=code,
        name=hosp_in.name,
        type=hosp_in.type or "Government",
        district=hosp_in.district or "Kottayam",
        panchayat=hosp_in.panchayat,
        address=hosp_in.address,
        phone=hosp_in.phone,
        email=hosp_in.email,
        emergency_number=hosp_in.emergency_number or "108",
        latitude=hosp_in.latitude,
        longitude=hosp_in.longitude,
        services=hosp_in.services,
        status=hosp_in.status or "Active"
    )
    db.add(new_hosp)

    # Add activity log
    today_str = datetime.now().strftime("%Y-%m-%d")
    db.add(models.ActivityLog(
        category="Hospitals",
        activity=f"New hospital registered: {new_hosp.name} ({new_hosp.district})",
        count=1,
        status="Active",
        log_date=today_str
    ))

    db.commit()
    db.refresh(new_hosp)
    return new_hosp

@router.put("/{id}", response_model=schemas.HospitalResponse)
def update_hospital(id: int, hosp_update: schemas.HospitalUpdate, db: Session = Depends(get_db)):
    hosp = db.query(models.Hospital).filter(models.Hospital.id == id).first()
    if not hosp:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Hospital not found")

    update_data = hosp_update.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(hosp, key, value)

    db.commit()
    db.refresh(hosp)
    return hosp

@router.delete("/{id}", status_code=status.HTTP_200_OK)
def delete_hospital(id: int, db: Session = Depends(get_db)):
    hosp = db.query(models.Hospital).filter(models.Hospital.id == id).first()
    if not hosp:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Hospital not found")

    db.delete(hosp)
    db.commit()
    return {"message": "Hospital deleted successfully", "id": id}
