from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import or_, func
from app.database import get_db
from app import models, schemas
from typing import Optional, List
import math

router = APIRouter(
    prefix="/api/donors",
    tags=["Donors"]
)

@router.get("", response_model=schemas.PaginatedDonorsResponse)
def get_donors(
    search: Optional[str] = Query(None),
    group: Optional[str] = Query("All"),
    status_filter: Optional[str] = Query("All", alias="status"),
    location: Optional[str] = Query("All"),
    page: int = Query(1, ge=1),
    limit: int = Query(7, ge=1, le=100),
    db: Session = Depends(get_db)
):
    query = db.query(models.Donor)

    # Search filter across multiple columns
    if search and search.strip():
        term = f"%{search.strip()}%"
        query = query.filter(
            or_(
                models.Donor.name.ilike(term),
                models.Donor.phone.ilike(term),
                models.Donor.email.ilike(term),
                models.Donor.blood_group.ilike(term),
                models.Donor.donor_code.ilike(term),
                models.Donor.location.ilike(term)
            )
        )

    # Blood group filter
    if group and group != "All":
        query = query.filter(
            or_(
                models.Donor.blood_group == group,
                models.Donor.blood_group == group.replace('−', '-'),
                models.Donor.blood_group == group.replace('-', '−')
            )
        )

    # Status filter
    if status_filter and status_filter != "All":
        query = query.filter(models.Donor.status == status_filter)

    # Location filter
    if location and location != "All":
        query = query.filter(models.Donor.location == location)

    total_count = query.count()
    total_pages = max(1, math.ceil(total_count / limit))
    offset = (page - 1) * limit
    donors = query.order_by(models.Donor.id.asc()).offset(offset).limit(limit).all()

    # Collect unique locations and blood groups from PostgreSQL
    distinct_locs = db.query(models.Donor.location).distinct().all()
    all_locations = ["All"] + sorted(list(set([l[0] for l in distinct_locs if l[0]])))
    blood_groups = ["All", "A+", "A−", "B+", "B−", "O+", "O−", "AB+", "AB−"]

    return schemas.PaginatedDonorsResponse(
        items=donors,
        total=total_count,
        page=page,
        limit=limit,
        pages=total_pages,
        locations=all_locations,
        blood_groups=blood_groups
    )

@router.get("/{id}", response_model=schemas.DonorResponse)
def get_donor_by_id(id: int, db: Session = Depends(get_db)):
    donor = db.query(models.Donor).filter(models.Donor.id == id).first()
    if not donor:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Donor not found")
    return donor

@router.post("", response_model=schemas.DonorResponse, status_code=status.HTTP_201_CREATED)
def create_donor(donor_in: schemas.DonorCreate, db: Session = Depends(get_db)):
    # Auto-generate next donor code e.g. DON008
    last_donor = db.query(models.Donor).order_by(models.Donor.id.desc()).first()
    next_num = (last_donor.id + 1) if last_donor else 1
    donor_code = f"DON{str(next_num).zfill(3)}"

    new_donor = models.Donor(
        donor_code=donor_code,
        name=donor_in.name,
        blood_group=donor_in.blood_group,
        phone=donor_in.phone,
        email=donor_in.email,
        location=donor_in.location,
        last_donation=donor_in.last_donation or "Never",
        status=donor_in.status or "Active",
        total_donations=donor_in.total_donations or 1,
        age=donor_in.age,
        gender=donor_in.gender
    )
    db.add(new_donor)
    db.commit()
    db.refresh(new_donor)
    return new_donor

@router.put("/{id}", response_model=schemas.DonorResponse)
def update_donor(id: int, donor_update: schemas.DonorUpdate, db: Session = Depends(get_db)):
    donor = db.query(models.Donor).filter(models.Donor.id == id).first()
    if not donor:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Donor not found")

    update_data = donor_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(donor, field, value)

    db.commit()
    db.refresh(donor)
    return donor

@router.delete("/{id}", status_code=status.HTTP_200_OK)
def delete_donor(id: int, db: Session = Depends(get_db)):
    donor = db.query(models.Donor).filter(
        or_(models.Donor.id == id, models.Donor.donor_code == str(id))
    ).first()
    if not donor:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Donor not found")

    db.delete(donor)
    db.commit()
    return {"message": "Donor deleted successfully", "id": id}
