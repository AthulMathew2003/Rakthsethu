from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app import models, schemas
from typing import List

router = APIRouter(
    prefix="/api/inventory",
    tags=["Blood Inventory"]
)

@router.get("", response_model=List[schemas.InventoryItemResponse])
def get_all_inventory(db: Session = Depends(get_db)):
    items = db.query(models.BloodInventory).order_by(models.BloodInventory.id.asc()).all()
    return items

@router.put("/{blood_group}", response_model=schemas.InventoryItemResponse)
def update_inventory_units(
    blood_group: str,
    update_data: schemas.InventoryItemUpdate,
    db: Session = Depends(get_db)
):
    item = db.query(models.BloodInventory).filter(
        models.BloodInventory.blood_group.in_([
            blood_group,
            blood_group.replace('−', '-'),
            blood_group.replace('-', '−')
        ])
    ).first()

    if not item:
        # Create if not found
        item = models.BloodInventory(
            blood_group=blood_group,
            units_available=update_data.units_available,
            units_reserved=update_data.units_reserved or 0,
            min_threshold=update_data.min_threshold or 20
        )
        db.add(item)
    else:
        item.units_available = update_data.units_available
        if update_data.units_reserved is not None:
            item.units_reserved = update_data.units_reserved
        if update_data.min_threshold is not None:
            item.min_threshold = update_data.min_threshold

    # Update status dynamically based on threshold
    if item.units_available <= (item.min_threshold // 2):
        item.status = "Critical"
    elif item.units_available <= item.min_threshold:
        item.status = "Low"
    else:
        item.status = "Sufficient"

    db.commit()
    db.refresh(item)
    return item
