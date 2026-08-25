import os
import logging
from redis import Redis
from rq import Queue

logger = logging.getLogger(__name__)

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

_redis_conn: Redis = None
_recovery_queue: Queue = None

def get_redis_connection() -> Redis:
    global _redis_conn
    if _redis_conn is None:
        try:
            conn = Redis.from_url(REDIS_URL, socket_timeout=1.0)
            conn.ping()
            _redis_conn = conn
        except Exception as e:
            logger.warning(f"Redis unavailable at '{REDIS_URL}' ({e})")
            raise ConnectionError(f"Redis connection failed: {e}")
    return _redis_conn

def get_queue() -> Queue:
    global _recovery_queue
    if _recovery_queue is None:
        conn = get_redis_connection()
        _recovery_queue = Queue("recovery_queue", connection=conn)
    return _recovery_queue
