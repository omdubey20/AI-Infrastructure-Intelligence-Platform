from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


# ─── Auth ───────────────────────────────────────
class UserCreate(BaseModel):
    username: str
    email: str
    password: str

class UserOut(BaseModel):
    id: int
    username: str
    email: str
    is_active: bool
    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str


# ─── Server ─────────────────────────────────────
class ServerCreate(BaseModel):
    name: str
    ip_address: str
    os_type: str
    web_server: str
    ssh_username: str
    ssh_password: Optional[str] = None
    ssh_key_path: Optional[str] = None
    ssh_port: int = 22

class ServerOut(BaseModel):
    id: int
    name: str
    ip_address: str
    os_type: str
    web_server: str
    status: str
    last_scanned: Optional[datetime]
    created_at: datetime
    class Config:
        from_attributes = True


# ─── Project ────────────────────────────────────
class ProjectOut(BaseModel):
    id: int
    name: str
    path: str
    size_mb: float
    last_modified: Optional[datetime]
    domain: Optional[str]
    dns_points_here: bool
    web_config_active: bool
    status: str
    server_id: int
    created_at: datetime
    class Config:
        from_attributes = True


# ─── Cleanup ────────────────────────────────────
class CleanupLogOut(BaseModel):
    id: int
    project_name: str
    server_name: str
    action: str
    performed_by: str
    performed_at: datetime
    class Config:
        from_attributes = True