from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import or_
from app.database import get_db
from app import models, schemas
from typing import Optional, List

router = APIRouter(
    prefix="/api/requests",
    tags=["Blood Requests"]
)

@router.get("", response_model=List[schemas.BloodRequestResponse])
def get_requests(
    status_filter: Optional[str] = Query(None, alias="status"),
    urgency: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    query = db.query(models.BloodRequest)
    if status_filter and status_filter != "All":
        query = query.filter(models.BloodRequest.status.ilike(status_filter))
    if urgency and urgency != "All":
        query = query.filter(models.BloodRequest.urgency.ilike(urgency))

    return query.order_by(models.BloodRequest.id.desc()).all()

@router.post("", response_model=schemas.BloodRequestResponse, status_code=status.HTTP_201_CREATED)
def create_blood_request(req_in: schemas.BloodRequestCreate, db: Session = Depends(get_db)):
    last_req = db.query(models.BloodRequest).order_by(models.BloodRequest.id.desc()).first()
    next_num = (last_req.id + 1) if last_req else 1
    req_code = f"REQ{str(next_num).zfill(3)}"

    new_req = models.BloodRequest(
        request_code=req_code,
        patient_name=req_in.patient_name,
        blood_group=req_in.blood_group,
        units_requested=req_in.units_requested,
        hospital_name=req_in.hospital_name,
        location=req_in.location,
        contact_phone=req_in.contact_phone,
        urgency=req_in.urgency or "Normal",
        status=req_in.status or "Pending",
        time_ago="Just now"
    )
    db.add(new_req)
    db.commit()
    db.refresh(new_req)
    return new_req

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
