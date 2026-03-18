# app/main.py
"""
FastAPI main application
Entry point for the IB Learning Community backend

Run with:
    uvicorn app.main:app --reload
    
Or:
    python -m uvicorn app.main:app --reload
"""

from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from app.config import settings
from app.database import engine, get_db
from app.models import Base
from app.routes import routers
from datetime import datetime

# ============================================================================
# CREATE TABLES (if they don't exist)
# ============================================================================

Base.metadata.create_all(bind=engine)

# ============================================================================
# INITIALIZE FASTAPI APP
# ============================================================================

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="IB Learning Community Backend API",
    version=settings.VERSION,
    docs_url="/api/docs",
    openapi_url="/api/openapi.json",
)

# ============================================================================
# MIDDLEWARE - CORS
# ============================================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================================================
# INCLUDE ALL ROUTES
# ============================================================================

for router in routers:
    app.include_router(router)

# ============================================================================
# HEALTH CHECK ENDPOINTS
# ============================================================================

@app.get("/health", tags=["health"])
def health_check():
    """
    Health check endpoint
    """
    return {
        "status": "healthy",
        "app_name": settings.PROJECT_NAME,
        "timestamp": datetime.utcnow().isoformat()
    }

@app.get("/api/health", tags=["health"])
def api_health_check():
    """
    API health check endpoint
    """
    return {
        "status": "ok",
        "message": "IB Learning Community API is running",
        "version": settings.VERSION,
        "timestamp": datetime.utcnow().isoformat()
    }

# ============================================================================
# WELCOME ENDPOINT
# ============================================================================

@app.get("/", tags=["info"])
def root():
    """
    Welcome message
    """
    return {
        "message": "Welcome to IB Learning Community API",
        "docs": "/api/docs",
        "version": settings.VERSION,
        "endpoints": {
            "auth": "/api/v1/auth",
            "units": "/api/v1/units",
            "assessments": "/api/v1/assessments",
            "submissions": "/api/v1/submissions",
            "profiles": "/api/v1/profiles",
            "wellbeing": "/api/v1/wellbeing",
            "voice": "/api/v1/voice",
            "messages": "/api/v1/messages",
            "reports": "/api/v1/reports",
        }
    }

# ============================================================================
# EXCEPTION HANDLERS
# ============================================================================

@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    """Custom HTTP exception handler"""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "status": "error",
            "message": exc.detail,
            "timestamp": datetime.utcnow().isoformat()
        }
    )

@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    """Catch-all exception handler"""
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "status": "error",
            "message": "Internal server error",
            "detail": str(exc) if settings.DEBUG else "An error occurred",
            "timestamp": datetime.utcnow().isoformat()
        }
    )

# ============================================================================
# STARTUP & SHUTDOWN EVENTS
# ============================================================================

@app.on_event("startup")
async def startup_event():
    """
    Run on app startup
    """
    print(f"🚀 {settings.PROJECT_NAME} API starting...")
    print(f"📍 Environment: {settings.ENVIRONMENT}")
    print(f"🗄️  Database: {settings.DATABASE_URL.split('@')[1] if '@' in settings.DATABASE_URL else 'Supabase'}")
    print(f"✅ API is ready!")

@app.on_event("shutdown")
async def shutdown_event():
    """
    Run on app shutdown
    """
    print(f"👋 {settings.PROJECT_NAME} API shutting down...")

# ============================================================================
# VERSION INFO
# ============================================================================

@app.get("/api/v1/version", tags=["info"])
def get_version():
    """
    Get API version info
    """
    return {
        "app_name": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "environment": settings.ENVIRONMENT,
        "timestamp": datetime.utcnow().isoformat()
    }

# ============================================================================
# DOCUMENTATION
# ============================================================================

"""
API STRUCTURE:

Authentication:
  POST   /api/v1/auth/register         - Register user
  POST   /api/v1/auth/login            - Login user
  POST   /api/v1/auth/refresh          - Refresh token
  POST   /api/v1/auth/logout           - Logout
  GET    /api/v1/auth/me               - Get current user

Units (T-01, S-02):
  POST   /api/v1/units                 - Create unit
  GET    /api/v1/units                 - List units
  GET    /api/v1/units/{id}            - Get unit details
  PATCH  /api/v1/units/{id}            - Update unit
  POST   /api/v1/units/{id}/join       - Student joins unit

Assessments (T-05):
  POST   /api/v1/assessments           - Create assessment
  GET    /api/v1/assessments           - List assessments
  GET    /api/v1/assessments/{id}      - Get assessment
  PATCH  /api/v1/assessments/{id}      - Update assessment

Submissions (S-05, T-06, S-06):
  POST   /api/v1/submissions           - Student submits work
  POST   /api/v1/submissions/{id}/feedback - Teacher provides feedback
  GET    /api/v1/submissions/{id}      - View submission & feedback

Learner Profiles (S-07, T-07):
  POST   /api/v1/profiles/self-assess  - Student self-assesses
  POST   /api/v1/profiles/{id}/rate    - Teacher rates student
  GET    /api/v1/profiles/student/{id} - Get student's profile
  GET    /api/v1/profiles/my-profile   - Student gets own profile

Well-Being (S-09):
  POST   /api/v1/wellbeing             - Record check-in
  GET    /api/v1/wellbeing/my-status   - Student's status
  GET    /api/v1/wellbeing/student/{id} - Teacher views student
  GET    /api/v1/wellbeing/class       - Class overview

Voice & Agency (T-03):
  POST   /api/v1/voice/decisions       - Create decision
  POST   /api/v1/voice/decisions/{id}/vote - Student votes
  GET    /api/v1/voice/decisions       - List decisions
  GET    /api/v1/voice/agency-events   - View agency events

Messages:
  POST   /api/v1/messages              - Send message
  GET    /api/v1/messages/inbox        - Get inbox
  GET    /api/v1/messages/{id}         - Get message
  PATCH  /api/v1/messages/{id}/read    - Mark as read

Reports (T-10):
  GET    /api/v1/reports/student/{id}  - Student progress report
  GET    /api/v1/reports/unit/{id}     - Unit progress report
  GET    /api/v1/reports/my-progress   - Student's own progress
"""

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )
