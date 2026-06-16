readme = """# AI Infrastructure Intelligence Platform

> A production-grade server management and cleanup automation system built for real-world infrastructure teams.

## Problem Statement

Managing 10+ servers with 47 deployed projects across environments leads to:
- Duplicate projects wasting disk space and causing confusion
- Unused 3-year-old deployments nobody knows about
- No central visibility into what's running where
- Manual cleanup that's error-prone and time-consuming

## Solution

A unified SaaS-like dashboard that replaces 7 separate tools (Ansible, NetBox, Zabbix, Prometheus, Grafana, Rundeck, AWX) with one system.

## Features

| Feature | Description |
|---|---|
| JWT Authentication | Secure login with bcrypt password hashing |
| SSH Server Discovery | Auto-discovers projects via Paramiko SSH |
| Risk Scoring Engine | Scores servers based on CPU/memory/disk/errors |
| Duplicate Detection | Fuzzy string matching with confidence score |
| DNS Live Check | Identifies which projects are actually live |
| Nightly Automation | APScheduler runs scans every night at 2 AM |
| Cleanup Workflow | Approve/Archive/Keep with audit trail |
| Live Dashboard | Recharts bar + donut charts, real-time data |

## Tech Stack

**Backend:** FastAPI · PostgreSQL · SQLAlchemy · APScheduler · Paramiko · bcrypt · JWT  
**Frontend:** React 18 · Axios · Recharts · React Router  
**Infrastructure:** GitHub · Uvicorn · python-dotenv

## Architecture
React Frontend (Dashboard, Servers, Projects, Cleanup)
↓ Axios + JWT
FastAPI Backend (/auth, /servers, /projects, /discovery, /cleanup, /stats)
↓ SQLAlchemy ORM
PostgreSQL Database
↓ APScheduler (nightly 2 AM)
SSH Discovery via Paramiko → 10 Remote Servers

## Quick Start

### Backend
```bash
cd backend
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

### Frontend
```bash
cd frontend
npm install && npm start
```

### Environment Variables (`backend/.env`)
DATABASE_URL=postgresql://user:password@localhost/serverdb
SECRET_KEY=your-secret-key
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=1440

## API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| POST | /auth/login | Get JWT token |
| GET | /auth/me | Current user info |
| GET | /stats/dashboard | Live dashboard stats |
| POST | /discovery/scan | Trigger SSH scan |
| GET | /servers | All servers |
| GET | /projects | All projects |
| GET | /cleanup/report | Cleanup recommendations |
| POST | /cleanup/approve/{id} | Approve action |

## Interview Talking Points

- **Data Pipeline:** Collect → Store → Analyze → Visualize → Act
- **Pattern Detection:** Fuzzy duplicate detection, risk scoring, anomaly flagging  
- **Automation:** APScheduler nightly jobs, no human intervention needed
- **Security:** JWT, bcrypt, Fernet encryption for SSH credentials, CORS
- **System Design:** Full-stack, production-grade, real business problem

## Author

Built by Om Dubey as part of an AI/ML Engineering internship portfolio.  
Demonstrates full-stack systems design, backend automation, and infrastructure intelligence.
"""
