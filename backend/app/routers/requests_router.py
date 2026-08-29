from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import or_
from app.database import get_db
from app import models, schemas
from typing import Optional, List
from datetime import datetime

router = APIRouter(
    prefix="/api/requests",
    tags=["Blood Requests"]
)

@router.get("", response_model=List[schemas.BloodRequestResponse])
def get_requests(
    search: Optional[str] = None,
    blood_group: Optional[str] = None,
    status: Optional[str] = None,
    urgency: Optional[str] = None,
    district: Optional[str] = None,
    db: Session = Depends(get_db)
):
    query = db.query(models.BloodRequest)

    if search:
        s = f"%{search}%"
        query = query.filter(
            or_(
                models.BloodRequest.patient_name.ilike(s),
                models.BloodRequest.hospital_name.ilike(s),
                models.BloodRequest.district.ilike(s),
                models.BloodRequest.contact_phone.ilike(s),
                models.BloodRequest.request_code.ilike(s),
                models.BloodRequest.blood_group.ilike(s)
            )
        )
    if blood_group and blood_group != "All":
        query = query.filter(models.BloodRequest.blood_group == blood_group)
    if status and status != "All":
        query = query.filter(models.BloodRequest.status.ilike(status))
    if urgency and urgency != "All":
        query = query.filter(models.BloodRequest.urgency.ilike(urgency))
    if district and district != "All":
        query = query.filter(models.BloodRequest.district.ilike(district))

    return query.order_by(models.BloodRequest.id.desc()).all()

@router.post("", response_model=schemas.BloodRequestResponse, status_code=status.HTTP_201_CREATED)
def create_blood_request(req_in: schemas.BloodRequestCreate, db: Session = Depends(get_db)):
    last_req = db.query(models.BloodRequest).order_by(models.BloodRequest.id.desc()).first()
    next_num = (last_req.id + 1) if last_req else 1
    req_code = f"BR{str(next_num).zfill(3)}"

    new_req = models.BloodRequest(
        request_code=req_code,
        patient_name=req_in.patient_name,
        blood_group=req_in.blood_group,
        units_requested=req_in.units_requested,
        hospital_name=req_in.hospital_name,
        district=req_in.district or "Kottayam",
        location=req_in.location or req_in.district or "Kottayam",
        contact_phone=req_in.contact_phone,
        emergency_contact=req_in.emergency_contact,
        required_date=req_in.required_date,
        urgency=req_in.urgency or "Normal",
        status=req_in.status or "Pending",
        notes=req_in.notes,
        time_ago="Just now"
    )
    db.add(new_req)

    # Activity log
    today_str = datetime.now().strftime("%Y-%m-%d")
    db.add(models.ActivityLog(
        category="Blood Requests",
        activity=f"New blood request {req_code} for {req_in.patient_name} ({req_in.blood_group}, {req_in.units_requested}U) at {req_in.hospital_name}",
        count=req_in.units_requested,
        status=req_in.status or "Pending",
        log_date=today_str
    ))

    db.commit()
    db.refresh(new_req)
    return new_req

@router.put("/{id}", response_model=schemas.BloodRequestResponse)
def update_blood_request(id: int, req_update: schemas.BloodRequestUpdate, db: Session = Depends(get_db)):
    req = db.query(models.BloodRequest).filter(models.BloodRequest.id == id).first()
    if not req:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Blood request not found")

    update_data = req_update.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(req, key, value)

    db.commit()
    db.refresh(req)
    return req

@router.put("/{id}/status", response_model=schemas.BloodRequestResponse)
def update_request_status(
    id: int,
    status_update: schemas.BloodRequestStatusUpdate,
    db: Session = Depends(get_db)
):
    req = db.query(models.BloodRequest).filter(models.BloodRequest.id == id).first()
    if not req:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Blood request not found")

    req.status = status_update.status

    # Activity log
    today_str = datetime.now().strftime("%Y-%m-%d")
    db.add(models.ActivityLog(
        category="Blood Requests",
        activity=f"Request {req.request_code} status updated to {status_update.status}",
        count=req.units_requested,
        status=status_update.status,
        log_date=today_str
    ))

    db.commit()
    db.refresh(req)
    return req

@router.delete("/{id}", status_code=status.HTTP_200_OK)
def delete_blood_request(id: int, db: Session = Depends(get_db)):
    req = db.query(models.BloodRequest).filter(models.BloodRequest.id == id).first()
    if not req:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Blood request not found")

    db.delete(req)
    db.commit()
    return {"message": "Blood request deleted successfully", "id": id}
