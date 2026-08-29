from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app import models, schemas, auth
from typing import Dict, Any

router = APIRouter(
    prefix="/api/settings",
    tags=["Settings"]
)

DEFAULT_SETTINGS = {
    "general": {
        "appName": "Rakthasethu",
        "orgName": "Rakthasethu Blood Management System",
        "email": "admin@rakthasethu.org",
        "phone": "+91 94951 78902",
        "defaultDistrict": "Kottayam",
        "language": "English"
    },
    "profile": {
        "fullName": "Sruthy M S",
        "email": "sruthy.admin@rakthasethu.org",
        "phone": "+91 98456 78901",
        "role": "Admin",
        "district": "Kottayam",
        "panchayat": "Kanjirappally",
        "avatar": "https://images.unsplash.com/photo-1494790108377-be9c29b29330?q=80&w=150&auto=format&fit=crop"
    },
    "notifications": {
        "bloodRequest": True,
        "bloodDonation": True,
        "lowStock": True,
        "expiryAlerts": True,
        "newUser": False,
        "campusEvents": True,
        "systemNotif": True,
        "emailNotif": True
    },
    "appearance": {
        "theme": "Light",
        "sidebarMode": "Expanded"
    },
    "security": {
        "twoFactor": False,
        "loginAlerts": True,
        "sessionTimeout": "30 Minutes"
    },
    "system": {
        "maintenanceMode": False,
        "automaticNotif": True,
        "lowStockThreshold": 5,
        "expiryWarningDays": 7,
        "defaultEventStatus": "Draft"
    }
}

@router.get("")
def get_settings(db: Session = Depends(get_db)):
    result = {}
    for section_name, default_val in DEFAULT_SETTINGS.items():
        row = db.query(models.SystemSetting).filter(models.SystemSetting.section == section_name).first()
        if row and row.settings_data:
            result[section_name] = row.settings_data
        else:
            result[section_name] = default_val
    return result

@router.put("")
def save_settings(payload: schemas.SettingsSaveRequest, db: Session = Depends(get_db)):
    data = payload.dict(exclude_unset=True)
    for section_name, section_data in data.items():
        if section_data is not None:
            row = db.query(models.SystemSetting).filter(models.SystemSetting.section == section_name).first()
            if not row:
                row = models.SystemSetting(section=section_name, settings_data=section_data)
                db.add(row)
            else:
                row.settings_data = section_data

    # If profile was updated, also update admin user in users table
    if payload.profile:
        admin = db.query(models.User).filter(models.User.email == "sruthy.admin@rakthasethu.org").first()
        if admin:
            if "fullName" in payload.profile:
                admin.full_name = payload.profile["fullName"]
            if "phone" in payload.profile:
                admin.phone_number = payload.profile["phone"]
            if "district" in payload.profile:
                admin.district = payload.profile["district"]
            if "panchayat" in payload.profile:
                admin.panchayat = payload.profile["panchayat"]

    db.commit()
    return {"message": "Settings saved successfully"}

@router.put("/profile")
def update_profile(profile_data: schemas.ProfileUpdateRequest, db: Session = Depends(get_db)):
    row = db.query(models.SystemSetting).filter(models.SystemSetting.section == "profile").first()
    current_data = row.settings_data if row and row.settings_data else DEFAULT_SETTINGS["profile"].copy()

    for key, val in profile_data.dict(exclude_unset=True).items():
        if val is not None:
            current_data[key] = val

    if not row:
        row = models.SystemSetting(section="profile", settings_data=current_data)
        db.add(row)
    else:
        row.settings_data = current_data

    admin = db.query(models.User).filter(models.User.email == "sruthy.admin@rakthasethu.org").first()
    if admin:
        if profile_data.fullName:
            admin.full_name = profile_data.fullName
        if profile_data.phone:
            admin.phone_number = profile_data.phone
        if profile_data.district:
            admin.district = profile_data.district
        if profile_data.panchayat:
            admin.panchayat = profile_data.panchayat

    db.commit()
    return {"message": "Profile updated successfully", "profile": current_data}

@router.post("/change-password")
def change_admin_password(pwd_data: schemas.ChangePassword, db: Session = Depends(get_db)):
    admin = db.query(models.User).filter(models.User.email == "sruthy.admin@rakthasethu.org").first()
    if not admin:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Admin user not found")

    if not auth.verify_password(pwd_data.old_password, admin.hashed_password):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Current password does not match")

    admin.hashed_password = auth.get_password_hash(pwd_data.new_password)
    db.commit()
    return {"message": "Password changed successfully"}
