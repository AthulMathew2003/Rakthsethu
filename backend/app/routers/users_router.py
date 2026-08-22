from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app import models, schemas, auth
from typing import List

router = APIRouter(
    prefix="/api/users",
    tags=["Users & Staff"]
)

@router.get("", response_model=List[schemas.UserResponse])
def get_all_users(db: Session = Depends(get_db)):
    return db.query(models.User).order_by(models.User.id.asc()).all()

@router.post("", response_model=schemas.UserResponse, status_code=status.HTTP_201_CREATED)
def create_staff_user(user_in: schemas.UserCreate, db: Session = Depends(get_db)):
    email_clean = user_in.email.lower().strip()
    existing = db.query(models.User).filter(models.User.email == email_clean).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered")

    new_user = models.User(
        email=email_clean,
        hashed_password=auth.get_password_hash(user_in.password),
        full_name=user_in.full_name,
        phone_number=user_in.phone_number,
        role=user_in.role or "Staff",
        is_active=True,
        is_admin=(user_in.role == "Admin")
    )
    db.add(new_user)
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

    db.commit()
    db.refresh(user)
    return user

@router.delete("/{id}", status_code=status.HTTP_200_OK)
def delete_staff_user(id: int, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.id == id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    if user.email == "donor@rakthasethu.org":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot delete default admin")

    db.delete(user)
    db.commit()
    return {"message": "User deleted successfully", "id": id}
