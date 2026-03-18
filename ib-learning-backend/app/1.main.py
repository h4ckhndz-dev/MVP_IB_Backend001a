## Minimal app/main.py (FastAPI Entry Point)

```python
"""
IB Learning Community - FastAPI Backend
Main application entry point
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import engine, Base
from app.routes import auth, units, assessments, submissions, profiles, wellbeing, voice, messages

# Create tables on startup (optional - use Alembic migrations in production)
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    print("🚀 IB Learning Community API Starting...")
    Base.metadata.create_all(bind=engine)
    yield
    # Shutdown
    print("🛑 IB Learning Community API Shutting Down...")

# Initialize FastAPI app
app = FastAPI(
    title=settings.APP_NAME,
    description="IB Learning Community Platform API",
    version=settings.APP_VERSION,
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router, prefix="/api/v1/auth", tags=["Authentication"])
app.include_router(units.router, prefix="/api/v1/units", tags=["Units"])
app.include_router(assessments.router, prefix="/api/v1/assessments", tags=["Assessments"])
app.include_router(submissions.router, prefix="/api/v1/submissions", tags=["Student Work"])
app.include_router(profiles.router, prefix="/api/v1/profiles", tags=["Learner Profiles"])
app.include_router(wellbeing.router, prefix="/api/v1/wellbeing", tags=["Well-Being"])
app.include_router(voice.router, prefix="/api/v1/voice", tags=["Student Voice"])
app.include_router(messages.router, prefix="/api/v1/messages", tags=["Messages"])

# Health check endpoint
@app.get("/health", tags=["System"])
async def health_check():
    return {
        "status": "healthy",
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION
    }

# Root endpoint
@app.get("/", tags=["Root"])
async def root():
    return {
        "message": "IB Learning Community API",
        "docs": "/docs",
        "health": "/health"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG
    )
```

---