from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from database import engine
import models
from routers import auth, servers, projects, cleanup

models.Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="ServerManager Pro",
    description="Professional Server Management & Cleanup System",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router)
app.include_router(servers.router)
app.include_router(projects.router)
app.include_router(cleanup.router)

@app.get("/")
def root():
    return {
        "message": "ServerManager Pro API is running",
        "version": "1.0.0",
        "status": "healthy"
    }

@app.get("/health")
def health_check():
    return {"status": "ok"}