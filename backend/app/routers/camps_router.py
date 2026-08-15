from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app import models, schemas
from typing import List

router = APIRouter(
    prefix="/api/camps",
    tags=["Camps & Events"]
)

@router.get("", response_model=List[schemas.CampEventResponse])
def get_camps(db: Session = Depends(get_db)):
    return db.query(models.CampEvent).order_by(models.CampEvent.id.desc()).all()

@router.post("", response_model=schemas.CampEventResponse, status_code=status.HTTP_201_CREATED)
def create_camp(camp_in: schemas.CampEventCreate, db: Session = Depends(get_db)):
    last_camp = db.query(models.CampEvent).order_by(models.CampEvent.id.desc()).first()
    next_num = (last_camp.id + 1) if last_camp else 1
    code = f"CAMP{str(next_num).zfill(3)}"

    new_camp = models.CampEvent(
        camp_code=code,
        title=camp_in.title,
        location=camp_in.location,
        event_date=camp_in.event_date,
        time_slot=camp_in.time_slot or "9:00 AM – 2:00 PM",
        organizer=camp_in.organizer,
        target_units=camp_in.target_units or 50,
        collected_units=camp_in.collected_units or 0,
        status=camp_in.status or "Upcoming"
    )
    db.add(new_camp)
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

@router.delete("/{id}", status_code=status.HTTP_200_OK)
def delete_camp(id: int, db: Session = Depends(get_db)):
    camp = db.query(models.CampEvent).filter(models.CampEvent.id == id).first()
    if not camp:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Camp event not found")

    db.delete(camp)
    db.commit()
    return {"message": "Camp event deleted successfully", "id": id}
