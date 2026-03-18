# app/routes/__init__.py
"""
Import all route modules
This file is used to collect all routes for registration with FastAPI app
"""

from app.routes import auth
from app.routes import units
from app.routes import assessments
from app.routes import submissions
from app.routes import profiles
from app.routes import wellbeing
from app.routes import voice
from app.routes import messages
from app.routes import reports

# Export routers for FastAPI app to include
routers = [
    auth.router,
    units.router,
    assessments.router,
    submissions.router,
    profiles.router,
    wellbeing.router,
    voice.router,
    messages.router,
    reports.router,
]
