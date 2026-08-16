# Physics Lab Schedule Agent System

> AI-powered assistant for university physics experiment scheduling: course arrangement, course selection consultation, class rescheduling, and lab tutoring.

[🇨🇳 中文版 README (Chinese)](README.zh.md)

---

## What is this?

A **four-module intelligent system** for university physics experiment teaching:

| Module | Capability |
|--------|-----------|
| 📅 **Scheduling** | Constraint-based auto-scheduling, conflict detection, candidate plan recommendation |
| 🎓 **Course Selection** | AI-powered Q&A on prerequisites, credits, eligibility |
| 🔄 **Rescheduling** | Template + natural language flow, conflict filtering, admin approval |
| 🔬 **Lab Tutoring** | AI-powered Q&A on experiment principles, data processing, error analysis |

**Design principle**: rule engine guarantees correctness (conflict filtering), LLM enhances experience (intent parsing, candidate plans, consultation).

## Why this project?

- Paper research shows lab courses are rarely handled by university academic systems — scheduling relies on manual coordination.
- One schedule adjustment can trigger conflicts across multiple classes, teachers, and labs.
- Existing tools (Excel, asking class representatives) cannot efficiently resolve cross-class conflicts.

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python FastAPI + openpyxl + python-constraint |
| Frontend | React + Vite + TypeScript + Tailwind CSS |
| LLM | TokenRhythm (OpenAI-compatible) / replaceable via env vars |
| Data | Excel schedule (433 entries) + student timetable |

## Quick Start

### Requirements

- Python 3.10+
- Node.js 18+
- Environment variables: `JIYUAN_LVDONG_BASE_URL`, `JIYUAN_LVDONG_API_KEY` (LLM credentials)

### Backend

```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Open **http://localhost:5173**

## Usage Flow

1. **Select identity** — pick your teacher card (system knows who you are)
2. **My courses** — view all courses with adjustable/non-adjustable status
3. **Template rescheduling** — select course + target week, auto conflict filtering
4. **Results** — green available slots + gray excluded slots with reasons + AI candidate plans
5. **Submit** — create reschedule request
6. **Admin approval** — approve/reject (requires admin login)
7. **Course selection / Lab tutoring** — ask AI questions with knowledge context

## Key Features

- ✅ **Three-way conflict filtering**: classroom / student timetable / teacher time
- ✅ **Reason transparency**: every excluded slot shows why
- ✅ **Natural language**: "I'm teacher Wu, move next week's class" → LLM intent parsing
- ✅ **Multi-turn follow-up**: system asks for missing info
- ✅ **SQLite persistence**: reschedule requests survive restart
- ✅ **13 unit tests** covering scheduling logic

## Project Structure

```
physics-scheduler-agent/
├── backend/
│   ├── app/
│   │   ├── main.py                 # FastAPI entry
│   │   ├── api/reschedule.py       # API endpoints
│   │   ├── agent/                  # RescheduleAgent, LLM parser, student schedule
│   │   ├── engine/                 # Constraint-based auto scheduler
│   │   └── utils/                  # Excel/PDF parsers
│   ├── tests/test_reschedule.py    # pytest unit tests
│   └── requirements.txt
├── frontend/
│   └── src/                        # React UI (4 modules)
├── scripts/prepare_demo.py         # One-click demo data prep
├── docs/                           # PRD, architecture, user guide, reflection
└── start.ps1 / start.bat           # One-click launcher
```

## API Overview

| Method | Path | Module | Description |
|--------|------|--------|-------------|
| POST | `/api/reschedule/upload` | Scheduling | Upload experiment schedule Excel |
| GET | `/api/reschedule/teachers` | Scheduling | Teacher list (identity selection) |
| GET | `/api/reschedule/teachers/{name}/courses` | Scheduling | Teacher's courses |
| POST | `/api/reschedule/auto-schedule` | Scheduling | Auto schedule generation |
| POST | `/api/reschedule/chat` | Rescheduling | Reschedule query (available + excluded + AI plans) |
| POST | `/api/reschedule/requests` | Rescheduling | Submit reschedule request |
| POST | `/api/reschedule/requests/{id}/approve` | Rescheduling | Admin approval |
| POST | `/api/reschedule/admin-login` | Auth | Admin login (approval desk) |
| POST | `/api/reschedule/course-select` | Selection | Course selection Q&A (LLM) |
| POST | `/api/reschedule/experiment-tutor` | Tutoring | Lab tutoring Q&A (LLM) |
| GET | `/health` | - | Health check |

## Tests

```bash
cd backend
python -m pytest tests/ -v
```

## Roadmap

- [ ] Conflict impact analysis ("who will this adjustment affect")
- [ ] Visual schedule grid (weekly timetable view)
- [ ] Data import wizard (field mapping for different schools)
- [ ] Multi-school data isolation
- [ ] RAG knowledge base for lab materials

## Documentation

- [中文 README (Chinese)](README.zh.md)
- [PRD V1.0 (Chinese)](docs/PRD-V1.0.md)
- [Technical Architecture V1.0 (Chinese)](docs/技术架构设计文档-V1.0.md)
- [User Guide (Chinese)](docs/产品使用指南.md)
- [Project Reflection (Chinese)](docs/项目总结与反思.md)
