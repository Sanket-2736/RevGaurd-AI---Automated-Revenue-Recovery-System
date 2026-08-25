import time
import uuid
import json
import logging
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, HTTPException, Depends, Query
from fastapi.responses import StreamingResponse
from sqlmodel import Session, select
from rq.job import Job
from rq.exceptions import NoSuchJobError

from app.db import get_session
from app.models import RecoveryCase, CaseStatus
from app.queue import get_queue, get_redis_connection
from app.tasks import process_case

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/batch", tags=["batch"])

# In-memory fallback batch tracking cache when Redis/RQ is offline
_FALLBACK_BATCH_STORE: Dict[str, Dict[str, Any]] = {}

@router.post("/run")
def run_batch_processing(
    limit: int = Query(default=50, ge=1, le=1000),
    session: Session = Depends(get_session)
):
    """
    Enqueues N DETECTED cases for asynchronous processing and returns a batch_id immediately (non-blocking).
    """
    # Fetch DETECTED cases up to limit
    detected_cases = session.exec(
        select(RecoveryCase)
        .where(RecoveryCase.status == CaseStatus.DETECTED)
        .limit(limit)
    ).all()

    if not detected_cases:
        return {
            "batch_id": None,
            "total_enqueued": 0,
            "message": "No DETECTED cases found for batch processing."
        }

    batch_id = f"batch_{int(time.time())}_{uuid.uuid4().hex[:6]}"
    job_ids = []
    use_rq = True

    try:
        q = get_queue()
        r = get_redis_connection()

        for case in detected_cases:
            job = q.enqueue(process_case, case.id, batch_id, job_id=f"{batch_id}_case_{case.id}")
            job_ids.append(job.id)

        # Store job IDs list under Redis key for batch status tracking (expires in 24h)
        batch_key = f"batch:{batch_id}:jobs"
        r.sadd(batch_key, *job_ids)
        r.expire(batch_key, 86400)

        logger.info(f"Enqueued {len(job_ids)} jobs under batch '{batch_id}' via RQ queue.")

    except Exception as e:
        logger.warning(f"Redis/RQ enqueue unavailable ({e}); executing fallback processing for batch '{batch_id}'")
        use_rq = False
        results = []
        for case in detected_cases:
            res = process_case(case.id, batch_id=batch_id)
            results.append(res)

        _FALLBACK_BATCH_STORE[batch_id] = {
            "batch_id": batch_id,
            "total": len(detected_cases),
            "completed": len(results),
            "failed": 0,
            "pending": 0,
            "progress_pct": 100.0,
            "is_finished": True,
            "results": results
        }

    return {
        "batch_id": batch_id,
        "total_enqueued": len(detected_cases),
        "mode": "RQ_REDIS" if use_rq else "INLINE_FALLBACK",
        "message": f"Successfully enqueued {len(detected_cases)} cases for batch processing."
    }

@router.get("/{batch_id}/status")
def get_batch_status(batch_id: str):
    """
    Polls processing progress, status metrics, and results for a given batch_id.
    """
    # Check fallback in-memory store first
    if batch_id in _FALLBACK_BATCH_STORE:
        return _FALLBACK_BATCH_STORE[batch_id]

    try:
        r = get_redis_connection()
        batch_key = f"batch:{batch_id}:jobs"
        raw_job_ids = r.smembers(batch_key)

        if not raw_job_ids:
            raise HTTPException(status_code=404, detail=f"Batch ID '{batch_id}' not found.")

        job_ids = [jid.decode("utf-8") if isinstance(jid, bytes) else jid for jid in raw_job_ids]
        total = len(job_ids)
        completed = 0
        failed = 0
        pending = 0
        results = []

        for jid in job_ids:
            try:
                job = Job.fetch(jid, connection=r)
                status = job.get_status()

                if status == "finished":
                    completed += 1
                    if job.result:
                        results.append(job.result)
                elif status == "failed":
                    failed += 1
                else:
                    pending += 1
            except NoSuchJobError:
                failed += 1

        is_finished = (completed + failed) == total
        progress_pct = round((completed + failed) / total * 100.0, 1) if total > 0 else 0.0

        return {
            "batch_id": batch_id,
            "total": total,
            "completed": completed,
            "failed": failed,
            "pending": pending,
            "progress_pct": progress_pct,
            "is_finished": is_finished,
            "results": results
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error checking batch status for '{batch_id}': {e}")
        raise HTTPException(status_code=500, detail=f"Failed to check batch status: {str(e)}")

@router.get("/{batch_id}/stream")
def stream_batch_events(batch_id: str):
    """
    Server-Sent Events (SSE) endpoint that pushes a JSON event every time a case in batch_id finishes processing.
    Pushed event schema: {case_id, case_type, action, approved, amount_recovered, route}
    """
    def event_generator():
        # Check fallback store first for instant replay if available
        if batch_id in _FALLBACK_BATCH_STORE:
            fb = _FALLBACK_BATCH_STORE[batch_id]
            for res in fb.get("results", []):
                evt = res.get("sse_event")
                if evt:
                    yield f"data: {json.dumps(evt)}\n\n"
            yield f"data: {json.dumps({'batch_id': batch_id, 'is_finished': True, 'progress_pct': 100.0})}\n\n"
            return

        # Connect to Redis Pub/Sub
        try:
            r = get_redis_connection()
            pubsub = r.pubsub()
            pubsub.subscribe(f"batch_events:{batch_id}")
            logger.info(f"SSE client subscribed to Pub/Sub channel 'batch_events:{batch_id}'")

            timeout_counter = 0
            try:
                while True:
                    message = pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
                    if message and message["type"] == "message":
                        data_str = message["data"].decode("utf-8") if isinstance(message["data"], bytes) else str(message["data"])
                        yield f"data: {data_str}\n\n"
                        timeout_counter = 0
                    else:
                        timeout_counter += 1
                        # Send periodic keep-alive ping comment every 15s
                        if timeout_counter % 15 == 0:
                            yield ": keep-alive ping\n\n"

                        # Check if batch is finished in DB/Redis
                        try:
                            status_info = get_batch_status(batch_id)
                            if status_info.get("is_finished"):
                                yield f"data: {json.dumps({'batch_id': batch_id, 'is_finished': True, 'progress_pct': 100.0})}\n\n"
                                break
                        except Exception:
                            pass
            except (GeneratorExit, Exception) as disconnect_err:
                logger.info(f"SSE client disconnected from stream batch '{batch_id}' ({disconnect_err})")
                try:
                    pubsub.unsubscribe(f"batch_events:{batch_id}")
                    pubsub.close()
                except Exception:
                    pass
                return

        except Exception as e:
            logger.error(f"Error in SSE event stream for batch '{batch_id}': {e}")
            yield f"data: {json.dumps({'error': str(e)})}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")

