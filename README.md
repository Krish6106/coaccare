# CoachCare

CoachCare is a software-only railway maintenance intelligence prototype. It links synthetic inspection findings, passenger feedback, repair records and work orders to help depot teams identify repeat defects, prioritize work and verify repairs. The application does not connect to railway systems or physical sensors.

## Requirements

- Node.js 20 or newer and npm
- Python 3.10 or newer

## Start the application

In one terminal, start the FastAPI service:

```bash
cd backend
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

In a second terminal, start the React client from the project root:

```bash
npm install
cp .env.example .env              # Windows: copy .env.example .env
npm run dev
```

Open the local URL printed by Vite (usually `http://localhost:5173`). The API is available at `http://localhost:8000/api`; interactive API documentation is at `http://localhost:8000/docs`.

The backend creates and seeds `backend/coachcare.db` automatically on first start. The records and activity are synthetic and are labeled as demo data in the UI. To reset the demo dataset, stop the API, delete `backend/coachcare.db`, and start the API again.

## Demo account

The prototype opens directly into the demo workspace and does not enforce sign-in. The profile shown in the interface is:

- **Name:** Arjun Sharma
- **Role:** Maintenance Engineer
- **Demo username:** `maintainer@coachcare.demo`
- **Demo password:** `CoachCare-Demo-2026`

The username and password are display/demo credentials only; no authentication service is configured.

## Main workflows

- **Overview:** database-derived defect and work KPIs, category and trend charts, priority distribution, recent activity and repeat defects requiring attention.
- **Recurring Defects:** repeat patterns grouped by coach, category and location, filterable history, repair context and a demo defect intake form.
- **Maintenance Priorities:** filter the task queue, assign a depot team and update task status. Severity, recurrence and resource readiness are visible alongside each recommendation.
- **Repair Verification:** review completed work, record a depot outcome and capture test notes. Failed or recurring outcomes reopen the associated defect record.

## Configuration

Copy `.env.example` to `.env` and set `VITE_API_URL` if the API is hosted elsewhere. The backend reads `DATABASE_URL`; SQLite is the default and can be replaced by a PostgreSQL SQLAlchemy URL for a later deployment.
# coaccare
