from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from database import Base, engine
from routers import stats, projects, cleanup, discovery
from routers.auth import router as auth_router
from routers import servers

import models

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="AI Infrastructure Intelligence Platform",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:5173"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(servers.router)
app.include_router(projects.router)
app.include_router(stats.router)
app.include_router(cleanup.router)
app.include_router(discovery.router)

@app.get("/")
def root():
    return {
        "message": "AI Infrastructure Intelligence Platform API",
        "version": "1.0.0",
        "status": "running"
    }

@app.get("/health")
def health():
    return {
        "status": "healthy",
        "database": "connected"
    }