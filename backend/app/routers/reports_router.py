from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.database import get_db
from app import models, schemas
from typing import Optional, List, Dict, Any

router = APIRouter(
    prefix="/api/reports",
    tags=["Reports & Analytics"]
)

@router.get("/analytics")
def get_reports_analytics(
    range_filter: Optional[str] = "Last 30 Days",
    category: Optional[str] = "Overview",
    db: Session = Depends(get_db)
):
    # Live counts from database
    total_users = db.query(models.User).count()
    active_users = db.query(models.User).filter(models.User.status == "Active").count()
    inactive_users = db.query(models.User).filter(models.User.status == "Inactive").count()
    suspended_users = db.query(models.User).filter(models.User.status == "Suspended").count()

    total_requests = db.query(models.BloodRequest).count()
    pending_requests = db.query(models.BloodRequest).filter(models.BloodRequest.status == "Pending").count()
    approved_requests = db.query(models.BloodRequest).filter(models.BloodRequest.status == "Approved").count()
    fulfilled_requests = db.query(models.BloodRequest).filter(models.BloodRequest.status == "Fulfilled").count()
    cancelled_requests = db.query(models.BloodRequest).filter(models.BloodRequest.status.in_(["Cancelled", "Rejected"])).count()

    total_donations = db.query(models.Donation).count()
    voluntary_donations = db.query(models.Donation).filter(models.Donation.donation_type == "Voluntary").count()
    replacement_donations = db.query(models.Donation).filter(models.Donation.donation_type == "Replacement").count()
    camp_donations = db.query(models.Donation).filter(models.Donation.donation_type == "Camp Donation").count()
    units_collected = db.query(func.sum(models.Donation.units)).scalar() or 0

    batches = db.query(models.BloodInventoryBatch).all()
    total_units = sum(b.available_units + b.reserved_units for b in batches)
    available_units = sum(b.available_units for b in batches)
    reserved_units = sum(b.reserved_units for b in batches)
    critical_batches = sum(1 for b in batches if b.available_units <= 4)

    total_events = db.query(models.CampEvent).count()
    upcoming_events = db.query(models.CampEvent).filter(models.CampEvent.status == "Upcoming").count()
    ongoing_events = db.query(models.CampEvent).filter(models.CampEvent.status == "Ongoing").count()
    completed_events = db.query(models.CampEvent).filter(models.CampEvent.status == "Completed").count()

    total_hospitals = db.query(models.Hospital).count()

    return {
        "counts": {
            "hospitalsCount": total_hospitals,
            "bloodRequestsCount": total_requests,
            "bloodDonationsCount": total_donations,
            "bloodInventoryCount": available_units,
            "usersCount": total_users,
            "eventsCount": total_events
        },
        "stats": {
            "users": {
                "total": total_users,
                "active": active_users,
                "inactive": inactive_users,
                "suspended": suspended_users,
                "newUsers": max(1, total_users - active_users)
            },
            "requests": {
                "total": total_requests,
                "pending": pending_requests,
                "approved": approved_requests,
                "fulfilled": fulfilled_requests,
                "critical": max(1, pending_requests)
            },
            "donations": {
                "total": total_donations,
                "completed": total_donations,
                "scheduled": 0,
                "units": units_collected
            },
            "inventory": {
                "totalUnits": total_units,
                "availableUnits": available_units,
                "reservedUnits": reserved_units,
                "lowStockBatches": critical_batches
            },
            "events": {
                "total": total_events,
                "upcoming": upcoming_events,
                "ongoing": ongoing_events,
                "completed": completed_events,
                "cancelled": 0
            }
        }
    }

@router.get("/activity-logs", response_model=List[schemas.ActivityLogResponse])
def get_activity_logs(
    category: Optional[str] = None,
    limit: int = 20,
    db: Session = Depends(get_db)
):
    query = db.query(models.ActivityLog)
    if category and category != "All" and category != "Overview":
        query = query.filter(models.ActivityLog.category.ilike(category))

    logs = query.order_by(models.ActivityLog.id.desc()).limit(limit).all()
    return logs
