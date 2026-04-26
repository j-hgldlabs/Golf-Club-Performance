from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routers import auth, sessions, analytics, admin

app = FastAPI(
    title="Golf Analytics API",
    description="Backend for the Golf Performance Dashboard.",
    version="0.1.0",
)

# Allow the Streamlit app (and any future frontend) to call the API.
# Tighten origins before going to production.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8501", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router,      prefix="/auth",      tags=["auth"])
app.include_router(sessions.router,  prefix="/sessions",  tags=["sessions"])
app.include_router(analytics.router, prefix="/analytics", tags=["analytics"])
app.include_router(admin.router,     prefix="/admin",     tags=["admin"])


@app.get("/health")
async def health():
    return {"status": "ok"}
