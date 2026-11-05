import asyncio
import os
import shutil
from datetime import datetime

import httpx
import gcs_storage
from fastapi import FastAPI, Depends, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from database import Base, engine, get_db
from models import (
    Patient, Provider, InsurancePlan, Referral, ReferralEvent,
    ReferralDocument, ReferralStatus,
)
from schemas import ReferralOut, ReferralCreate, ReferralStatusUpdate, ProviderOut, PatientOut
from queue_worker import enqueue_job, worker_loop, sla_monitor_loop

MOCK_EHR_URL = os.getenv("MOCK_EHR_URL", "http://localhost:9000")
UPLOAD_DIR = os.getenv("UPLOAD_DIR", "./uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)


app = FastAPI(title="ReferralDesk API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # fine for local dev; tighten before any real deployment
    allow_methods=["*"],
    allow_headers=["*"],
)

background_tasks = []


@app.on_event("startup")
async def start_background_workers():
    # These two loops are the local equivalent of an SQS-triggered Lambda
    # and a scheduled EventBridge/Lambda SLA sweep.
    background_tasks.append(asyncio.create_task(worker_loop()))
    background_tasks.append(asyncio.create_task(sla_monitor_loop()))


# ---------- Reference data ----------

@app.get("/api/patients", response_model=list[PatientOut])
def list_patients(db: Session = Depends(get_db)):
    return db.query(Patient).all()


@app.get("/api/providers", response_model=list[ProviderOut])
def list_providers(db: Session = Depends(get_db)):
    return db.query(Provider).all()


# ---------- Mock EHR integration ----------

@app.get("/api/ehr/patients/{ehr_patient_id}")
async def fetch_from_mock_ehr(ehr_patient_id: str):
    """
    Calls the separate Mock EHR service to demonstrate integrating with an
    external healthcare information system (a stand-in for a real EHR/FHIR API).
    """
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(f"{MOCK_EHR_URL}/patients/{ehr_patient_id}", timeout=5.0)
        except httpx.RequestError:
            raise HTTPException(status_code=502, detail="Mock EHR service unreachable")
    if resp.status_code != 200:
        raise HTTPException(status_code=404, detail="Patient not found in Mock EHR")
    return resp.json()


# ---------- Referrals ----------

@app.get("/api/referrals", response_model=list[ReferralOut])
def list_referrals(db: Session = Depends(get_db)):
    return db.query(Referral).order_by(Referral.created_at.desc()).all()


@app.get("/api/referrals/{referral_id}", response_model=ReferralOut)
def get_referral(referral_id: str, db: Session = Depends(get_db)):
    referral = db.query(Referral).filter(Referral.id == referral_id).first()
    if not referral:
        raise HTTPException(status_code=404, detail="Referral not found")
    return referral


@app.post("/api/referrals", response_model=ReferralOut)
async def create_referral(payload: ReferralCreate, db: Session = Depends(get_db)):
    patient = db.query(Patient).filter(Patient.id == payload.patient_id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    referral = Referral(
        patient_id=patient.id,
        specialty_requested=payload.specialty_requested,
        status=ReferralStatus.NEW,
        notes=payload.notes,
    )
    db.add(referral)
    db.commit()
    db.refresh(referral)

    db.add(ReferralEvent(
        referral_id=referral.id,
        event_type="CREATED",
        detail=f"Referral created for {patient.first_name} {patient.last_name} "
               f"requesting {payload.specialty_requested}.",
    ))
    referral.status = ReferralStatus.MATCHING
    db.add(ReferralEvent(
        referral_id=referral.id,
        event_type="QUEUED_FOR_MATCHING",
        detail="Enqueued to background matching worker (local SQS/Lambda stand-in).",
    ))
    db.commit()
    db.refresh(referral)

    # Hand off to the async worker instead of matching synchronously in this request.
    await enqueue_job({"type": "MATCH_REFERRAL", "referral_id": referral.id})

    return referral


@app.patch("/api/referrals/{referral_id}/status", response_model=ReferralOut)
def update_status(referral_id: str, payload: ReferralStatusUpdate, db: Session = Depends(get_db)):
    referral = db.query(Referral).filter(Referral.id == referral_id).first()
    if not referral:
        raise HTTPException(status_code=404, detail="Referral not found")

    try:
        new_status = ReferralStatus(payload.status)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid status value")

    old_status = referral.status
    referral.status = new_status
    db.add(ReferralEvent(
        referral_id=referral.id,
        event_type="STATUS_CHANGED",
        detail=f"Status changed from {old_status.value} to {new_status.value} by coordinator.",
    ))
    db.commit()
    db.refresh(referral)
    return referral


@app.post("/api/referrals/{referral_id}/documents", response_model=ReferralOut)
async def upload_document(referral_id: str, file: UploadFile = File(...), db: Session = Depends(get_db)):
    referral = db.query(Referral).filter(Referral.id == referral_id).first()
    if not referral:
        raise HTTPException(status_code=404, detail="Referral not found")

    dest_path = gcs_storage.save_upload(
        f"{referral_id}/{file.filename}", file.file, file.content_type
    )

    # storage_path today is a local path; swapping to S3 means storing the S3 key here instead.
    doc = ReferralDocument(
        referral_id=referral_id,
        file_name=file.filename,
        storage_path=dest_path,
        content_type=file.content_type,
    )
    db.add(doc)
    db.add(ReferralEvent(
        referral_id=referral_id,
        event_type="DOCUMENT_UPLOADED",
        detail=f"Document '{file.filename}' attached to referral.",
    ))
    db.commit()
    db.refresh(referral)
    return referral


# ---------- Load-test helper (for your traffic-spike demo) ----------

@app.post("/api/demo/simulate-burst")
async def simulate_burst(count: int, db: Session = Depends(get_db)):
    """
    Fires `count` referrals back-to-back for a random existing patient so you
    can film the dashboard staying responsive while the queue drains -- this
    is your local proof of the async/traffic-spike dimension.
    """
    patients = db.query(Patient).all()
    if not patients:
        raise HTTPException(status_code=400, detail="Seed patients first")

    created_ids = []
    for i in range(count):
        patient = patients[i % len(patients)]
        referral = Referral(
            patient_id=patient.id,
            specialty_requested="Cardiology",
            status=ReferralStatus.MATCHING,
        )
        db.add(referral)
        db.commit()
        db.refresh(referral)
        db.add(ReferralEvent(referral_id=referral.id, event_type="CREATED", detail="Burst-test referral."))
        db.commit()
        created_ids.append(referral.id)
        await enqueue_job({"type": "MATCH_REFERRAL", "referral_id": referral.id})

    return {"queued": len(created_ids), "referral_ids": created_ids}


@app.get("/api/health")
def health():
    return {"status": "ok", "time": datetime.utcnow().isoformat()}


# ---------- Kubernetes probes ----------
@app.get("/healthz")
def healthz():
    """Liveness: the process is up and serving requests.
    Deliberately checks nothing external, so a database outage never gets pods restarted."""
    return {"status": "alive"}


@app.get("/readyz")
def readyz():
    """Readiness: this pod can serve real traffic, which needs the database."""
    from sqlalchemy import text
    from fastapi.responses import JSONResponse
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except Exception:
        return JSONResponse(status_code=503, content={"status": "not ready", "database": "unreachable"})
    return {"status": "ready", "database": "ok"}


# ---------- Milestone 6: structured JSON logging, version, controlled fault ----------
import json
import logging
import sys
import time

from fastapi import Request
from fastapi.responses import JSONResponse


class JsonFormatter(logging.Formatter):
    """One JSON object per line. Cloud Logging reads 'severity' and 'message' from it."""
    def format(self, record):
        entry = {
            "severity": record.levelname,
            "message": record.getMessage(),
            "logger": record.name,
        }
        entry.update(getattr(record, "fields", {}))
        if record.exc_info:
            entry["exception"] = self.formatException(record.exc_info)
        return json.dumps(entry, default=str)


app_logger = logging.getLogger("referraldesk")
app_logger.setLevel(logging.INFO)
app_logger.propagate = False
if not app_logger.handlers:
    _handler = logging.StreamHandler(sys.stdout)
    _handler.setFormatter(JsonFormatter())
    app_logger.addHandler(_handler)

PROBE_PATHS = {"/healthz", "/readyz"}


@app.middleware("http")
async def log_requests(request: Request, call_next):
    start = time.time()
    status = 500
    try:
        response = await call_next(request)
        status = response.status_code
        return response
    finally:
        # Probes run every few seconds; skip them so they don't drown the real traffic.
        if request.url.path not in PROBE_PATHS:
            app_logger.log(
                logging.ERROR if status >= 500 else logging.INFO,
                "http_request",
                extra={"fields": {
                    "event": "http_request",
                    "method": request.method,
                    "path": request.url.path,
                    "status_code": status,
                    "duration_ms": round((time.time() - start) * 1000, 1),
                }},
            )


@app.get("/api/version")
def version():
    return {"version": os.getenv("APP_VERSION", "unknown")}


@app.get("/api/debug/error")
def controlled_error():
    """Deliberate 500 for the monitoring demo. Only active when ENABLE_FAULT_ENDPOINT=true."""
    if os.getenv("ENABLE_FAULT_ENDPOINT") != "true":
        return JSONResponse(status_code=404, content={"detail": "Not found"})
    return JSONResponse(status_code=500, content={"detail": "controlled test error"})


# --- M6: controlled failure switch for the rollback demo ---
from fastapi.responses import JSONResponse as _JSONResponse


@app.middleware("http")
async def simulate_readiness_failure(request, call_next):
    if os.environ.get("SIMULATE_READINESS_FAILURE", "false") == "true" and request.url.path == "/readyz":
        return _JSONResponse({"detail": "simulated readiness failure"}, status_code=503)
    return await call_next(request)
