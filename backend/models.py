"""
Enterprise AI Infrastructure Intelligence Platform
Database Models - Expanded Schema
"""
from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Boolean, DateTime,
    ForeignKey, Float, Text, BigInteger, Index
)
from sqlalchemy.orm import relationship
from database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    email = Column(String, unique=True, nullable=True)
    hashed_password = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)
    role = Column(String, default="viewer")  # admin, devops, viewer
    created_at = Column(DateTime, default=datetime.utcnow)
    last_login = Column(DateTime, nullable=True)

    audit_logs = relationship("AuditLog", back_populates="user")


class Server(Base):
    __tablename__ = "servers"
    __table_args__ = (
        Index("ix_servers_status", "status"),
        Index("ix_servers_environment", "environment"),
    )

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True, nullable=False)
    ip_address = Column(String, unique=True, index=True, nullable=False)
    environment = Column(String, default="production")
    status = Column(String, default="active")
    description = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # --- System Info (from SSH) ---
    hostname = Column(String, nullable=True)
    os_name = Column(String, nullable=True)
    os_version = Column(String, nullable=True)
    kernel = Column(String, nullable=True)
    architecture = Column(String, nullable=True)
    timezone = Column(String, nullable=True)

    # --- Hardware ---
    cpu_cores = Column(Integer, nullable=True)
    cpu_model = Column(String, nullable=True)
    ram_total_gb = Column(Float, default=0.0)
    swap_total_gb = Column(Float, default=0.0)
    disk_total_gb = Column(Float, default=0.0)

    # --- Live Metrics (updated every scan) ---
    cpu_usage = Column(Integer, default=0)
    memory_usage = Column(Integer, default=0)
    disk_usage = Column(Integer, default=0)
    swap_usage = Column(Integer, default=0)
    load_avg_1 = Column(Float, default=0.0)
    load_avg_5 = Column(Float, default=0.0)
    load_avg_15 = Column(Float, default=0.0)
    uptime_days = Column(Integer, default=0)
    error_count = Column(Integer, default=0)
    risk_score = Column(Integer, default=0)

    # --- Services ---
    web_server = Column(String, nullable=True)  # nginx, apache, none
    db_engines = Column(String, nullable=True)  # mysql,postgresql,redis
    docker_installed = Column(Boolean, default=False)
    docker_containers_running = Column(Integer, default=0)
    docker_images_count = Column(Integer, default=0)
    firewall_status = Column(String, nullable=True)
    selinux_status = Column(String, nullable=True)

    # --- Software Versions ---
    php_versions = Column(String, nullable=True)    # comma-separated
    node_versions = Column(String, nullable=True)
    python_versions = Column(String, nullable=True)
    java_versions = Column(String, nullable=True)

    # --- Network ---
    open_ports = Column(Text, nullable=True)        # JSON list
    running_services = Column(Text, nullable=True)  # JSON list
    network_interfaces = Column(Text, nullable=True)

    # --- Security ---
    ssl_expiry_days = Column(Integer, nullable=True)
    ssh_status = Column(String, nullable=True)

    # --- WHM / cPanel ---
    whm_host = Column(String, nullable=True)
    whm_token = Column(String, nullable=True)   # Fernet encrypted
    whm_port = Column(Integer, default=2087)
    whm_accounts_count = Column(Integer, default=0)

    # --- SSH Credentials ---
    ssh_username = Column(String, nullable=True)
    ssh_password = Column(String, nullable=True)    # Fernet encrypted
    ssh_private_key = Column(String, nullable=True) # Fernet encrypted
    ssh_port = Column(Integer, default=22)
    credentials_encrypted = Column(Boolean, default=False)

    # --- Scan State ---
    data_source = Column(String, default="estimated")  # agent, ssh, whm, estimated
    last_scanned_at = Column(DateTime, nullable=True)
    last_full_scan_at = Column(DateTime, nullable=True)
    scan_status = Column(String, default="never_scanned")  # scanning, success, error, never_scanned
    scan_error = Column(Text, nullable=True)

    # --- Agent ---
    agent_api_key = Column(String, nullable=True, unique=True)
    agent_installed = Column(Boolean, default=False)
    agent_last_seen = Column(DateTime, nullable=True)

    # --- AI ---
    ai_risk_confidence = Column(Float, default=0.0)
    ai_recommendation = Column(String, nullable=True)

    # Relationships
    projects = relationship("Project", back_populates="server")
    discoveries = relationship("ProjectDiscovery", back_populates="server", cascade="all, delete-orphan")
    scan_jobs = relationship("ScanJob", back_populates="server")
    ai_insights = relationship("AIInsight", back_populates="server")


class Project(Base):
    """Legacy project table - kept for backward compat, primary data is ProjectDiscovery."""
    __tablename__ = "projects"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True, nullable=False)
    description = Column(String, nullable=True)
    status = Column(String, default="active")
    server_id = Column(Integer, ForeignKey("servers.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    risk_score = Column(Integer, default=0)
    server = relationship("Server", back_populates="projects")


class ProjectDiscovery(Base):
    __tablename__ = "project_discoveries"
    __table_args__ = (
        Index("ix_pd_server_name", "server_id", "project_name"),
        Index("ix_pd_domain", "domain"),
        Index("ix_pd_is_live", "is_live"),
        Index("ix_pd_is_duplicate", "is_duplicate"),
    )

    id = Column(Integer, primary_key=True, index=True)
    server_id = Column(Integer, ForeignKey("servers.id"))

    # --- Identity ---
    project_name = Column(String, nullable=False, index=True)
    project_path = Column(String, nullable=False)
    domain = Column(String, nullable=True, index=True)
    owner = Column(String, nullable=True)

    # --- Framework & Tech ---
    framework = Column(String, nullable=True)       # laravel, wordpress, react, django, etc.
    language = Column(String, nullable=True)        # php, python, javascript, java, etc.
    php_version = Column(String, nullable=True)
    node_version = Column(String, nullable=True)
    python_version = Column(String, nullable=True)
    database_used = Column(String, nullable=True)   # mysql, postgresql, etc.
    web_server = Column(String, nullable=True)      # nginx, apache
    git_remote = Column(String, nullable=True)
    git_branch = Column(String, nullable=True)

    # --- Size & Activity ---
    size_mb = Column(Integer, default=0)
    last_modified = Column(DateTime, nullable=True)
    last_accessed = Column(DateTime, nullable=True)
    days_since_modified = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)

    # --- Health & Status ---
    dns_points_here = Column(Boolean, default=False)
    web_config_active = Column(Boolean, default=False)
    has_ssl = Column(Boolean, default=False)
    ssl_expiry_days = Column(Integer, nullable=True)
    is_live = Column(Boolean, default=False)        # actively serving production traffic
    env_type = Column(String, default="unknown")    # live, staging, dev, backup, duplicate, archive, unknown
    http_status = Column(Integer, nullable=True)    # HTTP response code

    # --- Duplicate Detection ---
    is_duplicate = Column(Boolean, default=False)
    duplicate_of_id = Column(Integer, ForeignKey("project_discoveries.id"), nullable=True)
    duplicate_confidence = Column(Integer, default=0)  # 0-100
    duplicate_signals = Column(Text, nullable=True)    # JSON: matched signals

    # --- Inactivity ---
    is_inactive = Column(Boolean, default=False)    # > 3 years unused
    inactivity_signals = Column(Text, nullable=True) # JSON: signals detected

    # --- AI / ML ---
    risk_score = Column(Integer, default=0)
    ai_confidence = Column(Float, default=0.0)
    recommendation = Column(String, default="keep")  # keep, archive, delete

    # --- User Action Override (persisted — survives restart) ---
    user_override = Column(String, nullable=True)   # keep, archive, delete

    # --- Meta ---
    data_source = Column(String, default="estimated")  # ssh, whm_estimated, estimated
    last_synced_at = Column(DateTime, nullable=True)


    # Relationships
    server = relationship("Server", back_populates="discoveries")
    duplicate_of = relationship("ProjectDiscovery", remote_side=[id])


class AuditLog(Base):
    __tablename__ = "audit_logs"
    __table_args__ = (
        Index("ix_audit_user", "user_id"),
        Index("ix_audit_action", "action"),
        Index("ix_audit_created", "created_at"),
    )

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    action = Column(String, nullable=False)          # scan, cleanup, login, create_server, delete_project, etc.
    entity_type = Column(String, nullable=True)      # server, project, discovery
    entity_id = Column(Integer, nullable=True)
    entity_name = Column(String, nullable=True)
    details = Column(Text, nullable=True)            # JSON details
    ip_address = Column(String, nullable=True)
    status = Column(String, default="success")       # success, error
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="audit_logs")


class ScanJob(Base):
    __tablename__ = "scan_jobs"

    id = Column(Integer, primary_key=True, index=True)
    server_id = Column(Integer, ForeignKey("servers.id"), nullable=True)
    triggered_by = Column(String, default="scheduler")  # scheduler, manual, api
    data_source = Column(String, nullable=True)
    status = Column(String, default="running")       # running, success, error
    projects_found = Column(Integer, default=0)
    projects_updated = Column(Integer, default=0)
    projects_removed = Column(Integer, default=0)
    error_message = Column(Text, nullable=True)
    started_at = Column(DateTime, default=datetime.utcnow)
    finished_at = Column(DateTime, nullable=True)
    duration_seconds = Column(Float, nullable=True)

    server = relationship("Server", back_populates="scan_jobs")


class AIInsight(Base):
    __tablename__ = "ai_insights"
    __table_args__ = (
        Index("ix_insight_server", "server_id"),
        Index("ix_insight_severity", "severity"),
        Index("ix_insight_category", "category"),
    )

    id = Column(Integer, primary_key=True, index=True)
    server_id = Column(Integer, ForeignKey("servers.id"), nullable=True)
    project_id = Column(Integer, ForeignKey("project_discoveries.id"), nullable=True)
    category = Column(String, nullable=False)        # resource, security, duplicate, inactive, ssl, optimization
    severity = Column(String, default="info")        # critical, warning, info
    title = Column(String, nullable=False)
    description = Column(Text, nullable=False)
    recommendation = Column(Text, nullable=True)
    is_resolved = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    resolved_at = Column(DateTime, nullable=True)

    server = relationship("Server", back_populates="ai_insights")


class MLRun(Base):
    __tablename__ = "ml_runs"

    id = Column(Integer, primary_key=True, index=True)
    run_id = Column(String, nullable=True, unique=True)
    experiment_name = Column(String, nullable=True)
    model_version = Column(Integer, default=1)
    n_estimators = Column(Integer, nullable=True)
    max_depth = Column(Integer, nullable=True)
    learning_rate = Column(Float, nullable=True)
    rmse = Column(Float, nullable=True)
    mae = Column(Float, nullable=True)
    r2_score = Column(Float, nullable=True)
    feature_importance = Column(Text, nullable=True)  # JSON
    drift_detected = Column(Boolean, default=False)
    training_samples = Column(Integer, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class HealthSnapshot(Base):
    __tablename__ = "health_snapshots"
    __table_args__ = (
        Index("ix_hs_server", "server_id"),
        Index("ix_hs_recorded", "recorded_at"),
    )

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    server_id = Column(Integer, ForeignKey("servers.id"), nullable=True)
    site_id = Column(Integer, ForeignKey("project_discoveries.id"), nullable=True)
    metric = Column(String(50), nullable=False)   # loadavg, cpu_usage, memory_usage, disk_usage, http_status
    value = Column(String(50), nullable=False)    # Stored as string, cast on read
    recorded_at = Column(DateTime, default=datetime.utcnow, index=True)

    server = relationship("Server")
    site = relationship("ProjectDiscovery")


class Alert(Base):
    __tablename__ = "alerts"
    __table_args__ = (
        Index("ix_alerts_server", "server_id"),
        Index("ix_alerts_resolved", "is_resolved"),
        Index("ix_alerts_severity", "severity"),
    )

    id = Column(Integer, primary_key=True, index=True)
    server_id = Column(Integer, ForeignKey("servers.id"), nullable=True)
    site_id = Column(Integer, ForeignKey("project_discoveries.id"), nullable=True)
    type = Column(String(50), nullable=False)     # site_down, disk_high, cpu_high, memory_high, ssl_expiring, malware, agent_offline
    severity = Column(String(20), default="warning") # info, warning, critical
    message = Column(String(500), nullable=False)
    is_resolved = Column(Boolean, default=False)
    notification_sent = Column(Boolean, default=False)
    teams_sent_at = Column(DateTime, nullable=True)
    whatsapp_sent_at = Column(DateTime, nullable=True)
    email_sent_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    resolved_at = Column(DateTime, nullable=True)

    server = relationship("Server")
    site = relationship("ProjectDiscovery")


class UptimeCheck(Base):
    __tablename__ = "uptime_checks"
    __table_args__ = (
        Index("ix_uc_site", "site_id"),
        Index("ix_uc_checked", "checked_at"),
    )

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    site_id = Column(Integer, ForeignKey("project_discoveries.id"), nullable=True)
    server_id = Column(Integer, ForeignKey("servers.id"), nullable=True)
    url = Column(String(500), nullable=False)
    is_up = Column(Boolean, default=True)
    http_status = Column(Integer, nullable=True)
    response_time_ms = Column(Integer, nullable=True)
    error_message = Column(String(500), nullable=True)
    ssl_valid = Column(Boolean, nullable=True)
    ssl_expiry_days = Column(Integer, nullable=True)
    checked_at = Column(DateTime, default=datetime.utcnow, index=True)

    site = relationship("ProjectDiscovery")
    server = relationship("Server")


class MalwareAlert(Base):
    __tablename__ = "malware_alerts"
    __table_args__ = (
        Index("ix_mal_server", "server_id"),
        Index("ix_mal_resolved", "is_resolved"),
    )

    id = Column(Integer, primary_key=True, index=True)
    server_id = Column(Integer, ForeignKey("servers.id"), nullable=True)
    site_id = Column(Integer, ForeignKey("project_discoveries.id"), nullable=True)
    file_path = Column(String(500), nullable=True)
    threat_type = Column(String(100), nullable=False)  # php_shell, base64_injection, suspicious_cron, suid_binary, clamav_hit
    severity = Column(String(20), default="critical")
    details = Column(Text, nullable=True)
    is_resolved = Column(Boolean, default=False)
    detected_at = Column(DateTime, default=datetime.utcnow, index=True)
    resolved_at = Column(DateTime, nullable=True)

    server = relationship("Server")
    site = relationship("ProjectDiscovery")


class AlertConfig(Base):
    __tablename__ = "alert_configs"

    id = Column(Integer, primary_key=True, index=True)
    teams_webhook_url = Column(String(500), nullable=True)
    whatsapp_enabled = Column(Boolean, default=True)
    whatsapp_user_phone = Column(String(50), nullable=True)
    whatsapp_group_id = Column(String(100), nullable=True)
    whatsapp_provider = Column(String(50), default="callmebot")
    whatsapp_api_key = Column(String(255), nullable=True)
    whatsapp_gateway_url = Column(String(500), nullable=True)
    whatsapp_account_sid = Column(String(100), nullable=True)
    whatsapp_from_phone = Column(String(50), nullable=True)
    email_to = Column(String(255), nullable=True)
    smtp_host = Column(String(255), nullable=True)
    smtp_port = Column(Integer, default=587)
    smtp_user = Column(String(255), nullable=True)
    smtp_password = Column(String(255), nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)