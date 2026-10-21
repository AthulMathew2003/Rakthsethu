from fastapi import APIRouter
from app.api.v1.auth import router as auth_router
from app.api.v1.blood_requests import router as blood_requests_router
from app.api.v1.donations import router as donations_router
from app.api.v1.donor_import import router as donor_import_router
from app.api.v1.donors import router as donors_router
from app.api.v1.hospitals import router as hospitals_router
from app.api.v1.locations import router as locations_router
from app.api.v1.matching import router as matching_router
from app.telegram.router import router as telegram_router

# Master v1 API Router
v1_router = APIRouter(prefix="/api/v1")

v1_router.include_router(auth_router)
v1_router.include_router(locations_router)
v1_router.include_router(hospitals_router)
v1_router.include_router(donor_import_router)
v1_router.include_router(donors_router)
v1_router.include_router(donations_router)
v1_router.include_router(blood_requests_router)
v1_router.include_router(matching_router)
v1_router.include_router(telegram_router)
