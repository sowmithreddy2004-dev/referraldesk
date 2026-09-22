"""
Mock EHR Service

Simulates the patient/insurance data a real Electronic Health Record system
(e.g. Epic, Cerner) would expose via a FHIR-style API. ReferralDesk's backend
calls this over HTTP exactly like it would call a real EHR, so swapping this
out later for a genuine EHR integration doesn't require changing the caller's
code shape -- only the base URL and auth.

Run standalone on port 9000:
    uvicorn main:app --reload --port 9000
"""
from fastapi import FastAPI, HTTPException

app = FastAPI(title="Mock EHR Service")

FAKE_EHR_RECORDS = {
    "EHR-1001": {
        "ehr_patient_id": "EHR-1001",
        "first_name": "Maria",
        "last_name": "Gonzalez",
        "date_of_birth": "1985-03-14",
        "insurance": {"payer": "BlueCross PPO", "member_id": "BC-88213", "network_id": "NET-A"},
        "recent_visit_summary": "Annual physical, referred for elevated blood pressure.",
    },
    "EHR-1002": {
        "ehr_patient_id": "EHR-1002",
        "first_name": "James",
        "last_name": "Whitfield",
        "date_of_birth": "1972-11-02",
        "insurance": {"payer": "Aetna HMO", "member_id": "AE-44210", "network_id": "NET-B"},
        "recent_visit_summary": "Follow-up on joint pain, referred to orthopedics.",
    },
    "EHR-1003": {
        "ehr_patient_id": "EHR-1003",
        "first_name": "Aisha",
        "last_name": "Bello",
        "date_of_birth": "1990-07-22",
        "insurance": {"payer": "BlueCross PPO", "member_id": "BC-77120", "network_id": "NET-A"},
        "recent_visit_summary": "Skin lesion noted during checkup, referred to dermatology.",
    },
    "EHR-1004": {
        "ehr_patient_id": "EHR-1004",
        "first_name": "Wen",
        "last_name": "Zhao",
        "date_of_birth": "1966-01-30",
        "insurance": {"payer": "UnitedHealth Choice", "member_id": "UH-99871", "network_id": "NET-C"},
        "recent_visit_summary": "Elevated A1C, referred to endocrinology.",
    },
    "EHR-1005": {
        "ehr_patient_id": "EHR-1005",
        "first_name": "Daniel",
        "last_name": "Okafor",
        "date_of_birth": "2001-09-09",
        "insurance": {"payer": "Aetna HMO", "member_id": "AE-10093", "network_id": "NET-B"},
        "recent_visit_summary": "Sports injury, referred to orthopedics.",
    },
}


@app.get("/patients/{ehr_patient_id}")
def get_patient(ehr_patient_id: str):
    record = FAKE_EHR_RECORDS.get(ehr_patient_id)
    if not record:
        raise HTTPException(status_code=404, detail="Patient not found in Mock EHR")
    return record


@app.get("/health")
def health():
    return {"status": "ok", "service": "mock-ehr"}
