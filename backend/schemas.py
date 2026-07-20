from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr


# ==================================================
# USER SCHEMAS
# ==================================================

class UserCreate(BaseModel):
    username: str
    email: EmailStr
    password: str


class UserOut(BaseModel):
    id: int
    username: str
    email: Optional[str] = None
    is_active: bool
    role: str

    class Config:
        from_attributes = True


# ==================================================
# AUTH SCHEMAS
# ==================================================

class Token(BaseModel):
    access_token: str
    token_type: str


# ==================================================
# SERVER SCHEMAS
# ==================================================

class ServerBase(BaseModel):
    name: str
    ip_address: str
    environment: str = "production"
    status: str = "active"
    description: Optional[str] = None


class ServerCreate(ServerBase):
    pass


class ServerUpdate(ServerBase):
    pass


class ServerOut(ServerBase):
    id: int
    created_at: datetime
    cpu_usage: int = 0
    memory_usage: int = 0
    disk_usage: int = 0
    error_count: int = 0
    uptime_days: int = 0
    risk_score: int = 0

    class Config:
        from_attributes = True


# ==================================================
# PROJECT SCHEMAS
# ==================================================

class ProjectBase(BaseModel):
    name: str
    description: Optional[str] = None
    status: str = "active"
    server_id: Optional[int] = None


class ProjectCreate(ProjectBase):
    pass


class ProjectUpdate(ProjectBase):
    pass


class ProjectOut(ProjectBase):
    id: int
    created_at: datetime
    risk_score: int = 0

    class Config:
        from_attributes = True


# ==================================================
# DASHBOARD / ANALYTICS SCHEMAS
# ==================================================

class DashboardStats(BaseModel):
    total_servers: int
    total_projects: int
    active_projects: int
    inactive_projects: int


# ==================================================
# AI RISK ENGINE SCHEMAS
# ==================================================

class RiskAnalysis(BaseModel):
    project_id: int
    project_name: str
    risk_score: int
    risk_level: str
    recommendation: str