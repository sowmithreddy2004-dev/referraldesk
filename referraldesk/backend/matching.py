"""
In-network provider matching engine.

Ranks eligible providers for a referral by:
  1. Specialty match (hard filter)
  2. Insurance network match (hard filter)
  3. Availability score (higher is better)
  4. Distance from patient (closer is better, simple Euclidean approx on lat/lng)

This is intentionally simple / deterministic so it's easy to demo and explain
in an interview: it is a ranking function, not a black box.
"""
import math
from sqlalchemy.orm import Session

from models import Provider, Patient


def _distance(lat1, lon1, lat2, lon2):
    # Flat-earth approximation is fine at city scale for a demo.
    return math.sqrt((lat1 - lat2) ** 2 + (lon1 - lon2) ** 2)


def find_ranked_providers(db: Session, patient: Patient, specialty: str, limit: int = 5):
    network_id = patient.insurance_plan.network_id if patient.insurance_plan else None

    candidates = db.query(Provider).filter(Provider.specialty == specialty).all()

    eligible = []
    for p in candidates:
        provider_networks = [n.strip() for n in p.network_ids.split(",")]
        in_network = network_id is not None and network_id in provider_networks
        if not in_network:
            continue
        dist = _distance(patient.latitude, patient.longitude, p.latitude, p.longitude)
        # Simple weighted score: availability matters most, distance is a tiebreaker.
        score = (p.availability_score * 10) - (dist * 5)
        eligible.append((score, dist, p))

    eligible.sort(key=lambda row: row[0], reverse=True)
    return [p for _, _, p in eligible[:limit]]
