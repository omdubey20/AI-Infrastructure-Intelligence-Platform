from sqlalchemy import Column, Integer, String, DateTime, Boolean, Float, Text, ForeignKey
from sqlalchemy.orm import relationship
from database import Base
from datetime import datetime

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class Server(Base):
    __tablename__ = "servers"

    id = Column(Integer, primary_key=True, index=True)
    name = Column (String, unique=True, index=True)
    ip_address = Column(String)
    os_type = Column(String)  # Ubuntu, CentOS, AlmaLinux, Windows
    web_server = Column(String)  # Nginx, Apache, IIS
    ssh_username = Column(String)
    ssh_password = Column(String, nullable=True)
    ssh_key_path = Column(String, nullable=True)
    ssh_port = Column(Integer, default=22)
    status = Column(String, default="unknown")  # online, offline, unknown
    last_scanned = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    projects = relationship("Project", back_populates="server")


class Project(Base):
    __tablename__ = "projects"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    path = Column(String)
    size_mb = Column(Float, default=0)
    last_modified = Column(DateTime, nullable=True)
    last_accessed = Column(DateTime, nullable=True)
    domain = Column(String, nullable=True)
    dns_points_here = Column(Boolean, default=False)
    web_config_active = Column(Boolean, default=False)
    status = Column(String, default="unknown")  # live, duplicate, unused, archive
    server_id = Column(Integer, ForeignKey("servers.id"))
    created_at = Column(DateTime, default=datetime.utcnow)
    notes = Column(Text, nullable=True)

    server = relationship("Server", back_populates="projects")


class CleanupLog(Base):
    __tablename__ = "cleanup_logs"

    id = Column(Integer, primary_key=True, index=True)
    project_name = Column(String)
    server_name = Column(String)
    action = Column(String)  # deleted, archived, kept
    performed_by = Column(String)
    performed_at = Column(DateTime, default=datetime.utcnow)
    notes = Column(Text, nullable=True)