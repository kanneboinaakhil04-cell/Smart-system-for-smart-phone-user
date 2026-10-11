from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from backend.database import db_wrapper
from backend.routers import auth, screentime, focus, checkins, goals, achievements, tips, progress, ai, export, realtime, challenges, accountability


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Initialize database
    await db_wrapper.init_db()
    yield

app = FastAPI(
    title="PhoneBalance API",
    description="Backend API for PhoneBalance - A Smart System for Healthy Smartphone Usage",
    version="1.1.0",
    lifespan=lifespan
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include Routers
app.include_router(auth.router)
app.include_router(screentime.router)
app.include_router(focus.router)
app.include_router(checkins.router)
app.include_router(goals.router)
app.include_router(achievements.router)
app.include_router(tips.router)
app.include_router(progress.router)
app.include_router(ai.router)
app.include_router(export.router)
app.include_router(realtime.router)
app.include_router(challenges.router)
app.include_router(accountability.router)




@app.get("/")
async def root():
    return {
        "status": "online",
        "app_name": "PhoneBalance API",
        "version": "1.0.0",
        "database": "MongoDB" if db_wrapper.using_mongodb else "Embedded Data Store (Active)"
    }
