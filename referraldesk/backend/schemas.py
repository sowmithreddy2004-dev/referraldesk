from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel


class InsurancePlanOut(BaseModel):
    id: str
    name: str
    network_id: str

    class Config:
        from_attributes = True


class PatientOut(BaseModel):
    id: str
    first_name: str
    last_name: str
    date_of_birth: str
    insurance_plan: Optional[InsurancePlanOut] = None

    class Config:
        from_attributes = True


class ProviderOut(BaseModel):
    id: str
    name: str
    specialty: str
    availability_score: int

    class Config:
        from_attributes = True


class ReferralEventOut(BaseModel):
    id: str
    event_type: str
    detail: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class ReferralDocumentOut(BaseModel):
    id: str
    file_name: str
    content_type: Optional[str] = None
    uploaded_at: datetime

    class Config:
        from_attributes = True


class ReferralCreate(BaseModel):
    patient_id: str
    specialty_requested: str
    notes: Optional[str] = None


class ReferralOut(BaseModel):
    id: str
    patient: PatientOut
    specialty_requested: str
    status: str
    matched_provider: Optional[ProviderOut] = None
    created_at: datetime
    sla_due_at: Optional[datetime] = None
    notes: Optional[str] = None
    events: List[ReferralEventOut] = []
    documents: List[ReferralDocumentOut] = []

    class Config:
        from_attributes = True


class ReferralStatusUpdate(BaseModel):
    status: str
