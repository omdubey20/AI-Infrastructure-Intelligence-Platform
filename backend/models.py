from datetime import datetime

from sqlalchemy import (
    Column,
    Integer,
    String,
    Boolean,
    DateTime,
    ForeignKey
)

from sqlalchemy.orm import relationship

from database import Base


# ==================================================
# USERS
# ==================================================

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)

    username = Column(
        String,
        unique=True,
        index=True,
        nullable=False
    )

    email = Column(
        String,
        unique=True,
        nullable=True
    )

    hashed_password = Column(
        String,
        nullable=False
    )

    is_active = Column(
        Boolean,
        default=True
    )

    role = Column(
        String,
        default="viewer"
    )


# ==================================================
# SERVERS
# ==================================================

class Server(Base):
    __tablename__ = "servers"

    id = Column(Integer, primary_key=True, index=True)

    name = Column(
        String,
        index=True,
        nullable=False
    )

    ip_address = Column(
        String,
        unique=True,
        index=True,
        nullable=False
    )

    environment = Column(
        String,
        default="production"
    )

    status = Column(
        String,
        default="active"
    )

    description = Column(
        String,
        nullable=True
    )

    created_at = Column(
        DateTime,
        default=datetime.utcnow
    )

    cpu_usage = Column(Integer, default=0)
    memory_usage = Column(Integer, default=0)
    disk_usage = Column(Integer, default=0)
    error_count = Column(Integer, default=0)
    uptime_days = Column(Integer, default=0)
    risk_score = Column(Integer, default=0)

    projects = relationship(
        "Project",
        back_populates="server"
    )

    discoveries = relationship(
        "ProjectDiscovery",
        back_populates="server"
    )


# ==================================================
# PROJECTS
# ==================================================

class Project(Base):
    __tablename__ = "projects"

    id = Column(Integer, primary_key=True, index=True)

    name = Column(
        String,
        index=True,
        nullable=False
    )

    description = Column(
        String,
        nullable=True
    )

    status = Column(
        String,
        default="active"
    )

    server_id = Column(
        Integer,
        ForeignKey("servers.id"),
        nullable=True
    )

    created_at = Column(
        DateTime,
        default=datetime.utcnow
    )

    risk_score = Column(
        Integer,
        default=0
    )

    server = relationship(
        "Server",
        back_populates="projects"
    )


# ==================================================
# PROJECT DISCOVERIES
# ==================================================

class ProjectDiscovery(Base):
    __tablename__ = "project_discoveries"

    id = Column(Integer, primary_key=True, index=True)

    server_id = Column(
        Integer,
        ForeignKey("servers.id")
    )

    project_name = Column(
        String,
        nullable=False
    )

    project_path = Column(
        String,
        nullable=False
    )

    size_mb = Column(
        Integer,
        default=0
    )

    domain = Column(
        String,
        nullable=True
    )

    dns_points_here = Column(
        Boolean,
        default=False
    )

    web_config_active = Column(
        Boolean,
        default=False
    )

    risk_score = Column(
        Integer,
        default=0
    )

    created_at = Column(
        DateTime,
        default=datetime.utcnow
    )

    server = relationship(
        "Server",
        back_populates="discoveries"
    )

# ==================================================
# SCAN LOGS (history for ML training)
# ==================================================

class ScanLog(Base):
    __tablename__ = "scan_logs"

    id = Column(Integer, primary_key=True, index=True)

    server_id = Column(
        Integer,
        ForeignKey("servers.id")
    )

    cpu_usage = Column(Integer, default=0)
    memory_usage = Column(Integer, default=0)
    disk_usage = Column(Integer, default=0)
    error_count = Column(Integer, default=0)
    uptime_days = Column(Integer, default=0)
    risk_score = Column(Integer, default=0)

    status = Column(String, default="active")

    scanned_at = Column(
        DateTime,
        default=datetime.utcnow
    )