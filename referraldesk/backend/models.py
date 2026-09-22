import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    Column, String, Integer, Float, DateTime, ForeignKey, Enum, Text
)
from sqlalchemy.orm import relationship

from database import Base


def gen_id():
    return str(uuid.uuid4())


class ReferralStatus(str, enum.Enum):
    NEW = "New"
    MATCHING = "Matching"
    SCHEDULED = "Scheduled"
    COMPLETED = "Completed"
    OVERDUE = "Overdue"


class InsurancePlan(Base):
    __tablename__ = "insurance_plans"

    id = Column(String, primary_key=True, default=gen_id)
    name = Column(String, nullable=False)
    network_id = Column(String, nullable=False)  # used to match provider networks

    patients = relationship("Patient", back_populates="insurance_plan")


class Patient(Base):
    __tablename__ = "patients"

    id = Column(String, primary_key=True, default=gen_id)
    first_name = Column(String, nullable=False)
    last_name = Column(String, nullable=False)
    date_of_birth = Column(String, nullable=False)
    ehr_patient_id = Column(String, nullable=True)  # id in the Mock EHR system
    insurance_plan_id = Column(String, ForeignKey("insurance_plans.id"))
    latitude = Column(Float, default=29.7604)   # default: Houston, TX
    longitude = Column(Float, default=-95.3698)

    insurance_plan = relationship("InsurancePlan", back_populates="patients")
    referrals = relationship("Referral", back_populates="patient")


class Provider(Base):
    __tablename__ = "providers"

    id = Column(String, primary_key=True, default=gen_id)
    name = Column(String, nullable=False)
    specialty = Column(String, nullable=False, index=True)
    network_ids = Column(String, nullable=False)  # comma-separated list of network ids
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    availability_score = Column(Integer, default=5)  # 0-10, higher = more openings

    referrals = relationship("Referral", back_populates="matched_provider")


class Referral(Base):
    __tablename__ = "referrals"

    id = Column(String, primary_key=True, default=gen_id)
    patient_id = Column(String, ForeignKey("patients.id"), nullable=False)
    specialty_requested = Column(String, nullable=False)
    status = Column(Enum(ReferralStatus), default=ReferralStatus.NEW, nullable=False)
    matched_provider_id = Column(String, ForeignKey("providers.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    sla_due_at = Column(DateTime, nullable=True)
    notes = Column(Text, nullable=True)

    patient = relationship("Patient", back_populates="referrals")
    matched_provider = relationship("Provider", back_populates="referrals")
    events = relationship(
        "ReferralEvent", back_populates="referral",
        order_by="ReferralEvent.created_at", cascade="all, delete-orphan"
    )
    documents = relationship(
        "ReferralDocument", back_populates="referral", cascade="all, delete-orphan"
    )


class ReferralEvent(Base):
    """Append-only audit log. Rows are never updated or deleted."""
    __tablename__ = "referral_events"

    id = Column(String, primary_key=True, default=gen_id)
    referral_id = Column(String, ForeignKey("referrals.id"), nullable=False)
    event_type = Column(String, nullable=False)   # e.g. CREATED, MATCHED, STATUS_CHANGED
    detail = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    referral = relationship("Referral", back_populates="events")


class ReferralDocument(Base):
    __tablename__ = "referral_documents"

    id = Column(String, primary_key=True, default=gen_id)
    referral_id = Column(String, ForeignKey("referrals.id"), nullable=False)
    file_name = Column(String, nullable=False)
    storage_path = Column(String, nullable=False)  # local path now, S3 key later
    content_type = Column(String, nullable=True)
    uploaded_at = Column(DateTime, default=datetime.utcnow)

    referral = relationship("Referral", back_populates="documents")
