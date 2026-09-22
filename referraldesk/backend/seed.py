"""
Run this once after the tables exist to populate realistic demo data:
    python seed.py
"""
from database import SessionLocal, Base, engine
from models import Patient, Provider, InsurancePlan

Base.metadata.create_all(bind=engine)

db = SessionLocal()

try:
    if db.query(InsurancePlan).count() > 0:
        print("Data already seeded, skipping.")
    else:
        plan_a = InsurancePlan(name="BlueCross PPO", network_id="NET-A")
        plan_b = InsurancePlan(name="Aetna HMO", network_id="NET-B")
        plan_c = InsurancePlan(name="UnitedHealth Choice", network_id="NET-C")
        db.add_all([plan_a, plan_b, plan_c])
        db.commit()

        patients = [
            Patient(first_name="Maria", last_name="Gonzalez", date_of_birth="1985-03-14",
                    ehr_patient_id="EHR-1001", insurance_plan_id=plan_a.id,
                    latitude=29.7604, longitude=-95.3698),
            Patient(first_name="James", last_name="Whitfield", date_of_birth="1972-11-02",
                    ehr_patient_id="EHR-1002", insurance_plan_id=plan_b.id,
                    latitude=29.7752, longitude=-95.4137),
            Patient(first_name="Aisha", last_name="Bello", date_of_birth="1990-07-22",
                    ehr_patient_id="EHR-1003", insurance_plan_id=plan_a.id,
                    latitude=29.7304, longitude=-95.3419),
            Patient(first_name="Wen", last_name="Zhao", date_of_birth="1966-01-30",
                    ehr_patient_id="EHR-1004", insurance_plan_id=plan_c.id,
                    latitude=29.7080, longitude=-95.4020),
            Patient(first_name="Daniel", last_name="Okafor", date_of_birth="2001-09-09",
                    ehr_patient_id="EHR-1005", insurance_plan_id=plan_b.id,
                    latitude=29.7899, longitude=-95.3499),
        ]
        db.add_all(patients)

        providers = [
            Provider(name="Dr. Sarah Kim", specialty="Cardiology", network_ids="NET-A,NET-B",
                     latitude=29.7600, longitude=-95.3600, availability_score=8),
            Provider(name="Dr. Robert Cole", specialty="Cardiology", network_ids="NET-C",
                     latitude=29.7700, longitude=-95.4000, availability_score=4),
            Provider(name="Dr. Priya Patel", specialty="Dermatology", network_ids="NET-A,NET-C",
                     latitude=29.7400, longitude=-95.3700, availability_score=9),
            Provider(name="Dr. Marcus Webb", specialty="Orthopedics", network_ids="NET-B",
                     latitude=29.7850, longitude=-95.3550, availability_score=6),
            Provider(name="Dr. Lin Chen", specialty="Endocrinology", network_ids="NET-A,NET-B,NET-C",
                     latitude=29.7200, longitude=-95.3900, availability_score=7),
            Provider(name="Dr. Angela Reyes", specialty="Cardiology", network_ids="NET-A",
                     latitude=29.7550, longitude=-95.3650, availability_score=10),
        ]
        db.add_all(providers)

        db.commit()
        print(f"Seeded {len(patients)} patients, {len(providers)} providers, 3 insurance plans.")
finally:
    db.close()
