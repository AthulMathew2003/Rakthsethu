from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.database import engine, Base
from app.routers import auth_router

# Initialize database tables automatically
try:
    Base.metadata.create_all(bind=engine)
except Exception as e:
    print(f"Database table initialization warning (check PostgreSQL connection): {e}")

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="FastAPI Backend connected to PostgreSQL database 'rakthasethu' for Rakthasethu application.",
    version="1.0.0"
)

# CORS Middleware to allow requests from frontend React client
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(auth_router.router)

@app.get("/")
def read_root():
    return {
        "message": "Welcome to Rakthasethu API",
        "database": "PostgreSQL (rakthasethu)",
        "docs_url": "/docs"
    }

@app.get("/health")
def health_check():
    return {"status": "ok", "service": settings.PROJECT_NAME}
