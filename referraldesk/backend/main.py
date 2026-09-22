import asyncio
import os
import shutil
from datetime import datetime

import httpx
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

Base.metadata.create_all(bind=engine)

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

    referral_dir = os.path.join(UPLOAD_DIR, referral_id)
    os.makedirs(referral_dir, exist_ok=True)
    dest_path = os.path.join(referral_dir, file.filename)

    with open(dest_path, "wb") as out:
        shutil.copyfileobj(file.file, out)

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
