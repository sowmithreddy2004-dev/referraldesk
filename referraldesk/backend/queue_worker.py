"""
Local stand-in for Amazon SQS + a Lambda/worker consumer.

Why this exists: referral volume spikes (flu season, open enrollment) and we
don't want provider matching or SLA escalation to block the API's normal
request/response cycle. In production this queue is Amazon SQS and the
consumer is an AWS Lambda function or a dedicated worker process. Locally,
we simulate the same "producer enqueues -> consumer processes async" pattern
with an in-memory asyncio.Queue and a background task inside the FastAPI app.

Swapping this out for real SQS later means changing only enqueue_job() and
the consumer loop's polling call -- the rest of the app (API routes, DB
models, matching logic) does not change.
"""
import asyncio
import random
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from database import SessionLocal
from models import Referral, ReferralEvent, ReferralStatus
from matching import find_ranked_providers

job_queue: "asyncio.Queue[dict]" = asyncio.Queue()

SLA_HOURS_BY_SPECIALTY_DEFAULT = 72  # hours before a referral is considered overdue


async def enqueue_job(job: dict):
    """Producer side: called by API routes instead of processing inline."""
    await job_queue.put(job)


async def _process_match_job(referral_id: str):
    db: Session = SessionLocal()
    try:
        # Simulate realistic processing latency so the async behavior is visible in a demo.
        await asyncio.sleep(random.uniform(1.5, 3.5))

        referral = db.query(Referral).filter(Referral.id == referral_id).first()
        if not referral:
            return

        ranked = find_ranked_providers(db, referral.patient, referral.specialty_requested)

        if ranked:
            best = ranked[0]
            referral.matched_provider_id = best.id
            referral.status = ReferralStatus.SCHEDULED
            referral.sla_due_at = datetime.utcnow() + timedelta(hours=SLA_HOURS_BY_SPECIALTY_DEFAULT)
            db.add(ReferralEvent(
                referral_id=referral.id,
                event_type="MATCHED",
                detail=f"Matched to {best.name} ({best.specialty}) — status set to Scheduled.",
            ))
        else:
            referral.status = ReferralStatus.MATCHING
            db.add(ReferralEvent(
                referral_id=referral.id,
                event_type="NO_MATCH_FOUND",
                detail="No eligible in-network provider found yet; remains in Matching.",
            ))

        db.commit()
    finally:
        db.close()


async def worker_loop():
    """Background consumer loop -- the local equivalent of a Lambda triggered by SQS."""
    while True:
        job = await job_queue.get()
        try:
            if job["type"] == "MATCH_REFERRAL":
                await _process_match_job(job["referral_id"])
        except Exception as e:
            print(f"[worker] job failed: {job} error={e}")
        finally:
            job_queue.task_done()


async def sla_monitor_loop(poll_seconds: int = 30):
    """
    Periodic SLA sweep -- checks for referrals past their due date and escalates
    them to Overdue. In production this could be a scheduled Lambda (EventBridge
    cron); locally it's a simple asyncio loop.
    """
    while True:
        await asyncio.sleep(poll_seconds)
        db: Session = SessionLocal()
        try:
            now = datetime.utcnow()
            overdue = (
                db.query(Referral)
                .filter(Referral.sla_due_at.isnot(None))
                .filter(Referral.sla_due_at < now)
                .filter(Referral.status.notin_([ReferralStatus.COMPLETED, ReferralStatus.OVERDUE]))
                .all()
            )
            for referral in overdue:
                referral.status = ReferralStatus.OVERDUE
                db.add(ReferralEvent(
                    referral_id=referral.id,
                    event_type="SLA_ESCALATED",
                    detail="Referral passed its SLA window without completion; escalated to Overdue.",
                ))
            if overdue:
                db.commit()
        finally:
            db.close()
