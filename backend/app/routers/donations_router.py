from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import or_
from app.database import get_db
from app import models, schemas
from typing import List, Optional
from datetime import datetime

router = APIRouter(
    prefix="/api/donations",
    tags=["Donations"]
)

@router.get("", response_model=List[schemas.DonationResponse])
def get_donations(
    search: Optional[str] = None,
    blood_group: Optional[str] = None,
    donation_type: Optional[str] = None,
    status: Optional[str] = None,
    district: Optional[str] = None,
    db: Session = Depends(get_db)
):
    query = db.query(models.Donation)

    if search:
        s = f"%{search}%"
        query = query.filter(
            or_(
                models.Donation.donor_name.ilike(s),
                models.Donation.phone.ilike(s),
                models.Donation.email.ilike(s),
                models.Donation.hospital.ilike(s),
                models.Donation.venue.ilike(s),
                models.Donation.donation_code.ilike(s),
                models.Donation.district.ilike(s)
            )
        )
    if blood_group and blood_group != "All":
        query = query.filter(models.Donation.blood_group == blood_group)
    if donation_type and donation_type != "All":
        query = query.filter(models.Donation.donation_type.ilike(donation_type))
    if status and status != "All":
        query = query.filter(models.Donation.status.ilike(status))
    if district and district != "All":
        query = query.filter(models.Donation.district.ilike(district))

    return query.order_by(models.Donation.id.desc()).all()

@router.post("", response_model=schemas.DonationResponse, status_code=status.HTTP_201_CREATED)
def record_donation(donation_in: schemas.DonationCreate, db: Session = Depends(get_db)):
    last_donation = db.query(models.Donation).order_by(models.Donation.id.desc()).first()
    next_num = (last_donation.id + 1) if last_donation else 1
    code = f"DN{str(next_num).zfill(3)}"

    new_donation = models.Donation(
        donation_code=code,
        donor_id=donation_in.donor_id,
        donor_name=donation_in.donor_name,
        blood_group=donation_in.blood_group,
        phone=donation_in.phone,
        email=donation_in.email,
        district=donation_in.district or "Kottayam",
        address=donation_in.address,
        donation_date=donation_in.donation_date,
        donation_type=donation_in.donation_type or "Voluntary",
        units=donation_in.units,
        hospital=donation_in.hospital or donation_in.venue or "Blood Bank",
        venue=donation_in.venue or donation_in.hospital or "Blood Bank",
        status=donation_in.status or "Completed",
        notes=donation_in.notes
    )
    db.add(new_donation)

    # If completed, automatically increment inventory
    if new_donation.status == "Completed":
        inv = db.query(models.BloodInventory).filter(
            models.BloodInventory.blood_group.in_([
                donation_in.blood_group,
                donation_in.blood_group.replace('−', '-'),
                donation_in.blood_group.replace('-', '−')
            ])
        ).first()
        if inv:
            inv.units_available += donation_in.units

    # Update donor if donor_id matches
    if donation_in.donor_id:
        donor = db.query(models.Donor).filter(models.Donor.id == donation_in.donor_id).first()
        if donor:
            donor.last_donation = donation_in.donation_date
            donor.total_donations += donation_in.units

    # Activity log
    today_str = datetime.now().strftime("%Y-%m-%d")
    db.add(models.ActivityLog(
        category="Blood Donations",
        activity=f"Donation {code} recorded: {donation_in.donor_name} ({donation_in.blood_group}, {donation_in.units}U)",
        count=donation_in.units,
        status=new_donation.status,
        log_date=today_str
    ))

    db.commit()
    db.refresh(new_donation)
    return new_donation

@router.put("/{id}", response_model=schemas.DonationResponse)
def update_donation(id: int, don_update: schemas.DonationUpdate, db: Session = Depends(get_db)):
    don = db.query(models.Donation).filter(models.Donation.id == id).first()
    if not don:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Donation record not found")

    update_data = don_update.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(don, key, value)

    db.commit()
    db.refresh(don)
    return don

@router.put("/{id}/status", response_model=schemas.DonationResponse)
def update_donation_status(id: int, status_update: schemas.DonationStatusUpdate, db: Session = Depends(get_db)):
    don = db.query(models.Donation).filter(models.Donation.id == id).first()
    if not don:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Donation record not found")

    don.status = status_update.status
    db.commit()
    db.refresh(don)
    return don

@router.delete("/{id}", status_code=status.HTTP_200_OK)
def delete_donation(id: int, db: Session = Depends(get_db)):
    don = db.query(models.Donation).filter(models.Donation.id == id).first()
    if not don:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Donation record not found")

    db.delete(don)
    db.commit()
    return {"message": "Donation record deleted successfully", "id": id}
