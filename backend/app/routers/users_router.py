from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import or_
from app.database import get_db
from app import models, schemas, auth
from typing import List, Optional
from datetime import datetime

router = APIRouter(
    prefix="/api/users",
    tags=["Users & Staff"]
)

@router.get("", response_model=List[schemas.UserResponse])
def get_all_users(
    search: Optional[str] = None,
    role: Optional[str] = None,
    status: Optional[str] = None,
    district: Optional[str] = None,
    db: Session = Depends(get_db)
):
    query = db.query(models.User)

    if search:
        s = f"%{search}%"
        query = query.filter(
            or_(
                models.User.full_name.ilike(s),
                models.User.email.ilike(s),
                models.User.phone_number.ilike(s),
                models.User.district.ilike(s),
                models.User.panchayat.ilike(s),
                models.User.user_code.ilike(s)
            )
        )
    if role and role != "All":
        query = query.filter(models.User.role.ilike(role))
    if status and status != "All":
        query = query.filter(models.User.status.ilike(status))
    if district and district != "All":
        query = query.filter(models.User.district.ilike(district))

    return query.order_by(models.User.id.asc()).all()

@router.post("", response_model=schemas.UserResponse, status_code=status.HTTP_201_CREATED)
def create_staff_user(user_in: schemas.UserCreate, db: Session = Depends(get_db)):
    email_clean = user_in.email.lower().strip()
    existing = db.query(models.User).filter(models.User.email == email_clean).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered")

    last_user = db.query(models.User).order_by(models.User.id.desc()).first()
    next_num = (last_user.id + 1) if last_user else 1
    user_code = f"USR{str(next_num).zfill(3)}"

    today_str = datetime.now().strftime("%Y-%m-%d")

    new_user = models.User(
        user_code=user_code,
        email=email_clean,
        hashed_password=auth.get_password_hash(user_in.password or "password123"),
        full_name=user_in.full_name,
        phone_number=user_in.phone_number,
        role=user_in.role or "Citizen",
        district=user_in.district or "Kottayam",
        panchayat=user_in.panchayat,
        registered_date=user_in.registered_date or today_str,
        last_active=user_in.last_active or today_str,
        status=user_in.status or "Active",
        is_active=(user_in.status != "Inactive" and user_in.status != "Suspended"),
        is_admin=(user_in.role in ["Admin", "Super Admin"])
    )
    db.add(new_user)

    # Activity log
    db.add(models.ActivityLog(
        category="Users",
        activity=f"New user registered: {new_user.full_name} ({new_user.role}, {new_user.district})",
        count=1,
        status="Active",
        log_date=today_str
    ))

    db.commit()
    db.refresh(new_user)
    return new_user

@router.put("/{id}", response_model=schemas.UserResponse)
def update_staff_user(id: int, user_update: schemas.UserUpdate, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.id == id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    update_data = user_update.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(user, key, value)

    if "status" in update_data:
        user.is_active = (user.status == "Active")
    if "role" in update_data:
        user.is_admin = (user.role in ["Admin", "Super Admin"])

    db.commit()
    db.refresh(user)
    return user

@router.put("/{id}/status", response_model=schemas.UserResponse)
def update_user_status(id: int, status_update: schemas.UserStatusUpdate, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.id == id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    user.status = status_update.status
    user.is_active = (status_update.status == "Active")

    today_str = datetime.now().strftime("%Y-%m-%d")
    db.add(models.ActivityLog(
        category="Users",
        activity=f"User {user.full_name} ({user.user_code or user.email}) status updated to {status_update.status}",
        count=1,
        status=status_update.status,
        log_date=today_str
    ))

    db.commit()
    db.refresh(user)
    return user

@router.delete("/{id}", status_code=status.HTTP_200_OK)
def delete_staff_user(id: int, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.id == id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    if user.email == "sruthy.admin@rakthasethu.org":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot delete default system admin")

    db.delete(user)
    db.commit()
    return {"message": "User deleted successfully", "id": id}
