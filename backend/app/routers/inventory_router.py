from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import or_
from app.database import get_db
from app import models, schemas
from typing import List, Optional
from datetime import datetime

router = APIRouter(
    prefix="/api/inventory",
    tags=["Blood Inventory"]
)

# ─── Blood Group Summary (for Dashboard & Stock Progress Overview) ─────────────
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

    if item.units_available <= (item.min_threshold // 2):
        item.status = "Critical"
    elif item.units_available <= item.min_threshold:
        item.status = "Low"
    else:
        item.status = "Sufficient"

    db.commit()
    db.refresh(item)
    return item


# ─── Blood Inventory Batches (for BloodInventory.jsx full CRUD) ───────────────
@router.get("/batches", response_model=List[schemas.InventoryBatchResponse])
def get_inventory_batches(
    search: Optional[str] = None,
    blood_group: Optional[str] = None,
    component: Optional[str] = None,
    status: Optional[str] = None,
    db: Session = Depends(get_db)
):
    query = db.query(models.BloodInventoryBatch)

    if search:
        s = f"%{search}%"
        query = query.filter(
            or_(
                models.BloodInventoryBatch.blood_group.ilike(s),
                models.BloodInventoryBatch.component.ilike(s),
                models.BloodInventoryBatch.storage_location.ilike(s),
                models.BloodInventoryBatch.batch_code.ilike(s),
                models.BloodInventoryBatch.notes.ilike(s)
            )
        )
    if blood_group and blood_group != "All":
        query = query.filter(models.BloodInventoryBatch.blood_group == blood_group)
    if component and component != "All":
        query = query.filter(models.BloodInventoryBatch.component.ilike(component))
    if status and status != "All":
        query = query.filter(models.BloodInventoryBatch.status.ilike(status))

    batches = query.order_by(models.BloodInventoryBatch.id.asc()).all()
    # Add computed total_units
    result = []
    for b in batches:
        resp = schemas.InventoryBatchResponse.from_orm(b)
        resp.total_units = b.available_units + b.reserved_units
        result.append(resp)
    return result

@router.post("/batches", response_model=schemas.InventoryBatchResponse, status_code=status.HTTP_201_CREATED)
def create_inventory_batch(batch_in: schemas.InventoryBatchCreate, db: Session = Depends(get_db)):
    last_batch = db.query(models.BloodInventoryBatch).order_by(models.BloodInventoryBatch.id.desc()).first()
    next_num = (last_batch.id + 1) if last_batch else 1
    code = f"INV{str(next_num).zfill(3)}"

    new_batch = models.BloodInventoryBatch(
        batch_code=code,
        blood_group=batch_in.blood_group,
        component=batch_in.component or "Whole Blood",
        available_units=batch_in.available_units,
        reserved_units=batch_in.reserved_units or 0,
        collection_date=batch_in.collection_date,
        expiry_date=batch_in.expiry_date,
        storage_location=batch_in.storage_location,
        status=batch_in.status or "Available",
        notes=batch_in.notes
    )
    db.add(new_batch)

    # Sync summary inventory units
    sync_inventory_summary(db, batch_in.blood_group)

    # Activity log
    today_str = datetime.now().strftime("%Y-%m-%d")
    db.add(models.ActivityLog(
        category="Blood Inventory",
        activity=f"New batch {code} added for {batch_in.blood_group} ({batch_in.component})",
        count=batch_in.available_units,
        status="Completed",
        log_date=today_str
    ))

    db.commit()
    db.refresh(new_batch)
    resp = schemas.InventoryBatchResponse.from_orm(new_batch)
    resp.total_units = new_batch.available_units + new_batch.reserved_units
    return resp

@router.put("/batches/{id}", response_model=schemas.InventoryBatchResponse)
def update_inventory_batch(id: int, batch_update: schemas.InventoryBatchUpdate, db: Session = Depends(get_db)):
    batch = db.query(models.BloodInventoryBatch).filter(models.BloodInventoryBatch.id == id).first()
    if not batch:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Inventory batch not found")

    update_data = batch_update.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(batch, key, value)

    sync_inventory_summary(db, batch.blood_group)

    db.commit()
    db.refresh(batch)
    resp = schemas.InventoryBatchResponse.from_orm(batch)
    resp.total_units = batch.available_units + batch.reserved_units
    return resp

@router.post("/batches/{id}/adjust", response_model=schemas.InventoryBatchResponse)
def adjust_inventory_batch_stock(id: int, adjust_data: schemas.InventoryBatchAdjust, db: Session = Depends(get_db)):
    batch = db.query(models.BloodInventoryBatch).filter(models.BloodInventoryBatch.id == id).first()
    if not batch:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Inventory batch not found")

    delta = adjust_data.quantity if adjust_data.type == "add" else -adjust_data.quantity
    new_avail = batch.available_units + delta
    if new_avail < 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Available units cannot drop below zero")

    batch.available_units = new_avail
    if new_avail == 0:
        batch.status = "Critical"
    elif new_avail <= 4:
        batch.status = "Low Stock"
    else:
        batch.status = "Available"

    sync_inventory_summary(db, batch.blood_group)

    # Activity log
    today_str = datetime.now().strftime("%Y-%m-%d")
    db.add(models.ActivityLog(
        category="Blood Inventory",
        activity=f"Stock level adjustment: batch {batch.batch_code} {batch.blood_group} ({adjust_data.reason or 'Manual adjustment'})",
        count=adjust_data.quantity,
        status="Completed",
        log_date=today_str
    ))

    db.commit()
    db.refresh(batch)
    resp = schemas.InventoryBatchResponse.from_orm(batch)
    resp.total_units = batch.available_units + batch.reserved_units
    return resp

@router.delete("/batches/{id}", status_code=status.HTTP_200_OK)
def delete_inventory_batch(id: int, db: Session = Depends(get_db)):
    batch = db.query(models.BloodInventoryBatch).filter(models.BloodInventoryBatch.id == id).first()
    if not batch:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Inventory batch not found")

    blood_group = batch.blood_group
    db.delete(batch)
    sync_inventory_summary(db, blood_group)
    db.commit()
    return {"message": "Inventory batch deleted successfully", "id": id}

def sync_inventory_summary(db: Session, blood_group: str):
    """Keep aggregated blood_inventory table in sync with batches"""
    batches = db.query(models.BloodInventoryBatch).filter(models.BloodInventoryBatch.blood_group == blood_group).all()
    total_avail = sum(b.available_units for b in batches)
    total_res = sum(b.reserved_units for b in batches)

    item = db.query(models.BloodInventory).filter(
        models.BloodInventory.blood_group.in_([
            blood_group,
            blood_group.replace('−', '-'),
            blood_group.replace('-', '−')
        ])
    ).first()

    if item:
        item.units_available = total_avail
        item.units_reserved = total_res
        if total_avail <= (item.min_threshold // 2):
            item.status = "Critical"
        elif total_avail <= item.min_threshold:
            item.status = "Low"
        else:
            item.status = "Sufficient"
