# ReferralDesk — Local Milestone Build

Healthcare referral operations platform. This is the **local-only** version required
for Milestone 1: a working front end + application layer + data store, with local
stand-ins for the AWS services you'll swap in later.

| Layer | This milestone (local) | Later (cloud) |
|---|---|---|
| Front end | React (Vite) kanban dashboard | Same, deployed to S3/CloudFront or similar |
| Application layer | FastAPI | Same, containerized on ECS/Fargate or EC2 |
| Relational data | PostgreSQL (Docker) | Amazon RDS / Aurora PostgreSQL |
| Document storage | Local filesystem (`backend/uploads/`) | Amazon S3 |
| Async matching + SLA escalation | Python `asyncio.Queue` + background task inside FastAPI | Amazon SQS + AWS Lambda (or worker on ECS) |
| External EHR integration | Standalone Mock EHR FastAPI service | Real EHR/FHIR API |

The three technical dimensions this project demonstrates: **relational data
modeling**, **unstructured file processing**, and **async/traffic-spike handling**.

---

## 1. Prerequisites (install these first)

| Tool | Why | Link |
|---|---|---|
| Python 3.11+ | Backend + Mock EHR | https://www.python.org/downloads/ |
| Node.js 18+ and npm | React frontend | https://nodejs.org/en/download |
| Docker Desktop | Runs local PostgreSQL | https://www.docker.com/products/docker-desktop/ |
| Git | Clone/version the project | https://git-scm.com/downloads |
| A code editor (VS Code recommended) | — | https://code.visualstudio.com/ |

---

## 2. Start PostgreSQL (Docker)

```bash
cd referraldesk
docker compose up -d
```

This starts Postgres on `localhost:5432` with database `referraldesk`,
user `referraldesk`, password `referraldesk` (see `docker-compose.yml`).

Docker Compose reference: https://docs.docker.com/compose/

---

## 3. Start the Mock EHR service (port 9000)

```bash
cd mock_ehr
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --reload --port 9000
```

Test it: open http://localhost:9000/patients/EHR-1001 — you should see a JSON
patient record. This simulates the external EHR system ReferralDesk integrates with.

---

## 4. Start the backend API (port 8000)

In a **new terminal**:

```bash
cd backend
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env            # defaults already match docker-compose
python3 seed.py                 # loads sample patients/providers/plans
uvicorn main:app --reload --port 8000
```

Test it: open http://localhost:8000/docs — this is FastAPI's interactive Swagger
UI, generated automatically from the code (great for demoing the API in your
video). Reference: https://fastapi.tiangolo.com/

---

## 5. Start the frontend (port 5173)

In a **third terminal**:

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:5173 — the kanban dashboard. Create a referral, watch it
move from **New → Matching → Scheduled** automatically as the background worker
processes it (takes 1.5–3.5 seconds, simulating real async latency).

Click **"Simulate 10x burst"** to fire 10 referrals at once — this is your
traffic-spike / async proof for the demo: the dashboard stays responsive while
the queue drains in the background.

---

## Project structure

```
referraldesk/
├── docker-compose.yml        # local Postgres
├── backend/                  # FastAPI application
│   ├── main.py                # API routes
│   ├── models.py               # SQLAlchemy models (Patient, Provider, InsurancePlan, Referral, ReferralEvent, ReferralDocument)
│   ├── schemas.py             # Pydantic request/response schemas
│   ├── matching.py            # provider-ranking engine
│   ├── queue_worker.py        # async queue + SLA monitor (local SQS/Lambda stand-in)
│   ├── seed.py                 # sample data loader
│   └── uploads/                # uploaded referral documents (local S3 stand-in)
├── mock_ehr/                 # standalone Mock EHR microservice
└── frontend/                 # React (Vite) kanban dashboard
    └── src/
        ├── App.jsx
        ├── api.js
        └── components/
```

---

## Core user flow (for your video demo)

1. Coordinator clicks **New referral**, picks a patient + specialty.
2. Backend creates the referral (status `New` → `Matching`), logs a `CREATED`
   audit event, and enqueues a matching job instead of processing it inline.
3. Background worker (local SQS/Lambda stand-in) picks up the job, ranks
   in-network providers by specialty/availability/distance, and assigns the
   best match — status becomes `Scheduled`, an SLA due date is set.
4. Coordinator opens the referral detail panel to see the matched provider,
   upload a referral letter, and review the full audit trail.
5. If a referral passes its SLA window unresolved, the background SLA monitor
   escalates it to `Overdue` automatically.
6. `Simulate 10x burst` demonstrates the system absorbing a volume spike
   without blocking the API or freezing the dashboard.

---

## Reference links (docs used throughout this stack)

**Frontend**
- React docs: https://react.dev/
- Vite: https://vitejs.dev/guide/

**Backend**
- FastAPI: https://fastapi.tiangolo.com/
- SQLAlchemy ORM: https://docs.sqlalchemy.org/en/20/orm/quickstart.html
- Pydantic: https://docs.pydantic.dev/latest/
- Uvicorn: https://www.uvicorn.org/
- httpx (async HTTP client used to call the Mock EHR): https://www.python-httpx.org/

**Data store**
- PostgreSQL docs: https://www.postgresql.org/docs/
- psycopg2: https://www.psycopg.org/docs/

**Cloud services you'll migrate to in later milestones**
- Amazon RDS for PostgreSQL: https://aws.amazon.com/rds/postgresql/
- Amazon S3: https://aws.amazon.com/s3/
- Amazon SQS: https://aws.amazon.com/sqs/
- AWS Lambda: https://aws.amazon.com/lambda/
- Amazon EventBridge (for scheduled SLA sweeps): https://aws.amazon.com/eventbridge/

**Tooling**
- Docker Compose: https://docs.docker.com/compose/
- Git: https://git-scm.com/doc

---

## Troubleshooting

- **Frontend says "Can't reach the API"** — make sure `uvicorn main:app --port 8000`
  is running and `docker compose up -d` has Postgres up (`docker ps` to check).
- **`psycopg2.OperationalError: connection refused`** — Postgres isn't running yet;
  run `docker compose up -d` from the project root and wait a few seconds.
- **Referral stuck in `Matching` forever** — check the backend terminal log; if no
  eligible in-network provider exists for that specialty/plan combo, it's
  expected to stay in `Matching` (this is realistic — some referrals genuinely
  need manual coordinator intervention, which is the point of the dashboard).
- **CORS errors in browser console** — confirm the backend is on port 8000 and
  `frontend/src/api.js`'s `API_BASE` matches.
