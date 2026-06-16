from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from app.database import engine, Base
from app.routers import auth, orders, attendance, payroll, inventory, ai, notifications, cron, settings
import os
from pathlib import Path

# Create database tables
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Sportify Management System API",
    description="Backend API for Sportify Management System",
    version="1.0.0"
)

# CORS middleware - Allow all origins for Vercel deployment
# In production, you can restrict this to your specific domain
import os
cors_origins = os.getenv("CORS_ORIGINS", "http://localhost:5173,http://localhost:3000").split(",")
# Add Vercel preview and production URLs dynamically
vercel_url = os.getenv("VERCEL_URL")
if vercel_url:
    cors_origins.append(f"https://{vercel_url}")

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router, prefix="/auth", tags=["Authentication"])
app.include_router(orders.router, prefix="/orders", tags=["Orders"])
app.include_router(attendance.router, prefix="/attendance", tags=["Attendance"])
app.include_router(payroll.router, prefix="/payroll", tags=["Payroll"])
app.include_router(inventory.router, prefix="/inventory", tags=["Inventory"])
app.include_router(ai.router, prefix="/ai", tags=["AI Image Generation"])
app.include_router(notifications.router, prefix="/notify", tags=["Notifications"])
app.include_router(settings.router, prefix="/settings", tags=["Settings"])
app.include_router(cron.router)

# Mount static files for AI-generated images (use /tmp on Vercel - ephemeral)
static_dir = Path("/tmp/static") if os.getenv("VERCEL") else Path("static")
static_dir.mkdir(exist_ok=True, parents=True)
(static_dir / "images" / "ai-generated").mkdir(parents=True, exist_ok=True)
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")


@app.get("/")
async def root():
    return {"message": "Sportify Management System API", "status": "running"}


@app.get("/health")
async def health_check():
    from app.image_storage import storage_status
    from app.firebase_app import firebase_status
    from app.database import SessionLocal
    from app.models import User

    push = firebase_status()
    db = SessionLocal()
    try:
        registered_tokens = db.query(User).filter(User.fcm_token.isnot(None)).count()
    finally:
        db.close()

    status = "healthy"
    warning = None
    if not push.get("ready"):
        status = "degraded"
        warning = "Push notifications unavailable — regenerate Firebase service account key"

    return {
        "status": status,
        **storage_status(),
        "push_notifications": {**push, "registered_devices": registered_tokens},
        "warning": warning,
    }

