from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app import models, schemas
from typing import List

router = APIRouter(
    prefix="/api/donations",
    tags=["Donations"]
)

@router.get("", response_model=List[schemas.DonationResponse])
def get_donations(db: Session = Depends(get_db)):
    return db.query(models.Donation).order_by(models.Donation.id.desc()).all()

@router.post("", response_model=schemas.DonationResponse, status_code=status.HTTP_201_CREATED)
def record_donation(donation_in: schemas.DonationCreate, db: Session = Depends(get_db)):
    last_donation = db.query(models.Donation).order_by(models.Donation.id.desc()).first()
    next_num = (last_donation.id + 1) if last_donation else 1
    code = f"DONAT-{str(next_num).zfill(3)}"

    new_donation = models.Donation(
        donation_code=code,
        donor_id=donation_in.donor_id,
        donor_name=donation_in.donor_name,
        blood_group=donation_in.blood_group,
        units=donation_in.units,
        donation_date=donation_in.donation_date,
        venue=donation_in.venue,
        status=donation_in.status or "Completed"
    )
    db.add(new_donation)

    # Automatically increment inventory stock for that blood group
    inv = db.query(models.BloodInventory).filter(
        models.BloodInventory.blood_group.in_([
            donation_in.blood_group,
            donation_in.blood_group.replace('−', '-'),
            donation_in.blood_group.replace('-', '−')
        ])
    ).first()
    if inv:
        inv.units_available += donation_in.units

    # Update donor's last donation date and total donations if donor_id matches
    if donation_in.donor_id:
        donor = db.query(models.Donor).filter(models.Donor.id == donation_in.donor_id).first()
        if donor:
            donor.last_donation = donation_in.donation_date
            donor.total_donations += donation_in.units

    db.commit()
    db.refresh(new_donation)
    return new_donation
