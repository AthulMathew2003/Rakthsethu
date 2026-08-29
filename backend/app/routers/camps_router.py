from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import or_
from app.database import get_db
from app import models, schemas
from typing import List, Optional
from datetime import datetime

router = APIRouter(
    prefix="/api/camps",
    tags=["Camps & Events"]
)

@router.get("", response_model=List[schemas.CampEventResponse])
def get_camps(
    search: Optional[str] = None,
    type: Optional[str] = None,
    status: Optional[str] = None,
    db: Session = Depends(get_db)
):
    query = db.query(models.CampEvent)

    if search:
        s = f"%{search}%"
        query = query.filter(
            or_(
                models.CampEvent.title.ilike(s),
                models.CampEvent.location.ilike(s),
                models.CampEvent.venue.ilike(s),
                models.CampEvent.organizer.ilike(s),
                models.CampEvent.camp_code.ilike(s)
            )
        )
    if type and type != "All":
        query = query.filter(models.CampEvent.type.ilike(type))
    if status and status != "All":
        query = query.filter(models.CampEvent.status.ilike(status))

    return query.order_by(models.CampEvent.id.asc()).all()

@router.post("", response_model=schemas.CampEventResponse, status_code=status.HTTP_201_CREATED)
def create_camp(camp_in: schemas.CampEventCreate, db: Session = Depends(get_db)):
    last_camp = db.query(models.CampEvent).order_by(models.CampEvent.id.desc()).first()
    next_num = (last_camp.id + 1) if last_camp else 1
    code = f"EV{str(next_num).zfill(3)}"

    new_camp = models.CampEvent(
        camp_code=code,
        title=camp_in.title,
        type=camp_in.type or "Blood Donation",
        location=camp_in.location or camp_in.venue or "Campus Ground",
        venue=camp_in.venue or camp_in.location,
        event_date=camp_in.event_date,
        start_time=camp_in.start_time or "09:00 AM",
        end_time=camp_in.end_time or "03:00 PM",
        time_slot=camp_in.time_slot or f"{camp_in.start_time or '09:00 AM'} – {camp_in.end_time or '03:00 PM'}",
        organizer=camp_in.organizer,
        participants=camp_in.participants or 0,
        max_participants=camp_in.max_participants or 100,
        target_units=camp_in.target_units or 50,
        collected_units=camp_in.collected_units or 0,
        description=camp_in.description,
        contact_number=camp_in.contact_number,
        registration_required=camp_in.registration_required or False,
        registration_deadline=camp_in.registration_deadline,
        image_banner=camp_in.image_banner,
        status=camp_in.status or "Upcoming"
    )
    db.add(new_camp)

    # Activity log
    today_str = datetime.now().strftime("%Y-%m-%d")
    db.add(models.ActivityLog(
        category="Campus Events",
        activity=f"New campus event created: {new_camp.title} ({new_camp.event_date})",
        count=new_camp.participants,
        status=new_camp.status,
        log_date=today_str
    ))

    db.commit()
    db.refresh(new_camp)
    return new_camp

@router.put("/{id}", response_model=schemas.CampEventResponse)
def update_camp(id: int, camp_update: schemas.CampEventUpdate, db: Session = Depends(get_db)):
    camp = db.query(models.CampEvent).filter(models.CampEvent.id == id).first()
    if not camp:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Camp event not found")

    update_data = camp_update.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(camp, key, value)

    db.commit()
    db.refresh(camp)
    return camp

@router.put("/{id}/status", response_model=schemas.CampEventResponse)
def update_camp_status(id: int, status_update: schemas.CampEventStatusUpdate, db: Session = Depends(get_db)):
    camp = db.query(models.CampEvent).filter(models.CampEvent.id == id).first()
    if not camp:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Camp event not found")

    camp.status = status_update.status

    today_str = datetime.now().strftime("%Y-%m-%d")
    db.add(models.ActivityLog(
        category="Campus Events",
        activity=f"Event {camp.camp_code} ({camp.title}) status changed to {status_update.status}",
        count=camp.participants,
        status=status_update.status,
        log_date=today_str
    ))

    db.commit()
    db.refresh(camp)
    return camp

@router.delete("/{id}", status_code=status.HTTP_200_OK)
def delete_camp(id: int, db: Session = Depends(get_db)):
    camp = db.query(models.CampEvent).filter(models.CampEvent.id == id).first()
    if not camp:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Camp event not found")

    db.delete(camp)
    db.commit()
    return {"message": "Camp event deleted successfully", "id": id}
