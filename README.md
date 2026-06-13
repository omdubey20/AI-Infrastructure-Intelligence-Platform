# AI Infrastructure Intelligence Platform

> Enterprise-grade server management and cleanup automation — FastAPI · React · PostgreSQL · APScheduler

## Features
- JWT authentication with bcrypt
- SSH-based server discovery (Paramiko)
- Automated risk scoring for idle servers
- Nightly APScheduler scans
- Live dashboard with Recharts
- Project-to-server mapping with DNS tracking
- Cleanup request workflow

## Tech Stack
**Backend:** FastAPI · PostgreSQL · SQLAlchemy · APScheduler · Paramiko · JWT  
**Frontend:** React · Axios · Recharts · React Router

## Quick Start
```bash
# Backend
cd backend && source venv/bin/activate
uvicorn main:app --reload

# Frontend
cd frontend && npm install && npm start
```

## API Endpoints
| Method | Endpoint | Description |
|---|---|---|
| POST | /auth/login | Get JWT token |
| GET | /stats/dashboard | Live dashboard stats |
| POST | /discovery/scan | Trigger SSH scan |
| GET | /servers | All servers |
| GET | /projects | All projects |
